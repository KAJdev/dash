DASH_GRAMMAR = """
start: statement+

statement: block | while | if | loop | event | function | ((assign | expression | return) ";")

assign: WORD "=" expression
//bind: WORD ["=" expression]
block: "{" statement* "}"
while: "while" expression block
if: "if" expression block [else]
else: "else" (if | block)
loop: "loop" block
event: "on" WORD block
return.1: "return" [expression]

expression: (LITERAL | ESCAPED_STRING | WORD | SIGNED_NUMBER | COLOR | inverse | call | (expression [OPERATOR expression])) | "(" expression ")"

//args: "(" [bind("," bind)*] ")"
binds: "(" [WORD("," WORD)*] ")"
args: "(" [expression("," expression)*] ")"
call: WORD args
function: "fn" WORD binds block
inverse: "not" expression

LITERAL: "true"|"false"|"none"
OPERATOR: "+"|"-"|"/"|"*"|"=="|"and"|"or"|"is"|"<"|">"|"<="|">="|"in"
COLOR: ("#"|"0x")(HEXDIGIT~6)

%import common.ESCAPED_STRING
%import common.SIGNED_NUMBER
%import common.WS
%import common.WORD
%import common.C_COMMENT
%import common.CPP_COMMENT
%import common.LETTER
%import common.HEXDIGIT

%ignore WS
%ignore C_COMMENT
%ignore CPP_COMMENT
"""

from lark import Lark
parser = Lark(DASH_GRAMMAR)