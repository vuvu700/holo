__author__ = "Andrieu Ludovic"

from .__typing import (
    TypeVar, Any, TextIO, Literal, Iterable, NamedTuple,
    Generic, Unpack, TypeVarTuple, ContextManager, Self,
    overload, Iterator, Generator, assertIsinstance,
    Mapping, Callable, Tuple, )
from .dummys import DummyContext
from .prettyFormats import prettyPrint, prettyTime, _ObjectRepr, print_exception
from .treeStrcutures import Node_Words, RootTreeIter, TreeIter
from .pointers import Pointer, ListPointer
from .protocols import _T, _T2, SupportsIndex, Sized


_Contexts = TypeVarTuple("_Contexts") # NOTE: can't be bound to contexts only:(
_TypesTuple = TypeVarTuple("_TypesTuple")
_Tuple = TypeVar("_Tuple", bound=tuple)

_T_Key2 = TypeVar("_T_Key2")
_T_Key = TypeVar("_T_Key")
_T_Value2 = TypeVar("_T_Value2")
_T_Value = TypeVar("_T_Value")


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


def separate(elements:"Iterable[tuple[_T, _T2]]")->"tuple[list[_T], list[_T2]]":
    first: "list[_T]" = []
    second: "list[_T2]" = []
    for a, b in elements:
        first.append(a)
        second.append(b)
    return (first, second)


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
    exemple of pattern: `"abcde_[fg]_<v1:d>_ <v2:d> yte <v3>"` , will return {"v1":int(str), "v2":float(str)), "v3":str}
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
            if varType in ('f', 'd'): # type == 'f' or type == 'd'
                if (varValue_endIndex < len(string)) and (string[varValue_endIndex] == "-"): # consider negative numbers
                    varValue_endIndex += 1
                while (varValue_endIndex < len(string)) and (string[varValue_endIndex] in "0123456789"): # as long the number is int compatible
                    varValue_endIndex += 1

                if varType == 'd': # process the value to the dict as type=int
                    dictVars[varName] = int(string[varValue_startIndex: varValue_endIndex])

                elif varType == "f":
                    #test if it was interupted by a point
                    if (varValue_endIndex +1 < len(string)) and (string[varValue_endIndex] == '.'): 
                        varValue_endIndex += 1
                        # check that the point isn't the last char of the string -> continue searching
                        if (varValue_endIndex < len(string)-1): 
                            varValue_endIndex += 1
                            while (varValue_endIndex < len(string)) and (string[varValue_endIndex] in "0123456789"): # as long the number is int compatible
                                varValue_endIndex += 1
                    # process the value to the dict as type=float
                    dictVars[varName] = float(string[varValue_startIndex: varValue_endIndex])
                else: raise ValueError(f"invalide type format: {repr(varType)}")

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
        elif indexString == len(string): # => indexPattern != len(pattern)
            return (False, dictVars)
        # => indexString == len(string)
        raise RuntimeError(f"an error happend, it stopped with bad index: indexString={indexString}, indexPattern={indexPattern}") # bad developement

    return (False, dictVars)


def int_to_bytes(number:int)->bytes:
    """converte a number like 1234(=0x04d2) - b"\x04\xd2"> """
    return bytes.fromhex(hex(number)[2: ])




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




def editTuple(
        oldTuple:"_Tuple", editAtIndex:int,
        newValue:"_T", checkType:"bool|type[_T]"=False)->"_Tuple":
    """`checkType` only check that the type of the new value is an instance of \
        the type of the old value or the given type"""
    if checkType is not False:
        typeToCheck:type
        if checkType is True:
            typeToCheck = type(oldTuple[editAtIndex])
        else: # => type is given
            typeToCheck = checkType
        if isinstance(newValue, typeToCheck) is False:
           raise TypeError(f"the the new value (of type: {type(newValue)}) is not an instance of {typeToCheck}")

    return tuple( # type:ignore can be checked before with checkType=True
        (oldValue if index != editAtIndex else newValue)
        for (index, oldValue) in enumerate(oldTuple)
    )





def rawInput(__size:int)->bytes:
    try: import msvcrt
    except: raise ImportError(f"currently only available for windows")
    if __size == 0:
        return b""
    # => using a buffer like that gives you concat with up to 256 long bytes
    #   and only ~ x1.2 more memory than simple bytes (for large sizes)
    BLOCKS_SIZE = 256
    buffers:"list[bytes]" = [b""]
    trueSize:int = 0
    while (__size is None) or (trueSize < __size):
        char:bytes = msvcrt.getch()
        if char == b'\x03': # => ctrl + C
            raise KeyboardInterrupt
        else: # append the char
            msvcrt.putch(char)
            lastBuffer:bytes = buffers[-1]
            if len(lastBuffer) < BLOCKS_SIZE:
                buffers[-1] = lastBuffer + char
            else: buffers.append(char)
            trueSize += 1
    msvcrt.putch(b"\n")
    return b"".join(buffers)



def iterateNtimes(__iterable:Iterable[_T], maxNbYields:int)->Generator[_T, None, None]:
    """yield up to `maxNbYields` elements from the `__iterable`"""
    yieldCount:int = 0
    for element in __iterable:
        yield element
        
        yieldCount += 1
        if yieldCount == maxNbYields: # => finished
            return None
        

def nbDigits(num:int)->int:
    """return the number of digits of `num`\n
    notes:
     - for negative `num` return 1+nbDigits(abs(`num`)) because of the '-' in front
     - nbDigits(0) = 1"""
    nbDig:int = 1
    if num < 0:
        nbDig += 1
        num = abs(num)
    while num >= 10:
        num //= 10
        nbDig += 1
    return nbDig


class IterableSized(Generic[_T]):
    __slots__ = ("elements", "size")
    def __init__(self, elements:"Iterable[_T]", size:int) -> None:
        self.elements = elements
        self.size = size
    def __iter__(self): return iter(self.elements)
    def __len__(self): return self.size


def getDuplicated(allItems:"Iterable[_T]")->"set[_T]":
    encountered: "set[_T]" = set()
    duplicated: "set[_T]" = set()
    for item in allItems:
        if item not in encountered:
            encountered.add(item)
        else: duplicated.add(item)
    return duplicated

def filterDuplicated(allItems:"Iterable[_T]")->"list[_T]":
    newList: "list[_T]" = []
    encountered: "set[_T]" = set()
    for item in allItems:
        if item not in encountered:
            # => first time seeing it
            encountered.add(item)
            newList.append(item)
        # else: => duplicated
    return newList

def batched(elements:"Iterable[_T]", batchSize:int)->"list[list[_T]]":
    all_batch: "list[list[_T]]" = []
    batch: "list[_T]" = []
    for elt in elements:
        if len(batch) == batchSize:
            # => batch is full, start a new batch
            all_batch.append(batch)
            batch = []
        batch.append(elt)
    if len(batch) != 0:
        all_batch.append(batch)
    del batch # either empty or alredy added
    return all_batch


def flatten(elts:"Iterable[Iterable[_T]]")->"Iterator[_T]":
    for elt in elts:
        yield from elt


class MapDict(Iterator[Tuple[_T_Key, _T_Value]]):
    __slots__ = ("__func", "__iterator", )
    __func: "Callable[[Any, Any], tuple[_T_Key, _T_Value]]"
    """(key, value) -> (newKey, newValue)"""
    __iterator: "Iterator[tuple[Any, Any]]"
    """iterator[(key, value)]"""
    
    def __new__(cls, func:"Callable[[_T_Key2, _T_Value2], tuple[_T_Key, _T_Value]]", 
                mapping:"Mapping[_T_Key2, _T_Value2]")->Self:
        self = object.__new__(cls) # avoid to use Generic.__new__
        self.__func = func
        self.__iterator = iter(mapping.items())
        return self
    
    def __next__(self)->"tuple[_T_Key, _T_Value]":
        return self.__func(*self.__iterator.__next__())
    
    def __iter__(self)->"Self":
        return self
    
    def toDict(self)->"dict[_T_Key, _T_Value]":
        return {newKey: newVal for (newKey, newVal) in self}


class MapDict2(Generic[_T_Key, _T_Key2, _T_Value, _T_Value2]):
    __slots__ = ("__func", )
    __func: "Callable[[_T_Key, _T_Value], tuple[_T_Key2, _T_Value2]]"
    """(key, value) -> (newKey, newValue)"""
    
    def __new__(cls, func:"Callable[[_T_Key, _T_Value], tuple[_T_Key2, _T_Value2]]")->Self:
        self = object.__new__(cls) # avoid to use Generic.__new__
        self.__func = func
        return self
    
    def __call__(self, mapping:"Mapping[_T_Key, _T_Value]")->"dict[_T_Key2, _T_Value2]":
        return dict(*(self.__func(*keyVal) for keyVal in mapping.items()))



class MapDictValues(Iterator[Tuple[_T_Key, _T_Value]]):
    __slots__ = ("__func", "__iterator", )
    __func: "Callable[[Any], _T_Value]"
    """(value) -> newValue"""
    __iterator: "Iterator[tuple[_T_Key, Any]]"
    """iterator[(key, value)]"""
    
    def __new__(cls, func:"Callable[[_T_Value2], _T_Value]", 
                mapping:"Mapping[_T_Key, _T_Value2]")->Self:
        self = object.__new__(cls) # avoid to use Generic.__new__
        self.__func = func
        self.__iterator = iter(mapping.items())
        return self
    
    def __next__(self)->"tuple[_T_Key, _T_Value]":
        key, value = self.__iterator.__next__()
        return (key, self.__func(value))
    
    def __iter__(self)->"Self":
        return self
    
    def toDict(self)->"dict[_T_Key, _T_Value]":
        return {newKey: newVal for (newKey, newVal) in self}


class MapDictValues2(Generic[_T_Value, _T_Value2]):
    __slots__ = ("__func", )
    __func: "Callable[[_T_Value], _T_Value2]"
    """(value) -> newValue"""
    
    def __new__(cls, func:"Callable[[_T_Value], _T_Value2]")->Self:
        self = object.__new__(cls) # avoid to use Generic.__new__
        self.__func = func
        return self
    
    def __call__(self, mapping:"Mapping[_T_Key, _T_Value]")->"dict[_T_Key, _T_Value2]":
        return {key: self.__func(val) for (key, val) in mapping.items()}


class MapDictKeys(Iterator[Tuple[_T_Key, _T_Value]]):
    __slots__ = ("__func", "__iterator", )
    __func: "Callable[[Any], _T_Key]"
    """(value) -> newValue"""
    __iterator: "Iterator[tuple[Any, _T_Value]]"
    """iterator[(key, value)]"""
    
    def __new__(cls, func:"Callable[[_T_Key2], _T_Key]", 
                mapping:"Mapping[_T_Key2, _T_Value]")->Self:
        self = object.__new__(cls) # avoid to use Generic.__new__
        self.__func = func
        self.__iterator = iter(mapping.items())
        return self
    
    def __next__(self)->"tuple[_T_Key, _T_Value]":
        key, value = self.__iterator.__next__()
        return (self.__func(key), value)
    
    def __iter__(self)->"Self":
        return self
    
    def toDict(self)->"dict[_T_Key, _T_Value]":
        return {newKey: newVal for (newKey, newVal) in self}


class MapDictKeys2(Generic[_T_Key, _T_Key2]):
    __slots__ = ("__func", )
    __func: "Callable[[_T_Key], _T_Key2]"
    """(value) -> newValue"""
    
    def __new__(cls, func:"Callable[[_T_Key], _T_Key2]")->Self:
        self = object.__new__(cls) # avoid to use Generic.__new__
        self.__func = func
        return self
    
    def __call__(self, mapping:"Mapping[_T_Key, _T_Value]")->"dict[_T_Key2, _T_Value]":
        return {self.__func(key): val for (key, val) in mapping.items()}

