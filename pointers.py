
from holo.protocols import _T, SupportsIndex

from holo.__typing import (
    Generic, Iterator, Iterable, MutableSequence,
)




class Pointer(Generic[_T]):
    def __init__(self, value:"_T"=...)->None: # type: ignore -> the unkown state is whanted when no default value is given
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



class ListPointer(Generic[_T]):
    """
    a = ListPointer([1, 2, 3, 4])
    -> list(a+1) == [2, 3, 4]
    """
    __slots__ = ("base", "__start")
    def __init__(self, __list:"MutableSequence[_T]|None"=None, *, start:int=0) -> None:
        if __list is None: __list = []
        self.base:"MutableSequence[_T]" = __list
        self.__start:int = start
    
    def _internal__getNewPos(self, relativeIndex:int)->int:
        """the new position of the index relative to the current start/stop\n
        return value is bounded to the start/stop (nor lower or bigger)"""
        if relativeIndex >= 0: 
            # => from the start
            return min(self.__start + relativeIndex, len(self.base))
        # => (relativeIndex < 0) => from the end
        else: return max(len(self.base) + relativeIndex, self.__start)
    
    def __add__(self, __value:"int")->"ListPointer[_T]":
        if isinstance(__value, int):
            return ListPointer(
                self.base, start=self._internal__getNewPos(__value))
        else: return NotImplemented
    
    def __len__(self)->int:
        return max(0, len(self.base) - self.__start)
    
    def __iter__(self)->Iterator[_T]:
        fastLst:"MutableSequence[_T]" = self.base
        return (fastLst[index] for index in range(self.__start, len(fastLst)))
    
    def __getitem__(self, __i:SupportsIndex)->"_T":
        return self.base[self._internal__getNewPos(int(__i))]

    def __setitem__(self, __key:SupportsIndex, __value:"_T")->None:
        self.base[self._internal__getNewPos(int(__key))] = __value

    def copy(self)->"list[_T]":
        res = self.base[self.__start: ]
        if isinstance(res, list):
            return res
        return list(res)
    
    def append(self, __object: _T) -> None:
        self.base.append(__object)
        
    def extend(self, __iterable:"Iterable[_T]") -> None: 
        self.base.extend(__iterable)
    
    def pop(self, __index:"SupportsIndex"=-1) -> _T:
        return self.base.pop(self._internal__getNewPos(int(__index)))