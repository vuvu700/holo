#cython: language_level=3str

from Cython.Includes.cpython cimport PyObject, freefunc


cdef void noFree(void *ptr) noexcept
"""don't free the value, usefull to free the struct \
witout freeing the values shared with another object\n
to use carefully"""



##################  utils funcs ##################

cdef bint str_compare(String str1, String str2)
"compare the two String (no ptrs)"
cdef bint string_startsWith(unsigned char* string, int bufferSize, unsigned char* pattern, int patternSize)
"whether the string starts with the given pattern"
cdef int string_findChar(unsigned char* string, int stringSize, unsigned char patternChar)
"""return the index of the first occurence of patternChar (size = 1) in the string,\
-1 if not found"""
cdef int string_findPattern(unsigned char* string, int stringSize, unsigned char* pattern, int patternSize)
"""return the index of the first occurence of the pattern in the string,\
-1 if not found\n
the hash calculation is based on a rolling hash (sum of the N last chars)"""
cdef unsigned char* str_copy(unsigned char *value, int size)
"create a copy of the value array /!\\ MALLOC"
cdef bint string_migthEndsWith(unsigned char* string, int stringSize, unsigned char* pattern, int patternSize)
"""to know if the given `string` migth ends with `pattern` \
    (ie: it ends with a fraction of `pattern`)\n
if `string` or `pattern` is empty, return False"""
cdef bint string_migthStartsWith(unsigned char* string, int stringSize, unsigned char* pattern, int patternSize)
"""to know if the given `string` migth starts with `pattern` \
    (ie: it starts with a fraction of `pattern`)\n
False => can't starts with\n
True => (starts with) if [pattern's size <= buffer's] \
    else (migth starts with => need buffer extend)\n
if `string` or `pattern` is empty, return True"""

##################  String  ##################
cdef struct String:
    unsigned char *value
    int size

cdef String* String_create(unsigned char* value, int size)
"create an initialize a String /!\\ MALLOC"
cdef String* String_create_empty(int size)
"create an empty String of a given size /!\\ MALLOC"
cdef String* String_create_copy(String *string)
"create an initialize a String based on the given String /!\\ MALLOC"
cdef String* String_create_fromPyStr(str pyString)
"create an initialize a String based on the given python str /!\\ MALLOC"
cdef String* String_fromBytes(bytes pyBytes)
"create an initialize a String based on the given python bytes /!\\ MALLOC"
cdef void String_free_all(String *string)
"free the String and it value"
cdef bint String_compare(String *str1, String *str2)
cdef bytearray String_toBytes(String *str)



##################  Node_Any  ##################
cdef struct Node_Any:
    void* value
    void* next # Node_Any*|NULL (when no next)

cdef Node_Any* Node_Any_create(void* value, Node_Any* next)
"create an initialize a Node_Any /!\\ MALLOC"
cdef void Node_Any_free_all(Node_Any* node, freefunc value_freeFunc)
"free this node and its value then reccursively the .next (free the whole chain)"



##################  LinkedList_Any  ##################
cdef struct LinkedList_Any:
    Node_Any* start
    Node_Any* end # must be the end of the list

cdef LinkedList_Any* LinkedList_Any_create()
"create an empty linked list of Any /!\\ MALLOC"
cdef void LinkedList_Any_free_all(LinkedList_Any* list, freefunc value_freeFunc)
"free the whole liste (including the str of each node)"
cdef void LinkedList_Any_append(LinkedList_Any* list, void *value)
"append the string at the end of the end of the list /!\\ MALLOC"



################## BytesIO_like  ##################
cdef struct BytesIO_like:
    LinkedList_Any *list # LinkedList_Any[str]
    int totalSize # the total size of each strings of the list

cdef BytesIO_like* BytesIO_like_create()
"create an empty BytesIO like /!\\ MALLOC"
cdef void BytesIO_like_free_all(BytesIO_like* stream)
"free the whole liste (including the str of each node)"
cdef void BytesIO_like_append(BytesIO_like* stream, String *string)
"append the string at the end of the end of the list"
cdef String* BytesIO_like_getValue(BytesIO_like* stream)
"""return a string containing the combined strings of the list /!\\ MALLOC"""



##################  BytearraySlice  ##################
cdef struct StringSlice:
    unsigned char* array # NULL => empty
    int start
    int stop

cdef StringSlice* StringSlice_create(unsigned char *array, int start, int stop)
"create and initialize a StringSlice /!\\ MALLOC"
cdef StringSlice *StringSlice_create_empty(int size)
"create an empty StringSlice of a certain size /!\\ MALLOC"
cdef void StringSlice_free_all(StringSlice* self)
"free the whole string slice and all its nodes"
cdef void StringSlice_cutStart(StringSlice *self, int newStart) nogil
cdef void StringSlice_cutSlice(StringSlice *self, int newStart, int newStop) nogil
cdef int StringSlice_size(StringSlice *self) nogil
cdef void StringSlice_copyFrom_StringSlice(StringSlice *self, int selfStart, StringSlice *other)
cdef int StringSlice_copyFrom_Bytes(StringSlice *self, int selfStart, bytes other)
"return the size copyed"
cdef String* StringSlice_copyTo_String(StringSlice *self, int selfStart, int selfStop)
cdef bint StringSlice_startsWith(StringSlice *slice, unsigned char* pattern, int patternSize)
"whether the slice starts with the given pattern"
cdef int StringSlice_findChar(StringSlice *slice, unsigned char patternChar)
"""return the index of the first occurence of patternChar (size = 1) in the slice,\
-1 if not found"""
cdef int StringSlice_findPattern(StringSlice *slice, unsigned char* pattern, int patternSize)
"""return the index of the first occurence of the pattern in the slice,\
-1 if not found\n
the hash calculation is based on a rolling hash (sum of the N last chars)"""
cdef bint StringSlice_migthEndsWith(StringSlice *slice, unsigned char* pattern, int patternSize)
"""to know if the given `string` migth ends with `pattern` \
    (ie: it ends with a fraction of `pattern`)\n
if `string` or `pattern` is empty, return False"""



##################  BytesSlice  ##################
cdef struct BytesSlice:
    PyObject *fromBytes # bytes
    unsigned char* array
    int start
    int stop

cdef BytesSlice* BytesSlice_create(bytes fromBytes)
"""create and initialize a BytesSlice `/!\\ MALLOC`"""
cdef void BytesSlice_recycle(BytesSlice *self, bytes newFromBytes)
"""recycle a BytesSlice with a new bytes avoids free/malloc"""
cdef void BytesSlice_free_all(BytesSlice* self)
"free the whole BytesSlice and decrement the fromBytes"
cdef void BytesSlice_release(BytesSlice* self)
"""'empty' the slice, decrement the fromBytes and set the array to NULL"""
cdef void BytesSlice_cutStart(BytesSlice *self, int newStart) nogil
"""return the start of the current slice"""
cdef void BytesSlice_cutSlice(BytesSlice *self, int newStart, int newStop) nogil
"""return the start and the end of the current slice"""
cdef int BytesSlice_size(BytesSlice *self) nogil
"""return the size of the current slice"""
cdef String* BytesSlice_copyTo_String(BytesSlice *self, int selfStart, int selfStop)
"""return a String* copy of the slice (after `selfStart` and `selfStop`)"""
cdef bytes BytesSlice_copyTo_bytes(BytesSlice *self)
"""return a bytes copy of the current slice"""
cdef bytes BytesSlice_copyTo_bytes2(BytesSlice *self, int selfStart, int selfStop)
"""return a bytes copy of the current slice"""
cdef bint BytesSlice_startsWith(BytesSlice *slice, unsigned char* pattern, int patternSize)
"whether the slice starts with the given pattern"
cdef bint BytesSlice_migthStartsWith(BytesSlice *slice, unsigned char* pattern, int patternSize)
"""to know if the given `string` migth starts with `pattern` \
    (ie: it starts with a fraction of `pattern`)\n
False => can't starts with\n
True => (starts with) if [pattern's size <= buffer's] \
    else (migth starts with => need buffer extend)\n
if `string` or `pattern` is empty, return True"""
cdef int BytesSlice_findChar(BytesSlice *slice, unsigned char patternChar)
"""return the index of the first occurence of patternChar (size = 1) in the slice,\
-1 if not found"""
cdef int BytesSlice_findPattern(BytesSlice *slice, unsigned char* pattern, int patternSize)
"""return the index of the first occurence of the pattern in the slice,\
-1 if not found\n
the hash calculation is based on a rolling hash (sum of the N last chars)"""
cdef int BytesSlice_findBytesPattern(BytesSlice *slice, bytes pattern)
"""return the index of the first occurence of the pattern in the slice, -1 if not found\n"""
cdef bint BytesSlice_migthEndsWith(BytesSlice *slice, unsigned char* pattern, int patternSize)
"""to know if the given `string` migth ends with `pattern` \
    (ie: it ends with a fraction of `pattern`)\n
if `string` or `pattern` is empty, return False"""


##################  Dict_StrAny  ##################
cdef struct MapStrAny_Node:
    # the node that contain the key and its value
    String key
    void *value # Any* != NULL
    void *next # MapStrAny_Node* | NULL(default), the next (key: value) that have the save hash

cdef void MapStrAny_Node_free_all(MapStrAny_Node *node, freefunc value_freeFunc)
"free the node, the key, the value, and the next nodes"

cdef struct Dict_StrAny:
    MapStrAny_Node ** map # array of MapStrAny_Node* | NULL (only for the hashs that have a key)
    int mapSize

cdef Dict_StrAny* Dict_StrAny_create()
"""create and initialize a StringSlice /!\\ MALLOC\n
copy the keys"""
cdef void Dict_StrAny_free_all(Dict_StrAny* dictionary, freefunc value_freeFunc)
"free the whole map, the keys and the values"
cdef void Dict_StrAny_set(Dict_StrAny *dictionary, String key, void *value, freefunc value_freeFunc)
"""set the value and key,\n
if the value is alredy present replace it and free the other\n
node and value must not be NULL"""
cdef void* Dict_StrAny_get(Dict_StrAny *dictionary, String key)
"return the value if found, or NULL if not found"
cdef bint Dict_StrAny_contain(Dict_StrAny *dictionary, String key)
"return whether the dict contain the key"
cdef LinkedList_Any* Dict_StrAny_items(Dict_StrAny *dictionary)
"""return a LinkedList_Any[MapStrAny_Node*] containing the nodes (copy the strings) /!\\ MALLOC\n
NOTE: current complexity: O(dict's map size * map's depth), can store the items directly if too much perf impact"""

