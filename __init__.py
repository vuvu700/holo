import sys
from collections.abc import Iterable
from holo.__typing import (
    TypeVar, Any, Sequence, TextIO, Literal, 
    Generic, Unpack, TypeVarTuple, ContextManager, Self,
)
import traceback

__author__ = "Andrieu Ludovic"

from holo.dummys import DummyContext
from holo.prettyFormats import prettyPrint, prettyTime


_T = TypeVar("_T")

# TODO: add un param a prettyPrint qui permet de ne pas forcer le compact récursivement mais redeterminer a chaque étape


class Node_Words():
    """ABR specialized O(log2 n) to search Iterable in large amount of other Iterable :\n
    a practical exemple with searching word in a liste of words"""

    __slots__ = ("letter", "isEndOfWord", "leaves")

    def __init__(self, letter:"str|Any")->None:
        self.letter:"str|Any" = letter
        self.isEndOfWord:bool = False
        self.leaves:"dict[str|Any, Node_Words]" = dict()

    def addWord(self, word:"Sequence[str|Any]")->None:
        """add an Iterable to the ABR, the Iterable must have hashable items"""
        if len(word) > 0:
            letter = word[0]
            leaves = self.leaves
            if letter in leaves:
                leaves[letter].addWord(word[1: ]) # continue to add the word on the node
            else:
                # reccursively create a new node and continue to add the word on it
                leaves.setdefault(letter,  Node_Words(letter)).addWord(word[1: ])

        else: self.isEndOfWord = True

    def __contains__(self, word:"Sequence[str|Any]")->bool:
        if len(word) == 0:
            return self.isEndOfWord
        return (word[0] in self.leaves) and (word[1: ] in self.leaves[word[0]])



def split_rec(string:str, listeOfSeparator:"list[str]")->"list[str]":
    """will turn "abcdeefghia"- > ['a', 'de', 'ia'], if the liste of spearators was ["bc", "efg"]"""
    res = []
    remaining = string
    while len(remaining) != 0:
        nextSplitIndex = len(remaining)
        separatorSize = 0
        for separator in listeOfSeparator:
            indexSplit = remaining.find(separator)
            if (indexSplit != -1) and ( indexSplit < nextSplitIndex):
                nextSplitIndex = indexSplit
                separatorSize = len(separator)

        res.append( remaining[:nextSplitIndex] )
        remaining = remaining[nextSplitIndex+separatorSize:]

    return res





def count(iterable:Iterable, doReturnListe:bool=False)->"dict[Any, int] | list[tuple[int, Any]]":
    """will count the number of occurence of each element in the `iterable` and return it
    in a dict[element, count] or in a list of tuples[count, element]"""
    result = dict()
    for part in iterable:
        if part in result:
            result[part] += 1
        else:
            result[part] = 1

    if doReturnListe is False:
        return result
    return [(count, part) for part, count in result.items()]





def patternValidation(string:str, pattern:str)->"tuple[bool, dict[str, int|float|str]]":
    """test if the `string` match the pattern and return the values extracted from it.
    `pattern` is a rule that the string have to respect :
    \t-the same order have to be respected between all items
    \t-every part with <varName:T> designate variables, and their type
    \t\tT : (f->float, d->int, s->string), if writen as <varName> T=string is used,
    \t\tif T=string, the string is interupted when the next rule is validated
    \t-every part with [abc] is a set of characters to ignore until the next character isn't in the set
    \t\tif writed like [a-z] the set will be all chars in the range of a to z (included), in the ascii table
    \t-every regular part of the string must be inside, in same order
    exemple of pattern: "abcde_[fg]_<v1:d>_ <v2:d> yte <v3>" , will return {"v1":int(str), "v2":float(str)), "v3":str}
    """
    def generateIgnoreCharSet(pattern:str, indexStart:int)->"tuple[set[str], int]":
        """generate the set of characters for the [...] rule and return a tuple(set of char, new index pattern)"""
        # consider that indexStart is the index of '[' that start the rule
        if pattern[indexStart] != '[':
            raise ValueError(f"indexStart={indexStart} doesn't designate an entry point for the [...] rule")

        ignoreCharSet:set[str] = set()
        index:int = indexStart + 1
        while index < len(pattern): # as long as the pattern isn't finished and and the size is sufficient
            # end of the block
            if pattern[index] == ']':
                return (ignoreCharSet, index+1)

            # it is a range -> generate the range in the set
            elif (index+2 < len(pattern)) and (pattern[index+1] == '-')  and (pattern[index+2] != ']'):
                chrStart_i, chrEnd_i = ord(pattern[index]), ord(pattern[index+2])
                step = -1 if chrStart_i > chrEnd_i else 1
                # add to the current set the chars in the range pattern[index] -> pattern[index+2] (both included, can be decresing order)
                ignoreCharSet.update(map(chr, range(chrStart_i, chrEnd_i+step, step)))
                index += 3

            # not a range so a normal char to add
            else:
                ignoreCharSet.add(pattern[index])
                index += 1

        #it didn't reached the end of the block, but the end of the pattern
        raise ValueError(f"pattern invalide from index {indexStart} to {index}:\n\tset to ignore is malformed -> invalid delimitation")




    dictVars:"dict[str, int|float|str]" = dict()

    indexString:int = 0
    indexPattern:int = 0
    # while either the pattern or the string have to get proccesed
    while (indexString < len(string)) and (indexPattern < len(pattern)):

        #start of an ignore set
        if pattern[indexPattern] == '[':
            charIgnore_set, indexPattern = generateIgnoreCharSet(pattern, indexPattern)
            while (indexString < len(string)) and (string[indexString] in charIgnore_set): # the char is in the [...] rule -> skip it
                indexString += 1



        #start of a var
        elif pattern[indexPattern] == '<':

            #get the name of the var from the pattern
            varName_startIndex:int = indexPattern+1
            varName_endIndex:int = indexPattern+1
            while (varName_endIndex < len(pattern)) and (pattern[varName_endIndex] not in [':', '>']): #it search the end of the name
                varName_endIndex += 1
            varName:str = pattern[varName_startIndex: varName_endIndex]
            indexPattern:int = varName_endIndex

            #get the type of the var
            if indexPattern < len(pattern): #because we must have at least a '>' remaining
                # the type has been specified
                if ((pattern[indexPattern] == ':') and
                    (indexPattern+2 < len(pattern)) and (pattern[indexPattern+2] == '>')):
                    varType = pattern[indexPattern + 1]
                    indexPattern += 3 # after the >
                elif pattern[indexPattern] == '>': # type omitted->s
                    varType = 's'
                    indexPattern += 1 # after the >
                else: raise ValueError(f"pattern invalide at index {indexPattern}:\n\ta var is malformed -> invalid delimitation")
            else: raise ValueError(f"pattern invalide at index {indexPattern}:\n\ta var is malformed -> invalid delimitation")

            #get the data from the string
            varValue_startIndex:int = indexString
            varValue_endIndex:int = indexString
            if varType in 'fd': # type == 'f' or type == 'd'
                while (varValue_endIndex < len(string)) and (string[varValue_endIndex] in "0123456789"): # as long the number is int compatible
                    varValue_endIndex += 1

                if varType == 'd': # process the value to the dict as type=int
                    dictVars[varName] = int(string[varValue_startIndex: varValue_endIndex])

                else:
                    #varType is 'f' because varType is single char and in 'df' but not equal to 'd'
                    if (varValue_endIndex +1 < len(string)) and (string[varValue_endIndex + 1] == '.'): #test if it was interupted by a point
                        varValue_endIndex += 1
                        if (varValue_endIndex < len(string)-1): #the point isn't the last char of the string -> continue searching
                            varValue_endIndex += 1
                            while (varValue_endIndex < len(string)) and (string[varValue_endIndex] in "0123456789"): # as long the number is int compatible
                                varValue_endIndex += 1
                    # process the value to the dict as type=float
                    dictVars[varName] = float(string[varValue_startIndex: varValue_endIndex])

            elif varType == 's': # the var is a string, it's delimitation is the start of the next rule
                if indexPattern < len(pattern):
                    if pattern[indexPattern] == '[': #start of an ignore set
                        charInterupt_set, _ = generateIgnoreCharSet(pattern, indexPattern)
                    elif pattern[indexPattern] == '<': #start of a var
                        raise NotImplementedError(f"pattern invalide at index {indexPattern} (not implemented yet):\n\ta <...:s> can't be followed by another <...:T>")
                    else: # normal matching rule
                        charInterupt_set = set(pattern[indexPattern])

                    while (varValue_endIndex < len(string)) and (string[varValue_endIndex] not in charInterupt_set): # as long the string isn't interfering with the next rule
                        varValue_endIndex += 1
                else: # en of the pattern reached so var will go to the end
                    varValue_endIndex = len(string)

                # add the value to the dict as type=str
                dictVars[varName] = string[varValue_startIndex: varValue_endIndex]

            else: raise ValueError(f"pattern invalide at index {indexPattern-1}:\n\ta var is malformed -> invalid type or doesn't exist")
            indexString = varValue_endIndex



        else: #not on a special block
            if string[indexString] == pattern[indexPattern]: #match -> increment index
                indexString += 1; indexPattern += 1
            else:
                break #match failed

    else: # process terminated without failure
        if (indexString == len(string)) and (indexPattern == len(pattern)):
            #the end of path and string reached => the string match the pattern
            return (True, dictVars)

        raise RuntimeError("an error happend") # bad developement

    return (False, dictVars)


def int_to_bytes(number:int)->bytes:
    """converte a number like 1234(=0x04d2) - b"\x04\xd2"> """
    size = len(hex(number))
    return number.to_bytes((size//2-1) + size%2, "big")






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








class Pointer(Generic[_T]):
    def __init__(self, value:"_T"=...)->None:
        self.__setted:bool = False
        if value is not ...:
            self.__value:"_T" = value
            self.__setted = True

    @property
    def value(self)->"_T":
        if self.__setted is True:
            return self.__value
        else: raise ValueError("the pointer is not setted, cant get the value")
    @value.setter
    def value(self, value:"_T")->None:
        self.__value = value
        self.__setted = True

    def unSet(self)->None:
        self.__setted = False
        del self.__value


    def isSetted(self)->bool:
        return self.__setted

    def __str__(self)->str:
        return f"{self.__class__.__name__}({str(self.value)})"

    def __repr__(self)->str:
        return f"{self.__class__.__name__}({repr(self.__value) if self.__setted is True else ''})"


_Contexts = TypeVarTuple("_Contexts") # NOTE: can't be bound to contexts only:(
class MultiContext(tuple, ContextManager, Generic[Unpack[_Contexts]]):
    def __new__(cls, *contexts:"Unpack[_Contexts]")->Self:
        if any(not isinstance(ctx, ContextManager) for ctx in contexts):
            raise TypeError("some of the given elements in `contexts` are not of type `ContextManager`")
        return super(MultiContext, cls).__new__(cls, contexts)

    def __enter__(self)->Self:
        for context in self:
            context.__enter__()
        return self

    def __exit__(self, *args, **kwargs)->None:
        for context in reversed(self):
            context.__exit__(*args, **kwargs)




_Tuple = TypeVar("_Tuple", bound=tuple)
def editTuple(oldTuple:"_Tuple", editAtIndex:int, newValue, checkType:bool=False)->"_Tuple":
    """`checkType` only check that the type of teh new value is an instance of the type of the old value"""
    if checkType is True:
        oldValue = oldTuple[editAtIndex]
        if isinstance(newValue, type(oldValue)) is False:
           raise TypeError(f"the type of the new value({type(newValue)}) is not an instance of the type of the old value({type(oldValue)})")

    return tuple( # type:ignore can be checked before with checkType=True
        (oldValue if index != editAtIndex else newValue)
        for (index, oldValue) in enumerate(oldTuple)
    )





def assertIsinstance(value:Any, type_:"type[_T]")->_T:
    """assert the type of value using assert isinstance(...), ... \n
    NOTE: using -OO makes this func equaivalent to cast(...)"""
    assert isinstance(value, type_), TypeError(f"the type if value: {type(value)} isn't an instance of type_={type_}")
    return value
    