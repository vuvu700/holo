from io import DEFAULT_BUFFER_SIZE

from .__typing import TypeVar, Generic, Literal
from .protocols import SupportsRead, SupportsWrite


try: from pyx_reader import ReaderFast
except ImportError: ReaderFast = None # fallback when absent


BIG_READSIZE = 500_000 
"""500k octes\n
manualy determined to be a size that give "the best" performances\n
but it loads way more at the same time"""

_T_value = TypeVar("_T_value", str, bytes)

class StringSlice(Generic[_T_value]):
    __slots__ = ("array", "start", "stop")
    def __init__(self, array:"_T_value", start:int=0, stop:"int|None"=None) -> None:
        self.array:"_T_value" = array
        self.start:int = 0
        self.stop:int = len(array)
        if start != 0: self.cutStart(start)
        if stop is not None: self.cutEnd(stop)
    
    def _internal__getNewPos(self, relativeIndex:int)->int:
        """the new position of the index relative to the current start/stop\n
        return value is bounded to the start/stop (nor lower or bigger)"""
        if relativeIndex == 0: 
            return self.start
        elif relativeIndex > 0: 
            # => from the start
            return min(self.start + relativeIndex, self.stop)
        # => (relativeIndex < 0) => from the end
        else: return max(self.stop + relativeIndex, self.start)
    
    def cutStart(self, newStart:int)->None:
        self.start = self._internal__getNewPos(newStart)
    def cutEnd(self, newStop:int)->None:
        self.stop = self._internal__getNewPos(newStop)
    def cutSlice(self, newStart:int, newStop:int)->None:
        self.start = self._internal__getNewPos(newStart)
        self.stop = self._internal__getNewPos(newStop)

    def __len__(self)->int:
        return self.stop - self.start

    def startsWith(self, pattern:"_T_value")->bool:
        return self.array.startswith(pattern, self.start, self.stop)
    
    def find(self, pattern:"_T_value")->int:
        """return the index of the start of the `pattern` relative to current value\n
        return -1 when the pattern wasn't found in the current value"""
        absIndex = self.array.find(pattern, self.start, self.stop)
        if absIndex != -1: 
            # => found, return relative index
            return absIndex - self.start 
        return -1 # => not found
    
    def getValue(self)->"_T_value":
        """return the current slice of array"""
        return self.array[self.start: self.stop]
    
    def getValue_cutted(self, maxSize:int)->"_T_value":
        """return the current slice of array, with the end cutted from maxSize"""
        return self.array[self.start: self._internal__getNewPos(maxSize)]

    def __pretty__(self, *args, **kwargs):
        return {"array": self.array, "start": self.start, "stop": self.stop}




class Reader(Generic[_T_value]):
    __slots__ = ("file", "readSize", "buffer", "readEOF")
    def __init__(self,
            file:"SupportsRead[_T_value]",
            readSize:"int|Literal['big']|None"=None)->None:
        self.file:"SupportsRead[_T_value]" = file
        self.readSize:int
        if readSize is None: self.readSize = DEFAULT_BUFFER_SIZE
        elif readSize == "big": # => big (potentialy fastest size to read)
            self.readSize = BIG_READSIZE
        else: self.readSize = readSize
        self.buffer:"StringSlice[_T_value]|None" = None
        """None => (self.readEOF: True => buffer Emptyed, False => need to read first chunck)"""
        self.readEOF:bool = False

    def _internal__firstRead(self)->None:
        self.buffer = StringSlice(self.file.read(self.readSize))
        if len(self.buffer) < self.readSize:
            self.readEOF = True


    def skipToPattern(self,
            pattern:"_T_value", *, stopBefore:bool,
            writer:"SupportsWrite[_T_value]|None"=None)->bool:
        
        startOfPattern_index:int; readed_size:int; newStartIndex:int
        writerString:"_T_value"; readedArray:"_T_value"
        
        if self.buffer is None:
            if self.readEOF is True:
                return False # => finished reading
            # => need first read
            self._internal__firstRead()
        
        assert isinstance(self.buffer, StringSlice), \
            TypeError(f"incorrect type for self.buffer: {self.buffer}")
        
        while (self.readEOF is False) or (len(self.buffer) > 0):
            startOfPattern_index = self.buffer.find(pattern)
            
            if startOfPattern_index != -1: # => pattern has been found
                start = self.buffer.start
                if writer is not None: 
                    # write up to the pattern's start
                    writerString = self.buffer.getValue_cutted(startOfPattern_index)
                    writer.write(writerString)
                
                newStartIndex = startOfPattern_index
                if stopBefore == False: # => also skip the pattern
                    newStartIndex += len(pattern)
                self.buffer.cutStart(newStartIndex)
                
                return True # => finished

            # => not fully in the current buffer
            elif self.readEOF is False: # => potentialy more to read
                # separate the case when (size == 1), (-(1-1) = 0) => cut nothing (insted of everything)
                if len(pattern) == 1: newStartIndex = len(self.buffer)
                else: newStartIndex = -(len(pattern) - 1)

                if writer is not None: 
                    writerString = self.buffer.getValue_cutted(newStartIndex)
                    # write the start of the current buffer in the result (only the part that is not kept)
                    writer.write(writerString)
                
                # keep the end of the current buffer and avoid cutting the pattern (in case partialy found)
                self.buffer.cutStart(newStartIndex)
                
                readedArray = self.file.read(self.readSize)
                readed_size = len(readedArray)
                
                # swap the two buffers
                self.buffer.__init__(self.buffer.getValue() + readedArray) # recycle current buffer

                if readed_size < self.readSize: # => EOF reached
                    self.readEOF = True
                continue # continue with the new buffer

            else: # => EOF alredy hitted => nothing more to read
                # (not found) and (EOF reached) => skip to the end of the document
                self.buffer = None # "empty" the buffer
                return False # => finished

        # => (self.readEOF is True) and (len(self.buffer) == 0)
        return False

    def startsWithPattern(self, pattern:"_T_value")->bool:
        """tell whether the buffer starts with the given pattern\n
        read what is nessecary for it, \
        will not delet anything from the buffer but might expand it\n
        if returned True, it guarenty reader.buffer starts with the pattern
        """
        readed_size: int; startsWith: bool
        
        if self.buffer is None:
            if self.readEOF is True:
                return False # => finished reading
            # => need first read
            self._internal__firstRead()
        
        assert isinstance(self.buffer, StringSlice), \
            TypeError(f"incorrect type for self.buffer: {self.buffer}")
        
        while (self.readEOF is False) or (len(self.buffer) > 0):
            startsWith = self.buffer.startsWith(pattern)
            
            if startsWith is True: # => buffer starts with pattern
                return True # => finished
            elif len(pattern) < len(self.buffer):
                return False # => finished

            # => not fully in the current buffer
            elif self.readEOF is True: # => EOF alredy hitted => nothing more to read
                return False # => finished

            else: # EOF not hitted => potentialy more to read
                # => read next and recreate the .buffer
                readedArray = self.file.read(self.readSize)
                readed_size = len(readedArray)
                
                # swap the two buffers
                self.buffer.__init__(self.buffer.getValue() + readedArray) # recycle current buffer

                if readed_size < self.readSize: # => EOF reached
                    self.readEOF = True
                continue # continue with the new buffer

        # => (self.readEOF is True) and (len(self.buffer) == 0)
        return False

    def skipPatternIf_startsWith(self, pattern:"_T_value")->bool:
        """skip the pattern if the Reader starts with it\n
        return whether it has skiped the pattren\n
        exemple (you are *):
            - *`pattern` => `pattern`*
            - *`not the pattern` => *`not the pattern`
        """
        if self.startsWithPattern(pattern) is True:
            assert isinstance(self.buffer, StringSlice), \
                RuntimeError("if the self.startsWithPattern retunrs True, it guarenty that self.buffer starts with `pattren`")
            self.buffer.cutStart(len(pattern))
            return True
        # else => self.startsWith(pattern) is False
        return False

    def read(self, __size:"int|None"=None)->"_T_value":
        if self.buffer is None:
            # => self.readEOF is True or not started
            if self.readEOF is True:
                return self.file.read(0)
            # => not started (don't use the buffer (empty))
            return self.file.read(__size)
        
        assert isinstance(self.buffer, StringSlice), \
            TypeError(f"incorrect type for self.buffer: {self.buffer}")
        
        bufferContent:"_T_value"
        if (__size is not None) and (__size >= 0):
            # => read (up to) precise amount
            # get the value in the buffer
            bufferContent = self.buffer.getValue_cutted(__size)
            self.buffer.cutStart(__size)
            if len(bufferContent) >= __size:
                self.buffer = None # empty the buffer (optim)
                # => buffer contained enough
                if len(bufferContent) == __size:
                    # => got everything needed
                    return bufferContent
                # else: read the file too
            # => buffer wasn't enough => concat
            return bufferContent + self.file.read(__size - len(bufferContent))
        # => read to EOF
        else: 
            bufferContent = self.buffer.getValue()
            self.buffer = None # empty the buffer (optim)
            if self.readEOF is True:
                # => buffer contained enough
                return bufferContent
            # => buffer wasn't enough
            return bufferContent + self.file.read()



def bench(filesBatch:"list[str]", readSize:"int|None"=None,
          pattern:"str|bytes|None"=None, encoding:"str|None"=None,
          doTextMode:bool=True)->None:
    import os
    from .profilers import Profiler
    from .prettyFormats import prettyDataSizeOctes
    
    prof = Profiler(["Reader [text]", "Reader [bytes]",
                     "ReaderFast (bench) [bytes]", "ReaderFast (class) [bytes]",
                     ])

    char:str
    charBytes:bytes
    if pattern is None:
        char = "\n"
        charBytes = char.encode("ascii")
    elif isinstance(pattern, str):
        char = pattern
        charBytes = pattern.encode("ascii")
    elif isinstance(pattern, bytes):
        charBytes = pattern
        char = pattern.decode("ascii")
    else: raise TypeError(f"unsupported pattern type: {type(pattern)}")
    
    fileSize:int = 0 # in bytes

    for filePath in filesBatch:
        if doTextMode is False: continue
        with open(filePath, mode="r", encoding=encoding, errors="ignore") as file:
            with prof.mesure("Reader [text]"):
                reader = Reader(file, readSize=readSize)
                while reader.skipToPattern(char, stopBefore=False):
                    ...
    
    nbFounds:int = 0
    for filePath in filesBatch:
        # track size
        fileStats = os.stat(filePath)
        fileSize += fileStats.st_size
        with open(filePath, mode="rb") as file:
            with prof.mesure("Reader [bytes]"):
                reader = Reader(file, readSize=readSize)
                while reader.skipToPattern(charBytes, stopBefore=False):
                    nbFounds += 1
    
    if ReaderFast is not None:
        for filePath in filesBatch:
            with open(filePath, mode="rb") as file:
                with prof.mesure("ReaderFast (class) [bytes]"):
                    reader = ReaderFast(file, readSize=readSize)
                    while reader.skipToPattern(charBytes, stopBefore=False):
                        ...
        
        for filePath in filesBatch:
            with open(filePath, mode="rb") as file:
                with prof.mesure("ReaderFast (bench) [bytes]"):
                    reader = ReaderFast(file, readSize=readSize)
                    reader._bench_skipToPattern(charBytes)
    
    
    print(f"finished (found: {nbFounds})")
    avgTimes = prof.totalTimes()
    #prettyPrint(avgTimes, specificFormats={float: prettyTime}, compact=True)

    for (categorie, avgTime) in avgTimes.items():
        print(f"{categorie}: {prettyDataSizeOctes(fileSize / avgTime)} / sec")


def benchRawRead(filesBatch:"list[str]", readSize:"int|None"=None,
                 encoding:"str|None"=None, doTextMode:bool=True)->None:
    import os
    from .profilers import Profiler
    from .prettyFormats import prettyDataSizeOctes
    
    prof = Profiler(["raw read [text]", "raw read [bytes]"])
    
    fileSize:int = 0 # in bytes
    
    for filePath in filesBatch:
        if doTextMode is False: continue

        with open(filePath, mode="r", encoding=encoding, errors="ignore") as file:
            with prof.mesure("raw read [text]"):
                while file.read(readSize):
                    ...
    
    for filePath in filesBatch:
        fileStats = os.stat(filePath); fileSize += fileStats.st_size; # track size
        with open(filePath, mode="rb") as file:
            with prof.mesure("raw read [bytes]"):
                while file.read(readSize):
                  ...
    
    for (categorie, avgTime) in prof.totalTimes().items():
        print(f"{categorie}: {prettyDataSizeOctes(fileSize / avgTime)} / sec")

def benchMulti(readSizes:"list[int|None]", patterns:"list[str|bytes]",
               filesBatch:"list[str]", encoding:"str|None"=None, 
               doTextMode:bool=True)->None:
    from .prettyFormats import prettyDataSizeOctes
    
    for readSize in readSizes:
        print(f"#### readSize={None if readSize is None else prettyDataSizeOctes(readSize)}")
        print(f"** raw bench")
        benchRawRead(filesBatch, readSize, encoding, doTextMode)
        print()
        for pattern in patterns:
            print(f"~~ pattern[{len(pattern)} char long]")
            bench(filesBatch, readSize, pattern, encoding, doTextMode)
        print("\n") # 2*new line



if __name__ == "__main__":
    benchMulti(
        readSizes=[BIG_READSIZE, None],
        # chance      1e964         1e19        1e16   65536   256
        patterns=[b"abcdefgh"*50, b"abcdefgh", b"abc", b"ab", b"a"],
        filesBatch=[
            rf"C:\Users\vuvu7\Documents\temp\file-{i}.bin"
            for i in range(10)],
        doTextMode=False,
    )
    