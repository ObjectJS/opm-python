#python
#encoding=utf-8

import sys
import os
import os.path
import shutil
import urllib2
import hashlib
import re
from urlparse import urlparse, urljoin
from xml.etree import ElementTree
from filelistener import FileListener
import csscompiler
from csscompiler import CSSCompiler

DEBUG = False
CONFIG_FILENAME = 'template-config.xml'
SOURCE_FILENAME = '.template-info/source'
INFO_PATH = '.template-info/fileinfo'
PACKAGES_FILENAME = '.packages'
PACKAGE_FILENAME = '.package'

def relativeURI(url1, url2):
    u''' url2相对于url1的相对路径字符串 '''
    import re

    # 去掉 ./ 这种表示当前目录的，学习一下 (?<=) 这种前导匹配
    url1 = re.sub(r'(^\./|(?<=/)\./)', lambda m: '', url1)
    url2 = re.sub(r'(^\./|(?<=/)\./)', lambda m: '', url2)
    url1 = url1.split('/')
    url2 = url2.split('/')
    pos = 0
    for i, part in enumerate(url1):
        if url2[i] != part: break
        else: pos = i

    url2 = url2[i:]
    url = len(url1[i+1:]) * '../' + '/'.join(url2)
    return url

def path2uri(path):
    u''' 将windows的path转换成没有协议的uri '''
    return urlparse(path.replace('\\', '/'))[2]

class PackageExistsException(Exception):
    def __init__(self, root_path):
        self.root = root_path

class NotInWorkspaceException(Exception):
    pass

class PackageNotFoundException(Exception):
    def __init__(self, package_url, caller_root = None):
        self.url = package_url
        self.caller = caller_root

class WorkspaceNotFoundException(Exception):
    pass

class ConfigError(Exception):
    def __init__(self, path):
        self.path = path

class StaticPackage():
    u''' 静态编译库 '''

    def __init__(self, root_path, publish_path = None, workspace = None, listener = None):
        self.url = None
        self.combines = {}
        self.listener = listener
        self.workspace = workspace

        self.root = root_path # 框架所在本地目录
        self.publish_path = publish_path # 发布文件的目录路径

        self.source_path = '' # 源文件的目录路径
        self.resource_path = '' # 资源文件目录路径
        self.library_path = '' # 库文件目录路径
        self.library_folders = {}

        self.combine_cache = {self.root: self} # 存储在combine过程中生成的package

        self.resource_dir = None

        self.serverPrefix = ''
        self.serverUrl = ''
        self.serverRoot = ''

        self.load_config()
        if not self.workspace: self.load_workspace()
        if not self.listener: self.init_listener()

    def load_workspace(self):
        workspace_path = Workspace.get_workspace(self.root)
        if workspace_path:
            self.workspace = Workspace(workspace_path)

    def init_listener(self):
        # 不是所有的库都需要有publish_path
        if self.publish_path:
            self.listener = FileListener(os.path.join(self.publish_path, INFO_PATH))

    def get_package(self, root_path):
        u''' 从缓存中获取package引用，如果没有则生成新的并加入缓存 '''
        package = self.combine_cache.get(root_path)
        if not package:
            package = StaticPackage(root_path, self.publish_path, workspace = self.workspace, listener = self.listener)
            self.combine_cache[root_path] = package
            package.combine_cache = self.combine_cache

        return package

    def get_publish_files(self):
        u''' 发布目录所有的css/js文件 '''

        def get_files(dir_path):
            paths = []
            for root, dirs, files in os.walk(dir_path):
                if '.svn' in root:
                    dirs[:] = []
                    continue
                for file in files:
                    path = os.path.join(root, file)
                    if os.path.splitext(path)[1] in ('.css', '.js'):
                        paths.append(path)

            return paths

        files = get_files(self.publish_path)
        return files

    def get_reverse_libs(self, all = False):
        u''' 所有被依赖库 '''

        libs = []
        if self.workspace:
            for local_path in self.workspace.url_packages.values():
                package = self.get_package(local_path)

                # 自己的路径在package相关library中，加入package的路径
                if self.root in package.get_libs():

                    if package.root not in libs:
                        libs.append(package.root)

                    if all:
                        sublibs = package.get_reverse_libs(all = True)
                        libs.extend([subpath for subpath in sublibs if subpath not in libs and subpath != self.root])

        return libs

    def get_sub_packages(self):
        subs = []

        if self.workspace:
            for package_root in self.workspace.local_packages:
                if package_root != self.root and package_root.startswith(self.root):
                    subs.append(package_root)

        else:
            # 遍历磁盘
            pass

        return subs

    def get_libs(self, all = False):
        u''' 所有依赖库 '''

        libs = []

        def get_sub(local_path):
            u'获取一个库的所有依赖库并存入libs'
            package = self.get_package(local_path)
            if package:
                sublibs = package.get_libs(all = True)
                libs.extend([subpath for subpath in sublibs if subpath not in libs])

        if self.workspace:

            if all:
                # 获取sub_packages的所有依赖库
                sub_packages = self.get_sub_packages()
                for local_path in sub_packages:
                    get_sub(local_path)

            for url in self.library_folders.values():
                # url有可能写错了，或者url更改了
                local_path = self.workspace.url_packages.get(url)

                if local_path:
                    if local_path not in libs:
                        libs.append(local_path)

                    if all:
                        get_sub(local_path)

                else:
                    raise PackageNotFoundException(url, self.root)

        return libs

    def get_relation_files(self, source, all = False):
        u''' 在合并过程中相关的文件列表 '''

        filetype = os.path.splitext(source)[1]

        if filetype == '.css' and os.path.exists(source):

            def pathTransformer(path):
                return self.get_library_path(path)

            imports, urls = csscompiler.getUrls(source, pathTransformer = pathTransformer, recursion = all, inAll = True)
            urls.extend(imports)
            # 需要监视的文件列表
            files = [source]
            for aurl in urls:
                # 不支持 http:// 和 绝对路径 
                if not urlparse(aurl)[0] and not urlparse(aurl)[2].startswith('/'):
                    file = os.path.join(os.path.split(source)[0], aurl)
                    file = self.get_library_path(file)
                    files.append(file)

            return files

        elif filetype == '.js' and (source in self.combines.keys() or os.path.exists(source)):
            if all:
                return self.get_combine_files(source)
            else:
                return self.combines[source]

        else:
            # 永远返回一个数组
            return []

    def get_combine_included(self, file):
        u''' 某个文件在当前库中被哪些文件引用了 '''

        files = []
        for combine in self.combines:
            for include in self.combines[combine]:
                if self.get_library_path(include) == file:
                    files.append(combine)
                    continue

        return files

    def get_included(self, source, all = False):
        if os.path.splitext(source)[1] == '.css':
            return []
        else:
            # 到workspace中找一圈
            feed_files = []
            if self.workspace:
                for local_path in self.workspace.local_packages.keys():
                    package = self.get_package(local_path)
                    feed_files.extend(package.get_combine_included(source))
            else:
                feed_files = self.get_combine_included(source)

            if all:
                others = []
                for feed_file in feed_files:
                    others.extend(self.get_included(feed_file, all = True))

                feed_files.extend(others)

            return feed_files

    def get_combine_files(self, path):
        u'''
        @param path 执行合并的文件
        @return relation_files 数组用来存储此文件相关的最小颗粒度的实体文件（非合并出来的文件）
        '''

        relation_files = [] # 存储整个合并过程中最小粒度的文件，最终会按照顺序进行合并

        if path not in self.combines.keys():
            return [path]

        for include in self.combines[path]:

            include = self.get_library_path(include)

            # package变量用来存储需要执行combine方法的package
            # 本框架外部文件
            if not include.startswith(self.source_path):
                root_path = StaticPackage.get_root(include)
                package = self.get_package(root_path)
                package.parse(include)
            # 默认为本package内部文件，为self
            else:
                package = self

            # 一个合并出来的文件
            if include in package.combines.keys():
                rFiles = package.get_combine_files(include)
                relation_files.extend(rFiles)

            # 一个最小粒度的文件
            else:
                relation_files.append(include)

        return relation_files

    def combine(self, output, files):
        u''' 将files文件列表合并成一个文件并写入到output '''

        text = ''
        for file in files:
            text += open(file, 'rb').read()

        target_dir = os.path.dirname(output)
        if not os.path.exists(target_dir): os.makedirs(target_dir)
        open(output, 'wb').write(text)

    def compile(self, filename, force = False):
        filename = os.path.realpath(filename)
        source, mode = self.parse(filename)
        if not source or not self.publish_path or not filename.startswith(self.publish_path):
            return None, None

        # 传进来的有可能是源文件路径 TODO
        if filename.startswith(self.source_path):
            return None, None

        relation_files = self.get_relation_files(source, all = True)
        if not relation_files:
            # 没有源文件的发布文件
            return None, None

        modified, not_exists = self.listener.update(filename, relation_files)

        filetype = os.path.splitext(filename)[1]
        if filetype == '.js':
            if force or len(modified):
                self.combine(filename, relation_files)

            return modified, not_exists

        elif filetype == '.css':
            if DEBUG:
                reload(csscompiler)
            csscompiler.DEBUG = DEBUG

            def pathTransformer(path):
                return self.get_library_path(path)

            if modified or force:
                name = os.path.split(filename)[1]
                cssId = hashlib.md5(urljoin('/' + urljoin(self.serverRoot, self.serverUrl), name)).hexdigest()[:8]

                compiler = CSSCompiler(pathTransformer = pathTransformer)
                css = compiler.compile(source, mode = mode, cssId = cssId)
                css = self.replace_css_url(css, source, name)
                self.write_file(filename, css)

            return (modified, not_exists)

        return None, None

    def replace_css_url(self, css, source, target):
        u''' 将css源文件中的url路径进行转换 '''

        def replaceURL(m):
            url = m.group(1)
            urltuple = urlparse(url)

            # 如果没有协议，则需要进行处理
            if not urltuple[0]:
                # 如果是绝对路径，则同serverPrefix+serverRoot进行拼接
                if url.startswith('/'):
                    prefix = urljoin(self.serverPrefix, self.serverRoot)
                    url = urljoin(prefix, url)

                # 如果是相对路径
                else:
                    # 拼出prefix http://xnimg.cn/n/apps/msg/
                    prefix = urljoin(self.serverPrefix, self.serverRoot)
                    prefix = urljoin(prefix, self.serverUrl)

                    # 本地路径
                    path = os.path.realpath(os.path.join(os.path.split(source)[0], url))

                    # 拼出url css/global-all-min.css
                    relative = target[len(self.publish_path) + 1:].replace('\\', '/')
                    url = urljoin(relative, url)

                    # 在同一目录树的库中，判断url引用的是否是source目录中的东西
                    # 如果是source中的，source中的所有东西都会复制到publish中，因此不需要针对publish进行路径转换
                    # 如果是resource中的，resource会复制到publish中，需要进行路径转换
                    # 如果不是url引用的文件不是source中的，没有复制过程，需要针对publish进行路径转换

                    if self.resource_path and path.startswith(self.resource_path):
                        resource_publish_path = os.path.realpath(os.path.join(self.publish_path, self.resource_dir))
                        url = urljoin(relativeURI(path2uri(self.publish_path), path2uri(resource_publish_path)), url)
                    elif not path.startswith(self.source_path):
                        url = urljoin(relativeURI(path2uri(self.publish_path), path2uri(self.source_path)), url)

                    # 合并成最终的url http://xnimg.cn/n/core/css/global-all-min.css
                    url = urljoin(prefix, url)

            return 'url(' + url + ')'

        return re.sub(r'url\([\'"]?(.+?)[\'"]?\)', replaceURL, css) # 绝对路径

    def build_files(self):
        u''' 复制相关文件 '''

        if not self.publish_path:
            return []

        files = self.build_source_files()
        if self.resource_path:
            files.extend(self.build_resource_files())

        return files

    def build_source_files(self):
        # package下的所有资源文件，忽略 lib 目录
        allFiles = []
        for root, dirs, files in os.walk(self.source_path):
            folders = re.split(r'[/\\]', root)
            if '.svn' in folders \
               or root.startswith(os.path.realpath(os.path.join(self.source_path, 'lib'))):
                continue
            for file in files:
                if os.path.splitext(file)[1] in ('.css', '.xhtml', '.html', '.js', '.xsl', '.xml', '.un~', '.tmp', '.swp'): continue
                path = os.path.join(root, file)
                allFiles.append(path)

        modified, notExists = self.listener.update(self.source_path, allFiles)

        files = []
        for file in modified:
            target = os.path.join(self.publish_path, file[len(self.source_path) + 1:])
            target_dir = os.path.dirname(target)
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)

            shutil.copy(file, target)
            files.append(target)

        return files

    def build_resource_files(self):
        # package下的所有资源文件，忽略 lib 目录
        allFiles = []
        for root, dirs, files in os.walk(self.resource_path):
            folders = re.split(r'[/\\]', root)
            if '.svn' in folders:
                continue
            for file in files:
                path = os.path.join(root, file)
                allFiles.append(path)

        modified, notExists = self.listener.update(self.resource_path, allFiles)

        files = []
        for file in modified:
            resource_publish_path = os.path.realpath(os.path.join(self.publish_path, self.resource_dir))
            target = os.path.join(resource_publish_path, file[len(self.resource_path) + 1:])
            target_dir = os.path.dirname(target)
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)

            shutil.copy(file, target)
            files.append(target)

        return files


    def write_file(self, path, txt):
        cssfile = open(path, 'wb')
        cssfile.write(txt)
        cssfile.close()

    def joinpath(self, path1, path2):
        return os.path.realpath(os.path.join(path1, path2))

    def parse_config(self, xmlConfig):
        # 已通过source文件读取到publish_path信息
        # 或者已经通过构造函数传进了publish_path信息
        # 不用通过template-config.xml读取
        # source引用方式下，不需要配置文件的publish配置
        if self.publish_path:
            pass

        # 没有source文件，publish_path同库在同一个目录树，需要通过publish配置生成publish_path信息
        else:
            publishNode = xmlConfig.find('publish')
            if publishNode != None:
                publishDir = xmlConfig.find('publish').get('dir')
                if not publishDir.endswith('/'): publishDir += '/'

                self.publish_path = self.joinpath(self.root, publishDir)

        self.url = xmlConfig.get('url')

        # source 是必需的
        sourceDir = xmlConfig.find('source').attrib['dir']
        if not sourceDir.endswith('/'): sourceDir += '/'
        self.source_path = self.joinpath(self.root, sourceDir)

        libraryNode = xmlConfig.find('library')
        if libraryNode != None:
            libraryDir = libraryNode.get('dir')
            self.library_path = self.joinpath(self.root, libraryDir)
            folderNodes = libraryNode.findall('folder')
            for folderNode in folderNodes:
               self.library_folders[folderNode.get('name')] = folderNode.get('url')

        resourceNode = xmlConfig.find('resource')
        if resourceNode != None and 'dir' in resourceNode.attrib.keys():
            self.resource_dir = resourceNode.attrib['dir']
            if not self.resource_dir.endswith('/'): self.resource_dir += '/'
            self.resource_path = self.joinpath(self.root, self.resource_dir)

        serverNode = xmlConfig.find('server')
        if serverNode != None:
            if 'prefix' in serverNode.attrib:
                self.serverPrefix = serverNode.attrib['prefix']

            if 'url' in serverNode.attrib:
                self.serverUrl = serverNode.attrib['url']

            if 'root' in serverNode.attrib:
                self.serverRoot = serverNode.attrib['root']

        if self.serverUrl and not self.serverUrl.endswith('/'):
            self.serverUrl = self.serverUrl + '/'

        if self.serverRoot and not self.serverRoot.endswith('/'):
            self.serverRoot = self.serverRoot + '/'

        combinesXML = xmlConfig.findall('source/combine')
        if combinesXML:
            for combine in combinesXML:
                key = self.joinpath(self.source_path, combine.get('path'))
                includesXML = combine.findall('include')
                includes = []
                for include in includesXML:
                    includePath = self.joinpath(self.source_path, include.get('path'))
                    includes.append(includePath)

                self.combines[key] = includes

    def load_config(self):
        ''' 解析配置文件 '''
        path = os.path.join(self.root, CONFIG_FILENAME)
        xmlConfig = ElementTree.parse(path)
        self.parse_config(xmlConfig.getroot())

    def get_library_path(self, includePath):
        includePath = os.path.realpath(includePath)
        # lib下的，要通过packages转换一下路径
        if includePath.startswith(self.library_path):
            path = includePath[len(self.library_path) + 1:]
            if path.find(os.sep) != -1: # lib/xxx.js 直接放，没有在一个library目录中
                folderName, pathInPackage = path.split(os.sep, 1) # lib下的目录名和相应package的内部路径
                if folderName in self.library_folders.keys():
                    url = self.library_folders[folderName]
                    if not self.workspace:
                        raise WorkspaceNotFoundException()

                    local_path = self.workspace.url_packages.get(url)
                    if local_path:
                        package = self.get_package(local_path)
                        new_path = os.path.join(package.root, pathInPackage)
                        return os.path.realpath(new_path)
                    # 在lib下，也定义了folder，但是相对应的url没有在packages中配置本地磁盘的路径，或者相应的库没有配置package的url属性
                    else:
                        raise PackageNotFoundException(url, self.root)

        return includePath

    def parse(self, path):
        u''' source 和 publish 路径一一对应 '''

        path = os.path.realpath(path)

        if path.startswith(self.source_path):
            return path, None

        elif self.publish_path and path.startswith(self.publish_path):
            package_path = path[len(self.publish_path) + 1:]

            if os.path.splitext(path)[1] == '.css':
                # xxx-all-min.css --> xxx
                package_path = os.path.splitext(package_path)[0].split('-')
                if len(package_path) < 3: return (None, None)
                name = '-'.join(package_path[:-2])
                mode = package_path[-2]
                source = os.path.join(self.source_path, name + '.css')
            else:
                source = os.path.join(self.source_path, package_path)
                mode = None

            return source, mode

        # 有可能是lib下的
        else:
            return None, None

    def link(self):
        u''' 连接源库与发布库 '''

        if self.url:
            package_file_path = os.path.join(self.publish_path, PACKAGE_FILENAME)
            open(package_file_path, 'wb').write(self.url)

        source_path = os.path.join(self.publish_path, SOURCE_FILENAME)
        source_dir = os.path.dirname(source_path)
        if not os.path.exists(source_dir):
            os.makedirs(source_dir)

        open(source_path, 'wb').write(self.root)

    @staticmethod
    def init(root_path):
        u''' 初始化一个目录为源库 '''

        root_path = os.path.realpath(root_path)
        config_path = os.path.join(root_path, CONFIG_FILENAME)

        if os.path.exists(config_path):
            raise PackageExistsException(root_path)

        if not os.path.exists(root_path):
            os.makedirs(root_path)

        open(config_path, 'wb').write(
            '<package>\n\t<library dir="lib">\n\t</library>\n\t<source dir="src">\n\t</source>\n\t<resource dir="res">\n\t</resource>\n</package>'
        )

    @staticmethod
    def is_root(path):
        u''' path是否是一个静态库的根路径 '''
        return os.path.exists(os.path.join(path, CONFIG_FILENAME))

    @staticmethod
    def get_root(path):
        u'''一个目录的源库根路径'''
        return StaticPackage.get_roots(path)[1]

    @staticmethod
    def get_publish(path):
        u''' 一个路径的发布库根路径 '''
        return StaticPackage.get_roots(path, just_publish_path = True)

    @staticmethod
    def get_roots(path, just_publish_path = False, workspace = None):
        u''' 通过遍历父目录查找root及publish_path '''

        publish_path = None
        root_path = None

        if os.path.isfile(path):
            path = os.path.dirname(path)

        while True:
            # 通过找 source 的方式读取到地址
            publish_source_path = os.path.join(path, SOURCE_FILENAME)
            if os.path.exists(publish_source_path):
                publish_path = path
                root_path = os.path.realpath(open(publish_source_path, 'r').read().strip())
                if just_publish_path: break

            # 通过.package 文件读取到地址
            if workspace:
                package_file_path = os.path.join(path, PACKAGE_FILENAME)
                if os.path.exists(package_file_path):
                    publish_path = path
                    package_url = open(package_file_path, 'r').read().strip()
                    package = workspace.get_package_by_url(package_url)
                    if not package:
                        raise PackageNotFoundException(package_url)
                    root_path = package.root
                    if just_publish_path: break

            # 直接找到配置文件
            if not just_publish_path and StaticPackage.is_root(path):
                root_path = os.path.realpath(path)
                break

            newpath = os.path.realpath(os.path.join(path, '../'))
            if newpath == path: break # 已经到根目录了，停止循环
            else: path = newpath

        if just_publish_path:
            return publish_path
        else:
            return publish_path, root_path

class Workspace():
    u''' 工作区 '''

    def __init__(self, root):
        self.root = root
        self.packages_file_path = os.path.join(self.root, PACKAGES_FILENAME)
        self.url_packages = {}
        self.local_packages = {}
        self.useless_packages = []
        self.remote_server = 'http://hg.xnimg.cn/'
        self.init_packages()

    def init_packages(self):
        if not os.path.exists(self.packages_file_path): return

        packages_file = open(self.packages_file_path, 'r').read().strip()
        if packages_file:
            lines = packages_file.split('\n')
        else:
            lines = []

        for package_path in lines:
            package_path, publish_path = re.match('^(.+?)\s*(?:=\s*(.+)?)?$', package_path.strip()).groups()
            local_path = os.path.realpath(os.path.join(self.root, package_path))
            self.add_package(local_path)

    def remote2local(self, package):
        u''' 将一个remotepackage的地址转换成当在本地时的地址 '''
        return os.path.realpath(os.path.join(self.root, package.hg_dir))

    def fetch_packages(self, package_url):
        u''' 根据package url找到所有相关package '''

        remote_workspace = RemoteWorkspace(self.remote_server)

        if package_url not in remote_workspace.url_packages.keys():
            raise PackageNotFoundException(package_url, self.root)

        path = remote_workspace.url_packages[package_url]
        package = RemoteStaticPackage(path, workspace = remote_workspace)

        packages = [path]

        for local_path in package.get_libs(all = True):
            packages.append(local_path)

        # 所有子库的相关依赖库
        for sub in package.subs:
            sub = package.get_package(sub)
            for local_path in sub.get_libs(all = True):
                if local_path not in packages:
                    packages.append(local_path)

        packages = [package.get_package(root_path) for root_path in packages]

        return packages

    def fetch(self, package):
        u''' 将一个package下载到本地工作区 '''

        # hg update
        def hg_update(local_path):
            dir = os.path.realpath(os.curdir)
            os.chdir(local_path)
            a = os.system('hg update')
            os.chdir(dir)

        # hg clone
        def hg_clone(url, local_path, noupdate = False):
            #print 'hg clone ' + ('--noupdate ' if noupdate else '')  + '%s %s' % (url, local_path)
            os.system('hg clone ' + ('--noupdate ' if noupdate else '')  + '%s %s' % (url, local_path))

        local_path = self.remote2local(package)

        # 本地已经有这个package了
        if os.path.exists(local_path):
            hg_update(local_path)

        # 本地存放的路径有可能与远程并不相同
        elif package.url in self.url_packages:
            local_path = self.url_packages[package.url]
            hg_update(local_path)

        # 本地没有，按照远程的路径获取
        else:
            self.add_package(local_path)

            # 处理父路径
            for parent in package.parents:
                parent = package.get_package(parent)
                parent_local_path = os.path.realpath(os.path.join(self.root, parent.hg_dir))
                if not os.path.exists(parent_local_path):
                    hg_clone(parent.hg_root, parent_local_path, noupdate = True)

            hg_clone(package.hg_root, local_path)

            # 处理子库，加入workspace
            for sub in package.subs:
                sub = package.get_package(sub)
                self.add_package(self.remote2local(sub))

    def load(self):
        for root, dirs, files in os.walk(self.root):
            if StaticPackage.is_root(root):
                if not self.has_package(root):
                    self.add_package(root)

        self.rebuild_package()

    def get_package_by_url(self, url):
        local_path = self.url_packages.get(url)
        if local_path:
            package = StaticPackage(local_path, workspace = self)
            return package

    def has_package(self, root_path):
        root_path = os.path.realpath(root_path)
        return root_path in self.local_packages.keys()

    def add_package(self, local_path):
        local_path = os.path.realpath(local_path)
        if not local_path.startswith(os.path.realpath(self.root)):
            raise NotInWorkspaceException

        config_path = os.path.join(local_path, CONFIG_FILENAME)
        if not os.path.exists(config_path):
            self.useless_packages.append(local_path)
        else:
            try:
                package_config = ElementTree.parse(config_path)
            except BaseException as e:
                raise ConfigError(config_path)
            else:
                package_url = package_config.getroot().get('url')
                self.local_packages[local_path] = package_url
                if package_url: self.url_packages[package_url] = local_path
                self.rebuild_package()

    def rebuild_package(self):
        # 不要在fastcgi中rebuild_package，因为没有文件锁，会出问题，给出提示即可。
        packages_file = open(self.packages_file_path, 'wb')
        packages = self.local_packages.keys()
        packages.sort()
        for local_path in packages:
            packages_file.write(self.transform_name(local_path) + '\n')

        packages_file.close()

    def transform_name(self, path):
        return path2uri(path[len(self.root) + 1:])

    @staticmethod
    def get_workspace(workspace_path):
        u''' 源库所在工作区 '''

        while True:
            if Workspace.is_root(workspace_path):
                return workspace_path
            else:
                newpath = os.path.realpath(os.path.join(workspace_path, '../'))
                if newpath == workspace_path: return
                else: workspace_path = newpath

        return None

    @staticmethod
    def is_root(path):
        u''' path是否是一个工作区的根路径 '''
        return os.path.exists(os.path.join(path, PACKAGES_FILENAME))

class RemoteWorkspace(Workspace):
    u'远程Workspace'

    def init_packages(self):
        sock = urllib2.urlopen(self.root + '_/raw-file/tip/.packages')
        lines = sock.read().strip().split('\n')
        for package_path in lines:
            package_path, publish_path = re.match('^(.+?)\s*(?:=\s*(.+)?)?$', package_path.strip()).groups()
            remote_path = urljoin(self.root, package_path + '/raw-file/tip/')
            config_path = urljoin(remote_path, CONFIG_FILENAME)
            try:
                sock = urllib2.urlopen(config_path)
            except:
                self.useless_packages.append(remote_path)
            else:
                try:
                    package_config = ElementTree.fromstring(sock.read())
                except BaseException as e:
                    raise ConfigError(config_path)
                else:
                    package_url = package_config.get('url')
                    self.local_packages[remote_path] = package_url
                    if package_url: self.url_packages[package_url] = remote_path
                    sock.close()

        sock.close()

class RemoteStaticPackage(StaticPackage):
    u'远程静态库'

    def __init__(self, root_path, publish_path = None, workspace = None, listener = None):
        StaticPackage.__init__(self, root_path, publish_path = publish_path, workspace = workspace, listener = listener)

        self.hg_root = self.get_hg_path(root_path)
        self.hg_dir = self.get_hg_path(root_path[len(self.workspace.root):])

        parents = []
        subs = []
        hg_root = self.get_hg_path(self.root)
        for path in self.workspace.local_packages:
            if path != self.root:
                if self.root.startswith(self.get_hg_path(path)):
                    parents.append(path)
                elif path.startswith(hg_root):
                    subs.append(path)

        # 按照路径长短排序，短的排前面，确保生成路径时先生成短的，先生成长的会导致短的无法生成
        self.parents = sorted(parents, cmp = lambda x, y: cmp(len(x), len(y)))
        self.subs = sorted(subs, cmp = lambda x, y: cmp(len(x), len(y)))

    def joinpath(self, path1, path2):
        return urljoin(path1, path2)

    def load_config(self):
        ''' 解析配置文件 '''
        config_path = urljoin(self.root, CONFIG_FILENAME)
        sock = urllib2.urlopen(config_path)
        package_config = ElementTree.fromstring(sock.read())
        self.parse_config(package_config)
        sock.close()

    def get_package(self, root_path):
        u''' 从缓存中获取package引用，如果没有则生成新的并加入缓存 '''
        package = self.combine_cache.get(root_path)
        if not package:
            package = RemoteStaticPackage(root_path, self.publish_path, workspace = self.workspace, listener = self.listener)
            self.combine_cache[root_path] = package
            package.combine_cache = self.combine_cache

        return package

    @staticmethod
    def get_hg_path(path):
        if path.endswith('/raw-file/tip/'):
            return path[:-13] # remove /raw-file/tip/ at the end
        else:
            return path
