from .__typing import (
    NamedTuple, Generic, overload, Callable,
    Iterable, Literal, LiteralString, TypeAlias,
    Union, Tuple, TypeVar, Unpack, TypeVarTuple,
)


from .protocols import Protocol, _T, _T_co

### types


_TupleType = TypeVarTuple("_TupleType")
_T_ArgName = TypeVar("_T_ArgName", bound=LiteralString)

_AmountRange:TypeAlias = Tuple["int", "int|None"]
"""tuple(nbMin, nbMax), None => not bounded"""
_AmountAlias:TypeAlias = Literal['*', '+', '?']
_Amounts:TypeAlias = Union[int, _AmountRange]
"""can be a precise number or a range"""
_AmountsExt:TypeAlias = Union[_Amounts, _AmountAlias]
"""can be a precise number or a range"""
_AmountAlias_to_Ranges:"dict[_AmountAlias, _AmountRange]" = {
    "*": (0, None), "+": (1, None), "?": (0, 1)}
"""convertion of _AmountAlias to _AmountRange"""
_Expr:TypeAlias = Union[str, "ComplexExpr", "ExprRef"]

### clases

class SyntaxTreeDefArg():
    def __init__(self,
            amount:"_AmountsExt", syntaxType:"SyntaxTreeType", argName:"str")->None:
        self.amount:"_Amounts" = _AmountsExt_to_Amounts(amount)
        self.syntaxType:"SyntaxTreeType" = syntaxType
        self.argName:"str" = argName



class SyntaxTreeType():
    def __init__(self, name:str, args:"list[SyntaxTreeDefArg]|None", expr:"Expr") -> None:
        self.name:str = name
        self.args:"list[SyntaxTreeDefArg]|None" = args
        self.expr:"Expr" = expr

class ComplexExpr():
    ... # TODO
    # ops priority: (a | b & c ** d) == (a | (b & (c ** d)))
    def __or__(self, __other:"_Expr")->"ComplexExpr": ... # TODO
    def __ror__(self, __other:"_Expr")->"ComplexExpr": ... # TODO
    def __and__(self, __other:"_Expr")->"ComplexExpr": ... # TODO
    def __rand__(self, __other:"_Expr")->"ComplexExpr": ... # TODO
    def __pow__(self, __other:"_AmountsExt")->"IterExpr":
        return IterExpr(self, amount=__other)

class Expr(ComplexExpr):
    def __init__(self, __expr:"_Expr", *, name:"str|None"=None) -> None:
        ... # TODO

class ExprRef(ComplexExpr):
    def __init__(self, *, name:str) -> None:
        ... # TODO

class IterExpr(ComplexExpr):
    def __init__(self, __expr:"_Expr", *, amount:"_AmountsExt") -> None:
        ... # TODO

class OptionalExpr(IterExpr):
    def __init__(self, __expr:"_Expr") -> None:
        super().__init__(__expr, amount="?")

### funcs

def _AmountsExt_to_Amounts(amount:"_AmountsExt")->"_Amounts":
    if isinstance(amount, (int, tuple)): # => _Amounts
        return amount
    elif isinstance(amount, str): # => _AmountAlias
        return _AmountAlias_to_Ranges[amount]
    else: raise ValueError(f"unrecognised amount: {amount}")

### tests


# assignment_expression ::=  [identifier ":="] expression
expression = Expr("...", name="expr")
identifier = Expr("...", name="identifier")
assignment_expression = Expr(
    OptionalExpr(identifier & ":=") & expression,
    name="assignment_expression")

# conditional_expression ::=  or_test ["if" or_test "else" expression]
# expression             ::=  conditional_expression | lambda_expr
or_test = Expr("...", name="or_test")
lambda_expr = Expr("...", name="lambda_expr")
conditional_expression = Expr(
    or_test & OptionalExpr(" if " & or_test & " else" & ExprRef(name="expression")),
    name="conditional_expression")
expression = Expr(
    conditional_expression | lambda_expr,
    name="expression")


class ProtocolAST(Protocol):
    __expr__:"ComplexExpr"



class Expression(ProtocolAST):
    __expr__ = expression

class Conditional_Expression(ProtocolAST):
    __expr__ = (conditional_expression | lambda_expr)