from __future__ import annotations

from enum import Enum

from lab3.exceptions.invalid_statement_error import InvalidStatementError
from lab3.interpreter.lexer import Token, lexing


class AstType(Enum):
    IF = "if"
    ELSE = "else"
    WHILE = "while"
    READ = "read"
    READ_CHAR = "read_char"
    PRINT_STRING = "print_string"
    PRINT_INT = "print_int"
    PRINT_CHAR = "print_char"
    LET = "let"
    EQ = "eq"
    GE = "ge"
    GT = "gt"
    LT = "lt"
    LE = "ne"
    NEQ = "neq"
    PLUS = "plus"
    MINUS = "minus"
    MUL = "mul"
    DIV = "div"
    SHL = "shl"
    SHR = "shr"
    AND = "and"
    OR = "or"
    XOR = "xor"
    STRING = "string"
    NUMBER = "number"
    NAME = "name"
    ROOT = "root"
    BLOCK = "block"
    ASSIGN = "assign"
    CMP = "cmp"
    MOD = "mod"


token2type = {getattr(Token, node_type.name): node_type for node_type in AstType if hasattr(Token, node_type.name)}


def map_token_to_type(token: Token) -> AstType:
    assert token in token2type
    return token2type[token]


class AstNode:
    def __init__(self, ast_type: AstType, value: str = ""):
        self.astType = ast_type
        self.children: list[AstNode] = []
        self.value = value

    @classmethod
    def from_token(cls, token: Token, value: str = "") -> AstNode:
        return cls(map_token_to_type(token), value)

    def add_child(self, node: AstNode) -> None:
        self.children.append(node)


def match_list(tokens: list[tuple[Token, str]], token_req: list[Token]) -> None:
    assert tokens[0][0] in token_req


def match_list_and_delete(tokens: list[tuple[Token, str]], token_req: list[Token]) -> tuple[Token, str]:
    match_list(tokens, token_req)
    return tokens.pop(0)


def parse_math_expression(tokens: list[tuple[Token, str]]) -> AstNode:
    return parse_first_level_operation(tokens)


def parse_first_level_operation(tokens: list[tuple[Token, str]]) -> AstNode:
    left_node: AstNode = parse_second_level_operations(tokens)
    node: AstNode = left_node

    while tokens and tokens[0][0] in [Token.PLUS, Token.MINUS]:
        node = AstNode.from_token(tokens[0][0])
        tokens.pop(0)
        node.add_child(left_node)
        node.add_child(parse_second_level_operations(tokens))
        left_node = node
    return node


def parse_second_level_operations(tokens: list[tuple[Token, str]]) -> AstNode:
    left_node: AstNode = parse_literal_or_name(tokens)
    node: AstNode = left_node
    while tokens and tokens[0][0] in [
        Token.MUL,
        Token.DIV,
        Token.AND,
        Token.OR,
        Token.XOR,
        Token.SHL,
        Token.SHR,
        Token.MOD,
    ]:
        node = AstNode.from_token(tokens[0][0])
        tokens.pop(0)
        node.add_child(left_node)
        node.add_child(parse_literal_or_name(tokens))
        left_node = node
    return node


def parse_literal_or_name(tokens: list[tuple[Token, str]]) -> AstNode:
    if tokens[0][0] == Token.NAME or tokens[0][0] == Token.NUMBER:
        node: AstNode = AstNode.from_token(tokens[0][0], tokens[0][1])
        tokens.pop(0)
        return node
    match_list_and_delete(tokens, [Token.LPAREN])
    expression: AstNode = parse_first_level_operation(tokens)
    match_list_and_delete(tokens, [Token.RPAREN])
    return expression


def parse_operand(tokens: list[tuple[Token, str]]) -> AstNode:
    if tokens[0][0] == Token.STRING:
        node: AstNode = AstNode.from_token(tokens[0][0], tokens[0][1])
        tokens.pop(0)
        return node
    if tokens[0][0] == Token.READ or tokens[0][0] == Token.READ_CHAR:
        return parse_read(tokens)
    node: AstNode = parse_math_expression(tokens)
    return node


def parse_comparison(tokens: list[tuple[Token, str]]) -> AstNode:
    left_node: AstNode = parse_math_expression(tokens)
    match_list(tokens, [Token.GE, Token.GT, Token.LE, Token.LT, Token.NEQ, Token.EQ])
    comp: AstNode = AstNode.from_token(tokens[0][0])
    tokens.pop(0)
    right_node: AstNode = parse_math_expression(tokens)
    comp.add_child(left_node)
    comp.add_child(right_node)
    return comp


def parse_while(tokens: list[tuple[Token, str]]) -> AstNode:
    node: AstNode = AstNode.from_token(tokens[0][0])
    match_list_and_delete(tokens, [Token.WHILE])
    match_list_and_delete(tokens, [Token.LPAREN])
    node.add_child(parse_comparison(tokens))
    match_list_and_delete(tokens, [Token.RPAREN])
    node.add_child(parse_block(tokens))
    return node


def parse_if(tokens: list[tuple[Token, str]]) -> AstNode:
    node: AstNode = AstNode.from_token(tokens[0][0])
    match_list_and_delete(tokens, [Token.IF])
    match_list_and_delete(tokens, [Token.LPAREN])
    node.add_child(parse_comparison(tokens))
    match_list_and_delete(tokens, [Token.RPAREN])
    node.add_child(parse_block(tokens))
    if tokens[0][0] == Token.ELSE:
        match_list_and_delete(tokens, [Token.ELSE])
        node.add_child(parse_block(tokens))
    return node


def parse_allocation_or_assignment(tokens: list[tuple[Token, str]]) -> AstNode:
    if tokens[0][0] == Token.LET:
        node: AstNode = AstNode.from_token(Token.LET)
        match_list_and_delete(tokens, [Token.LET])
    else:
        node: AstNode = AstNode.from_token(Token.ASSIGN)
    match_list(tokens, [Token.NAME])
    node.add_child(AstNode.from_token(Token.NAME, tokens[0][1]))
    tokens.pop(0)
    match_list_and_delete(tokens, [Token.ASSIGN])
    node.add_child(parse_operand(tokens))
    match_list_and_delete(tokens, [Token.SEMICOLON])
    return node


def parse_print(tokens: list[tuple[Token, str]]) -> AstNode:
    node: AstNode = AstNode.from_token(tokens[0][0])
    match_list_and_delete(tokens, [Token.PRINT_STRING, Token.PRINT_INT, Token.PRINT_CHAR])
    match_list_and_delete(tokens, [Token.LPAREN])
    node.add_child(parse_operand(tokens))
    if node.astType == AstType.PRINT_INT:
        assert node.children[0].astType != AstType.STRING
    if node.astType == AstType.PRINT_STRING:
        assert node.children[0].astType == AstType.STRING or node.children[0].astType == AstType.NAME
    if node.astType == AstType.PRINT_CHAR:
        assert node.children[0].astType == AstType.NAME
    match_list_and_delete(tokens, [Token.RPAREN])
    match_list_and_delete(tokens, [Token.SEMICOLON])
    return node


def parse_read(tokens: list[tuple[Token, str]]) -> AstNode:
    node: AstNode = AstNode.from_token(tokens[0][0])
    match_list_and_delete(tokens, [Token.READ, Token.READ_CHAR])
    match_list_and_delete(tokens, [Token.LPAREN])
    match_list_and_delete(tokens, [Token.RPAREN])
    return node


def parse_block(tokens: list[tuple[Token, str]]) -> AstNode:
    node: AstNode = AstNode(AstType.BLOCK)
    match_list_and_delete(tokens, [Token.LBRACE])
    while tokens[0][0] != Token.RBRACE:
        node.add_child(parse_statement(tokens))
    match_list_and_delete(tokens, [Token.RBRACE])
    return node


def parse_statement(tokens: list[tuple[Token, str]]) -> AstNode:
    if tokens[0][0] == Token.WHILE:
        return parse_while(tokens)
    if tokens[0][0] == Token.IF:
        return parse_if(tokens)
    if tokens[0][0] == Token.LET or tokens[0][0] == Token.NAME:
        return parse_allocation_or_assignment(tokens)
    if tokens[0][0] == Token.PRINT_STRING or tokens[0][0] == Token.PRINT_INT or tokens[0][0] == Token.PRINT_CHAR:
        return parse_print(tokens)
    if tokens[0][0] == Token.READ:
        return parse_read(tokens)
    raise InvalidStatementError("Invalid statement {}".format(tokens[0][0].name))


def parse_program(tokens: list[tuple[Token, str]]) -> AstNode:
    node: AstNode = AstNode(AstType.ROOT)
    while tokens:
        node.add_child(parse_statement(tokens))
    return node


def parse(program: str) -> AstNode:
    return parse_program(lexing(program))
