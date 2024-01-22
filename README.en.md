# clitheme - A CLI application framework for output customization

[中文](README.md) | **English**

`clitheme` allows you to customize the output of command line applications, giving them the style and personality you want.

Example:
```
$ example-app install-files
Found 2 files in current directory
-> Installing "example-file"...
-> Installing "example-file-2"...
Successfully installed 2 files
$ example-app install-file foo-nonexist
Error: File "foo-nonexist" not found
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
o(≧v≦)o Great! Found 2 files in current directory!
(>^ω^<) Installing "example-file"...
(>^ω^<) Installing "example-file-2:"...
o(≧v≦)o Successfully installed 2 files!
$ example-app install-file foo-nonexist
ಥ_ಥ Oh no, something went wrong! File "foo-nonexist" not found
```

## Features

- Multi-language (Internationalization) support
- Supports applying multiple themes simultaneously
- Clear and easy-to-understand theme definition file (`clithemedef`) syntax
- The theme data can be easily accessed without the use of frontend module

Not only `clitheme` can customize the output of command-line applications, it can also:
- Add support for another language for an application
- Support GUI applications

# Basic usage

## Data hierarchy and path naming

Applications use **path names** to specify the string definitions they want. Subsections in the path name is separated using spaces. The first two subsections are usually reserved for the developer and application name. Theme definition files will use this path name to adopt corresponding string definitions, achieving the effect of output customization.

For example, the path name `com.example example-app example-text` refers to the `example-text` string definition for the `example-app` application developed by `com.example`.

It is not required to always follow this path naming convention and specifying global definitions (not related to any specific application) is allowed. For example, `global-entry` and `global-example global-text` are also valid path names.

### Directly accessing the theme data hierarchy

One of the key design principles of `clitheme` is that the use of frontend module is not needed to access the theme data hierarchy, and its method is easy to understand and implement. This is important especially in applications written in languages other than Python because Python is the only language supported by the frontend module.

The data hierarchy is organized in a **subfolder structure**, meaning that every subsection in the path name represent a file or folder in the data hierarchy.

For example, the contents of string definition `com.example example-app example-text` is stored in the directory `<datapath>/com.example/example-app`. `<datapath>` is `$XDG_DATA_HOME/clitheme/theme-data` or `~/.local/share/clitheme/theme-data` under Linux and macOS systems.

Under Windows systems, `<datapath>` is `%USERPROFILE%\.local\share\clitheme\theme-data` or `C:\Users\<username>\.local\share\clitheme\theme-data`.

To access a specific language of a string definition, add `__` plus the locale name to the end of the directory path. For example: `<datapath>/com.example/example-app/example-text__en_US`

In conclusion, to directly access a specific string definition, convert the path name to a directory path and access the file located there.

## Frontend implementation and writing theme definition files

### Using the built-in frontend module

Using the frontend module provided by `clitheme` is very easy and straightforward. To access a string definition in the current theme setting, create a new `frontend.FetchDescriptor` object and use the provided `retrieve_entry_or_fallback` function.

You need to pass the path name and a fallback string to this function. If the current theme setting does not provide the specified path name and string definition, the function will return the fallback string.

You can pass the `domain_name`, `app_name`, and `subsections` arguments when creating a new `frontend.FetchDescriptor` object. When specified, these arguments will be automatically appended in front of the path name provided when calling the `retrieve_entry_or_fallback` function.

Let's demonstrate it using the previous examples:

```py
from clitheme import frontend

# Create a new FetchDescriptor object
f=frontend.FetchDescriptor(domain_name="com.example", app_name="example-app")

# Corresponds to "Found 2 files in current directory"
fcount="[...]"
f.retrieve_entry_or_fallback("found-file", "在当前目录找到了{}个文件".format(str(fcount)))

# Corresponds to "-> Installing "example-file"..."
filename="[...]"
f.retrieve_entry_or_fallback("installing-file", "-> 正在安装\"{}\"...".format(filename))

# Corresponds to "Successfully installed 2 files"
f.retrieve_entry_or_fallback("install-success", "已成功安装{}个文件".format(str(fcount)))

# Corresponds to "Error: File "foo-nonexist" not found"
filename_err="[...]"
f.retrieve_entry_or_fallback("file-not-found", "错误：找不到文件 \"{}\"".format(filename_err))
```

### Using the fallback frontend module

You can integrate the fallback frontend module provided by this project to better handle situations when `clitheme` does not exist on the system. This fallback module contains all the functions in the frontend module, and its functions will always return fallback values.

Import the `clitheme_fallback.py` file from the repository and insert the following code in your project to use it:

```py
try:
    from clitheme import frontend
except (ModuleNotFoundError, ImportError):
    import clitheme_fallback as frontend
```

The fallback module provided by this project will update accordingly with new versions. Therefore, it is recommended to import the latest version of this module to adopt the latest features.

### Information your application should provide

To allow users to write theme definition files of your application, your application should provide information about supported string definitions with its path name and default string.

For example, your app can implement a feature to output all supported string definitions:

```
$ example-app --clitheme-output-defs
com.example example-app found-file
Found {} files in current directory

com.example example-app installing-file
-> Installing "{}"...

com.example example-app install-success
Successfully installed {} files

com.example example-app file-not-found
Error: file "{}" not found
```

You can also include this information in your project's official documentation. The demo application in this repository provides an example of it and the corresponding README file is located in the folder `example-clithemedef`.

### Writing theme definition files

Consult the Wiki pages and documentation for detailed syntax of theme definition files. An example is provided below:

```
begin_header
    name Example theme
    version 1.0
    locales en_US
    supported_apps clitheme_demo
end_header

begin_main
    in_domainapp com.example example-app
        entry found-file
            locale default o(≧v≦)o Great! Found {} files in current directory!
            locale en_US o(≧v≦)o Great! Found {} files in current directory!
        end_entry
        entry installing-file
            locale default (>^ω^<) Installing "{}"...
            locale en_US (>^ω^<) Installing "{}"...
        end_entry
        entry install-success
            locale default o(≧v≦)o Successfully installed {} files!
            locale en_US o(≧v≦)o Successfully installed {} files!
        end_entry
        entry file-not-found
            locale default ಥ_ಥ Oh no, something went wrong! File "foo-nonexist" not found
            locale en_US ಥ_ಥ Oh no, something went wrong! File "foo-nonexist" not found
        end_entry
end_main
```

Use the command `clitheme apply-theme <file>` to apply the theme definition file onto the system. Supported applications will start using the string definitions listed in this file.

# Installation

Installing `clitheme` is very easy. You can use the provided Arch Linux, Debian, or pip package to install it.

### Install using pip

Download the whl file from the latest release and install it using `pip`:

    $ pip install clitheme-<version>-py3-none-any.whl

### Install using Arch Linux package

Because `pip` cannot be used to install Python packages onto an Arch Linux system, this project provides an Arch Linux package.

Because the built package only supports a specific Python version and will stop working when Python is upgraded, this project only provides files needed to build the package. Please see **Build Arch Linux package** for more information.

### Install using Debian package

Because `pip` cannot be used to install Python packages onto certain Debian Linux distributions, this project provides a Debian package.

Download the `.deb` file from the latest release and install it using `apt`:

    $ sudo apt install ./clitheme_<version>_all.deb

## Building the installation package

You can also build the installation package from source code, which allows you to include the latest or custom changes. This is the only method to install the latest development version of `clitheme`.

### Build pip package

`clitheme` uses the `hatchling` build backend, so installing it is required for building the package.

First, install the `hatch` package. You can use the software package provided by your Linux distribution, or install it using `pip`:

    $ pip install hatch

Next, making sure that you are under the project directory, use `hatch build` to build the package:

    $ hatch build

If this command does not work, try using `hatchling build` instead.

The corresponding pip package (whl file) can be found in the `dist` folder under the working directory.

### Build Arch Linux package

Make sure that the `base-devel` package is installed before building the package. You can install it using the following command:

    $ sudo pacman -S base-devel

To build the package, run `makepkg` under the project directory. You can use the following commands:

```sh
# Delete the temporary directories if makepkg has been run before. Issues will occur if you do not do so.
rm -rf buildtmp srctmp

makepkg -si
# -s: install dependencies required for building the package
# -i: automatically install the built package

# You can remove the temporary directories after you are finished
rm -rf buildtmp srctmp
```

**Warning:** You must rebuild the package every time Python is upgraded, because the package only works under the Python version when the package is built.

### Build Debian package

Because `pip` cannot be used to install Python packages onto certain Debian Linux distributions, this project provides a Debian package.

The following packages are required prior to building the package:

- `debhelper`
- `dh-python`
- `python3-hatchling`
- `dpkg-dev`

They can be installed using this command:

    sudo apt install debhelper dh-python python3-hatchling dpkg-dev

Run `dpkg-buildpackage -b` to build the package. A `.deb` file will be generated in the upper folder after the build process finishes.

## More information

- For more information, please reference the project's Wiki pages: https://gitee.com/swiftycode/clitheme/wikis/pages
    - You can also access the pages in these repositories:
    - https://gitee.com/swiftycode/clitheme-wiki-repo
    - https://github.com/swiftycode256/clitheme-wiki-repo
- This repository is also synced onto GitHub (using Gitee automatic sync feature): https://github.com/swiftycode256/clitheme
- You are welcome to propose suggestions and changes using Issues and Pull Requests
    - Use the Wiki repositories listed above for Wiki-related suggestions