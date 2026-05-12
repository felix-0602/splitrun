# DEEPSHIP 端到端 Demo：Hello World

## 目标

证明 DEEPSHIP 协议 + Mate 执行层能完成完整的自治开发闭环：

```
初始化 → 拆 WU → 执行 → 验证 → 记录 → 恢复 → COMPLETE
```

## 前置

- DEEPSEEK_API_KEY 已设置
- Mate 已安装（`pip install -e .`）
- 或直接用 CC + DEEPSHIP hook

## 步骤

### 1. 初始化项目结构

```bash
cd demos/hello-world
cp -r ../../Prompt.md .deepship/
cp -r ../../Plan.md .deepship/
```

### 2. 定义目标任务

编辑 `.deepship/Prompt.md`，设置目标：
- 创建一个 hello.py，包含 say_hello(name) 函数
- 创建 test_hello.py，测试 say_hello
- 跑 pytest 确认通过

### 3. 拆 Work Units

编辑 `.deepship/work_units.json`：

```json
{
  "work_units": [
    {
      "id": "WU1",
      "description": "创建 hello.py 含 say_hello 函数",
      "status": "pending",
      "files_allowed": ["hello.py"],
      "acceptance_tests": ["pytest test_hello.py -v"],
      "assigned_to": "orchestrator"
    },
    {
      "id": "WU2",
      "description": "创建 test_hello.py 测试 say_hello",
      "status": "pending",
      "files_allowed": ["test_hello.py"],
      "acceptance_tests": ["pytest test_hello.py -v"],
      "depends_on": ["WU1"],
      "assigned_to": "orchestrator"
    }
  ]
}
```

### 4. 用 Mate 执行

```bash
# 自治模式
mate --workspace demos/hello-world -g "完成 hello world 项目：创建 say_hello 函数和测试"

# 或对话模式逐步推进
mate --workspace demos/hello-world
> /go 完成 hello world 项目
```

### 5. 验证交付物

```bash
ls hello.py test_hello.py          # 文件存在
python -m pytest test_hello.py -v   # 测试通过
cat .deepship/log.jsonl | wc -l    # 审计日志非空
cat .deepship/state.json           # 状态为 COMPLETE
```

### 6. 崩溃恢复测试

中断 Mate，重新运行：

```bash
mate --workspace demos/hello-world
```

Mate 从 `.deepship/state.json` 恢复到最后一致状态。

## 期望结果

- [ ] hello.py 和 test_hello.py 被创建
- [ ] pytest 测试通过
- [ ] .deepship/log.jsonl 记录了完整工具调用链
- [ ] .deepship/state.json 状态为 COMPLETE
- [ ] 每个 Work Unit 状态从 pending → done → integrated
- [ ] 中断恢复后能继续执行

## CC 模式（替代方案）

如果不用 Mate CLI，也可以用 CC + DEEPSHIP hook 跑：

```
1. CC 打开 demos/hello-world/
2. 告诉 CC：按 .deepship/state.json + work_units.json 执行
3. PreToolUse hook 会自动拦越界 Edit/Write
```
