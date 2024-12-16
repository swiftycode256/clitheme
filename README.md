# clitheme - 命令行自定义工具

**中文** | [English](.github/README.md)

---

`clitheme`允许你对命令行输出进行个性化定制，给它们一个你想要的风格和个性。

样例：
```plaintext
$ clang test.c
test.c:1:1: error: unknown type name 'bool'
bool *func(int *a) {
^
test.c:4:3: warning: incompatible pointer types assigning to 'char *' from 'int *' [-Wincompatible-pointer-types]
        b=a;
         ^~
2 errors generated
```
```plaintext
$ clitheme apply-theme clang-theme.clithemedef.txt
==> Processing files...
Successfully processed files
==> Applying theme...
Theme applied successfully
```
```plaintext
$ clitheme-exec clang test.c
test.c:1:1: 错误！: 未知的类型名'bool',忘记定义了～ಥ_ಥ
bool *func(int *a) {
^
test.c:4:3: 提示: 'char *'从不兼容的指针类型赋值为'int *',两者怎么都……都说不过去！^^; [-Wincompatible-pointer-types]
        b=a;
         ^~
2 errors generated.
```

## 功能

`clitheme`包含以下主要功能：

- 对任何命令行应用程序的输出通过定义替换规则进行修改和自定义
- 自定义Unix/Linux文档手册（manpage）
- 包含类似于本地化套件（如GNU gettext）的应用程序API，帮助用户更好的自定义提示信息的内容

其他特性：

- 多语言支持
    - 这意味着你也可以用`clitheme`来为应用程序添加多语言支持
- 简洁易懂的**主题定义文件**语法
- 无需应用程序API也可以访问当前主题中的字符串定义（易懂的数据结构）

更多信息请见本项目的Wiki文档页面。你可以通过以下位置访问这些文档：
- https://gitee.com/swiftycode/clitheme/wikis
- https://gitee.com/swiftycode/clitheme-wiki-repo
- https://github.com/swiftycode256/clitheme-wiki-repo

# 功能样例和示范

## 命令行输出自定义

获取包含终端控制符号的原始输出内容：

```plaintext
# --debug：在每一行的输出前添加标记；包含输出是否为stdout或stderr的信息（"o>"或"e>"）
# --showchars：显示输出中的终端控制符号
# --nosubst：即使设定了主题，不对输出应用替换规则（获取原始输出）

$ clitheme-exec --debug --showchars --nosubst clang test.c
e> {{ESC}}[1mtest.c:1:1: {{ESC}}[0m{{ESC}}[0;1;31merror: {{ESC}}[0m{{ESC}}[1munknown type name 'bool'{{ESC}}[0m\r\n
e> bool *func(int *a) {\r\n
e> {{ESC}}[0;1;32m^\r\n
e> {{ESC}}[0m{{ESC}}[1mtest.c:4:3: {{ESC}}[0m{{ESC}}[0;1;35mwarning: {{ESC}}[0m{{ESC}}[1mincompatible pointer types assigning to 'char *' from 'int *' [-Wincompatible-pointer-types]{{ESC}}[0m\r\n
e>         b=a;\r\n
e> {{ESC}}[0;1;32m         ^~\r\n
e> {{ESC}}[0m2 errors generated.\r\n
```

根据输出内容编写主题定义文件和替换规则：

```plaintext
# 在header_section中定义一些关于该主题定义的基本信息；必须包括
{header_section}
    # 在header_section中必须定义`name`条目
    name clang样例主题
    [description]
        一个为clang打造的的样例主题，为了演示作用
    [/description]
{/header_section}

{substrules_section}
    # 设定"substesc"选项：内容中的"{{ESC}}"字样会被替换成ASCII Escape终端控制符号
    set_options substesc
    # 命令限制条件：以下的替换规则仅会在以下命令被调用时被应用。建议设定这个条件，因为可以尽量防止不应该的输出替换。
    [filter_commands]
        clang
        clang++
        gcc
        g++
    [/filter_commands]
    [subst_regex] (?P<prefix>^({{ESC}}.*?m)*(.+:\d+:\d+:) ({{ESC}}.*?m)*)warning: (?P<esc>({{ESC}}.*?m)*)incompatible pointer types assigning to '(?P<name1>.+)' from '(?P<name2>.+)'
        # 如果你想仅在系统语言设定为中文（zh_CN）时应用这个替换规则，你可以使用"locale:zh_CN"
        # 使用"locale:default"时不会添加系统语言限制
        locale:default \g<prefix>提示: \g<esc>'\g<name1>'从不兼容的指针类型赋值为'\g<name2>',两者怎么都……都说不过去！^^;
    [/subst_regex]
    [subst_regex] (?P<prefix>^({{ESC}}.*?m)*(.+:\d+:\d+:) ({{ESC}}.*?m)*)error: (?P<esc>({{ESC}}.*?m)*)unknown type name '(?P<type>.+)'
        locale:default \g<prefix>错误！: \g<esc>未知的类型名'\g<type>',忘记定义了～ಥ_ಥ
    [/subst_regex]
{/substrules_section}
```

使用`clitheme apply-theme <文件>`应用主题后，使用`clitheme-exec`执行命令以对输出应用这些替换规则：

```plaintext
$ clitheme apply-theme clang-theme.clithemedef.txt
$ clitheme-exec clang test.c
test.c:1:1: 错误！: 未知的类型名'bool',忘记定义了～ಥ_ಥ
bool *func(int *a) {
^
test.c:4:3: 提示: 'char *'从不兼容的指针类型赋值为'int *',两者怎么都……都说不过去！^^; [-Wincompatible-pointer-types]
        b=a;
         ^~
2 errors generated.
```

## 自定义manpage文档

编写/编辑manpage文档的源代码，并且保存在一个位置中：

```plaintext
$ nano man-pages/1/ls-custom.txt
# <编辑文件>
$ nano man-pages/1/cat-custom.txt
# <编辑文件>
```

编写主题定义文件：

```plaintext
{header_section}
    name 样例文档手册主题
    description 一个manpage文档手册样例主题
{/header_section}

{manpage_section}
    # 在"include_file"后添加*由空格分开*的文件路径（以主题定义文件所在的路径为父路径）
    # 在"as"后添加*由空格分开*的目标文件路径（放在如`/usr/share/man`文件夹下的文件路径）
    include_file man-pages 1 ls-custom.txt
        as man1 ls.1
    include_file man-pages 1 cat-custom.txt
        as man1 cat.1
{/manpage_section}
```

使用`clitheme apply-theme <文件>`应用主题后，使用`clitheme-man`查看这些自定义文档（使用方法和选项和`man`一样）：

```plaintext
$ clitheme apply-theme manpage-theme.clithemedef.txt
$ clitheme-man cat
$ clitheme-man ls
```

## 应用程序API和字符串定义

请见[此文档](./README-frontend.md)

# 安装与构建

安装`clitheme`非常简单，您可以通过pip软件包，Arch Linux软件包，或者Debian软件包安装。

### 通过Python/pip软件包安装

首先，确保Python 3已安装在系统中。`clitheme`需要Python 3.8或更高版本。

- 在Linux发行版上，你可以通过对应的软件包管理器安装Python
- 在macOS上，你可以通过Xcode命令行开发者工具安装Python（使用`xcode-select --install`命令），或者通过Python官网（ https://www.python.org/downloads ）下载
- 在Windows上，你可以通过Microsoft Store安装Python（[Python 3.13链接](https://apps.microsoft.com/detail/9pnrbtzxmb4z)），或者通过Python官网（ https://www.python.org/downloads ）下载

然后，确保`pip`软件包管理器已安装在Python中。以下命令将会通过本地安装`pip`，如果检测到没有安装。

    $ python3 -m ensurepip

从最新发行版页面下载`.whl`文件，使用`pip`直接安装即可：
    
    $ python3 -m pip install ./clitheme-<version>-py3-none-any.whl

### 通过Arch Linux软件包安装

因为构建的Arch Linux软件包只兼容特定的Python版本，并且升级Python版本后会导致原软件包失效，本项目仅提供构建软件包的方式，不提供构建好的软件包。详细请见下方的**构建Arch Linux软件包**。

### 通过Debian软件包安装

如需在Debian系统上安装，请从最新发行版页面下载`.deb`文件，使用`apt`安装即可：

    $ sudo apt install ./clitheme_<version>_all.deb

## 构建安装包

你也可以从仓库源代码构建安装包，以包括最新或自定义更改。如果需要安装最新的开发版本，则需要通过此方法安装。

### 构建pip软件包

`clitheme`使用的是`setuptools`构建器，所以构建软件包前需要安装它。

首先，安装`setuptools`、`build`、和`wheel`软件包。你可以通过你使用的Linux发行版提供的软件包，或者使用以下命令通过`pip`安装：

    $ python3 -m pip install --upgrade setuptools build wheel

然后，切换到项目目录，使用以下命令构建软件包：

    $ python3 -m build --wheel --no-isolation

构建完成后，相应的安装包文件可以在当前目录中的`dist`文件夹中找到。

### 构建Arch Linux软件包

构建Arch Linux软件包前，请确保`base-devel`软件包已安装。如需安装，请使用以下命令：

    $ sudo pacman -S base-devel

构建软件包前，请先确保任何对仓库文件的更改以被提交（git commit）：

    $ git add .
    $ git commit

构建软件包只需要在仓库目录中执行`makepkg`指令就可以了。你可以通过以下一系列命令来完成这些操作：

```sh
# 如果之前执行过makepkg，请删除之前生成的临时文件夹，否则构建时会出现问题
rm -rf buildtmp srctmp

makepkg -si
# -s：自动安装构建时需要的软件包
# -i：构建完后自动安装生成的软件包

# 完成后，你可以删除临时文件夹
rm -rf buildtmp srctmp
```

**注意：** 每次升级Python时，你需要重新构建并安装软件包，因为软件包只兼容构建时使用的Python版本。

### 构建Debian软件包

构建Debian软件包前，你需要安装以下用于构建的系统组件：

- `debhelper`
- `dh-python`
- `python3-setuptools`
- `dpkg-dev`
- `pybuild-plugin-pyproject`

你可以使用以下命令安装：

    sudo apt install debhelper dh-python python3-setuptools dpkg-dev pybuild-plugin-pyproject

安装完后，请在仓库目录中执行`dpkg-buildpackage -b`以构建软件包。完成后，你会在上层目录中获得一个`.deb`的文件。

# 更多信息

- 本仓库中的代码也同步在GitHub上（使用Gitee仓库镜像功能自动同步）：https://github.com/swiftycode256/clitheme
- 该项目的最新进展、未来计划、和开发中的新功能会在这里Gitee仓库中的Issues里列出：https://gitee.com/swiftycode/clitheme/issues
- 欢迎通过Issues和Pull Requests提交建议和改进。
    - Wiki页面也可以；你可以在上方列出的仓库中提交Issues和Pull Requests