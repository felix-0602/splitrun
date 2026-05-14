"""IntentClassifier — 归一化用户意图并分类路由类型."""

from __future__ import annotations

import re

from adapters.interrupt.schemas import NormalizedIntent, RouteType

# 需要独立 lane 的关键词（高复杂度 / 结构性改动）
LONG_TASK_KEYWORDS = [
    "implement", "implement a", "build", "create a", "refactor",
    "migrate", "redesign", "架构", "重构", "新建", "搭建",
    "design", "design a", "add a feature", "feature",
    "module", "system", "authentication", "database", "schema",
    "pipeline", "deployment", "rewrite",
]

# 小任务关键词（局部查询/修改）
SMALL_TASK_KEYWORDS = [
    "fix typo", "typo", "rename", "check", "look up",
    "what is", "where is", "how does", "find", "search",
    "explain", "show me", "read", "grep",
]

# 当前 lane 修改关键词（修正/补充当前目标）
MODIFY_PLAN_KEYWORDS = [
    "instead", "actually", "change the", "modify",
    "update the plan", "adjust", "revise",
    "不要", "换成", "改一下", "修正", "修改方案",
    "应该用", "换一种", "补充", "再加",
]


def normalize_intent(
    raw_input: str,
    current_lane_goal: str = "",
) -> NormalizedIntent:
    """将用户输入归一化为结构化意图。"""
    text = raw_input.strip()
    if not text:
        return NormalizedIntent(
            raw_input=raw_input,
            summary="(empty input)",
            route_type=RouteType.CACHE_ANSWER,
            confidence=0.0,
            ambiguity="Empty input — need clarification",
        )

    route_type, confidence = _classify_route(text, current_lane_goal)
    keywords = _extract_keywords(text)
    complexity = _estimate_complexity(text, route_type)
    ambiguity = _detect_ambiguity(text, route_type, confidence)

    return NormalizedIntent(
        raw_input=raw_input,
        summary=_summarize(text),
        route_type=route_type,
        confidence=confidence,
        ambiguity=ambiguity,
        keywords=keywords,
        estimated_complexity=complexity,
        replaces_current_goal=_is_replacement(text),
        supplements_current_goal=_is_supplement(text),
    )


def _classify_route(text: str, lane_goal: str) -> tuple[RouteType, float]:
    """分类路由类型，返回 (RouteType, confidence)。"""
    text_lower = text.lower()

    # 先检查 MODIFY_CURRENT_PLAN
    modify_score = sum(1 for kw in MODIFY_PLAN_KEYWORDS if kw.lower() in text_lower)
    if modify_score >= 2:
        return RouteType.MODIFY_CURRENT_PLAN, 0.85
    if modify_score == 1 and lane_goal and _related_to_goal(text_lower, lane_goal):
        return RouteType.MODIFY_CURRENT_PLAN, 0.75

    # 检查 NEW_LANE_LONG_TASK
    long_score = sum(1 for kw in LONG_TASK_KEYWORDS if kw.lower() in text_lower)
    if long_score >= 2 and len(text.split()) > 5:
        return RouteType.NEW_LANE_LONG_TASK, 0.80
    if long_score == 1 and len(text.split()) > 10:
        return RouteType.NEW_LANE_LONG_TASK, 0.70

    # 检查 CACHE_ANSWER（短问题，无需额外上下文）
    question_patterns = [
        r"^(what|where|who|when|why|how|is|are|can|does|do|should|which)\b",
        r"\?$",
    ]
    is_question = any(re.search(p, text_lower) for p in question_patterns)
    if is_question and len(text.split()) <= 10:
        return RouteType.CACHE_ANSWER, 0.85

    # 检查 SMALL_CONTEXT_TASK
    small_score = sum(1 for kw in SMALL_TASK_KEYWORDS if kw.lower() in text_lower)
    if small_score >= 1 and len(text.split()) <= 15:
        return RouteType.SMALL_CONTEXT_TASK, 0.75

    # 默认：根据长度和复杂度 fallback
    if len(text.split()) <= 5:
        return RouteType.CACHE_ANSWER, 0.60
    elif len(text.split()) <= 15:
        return RouteType.SMALL_CONTEXT_TASK, 0.55
    else:
        return RouteType.NEW_LANE_LONG_TASK, 0.50


def _extract_keywords(text: str) -> tuple[str, ...]:
    """从文本中提取关键词。"""
    words = text.lower().split()
    stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                   "to", "of", "in", "for", "on", "with", "at", "by", "from",
                   "and", "or", "but", "not", "this", "that", "it", "i", "we",
                   "you", "they", "me", "us", "him", "her", "them", "my", "our",
                   "your", "his", "its", "their", "do", "does", "did", "can",
                   "could", "will", "would", "shall", "should", "may", "might",
                   "just", "also", "very", "really", "so", "if", "then", "than"}
    keywords = []
    for w in words:
        clean = w.strip(",.!?;:\"'()[]{}")
        if clean and clean not in stop_words and len(clean) > 1:
            keywords.append(clean)
    return tuple(keywords[:10])


def _estimate_complexity(text: str, route_type: RouteType) -> str:
    """估算任务复杂度。"""
    word_count = len(text.split())
    if route_type == RouteType.CACHE_ANSWER:
        return "small"
    if route_type == RouteType.NEW_LANE_LONG_TASK:
        return "large"
    if word_count <= 10:
        return "small"
    elif word_count <= 30:
        return "medium"
    return "large"


def _detect_ambiguity(
    text: str, route_type: RouteType, confidence: float
) -> str | None:
    """检测意图是否模糊。"""
    if confidence < 0.6:
        return "Classification confidence too low — please clarify"
    if not text.strip():
        return "Empty input"
    word_count = len(text.split())
    if word_count <= 2:
        return "Input too short to determine intent"
    has_action_verb = bool(re.search(
        r"\b(implement|build|create|fix|change|modify|add|remove|delete|update|refactor|rewrite|migrate|design|configure|setup|deploy|test|debug|check|find|search|read|show|explain|run|start|stop|restart)\b",
        text.lower(),
    ))
    if not has_action_verb and route_type != RouteType.CACHE_ANSWER:
        return "No clear action verb detected"
    return None


def _summarize(text: str) -> str:
    """生成简短摘要。"""
    clean = text.strip().replace("\n", " ")
    if len(clean) <= 80:
        return clean
    return clean[:77] + "..."


def _is_replacement(text: str) -> bool:
    """判断是否替代当前目标。"""
    replacement_signals = [
        "instead of", "replace", "替代", "换成", "不要做",
        "stop doing", "abandon", "drop", "取消",
    ]
    return any(s.lower() in text.lower() for s in replacement_signals)


def _is_supplement(text: str) -> bool:
    """判断是否补充当前目标。"""
    supplement_signals = [
        "also", "additionally", "in addition", "补充", "再加",
        "另外", "顺便", "同时", "and also",
    ]
    return any(s.lower() in text.lower() for s in supplement_signals)


def _related_to_goal(text: str, goal: str) -> bool:
    """检查输入是否与当前 lane goal 相关。"""
    goal_words = set(goal.lower().split())
    text_words = set(text.lower().split())
    overlap = goal_words & text_words
    return len(overlap) >= 2
