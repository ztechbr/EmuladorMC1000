from dataclasses import dataclass
@dataclass(frozen=True,slots=True)
class CPUState:
    a:int=0; f:int=0; b:int=0; c:int=0; d:int=0; e:int=0; h:int=0; l:int=0; ix:int=0; iy:int=0; sp:int=0; pc:int=0; wz:int=0; i:int=0; r:int=0; iff1:bool=False; iff2:bool=False; im:int=0; af_alt:int=0; bc_alt:int=0; de_alt:int=0; hl_alt:int=0; q:int=0; halted:bool=False; ei_delay:int=0; reset_pending:bool=False; maskable_interrupt_vector:int|None=None; non_maskable_interrupt_pending:bool=False
