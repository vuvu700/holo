import sys
import traceback
from io import StringIO, TextIOBase
from datetime import timedelta
import re
from copy import deepcopy
import warnings


from .calc import divmod_rec
from .__typing import (
    Any, TextIO, BinaryIO, NamedTuple, Callable, 
    Mapping, Iterable, Sequence, AbstractSet,
    TypeVar, Sized, Literal, TypeGuard, FrameType,
    Sequence, _PrettyPrintable, assertIsinstance,
    isNamedTuple, CodeType, JsonTypeAlias, NoReturn, 
    ClassVar, getAttrName, Self, ClassFactory, _ownAttr,
)
from .protocols import _T, SupportsPretty, SupportsSlots, SupportsWrite

# TODO:
# apporter les ameiorations nécessaires pour pouvoir specificCompact les _ObjectRepr en fonction du type
# corriger le pb(?) qui fait que les _ObjectRepr ne se compactent pas correctement en fonction de la taille 

_T_NamedTuple = TypeVar("_T_NamedTuple", bound=NamedTuple)
_T_Type = TypeVar("_T_Type", bound=type)


JSON_STR_ESCAPE_TRANSLATE_TABLE = {
    ord('\"'): r'\"', ord("\\"): r"\\", ord("\b"): r"\b",
    ord("\f"): r"\f", ord("\n"): r"\n", ord("\r"): r"\r",
    ord("\t"): r"\t",
}





def prettyfyNamedTuple(cls:"type[_T_NamedTuple]")->"type[_T_NamedTuple]":
    """implement a generic methode to prettyPrint a NamedTuple class\n
    currently impossible to type but the retuned type satisfy holo.protocols.SupportsPretty"""
    def __pretty__(self:_T_NamedTuple, *args, **kwargs):
        return _ObjectRepr(self.__class__.__name__, (), self._asdict())
    setattr(cls, "__pretty__", __pretty__) 
    return cls


def basic__strRepr__(cls:_T_Type)->_T_Type:
    """implement a generic __str__ and __repr__ methode for a class (for __dict__ and __slots__)"""
    def __str__(self)->str:
        kwargs:"dict[str, Any]"
        if isinstance(self, SupportsSlots):
            kwargs = {name: getattr(self, name) for name in self.__slots__}
        else: kwargs = __dict__
        return f"{self.__class__.__name__}({', '.join(f'{name}={value}' for name, value in kwargs.items())})"

    setattr(cls, "__str__", __str__) 
    setattr(cls, "__repr__", __str__) 
    return cls




@prettyfyNamedTuple
class _PrettyPrint_fixedArgs(NamedTuple):
    stream: "SupportsWrite[str]"
    compactArgs: "PrettyPrint_CompactArgs"
    toStringFunc: "Callable[[object], str]"
    indentSequence: str

    def getIndent(self, nbIndents:int)->str:
        return self.indentSequence * nbIndents


@prettyfyNamedTuple
class _Pretty_Delimiter(NamedTuple):
    open:str; close:str

_PP_specialDelimChars:"dict[type, _Pretty_Delimiter]" = {
    dict:_Pretty_Delimiter('{', '}'),  list:_Pretty_Delimiter('[', ']'),
    set:_Pretty_Delimiter('{', '}'), tuple:_Pretty_Delimiter('(', ')'),
}
DEFAULT_MAPPING_DELIM = _Pretty_Delimiter("{", "}")
DEFAULT_ITERABLE_DELIM = _Pretty_Delimiter("[", "]")
EMPTY_DELIM = _Pretty_Delimiter("", "")


@prettyfyNamedTuple
class _Pretty_CompactRules(NamedTuple):
    """ - True => compact it\n
     - False => don't compact it\n
    when compacting: use the given rule\n
    NOTE: `key` is not affected by the current compacting state, \
        force the compacting reccursively"""
    newLine:bool; seqSpacing:bool; mapSpacing:bool
    indent:bool; key:bool

DEFAULT_COMPACT_RULES:"_Pretty_CompactRules" = \
    _Pretty_CompactRules(newLine=True, indent=True, seqSpacing=False, mapSpacing=False, key=True)
"""when compacting, it compact newLines, indents and keys but don't compact the spacing"""

MAX_COMPACT_RULES:"_Pretty_CompactRules" = \
    _Pretty_CompactRules(newLine=True, indent=True, seqSpacing=True, mapSpacing=True, key=True)


@basic__strRepr__
class PrettyPrint_CompactArgs():
    __slots__ = ("compactSmaller", "compactLarger", "compactSpecifics", "keepReccursiveCompact", "compactRules")
    def __init__(self,
            compactSmaller:"int|Literal[False]"=False, compactLarger:"int|Literal[False]"=False,
            keepReccursiveCompact:bool=True, compactSpecifics:"set[type]|None"=None,
            compactRules:"_Pretty_CompactRules"=DEFAULT_COMPACT_RULES) -> None:
        self.compactSmaller:"int|Literal[False]" = compactSmaller
        self.compactLarger:"int|Literal[False]" = compactLarger
        self.compactSpecifics:"set[type]|None" = compactSpecifics
        self.keepReccursiveCompact:bool = keepReccursiveCompact
        self.compactRules:"_Pretty_CompactRules" = compactRules
        
    def newCompactPrint(self, 
            objType:type, objSize:"int|None", currentCompactState:"_PP_compactState")->bool:
        if currentCompactState._force is not None: 
            return currentCompactState._force # forced
        if (currentCompactState.compactPrint is True) and (self.keepReccursiveCompact is True):
            return True # keep compacting
        # => we will over write the compactPrint
        ### compact based on size
        if objSize is not None:
            if (self.compactSmaller is not False) and (objSize <= self.compactSmaller):
                return True
            if (self.compactLarger is not False) and (objSize >= self.compactLarger):
                return True
        ### compact based on specific type
        if self.compactSpecifics is None: 
            return False # no specific rule
        return objType in self.compactSpecifics


@basic__strRepr__
class _PP_compactState():
    __slots__ = ("compactPrint", "_force")
    def __init__(self, compactPrint:bool, _force:"bool|None"=None) -> None:
        self.compactPrint:bool = compactPrint
        self._force:"bool|None" = _force
    
    def newFromCompactPrint(self, newCompactPrint:bool)->"_PP_compactState":
        return _PP_compactState(compactPrint=newCompactPrint, _force=self._force)
    def force(self, forceState:"bool|None")->"_PP_compactState":
        return _PP_compactState(compactPrint=self.compactPrint, _force=forceState)

@prettyfyNamedTuple
class _PP_KeyValuePair(NamedTuple):
    key:"_PrettyPrintable"; value:"_PrettyPrintable"
def _iterableToPairs(objItems:"Iterable[tuple[_PrettyPrintable, _PrettyPrintable]]")->"Iterable[_PP_KeyValuePair]":
    return map(lambda pair: _PP_KeyValuePair(*pair), objItems)

# don't @prettyfyNamedTuple
class _ObjectRepr(NamedTuple):
    className:str
    args:"tuple[_PrettyPrintable, ...]"
    kwargs:"dict[str, _PrettyPrintable]"
    kwargs_keyToValue:str = "="
    separator:str = ","
    forceStrKey: bool = True
    """this will make the key to be always printed with str"""

    def __len__(self)->int:
        return len(self.args) + len(self.kwargs)

    def __getStrRepr(self, func:"Callable[[object], str]")->str:
        """base of __getStrRepr where func is applied to each elements contained"""
        subStrings: list[str] = [
            self.className, "(", ]
        isFirst: bool = True
        for elt in self.args:
            if not isFirst: 
                subStrings.append(", ")
            else: isFirst = False
            subStrings.append(func(elt))
        for name, elt in self.kwargs.items():
            if not isFirst: 
                subStrings.append(", ")
            else: isFirst = False
            subStrings.append(f"{name}=")
            subStrings.append(func(elt))
        subStrings.append(")")
        return "".join(subStrings)
    
    def getStr(self)->str:
        """get a basic python `__str__` of object represented by `self`"""
        return self.__getStrRepr(str)

    def getRepr(self)->str:
        """get a basic python `__repr__` of object represented by `self`"""
        return self.__getStrRepr(repr)


def __prettyPrint_internal__print_Generic(
        objItems:"Iterable[_PP_KeyValuePair]|Iterable[_PrettyPrintable]", isMapping:bool,
        separatorSequence:str, keyToValue_sequence:str, delimiter:"_Pretty_Delimiter", 
        forceStrKey:bool, currCompactRules:"_Pretty_CompactRules", printEndingSeparator:bool,
        printStartingSequence:bool, printEndingSeqence:bool, currLineIndent:int,
        specificFormats:"dict[type[_T], Callable[[_T], str|_PrettyPrintable]]|None",
        currenCompactState:"_PP_compactState", fixedArgs:"_PrettyPrint_fixedArgs")->None:
    """internal that pretty print `mapping like` or `sequence like` objects"""
    
    # delimiter open
    fixedArgs.stream.write(delimiter.open)

    # create compact sequences
    isFirstElt:bool = True
    
    if currCompactRules.seqSpacing is False:
        if currCompactRules.newLine is True: # don't add an ending space when a new line
            separatorSequence = separatorSequence + " "
    if currCompactRules.mapSpacing is False:
        keyToValue_sequence = keyToValue_sequence + " "
    
    if currCompactRules.newLine is False: # new line
        separatorSequence = separatorSequence + "\n"
        if printStartingSequence is True:
            fixedArgs.stream.write("\n")
        if currCompactRules.indent is False: # indent the new lines
            nextElementSequence = fixedArgs.getIndent(currLineIndent+1)
            separatorSequence = separatorSequence + nextElementSequence
            if printStartingSequence is True:
                fixedArgs.stream.write(nextElementSequence)
    
    for subObj in objItems:
        if isFirstElt is True: isFirstElt = False
        else: # => not the first element
            fixedArgs.stream.write(separatorSequence)
        if (isMapping is True) and isinstance(subObj, _PP_KeyValuePair):
            # key
            if forceStrKey is True:
                fixedArgs.stream.write(str(subObj.key))
            else: 
                __prettyPrint_internal(
                    obj=subObj.key, currLineIndent=currLineIndent+1, 
                    prettyfyFromObj=None, specificFormats=specificFormats,
                    oldCompactState=currenCompactState.force(currCompactRules.key),
                    fixedArgs=fixedArgs,
                    # to force compacting state seem better for a key
                )
            # key to value
            fixedArgs.stream.write(keyToValue_sequence)
            value = subObj.value
            
        elif isMapping is True:
            # => (isMapping is True) and NOT isinstance(subObj, _PP_KeyValuePair)
            raise TypeError(f"while in mapping mode, the subObj of type {type(subObj)} isn't an instance of {_PP_KeyValuePair}")
        
        else: # => generic sequence
            value = subObj
        
        # value
        __prettyPrint_internal(
            obj=value, prettyfyFromObj=None,
            currLineIndent=currLineIndent+1, specificFormats=specificFormats,
            oldCompactState=currenCompactState, fixedArgs=fixedArgs,
        )
    if (isFirstElt is False) and (printEndingSeparator is True):
        # => has printed some elements
        fixedArgs.stream.write(separatorSequence)
    
    # ending sequence
    if (currCompactRules.newLine is False) and (printEndingSeqence is True): # new line
        fixedArgs.stream.write("\n")
        if currCompactRules.indent is False: # indent the new line
            fixedArgs.stream.write(fixedArgs.getIndent(currLineIndent))

    # delimiter close
    fixedArgs.stream.write(delimiter.close)
    

def __prettyPrint_internal__print_ObjectRepr(
        obj_repr:"_ObjectRepr", currCompactRules:"_Pretty_CompactRules", currLineIndent:int,
        specificFormats:"dict[type[_T], Callable[[_T], str|_PrettyPrintable]]|None",
        currenCompactState:"_PP_compactState", fixedArgs:"_PrettyPrint_fixedArgs")->None:
    """internal that pretty print `mapping like` or `sequence like` objects"""
    fixedArgs.stream.write(obj_repr.className)
    fixedArgs.stream.write("(")
    # size check needed: without this condition an empty object
    #   will print a starting sequence and an ending sequence
    if len(obj_repr) != 0: # => things to print
        __prettyPrint_internal__print_Generic(
            objItems=obj_repr.args, isMapping=False, 
            printEndingSeparator=(len(obj_repr.kwargs) != 0),
            separatorSequence=obj_repr.separator, keyToValue_sequence="",
            delimiter=EMPTY_DELIM, forceStrKey=False, 
            currCompactRules=currCompactRules, printStartingSequence=True,
            printEndingSeqence=False, currLineIndent=currLineIndent,
            specificFormats=specificFormats, currenCompactState=currenCompactState,
            fixedArgs=fixedArgs,
        )
        __prettyPrint_internal__print_Generic(
            objItems=_iterableToPairs(obj_repr.kwargs.items()), isMapping=True,
            separatorSequence=obj_repr.separator, forceStrKey=obj_repr.forceStrKey,
            keyToValue_sequence=obj_repr.kwargs_keyToValue,
            printEndingSeparator=False, delimiter=EMPTY_DELIM, 
            currCompactRules=currCompactRules._replace(mapSpacing=True),
            printStartingSequence=False, printEndingSeqence=True,
            currLineIndent=currLineIndent, specificFormats=specificFormats,
            currenCompactState=currenCompactState, fixedArgs=fixedArgs,
        )
    else: pass # => empty repr => nothing to print
    fixedArgs.stream.write(")")


def __prettyPrint_internal(
        obj:"_PrettyPrintable", currLineIndent:int, prettyfyFromObj:"Any|None",
        specificFormats:"dict[type[_T], Callable[[_T], str|_PrettyPrintable]]|None",
        oldCompactState:"_PP_compactState", fixedArgs:"_PrettyPrint_fixedArgs")->None:
    """`compactUnder` if the size (in elts) of the object is under its value, print it more compactly\n
    `specificFormats` is a dict: type -> (func -> obj -> str), if an obj is an instance use this to print\n
    `printClassName` whether it will print the class before printing the object (True->alway, None->default, False->never)\n
    `prettyfyFromObj` is setted when called after prettyfying an object to the object from it, otherwise is None\
        since None can't have a __pretty__ methode it is safe to use this value\n"""

    ## look for a specific format first
    if (specificFormats is not None):
        formatFunc = specificFormats.get(type(obj), None) # type: ignore normal that the _PrettyPrintable dont match _T
        if formatFunc is not None:
            # obj will use a specific format
            newObj:"str|Any" = formatFunc(obj)
            if newObj is obj: pass # => same object, use normal procedure
            # => not the same object
            elif isinstance(newObj, str):
                fixedArgs.stream.write(newObj)
                return None
            else:
                return __prettyPrint_internal(
                    obj=newObj, currLineIndent=currLineIndent,
                    oldCompactState=oldCompactState, prettyfyFromObj=None,
                    specificFormats=specificFormats, fixedArgs=fixedArgs, 
                )

    ## then use the general rule
    currenCompactState:"_PP_compactState" = oldCompactState.newFromCompactPrint(
        fixedArgs.compactArgs.newCompactPrint(
            objType=type(obj if prettyfyFromObj is None else prettyfyFromObj), 
            objSize=(len(obj) if isinstance(obj, Sized) else None),
            currentCompactState=oldCompactState,
        )
    )
    doCompactPrint:bool = currenCompactState.compactPrint
    currentCompactRules = _Pretty_CompactRules(
        newLine=(doCompactPrint and fixedArgs.compactArgs.compactRules.newLine),
        seqSpacing=(doCompactPrint and fixedArgs.compactArgs.compactRules.seqSpacing),
        mapSpacing=(doCompactPrint and fixedArgs.compactArgs.compactRules.mapSpacing),
        indent=(doCompactPrint and fixedArgs.compactArgs.compactRules.indent),
        key=fixedArgs.compactArgs.compactRules.key, # keep the rule even when not compacting
    )

    if isinstance(obj, SupportsPretty) and (type(obj) != type):
        # don't allow types beacuse classes that supports __pretty__ can pass otherwise
        __prettyPrint_internal(
            obj=obj.__pretty__(compactRules=currentCompactRules), 
            prettyfyFromObj=(obj if prettyfyFromObj is None else prettyfyFromObj), 
            # => keep the first prettyfyFromObj 
            currLineIndent=currLineIndent, oldCompactState=oldCompactState,
            specificFormats=specificFormats, fixedArgs=fixedArgs, 
        )
    
    elif isinstance(obj, _ObjectRepr):
        __prettyPrint_internal__print_ObjectRepr(
            obj_repr=obj, currCompactRules=currentCompactRules,
            currLineIndent=currLineIndent, specificFormats=specificFormats,
            currenCompactState=currenCompactState, fixedArgs=fixedArgs,
        )
           
    elif isinstance(obj, Mapping) or isNamedTuple(obj): # /!\ Mapping and NamedTuple can be iterable
        delimiter = _PP_specialDelimChars.get(type(obj), DEFAULT_MAPPING_DELIM)
        # create iterator
        objItems:"Iterable[tuple[_PrettyPrintable, _PrettyPrintable]]" = \
            (obj.items() if isinstance(obj, Mapping) else obj._asdict().items())
       
        __prettyPrint_internal__print_Generic(
            objItems=_iterableToPairs(objItems), isMapping=True, forceStrKey=False,
            separatorSequence=",", keyToValue_sequence=":", printEndingSeparator=False,
            delimiter=delimiter, currCompactRules=currentCompactRules,
            printStartingSequence=True, printEndingSeqence=True,
            currLineIndent=currLineIndent, specificFormats=specificFormats,
            currenCompactState=currenCompactState, fixedArgs=fixedArgs,
        )
        

    elif (isinstance(obj, Sequence) or isinstance(obj, AbstractSet)) and not (isinstance(obj, (str, bytes))):
        delimiter = _PP_specialDelimChars.get(type(obj), DEFAULT_ITERABLE_DELIM)
        
        __prettyPrint_internal__print_Generic(
            objItems=obj, isMapping=False, forceStrKey=False,
            separatorSequence=",", keyToValue_sequence="", printEndingSeparator=False,
            delimiter=delimiter, currCompactRules=currentCompactRules,
            printStartingSequence=True, printEndingSeqence=True,
            currLineIndent=currLineIndent, specificFormats=specificFormats,
            currenCompactState=currenCompactState, fixedArgs=fixedArgs,
        )

    else: # => default to str print
        fixedArgs.stream.write(fixedArgs.toStringFunc(obj))


def prettyPrint(
        *objs:"_PrettyPrintable", objsSeparator:"str|None"=" ", indentSequence:str=" "*4, 
        compact:"bool|None|PrettyPrint_CompactArgs"=None, stream:"SupportsWrite[str]|None"=None,
        specificFormats:"dict[type[_T], Callable[[_T|Any], str|Any]]|None"=None, end:"str|None"="\n",
        specificCompact:"set[type]|None"=None, defaultStrFunc:"Callable[[object], str]"=str, startIndent:int=0)->None:
    """/!\\ may not be as optimized as pprint but prettier print\n
    default `stream` -> stdout\n
    `compact` ...\n
    \t with compactUNDER if the size (in elts) of the object is <= its value (if not None)\n
    \t => print it more compactly (similar thing for compactOVER)\n
    `specificFormats` all values of the exact given type will be transformed with the given function\n
        - 1) if the returned object IS the same object as in inputed object, use the normal procedure
        - 2) if the returned object is a string, directly write it\n"""
    if stream is None: 
        stream = assertIsinstance(SupportsWrite, sys.stdout)
     

    compactArgs:"PrettyPrint_CompactArgs"
    startCompactState:"_PP_compactState"
    if compact is None: # => use a default config
        compactArgs = PrettyPrint_CompactArgs(1, False)
        startCompactState = _PP_compactState(False, _force=None)
    elif compact is True: # => always force compact 
        compactArgs = PrettyPrint_CompactArgs(compactRules=MAX_COMPACT_RULES)
        startCompactState = _PP_compactState(True, _force=True) 
    elif compact is False: # => never compact 
        compactArgs = PrettyPrint_CompactArgs()
        startCompactState = _PP_compactState(False, _force=False) 
    elif isinstance(compact, PrettyPrint_CompactArgs):
        compactArgs = compact
        startCompactState = _PP_compactState(False, _force=None)
    else: raise TypeError(f"invalide type of the compact parameter: {type(compact)}")

    if specificCompact is not None:
        if compactArgs.compactSpecifics is not None:
            # => merge the two sets
            compactArgs.compactSpecifics.update(specificCompact)
        else: # => no current set => use the given one
            compactArgs.compactSpecifics = specificCompact
    
    isFirstObj:bool = True
    for obj in objs:
        if (isFirstObj is False) and (objsSeparator is not None):
            stream.write(objsSeparator)
        else: isFirstObj = False # will be setted every times when (objsSeparator is None) but not a problem
        __prettyPrint_internal(
            obj, prettyfyFromObj=None, currLineIndent=startIndent,
            specificFormats=specificFormats, oldCompactState=startCompactState,
            fixedArgs=_PrettyPrint_fixedArgs(
                stream=stream, indentSequence=indentSequence, 
                toStringFunc=defaultStrFunc, compactArgs=compactArgs))
        
    if end is not None:
        stream.write(end)

def prettyString(
        *objs:"_PrettyPrintable", objsSeparator:"str|None"=" ", indentSequence:str=" "*4,
        compact:"bool|None|PrettyPrint_CompactArgs"=False, specificFormats:"dict[type[_T], Callable[[_T|Any], str|Any]]|None"=None,
        specificCompact:"set[type]|None"=None, defaultStrFunc:"Callable[[object], str]"=str, startIndent:int=0)->str:
    stream = StringIO()
    prettyPrint(
        *objs, objsSeparator=objsSeparator, indentSequence=indentSequence, compact=compact, 
        stream=stream, specificFormats=specificFormats, end=None, specificCompact=specificCompact,
        defaultStrFunc=defaultStrFunc, startIndent=startIndent,
    )
    return stream.getvalue()

def prettyPrintToJSON(
        obj:"_PrettyPrintable", indentSequence:str=" "*4, compact:"bool|None|PrettyPrint_CompactArgs"=None, stream:"TextIO|None"=None,
        specificFormats:"dict[type[_T], Callable[[_T|Any], str|Any]]|None"=None, end:"str|None"="\n", specificCompact:"set[type]|None"=None,
        defaultStrFunc:"Callable[[None|bool|int|float|str|object], str]|None"=None, startIndent:int=0)->None:
    """NOTE: don't check if the keys are str"""
    if defaultStrFunc is None:
        defaultStrFunc = toJSON_basicTypes
    prettyPrint(
        obj, objsSeparator=None, indentSequence=indentSequence, compact=compact,
        stream=stream, specificFormats=specificFormats, end=end, specificCompact=specificCompact,
        defaultStrFunc=defaultStrFunc, startIndent=startIndent,
    )

def prettyTime(t:"float|timedelta")->str:
    """print a time value in a more redable way"""
    if isinstance(t, timedelta):
        t = t.total_seconds()
    if t == 0.: return "0 sec"
    if t < 1.0: # small scale
        if t < 0.1e-9: # less than nano scale
            return f"{t:.3e} sec"
        elif t < 0.1e-6: # nano
            return f"{t*1e9:.3f} ns"
        elif t < 0.1e-3: # micro
            return f"{t*1e6:.3f} μs"
        else: # milli
            return f"{t*1e3:.3f} ms"
    elif t < 60.: # seconds
        return f"{t:.3f} sec"
    elif t < (3600.): # minutes
        return f"{int(t//60)} min {t%60:.1f} sec"
    elif t < (3600. * 24): # hours
        (nbH, nbMin, nbSec) = divmod_rec(t, [3600, 60])
        return f"{int(nbH)} h {int(nbMin)} min {nbSec:.1f} sec"
    elif t < (3600.* 24 * 7): # few days (high res)
        (nbDay, nbH, nbMin, nbSec) = divmod_rec(t, [3600*24, 3600, 60])
        return f"{int(nbDay)} day {int(nbH)} h {int(nbMin)} min {nbSec:.1f} sec"
    else: # many days (low res)
        return f"{t/(3600*24):.1f} day"

def get_prettyTime_Formater(
        timeScale:"Literal['ns', 'us', 'ms', 's', 'min', 'h', 'day', 'days']|None"
        )->"Callable[[float], str]":
    """print a time value in a more redable way"""
    return {
        None: prettyTime,
        "ns": lambda t: f"{round(t*1e9, 3)} ns",
        "us": lambda t: f"{round(t*1e6, 3)} μs",
        "ms": lambda t: f"{round(t*1e3, 3)} ms",
        "s": lambda t: f"{t:.3f} sec",
        "min": lambda t: f"{t//60} min {round(t%60, 1)} sec",
        "h": lambda t: "%d h %d min %d sec".format(*divmod_rec(int(t), [3600, 60])),
        "day": lambda t: "%d day %d h %d min".format(*divmod_rec(int(t), [3600*24, 3600, 60])),
        "days": lambda t: f"{round(t/(3600*24), 1)} day",
    }[timeScale]


def prettyDataSizeOctes(nbOctes:"int|float")->str:
    """print a data size value in a more redable way"""
    if nbOctes > 1e12: return f"{round(nbOctes/1e12, 3)} To"
    elif nbOctes > 1e9: return f"{round(nbOctes/1e9, 3)} Go"
    elif nbOctes > 1e6: return f"{round(nbOctes/1e6, 3)} Mo"
    elif nbOctes > 1e3: return f"{round(nbOctes/1e3, 3)} Ko"
    else: return f"{nbOctes} o"

def prettyDataSizeBytes(nbBytes:"int|float")->str:
    """print a data size value in a more redable way"""
    if nbBytes > 1e12: return f"{round(nbBytes/1e12, 3)} Tb"
    elif nbBytes > 1e9: return f"{round(nbBytes/1e9, 3)} Gb"
    elif nbBytes > 1e6: return f"{round(nbBytes/1e6, 3)} Mb"
    elif nbBytes > 1e3: return f"{round(nbBytes/1e3, 3)} Kb"
    else: return f"{nbBytes} b"


def get_prettyDataSizeOctes_Formater(dataSizeScale:"Literal['Ko', 'Mo', 'Go', 'To']|None")->"Callable[[float], str]":
    """print a time value in a more redable way"""
    return {
        None: prettyDataSizeOctes,
        "Ko": lambda nbOctes: f"{round(nbOctes/1e3, 3)} Ko",
        "Mo": lambda nbOctes: f"{round(nbOctes/1e6, 3)} Mo",
        "Go": lambda nbOctes: f"{round(nbOctes/1e9, 3)} Go",
        "To": lambda nbOctes: f"{round(nbOctes/1e12, 3)} To",
    }[dataSizeScale]

def get_prettyDataSizeBytes_Formater(dataSizeScale:"Literal['Kb', 'Mb', 'Gb', 'Tb']|None")->"Callable[[float], str]":
    """print a time value in a more redable way"""
    return {
        None: prettyDataSizeBytes,
        "Kb": lambda nbOctes: f"{round(nbOctes/1e3, 3)} Kb",
        "Mb": lambda nbOctes: f"{round(nbOctes/1e6, 3)} Mb",
        "Gb": lambda nbOctes: f"{round(nbOctes/1e9, 3)} Gb",
        "Tb": lambda nbOctes: f"{round(nbOctes/1e12, 3)} Tb",
    }[dataSizeScale]



def indent(text:str, nbIndents:int=1, indentSequence:str=" "*4)->str:
    fullIndentSequence = indentSequence * nbIndents
    return f"{fullIndentSequence}{(fullIndentSequence).join(text.splitlines(keepends=True))}"



def print_exception(error:BaseException, file:"SupportsWrite[str]|Literal['stderr', 'stdout']|None"=None)->None:
    """print an exception like when it is raised (print the traceback)\n
    default `stream` -> stderr"""
    if file is None: file = sys.stderr
    elif file == "stdout": file = sys.stdout
    elif file == "stderr": file = sys.stderr
    file = assertIsinstance(SupportsWrite, file)
    print(
        "".join(traceback.format_tb(error.__traceback__))
        + f"{error.__class__.__name__}: {error}",
        file=file)


def getCurrentFuncCode(depth:int=1)->CodeType:
    """the the code of the function called at the given depth:
    a depth of 0 is THIS function (useless xd), 
        1 (default) is the function that called THIS fucntion, ..."""
    return sys._getframe(depth).f_code

def getCurrentCallStack()->"list[FrameType]":
    """return the current call stack (ommiting this function)"""
    stack: "list[FrameType]" = []
    # get the frame of teh caller
    frame: "FrameType|None" = sys._getframe(1)
    while frame is not None:
        stack.append(frame)
        frame = frame.f_back
    return stack

def printCallStack(callStack:"list[FrameType]")->None:
    print("currentCallStack: ")
    print(*[f"\tfile: {frame.f_code.co_filename}, line {frame.f_lineno}"
            for frame in callStack], sep="\n")
    


def toJSON_basicTypes(obj:"None|bool|int|float|str|object")->"str|NoReturn":
        if type(obj) == str: return f"\"{obj.translate(JSON_STR_ESCAPE_TRANSLATE_TABLE)}\""
        elif type(obj) == bool: return ("true" if obj == True else "false")
        elif type(obj) in (int, float): return str(obj)
        elif obj is None: return "null"
        else: raise TypeError(f"the value of the given type: {type(obj)} isn't supported (only support builtin types, no inheritance)")


@prettyfyNamedTuple
class PrettyfyClassConfig(NamedTuple):
    showAttrs: "list[str]"
    """all the attrs to show"""
    hideAttrs: "list[str]"
    """all the attrs to always hide (overwrite the showAttrs)"""
    showDict: bool
    """whethere to shwo the __dict__"""
    addNewSlots: bool
    """when setuping a new class, gather the __slots__ to showAttrs"""
    mergeWithParent: bool
    """when setuping a new class, add the config from the parents\n
    it will merge all the parents"""

    def copy(self)->"Self":
        return deepcopy(self)
    
    def addAttrs(self, attrsToShow:"list[str]", 
                  attrsToHide:"list[str]", inplace:bool)->"Self":
        if inplace is False:
            self = self.copy()
        self.showAttrs.extend(attrsToShow)
        self.hideAttrs.extend(attrsToHide)
        return self

    def mergeWith(self, other:"PrettyfyClassConfig")->"PrettyfyClassConfig":
        """raw merge: (add the lists, self before other) and (apply or to the booleans)"""
        def removeDups(lst:"list[str]")->"list[str]":
            known: "set[str]" = set()
            res: "list[str]" = []
            for elt in lst:
                if elt not in known:
                    res.append(elt)
                    known.add(elt)
            return res
        
        return PrettyfyClassConfig(
            showAttrs=removeDups(self.showAttrs + other.showAttrs),
            hideAttrs=removeDups(self.hideAttrs + other.hideAttrs),
            showDict=(self.showDict or other.showDict),
            addNewSlots=(self.addNewSlots or other.addNewSlots),
            mergeWithParent=(self.mergeWithParent or other.mergeWithParent))



_T_PrettyfyClass = TypeVar("_T_PrettyfyClass", bound="type[PrettyfyClass]")


class PrettyfyClass(ClassFactory):
    """will add an advanced __pretty__ methode that you can configure\n
    setup a default `__str__` or `__rep__` based on `__prettyAttrs_after__`:
        * str and repr will be `prettyString` with `compact=...` to oneLine it (can be overwriten)
            you can give *args / **kwargs to `prettyString`"""
    __prettyAttrs__: "ClassVar[PrettyfyClassConfig]"
    """if you don't define it => if THIS class is explicitly a ... class
        * __slots__ -> it will add all the new atributs of THIS class and show the __dict__
        * __dict__ -> will add all content of the __dict__ even the ones of previous classes"""
    __prettyAttrs_after__: "ClassVar[PrettyfyClassConfig]"
    """the config that will be used by PrettyfyClass (created by PrettyfyClass, will be overwriten at setup)"""
    __overwrite_strRepr__: "ClassVar[bool]" = False
    """to tell wether the class will force using the __str/repr__ of PrettyfyClass\n
    this will propagate to subclasses until a new rule is given"""
    __slots__ = ()
    
    __str_compact_args = PrettyPrint_CompactArgs(
        compactSmaller=0, compactLarger=0, keepReccursiveCompact=True)
    
    def __init_subclass__(cls:"type[PrettyfyClass]", **kwargs)->None:
        ClassFactory._ClassFactory__registerFactoryUser(cls, **kwargs)
    
    @staticmethod
    def _ClassFactory__initSubclass(
            subClass:"type[PrettyfyClass]", **kwargs) -> None:
        #print(f"\n* start on {subClass} -> {getattr(subClass, '__prettyAttrs_after__', None)} *")
        
        #if _ownAttr(subClass, "__pretty__"):
        #    raise AttributeError(
        #        f"the sub class: {subClass} (or one if its base) "
        #        "must not redefine a __pretty__ methode, it is done by the factory")
        
        if subClass.__overwrite_strRepr__ is True:
            subClass.__str__ = PrettyfyClass.__str__
            subClass.__repr__ = PrettyfyClass.__repr__
        
        if _ownAttr(subClass, "__prettyAttrs__") is False:
            # => (__prettyAttrs__ not owned) => no config provided on this class
            bases_config = PrettyfyClass.__get_bases_cfg(subClass)
            if bases_config is None:
                # => no bases have it defined => all (default behaviour)
                subClass.__prettyAttrs_after__ = PrettyfyClassConfig(
                    showAttrs=PrettyfyClass.__collect_all_new_of_slots(subClass),
                    hideAttrs=[], showDict=True, addNewSlots=True, mergeWithParent=True)
                #print(f"* 1.1 -> final: {subClass.__prettyAttrs_after__}")
                return # finished here
            else: # => it is alredy define on a base
                # => merge with the bases
                #print(f"* 1.2.1 -> base: {bases_config}")
                newConfig = bases_config.copy() # copy the one from the bases
                if newConfig.addNewSlots is True:
                    newConfig.addAttrs(
                        attrsToShow=PrettyfyClass.__collect_all_new_of_slots(subClass),
                        attrsToHide=[], inplace=True)
                subClass.__prettyAttrs_after__ = newConfig
                #print(f"* 1.2.2 -> final: {subClass.__prettyAttrs_after__}")
                return # finished here
        else: 
            # => (__prettyAttrs__ is owned) => defined by the user
            #print(f"* 1.3.1 -> before: {subClass.__prettyAttrs__}")
            if subClass.__prettyAttrs__.mergeWithParent is True:
                # => find the nearest one in a base
                bases_cfg = PrettyfyClass.__get_bases_cfg(subClass)
                # set the __prettyAttrs_after__ config
                if bases_cfg is not None:
                    # => it has bases
                    subClass.__prettyAttrs_after__ = PrettyfyClassConfig.mergeWith(
                        bases_cfg, subClass.__prettyAttrs__)
                else: # => don't have bases
                    subClass.__prettyAttrs_after__ = subClass.__prettyAttrs__.copy()
                
                if subClass.__prettyAttrs_after__.addNewSlots is True:
                    subClass.__prettyAttrs_after__.addAttrs(
                        attrsToShow=PrettyfyClass.__collect_all_new_of_slots(subClass),
                        attrsToHide=[], inplace=True)
            #print(f"* 1.3.2 -> final: {subClass.__prettyAttrs_after__}")
            return  # finished here
        raise RuntimeError(f"code souldn't be reached")
    
    @staticmethod
    def __get_bases_cfg(subClass:"type[PrettyfyClass]")->"PrettyfyClassConfig|None":
        """return a copy of the cofig from the base (no merge betwin is done)"""
        merged_cfg: "PrettyfyClassConfig|None" = None
        for base in subClass.__bases__:
            base_cfg = getattr(base, "__prettyAttrs_after__", None)
            if isinstance(base_cfg, PrettyfyClassConfig):
                if merged_cfg is None:
                    merged_cfg = base_cfg
                else: merged_cfg.mergeWith(base_cfg.copy())
        return merged_cfg
                
    
    @staticmethod
    def __collect_all_new_of_slots(subClass:"type[PrettyfyClass]")->"list[str]":
        """if the class is slotted -> return all new slots (tuple)
        if class is dict based -> empty tuple"""
        if _ownAttr(subClass, "__slots__"): 
            # => __slots__ class
            return [getAttrName(subClass, name)
                    for name in getattr(subClass, "__slots__")
                    if name != "__weakref__"]
        else: # => __dict__ class 
            return []
    
    def __pretty__(self, *_, **__) -> _ObjectRepr:
        if _ownAttr(self.__class__, "__prettyAttrs_after__") is False:
            raise AttributeError(f"the class: {self.__class__} migth not have been configured")
        cfg = self.__prettyAttrs_after__
        attrsToValue: "dict[str, Any]" = {}
        for attrName in cfg.showAttrs: 
            attrsToValue[attrName] = getattr(self, attrName)
        if (cfg.showDict is True) and hasattr(self, "__dict__"):
            attrsToValue.update(self.__dict__)
        return _ObjectRepr(className=self.__class__.__name__, args=(), 
                           kwargs=attrsToValue, forceStrKey=True)

    def __str__(self, **kwargs) -> str:
        """get str of a oneLined of self.__pretty__"""
        return prettyString(self.__pretty__(), compact=self.__str_compact_args,**kwargs, defaultStrFunc=str)
    
    def __repr__(self, **kwargs) -> str:
        """get repr of a oneLined of self.__pretty__"""
        return prettyString(self.__pretty__(), compact=self.__str_compact_args, **kwargs, defaultStrFunc=repr)


class SingleLinePrinter():
    __slots__ = ("__file", "__currentLineLength", )
    
    def __init__(self, file:"TextIO|None")->None:
        self.__file: "TextIO|None" = file
        self.__currentLineLength: int = 0

    @property
    def file(self)->"TextIO":
        return (sys.stdout if self.__file is None else self.__file)
    @file.setter
    def file(self, newFile:"TextIO|None")->"None":
        self.__file = newFile

    def clearLine(self)->None:
        self.file.write("\r")
        self.file.write(" " * self.__currentLineLength)
        self.file.write("\r")
        self.__currentLineLength = 0
    
    def print(self, text:str)->None:
        """clear the current line and print the new `text`, 
        the `text` must be single lined"""
        self.clearLine()
        self.write(text=text)
    
    def validateText(self, text:str)->None:
        for bannedChr in ("\r", "\n", "\b"):
            pos: int = text.find(bannedChr)
            if pos != -1:
                raise ValueError(f"the text can't contain: {bannedChr} at index: {pos}")
        
    def write(self, text:str)->None:
        """continue printing on the current line, the text must be single lined"""
        self.validateText(text=text)
        res = self.file.write(text)
        self.__currentLineLength += len(text)

def NDigitsRounding(x:float, nbDigits:int)->float:
    return float(f"{x:.{nbDigits}g}")

expFloatPattern = re.compile(r"(?P<digit1>\d)(.(?P<subDigits>\d*))?e(?P<exp>[\-\+]\d*)")
def NDigitsFormating(x:float, nbDigits:int)->str:
    assert nbDigits > 0, ValueError(f"nbDigits: {nbDigits} must be > 0")
    expFormatedFloat: str = f"{x:.{nbDigits-1}e}"
    fullmatch: "re.Match[str]|None" = expFloatPattern.fullmatch(expFormatedFloat)
    assert fullmatch is not None
    groups: "dict[str, str]" = fullmatch.groupdict()
    subDigits = ("0"*(nbDigits-1) if groups['subDigits'] is None
                 else f"{groups['subDigits']:<0{nbDigits-1}}")
    allDigits: str = groups['digit1'] + subDigits
    exponent: int = int(groups["exp"]) - (nbDigits-1)
    frontZeros: int = exponent + nbDigits
    if frontZeros <= 0:
        return f"0.{'0'*abs(frontZeros)}{allDigits}"
    elif frontZeros < nbDigits:
        return f"{allDigits[: frontZeros]}.{allDigits[frontZeros: ]}"
    else: return str(int(allDigits)*10**exponent)