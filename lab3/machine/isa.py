from __future__ import annotations

import json
from enum import Enum


class EnumEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Register):
            return "r" + str(obj.value)
        return super().default(obj)


class StaticMemoryAddressStub:
    offset: int  # -1  означает последний элемент после всей статической памяти

    def __init__(self, offset: int = 0):
        self.offset = offset


class Opcode(Enum):
    ST = "ST"  # прямая адресация сохранения
    ST_ADDR = "ST_ADDR"  # косвенная адресация сохранения
    ST_STACK = "ST_STACK"  # относительно конца стека
    LD_ADDR = "LD_ADDR"  # косвенная адресация загрузки
    LD_LITERAL = "LD_LITERAL"  # для загрузки литерала напрямую
    LD_STACK = "LD_STACK"  # загрузка относительно конца стека
    LD = "LD"  # косвенная адресация загрузки
    JMP = "JMP"
    ADD = "ADD"
    DIV = "DIV"
    MUL = "MUL"
    MOD = "MOD"
    SUB = "SUB"
    MV = "MV"
    READ = "READ"
    PRINT = "PRINT"
    JLE = "JLE"  # less or equals
    JL = "JL"  # less
    JGE = "JGE"  # greater or equals
    JG = "JG"  # greater
    JNE = "JNE"  # not equals
    JE = "JE"  # equals
    NEG = "NEG"
    SHL = "SHL"
    SHR = "SHR"
    AND = "AND"
    OR = "OR"
    XOR = "XOR"
    CMP = "CMP"
    PUSH = "PUSH"
    POP = "POP"
    INC = "INC"
    DEC = "DEC"
    HALT = "HALT"
    ADD_LITERAL = "ADD_LITERAL"


data_memory_size = 4096


class Register(Enum):
    r0 = 0
    r1 = 1
    r2 = 2
    r3 = 3
    r4 = 4
    r5 = 5
    r6 = 6
    r7 = 7
    r8 = 8
    r9 = 9
    r10 = 10
    r11 = 11
    r12 = 12
    r13 = 13
    r14 = 14
    r15 = 15


SP: Register = Register.r14

DR: Register = Register.r13

PC: Register = Register.r1


class MachineWord:
    index: int
    opcode: Opcode
    arg1: int | Register | StaticMemoryAddressStub
    arg2: int | Register | StaticMemoryAddressStub

    def __init__(self, index: int, opcode: Opcode, arg1=None, arg2=None):
        self.index = index
        self.opcode = opcode
        self.arg1 = arg1
        self.arg2 = arg2


def write_machine_code_to_file(filename: str, code: list[MachineWord]) -> None:
    with open(filename, "w", encoding="utf-8") as file:
        buf = []
        for instr in code:
            buf.append(
                json.dumps(
                    {
                        "index": instr.index,
                        "opcode": instr.opcode.value,
                        "arg1": instr.arg1,
                        "arg2": instr.arg2,
                    },
                    cls=EnumEncoder,
                )
            )
        file.write("[" + ",\n ".join(buf) + "]")


def convert_to_register(arg):
    if arg and isinstance(arg, str) and arg.startswith("r"):
        return Register[arg]
    return arg


def read_code_from_file(filename: str) -> list[MachineWord]:
    with open(filename, encoding="utf-8") as file:
        code = json.loads(file.read())
    prog: list[MachineWord] = []
    for instr in code:
        word = MachineWord(
            instr["index"],
            Opcode[instr["opcode"]],
            convert_to_register(instr["arg1"]),
            convert_to_register(instr["arg2"]),
        )
        prog.append(word)
    for index in range(len(prog), data_memory_size):
        prog.append(MachineWord(index, Opcode.JMP, 0))
    return prog
