from abc import ABC,abstractmethod
from z80_python._alu import ALUMixin
from z80_python._blocks import BlockMixin
from z80_python._control import ControlMixin
from z80_python._core import CoreMixin
from z80_python._dispatch import DispatchMixin
from z80_python._flags import FLAG_C,FLAG_H,FLAG_N,FLAG_PV,FLAG_S,FLAG_X,FLAG_Y,FLAG_Z,Flags
from z80_python._index import IndexMixin
from z80_python._index_dispatch import IndexDispatchMixin
from z80_python._io import IOMixin
from z80_python._loads import LoadMixin
from z80_python._rotate import RotateBitMixin
from z80_python.state import CPUState
class Z80CPU(DispatchMixin,IndexDispatchMixin,IndexMixin,LoadMixin,ALUMixin,RotateBitMixin,BlockMixin,IOMixin,ControlMixin,CoreMixin,ABC):
    def step(self):
        if self._reset_pending:return self._accept_reset()
        if self._non_maskable_interrupt_pending:return self._accept_non_maskable_interrupt()
        if self._can_accept_maskable_interrupt():return self._accept_maskable_interrupt()
        delay=self._ei_delay>0
        if self.halted:self._inc_r();self._update_q(False);t=4
        else:t=self.decode_and_execute()
        if delay:self._ei_delay-=1
        return t
    @property
    def reset_pending(self):return self._reset_pending
    def request_reset(self):self._reset_pending=True
    def clear_reset(self):self._reset_pending=False
    @property
    def maskable_interrupt_pending(self):return self._pending_maskable_interrupt is not None
    def request_maskable_interrupt(self,vector_byte=0xff):
        if not isinstance(vector_byte,int) or not 0<=vector_byte<=255:raise ValueError
        self._pending_maskable_interrupt=vector_byte
    def clear_maskable_interrupt(self):self._pending_maskable_interrupt=None
    @property
    def non_maskable_interrupt_pending(self):return self._non_maskable_interrupt_pending
    def request_non_maskable_interrupt(self):self._non_maskable_interrupt_pending=True
    def clear_non_maskable_interrupt(self):self._non_maskable_interrupt_pending=False
    @abstractmethod
    def read_byte(self,addr):...
    @abstractmethod
    def write_byte(self,addr,value):...
    @abstractmethod
    def read_port(self,addr):...
    @abstractmethod
    def write_port(self,addr,value):...
