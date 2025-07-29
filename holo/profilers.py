from collections import deque
from time import perf_counter
from datetime import datetime, timedelta

from .__typing import (
    Iterable, Callable, Any, Iterable,
    Generic, TypeVar, ContextManager,
    LiteralString, Self, TypeGuard, Literal,
)
from .prettyFormats import prettyTime
from .protocols import _T, _P




_T_Categorie = TypeVar("_T_Categorie", bound=LiteralString)

class Profiler(Generic[_T_Categorie]):
    """mesure the times taken to do things, and get analytics with it"""

    def __init__(self,
            categories:"list[_T_Categorie]", nbMesurements:"int|None"=None,
            emaFactor:"None|int"=None, ignoreSimultaneousMesures:bool=False) -> None:
        """`categories`:list[str] is the names of tracked mesures\n
        `nbMesurements`int is the max nb of mesures to keep\n
        `ignoreSimultaneousMesures`:bool is whether an error will be raised when \
            multiples mesures of the same categorie are done, \
            or whether only the fist will be kept, other are ignored\n"""
        self._categories:"list[_T_Categorie]" = categories
        assert (nbMesurements != 0), ValueError
        self.__nbMesurements:"int|None" = nbMesurements
        self._mesures:"dict[_T_Categorie, deque[float]]" = {name: deque() for name in categories}
        """mesures ordering: 0-> most recent, last-> oldest"""
        self.__currentMesurers:"dict[_T_Categorie, SimpleProfiler]" = {}
        """hold the SimpleProfiler instances to mesure each categories"""
        self._emaMesure:"dict[_T_Categorie, float]" = {}
        self.__emaFactor:float
        if emaFactor is None:
            self.__emaFactor = (1 / (10_000 if self.nbMesurements is None else self.nbMesurements))
        else: self.__emaFactor = (1 / emaFactor)
        self._totalMesure:"dict[_T_Categorie, float]" = {categorie: 0. for categorie in self._categories}
        self.ignoreSimultaneousMesures:bool = ignoreSimultaneousMesures

    @property
    def categories(self)->"list[_T_Categorie]":
        return self._categories
    @property
    def nbMesurements(self)->"int|None":
        return self.__nbMesurements
    @nbMesurements.setter
    def nbMesurements(self, value:int)->None:
        if value == 0: raise ValueError("nbMesurements can't be set to 0")
        self.__nbMesurements = value
        self.__emaFactor = (1 / self.__nbMesurements)
        self._popExcidingMesures(None)
    @property
    def emaFactor(self)->int:
        return int(1 / self.__emaFactor)
    
    def clean(self)->None:
        """remove all mesures"""
        self.__init__(self.categories, self.__nbMesurements)

    def __updateEma(self, categorie:"_T_Categorie", newMesuredTime:float)->None:
        """compute and update the ema of the mesures for this categorie"""
        # newEma = oldEma * (1 - alpha) + newTime * alpha
        self._emaMesure[categorie] = (
            self._emaMesure.get(categorie, newMesuredTime) * (1 - self.__emaFactor)
            + newMesuredTime * self.__emaFactor
        )

    def __updateTotal(self, categorie:"_T_Categorie", newMesuredTime:float)->None:
        """compute and update the total of the mesures for this categorie"""
        self._totalMesure[categorie] += newMesuredTime

    def addManualMesure(self, categorie:"_T_Categorie", mesuredTime:"float|SimpleProfiler")->None:
        if categorie not in self._mesures:
            raise KeyError(f"the mesure categorie: {categorie} don't exist")
        if isinstance(mesuredTime, SimpleProfiler):
            mesuredTime = mesuredTime.time()
        self._mesures[categorie].appendleft(mesuredTime)
        self._popExcidingMesures(categorie)
        self.__updateEma(categorie, mesuredTime)
        self.__updateTotal(categorie, mesuredTime)

    def _popExcidingMesures(self, categorie:"_T_Categorie|None")->int:
        """pop the values when the number of mesures is over the hist size\n
        `categorie`:str|None, str -> pop for this categorie, None -> all categories\n
        return how much mesures where poped"""
        if self.__nbMesurements is None: return 0
        categories:"Iterable[_T_Categorie]" = (self._mesures.keys() if categorie is None else [categorie])
        nbPoped:int = 0
        for categorie in categories:
            categorieMesures:"deque[float]" = self._mesures[categorie]
            while len(categorieMesures) > self.__nbMesurements:
                categorieMesures.pop()
                nbPoped += 1
        return nbPoped

    def allMesure(self, categorie:"_T_Categorie")->"list[float]":
        if self.hasMesure(categorie) is True:
            return list(reversed(self._mesures[categorie])) # reversed => first to last mesure
        raise KeyError(f"no mesures for the categorie: {categorie}")
    def lastMesure(self, categorie:"_T_Categorie")->float:
        if self.hasMesure(categorie) is True:
            return self._mesures[categorie][0]
        raise KeyError(f"no mesures for the categorie: {categorie}")
    def avgMesure(self, categorie:"_T_Categorie")->float:
        if self.hasMesure(categorie) is True:
            return sum(self._mesures[categorie]) / len(self._mesures[categorie])
        raise KeyError(f"no mesures for the categorie: {categorie}")
    def emaMesure(self, categorie:"_T_Categorie")->float:
        if self.hasMesure(categorie) is True:
            return self._emaMesure[categorie]
        raise KeyError(f"no ema mesures for the categorie: {categorie}")
    def totalMesure(self, categorie:"_T_Categorie")->float:
        if self.hasMesure(categorie) is True:
            return self._totalMesure[categorie]
        raise KeyError(f"no total mesures for the categorie: {categorie}")

    def allTimes(self, categories:"list[_T_Categorie]|None"=None)->"dict[_T_Categorie, list[float]]":
        return {categorie: self.allMesure(categorie)
                for categorie in self.__getCategories(categories) if self.hasMesure(categorie)}
    def lastTimes(self, categories:"list[_T_Categorie]|None"=None)->"dict[_T_Categorie, float]":
        return {categorie: self.lastMesure(categorie)
                for categorie in self.__getCategories(categories) if self.hasMesure(categorie)}
    def avgTimes(self, categories:"list[_T_Categorie]|None"=None)->"dict[_T_Categorie, float]":
        return {categorie: self.avgMesure(categorie)
                for categorie in self.__getCategories(categories) if self.hasMesure(categorie)}
    def emaTimes(self, categories:"list[_T_Categorie]|None"=None)->"dict[_T_Categorie, float]":
        return {categorie: self.emaMesure(categorie)
                for categorie in self.__getCategories(categories) if self.hasEmaMesure(categorie)}
    def totalTimes(self, categories:"list[_T_Categorie]|None"=None)->"dict[_T_Categorie, float]":
        return {categorie: self.totalMesure(categorie)
                for categorie in self.__getCategories(categories) if self.hasMesure(categorie)}
    
    def str_allTimes(self,
            formatTimes:"Callable[[float], str]|None"=None,
            categories:"list[_T_Categorie]|None"=None)->"dict[_T_Categorie, list[str]]":
        if formatTimes is None: formatTimes = str
        return {categorie: [formatTimes(timeVal) for timeVal in  self.allMesure(categorie)]
                for categorie in self.__getCategories(categories) if self.hasMesure(categorie)}
    def str_lastTimes(self,
            formatTimes:"Callable[[float], str]|None"=None,
            categories:"list[_T_Categorie]|None"=None)->"dict[_T_Categorie, str]":
        if formatTimes is None: formatTimes = str
        return {categorie: formatTimes(self.lastMesure(categorie))
                for categorie in self.__getCategories(categories) if self.hasMesure(categorie)}
    def str_avgTimes(self,
            formatTimes:"Callable[[float], str]|None"=None,
            categories:"list[_T_Categorie]|None"=None)->"dict[_T_Categorie, str]":
        if formatTimes is None: formatTimes = str
        return {categorie: formatTimes(self.avgMesure(categorie))
                for categorie in self.__getCategories(categories) if self.hasMesure(categorie)}
    def str_emaTimes(self,
            formatTimes:"Callable[[float], str]|None"=None,
            categories:"list[_T_Categorie]|None"=None)->"dict[_T_Categorie, str]":
        if formatTimes is None: formatTimes = str
        return {categorie: formatTimes(self.emaMesure(categorie))
                for categorie in self.__getCategories(categories) if self.hasMesure(categorie)}
    def str_totalTimes(self,
            formatTimes:"Callable[[float], str]|None"=None,
            categories:"list[_T_Categorie]|None"=None)->"dict[_T_Categorie, str]":
        if formatTimes is None: formatTimes = str
        return {categorie: formatTimes(self.totalMesure(categorie))
                for categorie in self.__getCategories(categories) if self.hasMesure(categorie)}

    def __getCategories(self, categories:"list[_T_Categorie]|None")->"Iterable[_T_Categorie]":
        return (self.categories if categories is None else categories)

    def mesure(self, categorie:"_T_Categorie")->"SimpleProfiler":
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

    def _setMesure(self, categorie:"_T_Categorie", mesuredTime:float)->None:
        """internal function for mesure(...) to add the mesure"""
        self.addManualMesure(categorie, mesuredTime)
        self.__currentMesurers.pop(categorie)

    def hasMesure(self, categorie:"_T_Categorie")->bool:
        return (len(self._mesures[categorie]) != 0)
    def hasEmaMesure(self, categorie:"_T_Categorie")->bool:
        return categorie in self._emaMesure

    def wrapper(self, categorie:"_T_Categorie")->Callable[[Callable[_P, _T]], Callable[_P, _T]]:
        def wrapper(func:Callable[_P, _T])->Callable[_P, _T]:
            def wrappedFunc(*args:_P.args, **kwargs:_P.kwargs)->_T:
                startTime = perf_counter()
                try: return func(*args, **kwargs)
                finally: self.addManualMesure(categorie, perf_counter() - startTime)
            return wrappedFunc
        return wrapper

    def reset(self, categorie:"_T_Categorie|None"=None)->None:
        """reset a specific `categorie` or all if None is given"""
        if categorie is None:
            for categorie in self._categories: self.reset(categorie)
            return None
        self._mesures[categorie].clear()
        if categorie in self._emaMesure:
            del self._emaMesure[categorie]
        self._totalMesure[categorie] = 0.
    
    def copy(self, copyMesures:bool=False)->"Profiler[_T_Categorie]":
        """copy the Profiler, can't copy when self is mesuring\n
        if `copyMesures` is False, don't copy the mesures, only the config"""
        if len(self.__currentMesurers) != 0:
            raise RuntimeError(f"can't copy while mesuring (messurers that are still active: {self.__currentMesurers.keys()})")
        newProfiler:"Profiler[_T_Categorie]" = \
            Profiler(
                categories=self.categories, 
                nbMesurements=self.nbMesurements,
                emaFactor=self.emaFactor,
                ignoreSimultaneousMesures= \
                    self.ignoreSimultaneousMesures,
            )
        if copyMesures is False:
            # => done
            return newProfiler
        # => copy the messures
        for (categorie, mesures) in self._mesures.items():
            newProfiler._mesures[categorie] = \
                mesures.copy()
        # => copy the ema mesures
        for (categorie, emaMesure) in self._emaMesure.items():
            newProfiler._emaMesure[categorie] = emaMesure
        # => copy the total mesures
        for (categorie, totalMesure) in self._totalMesure.items():
            newProfiler._totalMesure[categorie] = totalMesure
        return newProfiler
        
    def isCategorie(self, categorie:str)->"TypeGuard[_T_Categorie]":
        return categorie in self._mesures.keys()

class SimpleProfiler(ContextManager, Generic[_T_Categorie]):
    """a simple profiler that hold a single mesure"""

    def __init__(self, name:"_T_Categorie|None"=None, setMesureFunc:"Callable[[_T_Categorie, float], Any]|None"=None)->None:
        self.name: "_T_Categorie|None" = name
        self.__setMesureFunc:"Callable[[_T_Categorie, float], Any]|None" = setMesureFunc
        self.startTime:"float|None" = None
        self.StopTime:"float|None" = None

    def __enter__(self)->"Self":
        self.StopTime = None
        self.startTime = perf_counter()
        return self

    def __exit__(self, *_)->None:
        self.StopTime = perf_counter()
        if self.startTime is None:
            raise RuntimeError("__exit__ called before __enter__ (encountered self.startTime = None)")
        if (self.__setMesureFunc is not None) and (self.name is not None): # => set the mesure
            self.__setMesureFunc(self.name, self.StopTime - self.startTime)

    def perttyStr(self, prettyTimeFunc:"Callable[[float], str]|None"=None)->str:
        if (self.startTime is None) or (self.StopTime is None):
            return f"SimpleProfiler({self.name}, noTime)"
        if prettyTimeFunc is None: 
            prettyTimeFunc = prettyTime
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
    def allMesure(self, *_, **__)->"list[float]": return []
    def lastMesure(self, *_, **__)->float: return -1.0
    def avgMesure(self, *_, **__)->float: return -1.0
    def emaMesure(self, *_, **__)->float: return -1.0
    def totalMesure(self, *_, **__)->float: return -1.0
    def allTimes(self, *_, **__)->"dict[Any, list[float]]": return {}
    def lastTimes(self, *_, **__)->"dict[Any, float]": return {}
    def avgTimes(self, *_, **__)->"dict[Any, float]": return {}
    def emaTimes(self, *_, **__)->"dict[Any, float]": return {}
    def totalTimes(self, *_, **__)->"dict[Any, float]": return {}
    def str_allTimes(self, *_, **__)->"dict[Any, list[str]]": return {}
    def str_lastTimes(self, *_, **__)->"dict[Any, str]": return {}
    def str_avgTimes(self, *_, **__)->"dict[Any, str]": return {}
    def str_emaTimes(self, *_, **__)->"dict[Any, str]": return {}
    def str_totalTimes(self, *_, **__)->"dict[Any, str]": return {}
    def hasMesure(self, *_, **__)->bool: return False
    def hasEmaMesure(self, *_, **__)->bool: return False
    def mesure(self, *_, **__)->"DummyProfiler": return self
    def reset(self, *_, **__)->None: ...
    def copy(self, *_, **__)->"DummyProfiler": return DummyProfiler()
    def isCategorie(self, *_, **__:str)->"Literal[True]": return True
    # for SimpleProfiler (acte as a dummy context too)
    def __enter__(self)->"Self": return self
    def __exit__(self, *_)->None: ...
    def perttyStr(self, *_, **__)->str: return ""
    def wrap(self, func:Callable[_P, _T])->Callable[_P, _T]: return func
    def time(self, *_, **__)->float: return -1.0





class StopWatch():
    """a stopwatch class to mesure easily the execution of tasks that can be paused"""
    __slots__ = (
        "__totalMesureTime", "__pausedTime", "__isMesuring", "__nbMesuresStarted",
        "__startTime", "__stopTime", "__currentMesureStartTime", "__lastMesureStopTime", )
    
    def __init__(self) -> None:
        self.__totalMesureTime: float = 0.0
        """total time of the mesures"""
        self.__pausedTime: float = 0.0
        """total time of the pauses"""
        self.__isMesuring: bool = False
        """the state it is currently mesuring\n
        when the clock is started: 
        - True -> (__currentMesureStartTime is not None)
        - False -> (__lastMesureStopTime is not None)"""
        self.__startTime: "float|None" = None
        """the perfconter time when it started | None -> not setted"""
        self.__stopTime: "float|None" = None
        """the perfconter time when it stoped | None -> not setted"""
        self.__currentMesureStartTime: "float|None" = None
        """the perfconter time when it started the current mesure | None -> not setted"""
        self.__lastMesureStopTime: "float|None" = None
        """the perfconter time when it stoped the last mesure | None -> not setted"""
        self.__nbMesuresStarted: int = 0
        """the number of mesures started"""
    
    def reset(self)->None:
        self.__init__()
    
    
    @property
    def isMesuring(self)->bool:
        return self.__isMesuring
    
    @property
    def nbMesuresStarted(self)->int:
        return self.__nbMesuresStarted
    
    @property
    def nbMesuresFinished(self)->int:
        return self.__nbMesuresStarted - (self.__isMesuring)
    
    @property
    def started(self)->bool:
        return (self.__startTime is not None)
    
    @property
    def stoped(self)->bool:
        """return if the clock was started then stoped"""
        return (self.started) and (self.__stopTime is not None)
    
    @property
    def totalTime(self)->float:
        """the total time since it started mesuring to the stoping (or now if not stoped)"""
        if self.__startTime is None:
            raise RuntimeError(f"you need to start the clock first")
        # => has started
        if self.__stopTime is not None:
            # => has stoped
            return (self.__stopTime - self.__startTime)
        # => started but not stoped 
        return (perf_counter() - self.__startTime)
    
    @property
    def mesuredTime(self)->float:
        """the total mesured time until it stated"""
        if self.__isMesuring is False:
            return self.__totalMesureTime
        # => isMesuring is True
        assert self.__currentMesureStartTime is not None
        # add the time of the current mesure
        return self.__totalMesureTime + (perf_counter() - self.__currentMesureStartTime)
    
    @property
    def pausedTime(self)->float:
        """the total mesured time until it stated"""
        if (self.__isMesuring is True) or (self.started is False) or (self.stoped is True):
            return self.__pausedTime
        # => (isMesuring is False) and (has started) and (has not stoped)
        assert self.__lastMesureStopTime is not None
        # add the since the end of the last mesure
        return self.__pausedTime + (perf_counter() - self.__lastMesureStopTime)
    
    
    def start(self, *, paused:bool=False, _time:"float|None"=None)->None:
        """start the clock (can only be called once before stoping the clock)\n
        `_time` to force a given start time"""
        if self.__startTime is not None:
            # => started
            raise RuntimeError(f"called start() but it was alredy started")
        # => start clocking
        self.__stopTime = None
        t: float = (_time or perf_counter())
        self.__startTime = t
        if paused is False:
            self.__isMesuring = True
            self.__currentMesureStartTime = t
            self.__nbMesuresStarted += 1
        else: # => start paused
            self.__lastMesureStopTime = t
        
    def play(self, *, _time:"float|None"=None)->bool:
        """put the clock in mesuring state (return True if it wasn't mesuring before)\n
        `_time` to force a given play time"""
        if (self.__isMesuring is False) and (self.__startTime is not None):
            # => (has alredy started) and (was paused) -> start mesuring
            assert (self.__lastMesureStopTime is not None)
            self.__isMesuring = True
            self.__nbMesuresStarted += 1
            t: float = (_time or perf_counter())
            self.__currentMesureStartTime = t
            self.__pausedTime += (t - self.__lastMesureStopTime)
            self.__lastMesureStopTime = None
            return True
        # => (__isMesuring is True) or (self.__startTime is None)
        elif self.__isMesuring is True:
            # => alredy mesuring
            return False 
        elif self.__startTime is None:
            # => not started
            self.start(_time=_time)
            return True
        else: raise RuntimeError(f"this situation is the first if")
    
    def pause(self, *, _time:"float|None"=None)->bool:
        """put the clock in pause state (return True if it wasn't paused before)\n
        `_time` to force a given pause time"""
        t: float = (_time or perf_counter())
        if self.__isMesuring is True:
            # => (has alredy started) and (was mesuring) -> pause the mesure
            assert (self.__currentMesureStartTime is not None)
            self.__lastMesureStopTime = t
            self.__isMesuring = False
            self.__totalMesureTime += (t - self.__currentMesureStartTime)
            self.__currentMesureStartTime = None
            return True
        # => not mesuring
        if self.__startTime is None:
            raise RuntimeError(f"can't pause a clock that wasn't started")
        # => alredy paused
        return False
        
    def tooglePause(self, *, _time:"float|None"=None)->bool:
        """toogle the play/pause state (return the new isMesuring state)\n
        `_time` to force a given play/pause time"""
        if self.__isMesuring is True:
            # => playing
            self.pause(_time=(_time or perf_counter()))
        else: # => paused
            self.play(_time=_time)
        return self.__isMesuring
        
    def stop(self, *, _time:"float|None"=None)->None:
        """stop the clock (can only be called once after starting the clock)\n
        `_time` to force a given stop time"""
        t: float = (_time or perf_counter())
        if self.__startTime is None:
            raise RuntimeError(f"the clock needs to be started first")
        if self.__stopTime is not None:
            raise RuntimeError(f"the clock was alredy stoped")
        # => (has started) and (not stoped)
        if self.__isMesuring is True:
            assert (self.__currentMesureStartTime is not None) \
                and (self.__lastMesureStopTime is None)
            self.__isMesuring = False
            self.__totalMesureTime += (t - self.__currentMesureStartTime)
            self.__currentMesureStartTime = None
        else: # => (isMesuring is False) => (was paused)
            assert (self.__lastMesureStopTime is not None) \
                and (self.__currentMesureStartTime is None)
            self.__pausedTime += (t - self.__lastMesureStopTime)
            self.__lastMesureStopTime = None
        # => (__lastMesureStopTime is None) and (__currentMesureStartTime is None)
        # => (__isMesuring is False) and (__startTime is not None)
        self.__stopTime = t



__referencePerfCounter: float = perf_counter()
__referenceDatetime: datetime = datetime.now()

def convert_datetime_to_perfCounter(t:datetime)->float:
    return __referencePerfCounter + (t - __referenceDatetime).total_seconds()

def convert_perfCounter_to_datetime(t:float)->datetime:
    return __referenceDatetime + timedelta(seconds=(t - __referencePerfCounter))

class RemainingTime_mean():
    """util class to Estimate the time remaining for a task\\
    use the mean time to estimate"""
    
    def __init__(self, finalAmount:"int|float", *, start:bool)->None:
        self.finalAmount: float = finalAmount
        self.currentAmount: float = 0
        self.startTime: "datetime|None" = None
        self.endTime: "datetime|None" = None
        if start is True:
            self.start()
    
    @property
    def progress(self)->float:
        """the current progress (from 0. to 1., truncated)"""
        return max(0., min(1., self.currentAmount / self.finalAmount))
    
    
    ### total time
    def estimatedTotalTimeDelta(self, noProgress:"_T"=None)->"timedelta|_T":
        """return the estimated total time of the task, in seconds, based on `self.progress`"""
        assert self.startTime is not None, f"it wasn't started"
        sinceStart = (datetime.now() - self.startTime)
        progress = self.progress
        if progress == 0.0:
            return noProgress # couldn't estimate
        # totalTime = sinceStart / self.progress 
        return sinceStart * (1 / self.progress)
    
    def estimatedTotalTime(self, noProgress:"_T"=None)->"float|_T":
        """return the estimated total time of the task, in seconds, based on `self.progress`"""
        totTime = self.estimatedTotalTimeDelta(noProgress=None)
        return (noProgress if totTime is None else totTime.total_seconds())
    
    def estimatedPrettyTotalTime(self, noProgress:"_T"=None)->"str|_T":
        """return the estimated total time of the task, prettyPrinted, based on `self.progress`"""
        estValue = self.estimatedTotalTime(noProgress=None)
        return (noProgress if estValue is None else prettyTime(estValue))
    
    
    ### remaining time
    def remainingTimeDelta(self, noProgress:"_T"=None)->"timedelta|_T":
        """return the remaining time, in seconds, based on `self.progress`"""
        assert self.startTime is not None, f"it wasn't started"
        sinceStart = (datetime.now() - self.startTime)
        progress = self.progress
        if progress == 0.0:
            return noProgress # couldn't estimate
        # totalTime = sinceStart / self.progress 
        # remainingTime = totalTime - sinceStart
        return sinceStart * (1 / self.progress - 1)
    
    def remainingTime(self, noProgress:"_T"=None)->"float|_T":
        """return the remaining time, in seconds, based on `self.progress`"""
        remTime = self.remainingTimeDelta(noProgress=None)
        return (noProgress if remTime is None else remTime.total_seconds())
    
    def remainingPrettyTime(self, noProgress:"_T"=None)->"str|_T":
        """return the remaining time, prettyPrinted, based on `self.progress`"""
        remTime = self.remainingTime(noProgress=None)
        return (noProgress if remTime is None else prettyTime(remTime))
    
    
    ### finish time
    def estimatedFinishDatetime(self, noProgress:"_T"=None)->"datetime|_T":
        """return the estimated datetime when it is expected to finish, based on `self.progress`"""
        assert self.startTime is not None, f"it wasn't started"
        remTime = self.remainingTimeDelta(noProgress=None)
        if remTime is None: 
            return noProgress
        return self.startTime + remTime
    
    def estimatedFinishTime(self, noProgress:"_T"=None)->"float|_T":
        """return the estimated posix timestamp when it is expected to finish, in seconds, based on `self.progress`"""
        finish = self.estimatedFinishDatetime(noProgress=None)
        return (noProgress if finish is None else finish.timestamp())
    
    def estimatedPrettyFinishTime(self, noProgress:"_T"=None)->"str|_T":
        """return the remaining time, prettyPrinted, based on `self.progress`"""
        finish = self.estimatedFinishDatetime(noProgress=None)
        return (noProgress if finish is None else finish.ctime())
    
    
    ### actions
    def restart(self, *, start:bool)->None:
        """reset everything to empty (amount, startTime, etc)"""
        self.__init__(finalAmount=self.finalAmount, start=start)
        
    def start(self)->None:
        """this will start counting the time from now"""
        assert self.startTime is None, f"it was alredy started, you can restart it if needed"
        self.startTime = datetime.now()
    
    def end(self)->None:
        """this will end to now (this keep the currentAmount unchanged)"""
        assert self.startTime is not None, f"it wasn't started"
        assert self.endTime is None, f"it was alredy stoped, you can restart it if needed"
        self.endTime = datetime.now()
    
    def isFinished(self)->bool:
        """return whether it was stoped"""
        return (self.endTime is not None)
    
    
    def __stopIfNeeded(self)->None:
        assert self.startTime is not None, f"it wasn't started"
        assert self.endTime is None, f"it was alredy stoped, you can restart it if needed"
        if self.currentAmount >= self.finalAmount:
            self.end()
        
    def addAmount(self, toAdd:"float|int")->bool:
        """add the amount to the current amount, return whether it finished"""
        self.currentAmount += toAdd
        self.__stopIfNeeded()
        return self.isFinished()
    
    def setAmount(self, newAmount:"float|int")->bool:
        """set the current amount to the value, return whether it finished"""
        self.currentAmount = newAmount
        self.__stopIfNeeded()
        return self.isFinished()
    
    