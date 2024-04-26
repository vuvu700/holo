from math  import gcd, ceil, sqrt, factorial as fac, pi, exp, erf
from decimal import Decimal, getcontext as decimal_getContext

from holo.__typing import Iterable, MutableSequence, TypeVar
from holo.protocols import (
    _T, _T_co, _T_contra, SupportsDivModRec,
    SupportsLenAndGetItem,
)

_T_MutableSequence = TypeVar("_T_MutableSequence", bound=MutableSequence)

decimal_getContext().prec = 28



def getFirstInv(modulo:int, start:int=2)->int:
    """return the first number to be inversible in Z/`modulo`Z\n
    return the inversible number or -1 if no number found found"""
    gcd_ = gcd # local
    if start < 2: start = 2
    for num in range(start, ceil(sqrt(modulo))):
        if gcd_(num, modulo) == 1:
            return num
    return -1

def getCenterInv(modulo:int)->int:
    """return the last number < sqrt(modulo) to be inversible in Z/`modulo`Z\n
    return the inversible number or -1 if no number found found"""
    gcd_ = gcd # local
    for num in range(ceil(sqrt(modulo)), 2-1, -1):
        if gcd_(num, modulo) == 1:
            return num
    return -1

# for modular inverse  -> sympy.mod_inverse(m1, mod)



def _simpleFactorisation(number:int)->"list[int]":
    factors:"list[int]" = []
    append_factor = factors.append # speed opti
    # all 2x factors
    while number %2 == 0:
        number //= 2
        append_factor(2)

    factor:int = 3
    while number > 1:
        if number % factor == 0: # divisible by factor
            append_factor(factor)
            number //= factor
            factor = 3
            continue
        factor += 2

    return factors

def factor(n:int, breakAllFactors:bool=True)->"list[int]":
    """return the list of the factors of `n`"""
    factors:"list[int]" = []
    append_factor = factors.append # speed opti
    gcd_ = gcd # local

    while n > 1:

        x_fixed = 2
        cycle_size = 2
        x = 2
        factor = 1
        while factor == 1:

            for _ in range(cycle_size):
                x = (x * x + 1) % n
                factor = gcd_(x - x_fixed, n)
                if factor > 1:
                    append_factor(factor)
                    n //= factor
                    break

            cycle_size *= 2
            x_fixed = x

    if breakAllFactors is True:
        return _all_factors(factors)
    else:
        return factors

def _all_factors(factorsListe:"list[int]")->"list[int]":
    final_factors:"list[int]" = []
    append_factor = final_factors.append # speed opti

    for factor in factorsListe:
        for subFactor in _simpleFactorisation(factor):
            append_factor(subFactor)
    return final_factors


def divmod_rec(
        value:"SupportsDivModRec[_T_contra, _T_co]",
        divisors:"Iterable[_T_contra]")->"list[_T_co]":
    results:"list[_T_co]" = []
    quotient:"_T_co"; remainder:"SupportsDivModRec[_T_contra, _T_co]"
    for div in divisors:
        quotient, remainder = divmod(value, div)
        results.append(quotient)
        value = remainder
    # add last remainder / initial value when no divisors
    results.append(value) # unfortunate but unsolvable
    return results

def divisor(n:int)->"list[int]":
    """return the list of its positive divisors"""
    return [div for div in range(1, n//2+1) if n % div == 0]

def nonDivisor(n:int)->"list[int]":
    """return the list of the numbers in [[1, n//2]] that aren't its divisor"""
    return [div for div in range(1, n//2+1) if n % div != 0]




piDecimal = Decimal("3.14159265358979323846264338327950288419716939937510582097494459230781640628620899862803482534211706798214808651328230664709384460955058223172535940812848111745028410270193852110555964462294895493038196442881097566593344612847564823378678316527120190914564856692346034861045432664821339360726024914127372458700660631558817488152092096282925409171536436789259036001133053054882046652138414695194151160943305727036575959195309218611738193261179310511854807446237996274956735188575272489122793818301194912983367336244065664308602139494639522473719070217986094370277053921717629317675238467481846766940513200056812714526356082778577134275778960917363717872146844090122495343014654958537105079227968925892354201995611212902196086403441815981362977477130996051870721134999999837297804995105973173281609631859502445945534690830264252230825334468503526193118817101000313783875288658753320838142061717766914730359825349042875546873115956286388235378759375195778185778053217122680661300192787661119590921642019893809525720106548586327886593615338182")
eDecimal  = Decimal("2.71828182845904523536028747135266249775724709369995957496696762772407663035354759457138217852516642742746639193200305992181741359662904357290033429526059563073813232862794349076323382988075319525101901157383418793070215408914993488416750924476146066808226480016847741185374234544243710753907774499206955170276183860626133138458300075204493382656029760673711320070932870912744374704723069697720931014169283681902551510865746377211125238978442505695369677078544996996794686445490598793163688923009879312773617821542499922957635148220826989519366803318252886939849646510582093923982948879332036250944311730123819706841614039701983767932068328237646480429531180232878250981945581530175671736133206981125099618188159304169035159888851934580727386673858942287922849989208680582574927961048419844436346324496848756023362482704197862320900216099023530436994184914631409343173814364054625315209618369088870701676839642437814059271456354906130310720851038375051011574770417189861068739696552126715468895703503540212340784981933432106817012100562788")
__pi2Deccimale = piDecimal*2

__CONST_2PI_SQRT = __pi2Deccimale.sqrt()

def factorial(x:int)->int:
    """stirling (extended) formula with decimals and use of math.factorial for low (<20) `x`"""
    if x < 20: return fac(x)
    x_:Decimal = Decimal(x)
    return int(__CONST_2PI_SQRT*x_.sqrt() * ((x_/eDecimal)**x_) * (
        1/(12*x_) - 1/(360*(x_**3))
        + 1/(1260*(x_**5)) - 1/(1680*(x_**7))
        + 1/(1188*x_**9) - 691/(360360*x_**11)
        + 1/(165*x_**13)
         - 1*3617/(122400*x_**15) ).exp()
    )



def gaussCurve(x:float, omega:float=1.0, mu:float=0.0)->float:
    return (1 / (omega * sqrt(2*pi))) \
        * exp(-1/2 * ((x - mu) / omega)**2)


def gaussCumulativeRepartition(x:float, omega:float=1.0, mu:float=0.0)->float:
    return 0.5 * (1 + erf((x - mu) / (omega*(2**0.5))))



def invertPermutation(permut:"list[int]")->"list[int]":
    ... # TODO

def appliePermutation(
        elements:"SupportsLenAndGetItem[_T]", permut:"list[int]")->"list[_T]":
    return [elements[indexItemFrom] for indexItemFrom in permut]

def appliePermutationInplace(
        elements:"_T_MutableSequence", permut:"list[int]")->"_T_MutableSequence":
    ... # TODO
    return elements
