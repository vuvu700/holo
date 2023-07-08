from collections import deque
from time import perf_counter
from io import StringIO

from typing import Iterable, Callable, Any, Iterable, Generic, TypeVar, ContextManager
import sys
if sys.version_info < (3, 11): from typing_extensions import LiteralString, ParamSpec
else: from typing import LiteralString, ParamSpec


_P = ParamSpec("_P")
_T = TypeVar("_T")

_Categorie = TypeVar("_Categorie", bound=LiteralString)
class Profiler(Generic[_Categorie]):
    """mesure the times taken to do things, and get analytics with it"""

    def __init__(self, categories:"list[_Categorie]", nbMesurements:int=60) -> None:
        """`categories`:list[str] is the names of tracked mesures\n
        `nbMesurements`int, is the max nb of mesures to keep"""
        self._categories:"list[_Categorie]" = categories
        self.__nbMesurements:"int" = nbMesurements
        self._mesures:"dict[_Categorie, deque[float]]" = {name: deque() for name in categories}
        """mesures ordering: 0-> most recent, last-> oldest"""
        self.__currentMesurers:"dict[_Categorie, SimpleProfiler]" = {}
        """hold the SimpleProfiler instances to mesure each categories"""
        self.__emaMesure:"dict[_Categorie, float]" = {}
        self.__emaFactor:float = (1 / nbMesurements)

    @property
    def categories(self)->"list[_Categorie]":
        return self._categories
    @property
    def nbMesurements(self)->int:
        return self.__nbMesurements
    @nbMesurements.setter
    def nbMesurements(self, value:int)->None:
        if value == 0: raise ValueError("nbMesurements can't be set to 0")
        self.__nbMesurements = value
        self.__emaFactor = (1 / self.__nbMesurements)
        self._popExcidingMesures(None)

    def clean(self)->None:
        self.__init__(list(self._mesures.keys()), self.__nbMesurements)

    def __updateEma(self, categorie:"_Categorie", newMesuredTime:float)->None:
        """compute and update the ema of the mesures for this categorie"""
        # newEma = oldEma * (1 - alpha) + newTime * alpha

        self.__emaMesure[categorie] = (
            self.__emaMesure.get(categorie, newMesuredTime) * (1 - self.__emaFactor)
            + newMesuredTime * self.__emaFactor
        )

    def addManualMesure(self, categorie:"_Categorie", mesuredTime:float)->None:
        if categorie not in self._mesures:
            raise KeyError(f"the mesure categorie: {categorie} don't exist")
        self._mesures[categorie].appendleft(mesuredTime)
        self._popExcidingMesures(categorie)
        self.__updateEma(categorie, mesuredTime)

    def _popExcidingMesures(self, categorie:"_Categorie|None")->int:
        """pop the values when the number of mesures is over the hist size\n
        `categorie`:str|None, str -> pop for this categorie, None -> all categories\n
        return how much mesures where poped"""
        categories:"Iterable[_Categorie]" = (self._mesures.keys() if categorie is None else [categorie])
        nbPoped:int = 0
        for categorie in categories:
            categorieMesures:"deque[float]" = self._mesures[categorie]
            while len(categorieMesures) > self.__nbMesurements:
                categorieMesures.pop()
                nbPoped += 1
        return nbPoped


    def lastMesure(self, categorie:"_Categorie")->float:
        if self.hasMesure(categorie) is True:
            return self._mesures[categorie][0]
        raise KeyError(f"no mesures for the categorie: {categorie}")
    def avgMesure(self, categorie:"_Categorie")->float:
        if self.hasMesure(categorie) is True:
            return sum(self._mesures[categorie]) / len(self._mesures[categorie])
        raise KeyError(f"no mesures for the categorie: {categorie}")
    def emaMesure(self, categorie:"_Categorie")->float:
        if self.hasMesure(categorie) is True:
            return self.__emaMesure[categorie]
        raise KeyError(f"no ema mesures for the categorie: {categorie}")

    def lastTimes(self, categories:"list[_Categorie]|None"=None)->"dict[_Categorie, float]":
        return {categorie: self.lastMesure(categorie)
                for categorie in self.__getCategories(categories) if self.hasMesure(categorie)}
    def avgTimes(self, categories:"list[_Categorie]|None"=None)->"dict[_Categorie, float]":
        return {categorie: self.avgMesure(categorie)
                for categorie in self.__getCategories(categories) if self.hasMesure(categorie)}
    def emaTimes(self, categories:"list[_Categorie]|None"=None)->"dict[_Categorie, float]":
        return {categorie: self.emaMesure(categorie)
                for categorie in self.__getCategories(categories) if self.hasEmaMesure(categorie)}

    def _str_times(self, formatTimes:"Callable[[float], str]|None", timesDict:"dict[_Categorie, float]")->str:
        formatTimes = (str if formatTimes is None else formatTimes)
        text = StringIO()
        firstCategorie:bool = True
        for (categorie, lastTime) in timesDict.items():
            if firstCategorie is False:
                text.write(", ")
            else: firstCategorie = False
            text.write(f"{categorie}: {formatTimes(lastTime)}")
        return text.getvalue()

    def str_lastTimes(self,
            formatTimes:"Callable[[float], str]|None"=None,
            categories:"list[_Categorie]|None"=None)->"str":
        return self._str_times(formatTimes, self.lastTimes(categories))
    def str_avgTimes(self,
            formatTimes:"Callable[[float], str]|None"=None,
            categories:"list[_Categorie]|None"=None)->"str":
        return self._str_times(formatTimes, self.avgTimes(categories))
    def str_emaTimes(self,
            formatTimes:"Callable[[float], str]|None"=None,
            categories:"list[_Categorie]|None"=None)->"str":
        return self._str_times(formatTimes, self.emaTimes(categories))

    def __getCategories(self, categories:"list[_Categorie]|None")->"Iterable[_Categorie]":
        return (self._mesures.keys() if categories is None else categories)

    def mesure(self, categorie:"_Categorie")->"SimpleProfiler":
        """to be used in:\n
        ```
        with profiler.mesure("categorie"):
            ... # code to mesure
        ```"""
        if categorie in self.__currentMesurers:
            raise RuntimeError(f"the profiler({self}) is alredy monitoring the categorie: {categorie}")
        simpleProfiler:"SimpleProfiler" = SimpleProfiler(categorie, self._setMesure)
        self.__currentMesurers[categorie] = simpleProfiler
        return simpleProfiler

    def _setMesure(self, categorie:"_Categorie", mesuredTime:float)->None:
        """internal function for mesure(...) to add the mesure"""
        self.addManualMesure(categorie, mesuredTime)
        self.__currentMesurers.pop(categorie)

    def hasMesure(self, categorie:"_Categorie")->bool:
        return (len(self._mesures[categorie]) != 0)
    def hasEmaMesure(self, categorie:"_Categorie")->bool:
        return categorie in self.__emaMesure

    def wrapper(self, categorie:"_Categorie")->Callable[[Callable[_P, _T]], Callable[_P, _T]]:
        def wrapper(func:Callable[_P, _T])->Callable[_P, _T]:
            def wrappedFunc(*args:_P.args, **kwargs:_P.kwargs)->_T:
                nonlocal func, self, categorie
                with self.mesure(categorie):
                    return func(*args, **kwargs)
            return wrappedFunc
        return wrapper

class SimpleProfiler(ContextManager):
    """a simple profiler that hold a single mesure"""

    def __init__(self, name:"_Categorie|None"=None, setMesureFunc:"Callable[[_Categorie, float], Any]|None"=None)->None:
        self.name:"_Categorie|None" = name
        self.__setMesureFunc:"Callable[[_Categorie, float], Any]|None" = setMesureFunc
        self.startTime:"float|None" = None
        self.StopTime:"float|None" = None

    def __enter__(self)->"SimpleProfiler":
        self.StopTime = None
        self.startTime = perf_counter()
        return self

    def __exit__(self, *_):
        self.StopTime = perf_counter()
        if self.startTime is None:
            raise RuntimeError("__exit__ called before __enter__ (encountered self.startTime = None)")
        if (self.__setMesureFunc is not None) and (self.name is not None): # => set the mesure
            self.__setMesureFunc(self.name, self.StopTime - self.startTime)

    def perttyStr(self, prettyTimeFunc:"Callable[[float], str]")->str:
        if (self.startTime is None) or (self.StopTime is None):
            return f"SimpleProfiler({self.name}, noTime)"
        return f"SimpleProfiler({self.name}, {prettyTimeFunc(self.StopTime - self.startTime)})"

    def __str__(self)->str:
        return self.perttyStr(lambda t: f"{t:.3e} sec")

    def wrapper(self, func:Callable[_P, _T])->Callable[_P, _T]:
        def wrappedFunc(*args:_P.args, **kwargs:_P.kwargs)->_T:
            nonlocal func, self
            with self:
                return func(*args, **kwargs)
        return wrappedFunc

