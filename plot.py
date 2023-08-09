import math as __math
import numpy as __numpy
import matplotlib.pyplot as __plt
from inspect import getfullargspec as __getfullargspec

from holo.__typing import Callable as __Callable, Literal as __Literal


def plot1dFunc(
        func:"__Callable[[float|__numpy.ndarray], float|int|__numpy.ndarray]",
        xStart:"float|int", xStop:"float|int", nbPoints:int=100,
        xLabel:"str|bool"=False, yLabel:"str|bool"=False, autoLabel:bool=False,
        plotLabel:"str|None"=None, figName:"None|str"=None)->None:
    
    fig = __plt.figure(figName)
    ax = fig.add_subplot(1, 1, 1)
    
    if autoLabel is True:
        xLabel = True
        yLabel = True

    X = __numpy.linspace(xStart, xStop, nbPoints)
    try:
        Y = func(X)
        if not isinstance(Y, __numpy.ndarray):
            raise TypeError
    except:
        Y = [func(x) for x in X]

    #plot the function
    ax.plot(X, Y, label=plotLabel)
    
    # Set axes label for the plot
    if xLabel is not False:
        if xLabel is True: # auto
            ax.set_xlabel(__getfullargspec(func).args[0])
        else:
            ax.set_xlabel(xLabel)
    else:
        ax.set_xlabel('x')

    if yLabel is not False:
        if yLabel is True: # auto
            ax.set_ylabel(func.__name__)
        else:
            ax.set_ylabel(yLabel)
    else:
        ax.set_ylabel('y')

    fig.show()

def plot2dFunc(
        func:"__Callable[[float|__numpy.ndarray, float|__numpy.ndarray], float|int|__numpy.ndarray]",
        xStart:"float|int", xStop:"float|int", yStart:"float|int", yStop:"float|int",
        xNbPoints:int=100, yNbPoints:int=100,
        xLabel:"str|bool"=False, yLabel:"str|bool"=False, zLabel:"str|bool"=False,
        autoLabel:bool=False, plotLabel:"str|None"=None, figName:"None|str"=None,
        zScale:"__Literal['linear', 'log10', 'ln']|None"=None)->None:
    
    CMAP = "viridis"
    if autoLabel is True:
        xLabel = True
        yLabel = True
        zLabel = True

    # for now dont suport differnet nb of points, compute even nb of pts while keeping the same total
    if xNbPoints != yNbPoints:
        yNbPoints = __math.ceil(__math.sqrt(yNbPoints * xNbPoints))
        xNbPoints = yNbPoints

    fig = __plt.figure(figName)
    ax3D = fig.add_subplot(1, 2, 1, projection='3d')
    ax2D = fig.add_subplot(1, 2, 2)

    X = __numpy.linspace(xStart, xStop, xNbPoints)
    Y = __numpy.linspace(yStart, yStop, yNbPoints)
    X_mesh, Y_mesh = __numpy.meshgrid(X, Y)
    try:
        Z = func(X_mesh, Y_mesh)
        if not isinstance(Z, __numpy.ndarray):
            raise TypeError
    except:
        Z = __numpy.array([[func(x, y) for y in Y] for x in X])

    if zScale is not None:
        if (zScale == "log10") or (zScale == "log"):
            Z = __numpy.log10(Z)
        elif (zScale == "ln"):
            Z = __numpy.log(Z)

    # 3D plot
    surf = ax3D.plot_surface(X_mesh, Y_mesh, Z, cmap=CMAP, label=plotLabel)
    fig.colorbar(surf, shrink=0.5, aspect=8)

    # 2D plot
    ax2D.pcolormesh(X_mesh, Y_mesh, Z, cmap=CMAP)

    # Set axes label for the 3D and 2D plots
    if xLabel is not False:
        if xLabel is True: # auto
            ax3D.set_xlabel(__getfullargspec(func).args[0])
            ax2D.set_xlabel(__getfullargspec(func).args[0])
        else:
            ax3D.set_xlabel(xLabel)
            ax2D.set_xlabel(xLabel)
    else:
        ax3D.set_xlabel('x')
        ax2D.set_xlabel('x')

    if yLabel is not False:
        if yLabel is True: # auto
            ax3D.set_ylabel(__getfullargspec(func).args[1])
            ax2D.set_ylabel(__getfullargspec(func).args[1])
        else:
            ax3D.set_ylabel(yLabel)
            ax2D.set_ylabel(yLabel)
    else:
        ax3D.set_ylabel('y')
        ax2D.set_ylabel('y')

    if zLabel is not False:
        if zLabel is True: # auto
            ax3D.set_zlabel(func.__name__)
        else:
            ax3D.set_zlabel(zLabel)
    else:
        ax3D.set_zlabel('z')


    fig.show()


def plotImage(array:__numpy.ndarray)->None:
    raise NotImplementedError("not imlplemented yet")

plot = plot1dFunc
plot2 = plot2dFunc
plotImg = plotImage