# Plan.md — Milestone 切片与执行计划

> Netclass Sidekick U 校园 Adapter · Phase 1 Week 2

---

## Project Reality Scan

| 项 | 当前事实 | 证据位置 | 影响 |
|----|----------|----------|------|
| 用户入口 | `uai.unipus.cn` → 课程 → 教程学习/作业 | browser snapshot 2026-05-09 | 脚本需 `@match` 这两个域名 |
| 内容入口 | 点击练习跳转到 `ucontent.unipus.cn` | URL 路由实测 | 跨域但在同一浏览器会话，Tampermonkey 可覆盖 |
| 当前调用链路 | DOM 提取 → 无（adapter 为空占位） | `client/src/adapters/unipus.ts:14` | 从零搭建 |
| 题目容器 | `.question-common-abs-question-container` | browser js 实测 | 主 selector |
| 填空输入 | `.comp-abs-input > input` | browser js 实测 | fill 类型答案填入 |
| 音频元素 | `<audio class="unipus-audio-h5">` src CDN + URL hash 含 duration | browser js 实测 | 听力题需下载音频送 Whisper |
| 时长追踪 | 学习记录页：必修学习时长/进度/得分 per unit | browser text 实测 | 验证指标 |
| 活跃度检测 | 鼠标/键盘长时间无操作暂停计时 | recon report | time-padder 需模拟 mousemove |
| 既有断点 | adapter 全为空占位；time-padder 也是占位；无 U 校园测试 | `unipus.ts`, `unipus-video.ts` | 从头实现 |

---

## Milestone 依赖图

```
M1: U校园题目提取 + 答案填入（填空/选择）
 |
 +---> M2: U校园 time-padder（音频视频自动播放 + 活跃度模拟）
 |
 +---> M3: U校园集成验证 + E2E
```

---

## M1: U校园题目提取 + 答案填入

- **目标**：脚本能在 U 校园练习页自动提取题目 DOM，填答案，提交
- **依赖**：无（已有超星 adapter 的 answer/fill 模块可复用）
- **建议 Effort**：`high`
- **预估文件数**：~4 个（adapter 重写 + filler 适配 + types + 测试）
- **主导质量维度**：🧩 Module Depth
- **质量门禁**：extract → answer → fill 链路在 fixture HTML 上跑通
- **文档影响**：更新 docs/ARCHITECTURE.md 的模块边界表
- **版本影响**：minor（新增 adapter，不影响现有超星行为）

### Acceptance Criteria
- [ ] AC1: `extractQuestionsFromUnipus()` 从 fixture HTML 提取题目：题干 + 选项 + 题型 + 音频 URL
- [ ] AC2: `createFiller()` 能填入 `.comp-abs-input > input` 的填空答案
- [ ] AC3: 适配 `fill/choice.ts` 到 U 校园选择题 DOM（若存在）
- [ ] AC4: `router.ts` 在 `ucontent.unipus.cn` 域名下触发 unipus adapter

### Reality Links
- **覆盖的用户入口/链路**：ucontent 练习页 → extract → /answer API → fill DOM
- **修复的既有断点**：`unipus.ts` 空占位 → 实装
- **不覆盖的相关断点**：听力 Whisper STT（留 Phase 2）；视频刷时长（留 M2）

### Real Acceptance Scenarios
- [ ] 用 Playwright 加载 `test/fixtures/unipus-listening-fill.json` fixture，extract 成功出 ≥1 道题
- [ ] 模拟 /answer hit 返回答案，filler 正确填入 input

### Validation Commands
```bash
cd server && npx tsc --noEmit && npx vitest run
cd client && npx tsc --noEmit && npx vitest run
```

### Documentation & Version Tasks
- [ ] 更新 `docs/ARCHITECTURE.md` 模块边界表 unipus adapter 状态
- [ ] bump client version minor

### Residual Risks
- [ ] 听力题自动答题依赖 Whisper（Phase 2），当前仅提取音频 URL
- [ ] 选择题 DOM 未经实测确认（所有已完成课程都是填空），需等新用户遇到选择题时补 adapter

---

## M2: U校园 time-padder（音频视频自动播放 + 活跃度模拟）

- **目标**：自动播放音频/视频，模拟活跃度防检测，刷满必修学习时长
- **依赖**：M1
- **建议 Effort**：`medium`
- **预估文件数**：~2 个（unipus-video 重写 + 测试）
- **主导质量维度**：🎨 UX
- **质量门禁**：video/audio hook + mousemove 模拟在 fixture 上可验证
- **文档影响**：无
- **版本影响**：patch

### Acceptance Criteria
- [ ] AC1: 检测 `<audio>` / `<video>` 元素自动 play + muted + 播放速率
- [ ] AC2: 每 3min ±30s 模拟 mousemove 防活跃度检测
- [ ] AC3: 学习记录页显示学习时长增长（验证指标）

### Reality Links
- **覆盖的用户入口/链路**：教程学习 → 视频/音频任务 → time-padder hook
- **修复的既有断点**：`unipus-video.ts` 空占位 → 基本实现
- **不覆盖的相关断点**：React state 深层 hook（暂用 DOM 级 play/pause 操作）

### Real Acceptance Scenarios
- [ ] U 校园视频页加载后 audio/video 自动播放
- [ ] 3 分钟后验证 mousemove 事件已派发

### Validation Commands
```bash
cd client && npx vitest run
```

### Documentation & Version Tasks
- [ ] 无文档影响（内部实现）
- [ ] bump client version patch

### Residual Risks
- [ ] 活跃度检测可能升级（需后续实地验证）
- [ ] React state hook 更可靠但工程量更大（当前 DOM 级方案先跑通）

---

## M3: U校园集成验证 + E2E

- **目标**：端到端验证 + fixture 补充 + 已知问题收口
- **依赖**：M2
- **建议 Effort**：`medium`
- **预估文件数**：~2 个
- **主导质量维度**：🔭 Observability
- **质量门禁**：全量测试绿 + E2E fixture 回归
- **文档影响**：更新 CHANGELOG
- **版本影响**：minor（U校园支持正式发布）

### Acceptance Criteria
- [ ] AC1: 全量 client + server 测试绿
- [ ] AC2: 至少 1 条 U 校园 E2E fixture 回归
- [ ] AC3: CHANGELOG 记录 U 校园支持

### Validation Commands
```bash
cd server && npx vitest run && cd ../client && npx vitest run
```

---

## 进度总览

| Milestone | 状态 | Effort |
|-----------|------|--------|
| M1 | ⬜ pending | high |
| M2 | ⬜ pending | medium |
| M3 | ⬜ pending | medium |
