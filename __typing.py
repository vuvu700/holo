import sys

from types import TracebackType, CodeType
from typing import (
    Iterable, Any, Sequence, TextIO,
    Generic, TypeVar, ContextManager,
    Generator, NamedTuple, Union, overload,
    Callable, Mapping, Sized, cast, NoReturn,
    DefaultDict, Iterator, Type, Container,
    TYPE_CHECKING, AbstractSet, MutableMapping,
    Tuple, List, Dict, Set, MutableSequence,
    OrderedDict, 
)
from typing import _GenericAlias # type: ignore
if sys.version_info < (3, 11):
    from typing_extensions import (
        Literal, Self, TypeVarTuple,
        Unpack, TypeGuard, LiteralString,
        ParamSpec, TypeAlias, Protocol,
        runtime_checkable, Concatenate,
        TypedDict, NotRequired,
    )
else: from typing import (
        Literal, Self, TypeVarTuple,
        Unpack, TypeGuard, LiteralString,
        ParamSpec, TypeAlias, Protocol,
        runtime_checkable, Concatenate,
        TypedDict, NotRequired,
    )

if TYPE_CHECKING:
    # => not executed
    from holo.protocols import SupportsPretty, SupportsStr, _T
    from holo.prettyFormats import _ObjectRepr


def assertIsinstance(type_:"type[_T]|tuple[type[_T], ...]", value:Any)->"_T":
    """assert that the type of value match the given type_\n
    also support `typing.Union`\n
    isn't suppressed with -OO"""
    if isinstance(type_, _GenericAlias) and getattr(type_, "__origin__") is Union:
        # => type_ is an Union
        type_ = cast("tuple[type[_T], ...]", getattr(type_, "__args__"))
        if None in type_:
            type_ = cast("tuple[type[_T], ...]", tuple(type(None) if t is None else t for t in type_))
    if not isinstance(value, type_):
        raise TypeError(f"the type if value: {type(value)} isn't an instance of type_={type_}")
    return value

def assertListSubType(subType:"type[_T]|tuple[type[_T], ...]", valuesList:"list[Any]")->"list[_T]":
    """return `valuesList` and assert that all its <value> respect assertIsinstance(subType, <value>)"""
    for subValue in valuesList: assertIsinstance(subType, subValue)
    return valuesList

def assertIterableSubType(subType:"type[_T]|tuple[type[_T], ...]", valuesList:"list[Any]")->"list[_T]":
    """return a list with the values in `valuesList` and assert that all its <value> respect assertIsinstance(subType, <value>)"""
    return [assertIsinstance(subType, subValue) for subValue in valuesList]

_PrettyPrintable = Union[
    "SupportsPretty", "_ObjectRepr", # specifics
    Mapping["_PrettyPrintable", "_PrettyPrintable"], NamedTuple, # mapping likes
    Sequence["_PrettyPrintable"], AbstractSet["_PrettyPrintable"], # Sequnce likes
    "SupportsStr", str, bytes, # others
]


def isNamedTuple(obj:object)->TypeGuard[NamedTuple]:
    """the isinstance(obj, NamedTuple) returns False for now, the morst accurate way to check it is this"""
    return isinstance(obj, NamedTuple) \
        or (isinstance(obj, tuple) and hasattr(obj, '_asdict') and hasattr(obj, '_fields'))


JsonTypeAlias = Union[None, bool, int, float, str, List["JsonTypeAlias"], Dict[str, "JsonTypeAlias"]]