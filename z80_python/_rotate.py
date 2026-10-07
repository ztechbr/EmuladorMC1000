"""Rotate, shift, and bit-operation implementation."""


class RotateBitMixin:
    """Private rotate, shift, and bit implementation."""
    def _rlc(self,x):
        x=((x<<1)|(x>>7))&255; self.f.c=x&1; self.f.n=self.f.h=0; self._set_parity(x); self._set_xysz(x); return x
    def _rrc(self,x):
        x=((x>>1)|(x<<7))&255; self.f.c=(x>>7)&1; self.f.n=self.f.h=0; self._set_parity(x); self._set_xysz(x); return x
    def _rl(self,x):
        carry=(x>>7)&1; x=((x<<1)|self.f.c)&255; self.f.c=carry; self.f.n=self.f.h=0; self._set_parity(x); self._set_xysz(x); return x
    def _rr(self,x):
        carry=x&1; x=((x>>1)|(self.f.c<<7))&255; self.f.c=carry; self.f.n=self.f.h=0; self._set_parity(x); self._set_xysz(x); return x
    def _sla(self,x):
        carry=(x>>7)&1; x=(x<<1)&255; self.f.c=carry; self.f.n=self.f.h=0; self._set_parity(x); self._set_xysz(x); return x
    def _sra(self,x):
        carry=x&1; x=(x&0x80)|(x>>1); self.f.c=carry; self.f.n=self.f.h=0; self._set_parity(x); self._set_xysz(x); return x
    def _sll(self,x):
        carry=(x>>7)&1; x=((x<<1)|1)&255; self.f.c=carry; self.f.n=self.f.h=0; self._set_parity(x); self._set_xysz(x); return x
    def _srl(self,x):
        carry=x&1; x>>=1; self.f.c=carry; self.f.n=self.f.h=0; self._set_parity(x); self._set_xysz(x); return x
    def _rot_apply(self,group,value): return (self._rlc,self._rrc,self._rl,self._rr,self._sla,self._sra,self._sll,self._srl)[group](value)
    def _op_rot(self,sub_opcode):
        group=(sub_opcode>>3)&7; dest=sub_opcode&7
        if dest==6:
            addr=self._hl(); self.write_byte(addr,self._rot_apply(group,self.read_byte(addr))); self._update_q(True); return 15
        self._write_reg(dest,self._rot_apply(group,self._read_reg(dest))); self._update_q(True); return 8
    def _op_rlca(self):
        self.a=((self.a<<1)|(self.a>>7))&255; self.f.c=self.a&1; self.f.n=self.f.h=0; self.f.set_xy(self.a); self._update_q(True); return 4
    def _op_rrca(self):
        self.f.c=self.a&1; self.a=((self.a>>1)|(self.a<<7))&255; self.f.n=self.f.h=0; self.f.set_xy(self.a); self._update_q(True); return 4
    def _op_rla(self):
        carry_in=self.f.c; self.f.c=(self.a>>7)&1; self.a=((self.a<<1)|carry_in)&255; self.f.n=self.f.h=0; self.f.set_xy(self.a); self._update_q(True); return 4
    def _op_rra(self):
        carry_in=self.f.c; self.f.c=self.a&1; self.a=((self.a>>1)|(carry_in<<7))&255; self.f.n=self.f.h=0; self.f.set_xy(self.a); self._update_q(True); return 4
    def _op_bit(self,sub_opcode):
        bit_index=(sub_opcode>>3)&7; src=sub_opcode&7
        if src==6: value=self.read_byte(self._hl()); xy_source=(self.wz>>8)&255; t_states=12
        else: value=self._read_reg(src); xy_source=value; t_states=8
        bit_set=(value>>bit_index)&1; self.f.n=0; self.f.h=1; self.f.z=0 if bit_set else 1; self.f.pv=self.f.z; self.f.s=1 if (bit_index==7 and bit_set) else 0; self.f.set_xy(xy_source); self._update_q(True); return t_states
    def _op_res(self,sub_opcode):
        bit_index=(sub_opcode>>3)&7; dest=sub_opcode&7; mask=~(1<<bit_index)&255
        if dest==6: addr=self._hl(); self.write_byte(addr,self.read_byte(addr)&mask); t_states=15
        else: self._write_reg(dest,self._read_reg(dest)&mask); t_states=8
        self._update_q(False); return t_states
    def _op_set(self,sub_opcode):
        bit_index=(sub_opcode>>3)&7; dest=sub_opcode&7; mask=1<<bit_index
        if dest==6: addr=self._hl(); self.write_byte(addr,self.read_byte(addr)|mask); t_states=15
        else: self._write_reg(dest,self._read_reg(dest)|mask); t_states=8
        self._update_q(False); return t_states
    def _op_rrd(self):
        addr=self._hl(); self.wz=(addr+1)&65535; data=self.read_byte(addr); self.write_byte(addr,((data>>4)|(self.a<<4))&255); self.a=(self.a&240)|(data&15); self.f.n=self.f.h=0; self._set_parity(self.a); self._set_xysz(self.a); self._update_q(True); return 18
    def _op_rld(self):
        addr=self._hl(); self.wz=(addr+1)&65535; data=self.read_byte(addr); self.write_byte(addr,((data<<4)|(self.a&15))&255); self.a=(self.a&240)|(data>>4); self.f.n=self.f.h=0; self._set_parity(self.a); self._set_xysz(self.a); self._update_q(True); return 18
