import sys
import time
from pathlib import Path
from datetime import datetime, timedelta
from io import TextIOWrapper

from .__typing import Union, TextIO, Literal, overload
from .files import StrPath

FULL_TIME_FORMAT = "%d/%m/%Y %H:%M:%S"
HOUR_TIME_FORMAT = "%H:%M:%S"

_WritersNames = Literal['stderr', 'stdout']


class _LoggerWriter(TextIO):
    def __init__(self, logFile:"TextIO", copyFile:"TextIO|None", level:str, 
                 newLogLineAfter:"timedelta"=timedelta(milliseconds=1))->None:
        self.logFile:"TextIO" = logFile
        self.copyFile:"TextIO|None" = copyFile
        self.level:str = level
        self.__timeLastWrite: datetime = datetime.min
        self.__timeLastInfos: datetime = datetime.min
        self.newLogLineAfter: timedelta = newLogLineAfter

    def timeSinceLastWrite(self)->timedelta:
        return datetime.now() - self.__timeLastWrite

    def timeSinceLastInfos(self)->timedelta:
        return datetime.now() - self.__timeLastInfos
    
    def writeLogsInfos(self)->None:
        currentTime: datetime = datetime.now()
        # determine logs infos to write
        
        if (self.timeSinceLastWrite() >= self.newLogLineAfter) \
                or (self.timeSinceLastInfos() > timedelta(seconds=1)):
            # needs to write new logs infos
            # select the format for the time
            timeFormat:str
            if self.__timeLastInfos.date() == currentTime.date() is False:
                timeFormat = FULL_TIME_FORMAT
            else: timeFormat =  HOUR_TIME_FORMAT
            
            # write the infos
            self.logFile.write(f"\n{time.strftime(timeFormat)} - {self.level} : \n")
            self.__timeLastInfos = currentTime
        self.__timeLastWrite = currentTime
    
    
    def write(self, message:str):
        """write the message, starting with some logging informations"""
        self.writeLogsInfos()
        if self.copyFile is not None:
            self.copyFile.write(message)
        self.logFile.write(message)

    def flush(self):
        self.logFile.flush()
        if self.copyFile is not None:
            self.copyFile.flush()


class Logger():
    def __init__(self,
            filePath:"StrPath", encoding:"str|None"=None, _noRePrint:"bool"=False, 
            newLogLineAfter:"timedelta"=timedelta(milliseconds=1), 
            fileOpenMode:"Literal['a', 'w']"='a', useBuffer:bool=True)->None:
        aux = lambda var, cond: None if cond else var
        self.file:"TextIO|None" = None # to avoid more errors in __del__
        self.file = open(filePath, mode=fileOpenMode, encoding=encoding, 
                         buffering=(-1 if useBuffer is True else 0))
        self.file.seek(0, 2) # got to the end of the log file
        self.logStdout:"_LoggerWriter" = _LoggerWriter(
            self.file, aux(sys.stdout, _noRePrint) , "INFO", newLogLineAfter)
        self.logStderr:"_LoggerWriter" = _LoggerWriter(
            self.file, aux(sys.stderr, _noRePrint), "ERROR", newLogLineAfter)

        sys.stderr = self.logStderr
        sys.stdout = self.logStdout


    def revert(self, writerName:"Union[_WritersNames, Literal['all']]")->None:
        if writerName in ("stderr", "all"):
            sys.stderr = self.logStderr.copyFile
        if writerName in ("stdout", "all"):
            sys.stdout = self.logStdout.copyFile

    def write(self, message:str, writerName:"_WritersNames"="stdout")->None:
        if writerName == "stderr":
            return self.logStderr.write(message)
        elif writerName == "stdout":
            return self.logStdout.write(message)
        else: raise ValueError(f"invalide wiriter name: {writerName}")

    def __del__(self):
        if self.file is not None:
            self.revert("all")
            if self.file.closed is False:
                self.file.close()

_Encoding = str
class LoggerContext():
    @overload # open file signature
    def __init__(self, file:"StrPath|tuple[StrPath, _Encoding]", *,
                 newLogLineAfter:"timedelta"=timedelta(milliseconds=1), 
                 fileOpenMode:"Literal['a', 'w']"='a', useBuffer:bool=True)->None:
        ...
    @overload # use file signature
    def __init__(self, file:"TextIOWrapper", *,
                 newLogLineAfter:"timedelta"=timedelta(milliseconds=1), useBuffer:bool=True)->None:
        ...
    def __init__(self, file:"StrPath|tuple[StrPath, _Encoding]|TextIOWrapper", 
                 *, newLogLineAfter:"timedelta"=timedelta(milliseconds=1),
                 fileOpenMode:"Literal['a', 'w']"='a', useBuffer:bool=True)->None:
        self.newLogLineAfter: timedelta = newLogLineAfter
        self.file:TextIO
        if isinstance(file, TextIOWrapper):
            self.file = file
        else: # => the path of the file to open is given 
            encoding:"str|None" = "utf-8" # don't use None to be consistant with the std...
            if isinstance(file, tuple):
                (file, encoding) = file
            self.file = open(file, mode=fileOpenMode, encoding=encoding,
                             buffering=(-1 if useBuffer is True else 0))
        self.logStdout:"_LoggerWriter|None" = None
        self.logStderr:"_LoggerWriter|None" = None
        
    def __enter__(self)->None:
        if (self.logStdout is not None) or (self.logStderr is not None):
            raise RuntimeError("the self.logStdout or self.logStderr is still opened")
        self.file.seek(0, 2) # got to the end of the log file
        self.logStdout = _LoggerWriter(self.file, sys.stdout , "INFO", self.newLogLineAfter)
        sys.stdout = self.logStdout
        self.logStderr = _LoggerWriter(self.file, sys.stderr, "ERROR", self.newLogLineAfter)
        sys.stderr = self.logStderr
    
    def __exit__(self, *_, **__)->None:
        if (self.logStdout is None) or (self.logStderr is None):
            raise RuntimeError("the self.logStdout or self.logStderr is not opened")
        sys.stdout = self.logStdout.copyFile
        self.logStdout = None
        sys.stderr = self.logStderr.copyFile
        self.logStderr = None
        
    def __del__(self):
        if self.file.closed is False:
            self.file.close()