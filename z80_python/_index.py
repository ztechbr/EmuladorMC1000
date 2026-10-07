"""DD/FD index-register instruction handlers."""
class IndexMixin:
    def _get_index(self,prefix):return self.ix if prefix==0xdd else self.iy
    def _set_index(self,prefix,value):
        value&=0xffff
        if prefix==0xdd:self.ix=value
        else:self.iy=value
    def _index_high_byte(self,prefix):return (self._get_index(prefix)>>8)&255
    def _index_low_byte(self,prefix):return self._get_index(prefix)&255
    def _set_index_high_byte(self,prefix,value):self._set_index(prefix,((value&255)<<8)|self._index_low_byte(prefix))
    def _set_index_low_byte(self,prefix,value):self._set_index(prefix,(self._index_high_byte(prefix)<<8)|(value&255))
    def _op_add_index_rr(self,prefix,sub_opcode):
        pair_index=(sub_opcode>>4)&3; index=self._get_index(prefix); value=index if pair_index==2 else self._read_pair(pair_index); self.wz=(index+1)&0xffff; result=index+value; self.f.c=1 if result>0xffff else 0; result&=0xffff; self.f.n=0; self.f.h=((index^value^result)&0x1000)>>12; self.f.set_xy((result>>8)&255); self._set_index(prefix,result); self._update_q(True); return 15
    def _op_ld_index_nn(self,prefix):self._set_index(prefix,self._read_operand_word());self._update_q(False);return 14
    def _op_ld_hl_nn(self):
        v=self._read_operand_word();self.h=(v>>8)&255;self.l=v&255;self._update_q(False);return 10
    def _op_ld_nn_hl(self):
        a=self._read_operand_word();self.write_byte(a,self.l);self.wz=(a+1)&0xffff;self.write_byte(self.wz,self.h);self._update_q(False);return 16
    def _op_ld_hl_nn_from_mem(self):
        a=self._read_operand_word();self.l=self.read_byte(a);self.wz=(a+1)&0xffff;self.h=self.read_byte(self.wz);self._update_q(False);return 16
    def _op_ld_nn_rr(self,pair_index):
        a=self._read_operand_word();v=self._read_pair(pair_index);self.write_byte(a,v&255);self.wz=(a+1)&0xffff;self.write_byte(self.wz,v>>8);self._update_q(False);return 20
    def _op_ld_rr_nn_from_mem(self,pair_index):
        a=self._read_operand_word();lo=self.read_byte(a);self.wz=(a+1)&0xffff;self._write_pair(pair_index,lo|(self.read_byte(self.wz)<<8));self._update_q(False);return 20
    def _op_im(self,mode):self.im=mode;self._update_q(False);return 8
    def _op_ed_nop(self):self._update_q(False);return 8
    def _op_prefix_ignored_basic(self,op):
        if op==0:return self._qret(False,4)
        if op==8:
            af=(self.a<<8)|self.f.byte;self.a=(self.af_>>8)&255;self.f.byte=self.af_&255;self.af_=af;self._update_q(False);return 4
        if op in (1,0x11,0x31):self._write_pair((op>>4)&3,self._read_operand_word());self._update_q(False);return 10
        if op==0x10:
            d=self._read_operand_byte();d-=256 if d>=128 else 0;self.b=(self.b-1)&255
            if self.b:self.wz=(self.pc+d)&0xffff;self.pc=self.wz;self._update_q(False);return 13
            self._update_q(False);return 8
        raise ValueError
    def _qret(self,m,t):self._update_q(m);return t
    def _op_ld_nn_index(self,prefix):
        a=self._read_operand_word();i=self._get_index(prefix);self.write_byte(a,i&255);self.wz=(a+1)&0xffff;self.write_byte(self.wz,i>>8);self._update_q(False);return 20
    def _op_ld_index_nn_from_mem(self,prefix):
        a=self._read_operand_word();lo=self.read_byte(a);self.wz=(a+1)&0xffff;self._set_index(prefix,lo|(self.read_byte(self.wz)<<8));self._update_q(False);return 20
    def _op_ld_a_index_h(self,prefix):self.a=self._index_high_byte(prefix);self._update_q(False);return 4
    def _op_ld_a_index_l(self,prefix):self.a=self._index_low_byte(prefix);self._update_q(False);return 4
    def _op_ld_r_index_byte(self,prefix,op):
        v=self._index_high_byte(prefix) if (op&7)==4 else self._index_low_byte(prefix);self._write_reg((op>>3)&7,v);self._update_q(False);return 4
    def _op_ld_index_byte_index_byte(self,prefix,op):
        v=self._index_high_byte(prefix) if (op&7)==4 else self._index_low_byte(prefix)
        if ((op>>3)&7)==4:self._set_index_high_byte(prefix,v)
        else:self._set_index_low_byte(prefix,v)
        self._update_q(False);return 4
    def _op_ld_index_byte_r(self,prefix,op):
        v=self._read_reg(op&7)
        if ((op>>3)&7)==4:self._set_index_high_byte(prefix,v)
        else:self._set_index_low_byte(prefix,v)
        self._update_q(False);return 4
    def _op_ld_index_byte_n(self,prefix,op):
        v=self._read_operand_byte()
        if ((op>>3)&7)==4:self._set_index_high_byte(prefix,v)
        else:self._set_index_low_byte(prefix,v)
        self._update_q(False);return 7
    def _op_inc_dec_index_byte(self,prefix,op):
        hi=((op>>3)&7)==4;v=self._index_high_byte(prefix) if hi else self._index_low_byte(prefix);r=self._inc(v) if (op&7)==4 else self._dec(v)
        if hi:self._set_index_high_byte(prefix,r)
        else:self._set_index_low_byte(prefix,r)
        self._update_q(True);return 4
    def _index_alu_reg(self,prefix,group,high):self._alu_a(group,self._index_high_byte(prefix) if high else self._index_low_byte(prefix));self._update_q(True);return 4
    def _op_add_a_index_h(self,p):return self._index_alu_reg(p,0,True)
    def _op_add_a_index_l(self,p):return self._index_alu_reg(p,0,False)
    def _op_adc_a_index_h(self,p):return self._index_alu_reg(p,1,True)
    def _op_adc_a_index_l(self,p):return self._index_alu_reg(p,1,False)
    def _op_sub_a_index_h(self,p):return self._index_alu_reg(p,2,True)
    def _op_sub_a_index_l(self,p):return self._index_alu_reg(p,2,False)
    def _op_sbc_a_index_h(self,p):return self._index_alu_reg(p,3,True)
    def _op_sbc_a_index_l(self,p):return self._index_alu_reg(p,3,False)
    def _op_and_a_index_h(self,p):return self._index_alu_reg(p,4,True)
    def _op_and_a_index_l(self,p):return self._index_alu_reg(p,4,False)
    def _op_xor_a_index_h(self,p):return self._index_alu_reg(p,5,True)
    def _op_xor_a_index_l(self,p):return self._index_alu_reg(p,5,False)
    def _op_or_a_index_h(self,p):return self._index_alu_reg(p,6,True)
    def _op_or_a_index_l(self,p):return self._index_alu_reg(p,6,False)
    def _op_cp_a_index_h(self,p):return self._index_alu_reg(p,7,True)
    def _op_cp_a_index_l(self,p):return self._index_alu_reg(p,7,False)
    def _op_inc_index(self,p):self._set_index(p,self._get_index(p)+1);self._update_q(False);return 10
    def _op_dec_index(self,p):self._set_index(p,self._get_index(p)-1);self._update_q(False);return 10
    def _op_pop_index(self,p):self._set_index(p,self._pop_word());self._update_q(False);return 14
    def _op_push_index(self,p):self._push_word(self._get_index(p));self._update_q(False);return 15
    def _op_ex_sp_index(self,p):
        v=self.read_byte(self.sp)|(self.read_byte((self.sp+1)&0xffff)<<8);i=self._get_index(p);self.write_byte(self.sp,i&255);self.write_byte((self.sp+1)&0xffff,i>>8);self._set_index(p,v);self.wz=v;self._update_q(False);return 23
    def _op_jp_index(self,p):self.pc=self._get_index(p);self._update_q(False);return 8
    def _op_ld_sp_index(self,p):self.sp=self._get_index(p);self._update_q(False);return 10
    def _op_ld_sp_hl(self):self.sp=self._hl();self._update_q(False);return 6
    def _op_pop_de(self):
        v=self._pop_word();self.d=(v>>8)&255;self.e=v&255;self._update_q(False);return 10
    def _op_pop_rr(self,op):self._write_pair((op>>4)&3,self._pop_word());self._update_q(False);return 10
    def _op_push_de(self):self._push_word(self._de());self._update_q(False);return 11
    def _op_push_rr(self,op):self._push_word(self._read_pair((op>>4)&3));self._update_q(False);return 11
    def _op_pop_af(self):
        v=self._pop_word();self.a=(v>>8)&255;self.f.byte=v&255;self._update_q(False);return 10
    def _op_push_af(self):self._push_word((self.a<<8)|self.f.byte);self._update_q(False);return 11
    def _op_exx(self):
        bc,de,hl=self._bc(),self._de(),self._hl();self._write_pair(0,self.bc_);self._write_pair(1,self.de_);self._write_pair(2,self.hl_);self.bc_,self.de_,self.hl_=bc,de,hl;self._update_q(False);return 4
    def _op_ex_sp_hl(self):
        v=self.read_byte(self.sp)|(self.read_byte((self.sp+1)&0xffff)<<8);hl=self._hl();self.write_byte(self.sp,hl&255);self.write_byte((self.sp+1)&0xffff,hl>>8);self.h=(v>>8)&255;self.l=v&255;self.wz=v;self._update_q(False);return 19
    def _index_displacement_addr(self,p):
        d=self._read_operand_byte();d-=256 if d>=128 else 0;a=(self._get_index(p)+d)&0xffff;self.wz=a;return a
    def _op_index_bit(self,p,d,op):
        d-=256 if d>=128 else 0;self.wz=(self._get_index(p)+d)&0xffff;v=self.read_byte(self.wz);bi=(op>>3)&7;bs=(v>>bi)&1;self.f.n=0;self.f.h=1;self.f.z=0 if bs else 1;self.f.pv=self.f.z;self.f.s=1 if bi==7 and bs else 0;self.f.set_xy(self.wz>>8);self._update_q(True);return 20
    def _op_index_rot(self,p,d,op):
        d-=256 if d>=128 else 0;self.wz=(self._get_index(p)+d)&0xffff;v=self._rot_apply((op>>3)&7,self.read_byte(self.wz));self.write_byte(self.wz,v);dest=op&7
        if dest!=6:self._write_reg(dest,v)
        self._update_q(True);return 23
    def _op_index_res_set(self,p,d,op,set_bit):
        d-=256 if d>=128 else 0;self.wz=(self._get_index(p)+d)&0xffff;mask=1<<((op>>3)&7);v=self.read_byte(self.wz);v=v|mask if set_bit else v&~mask;self.write_byte(self.wz,v);dest=op&7
        if dest!=6:self._write_reg(dest,v)
        self._update_q(False);return 23
    def _op_inc_index_mem(self,p):
        a=self._index_displacement_addr(p);self.write_byte(a,self._inc(self.read_byte(a)));self._update_q(True);return 23
    def _op_dec_index_mem(self,p):
        a=self._index_displacement_addr(p);self.write_byte(a,self._dec(self.read_byte(a)));self._update_q(True);return 23
    def _op_ld_r_index_mem(self,p,op):
        dest=(op>>3)&7;a=self._index_displacement_addr(p);self._write_reg(dest,self.read_byte(a));self._update_q(False);return 19
    def _op_ld_index_mem_r(self,p,op):
        src=op&7;a=self._index_displacement_addr(p);self.write_byte(a,self._read_reg(src));self._update_q(False);return 19
    def _op_ld_index_mem_n(self,p):
        a=self._index_displacement_addr(p);self.write_byte(a,self._read_operand_byte());self._update_q(False);return 19
    def _indexed_alu(self,p,g):
        a=self._index_displacement_addr(p);self._alu_a(g,self.read_byte(a));self._update_q(True);return 19
    def _op_add_a_index_mem(self,p):return self._indexed_alu(p,0)
    def _op_adc_a_index_mem(self,p):return self._indexed_alu(p,1)
    def _op_sub_a_index_mem(self,p):return self._indexed_alu(p,2)
    def _op_sbc_a_index_mem(self,p):return self._indexed_alu(p,3)
    def _op_and_a_index_mem(self,p):return self._indexed_alu(p,4)
    def _op_xor_a_index_mem(self,p):return self._indexed_alu(p,5)
    def _op_or_a_index_mem(self,p):return self._indexed_alu(p,6)
    def _op_cp_a_index_mem(self,p):return self._indexed_alu(p,7)
