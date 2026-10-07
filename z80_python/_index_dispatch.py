"""DD/FD index-prefix dispatcher, vendored from z80-python 0.3.0."""
class IndexDispatchMixin:
    def _execute_index(self,prefix,op):
        if op==0xcb:
            d=self._read_operand_byte();cb=self._read_operand_byte()
            if cb<=0x3f:return self._op_index_rot(prefix,d,cb)
            if cb<=0x7f:return self._op_index_bit(prefix,d,cb)
            if cb<=0xbf:return self._op_index_res_set(prefix,d,cb,set_bit=False)
            return self._op_index_res_set(prefix,d,cb,set_bit=True)
        if op==0x76:return self._op_halt()+4
        if op in (0x00,0x01,0x08,0x10,0x11,0x31):return self._op_prefix_ignored_basic(op)+4
        if op in (0x40,0x41,0x42,0x43,0x47,0x48,0x49,0x4a,0x4b,0x4f,0x50,0x51,0x52,0x53,0x57,0x58,0x59,0x5a,0x5b,0x5f,0x78,0x79,0x7a,0x7b,0x7f):return self._op_ld_r_r(op)+4
        if op==0x7c:return self._op_ld_a_index_h(prefix)+4
        if op==0x7d:return self._op_ld_a_index_l(prefix)+4
        if op in (0x44,0x45,0x4c,0x4d,0x54,0x55,0x5c,0x5d):return self._op_ld_r_index_byte(prefix,op)+4
        if op in (0x64,0x65,0x6c,0x6d):return self._op_ld_index_byte_index_byte(prefix,op)+4
        if op in (0x60,0x61,0x62,0x63,0x67,0x68,0x69,0x6a,0x6b,0x6f):return self._op_ld_index_byte_r(prefix,op)+4
        if op in (0x26,0x2e):return self._op_ld_index_byte_n(prefix,op)+4
        if op in (0x24,0x25,0x2c,0x2d):return self._op_inc_dec_index_byte(prefix,op)+4
        if op in (0x04,0x0c,0x14,0x1c,0x3c):return self._op_inc_r(op)+4
        if op in (0x05,0x0d,0x15,0x1d,0x3d):return self._op_dec_r(op)+4
        if op in (0x03,0x13,0x33):return self._op_inc_rr(op)+4
        if op in (0x0b,0x1b,0x3b):return self._op_dec_rr(op)+4
        if op in (0x06,0x0e,0x16,0x1e,0x3e):return self._op_ld_r_n(op)+4
        if op in (0x0a,0x1a):return self._op_ld_a_irr(self._bc() if op==0x0a else self._de())+4
        if op in (0x02,0x12):return self._op_ld_irr_a(self._bc() if op==0x02 else self._de())+4
        if op==0x3a:return self._op_ld_a_inn()+4
        if op==0x32:return self._op_ld_inn_a()+4
        if op==0xdb:return self._op_in_a_n()+4
        if op==0xd3:return self._op_out_n_a()+4
        if op in (0x18,0x20,0x28,0x30,0x38):return self._op_jr(op)+4
        if op==0x27:return self._op_daa()+4
        if op==0x2f:return self._op_cpl()+4
        if op in (0x37,0x3f):return self._op_scf_ccf(op,prefixed=True)+4
        if op==0x07:return self._op_rlca()+4
        if op==0x0f:return self._op_rrca()+4
        if op==0x17:return self._op_rla()+4
        if op==0x1f:return self._op_rra()+4
        plain={0x80,0x81,0x82,0x83,0x87,0x88,0x89,0x8a,0x8b,0x8f,0x90,0x91,0x92,0x93,0x97,0x98,0x99,0x9a,0x9b,0x9f,0xa0,0xa1,0xa2,0xa3,0xa7,0xa8,0xa9,0xaa,0xab,0xaf,0xb0,0xb1,0xb2,0xb3,0xb7,0xb8,0xb9,0xba,0xbb,0xbf}
        if op in plain:return self._op_alu_r(op)+4
        indexed={0x84:self._op_add_a_index_h,0x85:self._op_add_a_index_l,0x8c:self._op_adc_a_index_h,0x8d:self._op_adc_a_index_l,0x94:self._op_sub_a_index_h,0x95:self._op_sub_a_index_l,0x9c:self._op_sbc_a_index_h,0x9d:self._op_sbc_a_index_l,0xa4:self._op_and_a_index_h,0xa5:self._op_and_a_index_l,0xac:self._op_xor_a_index_h,0xad:self._op_xor_a_index_l,0xb4:self._op_or_a_index_h,0xb5:self._op_or_a_index_l,0xbc:self._op_cp_a_index_h,0xbd:self._op_cp_a_index_l}
        if op in indexed:return indexed[op](prefix)+4
        if op in (0x09,0x19,0x29,0x39):return self._op_add_index_rr(prefix,op)
        if op==0x21:return self._op_ld_index_nn(prefix)
        if op==0x22:return self._op_ld_nn_index(prefix)
        if op==0x23:return self._op_inc_index(prefix)
        if op==0x2a:return self._op_ld_index_nn_from_mem(prefix)
        if op==0x2b:return self._op_dec_index(prefix)
        if op==0x34:return self._op_inc_index_mem(prefix)
        if op==0x35:return self._op_dec_index_mem(prefix)
        if op==0x36:return self._op_ld_index_mem_n(prefix)
        if op in (0x46,0x4e,0x56,0x5e,0x66,0x6e,0x7e):return self._op_ld_r_index_mem(prefix,op)
        if op in (0x70,0x71,0x72,0x73,0x74,0x75,0x77):return self._op_ld_index_mem_r(prefix,op)
        memalu={0x86:self._op_add_a_index_mem,0x8e:self._op_adc_a_index_mem,0x96:self._op_sub_a_index_mem,0x9e:self._op_sbc_a_index_mem,0xa6:self._op_and_a_index_mem,0xae:self._op_xor_a_index_mem,0xb6:self._op_or_a_index_mem,0xbe:self._op_cp_a_index_mem}
        if op in memalu:return memalu[op](prefix)
        if op in (0xc0,0xc8,0xd0,0xd8,0xe0,0xe8,0xf0,0xf8):return self._op_ret_cc(op)+4
        if op in (0xc2,0xca,0xd2,0xda,0xe2,0xea,0xf2,0xfa,0xc3):return self._op_jp(op)+4
        if op in (0xc4,0xcc,0xd4,0xdc,0xe4,0xec,0xf4,0xfc,0xcd):return self._op_call(op)+4
        if op==0xc9:return self._op_ret()+4
        if op in (0xc7,0xcf,0xd7,0xdf,0xe7,0xef,0xf7,0xff):return self._op_rst(op)+4
        if op in (0xc6,0xce,0xd6,0xde,0xe6,0xee,0xf6,0xfe):return self._op_alu_n(op)+4
        if op==0xeb:return self._op_ex_de_hl()+4
        if op==0xd1:return self._op_pop_rr(op)+4
        if op==0xd5:return self._op_push_rr(op)+4
        if op==0xd9:return self._op_exx()+4
        if op==0xe1:return self._op_pop_index(prefix)
        if op==0xe3:return self._op_ex_sp_index(prefix)
        if op==0xe5:return self._op_push_index(prefix)
        if op==0xe9:return self._op_jp_index(prefix)
        if op==0xf1:return self._op_pop_af()+4
        if op==0xf5:return self._op_push_af()+4
        if op==0xf9:return self._op_ld_sp_index(prefix)
        if op==0xf3:return self._op_interrupt_enable(False)+4
        if op==0xfb:return self._op_interrupt_enable(True)+4
        if op==0xc1:return self._op_pop_rr(op)+4
        if op==0xc5:return self._op_push_rr(op)+4
        prefix_addr=(self.pc-2)&0xffff;self.pc=(prefix_addr+1)&0xffff;raise NotImplementedError(f'unhandled DD/FD opcode 0x{op:02X} at PC 0x{prefix_addr:04X}')
