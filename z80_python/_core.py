"""CPU state, fetch, stack, and register-selection helpers."""
from z80_python._flags import Flags
class CoreMixin:
    def __init__(self):
        self.a=0; self.f=Flags(); self.b=self.c=self.d=self.e=self.h=self.l=0
        self.ix=self.iy=self.sp=self.pc=self.wz=self.i=self.r=0
        self.iff1=self.iff2=False; self.im=0
        self.af_=self.bc_=self.de_=self.hl_=0; self.q=0; self._io_data=0; self.halted=False
        self._ei_delay=0; self._reset_pending=False; self._pending_maskable_interrupt=None; self._non_maskable_interrupt_pending=False
    def _inc_r(self): self.r=(self.r&0x80)|((self.r+1)&0x7f)
    def _update_q(self,flags_modified): self.q=self.f.byte if flags_modified else 0
    def _fetch_byte(self):
        value=self.read_byte(self.pc); self.pc=(self.pc+1)&0xffff; self._inc_r(); return value
    def _read_operand_byte(self):
        value=self.read_byte(self.pc); self.pc=(self.pc+1)&0xffff; return value
    def _read_operand_word(self):
        low=self._read_operand_byte(); high=self._read_operand_byte(); return (high<<8)|low
    def _push_word(self,value):
        self.sp=(self.sp-1)&0xffff; self.write_byte(self.sp,(value>>8)&255); self.sp=(self.sp-1)&0xffff; self.write_byte(self.sp,value&255)
    def _pop_word(self):
        low=self.read_byte(self.sp); self.sp=(self.sp+1)&0xffff; high=self.read_byte(self.sp); self.sp=(self.sp+1)&0xffff; return (high<<8)|low
    def _can_accept_maskable_interrupt(self): return self.iff1 and self._ei_delay==0 and self._pending_maskable_interrupt is not None
    def _accept_reset(self):
        if not self._reset_pending: raise RuntimeError('RESET is not asserted')
        self.pc=0; self.im=0; self.iff1=self.iff2=False; self.halted=False; self._ei_delay=0; self._update_q(False); return 3
    def _accept_non_maskable_interrupt(self):
        if not self._non_maskable_interrupt_pending: raise RuntimeError('no non-maskable interrupt is pending')
        self._non_maskable_interrupt_pending=False; self.halted=False; self.iff2=self.iff1; self.iff1=False; self._inc_r(); self._push_word(self.pc); self.wz=0x66; self.pc=self.wz; self._update_q(False); return 11
    def _accept_maskable_interrupt(self):
        vector_byte=self._pending_maskable_interrupt
        if vector_byte is None: raise RuntimeError('no maskable interrupt is pending')
        if not self.iff1 or self._ei_delay: raise RuntimeError('maskable interrupts cannot currently be accepted')
        if self.im==0 and (vector_byte&0xc7)!=0xc7: raise NotImplementedError('IM 0 currently supports only device-supplied RST opcodes')
        self._pending_maskable_interrupt=None; self.halted=False; self.iff1=self.iff2=False; self._inc_r(); self._push_word(self.pc)
        if self.im==0: self.wz=vector_byte&0x38; self.pc=self.wz; t=13
        elif self.im==1: self.wz=0x38; self.pc=self.wz; t=13
        else:
            va=((self.i&255)<<8)|vector_byte; low=self.read_byte(va); high=self.read_byte((va+1)&0xffff); self.wz=(high<<8)|low; self.pc=self.wz; t=19
        self._update_q(False); return t
    def _hl(self): return (self.h<<8)|self.l
    def _bc(self): return (self.b<<8)|self.c
    def _de(self): return (self.d<<8)|self.e
    def _read_pair(self,index): return (self._bc(),self._de(),self._hl(),self.sp)[index]
    def _write_pair(self,index,value):
        value&=0xffff
        if index==0:self.b=(value>>8)&255;self.c=value&255
        elif index==1:self.d=(value>>8)&255;self.e=value&255
        elif index==2:self.h=(value>>8)&255;self.l=value&255
        else:self.sp=value
    def _read_reg(self,index):
        if index==0:return self.b
        if index==1:return self.c
        if index==2:return self.d
        if index==3:return self.e
        if index==4:return self.h
        if index==5:return self.l
        if index==7:return self.a
        raise ValueError('register index 6 ((HL)) has no direct register backing')
    def _write_reg(self,index,value):
        value&=255
        if index==0:self.b=value
        elif index==1:self.c=value
        elif index==2:self.d=value
        elif index==3:self.e=value
        elif index==4:self.h=value
        elif index==5:self.l=value
        elif index==7:self.a=value
        else: raise ValueError('register index 6 ((HL)) has no direct register backing')
