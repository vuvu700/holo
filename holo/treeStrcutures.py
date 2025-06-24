from holo.__typing import (
    Any, Sequence, Iterator, Iterable,
    Generic, Generator, Callable, overload, cast,
)
from holo.protocols import _T, _T2
from functools import reduce


_missing = object()


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



class RootTreeIter(Generic[_T]):
    """Root of TreeIter[_T]"""
    __slots__ = ("_leafs", "isSequenceEnd", "__length")
    def __init__(self, elements:"Iterable[Iterable[_T]]|None"=None)->None:
        self._leafs:"dict[_T, TreeIter[_T]]" = {}
        self.isSequenceEnd:bool = False
        self.__length:int = 0
        if elements is not None:
            for elt in elements: self.addElement(elt)
    
    def addElement(self, element:"Iterable[_T]")->bool:
        """add the `element` to the tree\n
        return if it was a new element"""
        iterator:Iterator[_T] = iter(element)
        try: firstValue:"_T" = next(iterator)
        except StopIteration: # => empty
            if not self.isSequenceEnd:
                self.__length += 1
                self.isSequenceEnd = True
                return True
            return False
        
        tree:"TreeIter[_T]|None" = self._leafs.get(firstValue, None)
        if tree is None: 
            self._leafs[firstValue] = \
                tree = TreeIter(firstValue, parent=self)
        if tree._internal_addItrerator(iterator):
            self.__length += 1
            return True
        return False
    
    def getAllElementsTree(self)->"Generator[TreeIter[_T], None, None]":
        """yield all the TreeIter that are end of sequence"""
        for node in self._leafs.values():
            yield from node.getAllElements()
    
    @overload
    def getAllElementsValue(self, *, valuesRootToLeaf:bool=True)->"Generator[Generator[_T, None, None], None, None]": ...
    @overload
    def getAllElementsValue(self, reduceFunc:"Callable[[_T, _T], _T]", *, valuesRootToLeaf:bool=True)->"Generator[_T, None, None]": ...
    @overload
    def getAllElementsValue(self, reduceFunc:"Callable[[_T2, _T], _T2]", reduceDefault:"_T2", *, valuesRootToLeaf:bool=True)->"Generator[_T2, None, None]": ...
    def getAllElementsValue(self, reduceFunc:"Callable[[_T2, _T], _T2]|Callable[[_T, _T], _T]|None"=None, reduceDefault:"_T2"=_missing, *, valuesRootToLeaf:bool=True)->"Generator[Generator[_T, None, None]|_T|_T2, None, None]":
        """yield all the values added\n
        `reduceFunc` None -> yield Generator[_T], Callable[..., _T|_T2] -> yield _T|_T2\n
        `reduceDefault` _missing -> use the first element of the sequence as initial to reduce\
            _T2 -> use it as initial to reduce\n
        `valuesRootToLeaf` True -> values from root to leafs (slower), \
            False -> values from leafs to root (faster)"""
        if reduceFunc is None:
            for elt in self.getAllElementsTree():
                yield elt.getValues(rootToLeaf=valuesRootToLeaf)
        elif reduceDefault is _missing:
            reduceFunc = cast(Callable[[_T, _T], _T], reduceFunc)
            for elt in self.getAllElementsTree():
                yield reduce(reduceFunc, elt.getValues(rootToLeaf=valuesRootToLeaf))
        else:
            reduceFunc = cast(Callable[[_T2, _T], _T2], reduceFunc)
            for elt in self.getAllElementsTree():
                yield reduce(reduceFunc, elt.getValues(rootToLeaf=valuesRootToLeaf), reduceDefault)
        
    __iter__ = getAllElementsValue
    
    
    def __contains__(self, element:"Iterable[_T]")->bool:
        iterator:Iterator[_T] = iter(element)
        try: firstValue:"_T" = next(iterator)
        except StopIteration: # => empty
            return self.isSequenceEnd
        
        tree:"TreeIter[_T]|None" = self._leafs.get(firstValue, None)
        return (tree is None) or tree.__contains__(iterator)

    def __len__(self)->int:
        return self.__length
    
    def __getitem__(self, key:"Iterable[_T]")->"TreeIter[_T]":
        iterator:"Iterator[_T]" = iter(key)
        firstValue:"_T" = next(iterator)
        tree:"TreeIter[_T]" = self._leafs[firstValue]._internal__getitem__(iterator)
        if not tree.isSequenceEnd:
            raise KeyError(key)
        return tree
    
class TreeIter(Generic[_T]):
    """A tree structure to store Iterables of Iterables (ex: list of str)"""
    __slots__ = ("value", "isSequenceEnd", "_leafs", "parent", "__length")
    def __init__(self, value:"_T", parent:"TreeIter[_T]|RootTreeIter[_T]")->None:
        self.value:"_T" = value
        self.isSequenceEnd:bool = False
        self._leafs:"dict[_T, TreeIter[_T]]" = {}
        self.parent = parent
        self.__length:int = 0
    
    def _internal_addItrerator(self, iterator:"Iterator[_T]")->bool:
        """add to the leafs the values of the iterator\n
        return if it was a new element"""
        try: nextValue:"_T" = next(iterator)
        except StopIteration: # => empty
            if not self.isSequenceEnd:
                self.__length += 1
                self.isSequenceEnd = True
                return True
            return False
        
        tree:"TreeIter[_T]|None" = self._leafs.get(nextValue, None)
        if tree is None: 
            self._leafs[nextValue] = \
                tree = TreeIter(nextValue, parent=self)
        if tree._internal_addItrerator(iterator):
            self.__length += 1
            return True
        return False
        
    
    def getAllElements(self)->"Generator[TreeIter[_T], None, None]":
        """yield all the TreeIter that are end of sequence"""
        if self.isSequenceEnd is True:
            yield self
        for leafTree in self._leafs.values():
            yield from leafTree.getAllElements()
    
    def getBranche(self)->"Generator[TreeIter[_T], None, None]":
        """yield all the TreeIter of the branche (leaf to root) \
        (consider self the leaf of the branche)"""
        node:"TreeIter[_T]|RootTreeIter[_T]" = self
        while isinstance(node, TreeIter):
            yield node
            node = node.parent
    
    def getValues(self, rootToLeaf:bool=True, _force:bool=False)->"Generator[_T, None, None]":
        """yield the values of this element\
        or raise a valueError if not the end of a sequence (and not forced)\n
        `rootToLeaf` True -> values from root to leaf (slower), \
            False -> from leaf to branche (faster)\n
        `_force` False -> raise ValueError when self isn't the end of a sequence\
            True -> return anyway"""
        if (self.isSequenceEnd is False) and (_force is False):
            raise ValueError("current node isn't a sequence's end")
        branche:"Iterable[TreeIter[_T]]" = self.getBranche()
        if rootToLeaf: 
            branche = reversed(list(branche))
        
        for node in branche:
            yield node.value

    def __contains__(self, element:"Iterable[_T]")->bool:
        iterator:Iterator[_T] = iter(element)
        try: nextValue:"_T" = next(iterator)
        except StopIteration: # => empty
            return self.isSequenceEnd
        
        tree:"TreeIter[_T]|None" = self._leafs.get(nextValue, None)
        return (tree is None) or tree.__contains__(iterator)

    def __getitem__(self, key:"Iterable[_T]")->"TreeIter[_T]":
        iterator:"Iterator[_T]" = iter(key)
        firstValue:"_T" = next(iterator)
        if firstValue != self.value:
            raise KeyError(key)
        return self._internal__getitem__(iterator)
        
    
    def _internal__getitem__(self, key:"Iterator[_T]")->"TreeIter[_T]":
        return self._leafs[next(key)]._internal__getitem__(key)
