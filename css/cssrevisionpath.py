#python
#coding=utf-8

import re
import os
import os.path
from urlparse import urlparse, urljoin
from xml.etree import ElementTree

def generateRevisionUrl(url, compiler):
    ''' 生成版本号路径 '''

    localpath = compiler.translatePath(url)
    if not (localpath and os.path.exists(localpath)):
        # 本地不存在这个文件，返回原始url
        return url

    newurl = urljoin(compiler.cururl, url).split('/')
    urlarr = []
    lastRevisionUrl = ''
    lastPart = ''
    lastRevision = ''
    for i in range(len(newurl), 0, -1):
        part = newurl[i - 1]
        localpath = '/'.join(newurl[0:i])
        if localpath == '':
            localpath = '/'

        localpath = compiler.translatePath(localpath)

        infoXml = ElementTree.fromstring(os.popen('svn info --xml %s' % localpath).read())
        revisionUrl = infoXml.find('entry/url').text
        revision = infoXml.find('entry/commit').attrib['revision']

        if revisionUrl + '/' + lastPart != lastRevisionUrl:
            if lastRevision:
                #urlarr[-1] = urlarr[-1] + 'a%s' % lastRevision
                urlarr.append('%s' % lastRevision)
                
            lastRevision = revision

        urlarr.append(part)
        lastRevisionUrl = revisionUrl
        lastPart = part

    urlarr.insert(-1, '%s' % lastRevision)
    newurl = '/'.join(urlarr[::-1])

    return newurl


def generateRevisionUrl2(url, compiler):
    ''' 新版生成版本号路径 '''

    localpath = compiler.translatePath(url)
    if not (localpath and os.path.exists(localpath)):
        # 本地不存在这个文件，返回原始url
        return url

    newurl = urljoin(compiler.cururl, url)
    infoXml = ElementTree.fromstring(os.popen('svn info --xml %s' % localpath).read())
    revision = infoXml.find('entry/commit').attrib['revision']
    repositoryUrl = infoXml.find('entry/repository/root').text
    repositoryName = ElementTree.fromstring(os.popen('svn propget --xml xn:name %s' % repositoryUrl).read()).find('target/property').text
    #newurl = '/' + repositoryName + '_' + revision + newurl
    newurl = '/' + 'a' + revision + newurl

    return newurl


def generateRevisionUrl3(url, compiler):
    localpath = compiler.translatePath(url)
    if not (localpath and os.path.exists(localpath)):
        # 本地不存在这个文件，返回原始url
        return url

    newurl = 'http://xnimg.cn' + urljoin(compiler.puburl, url)

    return newurl


def cssRevisionPath(css, compiler):
    ''' 给css中的所有 url() (包括import url，但是此时import应该已经被替换成内容了) 增加版本号 '''

    prefix = re.search(r'\/\*Prefix=(.+?)\*\/', css)
    if prefix:
        prefix = prefix.group(1)
    else:
        prefix = compiler.urlPrefix

    def urlReplace(m):
        url = m.group(1)
        # 去掉 http 前缀
        if url.startswith(compiler.urlPrefix):
            url = url[len(compiler.urlPrefix):]

        newurl = generateRevisionUrl3(url, compiler)

        return 'url(' + newurl + ')'

    return re.sub(r'url\([\'"]?(.+?)[\'"]?\)', urlReplace, css)



