#!/bin/sh

START=`date +%s`

XN_STATIC=/opt/xn.static
scompiler=/opt/staticcompiler/staticcompiler.py
# 获取刚刚push的库属于哪个分支，只对default分支进行编译
branch=`hg log -r $HG_NODE --template {branch}`
# 必须用全路径，compile函数在不同路径下工作
commitlog=`pwd`/commitlog.txt

compile() {

	if [ -f .publish ]; then
		tmp=`cat .publish`
		publish_path=`eval echo $tmp`
		svn update $publish_path --accept theirs-full >> /dev/null
		python $scompiler publish $publish_path
		cd $publish_path
		svn add * --force
		svn commit -F $commitlog
		cd -
	else
		echo can\'t find .publish file for `pwd`
	fi
}

update_repo() {

	# hg优先级更高，因为有些库是hg、svn共同都在维护的
	if [ -d .hg ]; then
		echo $repo is a hg repo, hg update
		# hg update 不能传参数
		hg update >> /dev/null
	else
		echo $repo is a svn repo, svn update
		svn update >> /dev/null
	fi
}

if [ "$branch" = "default" ]; then
	# 编译当前库
	cd .
	parent=`hg parents --template {rev}`
	hg update >> /dev/null
	rev=`hg tip --template {rev}`
	echo up $parent to $rev
	# 将log保存到commitlog
	hg log -r $parent:$rev > $commitlog

	# 更新依赖的库
	python $scompiler libs -a | while read repo; do
		cd $repo
		update_repo
	done

	# 编译当前库
	compile

	# 编译依赖自己的库
	# 编译时并不更新其依赖库
	python $scompiler libs -r -a | while read repo; do
		cd $repo
		compile
	done

	rm $commitlog

else
	echo ignore branch $branch.
fi

END=`date +%s`
echo "Duration: $(($END-$START))s"
