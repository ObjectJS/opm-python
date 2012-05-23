#python
#coding=utf-8

import re

def base64Encode(localpath):
    ''' base64 '''

    import StringIO

    if os.path.exists(localpath):
        localfile = open(localpath, 'rb')
        base64io = StringIO.StringIO()
        base64.encode(localfile, base64io)
        base64str = base64io.getvalue()
        localfile.close()
        base64io.close()
        return base64str.replace('\n', '')

    return ""


def cssDataURI(css):
    ''' data-uri '''

    on = re.search(r'\/\*DATA_URI=TRUE\*\/', css)
    if not on:
        return css

    def urlReplace(m):
        url = m.group(1)
        localpath = self.translatePath(url)
        if localpath:
            if not mimetypes.inited:
                mimetypes.init() # get system mime.types

            base64str = base64Encode(localpath)
            if not base64str:
                newurl = url
            else:
                newurl = 'data:' + mimetypes.types_map[os.path.splitext(localpath)[1]] + ';base64,' + base64str
        else:
            newurl = url

        return 'url(\'' + newurl + '\')'

    return re.sub(r'url\([\'"]?(.+?)[\'"]?\)', urlReplace, css)


def cssIEDataURI(basename, css):
    ''' data-uri '''

    on = re.search(r'\/\*DATA_URI=TRUE\*\/', css)
    if not on:
        return css

    mhtmlSeparator = '_MY_BOUNDARY_SEPARATOR'
    mhtmlName = '_' + basename + '.mhtml.css'
    mhtml = 'Content-Type: multipart/related; boundary="' + mhtmlSeparator + '"' + 2 *'\n' 
    pi = 0

    def createMHTMLSection(path, pi):
        filename = os.path.basename(path)
        section = '--' + mhtmlSeparator + '\n' \
                + 'Content-Location:file' + str(pi) + '\n' \
                + 'Content-Transfer-Encoding:base64' + 2 * '\n' \
                + base64Encode(path) + '\n' 

        return section

    def urlReplace(m, pi, mhtml):
        url = m.group(1)
        localpath = self.translatePath(url)
        if localpath:
            if not mimetypes.inited:
                mimetypes.init() # get system mime.types

            mhtml += createMHTMLSection(localpath, pi)

            newurl = 'mhtml:' + self.rooturl + urljoin(self.cururl, mhtmlName) + '!file' + str(pi)
        else:
            newurl = url

        pi += 1

        return 'url(\'' + newurl + '\')'

    css = re.sub(r'url\([\'"]?(.+?)[\?&]uri-data=(.+?)[\'"]?\)', lambda m: urlReplace(m, pi, mhtml), css)

    mhtmlfile = open(self.translatePath(mhtmlName), "w")
    mhtmlfile.write(mhtml)
    mhtmlfile.close()

    return css

    def getSpriteConf(self, spritePath):
        ''' 读取 sprite 配置文件为conf对象 '''

        confPath = spritePath + '.conf'

        try:
            confFile = open(confPath, 'r')
        except:
            return {}

        confList = confFile.read().split('\n')
        conf = {}
        for c in confList:
            if c != '':
                l = c.split(' ')
                if l[0] == 'define':
                    key = l[1]
                    conf[key] = l[2:]
                    conf[key][0] = int(conf[key][0])
                    conf[key][1] = int(conf[key][1])
                    conf[key].append(True)
                else:
                    key = l[0]
                    conf[key] = l[1:]
                    conf[key][0] = int(conf[key][0])
                    conf[key][1] = int(conf[key][1])
                    conf[key].append(False)
        
        confFile.close()

        return conf

    
    def setSpriteConf(self, spritePath, conf):
        ''' 将conf配置写入到sprite配置文件中 '''

        result = sorted(conf.items(), key = lambda (k, v): (v[0], v[1]))

        confStr = ''
        for c in result:
            key = c[0]
            value = c[1]
            if value[2] == True:
                confStr += 'define '

            confStr += ' '.join([key, str(value[0]), str(value[1])])
            confStr += '\n'

        confPath = spritePath + '.conf'
        confFile = open(confPath, 'w')
        confFile.write(confStr)
        confFile.close()


    def cssSprite(self, rule):
        ''' 处理 background 属性，生成 CSS Sprite '''

        def relativePath(url1, url2):
            ''' 给出url2相对于url1的相对路径字符串 '''

            # 去掉 ./ 这种表示当前目录的，学习一下 (?<=) 这种前导匹配
            url1 = re.sub(r'(^\./|(?<=/)\./)', lambda m: '', url1)
            url2 = re.sub(r'(^\./|(?<=/)\./)', lambda m: '', url2)
            url1 = url1.split('/')
            url2 = url2.split('/')
            pos = 0
            for i, part in enumerate(url1):
                if url2[i] != part:
                    break
                else:
                    pos = i

            url2 = url2[i:]
            return (len(url1[i:]) - len(url2)) * '../' + '/'.join(url2)

        match = re.search('url\(([a-zA-Z0-9\.\/_-]+)\?sprite=([a-zA-Z0-9\.\/_-]+)(?:\&left\=(-?\d+))?(?:\&top\=(-?\d+))?\)\s+.+?\s+(0|left|\d+px)?\s+(0|top|\d+px)?', self.getStyle('background'))
        if match:
            sourceUrl, spriteUrl, left, top, positionX, positionY = match.groups()

            # 如果给出了left或者top的定位信息，则通过这个信息定位图片，否则为非编译模式，仅读取
            compileMode = bool(left or top)

            left = int(left) if left else 0
            top = int(top) if top else 0

            positionX = int(positionX.replace('px', '')) if positionX not in (None, 'left') else 0
            positionY = int(positionY.replace('px', '')) if positionY not in (None, 'top') else 0

            spriteUrl = urljoin(sourceUrl, spriteUrl)

            # 修改css中的background-image和background-position属性为新的图片和定位信息，此定位信息不可从配置文件中获取，以确保css文件中写的定位信息是准确的。
            self.rule.style.backgroundImage = 'url(' + spriteUrl + ')'
            self.rule.style.backgroundPosition = str(-left + positionX) + 'px ' + str(-top + positionY) + 'px'

            # 将此文件加入到待处理数组中，处理完整个css文件后通过调用doSprite生成图片文件
            if spriteUrl not in self.sprites:
                self.sprites.append(spriteUrl)

            # 编译模式，更新配置文件
            if compileMode:
                sourceKey = relativePath(spriteUrl, sourceUrl) # 文件的相对路径为conf的key
                spritePath = self.compiler.translatePath(spriteUrl)
                conf = self.getSpriteConf(spritePath)
                if not (sourceKey in conf.keys() and conf[sourceKey][2] == True):
                    # 图片需要被处理
                    conf[sourceKey] = [left, top, False]
                    self.setSpriteConf(spritePath, conf)


    def doSprite(self):
        ''' 每个css文件仅执行一次CSS Sprite图片合并，在css编译结束前调用一次 '''

        for spriteUrl in self.sprites:
            spritePath = self.compiler.translatePath(spriteUrl)
            conf = self.getSpriteConf(spritePath)

            cmd = 'convert'
            for key in conf:
                value = conf[key]
                sourcePath = self.compiler.translatePath(urljoin(spriteUrl, key))
                cmd += ' -page +' + str(value[0]) + '+' + str(value[1]) + ' ' + sourcePath

            cmd += ' -background none -mosaic png8:' + spritePath

            os.system(cmd)
            print 'generated css sprite:', spriteUrl

        self.sprites = []

