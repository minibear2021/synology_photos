import logging
import os
import shutil
import time

import concurrent-log-handler
import exiftool

nasLogger = logging.getLogger('sspark')
nasLogger.setLevel(logging.DEBUG)
chandler = concurrent-log-handler.ConcurrentRotatingFileHandler(filename='/volume1/download/logs/log.txt', maxBytes=1024 * 1024 * 1, backupCount=10, encoding='utf-8', delay=True)
chandler.setLevel(logging.DEBUG)
formatter = logging.Formatter(fmt='[%(asctime)s] %(levelname)s [%(filename)s:%(lineno)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
chandler.setFormatter(formatter)
nasLogger.addHandler(chandler)

imageSuffix = ['.jpg', '.png', '.heic']
videoSuffix = ['.mp4', '.mov', '.mpeg', '.mpg']

sourceDir = '/volume1/photo/upload/'
imageDir = '/volume1/photo/'
videoDir = '/volume1/photo/video/'
otherDir = '/volume1/photo/others/'


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
        with exiftool.ExifTool() as et:
            metaList = et.get_metadata(filePath)
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
    except:
        nasLogger.debug('excepted with ' + filePath)
    return fileTime


def ProcessMediaFiles(sourceDir, imageTargetDir, videoTargetDir, otherDir):
    files = os.listdir(sourceDir)
    for sourceName in files:
        sourcePath = os.path.join(sourceDir, sourceName)
        if os.path.isdir(sourcePath):
            continue  # 如果需要搜索子目录，注释此行
            if sourcePath.find('@eaDir') < 0:
                ProcessMediaFiles(sourcePath, imageTargetDir, videoTargetDir)
        else:
            nasLogger.debug('source: %s' % sourcePath)

            fileTime = None
            fileName, suffix = os.path.splitext(sourceName)

            if suffix.lower() in imageSuffix:
                targetDir = imageTargetDir
            elif suffix.lower() in videoSuffix:
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

    for sourceName in files:
        # 上一步未处理的文件，全部转入otherDir
        sourcePath = os.path.join(sourceDir, sourceName)
        if os.path.isdir(sourcePath):
            continue
        shutil.move(sourcePath, otherDir)


if __name__ == "__main__":
    nasLogger.debug('start process ...')
    ProcessMediaFiles(sourceDir, imageDir, videoDir, otherDir)
    nasLogger.debug('end process.')
