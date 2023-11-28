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
- 简洁易懂的主题信息文件（`clithemedef`）语法
- 无需前端API也可访问当前主题数据（易懂的数据结构）

`clitheme` 不仅可以定制命令行应用的输出，它还可以：
- 为应用添加多语言支持
- 支持图形化应用

## 前端实施和编写主题文件

应用程序是主要通过**路径名称**来指定所需的字符串。这个路径由空格分开来区别子路径。大部分时候路径的前两个名称是用来指定开发者和应用名称的。

比如`com.example example-app example-text`指的是`com.example`开发的`example-app`中的`example-text`字符串。

当然，路径名称也可以是全局的（不和任何应用信息关联），如`global-entry`或`global-example global-text`。

如果当前主题没有适配某个字符串，前端API将会使用调用时提供的备用字符串。

### 使用内置前端API

使用`clitheme`的python前端API非常简单，并且可以提供一些额外的信息。

我们拿上面的样例来示范：

```
from clitheme import frontend
[...]
f=frontend.FetchDescriptor(domain_name="com.example", app_name="example-app")

# 对应 “在当前目录找到了2个文件”
fcount=[...]
f.retrieve_entry_or_fallback("found-file", "在当前目录找到了{}个文件".format(str(fcount)))

# 对应 “-> 正在安装 "example-file"...”
filename=[...]
f.retrieve_entry_or_fallback("installing-file", "-> 正在安装\"{}\"...".format(filename))

# 对应 “已成功安装2个文件”
f.retrieve_entry_or_fallback("install-success", "已成功安装{}个文件".format(str(fcount)))
```

### 编写主题文件

关于主题文件的详细语法请见Wiki文档，下面将展示一个样例：

```
begin_header
    name 样例主题
    version 1.0
    locales zh_CN
end_header

begin_main
    in_domainapp com.example example-app
        entry found-file
            locale default o(≧v≦)o 太好了，在当前目录找到了{}个文件！
            locale zh_CN o(≧v≦)o 太好了，在当前目录找到了{}个文件！
        end_entry
        entry installing-file
            locale default (>^ω^<) 正在安装 "{}"...
            locale zh_CN (>^ω^<) 正在安装 "{}"...
        end_entry
        entry install-success
            locale default o(≧v≦)o 已成功安装{}个文件！
            locale zh_CN o(≧v≦)o 已成功安装{}个文件！
        end_entry
end_main
```

编写好主题文件后，使用 `clitheme apply-theme <file>`来应用主题。应用程序会直接采用主题中适配的字符串。

## 安装（待办）

安装`clitheme`非常简单，您可以通过Arch Linux软件包或者pip软件包安装。

### 通过Arch Linux软件包安装

todo

### 通过pip软件包安装

从最新发行版页面下载whl文件，使用`pip`直接安装即可：
    
    $ pip install clitheme-release-latest.whl

## 更多信息

具体的详细信息和文档请看本项目Wiki页面