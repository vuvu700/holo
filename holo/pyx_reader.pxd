#cython: language_level=3str
from Cython.Includes.cpython cimport PyObject

from pyx_datatypes cimport BytesSlice, BytesIO_like, String

from .protocols import SupportsRead
from . import Pointer


cdef struct Reader2:
    PyObject *file # SupportsRead[bytes]
    int readSize # how much to read each times
    BytesSlice *buffer
    bint readEOF # whether the EOF has been read

cdef Reader2* Reader2_create(file:SupportsRead[bytes], readSize:int|None)
cdef bint Reader2_skipToPattern(Reader2 *self, bytes pattern, bint stopBefore, writer:Pointer[bytes]|None)
cdef bint Reader2_startsWithPattern(Reader2 *self, bytes pattern)
cdef bint Reader2_skipPatternIf_startsWith(Reader2 *self, bytes pattern)
cdef void Reader2_free_all(Reader2 *self)

cdef bint Reader2_skipToPatternString(Reader2 *self, String *pattern, bint stopBefore, BytesIO_like *writer)
cdef bint Reader2_startsWithPatternString(Reader2 *self, String *pattern)
cdef bint Reader2_skipPatternStringIf_startsWith(Reader2 *self, String *pattern)