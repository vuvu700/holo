from typing import Callable
import inspect

# possible modifications: use the types.FunctionType(...)
# to create the new func to return


def replace(replace_targets_with:"dict[str, str]", printNewFunc:bool=False)->"Callable[[Callable], Callable]":
    """it will replace all parts of your code,
    targeted by the keys of `replace_targets_with` with the corresponding item\n
    WARNING: this MUST be the first decorator to get called (closest to the "def ...")\n
    """
    if isinstance(replace_targets_with, Callable): # case when : "@replace \ndef foo():..."
        return replace_targets_with


    def _replace(func:Callable)->Callable:
        #def _replace(func):
        nonlocal replace_targets_with
        if not inspect.isfunction(func):
            raise TypeError(f"the `func`:{func} must be a function")

        # get the code
        func_code_text:str = inspect.getsource(func)

        # suprimer le replace de func_code
        index_funcDef_start:int = func_code_text.find(f"def {func.__name__}(") # wrong: spacing can be way more than 1
        func_code_text = func_code_text[index_funcDef_start: ] # restrein to the code after def, ignore decorators

        # replace the targets
        for (code_target, code_replace) in replace_targets_with.items():
            func_code_text = func_code_text.replace(code_target, code_replace)

        # for debuging purpose
        if printNewFunc:
            print(func_code_text)

        # set the new code for the function
        func.__code__ = compile(func_code_text, "<preproc>", 'exec') # here it is a module to create the func
        for const in func.__code__.co_consts:
            if isinstance(const, type(func.__code__)):
                func.__code__ = const # the code object of the new func
                break
        else:
            raise TypeError("no code found")


        return func#firstExec

    return _replace
