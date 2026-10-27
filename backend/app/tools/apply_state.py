"""
状态更新脚本 — 读取 delta JSON，幂等更新 truth files
对应 PRD §十二 的 Reflector Delta 输出格式
"""
import json
import logging
import time
from pathlib import Path

from app.tools.file_ops import read_json, write_json

logger = logging.getLogger(__name__)


def apply_state_update(
    workspace_path: str,
    chapter_number: int,
    delta: dict,
) -> dict:
    """
    将 Reflector 生成的 delta 应用到 truth files。
    
    delta 格式：
    {
        "deltas": {
            "character_states": [...],
            "world_state": [...],
            "hook_updates": [...],
            "timeline_events": [...]
        }
    }
    
    幂等性保证：
    - inventory_add/remove: 检查是否已存在
    - hook_updates.upsert: 按 hook_id 去重
    - timeline_events: 按 event_id 去重
    """
    ws = Path(workspace_path)
    ch_id = f"chapter-{chapter_number:04d}"
    applied_log = []
    
    deltas = delta.get("deltas", delta)  # 兼容两种格式
    
    # ===== 更新角色状态 =====
    char_states_path = ws / "state" / "character_states.json"
    char_states = read_json(str(char_states_path)) or {"characters": {}}
    
    for cs in deltas.get("character_states", []):
        char_name = cs.get("character", "")
        updates = cs.get("updates", {})
        
        if char_name not in char_states["characters"]:
            char_states["characters"][char_name] = {"last_updated": ch_id}
        
        state = char_states["characters"][char_name]
        
        # 直接覆盖的字段
        for key in ["location", "cultivation_level", "hp", "emotional_state"]:
            if key in updates:
                state[key] = updates[key]
                applied_log.append(f"角色 {char_name}.{key} = {updates[key]}")
        
        # 列表型字段 — 幂等添加
        for key in ["inventory", "known_secrets"]:
            add_key = f"{key}_add"
            remove_key = f"{key}_remove"
            
            if key not in state:
                state[key] = []
            
            # 添加（幂等）
            for item in updates.get(add_key, []):
                if item not in state[key]:
                    state[key].append(item)
                    applied_log.append(f"角色 {char_name}.{key} 添加: {item}")
            
            # 移除
            for item in updates.get(remove_key, []):
                if item in state[key]:
                    state[key].remove(item)
                    applied_log.append(f"角色 {char_name}.{key} 移除: {item}")
        
        # 关系更新
        if "relationships" in updates:
            if "relationships" not in state:
                state["relationships"] = {}
            state["relationships"].update(updates["relationships"])
        
        state["last_updated"] = ch_id
    
    # 写回角色状态
    char_states_path.parent.mkdir(parents=True, exist_ok=True)
    char_states_path.write_text(
        json.dumps(char_states, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    
    # ===== 更新世界状态 =====
    world_state_path = ws / "state" / "world_state.json"
    world_state = read_json(str(world_state_path)) or {"faction_relations": {}, "active_events": [], "last_updated": ""}
    
    for ws_update in deltas.get("world_state", []):
        field = ws_update.get("field", "")
        update_data = ws_update.get("update", {})
        reason = ws_update.get("reason", "")
        
        if field in world_state:
            if isinstance(world_state[field], dict):
                world_state[field].update(update_data)
            elif isinstance(world_state[field], list):
                world_state[field].extend(update_data)
            applied_log.append(f"世界状态 {field} 更新: {reason}")
    
    world_state["last_updated"] = ch_id
    world_state_path.write_text(
        json.dumps(world_state, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    
    # ===== 更新伏笔（v4.0: 统一存储到 outline.json.foreshadowing） =====
    outline_path = ws / "outline" / "outline.json"
    outline_data = read_json(str(outline_path)) or {}
    foreshadowing = outline_data.get("foreshadowing", [])

    existing_hooks = {h["id"]: i for i, h in enumerate(foreshadowing)}

    for hook_update in deltas.get("hook_updates", []):
        hook_id = hook_update.get("hook_id", "")
        action = hook_update.get("action", "")

        if action == "advance":
            if hook_id in existing_hooks:
                hook = foreshadowing[existing_hooks[hook_id]]
                if hook.get("status") == "planted":
                    hook["status"] = "active"
                applied_log.append(f"伏笔 {hook_id} 推进")

        elif action == "upsert":
            if hook_id in existing_hooks:
                # 更新已有伏笔
                hook = foreshadowing[existing_hooks[hook_id]]
                for key in ["description", "status", "purpose", "characters"]:
                    if key in hook_update:
                        hook[key] = hook_update[key]
            else:
                # 新建伏笔
                new_hook = {
                    "id": hook_id,
                    "purpose": hook_update.get("description", hook_update.get("purpose", "")),
                    "description": hook_update.get("description", ""),
                    "start_chapter": hook_update.get("start_chapter", 0),
                    "end_chapter": hook_update.get("end_chapter", 0),
                    "characters": hook_update.get("characters", []),
                    "status": hook_update.get("status", "planted"),
                }
                foreshadowing.append(new_hook)
                existing_hooks[hook_id] = len(foreshadowing) - 1
            applied_log.append(f"伏笔 {hook_id} upsert")

        elif action == "resolve":
            if hook_id in existing_hooks:
                foreshadowing[existing_hooks[hook_id]]["status"] = "resolved"
                applied_log.append(f"伏笔 {hook_id} 已回收")

    outline_data["foreshadowing"] = foreshadowing
    write_json(str(outline_path), outline_data)
    
    # ===== 更新时间线 =====
    timeline_path = ws / "timeline" / "timeline.json"
    timeline = read_json(str(timeline_path)) or {"events": [], "time_system": {}}
    
    existing_events = {e["id"] for e in timeline.get("events", [])}
    
    for event in deltas.get("timeline_events", []):
        evt_id = event.get("id", f"evt_{len(timeline['events']) + 1:03d}")
        if evt_id not in existing_events:
            event["id"] = evt_id
            event.setdefault("chapter", ch_id)
            timeline["events"].append(event)
            existing_events.add(evt_id)
            applied_log.append(f"时间线事件 {evt_id} 添加")
    
    timeline_path.write_text(
        json.dumps(timeline, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    
    # ===== 写入应用日志 =====
    runtime_dir = ws / "runtime" / ch_id
    runtime_dir.mkdir(parents=True, exist_ok=True)
    log_path = runtime_dir / "state_applied.json"
    log_path.write_text(
        json.dumps({
            "chapter": ch_id,
            "applied_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "changes": applied_log,
            "total_changes": len(applied_log),
        }, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    
    logger.info(f"状态更新应用完成: {len(applied_log)} 项变更")
    
    return {
        "summary": f"状态更新完成: {len(applied_log)} 项变更",
        "changes": applied_log,
    }
