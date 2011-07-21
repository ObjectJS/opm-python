#python
#encoding=utf-8

import sys

fout = sys.stdout

prefix = '' # 输出所有消息时会带上这个前缀，一般用于被调用时的方便封装

def error(msg):
    fout.write(prefix + msg + '\n')

def warn(msg):
    fout.write(prefix + 'WARN:' + msg + '\n')

def msg(msg):
    fout.write(prefix + msg + '\n')
