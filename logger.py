import sys
import time
from pathlib import Path
from datetime import datetime

from holo.__typing import Union, TextIO, Literal

FULL_TIME_FORMAT = "%d/%m/%Y %H:%M:%S"
HOUR_TIME_FORMAT = "%H:%M:%S"

_WritersNames = Literal['stderr', 'stdout']

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
            if datetime.fromtimestamp(self.__timeLastInfos).day != datetime.today().day:
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

    def __del__(self)->None:
        if (self.copyFile is not None) and (self.copyFile.closed is False):
            self.copyFile.close()

class Logger():
    def __init__(self,
            filePath:"str|Path", encoding:"str|None"=None,
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
