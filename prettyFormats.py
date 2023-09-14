import sys
from collections.abc import Iterable
from io import StringIO

from holo.calc import divmod_rec
from holo.__typing import (
    Any, TextIO, NamedTuple,
    Callable, Mapping, TypeVar,
    Sized, Literal, TypeGuard, 
    Sequence, Container, 
    # pretty types
    _Pretty_CompactRules, _Pretty_Delimiter,
)
from holo.protocols import (
    _T, SupportsPretty, _PrettyPrintable, 
)


def isinstanceNamedTuple(obj:object)->TypeGuard[NamedTuple]:
    return (isinstance(obj, tuple) and hasattr(obj, '_asdict') and hasattr(obj, '_fields'))

class _PrettyPrint_fixedArgs(NamedTuple):
    stream:TextIO
    compactArgs:"PrettyPrint_CompactArgs"
    toStringFunc:"Callable[[object], str]"
    indentSequence:str

    def getIndent(self, nbIndents:int)->str:
        return self.indentSequence * nbIndents

_PP_specialDelimChars:"dict[type, _Pretty_Delimiter]" = {
    dict:_Pretty_Delimiter('{', '}'),  list:_Pretty_Delimiter('[', ']'),
    set:_Pretty_Delimiter('{', '}'), tuple:_Pretty_Delimiter('(', ')'),
}
DEFAULT_MAPPING_DELIM = _Pretty_Delimiter("{", "}")
DEFAULT_ITERABLE_DELIM = _Pretty_Delimiter("[", "]")

DEFAULT_COMPACT_RULES:"_Pretty_CompactRules" = \
    _Pretty_CompactRules(newLine=True, indent=True, spacing=False)
"""when compacting, it compact newLines, indents but keep spacing spacing"""

class PrettyPrint_CompactArgs():
    __slots__ = ("compactSmaller", "compactLarger", "compactSpecifics", "keepReccursiveCompact", "compactRules")
    def __init__(self,
            compactSmaller:"int|Literal[False]"=False, compactLarger:"int|Literal[False]"=False,
            keepReccursiveCompact:bool=False, compactSpecifics:"set[type]|None"=None,
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
            if (self.compactLarger is not False) and (objSize >= self.compactSmaller):
                return True
        ### compact based on specific type
        if self.compactSpecifics is None: 
            return False # no specific rule
        if type(obj) in self.compactSpecifics:
            return True # => exact type match
        # test if is instance of any specific rule
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

def __prettyPrint_internal(
        obj:"_PrettyPrintable", currLineIndent:int,
        specificFormats:"dict[type[_T], Callable[[_T], str|_PrettyPrintable]]|None", 
        oldCompactState:"_PP_compactState", args:"_PrettyPrint_fixedArgs")->None:
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
                args.stream.write(newObj)
            else:
                __prettyPrint_internal(
                    obj=newObj, currLineIndent=currLineIndent,
                    oldCompactState=oldCompactState,
                    specificFormats=specificFormats, args=args, 
                )
            return None

    ## then use the general rule
    isFirstElt:bool
    separatorSequence:str
    currenCompactState:"_PP_compactState" = oldCompactState.newFromCompactPrint(
        args.compactArgs.newCompactPrint(obj, oldCompactState)
    )
    compactPrint:bool = currenCompactState.compactPrint
    compactRules:"_Pretty_CompactRules" = args.compactArgs.compactRules
    compactNewLine:bool = (compactPrint and compactRules.newLine)
    compactIndent:bool = (compactPrint and compactRules.indent)
    compactSpacing:bool = (compactPrint and compactRules.spacing)

    if isinstance(obj, SupportsPretty):
        __prettyPrint_internal(
            obj=obj.__pretty__(compactRules if compactPrint is True else None),
            currLineIndent=currLineIndent, oldCompactState=oldCompactState,
            specificFormats=specificFormats, args=args, 
        )
            
    elif isinstance(obj, Mapping) or isinstanceNamedTuple(obj): # /!\ Mapping and NamedTuple can be iterable
        # delimiter open
        delimiter = _PP_specialDelimChars.get(type(obj), DEFAULT_MAPPING_DELIM)
        args.stream.write(delimiter.open)

        # create compact sequences
        isFirstElt = True
        separatorSequence:str = ","
        keyToValue_sequence:str = ":"
        
        if compactSpacing is False:
            keyToValue_sequence =  keyToValue_sequence + " "
            if compactNewLine is True: # don't add an ending space when a new line
                separatorSequence = separatorSequence + " "
        
        if compactNewLine is False: # new line
            separatorSequence = separatorSequence + "\n"
            args.stream.write("\n")
            if compactIndent is False: # indent the new lines
                nextElementSequence = args.getIndent(currLineIndent+1)
                separatorSequence = separatorSequence + nextElementSequence
                args.stream.write(nextElementSequence)
        
        # iterate over elements
        objItems:"Iterable[tuple[Any, Any]]" = \
            (obj.items() if isinstance(obj, Mapping) else obj._asdict().items())
        for key, value in objItems:
            if isFirstElt is True: isFirstElt = False
            else: # => not the first element
                args.stream.write(separatorSequence)
            # key
            __prettyPrint_internal(
                obj=key, currLineIndent=currLineIndent+1, specificFormats=specificFormats,
                oldCompactState=currenCompactState.force(True), args=args,
                # forceCompact -> True, seem better for a key
            )
            # key to value
            args.stream.write(keyToValue_sequence)
            # value
            __prettyPrint_internal(
                obj=value, currLineIndent=currLineIndent+1, specificFormats=specificFormats,
                oldCompactState=currenCompactState, args=args,
            )

        # ending sequence
        if compactNewLine is False: # new line
            args.stream.write("\n")
            if compactIndent is False: # indent the new line
                args.stream.write(args.getIndent(currLineIndent))

        # delimiter close
        args.stream.write(delimiter.close)

    elif (isinstance(obj, Sequence) \
            or (isinstance(obj, Iterable) and isinstance(obj, Container))) \
            and not (isinstance(obj, (str, bytes))): # => equivalent of `list`
        # delimiter open
        delimiter = _PP_specialDelimChars.get(type(obj), DEFAULT_ITERABLE_DELIM)
        args.stream.write(delimiter.open)

        # create compact sequences
        isFirstElt = True
        separatorSequence:str = ","
        keyToValue_sequence:str = ":"
        
        if compactSpacing is False:
            keyToValue_sequence =  keyToValue_sequence + " "
            if compactNewLine is True: # don't add an ending space when a new line
                separatorSequence = separatorSequence + " "
        
        if compactNewLine is False: # new line
            separatorSequence = separatorSequence + "\n"
            args.stream.write("\n")
            if compactIndent is False: # indent the new lines
                nextElementSequence = args.getIndent(currLineIndent+1)
                separatorSequence = separatorSequence + nextElementSequence
                args.stream.write(nextElementSequence)

        for item in obj:
            # separator
            if isFirstElt is True: isFirstElt = False
            else: # => not the first element
                args.stream.write(separatorSequence)
            # value
            __prettyPrint_internal(
                obj=item, currLineIndent=currLineIndent+1, specificFormats=specificFormats,
                oldCompactState=currenCompactState, args=args,
            )

        # ending sequence
        if compactNewLine is False: # new line
            args.stream.write("\n")
            if compactIndent is False: # indent the new line
                args.stream.write(args.getIndent(currLineIndent))
        
        # delimiter close
        args.stream.write(delimiter.close)

    else: # => default to str print
        args.stream.write(args.toStringFunc(obj))

def prettyPrint(
        obj:"_PrettyPrintable", indentSequence:str=" "*4, compact:"bool|None|PrettyPrint_CompactArgs"=False,
        stream:"TextIO|None"=None, specificFormats:"dict[type[_T], Callable[[_T], str|Any]]|None"=None, end:"str|None"="\n",
        specificCompact:"set[type]|None"=None, _defaultStrFunc:"Callable[[object], str]"=str, startIndent:int=0)->None:
    """/!\\ may not be as optimized as pprint but prettier print\n
    default `stream` -> stdout\n
    `compact` ...\n
    \t with compactUNDER if the size (in elts) of the object is <= its value (if not None)\n
    \t => print it more compactly (similar thing for compactOVER)"""
    if stream is None: stream = sys.stdout

    compactArgs:"PrettyPrint_CompactArgs"
    startCompactState:"_PP_compactState"
    if compact is None: # => use a default config
        compactArgs = PrettyPrint_CompactArgs(1, 20)
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
        args=_PrettyPrint_fixedArgs(
            stream=stream, indentSequence=indentSequence, 
            toStringFunc=_defaultStrFunc, compactArgs=compactArgs,
        )
    )
    if end is not None:
        stream.write(end)

def prettyString(
        obj:"_PrettyPrintable", indentSequence:str=" "*4, compact:"bool|None|PrettyPrint_CompactArgs"=False,
        specificFormats:"dict[type[_T], Callable[[_T], str|Any]]|None"=None, specificCompact:"set[type]|None"=None,
        _defaultStrFunc:"Callable[[object], str]"=str, startIndent:int=0)->str:
    stream = StringIO()
    prettyPrint(
        obj=obj, indentSequence=indentSequence, compact=compact, stream=stream,
        specificFormats=specificFormats, end=None, specificCompact=specificCompact,
        _defaultStrFunc=_defaultStrFunc, startIndent=startIndent,
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
