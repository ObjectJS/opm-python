#python
#coding=utf-8

import re

def getTrigger(cssId, selectorHacks):
    if not selectorHacks: return None
    rulestr = '#CSSID_' + cssId + ' {_display: expression("ele.runtimeStyle.display=\'block\';'
    for hack in selectorHacks:
        rulestr += 'Expressions.selector(\'' + hack[0].replace('\'', '\\\\\\\'') + '\', \'' + 'h_' + cssId + '_' + str(hack[1]) + '\');'

    rulestr = rulestr + '!run-once");}'
    return rulestr

class CSSSelectorCompiler():
    ''' 微软浏览器的CSS兼容性列表：
    
    http://msdn.microsoft.com/en-us/library/cc351024%28VS.85%29.aspx
    
    '''

    def __init__(self):
        self.hackedSelector = self.hackedSelector2 = {}
        self.selectorHacks = []
        self.hackid = 1
        self.cssId = ''

        self.combinator_compile = True


    def getHackId(self, hackid = ''):
        if not hackid: hackid = self.hackid
        return 'h_' + self.cssId + '_' + str(hackid)


    def deparseSelectorPart(self, part, noCombinator = False):
        ''' 将selector部分对象转换成selector字符串, noCombinator不转换选择符 '''

        text = ''

        if not noCombinator and 'combinator' in part.keys() and part['combinator']:
            text += part['combinator']

        if 'tag' in part.keys() and part['tag']:
            text += part['tag']

        if len(part['ident']) >= 2 and part['ident'][1] == '*':
            text += '*'

        if 'id' in part.keys() and part['id']:
            text += '#' + part['id']

        if 'classes' in part.keys() and part['classes']:
            for className in part['classes']:
                text += '.' + className

        if 'attributes' in part.keys() and part['attributes']:
            for attribute in part['attributes']:
                text += '[' + attribute['name']
                if attribute['operator']:
                    text += attribute['operator'] + "'" + attribute['value'] + "'"

                text += ']'

        if 'pseudos' in part.keys() and part['pseudos']:
            for pseudo in part['pseudos']:
                text += ':' + pseudo['name']
                if pseudo['value']:
                    text += '(' + pseudo['value'] + ')'

        return text


    def deparseSelector(self, selector):
        ''' 转换整个selector '''
        text = ''
        for part in selector:
            text += self.deparseSelectorPart(part)

        return text


    def parseSelector(self, text):
        ''' 解析选择器字符串为对象，核心算法来自Sly.js '''

        pattern = re.compile(ur'''[\w\u00a1-\uFFFF][\w\u00a1-\uFFFF-]*|[#.](?:[\w\u00a1-\uFFFF-]|\\:|\\.)+|[ \t\r\n\f](?=[\w\u00a1-\uFFFF*#.[:])|[ \t\r\n\f]*(,|>|\+|~)[ \t\r\n\f]*|\[([\w\u00a1-\uFFFF-]+)[ \t\r\n\f]*(?:([!*=^=$=~=|=]?=)[ \t\r\n\f]*(?:"([^"]*)"|'([^']*)'|([^\]]*)))?]|:([-\w\u00a1-\uFFFF]+)(?:\((?:"([^"]*)"|'([^']*)'|([^)]*))\))?|\*|(.+)''')

        def create(combinator):
            return {
                'ident': [],
                'classes': [],
                'attributes': [],
                'pseudos': [],
                'combinator': combinator
            }

        parsed = []
        current = create(None)
        current['first'] = True

        def refresh(combinator, current):
            parsed.append(current)
            current = create(combinator)

            return current

        match = None
        first = None

        results = pattern.finditer(text)
        for result in results:
            match = [result.group(0)]
            match.extend(result.groups())

            if match[-1]:
                print 'error'
                return []

            first = match[0]
            char = first[0]

            if char == '.':
                current['classes'].append(first[1:].replace('\\', ''))

            elif char == '#':
                current['id'] = first[1:].replace('\\', '')

            elif char == '[':
                current['attributes'].append({
                    'name': match[2],
                    'operator': match[3] or None,
                    'value': match[4] or match[5] or match[6] or None
                })

            elif char == ':':
                current['pseudos'].append({
                    'name': match[7],
                    'value': match[8] or match[9] or match[10] or None
                })

            else:
                if char in (' ', '\t', '\r', '\n', '\f'):
                    match[1] = match[1] or ' '

                combinator = match[1]

                if combinator:
                    if combinator == ',':
                        current['last'] = True
                        current = refresh(null, current)
                        current['first'] = True
                        continue

                    if 'first' in current and not len(current['ident']):
                        current['combinator'] = combinator

                    else:
                        current = refresh(combinator, current)
                else:
                    if first != '*':
                        current['tag'] = first

            current['ident'].append(first);

        current['last'] = True;
        parsed.append(current);

        return parsed;


    def insertTrigger(self, sheet):
        ''' 将Expression加入到css文件中 '''

        sheet.insertRule(cssselectorcompiler.getTrigger(self.cssId, self.selectorHacks))

    
    def compile(self, sheet, cssId, mode, doInsertTrigger = True):
        if mode not in ('ie6', 'ie7'):
            return []

        self.cssId = cssId
        for i, rule in enumerate(sheet.cssRules):
            if rule.typeString == 'STYLE_RULE':
                if mode == 'ie6':
                    rule = self.compileIE6(rule, i)

                elif mode == 'ie7':
                    rule = self.compileIE7(rule, i)

        if doInsertTrigger: self.insertTrigger(sheet)
        return self.selectorHacks


    def compileIE7(self, rule, i):
        ''' 将selector解析成IE7可用 '''

        pseudoTriggers = {
            'hover' : ('page-break-before', 'pageBreakBefore', 'auto'),
            'disabled' : ('page-break-after', 'pageBreakAfter', 'auto'),
        }

        for selector in rule.selectorList:

            prefix = ''
            prefix2 = ''

            selectorSeq = self.parseSelector(selector.selectorText)
            selectorSeq2 = self.parseSelector(selector.selectorText)

            for j, partSeq2 in enumerate(selectorSeq2):
                partSeq = selectorSeq[j]
                needCompile = False
                compileStatusPseudo = False

                if partSeq2['pseudos']:
                    #伪类
                    for k, pseudo in enumerate(partSeq2['pseudos']):
                        if (pseudo['name'] in ('focus', 'disabled', 'enabled')) \
                           or (pseudo['name'] in ('before', 'after') and rule.style.content not in ('"\\20"', "'\\20'")):
                            partSeq2['pseudos'].remove(pseudo)
                            partSeq['pseudos'].pop(k)
                            needCompile = True
                            compileStatusPseudo = pseudo['name']

                prefix += self.deparseSelectorPart(partSeq)

                if needCompile and compileStatusPseudo:
                    if compileStatusPseudo in ('after', 'before'):
                        prefix2 += self.deparseSelectorPart(partSeq2)
                        if compileStatusPseudo == 'after':
                            rule.parentStyleSheet.insertRule(prefix2 + '{behavior:expression("ele.runtimeStyle.behavior=\'none\';Expressions.pseudo.' + compileStatusPseudo + '(ele,\'' + self.getHackId() + '\');!run-once");}')

                        else:
                            rule.parentStyleSheet.insertRule(prefix2 + '{zoom:expression("ele.runtimeStyle.zoom=\'1\';Expressions.pseudo.' + compileStatusPseudo + '(ele,\'' + self.getHackId() + '\');!run-once");}')

                        selectorSeq.append({
                            'tag': compileStatusPseudo,
                            'ident': [],
                            'classes': [],
                            'attributes': [],
                            'pseudos': [],
                            'combinator': ' '
                        })
                        selectorSeq2.append({
                            'tag': compileStatusPseudo,
                            'ident': [],
                            'classes': [],
                            'attributes': [],
                            'pseudos': [],
                            'combinator': ' '
                        })

                    else:
                        if prefix in self.hackedSelector.keys():
                            # 已经处理过
                            partSeq2['classes'] = [self.getHackId(self.hackedSelector2[prefix])]

                        prefix2 += self.deparseSelectorPart(partSeq2)
                        if compileStatusPseudo in pseudoTriggers:
                            trigger = pseudoTriggers[compileStatusPseudo]

                        else:
                            trigger = ('behavior', 'behavior', 'none')

                        rule.parentStyleSheet.insertRule(prefix2 + '{' + trigger[0] + ':expression("ele.runtimeStyle.' + trigger[1] + '=\'' + trigger[2] + '\';Expressions.pseudo.' + compileStatusPseudo + '(ele,\'' + self.getHackId() + '\');!run-once");}')
                        partSeq2['classes'] = [self.getHackId()]
                        prefix2 += self.deparseSelectorPart(partSeq2)
                        self.hackid += 1

                elif needCompile and not compileStatusPseudo:
                    if prefix in self.hackedSelector.keys():
                        # 已经处理过
                        partSeq2['classes'] = [self.getHackId(self.hackedSelector2[prefix])]
                        prefix2 += self.deparseSelectorPart(partSeq2)

                    else:
                        # 需要处理
                        prefix2 += self.deparseSelectorPart(partSeq2)

                        self.selectorHacks.append((prefix, self.hackid))
                        self.hackedSelector[prefix2] = self.hackid
                        self.hackedSelector[prefix] = self.hackid

                        partSeq2['classes'] = [self.getHackId()]
                        self.hackid += 1

                else:
                    prefix2 += self.deparseSelectorPart(partSeq2)

            selector.selectorText = self.deparseSelector(selectorSeq2)

        return rule
    

    def compileIE6(self, rule, i):
        ''' 将selector解析成IE6可用 '''

        pseudoTriggers = {
            'hover' : ('page-break-before', 'pageBreakBefore', 'auto'),
            'disabled' : ('page-break-after', 'pageBreakAfter', 'auto'),
        }

        for selector in rule.selectorList:

            prefix = ''
            prefix2 = ''

            selectorSeq = self.parseSelector(selector.selectorText)
            selectorSeq2 = self.parseSelector(selector.selectorText)

            for j, partSeq2 in enumerate(selectorSeq2):
                partSeq = selectorSeq[j]
                needCompile = False
                compileStatusPseudo = False

                if partSeq2['combinator'] == ">" or len(partSeq2['classes']) > 1:
                    #子选择符
                    partSeq2['combinator'] = ' '
                    if self.combinator_compile:
                        partSeq2['classes'] = []
                        needCompile = True

                if partSeq2['attributes']:
                    for k, pseudo in enumerate(partSeq2['attributes']):
                        partSeq2['attributes'].remove(pseudo)
                        needCompile = True

                if partSeq2['pseudos']:
                    #伪类
                    for k, pseudo in enumerate(partSeq2['pseudos']):
                        if pseudo['name'] in ('nth-child', 'not'):
                            partSeq2['pseudos'].remove(pseudo)
                            needCompile = True

                        elif ('tag' not in partSeq2.keys() or partSeq2['tag'] != 'a') and pseudo['name'] == 'hover' \
                                or (pseudo['name'] in ('focus', 'disabled', 'enabled')) \
                                or (pseudo['name'] in ('before', 'after') and rule.style.content not in ('"\\20"', "'\\20'")):
                            partSeq2['pseudos'].remove(pseudo)
                            partSeq['pseudos'].pop(k)
                            needCompile = True
                            compileStatusPseudo = pseudo['name']

                prefix += self.deparseSelectorPart(partSeq)

                if needCompile and compileStatusPseudo:
                    if compileStatusPseudo in ('after', 'before'):
                        prefix2 += self.deparseSelectorPart(partSeq2)
                        if compileStatusPseudo == 'after':
                            rule.parentStyleSheet.insertRule(prefix2 + '{behavior:expression("ele.runtimeStyle.behavior=\'none\';Expressions.pseudo.' + compileStatusPseudo + '(ele,\'' + self.getHackId() + '\');!run-once");}')

                        else:
                            rule.parentStyleSheet.insertRule(prefix2 + '{zoom:expression("ele.runtimeStyle.zoom=\'1\';Expressions.pseudo.' + compileStatusPseudo + '(ele,\'' + self.getHackId() + '\');!run-once");}')

                        selectorSeq.append({
                            'tag': compileStatusPseudo,
                            'ident': [],
                            'classes': [],
                            'attributes': [],
                            'pseudos': [],
                            'combinator': ' '
                        })
                        selectorSeq2.append({
                            'tag': compileStatusPseudo,
                            'ident': [],
                            'classes': [],
                            'attributes': [],
                            'pseudos': [],
                            'combinator': ' '
                        })

                    else:
                        if prefix in self.hackedSelector.keys():
                            # 已经处理过
                            partSeq2['classes'] = ['h_' + self.cssId + '_' + str(self.hackedSelector2[prefix])]

                        prefix2 += self.deparseSelectorPart(partSeq2)
                        if compileStatusPseudo in pseudoTriggers:
                            trigger = pseudoTriggers[compileStatusPseudo]

                        else:
                            trigger = ('behavior', 'behavior', 'none')

                        rule.parentStyleSheet.insertRule(prefix2 + '{' + trigger[0] + ':expression("ele.runtimeStyle.' + trigger[1] + '=\'' + trigger[2] + '\';Expressions.pseudo.' + compileStatusPseudo + '(ele,\'' + self.getHackId() + '\');!run-once");}')
                        partSeq2['classes'] = [self.getHackId()]
                        prefix2 += self.deparseSelectorPart(partSeq2)
                        self.hackid += 1

                elif needCompile and not compileStatusPseudo:
                    if prefix in self.hackedSelector.keys():
                        # 已经处理过
                        partSeq2['classes'] = ['h_' + self.cssId + '_' + str(self.hackedSelector2[prefix])]
                        prefix2 += self.deparseSelectorPart(partSeq2)

                    else:
                        # 需要处理
                        prefix2 += self.deparseSelectorPart(partSeq2)

                        self.selectorHacks.append((prefix, self.hackid))
                        self.hackedSelector[prefix2] = self.hackid
                        self.hackedSelector[prefix] = self.hackid

                        partSeq2['classes'] = [self.getHackId()]
                        self.hackid += 1

                else:
                    prefix2 += self.deparseSelectorPart(partSeq2)

            selector.selectorText = self.deparseSelector(selectorSeq2)

        return rule

