#python
#encoding=utf-8
import os
import sys
import ui
import utils.commandline
from utils.commandline import arg, cwdarg, option, usage
from staticcompiler import StaticPackage, Workspace, PublishPackageException, PackageNotFoundException, PackageExistsException, FetchException

@cwdarg
@usage(u'scompiler get [源库url]')
@arg('url')
def get(workspace, url):
    u''' 从公共代码库获取源库 '''

    if workspace.__class__ == str:
        workspace = Workspace(workspace)

    load(workspace)

    try:
        packages = workspace.fetch_packages(url)
    except PackageNotFoundException, e:
        ui.error('%s package not found' % e.url)
        return 1
    else:
        for package in packages:
            try:
                workspace.fetch(package)
            except FetchException, e:
                ui.error(u'fetch error')
            except PackageExistsException, e:
                ui.error(u'%s package already exists' % e.root)

    load(workspace)

@cwdarg
@usage(u'opm workspace [源库路径]')
def workspace(root_path):
    u''' 源库所在工作区 '''
    if StaticPackage.get_root(root_path):
        ui.msg(Workspace.get_workspace(root_path))
    else:
        ui.msg(u'不是一个源库')
        return 1

@arg('filename')
@option('force', '-f', '--force', action = 'store_true', help = u'强制重新编译')
@option('no_build_files', '--no-build-files', action = 'store_true', help = u'不发布相关文件')
@usage(u'opm compile 发布库中的某个js/css文件 [options]')
def compile(filename, package = None, force = False, no_build_files = False):
    u'编译一个css/js文件'

    if not package:
        root_path = StaticPackage.get_root(filename)

        if not root_path:
            ui.error(u'没有找到源文件')
            return 1
        else:
            package = StaticPackage(root_path)

    try:
        modified, not_exists = package.compile(filename, force = force)
    except IOError, e:
        ui.error('%s file not found' % e.filename)
        return 1
    except PackageNotFoundException, e:
        ui.error('%s package not found' % e.url)
        return 1

    if modified or (force and modified != None):
        for modified_file in modified:
            ui.msg(u'Modified: %s' % modified_file)

        ui.msg(u'Compiled: %s' % filename)

    if not no_build_files:
        buildfiles(package = package)

def buildfiles(package = None):
    files = package.build_files()
    for build_file in files:
        ui.msg(u'Copy File: %s' % build_file)

@cwdarg
@arg('link_path')
@option('force', '-f', '--force', action='store_true', help=u'强制建立发布文件夹')
def link(path, link_path, force = False):
    u''' 将发布库与源库进行映射

如果库设置了url，则同时使用.package文件进行连接，需要工作区支持，如果没有url，则只进行本地连接。'''

    publish_path, root_path = StaticPackage.get_roots(path)
    if not publish_path and not root_path and link_path:
        publish_path, root_path = StaticPackage.get_roots(link_path)
        path, link_path = link_path, path

    if not publish_path:
        publish_path = os.path.realpath(link_path)
    else:
        root_path = os.path.realpath(link_path)

    if not root_path:
        ui.error('package not found')

    package = StaticPackage(root_path, publish_path = publish_path)

    if not os.path.exists(publish_path):
        if force:
            os.makedirs(publish_path)
        else:
            ui.msg(u'%s path not exists, run opm link path -f to create it.' % publish_path)
            return 1

    package.link()

    ui.msg(u'linked publish %s to %s' % (publish_path, root_path))

@cwdarg
@arg('publish_path')
@option('force', '-f', '--force', help = u'强制编译', action = 'store_true')
@usage(u'opm publish [源库路径] [发布库路径] [options]')
def publish(path, publish_path = None, force = False):
    u'''将整个目录进行发布'''

    do_link = False
    # 指定了第二个参数，则path一定是一个源库，第二个参数则是发布库，并自动进行link
    if publish_path:
        root_path = StaticPackage.get_root(path)
        path = publish_path # 发布整个库
        do_link = True
    # 没有指定第二个参数，则path一定是一个发布库
    else:
        publish_path, root_path = StaticPackage.get_roots(path)

    if not publish_path:
        ui.msg(u'No publish path.')
    else:
        package = StaticPackage(root_path, publish_path = publish_path)
        if not package.publish_path:
            ui.msg(u'No publish path.')
        else:
            ui.msg(u'publish to %s from %s' % (path, package.root))
            all_files = package.get_publish_files()
            for filename in all_files:
                compile(filename, package = package, force = force, no_build_files = True)

        buildfiles(package = package)
        if do_link:
            package.link()

@cwdarg
@usage(u'opm load [工作区路径]')
def load(workspace):
    u''' 加载本地工作区 '''

    if workspace.__class__ == str:
        workspace = Workspace(workspace)

    old_count = len(workspace.local_packages)
    workspace.load()
    added_count = len(workspace.local_packages) - old_count

    if len(workspace.useless_packages):
        for package in workspace.useless_packages:
            ui.msg(u'删除无用package %s' % package)

    ui.msg(u'已加入 %s 个源库' % added_count)

@cwdarg
@option('show_url', '-u', '--show-url', action = 'store_true', help = u'显示有url的源库的url')
@usage(u'opm packages [工作区路径]')
def packages(workspace_path, show_url = False):
    u''' 本工作区中所有源库 '''

    if os.path.isfile(workspace_path):
        workspace_path = os.path.dirname(workspace_path)

    # 有可能不是workspace跟路径，而是某个子路径
    workspace_path = Workspace.get_workspace(workspace_path)
    if not workspace_path:
        ui.error(u'没有工作区')
        return 1
    else:
        workspace = Workspace(workspace_path)
        if show_url:
            for url in workspace.url_packages.keys():
                ui.msg(url)
        else:
            for local_path in workspace.local_packages.keys():
                ui.msg(os.path.realpath(os.path.join(workspace.root, local_path)))

@cwdarg
@option('publish_path', '-p', '--publish-path', type = 'string', help = u'发布目录')
@option('force', '-f', '--force', action = 'store_true', help = u'强制建立发布目录')
def init(root_path, publish_path = None, force = False):
    u''' 初始化一个新的库
    
初始化一个新的库，建立template-config.xml配置文件及常用的目录，如果指定了 -p 参数，还可以自动建立与发布目录的连接'''
    ui.msg(u'初始化%s' % root_path)
    try:
        ui.msg(u'创建配置文件')
        StaticPackage.init(root_path)

    except PublishPackageException:
        ui.error(u'发布目录不能被初始化')
        return 1

    except PackageExistsException:
        ui.error(u'已经存在')
        return 1

    pathnames = ['test', 'doc', 'src', 'lib', 'res']
    for name in pathnames:
        path = os.path.join(root_path, name)
        if not os.path.exists(path):
            os.makedirs(path)
            ui.msg(u'生成默认目录 %s' % name)

    workspace_path = Workspace.get_workspace(root_path)
    if not workspace_path:
        ui.msg(u'没有工作区，请参照 opm help load')
    else:
        workspace = Workspace(workspace_path)

        if not workspace.has_package(root_path):
            workspace.add_package(root_path)
            ui.msg(u'加入本地工作区')
        else:
            ui.msg(u'本地工作区中已存在')

    ui.msg(u'成功！')

    if publish_path:
        link(root_path, publish_path, force = force)

@cwdarg
@usage(u'opm root [源库路径]')
def root(root_path):
    u''' 源库的根路径 '''
    ui.msg(StaticPackage.get_root(root_path))

@cwdarg
@usage(u'opm source [源库路径] [options]')
def source(publish_path):
    u''' 映射的源库路径 '''
    if StaticPackage.get_publish(publish_path):
        StaticPackage.get_root(publish_path)
    else:
        ui.error(u'不是一个发布库')

@cwdarg
def status(publish_path):
    u''' 检查发布库的编译状态 '''
    publish_path, root_path = StaticPackage.get_roots(publish_path)
    if not publish_path:
        ui.error(u'不是发布库')
        return 1

    package = StaticPackage(root_path, publish_path)

    files = package.get_publish_files()
    for filename in files:
        filetype = os.path.splitext(filename)[1]

        source, mode = package.parse(filename)
        rfiles = package.get_relation_files(source, all = True)
        modified, not_exists = package.listener.check(source, rfiles)
        if len(modified) or len(not_exists):
            for modified_file in modified:
                ui.msg('M ' + modified_file)

            for not_exists_file in not_exists:
                ui.msg('! ' + not_exists_file)

@cwdarg
@usage(u'opm libs [源库路径]')
@option('show_url', '-u', '--show-url', help=u'显示url而非本地路径', action='store_true')
@option('all', '-a', '--all', help=u'递归显示所有', action='store_true')
@option('reverse', '-r', '--reverse', help=u'显示被依赖的', action='store_true')
def libs(root_path, show_url = False, all = False, reverse = False):
    u''' 库的相关依赖库 '''
    root_path = StaticPackage.get_root(root_path)
    if not root_path:
        ui.error(u'不是源库')
        return 1

    package = StaticPackage(root_path)
    # 这个库没有设置url，不可能被别的库依赖
    if not package.url:
        ui.error(u'no url')
        return 1

    # 显示依赖自己的
    if reverse:
        libs = package.get_reverse_libs(all = all)
    # 显示依赖了谁
    else:
        libs = package.get_libs(all = all)

    if show_url:
        if package.workspace:
            for local_path in libs:
                url = package.workspace.local_packages.get(local_path)
                if url:
                    ui.msg(url)

        else:
            ui.error(u'没有工作区')
    else:
        for local_path in libs:
            ui.msg(local_path)

@arg('filename')
@option('all', '-a', '--all', help=u'递归显示所有', action='store_true')
@option('reverse', '-r', '--reverse', help=u'显示被依赖的', action='store_true')
def incs(filename, all = False, reverse = False):
    u''' 某文件所有依赖的文件 '''

    filename = os.path.realpath(filename)
    root_path = StaticPackage.get_root(filename)
    package = StaticPackage(root_path)

    filetype = os.path.splitext(filename)[1]

    if reverse:
        if filetype == '.css':
            ui.error(u'Not support yet, sorry.')
            return 1
        else:
            files = package.get_included(filename, all = all)
    else:
        files = package.get_relation_files(filename, all = all)

    for file in files:
        ui.msg(file)

@cwdarg
@option('fastcgi', '--fastcgi', help = u'使用fastcgi进行serve', action = 'store_true')
@option('port', '--port', help = u'指定端口号', type = 'int')
@option('debug', '-d', '--debug', help = u'debug模式', action = 'store_true')
@option('noload', '-n', '--noload', help = u'启动时不load工作区', action = 'store_true')
def serve(workspace_path, fastcgi = False, port = 8080, debug = False, noload = False):
    u''' 启动一个静态服务器

请指定工作区路径'''

    if Workspace.is_root(workspace_path):
        workspace = Workspace(os.path.realpath(workspace_path))
        if not noload:
            load(workspace = workspace)
    else:
        ui.error(u'工作区无效');
        workspace = None

    def print_request(environ, start_response):
        ''' 输出fastcgi本次请求的相关信息 '''

        import cgi
        start_response('200 OK', [('Content-Type', 'text/html')])
        yield '<html><head><title>Hello World!</title></head>\n' \
              '<body>\n' \
              '<p>Hello World!</p>\n' \
              '<table border="1">'
        names = environ.keys()
        names.sort()
        for name in names:
            yield '<tr><td>%s</td><td>%s</td></tr>\n' % (
                name, cgi.escape(`environ[name]`))

        form = cgi.FieldStorage(fp=environ['wsgi.input'], environ=environ,
                                keep_blank_values=1)
        if form.list:
            yield '<tr><th colspan="2">Form data</th></tr>'

        for field in form.list:
            yield '<tr><td>%s</td><td>%s</td></tr>\n' % (
                field.name, field.value)

        yield '</table>\n' \
              '</body></html>\n'

    def listen(environ, start_response):
        ''' 监听请求 '''
        if environ['DOCUMENT_URI'].endswith('/fuck.css'):
            return print_request(environ, start_response)

        DEBUG = debug

        filename = os.path.realpath(environ['REQUEST_FILENAME'])
        url = environ['DOCUMENT_URI']

        force = False # 是否强制重新编译
        # 没有 referer 时强制重新编译
        if not 'HTTP_REFERER' in environ.keys():
            force = True

        try:
            publish_path, root_path = StaticPackage.get_roots(filename, workspace = workspace)
        except PackageNotFoundException, e:
            ui.error(u'%s package not found' % e.url)
        else:
            if root_path:
                package = StaticPackage(root_path, publish_path, workspace = workspace)
                compile(filename, package = package, force = force, no_build_files = True)
                buildfiles(package = package)

        mimetypes = {
            '.css': 'text/css',
            '.js': 'text/javascript'
        }
        mimetype = mimetypes[os.path.splitext(filename)[1]]

        if not os.path.exists(filename):
            # 文件不存在
            start_response('404 Not Found', [])
            return '404 Not Found'

        start_response('200 OK', [('Content-Type', mimetype)])
        return [open(filename).read()]

    if fastcgi:
        from flup.server.fcgi import WSGIServer

        WSGIServer(listen, bindAddress=('localhost', port), debug = debug).run()
    else:
        ui.msg(u'现在还不支持server，请使用 opm serve --fastcgi 方式')

def main():
    commands = [get, init, compile, publish, link, load, serve, packages, workspace, root, source, status, libs, incs]
    if len(sys.argv) < 2:
        ui.msg(u'使用 opm help 得到用法')
    else:
        command = sys.argv[1]
        if command == 'help':
            subcommand = None
            if len(sys.argv) > 2:
                subcommand = globals()[sys.argv[2]]
            utils.commandline.help(commands, subcommand)
        else:
            all = globals()
            if command in all:
                utils.commandline.call(commands, globals()[command])
            else:
                utils.commandline.help(commands)
