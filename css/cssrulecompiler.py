#python
#coding=utf-8

import re

class CSSRuleCompiler():

    def __init__(self):
        self.mode = 'std'
        self.rule = None
        self.sprites = []


    def getStyle(self, name):
        names = self.rule.style.keys()
        ie6Name = '_' + name
        ieName = '*' + name
        if ((self.mode == 'ie6' and (ie6Name in names or ieName in names))) or (self.mode == 'ie7' and ieName in names):
            value = ''
            for property in self.rule.style:
                if property.name in (name):
                    value = property.value

                if self.mode == 'ie6' and property.name in (name, ieName, ie6Name):
                    value = property.value

                if self.mode == 'ie7' and property.name in (name, ieName):
                    value = property.value

        else:
            value = self.rule.style[name]

        return value


    def ieContent(self, rule):
        ''' content '''

        content = self.getStyle('content')
        if content and content != '"\\20"':
            # content: '\20' 为清除浮动，不做处理
            content = re.sub('^"(.*?)"$', lambda m: m.group(1).replace('\'', '\\\\\\\''), content)
            rule.style['behavior'] = 'expression("ele.runtimeStyle.behavior=\'none\';Expressions.style.content(ele, \'' + content + '\');!run-once")'

    def ie6PositionFixed(self, rule):
        ''' positioin: fixed '''

        if self.getStyle('position') == 'fixed':
            rule.style.position = 'expression("ele.runtimeStyle.position=\'absolute\';Expressions.style.position.fixed(ele);!run-once")'


    def ie6PositionFixedDelay(self, rule):
        ''' fixed position delay '''

        delay = self.getStyle('-ie6-position-fixed-delay')
        if delay:
            rule.style['behavior'] = 'expression("ele.runtimeStyle.behavior=\'none\';Expressions.style.position.fixed.delay(ele, ' + delay + ');!run-once")'


    def ie6LineHeightFix(self, rule):
        if self.getStyle('-ie6-line-height-fix') == 'fix':
	        rule.style['_letter-spacing'] = 'expression("ele.runtimeStyle.letterSpacing=\'0\';Expressions.style.fixLineHeight(ele);!run-once");'


    def ie6FloatFix(self, rule):
        if self.getStyle('float'):
            # 浮动双倍margin
            rule.style['display'] = 'inline'


    def ie6MinWidth(self, rule):
        if self.getStyle('min-width'):
            # min-width
            rule.style.width = 'expression("ele.runtimeStyle.width=\'auto\';Expressions.style.minWidth(ele, \'' + self.getStyle('min-width') + '\');!run-once")'


    def ieBoxSizingBorderBox(self, rule):
        if self.getStyle('box-sizing') == 'border-box':
            rule.style['zoom'] = 'expression("ele.runtimeStyle.zoom=\'1\';Expressions.style.boxSizing.borderBox(ele);!run-once");'


    def ieInlineBlock(self, rule):
        if self.getStyle('display') == 'inline-block':
            rule.style['display'] = 'inline'
            rule.style['zoom'] = '1'
    

    def ieOutline(self, rule):
        if self.getStyle('outline') == '0 none':
            rule.style['zoom'] = 'expression("ele.runtimeStyle.zoom=\'1\';Expressions.style.outline(ele, \'0 none\');!run-once");'


    def compile(self, sheet, mode):
        for i, rule in enumerate(sheet.cssRules):
            if rule.typeString == 'STYLE_RULE':
                self.rule = rule
                if mode == 'std':
                    rule = self.compileStandard(rule, i)
                elif mode == 'ie6':
                    rule = self.compileIE6(rule, i)
                elif mode == 'ie7':
                    rule = self.compileIE7(rule, i)


    def compileIE6(self, rule, i):
        self.mode = 'ie6'

        self.ie6PositionFixed(rule)
        self.ie6PositionFixedDelay(rule)
        self.ie6LineHeightFix(rule)
        self.ie6FloatFix(rule)
        self.ie6MinWidth(rule)
        #self.ieBoxSizingBorderBox(rule)
        self.ieContent(rule)
        self.ieInlineBlock(rule)
        self.ieOutline(rule)

        #if rule.style.position == 'relative':
            #rule.style['_zoom'] = '1'

        return rule


    def compileIE7(self, rule, i):
        self.mode = 'ie7'
        ie6UsePrefix = ('_', '-ie6-')

        self.ieInlineBlock(rule)
        self.ieContent(rule)
        self.ieOutline(rule)

        for property in rule.style:
            for prefix in ie6UsePrefix:
                if property.name.startswith(prefix):
                    rule.style.removeProperty(property.name)
        
        return rule
    

    def compileStandard(self, rule, i):
        self.mode = 'std'

        ieUsePrefixs = ['_', '*', '-ie-', '-ie6-', '-ie7-']
        for property in rule.style:
            # 删除所有IE专有属性
            for prefix in ieUsePrefixs:
                if property.name.startswith(prefix):
                    rule.style.removeProperty(property.name)


    def compileAll(self, rule, i):
        self.mode = 'ie6'

        self.ie6PositionFixed(rule)
        self.ie6PositionFixedDelay(rule)
        self.ie6LineHeightFix(rule)
        self.ie6FloatFix(rule)
        self.ie6MinWidth(rule)
        #self.ieBoxSizingBorderBox(rule)
        self.ieContent(rule)
        self.ieInlineBlock(rule)
        self.ieOutline(rule)

        #if rule.style.position == 'relative':
            #rule.style['_zoom'] = '1'

        return rule


    def compileIE7(self, rule, i):
        self.mode = 'ie7'
        ie6UsePrefix = ('_', '-ie6-')

        self.ieInlineBlock(rule)
        self.ieContent(rule)
        self.ieOutline(rule)

        for property in rule.style:
            for prefix in ie6UsePrefix:
                if property.name.startswith(prefix):
                    rule.style.removeProperty(property.name)
        
        return rule
