import random, math
import warnings

from holo.__typing import (
    Generic, Iterable, Generator, PartialyFinalClass, Iterator,
    overload, Literal, cast, Callable, FinalClass, TypeVar, Self,
)
from holo.protocols import _T, _T2, SupportsLowersComps


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


# TODO: clean the code + 
# idea n°1: test to remove the PartialyFinal since it reduce performances
#   and anyway the user can get the nodes so he can edit the links if he want to
# idea n°2: make the links private and keep the classes PartialyFinal


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

#[HEAD]<->   <->   <->   <->   <->   <->   <-> NIL
# HEAD <->   <->   <->[3]<->   <->   <->   <-> NIL
# HEAD <->   <->   <->[3]<->   <->   <-> 6 <-> NIL
# HEAD <->   <-> 2 <-> 3 <->   <->[5]<-> 6 <-> NIL
# HEAD <->   <-> 2 <-> 3 <-> 4 <->[5]<-> 6 <-> NIL
# HEAD <-> 1 <-> 2 <-> 3 <-> 4 <->[5]<->(6)<-> NIL

class Node_SkipList(Generic[_T, _T_key], FinalClass):
    """just hold the values and the next elements"""
    __slots__ = ("element", "key", "prevs", "nexts", )
    __TAIL__: "Node_SkipList|None" = None 
    """there is only a single TAIL (avoid useless object creations)"""
    element: _T
    key: _T_key
    prevs: "list[Node_SkipList[_T, _T_key]]"
    nexts: "list[Node_SkipList[_T, _T_key]]"
    
    def __new__(cls, elt:"_T", key:"_T_key", height:int) -> Self:
        # don't use the __new__ of generic: slow
        # don't use the __setattr__ de FinalClass slow and obviously the first first time setting
        self = object.__new__(cls)
        object.__setattr__(self, "element", elt)
        object.__setattr__(self, "key", key)
        object.__setattr__(self, "nexts", [...] * height)
        object.__setattr__(self, "prevs", [...] * height)
        return self
        
    @classmethod
    def insertNewNodeAfter(cls, elt:"_T", key:"_T_key", height:int,
                           nodesBefore:"list[Node_SkipList[_T, _T_key]]")->None:
        # improves performance enough (and is avoid unallocated elts in self.nexts)
        newNode = object.__new__(Node_SkipList)
        object.__setattr__(newNode, "element", elt)
        object.__setattr__(newNode, "key", key)
        object.__setattr__(newNode, "nexts", [])
        object.__setattr__(newNode, "prevs", [])
        for level in range(height):
            newNode.prevs.append(nodesBefore[level])
            newNode.nexts.append(nodesBefore[level].nexts[level])
            nodesBefore[level].nexts[level] = newNode
    
    @property
    def height(self)->int:
        """user friendly way to get the height of the node :)"""
        return len(self.nexts)
    
    @property
    def nextNode(self)->"Node_SkipList[_T, _T_key]":
        """user friendly way to get the next node :)"""
        return self.nexts[0]
    
    @property
    def prevNode(self)->"Node_SkipList[_T, _T_key]":
        """user friendly way to get the previous node :)"""
        return self.prevs[0]
    
    def detatch(self)->None:
        """detatch the node from the prevs/nexts \
        and clear the links of self (self.height will be 0)"""
        print(f"detatching node: {self}")
        for level in range(self.height):
            print(f"detaching level n°{level}, prev:{self.prevs[level]} next: {self.nexts[level]}")
            nodeBefore = self.prevs[level]
            nodeAfter = self.nexts[level]
            nodeBefore.nexts[level] = nodeAfter
            nodeAfter.prevs[level] = nodeBefore
        self.prevs.clear()
        self.nexts.clear()        
 
    @classmethod
    def createHEAD(cls)->"Node_SkipList":
        """create a HEAD and a TAIL connected together"""
        head: "Node_SkipList" = Node_SkipList(..., key=SMALLEST(), height=0)
        tail: "Node_SkipList" = Node_SkipList(..., key=BIGGEST(), height=0)
        head.nexts.append(tail)
        tail.prevs.append(head)
        return head
        

    def __str__(self) -> str:
        if self.element is self.key:
            return f"{self.__class__.__name__}(elt={self.element}, key is element, height={self.height})"
        return f"{self.__class__.__name__}(elt={self.element}, key={self.key}, height={self.height})"
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(element={repr(self.element)}, key={repr(self.key)}, height={repr(self.height)})"


class SkipList(Generic[_T, _T_key], PartialyFinalClass):
    """a (stable) sorted list that have the following complexity:
     * add: O(log1/p(n)) *average*
     * remove/pop: O(log1/p(n)) *average*
     * getSublist: O(log1/p(n)) *average*
     * get next elment: O(1)
     * get at index: O(log1/p(n)) *average* [not implemented yet]
     * search key: O(log1/p(n)) *average*
    """
    __slots__ = ("head", "tail", "probabilty", "__length", "keyFunc", )
    __finals__ = {"head", "tail", "probabilty", "keyFunc", }
    
    def __init__(self, elements:"Iterable[_T]", 
                 eltToKey:"Callable[[_T], _T_key]", probability:float=1/4) -> None:
        if (probability <= 0) or (probability >= 1):
            raise ValueError(f"the probability: {probability} of the SkipList must be in ]0, 1[")
        if probability > 0.8:
            warnings.warn(f"be aware that using high probability ({probability} > 0.8) of new layers will create a lots of layers an tho slowing down the process")
        self.head: "Node_SkipList[_T, _T_key]" = Node_SkipList.createHEAD()
        self.tail: "Node_SkipList[_T, _T_key]" = self.head.nextNode
        self.__length: int = 0
        self.probabilty: float = probability
        self.keyFunc: "Callable[[_T], _T_key]" = eltToKey
        # add the elements
        for elt in elements:
            self.append(elt)
    
    @property
    def height(self)->int:
        return self.head.height
    
    def length(self)->int:
        return self.__length
    def __len__(self)->int:
        return self.__length
    
    ### add an element ###
    
    def __addElement(self, elt:"_T", firstOfKeys:bool)->None:
        """add a new element to the list:
         * firstOfKeys=True -> insert before all the same keys
         * firstOfKeys=False -> append after all the same keys"""
        newNode_height: int = self.__getNextHeight()
        elt_key: "_T_key" = self.keyFunc(elt)
        self.__ensureHeight(newNode_height)
        insertionNodes: "list[Node_SkipList[_T, _T_key]]" = \
            self.__getLayersToKey(elt_key, beforeKey=firstOfKeys)
        Node_SkipList.insertNewNodeAfter(
            elt, elt_key, newNode_height, insertionNodes)
        self.__length += 1
    def append(self, elt:"_T")->None:
        """insert the elt after all the elements with the same key"""
        self.__addElement(elt, firstOfKeys=False)    
    def insert(self, elt:"_T")->None:
        """insert the elt before all the elements with the same key"""
        self.__addElement(elt, firstOfKeys=True)
        
    def extend(self, elements:"Iterable[_T]")->None:
        """a faster an more efficient procedure to append multiple elements\n
        it will cache the elements in a list before inserting to speed up the process"""
        elements_iter: "Iterator[_T]" = iter(sorted(elements, key=self.keyFunc))
        # => they are now sorted (faster sort than using this structure)
        # get the nodes to insert after and insert this node 
        try: elt: _T = next(elements_iter)
        except StopIteration: return None # => no elements to add
        elt_key: "_T_key" = self.keyFunc(elt)
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
            self.__ensureHeight(newNode_height)
            # len(insertionNodes) == old height of self
            if newNode_height > len(insertionNodes):
                # => extended the height, add some heads
                insertionNodes.extend([self.head] * (newNode_height - len(insertionNodes)))
            Node_SkipList.insertNewNodeAfter(elt, elt_key, newNode_height, insertionNodes)
            lastInsertedNode = lastInsertedNode.nexts[0]
            # update the insertion nodes with the last inserted node
            for level in range(lastInsertedNode.height):
                insertionNodes[level] = lastInsertedNode
            # get the next element and get its key
            try: elt = next(elements_iter)
            except StopIteration: break # => added all elements
            elt_key = self.keyFunc(elt)

    ### contain element/key ###

    def containKey(self, key:"_T_key")->bool:
        """tell whether there is an element with the same key inside the list"""
        try: # test if it can get a node with this key
            self.__getRemoveNodeFirst(key, removeNode=False)
            return True
        except KeyError: return False
    def __contains__(self, elt:"_T")->bool:
        """tell whether this element is inside the list"""
        key: _T_key = self.keyFunc(elt)
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
        if targetedNode is self.head:
            raise KeyError(f"there is no node before the key: {__key}")
        if removeNode is True:
            targetedNode.detatch()
            self.__length -= 1
        return targetedNode
    def __getRemoveNodeAfter(self, __key:"_T_key", removeNode:bool)->"Node_SkipList[_T, _T_key]":
        """get/remove the first node as: key < node.key, raise a KeyError there is no node after the key"""
        targetedNode: "Node_SkipList[_T, _T_key]" = \
            self.__getLayersToKey(__key, beforeKey=False)[0].nexts[0]
        # => first node as: key < targetedNode.key
        if targetedNode is self.head:
            raise KeyError(f"there is no node before the key: {__key}")
        if removeNode is True:
            targetedNode.detatch()
            self.__length -= 1
        return targetedNode
    def __getRemoveNodeFirst(self, __key:"_T_key", removeNode:bool)->"Node_SkipList[_T, _T_key]":
        """get/remove the first node with the same key, raise a KeyError if the key don't exist"""
        targetedNode: "Node_SkipList[_T, _T_key]" = \
            self.__getLayersToKey(__key, beforeKey=True)[0].nexts[0]
        # => first node as: key <= targetedNode.key
        if (targetedNode.key != __key):
            raise KeyError(f"the key: {__key} is not in the skip-list")
        # => targetedNode.key == key
        if removeNode is True:
            targetedNode.detatch()
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
            targetedNode.detatch()
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
        return self.__getRemoveNodeFirst(key, removeNode=False) 
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
        return self.tail.prevs[0]
    def getLast(self)->"_T":
        """return the last element of the list, raise a LookupError if the list is empty"""
        return self.getLastNode().element
    def popLastNode(self)->"Node_SkipList[_T, _T_key]":
        """pop the last node of the list, raise a LookupError if the list is empty"""
        lastNode: "Node_SkipList[_T, _T_key]" = self.getLastNode()
        lastNode.detatch()
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
        return self.head.nexts[0]
    def getFirst(self)->"_T":
        """return the first element of the list, raise a LookupError if the list is empty"""
        return self.getFirstNode().element
    def removeFirstNode(self)->"Node_SkipList[_T, _T_key]":
        """return the first node of the list, raise a LookupError if the list is empty"""
        firstNode = self.getFirstNode()
        firstNode.detatch()
        return firstNode
    def removeFirst(self)->"_T":
        """return the first element of the list, raise a LookupError if the list is empty"""
        return self.removeFirstNode().element
    
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
        """return the first element as: key < node.key, raise a KeyError there is no node before the key"""
        return self.__getRemoveNodeAfter(key, removeNode=False)
    def getAfter(self, key:"_T_key")->"_T":
        """return the first element as: key < node.key, raise a KeyError there is no node before the key"""
        return self.getNodeAfter(key).element
    def popNodeAfter(self, key:"_T_key")->"Node_SkipList[_T, _T_key]":
        """pop the first element as: key < node.key, raise a KeyError there is no node before the key"""
        return self.__getRemoveNodeAfter(key, removeNode=True)
    def popAfter(self, key:"_T_key")->"_T":
        """pop the first element as: key < node.key, raise a KeyError there is no node before the key"""
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
        if endNode.key < startNode.key:
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
        # detach nodes from self
        for node in poppedNodes:
            node.detatch()
        return poppedNodes
    def popSubList(self, startKey:"_T_key", endKey:"_T_key")->"list[_T]":
        """return and delete from self the sub list with all the nodes of self such as: startKey <= node.key <= endKey\n
        note: its in O((length of the sub list) + log1/p(length of the list))"""
        return [node.element for node in 
                self.popNodesSubList(startKey=startKey, endKey=endKey)]
    
    ### iter the list ####
    
    def iterNodes(self)->"Iterator[Node_SkipList[_T, _T_key]]":
        """yield all the nodes from the first to the last (exclude HEAD and TAIL)"""
        tail = self.tail
        currNode: "Node_SkipList[_T, _T_key]" = self.head.nexts[0]
        while currNode is not tail:
            yield currNode
            currNode = currNode.nexts[0]
        return None
    def __iter__(self)->"Iterator[_T]":
        """yield every element in the list"""
        for node in self.iterNodes():
            yield node.element
    
    ### utils methodes ###    
    
    def __ensureHeight(self, requiredHeight:int)->None:
        """makes sure that there is enought layers, create new leayers if needed"""
        nbNewLayers:int = requiredHeight - self.height
        if nbNewLayers <= 0:
            return 
        self.head.nexts.extend([self.tail] * nbNewLayers)
        self.tail.prevs.extend([self.head] * nbNewLayers)
    
    def __getLayersToKey(self, __key:"_T_key", beforeKey:bool)->"list[Node_SkipList[_T, _T_key]]":
        """return the nodes of each level where: 
        - beforeKey=True : node.key <  `key` <= node.nexts[level].key
           * this will get the nodes before the first node with given key
        - beforeKey=False: node.key <= `key` <  node.nexts[level].key
           * this is suited for getting the nodes to put before the new node with the given key\n
        note: HEAD might be in the layers but never TAIL"""
        self_height: int = self.height
        nodes: "list[Node_SkipList[_T, _T_key]]" = [...] * self_height
        currNode: "Node_SkipList[_T, _T_key]" = self.head 
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

    def __computeMaxOptimalHeight(self)->int:
        """compute the optimal number of layers with the current number of elements\n
        use self.length+2 to avoid math error, return at least 1"""
        pInv: float = 1 / self.probabilty
        return math.ceil(math.log((self.__length+2) * pInv, pInv))
    
    def __getNextHeight(self)->int:
        """return the height of the next node to be added\n
        cost in `min{ O(1/(1-p)) ; O(log1/p(nbNodes)) }`"""
        maxHeight = self.__computeMaxOptimalHeight()
        rand = random.random; proba = self.probabilty
        height = 1
        while (rand() < proba) and (height < maxHeight):
            height += 1
        return height
        # O(1) version, slower (3x) for low/normal probability
        maxHeight:int = self.__computeMaxOptimalHeight()
        maxLength = (1/self.probabilty)**maxHeight
        rand = random.randint(2, max(math.floor(maxLength), 2))
        height = 1 + maxHeight - math.ceil(math.log(rand, 1/self.probabilty))
        return height
   
    def __countNodesPerHeight(self)->"list[int]":
        counts: "list[int]" = [0] * self.height
        for node in self.iterNodes():
            counts[node.height-1] += 1
        return counts


class SubSkipList(Generic[_T, _T_key], FinalClass):
    __slots__ = ("startNode", "endNode", )
    
    def __init__(self, startNode:"Node_SkipList[_T, _T_key]", 
                 endNode:"Node_SkipList[_T, _T_key]") -> None:
        self.startNode:"Node_SkipList[_T, _T_key]" = startNode
        self.endNode:"Node_SkipList[_T, _T_key]" = endNode

    def iterNodes(self)->"Iterator[Node_SkipList[_T, _T_key]]":
        node: "Node_SkipList[_T, _T_key]" = self.startNode
        while node is not self.endNode:
            yield node
            node = node.nexts[0]
        # => node is self.endNode
        yield node
    
    def __iter__(self)->"Iterator[_T]":
        for node in self.iterNodes():
            yield node.element
