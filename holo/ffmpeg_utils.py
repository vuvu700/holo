import os
import ffmpeg
import shutil
import tempfile
from pathlib import Path

from .__typing import (
    NamedTuple, _PrettyPrintable, Literal,
    OrderedDict, assertListSubType, assertIsinstance,
    Union, Any, overload,
)
from .pointers import Pointer
from .prettyFormats import (
    prettyPrint, prettyfyNamedTuple, 
    _ObjectRepr, _Pretty_CompactRules,
)



_CudaInterpol = Literal["nearest", "bilinear", "bicubic", "lanczos"]
_SpeedPreset = Literal[
    "ultrafast", "superfast", "veryfast", "faster", "fast",
    "medium", "slow", "slower", "veryslow", "placebo",
]

_Crf_lossLess = Literal[0]
_Crf_veryHigh = Literal[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]
_Crf_high = Literal[18, 19, 20, 21, 22]
_Crf_medium = Literal[23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36]
_Crf_low = Literal[37, 38, 39, 40, 41]
_Crf_veryLow = Literal[42, 43, 44, 45, 46, 47, 48, 49, 50, 51]
_Crf = Union[_Crf_lossLess, _Crf_veryHigh, _Crf_high, _Crf_medium, _Crf_low, _Crf_veryLow]


class Output(NamedTuple):
    succes:bool
    stdout:bytes
    stderr:bytes
        
    def __pretty__(self, compactRules:"_Pretty_CompactRules|None"=None):
        compact:bool = (False if compactRules is None else compactRules.newLine)
        kwargs:"list[tuple[str, _PrettyPrintable]]" = []
        for field in self._fields:
            value = self.__getattribute__(field)
            if (field in ("stdout", "stderr")) and (compact is False):
                value = assertIsinstance(bytes, value).decode()
            kwargs.append((field, value))
        return _ObjectRepr(
            className=self.__class__.__name__,
            args=(), kwargs=OrderedDict(kwargs))


@prettyfyNamedTuple
class ImagesInfos(NamedTuple):
    imagesDir:"Path"
    """where the images are located"""
    imagesNamesPattern:str
    """the pattern to ge the images (like ...%xd..., "image%4d.png")"""
    namesTable:"dict[Path, Path]|None" = None
    """a table associating the original Path of the file to the generated name, in order to revert / remove the files"""
    methodeUsed:"Literal['copy', 'move']|None" = None
    """the methode that was used to generate it, None -> manualy done"""
    
    def getFullPattern(self)->str:
        """return the path and the pattern merged"""
        return self.imagesDir.joinpath(self.imagesNamesPattern).as_posix()
    
    def revert(self, removeDir:bool=True)->None:
        """if possible it will:
         - remove the images if they were copied
         - move back the images if they where moved
        `removeDir` will remove the self.imagesDir (only if self.methodeUsed is setted)"""
        if self.namesTable is None:
            # => can't revert anything
            return None
        # => revert each file
        assert self.methodeUsed is not None, \
            ValueError(f"when a .namesTable is given, .methodeUsed must be given too, in order to revert the images")
        if self.methodeUsed == "copy":
            for copiedImagePath in self.namesTable.values():
                os.remove(copiedImagePath)
        elif self.methodeUsed == "move":
            for originalImagePath, copiedImagePath in self.namesTable.items():
                shutil.move(src=copiedImagePath.as_posix(), dst=originalImagePath)
        else: raise NotImplementedError(f"unsupported self.methodeUsed: {self.methodeUsed}")
        
        if removeDir is True:
            os.rmdir(self.imagesDir) # will raise an error if the dir isn't empty
    
    @classmethod
    def from_imagesList(cls,
            imagesPaths:"list[Path]", methode:"Literal['copy', 'move']",
            imagesExtention:"str|None"=None, tempDir:"Path|None"=None)->"ImagesInfos":
        """setup everything to give the images as input to ffmpeg\n
        `imagesPaths` the paths to each image\n
        `methode`:
         - 'copy' -> will copy each file to a temporary directory
         - 'move' -> will move each file to a temporary directory
        `imagesExtention` the extention of all the images (None -> use the ext of teh first)
        """
        assert len(imagesPaths) > 0, IndexError("empty list of images, wont work")
        # determine the extention of the images
        if imagesExtention is None:
            imagesExtention = imagesPaths[0].suffix
        if imagesExtention.startswith('.'):
            imagesExtention = imagesExtention[1: ]
            
        # create the dir, the pattern
        if tempDir is None:
            tempDir = Path(tempfile.mkdtemp(prefix="images_to_video_tmpDir_"))
        nbImages_nbDigits:int = len(str(len(imagesPaths)))
        imagesNamesPattern = f"img%{nbImages_nbDigits}d.{imagesExtention}"
        getNewFileName = lambda index: tempDir.joinpath(f"img{imageIndex:0{nbImages_nbDigits}d}.{imagesExtention}")
        namesTable:"dict[Path, Path]" = {}

        # move / copy the files
        for imageIndex, imagePath in enumerate(imagesPaths):
            newImagePath:Path = getNewFileName(imageIndex)
            namesTable[imagePath] = newImagePath
            if methode == "copy":
                shutil.copy(imagePath, newImagePath)
            elif methode == "move":
                shutil.move(src=imagePath.as_posix(), dst=newImagePath)
            else: raise NotImplementedError(f"unsupported methode: {methode}")
        
        return ImagesInfos(
            imagesDir=tempDir, imagesNamesPattern=imagesNamesPattern,
            namesTable=namesTable, methodeUsed=methode,
        )

@prettyfyNamedTuple
class Scale(NamedTuple):
    """int+ -> specific size | -1 -> keep ratio | -n -> divide by n | 0 Do not apply interlaced scaling"""
    width:int
    height:int


@prettyfyNamedTuple
class VideoStreamInfos(NamedTuple):
    index:int
    codec_name:str # "h264"
    codec_long_name:str
    codec_tag_string:str
    width:int
    height:int
    pix_fmt:str # "yuv420p"
    field_order:str # "progressive"
    r_frame_rate:str # "25/1"
    duration:float # from "60.080000" seconds
    bit_rate:int # from "512757"
    nb_frames:int # from "1502"

@prettyfyNamedTuple
class AudioStreamInfos(NamedTuple):
    index:int
    codec_name:str # "aac"
    codec_long_name:str
    profile:str # "LC"
    codec_tag_string:str # "mp4a"
    sample_fmt:str # "fltp"
    sample_rate:int # from "44100"
    channels:int
    channel_layout:str # "stereo"
    duration:float # from "60.162902"
    bit_rate:int # from "95999"
    nb_frames:int # from "2591"

@prettyfyNamedTuple
class FormatInfos(NamedTuple):
    filename:str
    nb_streams:int
    nb_programs:int
    format_name:str # "mov,mp4,m4a,3gp,3g2,mj2"
    format_long_name:str
    duration:float # from "60.162902"
    size:int # from "4591940"
    bit_rate:int # from "610600"


@overload
def _convertInfo(rawInfos:"dict[str, Any]", isFormat:Literal[False])->"VideoStreamInfos|AudioStreamInfos": ...
@overload
def _convertInfo(rawInfos:"dict[str, Any]", isFormat:Literal[True])->"FormatInfos": ...
def _convertInfo(rawInfos:"dict[str, Any]", isFormat:bool)->"FormatInfos|VideoStreamInfos|AudioStreamInfos":
    if isFormat is True:
        cls = FormatInfos
    elif rawInfos["codec_type"] == "video":
        cls = VideoStreamInfos
    elif rawInfos["codec_type"] == "audio":
        cls = AudioStreamInfos
    else: raise ValueError(f"unsupported 'codec_type': {rawInfos['codec_type']}")
    
    # convert to cls
    return cls(**{
        key: toType(rawInfos[key]) 
        for key, toType in cls._field_types.items()
    })

class VideoInfos(NamedTuple):
    streams:"list[VideoStreamInfos|AudioStreamInfos]"
    format:FormatInfos
    rawProbDatas:"dict[str, Any]"
    
    def getVideoStreams(self)->"list[VideoStreamInfos]":
        return [streamInfos for streamInfos in self.streams
                if isinstance(streamInfos, VideoStreamInfos)]
    
    def getAudioStreams(self)->"list[AudioStreamInfos]":
        return [streamInfos for streamInfos in self.streams
                if isinstance(streamInfos, AudioStreamInfos)]
    
    @classmethod 
    def fromFilePath(cls, videoPath:Path)->"VideoInfos":
        return VideoInfos._fromRawProbDatas(ffmpeg.probe(videoPath.as_posix()))

    @classmethod 
    def _fromRawProbDatas(cls, rawProbDatas:"dict[str, Any]")->"VideoInfos":
        return VideoInfos(
            streams=[_convertInfo(rawStreamInfos, isFormat=False) 
                     for rawStreamInfos in rawProbDatas["streams"]],
            format=_convertInfo(rawProbDatas["format"], isFormat=True),
            rawProbDatas=rawProbDatas,
        )

    def __pretty__(self, *_, **__):
        resKwargs:"list[tuple[str, _PrettyPrintable]]" = []
        for field in self._fields:
            value = self.__getattribute__(field)
            if field == "rawProbDatas": value = ...
            resKwargs.append((field, value))
        return _ObjectRepr(
            className=self.__class__.__name__,
            args=(), kwargs=OrderedDict(resKwargs))


def ffmpeg_run_stream(
        stream:ffmpeg.Stream, overwrite:bool,
        grabCommand:"Pointer[list[str]]|None"=None)->Output:
    if overwrite is True: stream = ffmpeg.overwrite_output(stream)
    if grabCommand is not None:
        grabCommand.value = assertListSubType(str, ffmpeg.compile(stream))
    try: 
        stdout, stderr = ffmpeg.run(
            stream, capture_stderr=True, capture_stdout=True)
        return Output(succes=True, stdout=stdout, stderr=stderr)
    except ffmpeg.Error as error:
        return Output(succes=False, stdout=error.stdout, stderr=error.stderr)
        

def video_from_images(
        imagesInfos:ImagesInfos, outputPath:Path, framerate:float,
        overwrite:bool=True, grabCommand:"Pointer[list[str]]|None"=None)->Output:
    """combine the images to a video\n
    `imagesInfos` the infos needed to get the images\n
    `framerate` the framerate of the video"""
    images = ffmpeg.input(imagesInfos.getFullPattern())
    output = ffmpeg.output(images, outputPath.as_posix(), framerate=framerate)
    return ffmpeg_run_stream(output, overwrite, grabCommand=grabCommand)




def reprocess_video(
        inputVideoPath:Path, outputPath:Path,
        overwrite:bool=True, grabCommand:"Pointer[list[str]]|None"=None)->Output:
    assert inputVideoPath.exists(), \
        FileNotFoundError(f"the inputVideoPath: {inputVideoPath} don't exist")
    stream:ffmpeg.Stream = ffmpeg.input(inputVideoPath.as_posix())
    videoOutput:ffmpeg.Stream = ffmpeg.output(stream, outputPath.as_posix(), codec="copy")
    return ffmpeg_run_stream(videoOutput, overwrite=overwrite, grabCommand=grabCommand)

def compress_video_lossy(
        inputVideoPath:Path, outputPath:Path, newBitRate:"int|float|None",
        newSize:"Scale|tuple[Scale, _CudaInterpol]|None"=None,
        preset:"_SpeedPreset|None"=None,
        overwrite:bool=True, grabCommand:"Pointer[list[str]]|None"=None)->Output:
    """this will compress the video to the targeted `newBitRate` with the new size from `newSize`\n
    `newBitRate`:
        int -> is the targeted new bitrate
        float -> a multiplicator to the current video bitrate (from the first video stream)
        None -> keep current bitrate
    if `newSize` is given, the outputed video will be of the given size (see Scale.__doc__)\
        when `newSize` is given with a _CudaInterpol, use scale_cuda with the given methode"""
    assert (newBitRate is None) or (newBitRate > 0), \
        ValueError(f"newBitRate: {newBitRate} is invalide")
    assert inputVideoPath.exists(), \
        FileNotFoundError(f"the inputVideoPath: {inputVideoPath} don't exist")
    
    stream:ffmpeg.Stream = ffmpeg.input(inputVideoPath.as_posix())
    
    # additional args (defaults: use H.264 encoder, keep audio)
    additionalArgs:"dict[str, str|int]" = {"c:v": "libx264", "c:a": "copy"}
    
    # bit rate
    if newBitRate is not None:
        if isinstance(newBitRate, float): # => mult of the video's bitrate
            videoInfos = VideoInfos.fromFilePath(inputVideoPath)
            newBitRate = int(newBitRate * videoInfos.getVideoStreams()[0].bit_rate)
        additionalArgs["b:v"] = newBitRate
    
    if preset is not None:
        additionalArgs["preset"] = preset
    
    # resize
    if newSize is not None:
        cudaMethode:"_CudaInterpol|None" = None
        if not isinstance(newSize, Scale):
            newSize, cudaMethode = newSize
        if cudaMethode is None: # => use scale (normal)
            stream = ffmpeg.filter(stream, "scale", *newSize)
        else: # => use scale_cuda
            # NOTE: will not work if ffmpeg wasn't compiled with cuda
            stream = ffmpeg.filter(stream, "scale_cuda", *newSize, interp_algo=cudaMethode)
            additionalArgs["c:v"] = "h264_cuvid"
            additionalArgs["hwaccel"] = "nvdec"
            additionalArgs["hwaccel_device"] = "0"
    
    videoOutput:ffmpeg.Stream = ffmpeg.output(stream, outputPath.as_posix(), **additionalArgs)
    return ffmpeg_run_stream(videoOutput, overwrite=overwrite, grabCommand=grabCommand)

def compress_video_lossless(
        inputVideoPath:Path, outputPath:Path,
        preset:_SpeedPreset, quasiLossless:"Literal[False]|_Crf"=False,
        overwrite:bool=True, grabCommand:"Pointer[list[str]]|None"=None)->Output:
    """this will compress the video without lossing quality with the give speed `preset`\n
    if `quasiLossless` is True, it will use it as crf value, \
        improving file size and file compatibility"""
    assert inputVideoPath.exists(), \
        FileNotFoundError(f"the inputVideoPath: {inputVideoPath} don't exist")
    
    stream:ffmpeg.Stream = ffmpeg.input(inputVideoPath.as_posix())
    
    # additional args (defaults: use H.264 encoder, keep audio)
    additionalArgs:"dict[str, str|int]" = {"c:v": "libx264", "c:a": "copy"}
    additionalArgs["preset"] = preset
    if quasiLossless is False: # => true lossless
        additionalArgs["qp"] = 0
    else: # => quasi lossless
        additionalArgs["crf"] = quasiLossless
        
    
    videoOutput:ffmpeg.Stream = ffmpeg.output(stream, outputPath.as_posix(), **additionalArgs)
    return ffmpeg_run_stream(videoOutput, overwrite=overwrite, grabCommand=grabCommand)


def generateVideoThumbnail(
        inputVideoPath:Path, outputPath:Path,
        overwrite:bool=True, grabCommand:"Pointer[list[str]]|None"=None)->Output:
    """return best thumbnail of the video"""
    assert inputVideoPath.exists(), \
        FileNotFoundError(f"the inputVideoPath: {inputVideoPath} don't exist")
    stream:ffmpeg.Stream = ffmpeg.input(inputVideoPath.as_posix())
    additionalArgs:"dict[str, str|int]" = {"vf":"thumbnail", "frames:v": 1}
    videoOutput:ffmpeg.Stream = ffmpeg.output(stream, outputPath.as_posix(), **additionalArgs)
    return ffmpeg_run_stream(videoOutput, overwrite=overwrite, grabCommand=grabCommand)

def generateVideoMultiThumbnails(
        inputVideoPath:Path, outputPath:Path, 
        nbThumbnails:int, minimumFrameDelta:float=0.4,
        overwrite:bool=True, grabCommand:"Pointer[list[str]]|None"=None)->Output:
    """return nth best thumbnails of the video\n
    NOTE: the file name of `outputPath` must be a pattern like: 'image%..d.png'"""
    assert 0. <= minimumFrameDelta <= 1.0, ValueError(f"invalide minimumFrameDelta: {minimumFrameDelta}, must be inside [0. -> 1.]")
    assert inputVideoPath.exists(), \
        FileNotFoundError(f"the inputVideoPath: {inputVideoPath} don't exist")
    stream:ffmpeg.Stream = ffmpeg.input(inputVideoPath.as_posix())
    additionalArgs:"dict[str, str|int]" = {
        "vf": f"select=gt(scene\\,{minimumFrameDelta})",
        "frames:v": nbThumbnails, 
        "vsync": "vfr",
    }
    videoOutput:ffmpeg.Stream = ffmpeg.output(stream, outputPath.as_posix(), **additionalArgs)
    return ffmpeg_run_stream(videoOutput, overwrite=overwrite, grabCommand=grabCommand)


def addVideoThumbnail(
        inputVideoPath:Path, thumbnailPath:Path, outputPath:Path,
        overwrite:bool=True, grabCommand:"Pointer[list[str]]|None"=None)->Output:
    """create a new video from `inputVideoPath` with the image at `tumbnailPath` as a thumbnail"""
    assert inputVideoPath.exists(), FileNotFoundError(f"the inputVideoPath: {inputVideoPath} don't exist")
    assert thumbnailPath.exists(), FileNotFoundError(f"the tumbnailPath: {thumbnailPath} don't exist")
    stream:ffmpeg.Stream = ffmpeg.input(inputVideoPath.as_posix())
    thumbnailStream:ffmpeg.Stream = ffmpeg.input(thumbnailPath.as_posix())
    imagesExtention:str = thumbnailPath.suffix[1: ] # remove the '.' (and don't allow no extention)
    additionalArgs:"dict[str, str|int]" = {
        "c": "copy", "c:v:1": imagesExtention,
        "disposition:v:1": "attached_pic"}
    videoOutput = ffmpeg.output(stream, thumbnailStream, outputPath.as_posix(), **additionalArgs)
    return ffmpeg_run_stream(videoOutput, overwrite=overwrite, grabCommand=grabCommand)
    
    
"""
command:"Pointer[list[str]]" = Pointer()
res = video_from_images(
    ImagesInfos(
        imagesDir=Path("X:/documents/video/genVideoTest/out"),
        imagesNamesPattern="image%4d.png"),
    outputPath=Path("video.mp4"),
    framerate=24.99, overwrite=True, grabCommand=command,
)
print(command.value)
prettyPrint(res)
"""

"""
command:"Pointer[list[str]]" = Pointer()
srcDir:Path = Path("X:/documents/video/genVideoTest/out/")
images = ImagesInfos.from_imagesList(
    imagesPaths=[srcDir.joinpath(name) for name in os.listdir(srcDir) if name.startswith("image")],
    methode="copy")
prettyPrint(images)

res = video_from_images(
    imagesInfos=images,
    outputPath=Path("out.mp4"),
    framerate=24.99, overwrite=True, grabCommand=command,
)
prettyPrint(res)
images.revert()
"""

"""
from .prettyFormats import prettyTime
presets = ["ultrafast", "superfast", "veryfast", "faster", "fast",
    "medium", "slow", "slower", "veryslow", "placebo"]
prof = Profiler(presets)
CRF:_Crf_veryHigh = 17
for index, preset in enumerate(presets):
    with prof.mesure(preset):
        res = compress_video_lossless(
            inputVideoPath=Path("video.mp4"),
            outputPath=Path(f"video_compressed_{index}-{preset}.mp4"),
            preset=preset, quasiLossless=CRF, overwrite=True,
        )
    print(preset, res.succes)
prettyPrint(prof.avgTimes(), specificFormats={float: prettyTime})
"""

"""
from .prettyFormats import prettyTime
bRates = [50, 100, 500, 1_000, 5_000]
prof = Profiler(bRates)
for index, rate in enumerate(bRates):
    with prof.mesure(rate):
        res = compress_video_lossy(
            inputVideoPath=Path("video.mp4"),
            outputPath=Path(f"video_compressed_bRate-{rate:06_d}k.mp4"),
            newBitRate=rate*1000, preset="veryslow", overwrite=True,
        )
    print(rate, res.succes)
prettyPrint(prof.avgTimes(), specificFormats={float: prettyTime})
"""

"""
from .prettyFormats import prettyTime
bRates = [0.5, 0.75, 0.9, 1.0, 1.2, 1.5]
prof = Profiler(bRates)
for index, rate in enumerate(bRates):
    with prof.mesure(rate):
        res = compress_video_lossy(
            inputVideoPath=Path("video.mp4"),
            outputPath=Path(f"video_compressed_bRateFactor-{rate:1.2f}.mp4"),
            newBitRate=rate, preset="slower", overwrite=True,
        )
    print(rate, res.succes)
prettyPrint(prof.avgTimes(), specificFormats={float: prettyTime})
"""

"""
res = generateVideoThumbnail( 
    inputVideoPath=Path("video.mp4"), 
    outputPath=Path(f"bestThumbnail.png"),
)
prettyPrint(res)
"""

"""
res = generateVideoMultiThumbnails( 
    inputVideoPath=Path("video.mp4"), 
    outputPath=Path(f"bestThumbnails%02d.png"),
    nbThumbnails=10, minimumFrameDelta=0.4,
)
prettyPrint(res)
"""

pass

