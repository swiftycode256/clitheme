# clitheme - 命令行应用文本主题框架

`clitheme` 允许你定制命令行应用程序的输出，给它们一个你想要的风格和个性。

样例：
```
$ example-app install-files
在当前目录找到了2个文件
-> 正在安装 "example-file"...
-> 正在安装 "example-file-2"...
已成功安装2个文件
$ example-app install-file foo-nonexist
错误：找不到文件 "foo-nonexist"
```
```
$ clitheme apply-theme example-app-theme_clithemedef.txt
==> Generating data...
Successfully generated data
==> Applying theme...Success
Theme applied successfully
```
```
$ example-app install-files
o(≧v≦)o 太好了，在当前目录找到了2个文件！
(>^ω^<) 正在安装 "example-file"...
(>^ω^<) 正在安装 "example-file-2:"...
o(≧v≦)o 已成功安装2个文件！
$ example-app install-file foo-nonexist
ಥ_ಥ 糟糕，出错啦！找不到文件 "foo-nonexist"
```

## 功能

- 多语言支持
- 支持同时应用多个主题（待办）
- 简洁易懂的主题信息文件（clithemedef）语法
- 无需前端API也可访问当前主题数据（易懂的数据结构）

`clitheme` 不仅可以定制命令行应用的输出，它还可以：
- 为应用添加多语言支持
- 支持图形化应用

## 安装（待办）

安装`clitheme`非常简单，您可以通过Arch Linux软件包或者pip软件包安装。

### 通过Arch Linux软件包安装

todo

### 通过pip软件包安装

从最新发行版页面下载whl文件，使用pip直接安装即可：
    
    $ pip install clitheme-release-latest.whl

## 详细信息

具体的详细信息和文档请看本项目Wiki页面