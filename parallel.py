from collections.abc import Callable, Iterable, Mapping
from queue import Queue, Empty as EmptyError
from threading import Thread
import time

from holo.__typing import (
    Callable, Any, Iterable, Generic, Sequence,
)
from holo.prettyFormats import basic__strRepr__
from holo.protocols import _T, _P, SupportsIterableSized
from holo import Pointer

@basic__strRepr__
class TaskNoReturn():
    __slots__ = ("func", "funcArgs", "funcKwargs")
    def __init__(self, func:"Callable[_P, None]", *funcArgs:_P.args, **funcKwargs:_P.kwargs) -> None:
        self.func = func
        self.funcArgs = funcArgs
        self.funcKwargs = funcKwargs
    
@basic__strRepr__
class TaskWithReturn(Generic[_T]):
    __slots__ = ("func", "funcArgs", "funcKwargs")
    def __init__(self, func:"Callable[_P, _T]", *funcArgs:_P.args, **funcKwargs:_P.kwargs) -> None:
        self.func = func
        self.funcArgs = funcArgs
        self.funcKwargs = funcKwargs
    def _toTuple(self)->"tuple[Callable[..., Any], Iterable[Any], dict[str, Any]]":
        """internal function that remove the _P typing constraints"""
        return (self.func, self.funcArgs, self.funcKwargs)


class Worker(Thread):
    def __init__(self, manager:"Manager")->None:
        super().__init__(daemon=True)
        self.manager = manager
        
    def run(self)->None:
        while True:
            # handle pausing the workers
            if self.manager.isPaused is True:
                time.sleep(1e-3) # => sleep and relase the thread
                continue
            
            # try to get some work
            try: task = self.manager._tasksList.get()
            except EmptyError: 
                time.sleep(1e-5) # => relase the thread
                continue # => retry
            
            #=> got some work => do it
            try: task.func(*task.funcArgs, **task.funcKwargs)
            finally: self.manager._tasksList.task_done()


class Manager():
    def __init__(self, nbWorkers:int, startPaused:bool=False)->None:
        self._tasksList:"Queue[TaskNoReturn]" = Queue()
        self.__workers:"list[Worker]" = [Worker(self) for _ in range(nbWorkers)]
        self.__paused:bool = startPaused
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
        return self.__paused
    def unPause(self)->None:
        """un pause the workers, do nothing if they alredy were not paused"""
        self.__paused = False
    def pause(self)->None:
        """pause the workers, do nothing if they alredy were paused\n
        (it won't stop any current tasks, but it will not launche new ones)"""
        self.__paused = True
    
    def isEmpty(self)->bool:
        """return True when no more tasks are scheduled"""
        return (self._tasksList.qsize() == 0) # better than .empty()
    def join(self)->None:
        """return when all tasks are finished"""
        self._tasksList.join()

    def runBatchWithReturn(self, tasks:"SupportsIterableSized[TaskWithReturn[_T]]")->"list[_T]":
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

def parallelExec(tasks:"SupportsIterableSized[TaskWithReturn[_T]]", nbWorkers:"int|None")->"list[_T]":
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
    


