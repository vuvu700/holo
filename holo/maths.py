from .__typing import Iterable, Generic, overload, Literal
from .protocols import (
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







r""" Karatsuba polynomial theory: 
\text{############ when deg(a) ~ deg(b) ############} \newline
\text{the datas: } \newline
deg(a) = n = 2k \ge deg(b) \gt k \newline
a := a_1x^k + a_0 \text{ and } b := b_1x^k + b_0 \newline
\newline

\text{pre calc: }\newline
c_0 := a_0 \times b_0 \text{ and } c_2 := a_1 \times b_1 \newline
\lambda_1 := a_1 - a_0 \text{ and } \lambda_2 := b_1 - b_0 \newline 
\lambda_3 := \lambda_1 \times \lambda_2 \text{ and } \lambda_4 := c_2 + c_0 \newline
c_1:=  \lambda_4 - \lambda_3 \newline
\newline

\text{proofs: } \newline
c_1 = (a_1b_0 + a_0b_1) = ((a_1b_1 + a_0b_0) - (a_1-a_0)(b_1-b_0)) \newline
a \times b = (a_1x^k + a_0) \times (b_1x^k+b_0) \newline
a \times b = a_1b_1x^{2k} + (a_1b_0 + a_0b_1)x^k + a_0b_0 \newline
a \times b = c_2x^{2k} + c_1x^k + c_2 \newline
\newline

\text{cost :} \newline
C(n) = 3 \times C(n/2) + \alpha \times n \newline
C(n) = (\alpha +1)n^{log_2(3)} - 2\alpha \times n \newline
\Rightarrow  O(n^{log_2(3)}) \newline
\newline


\text{############ when deg(a) >> deg(b) ############} \newline
\text{the datas: } \newline
deg(a) = n = 2k \ge 2*deg(b) \Rightarrow deg(b) < k \newline
a := a_1x^k + a_0 \text{ and } b := 0x^k + b_0 = b_0 \newline
\newline

\text{pre calc: }\newline
c_1 := a_1 \times b_0  \text{ and } c_0 := a_0 \times b_0 \newline
\newline

\text{proofs: } \newline
a \times b = (a_1x^k + a_0) \times (b_0) \newline
a \times b = a_1b_0x^k + a_0b_0 \newline
a \times b = c_1x^k + c_0 \newline
\newline

\text{cost:} \newline
C(n) = 2 \times C(n/2) + \alpha \times n \newline
"""

class SimplePolynomial(Generic[_T_MathRing, _StrLiteral]):
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
            assert (expression is None) and (monomials is None) and (_copy is True) and (degree is None), \
                ValueError("canot give a `expression`, `monomials`, `_copy`, `degree` while giving `coeffs`")
            self.__coeffs = {power: coef for (power, coef) in enumerate(coeffs)}
    
    def __str__(self)->str:
        powers = sorted(self.__coeffs.keys(), reverse=True)
        return " + ".join(
            f"{self.__coeffs[power]}*{self.__varName}^{power}" 
            for power in powers)
    def __repr__(self)->str:
        powers = sorted(self.__coeffs.keys(), reverse=False)
        coeffsText = ", ".join(repr(self.__coeffs[power]) for power in powers)
        return f"{self.__class__.__name__}({coeffsText}, variableName={repr(self.__varName)})"
    
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
    def __internalAdd(cls, 
            coeffsTarget:"dict[int, _T_MathRing]", coeffsOther:"dict[int, _T_MathRing]",
            additionalPower:int=0)->"dict[int, _T_MathRing]":
        """perform `coeffsTarget` += `coeffsOther` * X^`additionalPower`, returns `coeffsTarget`"""
        for (power, coefOther) in coeffsOther.items():
            power += additionalPower
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
    def __internalSub(cls, 
            coeffsTarget:"dict[int, _T_MathRing]", coeffsOther:"dict[int, _T_MathRing]",
            additionalPower:int=0)->"dict[int, _T_MathRing]":
        """perform `coeffsTarget` -= `coeffsOther` * X^`additionalPower`, returns `coeffsTarget`"""
        for (power, coefOther) in coeffsOther.items():
            power += additionalPower
            coefSelf:"_T_MathRing|None" = coeffsTarget.get(power, None)
            if coefSelf is None: coeffsTarget[power] = coefOther
            else: coeffsTarget[power] = coefSelf - coefOther
        return coeffsTarget
    
    def __sub__(self, other:"SimplePolynomial[_T_MathRing, _StrLiteral]")->"SimplePolynomial[_T_MathRing, _StrLiteral]":
        if self.__varName != other.__varName:
            raise ValueError(f"can't add two SimplePolynomial with different variable name: {repr(self.__varName)} != {repr(other.__varName)}")
        newCoeffs:"dict[int, _T_MathRing]" = SimplePolynomial.__internalSub(self.__coeffs.copy(), other.__coeffs)
        return SimplePolynomial(monomials=newCoeffs, variableName=self.__varName, _copy=False, degree=None)
    
    def __isub__(self, other:"SimplePolynomial[_T_MathRing, _StrLiteral]")->"SimplePolynomial[_T_MathRing, _StrLiteral]":
        if self.__varName != other.__varName:
            raise ValueError(f"can't add two SimplePolynomial with different variable name: {repr(self.__varName)} != {repr(other.__varName)}")
        SimplePolynomial.__internalSub(self.__coeffs, other.__coeffs)
        self.__degree = None
        return self
    
    
    
    @classmethod
    def __internalNaiveMult(cls, coeffs1:"dict[int, _T_MathRing]", coeffs2:"dict[int, _T_MathRing]")->"dict[int, _T_MathRing]":
        """performe the 'multiplication' ops on the coeffs of `coeffsTarget` with the coeffs of `coeffsTarget`, returns `coeffsTarget`"""
        newCoeffs:"dict[int, _T_MathRing]" = {}
        for (power1, coeff1)  in coeffs1.items():
            for (power2, coeff2) in coeffs2.items():
                currCoeff:"_T_MathRing|None" = newCoeffs.get(power1+power2, None)
                if currCoeff is None:
                    newCoeffs[power1+power2] = coeff1 * coeff2
                else: newCoeffs[power1+power2] = currCoeff + (coeff1 * coeff2)
        return newCoeffs
    
    @classmethod
    def __internalSplitCoeffs(cls, 
            coeffs:"dict[int, _T_MathRing]", K:int)->"tuple[dict[int, _T_MathRing], dict[int, _T_MathRing]]":
        coeffs1:"dict[int, _T_MathRing]" = {}
        coeffs0:"dict[int, _T_MathRing]" = {}
        for (power, coeff) in coeffs.items():
            if coeff == 0: continue # skip zero coeffs => optimize the poly
            # => (coeff != 0)
            if power >= K: coeffs1[power-K] = coeff
            else: coeffs0[power] = coeff
        return (coeffs1, coeffs0)
    
    @classmethod
    def __internalFastMult(cls, coeffsA:"dict[int, _T_MathRing]", coeffsB:"dict[int, _T_MathRing]")->"dict[int, _T_MathRing]":
        """performe the fast karatsuba 'multiplication' ops on the coeffs of `coeffsA` with the coeffs of `coeffsB`, returns the new coeffs"""
        if (len(coeffsA) == 0) or (len(coeffsB) == 0):
            # => (A us null) or (B is null) => return null poly ie. empty coeffs
            return {}
        
        degreeA:int = SimplePolynomial.__internalComputeDegree(coeffsA) # O(N)
        degreeB:int = SimplePolynomial.__internalComputeDegree(coeffsB) # O(N)
        if degreeB > degreeA: # => swap A and B
            (coeffsA, coeffsB) = (coeffsB, coeffsA)
            (degreeA, degreeB) = (degreeB, degreeA)
        # => deg(A) >= deg(B)
        K:int = degreeA // 2
        
        if K < 8: # => prefer the naive methode (K < `arbitraryConstante`, 8 seems great)
            return SimplePolynomial.__internalNaiveMult(coeffsA, coeffsB)
        
        # split  A = A1*X^k + A0  and  B = B1*X^k + B0
        (coeffsA1, coeffsA0) = SimplePolynomial.__internalSplitCoeffs(coeffsA, K) # O(N)
        (coeffsB1, coeffsB0) = SimplePolynomial.__internalSplitCoeffs(coeffsB, K) # O(N)
        
        # do all the intermediary calcs
        coeffsC2 = SimplePolynomial.__internalFastMult(coeffsA1, coeffsB1) # O(K^log2(3))
        coeffsC0 = SimplePolynomial.__internalFastMult(coeffsA0, coeffsB0) # O(K^log2(3))
        coeffsL1 = SimplePolynomial.__internalSub(coeffsTarget=coeffsA1.copy(), coeffsOther=coeffsA0) # O(K)
        coeffsL2 = SimplePolynomial.__internalSub(coeffsTarget=coeffsB1.copy(), coeffsOther=coeffsB0) # O(K)
        del coeffsA1, coeffsA0, coeffsB1, coeffsB0
        coeffsL3 = SimplePolynomial.__internalFastMult(coeffsL1, coeffsL2) # O(K^log2(3))
        del coeffsL1, coeffsL2
        coeffsL4 = SimplePolynomial.__internalAdd(coeffsTarget=coeffsC2.copy(), coeffsOther=coeffsC0) # O(N)
        coeffsC1 = SimplePolynomial.__internalSub(coeffsTarget=coeffsL4.copy(), coeffsOther=coeffsL3) # O(N)
        del coeffsL3, coeffsL4
        # => only coeffs: (coeffsC2, coeffsC1, coeffsC0)
        # compute: C2*x^(2k) + C1*x^k + C0 (do the ops on coeffsC0 to avoid the "+ C0")
        SimplePolynomial.__internalAdd(coeffsTarget=coeffsC0, coeffsOther=coeffsC1, additionalPower=K)
        del coeffsC1
        SimplePolynomial.__internalAdd(coeffsTarget=coeffsC0, coeffsOther=coeffsC2, additionalPower=2*K)
        del coeffsC2
        
        return coeffsC0 # := A * B
    
    def __mul__(self, other:"SimplePolynomial[_T_MathRing, _StrLiteral]")->"SimplePolynomial[_T_MathRing, _StrLiteral]":
        if self.__varName != other.__varName:
            raise ValueError(f"can't multiplicate two SimplePolynomial with different variable name: {repr(self.__varName)} != {repr(other.__varName)}")
        newCoeffs:"dict[int, _T_MathRing]" = SimplePolynomial.__internalFastMult(self.__coeffs, other.__coeffs)
        return SimplePolynomial(monomials=newCoeffs, variableName=self.__varName, _copy=False, degree=None)
    
    def __imul__(self, other:"SimplePolynomial[_T_MathRing, _StrLiteral]")->"SimplePolynomial[_T_MathRing, _StrLiteral]":
        if self.__varName != other.__varName:
            raise ValueError(f"can't multiplicate two SimplePolynomial with different variable name: {repr(self.__varName)} != {repr(other.__varName)}")
        self.__coeffs = SimplePolynomial.__internalFastMult(self.__coeffs, other.__coeffs)
        self.__degree = None
        return self
    
    
    
    @classmethod
    def __internalPow(cls, coeffs:"dict[int, _T_MathRing]", power:int)->"dict[int, _T_MathRing]":
        """performe the 'multiplication' ops on the coeffs of `coeffsTarget` with the coeffs of `coeffsTarget`, returns `coeffsTarget`"""
        if power <= 0:
            for coeff in coeffs.values():
                if not(coeff == 0):
                    one:"_T_MathRing" = coeff**0
                    break
            else: # => didn't found a non null coef => null poly
                raise ZeroDivisionError("tryed to compute (null poly) ** `power` with `power` <= 0  ")
            coeffsOne:"dict[int, _T_MathRing]" = {0: one}
            
            if power == 0: return coeffsOne # 1*x^0  (1 of _T_MathRing)
            # => computing 1 / (coeffs ** (-power))
            return SimplePolynomial.__internalDiv(coeffsOne, SimplePolynomial.__internalPow(coeffs, -power))
        # => (power >= 1)
        # use the fast exponentiation algorithme
        # consider power[i] = (power >> i) % 2
        coeffsPow2i:"dict[int, _T_MathRing]" = coeffs
        del coeffs
        # find the first i with power % 2 == 1 (guarentied to end because power >= 1)
        i = 0
        while (power % 2) == 0:
            coeffsPow2i = SimplePolynomial.__internalFastMult(coeffsPow2i, coeffsPow2i) # mayby replaced by a fast squaring function ?
            power = power >> 1
            i += 1
            print(i, power, len(coeffsPow2i))
            
        coeffsResult = coeffsPow2i.copy()
        while (power != 0):
            if (power % 2) == 1:
                coeffsResult = SimplePolynomial.__internalFastMult(coeffsResult, coeffsPow2i)
            power = power >> 1
            if power != 0:
                coeffsPow2i = SimplePolynomial.__internalFastMult(coeffsPow2i, coeffsPow2i) # mayby replaced by a fast squaring function ?
            i += 1
            print(i, power, len(coeffsPow2i))
        return coeffsResult
    
    def __pow__(self, power:int)->"SimplePolynomial[_T_MathRing, _StrLiteral]":
        newCoeffs:"dict[int, _T_MathRing]" = SimplePolynomial.__internalPow(self.__coeffs, power)
        return SimplePolynomial(monomials=newCoeffs, variableName=self.__varName, _copy=False, degree=None)
    
    def __ipow__(self, power:int)->"SimplePolynomial[_T_MathRing, _StrLiteral]":
        self.__coeffs = SimplePolynomial.__internalPow(self.__coeffs, power)
        self.__degree = None
        return self
    
    
    
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
        
