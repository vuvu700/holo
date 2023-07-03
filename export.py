"""this script will export the holo module"""
from typing import Any, Generator, Iterable, NamedTuple
from typing_extensions import Literal, Self
from pathlib import Path
import os
import ast
import inspect

from holo import print_exception

HOLO_DIR:str = Path(__file__).parent.as_posix()
HOLO_SUB_MODULES:"list[str]" = os.listdir(HOLO_DIR)

def pathIsInsideHoloDir(path:"str|Path")->bool:
    if isinstance(path, str):
        path = Path(path)
    return (path.as_posix() == HOLO_DIR)

class Alias(NamedTuple):
    name:str
    alias:"str|None" = None

    @classmethod
    def fromAst(cls, node:ast.alias)->"Alias":
        return Alias(node.name, node.asname)

class ImportsRequirements(NamedTuple):
    fullModules:"list[str]"
    partialModules:"dict[str, list[str]]"

    def simplify(self)->Self:
        """in-place simplify it (return itself)"""
        for module in set(self.partialModules.keys()).intersection(self.fullModules):
            self.partialModules.pop(module)
        for module in self.partialModules.keys():
            self.partialModules[module] = list(set(self.partialModules[module]))
        return self

    def combine(self, otherImportsRequirements:"ImportsRequirements")->Self:
        """in-place combine (return itself)"""
        for fullModule in otherImportsRequirements.fullModules:
            self.fullModules.append(fullModule)

        for module, elements in otherImportsRequirements.partialModules.items():
            if module not in self.partialModules:
                self.partialModules[module] = []
            for elt in elements:
                self.partialModules[module].append(elt)
        return self.simplify()
    
    def isEmpty(self)->bool:
        return (len(self.fullModules) == 0) and (len(self.partialModules) == 0)


def exportAll(directory:str)->None:
    """`directory`:str is the directory where to export the holo module (must exist)"""
    ...

    
def getFileContent(fileName:str)->str:
    with open(fileName, mode="r") as file:
        content = file.read()
        if content.startswith("\xEF\xBB\xBF"):
            #print(f"corrected: {fileName}")
            return content[3: ]
        return content

def getFileContentOfNode(obj)->str:
    filePath:"str|None" = inspect.getsourcefile(obj)
    if filePath is None: return ""
    return getFileContent(filePath)


def astContentOfNode(node:ast.AST)->"dict[str, list[dict[str, Any]]]":
    result:"list[dict[str, Any]]" = []
    for name, field in ast.iter_fields(node):
        if isinstance(field, ast.AST):
            result.append({name: astContentOfNode(field)})

        elif isinstance(field, list):
            subListe = []
            for item in field:
                if isinstance(item, ast.AST):
                    subListe.append(astContentOfNode(item))
            result.append({name: subListe})

        else: # => a value
            result.append({name: field})

    return {node.__class__.__name__:result}

def extractImports(node:ast.AST)->"Generator[ast.Import|ast.ImportFrom, None, None]":
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        yield node
    for subNode in ast.iter_child_nodes(node):
        yield from extractImports(subNode)


def holoModule(moduleName:"str|None", directory:"str|Path")->"str|Literal[False]":
    """return the name of the module"""
    if moduleName is None: # from `.` import ...
        if pathIsInsideHoloDir(directory) is False:
            return False
        else: return "__init__"
    # else: => moduleName is an str

    if moduleName == "holo":
        return "__init__"
    if moduleName.startswith("holo."):
        return moduleName[len("holo."): ]
    if pathIsInsideHoloDir(directory) is True:
        if moduleName in HOLO_SUB_MODULES:
            return moduleName
    return False


def extractHoloModulesImports(
        imports:"Iterable[ast.Import|ast.ImportFrom]", directory:"str|Path")->"ImportsRequirements":
    """return (list[name of the module], dict[name of the module -> list[element name]])"""
    fullModules:"list[str]" = []
    importedElements:"dict[str, list[str]]" = {}
    holoModuleName:"str|Literal[False]"
    for node in imports:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if holoModule(alias.name, directory) is not False:
                    fullModules.append(alias.name)

        else: # => isinstance(node, ast.ImportFrom)
            holoModuleName = holoModule(node.module, directory)
            if holoModuleName is False: continue

            importedElements[holoModuleName] = []
            for elementToImportFrom in node.names:
                importedElements[holoModuleName].append(elementToImportFrom.name)

    return ImportsRequirements(fullModules, importedElements).simplify()

    
def getRecursivePythonFiles(directory:"str|Path")->"Iterable[str]":
    """return a list of all .py files inside the directory"""
    def internal(directory:Path)->"Generator[str, None, None]":
        for name in os.listdir(directory):
            nextPath = directory.joinpath(name)
            if nextPath.is_dir():
                yield from internal(nextPath)
            elif nextPath.is_file() and (nextPath.suffix == ".py"):
                yield nextPath.as_posix()
            else: pass

    if isinstance(directory, str): directory = Path(directory)
    return internal(directory)

def getAllHoloImportsRequirements(
        directory:"str|Path", skipParsFails:bool=False, printExceptions:bool=True)->ImportsRequirements:
    listFilenames = getRecursivePythonFiles(directory)

    importsRequirements = ImportsRequirements([], {})
    for filename in listFilenames:
        try:
            importsRequirements.combine(
                extractHoloModulesImports(extractImports(
                    ast.parse(getFileContent(filename), filename=filename),
                ), directory)
            )
        except Exception as err:
            if printExceptions is True:
                print(f'Exception happend during: "{filename}"')
                print_exception(err, file="stdout")

            if isinstance(err, SyntaxError) and (skipParsFails is False): raise
    return importsRequirements

def getPerFileHoloImportsRequirements(
        directory:"str|Path", skipParsFails:bool=False, printExceptions:bool=True)->"dict[str, ImportsRequirements]":
    listFilenames = getRecursivePythonFiles(directory)

    requirements = {}
    for filename in listFilenames:
        try:
            requirements[filename] = \
                extractHoloModulesImports(extractImports(
                    ast.parse(getFileContent(filename), filename=filename),
                ), directory)

        except Exception as err:
            if printExceptions is True:
                print(f'Exception happend during: "{filename}"')
                print_exception(err, file="stdout")

            if isinstance(err, SyntaxError) and (skipParsFails is False): raise
    return requirements