"""
an utility to make numba functions compilation much easier
"""

import attrs
import numba
from numba.core.typing.templates import Signature

from .__typing import (
    Literal, TypeAlias, Iterable, 
    Protocol, FinalClass, )

_Bitwidth = Literal[8, 16, 32, 64, 128]
_JitableBaseType = Literal["int", "float", "bool", "complex", "uint", "void", "str"]
_FuncDefinition:TypeAlias = "tuple[SupportsJitType, Iterable[SupportsJitType]]"



class SupportsJitType(Protocol):
    def __call__(self, *types:"SupportsJitType")->"_FuncDefinition":
        ...
        
    def getNumbaType(self, bitwidth:"_Bitwidth")->"numba.types.Type":
        ...



@attrs.frozen
class JitType():
    baseType: "_JitableBaseType"
    nbDims: int = 0
    """number of dimentions: 0 -> value; 1 -> array; 2 -> matrix ..."""
    fixedBitwidth: "None|_Bitwidth" = None

    def __call__(self, *types:"SupportsJitType")->"_FuncDefinition":
        return (self, types)

    def getNumbaType(self, bitwidth:"_Bitwidth")->"numba.types.Type":
        if self.fixedBitwidth is not None: 
            bitwidth = self.fixedBitwidth
        numbaType:"numba.types.Type"
        if self.baseType == "int":
            numbaType = numba.types.Integer(f"int{bitwidth}")
        elif self.baseType == "uint":
            numbaType = numba.types.Integer(f"uint{bitwidth}")
        elif self.baseType == "float":
            numbaType = numba.types.Float(f"float{bitwidth}")
        elif self.baseType == "complex":
            numbaType = numba.types.Complex(
                f"complex{bitwidth*2}",
                numba.types.Float(f"float{bitwidth}"))
        elif self.baseType == "bool":
            numbaType = numba.types.bool_ # ignore bitwidth
        elif self.baseType == "void":
            numbaType = numba.types.void # ignore bitwidth
        elif self.baseType == "str":
            numbaType = numba.types.string # ignore bitwidth
        else: raise ValueError(f"unsupported base type: {self.baseType}")
        # use the correct dims
        if self.nbDims == 0: # => value
            return numbaType
        else: # => add dims
            return numbaType.__getitem__([slice(None)] * self.nbDims)

@attrs.frozen
class JitUniTuple(SupportsJitType):
    subType: "JitType"
    count: int
    
    def __call__(self, *types:"JitType")->"_FuncDefinition":
        return (self, types)
    
    def getNumbaType(self, bitwidth:"_Bitwidth")->"numba.types.Type":
        return numba.types.UniTuple(
            self.subType.getNumbaType(bitwidth), 
            count=self.count)
        

class JitTuple(FinalClass, SupportsJitType):
    __slots__ = ("elements", )
    def __init__(self, *elements:"SupportsJitType") -> None:
        self.elements: "tuple[SupportsJitType, ...]" = elements
    
    def __call__(self, *types:"JitType")->"_FuncDefinition":
        return (self, types)
    
    def getNumbaType(self, bitwidth:"_Bitwidth")->"numba.types.Type":
        return numba.types.Tuple(tuple(
            subType.getNumbaType(bitwidth) for subType in self.elements))


def createDefinition(definition:"_FuncDefinition", bitwidth:"_Bitwidth")->Signature:
    outputType:"SupportsJitType" = definition[0]
    parameterTypes:"Iterable[SupportsJitType]" = definition[1]
    return outputType.getNumbaType(bitwidth)(*(
        jitType.getNumbaType(bitwidth) for jitType in parameterTypes))


@attrs.frozen
class Jitter():
    nopython:bool
    nogil:bool
    cache:bool
    bitwidths:"set[_Bitwidth]|None"
    fastmath: bool
    parallel: bool

    def __call__(self, 
            definition:"_FuncDefinition", bitwidths:"set[_Bitwidth]|None"=None,
            boundedLocals:"dict[str, numba.types.Type]|None"=None, 
            parallel:"bool|None"=None, inline:bool=False):
        """generate a numba.jit for a function with the given specifations\n
        `definition` is the type definition of the func to jit\n
        `bitwidths` the bitwidth to compile the functions with (None -> use the ones from `self`)\n
        `boundedLocals` a dict (varName -> numbaType) to force the type of some local variables\n
        `parallel` enable parallelization with numba.prange (disabled by default)"""
        if bitwidths is None:
            bitwidths = self.bitwidths
        assert (bitwidths is not None), ValueError(f"couldn't find bitwidths")
        if parallel is None: 
            parallel = self.parallel
        if boundedLocals is None: boundedLocals = {} # None not supported
        return numba.jit(
            [createDefinition(definition, bitwidth) for bitwidth in bitwidths],
            nopython=self.nopython, nogil=self.nogil, cache=self.cache,
            locals=boundedLocals, parallel=parallel, fastmath=self.fastmath,
            inline=("never" if inline is False else "always"))

    def getJitKwargs(self)->"dict[str, bool]":
        return {"nopython": self.nopython, "nogil": self.nogil, "cache": self.cache}

# values
integer = JitType("int", nbDims=0)
int32 = JitType("int", nbDims=0, fixedBitwidth=32)
int64 = JitType("int", nbDims=0, fixedBitwidth=64)
floating = JitType("float", nbDims=0)
float64 = JitType("float", nbDims=0, fixedBitwidth=64)
float32 = JitType("float", nbDims=0, fixedBitwidth=32)
boolean = JitType("bool", nbDims=0, fixedBitwidth=8)
void = JitType("void")
string = JitType("str")

# arrays
intArray = JitType("int", nbDims=1)
int64Array = JitType("int", nbDims=1, fixedBitwidth=64)
int32Array = JitType("int", nbDims=1, fixedBitwidth=32)
floatArray = JitType("float", nbDims=1)
float64Array = JitType("float", nbDims=1, fixedBitwidth=64)
float32Array = JitType("float", nbDims=1, fixedBitwidth=32)
boolArray = JitType("bool", nbDims=1, fixedBitwidth=8)

# matrix
intMatrix = JitType("int", nbDims=2)
floatMatrix = JitType("float", nbDims=2)
float64Matrix = JitType("float", nbDims=2, fixedBitwidth=64)
float32Matrix = JitType("float", nbDims=2, fixedBitwidth=32)
boolMatrix = JitType("bool", nbDims=2, fixedBitwidth=8)


basicJitter = Jitter(nopython=False, nogil=False, cache=False,
                     bitwidths=None, fastmath=False, parallel=False)
fastJitter = Jitter(nopython=True, nogil=True, cache=True, 
                    bitwidths={32, 64}, fastmath=False, parallel=False)