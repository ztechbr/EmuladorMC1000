from pathlib import Path
from app.services.machine import MC1000

class EmulatorModel:
    def __init__(self):
        root=Path(__file__).resolve().parents[2]
        self.machine=MC1000(root/'roms'/'mc1000.rom')
        self.machine.reset()
        self.machine.run_for(0.8)
        self.machine.start()

emulator=EmulatorModel()
