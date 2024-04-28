import sys
import traceback
from io import StringIO

from holo.calc import divmod_rec
from holo.__typing import (
    Any, TextIO, NamedTuple, Callable, 
    Mapping, Iterable, Sequence, AbstractSet,
    TypeVar, Sized, Literal, TypeGuard, 
    Sequence, _PrettyPrintable, assertIsinstance,
    isNamedTuple, CodeType, JsonTypeAlias, NoReturn, 
    ClassVar, getAttrName, cast, ClassFactory, _ownAttr,
)
from holo.protocols import _T, SupportsPretty, SupportsSlots

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
    stream:TextIO
    compactArgs:"PrettyPrint_CompactArgs"
    toStringFunc:"Callable[[object], str]"
    indentSequence:str

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

    def __len__(self)->int:
        return len(self.args) + len(self.kwargs)


def __prettyPrint_internal__print_Generic(
        objItems:"Iterable[_PP_KeyValuePair]|Iterable[_PrettyPrintable]", isMapping:bool,
        separatorSequence:str, keyToValue_sequence:str, delimiter:"_Pretty_Delimiter",
        currCompactRules:"_Pretty_CompactRules", printEndingSeparator:bool,
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
            raise TypeError(f"while in mapping mode, the subObj isn't an instance of {_PP_KeyValuePair} but {type(subObj)}")
        
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
            delimiter=EMPTY_DELIM, currCompactRules=currCompactRules,
            printStartingSequence=True, printEndingSeqence=False,
            currLineIndent=currLineIndent, specificFormats=specificFormats,
            currenCompactState=currenCompactState, fixedArgs=fixedArgs,
        )
        __prettyPrint_internal__print_Generic(
            objItems=_iterableToPairs(obj_repr.kwargs.items()), isMapping=True,
            separatorSequence=obj_repr.separator,
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

    if isinstance(obj, SupportsPretty):
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
            objItems=_iterableToPairs(objItems), isMapping=True,
            separatorSequence=",", keyToValue_sequence=":", printEndingSeparator=False,
            delimiter=delimiter, currCompactRules=currentCompactRules,
            printStartingSequence=True, printEndingSeqence=True,
            currLineIndent=currLineIndent, specificFormats=specificFormats,
            currenCompactState=currenCompactState, fixedArgs=fixedArgs,
        )
        

    elif (isinstance(obj, Sequence) or isinstance(obj, AbstractSet)) and not (isinstance(obj, (str, bytes))):
        delimiter = _PP_specialDelimChars.get(type(obj), DEFAULT_ITERABLE_DELIM)
        
        __prettyPrint_internal__print_Generic(
            objItems=obj, isMapping=False,
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
        compact:"bool|None|PrettyPrint_CompactArgs"=None, stream:"TextIO|None"=None,
        specificFormats:"dict[type[_T], Callable[[_T], str|Any]]|None"=None, end:"str|None"="\n",
        specificCompact:"set[type]|None"=None, defaultStrFunc:"Callable[[object], str]"=str, startIndent:int=0)->None:
    """/!\\ may not be as optimized as pprint but prettier print\n
    default `stream` -> stdout\n
    `compact` ...\n
    \t with compactUNDER if the size (in elts) of the object is <= its value (if not None)\n
    \t => print it more compactly (similar thing for compactOVER)\n
    `specificFormats` all values of the exact given type will be transformed with the given function\n
        - 1) if the returned object IS the same object as in inputed object, use the normal procedure
        - 2) if the returned object is a string, directly write it\n"""
    if stream is None: stream = sys.stdout

    compactArgs:"PrettyPrint_CompactArgs"
    startCompactState:"_PP_compactState"
    if compact is None: # => use a default config
        compactArgs = PrettyPrint_CompactArgs(1, False)
        startCompactState = _PP_compactState(False, _force=None)
    elif compact is True: # => always force compact 
        compactArgs = PrettyPrint_CompactArgs() # don't care
        startCompactState = _PP_compactState(True, _force=True) 
    elif compact is False: # => never compact 
        compactArgs = PrettyPrint_CompactArgs() # don't care
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
        compact:"bool|None|PrettyPrint_CompactArgs"=False, specificFormats:"dict[type[_T], Callable[[_T], str|Any]]|None"=None,
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
        specificFormats:"dict[type[_T], Callable[[_T], str|Any]]|None"=None, end:"str|None"="\n", specificCompact:"set[type]|None"=None,
        defaultStrFunc:"Callable[[None|bool|int|float|str|object], str]|None"=None, startIndent:int=0)->None:
    """NOTE: don't check if the keys are str"""
    if defaultStrFunc is None:
        defaultStrFunc = toJSON_basicTypes
    prettyPrint(
        obj, objsSeparator=None, indentSequence=indentSequence, compact=compact,
        stream=stream, specificFormats=specificFormats, end=end, specificCompact=specificCompact,
        defaultStrFunc=defaultStrFunc, startIndent=startIndent,
    )

def prettyTime(t:float)->str:
    """print a time value in a more redable way"""
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



def print_exception(error:BaseException, file:"TextIO|Literal['stderr', 'stdout']|None"=None)->None:
    """print an exception like when it is raised (print the traceback)\n
    default `stream` -> stderr"""
    if file is None: file = sys.stderr
    if file == "stdout": file = sys.stdout
    if file == "stderr": file = sys.stderr
    print(
        "".join(traceback.format_tb(error.__traceback__))
        + f"{error.__class__.__name__}: {error}",
        file=file
    )
    

def getCurrentFuncCode(depth:int=1)->CodeType:
    return sys._getframe(depth).f_code

def toJSON_basicTypes(obj:"None|bool|int|float|str|object")->"str|NoReturn":
        if type(obj) == str: return f"\"{obj.translate(JSON_STR_ESCAPE_TRANSLATE_TABLE)}\""
        elif type(obj) == bool: return ("true" if obj == True else "false")
        elif type(obj) in (int, float): return str(obj)
        else: raise TypeError(f"the value of the given type: {type(obj)} isn't supported (only support builtin types, no inheritance)")




class PrettyfyClass(ClassFactory):
    """## when defining __prettyAttrs__ :
    ### this is the behavious before adding attrs from bases (if getPrettyAttrs_fromBases)
    - not defined -> use 'all'
    - 'all' -> get all from __dict__ (if it has one) and __slots__ (if it has one) 
        * only add the attrs from __slots__ if it was defined in the class, not from a super class
        * 'all' will be changed to tuple[set[str], 'all'] in order to simplify the process
    - set[str] -> add the attrs from the set (can be __slots__/__dict__ class)
        * private attrs must be the ones from the class where __prettyAttrs__ is setted
        * set[str] will be changed to tuple[set[str], None] in order to simplify the process
    - tuple[(1), (2)] -> (this is what the class will have after the __init_subclass__)
        * (1) set[str] -> (like - 'set[str]'),
        * (2) bool: True -> get all from the self.__dict__ | False -> do nothing"""
    __prettyAttrs__: "ClassVar[set[str]|Literal['all']|tuple[set[str], bool]]"
    __slots__ = tuple()
    
    def __init_subclass__(cls:"type[ClassFactory]", **kwargs)->None:
        ClassFactory._ClassFactory__registerFactoryUser(cls, **kwargs)
    
    @staticmethod
    def _ClassFactory__initSubclass(subClass:"type[PrettyfyClass]", addPrettyAttrs_fromBases:bool=True, **kwargs) -> None:
        if _ownAttr(subClass, "__pretty__"):
            raise AttributeError(f"the sub class: {subClass} must not define a __pretty__ methode, it is done by the factory")
        if _ownAttr(subClass, "__prettyAttrs__") is False:
            # => wasn't defined in the class
            subClass.__prettyAttrs__ = "all"
        # => __prettyAttrs__ is the one of the class
        if subClass.__prettyAttrs__ == "all":
            subClass.__prettyAttrs__ = (set(), True)
            if _ownAttr(subClass, "__slots__"): # => __slots__ class
                subClass.__prettyAttrs__[0].update(
                    (getAttrName(subClass, name) for name in getattr(subClass, "__slots__")))
            # else => __dict__ class => 'all' is sufficient, nothing more to add
        else: # => set[str] | tuple[set[str], 'all']
            # transform the names to attrNames
            if isinstance(subClass.__prettyAttrs__, tuple):
                subClass.__prettyAttrs__ = (
                    set(getAttrName(subClass, name) for name in subClass.__prettyAttrs__[0]), 
                    subClass.__prettyAttrs__[1])
            else: # => set[str]
                subClass.__prettyAttrs__ = (set(getAttrName(subClass, name) for name in subClass.__prettyAttrs__), False)
        # => the transformation of __prettyAttrs__ is done
        
        if addPrettyAttrs_fromBases is False:
            return None # => finished here
        # add the __prettyAttrs__ from the bases
        set_getDict: bool = subClass.__prettyAttrs__[1]
        for baseClasse in subClass.__bases__:
            if (baseClasse is PrettyfyClass) or (): continue
            if not issubclass(baseClasse, PrettyfyClass):
                continue
            attrsSet, getDict = cast("tuple[set[str], bool]", baseClasse.__prettyAttrs__)
            subClass.__prettyAttrs__[0].update(attrsSet)
            if getDict == True: set_getDict = True
            # else: => keep it
        subClass.__prettyAttrs__ = (subClass.__prettyAttrs__[0], set_getDict)
    
    def __pretty__(self, *_, **__) -> _ObjectRepr:
        attrsToValue: "dict[str, Any]" = {}
        attrsSet, getDict = cast("tuple[set[str], bool]", self.__prettyAttrs__)
        for attrName in attrsSet: 
            attrsToValue[attrName] = getattr(self, attrName)
        if (getDict is True) and hasattr(self, "__dict__"):
            attrsToValue.update(self.__dict__)
        return _ObjectRepr(className=self.__class__.__name__, args=(), kwargs=attrsToValue)