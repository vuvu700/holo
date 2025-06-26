import numpy
import numba
from random import shuffle as __shuffle

from .types_ext import _2dArray_Float


def swapRow(array:_2dArray_Float, x1:int, x2:int)->None:
    array[[x1, x2], :] = array[[x2, x1], :]

def swapCopyRow(array:_2dArray_Float, x1:int, x2:int)->_2dArray_Float:
    array = array.copy()
    array[[x1, x2], :] = array[[x2, x1], :]
    return array

def swapCol(array:_2dArray_Float, y1:int, y2:int)->None:
    array[:, [y1, y2]] = array[:, [y2, y1]]

def swapCopyCol(array:_2dArray_Float, y1:int, y2:int)->_2dArray_Float:
    array = array.copy()
    array[:, [y1, y2]] = array[:, [y2, y1]]
    return array

def swapCopyRowsCols(array:_2dArray_Float, rows:"list[int]", cols:"list[int]")->_2dArray_Float:
    return array[rows, :][:, cols]

def swapCopyShuffle(array:_2dArray_Float, currRowsCols:"None|tuple[list[int], list[int]]"=None
        )->"tuple[_2dArray_Float, list[int], list[int]]":
    rows:"list[int]" = list(range(array.shape[0]))
    cols:"list[int]" = list(range(array.shape[1]))
    __shuffle(rows); __shuffle(cols)
    __shuffle(rows); __shuffle(cols)
    if currRowsCols is not None:
        rows, cols = combineSwaps(currRowsCols[0], rows, currRowsCols[1], cols)
    return (swapCopyRowsCols(array, rows, cols), rows, cols)

def swapCopySlide(array:_2dArray_Float, xSlide:int, ySlide:int, currRowsCols:"None|tuple[list[int], list[int]]"=None
        )->"tuple[_2dArray_Float, list[int], list[int]]":
    nbRows:int = array.shape[0];   nbCols:int = array.shape[1]
    rows:"list[int]" = [(row - xSlide) % nbRows for row in range(nbRows)]
    cols:"list[int]" = [(col - ySlide) % nbCols for col in range(nbCols)]
    if currRowsCols is not None:
        rows, cols = combineSwaps(currRowsCols[0], rows, currRowsCols[1], cols)
    return (swapCopyRowsCols(array, rows, cols), rows, cols)


def combineSwaps(rows1:"list[int]", rows2:"list[int]", cols1:"list[int]", cols2:"list[int]")->"tuple[list[int], list[int]]":
    """`rows1` and `cols1` are the first swaps applied and `rows2` and `cols2` are the second one"""
    return ([rows1[index] for index in rows2], [cols1[index] for index in cols2])


@numba.jit("float64[:, :](float64[:, :])", nopython=True, nogil=True)
def calcError(array:_2dArray_Float)->_2dArray_Float:
    result = numpy.zeros_like(array)
    nbRows, nbCols = array.shape
    kernelSize:int = 1 # should stay 1 unless one of the error parameter is the dist
    # with wrapping
    for x in range(nbRows):
        for y in range(nbCols):
            val = array[x, y]

            for dx in range(-kernelSize, kernelSize+1):
                x2 = (x + dx) % nbRows
                for dy in range(-kernelSize, kernelSize+1):
                    y2 = (y + dy) % nbCols
                    result[x, y] += abs(val - array[x2, y2])

    """ # without wrapping
    for x in range(nbRows):
        for y in range(nbCols):
            val = array[x, y]

            for dx in range(-kernelSize, kernelSize+1):
                x2 = x + dx
                if (x2 < 0) or (x2 >= nbRows): continue
                for dy in range(-kernelSize, kernelSize+1):
                    y2 = y + dy
                    if (y2 < 0) or (y2 >= nbCols): continue
                    result[x, y] += abs(val - array[x2, y2])"""

    kernelArea:int = (1 + 2*kernelSize) ** 2
    return result / (nbRows * nbRows) / kernelArea

def calcErrorSum(array:_2dArray_Float)->float:
    nbRows, nbCols = array.shape
    xHalf, yHalf = nbRows//2, nbCols//2
    errorMatrix:_2dArray_Float = calcError(array)
    return numpy.sum(errorMatrix) / (xHalf * yHalf)

# NOTE: practicaly correct
def calcSwaps(array:_2dArray_Float, nbStepMax:"int|None"=None, verbose:bool=False)->"tuple[list[int], list[int]]":
    """compute the rows and columns to swap in order to regroup the values of `array`\n
    return respectively the new order of the rows and columns (to appli with `swapCopyRowsCols`)\n
    note: for the corr matrix it is important to input the abs(...) of the matrix because -1 corr is very correlated too !\n"""
    def createTable(array:_2dArray_Float)->"list[tuple[float, int, int]]":
        table:"list[tuple[float, int, int]]" = []
        for row in range(array.shape[0]):
            for col in range(array.shape[1]):
                table.append((array[row][col], row, col))
        return sorted(table)

    array = array.copy()
    nbRows, nbCols = array.shape
    rows = list(range(nbRows))
    columns = list(range(nbCols))


    alreadySwappedRows:"list[int]" = []
    alreadySwappedCols:"list[int]" = []

    pervErrorSum:float
    newErrorSum:float
    errorMatrixRows:_2dArray_Float
    errorMatrixCols:_2dArray_Float
    errorTableRows:"list[tuple[float, int, int]]"
    errorTableCols:"list[tuple[float, int, int]]"
    row1:int ; row2:int
    col1:int ; col2:int

    stuckOnRows:bool
    stuckOnCols:bool
    lastTryImprovedError:"bool|None" # can be renamed: one_of_the_try_did_not_improved_the_error
    nbOfTry:int

    step:int = -1

    while (nbStepMax is None) or (step+1 < nbStepMax):
        step += 1
        if verbose is True:
            print(f"step n°{step}/{nbStepMax}", end="\r", flush=True)



        ######## row part
        # reset the vars
        nbOfTry = 0
        lastTryImprovedError = None
        alreadySwappedRows = []

        # calc the error matrix (for the rows)
        pervErrorSum = calcErrorSum(array)

        errorMatrixRows = numpy.array([
            [calcErrorSum(swapCopyRow(array, row1, row2)) for row2 in range(nbRows)]
            for row1 in range(nbRows)
        ])

        # create the sorted table of rows to swap
        errorTableRows = createTable(errorMatrixRows)

        # swap rows until it cant do better
        while (lastTryImprovedError is not False) or (nbOfTry < nbRows):
            # test if some rows remains
            if len(errorTableRows) == 0:
                break

            # find 2 rows to swap
            _, row1, row2 = errorTableRows.pop(0)
            if row1 == row2:
                # dont count as not improved because it cost nothing
                continue


            # if row already swaped (it had a better swap)
            if (row1 in alreadySwappedRows) or (row2 in alreadySwappedRows):
                # dont count as not improved because it cost nothing
                continue


            # do the swap (dont save it)
            swapRow(array, row1, row2)

            # compute the real new errorSum
            newErrorSum = calcErrorSum(array)
            nbOfTry += 1 # only the trys that are expensives are counted

            # if NO improvements
            if newErrorSum >= pervErrorSum:
                # undo the swap
                swapRow(array, row2, row1)
                # state as did not improved
                lastTryImprovedError = False

            # if improvements
            else:
                # state the swap
                alreadySwappedRows += [row1, row2]
                rows[row1], rows[row2] = rows[row2], rows[row1]

        # test if some swaps have been done (=> improvements)
        stuckOnRows = (len(alreadySwappedRows) == 0)




        ######## col part
        # reset the vars
        nbOfTry = 0
        lastTryImprovedError = None
        alreadySwappedCols = []

        # calc the error matrix (for the cols)
        pervErrorSum = calcErrorSum(array)

        errorMatrixCols = numpy.array([
            [calcErrorSum(swapCopyCol(array, col1, col2)) for col2 in range(nbCols)]
            for col1 in range(nbCols)
        ])

        # create the sorted table of cols to swap
        errorTableCols = createTable(errorMatrixCols)

        # swap rows until it cant do better
        while (lastTryImprovedError is not False) or (nbOfTry < nbCols):
            # test if some cols remains
            if len(errorTableCols) == 0:
                break

            # find 2 rows to swap
            _, col1, col2 = errorTableCols.pop(0)


            # if col already swaped (it had a better swap)
            if (col1 in alreadySwappedCols) or (col2 in alreadySwappedCols):
                # dont count as not improved because it cost nothing
                continue

            # do the swap (dont save it)
            swapCol(array, col1, col2)

            # compute the real new errorSum
            newErrorSum = calcErrorSum(array)
            nbOfTry += 1 # only the trys that are expensives are counted

            # if NO improvements
            if newErrorSum >= pervErrorSum:
                # undo the swap
                swapCol(array, col1, col2)
                # state as did not improved
                lastTryImprovedError = False

            # if improvements
            else:
                # state the swap
                columns[col1], columns[col2] = columns[col2], columns[col1]
                alreadySwappedCols += [col1, col2]




        # test if some swaps have been done (=> improvements)
        stuckOnCols = (len(alreadySwappedCols) == 0)



        if (stuckOnCols is True) and (stuckOnRows is True):
            # can't imporve more
            print(f"finished early at step n°{step}/{nbStepMax}")
            break

    if (nbStepMax != 0) and (verbose is True):
        # clear the current line (no pb if break)
        print(" " * 35, end="\r", flush=True)

    return (rows, columns)



def computeRegroupedMatrix(
        matrix:_2dArray_Float, nbStepMax:"int|None"=None,
        randomizeFirst:bool=False, nbIterations:int=1, verbose:bool=False,
        )->"tuple[_2dArray_Float, list[int], list[int]]":
    """compute the optimale reorder of a given `matrix` in less than `nbStepMax` steps (if given) \n
    in order to have a different result (potentialy better), \
        you can also keep the best of `nbIterations` of randomization\n
    return a copy of the `matrix` (with the swaps applied to regroup the values) and the new order\n"""
    #raise NotImplementedError("nbIter not implemented")
    bestErrorSum:float = calcErrorSum(matrix)
    newErrorSum:float
    bestRowsAll:"list[int]" = list(range(matrix.shape[0]))
    bestColsAll:"list[int]" = list(range(matrix.shape[1]))

    if randomizeFirst is False:
        nbIterations = 1

    for iterStep in range(nbIterations):
        # randomize to get better results
        if randomizeFirst is True:
            if verbose is True:
                print(f"starting iteration step: {iterStep+1}/{nbIterations}")
            # shuffle the matrix (...)
            matrixShuffled, rows1, cols1 = swapCopyShuffle(matrix)
            # main computation
            rows, cols = calcSwaps(matrixShuffled, nbStepMax, verbose)
            # combine the swaps
            rowsAll, colsAll = combineSwaps(rows1, rows, cols1, cols)

        else:
            rowsAll, colsAll = calcSwaps(matrix, nbStepMax, verbose)

        # comput the errorSum and store new best
        newErrorSum = calcErrorSum(swapCopyRowsCols(matrix, rowsAll, colsAll))
        if newErrorSum < bestErrorSum:
            bestErrorSum = newErrorSum
            bestRowsAll = rowsAll
            bestColsAll = colsAll

            if verbose is True:
                print(f"new best error found: {bestErrorSum}")


    return (swapCopyRowsCols(matrix, bestRowsAll, bestColsAll), bestRowsAll, bestColsAll)




