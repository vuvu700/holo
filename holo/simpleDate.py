from .__typing import overload, cast
from .prettyFormats import prettyTime


class TimeUnite:
    "is a time unite that correspond to 1 second"
    __slots__ = ("fullUnites", "partialUnits")
    @overload
    def __init__(self, nbUnites:int=1, nbPartialUnites:float=0., _directCopy:bool=False) -> None: ...
    @overload
    def __init__(self, nbUnites:"int|float"=1, ) -> None: ...
    def __init__(self, nbUnites:"int|float"=1, nbPartialUnites:float=0., _directCopy:bool=False) -> None:
        self.fullUnites:int; self.partialUnits:float
        if _directCopy is True:
            self.fullUnites = cast(int, nbUnites) # cast because of overload
            self.partialUnits = nbPartialUnites
            return None # => finished
        
        if isinstance(nbUnites, int):
            self.fullUnites = nbUnites
            self.partialUnits = 0.
        else: # => nbUnites is a float
            self.fullUnites = int(nbUnites // 1)
            self.partialUnits = (nbUnites % 1)
        if nbPartialUnites != 0.:
            (additionalFullUnites, self.partialUnits) = \
                divmod(self.partialUnits + nbPartialUnites, 1)
            self.fullUnites += int(additionalFullUnites)
        
    def __add__(self, other:"TimeUnite|int|float")->"TimeUnite":
        if isinstance(other, TimeUnite):
            return TimeUnite((self.fullUnites+other.fullUnites), (self.partialUnits+other.partialUnits), _directCopy=True)
        else: return self + TimeUnite(other)
    def __sub__(self, other:"TimeUnite|int|float")->"TimeUnite":
        if isinstance(other, TimeUnite):
            return TimeUnite((self.fullUnites-other.fullUnites), (self.partialUnits-other.partialUnits), _directCopy=True)
        else: return self + TimeUnite(other)
    __radd__ = __add__; __rsub__ = __sub__
    
    def __mul__(self, other:"int|float")->"TimeUnite":
        if isinstance(other, int):
            return TimeUnite((self.fullUnites*other), (self.partialUnits*other), _directCopy=True)
        else: return TimeUnite((self.fullUnites + self.partialUnits) * other)
    def __truediv__(self, other:"int|float")->"TimeUnite":
        return TimeUnite((self.fullUnites + self.partialUnits) / other)
    __rmul__ = __mul__; __rtruediv__ = __truediv__

    def __neg__(self)->"TimeUnite": return TimeUnite(-(self.fullUnites + self.partialUnits))
    def __pos__(self)->"TimeUnite": return TimeUnite(self.fullUnites, self.partialUnits, _directCopy=True)
    __rneg__ = __neg__; __rpos__ = __pos__

    def nbSeconds(self)->float:
        """the total number of seconds"""
        return self.fullUnites + self.partialUnits
    
    def __str__(self)->str:
        nbSeconds:float = self.nbSeconds()
        return ("" if nbSeconds >= 0. else "-") + prettyTime(abs(nbSeconds))
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.fullUnites}, {self.partialUnits})"
    
second:TimeUnite = TimeUnite()
minute:TimeUnite = 60 * second
hour:TimeUnite = 60 * minute
day:TimeUnite = 24 * hour
week:TimeUnite = 7 * day
