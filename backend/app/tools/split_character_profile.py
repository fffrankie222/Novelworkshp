"""
角色档案拆分脚本 — split_character_profile.py

读取 char-designer 输出的完整 PROFILE.json（14 组字段结构化 JSON），
自动拆分为 7 个子文件，方便 chapter-writer 按需引用：

- SOUL.md     — 组4（精神内核）
- GOALS.md    — 组1+组4+组6（目标与动机）
- STYLE.md    — 组5+组11+组12（外在表现与语言）
- TRAUMA.md   — 组3+组7（创伤与禁忌）
- RELATIONS.md — 组10（社交模式与关系）
- DECISIONS.md — 组8+组9（决策逻辑）
- ARC.md      — 组14（成长弧线与OOC红线）

每个子文件使用 Markdown 格式，包含字段名和值。
同时生成可读的 PROFILE.md 汇总文件。
"""
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# 子文件 → 字段组映射关系
FILE_FIELD_MAP = {
    "SOUL.md": {
        "title": "精神内核",
        "description": "角色的灵魂目标、隐秘欲望与核心价值观",
        "groups": ["group_4_soul"],
    },
    "GOALS.md": {
        "title": "目标与动机",
        "description": "角色的身份定位、内在驱动力与利益诉求",
        "groups": ["group_1_identity", "group_4_soul", "group_6_interest"],
    },
    "STYLE.md": {
        "title": "外在表现与语言",
        "description": "角色的外貌特征、行为习惯与说话方式",
        "groups": ["group_5_exterior", "group_11_speech", "group_12_micro"],
    },
    "TRAUMA.md": {
        "title": "创伤与禁忌",
        "description": "角色的根源创伤、内在矛盾与伪装机制",
        "groups": ["group_3_origin", "group_7_conflict"],
    },
    "RELATIONS.md": {
        "title": "社交模式与关系",
        "description": "角色的社交态度分层与他人印象",
        "groups": ["group_10_social"],
    },
    "DECISIONS.md": {
        "title": "决策逻辑",
        "description": "角色的思维风格、决策规则与情绪应激反应",
        "groups": ["group_8_thinking", "group_9_emotion"],
    },
    "ARC.md": {
        "title": "成长弧线",
        "description": "角色的成长轨迹与 OOC 红线",
        "groups": ["group_14_arc"],
    },
}

# 字段中文名映射（用于 Markdown 可读性）
FIELD_LABELS = {
    # 组1 基础身份
    "core_identity": "核心身份",
    "faction_position": "势力位置",
    "story_role": "故事角色",
    "social_title": "社会称谓",
    # 组2 世界观
    "world_rule_fit": "世界规则契合",
    "rule_view": "规则态度",
    "plot_restriction": "剧情限制",
    # 组3 根源
    "background_imprint": "成长烙印",
    "trauma_scar": "创伤伤疤",
    "taboo_topics": "禁忌话题",
    # 组4 精神内核
    "soul_goal": "灵魂目标",
    "hidden_desire": "隐秘欲望",
    "values": "价值观评分",
    # 组5 外在
    "appearance_feature": "外貌特征",
    "habit_action": "习惯动作",
    # 组6 利益
    "interest_claim": "利益诉求",
    "trade_principle": "交易原则",
    # 组7 矛盾
    "inner_conflict": "内在冲突",
    "private_self": "私密自我",
    "disguise_switch": "伪装切换",
    # 组8 思维
    "thinking_style": "思维风格",
    "decision_rules": "决策规则",
    "reward_logic": "奖励逻辑",
    # 组9 情绪
    "emotion_model": "情绪模式",
    "fear_triggers": "恐惧触发",
    "stress_response": "压力反应",
    "anger_style": "愤怒风格",
    # 组10 社交
    "carry_style": "分层态度",
    "others_impression": "他人印象",
    # 组11 语言
    "speech_style": "说话风格",
    "cadence": "语节奏",
    "signature_phrases": "标志性口头禅",
    # 组12 语言微特征
    "sentence_openers": "惯用句式开头",
    "forbidden_fillers": "禁用填充词",
    # 组13 能力
    "ability_ceiling": "能力天花板",
    "critical_weakness": "致命短板",
    "growth_potential": "成长潜力",
    # 组14 弧线
    "arc_trajectory": "成长轨迹",
    "ooc_red_lines": "OOC红线",
}


def _format_value(value) -> str:
    """将字段值格式化为可读的 Markdown 文本"""
    if value is None:
        return "_（未设定）_"
    if isinstance(value, dict):
        lines = []
        for k, v in value.items():
            lines.append(f"  - **{k}**: {v}")
        return "\n".join(lines)
    if isinstance(value, list):
        if not value:
            return "_（无）_"
        return "\n".join(f"  - {item}" for item in value)
    return str(value)


def _render_group_md(group_data: dict) -> str:
    """将一组字段渲染为 Markdown 文本"""
    lines = []
    for field_key, value in group_data.items():
        label = FIELD_LABELS.get(field_key, field_key)
        formatted = _format_value(value)
        lines.append(f"- **{label}** (`{field_key}`): {formatted}")
    return "\n".join(lines)


def split_character_profile(
    workspace_path: str,
    profile_json_path: Optional[str] = None,
) -> dict:
    """
    读取 PROFILE.json 并拆分为 7 个子文件 + 1 个汇总 PROFILE.md。

    Args:
        workspace_path: 书籍工作区路径
        profile_json_path: PROFILE.json 的相对路径，默认 "characters/PROFILE.json"

    Returns:
        {
            "summary": "拆分完成描述",
            "output_files": ["characters/SOUL.md", ...],
            "characters": ["角色名1", ...],
        }
    """
    ws = Path(workspace_path)
    chars_dir = ws / "characters"
    chars_dir.mkdir(parents=True, exist_ok=True)

    # 定位 PROFILE.json
    if profile_json_path:
        json_file = ws / profile_json_path
    else:
        json_file = chars_dir / "PROFILE.json"

    if not json_file.exists():
        logger.warning(f"PROFILE.json 不存在: {json_file}")
        return {
            "summary": f"PROFILE.json 不存在: {json_file}",
            "output_files": [],
            "characters": [],
        }

    # 读取 JSON
    with open(json_file, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # 兼容：如果 JSON 顶层就是单个角色（没有以角色名为 key）
    # 检测方式：如果存在 group_1_identity 等字段，说明是单角色
    if "group_1_identity" in raw_data or "group_4_soul" in raw_data:
        # 单角色格式，包装为多角色
        char_name = raw_data.get("name", raw_data.get("core_identity", "主角"))
        profile_data = {char_name: raw_data}
    else:
        profile_data = raw_data

    output_files = []
    character_names = list(profile_data.keys())

    # 为每个角色生成 7 个子文件
    for char_name, char_data in profile_data.items():
        for filename, file_spec in FILE_FIELD_MAP.items():
            md_lines = [
                f"# {char_name} — {file_spec['title']}",
                "",
                f"> {file_spec['description']}",
                "",
            ]

            for group_key in file_spec["groups"]:
                group_data = char_data.get(group_key, {})
                if group_data:
                    # 从 group_key 推断组号用于标题
                    group_num = group_key.split("_")[0].replace("group", "组")
                    group_title_map = {
                        "group_1_identity": "基础身份定位",
                        "group_2_world": "世界观绑定",
                        "group_3_origin": "根源底层",
                        "group_4_soul": "精神内核",
                        "group_5_exterior": "外在具象",
                        "group_6_interest": "利益与资源逻辑",
                        "group_7_conflict": "内在矛盾",
                        "group_8_thinking": "思维与决策",
                        "group_9_emotion": "情绪与应激",
                        "group_10_social": "社交模式",
                        "group_11_speech": "语言表达",
                        "group_12_micro": "语言微特征",
                        "group_13_ability": "能力与短板",
                        "group_14_arc": "成长弧线",
                    }
                    group_title = group_title_map.get(group_key, group_key)
                    md_lines.append(f"## {group_title}")
                    md_lines.append("")
                    md_lines.append(_render_group_md(group_data))
                    md_lines.append("")

            # 写入子文件
            # 如果有多个角色，使用角色名作为子目录
            if len(character_names) > 1:
                char_dir = chars_dir / char_name
                char_dir.mkdir(parents=True, exist_ok=True)
                out_path = char_dir / filename
            else:
                out_path = chars_dir / filename

            out_path.write_text("\n".join(md_lines), encoding="utf-8")
            rel_path = str(out_path.relative_to(ws))
            output_files.append(rel_path)
            logger.info(f"已生成: {rel_path}")

    # 生成汇总 PROFILE.md
    profile_md = _generate_profile_md(profile_data)
    profile_md_path = chars_dir / "PROFILE.md"
    profile_md_path.write_text(profile_md, encoding="utf-8")
    output_files.append(str(profile_md_path.relative_to(ws)))
    logger.info(f"已生成汇总: {profile_md_path.relative_to(ws)}")

    return {
        "summary": f"角色档案拆分完成：{len(character_names)} 个角色，{len(output_files)} 个文件",
        "output_files": output_files,
        "characters": character_names,
    }


def _generate_profile_md(profile_data: dict) -> str:
    """
    生成可读的汇总 PROFILE.md 文件。
    包含所有角色的全部 14 组字段。
    """
    lines = [
        "# 角色档案总览",
        "",
        f"> 共 {len(profile_data)} 个角色，覆盖 14 组字段",
        "",
    ]

    for char_name, char_data in profile_data.items():
        lines.append(f"---")
        lines.append(f"## {char_name}")
        lines.append("")

        group_title_map = {
            "group_1_identity": "基础身份定位",
            "group_2_world": "世界观绑定",
            "group_3_origin": "根源底层",
            "group_4_soul": "精神内核",
            "group_5_exterior": "外在具象人设",
            "group_6_interest": "利益与资源逻辑",
            "group_7_conflict": "内在矛盾",
            "group_8_thinking": "思维与决策",
            "group_9_emotion": "情绪与应激",
            "group_10_social": "社交模式",
            "group_11_speech": "语言表达",
            "group_12_micro": "语言微特征",
            "group_13_ability": "能力与短板",
            "group_14_arc": "成长弧线",
        }

        for group_key, group_title in group_title_map.items():
            group_data = char_data.get(group_key, {})
            if group_data:
                lines.append(f"### {group_title}")
                lines.append("")
                lines.append(_render_group_md(group_data))
                lines.append("")

    return "\n".join(lines)


# 命令行入口（便于独立调试）
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python split_character_profile.py <workspace_path> [profile_json_path]")
        sys.exit(1)
    ws_path = sys.argv[1]
    json_path = sys.argv[2] if len(sys.argv) > 2 else None
    result = split_character_profile(ws_path, json_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
