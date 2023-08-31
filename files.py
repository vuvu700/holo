import os
import shutil
from pathlib import Path
from io import StringIO as _StringIO
import random as _random

from holo.__typing import (
    Literal, NamedTuple, Generator, Callable,
    DefaultDict, Iterable, TypeAlias, Union,
)
from holo.protocols import SupportsRichComparison
                           
StrPath: TypeAlias = Union[str, Path]

def combinePaths(*args:"StrPath")->str:
    if len(args) == 0:
        raise IndexError("args is empty, no paths to combine")
    path:"Path" = Path(args[0])
    for index in range(1, len(args)):
        path = path.joinpath(args[index])
    return path.as_posix()




def getSize(path:str, endswith:"str|None"=None, maxDepth:int=-1, checkPermission:bool=True)->int:
    """return the size in octes of the tageted `path`\n
    the `path` can be either a directory or a single file\n
    it is calculated recursivly for directories\n
    `endswith` will only sum the size of files ending with it (default: no filter)\n
    `maxDepth` is a limite of the depth to search (negative values -> no limites)\n
    `checkPermission` when True, it will skip when a permission error hapend
    otherwise the exception is raised"""
    try:
        if os.path.isfile(path):
            size = os.path.getsize(path)
            if (endswith is not None) and (not path.endswith(endswith)):
                return 0
            return size

        elif maxDepth != 0:
            summed_size = 0
            path = path.replace("\\","/")

            for subPath in  os.listdir(path):
                summed_size += getSize(combinePaths(path, subPath), endswith, maxDepth-1)
            return summed_size
        else: return 0

    except PermissionError as error:
            if checkPermission is False:
                raise error
            return 0

def getFilesInfos(
        directory:Path, maxDepth:"int|None"=None, checkPermission:bool=True, 
        ordered:"bool|Callable[[os.DirEntry], SupportsRichComparison]"=False)->"Generator[os.DirEntry, None, None]":
    """create a generator that reccursively yield the infos about the files\n
    `directory` : Path, where to search\n
    `maxDepth` : int|None, the maximum reccursive depth allowed, \
        positive interger (0 -> current dir) or None (never stop)\n
    `checkPermission` : bool, wether it will \
        skip it when acces is not allowed, or raise an error\n
    `ordered` : bool|Callable[[os.DirEntry], bool], wether it will sort the files \
        True -> by name, Callable -> custom\n
    """
    # determine next maxDepth
    nextDepth:"int|None"
    if maxDepth is None: nextDepth = None
    elif (maxDepth < 0): return # max depth reached
    else: nextDepth = maxDepth-1
    
    # try determine the elements in the targeted directory
    try: allElements:"Iterable[os.DirEntry]" = os.scandir(directory)
    except:
        if checkPermission is True: return
        raise # when checkPermission is False => fail on bad permission

    # if asked order the elements
    if ordered is True: # default => sort by name
        ordered = lambda elt: elt.name
    if ordered is not False:
        allElements = sorted(allElements, key=ordered)
    
    # yield the files  and  yield form the dirs
    for element in allElements:
        elementPath:Path = directory.joinpath(element.name)
        if element.is_symlink(): continue # not a file, not supported
        elif element.is_file():
            yield element
        elif element.is_dir():
            yield from getFilesInfos(elementPath, maxDepth=nextDepth)
        else: continue # not supported


class ExtentionInfos(NamedTuple):
    extension: str
    nbFiles: int
    totalSize: int
    sizeProportion: float

def getSizeInfos(directory:Path, maxDepth:int=-1, checkPermission:bool=True)->"list[ExtentionInfos]":
    nbFiles:"dict[str, int]" = DefaultDict(lambda : 0)
    totalSize:"dict[str, int]" = DefaultDict(lambda : 0)
    for file in getFilesInfos(
            directory, maxDepth=maxDepth, ordered=False,
            checkPermission=checkPermission):
        extention:str =  "".join(Path(file.name).suffixes)
        nbFiles[extention] += 1
        totalSize[extention] += file.stat().st_size
    
    cummulatedTotalSize:int = sum(totalSize.values())
    return [
        ExtentionInfos(extention, nbFiles_, totalSize_, totalSize_/cummulatedTotalSize)
        for extention, nbFiles_, totalSize_
            in zip(nbFiles.keys(), nbFiles.values(), totalSize.values())
    ]




def correctDirPath(dirPath:str)->str:
    """take a path to the directory `dirPath` and aplies the folowing correction:
     - convert all backslash  to slashs
     - if the '/' is missing at the end -> add it,  \\
       (Warning: the returned path will now correspond to "`dirPath`/.")\n
     - if empty string, do nothing \n
    """
    if dirPath == "":
        return dirPath
    dirPath = dirPath.replace("\\", "/")
    if dirPath.endswith("/") is False: dirPath += '/'
    return dirPath


def correctFilename(filename:str, fileSystem:"str|None|Literal[False]"=None)->str:
    """check if the `filename` is valide regarding the `fileSystem` being used,
    raise an error if invalide\n
    ## Param :
    `fileSystem` must be :
     - a valide file system name, ("NTFS", "exFAT", "UNIX", ...) (full liste in the code, case sensitive),
     - None, determined by the os,
     - False, ignore\n
    """
    #raise NotImplementedError("not implemented yet")
    # determine `fileSystem`
    if fileSystem is False:
        return filename

    SUPORTED_FILESYSTEM = (
        "FAT8", "FAT12", "FAT16", "FAT32", "exFAT",
        "NTFS", "UNIX", "POSIX",
    )

    if fileSystem is None:
        try:
            fileSystem = {"nt":"NTFS", "posix":"UNIX"}[os.name]
        except:
            raise ValueError(f"unsuported auto fileSystem for the os: {os.name}")

    if isinstance(fileSystem, str):
        if fileSystem not in SUPORTED_FILESYSTEM:
            raise ValueError(f"unsuported fileSystem: {fileSystem}")
    else:
        raise TypeError(f"unsuported fileSystem's type: {type(fileSystem)}")

    if fileSystem == "NTFS":
        ...
    elif fileSystem == "UNIX":
        ...
    elif fileSystem == "POSIX":
        ...
    elif fileSystem == "exFAT":
        ...
    elif fileSystem == "FAT8":
        ...
    elif (fileSystem == "FAT12") or (fileSystem == "FAT16") or (fileSystem == "FAT32"):
        ...
    else: raise ValueError(f"the fileSystem: {fileSystem} will be suported but not implemented yet")

    return filename


def getParentDir(path:str)->str:
    """return the path to the parent directory of `path`, formated using correctDirPath"""
    newPath = os.path.dirname(path)
    if newPath == "":
        if path == "..":
            newPath = ".."
        else: # all `path` like '.', '', 'abcdef...'
            newPath = "."

    return correctDirPath(newPath)



def mkDirRec(directory:"StrPath")->None:
    """create (if necessary) the full directory's path asked"""
    Path(directory).mkdir(parents=True, exist_ok=True)


def get_subdirectorys(directory:"StrPath")->"list[str]":
    """return teh name of all the directorys insibe the targeted directory"""
    return [dirname for dirname in os.listdir(directory) if os.path.isdir(combinePaths(directory, dirname))]

def get_subfiles(directory:"StrPath")->"list[str]":
    """return teh name of all the directorys insibe the targeted directory"""
    return [filename for filename in os.listdir(directory) if os.path.isfile(combinePaths(directory, filename))]

def get_subfilesAndDirs(directory:"StrPath")->"list[str]":
    """return teh name of all the directorys insibe the targeted directory"""
    test = lambda path: (os.path.isfile(path) is True) or (os.path.isdir(path) is True)
    return [filename for filename in os.listdir(directory) if test(combinePaths(directory, filename))]


def get_unique_name(
        directory:"StrPath|None", onlyNumbers:bool=False,
        nbCharacters:"int|None"=16, randomChoice:bool=True,
        guidlike:bool=True, allowResize:bool=True,
        prefix:"str|None"=None, suffix:"str|None"=None,
        filter_dirnames:bool=True, filter_filename:bool=True)->str:
    """return a (valide) name for a sub directory at directory\n
    `onlyNumbers` will generate names only containing only numbers or with letters too\n
    `nbCharacters` int -> is the number of characters of the generated name, \
        if the number of characters need to be greater, the name will be longer,
        None -> minimize the size needed\n
    `randomChoice` whether to choose the smallest available or a random name \
        (may be less efficient when `allowResize` is True and the `directory` is realy filled)\n
    `guidlike` if toogled the name will contain '-' to split the name for better readability\n
    `allowResize` whether to resize to """
    _alphabet_num:"list[str]" = list("0123456789")
    _alphabet_alphanum:"list[str]" = _alphabet_num + list("abcdefghijklmnopqrstuvwxyz")
    _suffix_str:str = ("" if suffix is None else suffix)
    _prefix_str:str = ("" if prefix is None else prefix)
    def generate_name(nbCharacters:int, oldName:"str|None")->str:
        nonlocal alphabet
        if randomChoice is True:
            return "".join(_random.choices(alphabet, k=nbCharacters))
        elif oldName is None:
            return alphabet[0] * nbCharacters
        else: # => increment the old name
            # find the first character to modifie (due to the auto resize)
            new_name = _StringIO()
            retenue:bool = True # increment the current => retnue at index 0
            nbChars:int = len(alphabet)
            alphabet_reverse_table:"dict[str, int]" = {char:index for index, char in enumerate(alphabet)}
            for char in oldName:
                if retenue is True:
                    new_index:int = (alphabet_reverse_table[char] + 1) % nbChars
                    char = alphabet[new_index]
                    if new_index > 0: retenue = False # (new_index == 0) => (retrnue on next)
                new_name.write(char)
            return new_name.getvalue()

    alphabet:"list[str]" = (_alphabet_num if onlyNumbers is True else _alphabet_alphanum)

    #from time import perf_counter
    #t0 = perf_counter()
    currently_used_names:"set[str]" = set()
    if directory is not None:
        if (filter_dirnames is True) and (filter_filename is True):
            currently_used_names = set(get_subfilesAndDirs(directory))
        elif filter_dirnames is True: # => (filter_filename is False)
            currently_used_names = set(get_subdirectorys(directory))
        elif filter_filename is True: # => (filter_dirnames is False)
            currently_used_names = set(get_subfiles(directory))
        else: # => (filter_dirnames is False) and (filter_filename is False)
            pass # => empty set

    use_nbCharacters:int
    if nbCharacters is None:
        use_nbCharacters = (max(map(len, currently_used_names)) if allowResize is False else 1)
        # 1 => will be resized to minimal value
    else: use_nbCharacters = nbCharacters
    #t1 = perf_counter()


    ### resize to ensure a name will be generatable
    if allowResize is True:
        _counts_per_length:dict[int, int] = {}
        for used_dirnames in currently_used_names:
            size:int = len(used_dirnames)
            _counts_per_length[size] = _counts_per_length.get(size, 0) + 1
            del used_dirnames, size

        size:int = 1
        while _counts_per_length.get(size, 0) >= (0.95 * (len(alphabet) ** size)): # 0.95 to find valide names faster
            size += 1
        use_nbCharacters = max(use_nbCharacters, size)
        del _counts_per_length, size
    #t2 = perf_counter()


    # generate a name available
    name:str = generate_name(use_nbCharacters, oldName=None)
    while (_prefix_str + name + _suffix_str) in currently_used_names:
        name =generate_name(use_nbCharacters, oldName=name)
    #t3 = perf_counter()

    ### applie GUID like property
    if guidlike is True:
        new_name = _StringIO()
        for index, char in enumerate(name):
            if ((index % 4) == 0) and (index != 0):
                new_name.write("-")
            new_name.write(char)
        name = new_name.getvalue()

    #t4 = perf_counter()
    #print(f"{t1-t0:.4f}s, {t2-t1:.4f}s, {t3-t3:.4f}s, {t4-t3:.4f}s")

    return (_prefix_str + name + _suffix_str)


def copyTree(src:"StrPath", dst:"StrPath", dirs_exist_ok:bool=True)->None:
    # code very inspired from shutil.copytree
    names = os.listdir(src)

    os.makedirs(dst, exist_ok=dirs_exist_ok)
    for name in names:
        srcname = os.path.join(src, name)
        dstname = os.path.join(dst, name)
        if os.path.islink(srcname):
            raise OSError(f"the copy of symlink is not supported")
        elif os.path.isdir(srcname):
            copyTree(srcname, dstname, dirs_exist_ok=dirs_exist_ok)
        else: # => srcname is a file
            shutil.copy2(srcname, dstname)
    
    shutil.copystat(src, dst)
