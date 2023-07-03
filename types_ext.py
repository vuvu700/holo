import numpy
from typing import TYPE_CHECKING, Tuple

if TYPE_CHECKING:
    _Serie_Float = numpy.ndarray[int, numpy.dtype[numpy.floating]]
    _Serie_Integer = numpy.ndarray[int, numpy.dtype[numpy.integer]]
    _Serie_Boolean = numpy.ndarray[int, numpy.dtype[numpy.bool_]]

    _1dArray_Float = numpy.ndarray[Tuple[int], numpy.dtype[numpy.floating]]
    _2dArray_Float = numpy.ndarray[Tuple[int, int], numpy.dtype[numpy.floating]]
    _3dArray_Float = numpy.ndarray[Tuple[int, int, int], numpy.dtype[numpy.floating]]

    _1dArray_Integer = numpy.ndarray[Tuple[int], numpy.dtype[numpy.integer]]
    _2dArray_Integer = numpy.ndarray[Tuple[int, int], numpy.dtype[numpy.integer]]
    _3dArray_Integer = numpy.ndarray[Tuple[int, int, int], numpy.dtype[numpy.integer]]


else:
    from typing import _GenericAlias
    _Serie_Float =   _GenericAlias(numpy.ndarray, (int, _GenericAlias(numpy.dtype, (numpy.floating))))
    _Serie_Integer =   _GenericAlias(numpy.ndarray, (int, _GenericAlias(numpy.dtype, (numpy.integer))))
    _Serie_Boolean =   _GenericAlias(numpy.ndarray, (int, _GenericAlias(numpy.dtype, (numpy.bool_))))

    _1dArray_Float = _GenericAlias(numpy.ndarray, (Tuple[int], _GenericAlias(numpy.dtype, (numpy.floating))))
    _2dArray_Float = _GenericAlias(numpy.ndarray, (Tuple[int, int], _GenericAlias(numpy.dtype, (numpy.floating))))
    _3dArray_Float = _GenericAlias(numpy.ndarray, (Tuple[int, int, int], _GenericAlias(numpy.dtype, (numpy.floating))))

    _1dArray_Integer = _GenericAlias(numpy.ndarray, (Tuple[int], _GenericAlias(numpy.dtype, numpy.integer)))
    _2dArray_Integer = _GenericAlias(numpy.ndarray, (Tuple[int, int], _GenericAlias(numpy.dtype, numpy.integer)))
    _3dArray_Integer = _GenericAlias(numpy.ndarray, (Tuple[int, int, int], _GenericAlias(numpy.dtype, numpy.integer)))

