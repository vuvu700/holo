from typing import Iterator
from .__typing import Generic, TypeVar
from collections.abc import Mapping

_K = TypeVar("_K")
_V = TypeVar("_V")

class Groups(Mapping[_K, _V]):
    """to handle grouping values for different keys\
    the value is shared by all the keys of the group\\
    if using `strict` mode, adding twice a key will case a KeyError"""
    __slots__ = ("__keysGroups", "__valuesGroups", "__nextGrpID", "__strict")
    
    def __init__(self, content:"dict[tuple[_K, ...], _V]|None"=None, strict:bool=True) -> None:
        self.__nextGrpID: int = 0
        self.__keysGroups: "dict[_K, int]" = {}
        self.__valuesGroups: "dict[int, _V]" = {}
        self.__strict: bool = strict
        if content is not None:
            self.addGroups(content=content)
        
    def addGroups(self, content:"dict[tuple[_K, ...], _V]") -> None:
        """create new groups with the given keys"""
        for grpKeys, value in content.items():
            grpID = self.__nextGrpID
            self.__nextGrpID += 1
            self.__valuesGroups[grpID] = value
            for key in grpKeys:
                if (self.__strict is True) and (key in self.__keysGroups):
                    raise KeyError(f"the key: {key!r} was alredy added")
                self.__keysGroups[key] = grpID
    
    def __getitem__(self, key: _K) -> _V:
        return self.__valuesGroups[self.__keysGroups[key]]
    
    def __iter__(self) -> Iterator[_K]:
        return self.__keysGroups.__iter__()
    
    def __len__(self) -> int:
        return self.__keysGroups.__len__()

