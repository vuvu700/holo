import time

from holo.__typing import Literal

class Loading():
    def __init__(self, name:str, smoothing:float=0.0)->None:
        """configure an empty loading tracker\n
        `name` is the name of the loading\n
        `smoothing` [0. -> 1.[ is how much the time estimation will be smoothed\
            note: values closer to 1. mean more smoothing, 0. mean no smoothing"""
        if not (0 <= smoothing < 1): # check value
            raise ValueError(f"invalide bounding for smoothing: {smoothing}")
        self.name:str = name
        """the name of the loading"""
        self.__startTime:"float|None" = None
        """the time when the loading was started | None -> not started"""
        self.__endTime:"float|None" = None
        """the time when the loading has finished | None -> not finished"""
        self.__nbTaskDone:int = 0
        """the number of tasks alredy done"""
        self.__totaltasks:"int|None" = None
        """the total number of tasks to do | None ->  not setted"""
        self.smoothing:float = smoothing
        """the smoothing factor for time estimation"""
    
    def start(self)->None:
        if self.__startTime is not None:
            # => alredy started
            raise RuntimeError(f"the loading was alredy started")
        self.__startTime = time.time()
    
    def reset(self)->None:
        self.__init__(name=self.name, smoothing=self.smoothing)
    
    def runningTime(self)->float:
        """return how much time the loading has been running"""
        if self.__startTime is None: # => not started
            raise RuntimeError(f"the loading wasn't started")
        if self.__endTime is None: # => not finished yet
            return (time.time() - self.__startTime)
        # => has finished
        return (self.__endTime - self.__startTime)
    
    def setTotalTasks(self, nbTasks:int)->None:
        """set the total number of tasks for the first time"""
        if self.__totaltasks is not None:
            raise RuntimeError(f"the total number of tasks has alredy been setted")
        self.__totaltasks = nbTasks

    def getAvgTime(self)->float:
        """return the average time per task (no smoothing)"""
        if self.__startTime is None: # => not started
            raise RuntimeError(f"the loading wasn't started")
        if self.__totaltasks is None: # => nb tasks not setted
            raise RuntimeError(f"the total number of tasks wasn't setted")
        if self.__nbTaskDone == 0: # => no task done
            raise RuntimeError(f"no tasks done")
        return self.runningTime() / self.__nbTaskDone

    def finishTask(self)->None:
        """to call each time a task as been finished"""
        if self.__startTime is None: # => not started
            raise RuntimeError(f"the loading wasn't started")
        if self.__endTime is not None: # => alredy finished
            raise RuntimeError(f"the loading is alredy finished")
        self.__nbTaskDone += 1
        if self.__nbTaskDone == self.__totaltasks:
            # => loading finished => set end time
            self.__endTime = time.time()
    
    @property
    def __emaFactor(self)->float:
        return (1 - self.smoothing)
    
    def isFinished(self)->bool:
        """return whether if the loading has finished"""
        return self.__endTime is not None
    
    def getRemainingTime(self, algo:"Literal['avg', 'smooth']")->float:
        if self.__startTime is None: # => not started
            raise RuntimeError(f"the loading wasn't started")
        if self.__totaltasks is None: # => nb tasks not setted
            raise RuntimeError(f"the total number of tasks wasn't setted")
        if algo == "avg":
            #  avgTimePerTask * nbRemTasks
            return self.getAvgTime() * (self.__totaltasks - self.__nbTaskDone)
        else: raise NotImplementedError(f"algo = {algo} is not implemented")
    
    @property
    def nbTasksFinished(self)->int:
        """the number of tasks done"""
        if self.__startTime is None: # => not started
            raise RuntimeError(f"the loading wasn't started")
        if self.__totaltasks is None: # => nb tasks not setted
            raise RuntimeError(f"the total number of tasks wasn't setted")
        return self.__nbTaskDone
    
    @property
    def totalNbTasks(self)->int:
        """the number of tasks done"""
        if self.__startTime is None: # => not started
            raise RuntimeError(f"the loading wasn't started")
        if self.__totaltasks is None: # => nb tasks not setted
            raise RuntimeError(f"the total number of tasks wasn't setted")
        return self.__totaltasks