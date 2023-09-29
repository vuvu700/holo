import sys

from types import TracebackType
from typing import (
    Iterable, Any, Sequence, TextIO,
    Generic, TypeVar, ContextManager,
    Generator, NamedTuple, Union, overload,
    Callable, Mapping, Sized, cast, NoReturn,
    DefaultDict, Iterator, Type, Container,
    TYPE_CHECKING, AbstractSet, MutableMapping,
    Tuple, List, Dict, Set, MutableSequence,
)
if sys.version_info < (3, 11):
    from typing_extensions import (
        Literal, Self, TypeVarTuple,
        Unpack, TypeGuard, LiteralString,
        ParamSpec, TypeAlias, Protocol,
        runtime_checkable, Concatenate,
    )
else: from typing import (
        Literal, Self, TypeVarTuple,
        Unpack, TypeGuard, LiteralString,
        ParamSpec, TypeAlias, Protocol,
        runtime_checkable, Concatenate,
    )

if TYPE_CHECKING:
    # => not executed
    from holo.protocols import SupportsPretty, SupportsStr
    from holo.prettyFormats import _ObjectRepr


_PrettyPrintable = Union[
    "SupportsPretty", "_ObjectRepr", # specifics
    Mapping["_PrettyPrintable", "_PrettyPrintable"], NamedTuple, # mapping likes
    Sequence["_PrettyPrintable"], AbstractSet["_PrettyPrintable"], # Sequnce likes
    "SupportsStr", str, bytes, # others
]