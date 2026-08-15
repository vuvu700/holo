import numpy
from typing import Literal


_Iluminant = Literal["A", "B", "C", "D50", "D55", "D65", "D75", "E"]
_Observer = Literal["2", "10", "R"]


# ---------------------------------------------------------------------------
# Constants (values are from skimage)
# ---------------------------------------------------------------------------

XYZ_FROM_RGB = numpy.array([
    [0.412453, 0.357580, 0.180423],
    [0.212671, 0.715160, 0.072169],
    [0.019334, 0.119193, 0.950227],
], dtype=numpy.float64)

RGB_FROM_XYZ = numpy.linalg.inv(XYZ_FROM_RGB)

ILLUMINANTS: dict[_Iluminant, dict[_Observer, tuple[float, float, float]]] = {
    "A": {
        '2': (1.098466069456375, 1, 0.3558228003436005),
        '10': (1.111420406956693, 1, 0.3519978321919493),
        'R': (1.098466069456375, 1, 0.3558228003436005),
    },
    "B": {
        '2': (0.9909274480248003, 1, 0.8531327322886154),
        '10': (0.9917777147717607, 1, 0.8434930535866175),
        'R': (0.9909274480248003, 1, 0.8531327322886154),
    },
    "C": {
        '2': (0.980705971659919, 1, 1.1822494939271255),
        '10': (0.9728569189782166, 1, 1.1614480488951577),
        'R': (0.980705971659919, 1, 1.1822494939271255),
    },
    "D50": {
        '2': (0.9642119944211994, 1, 0.8251882845188288),
        '10': (0.9672062750333777, 1, 0.8142801513128616),
        'R': (0.9639501491621826, 1, 0.8241280285499208),
    },
    "D55": {
        '2': (0.956797052643698, 1, 0.9214805860173273),
        '10': (0.9579665682254781, 1, 0.9092525159847462),
        'R': (0.9565317453467969, 1, 0.9202554587037198),
    },
    "D65": {
        '2': (0.95047, 1.0, 1.08883),
        '10': (0.94809667673716, 1, 1.0730513595166162),
        'R': (0.9532057125493769, 1, 1.0853843816469158),
    },
    "D75": {
        '2': (0.9497220898840717, 1, 1.226393520724154),
        '10': (0.9441713925645873, 1, 1.2064272211720228),
        'R': (0.9497220898840717, 1, 1.226393520724154),
    },
    "E": {'2': (1.0, 1.0, 1.0), '10': (1.0, 1.0, 1.0), 'R': (1.0, 1.0, 1.0)},
}

# CIE fraction-based constants for LAB nonlinearity
_LAB_THRESH_LIN = 6 / 29                 # inverse threshold (on f(t))
_LAB_THRESH_CUBE = _LAB_THRESH_LIN ** 3  # forward threshold (on XYZ ratio)
_LAB_INV_SLOPE = 3 * (6 / 29) ** 2       # inverse linear slope
_LAB_SLOPE = 1 / _LAB_INV_SLOPE          # forward linear slope
_LAB_OFFSET = 4 / 29                     # forward/inverse offset


# ---------------------------------------------------------------------------
# dtype helpers
# ---------------------------------------------------------------------------

def _as_float64(arr: numpy.ndarray):
    """Return (float64 copy of arr, original dtype)."""
    return arr.astype(numpy.float64, copy=True), arr.dtype


def _from_float64(arr: numpy.ndarray, dtype: numpy.dtype, convertBack: bool) -> numpy.ndarray:
    """conditionaly convert back the array to the original dtype"""
    if not convertBack:
        return arr
    return arr.astype(dtype)


# ---------------------------------------------------------------------------
# RGB <-> XYZ conversions
# ---------------------------------------------------------------------------

def rgb2xyz(rgb: numpy.ndarray, convertBack: bool = True) -> numpy.ndarray:
    """Convert (..., 3) sRGB array in [0,1] to XYZ.
    Use `convertBack` to preserve input float dtype."""
    arr, in_dtype = _as_float64(rgb)

    mask = arr > 0.04045
    arr[mask] = ((arr[mask] + 0.055) / 1.055) ** 2.4
    arr[~mask] /= 12.92

    xyz = arr @ XYZ_FROM_RGB.T
    return _from_float64(xyz, in_dtype, convertBack)


def xyz2rgb(xyz: numpy.ndarray, convertBack: bool = True) -> numpy.ndarray:
    """Convert (..., 3) XYZ array to sRGB, clipped unconditionally to [0,1].
    Use `convertBack` to preserve input float dtype."""
    arr, in_dtype = _as_float64(xyz)
    
    rgb = arr @ RGB_FROM_XYZ.T

    mask = rgb > 0.0031308
    rgb[mask] = 1.055 * numpy.power(rgb[mask], 1 / 2.4) - 0.055
    rgb[~mask] *= 12.92

    numpy.clip(rgb, 0, 1, out=rgb)
    return _from_float64(rgb, in_dtype, convertBack)


# ---------------------------------------------------------------------------
# XYZ <-> LAB conversions
# LAB color space: L in [0, 100], a and b in [-100, +100]
# ---------------------------------------------------------------------------

def xyz2lab(xyz: numpy.ndarray, illuminant: _Iluminant = "D65",
            observer: _Observer = "2", convertBack: bool = True) -> numpy.ndarray:
    """Convert (..., 3) XYZ array to LAB.
    Use `convertBack` to preserve input float dtype."""
    arr, in_dtype = _as_float64(xyz)

    white = numpy.array(ILLUMINANTS[illuminant][observer], dtype=numpy.float64)
    arr = arr / white

    mask = arr > _LAB_THRESH_CUBE
    arr[mask] = numpy.cbrt(arr[mask])
    arr[~mask] = _LAB_SLOPE * arr[~mask] + _LAB_OFFSET

    x, y, z = arr[..., 0], arr[..., 1], arr[..., 2]

    L = 116.0 * y - 16.0
    a = 500.0 * (x - y)
    b = 200.0 * (y - z)

    lab = numpy.stack([L, a, b], axis=-1)
    return _from_float64(lab, in_dtype, convertBack)


def lab2xyz(lab: numpy.ndarray, illuminant: _Iluminant = "D65",
            observer: _Observer = "2", convertBack: bool = True,
            ) -> tuple[numpy.ndarray, None|numpy.ndarray]:
    """
    Convert (..., 3) LAB array to XYZ.
    Use `convertBack` to preserve input float dtype.

    Returns
    -------
    xyz : ndarray, converted colors
    invalid : ndarray or None
        Index array of shape (N, lab.ndim - 1) giving the full multi-index
        (one row per invalid element) of positions in `xyz` (excluding the
        channel axis) where the intermediate z value was negative and got
        clipped to 0. None if no clipping was necessary.
    """
    arr, in_dtype = _as_float64(lab)

    L, a, b = arr[..., 0], arr[..., 1], arr[..., 2]
    y = (L + 16.0) / 116.0
    x = a / 500.0 + y
    z = y - b / 200.0

    neg_mask = z < 0
    invalid = numpy.argwhere(neg_mask)
    if invalid.size == 0:
        invalid = None
    else:
        z[neg_mask] = 0.0

    out = numpy.stack([x, y, z], axis=-1)

    mask = out > _LAB_THRESH_LIN
    out[mask] = out[mask] ** 3
    out[~mask] = _LAB_INV_SLOPE * (out[~mask] - _LAB_OFFSET)

    white = numpy.array(ILLUMINANTS[illuminant][observer], dtype=numpy.float64)
    xyz = out * white

    return _from_float64(xyz, in_dtype, convertBack), invalid


# ---------------------------------------------------------------------------
# RGB <-> LAB conversions
# ---------------------------------------------------------------------------

def rgb2lab(rgb: numpy.ndarray, illuminant: _Iluminant = "D65", 
            observer: _Observer = "2", convertBack: bool = True) -> numpy.ndarray:
    """Convert (..., 3) LAB array to XYZ."""
    xyz = rgb2xyz(rgb, convertBack=False)
    return xyz2lab(xyz, illuminant, observer, convertBack=convertBack)


def lab2rgb(lab: numpy.ndarray, illuminant: _Iluminant = "D65",
            observer: _Observer = "2", convertBack: bool = True,
            ) -> tuple[numpy.ndarray, None|numpy.ndarray]:
    """
    Returns
    -------
    rgb : ndarray, same dtype as input
    invalid : ndarray of int or None
        indices array of shape (N, `lab.ndim`) of `xyz` where LAB->XYZ required negative-z clipping. 
        None if no clipping was necessary.
    """
    xyz, invalid = lab2xyz(lab, illuminant, observer, convertBack=False)
    rgb = xyz2rgb(xyz, convertBack=convertBack)
    return rgb, invalid



# ---------------------------------------------------------------------------
# dictinct colors generation
# ---------------------------------------------------------------------------

_Color = tuple[float, float, float]
_ColorsList = list[_Color]

def generer_couleurs_distinctes(
        n, *, randomSampling:bool=False, nb_samples:int=10_000,
        maxLuminance:float=0.9, minLuminance:float=0.1)->_ColorsList:
    """generate `n` differentc colors that maximise the visual difference betwin each others. \n
    Has a time complexity of O(`n` * `nb_samples`). \n
    :param randomSampling: whether to sample random colors or uniformly spaced colors.
        when disabled it is reproducable.
    :param nb_samples: the number of sampls to generate (whith `randomSampling` 
        the exacte numer of samples will be different due to the 3D grid size)
    :param maxLuminance: the maxi rgb luminance of the candidates (this avoid too white colors)
    :param minLuminance: the mini rgb luminance of the candidates (this limit too dark colors)
    :return: a list of `n` rgb colors with values in [0.0, 1.0]
    """
    # generate many RGB colors to sample from (this ensure the candates are valide colors)
    candidates_rgb: numpy.ndarray # (nbCandidates, 3) of float[0, 1]
    if randomSampling:
        candidates_rgb = numpy.random.rand(nb_samples, 3)
        # rescale to the requested range
        candidates_rgb *= (maxLuminance - minLuminance)
        candidates_rgb += minLuminance
    else:
        r = numpy.linspace(minLuminance, maxLuminance, num=int(nb_samples**(1/3)))
        candidates_rgb = numpy.stack([
            x.flatten() for x in numpy.meshgrid(r, r, r)], axis=1)
    nbCandidates = candidates_rgb.shape[0]
    
    # convert the rgb colors to CIE LAB 
    # (distances in that space are based on human perception)
    candidates_lab = rgb2lab(candidates_rgb) # (nbCandidates, 3) of float
    
    if not (1 <= n <= nbCandidates):
        raise ValueError(f"n={n} must be in [1, {nbCandidates}]")

    # greedy farthest-point sampling: apriximation of NP-hard "maximize the minimum pairwise distance"
    # At each step, we select the candidate that is the 
    # 3. Échantillonnage farthest-point vectorisé : on conserve, pour chaque
    # candidate, sa distance au carré à la couleur sélectionnée la plus proche.
    selected_candiates = numpy.empty(n, dtype=int) # (n, ) of int, index of selected candidates
    selected_candiates[0] = 0
    dist_to_selected = numpy.sum((candidates_lab - candidates_lab[0]) ** 2, axis=1) # (nbCandidates, ) of float
    """for each candidate, store the distance of the closest of the selected candidates"""
    dist_to_selected[0] = -numpy.inf # this ensure we never reselect the same, since we select with argmax
    
    # 4. À chaque itération, sélectionner la candidate la plus éloignée de
    # l'ensemble courant, puis mettre à jour toutes les distances en une fois.
    for i in range(1, n):
        best_candidate = numpy.argmax(dist_to_selected)
        """the (non selected) candidate that is the further of any alredy selected candidate"""
        selected_candiates[i] = best_candidate # select it
        new_distances = numpy.sum( # the distances for all candidates with the newly selected 
            (candidates_lab - candidates_lab[best_candidate]) ** 2, axis=1)
        # in place update the distance with the  new candidate
        numpy.minimum(dist_to_selected, new_distances, out=dist_to_selected)
        dist_to_selected[best_candidate] = -numpy.inf # avoid being reselected
    
    # convert back the LAB colors to RGB
    colors_rgb = lab2rgb(candidates_lab[selected_candiates])[0]
    return [(r, g, b) for r, g, b in colors_rgb.tolist()]

 