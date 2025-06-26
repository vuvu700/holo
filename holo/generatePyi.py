from mypy import stubgen
from pathlib import Path
import shutil, os

from .files import copyTree
from .__typing import NamedTuple, Union

class ModuleExport(NamedTuple):
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


class PackageExport(NamedTuple):
    packageName: str
    moduleDir: Path
    exportDirs: "list[Path]"

    @property
    def packageFullPath(self)->Path:
        return self.moduleDir.joinpath(self.packageName)
    
    def get_interfacesExports(self)->"list[Path]":
        return [destinationDir.joinpath(self.packageName) for destinationDir in self.exportDirs]


Exports = Union[ModuleExport, PackageExport]


def main(exportsList:"list[Exports]", workingDir:Path, removeCache:bool=True, removeTemporaryInterfaces:bool=True):
    TEMPORARY_PYI_DIR = workingDir.joinpath("tmp-pyi-dir") # use - to avoid being a package
    
    ### generate all the pyi in the temporary dir
    allModulesToConvert:list[str] = [
        (export.moduleFullPath if isinstance(export, ModuleExport) \
            else export.packageFullPath).as_posix()
        for export in exportsList
    ]
    stubgen.main(["-o", TEMPORARY_PYI_DIR.as_posix(), "--include-private", "--ignore-errors", *allModulesToConvert])
    # has exited if there is was probleme 

    # copy them at the correct path
    for export in exportsList:
        interfacePath:Path; destination:Path
        
        if isinstance(export, ModuleExport):
            interfacePath = TEMPORARY_PYI_DIR.joinpath(export.interfaceFileName)
            for destination in export.get_interfacesExports():
                shutil.copyfile(interfacePath, destination)
            os.remove(interfacePath)
            
        elif isinstance(export, PackageExport):
            interfacePath = TEMPORARY_PYI_DIR.joinpath(export.packageName)
            for destination in export.get_interfacesExports():
                copyTree(interfacePath, destination)
            shutil.rmtree(interfacePath)
            
        else: raise TypeError(f"unsupported export type: {type(export)}")
    
    # remove the temp dir (if empty)
    if removeTemporaryInterfaces is True:
        try: os.rmdir(TEMPORARY_PYI_DIR)
        except OSError: pass # => the dir wasn't empty (some external files remaining)

    # remove the mypy cache
    if removeCache is True:
        shutil.rmtree(Path(os.getcwd()).joinpath(".mypy_cache"))
    