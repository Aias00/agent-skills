#!/usr/bin/env python3
"""
Aggregate candidates from multiple existing source skills into one review queue.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import quote

import requests
from source_fetchers import SOURCE_LABELS, save_source_candidates
SKILL_ROOT = Path(__file__).resolve().parents[1]
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5-mini")
GEMINI_BASE_URL = os.environ.get("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

SOURCE_MAP = {
    "techcrunch": {
        "label": SOURCE_LABELS["techcrunch"],
    },
    "the-verge": {
        "label": SOURCE_LABELS["the-verge"],
    },
    "hn": {
        "label": SOURCE_LABELS["hn"],
    },
    "github-trending": {
        "label": SOURCE_LABELS["github-trending"],
    },
    "engadget": {
        "label": SOURCE_LABELS["engadget"],
    },
    "fast-company": {
        "label": SOURCE_LABELS["fast-company"],
    },
}

ALIASES = {
    "tc": "techcrunch",
    "tech-crunch": "techcrunch",
    "theverge": "the-verge",
    "verge": "the-verge",
    "hackernews": "hn",
    "github": "github-trending",
    "gh": "github-trending",
    "eng": "engadget",
    "fastcompany": "fast-company",
}

SOURCE_PRIORITY = {
    "techcrunch": 100,  # TechCrunch有专门的AI版块，AI相关性高
    "the-verge": 95,    # The Verge有AI版块，AI相关性高
    "hn": 80,           # Hacker News有很多AI/ML讨论
    "github-trending": 70,  # GitHub Trending AI项目
    "engadget": 40,     # 综合科技媒体，AI相关内容少
    "fast-company": 35,  # 商业媒体，AI相关内容少
}

# 默认新闻源配置（优先使用AI相关性高的源）
DEFAULT_SOURCES = ["techcrunch", "the-verge", "hn", "github-trending"]

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "this",
    "to",
    "users",
    "using",
    "with",
    "your",
    "more",
    "new",
    "latest",
    "over",
    "amid",
    "after",
    "about",
    "will",
    "now",
    "start",
    "starts",
    "starting",
    "launches",
    "launch",
    "rolling",
    "rollout",
    "rollingout",
    "ai",
    "artificial",
    "intelligence",
    "agent",
    "agents",
    "model",
    "models",
    "chatbot",
    "chatbots",
    "llm",
    "llms",
}

BRAND_TOKENS = {
    "openai",
    "chatgpt",
    "google",
    "gemini",
    "anthropic",
    "claude",
    "meta",
    "amazon",
    "microsoft",
    "apple",
    "perplexity",
    "xai",
    "grok",
    "llama",
}

THEME_KEYWORDS = {
    "产品更新": ["launch", "launches", "rollout", "rolling", "brings", "generate", "feature", "features", "chrome"],
    "版权与监管": ["lawsuit", "sue", "copyright", "regulation", "rules", "court", "injunction"],
    "公司动作": ["funding", "acquires", "buying", "deal", "partnership", "wins", "faces"],
    "开发者与工具": ["github", "open source", "developer", "coding", "tool", "workspace", "docs", "sheets"],
}

THEME_COMMENTARY = {
    "产品更新": "这类新闻真正值得跟的是分发范围和入口位置，因为它通常意味着平台开始把 AI 能力从演示阶段推向日常使用场景。",
    "版权与监管": "这类话题的重点通常不只是案子本身，而是它会继续抬高 AI 公司在训练数据、授权和合规上的成本。",
    "公司动作": "公司动作类新闻更适合连着看，因为单条消息只是局部变化，放在竞争格局里才看得出方向。",
    "开发者与工具": "开发者工具类新闻通常最能提前反映下一波工作流变化，尤其是当它开始进入真实团队和重复场景时。",
    "行业动态": "行业动态类新闻的价值不在于一句结论，而在于它帮助你判断市场现在真正关注的是什么。",
}


def default_output_dir() -> Path:
    date_part = datetime.now().strftime("%Y-%m-%d")
    return SKILL_ROOT / "content" / date_part


def normalize_text(text: str) -> str:
    text = text or ""
    text = text.replace("’", "'").replace("“", '"').replace("”", '"').replace("–", "-").replace("—", "-")
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff\s\-]+", " ", text.lower())
    text = re.sub(r"\s+", " ", text).strip()
    return text


def strip_markdown(text: str) -> str:
    text = text or ""
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = text.replace("**", "").replace("__", "").replace("*", "")
    text = re.sub(r"^Hacker News 标题[:：]\s*", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text: str) -> set[str]:
    tokens = set()
    for token in re.findall(r"[a-z0-9\u4e00-\u9fff][a-z0-9\u4e00-\u9fff\-\+\.#]*", normalize_text(text)):
        token = token.strip("-.")
        if not token or len(token) <= 1:
            continue
        if token in STOPWORDS:
            continue
        tokens.add(token)
    return tokens


def signature_tokens(text: str) -> set[str]:
    return {token for token in tokenize(text) if token not in BRAND_TOKENS}


def read_candidate_preview(content_md: str) -> str:
    path = Path(content_md)
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            text = parts[2]
    paragraphs = []
    buffer: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if buffer:
                paragraph = " ".join(buffer).strip()
                if paragraph:
                    paragraphs.append(paragraph)
                buffer = []
            continue
        if line.startswith("#"):
            continue
        if line.startswith("**原文链接**") or line.startswith("**来源") or line.startswith("**作者**"):
            continue
        if line.startswith("**发布时间**") or line.startswith("**摘要**") or line.startswith("**分类**"):
            continue
        if line.startswith("![Image]"):
            continue
        buffer.append(line)
    if buffer:
        paragraph = " ".join(buffer).strip()
        if paragraph:
            paragraphs.append(paragraph)
    for paragraph in paragraphs:
        if len(paragraph) >= 40:
            return strip_markdown(paragraph[:320])
    return strip_markdown(paragraphs[0][:320]) if paragraphs else ""


def translate_text(text: str, cache: dict[str, str]) -> str:
    text = strip_markdown(text)
    if not text:
        return ""
    if text in cache:
        return cache[text]
    if re.search(r"[\u4e00-\u9fff]", text):
        cache[text] = text
        return text
    if len(text) > 700:
        text = text[:700]
    try:
        url = (
            "https://translate.googleapis.com/translate_a/single"
            f"?client=gtx&sl=en&tl=zh-CN&dt=t&q={quote(text)}"
        )
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        payload = response.json()
        translated = "".join(part[0] for part in payload[0] if part and part[0]).strip()
        translated = re.sub(r"\s+", " ", translated)
        cache[text] = translated or text
        return cache[text]
    except Exception:
        cache[text] = text
        return text


def has_openai_config() -> bool:
    return bool(OPENAI_API_KEY)


def has_gemini_config() -> bool:
    return bool(GEMINI_API_KEY)


def has_llm_config(provider: str = "auto") -> bool:
    if provider == "openai":
        return has_openai_config()
    if provider == "gemini":
        return has_gemini_config()
    return has_gemini_config() or has_openai_config()


def score_ai_relevance(item: dict, provider: str = "gemini") -> float:
    """
    使用LLM给新闻的AI相关性打分（0-10分）

    评分标准：
    - 10分: 纯AI核心技术（如GPT、Transformer、Diffusion等）
    - 8-9分: AI重要应用/产品（如AI芯片、自动驾驶、AI医疗等）
    - 6-7分: AI公司重大动态（OpenAI、Anthropic等重大新闻）
    - 4-5分: AI相关但不重要（如AI辅助工具、小公司AI产品）
    - 0-3分: 与AI无关（传统科技、其他领域）
    """
    title = item.get("title", "")
    description = item.get("description", "")
    preview = item.get("preview", "")

    # 如果没有内容，给最低分
    if not title and not description:
        return 0.0

    prompt = f"""请给以下新闻的AI相关性打分（0-10分）：

标题：{title}
描述：{description}

评分标准：
- 10分: 纯AI核心技术/大模型（如GPT、Claude、多模态、RLHF等）
- 8-9分: AI重要应用/产品（如AI芯片、自动驾驶、AI医疗、机器人等）
- 6-7分: AI公司重大动态（OpenAI、Anthropic、Google AI等重大新闻）
- 4-5分: AI相关但不重要（如AI辅助工具、小公司AI产品）
- 0-3分: 与AI无关（传统科技、娱乐、政治、其他领域）

只返回一个数字（0.0到10.0之间的分数），不要其他文字。"""

    try:
        if provider == "openai":
            response = call_openai_llm([{"role": "user", "content": prompt}], temperature=0.1)
        elif provider == "gemini":
            response = call_gemini_llm([{"role": "user", "content": prompt}], temperature=0.1)
        else:
            # auto 模式，优先使用 Gemini
            if has_gemini_config():
                response = call_gemini_llm([{"role": "user", "content": prompt}], temperature=0.1)
            elif has_openai_config():
                response = call_openai_llm([{"role": "user", "content": prompt}], temperature=0.1)
            else:
                return 5.0  # 默认中等分数

        # 提取数字
        import re
        match = re.search(r'(\d+\.?\d*)', response)
        if match:
            score = float(match.group(1))
            # 限制在0-10之间
            return max(0.0, min(10.0, score))
        return 5.0  # 默认中等分数
    except Exception as e:
        print(f"[warning] Failed to score AI relevance for '{title[:50]}': {e}")
        return 5.0


def generate_ai_summary(item: dict, provider: str = "gemini") -> str:
    """
    使用LLM生成高质量的AI新闻摘要

    生成2-3句话的中文摘要，突出：
    - 核心事件/技术
    - 重要性/影响
    - 具体细节（公司名称、技术名称等）
    """
    title = item.get("title", "")
    description = item.get("description", "")
    preview = item.get("preview", "")

    if not title and not description:
        return "暂无摘要"

    prompt = f"""请为以下新闻生成一个高质量的中文摘要（2-3句话，80-150字）：

标题：{title}
描述：{description}

要求：
1. 突出核心事件或技术点
2. 说明其重要性或影响
3. 提及具体的公司、技术或产品名称
4. 用简洁的中文表述，专业但不晦涩
5. 只返回摘要内容，不要其他文字

注意：如果这条新闻与AI无关，请直接返回"与AI无关"。"""

    try:
        if provider == "openai":
            response = call_openai_llm([{"role": "user", "content": prompt}], temperature=0.5)
        elif provider == "gemini":
            response = call_gemini_llm([{"role": "user", "content": prompt}], temperature=0.5)
        else:
            # auto 模式，优先使用 Gemini
            if has_gemini_config():
                response = call_gemini_llm([{"role": "user", "content": prompt}], temperature=0.5)
            elif has_openai_config():
                response = call_openai_llm([{"role": "user", "content": prompt}], temperature=0.5)
            else:
                return preview[:150] if preview else ""

        summary = response.strip()

        # 如果LLM说与AI无关，返回标记
        if "与ai无关" in summary.lower() or "不相关" in summary or "无关" in summary:
            return "与AI无关"

        return summary
    except Exception as e:
        print(f"[warning] Failed to generate summary for '{title[:50]}': {e}")
        return preview[:150] if preview else ""
    """
    使用LLM给新闻的AI相关性打分（0-10分）

    评分标准：
    - 10分: 纯AI核心技术（如GPT、Transformer、Diffusion等）
    - 8-9分: AI重要应用/产品（如AI芯片、自动驾驶、AI医疗等）
    - 6-7分: AI公司重大动态（OpenAI、Anthropic等重大新闻）
    - 4-5分: AI相关但不重要（如AI辅助工具、小公司AI产品）
    - 0-3分: 与AI无关（传统科技、其他领域）
    """
    title = item.get("title", "")
    description = item.get("description", "")
    preview = item.get("preview", "")

    # 如果没有内容，给最低分
    if not title and not description:
        return 0.0

    prompt = f"""请给以下新闻的AI相关性打分（0-10分）：

标题：{title}
描述：{description}

评分标准：
- 10分: 纯AI核心技术/大模型（如GPT、Claude、多模态、RLHF等）
- 8-9分: AI重要应用/产品（如AI芯片、自动驾驶、AI医疗、机器人等）
- 6-7分: AI公司重大动态（OpenAI、Anthropic、Google AI等重大新闻）
- 4-5分: AI相关但不重要（如AI辅助工具、小公司AI产品）
- 0-3分: 与AI无关（传统科技、娱乐、政治、其他领域）

只返回一个数字（0.0到10.0之间的分数），不要其他文字。"""

    try:
        if provider == "openai" or (provider == "auto" and has_openai_config()):
            response = call_openai_llm([{"role": "user", "content": prompt}], temperature=0.1)
        else:
            response = call_gemini_llm([{"role": "user", "content": prompt}], temperature=0.1)

        # 提取数字
        import re
        match = re.search(r'(\d+\.?\d*)', response)
        if match:
            score = float(match.group(1))
            # 限制在0-10之间
            return max(0.0, min(10.0, score))
        return 5.0  # 默认中等分数
    except Exception as e:
        print(f"[warning] Failed to score AI relevance for '{title[:50]}': {e}")
        return 5.0


def generate_ai_summary(item: dict, provider: str = "auto") -> str:
    """
    使用LLM生成高质量的AI新闻摘要

    生成2-3句话的中文摘要，突出：
    - 核心事件/技术
    - 重要性/影响
    - 具体细节（公司名称、技术名称等）
    """
    title = item.get("title", "")
    description = item.get("description", "")
    preview = item.get("preview", "")

    if not title and not description:
        return "暂无摘要"

    prompt = f"""请为以下新闻生成一个高质量的中文摘要（2-3句话，80-150字）：

标题：{title}
描述：{description}

要求：
1. 突出核心事件或技术点
2. 说明其重要性或影响
3. 提及具体的公司、技术或产品名称
4. 用简洁的中文表述，专业但不晦涩
5. 只返回摘要内容，不要其他文字

注意：如果这条新闻与AI无关，请直接返回"与AI无关"。"""

    try:
        if provider == "openai" or (provider == "auto" and has_openai_config()):
            response = call_openai_llm([{"role": "user", "content": prompt}], temperature=0.5)
        else:
            response = call_gemini_llm([{"role": "user", "content": prompt}], temperature=0.5)

        summary = response.strip()

        # 如果LLM说与AI无关，返回标记
        if "与ai无关" in summary.lower() or "不相关" in summary or "无关" in summary:
            return "与AI无关"

        return summary
    except Exception as e:
        print(f"[warning] Failed to generate summary for '{title[:50]}': {e}")
        return preview[:150] if preview else ""


def call_openai_llm(messages: list[dict], model: str | None = None, temperature: float = 0.4) -> str:
    if not has_openai_config():
        raise RuntimeError("OPENAI_API_KEY is not configured")
    url = f"{OPENAI_BASE_URL}/chat/completions"
    payload = {
        "model": model or OPENAI_MODEL,
        "messages": messages,
        "temperature": temperature,
    }
    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def call_gemini_llm(messages: list[dict], model: str | None = None, temperature: float = 0.4) -> str:
    if not has_gemini_config():
        raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY is not configured")

    system_chunks: list[str] = []
    contents: list[dict] = []
    for message in messages:
        raw_content = message.get("content", "")
        if isinstance(raw_content, list):
            text = "\n".join(
                part.get("text", "")
                for part in raw_content
                if isinstance(part, dict) and part.get("text")
            ).strip()
        else:
            text = str(raw_content).strip()
        if not text:
            continue
        role = message.get("role", "user")
        if role == "system":
            system_chunks.append(text)
            continue
        gemini_role = "model" if role == "assistant" else "user"
        contents.append({"role": gemini_role, "parts": [{"text": text}]})

    if not contents:
        raise RuntimeError("No prompt content available for Gemini rewrite")

    payload = {
        "contents": contents,
        "generationConfig": {"temperature": temperature},
    }
    if system_chunks:
        payload["system_instruction"] = {
            "parts": [{"text": "\n\n".join(system_chunks)}],
        }

    response = requests.post(
        f"{GEMINI_BASE_URL}/models/{model or GEMINI_MODEL}:generateContent",
        params={"key": GEMINI_API_KEY},
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    candidates = data.get("candidates") or []
    if not candidates:
        raise RuntimeError(f"Gemini returned no candidates: {json.dumps(data, ensure_ascii=False)[:500]}")
    parts = candidates[0].get("content", {}).get("parts") or []
    text = "".join(part.get("text", "") for part in parts if isinstance(part, dict)).strip()
    if not text:
        raise RuntimeError(f"Gemini returned empty content: {json.dumps(data, ensure_ascii=False)[:500]}")
    return text


def call_llm(messages: list[dict], model: str | None = None, temperature: float = 0.4, provider: str = "auto") -> str:
    if provider == "gemini":
        return call_gemini_llm(messages, model=model, temperature=temperature)
    if provider == "openai":
        return call_openai_llm(messages, model=model, temperature=temperature)
    if has_gemini_config():
        return call_gemini_llm(messages, model=model, temperature=temperature)
    return call_openai_llm(messages, model=model, temperature=temperature)


def source_score(source: str) -> int:
    return SOURCE_PRIORITY.get(source, 50)


def candidate_quality(item: dict) -> float:
    return (
        source_score(item["source"])
        + min(len(item.get("description", "")), 220) / 10
        + min(len(item.get("preview", "")), 320) / 16
    )


def similarity(left: dict, right: dict) -> float:
    tokens_left = left.get("signature_tokens") or left.get("tokens", set())
    tokens_right = right.get("signature_tokens") or right.get("tokens", set())
    if not tokens_left or not tokens_right:
        return 0.0
    jaccard = len(tokens_left & tokens_right) / max(len(tokens_left | tokens_right), 1)
    title_seq = SequenceMatcher(None, left.get("normalized_title", ""), right.get("normalized_title", "")).ratio()
    preview_seq = SequenceMatcher(None, left.get("normalized_preview", ""), right.get("normalized_preview", "")).ratio()
    return (jaccard * 0.55) + (title_seq * 0.30) + (preview_seq * 0.15)


def is_same_event(left: dict, right: dict) -> bool:
    signature_overlap = len((left.get("signature_tokens") or set()) & (right.get("signature_tokens") or set()))
    tokens_overlap = len(left.get("tokens", set()) & right.get("tokens", set()))
    score = similarity(left, right)
    if score >= 0.62 and signature_overlap >= 2:
        return True
    if score >= 0.54 and signature_overlap >= 2:
        return True
    if signature_overlap >= 3 and SequenceMatcher(None, left.get("normalized_title", ""), right.get("normalized_title", "")).ratio() >= 0.45:
        return True
    if signature_overlap >= 2 and tokens_overlap >= 4 and SequenceMatcher(None, left.get("normalized_preview", ""), right.get("normalized_preview", "")).ratio() >= 0.35:
        return True
    return False


def enrich_item(item: dict, enable_llm: bool = True, llm_provider: str = "gemini") -> dict:
    preview = read_candidate_preview(item.get("content_md", ""))
    combined = " ".join(
        part for part in [item.get("title", ""), item.get("description", ""), preview] if part
    )
    enriched = dict(item)
    enriched["preview"] = preview
    enriched["normalized_title"] = normalize_text(item.get("title", ""))
    enriched["normalized_preview"] = normalize_text(preview)
    enriched["tokens"] = tokenize(combined)
    enriched["signature_tokens"] = signature_tokens(combined)

    # 基础质量分数
    base_quality = candidate_quality({
        "source": item.get("source", ""),
        "description": item.get("description", ""),
        "preview": preview
    })

    # 如果启用LLM，添加AI相关性和摘要
    if enable_llm and has_llm_config(llm_provider):
        print(f"[llm] Scoring and summarizing: {item.get('title', '')[:50]}...")
        ai_score = score_ai_relevance(item, provider=llm_provider)
        ai_summary = generate_ai_summary(item, provider=llm_provider)

        enriched["ai_relevance_score"] = ai_score
        enriched["ai_summary"] = ai_summary

        print(f"[llm]   - AI score: {ai_score:.1f}/10")
        print(f"[llm]   - Summary: {ai_summary[:80]}...")

        # 如果摘要说与AI无关，降低AI相关性分数
        if ai_summary == "与AI无关":
            enriched["ai_relevance_score"] = 0.0
            print(f"[llm]   - Marked as not AI-related")

        # 调整总质量分数：AI相关性占70%，基础质量占30%
        # 这样可以优先选择AI相关且内容质量高的新闻
        enriched["quality_score"] = (ai_score * 10 * 0.7) + (base_quality * 0.3)
        print(f"[llm]   - Quality score: {enriched['quality_score']:.2f}")
    else:
        print(f"[skip] Skipping LLM for: {item.get('title', '')[:50]}...")
        enriched["ai_relevance_score"] = 5.0  # 默认中等分数
        enriched["ai_summary"] = preview[:150] if preview else ""
        enriched["quality_score"] = base_quality

    return enriched


def cluster_events(items: list[dict], enable_llm: bool = True, llm_provider: str = "gemini") -> tuple[list[dict], list[dict]]:
    print(f"[enrich] Processing {len(items)} candidates with LLM={enable_llm}...")
    enriched = [enrich_item(item, enable_llm=enable_llm, llm_provider=llm_provider) for item in items]
    clusters: list[list[dict]] = []
    for item in enriched:
        matched_cluster: list[dict] | None = None
        for cluster in clusters:
            if any(is_same_event(item, existing) for existing in cluster):
                matched_cluster = cluster
                break
        if matched_cluster is None:
            clusters.append([item])
        else:
            matched_cluster.append(item)

    all_candidates = []
    unique_manifest = []
    for event_number, cluster in enumerate(clusters, start=1):
        cluster = sorted(cluster, key=lambda x: (x["quality_score"], len(x.get("description", ""))), reverse=True)
        primary = cluster[0]
        event_id = f"E{event_number:03d}"
        related_candidates = []
        for rank, item in enumerate(cluster, start=1):
            item["event_id"] = event_id
            item["is_primary"] = rank == 1
            item["duplicate_count"] = len(cluster) - 1
            item["related_sources"] = [member["source"] for member in cluster]
            related_candidates.append(
                {
                    "source": item["source"],
                    "source_label": item["source_label"],
                    "source_index": item.get("source_index"),
                    "title": item["title"],
                    "source_url": item["source_url"],
                    "author": item.get("author", ""),
                    "published_time": item.get("published_time", ""),
                    "dir": item["dir"],
                    "content_md": item["content_md"],
                }
            )
            all_candidates.append(
                {
                    "global_index": item.get("global_index"),
                    "event_id": event_id,
                    "is_primary": rank == 1,
                    "source": item["source"],
                    "source_label": item["source_label"],
                    "source_index": item.get("source_index"),
                    "title": item["title"],
                    "source_url": item["source_url"],
                    "author": item.get("author", ""),
                    "published_time": item.get("published_time", ""),
                    "description": item.get("description", ""),
                    "preview": item.get("preview", ""),
                    "dir": item["dir"],
                    "content_md": item["content_md"],
                    "duplicate_count": len(cluster) - 1,
                    "related_sources": [member["source_label"] for member in cluster],
                    "ai_relevance_score": item.get("ai_relevance_score"),
                    "ai_summary": item.get("ai_summary"),
                    "quality_score": item.get("quality_score"),
                }
            )
        unique_manifest.append(
            {
                "event_id": event_id,
                "source": primary["source"],
                "source_label": primary["source_label"],
                "source_index": primary.get("source_index"),
                "title": primary["title"],
                "source_url": primary["source_url"],
                "author": primary.get("author", ""),
                "published_time": primary.get("published_time", ""),
                "description": primary.get("description", ""),
                "preview": primary.get("preview", ""),
                "dir": primary["dir"],
                "content_md": primary["content_md"],
                "related_candidates": related_candidates,
                "duplicate_count": len(cluster) - 1,
                "related_sources": sorted({member["source_label"] for member in cluster}),
                "ai_relevance_score": primary.get("ai_relevance_score"),
                "ai_summary": primary.get("ai_summary"),
                "quality_score": primary.get("quality_score"),
            }
        )

    for global_index, item in enumerate(unique_manifest, start=1):
        item["global_index"] = global_index
    return all_candidates, unique_manifest


def derive_theme(item: dict) -> str:
    haystack = normalize_text(" ".join([item.get("title", ""), item.get("description", ""), item.get("preview", "")]))
    for theme, keywords in THEME_KEYWORDS.items():
        if any(keyword in haystack for keyword in keywords):
            return theme
    return "行业动态"


def summarize_title_line(title: str) -> str:
    clean = title.strip().rstrip(".")
    lower = clean.lower()
    patterns = [
        (r"^(?P<subject>.+?) starts rolling out (?P<object>.+)$", "{subject} 开始向更多用户推出 {object}。"),
        (r"^(?P<subject>.+?) will now generate (?P<object>.+)$", "{subject} 新增了可生成 {object} 的能力。"),
        (r"^(?P<subject>.+?) is the latest to sue (?P<object>.+)$", "{subject} 成为最新起诉 {object} 的一方。"),
        (r"^(?P<subject>.+?) wins a temporary injunction against (?P<object>.+)$", "{subject} 暂时获得了针对 {object} 的禁令胜利。"),
        (r"^(?P<subject>.+?) faces a lawsuit over (?P<object>.+)$", "{subject} 因 {object} 面临新的诉讼。"),
        (r"^(?P<subject>.+?) brings (?P<object>.+?) to (?P<target>.+)$", "{subject} 把 {object} 带到了 {target}。"),
        (r"^(?P<subject>.+?) delays (?P<object>.+)$", "{subject} 推迟了 {object}。"),
        (r"^(?P<subject>.+?) buys (?P<object>.+)$", "{subject} 收购了 {object}。"),
    ]
    for pattern, template in patterns:
        match = re.match(pattern, lower)
        if not match:
            continue
        groups = {key: clean[match.start(key):match.end(key)] for key in match.groupdict()}
        return template.format(**groups)
    return f"这条热点聚焦“{clean}”这件事。"


def build_digest_intro(summary: dict, manifest: list[dict]) -> list[str]:
    lines = [
        "## 今日概览",
        "",
        f"今天共扫描 **{summary['source_count']}** 个来源，收集原始候选 **{summary['raw_candidate_count']}** 条，自动去重后保留 **{summary['candidate_count']}** 个独立事件。",
    ]
    themes: dict[str, int] = {}
    for item in manifest:
        theme = derive_theme(item)
        themes[theme] = themes.get(theme, 0) + 1
    if themes:
        ordered = sorted(themes.items(), key=lambda pair: pair[1], reverse=True)[:3]
        lines.append("今天的主线主要集中在：")
        for theme, count in ordered:
            lines.append(f"- {theme}：{count} 条")
    lines.append("")
    return lines


def first_sentence(text: str) -> str:
    text = strip_markdown(text)
    if not text:
        return ""
    match = re.split(r"(?<=[\.\!\?。！？])\s+", text, maxsplit=1)
    return match[0].strip()


def find_candidate_image(candidate_dir: str) -> Path | None:
    base = Path(candidate_dir)
    if not base.exists():
        return None
    for pattern in ("img_01.*", "img_1.*", "img_*.jpg", "img_*.png", "img_*.webp"):
        matches = sorted(base.glob(pattern))
        if matches:
            return matches[0]
    return None


def prepare_digest_images(output_dir: Path, manifest: list[dict]) -> tuple[dict[int, str], str]:
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    image_map: dict[int, str] = {}
    cover_path = ""
    for item in manifest:
        source_path = find_candidate_image(item["dir"])
        if source_path is None:
            for related in item.get("related_candidates", []):
                source_path = find_candidate_image(related["dir"])
                if source_path is not None:
                    break
        if source_path is None:
            continue
        target_name = f"{item['global_index']:02d}{source_path.suffix.lower()}"
        target_path = images_dir / target_name
        shutil.copy2(source_path, target_path)
        image_map[item["global_index"]] = f"images/{target_name}"
        if not cover_path:
            cover_name = f"cover{source_path.suffix.lower()}"
            cover_file = images_dir / cover_name
            shutil.copy2(source_path, cover_file)
            cover_path = f"images/{cover_name}"
    return image_map, cover_path


def build_digest_markdown(
    manifest: list[dict],
    summary: dict,
    image_map: dict[int, str],
    cover_path: str,
    translation_cache: dict[str, str],
) -> str:
    lines = [
        f"# 今日 AI 热点速读（{summary['date']}）",
        "",
        f"> 来源：{', '.join(item['label'] for item in summary['sources'] if item['ok'])} | 编译日期：{summary['date']}",
        "",
        "---",
        "",
    ]
    if cover_path:
        lines.extend([f"![封面图]({cover_path})", "",])
    lines.extend(build_digest_intro(summary, manifest))
    for item in manifest:
        image_path = image_map.get(item["global_index"])
        if image_path:
            lines.extend([f"![配图]({image_path})", "",])
        lines.extend(build_item_story(item, translation_cache))
    lines.extend(build_digest_outro(manifest))
    return "\n".join(lines).strip() + "\n"


def build_rewrite_prompt(summary: dict, manifest: list[dict], draft_markdown: str) -> list[dict]:
    event_briefs = []
    for item in manifest:
        event_briefs.append(
            {
                "index": item["global_index"],
                "title": item["title"],
                "source": item["source_label"],
                "description": item.get("description", ""),
                "preview": item.get("preview", ""),
                "duplicate_count": item.get("duplicate_count", 0),
                "related_sources": item.get("related_sources", []),
            }
        )
    system = (
        "你是一名科技媒体中文编辑。你的任务是把一篇已经结构化完成的 AI 热点速读稿，"
        "重写成更自然、可读、像人写的中文成文稿。"
        "必须保留 Markdown 结构、所有图片 markdown 行、所有原文链接。"
        "不要删除标题层级，不要新增虚构事实，不要改动链接 URL。"
        "可以润色标题、导语、过渡句和收尾。"
    )
    user = (
        f"日期：{summary['date']}\n"
        f"来源数：{summary['source_count']}\n"
        f"原始候选数：{summary['raw_candidate_count']}\n"
        f"去重后事件数：{summary['candidate_count']}\n\n"
        f"事件摘要：\n{json.dumps(event_briefs, ensure_ascii=False, indent=2)}\n\n"
        "下面是当前草稿。请直接输出可发布的 Markdown 正文，不要解释：\n\n"
        f"{draft_markdown}"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def rewrite_digest_with_llm(
    manifest: list[dict],
    summary: dict,
    draft_markdown: str,
    rewrite_mode: str,
    rewrite_model: str | None,
    rewrite_provider: str,
) -> tuple[str, str]:
    if rewrite_mode == "off":
        return draft_markdown, "heuristic"
    if rewrite_mode == "auto" and not has_llm_config(rewrite_provider):
        return draft_markdown, "heuristic"

    providers: list[str]
    if rewrite_provider == "auto":
        providers = []
        if has_gemini_config():
            providers.append("gemini")
        if has_openai_config():
            providers.append("openai")
    else:
        providers = [rewrite_provider]

    if not providers:
        if rewrite_mode == "api":
            raise RuntimeError("No configured rewrite provider found. Set GEMINI_API_KEY/GOOGLE_API_KEY or OPENAI_API_KEY.")
        return draft_markdown, "heuristic"

    def normalize_rewritten_markdown(text: str) -> str:
        text = text.strip()
        if text.startswith("```markdown"):
            text = text[len("```markdown"):].strip()
        elif text.startswith("```"):
            text = text[3:].strip()
        if text.endswith("```"):
            text = text[:-3].strip()
        return text

    def looks_like_digest(text: str) -> bool:
        title_ok = "AI 热点" in text or "AI热点" in text or "今日 AI" in text or "今日AI" in text
        outro_ok = "## 收尾" in text or "## 今日总结与展望" in text or "## 总结" in text
        structure_ok = "## 今日概览" in text and outro_ok
        has_images = "![" in text and "images/" in text
        return title_ok and structure_ok and has_images

    last_error: Exception | None = None
    for provider in providers:
        try:
            rewritten = call_llm(
                build_rewrite_prompt(summary, manifest, draft_markdown),
                model=rewrite_model,
                provider=provider,
            )
            rewritten = normalize_rewritten_markdown(rewritten)
            if not looks_like_digest(rewritten):
                continue
            return rewritten.strip() + "\n", f"llm:{provider}"
        except Exception as exc:
            last_error = exc

    if rewrite_mode == "api" and last_error is not None:
        raise last_error
    return draft_markdown, "heuristic"


def build_item_story(item: dict, translation_cache: dict[str, str]) -> list[str]:
    title_zh = translate_text(item["title"], translation_cache) or item["title"]

    # 优先使用AI生成的摘要
    ai_summary = item.get("ai_summary", "")
    if ai_summary and ai_summary != "与AI无关":
        summary_zh = ai_summary
    else:
        summary_text = item.get("description") or item.get("preview") or item["title"]
        summary_zh = translate_text(first_sentence(summary_text), translation_cache) or strip_markdown(summary_text)

    lead = f"这条消息来自 {item['source_label']}。{summary_zh}"
    theme = derive_theme(item)
    source_hint = ""
    if item.get("duplicate_count", 0) > 0:
        companion_sources = [name for name in item.get("related_sources", []) if name != item["source_label"]]
        if companion_sources:
            source_hint = f" 同一事件还出现在 {', '.join(companion_sources)} 的报道里，说明这不是单点快讯，而是值得持续跟进的行业信号。"
    second = THEME_COMMENTARY.get(theme, THEME_COMMENTARY["行业动态"]) + source_hint
    lines = [
        f"## 🔹 {item['global_index']}. {title_zh}",
        "",
        f"**来源**：{item['source_label']}",
    ]
    if item.get("duplicate_count", 0) > 0:
        companion_sources = [name for name in item.get("related_sources", []) if name != item["source_label"]]
        if companion_sources:
            lines.append(f"**同事件补充来源**：{', '.join(companion_sources)}")
    lines.extend(
        [
            "",
            lead,
            "",
            second,
            "",
            f"*原文：[{item['source_label']}]({item['source_url']})*",
            "",
            "---",
            "",
        ]
    )
    return lines


def build_digest_outro(manifest: list[dict]) -> list[str]:
    if not manifest:
        return []
    themes = {}
    for item in manifest:
        theme = derive_theme(item)
        themes[theme] = themes.get(theme, 0) + 1
    ordered = sorted(themes.items(), key=lambda pair: pair[1], reverse=True)
    theme_text = "、".join(theme for theme, _ in ordered[:3])
    return [
        "## 收尾",
        "",
        f"如果把今天这些热点放在一起看，最值得继续跟的主线是：{theme_text}。",
        "更具体地说，后续可以优先盯住两类变化：一类是大平台把 AI 功能继续往真实入口里铺开，另一类是版权、合规和数据边界继续收紧后带来的新约束。",
        "",
    ]


def generate_daily_digest(
    output_dir: Path,
    manifest: list[dict],
    summary: dict,
    rewrite_mode: str,
    rewrite_model: str | None,
    rewrite_provider: str,
) -> tuple[Path, dict[str, str]]:
    path = output_dir / "00-今日AI热点速读.md"
    translation_cache: dict[str, str] = {}
    image_map, cover_path = prepare_digest_images(output_dir, manifest)
    draft_markdown = build_digest_markdown(manifest, summary, image_map, cover_path, translation_cache)
    final_markdown, mode_used = rewrite_digest_with_llm(
        manifest,
        summary,
        draft_markdown,
        rewrite_mode,
        rewrite_model,
        rewrite_provider,
    )
    path.write_text(final_markdown, encoding="utf-8")
    return path, {"cover_image_path": cover_path, "image_count": len(image_map), "rewrite_mode": mode_used}


def normalize_sources(source_csv: str | None) -> list[str]:
    if not source_csv:
        return DEFAULT_SOURCES  # 使用默认的高AI相关性源
    names = []
    for raw in source_csv.split(","):
        key = raw.strip().lower()
        if not key:
            continue
        key = ALIASES.get(key, key)
        if key not in SOURCE_MAP:
            raise ValueError(f"Unsupported source: {raw}")
        if key not in names:
            names.append(key)
    if not names:
        raise ValueError("No valid sources provided")
    return names


def run_source_fetch(source: str, limit: int, output_dir: Path) -> dict:
    config = SOURCE_MAP[source]
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = ["internal-fetch", source, f"--limit={limit}", f"--output-dir={output_dir}"]
    manifest_path = output_dir / "manifest.json"
    try:
        items = save_source_candidates(source, limit, output_dir)
    except Exception as exc:
        return {
            "source": source,
            "label": config["label"],
            "ok": False,
            "command": cmd,
            "returncode": 1,
            "stdout": "",
            "stderr": str(exc),
            "error": "internal fetch failed",
        }
    if not manifest_path.exists():
        return {
            "source": source,
            "label": config["label"],
            "ok": False,
            "command": cmd,
            "returncode": 1,
            "stdout": "",
            "stderr": "",
            "error": f"manifest.json not found under {output_dir}",
        }
    return {
        "source": source,
        "label": config["label"],
        "ok": True,
        "command": cmd,
        "count": len(items),
        "items": items,
        "dir": str(output_dir),
    }

def build_raw_manifest(source_results: list[dict]) -> list[dict]:
    manifest = []
    global_index = 1
    for result in source_results:
        if not result.get("ok"):
            continue
        for item in result.get("items", []):
            manifest.append(
                {
                    "global_index": global_index,
                    "source": result["source"],
                    "source_label": result["label"],
                    "source_index": item.get("index"),
                    "title": item.get("title", ""),
                    "source_url": item.get("source_url", ""),
                    "author": item.get("author", ""),
                    "published_time": item.get("published_time", ""),
                    "description": item.get("description", ""),
                    "dir": item.get("dir", ""),
                    "content_md": item.get("content_md", ""),
                }
            )
            global_index += 1
    return manifest


def write_readme(output_dir: Path, manifest: list[dict], summary: dict) -> None:
    lines = [
        "# AI 热点候选总表",
        "",
        f"**日期**：{summary['date']}",
        f"**来源总数**：{summary['source_count']}",
        f"**原始候选总数**：{summary['raw_candidate_count']}",
        f"**去重后事件数**：{summary['candidate_count']}",
        f"**自动速读稿**：{summary['daily_digest_path']}",
        f"**速读稿封面**：{summary['daily_digest_cover_image']}",
        f"**速读稿图片数**：{summary['daily_digest_image_count']}",
        "",
        "## 来源统计",
        "",
    ]
    for item in summary["sources"]:
        status = "OK" if item["ok"] else "FAILED"
        lines.append(f"- `{item['source']}` / {item['label']}：{status}，候选 {item.get('count', 0)}")
        if not item["ok"] and item.get("error"):
            lines.append(f"  错误：{item['error']}")
    lines.append("")
    lines.append("## 去重后候选列表")
    lines.append("")
    for item in manifest:
        lines.append(f"### {item['global_index']}. [{item['source_label']}] {item['title']}")
        lines.append(f"- 原文：{item['source_url']}")
        if item.get("author"):
            lines.append(f"- 作者：{item['author']}")
        if item.get("published_time"):
            lines.append(f"- 发布时间：{item['published_time']}")
        if item.get("duplicate_count", 0) > 0:
            lines.append(f"- 同事件补充来源：{', '.join(name for name in item.get('related_sources', []) if name != item['source_label'])}")
        lines.append(f"- 本地目录：{item['dir']}")
        lines.append(f"- 正文：{item['content_md']}")
        lines.append("")
    (output_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate AI hotspot candidates from multiple source skills.")
    parser.add_argument("--sources", help="Comma-separated sources: techcrunch,the-verge,hn,github-trending,engadget,fast-company")
    parser.add_argument("--limit-per-source", type=int, default=3, help="How many candidates to fetch per source.")
    parser.add_argument("--output-dir", default=str(default_output_dir()), help="Where to store the aggregated review queue.")
    parser.add_argument("--keep-duplicates", action="store_true", help="Skip automatic same-event deduplication.")
    parser.add_argument("--skip-digest", action="store_true", help="Do not auto-generate the daily digest draft.")
    parser.add_argument("--rewrite-mode", choices=["auto", "off", "api"], default="auto", help="How to rewrite the daily digest: auto uses LLM when configured, off uses heuristic text, api requires LLM success.")
    parser.add_argument("--rewrite-provider", choices=["auto", "openai", "gemini"], default="auto", help="Which provider to use for daily digest rewrite. auto prefers Gemini when configured, then OpenAI.")
    parser.add_argument("--rewrite-model", help="Override the rewrite model for the daily digest.")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on the first source failure.")

    # 新增参数：AI相关性过滤和LLM增强
    parser.add_argument("--enable-llm", action="store_true", default=True, help="Enable LLM for AI relevance scoring and summary generation (default: True).")
    parser.add_argument("--disable-llm", action="store_true", help="Disable LLM for faster processing.")
    parser.add_argument("--llm-provider", choices=["auto", "openai", "gemini"], default="gemini", help="Which LLM provider to use for AI scoring and summary.")
    parser.add_argument("--ai-relevance-threshold", type=float, default=4.0, help="Minimum AI relevance score (0-10) to include in results (default: 4.0). Set to 0 to include all.")
    parser.add_argument("--max-candidates", type=int, default=20, help="Maximum number of candidates to keep after AI filtering (default: 20).")

    args = parser.parse_args()

    # 如果用户明确禁用LLM
    if args.disable_llm:
        args.enable_llm = False

    try:
        sources = normalize_sources(args.sources)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        sys.exit(1)

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    source_results = []
    for source in sources:
        source_dir = output_dir / source
        result = run_source_fetch(source, args.limit_per_source, source_dir)
        source_results.append(result)
        if args.fail_fast and not result.get("ok"):
            print(json.dumps({"ok": False, "results": source_results}, ensure_ascii=False, indent=2))
            sys.exit(1)

    raw_manifest = build_raw_manifest(source_results)
    all_candidates, deduped_manifest = cluster_events(
        raw_manifest,
        enable_llm=args.enable_llm,
        llm_provider=args.llm_provider
    )
    raw_manifest = raw_manifest
    deduped_manifest = deduped_manifest

    # AI相关性过滤
    if args.enable_llm and args.ai_relevance_threshold > 0:
        print(f"\n[filter] Applying AI relevance filter (threshold: {args.ai_relevance_threshold}/10)...")
        before_count = len(deduped_manifest)
        filtered_manifest = [
            item for item in deduped_manifest
            if item.get("ai_relevance_score", 0.0) >= args.ai_relevance_threshold
        ]
        after_count = len(filtered_manifest)
        removed_count = before_count - after_count

        print(f"[filter] Kept {after_count} candidates (removed {removed_count} low-AI-relevance items)")

        # 显示被过滤掉的低分项目
        if removed_count > 0:
            low_score_items = [
                item for item in deduped_manifest
                if item.get("ai_relevance_score", 0.0) < args.ai_relevance_threshold
            ]
            print(f"[filter] Top 5 removed items (AI score < {args.ai_relevance_threshold}):")
            for item in low_score_items[:5]:
                title = item.get("title", "")[:60]
                ai_score = item.get("ai_relevance_score", 0.0)
                print(f"  - [{ai_score:.1f}/10] {title}...")

        deduped_manifest = filtered_manifest

        # 限制最大数量
        if args.max_candidates and len(deduped_manifest) > args.max_candidates:
            # 按质量分数排序并保留前N个
            deduped_manifest = sorted(
                deduped_manifest,
                key=lambda x: x.get("quality_score", 0),
                reverse=True
            )[:args.max_candidates]
            print(f"[filter] Limited to top {args.max_candidates} candidates by quality score")

    manifest = raw_manifest if args.keep_duplicates else deduped_manifest
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "all_candidates.json").write_text(json.dumps(all_candidates, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "source_count": len(sources),
        "raw_candidate_count": len(raw_manifest),
        "candidate_count": len(manifest),
        "sources": [
            {
                "source": item["source"],
                "label": item["label"],
                "ok": item["ok"],
                "count": item.get("count", 0),
                "dir": item.get("dir", ""),
                "error": item.get("error", ""),
            }
            for item in source_results
        ],
    }

    digest_path = None
    digest_assets = {"cover_image_path": "", "image_count": 0, "rewrite_mode": "none"}
    if not args.skip_digest:
        digest_source = deduped_manifest if not args.keep_duplicates else raw_manifest
        digest_path, digest_assets = generate_daily_digest(
            output_dir,
            digest_source,
            summary,
            rewrite_mode=args.rewrite_mode,
            rewrite_model=args.rewrite_model,
            rewrite_provider=args.rewrite_provider,
        )
    summary["daily_digest_path"] = str(digest_path) if digest_path else ""
    summary["daily_digest_cover_image"] = digest_assets["cover_image_path"]
    summary["daily_digest_image_count"] = digest_assets["image_count"]
    summary["daily_digest_rewrite_mode"] = digest_assets["rewrite_mode"]

    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_readme(output_dir, manifest, summary)

    payload = {
        "ok": True,
        "output_dir": str(output_dir),
        "raw_candidate_count": len(raw_manifest),
        "candidate_count": len(manifest),
        "source_results": summary["sources"],
        "manifest_path": str(output_dir / "manifest.json"),
        "all_candidates_path": str(output_dir / "all_candidates.json"),
        "summary_path": str(output_dir / "summary.json"),
        "daily_digest_path": summary["daily_digest_path"],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
