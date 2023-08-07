from collections import deque
from time import perf_counter

from __typing import (
    Iterable, Callable, Any, Iterable,
    Generic, TypeVar, ContextManager,
    LiteralString, ParamSpec,
)

_P = ParamSpec("_P")
_T = TypeVar("_T")

_Categorie = TypeVar("_Categorie", bound=LiteralString)
class Profiler(Generic[_Categorie]):
    """mesure the times taken to do things, and get analytics with it"""

    def __init__(self,
            categories:"list[_Categorie]", nbMesurements:int|None=None,
            emaFactor:None|int=None, ignoreSimultaneousMesures:bool=False) -> None:
        """`categories`:list[str] is the names of tracked mesures\n
        `nbMesurements`int is the max nb of mesures to keep\n
        `ignoreSimultaneousMesures`:bool is whether an error will be raised when \
            multiples mesures of the same categorie are done, \
            or whether only the fist will be kept, other are ignored\n"""
        self._categories:"list[_Categorie]" = categories
        self.__nbMesurements:"int|None" = nbMesurements
        self._mesures:"dict[_Categorie, deque[float]]" = {name: deque() for name in categories}
        """mesures ordering: 0-> most recent, last-> oldest"""
        self.__currentMesurers:"dict[_Categorie, SimpleProfiler]" = {}
        """hold the SimpleProfiler instances to mesure each categories"""
        self.__emaMesure:"dict[_Categorie, float]" = {}
        self.__emaFactor:float
        if emaFactor is None:
            self.__emaFactor = (1 / (10_000 if self.nbMesurements is None else self.nbMesurements))
        else: self.__emaFactor = (1 / emaFactor)
        self.__totalMesure:"dict[_Categorie, float]" = {categorie: 0. for categorie in self._categories}
        self.ignoreSimultaneousMesures:bool = ignoreSimultaneousMesures

    @property
    def categories(self)->"list[_Categorie]":
        return self._categories
    @property
    def nbMesurements(self)->int|None:
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

    def __updateTotal(self, categorie:"_Categorie", newMesuredTime:float)->None:
        """compute and update the total of the mesures for this categorie"""
        self.__totalMesure[categorie] += newMesuredTime

    def addManualMesure(self, categorie:"_Categorie", mesuredTime:"float|SimpleProfiler")->None:
        if categorie not in self._mesures:
            raise KeyError(f"the mesure categorie: {categorie} don't exist")
        if isinstance(mesuredTime, SimpleProfiler):
            mesuredTime = mesuredTime.time()
        self._mesures[categorie].appendleft(mesuredTime)
        self._popExcidingMesures(categorie)
        self.__updateEma(categorie, mesuredTime)
        self.__updateTotal(categorie, mesuredTime)

    def _popExcidingMesures(self, categorie:"_Categorie|None")->int:
        """pop the values when the number of mesures is over the hist size\n
        `categorie`:str|None, str -> pop for this categorie, None -> all categories\n
        return how much mesures where poped"""
        if self.__nbMesurements is None: return 0
        categories:"Iterable[_Categorie]" = (self._mesures.keys() if categorie is None else [categorie])
        nbPoped:int = 0
        for categorie in categories:
            categorieMesures:"deque[float]" = self._mesures[categorie]
            while len(categorieMesures) > self.__nbMesurements:
                categorieMesures.pop()
                nbPoped += 1
        return nbPoped

    def allMesure(self, categorie:"_Categorie")->list[float]:
        if self.hasMesure(categorie) is True:
            return list(reversed(self._mesures[categorie])) # reversed => first to last mesure
        raise KeyError(f"no mesures for the categorie: {categorie}")
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
    def totalMesure(self, categorie:"_Categorie")->float:
        if self.hasMesure(categorie) is True:
            return self.__totalMesure[categorie]
        raise KeyError(f"no total mesures for the categorie: {categorie}")

    def allTimes(self, categories:"list[_Categorie]|None"=None)->"dict[_Categorie, list[float]]":
        return {categorie: self.allMesure(categorie)
                for categorie in self.__getCategories(categories) if self.hasMesure(categorie)}
    def lastTimes(self, categories:"list[_Categorie]|None"=None)->"dict[_Categorie, float]":
        return {categorie: self.lastMesure(categorie)
                for categorie in self.__getCategories(categories) if self.hasMesure(categorie)}
    def avgTimes(self, categories:"list[_Categorie]|None"=None)->"dict[_Categorie, float]":
        return {categorie: self.avgMesure(categorie)
                for categorie in self.__getCategories(categories) if self.hasMesure(categorie)}
    def emaTimes(self, categories:"list[_Categorie]|None"=None)->"dict[_Categorie, float]":
        return {categorie: self.emaMesure(categorie)
                for categorie in self.__getCategories(categories) if self.hasEmaMesure(categorie)}
    def totalTimes(self, categories:"list[_Categorie]|None"=None)->"dict[_Categorie, float]":
        return {categorie: self.totalMesure(categorie)
                for categorie in self.__getCategories(categories) if self.hasMesure(categorie)}
    
    def str_allTimes(self,
            formatTimes:"Callable[[float], str]|None"=None,
            categories:"list[_Categorie]|None"=None)->dict[_Categorie, list[str]]:
        if formatTimes is None: formatTimes = str
        return {categorie: [formatTimes(timeVal) for timeVal in  self.allMesure(categorie)]
                for categorie in self.__getCategories(categories) if self.hasMesure(categorie)}
    def str_lastTimes(self,
            formatTimes:"Callable[[float], str]|None"=None,
            categories:"list[_Categorie]|None"=None)->dict[_Categorie, str]:
        if formatTimes is None: formatTimes = str
        return {categorie: formatTimes(self.lastMesure(categorie))
                for categorie in self.__getCategories(categories) if self.hasMesure(categorie)}
    def str_avgTimes(self,
            formatTimes:"Callable[[float], str]|None"=None,
            categories:"list[_Categorie]|None"=None)->dict[_Categorie, str]:
        if formatTimes is None: formatTimes = str
        return {categorie: formatTimes(self.avgMesure(categorie))
                for categorie in self.__getCategories(categories) if self.hasMesure(categorie)}
    def str_emaTimes(self,
            formatTimes:"Callable[[float], str]|None"=None,
            categories:"list[_Categorie]|None"=None)->dict[_Categorie, str]:
        if formatTimes is None: formatTimes = str
        return {categorie: formatTimes(self.emaMesure(categorie))
                for categorie in self.__getCategories(categories) if self.hasMesure(categorie)}
    def str_totalTimes(self,
            formatTimes:"Callable[[float], str]|None"=None,
            categories:"list[_Categorie]|None"=None)->dict[_Categorie, str]:
        if formatTimes is None: formatTimes = str
        return {categorie: formatTimes(self.totalMesure(categorie))
                for categorie in self.__getCategories(categories) if self.hasMesure(categorie)}

    def __getCategories(self, categories:"list[_Categorie]|None")->"Iterable[_Categorie]":
        return (self.categories if categories is None else categories)

    def mesure(self, categorie:"_Categorie")->"SimpleProfiler":
        """to be used in:\n
        ```
        with profiler.mesure("categorie"):
            ... # code to mesure
        ```"""
        if categorie in self.__currentMesurers:
            if self.ignoreSimultaneousMesures is False:
                raise RuntimeError(f"the profiler({self}) is alredy monitoring the categorie: {categorie}")
            else: # don't regiter it, will not add any mesure to self
                return SimpleProfiler(categorie)

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
                startTime = perf_counter()
                try: return func(*args, **kwargs)
                finally: self.addManualMesure(categorie, perf_counter() - startTime)
            return wrappedFunc
        return wrapper

    def reset(self, categorie:"_Categorie|None"=None)->None:
        """reset a specific `categorie` or all if None is given"""
        if categorie is None:
            for categorie in self._categories: self.reset(categorie)
            return None
        self._mesures[categorie].clear()
        if categorie in self.__emaMesure:
            del self.__emaMesure[categorie]
        self.__totalMesure[categorie] = 0.


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

    def __exit__(self, *_)->None:
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

    def wrap(self, func:Callable[_P, _T])->Callable[_P, _T]:
        def wrappedFunc(*args:_P.args, **kwargs:_P.kwargs)->_T:
            nonlocal func, self
            with self:
                return func(*args, **kwargs)
        return wrappedFunc

    def time(self)->float:
        if (self.startTime is None) or (self.StopTime is None):
            raise RuntimeError
        return self.StopTime - self.startTime


class DummyProfiler:
    def __init__(self, *_, **__) -> None: ...
    # for Profiler
    def wrapper(self, *_, **__)->Callable[[Callable[_P, _T]], Callable[_P, _T]]: return self.wrap
    def clean(self)->None: ...
    def addManualMesure(self, *_, **__)->None: ...
    def allMesure(self, *_, **__)->list[float]: return []
    def lastMesure(self, *_, **__)->float: return -1.0
    def avgMesure(self, *_, **__)->float: return -1.0
    def emaMesure(self, *_, **__)->float: return -1.0
    def totalMesure(self, *_, **__)->float: return -1.0
    def allTimes(self, *_, **__)->"dict[Any, list[float]]": return {}
    def lastTimes(self, *_, **__)->"dict[Any, float]": return {}
    def avgTimes(self, *_, **__)->"dict[Any, float]": return {}
    def emaTimes(self, *_, **__)->"dict[Any, float]": return {}
    def totalTimes(self, *_, **__)->"dict[Any, float]": return {}
    def str_allTimes(self, *_, **__)->dict[Any, list[str]]: return {}
    def str_lastTimes(self, *_, **__)->dict[Any, str]: return {}
    def str_avgTimes(self, *_, **__)->dict[Any, str]: return {}
    def str_emaTimes(self, *_, **__)->dict[Any, str]: return {}
    def str_totalTimes(self, *_, **__)->dict[Any, str]: return {}
    def hasMesure(self, *_, **__)->bool: return False
    def hasEmaMesure(self, *_, **__)->bool: return False
    def mesure(self, *_, **__)->"DummyProfiler": return self
    def reset(self, *_, **__)->None: ...
    # for SimpleProfiler (acte as a dummy context too)
    def __enter__(self)->"DummyProfiler": return self
    def __exit__(self, *_)->None: ...
    def perttyStr(self, *_, **__)->str: return ""
    def wrap(self, func:Callable[_P, _T])->Callable[_P, _T]: return func
    def time(self, *_, **__)->float: return -1.0
