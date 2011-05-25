#encoding=utf-8

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'))
import command

def get_paths(dir_path):
    paths = []
    for root, dirs, files in os.walk(dir_path):
        if '.svn' in root:
            continue
        for file in files:
            path = os.path.join(root, file)
            paths.append(path)
            pass
        pass
    return paths


pathlist = open(sys.argv[2], 'r').read().split('\n')
all_files = []
for path in pathlist:
    if os.path.isfile(path):
        if os.path.splitext(path)[1] in ('.css', '.js'):
           all_files.append(path)
    elif os.path.isdir(path):
        files = get_paths(path)
        all_files.extend([file for file in files if os.path.splitext(file)[1] in ('.css', '.js')])

publish_path = sys.argv[4]
source_path = command.source(publish_path)
result = os.system('svn update %s' % source_path)
if result != 0:
    raise Exception, 'SVN Update Error'

#open('last-commit.txt', 'w').write('\n'.join(all_files))
for file in all_files:
    command.compile(file, workspace_path = sys.argv[1])
