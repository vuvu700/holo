import sys
import time
from pathlib import Path
from datetime import datetime
from io import TextIOWrapper

from holo.__typing import Union, TextIO, Literal
from holo.files import StrPath

FULL_TIME_FORMAT = "%d/%m/%Y %H:%M:%S"
HOUR_TIME_FORMAT = "%H:%M:%S"

_WritersNames = Literal['stderr', 'stdout']

def isSameDate(date1:datetime, date2:datetime)->bool:
    """return True if the two date are the same day"""
    return (date1.day == date2.day) \
        and (date1.month == date2.month) \
        and (date1.year == date2.year)

floatToDtime = datetime.fromtimestamp

class _LoggerWriter(TextIO):
    intervaleInfoText:float = 0.001
    
    def __init__(self, logFile:"TextIO", copyFile:"TextIO|None", level:str)->None:
        self.logFile:"TextIO" = logFile
        self.copyFile:"TextIO|None" = copyFile
        self.level:str = level
        self.__timeLastWrite:float = 0.0
        self.__timeLastInfos:float = 0.0

    @property
    def timeSinceLastWrite(self)->float:
        return time.time() - self.__timeLastWrite
    @property
    def timeSinceLastInfos(self)->float:
        return time.time() - self.__timeLastInfos
    
    def writeLogsInfos(self)->None:
        currentTime:float = time.time()
        # determine logs infos to write
        
        if (self.timeSinceLastWrite >= self.intervaleInfoText) or (self.timeSinceLastInfos > 1.0):
            # select the format for the 
            timeFormat:str
            if isSameDate(floatToDtime(self.__timeLastInfos), floatToDtime(currentTime)) is False:
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
            filePath:"StrPath", encoding:"str|None"=None,
            _noRePrint:"bool"=False)->None:
        aux = lambda var, cond: None if cond else var
        self.file:"TextIO|None" = None # to avoid more errors in __del__
        self.file = open(filePath, mode='a', encoding=encoding)
        self.file.seek(0, 2) # got to the end of the log file
        self.logStdout:"_LoggerWriter" = \
            _LoggerWriter(self.file, aux(sys.stdout, _noRePrint) , "INFO")
        self.logStderr:"_LoggerWriter" = \
            _LoggerWriter(self.file, aux(sys.stderr, _noRePrint), "ERROR")

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
    def __init__(self, file:"StrPath|tuple[StrPath, _Encoding]|TextIOWrapper")->None:
        self.file:TextIO
        if isinstance(file, TextIOWrapper):
            self.file = file
        else:
            encoding:"str|None" = None
            if isinstance(file, tuple):
                (file, encoding) = file
            self.file = open(file, mode='a', encoding=encoding)
        self.logStdout:"_LoggerWriter|None" = None
        self.logStderr:"_LoggerWriter|None" = None
        
    def __enter__(self)->None:
        if (self.logStdout is not None) or (self.logStderr is not None):
            raise RuntimeError("the self.logStdout or self.logStderr is still opened")
        self.file.seek(0, 2) # got to the end of the log file
        self.logStdout = _LoggerWriter(self.file, sys.stdout , "INFO")
        sys.stdout = self.logStdout
        self.logStderr = _LoggerWriter(self.file, sys.stderr, "ERROR")
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