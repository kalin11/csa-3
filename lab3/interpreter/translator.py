from __future__ import annotations

import sys

from lab3.exceptions.illegal_token_error import IllegalTokenError
from lab3.interpreter.parser import AstNode, AstType, parse
from lab3.interpreter.program import Program, ast_type2opcode, inverted_conditions
from lab3.machine.isa import MachineWord, Opcode, Register, StaticMemoryAddressStub, write_machine_code_to_file


def ast_to_machine_code(root: AstNode, static_mem: str) -> list[MachineWord]:
    program = Program()
    for child in root.children:
        ast_to_machine_code_rec(child, program)
    program.add_instruction(Opcode.HALT)
    static_memory: list[int] = program.resolve_static_mem()
    with open(static_mem, "w") as file:
        # Преобразуем числа в строки и записываем их в файл
        file.write(" ".join(map(str, static_memory)))
    return program.machine_code


def ast_to_machine_code_rec(node: AstNode, program: Program) -> None:
    if node.astType == AstType.WHILE or node.astType == AstType.IF:
        ast_to_machine_code_if_or_while(node, program)

    elif node.astType in [AstType.PRINT_INT, AstType.PRINT_CHAR, AstType.PRINT_STRING]:
        ast_to_machine_code_print(node, program)

    elif node.astType == AstType.LET:
        ast_to_machine_code_let(node, program)

    elif node.astType == AstType.ASSIGN:
        ast_to_machine_code_assign(node, program)

    else:
        raise IllegalTokenError("Invalid ast node type {}".format(node.astType.name))


def parse_expression(node: AstNode, program: Program) -> int | None:
    if node.astType == AstType.NAME:
        return program.get_variable_offset(node.value)
    if node.astType == AstType.STRING:
        return program.add_variable_to_static_memory(node.value)
    return ast_to_machine_code_math(node, program)


def ast_to_machine_code_block(node: AstNode, program: Program) -> int:
    for child in node.children:
        ast_to_machine_code_rec(child, program)
    return program.current_command_address


def ast_to_machine_code_if_or_while(node: AstNode, program: Program) -> None:
    program.reset_registers()
    block_begin_stack_pointer: int = len(program.variables)
    comparator = node.children[0]
    block_begin: int = program.current_command_address
    left_address = parse_expression(comparator.children[0], program)
    if left_address is None:
        program.add_instruction(Opcode.MV, Register.r9, Register.r12)
    else:
        program.add_instruction(Opcode.LD_STACK, Register.r12, left_address)
    right_address = parse_expression(comparator.children[1], program)
    if right_address is not None:
        program.add_instruction(Opcode.LD_STACK, Register.r9, right_address)

    program.add_instruction(Opcode.CMP, Register.r12, Register.r9)
    comp_instr_addr = program.add_instruction(inverted_conditions[ast_type2opcode[comparator.astType]], -1)
    block_end = ast_to_machine_code_block(node.children[1], program)

    if node.astType == AstType.WHILE:
        block_end = program.add_instruction(Opcode.JMP, block_begin)
        program.machine_code[comp_instr_addr].arg1 = block_end + 1
    else:
        if len(node.children) == 3 and node.children[2].astType == AstType.ELSE:
            addr_before_else_block = program.add_instruction(Opcode.JMP, -1)
            else_block_end = ast_to_machine_code_block(node.children[1], program)
            program.machine_code[comp_instr_addr].arg1 = addr_before_else_block + 1  # else start address
            program.machine_code[addr_before_else_block].arg1 = else_block_end + 1
        else:
            program.machine_code[comp_instr_addr].arg1 = block_end + 1
    program.reset_registers()
    program.return_from_code_block(block_begin_stack_pointer)


def ast_to_machine_code_print(node: AstNode, program: Program) -> None:
    if node.astType == AstType.PRINT_INT:
        ast_to_machine_code_math(node.children[0], program)
        program.add_instruction(Opcode.PUSH, Register.r11)
        program.add_instruction(Opcode.LD_LITERAL, Register.r11, 1)
        loop_begin = program.add_instruction(Opcode.LD_LITERAL, Register.r10, 10)
        program.add_instruction(Opcode.MV, Register.r9, Register.r8)
        ast_to_machine_code_mod(node, program, Register.r8, Register.r10)
        ast_to_machine_code_div(node, program)
        program.add_instruction(Opcode.MV, Register.r8, Register.r10)
        program.add_instruction(Opcode.ADD_LITERAL, Register.r10, 48)
        cmp_addr = program.add_instruction(Opcode.CMP, Register.r9, Register.r0)
        program.add_instruction(Opcode.JE, cmp_addr + 5)
        program.add_instruction(Opcode.INC, Register.r11)
        program.add_instruction(Opcode.PUSH, Register.r10)
        program.add_instruction(Opcode.JMP, loop_begin)

        program.add_instruction(Opcode.PUSH, Register.r10)  # даже если 0, последний остаток надо записывать

        loop_begin = program.add_instruction(Opcode.CMP, Register.r11, Register.r0)
        program.add_instruction(Opcode.JE, loop_begin + 6)
        program.add_instruction(Opcode.POP, Register.r10)
        program.add_instruction(Opcode.PRINT, Register.r10, 0)
        program.add_instruction(Opcode.DEC, Register.r11)
        program.add_instruction(Opcode.JMP, loop_begin)
        program.add_instruction(Opcode.POP, Register.r11)

    if node.astType == AstType.PRINT_CHAR:
        ast_to_machine_code_math(node.children[0], program)
        program.add_instruction(Opcode.PRINT, Register.r9, 0)

    if node.astType == AstType.PRINT_STRING:
        if node.children[0].astType == AstType.STRING:
            str_addr = program.add_variable_to_static_memory(node.children[0].value)
            program.add_instruction(Opcode.LD_LITERAL, Register.r9, StaticMemoryAddressStub(str_addr))
        else:
            var_addr: int | None = program.get_variable_offset(node.children[0].value)
            assert var_addr is not None
            program.add_instruction(Opcode.LD_STACK, Register.r9, var_addr)
        program.add_instruction(Opcode.MV, Register.r9, Register.r11)  # адрес буффера из r9 в r11
        program.add_instruction(Opcode.LD, Register.r9, Register.r9)  # теперь в r9 первый символ строки
        while_start: int = program.current_command_address

        program.add_instruction(Opcode.CMP, Register.r9, Register.r0)
        program.add_instruction(Opcode.JE, while_start + 6)
        program.add_instruction(Opcode.PRINT, Register.r9, 0)
        program.add_instruction(Opcode.INC, Register.r11)
        program.add_instruction(Opcode.LD, Register.r9, Register.r11)
        program.add_instruction(Opcode.JMP, while_start)


def ast_to_machine_code_let(node: AstNode, program: Program) -> None:
    name: str = node.children[0].value
    if node.astType == AstType.LET:
        assert program.get_variable_offset(name) is None
        program.push_variable_to_stack(name, 0)
        ast_to_machine_code_assign(node, program)


def ast_to_machine_code_assign(node: AstNode, program: Program) -> None:
    name: str = node.children[0].value
    assert node.children[0].astType == AstType.NAME
    if node.astType in [AstType.ASSIGN, AstType.LET]:
        addr = program.get_variable_offset(name)
        assert addr is not None
        if node.children[1].astType == AstType.READ_CHAR:
            ast_to_machine_code_read_char(program)
            program.add_instruction(Opcode.ST_STACK, Register.r10, addr)
            program.clear_variable_in_registers(name)

        elif node.children[1].astType == AstType.STRING:
            new_address: int = program.add_variable_to_static_memory(node.children[1].value)
            st_literal_by_stack_offset(program, StaticMemoryAddressStub(new_address), addr)
            program.clear_variable_in_registers(name)

        elif node.children[1].astType == AstType.READ:
            ast_to_machine_code_read(program)
            program.add_instruction(Opcode.ST_STACK, Register.r9, addr)  # update var value
            program.clear_variable_in_registers(name)
        else:
            ast_to_machine_code_math(node.children[1], program)
            program.add_instruction(Opcode.ST_STACK, Register.r9, addr)
            program.clear_variable_in_registers(name)


def ast_to_machine_code_math(node: AstNode, program: Program) -> None:
    if not ast_to_machine_code_math_rec(node, program):
        program.add_instruction(Opcode.POP, Register.r9)


def resolve_register_for_operation(is_left: bool = True) -> Register:
    return Register.r9 if is_left else Register.r10


def ast_to_machine_code_math_rec(node: AstNode, program: Program, is_left: bool = True) -> bool:
    if node.astType == AstType.NUMBER:
        program.add_instruction(Opcode.LD_LITERAL, resolve_register_for_operation(is_left), int(node.value))
        return True
    if node.astType == AstType.NAME:
        reg = program.load_variable(node.value)
        program.add_instruction(Opcode.MV, reg, resolve_register_for_operation(is_left))
        return True
    if ast_to_machine_code_math_rec(node.children[0], program, True):
        program.add_instruction(Opcode.PUSH, Register.r9)
    if ast_to_machine_code_math_rec(node.children[1], program, False):
        program.add_instruction(Opcode.PUSH, Register.r10)
    program.add_instruction(Opcode.POP, Register.r10)
    program.add_instruction(Opcode.POP, Register.r9)
    if not perform_userspace_math(node, program):
        program.add_instruction(ast_type2opcode[node.astType], Register.r9, Register.r10)
    program.add_instruction(Opcode.PUSH, Register.r9)
    return False


def perform_userspace_math(node: AstNode, program: Program) -> bool:
    if node.astType is AstType.DIV:
        ast_to_machine_code_div(node, program)
        return True
    if node.astType is AstType.MOD:
        ast_to_machine_code_mod(node, program)
        return True
    if node.astType is AstType.MUL:
        ast_to_machine_code_mul(program)
        return True
    return False


def ast_to_machine_code_mul(program: Program):
    program.add_instruction(Opcode.MUL, Register.r9, Register.r10)


def ast_to_machine_code_div(node: AstNode, program: Program, reg1: Register = Register.r9,
                            reg2: Register = Register.r10) -> None:
    program.add_instruction(Opcode.DIV, reg1, reg2)


def ast_to_machine_code_mod(node: AstNode, program: Program,
                            reg1: Register = Register.r9,
                            reg2: Register = Register.r10,
                            ):
    program.add_instruction(Opcode.MOD, reg1, reg2)


def st_literal_by_stack_offset(program: Program, value: int | StaticMemoryAddressStub, var_addr: int):
    reg: Register = program.clear_register_for_variable()
    program.add_instruction(Opcode.LD_LITERAL, reg, value)
    program.add_instruction(Opcode.ST_STACK, reg, var_addr)


def ast_to_machine_code_read(program: Program) -> None:
    program.add_instruction(Opcode.PUSH, Register.r8)
    program.add_instruction(Opcode.LD_LITERAL, Register.r9, 0)  # прочитанный символ
    program.add_instruction(Opcode.LD_LITERAL, Register.r11, 0)  # счетчик
    program.add_instruction(Opcode.MV, Register.r2,
                            Register.r8)  # в r2 лежит адрес начала строки в динамической памяти
    program.add_instruction(Opcode.MV, Register.r8,
                            Register.r12)  # в r8 адрес начала буфера (сохраянем в r12 адрес начала буфера)
    do_while_start = program.current_command_address
    program.add_instruction(Opcode.READ, Register.r9, 0)
    program.add_instruction(Opcode.CMP, Register.r9, Register.r0)  # если символ равен 0, то строка закончилась
    program.add_instruction(Opcode.JE, do_while_start + 7)
    program.add_instruction(Opcode.INC, Register.r11)  # инкрементируем счетчик
    program.add_instruction(Opcode.INC, Register.r12)  # переход на следующий адрес буффера
    program.add_instruction(Opcode.ST, Register.r9, Register.r12)  # сохраняем символ в r9 в буффер
    program.add_instruction(Opcode.JMP, do_while_start)
    program.add_instruction(Opcode.INC, Register.r12)
    program.add_instruction(Opcode.ST, Register.r0, Register.r12)  # добавить нуль терминатор в конец строки
    program.add_instruction(Opcode.INC, Register.r8)
    program.add_instruction(Opcode.MV, Register.r8, Register.r9)  # save read string address in r9
    program.add_instruction(Opcode.ADD, Register.r8, Register.r11)
    program.add_instruction(Opcode.ST, Register.r8, Register.r2)
    program.add_instruction(Opcode.ADD, Register.r2, Register.r11)
    program.add_instruction(Opcode.INC, Register.r2)
    program.add_instruction(Opcode.POP, Register.r8)


def ast_to_machine_code_read_char(program: Program) -> None:
    program.add_instruction(Opcode.READ, Register.r10, 0)


def main(source, target, static_mem) -> None:
    with open(source, encoding="utf-8") as source_file:
        source = source_file.read()
    ast = parse(source)
    write_machine_code_to_file(target, ast_to_machine_code(ast, static_mem))


if __name__ == "__main__":
    assert len(sys.argv) == 4, "Wrong args: translator.py <source> <target>"
    _, source, target, static_mem = sys.argv
    main(source, target, static_mem)
