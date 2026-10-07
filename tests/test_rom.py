from pathlib import Path
import hashlib

from app.services.machine import MC1000

ROOT = Path(__file__).resolve().parents[1]
ROM = ROOT / 'roms' / 'mc1000.rom'
EXPECTED_SHA256 = '460e92dc45a8a877a4f44da9955dbe8a52d094c2aaaa2037f842c6b3af7f306a'


def new_machine() -> MC1000:
    m = MC1000(ROM)
    m.reset()
    m.run_for(0.9)
    return m


def visible(m: MC1000) -> str:
    return '\n'.join(m.text_screen())


def command(m: MC1000, text: str, settle: float = 0.30) -> str:
    m.type_text(text + '\r')
    m.run_for(settle)
    return visible(m)


def test_rom_identity():
    data = ROM.read_bytes()
    assert len(data) == 16_384
    assert hashlib.sha256(data).hexdigest() == EXPECTED_SHA256


def test_real_rom_boots_to_basic_prompt():
    m = new_machine()
    text = visible(m)
    assert 'MC-1000 CCE COLOR COMPUTER' in text
    assert '14618 BYTES' in text
    assert 'OK' in text
    assert not m.boot_mirror
    assert m.tstates > 1_000_000


def test_keyboard_matrix_executes_basic_expression():
    m = new_machine()
    text = command(m, 'PRINT 2+2')
    assert 'PRINT 2+2' in text
    assert ' 4' in text
    assert 'OK' in text


def test_basic_selects_documented_video_modes():
    m = new_machine()
    command(m, 'GR')
    assert m.vdg_ctrl == 0x89
    assert m.video_mode()['name'] == 'CG2'
    assert (m.video_mode()['width'], m.video_mode()['height']) == (128, 64)

    command(m, 'HGR')
    assert m.vdg_ctrl == 0x9F
    assert m.video_mode()['name'] == 'RG6'
    assert (m.video_mode()['width'], m.video_mode()['height']) == (256, 192)

    command(m, 'TEXT')
    assert m.vdg_ctrl == 0x01
    assert m.video_mode()['kind'] == 'text'


def test_memory_poke_peek_and_base_80_column_behavior():
    m = new_machine()
    text = command(m, 'POKE 4096,42:PRINT PEEK(4096)')
    assert ' 42' in text

    text = command(m, 'COLUMN 80')
    assert '?TI ERRO' in text

    text = command(m, 'COLUMN 31')
    assert '?PI ERRO' in text

    command(m, 'COLUMN 32')
    assert m.vdg_ctrl == 0x01


def test_direct_vdg_semigraphics_modes_are_exposed():
    m = new_machine()
    m.out_port(0x80, 0x40)
    assert m.video_mode()['name'] == 'SG4'
    assert (m.video_mode()['width'], m.video_mode()['height']) == (64, 32)
    m.out_port(0x80, 0x60)
    assert m.video_mode()['name'] == 'SG6'
    assert (m.video_mode()['width'], m.video_mode()['height']) == (64, 48)


def test_sound_command_reaches_ay_registers():
    m = new_machine()
    before = m.ay.regs[:]
    command(m, 'TEMPO 100,2,1:SOUND 87,15,1', settle=0.45)
    assert m.ay.regs != before
