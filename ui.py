#python
#encoding=utf-8

import sys

oldstdout = sys.stdout

def error(msg):
    print msg

def warn(msg):
    print 'WARN:', msg

def msg(msg):
    print msg
