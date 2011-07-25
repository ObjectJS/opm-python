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

# mercurial默认开始demandimport，替换了默认的import动作，将所有import模块变成延时加载，调用时才load
# 因此cssutils中的一个cssutils.codec模块没有被执行导致出错，在此关闭。
demandimport.disable()

logfile = open('/home/jingwei.li/opm.log', 'w+')
def log(str):
    logfile.write(str + '\n')
    logfile.flush()

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
        mergemod.update(repo, node_name, False, False, None)
        rev = repo['tip'].rev()
        ui.write('%s: update version from %s to %s\n' % (repo.root, parent, rev))
        os.chdir(repo.root)
        os.system('hg log -r %s:%s > %s' % (parent, rev, commitlog_path))

    # 更新依赖的库
    for repo_path in package.get_libs(all=True):
        sub_repo = hg.repository(ui, repo_path)
        mergemod.update(sub_repo, None, False, False, None)

    # 编译当前库
    returnValue = os.popen3('svn update %s --accept theirs-full' % publish_path)[1].read()
    returnValue = returnValue.strip()
    for line in returnValue.split('\n'):
        ui.write('%s: %s\n' % (repo.root, line))

    commands.ui.prefix = repo.root + ': '
    commands.ui.fout = ui.fout # 输入导出到客户端
    commands.publish(repo.root, publish_path)
    commands.ui.prefix = ''
    os.chdir(publish_path)
    os.popen3('svn add * --force')
    returnValue = os.popen3('svn commit -F %s' % commitlog_path)[1].read()
    returnValue = returnValue.strip()
    if not returnValue:
        ui.write('%s: nothing to commit.\n' % (repo.root,))
    else:
        for line in returnValue.split('\n'):
            ui.write('%s: %s\n' % (repo.root, line))

    # 编译依赖自己的库
    if not no_depts:
        for repo_path in package.get_reverse_libs(all=True):
            # 需要新生成一个ui实例进去，否则配置文件会继承
            sub_repo = hg.repository(ui, repo_path)
            publish(sub_repo.ui, sub_repo, commitlog_path = commitlog_path, no_depts = True)

    # 删除commitlog
    if generate_commitlog:
        os.remove(commitlog_path)

def incominghook(ui, repo, source = '', node = None, **opts):
    a = open('/home/jingwei.li/incoming.log', 'w+')
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
