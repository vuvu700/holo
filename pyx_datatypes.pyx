#cython: language_level=3str
cimport cython
from Cython.Includes.cpython cimport (
    PyObject, Py_XINCREF, Py_XDECREF, freefunc, 
    PyBytes_FromStringAndSize,
)
from libc.stdlib cimport malloc, free, calloc
# NOTE: there is a: `/!\\ MALLOC` when the returned value is from a malloc 


cdef void noFree(void * ptr) noexcept: 
    """don't free the value, usefull to free the struct \
    witout freeing the values shared with another object\n
    to use carefully"""
    ...


cdef enum constants:
    DICTMAP_SIZE = 32
    HASH_SEED = 0xc583ae27 # random number


##################  utils funcs ##################

cdef bint str_compare(String str1, String str2) noexcept:
    "compare the two String (no ptrs)"
    if str1.size != str2.size: return <bint>False
    cdef int index
    for index in range(str1.size):
        if str1.value[index] != str2.value[index]:
            return <bint>False
    return <bint>True

cdef bint string_startsWith(unsigned char* string, int stringSize, unsigned char* pattern, int patternSize) noexcept:
    "whether the string starts with the given pattern"
    cdef int index
    if stringSize < patternSize:
        return <bint>False
    
    # search the pattern in the remaining buffer
    for index in range(0, patternSize):
        if string[index] != pattern[index]:
            return <bint>False

    return <bint>True

cdef int string_findChar(unsigned char* string, int stringSize, unsigned char patternChar) noexcept:
    """return the index of the first occurence of patternChar (size = 1) in the string,\
    -1 if not found"""
    cdef int index
    if stringSize < 1: return -1
    for index in range(stringSize):
        if string[index] == patternChar:
            return index
    return -1

cdef int string_findPattern(unsigned char* string, int stringSize, unsigned char* pattern, int patternSize) noexcept:
    """return the index of the first occurence of the pattern in the string,\
    -1 if not found\n
    the hash calculation is based on a rolling hash (sum of the N last chars) (~20% faster than naive implementation)"""
    cdef int hashPattern = 0, hashString = 0
    cdef bint exactMatch = <bint>True
    cdef int index, deltaIndex, startIndex

    if stringSize < patternSize: return -1
    # compute the hash of the pattren
    # and compute the first hash of the buffer
    for index in range(patternSize):
        hashPattern += pattern[index]
        hashString += string[index]
        if hashPattern != hashString:
            exactMatch = <bint>False
    
    if exactMatch == True:
        # => find starts with pattern
        return 0

    # search the pattern in the remaining buffer
    for index in range(patternSize, stringSize):
        hashString += string[index]
        hashString -= string[index - patternSize]
        if hashString == hashPattern:
            startIndex = index -patternSize +1
            for deltaIndex in range(patternSize):
                if string[startIndex + deltaIndex] != pattern[deltaIndex]:
                    break
            else: # => all chars matched
                return startIndex

    return -1

cdef unsigned char* str_copy(unsigned char *value, int size) noexcept:
    "create a copy of the value array `/!\\ MALLOC`"
    cdef unsigned char* copyValue = <unsigned char*> malloc(<size_t>size * sizeof(char))
    cdef int index
    for index in range(size):
        copyValue[index] = value[index]
    return copyValue


cdef bint string_migthEndsWith(unsigned char* string, int stringSize, unsigned char* pattern, int patternSize) noexcept:
    """to know if the given `string` migth ends with `pattern` \
        (ie: it ends with a fraction of `pattern`)\n
    if `string` or `pattern` is empty, return False"""
    cdef int sliceSize, index
    if stringSize == 0:
        return <bint>False
    if patternSize == 1:
        return string[stringSize - 1] == pattern[0]
    for sliceSize in range(1, patternSize+1):
        if sliceSize > stringSize:
            return <bint>True#<bint>False
        # check that string[-sliceSize: ] == sub[: sliceSize]
        for index in range(sliceSize):
            # check each char
            if string[stringSize-sliceSize + index] != pattern[index]:
                break # => at least one difference
        else: # => string[-sliceSize: ] == sub[: sliceSize]
            return <bint>True
    return <bint>False

cdef bint string_migthStartsWith(
        unsigned char* string, int stringSize, unsigned char* pattern, int patternSize) noexcept:
    """to know if the given `string` migth starts with `pattern` \
        (ie: it starts with a fraction of `pattern`)\n
    False => can't starts with\n
    True => (starts with) if [pattern's size <= buffer's] \
        else (migth starts with => need buffer extend)\n
    if `string` or `pattern` is empty, return True"""
    cdef int index
    # search the pattern in the remaining buffer
    for index in range(0, min(patternSize, stringSize)):
        if string[index] != pattern[index]:
            return <bint>False

    return <bint>True




##################  String  ##################
cdef struct String:
    unsigned char *value
    int size

cdef String* String_create(unsigned char* value, int size) noexcept:
    "create an initialize a String `/!\\ MALLOC`"
    cdef String* string = <String*> malloc(<size_t>sizeof(String))
    string.value = value
    string.size = size
    return string

cdef String* String_create_empty(int size) noexcept:
    "create an empty String of a given size `/!\\ MALLOC`"
    cdef String* string = <String*> malloc(<size_t>sizeof(String))
    string.value = <unsigned char*> malloc(<size_t>size * sizeof(char))
    string.size = size
    return string

cdef String* String_create_copy(String *string) noexcept:
    "create an initialize a String based on the given String `/!\\ MALLOC`"
    cdef String* stringCopy = String_create_empty(string.size)
    cdef int index 
    for index in range(string.size):
        stringCopy.value[index] = string.value[index]
    return stringCopy

cdef String* String_create_fromPyStr(pyString:str):
    "create an initialize a String based on the given python str `/!\\ MALLOC`"
    cdef String string = String(<unsigned char *>pyString.encode(), len(pyString))
    cdef String *res = String_create_copy(&string) # copy needed because string.value is a ptr in a PyObject
    return res

cdef String* String_fromBytes(bytes pyBytes):
    "create an initialize a String based on the given python bytes /!\\ MALLOC"
    cdef String string = String(<unsigned char *>pyBytes, len(pyBytes))
    cdef String *res = String_create_copy(&string) # copy needed because string.value is a ptr in a PyObject
    return res


cdef void String_free_all(String *string) noexcept:
    "free the String and it value"
    if string == NULL: return
    free(string.value)
    free(string)

cdef bint String_compare(String *str1, String *str2):
    if str1 == str2: return <bint>True # compare the ptrs
    return str_compare(str1[0], str2[0])

cdef bytearray String_toBytes(String *str):
    cdef unsigned char *strArray = str.value
    cdef int index
    result:bytearray = bytearray(str.size)

    for index in range(str.size):
        result[index] = strArray[index]
    return result




##################  Node_Any  ##################
cdef struct Node_Any:
    void* value
    void* next # Node_Any*|NULL (when no next)

cdef Node_Any* Node_Any_create(void* value, Node_Any* next) noexcept:
    "create an initialize a Node_Any `/!\\ MALLOC`"
    cdef Node_Any* node = <Node_Any*> malloc(<size_t>sizeof(Node_Any))
    node.value = value
    node.next = next
    return node    


cdef void Node_Any_free_all(Node_Any* node, freefunc value_freeFunc) noexcept:
    "free this node and its value then reccursively the .next (free the whole chain)"
    if node == NULL: return
    value_freeFunc(node.value)
    Node_Any_free_all(<Node_Any*>node.next, value_freeFunc)
    free(node)


##################  LinkedList_Any  ##################
cdef struct LinkedList_Any:
    Node_Any* start
    Node_Any* end # must be the end of the list

cdef LinkedList_Any* LinkedList_Any_create() noexcept:
    "create an empty linked list of Any `/!\\ MALLOC`"
    cdef LinkedList_Any* list = <LinkedList_Any*> malloc(<size_t>sizeof(LinkedList_Any))
    list.start = list.end = NULL
    return list

cdef void LinkedList_Any_free_all(LinkedList_Any* list, freefunc value_freeFunc) noexcept:
    "free the whole liste (including the str of each node)"
    if list == NULL: return
    Node_Any_free_all(list.start, value_freeFunc) #NOTE: don't stop at .end if it is not the real end of the chain
    free(list)

cdef void LinkedList_Any_append(LinkedList_Any* list, void *value) noexcept:
    "append the string at the end of the end of the list `/!\\ MALLOC`"
    cdef Node_Any* newNode = Node_Any_create(value, NULL)
    if list.end == NULL:
        list.start = list.end = newNode
    else: # => list.end != NULL
        list.end.next = newNode
        list.end = newNode


################## BytesIO_like  ##################

cdef struct BytesIO_like:
    LinkedList_Any *list # LinkedList_Any[String*]
    int totalSize # the total size of each strings of the list

cdef BytesIO_like* BytesIO_like_create() noexcept:
    "create an empty BytesIO like `/!\\ MALLOC`"
    cdef BytesIO_like* stream = <BytesIO_like*> malloc(<size_t>sizeof(BytesIO_like))
    stream.list = LinkedList_Any_create()
    stream.totalSize = 0
    return stream    


cdef void BytesIO_like_free_all(BytesIO_like* stream) noexcept:
    "free the whole liste (including the str of each node)"
    if stream == NULL: return
    LinkedList_Any_free_all(stream.list, <freefunc>String_free_all)
    free(stream)

cdef void BytesIO_like_append(BytesIO_like* stream, String *string) noexcept:
    "append the string at the end of the end of the list"
    LinkedList_Any_append(stream.list, string)
    stream.totalSize += string.size

cdef String* BytesIO_like_getValue(BytesIO_like* stream) noexcept:
    """return a string containing the combined strings of the list `/!\\ MALLOC`"""
    cdef String *result = String_create_empty(stream.totalSize)
    cdef unsigned char *resultArray = result.value
    cdef int writeIndex = 0, deltaIndex
    cdef LinkedList_Any *list = stream.list
    cdef Node_Any* node = list.start
    cdef String *nodeString
    while node != NULL:
        # write the value of the current node
        nodeString = <String*>node.value 
        for deltaIndex in range(nodeString.size):
            resultArray[writeIndex + deltaIndex] = nodeString.value[deltaIndex]
        writeIndex += nodeString.size
        # go to next node
        node = <Node_Any*>node.next
    return result



##################  StringSlice  ##################
cdef struct StringSlice:
    unsigned char* array # NULL => empty
    int start
    int stop

cdef StringSlice* StringSlice_create(unsigned char *array, int start, int stop) noexcept:
    "create and initialize a StringSlice `/!\\ MALLOC`"
    cdef StringSlice* stringSlice = <StringSlice*> malloc(<size_t>sizeof(StringSlice))
    stringSlice.array = array
    stringSlice.start = start
    stringSlice.stop = stop
    return stringSlice

cdef StringSlice *StringSlice_create_empty(int size) noexcept:
    "create an empty StringSlice of a certain size `/!\\ MALLOC`"
    cdef unsigned char* string = <unsigned char*> malloc(<size_t>size * sizeof(char))
    return StringSlice_create(string, 0, size)

cdef void StringSlice_free_all(StringSlice* self) noexcept:
    "free the whole string slice and all its nodes"
    if self == NULL: return
    free(self.array)
    free(self)

cdef int _StringSlice_getNewPos(StringSlice *self, int relativeIndex) noexcept nogil:
    """the new position of the index relative to the current start/stop\n
    return value is bounded to the start/stop (nor lower or bigger)"""
    if relativeIndex == 0: 
        return self.start
    elif relativeIndex > 0: 
        return min(self.start + relativeIndex, self.stop)
    # => (relativeIndex < 0) => from the end
    else: return max(self.stop + relativeIndex, self.start)

cdef void StringSlice_cutStart(StringSlice *self, int newStart) noexcept nogil:
    self.start = _StringSlice_getNewPos(self, newStart)

cdef void StringSlice_cutSlice(StringSlice *self, int newStart, int newStop) noexcept nogil:
    self.start = _StringSlice_getNewPos(self, newStart)
    self.stop = _StringSlice_getNewPos(self, newStop)

cdef inline int StringSlice_size(StringSlice *self) noexcept nogil:
    return self.stop - self.start

cdef void StringSlice_copyFrom_StringSlice(StringSlice *self, int selfStart, StringSlice *other) noexcept:
    # determine the size of the sub slice
    cdef int newStart = _StringSlice_getNewPos(self, selfStart)
    cdef int otherSize = StringSlice_size(other)
    cdef int newStop = _StringSlice_getNewPos(self, selfStart + otherSize)
    cdef int writeSize = newStop - newStart
    assert writeSize == otherSize, \
        IndexError(f"missmatching sizes: writeSize:{writeSize} != otherSize:{otherSize}")
    # copy from 
    cdef int deltaIndex, otherStart = other.start
    cdef unsigned char *selfArray = self.array
    cdef unsigned char *otherArray = other.array
    for deltaIndex in range(writeSize):
        selfArray[newStart + deltaIndex] = \
            otherArray[otherStart + deltaIndex]

cdef int StringSlice_copyFrom_Bytes(StringSlice *self, int selfStart, bytes other):
    "return the size copyed"
    # determine the size of the sub slice
    cdef int newStart = _StringSlice_getNewPos(self, selfStart)
    cdef int otherSize = len(other)
    cdef int newStop = _StringSlice_getNewPos(self, selfStart + otherSize)
    cdef int writeSize = newStop - newStart
    assert writeSize == otherSize, \
        IndexError(f"missmatching sizes: writeSize:{writeSize} != otherSize:{otherSize}")
    # copy from 
    cdef int deltaIndex
    cdef unsigned char *selfArray = self.array
    cdef unsigned char *otherArray = <unsigned char*>other #NOTE: pointer to object's internal data => no free
    for deltaIndex in range(writeSize):
        selfArray[newStart + deltaIndex] = otherArray[deltaIndex]
    return otherSize

cdef String* StringSlice_copyTo_String(StringSlice *self, int selfStart, int selfStop) noexcept:
    # determine the size of the sub slice
    cdef int newStart = _StringSlice_getNewPos(self, selfStart)
    cdef int newStop = _StringSlice_getNewPos(self, selfStop)
    cdef int writeSize = newStop - newStart
    # create the target string
    cdef unsigned char *otherArray = <unsigned char*> malloc(<size_t> writeSize * sizeof(char))
    cdef String *target = String_create(otherArray, writeSize) # /!\ MALLOC (to return)
    # copy to
    cdef int deltaIndex
    cdef unsigned char *selfArray = self.array
    for deltaIndex in range(writeSize):
        otherArray[deltaIndex] = \
            selfArray[newStart + deltaIndex]
    return target

cdef bint StringSlice_startsWith(StringSlice *slice, unsigned char* pattern, int patternSize) noexcept:
    "whether the slice starts with the given pattern"
    if slice == NULL: return <bint>False
    return string_startsWith(slice.array+slice.start, StringSlice_size(slice), pattern, patternSize)

cdef int StringSlice_findChar(StringSlice *slice, unsigned char patternChar) noexcept:
    """return the index of the first occurence of patternChar (size = 1) in the slice,\
    -1 if not found"""
    if slice == NULL: return -1
    return string_findChar(slice.array+slice.start, StringSlice_size(slice), patternChar)

cdef int StringSlice_findPattern(StringSlice *slice, unsigned char* pattern, int patternSize) noexcept:
    """return the index of the first occurence of the pattern in the slice,\
    -1 if not found\n
    the hash calculation is based on a rolling hash (sum of the N last chars)"""
    if slice == NULL: return -1
    return string_findPattern(slice.array+slice.start, StringSlice_size(slice), pattern, patternSize)

cdef bint StringSlice_migthEndsWith(StringSlice *slice, unsigned char* pattern, int patternSize) noexcept:
    """to know if the given `string` migth ends with `pattern` \
        (ie: it ends with a fraction of `pattern`)\n
    if `string` or `pattern` is empty, return False"""
    if slice == NULL: return <bint>False
    return string_migthEndsWith(slice.array+slice.start, StringSlice_size(slice), pattern, patternSize)



##################  BytesSlice  ##################
cdef struct BytesSlice:
    PyObject *fromBytes # bytes
    unsigned char* array
    int start
    int stop

cdef BytesSlice* BytesSlice_create(bytes fromBytes):
    """create and initialize a BytesSlice `/!\\ MALLOC`"""
    cdef BytesSlice* bytesSlice = <BytesSlice*> malloc(<size_t>sizeof(BytesSlice))
    cdef PyObject *pyBytes = <PyObject*> fromBytes
    Py_XINCREF(pyBytes); bytesSlice.fromBytes = pyBytes
    bytesSlice.array = <unsigned char*>fromBytes
    bytesSlice.start = 0
    bytesSlice.stop = len(fromBytes)
    return bytesSlice

cdef void BytesSlice_recycle(BytesSlice *self, bytes newFromBytes):
    """recycle a BytesSlice with a new bytes avoids free/malloc"""
    # forget the old bytes
    Py_XDECREF(self.fromBytes)
    # replace with the new bytes
    cdef PyObject *pyBytes = <PyObject*> newFromBytes
    Py_XINCREF(pyBytes); self.fromBytes = pyBytes
    self.array = <unsigned char*>newFromBytes
    self.start = 0
    self.stop = len(newFromBytes)

cdef void BytesSlice_free_all(BytesSlice* self):
    "free the whole BytesSlice and decrement the fromBytes"
    if self == NULL: return
    Py_XDECREF(self.fromBytes)
    self.fromBytes = NULL
    free(self)

cdef void BytesSlice_release(BytesSlice* self):
    """'empty' the slice, decrement the fromBytes and set the array to NULL"""
    if self == NULL: return
    Py_XDECREF(self.fromBytes)
    self.fromBytes = NULL
    self.array = NULL
    self.start = 0
    self.stop = 0

cdef int _BytesSlice_getNewPos(BytesSlice *self, int relativeIndex) noexcept nogil:
    """the new position of the index relative to the current start/stop\n
    return value is bounded to the start/stop (nor lower or bigger)"""
    if relativeIndex == 0: 
        return self.start
    elif relativeIndex > 0: 
        return min(self.start + relativeIndex, self.stop)
    # => (relativeIndex < 0) => from the end
    else: return max(self.stop + relativeIndex, self.start)

cdef void BytesSlice_cutStart(BytesSlice *self, int newStart) noexcept nogil:
    """return the start of the current slice"""
    self.start = _BytesSlice_getNewPos(self, newStart)

cdef void BytesSlice_cutSlice(BytesSlice *self, int newStart, int newStop) noexcept nogil:
    """return the start and the end of the current slice"""
    self.start = _BytesSlice_getNewPos(self, newStart)
    self.stop = _BytesSlice_getNewPos(self, newStop)

cdef inline int BytesSlice_size(BytesSlice *self) noexcept nogil:
    """return the size of the current slice"""
    return self.stop - self.start

cdef String* BytesSlice_copyTo_String(BytesSlice *self, int selfStart, int selfStop) noexcept:
    """return a String* copy of the slice (after `selfStart` and `selfStop`)"""
    # determine the size of the sub slice
    cdef int newStart = _BytesSlice_getNewPos(self, selfStart)
    cdef int newStop = _BytesSlice_getNewPos(self, selfStop)
    cdef int writeSize = newStop - newStart
    # create the target string
    cdef unsigned char *otherArray = <unsigned char*> malloc(<size_t>writeSize * sizeof(char)) # /!\ MALLOC (held by returned String)
    cdef String *target = String_create(otherArray, writeSize) # /!\ MALLOC (to return)
    # copy to
    cdef int deltaIndex
    cdef unsigned char *selfArray = self.array
    for deltaIndex in range(writeSize):
        otherArray[deltaIndex] = \
            selfArray[newStart + deltaIndex]
    return target

cdef bytes BytesSlice_copyTo_bytes(BytesSlice *self):
    """return a bytes copy of the current slice"""
    return PyBytes_FromStringAndSize(<char*>self.array+self.start, <Py_ssize_t>BytesSlice_size(self))

cdef bytes BytesSlice_copyTo_bytes2(BytesSlice *self, int selfStart, int selfStop):
    """return a bytes copy of the current slice"""
    cdef int newStart = _BytesSlice_getNewPos(self, selfStart)
    cdef int newStop = _BytesSlice_getNewPos(self, selfStop)
    cdef int writeSize = newStop - newStart
    return PyBytes_FromStringAndSize(<char*>self.array+newStart, <Py_ssize_t>writeSize)


cdef bint BytesSlice_startsWith(BytesSlice *slice, unsigned char* pattern, int patternSize) noexcept:
    "whether the slice starts with the given pattern"
    return string_startsWith(slice.array+slice.start, BytesSlice_size(slice), pattern, patternSize)

cdef bint BytesSlice_migthStartsWith(BytesSlice *slice, unsigned char* pattern, int patternSize) noexcept:
    """to know if the given `string` migth starts with `pattern` \
        (ie: it starts with a fraction of `pattern`)\n
    False => can't starts with\n
    True => (starts with) if [pattern's size <= buffer's] \
        else (migth starts with => need buffer extend)\n
    if `string` or `pattern` is empty, return True"""
    return string_migthStartsWith(slice.array+slice.start, BytesSlice_size(slice), pattern, patternSize)


cdef int BytesSlice_findChar(BytesSlice *slice, unsigned char patternChar) noexcept:
    """return the index of the first occurence of patternChar (size = 1) in the slice,\
    -1 if not found"""
    return string_findChar(slice.array+slice.start, BytesSlice_size(slice), patternChar)

cdef int BytesSlice_findPattern(BytesSlice *slice, unsigned char* pattern, int patternSize) noexcept:
    """return the index of the first occurence of the pattern in the slice,\
    -1 if not found\n
    the hash calculation is based on a rolling hash (sum of the N last chars)"""
    return string_findPattern(slice.array+slice.start, BytesSlice_size(slice), pattern, patternSize)

cdef int BytesSlice_findBytesPattern(BytesSlice *slice, bytes pattern):
    """return the index of the first occurence of the pattern in the slice, -1 if not found\n"""
    cdef int absIndex = (<bytes>slice.fromBytes).find(pattern, slice.start, slice.stop)
    if absIndex != -1: 
        # => found, return relative index
        return absIndex - slice.start 
    return -1 # => not found

cdef bint BytesSlice_migthEndsWith(BytesSlice *slice, unsigned char* pattern, int patternSize) noexcept:
    """to know if the given `string` migth ends with `pattern` \
        (ie: it ends with a fraction of `pattern`)\n
    if `string` or `pattern` is empty, return False"""
    return string_migthEndsWith(slice.array+slice.start, BytesSlice_size(slice), pattern, patternSize)





##################  Dict_StrAny  ##################

cdef struct MapStrAny_Node:
    # the node that contain the key and its value
    String key
    void *value # Any* != NULL
    void *next # MapStrAny_Node* | NULL(default), the next (key: value) that have the save hash

cdef MapStrAny_Node* _MapStrAny_Node_create(String key, void *value) noexcept:
    """create and initialize a MapStrAny_Node `/!\\ MALLOC`\n
    `/!\\ MALLOC`(2) copy the key"""
    cdef MapStrAny_Node* node = <MapStrAny_Node*> malloc(<size_t>sizeof(MapStrAny_Node))
    node.key.value = str_copy(key.value, key.size)
    node.key.size = key.size
    node.value = value
    node.next = NULL
    return node

cdef void MapStrAny_Node_free_all(MapStrAny_Node *node, freefunc value_freeFunc) noexcept:
    "free the node, the key, the value, and the next nodes"
    if node == NULL: return
    free(node.key.value) # the key is part of the MapStrAny_Node, so only the value is a copy
    value_freeFunc(node.value)
    MapStrAny_Node_free_all(<MapStrAny_Node*>node.next, value_freeFunc)
    free(node)

cdef void* _MapStrAny_Node_get(MapStrAny_Node *node, String key) noexcept:
    "return the value if found, or NULL if not found"
    if node == NULL: return NULL # => not found
    if str_compare(node.key, key):
        # => found
        return node.value
    # => search in next
    return _MapStrAny_Node_get(<MapStrAny_Node*>node.next, key)

cdef bint _MapStrAny_Node_contain(MapStrAny_Node *node, String key) noexcept:
    "return the value if found, or NULL if not found"
    if node == NULL:
        return <bint>False # => not found
    elif str_compare(node.key, key):
        # => found
        return <bint>True
    else:
            # => search in next
        return _MapStrAny_Node_contain(<MapStrAny_Node*>node.next, key)


cdef void _MapStrAny_Node_set(MapStrAny_Node *node, String key, void *value, freefunc value_freeFunc) noexcept:
    """set the value and key in the nodes, \n
    if the value is alredy present replace it and free the other\n
    node and value must not be NULL"""
    if str_compare(node.key, key):
        # => found => replace it
        value_freeFunc(node.value)
        node.value = value
    # => not found
    elif node.next == NULL: # => end reached => add it here
        node.next = _MapStrAny_Node_create(key, value)
    else: # => go to the next
        _MapStrAny_Node_set(<MapStrAny_Node*>node.next, key, value, value_freeFunc)


cdef struct Dict_StrAny:
    MapStrAny_Node ** map # array of MapStrAny_Node* | NULL (only for the hashs that have a key)
    int mapSize


cdef Dict_StrAny* Dict_StrAny_create() noexcept:
    """create and initialize a StringSlice `/!\\ MALLOC`\n
    copy the keys"""
    cdef Dict_StrAny* dictionary = <Dict_StrAny*> malloc(<size_t>sizeof(Dict_StrAny))
    dictionary.mapSize = constants.DICTMAP_SIZE
    dictionary.map = <MapStrAny_Node**> calloc(<size_t>dictionary.mapSize, <size_t>sizeof(MapStrAny_Node*))
    return dictionary

cdef void Dict_StrAny_free_all(Dict_StrAny* dictionary, freefunc value_freeFunc) noexcept:
    "free the whole map, the keys and the values"
    if dictionary == NULL: return
    cdef int indexNode
    for indexNode in range(dictionary.mapSize):
        MapStrAny_Node_free_all(dictionary.map[indexNode], value_freeFunc)
    free(dictionary.map)
    free(dictionary)


cdef int _Dict_StrAny_hashKey(String key, int mapSize) noexcept:
    "return the position on the map of the node"
    # NOTE: use teh MurmurHash3_x86_32 hash function
    cdef int hash = constants.HASH_SEED, index
    for index in range(key.size):
        #hash += <unsigned char>key[index]
        hash ^= <unsigned char>key.value[index]
        hash *= 0x5bd1e995 # magic number 
        hash ^= (hash >> 15)
    with cython.cdivision: # typing: ignore is ok
        return hash % mapSize

cdef void Dict_StrAny_set(Dict_StrAny *dictionary, String key, void *value, freefunc value_freeFunc) noexcept:
    """set the value and key,\n
    if the value is alredy present replace it and free the other\n
    node and value must not be NULL"""
    cdef int keyHash = _Dict_StrAny_hashKey(key, dictionary.mapSize)
    cdef MapStrAny_Node* node = dictionary.map[keyHash]
    if node == NULL:
        # => fist key with this hash => create and set the node
        dictionary.map[keyHash] = _MapStrAny_Node_create(key, value)
        return
    # => set inside the node
    _MapStrAny_Node_set(node, key, value, value_freeFunc)

cdef void* Dict_StrAny_get(Dict_StrAny *dictionary, String key) noexcept:
    "return the value if found, or NULL if not found"
    cdef int keyHash = _Dict_StrAny_hashKey(key, dictionary.mapSize)
    cdef MapStrAny_Node* node = dictionary.map[keyHash]
    if node == NULL: # => no key with this hash
        return NULL
    # => get from the node
    return _MapStrAny_Node_get(node, key)

cdef bint Dict_StrAny_contain(Dict_StrAny *dictionary, String key) noexcept:
    "return whether the dict contain the key"
    cdef int keyHash = _Dict_StrAny_hashKey(key, dictionary.mapSize)
    cdef MapStrAny_Node* node = dictionary.map[keyHash]
    if node == NULL: # => no key with this hash
        return <bint>False
    # => get from the node
    return _MapStrAny_Node_contain(node, key)

cdef LinkedList_Any* Dict_StrAny_items(Dict_StrAny *dictionary) noexcept:
    """return a LinkedList_Any[MapStrAny_Node*] containing the nodes (copy the strings) `/!\\ MALLOC`\n
    NOTE: current complexity: O(dict's map size * map's depth), can store the items directly if too much perf impact"""
    cdef MapStrAny_Node *node
    cdef LinkedList_Any *result = LinkedList_Any_create() # /!\ MALLOC (to return)
    "LinkedList_Any[MapStrAny_Node*]"
    cdef int indexMap
    for indexMap in range(constants.DICTMAP_SIZE):
        node = dictionary.map[indexMap]
        # append all the nodes at this hash
        while node != NULL:
            LinkedList_Any_append(result, node)
            node = <MapStrAny_Node*>node.next
    return result


