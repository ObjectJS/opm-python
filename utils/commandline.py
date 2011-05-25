#python
#encoding=utf-8

import sys
import os
import inspect
from optparse import OptionParser

__doc__ = u'''
一个用decorator描述命令行的辅助库
每一个用call调用的函数都是一个子命令
arg - 描述一个参数，可通过设置函数参数的默认值设定此参数是否必须
cwdarg - 描述函数的第一个参数为当前路径
option - 描述一个option

Arg Example:

    @cwdarg
    @arg('arg2')
    @arg('arg3')
    def subcommand(arg1, arg2, arg3 = None)

    command subcommand path1 path2  --> 当前路径 path1 path2
    command subcommand path1        --> 当前路径 path1
    command subcommand              --> 出错，参数个数不足两个
    command subcommand path1 path2 path3 --> path3 path1 path2 当参数个数与定义参数个数相同时，最后一个参数用于替换当前路径
'''

def arg(name):
    def _arg(func):
        def _func(*args, **kwargs):
            return func(*args, **kwargs)

        if 'commands' in func.__dict__:
            _func.commands = func.commands
        else:
            _func.commands = {'func': func}

        if 'allowlength' not in _func.commands:
            _func.commands['allowlength'] = 1
        else:
            allowlength = _func.commands['allowlength']
            _func.commands['allowlength'] = allowlength + 1

        return _func
    return _arg

def cwdarg(func):
    def _func(*args, **kwargs):
        return func(*args, **kwargs)

    if 'commands' in func.__dict__:
        _func.commands = func.commands
    else:
        _func.commands = {'func': func}

    if 'allowlength' not in _func.commands:
        _func.commands['allowlength'] = 1
    else:
        allowlength = _func.commands['allowlength']
        _func.commands['allowlength'] = allowlength + 1

    if 'cwdarg' not in _func.commands:
        _func.commands['cwdarg'] = True

    return _func

def option(name, *optionargs, **optionkwargs):
    def _option(func):
        def _func(*args, **kwargs):
            return func(*args, **kwargs)

        if 'commands' in func.__dict__:
            _func.commands = func.commands
        else:
            _func.commands = {'func': func}

        if 'options' not in _func.commands:
            _func.commands['options'] = []

        optionkwargs['dest'] = name
        _func.commands['options'].append((optionargs, optionkwargs))

        return _func
    return _option

def usage(usage):
    def _usage(func):
        def _func(*args, **kwargs):
            return func(*args, **kwargs)

        if 'commands' in func.__dict__:
            _func.commands = func.commands
        else:
            _func.commands = {'func': func}

        _func.commands['usage'] = usage

        return _func
    return _usage

def initcommand(func):
    parser = OptionParser()
    cwdarg = False
    allowlength = 0
    if 'commands' not in func.__dict__:
        func()
        sys.exit(0)

    if 'options' in func.commands:
        for option in func.commands['options']:
            parser.add_option(*option[0], **option[1])

    if 'usage' in func.commands:
        usage = func.commands['usage']

        usage = usage + '\n' + func.commands['func'].__name__.strip()
    else:
        usage = ''

    if 'allowlength' in func.commands:
        allowlength = func.commands['allowlength']

    if 'cwdarg' in func.commands:
        cwdarg = True

    doc = func.commands['func'].__doc__;
    if doc:
        usage = usage + doc

    parser.set_usage(usage)

    return (parser, cwdarg, allowlength)

def call(commands, command):
    if command not in commands:
        help(commands)
        sys.exit(1)

    parser, cwdarg, allowlength = initcommand(command)
    if 'commands' in command.__dict__: command = command.commands['func']

    opts, args = parser.parse_args()
    args = list(args[1:]) # 去掉子命令

    argspec = inspect.getargspec(command)
    if argspec.defaults:
        argsmin = len(argspec.args) - len(argspec.defaults)
    else:
        argsmin = len(argspec.args)

    if cwdarg:
        if len(args) == allowlength:
            cwd = os.path.join(os.getcwd(), args[0])
            args = args[1:]
            args.insert(0, cwd)
        else:
            args.insert(0, os.getcwd()) # 第一个参数为当前路径

    if len(args) > allowlength or len(args) < argsmin:
        print u'参数错误'
        return

    kwargs = {}
    for key in opts.__dict__.keys():
        if opts.__dict__[key] is not None:
            kwargs[key] = opts.__dict__[key]

    result = command(*args, **kwargs)
    if not result: result = 0
    sys.exit(result)

def help(commands, command = None):
    if not command:
        print u'输入 scompiler help command 获得子命令的帮助\n'
        for command in commands:
            desc = command.commands['func'].__doc__.split('\n')[0].strip()
            print ' %s %s %s' % (command.commands['func'].__name__, (12 - len(command.commands['func'].__name__)) * ' ', desc)

    else:
        parser, cwdarg, allowlength = initcommand(command)
        parser.print_help()

