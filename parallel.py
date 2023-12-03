from collections.abc import Callable, Iterable, Mapping
from queue import Queue, Empty as EmptyError
from threading import Thread
import time

from holo.__typing import Callable, Any, Iterable, TypeAlias
from holo.protocols import _T, _P
from holo import Pointer

_TaskNoReturn:TypeAlias = "tuple[Callable[..., None], Iterable[Any], dict[str, Any]]"
_TaskWithReturn:TypeAlias = "tuple[Callable[..., Any], Iterable[Any], dict[str, Any]]"

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
            try: (func, funcArgs, funcKwargs) = self.manager._tasksList.get()
            except EmptyError: 
                time.sleep(1e-5) # => relase the thread
                continue # => retry
            
            #=> got some work => do it
            func(*funcArgs, **funcKwargs)
            self.manager._tasksList.task_done()


class Manager():
    def __init__(self, nbWorkers:int, startPaused:bool=False)->None:
        self._tasksList:"Queue[_TaskNoReturn]" = Queue()
        self.__workers:"list[Worker]" = [Worker(self) for _ in range(nbWorkers)]
        self.__paused:bool = startPaused
        # start the workers
        for worker in self.__workers:
            worker.start()

    def addWork(self, func:"Callable[_P, None]", *funcArgs:_P.args, **funcKwargs:_P.kwargs)->None:
        """add the work to the stack, will start when a worker will be available\n
        if you need to return a value, consider callbacks, or use a Pointer"""
        self._tasksList.put((func, funcArgs, funcKwargs))
    
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


def taskResultGraber(func:"Callable[_P, None]", resPtr:Pointer, *funcArgs:_P.args, **funcKwargs:_P.kwargs)->None:
    """a util function that put the result of `func` in `resPtr`"""
    resPtr.value = func(*funcArgs, **funcKwargs)

def parallelExec(tasks:"list[_TaskWithReturn]", nbWorkers:"int|None")->"list[Any]":
    """execute the `tasks` in parallel with `nbWorkers` workers\n
    `nbWorkers`: int -> the numbr of worker to create, None -> create one worker per tasks\n
    return a list of results as [tasks[0] -> res[0], ..., tasks[n] -> res[n]]"""
    nbTasks:int = len(tasks)
    # create pointers to grab each results
    resultPointers = [Pointer() for _ in range(nbTasks)]
    # crate the manager
    if nbWorkers is None:
        manager = Manager(nbWorkers=nbTasks, startPaused=False)
    else: manager = Manager(nbWorkers=nbWorkers, startPaused=False)
    # start working
    for taskIndex, (func, funcArgs, funcKwargs) in enumerate(tasks):
        manager.addWork(taskResultGraber, func, resultPointers[taskIndex], *funcArgs, **funcKwargs)
    # wait until all tasks are done
    manager.join()
    # assemble the results and return
    return [resultPointers[taskIndex].value for taskIndex in range(nbTasks)]
    


