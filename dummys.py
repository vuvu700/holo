from typing import ContextManager, Callable, TypeVar, ParamSpec

_T = TypeVar("_T")
_P = ParamSpec("_P")

class DummyContext(ContextManager):
    def __enter__(self)->None: pass
    def __exit__(self, *_, **__)->None: pass


def dummyWrapper(func:"Callable[_P, _T]")->"Callable[_P, _T]":
    return func

def dummyWrapperOfWrapper(*_, **__)->"Callable[[Callable[_P, _T]], Callable[_P, _T]]":
    def dummyWrapper(func:"Callable[_P, _T]")->"Callable[_P, _T]":
        return func
    return dummyWrapper