# 代码规范

> 提炼自 `~/.claude/rules/common/`，完整原文见对应规则文件。

## Section B: 代码规范

> 以下提炼自 `~/.claude/rules/common/`，完整原文见对应规则文件。

### B.1 不可变性 (CRITICAL)

**始终创建新对象，绝不修改已有对象。**

```python
# BAD: 修改原对象
def update_user(user, field, value):
    user[field] = value
    return user

# GOOD: 返回新对象
def update_user(user, field, value):
    return {**user, field: value}
```

### B.2 核心原则

| 原则 | 含义 |
|------|------|
| **KISS** | 选最简单且确实能用的方案 |
| **DRY** | 重复逻辑抽取为共享函数，但确定是真重复再抽 |
| **YAGNI** | 不建"以后可能用到"的东西，按需扩展 |

### B.3 文件组织

- 文件 200-400 行典型，**800 行为硬上限**
- 函数 **50 行为硬上限**
- 按 feature/domain 组织，不按 type 组织
- 高内聚、低耦合

### B.4 错误处理

- 每层显式处理错误，不悄悄吞掉
- UI 层给用户友好提示
- 服务端记录详细上下文日志
- **绝不**用空的 `except:` 或 `catch {}`

### B.5 命名约定

| 类型 | 风格 | 示例 |
|------|------|------|
| 变量/函数 | `camelCase` | `getUserById` |
| 布尔值 | `is`/`has`/`should`/`can` 前缀 | `isActive`, `hasPermission` |
| 接口/类型/组件 | `PascalCase` | `UserProfile`, `OrderService` |
| 常量 | `UPPER_SNAKE_CASE` | `MAX_RETRY_COUNT` |

### B.6 输入验证

- 在**系统边界**验证所有外部输入
- 用 schema 验证（Zod/Pydantic/joi）
- Fail fast——不合格直接报错，不传进内部逻辑
- 永不信任外部数据（API 响应、用户输入、文件内容）

### B.7 重复利用优先

在写任何新代码前：
1. **GitHub 搜索已有实现** → `gh search repos` / `gh search code`
2. **查包管理器** → npm / PyPI / crates.io
3. **再查文档** → Context7 / 官方 docs
4. **最后才手写** → 优先 fork/port/wrap 已有方案

### B.8 深度模块与接口设计 (CRITICAL)

模块好不好，不看内部多优雅，看**测试是写起来像在描述行为，还是写起来像在拼凑内部依赖**。以下三条规则在每轮 EXECUTE 前自检。

#### 规则 1：接口优先——先用测试定义契约，再写实现

写任何模块前，先写 3 段调用方视角的测试草稿：成功路径 + 至少 2 条失败路径。这些测试定义接口契约——输入、输出、错误模式。

```typescript
// 先写这个（接口设计草稿），再写 createCheckoutSession 的实现
test("成功创建支付会话", async () => {
  const session = await createCheckoutSession({ cartId: "cart_123", method: "card" });
  expect(session.status).toBe("requires_payment");
  expect(session.url).toMatch(/^https:\/\/checkout\./);
});

test("购物车为空时直接拒绝", async () => {
  await expect(createCheckoutSession({ cartId: "empty", method: "card" }))
    .rejects.toThrow("CART_EMPTY");
});

test("支付方式不可用时返回明确错误", async () => {
  await expect(createCheckoutSession({ cartId: "cart_123", method: "wechat_pay" }))
    .rejects.toThrow("PAYMENT_METHOD_UNAVAILABLE");
});
```

**硬信号**：测试里 mock 超过 2 个 → 接口设计有问题，回退重来，别急着写实现。Mock 数量 ≈ 浅模块集群数量。

#### 规则 2：合并条件——穿过 3 个模块才能验证的行为，不是补测试，是合并模块

判断标准只有一个：你要测的这个行为，必须穿过几个模块的接口？

- **穿过 1 个** → 模块形状正确
- **穿过 3+ 个** → 浅模块集群，该合并了

```typescript
// BAD: 下单减库存散在 4 个模块，测试要准备 4 个 mock
class OrderService {
  async placeOrder(cart) {
    const items = await this.cartRepo.getItems(cart.id);       // 模块1
    await this.inventoryService.reserve(items);                 // 模块2
    const order = await this.orderRepo.create(items);           // 模块3
    await this.paymentService.charge(order.total);              // 模块4
    return order;
  }
}

// GOOD: 合并为深模块，接口只有一个入口，测试只需 2 个适配器
class OrderPlacement {
  async place(order: OrderRequest): Promise<OrderResult> {
    // 内部：库存检查 → 下单 → 支付 → 库存扣减
    // 调用方不需要知道内部有几个步骤
  }
}
```

合并后：旧单元测试删除，在新接口上重写行为测试。**不保留两份测试**——旧测试在重构时会碎，留着只会制造噪音。

#### 规则 3：接缝只在有两个适配器时存在

**一个适配器 = 假设性接缝，两个适配器 = 真正的接缝。** 不要在只有生产适配器的情况下引入 interface/port——那是为了"以后可能扩展"的废抽象。

| 依赖类型 | 例子 | 测试策略 | 需要接缝？ |
|----------|------|----------|-----------|
| 纯计算/内存状态 | 价格计算、状态机 | 直接测 | **不需要** |
| 本地可替换 | Postgres → PGLite, 内存文件系统 | 测试里跑真实替代品 | **内部接缝即可**，不暴露 |
| 远程但自己可控 | 自己的微服务 | 内存适配器 + HTTP 适配器 | **需要**，刚好两个适配器 |
| 真正的第三方 | Stripe, 短信, 邮件 | Mock 适配器 | **需要**，但只在系统边界 |

**不在接缝上再加接缝**：如果一个依赖可以本地替换，直接换，不要再包一层 interface。

```typescript
// BAD: Postgres 可以用 PGLite 替换，不需要再包一层 port
interface IDatabase {
  query(sql: string): Promise<Row[]>;
}
class PostgresDatabase implements IDatabase { ... }
class OrderService {
  constructor(private db: IDatabase) {}  // 废接缝——只有一个真实适配器
}

// GOOD: 直接依赖，测试用 PGLite 替换即可
class OrderService {
  constructor(private db: PostgresClient) {}  // 测试注入 PGLite 实例
}
```

#### 每轮 EXECUTE 前自检

```
[ ] 新模块的接口能让测试覆盖所有关键行为吗？（成功 + ≥2 失败路径）
[ ] 测试 mock 超过 2 个吗？→ 回退，重新设计接口
[ ] 测一个行为穿过 3+ 个模块吗？→ 合并模块，不补测试
[ ] 引入的接缝有至少两个适配器吗？→ 只有一个就别建
[ ] 旧测试删了吗？→ 合并后旧单元测试必须删除
```

#### 逃逸出口：无法遵守时，记录而非阻塞

以上规则是设计目标，不是阻塞条件。遇到以下真实困境可以暂时违反，但必须**有记录、有意识**：

| 困境 | 典型场景 | 本轮处理方式 |
|------|---------|-------------|
| 遗留代码改造 | 散在 4 个模块，但合并需 3 天，只剩 2 小时 | 最小改动交付，记录债务 |
| 框架约束 | Controller / route handler 天生是 pass-through | 框架决定的浅模块不必强求深度 |
| 接口未收敛 | 新功能，调用方还不确定需要什么 | 先写脏实现让调用方用，接口从使用中浮现后重构 |
| 第三方复杂度是真实的 | 底层服务接口本就很大，无法简化 | 如实包装，不强行缩小接口 |

**违反时必须记录**：在 Documentation.md §5 已知问题中追加一条，格式如下：

```
违反哪条规则 + 原因 + 剩余风险 + 计划什么时候还债（或为什么不还）
```

没有记录的违反 = 屎山。记录了的违反 = 技术债。

---

### B.9 DOM 脚本开发：先验证再编码

写 userscript / Playwright / 任何跟网页 DOM 交互的脚本时，**禁止凭源码分析猜测 DOM 结构**。
SPA 渲染、iframe 嵌套、JS 动态创建元素都会让运行时 DOM 跟源码判断完全不同。

- **规则**：改 DOM 交互逻辑前，用 `Skill(connect-chrome)` 开真实浏览器 → `js` 命令抓取实际 DOM 树 → 确认 selector/层级/时序后再动手。
- **反例**：本次会话 4 个 bug 中有 3 个如果只看源码会修错方向。Chrome 实况抓取到 work 壳 3 层嵌套 + 内层 api/work iframe 由 JS 动态创建，这是源码分析永远看不到的事实。

### B.10 iframe Document 引用：跨异步边界即失效

`HTMLIFrameElement.contentDocument` 返回的 `Document` 对象在 iframe 导航（表单提交、链接跳转、JS redirect）后会变成 **detached document** — 所有 `querySelector` / `querySelectorAll` 返回空结果，且**不报错**。

- **规则**：任何 `await`（尤其是表单提交、页面跳转）之后，**必须从 iframe 元素重新取 `contentDocument`**，不能用之前缓存的变量。
- **反例**：`filler.ts` 在 `submitWork()` 前 capture 了 `rootDoc`，提交后 iframe reload，`readMarks(rootDoc)` 读到 detached document → 批改全显示 `?`。修复：`frameElement.contentDocument` 重取。

### B.11 Edit 前必读文件：不靠记忆写 old_string

Edit 工具要求 `old_string` 精确字符匹配（含空格、换行、缩进）。凭记忆写几乎必错——少一个空格、多一个换行、`13px` 记成 `14px`，整个 edit 就 fail。

- **规则**：Edit 任何文件前，**必须先用 Read 确认当前内容**，从 Read 输出中逐字符复制 `old_string`。
- **反例**：本轮 UI 重写时，Edit App.css 凭记忆拼 `old_string`，结果 `font-size: 14px` 实际是 `13px`，差一个数字就 fail。
- **心跳期间**：如果上次 Read 已超过 5 次工具调用，重新 Read 确认内容没有因 linter/用户/并行 agent 修改而漂移。

---

