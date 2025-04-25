from holo.__typing import List, overload, Callable, Literal, Tuple
from holo.types_ext import _1dArray_Float, _2dArray_Float, _3dArray_Float
from holo import separate
from holo.prettyFormats import prettyPrint

_Verbose = Literal[0, 1, 2]
_Selection = Literal["uniform", "bests", "worsts", "ordered"]
_Param = Tuple[float, ...]

import math
import numpy
from opensimplex import noise2array, noise2, seed
import matplotlib.pyplot as plt
from scipy.interpolate import griddata

N = 2 # nb of dimentions for the func
scale = 1/3
def coeffs():
    global _f_coefs, _f_bias
    _f_coefs = numpy.random.uniform(-5, 5, (N, ))
    _f_bias = numpy.random.uniform(-0.7, 0.7, (N, ))
    print(_f_coefs, _f_bias)
    seed(numpy.random.randint(0, 2**30))
try: _ = _f_coefs
except: coeffs()

@overload
def _func(params:"_3dArray_Float")->"_2dArray_Float": ... 
@overload
def _func(params:"_1dArray_Float")->"float": ...
def _func(params:numpy.ndarray):
    params = params * scale
    result = numpy.sin(_f_coefs * params - _f_bias).sum(axis=-1)
    result += numpy.cos((params**2).sum(axis=-1))
#    result += numpy.cos(params.sum(axis=-1))
    return abs(result)**0.5

def func_param(param:"_Param")->float:
    return _func(numpy.asarray(param)) # type: ignore

def _funcPerlin(params:"_3dArray_Float")->"_2dArray_Float":
    shape = params.shape[: -1]
    X = params[0, :, 0].flatten() * scale
    Y = params[:, 0, 1].flatten() * scale
    return abs(noise2array(X, Y)).reshape(shape) # type: ignore
    return (noise2array(X, Y).reshape(shape)+1)/2 # type: ignore

def funcPerlin(param:"_Param")->float:
    x, y, *others = param
    return abs(noise2(x*scale, y*scale))
    return (noise2(x*scale, y*scale)+1) / 2

def plotFunc(
        paramsMin:"tuple[float, float]", paramsMax:"tuple[float, float]", 
        resolution:int, func)->None:
    assert N == 2
    X_raw = numpy.stack(numpy.meshgrid(
        *[numpy.linspace(mini, maxi, num=resolution) 
          for (mini, maxi) in zip(paramsMin, paramsMax)]), 
        axis=-1)
    y_raw = func(X_raw)
    cs = plt.contourf(
        X_raw[:, :, 0], X_raw[:, :, 1], y_raw, 
        alpha=1.0, levels=10)
    plt.colorbar(cs)


class HyperparametersSearch():
    EPSILON = 1e-5
    def __init__(self, baseParameters:"list[_Param]", 
                 func:"Callable[[_Param], float]", nbNeightbors:"int|None", 
                 semiRandomSelection:"_Selection"="ordered", 
                 learningRate:float=1.0, normalizeGradient:bool=True,
                 verbose:"_Verbose"=0) -> None:
        self.lr: float = learningRate
        self.K: "int|None" = nbNeightbors
        self.norm: bool = normalizeGradient
        self.verbose: "_Verbose" = verbose
        self.knownParameters: "dict[_Param, float]" = {}
        self._parametersOrder: "list[_Param]" = []
        self._currentParamIndex: int = 0
        self.func: "Callable[[_Param], float]" = func
        self.semiRndomSelection: "_Selection" = semiRandomSelection
        for param in baseParameters:
            self.evaluateParameter(param)
        self._currentParamIndex = 0 # (len(self._parametersOrder) - 1)
    
    #### KNN
    
    def getKNearest(self, param:_Param, nbNearest:int)->"list[_Param]":
        assert len(self.knownParameters) > 0, \
            IndexError("no parameters alredy known")
        allDists = sorted(
            (self.distance(param, param2), param2)
            for param2 in self.knownParameters.keys())
        return [param2 for (dist, param2) in allDists[: nbNearest]]
    
    def nearestKnown(self, param:"_Param")->"_Param":
        return self.getKNearest(param, 1)[0]
    
    #### conversion
    
    @staticmethod
    def __convertParam(param:"_1dArray_Float")->"_Param":
        return tuple(map(float, param))
    
    @staticmethod
    def __toNumpy(param:"_Param")->"_1dArray_Float":
        return numpy.asarray(param, dtype=numpy.float64)
    
    #### utils
    
    def getScore(self, param:"_Param")->float:
        return self.knownParameters[param]
    
    @staticmethod
    def distance(param1:"_Param", param2:"_Param")->float:
        return numpy.linalg.norm(
            numpy.asarray(param1) - numpy.asarray(param2), ord=2)
    
    def __nbKeep(self, keepBest:"float|int")->float:
        if isinstance(keepBest, float):
            return math.ceil(keepBest * len(self.knownParameters))
        else: return keepBest
    
    def _plotPoints(self, keepBest:"float|int"=1.0, color:str="orange")->None:
        # select the params to plot
        params = self.getbestParams(keepBest)
        # transforme the coordinates and plot
        P1: "list[float]" = []
        P2: "list[float]" = []
        for (p1, p2, *others) in params:
            P1.append(p1)
            P2.append(p2)
        plt.scatter(P1, P2, c=color)
    
    def _plotScoreMap(self, keepBest:"float|int"=1.0, alpha:float=1.0):
        params, scores = separate(self.getbestPairs(keepBest))
        params_arr = numpy.asarray(params, dtype=numpy.float64)
        z: _1dArray_Float = numpy.asarray(scores, dtype=numpy.float64)
        x: _1dArray_Float = params_arr[:, 0]
        y: _1dArray_Float = params_arr[:, 1]
        # Create a grid for (x, y)
        x_grid, y_grid = numpy.meshgrid(
            numpy.linspace(x.min(), x.max(), 200), 
            numpy.linspace(y.min(), y.max(), 200))
        z_grid = griddata((x, y), z, (x_grid, y_grid), method='linear')
        cs = plt.contourf(
            x_grid, y_grid, z_grid, alpha=alpha, 
            levels=10, cmap="RdBu_r")
        plt.colorbar(cs)
    
    def _plotGradField(self, keepBest:"float|int"=1.0):
        allParams = self.getbestParams(keepBest)
        params_arr = numpy.asarray(allParams, dtype=numpy.float64)
        gradients = [-self.__computeGradient(param) 
                     for param in allParams]
        gradients_arr = numpy.asarray(gradients, dtype=numpy.float64)
        x: _1dArray_Float = params_arr[:, 0]
        y: _1dArray_Float = params_arr[:, 1]
        u: _1dArray_Float = gradients_arr[:, 0]
        v: _1dArray_Float = gradients_arr[:, 1]
        # Create a grid for (x, y)
        resolution = 20
        x_grid, y_grid = numpy.meshgrid(
            numpy.linspace(x.min(), x.max(), resolution), 
            numpy.linspace(y.min(), y.max(), resolution))
        u_grid = griddata((x, y), u, (x_grid, y_grid), method='linear')
        v_grid = griddata((x, y), v, (x_grid, y_grid), method='linear')
        cs = plt.quiver(x_grid, y_grid, u_grid, v_grid)
    
    def getbestScores(self, keepBest:"float|int")->"list[float]":
        return sorted(self.knownParameters.values())[: self.__nbKeep(keepBest)]
    def getbestParams(self, keepBest:"float|int")->"list[_Param]":
        return sorted(self.knownParameters.keys(), 
                      key=lambda p:self.knownParameters[p])[: self.__nbKeep(keepBest)]
    def getbestPairs(self, keepBest:"float|int")->"list[tuple[_Param, float]]":
        return sorted(self.knownParameters.items(), 
                      key=lambda t:t[1])[: self.__nbKeep(keepBest)]
    
    
    #### parameter picking
    
    def _selectSemiRandomKnown(self)->"_Param":
        """return the base knwon parameter fo search from
        for the next iteration"""
        scores = numpy.asarray(list(self.knownParameters.values()))
        minScore: float = scores.min()
        maxScore: float = scores.max()
        fScore: "Callable[[float], float]"
        if self.semiRndomSelection == "bests":
            fScore = lambda score: (maxScore - score)
        elif self.semiRndomSelection == "worsts":
            fScore = lambda score: (score - minScore)
        elif self.semiRndomSelection == "uniform":
            fScore = lambda score: 1.0
        elif self.semiRndomSelection == "ordered":
            # get next in 
            param = self._parametersOrder[self._currentParamIndex]
            nbParams: int = len(self._parametersOrder)
            self._currentParamIndex += 1
            if (self._currentParamIndex >= nbParams):
                if (nbParams > 10):
                    self._currentParamIndex = nbParams // 2
                else: self._currentParamIndex = 0
            return param
        else: raise ValueError(f"unsupported selection methode: {self.semiRndomSelection}")
        
        allParams = sorted(
            ((fScore(score), param)
             for param, score in self.knownParameters.items()),
            reverse=True)
        scoresSum: float = sum(score for (score, _) in allParams)
        targetedScore = numpy.random.uniform(0, scoresSum)
        # find the selected parameter
        currScoreSum: float = 0.0
        for score, param in allParams:
            currScoreSum += score
            if currScoreSum >= targetedScore:
                # => selected
                return param
        raise RuntimeError(f"[BUG] {targetedScore} / {currScoreSum}")
    
    #### fitting
    
    def evaluateParameter(self, param:"_Param")->"tuple[float, bool]":
        """evaluate the function for the given parameters\n
        if it alredy know some parameters close enought, dont compute it 
        and use its results\n
        returns (evalOfFunc, isNewParameters)
        """
        # test if alredy known (require at least one that is alredy known)
        if len(self.knownParameters) != 0:
            # => might have a nearest
            nearest = self.nearestKnown(param)
            dist = self.distance(param, nearest)
            if (dist < self.EPSILON):
                # => considered alredy known
                if self.verbose >= 1:
                    print(f"not processing {param} because {nearest} "
                          f"is too close (distance={float(dist)})")
                return (self.getScore(nearest), False)
            # => not known param close enougth
            del nearest, dist
        # => compute the score for the given param
        score: float = self.func(param)
        self.knownParameters[param] = score
        self._parametersOrder.append(param)
        if self.verbose >= 2:
            print(f"has computed func for {param} -> score={score} ")
        return (score, True)
    
    def __computeGradient(
            self, param:"_Param")->"_1dArray_Float":
        # find the neigthbors
        kNearests: "list[_Param]"
        if self.K is None:
            kNearests = list(self.knownParameters.keys())
        else: kNearests = self.getKNearest(param, self.K+1)
        # compute the gradient
        score: float = self.knownParameters[param]
        param_arr: _1dArray_Float = self.__toNumpy(param)
        gradient: _1dArray_Float = numpy.zeros_like(param_arr)
        for neightbor in kNearests:
            if neightbor == param: 
                continue
            neightbor_score: float = self.knownParameters[neightbor]
            neightbor_arr: _1dArray_Float = self.__toNumpy(neightbor)
            scoreDelta: float = (neightbor_score-score)
            distance: float = self.distance(param, neightbor)
            deltaVect = (neightbor_arr - param_arr)
            gradient += scoreDelta * (deltaVect / distance**2)
        if self.norm is True:
            # normalize it
            grad_norm = numpy.linalg.norm(gradient)
            if self.verbose >= 2:
                print(f"[DEBUG] ||grad|| = {grad_norm:.3g}")
            gradient /= grad_norm
        return gradient 
    
    def __computeNextParam(
            self, param:"_Param")->"_Param":
        gradient: _1dArray_Float = self.__computeGradient(param)
        param_arr: _1dArray_Float = self.__toNumpy(param)
        # aplie the gradient decente
        next_param_arr = param_arr - (self.lr * gradient)
        return self.__convertParam(next_param_arr)
    
    def fit(self, nbSteps:int)->None:
        for _ in range(nbSteps):
            param = self._selectSemiRandomKnown()
            param_next = self.__computeNextParam(param)
            (score, isNew) = self.evaluateParameter(param_next)



"""
# tests

### check distribution
counts = {param: 0 for param in search.knownParameters.keys()}
for _ in range(1000):
    param = search._selectKnown()
    counts[param] += 1
prettyPrint(counts)



#coeffs()
plt.show()
plotFunc([-3, -3], [3, 3], 100, _funcPerlin)

basePoints = [(-1.8, -1.0), (0.0, -2.0), (-0.5, 1.5), (1.1, 0.5), (0.7,-0.1)]
search = HyperparametersSearch(
    baseParameters=basePoints, 
    func=funcPerlin, semiRandomSelection=True, 
    nbNeightbors=200, learningRate=0.1, verbose=0)
nbParams = len(search.knownParameters) 
print(f"nb of known parameters: {nbParams}")

search.fit(nbSteps=20)
print(f"{len(search.knownParameters)-nbParams} new points")

search._plotScoreMap(alpha=0.6)

#search._plotPoints(color="black")
search._plotPoints(0.5, color="gray")
plt.scatter(*separate(basePoints), c="pink")
search._plotPoints(0.05, color="cyan")
print(", ".join(map(lambda x:f"{x:.3g}", search.getbestScores(0.05))))
""";