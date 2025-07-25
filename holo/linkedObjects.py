import random, math
import warnings

from .__typing import (
    Generic, Iterable, Generator, Iterator,
    overload, Literal, cast, Callable, 
    FinalClass, TypeVar, Self, override,
    assertIsinstance, Sequence,
)
from .protocols import (
    _T, _T2, SupportsLowersComps, SupportsSort, SupportsIndex)
from .prettyFormats import _ObjectRepr

class EmptyError(Exception):
    """when an invalid action was tryed on an empty object"""


class Node(Generic[_T]):
    __slots__ = ("value", "next", "prev")
    def __init__(self, 
            value:"_T", next:"Node[_T]|None"=None, 
            prev:"Node[_T]|None"=None)->None:
        self.value:"_T" = value
        self.next:"Node[_T]|None" = next
        self.prev:"Node[_T]|None" = prev

    def __next__(self)->"_T":
        if self.next is not None:
            return self.next.value
        raise StopIteration()

    def __prev__(self)->"_T":
        if self.prev is not None:
            return self.prev.value
        raise StopIteration()

    def __iter__(self)->"Generator[_T, None, None]":
        node:"Node[_T]|None" = self
        while node is not None:
            yield node.value
            node = node.next

    def __call__(self)->"_T":
        return self.value


class NodeDCycle(Node[_T]):
    """a subClass of Node that are allways linked, as a double cycle"""
    def __init__(self, value:"_T", next:"NodeDCycle[_T]|None", prev:"NodeDCycle[_T]|None")->None:
        """`next` / `prev` setted to None will designate to `self`"""
        self.value:"_T" = value
        # bind next
        self.next:"NodeDCycle[_T]"
        if next is None: # => link to self
            self.next = self
        else: # => link to custom
            self.next = next
            next.prev = self
        # bind prev
        self.prev:"NodeDCycle[_T]"
        if prev is None: # => link to self
            self.prev = self
        else: # => link to custom
            self.prev = prev
            prev.next = self

    def detatche(self)->"NodeDCycle[_T]":
        """detache the node of its .prev and its .next, and make it loop on itself\n
        old .prev and .next will be linked toogether according to the initial .prev and .next\n
        return initial self.next"""
        # relink prev and next toogether
        next:"NodeDCycle[_T]"
        next = self.prev.next = self.next
        self.next.prev = self.prev
        # make self loop on itself
        self.next = self.prev = self
        return next


class NodeAuto(Node[_T]):
    """this sub class of Node will automaticaly attach the prev/next to self"""
    __slots__ = ()
    def __init__(self, 
            value:"_T", next:"NodeAuto[_T]|None"=None, 
            prev:"NodeAuto[_T]|None"=None)->None:
        self.value: "_T" = value
        self.next: "NodeAuto[_T]|None" = next
        self.prev: "NodeAuto[_T]|None" = prev
        if next is not None: next.prev = self
        if prev is not None: prev.next = self


class LinkedList(Generic[_T]):
    __slots__ = ("__start", "__end", "__length")
    def __init__(self, __initial:"Iterable[_T]|None"=None) -> None:
        """if `__initial` is given append all its values"""
        self.__start:"Node[_T]|None" = None
        self.__end:"Node[_T]|None" = None
        self.__length:int = 0
        if __initial is not None:
            for value in __initial:
                self.append(value)
    
    def insert(self, value:"_T")->None:
        """insert at the start"""
        if self.__start is None:
            # => empty
            self.__start = Node(value)
            self.__end = self.__start
            self.__length = 1
        else:
            # => have some nodes
            self.__start = Node(value, next=self.__start)
            self.__length += 1
    
    def append(self, value:"_T")->None:
        """append at the end"""
        if self.__end is None:
            # => empty => end = start = None
            self.__start = Node(value)
            self.__end = self.__start
            self.__length = 1
        else:
            # => have some nodes
            currentEnd:"Node[_T]" = self.__end
            self.__end = currentEnd.next = Node(value)
            self.__length += 1
    
    @overload
    def pop(self, ensure:Literal[False])->"_T|None": ...
    @overload
    def pop(self, ensure:Literal[True]=True)->"_T": ...
    def pop(self, ensure:bool=True)->"_T|None":
        """pop the first value (raise EmptyError when empty)\n
        return None when empty and `ensure` is False"""
        if self.__start is None:
            # => empty => no value
            if ensure is False:
                return None
            else: raise EmptyError("no start value: is empty")
        # => not empty
        poppedValue:"_T" = self.__start.value
        self.__start = self.__start.next
        if self.__start is None:
            # => only had one value => re become empty
            self.__end = None
            # => (self.__start is None) and (self.__end is None) => empty
        self.__length -= 1
        return poppedValue
    
    def clear(self)->None:
        """remove all values\n
        (don't edit the nodes, O(1))"""
        self.__start = None
        self.__end = None
        self.__length = 0

    @property
    def isEmpty(self)->bool:
        """tell whether it is empty"""
        return self.__start is None
    
    def popAll(self)->"Generator[_T, None, None]":
        while self.__start is not None:
            yield self.pop()

    @overload
    def startValue(self, ensure:Literal[False])->"_T|None": ...
    @overload
    def startValue(self, ensure:Literal[True]=True)->"_T": ...
    def startValue(self, ensure:bool=True)->"_T|None":
        """get the first value (raise EmptyError when empty)\n
        return None when empty and `ensure` is False"""
        if self.__start is None:
            # => empty => no value
            if ensure is False:
                return None
            else: raise EmptyError("no start value: is empty")
        # => not empty
        return self.__start.value
    
    @overload
    def endValue(self, ensure:Literal[False])->"_T|None": ...
    @overload
    def endValue(self, ensure:Literal[True]=True)->"_T": ...
    def endValue(self, ensure:bool=True)->"_T|None":
        """get the last value (raise EmptyError when empty)\n
        return None when empty and `ensure` is False"""
        if self.__end is None:
            # => empty => no value
            if ensure is False:
                return None
            else: raise EmptyError("no end value: is empty")
        # => not empty
        return self.__end.value
    
    def __len__(self)->int:
        return self.__length
    
    def __iter__(self)->"Generator[_T, None, None]":
        if self.__start is None:
            # => empty
            return None
        # => not empty
        yield from iter(self.__start)
    
    def __str__(self)->str:
        return f"{self.__class__.__name__}({' -> '.join(map(str, iter(self)))})"
    def __repr__(self)->str:
        return f"{self.__class__.__name__}([{', '.join(map(repr, iter(self)))}])"

class Stack(LinkedList[_T]):
    # debind some methodes
    append:None = None
    endValue:None = None

class Queue(LinkedList[_T]):
    # debind some methodes
    insert:None = None
    endValue:None = None



class DCycle(Generic[_T]):
    """double dirrection cycle"""
    __slots__ = ("__current", "__length")
    def __init__(self, __initial:"Iterable[_T]|None"=None) -> None:
        """if `__initial` is given append all its values"""
        self.__current:"NodeDCycle[_T]|None" = None
        self.__length:int = 0
        if __initial is not None:
            for value in __initial:
                self.append(value)

    def insert(self, value:"_T")->None:
        """insert at the start, move the old current to next"""
        if self.__current is None:
            # => empty
            self.__current = NodeDCycle(value, None, None)
            # => (itself) <-> (current) <-> (itself)
        else: # => not empty
            self.__current = NodeDCycle(
                value, 
                prev=self.__current.prev, # => (old current's prev) <-> (new current)
                next=self.__current, # => (new current) <-> (old current)
            )
            # => (old current's prev) <-> (new current) <-> (old current)
        self.__length += 1

    def append(self, value:"_T")->None:
        """append at the end, new prev of current"""
        if self.__current is None:
            # => empty
            self.__current = NodeDCycle(value, None, None)
        else: # => not empty
            self.__current.prev = NodeDCycle(
                value,
                prev=self.__current.prev, # => (old current's prev) <-> (new current's prev)
                next=self.__current, # => (new current's prev) <-> (current)
            )
            # => (old current's prev) <-> (new current's prev) <-> (current)
        self.__length += 1
    
    @overload
    def pop(self, ensure:Literal[False])->"_T|None": ...
    @overload
    def pop(self, ensure:Literal[True]=True)->"_T": ...
    def pop(self, ensure:bool=True)->"_T|None":
        """pop the current value (raise EmptyError when empty)\n
        return None when empty and `ensure` is False"""
        if self.__current is None:
            # => empty => no value
            if ensure is False:
                return None
            else: raise EmptyError("the cycle is empty")
        # => not empty
        currentNode:"Node[_T]" = self.__current
        poppedValue:"_T" = currentNode.value
        if self.__length == 1:
            # detatching a 1 node cycle relink to itself
            self.__current = None
            self.__length = 0
            return poppedValue 
        
        # length > 1 => current.next is not current
        self.__current = self.__current.detatche()        
        self.__length -= 1
        
        return poppedValue

    def popAll(self)->"Generator[_T, None, None]":
        while self.__current is not None:
            yield self.pop()

    @overload
    def currentValue(self, ensure:Literal[False])->"_T|None": ...
    @overload
    def currentValue(self, ensure:Literal[True]=True)->"_T": ...
    def currentValue(self, ensure:bool=True)->"_T|None":
        """get the current value (raise EmptyError when empty)\n
        return None when empty and `ensure` is False"""
        if self.__current is None:
            # => empty => no value
            if ensure is False:
                return None
            else: raise EmptyError("the cycle is empty")
        # => not empty
        return self.__current.value

    def clear(self)->None:
        """remove all values\n
        (don't edit the nodes, O(1))"""
        self.__current = None
        self.__length = 0

    @property
    def isEmpty(self)->bool:
        """tell whether it is empty"""
        return self.__current is None

    def __len__(self)->int:
        return self.__length
    
    def rotate1(self, forward:bool=True, ensure:bool=True)->None:
        """rottate the cycle (raise EmptyError when empty)\n
        return None when empty and `ensure` is False"""
        if self.__current is None:
            # => empty
            if ensure is False:
                return None
            else: raise EmptyError("can't rotate an empty cycle")
        # => not empty
        if forward is True:
            self.__current = self.__current.next
        else: self.__current = self.__current.prev
    
    def rotate(self, moves:int=1, ensure:bool=True, force:bool=False)->int:
        """rotate the cycle (raise EmptyError when empty)\n
         - positive move => rotate forward\n
         - negative move => rotate backward\n
        when `force` is False (default), \
            optimize the rotation to do the least amount of moves: \n
        \t  can choose to go in the opposite direction, ignore loops\n
        return the true amount of moves done (=> 0 when empty and `ensure` is False)"""
        # compute the amount of moves to be done
        direction:bool
        """True <=> forward"""
        if force is False:
            direction = True
            moves = moves % self.__length # forward moves
            if moves > (self.__length - moves):
                moves = -(self.__length - moves) # backward moves
                direction = False
        else:
            direction = (moves >= 0)
            moves = abs(moves)
        
        if self.__current is None:
            # => empty
            if ensure is False:
                return 0
            else: raise EmptyError("can't rotate an empty cycle")

        # => not empty
        # execute the moves
        for _ in range(abs(moves)):
            if direction: # don't use "is True" for a little perf gain
                self.__current = self.__current.next
            else: self.__current = self.__current.prev
        return moves

    def __iter__(self)->"Generator[_T, None, None]":
        if self.__current is None:
            # => empty
            return None
        # => not empty
        startNode:"Node[_T]" = self.__current
        yield startNode.value
        node:"Node[_T]" = startNode.next
        while (node is not startNode):
            yield node.value
            node = node.next

    def __str__(self)->str:
        return f"{self.__class__.__name__}({' <-> '.join(map(str, iter(self)))} <->)"
    def __repr__(self)->str:
        return f"{self.__class__.__name__}([{', '.join(map(repr, iter(self)))}])"




class NoHistoryError(Exception):
    """no history is available"""

class _HistoryNode(NodeAuto[_T]):
    __NB_NODES_CREATED: int = 0
    __slots__ = ("ID", )
    next: "_HistoryNode|None"
    prev: "_HistoryNode|None"
    
    def __init__(self, value:"_T", next:"_HistoryNode|None"=None,
                 prev:"_HistoryNode|None"=None) -> None:
        super().__init__(value, next, prev)
        self.ID = _HistoryNode.__NB_NODES_CREATED
        _HistoryNode.__NB_NODES_CREATED += 1
    
class History(Generic[_T]):
    __slots__ = ("__values", "__NULL_HIST", )
    
    def __init__(self, valuesType:"type[_T]|None"=None) -> None:
        """create an empty history (`valuesType` isn't used, on here for type annotation)"""
        self.__NULL_HIST: "_HistoryNode[_T]" = _HistoryNode(...)
        self.__values: "_HistoryNode[_T]" = self.__NULL_HIST
        """all the values, prev/current elements are the values to revert to, 
        next values are the ones to redo\ncurrent Node is the last value """
    
    def getEmptyHistID(self)->int:
        return self.__NULL_HIST.ID
    
    def getCurrentNodeID(self)->int:
        """return the ID of the currently targted node"""
        return self.__values.ID
    
    def addCheckpoint(self, value:"_T")->None:
        """add the given config to the history"""
        if self.__values is self.__NULL_HIST:
            # => no current actions
            prev = self.__NULL_HIST
        else: # => drop the redo action
            self.__values.next = None 
            # add the action in front of the old action
            prev = self.__values
        self.__values = _HistoryNode(value, prev=prev)
        
    def undoOne(self)->"_T":
        """return the value undone, 
        raise a NoHistoryError if there is no history available"""
        if self.__values is self.__NULL_HIST:
            raise NoHistoryError("there is no history to revert")
        # => revert
        value: "_T" = self.__values.value
        assert self.__values.prev is not None
        self.__values = self.__values.prev
        return value
        
    def redoOne(self)->"_T":
        """retunr the redone value, 
        raise a NoHistoryError if there is no history available"""
        if self.__values.next is None:
            raise NoHistoryError("there is no history to redo")
        # => redo
        value: "_T" = self.__values.next.value
        self.__values = self.__values.next
        return value

    def clearHistory(self)->None:
        self.__init__()

    def __get_allToRedo(self)->"list[_T]":
        values: "list[_T]" = []
        hist = self.__values.next
        while hist is not None:
            values.append(hist.value)
            hist = hist.next
        values.reverse()
        return values

    def __get_allToRevert(self)->"list[_T]":
        if self.__values is None:
            return []
        actions: "list[_T]" = []
        hist = self.__values
        while hist is not self.__NULL_HIST:
            assert hist is not None
            actions.append(hist.value)
            hist = hist.prev
        return actions

    def __pretty__(self, *_, **__)->"_ObjectRepr":
        return _ObjectRepr(self.__class__.__name__, 
            args=("timeline: |done after <- done before|", ),
            kwargs={"toRedo": self.__get_allToRedo(), 
                    "toRevert": self.__get_allToRevert()})






class SMALLEST(): 
    def __lt__(self, __other:object)->bool: return True
    def __le__(self, __other:object)->bool: return True
    # => __eq__ = object.__eq__

class BIGGEST(): 
    def __lt__(self, __other:object)->bool: return False
    def __le__(self, __other:object)->bool: return False
    # => __eq__ = object.__eq__


_T_key = TypeVar("_T_key", bound=SupportsLowersComps)


# HEAD <->   <->   <->   <->   <->   <->  <-> NIL
# HEAD <->   <->   <-> 3 <->   <->   <->  <-> NIL
# HEAD <->   <->   <-> 3 <->   <->   <-> 6 -> NIL
# HEAD <->   <-> 2 <-> 3 <->   <-> 5 <-> 6 -> NIL
# HEAD <->   <-> 2 <-> 3 <-> 4 <-> 5 <-> 6 -> NIL
# HEAD <-> 1 <-> 2 <-> 3 <-> 4 <-> 5 <-> 6 -> NIL

#[HEAD]<->   <->   <->   <->   <->   <->   <->   <-> NIL
# HEAD <->   <->   <->[3]<->   <->   <->   <->   <-> NIL
# HEAD <->   <->   <->[3]<->   <->   <->   <-> 6 <-> NIL
# HEAD <->   <-> 2 <-> 3 <->   <->   <->[5]<-> 6 <-> NIL
# HEAD <->   <-> 2 <-> 3 <->   <-> 4 <->[5]<-> 6 <-> NIL
# HEAD <-> 1 <-> 2 <-> 3 <-> 4 <-> 4 <->[5]<->(6)<-> NIL

#                               11                                               
# o---------------------------------------------------------------> o    Top level
#   1           3              2                    5                             
# o---> o---------------> o---------> o---------------------------> o    Level 3
#   1        2        1        2              3              2                       
# o---> o---------> o---> o---------> o---------------> o---------> o    Level 2
#   1     1     1     1     1     1     1     1     1     1     1                     
# o---> o---> o---> o---> o---> o---> o---> o---> o---> o---> o---> o    Bottom level
# Head  1st   2nd   3rd   4th   5th   6th   7th   8th   9th   10th  NIL

# HEAD <->   <->   <->   <->   <->   <->   <->   <->   <->   <->    <-> NIL
# HEAD <-> 1 <->   <->   <-> 4 <->   <-> 6 <->   <->   <->   <->    <-> NIL
# HEAD <-> 1 <->   <-> 3 <-> 4 <->   <-> 6 <->   <->   <-> 9 <->    <-> NIL
# HEAD <-> 1 <-> 2 <-> 3 <-> 4 <-> 5 <-> 6 <-> 7 <-> 8 <-> 9 <-> 10 <-> NIL


class Node_SkipList(Generic[_T, _T_key]):
    """just hold the values and the next elements"""
    __slots__ = ("element", "key", "prevs", "nexts", )
    # define the types of the attrs
    element: _T
    key: _T_key
    prevs: "list[Self]"
    nexts: "list[Self]"
        
    def __new__(cls, elt:"_T", key:"_T_key", height:int) -> Self:
        # don't use the __new__ of generic: slow
        # don't use the __setattr__ de FinalClass slow and obviously the first first time setting
        self = object.__new__(cls)
        object.__setattr__(self, "element", elt)
        object.__setattr__(self, "key", key)
        object.__setattr__(self, "nexts", [NotImplemented] * height)
        object.__setattr__(self, "prevs", [NotImplemented] * height)
        return self
        
    @classmethod
    def insertNewNodeAfter(cls, elt:"_T", key:"_T_key", height:int, nodesBefore:"list[Self]")->"Self":
        # doing so improves performance and it avoid all having ... elts in self.nexts
        newNode = object.__new__(cls)
        object.__setattr__(newNode, "element", elt)
        object.__setattr__(newNode, "key", key)
        object.__setattr__(newNode, "nexts", [])
        object.__setattr__(newNode, "prevs", [])
        # attache the nodes
        for level in range(height):
            newNode.prevs.append(nodesBefore[level])
            newNode.nexts.append(nodesBefore[level].nexts[level])
            nodesBefore[level].nexts[level] = newNode
            newNode.nexts[level].prevs[level] = newNode
        return newNode
    
    @property
    def height(self)->int:
        """user friendly way to get the height of the node :)"""
        return len(self.nexts)
    
    @property
    def nextNode(self)->"Self":
        """user friendly way to get the next node :)"""
        return self.nexts[0]
    
    @property
    def prevNode(self)->"Self":
        """user friendly way to get the previous node :)"""
        return self.prevs[0]
    
    def detatch(self, prevNodes:"list[Self]")->None:
        """detatch the node from the prevs/nexts \
        and clear the links of self (self.height will be 0)\n
        `prevNodes` is not used if it isn't an indexed node"""
        for level in range(self.height):
            nodeBefore = self.prevs[level]
            nodeAfter = self.nexts[level]
            nodeBefore.nexts[level] = nodeAfter
            nodeAfter.prevs[level] = nodeBefore
        # remove the acces to other nodes
        self.prevs.clear()
        self.nexts.clear()
 
    @classmethod
    def createHEAD(cls)->"Self":
        """create a HEAD and a TAIL connected together"""
        head: "Self" = cls(NotImplemented, height=0,
                           key=SMALLEST()) # type: ignore
        tail: "Self" = cls(NotImplemented, height=0,
                           key=BIGGEST()) # type: ignore
        head.nexts.append(tail)
        tail.prevs.append(head)
        return head
        

    def __str__(self) -> str:
        if self.element is self.key:
            return f"{self.__class__.__name__}(elt={self.element}, key is element, height={self.height})"
        return f"{self.__class__.__name__}(elt={self.element}, key={self.key}, height={self.height})"
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(element={repr(self.element)}, key={repr(self.key)}, height={repr(self.height)})"

    def __pretty__(self, *_, **__)->"_ObjectRepr":
        return _ObjectRepr(
            self.__class__.__name__, args=(),
            kwargs={"elt": self.element, "key": self.key, 
                    "height": self.height})



class Node_SkipList_indexed(Node_SkipList[_T, _T_key]):
    """just hold the values and the next elements"""
    __slots__ = ("widths", )
    # define the types of the attrs
    prevs: "list[Node_SkipList_indexed[_T, _T_key]]"
    nexts: "list[Node_SkipList_indexed[_T, _T_key]]"
    widths: "list[int]"
    
    @override
    def __new__(cls, elt:"_T", key:"_T_key", height:int) -> Self:
        newNode: "Self" = super().__new__(cls, elt, key, height)
        object.__setattr__(newNode, "widths", [NotImplemented] * height)
        return newNode
    
    @override
    @classmethod
    def insertNewNodeAfter(cls, elt:"_T", key:"_T_key", height:int, nodesBefore:"list[Self]")->"Self":
        newNode: "Self" = super().insertNewNodeAfter(elt, key, height, nodesBefore)
        object.__setattr__(newNode, "widths", [NotImplemented] * height)
        # update the widths of the prevs and self (nexts don't needs it)
        newNode._updateWidths([newNode] * height) # update self
        newNode._updateWidths(nodesBefore) # update the prevs
        return newNode
    
    
    
    def detatch(self, prevNodes:"list[Self]")->None:
        super().detatch(prevNodes)
        self.widths.clear()
        # update the widths of the prevs nodes (nexts don't needs it)
        self._updateWidths(prevNodes)
    
    def getIndex(self)->int:
        if self.height == 0:
            raise IndexError(f"can't compute the index of a node with no height")
        totalWidth: int = -1 
        # starts at -1 because it will count indexes from HEAD
        #   ie. the real index is 1 less than what is computed
        currentNode = self
        while len(currentNode.prevs) != 0:
            # because the only node expected to have 0 prevs is the HEAD
            # => (currentNode is not HEAD)
            level: int = (currentNode.height -1)
            currentNode = currentNode.prevs[level]
            totalWidth += currentNode.widths[level]
        return totalWidth
    
    

    def _updateWidths(self, nodes:"list[Self]")->None:
        """update the widths of given nodes (for each height)\n
        note: the prevs can be detached of self ()"""
        # the width at height == 0 always stay 1
        if len(nodes) == 0: 
            return # => nothing to update
        # => height >= 1
        # the width at height == 0 always stay 1
        nodes_iter = iter(nodes)
        next(nodes_iter).widths[0] = 1
        # update the width for the other heights
        for level, nodeToUpdate in enumerate(nodes_iter, start=1):
            nextNode = nodeToUpdate.nexts[level]
            curr = nodeToUpdate.nexts[level-1]
            width: int = nodeToUpdate.widths[level-1]
            while curr is not nextNode:
                width += curr.widths[level-1]
                curr = curr.nexts[level-1]
            nodeToUpdate.widths[level] = width
    
    @override
    @classmethod
    def createHEAD(cls)->"Node_SkipList_indexed":
        head = super().createHEAD()
        head.widths.append(1)
        return head
        
    def __str__(self) -> str:
        if self.element is self.key:
            return f"{self.__class__.__name__}(elt={self.element}, key is element, height={self.height}, widths={self.widths})"
        return f"{self.__class__.__name__}(elt={self.element}, key={self.key}, height={self.height}, widths={self.widths})"
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(element={repr(self.element)}, key={repr(self.key)}, height={repr(self.height)}, widths={self.widths})"
    
    @override
    def __pretty__(self, *_, **__) -> _ObjectRepr:
        objRepr = super().__pretty__(*_, **__)
        objRepr.kwargs["widths"] = self.widths
        return objRepr

class SkipList(Generic[_T, _T_key], Sequence):
    """a (stable) sorted list that have the following complexity:
     * add: O(log1/p(n)) *average*
     * remove/pop: O(log1/p(n)) *average*
     * getSublist: O(log1/p(n)) *average*
     * get next elment: O(1)
     * get at index: O(log1/p(n)) *average* [not implemented yet]
     * search key: O(log1/p(n)) *average*
    """
    __slots__ = ("__head", "__tail", "__probabilty", "__length", "__keyFunc", 
                 "__indexed", "__nodeClass", )
    
    def __init__(self, elements:"Iterable[_T]", eltToKey:"Callable[[_T], _T_key]", 
                 probability:float=1/4, indexed:bool=True,
                 addElementMethode:"Literal['extend', 'extend_sortInPlace', 'append']"="extend") -> None:
        """initialize the SkipList with the given element to key function and the given probability per layer\n
        `elements` are the first elements to be added and they will be added with the methode of `addElementMethode`\n
        note that `addElementMethode` only change how `elements` during the __init__, nothing else\n
        `indexed` is whether the operations on the indices are allowed, when desactivated it is much 2-3x faster"""
        if (probability <= 0) or (probability >= 1):
            raise ValueError(f"the probability: {probability} of the SkipList must be in ]0, 1[")
        if probability > 0.8:
            warnings.warn(f"be aware that using high probability ({probability} > 0.8) of new layers will create a lots of layers an tho slowing down the process")
        # select the correct class for the nodes
        self.__indexed: bool = indexed
        self.__nodeClass: "type[Node_SkipList[_T, _T_key]]" = \
            (Node_SkipList if indexed is False else Node_SkipList_indexed)
        
        self.__head: "Node_SkipList[_T, _T_key]" = self.__nodeClass.createHEAD()
        self.__tail: "Node_SkipList[_T, _T_key]" = self.__head.nextNode
        self.__length: int = 0
        self.__probabilty: float = probability
        self.__keyFunc: "Callable[[_T], _T_key]" = eltToKey
        # add the elements
        if addElementMethode == "extend":
            self.extend(elements)
        elif addElementMethode == "extend_sortInPlace":
            if not isinstance(elements, SupportsSort):
                raise TypeError(f"in order to use the `addElementMethode`: {addElementMethode}, `elements` must support the {SupportsSort} protocol")
            self.extend(elements, inPlaceSort=True)
        elif addElementMethode == "append":
            for elt in elements:
                self.append(elt)
        else: raise ValueError(f"invalide `addElementMethode`: {addElementMethode} parameter")
    
    @property
    def height(self)->int:
        return self.__head.height
    
    def __len__(self)->int:
        return self.__length
    
    @property
    def isIndexed(self)->bool:
        return self.__indexed
    
    ### add an element ###
    
    def __addElement(self, elt:"_T", firstOfKeys:bool)->None:
        """add a new element to the list:
         * firstOfKeys=True -> insert before all the same keys
         * firstOfKeys=False -> append after all the same keys"""
        newNode_height: int = self.__getNextHeight()
        elt_key: "_T_key" = self.__keyFunc(elt)
        self.__ensureHeight(newNode_height)
        insertionNodes: "list[Node_SkipList[_T, _T_key]]" = \
            self.__getLayersToKey(elt_key, beforeKey=firstOfKeys)
        self.__nodeClass.insertNewNodeAfter(
            elt, elt_key, newNode_height, insertionNodes)
        self.__length += 1
    def append(self, elt:"_T")->None:
        """insert the elt after all the elements with the same key"""
        self.__addElement(elt, firstOfKeys=False)    
    def insert(self, elt:"_T")->None:
        """insert the elt before all the elements with the same key"""
        self.__addElement(elt, firstOfKeys=True)
       
    @overload 
    def extend(self, elements:"SupportsSort[_T]", inPlaceSort:Literal[True])->None:
        """a faster an more efficient procedure to append multiple elements\n
        will sort the `elements` in place to avoid using more memory"""
    @overload
    def extend(self, elements:"Iterable[_T]")->None:
        """a faster an more efficient procedure to append multiple elements\n
        it will cache the elements in a list before inserting to speed up the process\n
        note: you can use the `inPlaceSort` parameter to avoid this issue"""

    def extend(self, elements:"Iterable[_T]", inPlaceSort:bool=False)->None:
        if inPlaceSort is True:
            # => must support sort and be iterable
            elements = cast("SupportsSort[_T]", elements)
            elements.sort(key=self.__keyFunc)
        else: # => don't sort in place
            elements = sorted(elements, key=self.__keyFunc)
        elements_iter: "Iterator[_T]" = iter(elements)
        # => they are now sorted (faster sort than using this structure)
        # get the nodes to insert after and insert this node 
        try: elt: _T = next(elements_iter)
        except StopIteration: return None # => no elements to add
        elt_key: "_T_key" = self.__keyFunc(elt)
        insertionNodes: "list[Node_SkipList[_T, _T_key]]" = \
            self.__getLayersToKey(elt_key, beforeKey=False)
        lastInsertedNode: "Node_SkipList[_T, _T_key]" = insertionNodes[0]
        """might be HEAD, never TAIL"""
        # insert the node here while it can
        while True:
            if lastInsertedNode.nexts[0].key <= elt_key:
                # => can't append after the current insertion nodes
                insertionNodes = self.__getLayersToKey(elt_key, beforeKey=False)
                # => now you can :)
            newNode_height: int = self.__getNextHeight()
            # len(insertionNodes) == self.height and it is faster than self.height
            if newNode_height > len(insertionNodes):
                # => extended the height, add some heads
                insertionNodes.extend([self.__head] * (newNode_height - len(insertionNodes)))
                self.__ensureHeight(newNode_height)
            self.__nodeClass.insertNewNodeAfter(elt, elt_key, newNode_height, insertionNodes)
            self.__length += 1
            lastInsertedNode = lastInsertedNode.nexts[0]
            # update the insertion nodes with the last inserted node
            for level in range(lastInsertedNode.height):
                insertionNodes[level] = lastInsertedNode
            # get the next element and get its key
            try: elt = next(elements_iter)
            except StopIteration: break # => added all elements
            elt_key = self.__keyFunc(elt)

    ### contain element/key ###

    def containKey(self, key:"_T_key")->bool:
        """tell whether there is an element with the same key inside the list"""
        try: # test if it can get a node with this key
            self.__getRemoveNodeFirst(key, removeNode=False)
            return True
        except KeyError: return False
    
    def __contains__(self, elt:"_T")->bool:
        """tell whether this element is inside the list"""
        key: _T_key = self.__keyFunc(elt)
        try: # try to get the first node with this key
            node: "Node_SkipList[_T, _T_key]" = \
                self.__getRemoveNodeFirst(key, removeNode=False)
        except KeyError: return False
        # find if one of the nodes with this key has the `elt`
        while node.key == key:
            if elt == node.element:
                return True
            node = node.nexts[0]
        return False
    
    ### utils to: get remove fetch pop nodes ###
    
    def __getRemoveNodeBefore(self, __key:"_T_key", removeNode:bool)->"Node_SkipList[_T, _T_key]":
        """get/remove the last node as: node.key < key, raise a KeyError there is no node before the key"""
        targetedNode: "Node_SkipList[_T, _T_key]" = \
            self.__getLayersToKey(__key, beforeKey=True)[0]
        # => last node as: targetedNode.key < key <= targetedNode.nexts[level].key
        if targetedNode is self.__head:
            raise KeyError(f"there is no node before the key: {__key}")
        if removeNode is True:
            targetedNode.detatch(([] if self.__indexed is False 
                                  else self.__internal_getNodesBefore(targetedNode)))
            self.__length -= 1
        return targetedNode
    def __getRemoveNodeAfter(self, __key:"_T_key", removeNode:bool)->"Node_SkipList[_T, _T_key]":
        """get/remove the first node as: key < node.key, raise a KeyError there is no node after the key"""
        nodesBefore: "list[Node_SkipList[_T, _T_key]]" = \
            self.__getLayersToKey(__key, beforeKey=False)
        targetedNode: "Node_SkipList[_T, _T_key]" = nodesBefore[0].nexts[0]
        # => first node as: key < targetedNode.key
        if targetedNode is self.__head:
            raise KeyError(f"there is no node before the key: {__key}")
        if removeNode is True:
            targetedNode.detatch(nodesBefore)
            self.__length -= 1
        return targetedNode
    def __getRemoveNodeFirst(self, __key:"_T_key", removeNode:bool)->"Node_SkipList[_T, _T_key]":
        """get/remove the first node with the same key, raise a KeyError if the key don't exist"""
        nodesBefore: "list[Node_SkipList[_T, _T_key]]" = \
            self.__getLayersToKey(__key, beforeKey=True)
        targetedNode: "Node_SkipList[_T, _T_key]" = \
            nodesBefore[0].nexts[0]
        # => first node as: key <= targetedNode.key
        if (targetedNode.key != __key):
            raise KeyError(f"the key: {__key} is not in the skip-list")
        # => targetedNode.key == key
        if removeNode is True:
            targetedNode.detatch(nodesBefore)
            self.__length -= 1
        return targetedNode
    def __getRemoveNodeLast(self, __key:"_T_key", removeNode:bool)->"Node_SkipList[_T, _T_key]":
        """get/remove the last node with the same key, raise a KeyError if the key don't exist"""
        targetedNode: "Node_SkipList[_T, _T_key]" = \
            self.__getLayersToKey(__key, beforeKey=False)[0]
        # => last node as: targetedNode.key <= key
        if (targetedNode.key != __key):
            raise KeyError(f"the key: {__key} is not in the skip-list")
        if removeNode is True:
            targetedNode.detatch(([] if self.__indexed is False 
                                  else self.__internal_getNodesBefore(targetedNode)))
            self.__length -= 1
        return targetedNode
    
    ### get remove fetch pop nodes/elements ###
    
    def getNode(self, key:"_T_key")->"Node_SkipList[_T, _T_key]":
        """get the first node with the same key, raise a KeyError if the key don't exist"""
        return self.__getRemoveNodeFirst(key, removeNode=False) 
    def get(self, key:"_T_key")->"_T":
        """get the first element with the same key, raise a KeyError if the key don't exist"""
        return self.getNode(key).element
    
    def fetchNode(self, key:"_T_key")->"Node_SkipList[_T, _T_key]":
        """get the last node with the same key, raise a KeyError if the key don't exist"""
        return self.__getRemoveNodeLast(key, removeNode=False) 
    def fetch(self, key:"_T_key")->"_T":
        """get the last element with the same key, raise a KeyError if the key don't exist"""
        return self.getNode(key).element
    
    def removeNode(self, key:"_T_key")->"Node_SkipList[_T, _T_key]":
        """pop the first Node with the same key, raise a KeyError if the key don't exist"""
        return self.__getRemoveNodeFirst(key, removeNode=True)
    def remove(self, key:"_T_key")->"_T":
        """pop the first element with the same key, raise a KeyError if the key don't exist"""
        return self.removeNode(key).element
    
    def popNode(self, key:"_T_key")->"Node_SkipList[_T, _T_key]":
        """pop the last node with the same key, raise a KeyError if the key don't exist"""
        return self.__getRemoveNodeLast(key, removeNode=True)
    def pop(self, key:"_T_key")->"_T":
        """pop the last element with the same key, raise a KeyError if the key don't exist\n
        NOTE: it is less efficient than self.remove(key) (maybe consider using it)"""
        return self.popNode(key).element
    
    ### get/pop last node ###
    
    def getLastNode(self)->"Node_SkipList[_T, _T_key]":
        """return the last node of the list, raise a LookupError if the list is empty"""
        if self.__length == 0:
            raise LookupError("the list is empty, can't get the last element")
        # => not empty => HEAD.next != TAIL
        return self.__tail.prevs[0]
    def getLast(self)->"_T":
        """return the last element of the list, raise a LookupError if the list is empty"""
        return self.getLastNode().element
    def popLastNode(self)->"Node_SkipList[_T, _T_key]":
        """pop the last node of the list, raise a LookupError if the list is empty"""
        lastNode: "Node_SkipList[_T, _T_key]" = self.getLastNode()
        lastNode.detatch(([] if self.__indexed is False 
                          else self.__internal_getNodesBefore(lastNode)))
        self.__length -= 1
        return lastNode
    def popLast(self)->"_T":
        """pop the last element of the list, raise a LookupError if the list is empty"""
        return self.popLastNode().element

    ### get/pop first node ###

    def getFirstNode(self)->"Node_SkipList[_T, _T_key]":
        """return the first node of the list, raise a LookupError if the list is empty"""
        if self.__length == 0:
            raise LookupError("the list is empty, can't get the first element")
        # => not empty => HEAD.next != TAIL
        return self.__head.nexts[0]
    def getFirst(self)->"_T":
        """return the first element of the list, raise a LookupError if the list is empty"""
        return self.getFirstNode().element
    def popFirstNode(self)->"Node_SkipList[_T, _T_key]":
        """pop the first node of the list, raise a LookupError if the list is empty"""
        firstNode = self.getFirstNode()
        firstNode.detatch([self.__head] * self.height)
        self.__length -= 1
        return firstNode
    def popFirst(self)->"_T":
        """pop the first element of the list, raise a LookupError if the list is empty"""
        return self.popFirstNode().element
    
    ### get/pop before key ###
    
    def getNodeBefore(self, key:"_T_key")->"Node_SkipList[_T, _T_key]":
        """return the last node as: node.key < key, raise a KeyError there is no node before the key"""
        return self.__getRemoveNodeBefore(key, removeNode=False)
    def getBefore(self, key:"_T_key")->"_T":
        """return the last element as: node.key < key, raise a KeyError there is no node before the key"""
        return self.getNodeBefore(key).element
    def popNodeBefore(self, key:"_T_key")->"Node_SkipList[_T, _T_key]":
        """pop the last node as: node.key < key, raise a KeyError there is no node before the key"""
        return self.__getRemoveNodeBefore(key, removeNode=True)
    def popBefore(self, key:"_T_key")->"_T":
        """pop the last element as: node.key < key, raise a KeyError there is no node before the key"""
        return self.popNodeBefore(key).element

    ### get/pop after key ###

    def getNodeAfter(self, key:"_T_key")->"Node_SkipList[_T, _T_key]":
        """return the first node as: key < node.key, raise a KeyError there is no node after the key"""
        return self.__getRemoveNodeAfter(key, removeNode=False)
    def getAfter(self, key:"_T_key")->"_T":
        """return the first element as: key < node.key, raise a KeyError there is no node after the key"""
        return self.getNodeAfter(key).element
    def popNodeAfter(self, key:"_T_key")->"Node_SkipList[_T, _T_key]":
        """pop the first element as: key < node.key, raise a KeyError there is no node after the key"""
        return self.__getRemoveNodeAfter(key, removeNode=True)
    def popAfter(self, key:"_T_key")->"_T":
        """pop the first element as: key < node.key, raise a KeyError there is no node after the key"""
        return self.popNodeAfter(key).element
    
    ### sub list ###    
    
    def getSubListView(self, startKey:"_T_key", endKey:"_T_key")->"SubSkipList[_T, _T_key]|None":
        """return the sub list with all the nodes of self such as: startKey <= node.key <= endKey\n
        return None if the sublist is empty\n
        note: its in O(log1/p(self.length) to ge the view (it don't iterate it)"""
        startNode: "Node_SkipList[_T, _T_key]" = \
            self.__getLayersToKey(startKey, beforeKey=True)[0].nexts[0]
        endNode: "Node_SkipList[_T, _T_key]" = \
            self.__getLayersToKey(endKey, beforeKey=False)[0]
        if (startNode is self.__tail) or (endNode.key < startNode.key):
            # => the sub list is empty
            return None
        # => the sub list is NOT empty
        return SubSkipList(startNode=startNode, endNode=endNode)
    
    def popNodesSubList(self, startKey:"_T_key", endKey:"_T_key")->"list[Node_SkipList[_T, _T_key]]":
        """return and delete from self the sub list with all the nodes of self such as: startKey <= node.key <= endKey\n
        note: its in O((length of the sub list) + log1/p(length of the list))"""
        subList: "SubSkipList[_T, _T_key]|None" = \
            self.getSubListView(startKey=startKey, endKey=endKey)
        if subList is None: # => the sublist is empty
            return []
        poppedNodes: "list[Node_SkipList[_T, _T_key]]" = \
            list(subList.iterNodes())
        nodesBefore: "list[Node_SkipList[_T, _T_key]]" = \
            ([] if self.__indexed is False 
             else self.__internal_getNodesBefore(poppedNodes[0]))
        # detach nodes from self
        for node in poppedNodes:
            node.detatch(nodesBefore)
            self.__length -= 1
        return poppedNodes
    def popSubList(self, startKey:"_T_key", endKey:"_T_key")->"list[_T]":
        """return and delete from self the sub list with all the nodes of self such as: startKey <= node.key <= endKey\n
        note: its in O((length of the sub list) + log1/p(length of the list))"""
        return [node.element for node in 
                self.popNodesSubList(startKey=startKey, endKey=endKey)]
    
    
    ### internals for the getitem / delitem
    
    def __getRemoveNodeAtIndex(self, index:"SupportsIndex", *, removeNode:bool)->"Node_SkipList_indexed[_T, _T_key]":
        if self.__indexed is False:
            raise IndexError(f"this SkipList was asked to don't use indices")
        assert isinstance(self.__head, Node_SkipList_indexed)
        #determine the true index to get
        if self.__length == 0: 
            raise IndexError(f"impossible operation on an empty SkipList")
        targetedIndex: int = index.__index__() 
        if (targetedIndex >= self.__length) or (targetedIndex < -self.__length):
            raise IndexError(f"index out of range: {targetedIndex}")
        targetedIndex %= self.__length
        del index
        """the true targeted index, in [0, len[ """
        currentIndex: int = -1 
        # -> -1 because it cant' be `targetedIndex` 
        #       (currently targeting head, and widths on head are 1+width from the first element)
        currentNode: "Node_SkipList_indexed[_T, _T_key]" = self.__head
        currentLevel: int = currentNode.height -1
        """must be <= to currents node's height (and >= 0)"""
        nodesBefore: "list[Node_SkipList_indexed[_T, _T_key]]" = [NotImplemented] * self.height
        while currentIndex < targetedIndex:
            # => targeted node is further
            deltaIndex: int = targetedIndex - currentIndex
            # deltaIndex >= 1 and (all currentNode.widths >= 1)
            # determine the best level to move closer to the targetedIndex
            while currentNode.widths[currentLevel] > deltaIndex:
                nodesBefore[currentLevel] = currentNode
                currentLevel -= 1
            # => currentIndex + currentNode.widths[currentLevel] <= targetedIndex
            currentIndex += currentNode.widths[currentLevel]
            currentNode = currentNode.nexts[currentLevel]
        assert currentIndex == targetedIndex
        nodesBefore[: currentNode.height] = currentNode.prevs
        #remove the node if needed
        if removeNode is True:
            currentNode.detatch(nodesBefore)
            self.__length -= 1
        return currentNode
    
    def __internal_getRemoveSlice(self, __index:"slice")->"SkipList[_T, _T_key]":
        startIndex, stopIndex, step = __index.indices(self.__length)
        return SkipList(
            [self.__getRemoveNodeAtIndex(index, removeNode=False).element
             for index in range(startIndex, stopIndex, step)],
            self.__keyFunc, probability=self.__probabilty, addElementMethode="extend")
    
    def __internal_delSlice(self, __index:"slice")->None:
        startIndex, stopIndex, step = __index.indices(self.__length)
        # => step can't be 0
        if step < 0:
            for index in range(startIndex, stopIndex, step):
                self.__getRemoveNodeAtIndex(index, removeNode=True)
        else: # => (step > 0)
            for nbRemoved, index in enumerate(range(startIndex, stopIndex, step)):
                self.__getRemoveNodeAtIndex(index-nbRemoved, removeNode=True)
        
            
    
    ### index related getitem / delitem (no setitem)
    
    def getNodeAtIndex(self, index:"SupportsIndex")->"Node_SkipList_indexed[_T, _T_key]":
        return self.__getRemoveNodeAtIndex(index, removeNode=False)
    def popNodeAtIndex(self, index:"SupportsIndex")->"Node_SkipList_indexed[_T, _T_key]":
        return self.__getRemoveNodeAtIndex(index, removeNode=True)
    def popAtIndex(self, index:"SupportsIndex")->"_T":
        return self.__getRemoveNodeAtIndex(index, removeNode=True).element
    
    @overload
    def __getitem__(self, __index:"SupportsIndex")->"_T": ...
    @overload
    def __getitem__(self, __index:"slice")->"SkipList[_T, _T_key]": ...
    def __getitem__(self, __index:"SupportsIndex|slice")->"_T|SkipList[_T, _T_key]":
        if isinstance(__index, slice):
            return self.__internal_getRemoveSlice(__index)
        # => __index is not a slice
        return self.__getRemoveNodeAtIndex(__index, removeNode=False).element
    
    def __delitem__(self, __index:"SupportsIndex|slice")->None:
        if isinstance(__index, slice):
            self.__internal_delSlice(__index)
        else: # => __index is not a slice
            self.__getRemoveNodeAtIndex(__index, removeNode=True)
        
    
    
    ### iter the list ####
    
    def iterNodes(self, *, reverse:bool=False)->"Iterator[Node_SkipList[_T, _T_key]]":
        """yield all the nodes from the first to the last (exclude HEAD and TAIL)"""
        tail = self.__tail
        head = self.__head
        currNode: "Node_SkipList[_T, _T_key]"
        if reverse is False:
            currNode = head.nexts[0]
            while currNode is not tail:
                yield currNode
                currNode = currNode.nexts[0]
            return None
        
        else: # => reverse order
            currNode = tail.prevs[0]
            while currNode is not head:
                yield currNode
                currNode = currNode.prevs[0]
            return None
            
    def __iter__(self)->"Iterator[_T]":
        """yield every element in the list"""
        for node in self.iterNodes():
            yield node.element
            
    def __reversed__(self)->"Iterator[_T]":
        for node in self.iterNodes(reverse=True):
            yield node.element
    
    @overload
    def index(self, value:"_T")->int: ...
    @overload
    def index(self, value:"_T", start:int=0, stop:int=...)->int: ...
    def index(self, value:"_T", start:int=0, stop:"int|None"=None)->int:
        """return the index of the first item with the same `value`, \
            and withing the `start` and `stop`"""
        if self.__indexed is False:
            raise IndexError(f"this SkipList was asked to don't use indices")
        start, stop, _ = slice(start, stop).indices(self.__length)
        if start >= stop: 
            raise IndexError(f"empty range to search -> start:{start}, stop:{stop} (transformed indices)")
        key: "_T_key" = self.__keyFunc(value)
        candidates: "SubSkipList[_T, _T_key]|None" = self.getSubListView(startKey=key, endKey=key)
        if (candidates is None): 
            raise IndexError(f"value isn't in the SkipList (key not found for this value)")
        # => candidates: SubSkipList[_T, _T_key] => some elements have the same key
        startIndex: int = assertIsinstance(Node_SkipList_indexed, candidates.startNode).getIndex()
        lastIndex: int = assertIsinstance(Node_SkipList_indexed, candidates.endNode).getIndex()
        last: int = stop-1
        """last index to search"""
        del stop
        ### determine if the candidates are in the search range
        if (lastIndex < start) or (last < startIndex):
            # => the search slice and the slice of the elts with the same key don't intersect
            raise IndexError("key of the value not found inside the given interval")
        # => the search interval and candidates interval intersect
        # => (startIndex <= last) and (start <= lastIndex) and (start <= last) and (startIndex <= lastIndex)
        ### narrow the search to the start and stop indices
        if startIndex < start:
            # => can start later, at index start
            # startNode can be swaped because: (start <= lastIndex)
            candidates.startNode = self.getNodeAtIndex(start)
            startIndex = start
            # => (start <= startIndex)
        # => (start <= startIndex <= lastIndex) and (startIndex <= last) and (start <= last)
        # -> (startIndex <= lastIndex) because: 
        #       if (lastIndex < startIndex) then (old startIndex < start) 
        #           then (startIndex == start) then (lastIndex < start) -> impossible 
        if  last < lastIndex:
            # => can stop earlier, at index last
            # endNode can be swaped because: (startIndex <= lastIndex)
            candidates.endNode = self.getNodeAtIndex(last)
            lastIndex = last
            # => (lastIndex <= last)
        # => (start <= startIndex <= lastIndex <= last)
        # => optimal search range
        
        # search for the value in the view
        for deltaIndex, elt in enumerate(candidates.__iter__()):
            if elt == value:
                return startIndex + deltaIndex
        # => no element with the searched value found
        raise IndexError(f"value not found in given interval of the SkipList")
        
        
        ########################### assert isinstance(..., Node_SkipList_indexed)
        
    def count(self, value:"_T")->int:
        key: "_T_key" = self.__keyFunc(value)
        candidates: "SubSkipList[_T, _T_key]|None" = self.getSubListView(startKey=key, endKey=key)
        if (candidates is None): 
            return 0
        # => candidates: SubSkipList[_T, _T_key] => some elements have the same key
        return sum(1 for elt in candidates if elt == value)
        
    
    
    ### utils methodes ###
    def __internal_getNodesBefore(self, node:"Node_SkipList[_T, _T_key]")->"list[Node_SkipList[_T, _T_key]]":
        """return all the nodes connecting to the """
        nodesBefore: "list[Node_SkipList[_T, _T_key]]" = [NotImplemented] * self.height
        assert node.height >= 1
        for level, prevNode in enumerate(node.prevs):
            nodesBefore[level] = prevNode
        targetedHeight = node.height + 1
        currentNode: "Node_SkipList[_T, _T_key]" = node.prevs[-1]
        # => currentNode and targetedLevel are bound ! because height of node is >= 1
        while targetedHeight <= self.height:
            # => targted height is 
            # => search a node with an height >= targetedLevel
            while (currentNode.height < targetedHeight):
                currentNode = currentNode.prevs[-1]
            # => currentNode is the first node with more levels
            # => currentIndex + currentNode.widths[currentLevel] <= targetedIndex
            nodesBefore[targetedHeight-1] = currentNode
            targetedHeight += 1
            
        return nodesBefore
    
    def __ensureHeight(self, requiredHeight:int)->None:
        """makes sure that there is enought layers, create new leayers if needed"""
        nbNewLayers:int = requiredHeight - self.height
        if nbNewLayers <= 0:
            return 
        self.__head.nexts.extend([self.__tail] * nbNewLayers)
        self.__tail.prevs.extend([self.__head] * nbNewLayers)
        if self.__indexed is True:
            assert isinstance(self.__head, Node_SkipList_indexed) \
                and isinstance(self.__tail, Node_SkipList_indexed)
            self.__head.widths.extend([NotImplemented] * nbNewLayers)
            self.__tail._updateWidths(self.__tail.prevs)
        
    
    def __getLayersToKey(self, __key:"_T_key", beforeKey:bool)->"list[Node_SkipList[_T, _T_key]]":
        """return the nodes of each level where: 
        - beforeKey=True : node.key <  `key` <= node.nexts[level].key
           * this will get the nodes before the first node with given key
        - beforeKey=False: node.key <= `key` <  node.nexts[level].key
           * this is suited for getting the nodes to put before the new node with the given key\n
        note: HEAD might be in the layers but never TAIL"""
        self_height: int = self.height
        nodes: "list[Node_SkipList[_T, _T_key]]" = [NotImplemented] * self_height
        currNode: "Node_SkipList[_T, _T_key]" = self.__head 
        # => (HEAD < key) => (currNode.key < key)
        for level in range(self_height-1, -1, -1):
            nextNode: "Node_SkipList[_T, _T_key]" = currNode.nexts[level]
            # separated like that to save performances (it is signifcant enough)
            if beforeKey is True:
                # (while required condition): currNode.key < key 
                while (nextNode.key < __key):
                    # => currNode.key <= nextNode.key < key
                    currNode = nextNode
                    nextNode = currNode.nexts[level]
                    # => currNode.key < key (=> meets while req condition)
                # => currNode.key < key <= currNode.nexts[level].key
                nodes[level] = currNode
            
            else: # => beforeKey is False
                # (while required condition): currNode.key <= key 
                while (nextNode.key <= __key):
                    # => currNode.key <= nextNode.key <= key
                    currNode = nextNode
                    nextNode = currNode.nexts[level]
                    # => currNode.key <= key (=> meets while req condition)
                # => currNode.key <= key < currNode.nexts[level].key
                nodes[level] = currNode
        return nodes
    
    def __getNextHeight(self)->int:
        """return the height of the next node to be added\n
        cost in `minimum of O(1/(1-p)) and O(log1/p(nbNodes))`"""
        proba = self.__probabilty
        pInv: float = 1 / proba
        ## compute the optimal number of layers with the current number of elements
        ## use self.length+2 to avoid math error, return at least 1
        maxHeight = math.ceil(math.log((self.__length+2) * pInv, pInv))
        # get a random height 
        rand = random.random
        height = 1
        while (rand() < proba) and (height < maxHeight):
            height += 1
        return height
   
    def _countNodesPerHeight(self)->"list[int]":
        counts: "list[int]" = [0] * self.height
        for node in self.iterNodes():
            counts[node.height-1] += 1
        return counts
    
    def __pretty__(self, *_, **__)->"_ObjectRepr":
        return _ObjectRepr(self.__class__.__name__, args=tuple(self), kwargs={})


class SubSkipList(Generic[_T, _T_key], FinalClass):
    """a view on a SkipList"""
    __slots__ = ("startNode", "endNode", )
    
    def __init__(self, startNode:"Node_SkipList[_T, _T_key]", 
                 endNode:"Node_SkipList[_T, _T_key]") -> None:
        self.startNode:"Node_SkipList[_T, _T_key]" = startNode
        """first node of the the view"""
        self.endNode:"Node_SkipList[_T, _T_key]" = endNode
        """last node INSIDE the the view"""

    def iterNodes(self, *, reverse:bool=False)->"Iterator[Node_SkipList[_T, _T_key]]":
        node: "Node_SkipList[_T, _T_key]"
        if reverse is False:
            # => forward
            node = self.startNode
            while node is not self.endNode:
                yield node
                node = node.nexts[0]
            # => node is self.endNode
            yield node
        else: # => backward
            node = self.endNode
            while node is not self.startNode:
                yield node
                node = node.prevs[0]
            # => node is self.startNode
            yield node
        
    def __iter__(self)->"Iterator[_T]":
        for node in self.iterNodes(reverse=False):
            yield node.element
    
    def __reversed__(self)->"Iterator[_T]":
        for node in self.iterNodes(reverse=True):
            yield node.element


#rand = random.random
#s = SkipList((rand() for _ in range(10_000)), 
#             lambda elt: elt, addElementMethode="extend")
