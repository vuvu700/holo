from holo.__typing import (TextIO, TypeVar, Callable, ParamSpec, Literal)

from holo import print_exception
from holo.dummys import dummyWrapper, dummyWrapperOfWrapper

_T = TypeVar("_T")
_P = ParamSpec("_P")
_FailType = TypeVar("_FailType")
failObject = object()

def secureFunc(func:"Callable[_P, _T]", _failObject:"_FailType"=failObject, printErrors:bool=True)->"Callable[_P, _T|_FailType]":
    """avoid errors being raised\n
    if an error happend, print them if `printErrors`, and return `_failObject`"""
    def securedFunc(*args:_P.args, **kwargs:_P.kwargs)->"_T|_FailType":
        nonlocal func, printErrors, _failObject
        try: return func(*args, **kwargs)
        except Exception as err:
            if printErrors is True: print_exception(err)
            return _failObject
    return securedFunc


def secureWrapper(_failObject:"_FailType"=failObject, printErrors:bool=True)->"Callable[[Callable[_P, _T]], Callable[_P, _T|_FailType]]":
    """avoid errors being raised\n
    if an error happend, print them if `printErrors`, and return `_failObject`"""
    def internal(func:"Callable[_P, _T]")->"Callable[_P, _T|_FailType]":
        def securedFunc(*args:_P.args, **kwargs:_P.kwargs)->"_T|_FailType":
            nonlocal func, printErrors, _failObject
            try: return func(*args, **kwargs)
            except Exception as err:
                if printErrors is True: print_exception(err)
                return _failObject
        return securedFunc
    return internal


def printError(file:"TextIO|Literal['stderr', 'stdout']"="stdout")->"Callable[[Callable[_P, _T]], Callable[_P, _T]]":
    """avoid errors being raised\n
    if an error happend, print them if `printErrors`, and return `_failObject`"""
    def internal(func:"Callable[_P, _T]")->"Callable[_P, _T]":
        def newFunc(*args:_P.args, **kwargs:_P.kwargs)->"_T":
            nonlocal func
            try: return func(*args, **kwargs)
            except Exception as err:
                print_exception(err, file)
                raise
        return newFunc
    return internal


def printFuncName(func:"Callable[_P, _T]")->"Callable[_P, _T]":
    def newFunc(*args:_P.args, **kwargs:_P.kwargs)->"_T":
        nonlocal func
        print(func.__name__)
        return func(*args, **kwargs)
    return newFunc