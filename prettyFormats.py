import sys
import traceback
from io import StringIO

from holo.calc import divmod_rec
from holo.__typing import (
    Any, TextIO, NamedTuple, Callable, 
    Mapping, Iterable, Sequence, AbstractSet,
    TypeVar, Sized, Literal, TypeGuard, 
    Sequence, _PrettyPrintable,
)
from holo.protocols import _T, SupportsPretty



_T_NamedTuple = TypeVar("_T_NamedTuple", bound=NamedTuple)


def isinstanceNamedTuple(obj:object)->TypeGuard[NamedTuple]:
    return (isinstance(obj, tuple) and hasattr(obj, '_asdict') and hasattr(obj, '_fields'))



class _PrettyPrint_fixedArgs(NamedTuple):
    stream:TextIO
    compactArgs:"PrettyPrint_CompactArgs"
    toStringFunc:"Callable[[object], str]"
    indentSequence:str

    def getIndent(self, nbIndents:int)->str:
        return self.indentSequence * nbIndents


class _Pretty_Delimiter(NamedTuple):
    open:str; close:str

_PP_specialDelimChars:"dict[type, _Pretty_Delimiter]" = {
    dict:_Pretty_Delimiter('{', '}'),  list:_Pretty_Delimiter('[', ']'),
    set:_Pretty_Delimiter('{', '}'), tuple:_Pretty_Delimiter('(', ')'),
}
DEFAULT_MAPPING_DELIM = _Pretty_Delimiter("{", "}")
DEFAULT_ITERABLE_DELIM = _Pretty_Delimiter("[", "]")
EMPTY_DELIM = _Pretty_Delimiter("", "")


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
        
    def newCompactPrint(self, obj:Any, currentCompactState:"_PP_compactState")->bool:
        if currentCompactState._force is not None: 
            return currentCompactState._force # forced
        if (currentCompactState.compactPrint is True) and (self.keepReccursiveCompact is True):
            return True # keep compacting
        # => we will over write the compactPrint
        ### compact based on size
        if isinstance(obj, Sized):
            objSize:int = len(obj)
            if (self.compactSmaller is not False) and (objSize <= self.compactSmaller):
                return True
            if (self.compactLarger is not False) and (objSize >= self.compactLarger):
                return True
        ### compact based on specific type
        if self.compactSpecifics is None: 
            return False # no specific rule
        return type(obj) in self.compactSpecifics


class _PP_compactState():
    __slots__ = ("compactPrint", "_force")
    def __init__(self, compactPrint:bool, _force:"bool|None"=None) -> None:
        self.compactPrint:bool = compactPrint
        self._force:"bool|None" = _force
    
    def newFromCompactPrint(self, newCompactPrint:bool)->"_PP_compactState":
        return _PP_compactState(compactPrint=newCompactPrint, _force=self._force)
    def force(self, forceState:"bool|None")->"_PP_compactState":
        return _PP_compactState(compactPrint=self.compactPrint, _force=forceState)


class _PP_KeyValuePair(NamedTuple):
    key:"_PrettyPrintable"; value:"_PrettyPrintable"
def _iterableToPairs(objItems:"Iterable[tuple[_PrettyPrintable, _PrettyPrintable]]")->"Iterable[_PP_KeyValuePair]":
    return map(lambda pair: _PP_KeyValuePair(*pair), objItems)

class _ObjectRepr(NamedTuple):
    className:str
    args:"tuple[_PrettyPrintable, ...]"
    kwargs:"dict[str, _PrettyPrintable]"



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
                obj=subObj.key, currLineIndent=currLineIndent+1, specificFormats=specificFormats,
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
            obj=value, currLineIndent=currLineIndent+1, specificFormats=specificFormats,
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
        obj:"_ObjectRepr", currCompactRules:"_Pretty_CompactRules", currLineIndent:int,
        specificFormats:"dict[type[_T], Callable[[_T], str|_PrettyPrintable]]|None",
        currenCompactState:"_PP_compactState", fixedArgs:"_PrettyPrint_fixedArgs")->None:
    """internal that pretty print `mapping like` or `sequence like` objects"""
    fixedArgs.stream.write(obj.className)
    fixedArgs.stream.write("(")
    # size check needed: without this condition an empty object
    #   will print a starting sequence and an ending sequence
    argsIsEmpty:bool = (len(obj.args) != 0)
    kwargsIsEmpty:bool = (len(obj.kwargs) != 0)
    if (argsIsEmpty is False) or (kwargsIsEmpty is False):
        __prettyPrint_internal__print_Generic(
            objItems=obj.args, isMapping=False, printEndingSeparator=kwargsIsEmpty,
            separatorSequence=",", keyToValue_sequence="",
            delimiter=EMPTY_DELIM, currCompactRules=currCompactRules,
            printStartingSequence=True, printEndingSeqence=False,
            currLineIndent=currLineIndent, specificFormats=specificFormats,
            currenCompactState=currenCompactState, fixedArgs=fixedArgs,
        )
        __prettyPrint_internal__print_Generic(
            objItems=_iterableToPairs(obj.kwargs.items()), isMapping=True,
            separatorSequence=",", keyToValue_sequence="=", printEndingSeparator=False,
            delimiter=EMPTY_DELIM, currCompactRules=currCompactRules._replace(mapSpacing=True),
            printStartingSequence=False, printEndingSeqence=True,
            currLineIndent=currLineIndent, specificFormats=specificFormats,
            currenCompactState=currenCompactState, fixedArgs=fixedArgs,
        )
    else: pass # => empty repr => nothing to print
    fixedArgs.stream.write(")")


def __prettyPrint_internal(
        obj:"_PrettyPrintable", currLineIndent:int,
        specificFormats:"dict[type[_T], Callable[[_T], str|_PrettyPrintable]]|None",
        oldCompactState:"_PP_compactState", fixedArgs:"_PrettyPrint_fixedArgs")->None:
    """`compactUnder` if the size (in elts) of the object is under its value, print it more compactly\n
    `specificFormats` is a dict: type -> (func -> obj -> str), if an obj is an instance use this to print\n
    `printClassName` whether it will print the class before printing the object (True->alway, None->default, False->never)\n"""

    ## look for a specific format first
    if (specificFormats is not None):
        formatFunc = specificFormats.get(type(obj), None) # type: ignore normal that the _PrettyPrintable dont match _T
        if formatFunc is not None:
            # obj will use a specific format
            newObj:"str|Any" = formatFunc(obj)
            if isinstance(newObj, str):
                fixedArgs.stream.write(newObj)
            else:
                __prettyPrint_internal(
                    obj=newObj, currLineIndent=currLineIndent,
                    oldCompactState=oldCompactState,
                    specificFormats=specificFormats, fixedArgs=fixedArgs, 
                )
            return None

    ## then use the general rule
    currenCompactState:"_PP_compactState" = oldCompactState.newFromCompactPrint(
        fixedArgs.compactArgs.newCompactPrint(obj, oldCompactState)
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
            currLineIndent=currLineIndent, oldCompactState=oldCompactState,
            specificFormats=specificFormats, fixedArgs=fixedArgs, 
        )
    
    elif isinstance(obj, _ObjectRepr):
        __prettyPrint_internal__print_ObjectRepr(
            obj=obj, currCompactRules=currentCompactRules,
            currLineIndent=currLineIndent, specificFormats=specificFormats,
            currenCompactState=currenCompactState, fixedArgs=fixedArgs,
        )
           
    elif isinstance(obj, Mapping) or isinstanceNamedTuple(obj): # /!\ Mapping and NamedTuple can be iterable
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
        obj:"_PrettyPrintable", indentSequence:str=" "*4, compact:"bool|None|PrettyPrint_CompactArgs"=None,
        stream:"TextIO|None"=None, specificFormats:"dict[type[_T], Callable[[_T], str|Any]]|None"=None, end:"str|None"="\n",
        specificCompact:"set[type]|None"=None, defaultStrFunc:"Callable[[object], str]"=str, startIndent:int=0)->None:
    """/!\\ may not be as optimized as pprint but prettier print\n
    default `stream` -> stdout\n
    `compact` ...\n
    \t with compactUNDER if the size (in elts) of the object is <= its value (if not None)\n
    \t => print it more compactly (similar thing for compactOVER)"""
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

    __prettyPrint_internal(
        obj, currLineIndent=startIndent, specificFormats=specificFormats,
        oldCompactState=startCompactState,
        fixedArgs=_PrettyPrint_fixedArgs(
            stream=stream, indentSequence=indentSequence, 
            toStringFunc=defaultStrFunc, compactArgs=compactArgs,
        )
    )
    if end is not None:
        stream.write(end)

def prettyString(
        obj:"_PrettyPrintable", indentSequence:str=" "*4, compact:"bool|None|PrettyPrint_CompactArgs"=False,
        specificFormats:"dict[type[_T], Callable[[_T], str|Any]]|None"=None, specificCompact:"set[type]|None"=None,
        defaultStrFunc:"Callable[[object], str]"=str, startIndent:int=0)->str:
    stream = StringIO()
    prettyPrint(
        obj=obj, indentSequence=indentSequence, compact=compact, stream=stream,
        specificFormats=specificFormats, end=None, specificCompact=specificCompact,
        defaultStrFunc=defaultStrFunc, startIndent=startIndent,
    )
    return stream.getvalue()


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


def prettyfyNamedTuple(cls:"type[_T_NamedTuple]")->"type[_T_NamedTuple]":
    """currently impossible to type but the retuned type \
        satisfy holo.protocols.SupportsPretty"""
    def __pretty__(self:_T_NamedTuple, *args, **kwargs):
        return _ObjectRepr(self.__class__.__name__, (), self._asdict())
    setattr(cls, "__pretty__", __pretty__) 
    return cls


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