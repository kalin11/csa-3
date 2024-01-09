from __future__ import annotations

import logging
import sys
from enum import Enum

from lab3.machine.isa import MachineWord, Opcode, Register, SP, PC, DR, read_code_from_file


class Alu:
    is_negative: bool = False
    is_zero: bool = False

    min_value = -(2 ** 32)
    max_value = 2 ** 32 - 1

    def set_flags(self, value: int) -> None:
        if value > self.max_value:
            value = value & self.min_value
        if value < self.min_value:
            value = value & self.min_value
        self.is_negative = value < 0
        self.is_zero = value == 0

    def execute(self, opcode: Opcode, arg1: int, arg2: int) -> int:
        res: int = 0
        operations = {
            Opcode.ADD: lambda a, b: a + b,
            Opcode.ADD_LITERAL: lambda a, b: a + b,
            Opcode.INC: lambda a, b: a + 1,
            Opcode.DEC: lambda a, b: a - 1,
            Opcode.SHR: lambda a, b: a >> b,
            Opcode.SHL: lambda a, b: 0 if a == 0 else a << b,
            Opcode.XOR: lambda a, b: a ^ b,
            Opcode.AND: lambda a, b: a & b,
            Opcode.OR: lambda a, b: a | b,
            Opcode.NEG: lambda a, b: ~a,
            Opcode.MUL: lambda a, b: a * b,
            Opcode.DIV: lambda a, b: a // b,
            Opcode.MOD: lambda a, b: a % b
        }

        operation = operations.get(opcode, None)
        if operation is not None:
            res = operation(arg1, arg2)
        else:
            raise ValueError(f"Unknown opcode {opcode}")
        self.set_flags(res)
        return res


class DataPath:
    instruction_memory: list[MachineWord]

    data_memory: list

    input_ports: dict[int, list[str]]

    output_ports: dict[int, list[str]]

    registers: dict[Register, int]

    memory_size: int

    alu: Alu = None

    def __init__(self, instruction_memory: list[MachineWord], ports: dict[int, list[str]], memory_size: int = 2048):
        self.registers = {}
        self.output_ports = {}
        self.memory_size = memory_size
        self.instruction_memory = instruction_memory
        self.alu = Alu()
        self.data_memory = [None] * memory_size
        self.input_ports = ports
        self.output_ports[0] = []
        for register_number in range(0, 17):
            self.registers[Register(register_number)] = 0
        self.registers[SP] = self.memory_size - 1

    def latch_register(self, register: Register, value: int) -> None:
        self.registers[register] = value

    def load_register(self, register: Register) -> int:
        return self.registers[register]

    def get_instruction(self, address: int) -> MachineWord:
        return self.instruction_memory[address]

    def work_with_memory(self, oe: bool, wr: bool, address: int) -> int | None:
        if oe:
            return self.data_memory[address]
        if wr:
            self.data_memory[address] = self.registers[DR]
        return None

    def read_from_mem(self, address: int) -> int:
        return self.data_memory[address]

    def execute_arithmetic(self, opcode: Opcode, arg1: int, arg2: int = 0) -> int:
        return self.alu.execute(opcode, arg1, arg2)

    def is_zero(self) -> bool:
        return self.alu.is_zero

    def is_negative(self) -> bool:
        return self.alu.is_negative

    def read_char(self, port: int) -> int:
        if len(self.input_ports[port]) == 0:
            return 0
        return ord(self.input_ports[port].pop(0))

    def write_char(self, char: int, port: int) -> None:
        self.output_ports[port].append(chr(char))


class ControlUnit:
    data_path: DataPath = None
    tick_counter: int = 0

    def __init__(self, data_path: DataPath) -> None:
        self.tick_counter = 0
        self.data_path = data_path

    def tick(self) -> None:
        self.tick_counter += 1

    def get_tick(self) -> int:
        return self.tick_counter

    def decode_and_execute_control_flow_instruction(self, instruction: MachineWord, opcode: Opcode) -> bool:
        if opcode is Opcode.HALT:
            raise StopIteration()

        if opcode is Opcode.JMP:
            addr: int = instruction.arg1
            self.data_path.latch_register(PC, addr)
            self.tick()
            return True

        jmp_flag: bool = False

        if (
                opcode is Opcode.JE
                or opcode is Opcode.JNE
                or opcode is Opcode.JL
                or opcode is Opcode.JLE
                or opcode is Opcode.JG
                or opcode is Opcode.JGE
        ):
            match opcode:
                case Opcode.JE:
                    jmp_flag = self.data_path.is_zero() == 1
                case Opcode.JNE:
                    jmp_flag = self.data_path.is_zero() == 0
                case Opcode.JG:
                    jmp_flag = self.data_path.is_negative() == 0
                case Opcode.JGE:
                    jmp_flag = self.data_path.is_negative() == 0 or self.data_path.is_zero() == 1
                case Opcode.JL:
                    jmp_flag = self.data_path.is_negative() == 1
                case Opcode.JLE:
                    jmp_flag = self.data_path.is_negative() == 1 or self.data_path.is_zero() == 1
            if jmp_flag:
                self.data_path.latch_register(PC, instruction.arg1)
            else:
                self.data_path.latch_register(PC, self.data_path.registers[PC] + 1)

            self.tick()
            return True
        return False

    def fetch_instruction(self) -> MachineWord:
        address: int = self.data_path.registers[PC]
        instruction: MachineWord = self.data_path.instruction_memory[address]
        self.data_path.latch_register(DR, instruction.arg1)
        self.tick()
        return instruction

    def ld_address(self, instruction: MachineWord) -> None:
        address: int = instruction.arg2
        register: Register = instruction.arg1
        if isinstance(address, Register):
            address = self.data_path.registers[register]
        data: int | None = self.data_path.work_with_memory(True, False, address)
        self.data_path.latch_register(DR, data)
        self.tick()
        self.data_path.latch_register(register, data)
        self.tick()

    def ld_literal(self, instruction: MachineWord) -> None:
        value: int = instruction.arg2
        register: Register = instruction.arg1
        self.data_path.latch_register(register, value)
        self.tick()

    def ld(self, instruction: MachineWord) -> None:
        register_to: Register = instruction.arg1
        address_register: Register = instruction.arg2
        address_to_read: int = self.data_path.execute_arithmetic(Opcode.ADD, 0,
                                                                 self.data_path.registers[address_register])
        self.tick()
        data: int = self.data_path.work_with_memory(True, False, address_to_read)
        self.data_path.latch_register(DR, data)  # в DR значение
        self.tick()
        self.data_path.latch_register(register_to, data)
        self.tick()

    def ld_stack(self, instruction: MachineWord) -> None:
        register_to: Register = instruction.arg1
        address: int = self.data_path.memory_size - instruction.arg2 - 1
        self.tick()
        data: int | None = self.data_path.work_with_memory(True, False, address)
        self.data_path.latch_register(DR, data)
        self.tick()
        self.data_path.latch_register(register_to, data)
        self.tick()

    def st_address(self, instruction: MachineWord) -> None:
        address: int = instruction.arg2
        register: Register = instruction.arg1
        register_data: int = self.data_path.execute_arithmetic(Opcode.ADD, 0, self.data_path.registers[register])
        self.tick()
        self.data_path.latch_register(DR, register_data)
        self.tick()
        self.data_path.work_with_memory(False, True, address)
        self.tick()

    def st(self, instruction: MachineWord) -> None:
        data_register: Register = instruction.arg1
        data: int = self.data_path.execute_arithmetic(Opcode.ADD, 0, self.data_path.registers[data_register])
        self.tick()
        self.data_path.latch_register(DR, data)
        self.tick()
        address_register: Register = instruction.arg2
        address: int = self.data_path.execute_arithmetic(Opcode.ADD, 0, self.data_path.registers[address_register])
        self.tick()
        self.data_path.work_with_memory(False, True, address)
        self.tick()

    def st_stack(self, instruction: MachineWord) -> None:
        register_from: Register = instruction.arg1
        data: int = self.data_path.execute_arithmetic(Opcode.ADD, 0, self.data_path.registers[register_from])
        self.data_path.latch_register(DR, data)
        self.tick()
        address_to: int = self.data_path.memory_size - instruction.arg2 - 1
        self.tick()
        self.data_path.work_with_memory(False, True, address_to)
        self.tick()

    def mv(self, instruction: MachineWord) -> None:
        register_from: Register = instruction.arg1
        register_from_data: int = self.data_path.execute_arithmetic(Opcode.ADD, 0,
                                                                    self.data_path.registers[register_from])
        self.tick()
        register_to: Register = instruction.arg2
        self.data_path.latch_register(register_to, register_from_data)
        self.tick()

    def read(self, instruction: MachineWord) -> None:
        register: Register = instruction.arg1
        port: int = instruction.arg2
        data: int = self.data_path.read_char(port)
        self.data_path.latch_register(register, data)
        self.tick()

    def print_symbol(self, instruction: MachineWord) -> None:
        register: Register = instruction.arg1
        data: int = self.data_path.execute_arithmetic(Opcode.ADD, 0, self.data_path.registers[register])
        self.tick()
        port: int = instruction.arg2
        self.data_path.write_char(data, port)
        self.tick()

    def arythm(self, instruction: MachineWord) -> None:
        res: int = self.data_path.execute_arithmetic(
            instruction.opcode,
            self.data_path.load_register(instruction.arg1),
            self.data_path.load_register(instruction.arg2)
        )
        self.data_path.latch_register(instruction.arg1, res)
        self.tick()

    def add_literal(self, instruction: MachineWord) -> None:
        res: int = self.data_path.execute_arithmetic(
            instruction.opcode,
            self.data_path.load_register(instruction.arg1),
            instruction.arg2
        )
        self.data_path.latch_register(instruction.arg1, res)
        self.tick()

    def push(self, instruction: MachineWord) -> None:
        data_register: Register = instruction.arg1
        data: int = self.data_path.execute_arithmetic(
            Opcode.ADD,
            0,
            self.data_path.registers[data_register]
        )
        self.data_path.latch_register(DR, data)
        self.tick()
        address_register: Register = SP
        address: int = self.data_path.execute_arithmetic(
            Opcode.ADD,
            0,
            self.data_path.registers[address_register]
        )
        self.data_path.work_with_memory(False, True, address)
        self.tick()
        res: int = self.data_path.execute_arithmetic(Opcode.DEC, self.data_path.load_register(SP))
        self.data_path.latch_register(SP, res)
        self.tick()

    def pop(self, instruction: MachineWord) -> None:
        res: int = self.data_path.execute_arithmetic(Opcode.INC, self.data_path.load_register(SP))
        self.data_path.latch_register(SP, res)
        self.tick()
        address: int = self.data_path.execute_arithmetic(Opcode.ADD, self.data_path.registers[SP], 0)
        self.tick()
        data: int | None = self.data_path.work_with_memory(True, False, address)
        self.data_path.latch_register(DR, data)
        self.tick()
        self.data_path.latch_register(instruction.arg1, data)
        self.tick()

    def cmp(self, instruction: MachineWord) -> None:
        inv = self.data_path.execute_arithmetic(Opcode.NEG, self.data_path.load_register(instruction.arg2))
        self.tick()
        inv = self.data_path.execute_arithmetic(Opcode.INC, inv)
        self.tick()
        self.data_path.execute_arithmetic(Opcode.ADD, self.data_path.load_register(instruction.arg1), inv)
        self.tick()

    def sub(self, instruction: MachineWord) -> None:
        inv = self.data_path.execute_arithmetic(Opcode.NEG, self.data_path.load_register(instruction.arg2))
        self.tick()
        inv = self.data_path.execute_arithmetic(Opcode.INC, inv)
        self.tick()
        res = self.data_path.execute_arithmetic(Opcode.ADD, self.data_path.load_register(instruction.arg1), inv)
        self.data_path.latch_register(instruction.arg1, res)
        self.tick()

    def unary_arythm(self, instruction: MachineWord) -> None:
        res: int = self.data_path.execute_arithmetic(instruction.opcode, self.data_path.load_register(instruction.arg1))
        self.data_path.latch_register(instruction.arg1, res)
        self.tick()

    def decode_and_execute_instruction(self):
        instr: MachineWord = self.fetch_instruction()
        opcode: Opcode = instr.opcode
        opcode_mapping = {
            Opcode.LD_ADDR: self.ld_address,
            Opcode.LD_LITERAL: self.ld_literal,
            Opcode.LD: self.ld,
            Opcode.LD_STACK: self.ld_stack,
            Opcode.ST_ADDR: self.st_address,
            Opcode.ST: self.st,
            Opcode.ST_STACK: self.st_stack,
            Opcode.MV: self.mv,
            Opcode.READ: self.read,
            Opcode.PRINT: self.print_symbol,
            Opcode.ADD: self.arythm,
            Opcode.OR: self.arythm,
            Opcode.AND: self.arythm,
            Opcode.SHL: self.arythm,
            Opcode.SHR: self.arythm,
            Opcode.XOR: self.arythm,
            Opcode.INC: self.unary_arythm,
            Opcode.DEC: self.unary_arythm,
            Opcode.ADD_LITERAL: self.add_literal,
            Opcode.CMP: self.cmp,
            Opcode.SUB: self.sub,
            Opcode.PUSH: self.push,
            Opcode.POP: self.pop,
            Opcode.NEG: self.unary_arythm,
            Opcode.MUL: self.arythm,
            Opcode.DIV: self.arythm,
            Opcode.MOD: self.arythm,
        }
        if self.decode_and_execute_control_flow_instruction(instr, opcode):
            return
        if opcode in opcode_mapping:
            opcode_mapping[opcode](instr)

        self.data_path.latch_register(PC, self.data_path.registers[PC] + 1)
        self.tick()

    def print_val_if_enum(self, value):
        if isinstance(value, Enum):
            return value.name
        return value

    def __repr__(self):
        formatted_registers = {f"r{register.value}": value for register, value in self.data_path.registers.items()}
        formatted_string = ", ".join([f"'{key}': {value}" for key, value in formatted_registers.items()])

        state_repr = "TICK: {:3} PC: {:3}  MEM_OUT: {} {} reg: {}".format(
            self.tick_counter,
            self.data_path.registers[PC],
            self.print_val_if_enum(self.data_path.instruction_memory[self.data_path.registers[PC]].arg1),
            self.print_val_if_enum(self.data_path.instruction_memory[self.data_path.registers[PC]].arg2),
            formatted_string,
        )

        instr = self.data_path.instruction_memory[self.data_path.registers[PC]]
        opcode = str(instr.opcode)

        instr_repr = "  ('{}'@{}:{} {})".format(instr.id, opcode, instr.arg1, instr.arg2)

        return "{} \t{}".format(state_repr, instr_repr)


def simulation(mem: list[MachineWord], input_tokens: list[str], limit: int, static_mem: str):
    ports: dict[int, list[str]] = {}
    ports[0] = input_tokens
    data_path = DataPath(mem, ports)
    control_unit = ControlUnit(data_path)
    instr_counter = 0

    with open(static_mem, encoding="utf-8") as file:
        # Чтение строки из файла
        line = file.readline()

        # Разделение строки на отдельные числа по пробелам
        numbers_str = line.split()

        # Преобразование строк в целые числа
        numbers = [int(num) for num in numbers_str]
        data_path.data_memory[:len(numbers)] = numbers
        data_path.registers[Register.r16] = len(numbers)

    logging.debug("%s", control_unit)
    try:
        while instr_counter < limit:
            control_unit.decode_and_execute_instruction()
            instr_counter += 1
            logging.debug("%s", control_unit)
    except EOFError:
        logging.warning("Input buffer is empty!")
    except StopIteration:
        pass

    if instr_counter >= limit:
        logging.warning("Limit exceeded!")
    logging.info("output_buffer: %s", repr("".join(data_path.output_ports[0])))
    return "".join(data_path.output_ports[0]), instr_counter, control_unit.get_tick()


def main(code_file, input_file, static_mem):
    code: list[MachineWord] = read_code_from_file(code_file)
    with open(input_file, encoding="utf-8") as file:
        input_text = file.read()
        input_token = []
        for char in input_text:
            input_token.append(char)

    output, instr_counter, ticks = simulation(
        code,
        input_tokens=input_token,
        limit=100000,
        static_mem=static_mem
    )

    print("".join(output))
    print("instr_counter: ", instr_counter, "ticks:", ticks)


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    assert len(sys.argv) == 4, "Wrong arguments: emulator.py <code_file> <input_file> <static_mem>"
    _, code_file, input_file, static_memory = sys.argv
    main(code_file, input_file, static_memory)
