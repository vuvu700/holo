from holo.protocols import SupportsRead
from holo import Pointer

class ReaderFast:
    def __init__(self, file:SupportsRead[bytes], readSize:int|None=None)->None: ...
    def skipToPattern(self, pattern:bytes, stopBefore:bool, writer:Pointer[bytes]|None=None)->bool: ...
    def startsWithPattern(self, pattern:bytes)->bool: ...
    def skipPatternIf_startsWith(self, pattern:bytes)->bool: ...
    def __del__(self)->None: ...
    def _bench_skipToPattern(self, pattern:bytes)->None: ...
    