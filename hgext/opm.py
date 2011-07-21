#/usr/bin/python
#encoding=utf-8

import sys
import os
sys.path.insert(0, os.path.realpath(os.path.join(__file__, '../../')))

import opm, commands
from mercurial import hg, demandimport
from mercurial import merge as mergemod
import mercurial.ui
import time

demandimport.disable()

def publish(ui, repo, node_name = 'tip', commitlog_path = None, no_depts = False):
    u'发布一个库至svn'

    publish_path = ui.config('opm', 'publish-path')
    publish_branch = ui.config('opm', 'publish-branch', 'default') # 默认作为发布源的分支名称

    # 只有没有commitlog_path参数的时候才生成commitlog
    if not commitlog_path:
        commitlog_path = os.path.join(repo.root, './commitlog.txt')
        generate_commitlog = True
    else:
        generate_commitlog = False

    commitlog_path = os.path.realpath(commitlog_path)

    if not publish_path:
        ui.warn('%s: no publish path\n' % repo.root)
        return

    node = repo[node_name]
    node_branch = node.branch()

    # 不是需要被编译的分支
    if node_branch != publish_branch:
        ui.warn('%s: ignore branch %s\n' % (repo.root, node_branch))
        return

    package = opm.StaticPackage(repo.root)

    # 编译当前库，生成commitlog
    if generate_commitlog:
        parent = node.parents()[0].rev()
        mergemod.update(repo, None, False, False, None)
        rev = node.rev()
        ui.write('%s: update version from %s to %s\n' % (repo.root, parent, rev))
        os.system('hg log -r %s:%s > %s' % (parent, rev, commitlog_path))

    # 更新依赖的库
    for repo_path in package.get_libs(all=True):
        sub_repo = hg.repository(ui, repo_path)
        mergemod.update(sub_repo, None, False, False, None)

    # 编译当前库
    returnValue = os.popen3('svn update %s --accept theirs-full' % publish_path)[1].read()
    ui.write('%s: %s updated %s' % (repo.root, publish_path, returnValue))
    commands.ui.prefix = repo.root + ': '
    commands.publish(repo.root, publish_path)
    commands.ui.prefix = ''
    olddir = os.curdir
    os.chdir(publish_path)
    os.popen3('svn add * --force')
    returnValue = os.popen3('svn commit -F %s' % commitlog_path)[1].read()
    returnValue = returnValue.strip()
    if not returnValue:
        ui.write('%s: nothing to commit.\n' % (repo.root,))
    else:
        for line in returnValue.split('\n'):
            ui.write('%s: %s\n' % (repo.root, line))

    os.chdir(olddir)

    # 编译依赖自己的库
    if not no_depts:
        for repo_path in package.get_reverse_libs(all=True):
            # 需要新生成一个ui实例进去，否则配置文件会继承
            sub_repo = hg.repository(mercurial.ui.ui(), repo_path)
            publish(sub_repo.ui, sub_repo, commitlog_path = commitlog_path, no_depts = True)

    # 删除commitlog
    if generate_commitlog:
        os.remove(commitlog_path)

def incominghook(ui, repo, source = '', node = None, **opts):
    a = open('/home/jingwei/fuck', 'w+')
    a.write(time.ctime())
    a.close()
    publish(ui, repo, node)

def reposetup(ui, repo):
    ui.setconfig('hooks', 'incoming.autocompile', incominghook)

cmdtable = {
    "opm-publish": (publish,
                [('', 'no-depts', False, '不编译依赖于自己的库'),
                ('', 'commitlog-path', None, 'svn提交log路径')],
               '[options] [NODE]')
}
