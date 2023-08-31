import random

from holo.__typing import Iterable


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

