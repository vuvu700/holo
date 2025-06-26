import random


from .__typing import (
    Iterable, Callable,
)
from .protocols import _T, SupportsLenAndGetItem



def shuffle_str(string:str)->str:
    tmp = list(string)
    random.shuffle(tmp)
    return "".join(tmp)

DEFAULT_ALPHABET:"list[str]" = \
    [chr(c) for c in range(ord('a'), ord('z')+1)] \
    + [chr(c) for c in range(ord('A'), ord('A')+1)] \
    + list("0123456789_-")

def randomStrings(nbStrings:int, stringSize:"int|range"=range(6, 8), alphabet:"Iterable[str]"=DEFAULT_ALPHABET)->"list[str]":
    # setup
    if isinstance(stringSize, int):
        stringSize = range(stringSize, stringSize)
    sizeStart:int = stringSize.start
    sizeStop:int = stringSize.stop
    sizeStep:int = stringSize.step
    
    if not isinstance(alphabet, list):
        alphabet = list(alphabet)
    alphabetSize:int = len(alphabet)
    
    result:"list[str]" = [
        "".join(
            alphabet[random.randrange(0, alphabetSize)] 
            for _ in range(random.randrange(sizeStart, sizeStop, sizeStep))
        )
        for _ in range(nbStrings)
    ]
    return result



def gaussianPermutation(size:int, randomness:float=0.1, loop:bool=False)->"list[int]":
    """return the permuation table, with the pos of the items shifted based on a gaussian distribustion\n
    ie. there are more chance that the item stay around its position\n
    be increesing the `randomness` you increese the chances to move the item further away\n
    default randomness is 0.10 = 10 %, ie. 1 S.D. to move of 10% (of the `size`) from its current pos\n
    `loop` is whether an item that an item too much shifted will loop\n
    complexity in O(n * log(n))"""
    if randomness == 0.0: # => no random => no changes
        return list(range(size))
    
    randNewPos:"Callable[[int], float]"
    if loop is True:
        randNewPos = lambda currPos: \
            (currPos + 0.5 + random.gauss(0.0, randomness) * size) % size
        # why +0.5 ? -> (with size of 20)
        # should not loop: 
        #  (old): (0 -0.4) % 20 -> 19.6 # BAD ; (19 +0.4) % 20 -> 19.4 # OK
        #  (new): (0 +0.5 -0.4) % 20 -> 0.1 # OK; (19 +0.5 +0.4) % 20 -> 19.9 # OK
        # should loop:
        #  (old): (0 -0.6) % 20 -> 19.4 # OK ; (19 +0.6) % 20 -> 19.4 # BAD
        #  (new): (0 +0.5 -0.6) % 20 -> 19.9 # OK; (19 +0.5 +0.6) % 20 -> 0.1 # OK
    else: randNewPos = lambda currPos: (currPos + random.gauss(0.0, randomness) * size)
    newOrder:"list[float]" = list(map(randNewPos, range(size)))
    """the 'pos' of each items relative to eache other ()"""
    
    return sorted(range(size), key=lambda index: newOrder[index])

def gaussianShuffle(
        elements:"SupportsLenAndGetItem[_T]", randomness:float=0.1, loop:bool=False)->"list[_T]":
    """return a shuffuled list of elts. from `elements`, \
        with the pos of the items shifted based on a gaussian distribustion\n
    ie. there are more chance that the item stay around its position\n
    be increesing the `randomness` you increese the chances to move the item further away\n
    default randomness is 0.10 = 10 %, ie. 1 S.D. to move of 10% (of the `size`) from its current pos\n
    `loop` is whether an item that an item too much shifted will loop\n
    complexity in O(n * log(n))"""
    permuationTable:"list[int]" = \
        gaussianPermutation(len(elements), randomness=randomness, loop=loop)
    return [elements[indexItemFrom] for indexItemFrom in permuationTable]



def playlistShuffle(elements:"SupportsLenAndGetItem[_T]", ratioReplayLater:float=0.3)->"list[_T]":
    """return a shuffuled list of elts. from `elements`\n
    `ratioReplayLater` keep the given proportion of the latest played elements from appearing\
        in the first next played elements, ie. in the start of the returned list\
    complexity in O(n)"""
    nbElts:int = len(elements) # in case it is "long" to compute
    nbSafeElts:int = int(nbElts * ratioReplayLater)
    deltaElts:int = nbElts - nbSafeElts
    if nbSafeElts >= nbElts-1:
        # the shuffle of 1 or 0 elements dont change the list
        return [elements[i] for i in range(nbElts)] # range = id. permutation
    
    # determine the start of the permut table
    permutTable:"list[int]" = list(range(nbElts))
    randrange = random.randrange
    index:int; index2:int
    # shuffle the start
    for index in range(deltaElts):
        index2 = randrange(0, index+1) # don't swap with the end (safe positions)
        (permutTable[index], permutTable[index2]) = \
            (permutTable[index2], permutTable[index])
    # shuffle the end
    for index in range(nbSafeElts, nbElts):
        index2 = randrange(nbSafeElts, index+1) # don't swap with the start (unsafe positions)
        (permutTable[index], permutTable[index2]) = \
            (permutTable[index2], permutTable[index])
    
    return [elements[indexItemFrom] for indexItemFrom in permutTable]


def benchShuffle(size:int)->None:
    from .prettyFormats import prettyPrint, prettyTime
    from .profilers import Profiler
    
    playlist = list(range(size))
    prof = Profiler(["random", "playlist-lowSafe", "playlist-highSafe", "gaussian-lowRand", "gaussian-veryLowRand", "gaussian-highRand"])

    with prof.mesure("random"):
        random.shuffle(playlist)

    with prof.mesure("playlist-lowSafe"):
        playlistShuffle(playlist, ratioReplayLater=0.1)
    with prof.mesure("playlist-highSafe"):
        playlistShuffle(playlist, ratioReplayLater=0.4)

    with prof.mesure("gaussian-veryLowRand"):
        gaussianShuffle(playlist, randomness=0.01)    
    with prof.mesure("gaussian-lowRand"):
        gaussianShuffle(playlist, randomness=0.1)
    with prof.mesure("gaussian-highRand"):
        gaussianShuffle(playlist, randomness=0.4)
        
    prettyPrint(prof.avgTimes(), specificFormats={float: prettyTime})