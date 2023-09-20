from collections.abc import Callable, Iterable, Mapping
import os, os.path
import threading
import time
import weakref
import gc
from pathlib import Path
import pickle



from holo.__typing import (
    Any, Generic, Iterator, TypeVar, Generator,
    Self, MutableMapping, Iterable,
    Literal, overload, TypeAlias, TYPE_CHECKING,
)
from holo.protocols import (
    SupportsWrite, SupportsFileRead, 
    SupportsPickleRead,
    SupportsReduce, _KT, _T, 
)

from holo.files import get_unique_name
from holo import print_exception

if TYPE_CHECKING:
    # => heavy imports, they will be done justInTime
    import pandas, numpy





### types definitions

_T_Savable = TypeVar("_T_Savable", 
    bound="SupportsReduce|numpy.ndarray|pandas.DataFrame")


class _Unsetted():
    """class that garenty up to one instance"""
    __value:"_Unsetted|None" = None
    def __new__(cls)->Self:
        obj = super().__new__(cls)
        if _Unsetted.__value is None:
            _Unsetted.__value = obj
            return obj
        else: raise RuntimeError("tryed to create a second instance")


_Verbose = Literal[0, 1, 2, 3]

_CompressionLib = Literal["lz4", "lzma", "bz2", "bzip2", "lzo", "blosc", "zlib"]
"""some _CompressionLib are only usable certain _SaveLib"""

_StandardMethodes = Literal[
    # standard library
    "allwaysPickle",
    # req numpy, pandas
    "pickle|numpy|pandas",
        # ndarray => numpy, DataFrame => pandas
        # otherwise => pickle
    # req joblib
    "allwaysJoblib", 
    # req joblib, numpy, pandas
    "pickle|joblib", 
        # ndarray|DataFrame => joblib, otherwise => pickle
]

_SaveLib = Literal["pickle", "numpy", "pandas", "joblib"]

_CustomMethodes:TypeAlias = "dict[type, _SaveLib]"
"""you give a map asscociating types to a certain lib\n
the objects that will be saved will use the lib of the most narrowed matching type:\n
when given {object:lib1, int:lib2, <subclass 'A' of int>:lib3}: \n
 - an instance of 'A' will use lib3\n
 - an instance of 'int' (and not of 'A') will use lib2\n
 - an instance of 'str' will use lib1\n
avoid using mixed subclass:
ex: when given {str:lib1, int:lib2}, \
    and an instance of 'str' and 'int', it migth coose one or the other
"""

### consts

SESSION_UPDATE_AFTER:int = 1*60 # update the session every 1min
SESSION_DELETE_AFTER:int = 5*60 # NOTE: /!\ an un-updated session for 5min is deleted
FILENAME_SESSION_INFOS:str = "session.txt"

SAVEMODULE_DIRECTORY:Path = Path(os.environ["TEMP"]).joinpath(".SaveModule/")

CONST_PANDAS_HDF_KEY = "DF"

ALLOWED_CompressionLibs:"dict[_SaveLib|Literal['__other__'], set[_CompressionLib]]" = {
    "__other__": {"lz4", "bz2", "bzip2", "lzma"},
    "pandas": {"lzo", "bzip2", "blosc", "zlib"},
}

_unsetted = _Unsetted() # create its unique instance

### general funcs

def copyStr(string:str)->str:
    return "".join(string)

def cleanFile_if_exist(filePath:str)->None:
    """function to finalize ObjectSaver"""
    if os.path.lexists(filePath) is True:
        os.remove(filePath)

SESSION_UPDATE_AFTER:int = 5 # update the session every 1min
SESSION_DELETE_AFTER:int = 30 # NOTE: /!\ an un-updated session for 5min is deleted
### Session definition

class SessionsCleaner(threading.Thread):
    def __init__(self, start:bool=False) -> None:
        super().__init__(daemon=True)
        self.__paused:bool = False
        if start is True:
            self.start()
    
    def clean_old_sessions(self, directorys:"list[Path]")->None:
        for directory in (directorys + [SAVEMODULE_DIRECTORY]):
            for sessionDirPath in directory.iterdir():
                print(f"treating: {sessionDirPath.as_posix()} ...", end=None)
                if sessionDirPath.is_dir() is False:
                    print(f" => not a dir")
                    continue # => not a dir => not a session
                
                # try to get the session's file
                try: 
                    with open(sessionDirPath.joinpath(FILENAME_SESSION_INFOS), mode='r') as sessionFile:
                        sessionFile_content = sessionFile.read()
                except PermissionError:
                    print(f" => PermissionError")
                    continue # => file is being accessed => session is running
                except FileNotFoundError:
                    print(f" => FileNotFoundError")
                    continue # => no session file => not a session or not yet created
                
                # read the session's file
                sessionLastUpdate:float = float(sessionFile_content)
                if (time.time() - sessionLastUpdate) > SESSION_DELETE_AFTER:
                    print(f" => cleaning it")
                    # => session is too old => delete it
                    for sessionsFiles in sessionDirPath.iterdir():
                        print(f" -> removing {sessionsFiles.name}")
                        os.remove(sessionsFiles)
                    sessionDirPath.rmdir()
                else: # => not old enough to be deleted
                    continue
    
    def _firstStart(self)->None:
        if self.is_alive() is False:
            self.start()
    
    def pause(self)->None:
        self.__paused = True
    def unpause(self)->None:
        self.__paused = False
    
    def run(self)->None:
        print("here 1")
        while True:
            print("here 2")
            try:
                while self.__paused is True:
                    print("here paused")
                    time.sleep(0.1) # => sleep a few moments
                
                print("here 3")
                # => update each session
                sessionsHolderDirs:"list[Path]" = []
                session:"Session|None"
                for sessionRef in Session.sessionsHierarchy:
                    print("here 3.1")
                    session = sessionRef()
                    if (session is None) or (session.wasCleaned is True):
                        continue # => session is dead
                    # => updating the session
                    session.update_session()
                    session.clean_forgoten_objects()
                    sessionsHolderDirs.append(session.directory.parent)
                    print("here 3.2")
                self.clean_old_sessions(sessionsHolderDirs)
                del sessionsHolderDirs
                print("here 4")
                time.sleep(SESSION_UPDATE_AFTER) # update every

            except Exception as err:
                print("here 5")
                # => don't stop on errors
                print("an error happened durring update")
                print_exception(err)



class Session():
    sessionsHierarchy:"list[weakref.ref[Session]]" = []
    """store a weakref to all the sessions, \
        added sessions are pushed at the end, \
        and so considered on top of previous sessions"""
    sessionsCleaner:"SessionsCleaner" = SessionsCleaner(start=False)
    # don't start it now: the class `Session` isn't created yet  
    __totalSessionsCount:int = 0
    
    def __init__(self,
            location:"Path|None"=None, dirName:"None|str"=None, 
            name:"str|None"=None, savingArgs:"SaveArgs|None"=None,
            verbose:"_Verbose"=0)->None:
        Session.sessionsCleaner._firstStart()
        self.__name:str = Session.__getNewName(name)
        self.__directory:Path = \
            self.__create_session_directory(location=location, dirName=dirName)
        self.verbose:"_Verbose" = verbose # TODO: use it 
        self.__tracked_objects:"dict[str, weakref.finalize]" = {}
        self.objects_count:int = 0
        """total abount of tracked object (during lifetime)"""
        if savingArgs is None:
            savingArgs = SaveArgs(compression=None, methode="allwaysPickle")
        self.savingArgs:"SaveArgs" = savingArgs
        
        # => bind the session
        Session.bindSession(self)
        self.__cleanedSession:bool = False
        """when True => the Session is unusable (debinded and files migth be cleaned)"""
        self.update_session()

    @classmethod
    def get_topSession(cls)->"Session":
        hierarchy = Session.sessionsHierarchy
        session:"Session|None"
        for sessionRef in reversed(hierarchy):
            session = sessionRef()
            if session is None:
                hierarchy.pop()
            else: # => found a Session
                return session
        raise RuntimeError("no session setted")
            
    @classmethod
    def __getNewName(cls, useName:"str|None")->str:
        # => determine the names currently used
        currentNames:"set[str]" = set()
        session:"Session|None"
        # reversed => index of nexts stay correct after popping
        for sessionRef in reversed(Session.sessionsHierarchy):
            session = sessionRef()
            if session is None:
                continue # => session is dead
            else: # => found a Session
                currentNames.add(session.__name)
        # => determine the name to give
        if useName is None:
            useName = f"session n°{Session.__totalSessionsCount+1}"
        if useName in currentNames:
            raise ValueError(f"the given name: {repr(useName)} is alredy used by a Session")
        # => name isn't alredy used
        Session.__totalSessionsCount += 1
        return useName
            
        
    
    @classmethod
    def bindSession(cls, session:"Session")->None:
        Session.sessionsHierarchy.append(weakref.ref(session))
    
    
    @property
    def wasCleaned(self)->bool:
        return self.__cleanedSession
    
    @property
    def directory(self)->Path:
        return self.__directory
    
    def __create_session_directory(self,
            location:"Path|None"=None, dirName:"None|str"=None)->Path:
        if location is None:
            location = SAVEMODULE_DIRECTORY
        if location.exists() is False:
            location.mkdir()
        if dirName is None:
            dirName = get_unique_name(
                location, onlyNumbers=False, nbCharacters=8, guidlike=True,
                randomChoice=True, prefix="session_", suffix="/",
                filter_dirnames=True, filter_filename=False,
            )    
        directory = location.joinpath(dirName)
    
        # check the path and create the directory if needed
        if directory.exists() is True:
            raise FileExistsError(f"the selected session at {repr(directory.as_posix())} alredy exist")
        directory.mkdir(exist_ok=True)
        return directory
    
    
    def track_object(self, obj:"ObjectSaver")->None:
        """copy the tmp_file_path to leave no reference"""
        if self.wasCleaned is True:
            raise RuntimeError(f"the session was cleaned, don't accept new objects")
        objFileStrPath = obj.filePath.as_posix() # not a ref to obj
        object_finalizer = weakref.finalize(
            obj, cleanFile_if_exist, objFileStrPath,
        )
        self.__tracked_objects[objFileStrPath] = object_finalizer
        # => tracking it

    def untrack_object(self, obj:"ObjectSaver")->bool:
        """clean the return false if the object was not tracked, only un-track"""
        # don't disable when was cleaned, is is still safe to use
        fileStrPath:str = obj.filePath.as_posix()
        finalizer:"weakref.finalize|None" = self.__tracked_objects.get(fileStrPath, None)
        if finalizer is not None: # => objetc is tracked, clean it and un-track
            if finalizer.alive is True:
                finalizer() 
                # => file cleaned
            else:
                cleanFile_if_exist(fileStrPath)
                self.__tracked_objects.pop(fileStrPath)
                # => object untracked
            return True
        # => not tracked
        return False

    def allocate_unique_id(self)->int:
        if self.wasCleaned is True:
            raise RuntimeError(f"the session was cleaned, don't accept new objects")
        self.objects_count += 1
        return self.objects_count - 1

    def update_session(self)->None:
        if self.wasCleaned is True:
            raise RuntimeError(f"the session was cleaned, can't be re-updated")
        with open(self.directory.joinpath(FILENAME_SESSION_INFOS), mode="w") as sessionFile:
            sessionFile.write(f"{time.time():.03f}")
            sessionFile.flush()



    def clean_forgoten_objects(self)->None:
        # don't disable when was cleaned, is is still safe to use
        gc.collect()
        items_to_pop:"list[str]" = []
        # clean the object un-tracked
        for (file_path, object_finalizer) in self.__tracked_objects.items():
            if object_finalizer.alive is False:
                cleanFile_if_exist(file_path)
                items_to_pop.append(file_path)
        # un-track the objects
        for file_path in items_to_pop:
            self.__tracked_objects.pop(file_path)
            # => proped forgoten object

    def __debindSession(self)->None:
        """debind the session from Session and pop dead sessions\n
        safe to call multiple time"""
        hierarchy = Session.sessionsHierarchy
        session:"Session|None"
        index:int = len(hierarchy) # out of the list
        # decreesing index => index of nexts stay correct after popping
        for sessionRef in reversed(hierarchy):
            index -= 1 # => from now index is correct
            session = sessionRef()
            if session is None:
                hierarchy.pop(index)
            # => found a Session
            elif session is self:
                # => debind it
                hierarchy.pop(index)
            else: pass # => not self

    @classmethod
    def debindDeadSessions(cls)->None:
        hierarchy = Session.sessionsHierarchy
        session:"Session|None"
        index:int = len(hierarchy) # out of the list
        # decreesing index => index of nexts stay correct after popping
        for sessionRef in reversed(hierarchy):
            index -= 1 # => from now index is correct
            session = sessionRef()
            if session is None:
                hierarchy.pop(index)
            # => found a Session
            else: pass # => not self

    def clear(self, showFilesError:bool=True)->None:
        """ - clean the session of all forgoten objects\n
         - makes sure there is no tracked objects remaining\n
         - try to remove the directory (silent if showFilesError is False)\n
         - debind the session of Session and replace the mainSession (if needed)"""
        self.clean_forgoten_objects()
        if len(self.__tracked_objects) != 0:
            # => tracked objects remaining
            raise RuntimeError(
                f"tryed to clear the session:{self} "
                f"but there is still {len(self.__tracked_objects)} tracked objects")
        # => no tracked objects => can clean and stop the session
        # => there should only be the session file in the directory
        if self.wasCleaned is True:
            return None # => alredy cleaned and unbind
        
        try:
            os.remove(self.directory.joinpath(FILENAME_SESSION_INFOS))
            self.directory.rmdir()
        except (OSError, FileNotFoundError) as err:
            # => don't stop on errors
            if showFilesError is True:
                print("/!\\ an error happened while trying to clean the directory")
                print_exception(err)
        self.__debindSession()
        self.__cleanedSession = True
        

    def __del__(self)->None:
        """all objects of this session must be be dead\n
        try to clean the directory (silence common files exceptions)"""
        self.clear(showFilesError=True)
        
    def __enter__(self)->Self:
        return self
    def __exit__(self, *_)->None:
        self.clear(showFilesError=True)




### SaveArgs

class SaveArgs():
    def __init__(self,
            compression:"tuple[_CompressionLib, int]|None"=None,
            methode:"_StandardMethodes|_CustomMethodes"="allwaysPickle")->None:
        self.compression:"tuple[_CompressionLib, int]|None" = compression
        self.methode:"_CustomMethodes" = SaveArgs._stdMethode_to_custom(methode)
        self._preImport_compLib()
    
    @property
    def compressionLevel(self)->"int|None":
        if self.compression is None:
            return None
        return self.compression[1]

    @property
    def compressionLib(self)->"_CompressionLib|None":
        if self.compression is None:
            return None
        return self.compression[0]

    def save(self, filePath:Path, obj:object)->None:
        useLib:"_SaveLib" = self.getSaveLib(type(obj))
        fileNormal:"SupportsWrite[bytes]"
        fileHdf:"pandas.HDFStore"
        if useLib == "pickle":
            fileNormal = self.getFile(filePath, useLib, 'w')
            pickle.dump(obj=obj, file=fileNormal, protocol=-1)
        elif useLib == "numpy":
            import numpy
            fileNormal = self.getFile(filePath, useLib, 'w')
            numpy.save(arr=obj, file=fileNormal, allow_pickle=True)
        elif useLib == "pandas":
            import pandas
            fileHdf = self.getFile(filePath, useLib, 'w')
            assert isinstance(obj, pandas.DataFrame), \
                TypeError(f"in order to save an object with lib: {useLib}"
                          f"the object needs to be an instance of {pandas.DataFrame}")
            obj.to_hdf(fileHdf, CONST_PANDAS_HDF_KEY)
        elif useLib == "joblib":
            import joblib
            fileNormal = self.getFile(filePath, useLib, 'w')
            joblib.dump(obj, fileNormal, protocol=-1)
        else: raise ValueError(f"the lib: {useLib} isn't supported")
        # => saved the object
        
    def load(self, filePath:Path, objectType:"type[_T]")->"_T":
        useLib:"_SaveLib" = self.getSaveLib(objectType)
        fileNormal:"SupportsFileRead[bytes]"
        filePickle:"SupportsPickleRead"
        fileHdf:"pandas.HDFStore"
        if useLib == "pickle":
            filePickle = self.getFile(filePath, useLib, 'r')
            obj = pickle.load(file=filePickle)
        elif useLib == "numpy":
            import numpy
            fileNormal = self.getFile(filePath, useLib, 'r')
            obj = numpy.load(file=fileNormal, allow_pickle=True)
        elif useLib == "pandas":
            import pandas
            fileHdf = self.getFile(filePath, useLib, 'r')
            obj = pandas.read_hdf(fileHdf, CONST_PANDAS_HDF_KEY)
        elif useLib == "joblib":
            import joblib
            fileNormal = self.getFile(filePath, useLib, 'r')
            obj = joblib.load(fileNormal)
        else: raise ValueError(f"the lib: {useLib} isn't supported")
        # => loaded the object, checking asserting its type
        assert isinstance(obj, objectType), \
            TypeError(f"the readed object with lib: {useLib} is of type: {type(obj)} "
                        f"but expected an object of type: {objectType}")
        return obj

    def getSaveLib(self, objectType:"type")->"_SaveLib":
        narrowestType:"type|None" = None
        selectedLib:"_SaveLib|None" = None
        for typeToCkeck, lib in self.methode.items():
            if issubclass(objectType, typeToCkeck):
                if (narrowestType is None) or issubclass(typeToCkeck, narrowestType):
                    # => new type | subclass of current narrowest type
                    narrowestType = typeToCkeck
                    selectedLib = lib
        if selectedLib is None:
            raise TypeError(f"couldn't find a lib for the given type: {objectType}")
        return selectedLib
    
    @overload
    def getFile(self, filePath:Path, saveLib:"Literal['pandas']", mode:"Literal['r','w']")->"pandas.HDFStore": ...
    @overload
    def getFile(self, filePath:Path, saveLib:"Literal['pickle']", mode:"Literal['r']")->"SupportsPickleRead": ...
    @overload
    def getFile(self, filePath:Path, saveLib:"_SaveLib", mode:"Literal['r']")->"SupportsFileRead[bytes]": ...
    @overload
    def getFile(self, filePath:Path, saveLib:"_SaveLib", mode:"Literal['w']")->"SupportsWrite[bytes]": ...
    def getFile(self, 
            filePath:Path, saveLib:"_SaveLib", mode:"Literal['r', 'w']",
            )->"SupportsWrite[bytes]|SupportsFileRead[bytes]|pandas.HDFStore|SupportsPickleRead":
        """not overloaded version"""
        compLib:"_CompressionLib|None" = self.compressionLib
        compLevel:"int|None" = self.compressionLevel
        self._assert_allowed_compLib(saveLib, compLib)
        
        if saveLib == "pandas":
            # => hdf file
            import pandas
            return pandas.HDFStore(
                filePath, mode=mode, complevel=compLevel,
                complib=compLib)
        # => lib != "pandas" => normal file | compress file
        if compLib is not None:
            # => compress file
            if compLib == "lz4":
                if compLevel is None: compLevel = 0 # default
                import lz4.frame
                return lz4.frame.LZ4FrameFile(
                    filePath, mode=mode, compression_level=compLevel,
                    block_size=lz4.frame.BLOCKSIZE_MAX4MB)
            elif compLib == "lzma":
                import lzma
                if (compLevel is not None) and (compLevel > 9):
                    compLevel = (compLevel | lzma.PRESET_EXTREME)
                return lzma.LZMAFile(filePath, mode=mode, preset=compLevel)
            elif compLib in ("bz2", "bzip2"):
                if compLevel is None: compLevel = 9 # is default
                import bz2
                return bz2.BZ2File(filePath, mode=mode, compresslevel=compLevel)
            else: raise ValueError(f"unsupported compLib: {compLib} with the saveLib: {saveLib}")
        
        # => uncompressed file
        return open(filePath, mode=(mode+'b')) 
    
    @classmethod
    def _assert_allowed_compLib(cls, saveLib:"_SaveLib", compLib:"_CompressionLib|None")->None:
        if compLib is not None:
            allowed_compLibs:"set[_CompressionLib]" = ALLOWED_CompressionLibs["__other__"]
            allowed_compLibs = ALLOWED_CompressionLibs.get(saveLib, allowed_compLibs)
            assert compLib in allowed_compLibs, \
                ValueError(f"the _CompressionLib: {compLib} isn't supported "
                           f"with the _SaveLib: {saveLib}")
        
    
    @classmethod
    def _stdMethode_to_custom(cls,
            methode:"_StandardMethodes|_CustomMethodes")->"_CustomMethodes":
        """transform _StandardMethodes to _CustomMethodes and pre import the needed libs"""
        if isinstance(methode, dict):
            return methode
        # => standard methode
        # in time import of the needed libs
        if methode == "allwaysPickle":
            # nothing to pre import 
            return {object:"pickle"}
        
        elif methode == "allwaysJoblib":
            import joblib
            return {object:"joblib"}
        
        elif methode == "pickle|joblib":
            import joblib, numpy, pandas
            return {object:"pickle", numpy.ndarray:"joblib",
                    pandas.DataFrame:"joblib"}
        
        elif methode == "pickle|numpy|pandas":
            import numpy, pandas
            return {object:"pickle", numpy.ndarray:"numpy",
                    pandas.DataFrame:"pandas"}
            
        else: raise ValueError(f"standard methode: {repr(methode)} isn't supported")

    def _preImport_compLib(self)->None:
        compLib:"_CompressionLib|None" = self.compressionLib
        if compLib is None: 
            return
        if compLib in ("bz2", "bzip2", "lz4", "lzma"):
            __import__(compLib)
        # => other libs don't need pre import



### ObjectSaver definition
   
## infos about storing dfs at
# https://tech.blueyonder.com/efficient-dataframe-storage-with-apache-parquet/
# https://towardsdatascience.com/the-best-format-to-save-pandas-data-414dca023e0d
## infos about lz4:
# https://lz4.org/

class ObjectSaver(Generic[_T_Savable]):
    _Filename_prefix = "__SaveModuleFile_"
    
    def __init__(self, 
            value:"_T_Savable", saveCompressed:bool=False, 
            session:"Session|None"=None, savingArgs:"SaveArgs|None"=None) -> None:
        self.__value:"_T_Savable|_Unsetted" = value
        self.__type:"type[_T_Savable]" = type(self.__value)
        self.__saveState:bool = False
        
        
        self.__session:Session
        self.__filePath:Path
        self.__setSession(session)
        self.__savingArgs:"SaveArgs"
        if savingArgs is None: 
            self.__savingArgs = self.__session.savingArgs
        else: self.__savingArgs = savingArgs
            
        
        
    
    @property
    def value(self)->"_T_Savable":
        if self.__saveState is True:
            self.load()
        if not isinstance(self.__value, self.__type):
            raise TypeError(
                "something whent wrong: got self.__value "
                f"of type {type(self.__value)} insted of {self.__type}"
            )
        return self.__value
    
    
    def setValue(self, newValue:"_T_Savable")->None:
        """set the new value, if it was saved, it is now considered as loaded\n
        don't interact with the disk"""
        if not isinstance(newValue, self.__type):
            raise TypeError(
                "something whent wrong: got `newValue` "
                f"of type {type(newValue)} insted of {self.__type}"
            )
        self.__saveState = False
        self.__value = newValue
        self.__type = type(newValue)
    
    @property
    def valueType(self)->"type[_T_Savable]":
        return self.__type

    @property
    def filePath(self)->"Path":
        return self.__filePath
    
    def isSaved(self)->bool:
        return self.__saveState
    
    def __genFilePath(self)->Path:
        """determine the filename and assemble with the directory\\
        the generated filename should remain the same during the run"""
        fileName:str = f"{self._Filename_prefix}{self.__session.allocate_unique_id()}"
        return self.__session.directory.joinpath(fileName)


    def load(self, force:bool=False)->None:
        """load the data from the disk if it was saved"""
        if (self.__saveState is False) and (force is False):
            return # alredy loaded, nothing to do
        # => (force is True) or (self.__saveState is True)
        self.__value = self.__savingArgs.load(
            self.__filePath, self.__type)
        self.__saveState = False
    
    def save(self, force:bool=False)->None:
        """save the data to the disk if it wasn't saved"""
        if (self.__saveState is True) and (force is False):
            return # alredy loaded, nothing to do
        # => (force is True) or (self.__saveState is False)
        self.__savingArgs.save(self.__filePath, self.__value)
        self.__value = _unsetted
        self.__saveState = True
    
    def unLoad_noSave(self)->None:
        """release the object in memory, without saving it (but will get marked as saved)\\
        (it need to be saved once, in or it will crash when loading)"""
        self.__value = _unsetted
        self.__saveState = True
    
    def clean(self, _force:bool=False)->bool:
        """clean the file on the disk (if it exist and object is loaded)\n
        return true if it deleted a file, false otherwise"""
        if (self.__saveState is False) or (_force is True):
            if self.__filePath.exists() is True:
                os.remove(self.__filePath)
                return True
        return False
    
    def __str__(self)->str:
        return f"{self.__class__}({self.__type}, {'SAVED' if self.__saveState else 'LOADED'})"

    def __setSession(self, session:"Session|None")->None:
        """internal function to set the session"""
        self.__session = (Session.get_topSession() if session is None else session)
        self.__filePath = self.__genFilePath()
        self.__session.track_object(self)
        
    
    def changeSession(self, newSession:"Session|None")->None:
        """transfert the object from the current session to the `newSession`\n
        cause the object to be loaded, and the current file removed\n
        if the object was saved before, resave with the new session\n
        - do nothing if the current session is new session"""
        if self.__session is newSession:
            return # => same session
        wasSaved:bool = self.__saveState
        self.load()
        self.__session.untrack_object(self)
        self.__setSession(newSession)
        if wasSaved is True:
            self.save()
    
    def __enter__(self)->Self:
        self.load()
        return self
    def __exit__(self, *_)->None:
        self.save()
    
    
    def __del__(self)->None:
        """force to clean the file and untrack the object of the session"""
        self.clean(_force=True)
        self.__session.untrack_object(self)



### DictSaver definition


class DictSaver(MutableMapping, Generic[_KT, _T_Savable]):
    def __init__(self,
            __map:"MutableMapping[_KT, _T_Savable]",
            saveCompressed:bool=False, session:"Session|None"=None)->None:
        
        self.__map:"MutableMapping[_KT, ObjectSaver[_T_Savable]]" = {}
        self.__saveCompressed:bool = saveCompressed
        self.__session:Session = (Session.get_topSession() if session is None else session)
        
        for (key, value) in __map.items():
            self.__setitem__(key, value)
        
    ### MutableMapping implementation
    
    def __setitem__(self, __key:"_KT", __value:"_T_Savable")->None:
        if __key not in self.__map:
            self.__map[__key] = ObjectSaver(
                __value, saveCompressed=self.__saveCompressed,
                session=self.__session)
        else: # => set the new value
            self.__map[__key].setValue(__value)
    
    def __getitem__(self, __key:"_KT")->"_T_Savable":
        return self.__map[__key].value
    
    def __delitem__(self, __key:"_KT")->None:
        del self.__map[__key]
    
    def __contains__(self, __key:"_KT")->bool:
        # avoid the methode to mixin from __getitem__ (whitch loads the object)
        return self.__map.__contains__(__key)
    
    def __iter__(self)->"Iterator[_KT]":
        return iter(self.__map)

    def __len__(self)->int:
        return len(self.__map)

    def keys(self)->"list[_KT]":
        return list(self.__map.keys())

    def items(self,
            jitLoadSave:bool=False, preferUnload:bool=False,
            )->"Generator[tuple[_KT, _T_Savable], None, None]":
        for key, objSaver in self.__map.items():
            # auto load it 
            yield (key, objSaver.value)
            if jitLoadSave is False:
                # => 're-save' it
                if preferUnload is False:
                    objSaver.save()
                else: objSaver.unLoad_noSave()

    def values(self, 
            jitLoadSave:bool=False, preferUnload:bool=False,
            )->"Generator[_T_Savable, None, None]":
        for objSaver in self.__map.values():
            # alredy load it 
            yield objSaver.value
            if jitLoadSave is False:
                # => 're-save' it
                if preferUnload is False:
                    objSaver.save()
                else: objSaver.unLoad_noSave()

    ### specific methodes
    
    @overload 
    def getRaw(self, __key:"_KT", __default:"_T"=None)->"ObjectSaver[_T_Savable]|_T": ...
    @overload 
    def getRaw(self, __key:"_KT",  __default:"ObjectSaver[_T_Savable]")->"ObjectSaver[_T_Savable]": ...
    def getRaw(self, __key:"_KT", __default:"ObjectSaver[_T_Savable]|_T"=None)->"ObjectSaver[_T_Savable]|_T":
        return self.__map.get(__key, __default)

    def save(self, *__keys:"_KT")->None:
        """call .save() on the ObjectSaver at the given keys\n
        when empty save all"""
        _keys:"Iterable[_KT]" = __keys
        if len(__keys) == 0:
            # => all keys
            _keys = self.__map.keys()
        for key in _keys:
            self.__map[key].save()
    
    def load(self, *__keys:"_KT")->None:
        """call .load() on the ObjectSaver at the given keys\n
        when empty save all"""
        _keys:"Iterable[_KT]" = __keys
        if len(__keys) == 0:
            # => all keys
            _keys = self.__map.keys()
        for key in _keys:
            self.__map[key].load()

