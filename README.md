# CSA lab 3
Выполнил Лысенко Артём Константинович P33312
- `alg | risc | harv | hw | instr | struct | stream | port | cstr | prob5 | pipeline`
- Без усложнения

## Язык программирования
Разработанный язык похож на супер упрощенный JS. 
Строки разделяются точкой с запятой.
### Язык поддерживает
1. объявление и инициализацию переменных
2. математические операции
3. конструкции `if`, `if-else`, `while`
4. `read()` - читает строку из входного буфера
5. `read_char()` - читает символ,
6. `print_string()`, `print_int()`, `print_char()`

Язык не поддерживает функции, приведенные выше read() и пр - это просто синтаксис. 
Есть только 2 типа - int, str. Типизация сильная, динамическая.
Язык поддерживает области видимости, которые определяются блоками while и if.
### Расширенная форма Бэкуса-Наура
``` ebnf
program ::= statement | program statement
statement ::= conditional | while | io | allocation | assign | if
assign ::= name "=" expr
io ::= read | print_int | print_str
conditional ::= if | else
if ::= "if" "(" comp_expr ")" "{" program "}"
else ::= "else" "{" program "}"
while ::= "while" "(" comp_expr ")" "{" program "}"
allocation ::= "let" name "=" value semicolon 
    | "let" name "=" read_char semicolon 
    | "let" name "=" read semicolon 
read ::= "read()" semicolon
read_char ::= "read_char()" semicolon
print_string ::= "print_str(" name ")" semicolon | "print(" string ")" semicolon
print_int ::= "print_int(" name ")" semicolon | "print(" number ")" semicolon
print_char ::= "print_char(" name ")" semicolon
value ::= string | number
string ::= "\"[\w\s,.:;!?()\\-]+\""
comp_expr ::= expr comparison_sign expr
expr ::= "(" expr ")" | expr op expr | number | string | name
comparison_sign ::= "==" | ">=" | ">" | "<" | "<=" | "!="
name ::= "[a-zA-Z]+"
number ::= "-?[0-9]+"
semicolon ::= ";"
op ::= "*" | "/" | "%" | "+" | "-" | "<<" | ">>" | "&" | "|" | "^"
```

Примеры кода:
```
let f1 = 1;
let f2 = 2;
let ans = f2;
let max = 4000000;
while( f1 + f2 < max ) {
  let f3 = f1 + f2;
  if (f3 % 2 == 0) {
    ans = ans + f3;
  }
  f1 = f2;
  f2 = f3;
}
print_int(ans);
```

```
let b = "cat";
let da = "hello\n";
print_string(da);
```

## Организация памяти
`todo`
## Система команд

Особенности процессора:

- Машинное слово -- 32 бита, знаковое.
- Поток управления:
    - инкремент `PC` после каждой инструкции;
    - условные и безусловные переходы.
У команды может быть до двух аргументов.

