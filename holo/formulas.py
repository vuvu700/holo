import operator


from .__typing import (
    NamedTuple, _PrettyPrintable, Literal,
    OrderedDict, assertListSubType, assertIsinstance,
    Union, Any, overload, LiteralString, TypeVar,
    Generic, get_args, Callable, NoReturn,
)
from .protocols import Protocol, runtime_checkable
from .pointers import Pointer
from .prettyFormats import (
    prettyPrint, prettyfyNamedTuple, 
    _ObjectRepr, _Pretty_CompactRules,
)

_Ops = Literal["+", "-", "*", "/", "//", "%", "**", "@", ">>", "<<"]
_UnaryOps = Literal["+", "-", "~"]
Ops_to_func:"dict[_Ops, Callable[[Variable|Any, Variable|Any], Any]]" = {
    "+":operator.add, "-":operator.sub, "*":operator.mul, "/":operator.truediv,
    "//":operator.floordiv, "%":operator.mod, "**":operator.pow, "@":operator.matmul,
    ">>":operator.rshift, "<<":operator.lshift,
}
UnaryOps_to_func:"dict[_UnaryOps, Callable[[Variable|Any], Any]]" = {
    "+":operator.pos, "-":operator.neg, "~":operator.invert,
}
assert len(set(get_args(_Ops)).symmetric_difference(Ops_to_func.keys()) ) == 0, \
    KeyError(f"missing/too much keys in Ops_to_func")
assert len(set(get_args(_UnaryOps)).symmetric_difference(UnaryOps_to_func.keys()) ) == 0, \
    KeyError(f"missing/too much keys in UnaryOps_to_func")


class EvalError(Exception): ...

class Missing():
    def __str__(self)->str:
        return "missing"
    def __repr__(self)->str:
        return f"{self.__class__.__name__}()"
missing = Missing()


@runtime_checkable
class SupportsEvaluate(Protocol):
    def evaluate(self, useValue:"dict[str, Any]", keepMissingVariables:bool=True)->Any:
        ...

class FormulaBase():
    # ops
    def __add__(self, other:Any)->"Operation": return Operation(self, "+", other)
    def __sub__(self, other:Any)->"Operation": return Operation(self, "-", other)
    def __mul__(self, other:Any)->"Operation": return Operation(self, "*", other)
    def __truediv__(self, other:Any)->"Operation": return Operation(self, "/", other)
    def __floordiv__(self, other:Any)->"Operation": return Operation(self, "//", other)
    def __mod__(self, other:Any)->"Operation": return Operation(self, "%", other)
    def __pow__(self, other:Any)->"Operation": return Operation(self, "**", other)
    def __matmul__(self, other:Any)->"Operation": return Operation(self, "@", other)
    def __rshift__(self, other:Any)->"Operation": return Operation(self, ">>", other)
    def __lshift__(self, other:Any)->"Operation": return Operation(self, "<<", other)
    
    # r-ops
    def __radd__(self, other:Any)->"Operation": return Operation(other, "+", self)
    def __rsub__(self, other:Any)->"Operation": return Operation(other, "-", self)
    def __rmul__(self, other:Any)->"Operation": return Operation(other, "*", self)
    def __rtruediv__(self, other:Any)->"Operation": return Operation(other, "/", self)
    def __rfloordiv__(self, other:Any)->"Operation": return Operation(other, "//", self)
    def __rmod__(self, other:Any)->"Operation": return Operation(other, "%", self)
    def __rpow__(self, other:Any)->"Operation": return Operation(other, "**", self)
    def __rmatmul__(self, other:Any)->"Operation": return Operation(other, "@", self)
    def __rrshift__(self, other:Any)->"Operation": return Operation(other, ">>", self)
    def __rlshift__(self, other:Any)->"Operation": return Operation(other, "<<", self)
    
    # unary ops
    def __pos__(self)->"UnaryOperation": return UnaryOperation("+", self)
    def __neg__(self)->"UnaryOperation": return UnaryOperation("-", self)
    def __invert__(self)->"UnaryOperation": return UnaryOperation("~", self)


_T_VarName = TypeVar("_T_VarName", LiteralString, str)
class Variable(Generic[_T_VarName], FormulaBase, SupportsEvaluate):
    usedNames:"set[str]" = set()
    __duplicatesAllowed:bool = True
    
    @classmethod
    def allowDuplicatedValiable(cls)->None:
        cls.__duplicatesAllowed = True
    @classmethod
    def blockDuplicatedValiable(cls)->None:
        cls.__duplicatesAllowed = False
    
    
    @overload
    def __init__(self, name:_T_VarName)->None: ...
    @overload
    def __init__(self, name:_T_VarName, value:Any)->None: ...
    def __init__(self, name:_T_VarName, value:"Missing|FormulaBase|Any"=missing)->None:
        self.name = name
        self.value:"Missing|FormulaBase|Any" = value
        
    
    @property
    def name(self)->_T_VarName:
        return self.__name
    @name.setter
    def name(self, newName:_T_VarName)->None:
        if (self.__duplicatesAllowed is False) and (newName in self.usedNames):
            raise NameError(f"the valiable name: {newName} is alredy used")
        self.__name:_T_VarName = newName
    
    def hasValue(self)->bool:
        return self.value is missing
    
    def __pretty__(self, *_, **__):
        kwargs:"dict[str, _PrettyPrintable]" = {}
        if self.value is not missing:
            kwargs["fixed to"] = self.value
        return _ObjectRepr(
            className=self.__class__.__name__,
            args=(self.name, ), kwargs=kwargs,
        )
    
    def __str__(self) -> str:
        if self.value is missing:
            return self.name
        # => has a value
        return f"({self.name} := {self.value})"
    __repr__ = __str__
        
    
    def evaluate(self, useValue:"dict[str, Any]", keepMissingVariables:bool=True)->Any:
        value = useValue.get(self.name, missing)
        if value is not missing: # => value was given
            return value
        # => value not given => compute the value
        if self.value is missing:
            # => has no value to give or to compute
            if keepMissingVariables is True:
                return self
            else: raise EvalError(f"the variable named: {self.name} don't have a value to evaluate")
        # => has a value to give or to compute
        if isinstance(self.value, NEEDS_PARENTHHESIS):
            # => need further evaluation
            return self.value.evaluate(useValue)
        # => value is a fixed value
        return self.value
        
            
class Operation(FormulaBase, SupportsEvaluate):
    def __init__(self, leftMember:"SupportsEvaluate|Any", op:"_Ops", rightMember:"SupportsEvaluate|Any")->None:
        self.leftMember:"SupportsEvaluate|Any" = leftMember
        self.op:"_Ops" = op
        self.rightMember:"SupportsEvaluate|Any" = rightMember
    
    def evaluate(self, useValue:"dict[str, Any]", keepMissingVariables:bool=True)->Any:
        leftMember = self.leftMember
        if isinstance(leftMember, SupportsEvaluate):
            leftMember = leftMember.evaluate(useValue=useValue, keepMissingVariables=keepMissingVariables)
        rightMember = self.rightMember
        if isinstance(rightMember, SupportsEvaluate):
            rightMember = rightMember.evaluate(useValue=useValue, keepMissingVariables=keepMissingVariables)
        return Ops_to_func[self.op](leftMember, rightMember)
    
    def __pretty__(self, *_, **__):
        return _ObjectRepr(
            className=self.__class__.__name__,
            args=(self.leftMember, self.op, self.rightMember),
            kwargs=dict(),
        )    

    def __str__(self) -> str:
        leftMember = self.leftMember
        if isinstance(leftMember, NEEDS_PARENTHHESIS):
            leftMember = f"({leftMember})"
        rightMember = self.rightMember
        if isinstance(rightMember, NEEDS_PARENTHHESIS):
            rightMember = f"({rightMember})"
        op = self.op
        if op != "**": op = f" {op} "
        return f"{leftMember}{op}{rightMember}"
    __repr__ = __str__

class UnaryOperation(FormulaBase, SupportsEvaluate):
    def __init__(self, op:"_UnaryOps", member:"Variable|Any|Missing"=missing)->None:
        self.op:"_UnaryOps" = op
        self.member:"Variable|Any|Missing" = member
    
    def evaluate(self, useValue:"dict[str, Any]", keepMissingVariables:bool=True)->Any:
        member = self.member
        if isinstance(member, SupportsEvaluate):
            member = member.evaluate(useValue=useValue, keepMissingVariables=keepMissingVariables)
        return UnaryOps_to_func[self.op](member)
    
    def __pretty__(self, *_, **__):
        return _ObjectRepr(
            className=self.__class__.__name__,
            args=(self.op, self.member),
            kwargs=dict(),
        )
    
    def __str__(self) -> str:
        member = self.member
        if isinstance(member, NEEDS_PARENTHHESIS):
            member = f"({member})"
        return f"{self.op}{member}"
    __repr__ = __str__




class Function(FormulaBase, SupportsEvaluate):
    #def __init__(self, inputs:"list[Variable]", formula:"FormulaBase|Callable[[list[Any]], Any]|Any")->None:
    def __init__(self, inputs:"list[Variable]", formula:"FormulaBase|Any")->None:
        self.inputs:"list[Variable]" = inputs
        self.formula:"FormulaBase|Any" = formula
    
    def __call__(self, *values:Any)->Any:
        return self.evaluate(
            useValue={var.name:value for var, value in zip(self.inputs, values)},
            keepMissingVariables=True,
        )
        
    def evaluate(self, useValue:"dict[str, Any]", keepMissingVariables:bool=True)->Any:
        if isinstance(self.formula, SupportsEvaluate):
            return self.formula.evaluate(useValue, keepMissingVariables)
        #elif isinstance(self.formula, Callable):
        #    return self.formula([useValue[var.name] for var in self.inputs]) # TODO
        # => not evaluable or callable
        return self.formula

    def __pretty__(self, *_, **__):
        return _ObjectRepr(
            className=self.__class__.__name__,
            args=(self.inputs, self.formula), kwargs={}, 
            separator=" -> ",
        )
    
    def __str__(self) -> str:
        return f"({[var.name for var in self.inputs]} -> {self.formula})"
    __repr__ = __str__


# typing const
NEEDS_PARENTHHESIS = (Operation, UnaryOperation)
"""the expressions that needs parenthesis with __str/repr__, to avoid mistakes with priorities"""



