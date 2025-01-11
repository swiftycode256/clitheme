# clitheme - Command line customization utility

[中文](../README.md) | **English**

**Disclaimer:** Please do not use this tool to create harmful or illegal content. The author of this software does not claim any responsibility for content and definition files created by others.

---

`clitheme` allows you to customize the output of command line applications, giving them the style and personality you want.

Example:
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
test.c:1:1: Error! : unknown type name 'bool', you forgot to d……define it!~ಥ_ಥ
bool *func(int *a) {
^
test.c:4:3: note: incompatible pointer types 'char *' and 'int *', they're so……so incompatible!~ [-Wincompatible-pointer-types]
        b=a;
         ^~
2 errors generated.
```

## Features

`clitheme` has these main features:

- Customize and modify the output of any command line application through defining substitution rules
- Customize Unix/Linux manual pages (man pages)
- A frontend API for applications similar to localization toolkits (like GNU gettext), which can help users better customize output messages

Other characteristics:

- Multi-language/internalization support
    - This means that you can also use `clitheme` to add internalization support for command line applications
- Easy-to-understand **theme definition file** syntax
- The string entries in the current theme setting can be accessed without using the frontend API (easy-to-understand data structure)

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
# Define basic information for this theme in header_section; required
{header_section}
    # `name` is a required entry in header_section
    name clang example theme
    [description]
        An example theme for clang (for demonstration purposes)
    [/description]
{/header_section}

{substrules_section}
    # Set "substesc" option: "{{ESC}}" in content will be replaced with the ASCII Escape terminal control character
    set_options substesc
    # Command filter: following substitution rules will be applied only if these commands are invoked. It is recommended as it can prevent unwanted output substitutions.
    [filter_commands]
        clang
        clang++
        gcc
        g++
    [/filter_commands]
    [subst_regex] (?P<prefix>^({{ESC}}.*?m)*(.+:\d+:\d+:) ({{ESC}}.*?m)*)warning: (?P<esc>({{ESC}}.*?m)*)incompatible pointer types assigning to '(?P<name1>.+)' from '(?P<name2>.+)'
        # Use "locale:en_US" if you only want the substitution rule to applied when the system locale setting is English (en_US)
        # Use "locale:default" to not apply any locale filters
        locale:default \g<prefix>note: \g<esc>incompatible pointer types '\g<name1>' and '\g<name2>', they're so……so incompatible!~
    [/subst_regex]
    [subst_regex] (?P<prefix>^({{ESC}}.*?m)*(.+:\d+:\d+:) ({{ESC}}.*?m)*)error: (?P<esc>({{ESC}}.*?m)*)unknown type name '(?P<type>.+)'
        locale:default \g<prefix>Error! : \g<esc>unknown type name '\g<type>', you forgot to d……define it!~ಥ_ಥ
    [/subst_regex]
{/substrules_section}
```

After applying the theme with `clitheme apply-theme <file>`, execute the command with `clitheme-exec` to apply the substitution rules onto the output: 

```plaintext
$ clitheme apply-theme clang-theme.clithemedef.txt
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
{header_section}
    name Example manual page theme
    description An example man page theme
{/header_section}

{manpage_section}
    # Add the file path *separated by spaces* after "include_file" (with the directory the theme definition file is placed as the parent directory)
    # Add the target file path (e.g. where the file is placed under `/usr/share/man`) *separated by spaces* after "as"
    include_file man-pages 1 ls-custom.txt
        as man1 ls.1
    include_file man-pages 1 cat-custom.txt
        as man1 cat.1
{/manpage_section}
```

After applying the theme with `clitheme apply-theme <file>`, use `clitheme-man` to view these custom man pages (arguments and options are the same as `man`):

```plaintext
$ clitheme apply-theme manpage-theme.clithemedef.txt
$ clitheme-man cat
$ clitheme-man ls
```

## Application frontend API and string entries

Please see [this article](./README-frontend.en.md)

# Installing and building

`clitheme` can be installed through pip package, Debian package, and Arch Linux package.

### Install using Python/pip package

First, ensure that Python 3 is installed on the system. `clitheme` requires Python 3.8 or higher.

- On Linux distributions, you can use relevant package manager to install 
- On macOS, you can install Python through Xcode command line developer tools (use `xcode-select --install` command), or through Python website ( https://www.python.org/downloads )
- On Windows, you can install Python through Microsoft Store ([Python 3.13 link](https://apps.microsoft.com/detail/9pnrbtzxmb4z)), or through Python website ( https://www.python.org/downloads )

Then, ensure that `pip` is installed within Python. The following command will perform an offline install of `pip` if it's not detected.

    $ python3 -m ensurepip

Download the `.whl` file from latest distribution page and install it using `pip`:
    
    $ python3 -m pip install ./clitheme-<version>-py3-none-any.whl

### Install using Arch Linux package

Because each build of the Arch Linux package only supports a specific Python version and upgrading Python will break the package, pre-built packages are not provided and you need to build the package. Please see **Building Arch Linux package** below.

### Install using Debian package

Download the `.deb` file from the latest distribution page and install using `apt`:

    $ sudo apt install ./clitheme_<version>_all.deb

## Building packages

You can build the package from the repository source code, which includes any latest or custom changes. You can also use this method to install the latest development version.

### Build pip package

`clitheme` uses the `setuptools` build system, so it needs to be installed beforehand.

First, install `setuptools`, `build`, and `wheel` packages. You can use the packages provided by your Linux distribution, or install using `pip`:

    $ python3 -m pip install --upgrade setuptools build wheel

Then, switch to project directory and use the following command to build the package:

    $ python3 -m build --wheel --no-isolation

The package file can be found in the `dist` folder after build finishes.

### Build Arch Linux package

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

# You can delete the temporary directories after it completes
rm -rf buildtmp srctmp
```

**Note:** The package must be re-built every time Python is upgraded, because the package only works with the version of Python installed during build

### Build Debian package

Install the following packages before building:

- `debhelper`
- `dh-python`
- `python3-setuptools`
- `dpkg-dev`
- `pybuild-plugin-pyproject`

You can use the following command to install:

    sudo apt install debhelper dh-python python3-setuptools dpkg-dev pybuild-plugin-pyproject

While in the repo directory, execute `dpkg-buildpackage -b` to build the package. A `.deb` file will be generated at the parent directory (`..`) after build completes.

# More information

- This repository is also synced onto GitHub (using Gitee automatic sync feature): https://github.com/swiftycode256/clitheme
- The latest developments, future plans, and in-development features of this project are detailed in the Issues section of the Gitee repository: https://gitee.com/swiftycode/clitheme/issues
- Feel free to propose suggestions and changes using Issues and Pull Requests
    - Use the Wiki repositories listed above for Wiki-related suggestions
