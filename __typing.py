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
    OrderedDict, ClassVar,
)
from typing import _GenericAlias # type: ignore
if sys.version_info < (3, 11):
    from typing_extensions import (
        Literal, Self, TypeVarTuple,
        Unpack, TypeGuard, LiteralString,
        ParamSpec, TypeAlias, Protocol,
        runtime_checkable, Concatenate,
        TypedDict, NotRequired, get_args,
        override, get_origin,
    )
else: from typing import (
        Literal, Self, TypeVarTuple,
        Unpack, TypeGuard, LiteralString,
        ParamSpec, TypeAlias, Protocol,
        runtime_checkable, Concatenate,
        TypedDict, NotRequired, get_args,
        override, get_origin,
    )

if TYPE_CHECKING:
    # => not executed
    from holo.protocols import SupportsPretty, SupportsStr, _T
    from holo.prettyFormats import _ObjectRepr

# TODO
'''
def typeCheck(type_:"type[_T]|tuple[type[_T], ...]", value:Any)->"TypeGuard[_T]":
    """intensive type checking, will performe in depth checks (not meant for speed, meant for accuracy)"""
    if isinstance(type_, tuple):
        return any(__internal_typeCheck(type_=subType, value=value) for subType in type_)
    return __internal_typeCheck(type_, value)

def foo(a:Any):
    if typeCheck(list[Union[int, float]], a):
        ...

def __internal_typeCheck(type_:"type[_T]", value:Any)->"TypeGuard[_T]":
    """internal function for typeCheck"""
    if type_ == None: return value is None
    if type_ == NamedTuple: 
        return isNamedTuple(value)
    if isinstance(type_, _GenericAlias) and getattr(type_, "__origin__") is Union:
        # => type_ is an Union
        types_ = cast("tuple[type[_T], ...]", getattr(type_, "__args__"))
        if None in type_:
            type_ = cast("tuple[type[_T], ...]", tuple(type(None) if t is None else t for t in type_))
    return isinstance()
'''


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

def assertIterableSubType(subType:"type[_T]|tuple[type[_T], ...]", valuesList:"Iterable[Any]")->"list[_T]":
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
    return isinstance(obj, tuple) \
        and all(hasattr(obj, field) for field in 
                ['_asdict', '_field_defaults', '_fields', '_make', '_replace'])


JsonTypeAlias = Union[None, bool, int, float, str, List["JsonTypeAlias"], Dict[str, "JsonTypeAlias"]]




### to make some classes final or partialy final

class FinalClass():
    """make all attr of the sub classes final"""
    def __init_subclass__(cls, allow_setattr_overload:bool=False) -> None:
        if allow_setattr_overload: return None # => no checks to do
        if getattr(cls, "__setattr__") is not FinalClass.__setattr__:
            # => redefining __setattr__ in cls
            raise ValueError(f"the sub class: {cls} of {FinalClass} has modified __setattr__")
        # => all good
                    
    def __setattr__(self, name: str, value: Any) -> None:
        if hasattr(self, name):
            raise AttributeError(f"Trying to set twice a the final attribute: {name}")
        print(f"setting {name} to {value}")
        super().__setattr__(name, value)




class PartialyFinalClass():
    """make all the attr in __finals__ (must be setted) of the sub classes final\n
     will add in the class.__finals__ all the attrs in the __finals__ of its base classes (they must Inherit from this protocol)"""
    __finals__: "ClassVar[set[str]]"
    
    def __init_subclass__(cls, allow_setattr_overload:bool=False) -> None:
        if allow_setattr_overload is False:
            # => check __setattr__
            if getattr(cls, "__setattr__") is not PartialyFinalClass.__setattr__:
                # => redefining __setattr__ in cls
                raise ValueError(f"the sub class: {cls} of {PartialyFinalClass} has modified __setattr__")
        # => __setattr_ is fine
        if ("__finals__" in cls.__dict__.keys()) is False:
            raise AttributeError(f"couldn't initialize the class: {cls}: it don't implement correctly the partialy final protocol, the class attribut: '__finals__' is missing")
        # => the class is valide !
        # replace the names with the true name of each atrr
        for name in cls.__finals__:
            attrName = cls.__getAttName(name)
            if attrName != name: # => wrong name in __finals__
                cls.__finals__.remove(name)
                cls.__finals__.add(attrName)
            # else: => alredy in __finals__
        # add the names from the base classes
        cls.__addFinalAttrs_fromBases(cls.__bases__)
    
    @classmethod
    def __addFinalAttrs_fromBases(cls, bases:"tuple[type[PartialyFinalClass], ...]")->None:
        for baseClasse in bases:
            if baseClasse is PartialyFinalClass: continue
            if issubclass(baseClasse, PartialyFinalClass) is False:
                continue
            for attrName in baseClasse.__finals__:
                if attrName in cls.__finals__:
                    raise ValueError(f"can't add the final attribut: {repr(attrName)} from {baseClasse} twice on {cls}, it can be a collision betwin the __finals__ of its base classes")
                cls.__finals__.add(attrName)
            cls.__addFinalAttrs_fromBases(baseClasse.__bases__)
    
    @classmethod
    def __getAttName(cls, name:str)->str:
        if name.startswith("__") and not name.endswith("__"):
            # => is a private attr
            return f"_{cls.__name__}{name}"
        return name
    
    def __setattr__(self, name: str, value: Any) -> None:
        # print(f"called {self}.__settattr__({repr(name)}, {value})")
        if (name in self.__class__.__finals__) and hasattr(self, name):
            raise AttributeError(f"Trying to set twice a the final attribute: {name}")
        super().__setattr__(name, value)



class FreezableClass():
    """make the sub classes frozen\n
    you will initialize the frozen state with:\n
        - super().__init__() => set to the default state (given to the class, if its None, __init__ do nothing)\n
        - self._freez() / self._unfreez() will also set it to the desired state"""
    __slots__ = ("__frozen", )
    __initialFreez: "ClassVar[bool|None]"
    def __init_subclass__(cls, initialFreezState:"bool|None", allow_setattr_overload:bool=False) -> None:
        if (allow_setattr_overload is False) and (getattr(cls, "__setattr__") is not FreezableClass.__setattr__):
            # => redefining __setattr__ in cls
            raise ValueError(f"the sub class: {cls} of {FreezableClass} has modified __setattr__")
        cls.__initialFreez = initialFreezState
        
    def __init__(self) -> None:
        if self.__initialFreez is True: self._freeze()
        elif self.__initialFreez is False: self._unfreeze()
        # else => unsetted
        super().__init__()

    def __setattr__(self, attr:str, value:Any):
       if self.__frozen is True:
            raise AttributeError(f"Trying to set attribute on a frozen instance")
       return super().__setattr__(attr, value)
    
    def _freeze(self)->None:
        object.__setattr__(self, f"_{FreezableClass.__name__}__frozen", True)
    def _unfreeze(self)->None:
        object.__setattr__(self, f"_{FreezableClass.__name__}__frozen", False)

