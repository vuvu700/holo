from collections.abc import Iterable
from typing import (
    Iterable, Any, TextIO, NamedTuple,
    Callable, Mapping, Sized, Generator, cast,
)
from typing_extensions import Literal
import sys

from holo.calc import divmod_rec

def isinstanceNamedTuple(obj:object)->bool:
    return (isinstance(obj, tuple) and hasattr(obj, '_asdict') and hasattr(obj, '_fields'))

def __prettyPrint_internal(
        obj:object, indentSpaces:int, stream:"TextIO", compactUnder:"int|None", compactOver:"int|None",
        currLineIndent:int, specificFormats:"dict[type, Callable[[Any], str]]|None", forceCompact:bool,
        toStringFunc:"Callable[[object], str]", printClassName:"bool|None", indentSequence:str):
    """`compactUnder` if the size (in elts) of the object is under its value, print it more compactly\n
    `specificFormats` is a dict: type -> (func -> obj -> str), if an obj's correspond use this to print\n
    `printClassName` whether it will print the class before printing the object (True->alway, None->default, False->never)\n"""
    specialDelimChars:"dict[type, tuple[str, str]]" = {
        dict:('{', '}'),  list:('[', ']'), set:('{', '}'), tuple:('(', ')'),
        int:('(', ')'), float:('(', ')'), str:('(', ')'), complex:('(', ')'),
    }
    typesSpecialDelim:"tuple[type, ...]" = tuple(specialDelimChars.keys())

    ## look for a specific format first
    if (specificFormats is not None):
        for (type_, formatFunc) in specificFormats.items():
            if isinstance(obj, type_):
                if printClassName is True:
                    tmp:bool = False
                    stream.write(obj.__class__.__name__)
                    if type(obj) in typesSpecialDelim:
                        stream.write(specialDelimChars[type(obj)][0]); tmp=True
                    else: stream.write("#")
                    stream.write(toStringFunc(obj))
                    if tmp is True:
                        stream.write(specialDelimChars[type(obj)][1])
                    else: stream.write("#")
                else: stream.write(formatFunc(obj))

                return None

    ## then use the general rule
    isFirstElt:bool
    compactPrint:bool = forceCompact
    newLineSequence:str
    if (compactPrint is False) and isinstance(obj, Sized):
        objSize:int = len(obj)
        compactPrint = ((compactUnder is not None) and (objSize <= compactUnder))
        compactPrint = (compactPrint is True) or ((compactOver is not None) and (objSize >= compactOver))
    reccursiveForceCompact:bool = forceCompact

    if isinstance(obj, Mapping) or isinstanceNamedTuple(obj): # Mapping and NamedTuple can be iterable
        if not isinstance(obj, Mapping): obj = cast(NamedTuple, obj) # NamedTuple can't be isinstanced => use a trick

        if printClassName is True: stream.write(obj.__class__.__name__)
        if type(obj) in typesSpecialDelim:
            stream.write(specialDelimChars[type(obj)][0])
        else:
            if printClassName is None:
                stream.write(obj.__class__.__name__)
            stream.write("{")

        if compactPrint is False:
            stream.write("\n" + indentSequence*(currLineIndent+indentSpaces))

        isFirstElt = True
        newLineSequence = ", " if (compactPrint is True) else (",\n" + indentSequence*(currLineIndent+indentSpaces))
        objItems:"Iterable[tuple[Any, Any]]" = (obj.items() if isinstance(obj, Mapping) else obj._asdict().items())
        for key, value in objItems:
            if isFirstElt is True: isFirstElt = False
            else: stream.write(newLineSequence)
            __prettyPrint_internal(
                key, indentSpaces, stream, compactUnder, compactOver, currLineIndent+indentSpaces, specificFormats,
                toStringFunc=toStringFunc, forceCompact=True, printClassName=printClassName, indentSequence=indentSequence,
                # forceCompact=True seem better for a key
            )
            stream.write(": ")
            __prettyPrint_internal(
                value, indentSpaces, stream, compactUnder, compactOver, currLineIndent+indentSpaces, specificFormats,
                forceCompact=reccursiveForceCompact, toStringFunc=toStringFunc, printClassName=printClassName, indentSequence=indentSequence,
            )

        if (compactPrint is False):
            stream.write("\n" + indentSequence*currLineIndent)
        if type(obj) in typesSpecialDelim:
            stream.write(specialDelimChars[type(obj)][1])
        else : stream.write("}")
        return None

    elif isinstance(obj, Iterable) and (not isinstance(obj, (Generator, str, bytes))):
        if printClassName is True: stream.write(obj.__class__.__name__)
        if type(obj) in typesSpecialDelim:
            stream.write(specialDelimChars[type(obj)][0])
        else:
            if printClassName is None:
                stream.write(obj.__class__.__name__)
            stream.write("[")

        if (compactPrint is False):
            stream.write("\n" + indentSequence*(currLineIndent+indentSpaces))

        isFirstElt = True
        newLineSequence = ", " if (compactPrint is True) else (",\n" + indentSequence*(currLineIndent+indentSpaces))
        for item in obj:
            if isFirstElt is True: isFirstElt = False
            else: stream.write(newLineSequence)
            __prettyPrint_internal(
                item, indentSpaces, stream, compactUnder, compactOver, currLineIndent+indentSpaces, specificFormats,
                forceCompact=reccursiveForceCompact, toStringFunc=toStringFunc, printClassName=printClassName, indentSequence=indentSequence,

            )

        if (compactPrint is False):
            stream.write("\n" + indentSequence*currLineIndent)
        if type(obj) in typesSpecialDelim:
            stream.write(specialDelimChars[type(obj)][1])
        else : stream.write("]")
        return None

    else:
        # print normaly
        if printClassName is True:
            tmp:bool = False
            stream.write(obj.__class__.__name__)
            if type(obj) in typesSpecialDelim:
                stream.write(specialDelimChars[type(obj)][0]); tmp=True
            else: stream.write("|")
            stream.write(toStringFunc(obj))
            if tmp is True:
                stream.write(specialDelimChars[type(obj)][1])
            else: stream.write("|")

        else : stream.write(toStringFunc(obj))
        return None


def prettyPrint(
        obj:object, indents:int=4, indentSequence:str=" ", compact:"tuple[int|None, int|None]|bool|None"=False,
        stream:"TextIO|None"=None, specificFormats:"dict[type, Callable[[Any], str]]|None"=None, end:"str|None"="\n",
        _defaultStrFunc:"Callable[[object], str]"=str, printClassName:"bool|None"=False)->None:
    """/!\\ may not be as optimized as pprint but prettier print\n
    default `stream` -> stdout\n
    `compact` is either a tuple of (compactUnder, compactOver) or bool (True -> (1, 35))\n
    \t with compactUNDER if the size (in elts) of the object is <= its value (if not None)\n
    \t => print it more compactly (similar thing for compactOVER)\n
    `indents` the number of time the `indentSequence` is repeated very indentation"""
    if stream is None: stream = sys.stdout

    compactUnder:"int|None"; compactOver:"int|None"
    if compact is None: compactUnder = 1; compactOver = 35
    elif compact is False: compactUnder = 0; compactOver = None
    elif compact is True: compactUnder = -1; compactOver = -1
    else: compactUnder = compact[0]; compactOver = compact[1]

    __prettyPrint_internal(
        obj, indentSpaces=indents, stream=stream, compactUnder=compactUnder, compactOver=compactOver,
        specificFormats=specificFormats, currLineIndent=0, forceCompact=(compact is True),
        toStringFunc=_defaultStrFunc, printClassName=printClassName, indentSequence=indentSequence,
    )
    if end is not None:
        stream.write(end)



def prettyTime(t:float)->str:
    """print a time value in a more redable way"""
    if t == 0.: return "0. sec"
    if t < 1.0: # small scale
        if t < 0.1e-9: # less than nano scale
            return f"{t:.3e} sec"
        elif t < 0.1e-6: # nano
            return f"{round(t*1e9, 3)} ns"
        elif t < 0.1e-3: # micro
            return f"{round(t*1e6, 3)} μs"
        else: # milli
            return f"{round(t*1e3, 3)} ms"
    elif t < 60.: # seconds
        return f"{t:.3f} sec"
    elif t < (60. * 60): # minutes
        return f"{t//60} min {round(t%60, 1)} sec"
    elif t < (60. * 60 * 24): # hours
        (nbH, nbMin, nbSec) = divmod_rec(int(t), 3600, 60)
        return f"{nbH} h {nbMin} min {nbSec} sec"
    elif t < (60. * 60 * 24 * 7): # days (high res)
        (nbDay, nbH, nbMin, _) = divmod_rec(int(t), 3600*24, 3600, 60)
        return f"{nbDay} day {nbH} h {nbMin} min"
    else: # days (low res)
        return f"{round(t/(3600*24), 1)} day"

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
        "h": lambda t: "%d h %d min %d sec".format(*divmod_rec(int(t), 3600, 60)),
        "day": lambda t: "%d day %d h %d min".format(*divmod_rec(int(t), 3600*24, 3600, 60)),
        "days": lambda t: f"{round(t/(3600*24), 1)} day",
    }[timeScale]


def prettyDataSizeOctes(nbOctes:int)->str:
    """print a data size value in a more redable way"""
    if nbOctes > 1e12: return f"{round(nbOctes/1e12, 3)} To"
    elif nbOctes > 1e9: return f"{round(nbOctes/1e9, 3)} Go"
    elif nbOctes > 1e6: return f"{round(nbOctes/1e6, 3)} Mo"
    elif nbOctes > 1e3: return f"{round(nbOctes/1e3, 3)} Ko"
    else: return f"{nbOctes} o"

def prettyDataSizeBytes(nbBytes:int)->str:
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
