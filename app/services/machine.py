"""CCE MC-1000 machine model.

The 16 KiB firmware ROM is executed unchanged. The surrounding machine is
modelled in Python from the public MAME MC-1000 driver and MC-1000 technical
material. This module intentionally keeps firmware semantics inside the ROM:
BASIC tokenisation, commands, error messages, cassette protocol and monitor
routines are not reimplemented as a second interpreter.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import io
import struct
import threading
import time
import wave

from z80_python import Z80CPU

CPU_HZ = 3_579_545
AY_HZ = CPU_HZ / 2
IRQ_HZ = 367
IRQ_PERIOD = CPU_HZ / IRQ_HZ
# MAME's comments for the MC-1000 NE555 circuit: low about 6.93 us.
IRQ_PULSE_TSTATES = CPU_HZ * 6.93e-6

# MC6847 6-bit alphanumeric repertoire. Bit 7 is INV on the MC-1000.
MC6847_CHARS = '@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]↑← !"#$%&\'()*+,-./0123456789:;<=>?'

# MC-1000 keyboard matrix, active low. Each tuple is (row, bit mask).
KEYS = {
    '@': (0, 0x01), 'H': (0, 0x02), 'P': (0, 0x04), 'X': (0, 0x08), '0': (0, 0x10), '8': (0, 0x20),
    'A': (1, 0x01), 'I': (1, 0x02), 'Q': (1, 0x04), 'Y': (1, 0x08), '1': (1, 0x10), '9': (1, 0x20),
    'B': (2, 0x01), 'J': (2, 0x02), 'R': (2, 0x04), 'Z': (2, 0x08), '2': (2, 0x10), ':': (2, 0x20),
    'C': (3, 0x01), 'K': (3, 0x02), 'S': (3, 0x04), 'ENTER': (3, 0x08), '3': (3, 0x10), ';': (3, 0x20),
    'D': (4, 0x01), 'L': (4, 0x02), 'T': (4, 0x04), 'SPACE': (4, 0x08), '4': (4, 0x10), ',': (4, 0x20),
    'E': (5, 0x01), 'M': (5, 0x02), 'U': (5, 0x04), 'BACKSPACE': (5, 0x08), '5': (5, 0x10), '-': (5, 0x20),
    'F': (6, 0x01), 'N': (6, 0x02), 'V': (6, 0x04), '^': (6, 0x08), '6': (6, 0x10), '.': (6, 0x20),
    'G': (7, 0x01), 'O': (7, 0x02), 'W': (7, 0x04), 'RESET': (7, 0x08), '7': (7, 0x10), '/': (7, 0x20),
}

SHIFTED = {
    '!': '1', '"': '2', '#': '3', '$': '4', '%': '5', '&': '6', "'": '7',
    '(': '8', ')': '9', '*': ':', '+': ';', '<': ',', '=': '-', '>': '.', '?': '/',
}

# AY-3-8910 implemented register widths. Registers 14/15 are 8-bit I/O ports.
AY_MASKS = [0xFF, 0x0F, 0xFF, 0x0F, 0xFF, 0x0F, 0x1F, 0xFF,
            0x1F, 0x1F, 0x1F, 0xFF, 0xFF, 0x0F, 0xFF, 0xFF]


class MC1000CPU(Z80CPU):
    """Validated Z80 core bound to the MC-1000 host buses."""

    def __init__(self, machine: 'MC1000'):
        self.machine = machine
        super().__init__()

    def read_byte(self, addr: int) -> int:
        return self.machine.read(addr)

    def write_byte(self, addr: int, value: int) -> None:
        self.machine.write(addr, value)

    def read_port(self, addr: int) -> int:
        return self.machine.in_port(addr)

    def write_port(self, addr: int, value: int) -> None:
        self.machine.out_port(addr, value)


@dataclass
class AY8910:
    """AY-3-8910 register and I/O-facing model.

    Tone/noise synthesis is a presentation concern in the browser. The machine
    side preserves all 16 registers and the MC-1000's port A/B wiring.
    """

    machine: 'MC1000'
    selected: int = 0
    regs: list[int] = field(default_factory=lambda: [0] * 16)

    def reset(self) -> None:
        self.selected = 0
        self.regs[:] = [0] * 16

    def select(self, value: int) -> None:
        self.selected = value & 0x0F

    def write(self, value: int) -> None:
        r = self.selected
        value &= AY_MASKS[r]
        old = self.regs[r]
        self.regs[r] = value
        if r == 14:
            # MAME: AY port A -> key latch and cassette output on bit 7.
            self.machine.key_latch = value
            level = -1.0 if (value & 0x80) else 1.0
            if level != self.machine.cassette_out_level:
                self.machine.cassette_out_level = level
                self.machine._record_edge()
        if old != value:
            self.machine.ay_revision += 1

    def read(self) -> int:
        # MAME: AY port B reads keyboard matrix + cassette input.
        if self.selected == 15:
            return self.machine.keyboard_read()
        return self.regs[self.selected] & AY_MASKS[self.selected]


class MC1000:
    """Functional model of the CCE MC-1000 around the original ROM."""

    def __init__(self, rom_path: str | Path, ram_kb: int = 16):
        self.rom = Path(rom_path).read_bytes()
        if len(self.rom) != 0x4000:
            raise ValueError('MC-1000 ROM must be exactly 16384 bytes')
        if ram_kb not in (16, 48):
            raise ValueError('ram_kb must be 16 or 48')

        # The MAME driver allocates a C000-sized backing store and maps portions
        # according to the installed RAM option.
        self.ram = bytearray(0xC000)
        self.vram = bytearray(0x1800)
        self.vram80 = bytearray(0x0800)
        self.ram_kb = ram_kb

        self.boot_mirror = True
        self.vdg_ctrl = 0
        self.vram80_bank = 0

        self.key_rows = [0xFF] * 8
        self.shift = False
        self.ctrl = False
        self.key_latch = 0xFF

        self.cassette_samples: list[float] = []
        self.cassette_rate = 44_100
        self.cassette_play = False
        self.cassette_start_t = 0
        self.cassette_out_level = 1.0
        self.recording = False
        self.record_edges: list[tuple[int, float]] = []

        self.printer_busy = 0
        self.printer_data = 0
        self.printer_strobe = 1
        self.printer_output = bytearray()

        self.ay_revision = 0
        self.ay = AY8910(self)
        self.cpu = MC1000CPU(self)
        self.tstates = 0
        self.lock = threading.RLock()
        self.running = False
        self.thread: threading.Thread | None = None
        self.next_irq_assert = IRQ_PERIOD - IRQ_PULSE_TSTATES
        self.next_irq_clear = IRQ_PERIOD

    def reset(self) -> None:
        """Board reset.

        RAM/VRAM are deliberately not cleared, matching a reset rather than a
        simulated power-off. Firmware reinitialises the visible machine state.
        """
        with self.lock:
            self.boot_mirror = True
            self.vdg_ctrl = 0
            self.vram80_bank = 0
            self.key_latch = 0xFF
            self.key_rows[:] = [0xFF] * 8
            self.shift = self.ctrl = False
            self.ay.reset()
            self.ay_revision += 1
            self.cpu = MC1000CPU(self)
            self.tstates = 0
            self.next_irq_assert = IRQ_PERIOD - IRQ_PULSE_TSTATES
            self.next_irq_clear = IRQ_PERIOD

    # ---------------------------------------------------------------------
    # Memory
    # ---------------------------------------------------------------------
    def read(self, addr: int) -> int:
        addr &= 0xFFFF
        if addr < 0x2000:
            return self.rom[addr] if self.boot_mirror else self.ram[addr]
        if addr < 0x2800:
            return self.vram80[addr - 0x2000] if self.vram80_bank else self.ram[addr]
        if addr < 0x4000:
            return self.ram[addr]
        if addr < 0x8000:
            return self.ram[addr] if self.ram_kb > 16 else 0xFF
        if addr < 0x9800:
            # MAME: bit 0 of port 80h controls CPU access to MC6847 RAM.
            if not (self.vdg_ctrl & 1):
                return self.vram[addr - 0x8000]
            return self.ram[addr] if self.ram_kb > 16 else 0xFF
        if addr < 0xC000:
            return self.ram[addr] if self.ram_kb > 16 else 0xFF
        return self.rom[addr - 0xC000]

    def write(self, addr: int, value: int) -> None:
        addr &= 0xFFFF
        value &= 0xFF
        if addr < 0x2000:
            if not self.boot_mirror:
                self.ram[addr] = value
        elif addr < 0x2800:
            if self.vram80_bank:
                self.vram80[addr - 0x2000] = value
            else:
                self.ram[addr] = value
        elif addr < 0x4000:
            self.ram[addr] = value
        elif addr < 0x8000:
            if self.ram_kb > 16:
                self.ram[addr] = value
        elif addr < 0x9800:
            if not (self.vdg_ctrl & 1):
                self.vram[addr - 0x8000] = value
            elif self.ram_kb > 16:
                self.ram[addr] = value
        elif addr < 0xC000 and self.ram_kb > 16:
            self.ram[addr] = value

    # ---------------------------------------------------------------------
    # I/O map
    # 04h printer status/strobe, 05h printer data, 12h optional 80-column bank,
    # 20h/40h/60h AY, 80h MC6847/COL32 mode and banking.
    # ---------------------------------------------------------------------
    def in_port(self, port: int) -> int:
        p = port & 0xFF
        if p == 0x04:
            return self.printer_busy & 1
        if p == 0x40:
            return self.ay.read()
        return 0xFF

    def out_port(self, port: int, value: int) -> None:
        p = port & 0xFF
        value &= 0xFF
        if p == 0x04:
            new_strobe = value & 1
            # Centronics STROBE is active low. Capture the byte on falling edge.
            if self.printer_strobe and not new_strobe:
                self.printer_output.append(self.printer_data)
            self.printer_strobe = new_strobe
        elif p == 0x05:
            self.printer_data = value
        elif p == 0x12:
            self.vram80_bank = value & 1
        elif p == 0x20:
            self.ay.select(value)
        elif p == 0x60:
            self.ay.write(value)
        elif p == 0x80:
            self.vdg_ctrl = value

    # ---------------------------------------------------------------------
    # Keyboard
    # ---------------------------------------------------------------------
    def keyboard_read(self) -> int:
        data = 0xFF
        for row in range(8):
            if not (self.key_latch & (1 << row)):
                data &= self.key_rows[row]
        data = (data & 0x3F) | (0 if self.shift else 0x40) | (0 if self.ctrl else 0x80)
        if self.cassette_play and self._cassette_level() >= 0:
            data &= 0x7F
        return data

    def key(self, name: str, down: bool = True) -> None:
        name = name.upper()
        if name == 'SHIFT':
            self.shift = down
            return
        if name in ('CTRL', 'CONTROL'):
            self.ctrl = down
            return
        if name == 'RESET' and down:
            self.reset()
            return
        if name not in KEYS:
            return
        row, mask = KEYS[name]
        if down:
            self.key_rows[row] &= (~mask) & 0xFF
        else:
            self.key_rows[row] |= mask

    def type_char(self, ch: str) -> None:
        """Inject one ASCII character through the real keyboard matrix.

        The relatively long hold/release windows are intentional. They let the
        firmware's own keyboard scan/debounce path observe every character.
        """
        shift = False
        key = ch.upper()
        if ch in SHIFTED:
            key = SHIFTED[ch]
            shift = True
        elif ch == ' ':
            key = 'SPACE'
        elif ch in ('\r', '\n'):
            key = 'ENTER'
        if key in KEYS:
            self.shift = shift
            self.key(key, True)
            self.run_cycles(int(CPU_HZ * 0.045))
            self.key(key, False)
            self.shift = False
            self.run_cycles(int(CPU_HZ * 0.045))

    def type_text(self, text: str) -> None:
        for ch in text:
            self.type_char(ch)

    # ---------------------------------------------------------------------
    # Clock and NE555 IRQ
    # ---------------------------------------------------------------------
    def run_cycles(self, budget: int) -> int:
        used = 0
        with self.lock:
            while used < budget:
                # MAME changes bank 0000-1FFF from boot ROM to RAM as a side
                # effect of the first opcode fetch at C000-FFFF.
                if self.boot_mirror and 0xC000 <= self.cpu.pc <= 0xFFFF:
                    self.boot_mirror = False

                t = self.tstates
                if t >= self.next_irq_clear:
                    self.cpu.clear_maskable_interrupt()
                    while t >= self.next_irq_clear:
                        self.next_irq_clear += IRQ_PERIOD
                        self.next_irq_assert += IRQ_PERIOD
                elif t >= self.next_irq_assert:
                    if not self.cpu.maskable_interrupt_pending:
                        self.cpu.request_maskable_interrupt(0xFF)

                cyc = self.cpu.step()
                self.tstates += cyc
                used += cyc
        return used

    def run_for(self, seconds: float) -> int:
        return self.run_cycles(int(CPU_HZ * seconds))

    def start(self) -> None:
        if self.running:
            return
        self.running = True

        def loop() -> None:
            last = time.perf_counter()
            while self.running:
                now = time.perf_counter()
                dt = min(0.05, now - last)
                last = now
                self.run_cycles(max(2_000, int(CPU_HZ * dt)))
                time.sleep(0.001)

        self.thread = threading.Thread(target=loop, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.running = False

    # ---------------------------------------------------------------------
    # Cassette. The ROM performs the protocol. We only provide analogue-sign
    # conversion to/from WAV on the same AY pins as the original machine.
    # ---------------------------------------------------------------------
    def load_wav(self, data: bytes) -> None:
        with wave.open(io.BytesIO(data), 'rb') as w:
            if w.getcomptype() != 'NONE':
                raise ValueError('WAV cassette must be uncompressed PCM')
            self.cassette_rate = w.getframerate()
            n = w.getnframes()
            channels = w.getnchannels()
            width = w.getsampwidth()
            raw = w.readframes(n)

        if width == 1:
            vals = [b - 128 for b in raw]
        elif width == 2:
            vals = struct.unpack('<' + 'h' * (len(raw) // 2), raw)
        else:
            raise ValueError('WAV cassette supports 8-bit or 16-bit PCM')

        # Average channels and remove DC bias. The firmware sees only polarity,
        # exactly as the digital cassette input callback in the emulator model.
        mono = []
        for i in range(0, len(vals), channels):
            frame = vals[i:i + channels]
            mono.append(sum(frame) / max(1, len(frame)))
        dc = sum(mono) / len(mono) if mono else 0.0
        self.cassette_samples = [v - dc for v in mono]
        self.cassette_start_t = self.tstates
        self.cassette_play = True

    def _cassette_level(self) -> float:
        if not self.cassette_samples:
            return -1.0
        idx = int((self.tstates - self.cassette_start_t) * self.cassette_rate / CPU_HZ)
        if idx >= len(self.cassette_samples):
            self.cassette_play = False
            return -1.0
        return 1.0 if self.cassette_samples[max(0, idx)] >= 0 else -1.0

    def begin_record(self) -> None:
        self.recording = True
        self.record_edges = [(self.tstates, self.cassette_out_level)]

    def _record_edge(self) -> None:
        if self.recording:
            self.record_edges.append((self.tstates, self.cassette_out_level))

    def end_record_wav(self) -> bytes:
        self.recording = False
        if not self.record_edges:
            return b''
        end = self.tstates
        base = self.record_edges[0][0]
        n = max(1, int((end - base) * 44_100 / CPU_HZ))
        pcm = [0] * n
        ei = 0
        level = self.record_edges[0][1]
        for j in range(n):
            t = base + j * CPU_HZ / 44_100
            while ei + 1 < len(self.record_edges) and self.record_edges[ei + 1][0] <= t:
                ei += 1
                level = self.record_edges[ei][1]
            pcm[j] = 22_000 if level > 0 else -22_000

        out = io.BytesIO()
        with wave.open(out, 'wb') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(44_100)
            w.writeframes(struct.pack('<' + 'h' * len(pcm), *pcm))
        return out.getvalue()

    # ---------------------------------------------------------------------
    # Video/state presentation
    # ---------------------------------------------------------------------
    def text_screen(self) -> list[str]:
        rows = []
        for y in range(16):
            line = ''
            for x in range(32):
                v = self.vram[y * 32 + x]
                code = v & 0x3F
                line += MC6847_CHARS[code] if code < len(MC6847_CHARS) else '?'
            rows.append(line)
        return rows

    def video_mode(self) -> dict[str, int | str | bool]:
        c = self.vdg_ctrl
        ag = bool(c & 0x80)
        as_mode = bool(c & 0x40)
        int_ext = bool(c & 0x20)
        gm = ((c >> 4) & 1) << 2 | ((c >> 3) & 1) << 1 | ((c >> 2) & 1)
        css = bool(c & 0x02)
        if not ag:
            if as_mode:
                if int_ext:
                    return {'kind': 'semigraphics', 'name': 'SG6', 'width': 64, 'height': 48, 'gm': gm, 'css': css}
                return {'kind': 'semigraphics', 'name': 'SG4', 'width': 64, 'height': 32, 'gm': gm, 'css': css}
            return {'kind': 'text', 'name': 'ALPHA', 'width': 32, 'height': 16, 'gm': gm, 'css': css, 'external': int_ext}
        names = ['CG1', 'RG1', 'CG2', 'RG2', 'CG3', 'RG3', 'CG6', 'RG6']
        dims = [(64, 64), (128, 64), (128, 64), (128, 96), (128, 96), (128, 192), (128, 192), (256, 192)]
        w, h = dims[gm]
        return {'kind': 'graphics', 'name': names[gm], 'width': w, 'height': h, 'gm': gm, 'css': css}

    def printer_text(self) -> str:
        return self.printer_output.decode('latin-1', errors='replace')

    def snapshot(self) -> dict:
        with self.lock:
            return {
                'text': self.text_screen(),
                'vdg_ctrl': self.vdg_ctrl,
                'video_mode': self.video_mode(),
                'vram': self.vram.hex(),
                'pc': self.cpu.pc,
                'sp': self.cpu.sp,
                'af': (self.cpu.a << 8) | self.cpu.f.byte,
                'bc': (self.cpu.b << 8) | self.cpu.c,
                'de': (self.cpu.d << 8) | self.cpu.e,
                'hl': (self.cpu.h << 8) | self.cpu.l,
                'ix': self.cpu.ix,
                'iy': self.cpu.iy,
                'i': self.cpu.i,
                'r': self.cpu.r,
                'im': self.cpu.im,
                'iff1': self.cpu.iff1,
                'tstates': self.tstates,
                'ay': self.ay.regs[:],
                'ay_clock': AY_HZ,
                'cassette_play': self.cassette_play,
                'cassette_recording': self.recording,
                'printer_bytes': len(self.printer_output),
                'ram_kb': self.ram_kb,
            }
