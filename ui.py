#python
#encoding=utf-8

import sys

oldstdout = sys.stdout

prefix = '' # 输出所有消息时会带上这个前缀，一般用于被调用时的方便封装

def error(msg):
    print prefix + msg

def warn(msg):
    print prefix + 'WARN:', msg

def msg(msg):
    print prefix + msg
