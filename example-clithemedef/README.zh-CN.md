# 字符串定义说明

本仓库中的`clitheme_example.py`支持以下字符串定义。默认字符串文本会以blockquote样式显示在路径名称下方。部分定义会包含额外的说明。

---

以下字符串会在`install-files`和`install-file`指令输出中用到：

`com.example example-app found-file`

> 在当前目录找到了{}个文件

`com.example example-app installing-file`

> -> 正在安装 "{}"...

`com.example example-app install-success`

> 已成功安装{}个文件

该文本会被`install-files`指令输出调用。

`com.example example-app install-success-file`

> 已成功安装"{}"

该文本会被`install-file`指令输出调用。

`com.example example-app file-not-found`

> 错误：找不到文件"{}"

`com.example example-app format-error`

> 错误：命令语法不正确

`com.example example-app directory-empty`

> 错误：当前目录里没有任何文件

该文本只会被`install-files`指令输出调用。

---

以下字符串会在帮助信息中用到：

`com.example example-app helpmessage description-general`

> 文件安装程序样例（不会修改系统中的文件）

该文本提供应用程序的名称，会在第一行显示。

`com.example example-app helpmessage description-usageprompt`

> 使用方法：

你可以通过此字符串定义”使用方法“的输出样式，会在命令列表前一行显示。

`com.example example-app helpmessage unknown-command`

> 错误：未知命令"{}"