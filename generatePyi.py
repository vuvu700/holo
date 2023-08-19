from mypy import stubgen
from pathlib import Path
from typing import NamedTuple
import shutil, os

class Export(NamedTuple):
    moduleName: str
    moduleDir: Path
    exportDirs: "list[Path]"

    @property
    def moduleFileName(self)->str:
        return f"{self.moduleName}.py"
    @property
    def moduleFullPath(self)->Path:
        return self.moduleDir.joinpath(self.moduleFileName)
    
    @property
    def interfaceFileName(self)->str:
        return f"{self.moduleName}.pyi"
    def get_interfacesExports(self)->"list[Path]":
        return [destinationDir.joinpath(self.interfaceFileName) for destinationDir in self.exportDirs]


def main(exportsList:"list[Export]", workingDir:Path, removeCache:bool=True, removeTemporaryInterfaces:bool=True):
    TEMPORARY_PYI_DIR = workingDir.joinpath("tmp-pyi-dir") # use - to avoid being a package
    
    ### generate all the pyi in the temporary dir
    allModulesToConvert:list[str] = [export.moduleFullPath.as_posix() for export in exportsList]
    stubgen.main(["-o", TEMPORARY_PYI_DIR.as_posix(), "--include-private", "--ignore-errors", *allModulesToConvert])
    # has exited if there is was probleme 

    # copy them at the correct path
    for export in exportsList:
        interfacePath = TEMPORARY_PYI_DIR.joinpath(export.interfaceFileName)
        for destination in export.get_interfacesExports():
            shutil.copyfile(interfacePath, destination)
        if removeTemporaryInterfaces is True:
            os.remove(interfacePath)
    if removeTemporaryInterfaces is True:
        try: os.rmdir(TEMPORARY_PYI_DIR)
        except OSError: pass # the dir wasn't empty (some external files remaining)

    # remove the mypy cache
    if removeCache is True:
        shutil.rmtree(Path(os.getcwd()).joinpath(".mypy_cache"))
    