#python
#coding=utf-8

import os
import sys
import re
import base64
import mimetypes
import logging
from urlparse import urlparse, urljoin

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'cssutils-0.9.7a3-py2.6.egg'))
import cssutils
import cssutils.cssproductions

import css.cssselectorcompiler as cssselectorcompiler
import css.cssrulecompiler as cssrulecompiler

reload(cssselectorcompiler)
reload(cssrulecompiler)

DEVELOPMENT = True
DEBUG = False
SUPPORT_COMPILE_MODE = ('std', 'ie6', 'ie7', 'all') # TODO:需要一个 allie 的mode，以避免IE条件注释的bug造成的影响

cssutils.cssproductions.PRODUCTIONS.insert(1, cssutils.cssproductions._DXImageTransform) # 从settings中获得的代码，支持DXImageTransform
cssutils.cssproductions.PRODUCTIONS.insert(1, ('FUNCTION', r'\(?\s*function\s*\(({ident},?\s*)*\)\s*\{(\s|\S)*?\}\s*\)?\((({ident}|\.),?\s*)*\)'))
cssutils.cssproductions.PRODUCTIONS.insert(1, ('EXPRESSIONJS', r'Expressions(\.\S+?)+?\(.+?\);'))
cssutils.cssproductions.MACROS['ident'] = r'[-\*]?{nmstart}{nmchar}*' # 支持 *zoom 形式的 IE7 hack
cssutils.profile.removeProfile(all=True)
cssutils.log.setLevel(logging.ERROR)

cssutils.ser.prefs.useDefaults()
#if DEBUG:
    #cssutils.ser.prefs.useDefaults()
#else:
    #cssutils.ser.prefs.useMinified()


class CSSCompiler():
    ''' CSS Compiler '''


    def __init__(self, pathTransformer = lambda path: path):

        self.__selectorHacks = []
        self.pathTransformer = pathTransformer


    def getOptions(self, css):
        '''
        selector-compile: none, all, no-combinator
        rule-compile: none, all
        '''
        profile = None
        options = {}
        profileText = re.search(r'@-css-compiler-profile\s+[\'\"](.+?)[\'\"];', css)
        optionText = re.search(r"""
                                  @-css-compiler\s*{
                                  ((?:\s*?(?:\S+)\s*:\s*(?:.*);?\s*?)*?)
                                 }
                                  """, css, re.M | re.VERBOSE)

        if profileText:
            profile = profileText.group(1)
            if profile == 'all':
                options['selector-compile'] = 'all'
                options['rule-compile'] = 'all'

            if profile == 'default':
                options['selector-compile'] = 'none'
                options['rule-compile'] = 'all'

            if profile == 'not-good-in-ie6':
                options['selector-compile'] = 'no-combinator'
                options['rule-compile'] = 'all'

            if profile == 'just-compress':
                options['selector-compile'] = 'none'
                options['rule-compile'] = 'none'

        if optionText:
            optionText = optionText.group(1)
            matches = re.finditer(r'\s*?(\S+)\s*:\s*([^;]*);?\s*?', optionText, re.M)
            for match in matches:
                key, value = match.groups()
                options[key] = value

        return options


    def processImport(self, path, mode, cssId):
        ''' 处理 import '''

        def doProcessImport(path, url = '.'):

            def processStr(m):
                k = m.group(1)
                result = '/* import by ' + url + ' */\n'
                result += doProcessImport(os.path.join(os.path.dirname(path), k), urljoin(url, k))
                result = re.sub(r'url\([\'"]?(.+?)[\'"]?\)', lambda m: 'url(' + urljoin(k, m.group(1)) + ')', result) # 把所有文件路径改为相对于最初的文件

                return result

            try:
                src = open(self.pathTransformer(path))
            except:
                return '/* ' + os.path.abspath(path) + ' is not exists */'

            css = src.read()

            options = self.getOptions(css)

            if options:
                sheet = cssutils.parseString(css)
                if 'rule-compile' in options.keys() and options['rule-compile'] != 'none':
                    ruleCompiler = cssrulecompiler.CSSRuleCompiler()
                    ruleCompiler.compile(sheet, mode)

                if 'selector-compile' in options.keys() and options['selector-compile'] != 'none':
                    selectorCompiler = cssselectorcompiler.CSSSelectorCompiler()
                    if options['selector-compile'] == 'no-combinator': selectorCompiler.combinator_compile = False
                    selectorHacks = selectorCompiler.compile(sheet, cssId, mode, doInsertTrigger = False)
                    self.__selectorHacks.extend(selectorHacks)

                css = sheet.cssText

            css = re.sub("@import\s+?url\('?(.+?)'?\);", processStr, css)

            return css + '\n\n'

        return doProcessImport(path)


    def compile(self, path, mode, cssId = ''):
        ''' 执行编译 '''

        if mode not in SUPPORT_COMPILE_MODE: return ''

        css = self.processImport(path, mode, cssId)

        triggerStr = cssselectorcompiler.getTrigger(cssId, self.__selectorHacks)
        if triggerStr: css += triggerStr.encode('utf-8')
        css = re.sub('expression\(\"((\s|\S)*?)!run-once\"\)', lambda m: 'expression(function(ele){' + m.group(1) + '}(this))', css)
        # expressions(function(){}(this)) Chrome可以识别；
        # expressions((function(){})(this)) 会导致chrome一些老版本中断解析css，但是！chrome引用 -std.min.css 并不会出现expression

        return css


def getUrls(path, pathTransformer = lambda path: path, recursion = True, inAll = False):
    ''' 返回css中的所有url, recursion 递归处理 import, inAll 返回一个url被处理过的平面数组, 否则返回一个 tuple '''

    root, name = os.path.split(path)

    def processFile(rurl, imports = [], urls = []):
        path = os.path.join(root, rurl)
        path = pathTransformer(path)
        try:
            src = open(path)
        except:
            return

        css = src.read()
        src.close()
        css = re.sub(r'\/\*(\s|\S)*?\*\/', lambda m: '', css) # 先清空注释

        matches = re.finditer("(@import)?\s*?url\('?(.+?)'?\)", css, re.M)
        if inAll == True:
            for match in matches:
                value = urljoin(rurl, match.group(2))
                flag = match.group(1)
                if urls.count(value): continue
                if flag == '@import':
                    imports.append(value)
                    processFile(value, imports = imports, urls = urls)
                else:
                    urls.append(value)

            return (imports, urls)

        else:
            imports = []
            urls = []
            for match in matches:
                value = match.group(2)
                flag = match.group(1)
                if flag == '@import':
                    imports.append(processFile(value))
                else:
                    urls.append(value)

        return (rurl, imports, urls)

    return processFile(name)

