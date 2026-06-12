# 第 24 章：AST 逆向基础
## 本章在主流程中的位置

AST 分析是第 21-23 章的进一步工程化：当人工阅读 JavaScript 变得困难时，用语法树帮助我们定位函数、变量和调用关系。

它仍然服务第 1 章的主流程，尤其是“找到入口”和“发送请求”。分析的最终产出应该回到稳定请求、清晰参数和可维护代码，而不是停留在技术演示。

## 背景介绍

上一章我们手工恢复了一段混淆 JavaScript 的可读性。手工处理适合小片段，但真实项目里，代码可能有几千行、几万行。如果每个 `_0xarr[3]` 都靠手工替换，很快就会出错。

这时就需要 AST。

AST 是 Abstract Syntax Tree，中文叫抽象语法树。它可以理解成“代码的结构化说明书”。人看到的是一行行代码，解析器看到的是树：

```javascript
const x = 1 + 2;
```

在 AST 里，它大致会变成：

```text
VariableDeclaration
  VariableDeclarator
    Identifier: x
    BinaryExpression: +
      NumericLiteral: 1
      NumericLiteral: 2
```

有了 AST，我们就可以用程序遍历代码结构，找到字符串数组、替换属性访问、折叠常量、删除无用分支、统计函数调用关系。

本章是入门，不追求把所有混淆都自动还原。目标是让你理解 AST 的价值，并能对自建样例做几个基础转换。

## 本章目标

学完本章后，你应该能做到：

1. 理解 AST 是什么，以及为什么它比字符串替换可靠。
2. 使用 Babel 解析 JavaScript。
3. 遍历 AST 节点。
4. 识别变量声明、函数调用、成员访问、字符串字面量。
5. 对自建样例做简单转换。
6. 知道 AST 分析的边界和工程风险。

## 适用场景

AST 适合：

- 批量分析自有 JS 代码。
- 授权环境下做前端安全审计。
- 自动提取接口路径和参数名。
- 清理简单混淆样例。
- 生成调用关系表。
- 写代码迁移和重构工具。

## 不适用场景

AST 不适合：

- 未授权还原第三方防护逻辑。
- 指望一键破解所有混淆。
- 替代运行时调试。
- 处理所有动态执行逻辑，比如 `eval`、动态拼接函数、运行时解密。

AST 是静态分析工具，静态分析看的是代码结构；运行时值仍然需要断点、日志或沙箱执行辅助。

## 准备 Node.js 项目

新建目录：

```text
ast_demo/
  input.js
  analyze.js
  transform.js
  package.json
```

初始化：

```bash
npm init -y
npm install @babel/parser @babel/traverse @babel/generator @babel/types
```

这些包分别负责：

- `@babel/parser`：把 JavaScript 源码解析成 AST。
- `@babel/traverse`：遍历 AST。
- `@babel/generator`：把 AST 重新生成代码。
- `@babel/types`：判断和创建 AST 节点。

## 输入样例

`input.js`：

```javascript
var _0xarr = ["keyword", "timestamp", "signText", "python", "log"];

function _0xbuild(_0xa) {
  var _0xt = Math["floor"](Date["now"]() / 1000);
  var _0xs = _0xa + "|" + _0xt + "|" + "demo";
  var _0xo = {};
  _0xo[_0xarr[0]] = _0xa;
  _0xo[_0xarr[1]] = _0xt;
  _0xo[_0xarr[2]] = _0xs;
  return _0xo;
}

console[_0xarr[4]](_0xbuild(_0xarr[3]));
```

这个样例和上一章一致。我们要做几件事：

1. 找出字符串数组。
2. 把 `_0xarr[0]` 替换为 `"keyword"`。
3. 把 `Math["floor"]` 替换为 `Math.floor`。
4. 输出可读一些的代码。

## 第一个 AST 分析脚本

`analyze.js`：

```javascript
const fs = require("fs");
const parser = require("@babel/parser");
const traverse = require("@babel/traverse").default;

const code = fs.readFileSync("input.js", "utf8");
const ast = parser.parse(code, {
  sourceType: "script",
});

traverse(ast, {
  VariableDeclarator(path) {
    const id = path.node.id;
    const init = path.node.init;

    if (!id || !init) {
      return;
    }

    if (init.type === "ArrayExpression") {
      const values = init.elements.map(element => {
        if (element && element.type === "StringLiteral") {
          return element.value;
        }
        return null;
      });

      console.log("array variable:", id.name, values);
    }
  },

  CallExpression(path) {
    const callee = path.node.callee;
    console.log("call expression:", callee.type);
  },
});
```

运行：

```bash
node analyze.js
```

你会看到类似：

```text
array variable: _0xarr [ 'keyword', 'timestamp', 'signText', 'python', 'log' ]
call expression: MemberExpression
...
```

这说明我们已经能用程序找到字符串数组。

## 逐段解释

```javascript
const code = fs.readFileSync("input.js", "utf8");
```

读取源代码。AST 工具处理的是文本输入。

```javascript
const ast = parser.parse(code, {
  sourceType: "script",
});
```

把代码解析成 AST。`sourceType` 可以是 `script` 或 `module`。普通脚本用 `script`，有 `import/export` 的现代模块用 `module`。

```javascript
traverse(ast, {
  VariableDeclarator(path) {
    ...
  }
});
```

遍历 AST。每遇到一个变量声明节点，就执行 `VariableDeclarator` 里的函数。

```javascript
if (init.type === "ArrayExpression") {
```

判断变量初始值是不是数组。

```javascript
element.type === "StringLiteral"
```

判断数组元素是不是字符串字面量。

## 转换脚本：替换字符串数组索引

`transform.js`：

```javascript
const fs = require("fs");
const parser = require("@babel/parser");
const traverse = require("@babel/traverse").default;
const generate = require("@babel/generator").default;
const t = require("@babel/types");

const code = fs.readFileSync("input.js", "utf8");
const ast = parser.parse(code, {
  sourceType: "script",
});

const stringArrays = new Map();

traverse(ast, {
  VariableDeclarator(path) {
    const id = path.node.id;
    const init = path.node.init;

    if (!t.isIdentifier(id) || !t.isArrayExpression(init)) {
      return;
    }

    const values = [];
    for (const element of init.elements) {
      if (!t.isStringLiteral(element)) {
        return;
      }
      values.push(element.value);
    }

    stringArrays.set(id.name, values);
  },
});

traverse(ast, {
  MemberExpression(path) {
    const object = path.node.object;
    const property = path.node.property;

    if (
      t.isIdentifier(object) &&
      stringArrays.has(object.name) &&
      t.isNumericLiteral(property)
    ) {
      const values = stringArrays.get(object.name);
      const value = values[property.value];
      path.replaceWith(t.stringLiteral(value));
      return;
    }

    if (
      path.node.computed &&
      t.isStringLiteral(property) &&
      /^[A-Za-z_$][A-Za-z0-9_$]*$/.test(property.value)
    ) {
      path.node.computed = false;
      path.node.property = t.identifier(property.value);
    }
  },
});

const output = generate(ast, {
  comments: false,
  jsescOption: { minimal: true },
}).code;

fs.writeFileSync("output.js", output, "utf8");
console.log(output);
```

运行：

```bash
node transform.js
```

输出会接近：

```javascript
var _0xarr = ["keyword", "timestamp", "signText", "python", "log"];
function _0xbuild(_0xa) {
  var _0xt = Math.floor(Date.now() / 1000);
  var _0xs = _0xa + "|" + _0xt + "|" + "demo";
  var _0xo = {};
  _0xo["keyword"] = _0xa;
  _0xo["timestamp"] = _0xt;
  _0xo["signText"] = _0xs;
  return _0xo;
}
console.log(_0xbuild("python"));
```

虽然变量名还没有恢复，但字符串索引和属性访问已经清楚很多。

## 逐段解释转换逻辑

### 收集字符串数组

```javascript
const stringArrays = new Map();
```

用 Map 保存数组变量名和字符串列表：

```text
_0xarr -> ["keyword", "timestamp", "signText", "python", "log"]
```

第一遍遍历只负责收集信息，不修改代码。这样逻辑更清晰。

### 判断数组是否全是字符串

```javascript
for (const element of init.elements) {
  if (!t.isStringLiteral(element)) {
    return;
  }
  values.push(element.value);
}
```

如果数组里不全是字符串，就先不处理。入门阶段宁可保守，避免误替换。

### 替换 `_0xarr[0]`

```javascript
if (
  t.isIdentifier(object) &&
  stringArrays.has(object.name) &&
  t.isNumericLiteral(property)
) {
  const values = stringArrays.get(object.name);
  const value = values[property.value];
  path.replaceWith(t.stringLiteral(value));
}
```

这段检测成员访问：

```javascript
_0xarr[0]
```

如果对象名是已知字符串数组，属性是数字，就替换成字符串字面量：

```javascript
"keyword"
```

### 替换 `Date["now"]`

```javascript
if (
  path.node.computed &&
  t.isStringLiteral(property) &&
  /^[A-Za-z_$][A-Za-z0-9_$]*$/.test(property.value)
) {
  path.node.computed = false;
  path.node.property = t.identifier(property.value);
}
```

这段把：

```javascript
Date["now"]
```

改成：

```javascript
Date.now
```

只有属性名是合法标识符时才能这样改。如果属性名包含 `-`，就不能改成点语法。

## 为什么 AST 比字符串替换可靠

你可能会想，用字符串替换不也能把 `_0xarr[0]` 替换掉吗？

简单情况下可以。但字符串替换不知道代码结构，容易误伤：

```javascript
var text = "_0xarr[0] should not be replaced inside this string";
```

字符串替换可能把字符串内容也改了。AST 知道哪个是代码里的成员访问，哪个只是字符串文本，所以更可靠。

AST 还可以处理空格、换行、括号差异：

```javascript
_0xarr [ 0 ]
```

字符串匹配可能漏掉，AST 不会。

## 常见 AST 节点

入门阶段先记这些：

| 节点类型 | 含义 | 示例 |
| --- | --- | --- |
| Identifier | 标识符 | `name` |
| StringLiteral | 字符串 | `"hello"` |
| NumericLiteral | 数字 | `123` |
| VariableDeclarator | 变量声明项 | `const x = 1` 中的 `x = 1` |
| FunctionDeclaration | 函数声明 | `function fn(){}` |
| CallExpression | 函数调用 | `fn()` |
| MemberExpression | 成员访问 | `obj.name` 或 `obj["name"]` |
| BinaryExpression | 二元表达式 | `a + b` |
| AssignmentExpression | 赋值表达式 | `a = b` |
| ReturnStatement | return 语句 | `return x` |

不需要一开始背完整 AST 规范。遇到不懂的节点，可以打印出来看。

## 调试 AST 脚本

### 打印节点

```javascript
console.log(JSON.stringify(path.node, null, 2));
```

这能看到节点完整结构。但大文件会输出很多，建议只在特定条件下打印。

### 使用 AST Explorer

AST Explorer 是学习 AST 很好的工具。把代码粘进去，选择 Babel parser，就能看到树结构。它适合学习节点类型和路径。

### 小步转换

不要一上来写一个万能转换器。建议：

1. 先只识别字符串数组。
2. 再替换索引访问。
3. 再恢复属性访问。
4. 再做常量折叠。
5. 再尝试删除无用代码。

每一步都保存输出并运行测试。

## 常见错误

### 错误一：误替换动态索引

```javascript
_0xarr[i]
```

这里 `i` 运行时才知道。入门转换器不应该乱替换。

### 错误二：删除看似无用但有副作用的代码

```javascript
unused();
```

函数名叫 unused，不代表没有副作用。它可能写 Cookie、修改全局变量、发请求。删除代码前要确认行为。

### 错误三：忽略作用域

不同作用域可能有同名变量：

```javascript
var _0xarr = ["a"];
function test() {
  var _0xarr = ["b"];
}
```

简单按变量名替换可能出错。复杂转换要理解作用域绑定。Babel 的 `path.scope` 可以帮助处理。

### 错误四：把 AST 当万能逆向工具

AST 很强，但处理不了所有运行时行为。比如：

```javascript
eval(code)
new Function(code)
```

这类动态代码需要结合运行时分析。

## 工程化扩展

### 提取接口路径

可以遍历 `StringLiteral`，找出包含 `/api/` 的字符串：

```javascript
traverse(ast, {
  StringLiteral(path) {
    if (path.node.value.includes("/api/")) {
      console.log("api path:", path.node.value);
    }
  },
});
```

这适合自有项目做接口清单审计。

### 生成调用关系表

遍历 `FunctionDeclaration` 和 `CallExpression`，可以生成粗略调用关系。虽然不一定完整，但对理解大文件很有帮助。

### 代码迁移

AST 不只用于逆向，也常用于重构。例如：

- 批量替换旧 API。
- 修改 import 路径。
- 插入埋点。
- 迁移框架写法。

理解 AST 会提高你处理大型代码库的能力。

## 安全与合规注意

AST 分析本身是一种通用编程技术。本书把它放在授权测试、自建靶场、防御理解和工程排障语境里。使用时要遵守：

- 不分析未授权目标的防护逻辑。
- 不还原或复制第三方商业核心代码。
- 不绕过访问控制。
- 不把包含敏感逻辑的样本随意传播。
- 对内部分析产物做好权限管理。

## 本章小结

AST 是代码的结构化表示。相比字符串替换，它更可靠、更可控，适合批量分析和转换 JavaScript。

本章你完成了：

- 使用 Babel 解析代码。
- 遍历变量声明和函数调用。
- 找出字符串数组。
- 替换字符串数组索引。
- 恢复 `Date["now"]` 这类属性访问。

到这里，第七篇的基础已经完整：你知道为什么要分析 JS，理解常见参数生成，能恢复简单混淆可读性，也能用 AST 做基础转换。

## 课后练习

1. 创建 `ast_demo` 项目，安装 Babel 相关依赖。
2. 运行 `analyze.js`，打印字符串数组。
3. 运行 `transform.js`，生成 `output.js`。
4. 给输入样例增加 `_0xarr[5] = "/api/search"`，修改脚本提取 API 路径。
5. 尝试把 `_0xbuild` 手工重命名为 `buildParams`，观察输出是否仍能运行。
6. 写一段说明：AST 转换比字符串替换可靠在哪里，又有哪些边界。
