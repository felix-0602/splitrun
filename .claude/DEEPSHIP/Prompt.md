# Prompt.md — DEEPSHIP 框架自身项目定义

> 本文件是 DEEPSHIP 框架作为**项目**的目标和约束。根目录的同名文件是通用模板。

---

## 1. 项目身份

- **项目名称**：DEEPSHIP
- **一句话描述**：AI 自治开发的执行框架——定义"AI 怎么干活"的行为规范、状态机和契约体系
- **主要用户入口**：`~/.claude/CLAUDE.md` 索引 → 加载四文件体系
- **端到端主链路**：AI 启动 → READ_CONTEXT → 执行状态机 → VALIDATE（含自省）→ RECORD → 交付

---

## 2. 目标

1. AI agent 能从需求理解走到代码交付，每一步有可验证的产出
2. 框架自身的结构性退化能被自动检测（verify.py）
3. 每个使用 DEEPSHIP 的项目有独立的真相源，互不污染
4. 框架本身趋近"好的代码库"：契约清晰、可测试、改动安全

---

## 3. 非目标

- 不做项目管理（甘特图、资源分配）
- 不做 CI/CD（不替代 GitHub Actions）
- 不做语言专精（不替代 pytest、go test）
- 不做 GUI

---

## 4. 硬约束

| 类别 | 约束 | 原因 |
|------|------|------|
| 格式 | Markdown only | 任何编辑器可读 |
| 依赖 | 核心零外部依赖 | 不引入包袱 |
| 行数 | 单文件 ≤ 800 行 | 自身遵守 B.3 |

---

## 5. Done When

- [ ] `python .claude/DEEPSHIP/checks/verify.py` 零错误通过
- [ ] 根目录模板文件无项目特定数据
- [ ] README 声明可被 verify.py 验证
- [ ] Implement.md VALIDATE 含架构自省
