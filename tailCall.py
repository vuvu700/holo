from typing import (Generic, TypeVar, Callable)
import sys
if sys.version_info < (3, 11): from typing_extensions import ParamSpec, NoReturn
else: from typing import ParamSpec, NoReturn


_T = TypeVar("_T")
_P = ParamSpec("_P")

def nullFunc()->NoReturn:
    raise RuntimeError("shoudn't be called")

class TailCallOutput(Generic[_T]):
    __slots__ = ("func", "result", "combineFunc", "args", "kwargs")
    def __init__(self,
            func:"Callable[_P, TailCallOutput[_T]|NoReturn]", result:_T, combineFunc:"Callable[[_T, _T], _T]|None",
            *args:_P.args, **kwargs:_P.kwargs)->None:
        self.func = func
        self.result = result
        self.combineFunc = combineFunc
        self.args = args
        self.kwargs = kwargs

    def asTuple(self):
        return (self.func, self.result, self.combineFunc, self.args, self.kwargs)


def tailCallOptimize(funcToWrap:Callable[_P, TailCallOutput[_T]])->Callable[_P, _T]:
    def wrappedFunc(*originalArgs:_P.args, **originalKwargs:_P.kwargs)->_T:
        nonlocal funcToWrap
        (func, result, combineFunc, args, kwargs) = funcToWrap(*originalArgs, **originalKwargs).asTuple()
        while combineFunc is not None:
            (func, newResult, newCombineFunc, args, kwargs) = func(*args, **kwargs).asTuple()
            result = combineFunc(result, newResult)
            combineFunc = newCombineFunc
        return result
    return wrappedFunc


if __name__ == "__main__":

    def fact_normal(n:int)->int:
        return (1 if n <= 1 else n * fact_normal(n-1))

    def _fact_TCO(n:int)->"TailCallOutput[int]":
        if n <= 1:
            return TailCallOutput(nullFunc, 1, None)
        return TailCallOutput(_fact_TCO, n, (lambda new, old: new * old), n=n-1)
    fact_TCO = tailCallOptimize(_fact_TCO)


    def fact_iter(n:int)->int:
        res = n
        while n > 1:
            res *= n-1
            n -= 1
        return res





