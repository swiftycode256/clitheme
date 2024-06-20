# 应用程序API和字符串定义示范

## 数据结构和路径名称

应用程序是主要通过**路径名称**来指定所需的字符串。这个路径由空格来区别子路径（`subsections`）。大部分时候路径的前两个名称是用来指定开发者和应用名称的。主题文件会通过该路径名称来适配对应的字符串，从而达到自定义输出的效果。

比如`com.example example-app example-text`指的是`com.example`开发的`example-app`中的`example-text`字符串。

当然，路径名称也可以是全局的（不和任何应用信息关联），如`global-entry`或`global-example global-text`。

### 直接访问主题数据结构

`clitheme`的核心设计理念之一包括无需使用frontend模块就可以访问主题数据，并且访问方法直观易懂。这一点在使用其他语言编写的程序中尤其重要，因为frontend模块目前只提供Python程序的支持。

`clitheme`的数据结构采用了**子文件夹**的结构，意味着路径中的每一段代表着数据结构中的一个文件夹/文件。

比如说，`com.example example-app example-text` 的字符串会被存储在`<datapath>/com.example/example-app/example-text`。在Linux和macOS系统下，`<datapath>`是 `$XDG_DATA_HOME/clitheme/theme-data`或`~/.local/share/clitheme/theme-data`。

在Windows系统下，`<datapath>`是`%USERPROFILE%\.local\share\clitheme\theme-data`。（`C:\Users\<用户名称>\.local\share\clitheme\theme-data`）

如果需要访问该字符串的其他语言，直接在路径的最后添加`__`加上locale名称就可以了。比如：`<datapath>/com.example/example-app/example-text__zh_CN`

所以说，如果需要直接访问字符串信息，只需要访问对应的文件路径就可以了。

## 前端实施和编写主题文件

### 使用内置frontend模块

使用`clitheme`的frontend模块非常简单。只需要新建一个`frontend.FetchDescriptor`实例然后调用该实例中的`retrieve_entry_or_fallback`即可。

该函数需要提供路径名称和默认字符串。如果当前主题设定没有适配该字符串，则函数会返回提供的默认字符串。

如果新建`FetchDescriptor`时提供了`domain_name`，`app-name`，或`subsections`，则调用函数时会自动把它添加到路径名称前。

我们拿上面的样例来示范：

```py
from clitheme import frontend

# 新建FetchDescriptor实例
f=frontend.FetchDescriptor(domain_name="com.example", app_name="example-app")

# 对应 “在当前目录找到了2个文件”
fcount="[...]"
f.retrieve_entry_or_fallback("found-file", "在当前目录找到了{}个文件".format(str(fcount)))

# 对应 “-> 正在安装 "example-file"...”
filename="[...]"
f.retrieve_entry_or_fallback("installing-file", "-> 正在安装\"{}\"...".format(filename))

# 对应 “已成功安装2个文件”
f.retrieve_entry_or_fallback("install-success", "已成功安装{}个文件".format(str(fcount)))

# 对应 “错误：找不到文件 "foo-nonexist"”
filename_err="[...]"
f.retrieve_entry_or_fallback("file-not-found", "错误：找不到文件 \"{}\"".format(filename_err))
```

### 使用fallback模块

应用程序还可以在src中内置本项目提供的fallback模块，以便更好的处理`clitheme`模块不存在时的情况。该fallback模块包括了frontend模块中的所有定义和功能，并且会永远返回失败时的默认值（fallback）。

如需使用，请在你的项目文件中导入`frontend_fallback.py`文件，并且在你的程序中包括以下代码：

```py
try:
    from clitheme import frontend
except (ModuleNotFoundError, ImportError):
    import frontend_fallback as frontend
```

本项目提供的fallback文件会随版本更新而更改，所以请定期往你的项目里导入最新的fallback文件以适配最新的功能。

### 应用程序应该提供的信息

为了让用户更容易编写主题文件，应用程序应该加入输出字符串定义的功能。该输出信息应该包含路径名称和默认字符串。

比如说，应用程序可以通过`--clitheme-output-defs`来输出所有的字符串定义：

```
$ example-app --clitheme-output-defs
com.example example-app found-file
在当前目录找到了{}个文件

com.example example-app installing-file
-> 正在安装"{}"...

com.example example-app install-success
已成功安装{}个文件

com.example example-app file-not-found
错误：找不到文件 "{}"
```

应用程序还可以在对应的官方文档中包括此信息。如需样例，请参考本仓库中`example-clithemedef`文件夹的[README文件](example-clithemedef/README.zh-CN.md)。

### 编写主题文件

关于主题文件的详细语法请见Wiki文档，下面将展示一个样例：

```
{header_section}
    name 样例主题
    version 1.0
    locales zh_CN
    supported_apps frontend_demo
{/header_section}

{entries_section}
    in_domainapp com.example example-app
        [entry] found-file
            locale:default o(≧v≦)o 太好了，在当前目录找到了{}个文件！
            locale:zh_CN o(≧v≦)o 太好了，在当前目录找到了{}个文件！
        [/entry]
        [entry] installing-file
            locale:default (>^ω^<) 正在安装 "{}"...
            locale:zh_CN (>^ω^<) 正在安装 "{}"...
        [/entry]
        [entry] install-success
            locale:default o(≧v≦)o 已成功安装{}个文件！
            locale:zh_CN o(≧v≦)o 已成功安装{}个文件！
        [/entry]
        [entry] file-not-found
            locale:default ಥ_ಥ 糟糕，出错啦！找不到文件 "{}"
            locale:zh_CN ಥ_ಥ 糟糕，出错啦！找不到文件 "{}"
        [/entry]
end_main
```

编写好主题文件后，使用 `clitheme apply-theme <file>`来应用主题。应用程序会直接采用主题中适配的字符串。
