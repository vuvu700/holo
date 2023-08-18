import sys

from typing import (
    Iterable, Any, Sequence, TextIO,
    Generic, TypeVar, ContextManager,
    Generator, NamedTuple, Union, overload,
    Callable, Mapping, Sized, cast, NoReturn,
    DefaultDict,
)
if sys.version_info < (3, 11):
    from typing_extensions import (
        Literal, Self, TypeVarTuple,
        Unpack, TypeGuard, LiteralString,
        ParamSpec,
    )
else: from typing import (
        Literal, Self, TypeVarTuple,
        Unpack, TypeGuard, LiteralString,
        ParamSpec
    )