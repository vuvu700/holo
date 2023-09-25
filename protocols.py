from collections.abc import (
    Awaitable, Iterable, Set as AbstractSet, 
    Sized, Container, Iterator, Collection
)
from holo.__typing import (
    Protocol, TypeVar, Any, TypeAlias, Union, runtime_checkable,
    Mapping, Sequence, NamedTuple, TYPE_CHECKING, overload, Self,
    _PrettyPrintable, TracebackType, Callable, Concatenate,
)

if TYPE_CHECKING:
    from holo.prettyFormats import _Pretty_CompactRules

# some code extracted from /*vscode-pylance*/dist/typeshed_fallback/stdlib/_typeshed/__init__.py

## generic type vars
_KT = TypeVar("_KT")
_KT_co = TypeVar("_KT_co", covariant=True)
_KT_contra = TypeVar("_KT_contra", contravariant=True)
_VT = TypeVar("_VT")
_VT_co = TypeVar("_VT_co", covariant=True)
_T = TypeVar("_T")
_T2 = TypeVar("_T2"); _T3 = TypeVar("_T3"); _T3 = TypeVar("_T3")
_T_co = TypeVar("_T_co", covariant=True)
_T_contra = TypeVar("_T_contra", contravariant=True)

## bounded type vars
_T_co_Sized = TypeVar("_T_co_Sized", bound=Sized, covariant=True)
_T_contra_Sized = TypeVar("_T_contra_Sized", bound=Sized, contravariant=True)



# stable
class IdentityFunction(Protocol):
    def __call__(self, __x: _T) -> _T: ...

# stable
class SupportsNext(Protocol[_T_co]):
    def __next__(self) -> _T_co: ...

# stable
class SupportsAnext(Protocol[_T_co]):
    def __anext__(self) -> "Awaitable[_T_co]": ...

@runtime_checkable
class SupportsContext(Protocol):
    def __enter__(self)->Self: ...
    __exit__:"Callable[Concatenate[Self, ...], None]"


# Comparison protocols

class SupportsDunderLT(Protocol[_T_contra]):
    def __lt__(self, __other: _T_contra) -> bool: ...

class SupportsDunderGT(Protocol[_T_contra]):
    def __gt__(self, __other: _T_contra) -> bool: ...

class SupportsDunderLE(Protocol[_T_contra]):
    def __le__(self, __other: _T_contra) -> bool: ...

class SupportsDunderGE(Protocol[_T_contra]):
    def __ge__(self, __other: _T_contra) -> bool: ...

class SupportsAllComparisons(
    SupportsDunderLT[Any], SupportsDunderGT[Any], SupportsDunderLE[Any], SupportsDunderGE[Any], Protocol
): ...

SupportsRichComparison: TypeAlias = Union[SupportsDunderLT[Any], SupportsDunderGT[Any]]
SupportsRichComparisonT = TypeVar("SupportsRichComparisonT", bound=SupportsRichComparison)




# Dunder protocols

class SupportsAdd(Protocol[_T_contra, _T_co]):
    def __add__(self, __x: _T_contra) -> _T_co: ...

class SupportsRAdd(Protocol[_T_contra, _T_co]):
    def __radd__(self, __x: _T_contra) -> _T_co: ...

class SupportsSub(Protocol[_T_contra, _T_co]):
    def __sub__(self, __x: _T_contra) -> _T_co: ...

class SupportsRSub(Protocol[_T_contra, _T_co]):
    def __rsub__(self, __x: _T_contra) -> _T_co: ...

class SupportsDivMod(Protocol[_T_contra, _T_co]):
    def __divmod__(self, __other: _T_contra) -> _T_co: ...

class SupportsRDivMod(Protocol[_T_contra, _T_co]):
    def __rdivmod__(self, __other: _T_contra) -> _T_co: ...

class SupportsDivModRec(Protocol[_T_contra, _T_co]):
    """this protocol is meant for divmod_rec() @ holo.calc"""
    def __divmod__(
        self, __other: _T_contra
        ) -> "tuple[_T_co, SupportsDivModRec[_T_contra, _T_co]]": ...




# This protocol is generic over the iterator type, while Iterable is
# generic over the type that is iterated over.
class SupportsIter(Protocol[_T_co]):
    def __iter__(self) -> _T_co: ...

class SupportsIterable(SupportsIter[_T_co], Protocol):
    def __iter__(self)->"Iterator[_T_co]": ...

# This protocol is generic over the iterator type, while AsyncIterable is
# generic over the type that is iterated over.
class SupportsAiter(Protocol[_T_co]):
    def __aiter__(self) -> _T_co: ...

class SupportsLenAndGetItem(Protocol[_T_co]):
    def __len__(self) -> int: ...
    def __getitem__(self, __k: int) -> _T_co: ...

class SupportsTrunc(Protocol):
    def __trunc__(self) -> int: ...



# Mapping-like protocols

# stable
class SupportsItems(Protocol[_KT_co, _VT_co]):
    def items(self) ->"AbstractSet[tuple[_KT_co, _VT_co]]": ...

# stable
class SupportsKeysAndGetItem(Protocol[_KT, _VT_co]):
    def keys(self) -> "Iterable[_KT]": ...
    def __getitem__(self, __key: _KT) -> _VT_co: ...

# stable
class SupportsGetItem(Protocol[_KT_contra, _VT_co]):
    def __contains__(self, __x: Any) -> bool: ...
    def __getitem__(self, __key: _KT_contra) -> _VT_co: ...

# stable
class SupportsItemAccess(SupportsGetItem[_KT_contra, _VT], Protocol[_KT_contra, _VT]):
    def __setitem__(self, __key: _KT_contra, __value: _VT) -> None: ...
    def __delitem__(self, __key: _KT_contra) -> None: ...

@runtime_checkable
class SupportsReduce(Protocol):
    def __reduce__(self) -> "str | tuple[Any, ...]":
        ...



# files like protocols

class SupportsRead(Protocol[_T_co_Sized]):
    def read(self, __size:"int|None"=...)->_T_co_Sized: ...

class SupportsFileRead(SupportsContext, Protocol[_T_co_Sized]):
    def read(self, __size:"int|None"=...)->_T_co_Sized: ...
    def seek(self, __offset:int, __whence:int=...,)->_T_co_Sized: ...
    def close(self)->None: ...

class SupportsPickleRead(SupportsContext, Protocol):
    def read(self, __n:int)->bytes: ...
    def readline(self)->bytes: ...
    def close(self)->None: ...

class SupportsWrite(Protocol[_T_contra_Sized]):
    def write(self, __buffer: _T_contra_Sized) -> int: ...

class SupportsFileWrite(SupportsContext, Protocol[_T_contra_Sized]):
    def write(self, __buffer: _T_contra_Sized) -> int: ...
    def close(self)->None: ...


# pretty format protocols

@runtime_checkable
class SupportsStr(Protocol):
    """(runtime checkable)"""
    def __str__(self)->str:
        ...
        
@runtime_checkable
class SupportsPretty(Protocol):
    """(runtime checkable)"""
    @overload
    def __pretty__(self, *args, **kwargs)->"_PrettyPrintable": ...
    @overload
    def __pretty__(self, compactRules:"_Pretty_CompactRules|None"=None)->"_PrettyPrintable": ...
    def __pretty__(self, compactRules:"_Pretty_CompactRules|None"=None, *args, **kwargs)->"_PrettyPrintable":
        """return the new object to pretty print\n
        `compactRules`: None when not specified"""
        ...
