#cython: language_level=3str
from Cython.Includes.cpython cimport PyObject, Py_XINCREF, Py_XDECREF
from libc.stdlib cimport malloc, free

from pyx_datatypes cimport (
    BytesSlice, BytesSlice_create, BytesSlice_recycle, BytesSlice_free_all, BytesSlice_release,
        BytesSlice_cutStart, BytesSlice_migthEndsWith, BytesSlice_size, BytesSlice_copyTo_bytes,
        BytesSlice_findBytesPattern, BytesSlice_copyTo_bytes2, BytesSlice_findChar, 
        BytesSlice_migthStartsWith, BytesSlice_findPattern, BytesSlice_copyTo_String,
    BytesIO_like, BytesIO_like_append,
    String,
)

from io import DEFAULT_BUFFER_SIZE

from holo.protocols import SupportsRead
from holo import Pointer

cdef struct Reader2:
    PyObject *file # SupportsRead[bytes]
    int readSize # how much to read each times
    BytesSlice *buffer
    bint readEOF # whether the EOF has been read


cdef Reader2* Reader2_create(file:SupportsRead[bytes], readSize:int|None):
    "create an initialize a Reader `/!\\ MALLOC`"
    cdef Reader2 *self = <Reader2*> malloc(<size_t>sizeof(Reader2))
    cdef PyObject *file_ = <PyObject*>file
    Py_XINCREF(file_)
    self.file = file_
    self.readSize = DEFAULT_BUFFER_SIZE
    self.buffer = BytesSlice_create(b"")
    self.readEOF = <bint>False
    if readSize is not None:
        self.readSize = readSize
    return self

cdef bint Reader2_skipToPattern(Reader2 *self, bytes pattern, bint stopBefore, writer:Pointer[bytes]|None):
    cdef int startOfPattern_index, readed_size, newStartIndex
    cdef bint migthEndsWith
    cdef bytes newBuffer

    cdef unsigned char *patternArray = <unsigned char*>pattern
    cdef int patternSize = len(pattern)
    cdef list contentsList = []
    cdef bint found = <bint>False
    
    reader_file:"SupportsRead[bytes]" = <object>self.file
    while (self.readEOF == False) or (BytesSlice_size(self.buffer) > 0):
        # search the pattern in the buffer 
        if patternSize > 1:
            startOfPattern_index = BytesSlice_findBytesPattern(self.buffer, pattern)
        elif patternSize == 1:
            startOfPattern_index = BytesSlice_findChar(self.buffer, patternArray[0])
        else:  # => (pattern.size == 0) => do nothing 
            # => finished (found)
            found = <bint>True 
            break
        
        if startOfPattern_index != -1: # => pattern has been found
            if writer is not None: 
                # write up to the pattern's start
                contentsList.append(
                    BytesSlice_copyTo_bytes2(self.buffer, 0, startOfPattern_index)
                )
            
            newStartIndex = startOfPattern_index
            if stopBefore == False: # => also skip the pattern
                newStartIndex += patternSize
            BytesSlice_cutStart(self.buffer, newStartIndex)
            # => finished (found)
            found = <bint>True 
            break 
        
        # => not fully in the current buffer
        elif self.readEOF is False: # => potentialy more to read
            # determine if the current buffer migth ends with pattern if extended
            if patternSize == 1:
                # => migthEndsWith is False => cut to the end
                newStartIndex = BytesSlice_size(self.buffer)
            else:
                migthEndsWith = BytesSlice_migthEndsWith(self.buffer, patternArray, patternSize)
                if migthEndsWith is True:
                    newStartIndex = -(patternSize - 1)
                else: # => migthEndsWith is False => cut to the end
                    newStartIndex = BytesSlice_size(self.buffer)

            if writer is not None: 
                # write the start of the current buffer in the result (only the part that is not kept)
                contentsList.append(BytesSlice_copyTo_bytes2(self.buffer, 0, newStartIndex))
            
            # keep the end of the current buffer and avoid cutting the pattern (in case partialy found)
            BytesSlice_cutStart(self.buffer, newStartIndex)


            newBuffer = reader_file.read(self.readSize) # <- readed bytes
            readed_size = len(newBuffer)
            
            # update the buffer with the newly readed datas
            # merge remainder of the current buffer with the new buffer
            BytesSlice_recycle(self.buffer, BytesSlice_copyTo_bytes(self.buffer) + newBuffer)

            if readed_size < self.readSize: # => EOF reached
                self.readEOF = <bint>True
            continue # continue with the new buffer
            ### ends of "not fully in the current buffer"

        else: # => EOF alredy hitted => nothing more to read
            # (not found) and (EOF reached) => skip to the end of the document
            BytesSlice_release(self.buffer)
            # => finished (not found)
            found = <bint>False 
            break 
    
    # => finished (all reason)
    if writer is not None:
        writer.value = b"".join(contentsList)
    return found

cdef bint Reader2_startsWithPattern(Reader2 *self, bytes pattern):
    """tell whether the buffer starts with the given pattern\n
    read what is nessecary for it, \
    will not delet anything from the buffer but might expand it\n
        if returned True, it guarenty reader.buffer starts with the pattern
    """
    cdef String patternString = String(<unsigned char*>pattern, len(pattern))
    return Reader2_startsWithPatternString(self, &patternString)

cdef bint Reader2_skipPatternIf_startsWith(Reader2 *self, bytes pattern):
    if Reader2_startsWithPattern(self, pattern) is True:
        BytesSlice_cutStart(self.buffer, len(pattern))
        return <bint>True
    # else => self.startsWith(pattern) is False
    return <bint>False

cdef void Reader2_free_all(Reader2 *self):
    if self == NULL: return
    Py_XDECREF(self.file)
    self.file = NULL
    BytesSlice_free_all(self.buffer)
    free(self)




cdef class ReaderFast:
    cdef Reader2 *reader

    def __init__(self, file:"SupportsRead[bytes]", readSize:int|None=None)->None:
        self.reader = Reader2_create(file, readSize)
    
    cpdef bint skipToPattern(self, bytes pattern, bint stopBefore, writer:"Pointer[bytes]|None"=None):
        return Reader2_skipToPattern(self.reader, pattern, <bint>stopBefore, writer)
    
    cpdef bint startsWithPattern(self, bytes pattern):
        """tell whether the buffer starts with the given pattern\n
        read what is nessecary for it, \
        will not delet anything from the buffer but might expand it\n
        if returned True, it guarenty reader.buffer starts with the pattern
        """
        return Reader2_startsWithPattern(self.reader, pattern)

    cpdef bint skipPatternIf_startsWith(self, bytes pattern):
        return Reader2_skipPatternIf_startsWith(self.reader, pattern)
    
    cpdef bytes read(self, _size:"int|None"=None):
        cdef BytesSlice *buffer = self.reader.buffer
        cdef bytes bufferContent
        reader_file:"SupportsRead[bytes]" = <object>self.reader.file
        if BytesSlice_size(buffer) == 0:
            # => empty buffer => read directly from the file
            return reader_file.read(_size)
        elif (_size is not None) and (_size >= 0):
            # => read (up to) precise amount
            # get the value in the buffer
            bufferContent = BytesSlice_copyTo_bytes2(buffer, 0, _size)
            BytesSlice_cutStart(buffer, _size) # => empty the buffer when 
            if len(bufferContent) == _size:
                # => buffer exactly all => no more read
                BytesSlice_release(buffer) # fully empty the buffer (optim)
                return bufferContent
            # => buffer wasn't enough => concat
            return bufferContent + reader_file.read(_size - len(bufferContent))
        # => read to EOF
        else: 
            bufferContent = BytesSlice_copyTo_bytes(buffer)
            BytesSlice_release(buffer) # fully empty the buffer (optim)
            if self.reader.readEOF is True:
                # => buffer contained enough
                return bufferContent
            # => buffer wasn't enough
            return bufferContent + reader_file.read()
    


    def _bench_skipToPattern(self, bytes pattern)->None:
        while self.skipToPattern(pattern, stopBefore=<bint>False):
            ...

    def __del__(self)->None:
        Reader2_free_all(self.reader)




### extention of reader2_... with `String *pattern` and `BytesIO_like *writer`
cdef bint Reader2_skipToPatternString(Reader2 *self, String *pattern, bint stopBefore, BytesIO_like *writer):
    """slower search version but use `String *pattern` and `BytesIO_like *writer`"""
    cdef int startOfPattern_index, readed_size, newStartIndex
    cdef bint migthEndsWith
    cdef bytes newBuffer
    
    reader_file:"SupportsRead[bytes]" = <object>self.file
    while (self.readEOF == False) or (BytesSlice_size(self.buffer) > 0):
        # search the pattern in the buffer 
        if pattern.size > 1:
            startOfPattern_index = BytesSlice_findPattern(self.buffer, pattern.value, pattern.size)
        elif pattern.size == 1:
            startOfPattern_index = BytesSlice_findChar(self.buffer, pattern.value[0])
        else:  # => (pattern.size == 0) => do nothing 
            return <bint>True # => finished (found)
        
        if startOfPattern_index != -1: # => pattern has been found
            if writer != NULL: 
                # write up to the pattern's start
                BytesIO_like_append(writer,
                    BytesSlice_copyTo_String(self.buffer, 0, startOfPattern_index) # /!\\ MALLOC (held by writer)
                )
            
            newStartIndex = startOfPattern_index
            if stopBefore == False: # => also skip the pattern
                newStartIndex += pattern.size
            BytesSlice_cutStart(self.buffer, newStartIndex)
            return <bint>True # => finished (found)
        
        # => not fully in the current buffer
        elif self.readEOF is False: # => potentialy more to read
            
            # determine if the current buffer migth ends with pattern if extended
            if pattern.size == 1:
                # => migthEndsWith is False => cut to the end
                newStartIndex = BytesSlice_size(self.buffer)
            else:
                migthEndsWith = BytesSlice_migthEndsWith(self.buffer, pattern.value, pattern.size)
                if migthEndsWith is True:
                    newStartIndex = -(pattern.size - 1)
                else: # => migthEndsWith is False => cut to the end
                    newStartIndex = BytesSlice_size(self.buffer)

            if writer != NULL: 
                # write the start of the current buffer in the result (only the part that is not kept)
                BytesIO_like_append(writer,
                    BytesSlice_copyTo_String(self.buffer, 0, newStartIndex)
                )
            
            # keep the end of the current buffer and avoid cutting the pattern (in case partialy found)
            BytesSlice_cutStart(self.buffer, newStartIndex)


            newBuffer = reader_file.read(self.readSize) # <- readed bytes
            readed_size = len(newBuffer)
            
            # update the buffer with the newly readed datas
            # merge remainder of the current buffer with the new buffer
            BytesSlice_recycle(self.buffer, BytesSlice_copyTo_bytes(self.buffer) + newBuffer)

            if readed_size < self.readSize: # => EOF reached
                self.readEOF = <bint>True
            continue # continue with the new buffer
            ### ends of "not fully in the current buffer"

        else: # => EOF alredy hitted => nothing more to read
            # (not found) and (EOF reached) => skip to the end of the document
            BytesSlice_release(self.buffer)
            return <bint>False # => finished (not found)
    
    return <bint>False # => finished (not found)


cdef bint Reader2_startsWithPatternString(Reader2 *self, String *pattern):
    """version that use `String *pattern` and `BytesIO_like *writer` (internal for Reader2_startsWithPattern)\n
    tell whether the buffer starts with the given pattern\n
    read what is nessecary for it, \
    will not delet anything from the buffer but might expand it\n
    if returned True, it guarenty reader.buffer starts with the pattern
    """
    cdef int readed_size
    cdef bint migthStartsWith
    """False => can't starts with\n
    True => (starts with) if pattern's size < buffer's \
        else (migth starts with => need buffer extend)"""

    reader_file:"SupportsRead[bytes]" = <object>self.file
    while (self.readEOF == False) or (BytesSlice_size(self.buffer) > 0):
        if pattern.size == 0: # => starts with empty
            return <bint>True # => finished (found)
        else: # => pattern not empty
            migthStartsWith = BytesSlice_migthStartsWith(self.buffer, pattern.value, pattern.size)

        if migthStartsWith == False: # => can't starts with
            return <bint>False # => finished
        # => migthStartsWith is True
        elif pattern.size <= BytesSlice_size(self.buffer):
            # => bigger buffer than pattern => buffer starts with pattern
            return <bint>True # => finished
        # => (migthStartsWith is True) and (smaller buffer than pattern) => potential starts with
        elif self.readEOF == True:
            # => EOF alredy hitted => nothing more to read (file is finished)
            return <bint>False # => finished
        else: # EOF not hitted => potentialy more to read (file not finished yet)
            # => read next and recreate the .buffer
            readedArray = reader_file.read(self.readSize)
            readed_size = len(readedArray)
            
            # extend the buffer
            BytesSlice_recycle(self.buffer, BytesSlice_copyTo_bytes(self.buffer) + readedArray)

            if readed_size < self.readSize: # => EOF reached
                self.readEOF = <bint>True
            continue # continue with the new buffer
        
    # => (self.readEOF is True) and (len(self.buffer) == 0)
    return <bint>False


cdef bint Reader2_skipPatternStringIf_startsWith(Reader2 *self, String *pattern):
    if Reader2_startsWithPatternString(self, pattern) is True:
        BytesSlice_cutStart(self.buffer, pattern.size)
        return <bint>True
    # else => self.startsWith(pattern) is False
    return <bint>False