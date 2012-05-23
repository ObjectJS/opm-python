#python
#coding=utf-8

import sys
import os
import os.path
from urlparse import urlparse, urljoin
sys.path.insert(0, 'lib/lxml-2.2.4-py2.6-win32.egg')
from lxml import etree

class XSLTemplate():

    def __init__(self, urlResolver = lambda url: url):
        self.urlResolver = urlResolver
        self.url = ''


    def relativeURI(self, url1, url2):
        ''' url2相对于url1的相对路径字符串 '''
        import re

        # 去掉 ./ 这种表示当前目录的，学习一下 (?<=) 这种前导匹配
        url1 = re.sub(r'(^\./|(?<=/)\./)', lambda m: '', url1)
        url2 = re.sub(r'(^\./|(?<=/)\./)', lambda m: '', url2)
        url1 = url1.split('/')
        url2 = url2.split('/')
        pos = 0
        for i, part in enumerate(url1):
            if url2[i] != part: break
            else: pos = i

        url2 = url2[i:]
        url = len(url1[i+1:]) * '../' + '/'.join(url2)
        return url


    def translatePath(self, url):
        url = urljoin(self.url, url)

        return self.urlResolver(url)


    def compile(self, url, pubdir):
        ''' 执行编译 '''

        self.url = url

        # 执行编译xhtml
        xmlparser = etree.XMLParser()
        xmlparser.resolvers.add(PathResolver(self.translatePath))

        path = self.translatePath(url)
        xml = etree.parse(path)
        pi = xml.getroot().getprevious()
        if not isinstance(pi, etree._XSLTProcessingInstruction):
            return

        print 'Recompiling XHTML'

        xsltpath = pi.get('href')
        xslt = etree.parse(xsltpath, xmlparser)

        try:
            transform = etree.XSLT(xslt)
            resultTree = transform(xml,\
                                   template_mode = etree.XSLT.strparam('publish'),\
                                   template_uri_prefix = etree.XSLT.strparam(self.relativeURI(urljoin(url, '.'), pubdir)),\
                                   template_lint_uri = etree.XSLT.strparam('true')\
                                  )
            result = etree.tostring(resultTree, method='html', encoding='utf-8', pretty_print=True)
        except:
            print 'transform xhtml error.'
            return

        filename = url[len(urljoin(url, '.')):-5] + 'html'
        path = self.translatePath(urljoin(pubdir, filename))
        self.writeFile(path, result)
        
        return resultTree


    def writeFile(self, path, txt):
        print 'generated:', path
        cssfile = open(path, "w")
        cssfile.write(txt)
        cssfile.close()


def getUrls(url, urlResolver = lambda u: u):
    tree = etree.parse(urlResolver(url))
    xsltpath = os.path.abspath('d:/works/xn.static/n/template.xsl')
    xmlparser = etree.XMLParser()
    xmlparser.resolvers.add(PathResolver(urlResolver))
    xslt = etree.parse(xsltpath, xmlparser)
    try:
        transform = etree.XSLT(xslt)
        resultTree = transform(tree,\
                               template_mode = etree.XSLT.strparam('geturls'),\
                               template_lint_uri = etree.XSLT.strparam('true'),\
                               template_server_root = etree.XSLT.strparam('/n/')\
                              )
    except:
        print 'get urls error'
        return []

    result = resultTree.findall('//*')
    arr = []
    for item in result:
        arr.append(urljoin(url, item.text))

    return arr


def main():
    from optparse import OptionParser
    parser = OptionParser('usage: python %prog command [options] args')

    parser.add_option('-p', '--pppp',
                      dest="var",
                      type='string',
                      default=False,
                      help="write afsdafsdaf")

    opts, args = parser.parse_args()

    if len(args) <= 1:
        parser.print_help()
        return

    command = args[0]
    url = args[1]




class PathResolver(etree.Resolver):
    def __init__(self, urlResolver):
        self.urlResolver = urlResolver

    def resolve(self, url, id, context):
        import re
        if re.search(r'^file\:///[a-zA-Z]\:/', url): # file:///d:/works/xn.static/n/apps...
            path = re.sub(r'^file\:///', '', url)
        elif re.search(r'^file\:///', url): # file:///n/apps...
            url = re.sub(r'^file\://', '', url)
            path = self.urlResolver(url)
        else:
            path = self.urlResolver(url)

        try:
            return self.resolve_file(open(path), context)
        except:
            pass


if __name__ == '__main__':
    main()

