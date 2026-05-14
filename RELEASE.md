# Release Checklist

发版前必须全部通过。任一失败 = 不发版。

## 1. 代码完整性

```bash
# 语法检查：所有 Python 文件必须能编译
python -m py_compile adapters/parallel/dispatcher.py
python -m py_compile adapters/parallel/collector.py
python -m py_compile adapters/parallel/rotate.py
python -m py_compile adapters/parallel/spawn_lane.py
python -m py_compile adapters/cc/hooks/deepship_gate.py
python -m py_compile adapters/cc/transition_state.py
python -m py_compile checks/gap_scan.py

# 无未跟踪的关键文件
git status --short | grep -v "\.pyc\|__pycache__"
```

## 2. Conformance 测试

```bash
# 所有 conformance case 必须通过
python -m unittest discover -s tests/conformance -p "test_*.py" -v

# 框架自验证
python checks/verify.py
```

## 3. 逻辑测试

```bash
# Fork 分组：execution_mode 强制施行
python -c "
from adapters.parallel.dispatcher import group_by_fork
# 验证：fork+parallel_group → 并行组；inline/serial → 串行组
"

# Rotate 门禁：非 rotatable 被拒绝
python -c "
from adapters.parallel.rotate import rotate
# 验证：continuation_mode != rotatable → exit 1
"

# Collector 安全：--cleanup 无 --apply 被拒绝
python adapters/parallel/collector.py --cleanup 2>&1 | grep -q 'ERROR' && echo 'PASS'
```

## 4. Schema 一致性

```bash
# work_units.json schema 包含两轴字段
python -c "
import json
from pathlib import Path
schema = json.loads(Path('schemas/work_unit.schema.json').read_text(encoding='utf-8'))
assert 'execution_mode' in schema['properties']
assert 'continuation_mode' in schema['properties']
assert 'parallel_group' in schema['properties']
print('OK')
"
```

## 5. 协议完整性

```bash
# 协议文档与 schema 一致
python checks/verify.py | grep -c 'PASS'

# 无 TODO / 占位符残留
grep -r "TODO\|FIXME\|XXX" protocol/ rules/ schemas/ --include="*.md" --include="*.json" | grep -v "RELEASE.md" && echo "WARN: TODOs found" || echo "OK"
```

## 6. 文档同步

- [ ] README.md 版本号与 VERSION 一致
- [ ] CHANGELOG.md 包含本次发版的所有重要变更
- [ ] Documentation.md §1 的状态为 `done` 且日期为当天
- [ ] `adapters/parallel/README.md` 的命令示例与实际 CLI 一致

## 7. 版本标记

```bash
VERSION=$(cat VERSION)
git tag -a "v$VERSION" -m "DEEPSHIP v$VERSION"
git push origin "v$VERSION"
```

## 8. 发布前最终检查

- [ ] `git status` 干净（无未提交改动）
- [ ] 所有 conformance case 通过
- [ ] collector `--cleanup` 安全门禁生效
- [ ] rotate 硬门禁生效
- [ ] dispatcher `execution_mode` 强制施行
- [ ] CHANGELOG 已更新
- [ ] VERSION 已更新
