from collections.abc import Callable, Iterable, Mapping
import os, os.path
import threading
import time
import weakref
import gc
from pathlib import Path
import pickle



from holo.__typing import (
    Generic, Iterator, TypeVar, Generator,
    Self, MutableMapping, Iterable, Tuple,
    LiteralString, Literal, overload, TypeAlias,
    TYPE_CHECKING, Dict,
)
from holo.protocols import (
    SupportsFileWrite, SupportsFileRead, 
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

_CompressionLib = Literal["lz4", "lzma", "bz2", "bzip2", "lzo", "blosc", "zlib", "blosc:lz4"]
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
_SaveLibExt = Literal["__other__", "pickle", "numpy", "pandas", "joblib"]

_CustomMethodes:TypeAlias = Dict[type, _SaveLib]
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

_CompressionTuple = Tuple[_CompressionLib, int]

_CustomCompression:TypeAlias = "dict[_SaveLibExt|tuple[_SaveLib, type], _CompressionTuple]"

### consts

SESSION_UPDATE_AFTER:int = 1*60 # update the session every 1min
SESSION_DELETE_AFTER:int = 5*60 # NOTE: /!\ an un-updated session for 5min is deleted
FILENAME_SESSION_INFOS:str = "session.txt"

SAVEMODULE_DIRECTORY:Path = Path(os.environ["TEMP"]).joinpath(".SaveModule/")

CONST_PANDAS_HDF_KEY = "DF"

ALLOWED_CompressionLibs:"dict[_SaveLibExt, set[_CompressionLib]]" = {
    "__other__": {"lz4", "bz2", "bzip2", "lzma"},
    "pandas": {"blosc:lz4", "lzo", "bzip2", "blosc", "zlib"},
}

_unsetted = _Unsetted() # create its unique instance


### general funcs

def copyStr(string:str)->str:
    return "".join(string)

def cleanFile_if_exist(filePath:str)->None:
    """function to finalize ObjectSaver"""
    if os.path.lexists(filePath) is True:
        os.remove(filePath)

### Session definition

class SessionsCleaner(threading.Thread):
    def __init__(self, start:bool=False) -> None:
        super().__init__(daemon=True)
        self.__paused:bool = False
        # TODO: sys d'historique des acctions
        # => no print mais quand meme accesible
        if start is True:
            self.start()
    
    def clean_old_sessions(self, directorys:"list[Path]")->None:
        for directory in (directorys + [SAVEMODULE_DIRECTORY]):
            for sessionDirPath in directory.iterdir():
                #print(f"treating: {sessionDirPath.as_posix()} ...", end=None)
                if sessionDirPath.is_dir() is False:
                    #print(f" => not a dir")
                    continue # => not a dir => not a session
                
                # try to get the session's file
                try: 
                    with open(sessionDirPath.joinpath(FILENAME_SESSION_INFOS), mode='r') as sessionFile:
                        sessionFile_content = sessionFile.read()
                except PermissionError:
                    #print(f" => PermissionError")
                    continue # => file is being accessed => session is running
                except FileNotFoundError:
                    #print(f" => FileNotFoundError")
                    continue # => no session file => not a session or not yet created
                
                # read the session's file
                sessionLastUpdate:float = float(sessionFile_content)
                if (time.time() - sessionLastUpdate) > SESSION_DELETE_AFTER:
                    #print(f" => cleaning it")
                    # => session is too old => delete it
                    for sessionsFiles in sessionDirPath.iterdir():
                        #print(f" -> removing {sessionsFiles.name}")
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
        while True:
            try:
                while self.__paused is True:
                    print("here paused")
                    time.sleep(0.1) # => sleep a few moments
                
                # => update each session
                sessionsHolderDirs:"list[Path]" = []
                session:"Session|None"
                for sessionRef in Session.sessionsHierarchy:
                    session = sessionRef()
                    if (session is None) or (session.wasCleaned is True):
                        continue # => session is dead
                    # => updating the session
                    session.update_session()
                    session.clean_forgoten_objects()
                    sessionsHolderDirs.append(session.directory.parent)
                self.clean_old_sessions(sessionsHolderDirs)
                del sessionsHolderDirs
                time.sleep(SESSION_UPDATE_AFTER) # update every

            except Exception as err:
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
            compression:"_CompressionTuple|_CustomCompression|None"=None,
            methode:"_StandardMethodes|_CustomMethodes"="allwaysPickle")->None:
        self.compression:"_CompressionTuple|_CustomCompression|None" = compression
        self.methode:"_CustomMethodes" = SaveArgs._stdMethode_to_custom(methode)
        self._preImport_compLib()
    
    def getCompressionTuple(self, objectType:type, useLib:"_SaveLib|None"=None)->"_CompressionTuple|None":
        if self.compression is None:
            return None
        elif isinstance(self.compression, tuple):
            return self.compression
        # => custom
        if useLib is None: # => auto
            useLib = self.getSaveLib(objectType)
        # => useLib is defined
        narrowestType:"type|None" = None
        narrowestCompTuple:"_CompressionTuple|None" = None
        fromOther:bool = False
        for saveLib, compTuple in self.compression.items():
            if isinstance(saveLib, tuple):
                # => custom compTuple
                (saveLib, keyType) = saveLib
                if (saveLib == useLib) and issubclass(objectType, keyType) \
                        and ((narrowestType is None) or issubclass(keyType, narrowestType)):
                    # => correct saveLib, correct type, narrower
                    narrowestType = keyType
                    narrowestCompTuple = compTuple
            else: # => generic compTuple
                if ((saveLib == useLib) and ((narrowestCompTuple is None) or (fromOther is True))) \
                        or ((saveLib == "__other__") and (fromOther is False)): 
                    # => correct saveLib, not setted yet => set the default
                    fromOther = (saveLib == "__other__")
                    narrowestCompTuple = compTuple
        #print(f"{objectType} -> {narrowestCompTuple}")
        return narrowestCompTuple
    

    def save(self, filePath:Path, obj:object)->None:
        useLib:"_SaveLib" = self.getSaveLib(type(obj))
        fileNormal:"SupportsFileWrite[bytes]"
        fileHdf:"pandas.HDFStore" # TODO: use with insted of .close()
        objectType:type = type(obj)
        if useLib == "pickle":
            with self.getFile(filePath, objectType, useLib, 'w') as fileNormal:
                pickle.dump(obj=obj, file=fileNormal, protocol=-1)
            fileNormal.close()
        elif useLib == "numpy":
            import numpy
            with self.getFile(filePath, objectType, useLib, 'w') as fileNormal:
                numpy.save(arr=obj, file=fileNormal, allow_pickle=True)
            fileNormal.close()
        elif useLib == "pandas":
            import pandas
            with self.getFile(filePath, objectType, useLib, 'w') as fileHdf:
                assert isinstance(obj, pandas.DataFrame), \
                    TypeError(f"in order to save an object with lib: {useLib}"
                            f"the object needs to be an instance of {pandas.DataFrame}")
                obj.to_hdf(fileHdf, CONST_PANDAS_HDF_KEY)
        elif useLib == "joblib":
            import joblib
            with self.getFile(filePath, objectType, useLib, 'w') as fileNormal:
                joblib.dump(obj, fileNormal, protocol=-1)
            fileNormal.close()
        else: raise ValueError(f"the lib: {useLib} isn't supported")
        # => saved the object
        
    def load(self, filePath:Path, objectType:"type[_T]")->"_T":
        useLib:"_SaveLib" = self.getSaveLib(objectType)
        fileNormal:"SupportsFileRead[bytes]"
        filePickle:"SupportsPickleRead"
        fileHdf:"pandas.HDFStore"
        if useLib == "pickle":
            with self.getFile(filePath, objectType, useLib, 'r') as filePickle:
                obj = pickle.load(file=filePickle)
        elif useLib == "numpy":
            import numpy
            with self.getFile(filePath, objectType, useLib, 'r') as fileNormal:
                obj = numpy.load(file=fileNormal, allow_pickle=True)
        elif useLib == "pandas":
            import pandas
            with self.getFile(filePath, objectType, useLib, 'r') as fileHdf:
                obj = pandas.read_hdf(fileHdf, CONST_PANDAS_HDF_KEY)
        elif useLib == "joblib":
            import joblib
            with self.getFile(filePath, objectType, useLib, 'r') as fileNormal:
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
    def getFile(self, 
            filePath:Path, objectType:type, saveLib:"Literal['pandas']",
            mode:"Literal['r','w']")->"pandas.HDFStore": ...
    @overload
    def getFile(self, 
            filePath:Path, objectType:type, saveLib:"Literal['pickle']",
            mode:"Literal['r']")->"SupportsPickleRead": ...
    @overload
    def getFile(self, 
            filePath:Path, objectType:type, saveLib:"_SaveLib",
            mode:"Literal['r']")->"SupportsFileRead[bytes]": ...
    @overload
    def getFile(self, 
            filePath:Path, objectType:type, saveLib:"_SaveLib",
            mode:"Literal['w']")->"SupportsFileWrite[bytes]": ...
    def getFile(self, 
            filePath:Path, objectType:type, saveLib:"_SaveLib", mode:"Literal['r', 'w']",
            )->"SupportsFileWrite[bytes]|SupportsFileRead[bytes]|pandas.HDFStore|SupportsPickleRead":
        """not overloaded version"""
        compTuple = self.getCompressionTuple(objectType, useLib=saveLib)
        compLib:"_CompressionLib|None" = (None if compTuple is None else compTuple[0])
        compLevel:"int|None" = (None if compTuple is None else compTuple[1])
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
    
    def getAllCompLibs(self)->"list[_CompressionLib]":
        if self.compression is None:
            return []
        elif isinstance(self.compression, tuple):
            return [self.compression[0]]
        # => custom
        result:"list[_CompressionLib]" = []
        for (compLib, _) in self.compression.values():
            result.append(compLib)
        return result
    
    def getAllSaveLibs(self)->"list[_SaveLib]":
        return list(self.methode.values())
    
    def _preImport_compLib(self)->None:
        for compLib in self.getAllCompLibs():
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
            value:"_T_Savable", session:"Session|None"=None,
            savingArgs:"SaveArgs|None"=None)->None:
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

    def fileSize(self)->"int|None":
        """when saved return the size of the file, when not saved return None"""
        if self.__saveState is True:
            # => is saved
            return os.path.getsize(self.filePath)
        # => not saved
        return None
    
    def getSaveLib(self)->"_SaveLib":
        return self.__savingArgs.getSaveLib(self.__type)
    

### DictSaver definition


class DictSaver(MutableMapping, Generic[_KT, _T_Savable]):
    def __init__(self, __map:"MutableMapping[_KT, _T_Savable]", session:"Session|None"=None)->None:
        self.__map:"MutableMapping[_KT, ObjectSaver[_T_Savable]]" = {}
        self.__session:Session = (Session.get_topSession() if session is None else session)
        
        for (key, value) in __map.items():
            self.__setitem__(key, value)
        
    ### MutableMapping implementation
    
    def __setitem__(self, __key:"_KT", __value:"_T_Savable")->None:
        if __key not in self.__map:
            self.__map[__key] = ObjectSaver(
                __value, session=self.__session)
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

    def getAllFileSize(self)->"dict[_KT, int]":
        """return the size of all the objects that are saved"""
        result:"dict[_KT, int]" = {}
        for (key,  objSaver) in self.__map.items():
            fileSize = objSaver.fileSize()
            if fileSize is not None:
                result[key] = fileSize
        return result

    def getAllSaveLibs(self)->"dict[_KT, _SaveLib]":
        """return the size of all the objects that are saved"""
        result:"dict[_KT, _SaveLib]" = {}
        for (key,  objSaver) in self.__map.items():
            result[key] = objSaver.getSaveLib()
        return result







def benchMethode(
        directory:"Path|None"=None, nbPasses:int=1, 
        compressTuple:"_CompressionTuple|_CustomCompression|None"=None)->None:
    t0 = time.perf_counter()
    import numpy, joblib, pandas
    import lzma, lz4, bz2, zlib
    t1 = time.perf_counter()
    if (t1 - t0) > 0.25:
        print("imports done")
    del t0, t1
    
    from holo.profilers import Profiler
    from holo.prettyFormats import prettyPrint, prettyTime, prettyDataSizeOctes
    import random
    
    def prettyProfTimes(prof:Profiler)->None:
        prettyPrint(prof.avgTimes(), specificFormats={float: prettyTime})
    
    profGeneral = Profiler([
        "create obj1", "create obj2", "create obj3",
    ])
    
    profMethodeObj1 = Profiler([
        "allwaysPickle (save)", "allwaysPickle (load)",
        "pickle|numpy|pandas (save)", "pickle|numpy|pandas (load)",
        "allwaysJoblib (save)", "allwaysJoblib (load)",
        "pickle|joblib (save)", "pickle|joblib (load)",
    ])
    profMethodeObj1_dict = profMethodeObj1.copy()
    profMethodeObj2 = profMethodeObj1.copy()
    profMethodeObj2_dict = profMethodeObj1.copy()
    profMethodeObj3 = profMethodeObj1.copy()
    
    filesSizes:"dict[LiteralString, dict[_StandardMethodes, int|None]]" = {
        "obj1":{}, "obj2":{}, "obj3":{}, "obj1_dict":{}, "obj2_dict":{}}
    objsSaveLibs:"dict[LiteralString, dict[_StandardMethodes, _SaveLib]]" = {
        "obj1":{}, "obj2":{}, "obj3":{}, "obj1_dict":{}, "obj2_dict":{}}
    
    def firstVal(__v:"dict[str, _T]")->"_T":
        return next(iter(__v.values()))
    N:int = 10_000
    
    def badNumpyRandomArray(shape:"tuple[int, ...]")->numpy.ndarray:
        rawArray = numpy.random.randint(low=0, high=2**64-1, size=shape, dtype="uint64")
        rawArray = rawArray % (2 ** 32)
        return numpy.ndarray(shape, dtype="float16", buffer=rawArray)
    
    with profGeneral.mesure("create obj1"):
        obj1:"dict[str, numpy.ndarray]" = {
            "X": badNumpyRandomArray((N, 50, 50)),
            "Y": badNumpyRandomArray((N, 1, 50)),
        }
    
    with profGeneral.mesure("create obj2"):
        obj2:"dict[str, pandas.DataFrame]" = {
            f"df n°{i}": pandas.DataFrame({
                    f"col n°{i}": \
                        badNumpyRandomArray((N, ))
                    for i in range(80)
                })
            for i in range(15)
        }
    
    with profGeneral.mesure("create obj3"):
        obj3:"list[tuple[bool, int]]" = [
            (bool(random.randint(0, 1)), random.randint(0, 2**32))
            for _ in range(N)
        ]
    for methode in ("allwaysPickle", "pickle|numpy|pandas", "allwaysJoblib"):
        with Session(savingArgs=SaveArgs(methode=methode, compression=compressTuple)):
            categorie_save = f"{methode} (save)"
            categorie_load = f"{methode} (load)"
            assert profMethodeObj1.isCategorie(categorie_save)
            assert profMethodeObj1.isCategorie(categorie_load)
            
            for _ in range(nbPasses):
                # obj1
                saveObj1 = ObjectSaver(obj1)
                with profMethodeObj1.mesure(categorie_save):
                    saveObj1.save()
                filesSizes["obj1"][methode] = saveObj1.fileSize()
                objsSaveLibs["obj1"][methode] = saveObj1.getSaveLib()
                with profMethodeObj1.mesure(categorie_load):
                    saveObj1.load()
                del saveObj1
                saveDict1 = DictSaver(obj1)
                with profMethodeObj1_dict.mesure(categorie_save):
                    saveDict1.save()
                filesSizes["obj1_dict"][methode] = sum(saveDict1.getAllFileSize().values())
                objsSaveLibs["obj1_dict"][methode] = firstVal(saveDict1.getAllSaveLibs())
                with profMethodeObj1_dict.mesure(categorie_load):
                    saveDict1.load()
                del saveDict1
                
                # obj2
                saveObj2 = ObjectSaver(obj2)
                with profMethodeObj2.mesure(categorie_save):
                    saveObj2.save()
                filesSizes["obj2"][methode] = saveObj2.fileSize()
                objsSaveLibs["obj2"][methode] = saveObj2.getSaveLib()
                with profMethodeObj2.mesure(categorie_load):
                    saveObj2.load()
                del saveObj2
                saveDict2 = DictSaver(obj2)
                with profMethodeObj2_dict.mesure(categorie_save):
                    saveDict2.save()
                filesSizes["obj2_dict"][methode] = sum(saveDict2.getAllFileSize().values())
                objsSaveLibs["obj2_dict"][methode] = firstVal(saveDict2.getAllSaveLibs())
                with profMethodeObj2_dict.mesure(categorie_load):
                    saveDict2.load()
                del saveDict2

                # obj3
                saveObj3 = ObjectSaver(obj3)
                with profMethodeObj3.mesure(categorie_save):
                    saveObj3.save()
                filesSizes["obj3"][methode] = saveObj3.fileSize()
                objsSaveLibs["obj3"][methode] = saveObj3.getSaveLib()
                with profMethodeObj3.mesure(categorie_load):
                    saveObj3.load()
                del saveObj3
    
    print("general: ")
    prettyProfTimes(profGeneral)
    print()
    print("obj1 (ObjectSaver)")
    prettyProfTimes(profMethodeObj1)
    print()
    print("obj1 (DictSaver)")
    prettyProfTimes(profMethodeObj1_dict)
    print()
    print("obj2 (ObjectSaver)")
    prettyProfTimes(profMethodeObj2)
    print()
    print("obj2 (DictSaver)")
    prettyProfTimes(profMethodeObj2_dict)
    print()
    print("obj3 (ObjectSaver)")
    prettyProfTimes(profMethodeObj3)
    print()
    print("files sizes")
    prettyPrint(filesSizes, specificFormats={int: lambda a: prettyDataSizeOctes(a)})
    print()
    print("saves lib")
    prettyPrint(objsSaveLibs)

#benchMethode(nbPasses=1, compressTuple=None)
#benchMethode(nbPasses=1, compressTuple={"__other__":("lz4", 0), "pandas":("blosc", 0)})
#benchMethode(nbPasses=1, compressTuple={"__other__":("lz4", 3), "pandas":("blosc", 3)})
#benchMethode(nbPasses=1, compressTuple={"__other__":("lz4", 9), "pandas":("blosc", 9)})
