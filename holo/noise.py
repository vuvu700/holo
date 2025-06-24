import numpy
from types_ext import _2dArray_Float


# -> type hint !
def _perlin(x:_2dArray_Float, y:_2dArray_Float)->_2dArray_Float:
    # permutation table
    p = numpy.arange(256, dtype=int)
    numpy.random.shuffle(p)
    p = numpy.stack([p, p]).flatten()
    # coordinates of the top-left
    xi, yi = x.astype(int), y.astype(int)
    # internal coordinates
    xf, yf = x - xi, y - yi
    # fade factors
    u, v = _fade(xf), _fade(yf)
    # noise components
    n00 = _gradient(p[p[xi] + yi], xf, yf)
    n01 = _gradient(p[p[xi] + yi + 1], xf, yf - 1)
    n11 = _gradient(p[p[xi + 1] + yi + 1], xf - 1, yf - 1)
    n10 = _gradient(p[p[xi + 1] + yi], xf - 1, yf)
    # combine noises
    x1 = _lerp(n00, n10, u)
    x2 = _lerp(n01, n11, u)  
    return _lerp(x1, x2, v) 

def _lerp(a, b, x:_2dArray_Float)->_2dArray_Float:
    "linear interpolation"
    return a + x * (b - a)

def _fade(t):
    "6t^5 - 15t^4 + 10t^3"
    return 6 * t**5 - 15 * t**4 + 10 * t**3

def _gradient(h, x, y):
    "grad converts h to the right gradient vector and return the dot product with (x,y)"
    vectors = numpy.array([[0, 1], [0, -1], [1, 0], [-1, 0]])
    g = vectors[h % 4]
    return g[:, :, 0] * x + g[:, :, 1] * y



def perlin_main(x:float, y:float, x2:float, y2:float, height:int, width:int)->_2dArray_Float:
    """return an array of perlin noise of size `height` * `width`\
        the coordinates of the noise are (x, y) to (x2, y2) included """
    hLin = numpy.linspace(x, x2, height, endpoint=True)
    wLin = numpy.linspace(y, y2, width, endpoint=True)
    x_, y_ = numpy.meshgrid(hLin, wLin)
    return _perlin(x_, y_)
