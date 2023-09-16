from __future__ import annotations
from pathlib import Path
from setuptools import setup, Extension
from Cython.Build import cythonize
import os
import sys
import shutil

############## HELP ##############
# (debug files remain) $python ./setup.py build_ext 
# (only *.pyd/.so remain): $python -OO ./setup.py build_ext 


DEP_FILES:bool; ANNOTATE:bool; FORCE:bool; DEBUG:bool
OPTIMIZE:str; USE_ASSERTS:bool; DEL_GENERATED_FILES:bool

if __debug__: # debug
    DEP_FILES = True
    ANNOTATE = True
    FORCE = False
    DEBUG = True
    OPTIMIZE = ("/Od" if sys.platform == "win32" else "-O0")
    USE_ASSERTS = True
    DEL_GENERATED_FILES = False

else: # release
    DEP_FILES = False
    ANNOTATE = False
    FORCE = True
    DEBUG = False
    OPTIMIZE = ("/O2" if sys.platform == "win32" else "-O3")
    USE_ASSERTS = False
    DEL_GENERATED_FILES = True


SRC_DIR = Path(".")
modulesToCompile:dict[str, Path] = {
    moduleName : \
        SRC_DIR.joinpath(f"{moduleName}.pyx")
    for moduleName in [
        "pyx_datatypes", "pyx_reader",
    ]
}
extra_compile_args:list[str] = [OPTIMIZE, ]
if USE_ASSERTS is False:
    extra_compile_args.append("-DCYTHON_WITHOUT_ASSERTIONS")

ext_modules = [
    Extension(
        moduleName, [modulePath.as_posix()], 
        include_dirs=["."], 
        extra_compile_args=extra_compile_args
    ) for (moduleName, modulePath) in modulesToCompile.items()
]

setup(
    include_dirs=[SRC_DIR.as_posix()],
    ext_modules = cythonize(
        ext_modules, #modulesToCompile,
        annotate=ANNOTATE, depfile=DEP_FILES, 
        force=True, show_all_warnings=False, gdb_debug=DEBUG),
    options={"build_ext": {"build_lib": SRC_DIR.as_posix()}},
)

### clean the generated files
if DEL_GENERATED_FILES is True:
    #clean the *.[c, c.dep, html] files
    print("cleaning *.c files")
    for (moduleName, modulePath) in modulesToCompile.items():
        for extention in (".c", ".c.dep", ".html"):
            moduleGeneratedFile:str = \
                modulePath.as_posix().replace(".pyx", extention)
            if os.path.exists(moduleGeneratedFile):
                os.remove(moduleGeneratedFile)


    # clean the build and debug
    print("cleaning build dir")
    if os.path.exists("./build"):
        shutil.rmtree("./build")
    
    print("cleaning debug dir")
    if os.path.exists("./cython_debug"):
        shutil.rmtree("./cython_debug")