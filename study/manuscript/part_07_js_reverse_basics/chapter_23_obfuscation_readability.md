# 第 23 章：混淆、压缩与可读性恢复
## 本章在主流程中的位置

本章仍然围绕“找到入口”和“发送请求”展开。当前端代码被压缩或混淆后，接口入口和参数逻辑会变得难读，本章训练的是把代码恢复到可分析状态。

它承接第 21、22 章的 JS 分析需求，并为第 24 章 AST 分析做准备。这里的目标不是追求复杂技巧，而是让请求来源可解释。

## 背景介绍

当你在 DevTools 里打开线上 JavaScript 文件时，经常会看到一整行挤在一起的代码，变量名短得像 `a`、`b`、`c`，函数名也看不出含义。新手第一次看到这种文件，很容易以为它是“加密代码”。

这里要先区分三个概念：

- 压缩：去掉空格、换行、注释，缩短变量名，让文件更小。
- 混淆：故意降低可读性，让人更难理解逻辑。
- 加密：没有密钥时不能直接还原明文。

绝大多数前端 JS 文件不是加密，而是压缩或混淆。浏览器必须执行这些代码，所以它最终一定能看到可执行的 JavaScript。我们做可读性恢复，不是为了“破解”，而是为了在授权排障、自有系统分析和防御评估中看清逻辑。

本章会讲如何把难读的 JS 变得稍微可读：格式化、搜索关键词、利用 Source Map、识别常见混淆形态、写分析记录。最后会给一个自建混淆样例，演示如何逐步拆开。

## 本章目标

学完本章后，你应该能做到：

1. 区分压缩、混淆、加密。
2. 使用格式化工具恢复换行和缩进。
3. 利用关键词、字符串、接口路径定位关键函数。
4. 理解常见混淆形态：短变量、字符串数组、控制流平坦化、死代码。
5. 知道可读性恢复的边界和局限。
6. 为后续 AST 分析打基础。

## 适用场景

本章适合：

- 自有前端项目上线后排查问题。
- 授权 SDK 代码审计。
- 查找接口参数生成位置。
- 评估前端敏感逻辑暴露风险。
- 将压缩代码整理成可阅读的分析材料。

## 不适用场景

本章不用于：

- 未授权分析第三方防护代码。
- 绕过访问控制、验证码、风控。
- 还原商业软件核心逻辑并规避授权。
- 自动化批量破解混淆保护。

## 压缩、混淆、加密的区别

### 压缩

压缩前：

```javascript
function add(a, b) {
  return a + b;
}
console.log(add(1, 2));
```

压缩后：

```javascript
function add(n,o){return n+o}console.log(add(1,2));
```

压缩的主要目标是减小文件体积。格式化后通常比较容易读。

### 混淆

混淆后可能变成：

```javascript
var _0x12ab=["log"];function _0x33c1(_0xa,_0xb){return _0xa+_0xb}console[_0x12ab[0]](_0x33c1(1,2));
```

混淆不仅减少体积，还故意隐藏语义，比如把字符串放进数组，把变量名变成无意义名称。

### 加密

加密后的内容通常不能直接执行，必须先解密。例如：

```text
U2FsdGVkX1+...
```

如果浏览器能直接执行一个 JS 文件，它就不是传统意义上完全不可读的加密文件。即使有自解密逻辑，运行时也会出现明文代码或可执行逻辑。

## 可读性恢复的基本流程

### 第一步：格式化

DevTools Sources 面板左下角通常有 `{}` 按钮，可以 Pretty print。它会把一行代码展开成多行。

格式化不会恢复变量名含义，但能恢复结构：

- 函数边界。
- if / else。
- for / while。
- try / catch。
- 对象字面量。

这一步非常重要。没有格式化就直接读压缩代码，效率很低。

### 第二步：搜索关键词

常见关键词：

```text
fetch
XMLHttpRequest
axios
sign
token
timestamp
nonce
localStorage
sessionStorage
cookie
api/
```

如果你要找接口参数生成逻辑，优先搜索接口路径、参数名、错误提示、字段名。

### 第三步：从字符串入手

混淆代码可以改变量名，但字符串通常会留下线索。例如：

```javascript
"/api/search"
"invalid sign"
"Authorization"
"timestamp"
```

字符串就像路标。找到路标，再看它附近的函数。

### 第四步：结合断点

静态阅读很容易迷路。断点能让代码在运行时停住，看到真实变量值。常用方式：

- XHR / Fetch 断点。
- 在可疑函数开头打断点。
- 在参数生成后打断点。
- 在 `localStorage.getItem` 附近打断点。

### 第五步：写分析记录

不要只在脑子里理解。记录：

```text
接口：/api/search
触发：点击搜索按钮
关键函数：buildParams -> makeSign -> fetch
关键参数：keyword, ts, nonce, sign
签名输入：按字段名排序后的 query string
风险提示：密钥位于前端，仅适合低风险校验
```

分析记录是团队协作的基础。

## 自建混淆样例

先看一段正常代码：

```javascript
function buildParams(keyword) {
  const timestamp = Math.floor(Date.now() / 1000);
  const signText = keyword + "|" + timestamp + "|demo";
  return {
    keyword: keyword,
    timestamp: timestamp,
    signText: signText
  };
}

console.log(buildParams("python"));
```

手工做一点简单混淆：

```javascript
var _0xarr=["keyword","timestamp","signText","python","log"];
function _0xbuild(_0xa){
  var _0xt=Math["floor"](Date["now"]()/1000);
  var _0xs=_0xa+"|"+_0xt+"|"+"demo";
  var _0xo={};
  _0xo[_0xarr[0]]=_0xa;
  _0xo[_0xarr[1]]=_0xt;
  _0xo[_0xarr[2]]=_0xs;
  return _0xo;
}
console[_0xarr[4]](_0xbuild(_0xarr[3]));
```

这段代码没有高级技巧，但已经比原来难读。我们一步步恢复。

## 逐段拆解

### 识别字符串数组

```javascript
var _0xarr=["keyword","timestamp","signText","python","log"];
```

这类数组常用于隐藏字符串。后面代码里的 `_0xarr[0]` 实际是 `"keyword"`。

可以手工替换：

```javascript
_0xo["keyword"] = _0xa;
_0xo["timestamp"] = _0xt;
_0xo["signText"] = _0xs;
```

替换后语义马上清楚很多。

### 重命名变量

混淆变量：

```javascript
function _0xbuild(_0xa)
```

根据上下文可以重命名为：

```javascript
function buildParams(keyword)
```

注意，重命名是推断，不一定百分百准确。分析记录里应说明哪些是确定事实，哪些是推测。

### 还原属性访问

```javascript
Date["now"]()
Math["floor"](...)
```

可以还原为：

```javascript
Date.now()
Math.floor(...)
```

这种写法常见于混淆器，因为它把属性名也变成字符串，方便统一处理。

### 得到可读版本

恢复后：

```javascript
function buildParams(keyword) {
  const timestamp = Math.floor(Date.now() / 1000);
  const signText = keyword + "|" + timestamp + "|demo";
  const params = {};
  params["keyword"] = keyword;
  params["timestamp"] = timestamp;
  params["signText"] = signText;
  return params;
}

console.log(buildParams("python"));
```

这不是源码，但已经足够帮助我们理解逻辑。

## 常见混淆形态

### 短变量名

```javascript
function a(b,c){return b+c}
```

处理方法：结合调用位置和参数值重命名。

### 字符串数组

```javascript
var s=["/api/search","sign","token"];
fetch(s[0])
```

处理方法：把数组索引替换成字符串。

### 字符串拼接

```javascript
var url="/api/"+"sea"+"rch";
```

处理方法：运行或静态合并常量。

### 控制流平坦化

正常代码：

```javascript
step1();
step2();
step3();
```

混淆后：

```javascript
while (true) {
  switch (state) {
    case 0: step1(); state = 1; break;
    case 1: step2(); state = 2; break;
    case 2: step3(); return;
  }
}
```

处理方法：先确认执行顺序，再记录关键分支。复杂场景可以借助 AST 或运行时断点。

### 死代码

```javascript
if (false) {
  callUnusedFunction();
}
```

或永远不会被调用的函数。处理方法是结合运行时覆盖率和调用栈，不要把所有代码都当成关键逻辑。

## 工具选择

### DevTools Pretty Print

最方便，适合第一步格式化。

### Prettier

适合本地格式化 JS 文件：

```bash
npx prettier input.js --write
```

### AST 工具

当你需要批量替换字符串数组、重命名变量、删除死代码时，手工处理会很累。下一章会讲 Babel AST。

### 运行时断点

静态工具看结构，断点看真实值。两者结合效果最好。

## 常见错误

### 错误一：把压缩误认为加密

一行代码不等于加密。先 Pretty print，再判断难度。

### 错误二：试图一次读完整个文件

现代前端 bundle 可能几 MB。不要从头读到尾。围绕接口路径、参数名、调用栈定位关键区域。

### 错误三：过度相信变量名推断

你把 `_0xa` 改成 `keyword` 是为了理解，但这只是根据上下文的命名。分析文档中要区分原始事实和人工命名。

### 错误四：忽视 Source Map

内部系统如果有 Source Map，排障会简单很多。先看有没有 Source Map，不要一上来硬读压缩代码。

### 错误五：把前端逻辑当作完整安全边界

混淆只能增加阅读成本，不能真正保护前端秘密。真正的权限控制、密钥保护和数据范围校验应在服务端。

## 调试方法

### 使用覆盖率

Chrome DevTools 的 Coverage 工具可以显示哪些代码执行过。对于大文件，先找执行过的区域，能减少阅读范围。

### 用 console 验证小片段

把可疑函数的输入输出复制到 Console 中，用固定参数测试。注意只在自建或授权环境操作。

### 保存格式化版本

排障时可以保存一份格式化后的 JS 文件，并在分析记录里写清来源、时间、版本。不要把包含敏感业务逻辑的文件随意扩散。

### 对比版本差异

如果昨天能用，今天不能用，可能是前端 bundle 更新。对比两个版本的关键函数差异，比重新分析更快。

## 工程化扩展

### 建立分析工作台

团队可以建立一个本地目录：

```text
analysis/
  samples/
    app.2026-01-01.js
  formatted/
    app.2026-01-01.pretty.js
  notes/
    search_api.md
```

这样每次分析都有输入样本、处理结果和结论记录。

### 自有系统的防御建议

如果你负责自有系统安全：

- 不要把真正密钥放在前端。
- 不要依赖混淆保护核心权限。
- 生产环境谨慎暴露 Source Map。
- 服务端做身份、权限、额度、频率校验。
- 对异常请求做审计。

混淆可以保护代码可读性，但不能替代服务端安全设计。

## 安全与合规注意

可读性恢复是一种中性技术。它可以用于内部排障，也可能被滥用。本文只建议在这些边界内使用：

- 自建页面。
- 公司内部授权项目。
- 合作方明确授权的 SDK 或前端。
- 防御评估和安全审计。
- 教学靶场。

未授权目标不应分析其防护逻辑，更不应据此绕过访问限制。

## 本章小结

混淆并不可怕。先区分压缩、混淆、加密，再按格式化、搜索关键词、分析字符串、结合断点、记录结论的顺序处理，大多数工程排障问题都能推进。

下一章会进入 AST。AST 能让我们用程序理解和改写程序，适合批量处理字符串数组、常量折叠、死代码删除等工作。

## 课后练习

1. 把本章混淆样例复制到本地，用 Prettier 格式化。
2. 手工把 `_0xarr[0]` 这类索引替换为真实字符串。
3. 给变量重新命名，写出一份可读版本。
4. 在浏览器 Console 中运行混淆版和可读版，确认输出一致。
5. 写一份分析记录，说明每个变量名是如何推断出来的。
6. 查阅自己项目的前端构建产物，区分哪些是压缩，哪些是混淆。
