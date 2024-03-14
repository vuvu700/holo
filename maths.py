from holo.__typing import Iterable, Generic, overload, Literal
from holo.protocols import (
    SupportsMathAdd, SupportsMathMul, SupportsMathRing, 
    _T_MathAdd, _T_MathMul, _T_MathRing, _StrLiteral,
)

class ModuloRing(SupportsMathRing):
    __slots__ = ("__k", "__N")
    def __init__(self, k:int, N:int) -> None:
        self.__k:int = k % N
        self.__N:int = N
    
    def __add__(self, other:"ModuloRing|int")->"ModuloRing": ... # TODO
    def __iadd__(self, other:"ModuloRing|int")->"ModuloRing": ... # TODO
    def __sub__(self, other:"ModuloRing|int")->"ModuloRing": ... # TODO
    def __isub__(self, other:"ModuloRing|int")->"ModuloRing": ... # TODO
    def __mul__(self, other:"ModuloRing|int")->"ModuloRing": ... # TODO
    def __imul__(self, other:"ModuloRing|int")->"ModuloRing": ... # TODO
    def __pow__(self, other:"ModuloRing|int")->"ModuloRing": ... # TODO
    def __ipow__(self, other:"ModuloRing|int")->"ModuloRing": ... # TODO
    def __div__(self, other: "ModuloRing|int")->"ModuloRing": ... # TODO
    def __idiv__(self, other: "ModuloRing|int")->"ModuloRing": ... # TODO




class Monomial(Generic[_T_MathRing]):
    """also called power product, represent an expression like: (-7 * X^2 * Y^4)"""
    @overload
    def __init__(self, *, coef:_T_MathRing, power:int, variableName:str="X") -> None: ...
    @overload
    def __init__(self, *, expression:"str") -> None: ...
    @overload
    def __init__(self, *, coef:_T_MathRing, variables:"dict[str, int]") -> None: ...
    
    def __init__(self, *, coef:"_T_MathRing|None"=None, power:"int|None"=None, variableName:str="X", expression:"str|None"=None, variables:"dict[str, int]|None"=None) -> None:
        self.__coef:"_T_MathRing"
        self.__variables:"dict[str, int]"
        """each variable and its power"""
        # assert that the parameters are given accordingly to only one of the overloads
        if expression is not None: # => use expression
            assert (coef is None) and (power is None) and (variableName == "X") and (variables is None), \
                ValueError("canot give a `coef`, `power`, `variableName` or `variables` while giving `expression`")
            raise NotImplementedError("not implemented yet, the parser need to be created first")
        elif (variables is not None) and (coef is not None): # => multiple variables given
            assert (power is None) and (variableName == "X") and (expression is None), \
                ValueError("canot give a `power`, `variableName` or `expression` while giving `coef` and `variables`")
            self.__coef = coef
            self.__variables = variables.copy()
        elif (power is not None) and (coef is not None):
            assert (variables is None) and (expression is None), \
                ValueError("canot give a `variables` or `expression` while giving `coef` and `power`")
            self.__coef = coef
            self.__variables = {variableName: power}
        else: raise ValueError("no valide signature found")
    
    def getCoef(self)->_T_MathRing:
        """/!\\ risky function, allow to edit the monomial"""
        return self.__coef
    
    def degree(self)->int:
        if (self.__coef == 0): # => the monomial is nul
            return -1
        return sum(self.__variables.values())
    
    def _getVariablesPowerString(self)->str:
        """convert the variables and powers to some text"""
        return "*".join(f"{variable}^{power}" for (variable, power) in self.__variables.items())
    
    def getVariablesPowers(self)->"dict[str, int]":
        """safe function, don't allow to edit the monomial (return a copy, slower)"""
        return self.__variables.copy()
    
    def _getRawVariables(self)->"dict[str, int]":
        """/!\\ risky function, allow to edit the monomial"""
        return self.__variables
    
    def __str__(self)->str:
        return f"{self.__coef}*{self._getVariablesPowerString()}"
    
    def __add__(self, other:"Monomial[_T_MathRing]")->"tuple[Monomial[_T_MathRing], Monomial[_T_MathRing]|None]": 
        ... # TODO
        
    def __iadd__(self, other:"Monomial[_T_MathRing]")->"Monomial[_T_MathRing]":
        if self.__variables != other.__variables: 
            raise ValueError(
                f"the variables or powers of `other`{other.__variables} don't correspond with"\
                f" the ones of `self`{self._getVariablesPowerString()}")
        # => matching variables and powers
        self.__coef += other.__coef
        return self
    
    def copy(self)->"Monomial[_T_MathRing]":
        return Monomial(coef=self.__coef, variables=self.__variables.copy())











class SimplePolynomial(Generic[_T_MathRing, _StrLiteral], SupportsMathRing):
    __slots__ = ("__coeffs", "__varName", "__degree")
    
    @overload
    def __init__(self, *coeffs:_T_MathRing, variableName:"_StrLiteral"="X") -> None:
        """create a poly with the coeffs given in the order: a[0] -> a[n-1]\n
        if you don't give coeffs, create a null polynomial"""
    @overload
    def __init__(self, *, expression:str, variableName:"_StrLiteral"="X") -> None:
        """create a poly from a maths expression"""
    @overload
    def __init__(self, *, monomials:"dict[int, _T_MathRing]", variableName:"_StrLiteral"="X") -> None:
        """create a poly from the coeffs of its monomials: dict{power: coef}"""
    @overload
    def __init__(self, *, monomials:"dict[int, _T_MathRing]", variableName:"_StrLiteral"="X", _copy:Literal[False], degree:"int|None") -> None:
        """/!\\ this signature is for internal purpose only\n
        create a poly from the coeffs of its monomials: dict{power: coef}"""
    def __init__(self, 
            *coeffs:_T_MathRing, expression:"str|None"=None, monomials:"dict[int, _T_MathRing]|None"=None,
            variableName:"_StrLiteral"="X", _copy:bool=True, degree:"int|None"=None) -> None:
        self.__varName:"_StrLiteral" = variableName
        self.__coeffs:"dict[int, _T_MathRing]"
        self.__degree:"int|None" = None
        """None => needs to be computed | int => is computed"""
        
        if expression is not None: # => use expression
            assert (len(coeffs) == 0) and (monomials is None) and (_copy is False) and (degree is None), \
                ValueError("canot give a `coeffs`, `monomials`, `_copy`, `degree` while giving `expression`")
            raise NotImplementedError("not implemented yet, the parser need to be created first")
            
        elif monomials is not None: # => monomials given (potential init by copy)
            assert (expression is None) and (len(coeffs) == 0), \
                ValueError("canot give a `expression`, `coeffs` while giving `monomials`")
            if _copy is True: # => init by copy
                self.__coeffs = monomials.copy()
                self.__degree = degree
            else: 
                assert (degree is None), \
                    ValueError("canot give a `degree` while giving `monomials` without copying (should be internal only)")
                self.__coeffs = monomials
        else: # => consecutive coeffs given (0 or more)
            assert (expression is None) and (monomials is None) and (_copy is False) and (degree is None), \
                ValueError("canot give a `expression`, `monomials`, `_copy`, `degree` while giving `coeffs`")
            self.__coeffs = {power: coef for (power, coef) in enumerate(coeffs)}
    
    def optimize(self)->bool:
        """optimize the polynomial (pop the null coeffs)
        return whether it optimized something"""
        # pop null coeffs
        didSomething:bool = False
        for (power, coef) in self.__coeffs.items():
            if coef == 0:
                self.__coeffs.pop(power)
                didSomething = True
        return didSomething
    
    @classmethod
    def __internalComputeDegree(cls, coeffs:"dict[int, _T_MathRing]")->int:
        """internal function to compute the degree of a poly described by the following coeffs"""
        # compute the degree of the biggest not null monomial
        degree:int = -1
        for (power, coef) in coeffs.items():
            if not(coef == 0) and (power > degree):
                degree = power
        return degree
    
    @property
    def degree(self)->int:
        """the degree of the polynomial (-> returns -1 for the null poly)"""
        if self.__degree is None:
            # => compute the degree
            self.__degree = SimplePolynomial.__internalComputeDegree(self.__coeffs)
        return self.__degree
        

    @classmethod
    def __internalAdd(cls, coeffsTarget:"dict[int, _T_MathRing]", coeffsOther:"dict[int, _T_MathRing]")->"dict[int, _T_MathRing]":
        """performe the 'add' ops on the coeffs of `coeffsTarget` with the coeffs of `coeffsTarget`, returns `coeffsTarget`"""
        for (power, coefOther) in coeffsOther.items():
            coefSelf:"_T_MathRing|None" = coeffsTarget.get(power, None)
            if coefSelf is None: coeffsTarget[power] = coefOther
            else: coeffsTarget[power] = coefSelf + coefOther
        return coeffsTarget
    
    def __add__(self, other:"SimplePolynomial[_T_MathRing, _StrLiteral]")->"SimplePolynomial[_T_MathRing, _StrLiteral]":
        if self.__varName != other.__varName:
            raise ValueError(f"can't add two SimplePolynomial with different variable name: {repr(self.__varName)} != {repr(other.__varName)}")
        newCoeffs:"dict[int, _T_MathRing]" = SimplePolynomial.__internalAdd(self.__coeffs.copy(), other.__coeffs)
        return SimplePolynomial(monomials=newCoeffs, variableName=self.__varName, _copy=False, degree=None)
    
    def __iadd__(self, other:"SimplePolynomial[_T_MathRing, _StrLiteral]")->"SimplePolynomial[_T_MathRing, _StrLiteral]":
        if self.__varName != other.__varName:
            raise ValueError(f"can't add two SimplePolynomial with different variable name: {repr(self.__varName)} != {repr(other.__varName)}")
        SimplePolynomial.__internalAdd(self.__coeffs, other.__coeffs)
        self.__degree = None
        return self
    
    @classmethod
    def __internalSub(cls, coeffsTarget:"dict[int, _T_MathRing]", coeffsOther:"dict[int, _T_MathRing]")->"dict[int, _T_MathRing]":
        """performe the 'add' ops on the coeffs of `coeffsTarget` with the coeffs of `coeffsTarget`, returns `coeffsTarget`"""
        for (power, coefOther) in coeffsOther.items():
            coefSelf:"_T_MathRing|None" = coeffsTarget.get(power, None)
            if coefSelf is None: coeffsTarget[power] = coefOther
            else: coeffsTarget[power] = coefSelf - coefOther
        return coeffsTarget
    
    def __sub__(self, other:"SimplePolynomial[_T_MathRing, _StrLiteral]")->"SimplePolynomial[_T_MathRing, _StrLiteral]":
        if self.__varName != other.__varName:
            raise ValueError(f"can't add two SimplePolynomial with different variable name: {repr(self.__varName)} != {repr(other.__varName)}")
        newCoeffs:"dict[int, _T_MathRing]" = SimplePolynomial.__internalAdd(self.__coeffs.copy(), other.__coeffs)
        return SimplePolynomial(monomials=newCoeffs, variableName=self.__varName, _copy=False, degree=None)
    
    def __isub__(self, other:"SimplePolynomial[_T_MathRing, _StrLiteral]")->"SimplePolynomial[_T_MathRing, _StrLiteral]":
        if self.__varName != other.__varName:
            raise ValueError(f"can't add two SimplePolynomial with different variable name: {repr(self.__varName)} != {repr(other.__varName)}")
        SimplePolynomial.__internalAdd(self.__coeffs, other.__coeffs)
        self.__degree = None
        return self
    
    @classmethod
    def __internalMult(cls, coeffs1:"dict[int, _T_MathRing]", coeffs2:"dict[int, _T_MathRing]")->"dict[int, _T_MathRing]":
        """performe the 'multiplication' ops on the coeffs of `coeffsTarget` with the coeffs of `coeffsTarget`, returns `coeffsTarget`"""
        # TODO
        return coeffs1
    
    def __mul__(self, other:"SimplePolynomial[_T_MathRing, _StrLiteral]")->"SimplePolynomial[_T_MathRing, _StrLiteral]":
        if self.__varName != other.__varName:
            raise ValueError(f"can't multiplicate two SimplePolynomial with different variable name: {repr(self.__varName)} != {repr(other.__varName)}")
        newCoeffs:"dict[int, _T_MathRing]" = self.__internalMult(self.__coeffs, other.__coeffs)
        return SimplePolynomial(monomials=newCoeffs, variableName=self.__varName, _copy=False, degree=None)
    
    def __imul__(self, other:"SimplePolynomial[_T_MathRing, _StrLiteral]")->"SimplePolynomial[_T_MathRing, _StrLiteral]":
        if self.__varName != other.__varName:
            raise ValueError(f"can't multiplicate two SimplePolynomial with different variable name: {repr(self.__varName)} != {repr(other.__varName)}")
        self.__coeffs = self.__internalMult(self.__coeffs, other.__coeffs)
        self.__degree = None
        return self
    
    
    @classmethod
    def __internalPow(cls, coeffs:"dict[int, _T_MathRing]", power:int)->"dict[int, _T_MathRing]":
        """performe the 'multiplication' ops on the coeffs of `coeffsTarget` with the coeffs of `coeffsTarget`, returns `coeffsTarget`"""
        # TODO
        return coeffs
    
    def __pow__(self, power:int)->"SimplePolynomial[_T_MathRing, _StrLiteral]":
        ...
    
    def __ipow__(self, other:"SimplePolynomial[_T_MathRing, _StrLiteral]")->"SimplePolynomial[_T_MathRing, _StrLiteral]":
        ...
    
    
    @classmethod
    def __internalDiv(cls, coeffs1:"dict[int, _T_MathRing]", coeffs2:"dict[int, _T_MathRing]")->"dict[int, _T_MathRing]":
        """performe the 'multiplication' ops on the coeffs of `coeffsTarget` with the coeffs of `coeffsTarget`, returns `coeffsTarget`"""
        # TODO
        return coeffs1
    
    def __div__(self, other:"SimplePolynomial[_T_MathRing, _StrLiteral]")->"SimplePolynomial[_T_MathRing, _StrLiteral]":
        if self.__varName != other.__varName:
            raise ValueError(f"can't multiplicate two SimplePolynomial with different variable name: {repr(self.__varName)} != {repr(other.__varName)}")
        newCoeffs:"dict[int, _T_MathRing]" = self.__internalDiv(self.__coeffs, other.__coeffs)
        return SimplePolynomial(monomials=newCoeffs, variableName=self.__varName, _copy=False, degree=None)
    
    def __idiv__(self, other:"SimplePolynomial[_T_MathRing, _StrLiteral]")->"SimplePolynomial[_T_MathRing, _StrLiteral]":
        if self.__varName != other.__varName:
            raise ValueError(f"can't multiplicate two SimplePolynomial with different variable name: {repr(self.__varName)} != {repr(other.__varName)}")
        self.__coeffs = self.__internalDiv(self.__coeffs, other.__coeffs)
        self.__degree = None
        return self














class Polynomial(Generic[_T_MathRing]):
    __slots__ = ("__monomials", )
    
    @overload
    def __init__(self, *coeffs:_T_MathRing, variableName:str="X") -> None:
        """create a poly with the coeffs given in the order: a[0] -> a[n-1]"""
    @overload
    def __init__(self, *, expression:"str") -> None: ...
    @overload
    def __init__(self, *, monomials:"Iterable[Monomial[_T_MathRing]]", copy:bool=True) -> None: ...
    
    def __init__(self, 
            *coeffs:_T_MathRing, variableName:str="X", expression:"str|None"=None,
            monomials:"Iterable[Monomial[_T_MathRing]]|None"=None, copy:bool=True) -> None:
        self.__monomials:"list[Monomial[_T_MathRing]]"
        """the list of monomials that describe the polynomial\n
        they are sorted by degree (lowest to biggest)"""
        # assert that the parameters are given accordingly to only one of the overloads
        if monomials is not None:
            assert (expression is None) and (len(coeffs) == 0) and (variableName == "X"), \
                ValueError("canot give an `expression`, `coeffs` or change `variableName` while giving `monomials`")
            self.__monomials = self.__optimizeMonomials(monomials, copy=copy)
        elif len(coeffs) != 0:
            assert (expression is None) and (monomials is None), \
                ValueError("canot give an `expression`, `monomials` while giving `coeffs`")
            assert (len(variableName) != 0), ValueError("empty `variableName` is not allowed")
            # => coeffs are given like P(X) = sum(coeffs[i] * X^i)
            self.__monomials = self.__optimizeMonomials(
                    (Monomial(coef=coef, power=degree, variableName=variableName) 
                     for (degree, coef) in enumerate(coeffs)),
                    copy=False)
        elif expression is not None:
            raise NotImplementedError("not implemented yet, the parser need to be created first")
        else: raise ValueError("no valide argument given")
    
    def degree(self)->int:
        # because they are sorted by degree, the biggest is the last
        return self.__monomials[-1].degree()
    
    @staticmethod
    def __optimizeMonomials(
            srcMonomials:"Iterable[Monomial[_T_MathRing]]", copy:bool)->"list[Monomial[_T_MathRing]]":
        """optimize the monomials to regroup them, `copy` is whether to do a copy of the inputed monomials"""
        monomialsGroups:"dict[dict[str, int], Monomial[_T_MathRing]]" = {}
        """the monomials of the polynomial regrouped by signature(based of variables and powers)"""
        for monomial in srcMonomials:
            if copy is True: # => need to do a copy
                monomial = monomial.copy()
            signature:"dict[str, int]" = monomial._getRawVariables()
            currMonomial:"Monomial[_T_MathRing]|None" = monomialsGroups.get(signature, None)
            if currMonomial is None: # => first with its signature => add it
                monomialsGroups[signature] = monomial
            else: # => alredy a monomial with the same signature => merge them
                currMonomial += monomial
        # put back the merged monomials in self
        filteredMonomials:"Iterable[Monomial[_T_MathRing]]" = \
            (monomial for monomial in monomialsGroups.values() if not (monomial.getCoef() == 0))
        return sorted(filteredMonomials, key=Monomial.degree)
        
