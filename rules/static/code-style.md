# 代码规范（静态层）

> **在所有状态下适用。** EXECUTE 状态必须加载。受益于 prompt caching。
> 完整原文：`implement/code-style.md`

## 不可变性 (CRITICAL)

始终创建新对象，绝不修改已有对象：
```python
# BAD: user[field] = value; return user
# GOOD: return {**user, field: value}
```

## 核心原则

- **KISS**：选最简单且确实能用的方案
- **DRY**：确定是真重复再抽取，不提前抽象
- **YAGNI**：不建"以后可能用到"的东西

## 硬上限

- 文件 ≤ 800 行
- 函数 ≤ 50 行
- 嵌套 ≤ 4 层

## 命名

| 类型 | 风格 |
|------|------|
| 变量/函数 | `camelCase` |
| 布尔 | `is`/`has`/`should`/`can` 前缀 |
| 接口/类型/组件 | `PascalCase` |
| 常量 | `UPPER_SNAKE_CASE` |

## 错误处理

- 每层显式处理错误，不悄悄吞掉
- 绝不使用空 `except:` 或 `catch {}`

## 输入验证

- 在系统边界验证所有外部输入
- Fail fast——不合格直接报错
- 永不信任外部数据

## 重复利用优先

1. GitHub 搜索 → 2. 查包管理器 → 3. 查文档 → 4. 最后才手写

## 禁止

- 不凭记忆写 `old_string` → Edit 前必 Read
- 不改 bug 时顺手"优化"旁边代码
- 不加"以后可能用"的抽象
