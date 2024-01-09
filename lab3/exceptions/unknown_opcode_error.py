class UnknownOpcodeError(Exception):
    def __init__(self, opcode):
        self.message = opcode
        super().__init__(f"Unknown opcode {opcode}")
