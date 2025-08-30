from collections import deque
from time import perf_counter
from datetime import datetime, timedelta

from .__typing import (
    Iterable, Callable, Any, Iterable, OrderedDict,
    Generic, TypeVar, ContextManager,
    LiteralString, Self, TypeGuard, Literal,
    override, assertIsinstance, Union,
)
from .prettyFormats import prettyTime
from .protocols import _T, _P


class _ProfilerCategory():
    """hold the mesures of a categorie"""
    __slots__ = ("prof", "mesures", "emaMesure", "totalNb", 
                 "totalTime", "currentMesurer", )
    
    def __init__(self, prof:"Profiler") -> None:
        self.prof: Profiler = prof
        """the profiler that store the categorie"""
        self.mesures: "deque[float]" = deque()
        """all the mesures stored (in sec), FIFO order"""
        self.emaMesure: "float|None" = None
        """the current ema of mesures (in sec)"""
        self.totalNb: int = 0
        """total nb of mesures"""
        self.totalTime: float = 0.0
        """the sum of all mesures (in sec)"""
        self.currentMesurer: "SimpleProfiler|None" = None
        """the current SimpleProfiler that is used to mesure this category"""
    
    def copy(self)->"_ProfilerCategory":
        assert self.currentMesurer is None
        new = _ProfilerCategory(self.prof)
        new.mesures = self.mesures.copy()
        new.emaMesure = self.emaMesure
        new.totalNb = self.totalNb
        new.totalTime = self.totalTime
        return new
    
    def avgMesure(self)->"float":
        """the global average mesure"""
        return (0.0 if (self.totalNb == 0) else (self.totalTime / self.totalNb))
    
    def _update(self, newMesure:float)->None:
        # add mesure
        self.mesures.append(newMesure)
        # pop exciding
        self._popExcidingMesures()
        # update total
        self.totalNb += 1
        self.totalTime += newMesure
        # update ema
        emaCoef: float = self.prof.emaCoef
        if self.emaMesure is not None:
            self.emaMesure = (self.emaMesure * (1-emaCoef) + newMesure * emaCoef)
        else: self.emaMesure = newMesure
    
    def _popExcidingMesures(self)->int:
        """pop the values when the number of mesures is over the hist size\n
        `categorie`:str|None, str -> pop for this categorie, None -> all categories\n
        return how much mesures where poped"""
        histSize = self.prof.historyMaxSize
        if histSize is None: 
            return 0
        nbPoped:int = 0
        mesures = self.mesures
        while len(mesures) > histSize:
            mesures.popleft()
            nbPoped += 1
        return nbPoped
        
    

_T_Category = TypeVar("_T_Category", bound=LiteralString)
_T_Category2 = TypeVar("_T_Category2", bound=LiteralString)

class Profiler(Generic[_T_Category]):
    """mesure the times taken to do things, and get analytics with it"""
    __slots__ = ("_mesures", "__historyMaxSize", "emaCoef", "ignoreSimultaneousMesures", )

    def __init__(self,
            categories:"list[_T_Category]", historyMaxSize:"int|None"=None,
            emaCoef:"float"=0.01, ignoreSimultaneousMesures:bool=False) -> None:
        """`categories`:list[str] is the names of tracked mesures\n
        `historyMaxSize` is the max nb of mesures to keep | None => keep all\n
        `ignoreSimultaneousMesures`:bool is whether an error will be raised when \
            multiples mesures of the same categorie are done, \
            or whether only the fist will be kept, other are ignored\n
        `emaCoef` is the coef used to compute the ema of the mesures per categories"""
        # check the values are correct
        assert (historyMaxSize is None) or (historyMaxSize > 0)
        assert (0.0 < emaCoef <= 1.0)
        self._mesures: "OrderedDict[_T_Category, _ProfilerCategory]" = OrderedDict(
            [(name, _ProfilerCategory(self)) for name in categories])
        self.historyMaxSize = historyMaxSize
        """the max nb of last mesures to keep per categorie | None => keep all"""
        self.emaCoef: float = emaCoef
        self.ignoreSimultaneousMesures: bool = ignoreSimultaneousMesures

    def extendCategories(
            self, newCategories:"list[_T_Category2]",
            *, inplace:bool)->"Profiler[Union[_T_Category, _T_Category2]]":
        newProf: "Profiler[Union[_T_Category, _T_Category2]]" = \
            (self if inplace is True else self.copy(copyMesures=True)) # type: ignore
        for catName in newCategories:
            assert catName not in newProf._mesures.keys()
            newProf._mesures[catName] = _ProfilerCategory(newProf)
        return newProf
    
    @property
    def categories(self)->"list[_T_Category]":
        return list(self._mesures.keys())
    @property
    def historyMaxSize(self)->"int|None":
        return self.__historyMaxSize
    @historyMaxSize.setter
    def historyMaxSize(self, value:"int|None")->None:
        if value == 0: raise ValueError("nbMesurements can't be set to 0")
        self.__historyMaxSize = value
        self._popExcidingMesures(None)
    
    def _popExcidingMesures(self, categories:"list[_T_Category]|None")->int:
        return sum(self._mesures[cat]._popExcidingMesures() 
                   for cat in self.__getCategories(categories))

    def addManualMesure(self, categorie:"_T_Category", mesuredTime:"float|SimpleProfiler")->None:
        if categorie not in self._mesures:
            raise KeyError(f"the mesure categorie: {categorie} don't exist")
        if isinstance(mesuredTime, SimpleProfiler):
            mesuredTime = mesuredTime.time()
        self._mesures[categorie]._update(mesuredTime)

    ## per category methodes

    def allMesure(self, category:"_T_Category")->"list[float]":
        """the list of all mesures in that category (first value is the oldest)"""
        assert self.hasMesureStored(category), f"no mesures for the categorie: {category}"
        return list(self._mesures[category].mesures)
    def lastMesure(self, category:"_T_Category")->float:
        """the last mesure of that category"""
        assert self.hasMesureStored(category), f"no mesures for the categorie: {category}"
        return self._mesures[category].mesures[-1]
    def avgMesure(self, category:"_T_Category")->float:
        """the average mesure of that category (global)"""
        assert self.hasMesured(category), f"no mesures for the categorie: {category}"
        return self._mesures[category].avgMesure()
    def emaMesure(self, category:"_T_Category")->float:
        assert self.hasMesured(category), f"no mesures for the categorie: {category}"
        emaMesure = self._mesures[category].emaMesure
        return (0.0 if emaMesure is None else emaMesure)
    def totalMesure(self, category:"_T_Category")->float:
        assert self.hasMesured(category), f"no mesures for the categorie: {category}"
        return self._mesures[category].totalTime

    def allTimes(self, categories:"list[_T_Category]|None"=None)->"dict[_T_Category, list[float]]":
        return {categorie: self.allMesure(categorie)
                for categorie in self.__getCategories(categories) if self.hasMesureStored(categorie)}
    def lastTimes(self, categories:"list[_T_Category]|None"=None)->"dict[_T_Category, float]":
        return {categorie: self.lastMesure(categorie)
                for categorie in self.__getCategories(categories) if self.hasMesureStored(categorie)}
    def avgTimes(self, categories:"list[_T_Category]|None"=None)->"dict[_T_Category, float]":
        return {categorie: self.avgMesure(categorie)
                for categorie in self.__getCategories(categories) if self.hasMesured(categorie)}
    def emaTimes(self, categories:"list[_T_Category]|None"=None)->"dict[_T_Category, float]":
        return {categorie: self.emaMesure(categorie)
                for categorie in self.__getCategories(categories) if self.hasMesured(categorie)}
    def totalTimes(self, categories:"list[_T_Category]|None"=None)->"dict[_T_Category, float]":
        return {categorie: self.totalMesure(categorie)
                for categorie in self.__getCategories(categories) if self.hasMesured(categorie)}
    
    def pretty_allTimes(self,
            formatTimes:"Callable[[float], str]|None"=None,
            categories:"list[_T_Category]|None"=None)->"dict[_T_Category, list[str]]":
        if formatTimes is None: formatTimes = prettyTime
        return {name: [formatTimes(timeVal) for timeVal in mesures] 
                for name, mesures in self.allTimes(categories).items()}
    def pretty_lastTimes(self,
            formatTimes:"Callable[[float], str]|None"=None,
            categories:"list[_T_Category]|None"=None)->"dict[_T_Category, str]":
        if formatTimes is None: formatTimes = prettyTime
        return {name: formatTimes(timeVal) for name, timeVal in self.lastTimes(categories).items()}
    def pretty_avgTimes(self,
            formatTimes:"Callable[[float], str]|None"=None,
            categories:"list[_T_Category]|None"=None)->"dict[_T_Category, str]":
        if formatTimes is None: formatTimes = prettyTime
        return {name: formatTimes(timeVal) for name, timeVal in self.avgTimes(categories).items()}
    def pretty_emaTimes(self,
            formatTimes:"Callable[[float], str]|None"=None,
            categories:"list[_T_Category]|None"=None)->"dict[_T_Category, str]":
        if formatTimes is None: formatTimes = prettyTime
        return {name: formatTimes(timeVal) for name, timeVal in self.emaTimes(categories).items()}
    def pretty_totalTimes(self,
            formatTimes:"Callable[[float], str]|None"=None,
            categories:"list[_T_Category]|None"=None)->"dict[_T_Category, str]":
        if formatTimes is None: formatTimes = prettyTime
        return {name: formatTimes(timeVal) for name, timeVal in self.totalTimes(categories).items()}
    
    def __getCategories(self, categories:"list[_T_Category]|None")->"list[_T_Category]":
        return (self.categories if categories is None else categories)

    def mesure(self, categorie:"_T_Category")->"SimpleProfiler":
        """to be used in:\n
        ```
        with profiler.mesure("categorie"):
            ... # code to mesure
        ```"""
        if self._mesures[categorie].currentMesurer is not None:
            if self.ignoreSimultaneousMesures is False:
                raise RuntimeError(f"the profiler({self}) is alredy monitoring the categorie: {categorie}")
            else: # don't regiter it, will not add any mesure to self
                return SimpleProfiler(categorie)
        simpleProfiler:"SimpleProfiler" = SimpleProfiler(categorie, self._setMesure)
        self._mesures[categorie].currentMesurer = simpleProfiler
        return simpleProfiler

    def _setMesure(self, categorie:"_T_Category", mesuredTime:float)->None:
        """internal function for mesure(...) to add the mesure"""
        self.addManualMesure(categorie, mesuredTime)
        self._mesures[categorie].currentMesurer = None

    def hasMesureStored(self, categorie:"_T_Category")->bool:
        return (len(self._mesures[categorie].mesures) > 0)
    def hasMesured(self, categorie:"_T_Category")->bool:
        return (self._mesures[categorie].totalNb > 0)

    def wrapper(self, categorie:"_T_Category")->Callable[[Callable[_P, _T]], Callable[_P, _T]]:
        def wrapper(func:Callable[_P, _T])->Callable[_P, _T]:
            def wrappedFunc(*args:_P.args, **kwargs:_P.kwargs)->_T:
                startTime = perf_counter()
                try: return func(*args, **kwargs)
                finally: self.addManualMesure(categorie, perf_counter() - startTime)
            return wrappedFunc
        return wrapper

    def reset(self, categorie:"_T_Category|None"=None)->None:
        """reset a specific `categorie` or all if None is given"""
        if categorie is None:
            # => reset all
            for categorie in self.categories: 
                self.reset(categorie)
            return None
        # => single category
        self._mesures[categorie].__init__(self)
    
    def copy(self, copyMesures:bool=False)->"Profiler[_T_Category]":
        """copy the Profiler, can't copy when self is mesuring\n
        if `copyMesures` is False, don't copy the mesures, only the config"""
        # check there are no active mesureur
        activeMesureurs: "list[_T_Category]" = []
        for categorie, datas in self._mesures.items():
            if datas.currentMesurer is not None:
                activeMesureurs.append(categorie)
        if len(activeMesureurs) > 0:
            raise RuntimeError(f"can't copy while mesuring (mesurers that are still active: {activeMesureurs})")
        # => can copy
        newProfiler:"Profiler[_T_Category]" = Profiler(
            categories=self.categories, historyMaxSize=self.historyMaxSize,
            emaCoef=self.emaCoef, ignoreSimultaneousMesures=self.ignoreSimultaneousMesures)
        if copyMesures is False:
            return newProfiler # => done
        # => copy the mesures
        for (categorie, mesures) in self._mesures.items():
            newProfiler._mesures[categorie] = mesures.copy()
        return newProfiler
        
    def isCategorie(self, categorie:str)->"TypeGuard[_T_Category]":
        return categorie in self._mesures.keys()

class SimpleProfiler(ContextManager, Generic[_T_Category]):
    """a simple profiler that hold a single mesure"""
    __slots__ = ("name", "__setMesureFunc", "startTime", "StopTime")

    def __init__(self, name:"_T_Category"="", setMesureFunc:"Callable[[_T_Category, float], Any]|None"=None)->None:
        self.name: "_T_Category" = name
        self.__setMesureFunc: "Callable[[_T_Category, float], Any]|None" = setMesureFunc
        self.startTime: "float|None" = None
        self.StopTime: "float|None" = None

    def __enter__(self)->"Self":
        self.StopTime = None
        self.startTime = perf_counter()
        return self

    def __exit__(self, *_)->None:
        assert self.startTime is not None, \
            RuntimeError("__exit__ called before __enter__ (encountered self.startTime = None)")
        self.StopTime = perf_counter()
        if (self.__setMesureFunc is not None): # => set the mesure
            self.__setMesureFunc(self.name, (self.StopTime - self.startTime))

    def perttyStr(self, prettyTimeFunc:"Callable[[float], str]|None"=None)->str:
        if (self.startTime is None) or (self.StopTime is None):
            return f"SimpleProfiler({self.name!r}, noTime)"
        if prettyTimeFunc is None: 
            prettyTimeFunc = prettyTime
        return f"SimpleProfiler({self.name!r}, {prettyTimeFunc(self.StopTime - self.startTime)})"

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

class _RemainingTime_Base():
    """util class to estimate the time remaining for a task"""
    EPSILON = 1.0e-6
    
    def __init__(self, finalAmount:"int|float", *, start:bool)->None:
        self.finalAmount: float = finalAmount
        self.__currentAmount = 0
        self.startTime: "datetime|None" = None
        self.endTime: "datetime|None" = None
        if start is True:
            self.start()
    
    @property
    def progress(self)->float:
        """the current progress (from 0. to 1., truncated)"""
        return max(0., min(1., self.currentAmount / self.finalAmount))
    
    def getCurrentAmountPerSec(self)->"float|None":
        raise NotImplementedError
    
    ### total time  
    def estimatedTotalTimeDelta(self, noProgress:"_T"=None)->"timedelta|_T":
        """return the estimated total time of the task, in seconds, based on `self.progress`"""
        assert self.startTime is not None, f"it wasn't started"
        remTime = self.remainingTimeDelta(noProgress=None)
        if remTime is None:
            return noProgress
        sinceStart = (datetime.now() - self.startTime)
        return sinceStart + remTime
    
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
        amountPerSec = self.getCurrentAmountPerSec()
        if amountPerSec is None:
            return noProgress # couldn't estimate
        remainingAmount = (self.finalAmount - self.currentAmount)
        return timedelta(seconds=(remainingAmount / amountPerSec))
    
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
        remTime = self.remainingTimeDelta(noProgress=None)
        if remTime is None:
            return noProgress
        return datetime.now() + remTime
    
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
        delta = (newAmount - self.currentAmount)
        assert delta >= 0.0, \
            f"can't set a new amount({newAmount}) that is below the current amount({self.currentAmount})"
        return self.addAmount(delta)
    
    @property
    def currentAmount(self)->float:
        return self.__currentAmount
    
    def _internalSetCurrentAmount(self, value:float)->None:
        if value < 0.0: raise ValueError(f"invalide value for currentAmount: {value} < 0.0")
        if value > self.finalAmount + self.EPSILON: 
            raise ValueError(f"invalide value for currentAmount: {value} > finalAmount({self.finalAmount}) + epsilon")
        self.__currentAmount: float = value
    
    @currentAmount.setter
    def currentAmount(self, value:float)->float:
        self._internalSetCurrentAmount(value=value)
        return value
        

class RemainingTime_mean(_RemainingTime_Base):
    
    @override
    def getCurrentAmountPerSec(self)->"float|None":
        if self.startTime is None: 
            return None
        if self.currentAmount == 0.0:
            return None
        return self.currentAmount / ((datetime.now() - self.startTime).total_seconds() + self.EPSILON)
    
    
    
class RemainingTime_ema(_RemainingTime_Base):
    
    def __init__(self, finalAmount:"int|float", *, start:bool, emaCoef:float=0.75)->None:
        assert 0.0 < emaCoef <= 1.0, f"invalide value for emaCoef: {emaCoef}"
        self.emaCoef: float = emaCoef
        self._tLastAdd: "datetime|None" = None
        """the moment when the last add (or start) was done"""
        self.__currentSpeed: "float|None" = None
        """the current value of amount/sec (smoothed by the ema)"""
        super().__init__(finalAmount, start=start)

    def getCurrentAmountPerSec(self)->"float|None":
        return self.__currentSpeed
    
    @override
    def restart(self, *, start:bool)->None:
        self.__init__(finalAmount=self.finalAmount, start=start, emaCoef=self.emaCoef)
    
    @override
    def start(self)->None:
        super().start()
        self._tLastAdd = assertIsinstance(datetime, self.startTime)
    
    @override
    def _internalSetCurrentAmount(self, value:float)->None:
        previous: float = self.currentAmount
        super()._internalSetCurrentAmount(value)
        # update the ema
        now = datetime.now()
        duration = (now - assertIsinstance(datetime, self._tLastAdd))
        speed: float = ((self.currentAmount - previous) / (duration.total_seconds() + self.EPSILON))
        if self.__currentSpeed is None:
            # => no speed currently
            self.__currentSpeed = speed
        else: # => update the ema
            self.__currentSpeed = self.__currentSpeed * (1-self.emaCoef) + self.emaCoef * speed
        self._tLastAdd = now
        