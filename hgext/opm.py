#/usr/bin/python
#encoding=utf-8

import sys
import os
sys.path.insert(0, os.path.realpath(os.path.join(__file__, '../../')))
for p in os.environ.get('PYTHONPATH', '').split(';'):
    sys.path.append(p)

# mercurial默认开始demandimport，替换了默认的import动作，将所有import模块变成延时加载，调用时才load
# 因此cssutils中的一个cssutils.codec模块没有被执行导致出错
# 使用__import__避免import带来的demandimport
opm = __import__('opm')
import commands

from mercurial import hg
from mercurial import merge as mergemod
from mercurial.i18n import _
import mercurial.ui
import mercurial.commands
import mercurial.extensions
import time

def runcmd(ui, repo, cmd, empty = ''):
    #ui.write('%s: %s\n' % (repo.root, cmd))
    returnValue = os.popen3(cmd)
    returnValue = returnValue[1].read() + returnValue[2].read() # 输出stdout和stderr
    returnValue = returnValue.strip()
    if returnValue:
        for line in returnValue.split('\n'):
            ui.write('%s: %s\n' % (repo.root, line))
    elif empty:
        ui.write('%s: %s\n' % (repo.root, empty))

def _publish(ui, repo, commitlog_path, rebuild = False):
    u'发布一个库至svn'

    # 编译当前库
    publish_path = ui.config('opm', 'publish-path')

    if not publish_path:
        ui.warn('%s: no publish path\n' % repo.root)
    else:
        # 编译当前库
        runcmd(ui, repo, 'svn update %s --force --accept theirs-full' % publish_path)
        commands.ui.prefix = repo.root + ': '
        commands.ui.fout = ui.fout # 输入导出到客户端
        commands.publish(repo.root, publish_path, rebuild = rebuild)
        commands.ui.prefix = ''
        runcmd(ui, repo, 'svn commit %s -F %s' % (publish_path, commitlog_path), 'nothing to commit.')

def publish(ui, repo, source = '', node = 'default', **opts):

    # 只对静态编译框架维护的库进行操作
    if not opm.StaticPackage.is_root(repo.root) or source == 'pull':
        return

    publish_branch = ui.config('opm', 'publish-branch', 'default') # 默认作为发布源的分支名称
    node = repo[node]
    node_branch = node.branch()

    # 不是需要被编译的分支
    if node_branch != publish_branch:
        ui.warn('%s: ignore branch %s\n' % (repo.root, node_branch))
        return

    # update当前库
    mergemod.update(repo, None, False, False, None)

    # 生成commitlog
    commitlog_path = os.path.realpath(os.path.join(repo.root, './commitlog.txt'))
    parent = node.parents()[0].rev()
    rev = node.rev()
    ui.write('%s: update version from %s to %s\n' % (repo.root, parent, rev))
    os.chdir(repo.root)
    os.system('hg log -b %s -r %s:%s > %s' % (node_branch, parent, rev, commitlog_path))

    # 编译自己
    _publish(ui, repo, commitlog_path, rebuild = True)

    # 编译依赖自己的库
    package = opm.StaticPackage(repo.root)
    for repo_path in package.get_reverse_libs(all=True):
        sub_repo = hg.repository(ui, repo_path)
        _publish(sub_repo.ui, sub_repo, commitlog_path, rebuild = False)

    # 删除commitlog
    os.remove(commitlog_path)

def pullwrapper(orig, *args, **kwargs):
    result = orig(*args, **kwargs)
    if kwargs['depts']:
        pull(*args, **kwargs)
    return result

def pull(ui, repo, *args, **kwargs):
    package = opm.StaticPackage(repo.root)
    for repo_path in package.get_libs(all=True):
        sub_repo = hg.repository(ui, repo_path)
        mercurial.commands.pull(sub_repo.ui, sub_repo, *args, **kwargs)

def reposetup(ui, repo):
    ui.setconfig('hooks', 'incoming.autocompile', publish)

def uisetup(ui):
    '''Initialize the extension.'''

    #wrap pull
    entry = mercurial.extensions.wrapcommand(mercurial.commands.table, 'pull', pullwrapper)
    entry[1].append(('D', 'depts', None, _('pull dependencies')))

cmdtable = {
    'opm-publish': (publish,
                [],
               '[options] [NODE]')
}

