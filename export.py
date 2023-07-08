"""this script will export the holo module"""
from typing import Any, Generator, Iterable, NamedTuple, Union, overload
from typing_extensions import Literal, Self
from pathlib import Path
import os
import ast
import inspect

from holo import print_exception

HOLO_DIR:str = Path(__file__).parent.as_posix()
HOLO_SUB_MODULES:"list[str]" = os.listdir(HOLO_DIR)

_Import = Union[ast.Import, ast.ImportFrom]

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
    fullModules:"set[str]"
    partialModules:"dict[str, set[str]]"

    def simplify(self)->Self:
        """in-place simplify it (return itself)"""
        for module in set(self.partialModules.keys()).intersection(self.fullModules):
            self.partialModules.pop(module)
        for module in self.partialModules.keys():
            self.partialModules[module] = set(self.partialModules[module])
        return self

    def combine(self, otherImportsRequirements:"ImportsRequirements")->Self:
        """in-place combine (return itself)"""
        for fullModule in otherImportsRequirements.fullModules:
            self.fullModules.add(fullModule)

        for module, elements in otherImportsRequirements.partialModules.items():
            if module not in self.partialModules:
                self.partialModules[module] = set()
            for elt in elements:
                self.partialModules[module].add(elt)
        return self.simplify()
    
    def isEmpty(self)->bool:
        return (len(self.fullModules) == 0) and (len(self.partialModules) == 0)

    def allModules(self)->"set[str]":
        return self.fullModules.union(self.partialModules.keys())

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

def extractImports(node:ast.AST)->"Generator[_Import, None, None]":
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        yield node
    for subNode in ast.iter_child_nodes(node):
        yield from extractImports(subNode)



@overload
def getModuleName(
        moduleName:"str|None", directory:"str|Path",
        holoModulesOnly:"Literal[False]")->str: ...
@overload
def getModuleName(
        moduleName:"str|None", directory:"str|Path",
        holoModulesOnly:"bool")->"str|Literal[False]": ...

def getModuleName(
        moduleName:"str|None", directory:"str|Path",
        holoModulesOnly:bool)->"str|Literal[False]":
    """return the name of the module"""
    directory = Path(directory)
    dirName:str = directory.name
    dirNameDot:str = dirName + "."
    
    if moduleName is None: # from `.` import ...
        if (holoModulesOnly is True) and (pathIsInsideHoloDir(directory) is False):
            return False
        return "__init__"
    # else: => moduleName is an str

    if moduleName == dirName:
        return "__init__"
    if moduleName.startswith(dirNameDot):
        return moduleName[len(dirNameDot): ]
    
    
    if holoModulesOnly is True:
        if (pathIsInsideHoloDir(directory) is True) and (moduleName in HOLO_SUB_MODULES):
            return moduleName
        else: return False
    return moduleName

def extractModulesImports(
        imports:"Iterable[_Import]", directory:"str|Path",
        holoModulesOnly:bool, perFileImports:bool)->"ImportsRequirements":
    """return (list[name of the module], dict[name of the module -> list[element name]])"""
    fullModules:"set[str]" = set()
    importedElements:"dict[str, set[str]]" = {}
    moduleName:"str|Literal[False]"
    for node in imports:
        if isinstance(node, ast.Import):
            for alias in node.names:
                moduleName = getModuleName(alias.name, directory, holoModulesOnly)
                if moduleName is not False:
                    fullModules.add(moduleName)

        else: # => isinstance(node, ast.ImportFrom)
            moduleName = getModuleName(node.module, directory, holoModulesOnly)
            if moduleName is False: continue

            importedElements[moduleName] = set()
            for elementToImportFrom in node.names:
                importedElements[moduleName].add(elementToImportFrom.name)

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


@overload
def getImportsRequirements(
        directory:"str|Path", perFileImports:"Literal[False]", holoModulesOnly:bool=True,
        resolveDirectory:bool=False, skipParsFails:bool=False, printExceptions:bool=True)->"ImportsRequirements": ...
@overload
def getImportsRequirements(
        directory:"str|Path", perFileImports:"Literal[True]", holoModulesOnly:bool=True,
        resolveDirectory:bool=False, skipParsFails:bool=False, printExceptions:bool=True)->"dict[str, ImportsRequirements]": ...

def getImportsRequirements(
        directory:"str|Path", perFileImports:bool, holoModulesOnly:bool=True, resolveDirectory:bool=False,
        skipParsFails:bool=False, printExceptions:bool=True)->"dict[str, ImportsRequirements]|ImportsRequirements":
    if resolveDirectory is True:
        directory = Path(directory).resolve()
    
    listFilenames = getRecursivePythonFiles(directory)
    
    requirements:"dict[str, ImportsRequirements]" = {}
    for filename in listFilenames:
        try:
            getImports:"Generator[_Import, None, None]" = extractImports(
                ast.parse(getFileContent(filename), filename=filename),
            )
            requirements[filename] = extractModulesImports(getImports, directory, holoModulesOnly, perFileImports)

        except Exception as err:
            if printExceptions is True:
                print(f'Exception happend during: "{filename}"')
                print_exception(err, file="stdout")

            if isinstance(err, SyntaxError) and (skipParsFails is False): raise
    
    if perFileImports is True:
        return requirements
    
    # else => combine the results
    importsRequirements = ImportsRequirements(set(), {})
    for imports in requirements.values():
        importsRequirements.combine(imports)
    return importsRequirements
from holo.prettyFormats import prettyPrint
