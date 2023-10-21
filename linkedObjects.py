from holo.__typing import (
    Generic, Iterable, Generator,
    overload, Literal, NoReturn,
)
from holo.protocols import _T

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
