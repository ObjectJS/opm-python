# coding=utf-8

import os
import os.path
import sys
import getopt
import re
import posixpath
import ConfigParser
import BaseHTTPServer
import SimpleHTTPServer
from SimpleHTTPServer import SimpleHTTPRequestHandler
from BaseHTTPServer import HTTPServer

global csscompiler
global jscompiler
global xsltemplate

DEBUG = False
_defaultServer = ''
_servers = {}

class StaticHTTPRequestHandler(SimpleHTTPRequestHandler):

    serverRoot = ''
    domain = ''

    def parse_request(self):
        result = SimpleHTTPRequestHandler.parse_request(self)

        if self.headers:
            self.domain = self.headers['host'].split(':')[0]

            if self.domain in _servers.keys():
                self.serverRoot = _servers[self.domain]['path']
            else:
                self.serverRoot = _defaultServer

        os.chdir(self.serverRoot)

        return result

    def guess_type(self, path):
        ''' .xhtml的mime-type、IE下的特殊处理 '''

        self.extensions_map['.xhtml'] = r'application/xhtml+xml'
        #self.extensions_map['.xhtml'] = r'text/xml'
        if self.headers.getheader('user-agent').count('MSIE'):
            self.extensions_map['.xhtml'] = r'text/xml'

        return SimpleHTTPRequestHandler.guess_type(self, path)


    def do_GET(self):
        """ Rewrite版本号、监听css/js/html """

        self.path = re.sub('^\/([ab]?\d+?)\/', '/', self.path) # rewrite版本号路径
        path = self.translate_path(self.path)
        ctype = self.guess_type(path)
        if ctype == "text/css":
            if DEBUG:
                reload(csscompiler)

            csscompiler.DEBUG = DEBUG
            csscompiler.listen_css(self.serverRoot,
                                   serverDomain = server.domain,
                                   serverPath = server.path,
                                   referer = server.headers['referer'] if 'referer' in server.headers.keys(),
                                   userAgent = server.headers['user-agent']
                                  )

        if ctype == "text/javascript":
            if DEBUG:
                reload(jscompiler)

            jscompiler.DEBUG = DEBUG
            jscompiler.listen_js(self.serverRoot, self)

        if ctype == "application/xhtml+xml":
            if DEBUG:
                reload(xsltemplate)

            xsltemplate.DEBUG = DEBUG
            xsltemplate.listen_xhtml(self.serverRoot, self)

        if ctype == "text/html":
            if DEBUG:
                reload(xsltemplate)

            xsltemplate.DEBUG = DEBUG
            xsltemplate.listen_xhtml(self.serverRoot, self)

        SimpleHTTPRequestHandler.do_GET(self)


class StaticServer():

    port = 80

    def __init__(self, port):
        confpath = 'server.ini'
        cfg = ConfigParser.RawConfigParser()
        global _defaultServer
        global _servers
        cfg.readfp(open(confpath))

        for section in cfg.sections():
            if section == 'Server0':
                _defaultServer = cfg.get(section, 'path')
            else:
                _servers[cfg.get(section, 'name')] = {
                    'path': cfg.get(section, 'path'),
                }
        self.port = port


    def start(self, ServerClass = BaseHTTPServer.HTTPServer, HandlerClass = StaticHTTPRequestHandler):
        httpd = ServerClass(('', self.port), HandlerClass)
        httpd.serve_forever()


if __name__ == '__main__': 

    PORT = 80

    def showUsage():
        print u"""
        -p, --help:                     输出此信息
        -c path, --compiler path:       定义csscompiler的路径，默认 ../../
        -p port, --port port:           定义服务器监听端口，默认80
        -d, --debug:                    Debug模式
        """.encode(sys.getfilesystemencoding())

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hc:p:d', ['help', 'compiler=', 'port=', 'debug'])
    except getopt.GetoptError:
        showUsage()
        sys.exit(2)


    config = {
        'compiler_path': '../../',
    }
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            showUsage()
            sys.exit()
        elif opt in ('-d', '--debug'):
            DEBUG = True
        elif opt in ('-p', '--port'):
            PORT = int(arg)
        elif opt in ('-c', '--compiler'):
            config['compiler_path'] = os.path.abspath(arg)

    curdir = os.getcwd()
    sys.path.insert(0, os.path.abspath(config['compiler_path']))
    os.chdir(config['compiler_path'])
    csscompiler = __import__('csscompiler')
    jscompiler = __import__('jscompiler')
    xsltemplate = __import__('xsltemplate')
    os.chdir(curdir)

    server = StaticServer(PORT)
    server.start()

