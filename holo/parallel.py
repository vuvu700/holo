from collections.abc import Callable, Iterable

from queue import Queue
import threading

import multiprocess
import multiprocess.managers
import multiprocess.process
import multiprocess.queues
import multiprocess.synchronize

from .__typing import (
    Callable, Any, Iterable, Generic, )
from .prettyFormats import PrettyfyClass, basic__strRepr__, print_exception
from .protocols import _T, _P, SupportsIterableSized
from . import Pointer, assertIsinstance


### Globals ### 

_MP_Process: "type[multiprocess.process.BaseProcess]" = \
    assertIsinstance(type, multiprocess.Process) # type: ignore # yes it exist ?!

class MP_Exception():
    __slots__ = ("err", )
    def __init__(self, err: Exception) -> None:
        self.err = err

### Tasks ### 

class Task(Generic[_T], PrettyfyClass):
    __slots__ = ("func", "funcArgs", "funcKwargs", )
    
    def __init__(self, func:"Callable[_P, _T]", 
                 *funcArgs:_P.args, **funcKwargs:_P.kwargs) -> None:
        self.func = func
        self.funcArgs = funcArgs
        self.funcKwargs = funcKwargs
    
    def _toTuple(self)->"tuple[Callable[..., _T], Iterable[Any], dict[str, Any]]":
        """internal function that remove the _P typing constraints"""
        return (self.func, self.funcArgs, self.funcKwargs)

class TaskNoReturn(Task[None]):
    ...

class Task_MP(Task[_T]):
    __slots__ = ("taskID", )
    
    def __init__(self, taskID:int, func:"Callable[_P, _T]", 
                 *funcArgs:_P.args, **funcKwargs:_P.kwargs) -> None:
        super().__init__(func=func, *funcArgs, **funcKwargs)
        self.taskID: int = taskID



### Multi Threading ### 


class _Worker(threading.Thread):
    def __init__(self, manager:"Manager")->None:
        super().__init__(daemon=True)
        self.manager = manager
        
    def run(self)->None:
        while True:
            # handle pausing the workers
            self.manager.waitUntilRunning()
            # get some work (wait until some is available)
            task = self.manager._tasksList.get()
            #=> got some work => do it
            try: task.func(*task.funcArgs, **task.funcKwargs)
            except Exception as err:
                print_exception(err)
            finally: self.manager._tasksList.task_done()


class Manager():
    def __init__(self, nbWorkers:int, startPaused:bool=False)->None:
        self._tasksList:"Queue[TaskNoReturn]" = Queue()
        self.__workers:"list[_Worker]" = [_Worker(self) for _ in range(nbWorkers)]
        self.__runningEvent: threading.Event = threading.Event()
        self.setPaused(startPaused)
        # start the workers
        for worker in self.__workers:
            worker.start()

    def addWork(self, func:"Callable[_P, None]", *funcArgs:_P.args, **funcKwargs:_P.kwargs)->None:
        """add the work to the stack, will start when a worker will be available\n
        if you need to return a value, consider callbacks, or use a Pointer"""
        self._tasksList.put(TaskNoReturn(func, *funcArgs, **funcKwargs))
    def addTaskNoReturn(self, task:TaskNoReturn)->None:
        """add the task to the stack, will start when a worker will be available"""
        self._tasksList.put(task)
    
    @property
    def isPaused(self)->bool:
        """whether the workers are able to start new tasks"""
        return (self.__runningEvent.is_set() is False)
    def unPause(self)->None:
        """un pause the workers, do nothing if they alredy were not paused"""
        self.__runningEvent.set()
    def pause(self)->None:
        """pause the workers, do nothing if they alredy were paused\n
        (it won't stop any current tasks, but it will not launche new ones)"""
        self.__runningEvent.clear()
    def setPaused(self, value:bool)->None:
        """True -> self.pause() | False -> self.unPause()"""
        if value is True:
            self.pause()
        else: self.unPause()
    def waitUntilRunning(self)->None:
        """blocking until the manager is running (dont call in the main process)"""
        self.__runningEvent.wait()
    
    def remainingTasks(self)->int:
        """return the aproximative number of tasks that are still scheduled"""
        return self._tasksList.qsize()
    def join(self)->None:
        """return when all tasks are finished"""
        self._tasksList.join()

    def runBatchWithReturn(self, tasks:"SupportsIterableSized[Task[_T]]")->"list[_T]":
        """execute the `tasks` with the manager (blocking)\n
        return a list of results as [tasks[0] -> res[0], ..., tasks[n] -> res[n]]"""
        # create pointers to grab each results
        resultPointers:"list[Pointer[_T]]" = []
        # start working
        self.unPause()
        for task in tasks:
            resPtr: "Pointer[_T]" = Pointer()
            resultPointers.append(resPtr)
            (func, funcArgs, funcKwargs) = task._toTuple()
            self.addWork(taskResultGraber, func, resPtr, *funcArgs, **funcKwargs)
        # wait until all tasks are done
        self.join()
        # assemble the results and return
        return [ptr.value for ptr in resultPointers]


#def taskResultGraber(func:"Callable[_P, _T|Any]", resPtr:"Pointer[_T|Any]", *funcArgs:_P.args, **funcKwargs:_P.kwargs)->None:
def taskResultGraber(func:"Callable[_P, _T]", resPtr:"Pointer[_T]", *funcArgs:_P.args, **funcKwargs:_P.kwargs)->None:
    """a util function that put the result of `func` in `resPtr`"""
    resPtr.value = func(*funcArgs, **funcKwargs)

def parallelExec(tasks:"SupportsIterableSized[Task[_T]]", nbWorkers:"int|None")->"list[_T]":
    """execute the `tasks` in parallel with `nbWorkers` workers\n
    `nbWorkers`: int -> the numbr of worker to create, None -> create one worker per tasks\n
    return a list of results as [tasks[0] -> res[0], ..., tasks[n] -> res[n]]"""
    nbTasks:int = len(tasks)
    # create pointers to grab each results
    resultPointers:"list[Pointer[_T]]" = [Pointer() for _ in range(nbTasks)]
    # crate the manager
    if nbWorkers is None: nbWorkers = nbTasks
    manager = Manager(nbWorkers=nbWorkers, startPaused=False)
    # start working
    for taskIndex, task in enumerate(tasks):
        (func, funcArgs, funcKwargs) = task._toTuple()
        manager.addWork(taskResultGraber, func, resultPointers[taskIndex], *funcArgs, **funcKwargs)
    # wait until all tasks are done
    manager.join()
    # assemble the results and return
    return [resultPointers[taskIndex].value for taskIndex in range(nbTasks)]
    



### Multi Processing ### 





class ProcessWorker(_MP_Process, Generic[_T]):
    def __init__(self, manager:"ProcessManager[_T]")->None:
        super().__init__(daemon=True)
        self.manager = manager
        
    def run(self)->None:
        while True:
            # handle pausing the workers
            self.manager.waitUntilRunning()
            # try to get some work
            task: "Task_MP[_T]" = self.manager._tasksQueue.get()
            #=> got some work => do it
            try: 
                result = task.func(*task.funcArgs, **task.funcKwargs)
                self.manager._results[task.taskID] = result
            except Exception as err:
                self.manager._results[task.taskID] = MP_Exception(err)
            finally: self.manager._tasksQueue.task_done()


class ProcessManager(Generic[_T]):
    __Common_Ctx: "multiprocess.context.SpawnContext" = \
        assertIsinstance(
            multiprocess.context.SpawnContext, 
            multiprocess.context.BaseContext().get_context("spawn"))
    # sligth trick but it gets the spawn context of the lib
    
    def __init__(self, nbWorkers:int, startPaused:bool=False, newContext:bool=False)->None:
        # type hint (they are large so regrouped here)
        self._ctx: "multiprocess.context.SpawnContext"
        self._tasksQueue: "multiprocess.queues.JoinableQueue"
        self._results: "dict[int, _T|MP_Exception]"
        self.__runningEvent: "multiprocess.synchronize.Event"
        self.__workers: "list[ProcessWorker[_T]]"
        self.__next_taskID: int = 0
        """the taskID that will be given to the next task"""
        
        # handle context
        if newContext is True:
            # => create a new context for this manager
            self._ctx = multiprocess.context.SpawnContext()
        else: self._ctx = ProcessManager.__Common_Ctx
        # initialize manager
        self._tasksQueue = self._ctx.JoinableQueue()
        self.__runningEvent = self._ctx.Event()
        self.setPaused(startPaused)
        # setup the sync manager for the results
        self.__syncManager = multiprocess.managers.SyncManager(ctx=self._ctx)
        self.__syncManager.start()
        self._results = self.__syncManager.dict() # type: ignore
        # initialize workers
        self.__workers = [ProcessWorker(self) for _ in range(nbWorkers)]
        # start the workers
        for worker in self.__workers:
            worker.start()
    
    def __giveTaskID(self)->int:
        taskID = self.__next_taskID
        self.__next_taskID += 1
        return taskID
    
    @property
    def isPaused(self)->bool:
        """whether the workers are able to start new tasks"""
        return (self.__runningEvent.is_set() is False)
    def unPause(self)->None:
        """un pause the workers, do nothing if they alredy were not paused"""
        self.__runningEvent.set()
    def pause(self)->None:
        """pause the workers, do nothing if they alredy were paused\n
        (it won't stop any current tasks, but it will not launche new ones)"""
        self.__runningEvent.clear()
    def setPaused(self, value:bool)->None:
        """True -> self.pause() | False -> self.unPause()"""
        if value is True:
            self.pause()
        else: self.unPause()
    def waitUntilRunning(self)->None:
        """blocking until the manager is running (dont call in the main process)"""
        self.__runningEvent.wait()
    
    def remainingTasks(self)->int:
        """return the aproximative number of tasks that are still scheduled"""
        return self._tasksQueue.qsize()
    def join(self)->None:
        """return when all tasks are finished"""
        self._tasksQueue.join()
    
    def addWork(self, func:"Callable[_P, _T]", *funcArgs:_P.args, **funcKwargs:_P.kwargs)->int:
        """add the work to the stack, will start when a worker will be available\n
        if you need to return a value, consider callbacks, or use a Pointer\n
        return the taskID of the generated task (use it to get the result)"""
        return self.addTask(Task(func, *funcArgs, **funcKwargs))
    def addTask(self, task:Task[_T])->int:
        """add the task to the stack, will start when a worker will be available"""
        taskID: int = self.__giveTaskID()
        self._tasksQueue.put(Task_MP(
            taskID, task.func, *task.funcArgs, **task.funcKwargs))
        return taskID
    
    def getResult(self, taskID:int, popIt:bool=True)->"_T|MP_Exception":
        if popIt is True:
            return self._results.pop(taskID)
        else: return self._results[taskID]
    
    def runBatch(self, tasks:"SupportsIterableSized[Task[_T]]")->"list[_T]":
        """execute the `tasks` with the manager (blocking)\n
        return a list of results as [tasks[0] -> res[0], ..., tasks[n] -> res[n]]\n
        if some exceptions happends, will print thelm all then raise a RuntimeError"""
        # create pointers to grab each results
        taskIDs:"list[int]" = []
        # start working
        self.unPause()
        for task in tasks:
            (func, funcArgs, funcKwargs) = task._toTuple()
            taskIDs.append(self.addWork(func, *funcArgs, **funcKwargs))
        # wait until all tasks are done
        self.join()
        # assemble the results and return
        results = [self.getResult(taskID, popIt=True) for taskID in taskIDs]
        filteredResults: list[_T] = []
        hasExceptions: bool = False
        for res in results:
            if isinstance(res, MP_Exception):
                hasExceptions = True
                print_exception(res.err)
            else: filteredResults.append(res)
        if hasExceptions is True:
            raise RuntimeError("some tasks failed, tracebacks are alredy printed")
        return filteredResults
