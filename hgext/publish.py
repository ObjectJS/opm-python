#/usr/bin/python
#encoding=utf-8

import sys
import os
sys.path.insert(0, os.path.realpath(os.path.join(__file__, '../../')))

import staticcompiler as opm
from mercurial.i18n import _
from mercurial import hg, commands

def incominghook(ui, repo, source = 'default', **opts):
    pass

def reposetup(ui, repo):
    ui.setconfig('hooks', 'incoming.autocompile', incominghook)

def compile(publish_path, commit_log_path = None):
    os.system('svn update %s --accept theirs-full' % publish_path)
    olddir = os.curdir
    os.chdir(publish_path)
    os.system('svn add * --force')
    #os.system('svn commit -F %s' % commit_log_path)
    os.chdir(olddir)

def publish(ui, repo, node_name = 'tip', **opts):
    publish_path = ui.config('opm', 'publish')
    if publish_path:
        node = repo[node_name]
        branch_name = node.branch()
        if branch_name == 'default':
            parent = node.parents()[0].rev()
            hg.update(repo, None)
            rev = node.rev()
            ui.write('up %s to %s' % (parent, rev))
            # hg log -r $parent:$rev > $commitlog

            package = opm.StaticPackage(os.path.realpath('.'))

            # 更新依赖的库
            for repo in package.get_libs(all=True):
                commands.update(ui, repo)

            compile(publish_path)

            # 编译依赖自己的库
            # 编译时并不更新其依赖库
            for repo_path in package.get_reverse_libs(all=True):
                repo = hg.repository(repo_path)
                compile(repo.ui.config('opm', 'publish'))

            # rm $commitlog


cmdtable = {
    "publish": (publish,
                [],
               '[options] [NODE]')
}
