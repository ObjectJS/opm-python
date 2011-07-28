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

def publish(ui, repo, node_name = 'tip', commitlog_path = None, no_depts = False, rebuild = False):
    u'发布一个库至svn'

    # 只对静态编译框架维护的库进行操作
    if not opm.StaticPackage.is_root(repo.root):
        return

    publish_path = ui.config('opm', 'publish-path')
    publish_branch = ui.config('opm', 'publish-branch', 'default') # 默认作为发布源的分支名称

    node = repo[node_name]
    node_branch = node.branch()

    # 不是需要被编译的分支
    if node_branch != publish_branch:
        ui.warn('%s: ignore branch %s\n' % (repo.root, node_branch))
        return

    # 只有没有commitlog_path参数的时候才生成commitlog
    if not commitlog_path:
        commitlog_path = os.path.join(repo.root, './commitlog.txt')
        generate_commitlog = True
    else:
        generate_commitlog = False

    commitlog_path = os.path.realpath(commitlog_path)

    package = opm.StaticPackage(repo.root)

    parent = node.parents()[0].rev()
    mergemod.update(repo, node_name, False, False, None)

    # 生成commitlog
    if generate_commitlog:
        rev = repo['tip'].rev()
        ui.write('%s: update version from %s to %s\n' % (repo.root, parent, rev))
        os.chdir(repo.root)
        os.system('hg log -r %s:%s > %s' % (parent, rev, commitlog_path))

    if not publish_path:
        ui.warn('%s: no publish path\n' % repo.root)
    else:
        # 更新依赖的库
        for repo_path in package.get_libs(all=True):
            sub_repo = hg.repository(ui, repo_path)
            mergemod.update(sub_repo, None, False, False, None)

        # 编译当前库
        runcmd(ui, repo, 'svn update %s --accept theirs-full' % publish_path)
        commands.ui.prefix = repo.root + ': '
        commands.ui.fout = ui.fout # 输入导出到客户端
        commands.publish(repo.root, publish_path, rebuild = rebuild)
        commands.ui.prefix = ''
        runcmd(ui, repo, 'svn commit %s -F %s' % (publish_path, commitlog_path), 'nothing to commit.')

    # 编译依赖自己的库
    if not no_depts:
        for repo_path in package.get_reverse_libs(all=True):
            # 需要新生成一个ui实例进去，否则配置文件会继承
            sub_repo = hg.repository(ui, repo_path)
            publish(sub_repo.ui, sub_repo, commitlog_path = commitlog_path, no_depts = True, rebuild = False)

    # 删除commitlog
    if generate_commitlog:
        os.remove(commitlog_path)

def incominghook(ui, repo, source = '', node = None, **opts):
    a = open('/home/jingwei.li/incoming.log', 'w+')
    a.write(time.ctime())
    a.close()

    publish(ui, repo, node, rebuild = True)

def reposetup(ui, repo):
    ui.setconfig('hooks', 'incoming.autocompile', incominghook)

cmdtable = {
    "opm-publish": (publish,
                [('', 'no-depts', False, '不编译依赖于自己的库'),
                ('', 'commitlog-path', None, 'svn提交log路径'),
                ('', 'rebuild', False, '完整编译，重建发布文件索引')],
               '[options] [NODE]')
}
