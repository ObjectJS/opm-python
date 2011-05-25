set pyinstaller=d:\works\pyinstaller-1.5-rc1
python %pyinstaller%/makespec.py --onefile --upx --paths .;cssutils-0.9.7a3-py2.6.egg;C:\Python27\Lib\site-packages\flup-1.0.3.dev_20110405-py2.7.egg --name scompiler staticcompiler.py
python %pyinstaller%/build.py scompiler.spec
