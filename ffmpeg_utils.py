import os
import ffmpeg
import shutil
import tempfile
from pathlib import Path

from holo.__typing import (
    NamedTuple, _PrettyPrintable, Literal,
    OrderedDict, assertListSubType, assertIsinstance,
)
from holo.pointers import Pointer
from holo.prettyFormats import (
    prettyPrint, prettyfyNamedTuple, 
    _ObjectRepr, _Pretty_CompactRules,
)






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
            imagesExtention:"str|None"=None)->"ImagesInfos":
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
        tempDir:Path = Path(tempfile.mkdtemp(prefix="images_to_video_tmpDir_"))
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
                





def ffmpeg_run_stream(stream:ffmpeg.Stream)->Output:
    try: 
        stdout, stderr = ffmpeg.run(stream, capture_stderr=True, capture_stdout=True)
        return Output(succes=True, stdout=stdout, stderr=stderr)
    except ffmpeg.Error as error:
        return Output(succes=False, stdout=error.stdout, stderr=error.stderr)
        

def video_from_images(
        imagesInfos:ImagesInfos, outputPath:Path, framerate:float,
        overwrite:bool, grabCommand:"Pointer[list[str]]|None"=None)->Output:
    """combine the images to a video\n
    `imagesInfos` the infos needed to get the images\n
    `outputPath` the path of the outputed video\n
    `framerate` the framerate of the video\n
    `overwrite` whether to overwite the file it it alredy exist"""
    images = ffmpeg.input(imagesInfos.getFullPattern())
    output = ffmpeg.output(images, outputPath.as_posix(), framerate=framerate)
    if overwrite is True:
        output = ffmpeg.overwrite_output(output)
    if grabCommand is not None:
        grabCommand.value = assertListSubType(str, ffmpeg.compile(output))
    return ffmpeg_run_stream(output)




def reprocess_video(inputVideoPath:Path)->None:
    ...
    
def compress_video(inputVideoPath:Path)->None:
    ...


"""
command:"Pointer[list[str]]" = Pointer()
res = video_from_images(
    ImagesInfos(imagesDir=Path("tmp"), imagesNamesPattern="image%4d.png"),
    outputPath=Path("tmp/out.mp4"),
    framerate=24.99, overwrite=True, grabCommand=command,
)
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

pass

