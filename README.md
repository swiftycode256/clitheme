# `CLI`theme - Command line customization utility

[中文](./README.zh.md) | **English**

**Disclaimer:** This software only provides the technical utility for modifying content output. Do not use this tool to create harmful or illegal content; the author is not responsible for content and definition files created by others, including modifications of content created by this author.

---

CLItheme allows you to customize the output of command line applications, giving them the style and personality you want.

Example:
```plaintext
$ clang test.c
test.c:1:1: error: unknown type name 'bool'
bool *func(int *a) {
^
test.c:4:3: warning: incompatible pointer types assigning to 'char *' from 'int *' [-Wincompatible-pointer-types]
        b=a;
         ^~
2 errors generated.
```
```plaintext
$ clitheme apply-theme clang-theme.ctdef.txt
==> Successfully processed files
Theme applied successfully
```
```plaintext
$ clitheme-exec clang test.c
test.c:1:1: Error! : unknown type name 'bool', you forgot to d……define it!~ಥ_ಥ
bool *func(int *a) {
^
test.c:4:3: note: incompatible pointer types 'char *' and 'int *', they're so……so incompatible!~ [-Wincompatible-pointer-types]
        b=a;
         ^~
2 errors generated.
```

## Features

CLItheme has these main features:

- Customize and modify the output of any command line application through defining substitution rules
- Customize Unix/Linux manual pages (man pages)
- A frontend API for applications similar to localization toolkits (like GNU gettext), which can help users better customize output messages

Other characteristics:

- Multi-language/i18n support
    - This means that you can also use CLItheme to add i18n (internationalization) support for command line applications
- Easy-to-understand **theme definition file** syntax
- The string entries in the current theme setting can be accessed without using the frontend API (easy-to-understand data structure)

## Documentation

For more information, please see the project's Wiki documentation page. It can be accessed through the following links:

- https://gitee.com/swiftycode/clitheme/wikis
- https://gitee.com/swiftycode/clitheme-wiki-repo
- https://github.com/swiftycode256/clitheme-wiki-repo

# Feature examples and demos

## Command line output substitution

Get the command line output, including any terminal control characters:

```plaintext
# --debug: Add a marker at the beginning of each line; contains information on whether the output is stdout/stderr ("o>" or "e>")
# --showchars: Show terminal control characters in the output
# --nosubst: Even if a theme is set, do not apply substitution rules (get original output content)

$ clitheme-exec --debug --showchars --nosubst clang test.c
e> {{ESC}}[1mtest.c:1:1: {{ESC}}[0m{{ESC}}[0;1;31merror: {{ESC}}[0m{{ESC}}[1munknown type name 'bool'{{ESC}}[0m\r\n
e> bool *func(int *a) {\r\n
e> {{ESC}}[0;1;32m^\r\n
e> {{ESC}}[0m{{ESC}}[1mtest.c:4:3: {{ESC}}[0m{{ESC}}[0;1;35mwarning: {{ESC}}[0m{{ESC}}[1mincompatible pointer types assigning to 'char *' from 'int *' [-Wincompatible-pointer-types]{{ESC}}[0m\r\n
e>         b=a;\r\n
e> {{ESC}}[0;1;32m         ^~\r\n
e> {{ESC}}[0m2 errors generated.\r\n
```

Write theme definition file and substitution rules based on the output:

```plaintext
{header}
    name: clang example theme
    [description]
        An example theme for clang (for demonstration purposes)
    [/description]
{/header}

{substrules}
    # Set "substesc" option: "{{ESC}}" in content will be replaced with the ASCII Escape terminal control character
    (set_options) substesc substvar
    [filter_cmds]
        clang
        clang++
        gcc
        g++
    [/filter_cmds]
        setvar[prefix_group]: (?P<prefix>^({{ESC}}.*?m)*(.+:\d+:\d+:) ({{ESC}}.*?m)*)
        [subst_regex] {{prefix_group}}warning: (?P<esc>({{ESC}}.*?m)*)incompatible pointer types assigning to '(?P<name1>.+)' from '(?P<name2>.+)'
            # Use "locale[en_US]" if you only want the substitution rule to applied when the system locale setting is English (en_US)
            # Use "locale[default]" to not apply any locale filters
            default: \g<prefix>note: \g<esc>incompatible pointer types '\g<name1>' and '\g<name2>', they're so……so incompatible!~
        [/subst_regex]
        [subst_regex] {{prefix_group}}error: (?P<esc>({{ESC}}.*?m)*)unknown type name '(?P<type>.+)'
            default: \g<prefix>Error! : \g<esc>unknown type name '\g<type>', you forgot to d……define it!~ಥ_ಥ
        [/subst_regex]
{/substrules}
```

After applying the theme with `clitheme apply-theme <file>`, execute the command with `clitheme-exec` to apply the substitution rules onto the output: 

```plaintext
$ clitheme apply-theme clang-theme.ctdef.txt
$ clitheme-exec clang test.c
test.c:1:1: Error! : unknown type name 'bool', you forgot to d……define it!~ಥ_ಥ
bool *func(int *a) {
^
test.c:4:3: note: incompatible pointer types 'char *' and 'int *', they're so……so incompatible!~ [-Wincompatible-pointer-types]
        b=a;
         ^~
2 errors generated.
```

## Custom man pages

Write/edit the source code of the man page and save it into a location:

```plaintext
$ nano man-pages/1/ls-custom.txt
# <edit file>
$ nano man-pages/1/cat-custom.txt
# <edit file>
```

Write a theme definition file:

```plaintext
{header}
    name: Example manual page theme
    description: An example man page theme
{/header}

{manpages}
    # '/' in file paths are denoted with spaces
    <include_file> man-pages 1 ls-custom.txt
        as: man1 ls.1
    <include_file> man-pages 1 cat-custom.txt
        as: man1 cat.1
{/manpages}
```

After applying the theme with `clitheme apply-theme <file>`, use `clitheme-man` to view these custom man pages (arguments and options are the same as `man`):

```plaintext
$ clitheme apply-theme manpage-theme.ctdef.txt
$ clitheme-man cat
$ clitheme-man ls
```

## Application frontend API and string entries

Please see files in the `frontend-demo` folder, which contains a sample definition file and app that demonstrates usage of the `frontend` module.

For more information, please see [this article](./README-frontend.md).

# Download and install

CLItheme can be installed through pip package, Debian package, and Arch Linux package.

## Install using Python/pip package

First, ensure that Python 3 is installed on the system. CLItheme requires Python 3.8 or higher.

- On Linux distributions, you can use relevant package manager to install 
- On macOS, you can install Python through Xcode command line developer tools (use `xcode-select --install` command), or through Python website ( https://www.python.org/downloads )
- On Windows, you can install Python through the [Python Install Manager](https://apps.microsoft.com/detail/9nq7512cxl7t), or through the installers that can be downloaded from Python website ( https://www.python.org/downloads )

Then, ensure that `pip` is installed within Python. The following command will perform an offline install of `pip` if it's not detected.

    $ python3 -m ensurepip

Download the `.whl` file from the [latest release](../../releases/latest) and install it using `pip`:
    
    $ python3 -m pip install ./clitheme-<version>-py3-none-any.whl

> [!IMPORTANT]
> Official release files are only distributed through the [repository releases page](../../releases). Packages distributed through other channels (e.g. PyPI/pip, Conda, Homebrew, AUR, etc.) are not managed by this author and should be used at your own risk!

## Install using Arch Linux package

Because each build of the Arch Linux package only supports a specific Python version and upgrading Python will break the package, pre-built packages are not provided and you need to build the package. Please see **Building Arch Linux package** below.

## Install using Debian package

Download the `.deb` file from the latest distribution page and install using `apt`:

    $ sudo apt install ./clitheme_<version>_all.deb

# Building packages

You can build the package from the repository source code, which includes any latest or custom changes. You can also use this method to install the latest development version.

## Build pip package

CLItheme uses the `setuptools` build system, so it needs to be installed beforehand.

First, install `setuptools`, `build`, and `wheel` packages. You can use the packages provided by your Linux distribution, or install using `pip`:

    $ python3 -m pip install --upgrade setuptools build wheel

Then, switch to project directory and use the following command to build the package:

    $ python3 -m build --wheel --no-isolation

The package file can be found in the `dist` folder after build finishes.

## Build Arch Linux package

Ensure that the `base-devel` package is installed before building. Use the following command to install:

    $ sudo pacman -S base-devel

Before build the package, make sure that any changes in the repository are committed (git commit):

    $ git add .
    $ git commit

Execute `makepkg` to build the package. Use the following commands to perform these operations:

```sh
# If makepkg is executed before, delete the temporary directories to prevent issues
rm -rf buildtmp srctmp

makepkg -si
# -s: Automatically install required build dependencies (e.g. python-setuptools, python-build)
# -i：Automatically install the built package
```

**Note:** The package must be re-built every time Python is upgraded, because the package only works with the version of Python installed during build

## Build Debian package

Install the following packages before building:

- `debhelper`
- `dh-python`
- `python3-setuptools`
- `dpkg-dev`
- `pybuild-plugin-pyproject`

You can use the following command to install:

    $ sudo apt install debhelper dh-python python3-setuptools dpkg-dev pybuild-plugin-pyproject

In the repo directory, use the following command to build the package. A `.deb` file will be generated in its parent directory after build completes.

    $ dpkg-buildpackage -b --no-sign