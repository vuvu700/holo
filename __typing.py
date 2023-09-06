import sys

from typing import (
    Iterable, Any, Sequence, TextIO,
    Generic, TypeVar, ContextManager,
    Generator, NamedTuple, Union, overload,
    Callable, Mapping, Sized, cast, NoReturn,
    DefaultDict, Iterator, Type, Container,
    TYPE_CHECKING,
)
if sys.version_info < (3, 11):
    from typing_extensions import (
        Literal, Self, TypeVarTuple,
        Unpack, TypeGuard, LiteralString,
        ParamSpec, TypeAlias, Protocol,
        runtime_checkable,
    )
else: from typing import (
        Literal, Self, TypeVarTuple,
        Unpack, TypeGuard, LiteralString,
        ParamSpec, TypeAlias, Protocol,
        runtime_checkable,
    )


## types related to pretty format

class _Pretty_CompactRules(NamedTuple):
    newLine:bool; spacing:bool; indent:bool

class _Pretty_Delimiter(NamedTuple):
    open:str; close:str