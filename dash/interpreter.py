from dataclasses import dataclass, field
from lark import Transformer, Tree, Token, Lark, Transformer
from grammars import parser
import jaro

class DashTrue:
   __bool__ = lambda _: True
   __str__ = __repr__ = lambda _: "true"

class DashFalse:
    __bool__ = lambda _: False
    __str__ = __repr__ = lambda _: "false"

class DashNone:
    __bool__ = lambda _: False
    __str__ = __repr__ = lambda _: "none"

none = DashNone()
true = DashTrue()
false = DashFalse()

LITERALS = {
    'none': none,
    'true': true,
    "false": false
}

def filter_children(children):
    return list(filter(lambda child: child is not None, iter(children)))

class DashTransformer(Transformer):
    def SIGNED_NUMBER(self, n):
        return float(n)

    def ESCAPED_STRING(self, s: str):
        return s[1:-1]

    def LITERAL(self, l):
        return LITERALS[l]

    def COLOR(self, c):
        return int(c.replace("#", "0x"), 16)

class StandardLibrary:
    pass

@dataclass(slots=True)
class Memory:
    objects: dict = field(default_factory=dict)
    functions: dict = field(default_factory=dict)
    events: dict = field(default_factory=dict)

class Environment:
    def __init__(self):
        self.memory = [
            Memory()
        ]

    def get(self, name: str, domain: str):
        for memory in reversed(self.memory):
            if (seg := getattr(memory, domain)) is not None:
                if name not in seg:
                    continue
                return seg[name]

        # try to find a similar name in the global memory
        err = f"`{name}` not found in the current scope."
        for memory in reversed(self.memory):
            for _name in getattr(memory, domain):
                if jaro.jaro_winkler_metric(name, _name) > 0.8:
                    err += f" Did you mean `{_name}`?"
        
        raise NameError(err)

    def set(self, name: str, value, domain: str, _global: bool = False):
        if _global:
           getattr(self.memory[0], domain)[name] = value
        else:
            getattr(self.memory[-1], domain)[name] = value

    def push(self, memory: Memory = None):
        self.memory.append(memory or Memory())

    def pop(self):
        self.memory.pop()

    def __str__(self):
        return str(self.memory)

    def __repr__(self) -> str:
        return str(self)

class Interpreter:
    def __init__(self, stdlib: StandardLibrary):
        self.inputs = []
        self.outputs = []
        self.halted = False
        self.debug = False
        self.memory = Environment()

        for name, func in stdlib.__class__.__dict__.items():
            if not name.startswith('_'):
                self.memory.set(name, func, 'functions', True)

    def parse(self, program: str):
        return DashTransformer().transform(parser.parse(program))

    def eval(self, program: str):
        for statement in self.parse(program).children:
            self.eval_statement(statement.children[0])

    def call_event(self, event, **args):
        try:
            event = self.memory.get(event, 'events')
        except NameError:
            return

        return self.eval_block(event, memory=Memory(
            objects={**args}
        ))

    def eval_expression(self, expression):
        expression.children = filter_children(expression.children)

        if len(expression.children) == 1:
            child = expression.children[0]
            if isinstance(child, Token):
                if child.type == "WORD":
                    return self.memory.get(child.value, 'objects')
            elif isinstance(child, Tree):
                if child.data == "inverse":
                    return not self.eval_expression(child.children[0])
                elif child.data == "call":
                    args = filter_children(child.children[1].children)
                    func = self.memory.get(child.children[0].value, 'functions')

                    if not callable(func):
                        if len(args) != len(func['args']):
                            raise TypeError(f"`{child.children[0].value}` expects {len(func['args'])} arguments, got {len(args)}")

                        return self.eval_block(func['body'], memory=Memory(
                            objects={
                                arg: self.eval_expression(args[i])
                                for i, arg in enumerate(func['args'])
                            }
                        ))
                    else:
                        return func(self.memory, *[self.eval_expression(arg) for arg in args])
            else:
                return child

        elif len(expression.children) == 3:
            left = self.eval_expression(expression.children[0])
            right = self.eval_expression(expression.children[2])
            operator = expression.children[1].value

            if operator == "==" or operator == "is": return left == right
            elif operator == "!=": return left != right
            elif operator == ">": return left > right
            elif operator == "<": return left < right
            elif operator == ">=": return left >= right
            elif operator == "<=": return left <= right
            elif operator == "and": return left and right
            elif operator == "or": return left or right
            elif operator == "in": return right in left
            elif operator == "+": return left + right
            elif operator == "-": return left - right
            elif operator == "*": return left * right
            elif operator == "/": return left / right
            elif operator == "%": return left % right
            elif operator == "**": return left ** right
            elif operator == "//": return left // right

    def eval_block(self, block, memory=None):
        self.memory.push(memory)
        for statement in block.children:
            x = self.eval_statement(statement.children[0])
            if x is not None:
                return x
        self.memory.pop()

    def eval_statement(self, rule):
        if rule.data == "assign":
            name = rule.children[0].value
            value = self.eval_expression(rule.children[1])
            self.memory.set(name, value, 'objects')

        elif rule.data == "block":
            self.eval_block(rule)

        elif rule.data == "if":
            condition = self.eval_expression(rule.children[0])
            if condition:
                self.eval_block(rule.children[1])
            elif rule.children[2] is not None:
                self.eval_statement(rule.children[2].children[0])

        elif rule.data == "while":
            condition = self.eval_expression(rule.children[0])
            while condition:
                self.eval_block(rule.children[1])
                condition = self.eval_expression(rule.children[0])

        elif rule.data == "loop":
            while True:
                self.eval_block(rule.children[0])

        elif rule.data == "event":
            name = rule.children[0].value
            self.memory.set(name, rule.children[1], 'events')

        elif rule.data == "function":
            args = rule.children[1].children
            self.memory.set(rule.children[0].value, {
                'args': [
                    arg.value for arg in args if arg
                ],
                'body': rule.children[2]
            }, 'functions')

        elif rule.data == "expression":
            self.eval_expression(rule)

        elif rule.data == "return":
            return self.eval_expression(rule.children[0])