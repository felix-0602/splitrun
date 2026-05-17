# DEEPSHIP v0

> **按需启动的并行开发闭环。** 把复杂任务拆成独立 Work Unit，在隔离的 git worktree 中并行执行，最后带证据收敛合并。

DEEPSHIP 不是常驻框架。它是四个按需调用的命令，解决 Claude Code 的一个根本限制：**单线程、单上下文。**

## 四个命令

```
/deepship-scope   先对齐任务认知——"我理解对了吗？值不值得并行？"
/deepship-spawn   拆 WU，开隔离 worktree，并行启动 Claude Code 会话
/deepship-status  看所有 Lane 状态——谁 done、谁 blocked、能不能 land
/deepship-land    收报告、验边界、跑测试、合并分支、出交付摘要
```

## 核心闭环

```
scope → spawn → status → land
 共识     拆+开     看      收+证
```

- **scope** 让 Brain 在动手前把认知摊开给你纠偏。产物是 `.deepship/scope.md`
- **spawn** 基于共识拆 WU，展示文件边界，你确认后开 Lane。调 `spawn_lane.py` 创建 worktree + 启动终端
- **status** 聚合视图——done/blocked/越界/无报告/can-land 判定
- **land** 三类检查（Boundary/Evidence/Integration）全过才 merge。产物是 `.deepship/land-report.md`

## 什么时候用

- 任务涉及 ≥2 个互不依赖的模块
- 单次对话上下文不够，想并行推进
- 需要验证交付证据，不只是"AI 说做完了"

不适合并行的小任务直接用 Claude Code 就好。DEEPSHIP 的价值不是强行并行，是判断什么时候值得并行。

## 持久化

```text
.deepship/
  scope.md                  # scope 输出——任务共识
  lanes/index.json          # Lane 注册表
  lanes/LANE-XXX/task.md    # Lane 任务说明
  lanes/LANE-XXX/report.json# Lane 完成报告
  land-report.md            # land 输出——交付证据
```

## 自验证

```bash
python checks/verify.py
```

## 仓库结构

```text
DEEPSHIP/
├── skills/                     # 4 个 skill 文件
│   ├── deepship-scope/SKILL.md
│   ├── deepship-spawn/SKILL.md
│   ├── deepship-status/SKILL.md
│   └── deepship-land/SKILL.md
├── adapters/
│   ├── brain/                  # WU 分派 + Lane 监控
│   │   ├── dispatch.py
│   │   └── monitor.py
│   └── parallel/               # Lane 创建 + 工具函数
│       ├── spawn_lane.py
│       ├── _utils.py
│       └── rotate.py
├── checks/
│   └── verify.py               # 框架自检
├── CLAUDE.md                   # Skill 路由规则
└── README.md
```

## 与 v2/v3 的区别

v2/v3 是常驻框架：状态机、JIT 规则加载、Intent-Aware Profiles、hooks、revolution、interrupt、A2A……20+ 个目录，12 个状态文件，5 层适配器。

v0 是四个命令。不常驻、不熵增、只在需要时调用。

## License

MIT
