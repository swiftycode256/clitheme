#!/usr/bin/python3

import os
import sys
from src.clitheme import frontend

demo_message="""正在展示{}演示（不会修改系统上的文件）："""

help_usage=\
"""
{0} install-files
{0} install-file [FILE]
{0} --help
{0} --clitheme-output-defs
"""

frontend.global_domain="com.example"
frontend.global_appname="example-app"
f=frontend.FetchDescriptor()

if len(sys.argv)>1 and sys.argv[1]=="install-files":
    if len(sys.argv)!=2:
        print(f.retrieve_entry_or_fallback("format-error", "错误：命令语法不正确"))
        exit(1)
    print(demo_message.format(sys.argv[1]))
    dirfiles=os.listdir()
    if len(dirfiles)==0:
        print(f.retrieve_entry_or_fallback("directory-empty","错误：当前目录里没有任何文件"))
    print(f.retrieve_entry_or_fallback("found-file", "在当前目录找到了{}个文件").format(str(len(dirfiles))))
    for item in dirfiles:
        print(f.retrieve_entry_or_fallback("installing-file", "-> 正在安装 \"{}\"...").format(item))
    print(f.retrieve_entry_or_fallback("install-success","已成功安装{}个文件").format(str(len(dirfiles))))
elif len(sys.argv)>1 and sys.argv[1]=="install-file":
    if len(sys.argv)!=3:
        print(f.retrieve_entry_or_fallback("format-error", "错误：命令语法不正确"))
        exit(1)
    print(demo_message.format(sys.argv[1]))
    item=sys.argv[2].strip()
    if os.path.exists(item):
        print(f.retrieve_entry_or_fallback("installing-file", "-> 正在安装 \"{}\"...").format(item))
        print(f.retrieve_entry_or_fallback("install-success-file","已成功安装\"{}\"").format(item))
    else:
        print(f.retrieve_entry_or_fallback("file-not-found","错误：找不到文件\"{}\"").format(item))
        exit(1)
else:
    f2=frontend.FetchDescriptor(subsections="helpmessage")
    print(f2.retrieve_entry_or_fallback("description-general","文件安装程序样例（不会修改系统中的文件）"))
    print(f2.retrieve_entry_or_fallback("description-usageprompt","使用方法："))
    print(help_usage.format(sys.argv[0]))
    if len(sys.argv)>1 and sys.argv[1]=="--help":
        exit(0)
    elif len(sys.argv)>1:
        print(f2.retrieve_entry_or_fallback("unknown-command","错误：未知命令\"{}\"").format(sys.argv[1]))
    exit(1)