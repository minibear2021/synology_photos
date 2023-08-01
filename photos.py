import logging
import os
import shutil
import time
import zipfile

import concurrent_log_handler
import exiftool
import pillow_heif
from PIL import Image

nasLogger = logging.getLogger('photos')
nasLogger.setLevel(logging.DEBUG)
chandler = concurrent_log_handler.ConcurrentRotatingFileHandler(filename='/volume1/download/logs/log.txt', maxBytes=1024 * 1024 * 1, backupCount=10, encoding='utf-8', delay=True)
chandler.setLevel(logging.DEBUG)
formatter = logging.Formatter(fmt='[%(asctime)s] %(levelname)s [%(filename)s:%(lineno)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
chandler.setFormatter(formatter)
nasLogger.addHandler(chandler)

imageSuffix = ['.jpg', '.png', '.heic', '.livp']
videoSuffix = ['.mp4', '.mov', '.mpeg', '.mpg']

sourceDir = '/volume1/photo/upload/'
imageDir = '/volume1/photo/'
videoDir = '/volume1/photo/video/'
otherDir = '/volume1/photo/others/'


# 是否解压livp文件
unzipLivp = True

# 是否将heic文件转换为jpg格式
heic2jpg = True

# jpeg图片质量，0至100，默认90
jpgQuality = 95


def CompareFileSize(source, target):
    """
    compare file size
    """
    if not os.path.exists(target) or os.path.getsize(source) > os.path.getsize(target):
        return True
    else:
        return False


def DecodeMediaTime(filePath):
    fileTime = None
    try:
        with exiftool.ExifToolHelper() as et:
            metaList = et.get_metadata(filePath)
            if type(metaList) == list:
                metaList = metaList[0]
            if metaList:
                if 'EXIF:DateTimeOriginal' in metaList:  # photo
                    timeStamp = metaList['EXIF:DateTimeOriginal']
                    nasLogger.debug('EXIF:DateTimeOriginal@' + timeStamp)
                elif 'QuickTime:MediaCreateDate' in metaList:
                    timeStamp = metaList['QuickTime:MediaCreateDate']
                    nasLogger.debug('QuickTime:MediaCreateDate@' + timeStamp)
                elif 'QuickTime:TrackCreateDate' in metaList:
                    timeStamp = metaList['QuickTime:TrackCreateDate']
                    nasLogger.debug('QuickTime:TrackCreateDate@' + timeStamp)
                elif 'File:FileType' in metaList and metaList['File:FileType'] == 'MPEG':
                    timeStamp = metaList['File:FileModifyDate'][0:19]
                    nasLogger.debug('File:FileModifyDate@' + timeStamp)
                else:
                    timeStamp = None
                    nasLogger.debug("timeStamp@None")
                if timeStamp:
                    fileTime = time.strptime(timeStamp, '%Y:%m:%d %H:%M:%S')
    except Exception as e:
        nasLogger.debug(f'excepted at {filePath} with {e}')
    return fileTime


def ProcessMediaFiles(sourceDir, imageTargetDir, videoTargetDir, otherDir):
    files = os.listdir(sourceDir)
    for sourceName in files:
        sourcePath = os.path.join(sourceDir, sourceName)
        if os.path.isdir(sourcePath):
            continue  # 如果需要搜索子目录，注释此行
            if sourcePath.find('@eaDir') < 0:  # 忽略群晖自动生成的目录
                ProcessMediaFiles(sourcePath, imageTargetDir, videoTargetDir, otherDir)
        else:
            nasLogger.debug('source: %s' % sourcePath)

            fileTime = None
            fileName, suffix = os.path.splitext(sourceName)
            suffix = suffix.lower()

            if suffix in imageSuffix:
                if suffix == '.livp' and unzipLivp:
                    unzipedFileName = UnzipLivp(sourcePath, sourceDir)
                    if not unzipedFileName:
                        continue
                    sourceName = unzipedFileName
                    fileName, suffix = os.path.splitext(sourceName)
                    sourcePath = os.path.join(sourceDir, sourceName)
                if suffix == '.heic' and heic2jpg:
                    jpegFileName = Heic2Jpeg(sourceDir, sourceName, sourceDir)
                    if not jpegFileName:
                        continue
                    sourceName = jpegFileName
                    suffix = '.jpg'
                    sourcePath = os.path.join(sourceDir, sourceName)
                targetDir = imageTargetDir
            elif suffix in videoSuffix:
                targetDir = videoTargetDir
            else:
                continue  # 跳过不需要处理的文件类型

            fileTime = DecodeMediaTime(sourcePath)

            if fileTime:
                year = time.strftime('%Y', fileTime)
                month = time.strftime('%m', fileTime)
                targetPath = os.path.join(targetDir, year)
                if not os.path.exists(targetPath):
                    os.mkdir(targetPath)
                targetPath = os.path.join(targetDir, year, month)
                if not os.path.exists(targetPath):
                    os.mkdir(targetPath)
                targetName = time.strftime('%Y-%m-%d %H%M%S', fileTime) + suffix
                targetPath = os.path.join(targetDir, year, month, targetName)
                if CompareFileSize(sourcePath, targetPath):
                    nasLogger.debug('target: %s' % targetPath)
                    # 测试的时候注释下面三行，正式运行时取消注释
                    shutil.move(sourcePath, targetPath)
                else:
                    os.remove(sourcePath)  # 已经存在的文件，尺寸较小者直接删除

    files = os.listdir(sourceDir)
    for sourceName in files:
        # 上一步未处理的文件，全部转入otherDir
        sourcePath = os.path.join(sourceDir, sourceName)
        if os.path.isdir(sourcePath):
            continue
        try:
            shutil.move(sourcePath, otherDir)
        except:
            pass


def UnzipLivp(livpFilePath, targetDir):
    """
    decompress livp file
    """
    with zipfile.ZipFile(livpFilePath) as zf:
        for zf_filename in zf.namelist():
            filename = zf_filename.lower()
            if filename.endswith('.heic') or filename.endswith('.jpeg'):
                zf.extract(zf_filename, targetDir)
                os.remove(livpFilePath)
                return zf_filename
    return None


def Heic2Jpeg(sourceDir, heicFileName, targetDir):
    """
    convert heic to jpeg
    """
    try:
        heifFilePath = os.path.join(sourceDir, heicFileName)
        heifFile = pillow_heif.read_heif(heifFilePath)
        image = Image.frombytes(heifFile.mode, heifFile.size, heifFile.data, 'raw')
        fileName, suffix = os.path.splitext(heicFileName)
        jpgFileName = fileName + '.jpg'
        jpgFilePath = os.path.join(targetDir, jpgFileName)
        dictionary = heifFile.info
        exif_dict = dictionary['exif']
        image.save(jpgFilePath, format='jpeg', quality=jpgQuality, exif=exif_dict)
        os.remove(heifFilePath)
        return jpgFileName
    except Exception as e:
        nasLogger.exception(e)
        return None


if __name__ == "__main__":
    nasLogger.debug('start process ...')
    ProcessMediaFiles(sourceDir, imageDir, videoDir, otherDir)
    nasLogger.debug('end process.')
