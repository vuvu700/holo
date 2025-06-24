import sys

from types import (
    TracebackType, CodeType, MethodType,
    FrameType, 
)
from typing import (
    Iterable, Any, Sequence, TextIO, BinaryIO,
    Generic, TypeVar, ContextManager,
    Generator, NamedTuple, Union, overload,
    Callable, Mapping, Sized, cast, NoReturn,
    DefaultDict, Iterator, Type, Container,
    TYPE_CHECKING, AbstractSet, MutableMapping,
    Tuple, List, Dict, Set, MutableSequence,
    OrderedDict, ClassVar, Optional, ForwardRef, )
from typing import _GenericAlias # type: ignore

if sys.version_info < (3, 12):
    from typing_extensions import (
        Literal, Self, TypeVarTuple,
        Unpack, TypeGuard, LiteralString,
        ParamSpec, TypeAlias, Protocol,
        runtime_checkable, Concatenate,
        TypedDict, NotRequired, get_args,
        override, get_origin, Required,
        TypeAliasType, Never, )
else: from typing import (
        Literal, Self, TypeVarTuple,
        Unpack, TypeGuard, LiteralString,
        ParamSpec, TypeAlias, Protocol,
        runtime_checkable, Concatenate,
        TypedDict, NotRequired, get_args,
        override, get_origin, Required,
        TypeAliasType, Never, )


if TYPE_CHECKING:
    # => not executed
    print("hello")
    from holo.protocols import SupportsPretty, SupportsStr, ClassFactoryProtocol, _T
    from holo.prettyFormats import _ObjectRepr


_T_ClassFactory = TypeVar("_T_ClassFactory", bound="type[ClassFactory]")

_T_LiteralString = TypeVar("_T_LiteralString", bound=LiteralString)
def get_args_LiteralString(t:"type[_T_LiteralString]")->"tuple[_T_LiteralString, ...]":
    return get_args(t)

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
    if get_origin(type_) is Union:
        # => type_ is an Union
        type_ = cast("tuple[type[_T], ...]", get_args(type_))
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



def getLiteralArgs(t)->"set": # TODO: seems it can't be typed ?!
    """return a set containing all the literals in this type (can be recursive unions of literals)"""
    origin = get_origin(t)
    args = set()
    if origin == Literal:
        for arg in get_args(t):
            if get_origin(arg) == None:
                args.add(arg)
            else: # => is a generic alias
                args.update(getLiteralArgs(arg))
    elif origin == Union:
        for subT in get_args(t):
            args.update(getLiteralArgs(subT))
    else: raise TypeError(f"invalide origin for t: {origin}")
    return args

#_convTrainSingleMetrics = Literal["nbConvStep_train", "nbConvStep_val"]
#res = getLiteralArgs(_convTrainSingleMetrics)


def isNamedTuple(obj:object)->TypeGuard[NamedTuple]:
    """the isinstance(obj, NamedTuple) returns False for now, the morst accurate way to check it is this"""
    return isinstance(obj, tuple) \
        and all(hasattr(obj, field) for field in 
                ['_asdict', '_field_defaults', '_fields', '_make', '_replace'])


JsonTypeAlias = Union[None, bool, int, float, str, List["JsonTypeAlias"], Dict[str, "JsonTypeAlias"]]


def getSubclasses(t:"type[_T]")->"Generator[type[_T], None, None]":
    """yield all the type that are subclasses of `t` (including t, yielded first)"""
    yield t
    for subT in type.__subclasses__(t): # doing so also handle (t is type)
        yield from getSubclasses(subT)



### to make some classes final or partialy final

def isPrivateAttr(name:str)->bool:
    return (name.startswith("__") and not name.endswith("__"))

def getAttrName(cls:type, name:str)->str:
    return (f"_{cls.__name__}{name}" if isPrivateAttr(name) else name)

def _ownAttr(cls:type, attrName:str)->bool:
    """return whether a `attrName` was defined on this class (False if inherited)\n
    /!\\ BIG WARNING it "may" have side effects since it try to del the attr and put it back (use type. methodes)"""
    try: 
        tmp = object.__getattribute__(cls, attrName)
        type.__delattr__(cls, attrName)
    except AttributeError: 
        return False # => don't has the attr or don't own it
    # => own the attr | put the value back where it come from ^^
    type.__setattr__(cls, attrName, tmp)
    return True

def set_classMethode(cls:type, baseFunction:"Callable[Concatenate[type, ...], Any]")->None:
    temporary_type = type("temporary_type", tuple(), {baseFunction.__name__: classmethod(baseFunction)})
    type.__setattr__(cls, baseFunction.__name__, object.__getattribute__(temporary_type, baseFunction.__name__))




class ClassFactory():
    """notify to other ClassFactory to call __init_subclass__ on it"""
    __slots__ = ()
    
    __registered_factories: "set[type[ClassFactoryProtocol]]" = set()
    __registered_subclasses: "DefaultDict[type[ClassFactory], set[type[ClassFactoryProtocol]]]" = DefaultDict(set)
    """dict[subclass -> factories (they are stored in ClassFactory.__registered_factories)]"""
    __NAME_initFactory: str = "_ClassFactory__initSubclass"
    
    def __init_subclass__(cls) -> None:
        ClassFactory.__manual_init_subclass__(cls)

    @staticmethod
    def __manual_init_subclass__(subClass:"type[ClassFactory]")->None:
        # assert the sub class is a valide ClassFactory
        factory = ClassFactory.__validateFactory(subClass)
        # => a new ClassFactory 
        ClassFactory.__registered_factories.add(factory)
        ClassFactory.__registered_subclasses[subClass].add(factory)
        return None


    @staticmethod
    def __validateFactory(subClass:"type[ClassFactory]")->"type[ClassFactoryProtocol]":
        if not issubclass(subClass, ClassFactory):
            raise TypeError(f"the sub class: {subClass} must be a sub class of {ClassFactory}")
        if (not _ownAttr(subClass, ClassFactory.__NAME_initFactory)) \
                or (not callable(getattr(subClass, ClassFactory.__NAME_initFactory))):
            raise AttributeError(f"the sub class: {subClass} must define a {ClassFactory.__NAME_initFactory} static methode")
        if not _ownAttr(subClass, "__slots__"):
            raise AttributeError(f"the sub class: {subClass} must define a __slots__ class attribut")
        if not _ownAttr(subClass, "__init_subclass__"):
            raise AttributeError(f"the sub class: {subClass} must define a __init_subclass__ (must register the sub class)")
        return cast("type[ClassFactoryProtocol]", subClass) # => the sub class is a valide factory

    @staticmethod
    def _ClassFactory__registerFactoryUser(subClass:"_T_ClassFactory", **kwargs)->"_T_ClassFactory":
        """register a sub class and call the factories on it"""
        for base in subClass.__bases__:
            factorys = ClassFactory.__registered_subclasses.get(base, None)
            if factorys is not None:
                ClassFactory.__registered_subclasses[subClass].update(factorys)
        ClassFactory._ClassFactory__callFactories(subClass, **kwargs)
        return subClass

    @staticmethod
    def _ClassFactory__callFactories(subClass:"type[ClassFactory]", **kwargs)->None:
        for factory in ClassFactory.__registered_subclasses[subClass]:
            factory._ClassFactory__initSubclass(subClass, **kwargs)



class FinalClass(ClassFactory):
    """make all attr of the sub classes final"""
    __slots__ = ()
    
    def __init_subclass__(cls:"type[FinalClass]", **kwargs)->None:
        ClassFactory._ClassFactory__registerFactoryUser(cls, **kwargs)
    
    @staticmethod
    def _ClassFactory__initSubclass(subClass:"type[FinalClass]", allow_setattr_overload:bool=False, **kwargs) -> None:
        if allow_setattr_overload: return None # => no checks to do
        if getattr(subClass, "__setattr__") is not FinalClass.__setattr__:
            # => redefining __setattr__ in cls
            raise ValueError(f"the sub class: {subClass} of {FinalClass} has modified __setattr__")
        # => all good
                    
    def __setattr__(self, name: str, value: Any) -> None:
        if hasattr(self, name):
            raise AttributeError(f"Trying to set twice a the final attribute: {name}")
        super().__setattr__(name, value)




class PartialyFinalClass(ClassFactory):
    """make 'final' all the attr in __finals__ (must be setted at least once) of the sub classes of PartialyFinalClass\n
     will add in the class.__finals__ all the attrs in the __finals__ of its base classes (they must Inherit from this protocol)"""
    __slots__ = ()
    __finals__: "ClassVar[set[str]]"
    
    def __init_subclass__(cls:"type[PartialyFinalClass]", **kwargs)->None:
        ClassFactory._ClassFactory__registerFactoryUser(cls, **kwargs)
    
    @staticmethod
    def _ClassFactory__initSubclass(subClass:"type[PartialyFinalClass]", allow_setattr_overload:bool=False, **kwargs) -> None:
        if allow_setattr_overload is False:
            # => check __setattr__
            if getattr(subClass, "__setattr__") is not PartialyFinalClass.__setattr__:
                # => redefining __setattr__ in cls
                raise ValueError(f"the sub class: {subClass} of {PartialyFinalClass} has modified __setattr__")
        # => __setattr_ is fine
        if hasattr(subClass, "__finals__") is False:
            raise AttributeError(f"couldn't initialize the class: {subClass}: it don't implement correctly the partialy final protocol, the class attribut: '__finals__' is missing")
        # => __finals__ has at least be defined once
        if "__finals__" not in subClass.__dict__.keys():
            # => the class don't re-define it => no new finals
            subClass.__finals__ = set()
        # => the class is valide !
        # replace the names with the true name of each atrr
        for name in subClass.__finals__:
            attrName = getAttrName(subClass, name)
            if attrName != name: # => wrong name in __finals__
                subClass.__finals__.remove(name)
                subClass.__finals__.add(attrName)
            # else: => alredy in __finals__
        # add the names from the base classes
        subClass.__addFinalAttrs_fromBases(subClass.__bases__)
    
    @classmethod
    def __addFinalAttrs_fromBases(cls, bases:"tuple[type, ...]")->None:
        for baseClasse in bases:
            if baseClasse is PartialyFinalClass: continue
            if not issubclass(baseClasse, PartialyFinalClass):
                continue
            for attrName in baseClasse.__finals__:
                if attrName in cls.__finals__:
                    raise ValueError(f"can't add the final attribut: {repr(attrName)} from {baseClasse} twice on {cls}, it can be a collision betwin the __finals__ of its base classes")
                cls.__finals__.add(attrName)
    
    def __setattr__(self, name: str, value: Any) -> None:
        if (name in self.__class__.__finals__) and hasattr(self, name):
            raise AttributeError(f"Trying to set twice a the final attribute: {name}")
        super().__setattr__(name, value)



class FreezableClass(ClassFactory):
    """make the sub classes frozen\n
    you will initialize the frozen state with:\n
        - super().__init__() => set to the default state (given to the class, if its None, __init__ do nothing)\n
        - self._freez() / self._unfreez() will also set it to the desired state"""
    __slots__ = ("__frozen", )
    __initialFreez: "ClassVar[bool|None]"
    
    def __init_subclass__(cls:"type[FreezableClass]", **kwargs)->None:
        ClassFactory._ClassFactory__registerFactoryUser(cls, **kwargs)
    
    @staticmethod
    def _ClassFactory__initSubclass(subClass:"type[FreezableClass]", initialFreezState:"bool|None", allow_setattr_overload:bool=False, **kwargs) -> None:
        if (allow_setattr_overload is False) and (getattr(subClass, "__setattr__") is not FreezableClass.__setattr__):
            # => redefining __setattr__ in cls
            raise ValueError(f"the sub class: {subClass} of {FreezableClass} has modified __setattr__")
        subClass.__initialFreez = initialFreezState
        
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

