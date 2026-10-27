"""
风格分析工具 — 从参考文本提取风格特征
对应 PRD Phase 4 的风格克隆功能（基础版）
"""
import json
import logging
import re
from pathlib import Path
from collections import Counter

logger = logging.getLogger(__name__)


def analyze_style(reference_texts: list[str]) -> dict:
    """
    从参考文本中提取风格特征。
    
    Args:
        reference_texts: 参考文本列表
    Returns:
        风格特征字典
    """
    all_text = "\n".join(reference_texts)
    
    # 基础统计分析
    style = {
        "avg_sentence_length": _avg_sentence_length(all_text),
        "sentence_length_variance": _sentence_length_variance(all_text),
        "dialogue_ratio": _dialogue_ratio(all_text),
        "paragraph_count": len([p for p in all_text.split("\n\n") if p.strip()]),
        "common_punctuation": _common_punctuation(all_text),
        "narrative_pov_guess": _guess_pov(all_text),
        "sensory_density": _sensory_density(all_text),
        "action_to_description_ratio": _action_desc_ratio(all_text),
    }
    
    return style


def _avg_sentence_length(text: str) -> float:
    """平均句长"""
    sentences = re.split(r"[。！？.!?]", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return 0
    return sum(len(s) for s in sentences) / len(sentences)


def _sentence_length_variance(text: str) -> float:
    """句长方差（衡量节奏变化）"""
    sentences = re.split(r"[。！？.!?]", text)
    sentences = [len(s.strip()) for s in sentences if s.strip()]
    if len(sentences) < 2:
        return 0
    mean = sum(sentences) / len(sentences)
    variance = sum((x - mean) ** 2 for x in sentences) / len(sentences)
    return variance


def _dialogue_ratio(text: str) -> float:
    """对话占比"""
    dialogue_chars = 0
    in_dialogue = False
    for char in text:
        if char in "\u201c":  # "
            in_dialogue = True
        elif char in "\u201d":  # "
            in_dialogue = False
        elif in_dialogue:
            dialogue_chars += 1
    
    total = len(text.replace("\n", "").replace(" ", ""))
    return dialogue_chars / total if total > 0 else 0


def _common_punctuation(text: str) -> list[str]:
    """常用标点统计"""
    puncts = re.findall(r"[，。！？、；：""''—…·]", text)
    counter = Counter(puncts)
    return [p for p, _ in counter.most_common(5)]


def _guess_pov(text: str) -> str:
    """猜测叙事视角"""
    first_person = len(re.findall(r"我", text))
    third_person = len(re.findall(r"他|她", text))
    
    if first_person > third_person * 2:
        return "first_person"
    elif third_person > first_person:
        return "third_person_limited"
    else:
        return "uncertain"


def _sensory_density(text: str) -> float:
    """感官描写密度（每千字）"""
    sensory_words = re.findall(
        r"看见|听到|闻到|触摸|尝到|感觉|明亮|昏暗|喧嚣|寂静|芬芳|恶臭|"
        r"柔软|坚硬|温热|冰冷|甘甜|苦涩|刺眼|朦胧|清脆|沉闷",
        text
    )
    total_chars = len(text)
    return len(sensory_words) / (total_chars / 1000) if total_chars > 0 else 0


def _action_desc_ratio(text: str) -> float:
    """动作描写与场景描写的比例"""
    action_words = len(re.findall(r"挥|砍|冲|跑|跳|踢|打|抓|推|拉|闪|躲|攻击|防御", text))
    desc_words = len(re.findall(r"巍峨|广袤|幽深|璀璨|磅礴|朦胧|缭绕|绵延|苍茫", text))
    
    if desc_words == 0:
        return 10.0  # 全是动作
    return action_words / desc_words
