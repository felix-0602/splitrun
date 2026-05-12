"""
样例：临时 API 响应字段验证脚本
用法：python .claude/DEEPSHIP/checks/sample-api-check.py
跑完确认结果后删掉本文件。

checks/ 里的脚本遵循：写 → 跑 → 验证 → 删
不复用的不进测试套件，不累积历史遗物。
"""
import json, sys

# 示例：验证 API 响应包含必要字段
SAMPLE_RESPONSE = {
    "status": "ok",
    "data": {"id": 1, "name": "test"},
}

REQUIRED_FIELDS = ["status", "data"]
REQUIRED_DATA_FIELDS = ["id", "name"]

errors = []

for field in REQUIRED_FIELDS:
    if field not in SAMPLE_RESPONSE:
        errors.append(f"缺少顶层字段: {field}")

for field in REQUIRED_DATA_FIELDS:
    if field not in SAMPLE_RESPONSE.get("data", {}):
        errors.append(f"缺少 data 字段: {field}")

if errors:
    print("FAIL:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("OK: 所有必要字段存在")
