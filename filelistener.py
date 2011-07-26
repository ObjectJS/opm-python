#python
#encoding=utf-8

import os
import re
from urllib import quote_plus, unquote_plus

class FileListener():
    ''' 文件改动监控 '''

    def __init__(self, fileInfoPath):
        self.fileInfoPath = fileInfoPath

    def get_files(self):
        files = []
        for file in os.listdir(self.fileInfoPath):
            files.append(unquote_plus(file))

        return files

    def writeChanges(self, path, info):
        u''' 将文件改动信息写入到文件中 '''

        hash = quote_plus(path)
        filename = os.path.join(self.fileInfoPath, hash)

        text = ''
        info = sorted(info.items(), key = lambda d: d[0])
        for path, timestamp in info:
            text += '"%s" %s\n' % (path, timestamp)

        try:
            file = open(filename, 'w')
        except:
            return 

        file.write(text)
        file.close()

    def getChanges(self, path):
        ''' 通过缓存文件读取改动配置信息 '''

        hash = quote_plus(path)
        filename = os.path.join(self.fileInfoPath, hash)

        try:
            file = open(filename, 'r')
        except:
            dir = os.path.dirname(filename)
            if not os.path.exists(dir): os.makedirs(dir)
            file = open(filename, 'w').write('')
            file = open(filename, 'r')

        lines = file.readlines()
        info = {}
        for line in lines:
            match = re.match(r'^\"(.+?)\"\s+?([\d\.]+?)$', line)
            if match:
                path, timestamp = match.groups()
                path = os.path.realpath(path)
                info[path] = timestamp

        return info

    def check(self, file, files, fake = False):
        modified = []
        not_exists = []

        # 假的，每次都返回全都改过，测试用
        if fake:
            return (files, [])

        if file.__class__ == dict:
            info = file
        else:
            info = self.getChanges(file)

        for path in files:
            path = os.path.realpath(path) # lint
            if not os.path.exists(path):
                not_exists.append(path)
                # 如果存有信息，但是文件已经不存在了，说明文件曾经有过，现在被删除了，需要把信息也删除，并执行重写
                # 如果没有信息，文件也不存在，说明路径写错了，无需重写信息，只需返回not_exists就可以了
                if path in info.keys():
                    del info[path]

            else:
                timestamp = str(os.stat(path).st_mtime)
                if path not in info.keys() or timestamp != info[path]:
                    info[path] = timestamp
                    modified.append(path)

        return modified, not_exists

    def update(self, file, files, fake = False):
        info = self.getChanges(file)
        modified, not_exists = self.check(info, files, fake = fake)

        if len(modified) or len(not_exists):
            self.writeChanges(file, info)

        return modified, not_exists
