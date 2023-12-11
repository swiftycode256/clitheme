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

**注意：**`clitheme`当前仅支持拥有Python 3的Linux和macOS系统，暂不支持Windows系统。

# 基本用法

## 数据结构和路径名称

应用程序是主要通过**路径名称**来指定所需的字符串。这个路径由空格来区别子路径（`subsections`）。大部分时候路径的前两个名称是用来指定开发者和应用名称的。主题文件会通过该路径名称来适配对应的字符串，从而达到自定义输出的效果。

比如`com.example example-app example-text`指的是`com.example`开发的`example-app`中的`example-text`字符串。

当然，路径名称也可以是全局的（不和任何应用信息关联），如`global-entry`或`global-example global-text`。

### 直接访问主题数据结构

`clitheme`的核心设计理念之一包括无需使用前端API就可以访问主题数据，并且访问方法直观易懂。这一点在使用其他语言编写的程序中尤其重要，因为前端API目前只提供Python程序的支持。

`clitheme`的数据结构采用了**子文件夹**的结构，意味着路径中的每一段代表着数据结构中的一个文件夹/文件。

比如说，`com.example example-app example-text` 的字符串会被存储在`$datapath/com.example/example-app/example-text`。一般情况下，`$datapath`（数据根目录）是 `~/.local/share/clitheme/theme-data`。

如果需要访问该字符串的其他语言，直接在路径的最后添加`__`加上locale名称就可以了。比如：`$datapath/com.example/example-app/example-text__zh_CN`

所以说，如果需要直接访问字符串信息，只需要访问对应的文件路径就可以了。

## 前端实施和编写主题文件

### 使用内置前端API

使用`clitheme`的python前端API非常简单。只需要新建一个`frontend.FetchDescriptor`实例然后调用该实例中的`retrieve_entry_or_fallback`即可。

该函数需要提供路径名称和默认字符串。如果当前主题设定没有适配该字符串，则函数会返回提供的默认字符串。

如果新建`FetchDescriptor`时提供了`domain_name`，`app-name`，或`subsections`，则调用函数时会自动把它添加到路径名称前。

我们拿上面的样例来示范：

```py
from clitheme import frontend

# 新建FetchDescriptor实例
f=frontend.FetchDescriptor(domain_name="com.example", app_name="example-app")

# 对应 “在当前目录找到了2个文件”
fcount=[...]
f.retrieve_entry_or_fallback("found-file", "在当前目录找到了{}个文件".format(str(fcount)))

# 对应 “-> 正在安装 "example-file"...”
filename=[...]
f.retrieve_entry_or_fallback("installing-file", "-> 正在安装\"{}\"...".format(filename))

# 对应 “已成功安装2个文件”
f.retrieve_entry_or_fallback("install-success", "已成功安装{}个文件".format(str(fcount)))

# 对应 “错误：找不到文件 "foo-nonexist"”
filename_err=[...]
f.retrieve_entry_or_fallback("file-not-found", "错误：找不到文件 \"{}\"".format(filename_err))
```

### 使用前端fallback模块

应用程序还可以在src中内置本项目提供的fallback模块，以便更好的处理`clitheme`模块不存在时的情况。该fallback模块包括了前端API中的所有定义和功能，并且会永远返回失败时的默认值（fallback）。

如需使用，请在你的项目文件中导入`clitheme_fallback.py`文件，并且在你的程序中包括以下代码：

```py
try:
    from clitheme import frontend
except (ModuleNotFoundError, ImportError):
    import clitheme_fallback as frontend
```

本项目提供的fallback文件会随版本更新而更改，所以请定期往你的项目里导入最新的fallback文件以获得最新的功能。

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

应用程序还可以在对应的官方文档中包括此信息。

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
        entry file-not-found
            locale default ಥ_ಥ 糟糕，出错啦！找不到文件 "{}"
            locale zh_CN ಥ_ಥ 糟糕，出错啦！找不到文件 "{}"
        end_entry
end_main
```

编写好主题文件后，使用 `clitheme apply-theme <file>`来应用主题。应用程序会直接采用主题中适配的字符串。

# 安装

安装`clitheme`非常简单，您可以通过Arch Linux软件包或者pip软件包安装。

### 通过pip软件包安装

从最新发行版页面下载whl文件，使用`pip`直接安装即可：
    
    $ pip install clitheme-<version>-py3-none-any.whl

### 通过Arch Linux软件包安装

因为Arch Linux上无法使用`pip`往系统里直接安装pip软件包，所以本项目提供Arch Linux软件包。

如需安装，从最新发行版页面下载`.pkg.tar.zst`文件，使用`pacman`安装即可：

    $ sudo pacman -U clitheme-<version>.pkg.tar.zst

## 构建安装包

你也可以从仓库源代码构建安装包，以包括最新或自定义更改。如果需要安装最新的开发版本，则需要通过此方法安装。

### 构建pip软件包

`clitheme`使用的是`hatchling`构建器，所以构建软件包前需要安装它。

首先，安装`hatch`软件包。你可以通过你使用的Linux发行版提供的软件包，或者使用以下命令通过`pip`安装：

    $ pip install hatch

然后，切换到项目目录，使用`hatch build`构建软件包：

    $ hatch build

构建完成后，相应的安装包文件可以在当前目录中的`dist`文件夹中找到。

### 构建Arch Linux软件包

构建Arch Linux软件包前，请确保`base-devel`软件包已安装。如需安装，请使用以下命令：

    $ sudo pacman -S base-devel

构建软件包的方法如下：

- 在仓库目录下创建一个临时文件夹（如`build`）并切换当前路径
- 给当前仓库创建一个名为`repo-src.tar.gz`的归档，存储在临时目录（必须在临时目录或仓库目录内完成）
- 把`PKGBUILD`文件拷贝到临时文件夹里
- 使用`makepkg`构建软件包

你可以通过以下一系列命令来完成这些操作。确保当前目录为仓库目录，并且执行以下命令：
```sh
mkdir build; cd build
tar cf repo-src.tar.gz ..
cp ../PKGBUILD .
makepkg -sci
# -s：自动安装构建时需要的软件包
# -c：构建完后删除临时生成的数据和文件夹
# -i：构建完后自动安装生成的软件包

# 完成后，你可以删除临时文件夹
cd ..; rm -rf build
```

## 更多信息

更多的详细信息和文档请参考本项目Wiki页面。