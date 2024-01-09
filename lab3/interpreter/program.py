from __future__ import annotations

from lab3.interpreter.parser import AstType
from lab3.machine.isa import SP, MachineWord, Opcode, Register, StaticMemoryAddressStub

ast_type2opcode = {
    AstType.EQ: Opcode.JE,
    AstType.GE: Opcode.JGE,
    AstType.GT: Opcode.JG,
    AstType.LT: Opcode.JL,
    AstType.LE: Opcode.JLE,
    AstType.NEQ: Opcode.JNE,
    AstType.PLUS: Opcode.ADD,
    AstType.MINUS: Opcode.SUB,
    AstType.XOR: Opcode.XOR,
    AstType.OR: Opcode.OR,
    AstType.AND: Opcode.AND,
    AstType.SHL: Opcode.SHL,
    AstType.SHR: Opcode.SHR,
}

inverted_conditions = {
    Opcode.JE: Opcode.JNE,
    Opcode.JGE: Opcode.JL,
    Opcode.JG: Opcode.JLE,
    Opcode.JL: Opcode.JGE,
    Opcode.JLE: Opcode.JG,
    Opcode.JNE: Opcode.JE,
}


class Program:
    def __init__(self):
        self.machine_code: list[MachineWord] = []
        self.static_memory: list[int] = []
        self.input_buffer_size = 32
        self.current_command_address: int = 0
        self.current_static_offset = 0
        self.variables: dict[str, int] = {}
        self.register_to_variable: dict[Register, str] = {}
        self.variable_to_register: dict[str, Register] = {}
        self.register_counter = 3
        self.program_size = 2048

    def add_instruction(
            self,
            opcode: Opcode,
            arg1: int | Register | StaticMemoryAddressStub = 0,
            arg2: int | Register | StaticMemoryAddressStub = 0,
    ) -> int:
        self.machine_code.append(MachineWord(self.current_command_address, opcode, arg1, arg2))
        self.current_command_address += 1
        return self.current_command_address - 1

    def change_register(self) -> Register:
        self.register_counter += 1
        if self.register_counter >= 9:
            self.register_counter = 3
        return Register(self.register_counter)

    def clear_register_for_variable(self) -> Register:
        register = self.change_register()
        variable: str | None = self.register_to_variable.get(register)
        self.register_to_variable.pop(register, None)
        self.variable_to_register.pop(variable, None)
        return register

    def add_data_to_static_memory(self, value: int) -> None:
        self.static_memory.append(value)
        self.current_static_offset += 1

    def push_variable_to_stack(self, name: str, value: int) -> int:
        var_addr = len(self.variables)
        register = self.clear_register_for_variable()
        self.add_instruction(Opcode.LD_LITERAL, register, value)
        self.add_instruction(Opcode.PUSH, register)
        self.variables[name] = var_addr
        return var_addr

    def get_variable_offset(self, name: str) -> int | None:
        return self.variables.get(name)

    def clear_variable_in_registers(self, name: str) -> None:
        register: Register | None = self.variable_to_register.get(name)
        if register is not None:
            self.register_to_variable.pop(register)
            self.variable_to_register.pop(name)

    def return_from_code_block(self, stack_offset_before_block: int) -> None:
        variables_to_delete = []
        for name in self.variables:
            if self.get_variable_offset(name) >= stack_offset_before_block:
                self.clear_variable_in_registers(name)
                variables_to_delete.append(name)
        for name in variables_to_delete:
            self.variables.pop(name)
        self.add_instruction(Opcode.LD_LITERAL, SP, self.program_size - 1 - stack_offset_before_block)

    def add_variable_to_static_memory(self, value: str) -> int:
        size: int = len(value)
        for char in value:
            self.add_data_to_static_memory(ord(char))
        self.add_data_to_static_memory(ord("\0"))
        size += 1
        return self.current_static_offset - size

    def add_strings_to_static_memory(self) -> None:
        static_memory_start_addr: int = 0
        for instruction in self.machine_code:
            if isinstance(instruction.arg1, StaticMemoryAddressStub) and instruction.arg1.offset >= 0:
                instruction.arg1 = instruction.arg1.offset + static_memory_start_addr
            if isinstance(instruction.arg2, StaticMemoryAddressStub) and instruction.arg2.offset >= 0:
                instruction.arg2 = instruction.arg2.offset + static_memory_start_addr

    def resolve_static_mem(self) -> list[int] | None:
        self.add_strings_to_static_memory()
        static_mem_end = self.current_command_address - 1
        for instruction in self.machine_code:
            if isinstance(instruction.arg1, StaticMemoryAddressStub) and instruction.arg1.offset < 0:
                instruction.arg1 = -instruction.arg1.offset + static_mem_end
            if isinstance(instruction.arg2, StaticMemoryAddressStub) and instruction.arg2.offset < 0:
                instruction.arg2 = -instruction.arg2.offset + static_mem_end
        return self.static_memory

    def load_variable(self, var_name: str) -> Register:
        register: Register = self.variable_to_register.get(var_name)
        if register is not None:
            return register
        register: Register = self.clear_register_for_variable()
        variable_offset: int = self.get_variable_offset(var_name)
        self.add_instruction(Opcode.LD_STACK, register, variable_offset)
        self.variable_to_register[var_name] = register
        self.register_to_variable[register] = var_name
        return register

    def reset_registers(self):
        self.register_to_variable.clear()
        self.variable_to_register.clear()
