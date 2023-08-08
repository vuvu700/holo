from queue import Queue, Empty as EmptyError
from threading import Thread
import time
from typing import Callable, Any, Iterable
from array import array

from holo import Pointer


# TODO: ajouter un moyen de clear les outputs deja calculés (seulement possible si )


class Worker(Thread):
    """a worker that will exec tasks one by one, and send the anwser back"""

    def __init__(self,
            workFunction:"Callable[[Any], Any|None]",
            queueInputs:"Queue[Any]",
            queueOutputs:"Queue[tuple[Any, Any]]",
            verbose:int=1, getItemTimeout:"float|None"=None,
            stopWhenOutOfWork:bool=False,
            p_workDoneCounter:"Pointer[int]|None"=None)->None:
        """ * `workFunction` is the function that wil be called each time, it arg will be the value from queueInputs, \
                it will retun a result or None, None mean no result will be added to the queue\n
            * `queueInputs` is the queue where the inputs will be getted\n
            * `queueOutputs` is where the outputs will be added, in a tuple like: tuple(input, output)\n
            * `getItemTimeout` is the time in second before the next lookup on the queueInputs if empty or blocked,\
                None mean no waiting time, None or a value too low migth compromise the \n
        """
        super().__init__()

        self.workFunction:"Callable[[Any], Any|None]" = workFunction
        self.queueInputs:"Queue[Any]" = queueInputs
        self.queueOutputs:"Queue[tuple[Any, Any]]" = queueOutputs

        self.verbose:int = verbose
        self.getItemTimeout:"float|None" = getItemTimeout
        self.__running:bool = False
        self.__stoped:bool = False
        self.__waitingInputs:bool = False
        self.__getItemBlock:bool = not isinstance(self.getItemTimeout, type(None))
        self.__stopWhenOutOfWork:bool = stopWhenOutOfWork
        self.__p_workDoneCounter:"Pointer[int]|None" = p_workDoneCounter

    def run(self):
        while self.__running is True:

            try:
                arg:"Any" = self.queueInputs.get(block=self.__getItemBlock, timeout=self.getItemTimeout)
                self.__waitingInputs = False
            except EmptyError:
                if self.__stopWhenOutOfWork is True:
                    self.stop()
                else:
                    self.__waitingInputs = True
                continue

            try:
                result:"Any" = self.workFunction(arg)
                if result is not None:
                    self.queueOutputs.put((arg, result))

            except Exception as error:
                if self.verbose == 1:
                    print(f"{type(error)} happend for the value: {arg}")
                elif self.verbose > 1:
                    print(f"{error}, for the value: {arg}")

            finally:
                if self.__p_workDoneCounter is not None:
                    self.__p_workDoneCounter.value += 1
                self.queueInputs.task_done()
        
        if (self.__running is True) or (self.__stoped is True):
            raise RuntimeError(
                "bad dev: __running and __stoped should be false when exiting the run, "
                + f"but __running={self.__running} and __stoped={self.__stoped}")
        self.__waitingInputs = False
        
    def start(self)->bool:
        """try to start the Worker for the first time, return True it started the Worker, false otherwise"""
        if self.__running is True:
            return False
        elif self.__stoped is True:
            return False
        else:
            self.__running = True
            super().start()
            return True

    def stop(self)->bool:
        """try to stop the Worker for the first time, return True it stopped the Worker, false otherwise"""
        if self.__running is False:
            return False
        elif self.__stoped is True:
            return False
        else:
            self.__running = False
            self.__stoped = False
            return True

    def isWaitingInputs(self)->bool:
        return self.__waitingInputs

    def isRunning(self)->bool:
        return self.__running

    def isStoped(self)->bool:
        return self.__stoped


class WorkersPool:
    """pool of Workers doing multiple instances of a single task in parallel"""


    def __init__(self,
            numberOfWorkers:int,
            workFunction:"Callable[[Any], Any|None]",
            initialInputs:"Iterable[Any]|None"=None,
            verbose:int=1, workersGetItemTimeout:"float|None"=None,
            stopWorkersWhenOutOfWork:bool=False, trackWorkProgress:bool=True)->None:
        
        if numberOfWorkers <= 0:
            raise ValueError(f"the number of workers need to be >= 1")
        
        # vars setup
        self.nbWorkers:int = numberOfWorkers
        self.verbose:int = verbose
        self.workersGetItemTimeout:"float|None" = workersGetItemTimeout
        self.stopWorkersWhenOutOfWork:bool = stopWorkersWhenOutOfWork
        self.__addedWorkCount:int = 0
        self.__finishedWorkCount:int = 0
        self.__finishedWorkCount_perWorker:"list[Pointer[int]]" = [Pointer(0) for _ in range(self.nbWorkers)]
        self.__trackWorkProgress:bool = trackWorkProgress

        # create the queues needed
        self.queueInputs:"Queue[Any]" = Queue(0)
        self.queueOutputs:"Queue[tuple[Any, Any]]" = Queue(0)
        self.__outputsConverted:"list[list[tuple[Any, Any]]]" = []
        """all the outputs previously converted"""

        # create all the workers
        self.__workersList:"list[Worker]" = []
        for workerIndex in range(self.nbWorkers):

            if self.__trackWorkProgress is True:
                p_workDoneCounter = self.__finishedWorkCount_perWorker[workerIndex]
            else:p_workDoneCounter = None

            self.__workersList.append(
                Worker(
                    workFunction, self.queueInputs, self.queueOutputs,
                    verbose=self.verbose, getItemTimeout=self.workersGetItemTimeout,
                    stopWhenOutOfWork=self.stopWorkersWhenOutOfWork,
                    p_workDoneCounter=p_workDoneCounter,
                )
            )

        # add the initial inputs
        if initialInputs is not None:
            self.addInputs(initialInputs)
            
    
    def addInputs(self, newInputs:"Iterable[Any]")->None:
        """add the new work to the current queue"""
        addedWorkCount:int = 0
        for inputArg in newInputs:
            self.queueInputs.put(inputArg)
            addedWorkCount += 1
        if self.__trackWorkProgress is True:
            self.__addedWorkCount += addedWorkCount

    def startWorkers(self)->bool:
        """strat all workers, and return True if it started them all"""
        return all([worker.start() for worker in self.__workersList])

    def stopWorkers(self)->bool:
        """stop all workers, and return True if it stoped them all"""
        return all([worker.stop() for worker in self.__workersList])

    def joinWorkers(self)->bool:
        """if the workers will stop when out of work, return True when all workers joined\n
        if the workers will NOT stop when out of work, return False\n"""
        if self.stopWorkersWhenOutOfWork is True:
            for worker in self.__workersList:
                worker.join()
            return True
        else:
            return False

    def joinWorkFinished(self)->bool:
        """join when all the planned work is finished and return True or no workers are working and return False"""
        intervalChecksWorkers:float = 1e-4 #sec
        with self.queueInputs.all_tasks_done:

            # while some unfinished tasks remain
            while self.queueInputs.unfinished_tasks != 0:
                # test if no worker are working
                if sum(worker.isRunning() is True for worker in self.__workersList) == 0:
                    return False
                #wait a certaint time before re checking the workers 
                self.queueInputs.all_tasks_done.wait(intervalChecksWorkers)
                
        return True

    def isWorkFinished(self)->bool:
        """return whether all the planed work is finished"""
        with self.queueInputs.all_tasks_done:
            return self.queueInputs.unfinished_tasks == 0

    def workersAreRunning(self)->bool:
        """return True if any worker is still running"""
        return any(worker.isRunning for worker in self.__workersList)


    def getLastOutputs(self)->"list[tuple[Any, Any]]":
        nbOutputs:int = self.queueOutputs.qsize()
        # the real nb of outputs might increase but will not decrease outside of this function
        outputsList:"list[tuple[Any, Any]]" = [(None, None)] * nbOutputs

        nbOutputsConverted:int = 0
        outputValue:"tuple[Any, Any]"
        for index in range(nbOutputs):
            try:
                outputValue = self.queueOutputs.get(block=False)
                outputsList[index] = outputValue
                nbOutputsConverted += 1

            except EmptyError:
                outputsList = outputsList[: nbOutputsConverted]
                break

        if len(outputsList) > 0:
            self.__outputsConverted.append(outputsList)

        return outputsList

    def getAllOutputs(self, updateOutputs:bool=True)->"list[tuple[Any, Any]]":
        if updateOutputs is True:
            self.getLastOutputs()
        outputsList:"list[tuple[Any, Any]]" = []
        for convertedList in self.__outputsConverted:
            outputsList += convertedList
        return outputsList
    
        
    def getAllOutputs_fast(self, updateOutputs:bool=True)->"list[list[tuple[Any, Any]]]":
        if updateOutputs is True:
            self.getLastOutputs()
        return self.__outputsConverted

    def getNbWorkAdded(self)->int:
        """return the number of planned work"""
        return self.__addedWorkCount

    def getNbWorkFinished(self)->int:
        """return the total cont of finished work"""
        # update the count
        new_finishedWorkCount:int = 0
        for indexWorker in range(self.nbWorkers):
            new_finishedWorkCount += self.__finishedWorkCount_perWorker[indexWorker].value
        self.__finishedWorkCount = new_finishedWorkCount
        
        return self.__finishedWorkCount
    
    def getNbWorkFinished_perWorker(self)->"list[int]":
        """return a copy of the count of finished work, for each worker"""
        return [ptr.value for ptr in self.__finishedWorkCount_perWorker]

    def clearOutputs(self)->bool:
        """try to clear the outputs and reset the counters of work, only possible if the work is finished"""
        if self.isWorkFinished() is True:
            self.__outputsConverted = []
            self.__addedWorkCount = 0
            self.__finishedWorkCount = 0
            for indexWorker in range(self.nbWorkers):
                self.__finishedWorkCount_perWorker[indexWorker].value = 0

            return True
        else:
            return False

def demo()->None:
    ## run a demo
    def func(t)->float:
        t *= 1e-6
        time.sleep(t)
        return t

    pool = WorkersPool(10, func, range(1_000))
    print("pool created")
    print(pool.getNbWorkFinished(), pool.getNbWorkAdded())
    
    pool.startWorkers()
    print("pool started")

    print(pool.getNbWorkFinished(), pool.getNbWorkAdded())
    time.sleep(0.01)
    print("slept 0.01 sec")
    print(pool.getNbWorkFinished(), pool.getNbWorkAdded())
    
    pool.addInputs(range(1_000, 2_000))
    print("added new work")

    print(pool.getNbWorkFinished(), pool.getNbWorkAdded())
    time.sleep(0.01)
    print("slept 0.01 sec")
    print(pool.getNbWorkFinished(), pool.getNbWorkAdded())

    print("waiting all work are finished")
    pool.joinWorkFinished()
    print("all work are finished")

    print(pool.getNbWorkFinished(), pool.getNbWorkAdded())
    print(pool.getNbWorkFinished_perWorker())

