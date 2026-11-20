#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
workout_builder — 实战验证的 Garmin Connect 训练课表构建器
Battle-tested Garmin workout builder (running + strength + push lifecycle).

来源 / Origin: 2026-11-20 HYROX 三日课表实战（跑课 pace.zone + 力量课动作库 +
创建/验证/推送全流程），所有坑位均已实测踩过并验证解法。

核心经验 / Hard-won lessons (all field-tested):
  1. 重复组 RepeatGroup：stepOrder 必须**全局递增**，组内子步骤 childStepId
     必须指向组的 stepOrder（=组的 childStepId），否则服务器只保留最后一个子步骤。
  2. 跑课配速 pace.zone：targetType=6，targetValueOne=快端(m/s) 必须 **大于**
     targetValueTwo=慢端；步骤内**不得带 zoneNumber/targetValueUnit**（会被服务器
     静默置空），且必须带 strokeType/equipmentType 空对象。6:00/km=2.77778。
  3. 力量课 strength_training：每个动作步骤必须带 `category` + `exerciseName`
     （取自 garminconnect.exercises 动作库），否则是残缺的「运动」步骤——
     web 编辑器红色校验「必须选择运动」，手表上步骤显示为空。
     动作步 endCondition 用 reps（conditionTypeId 10）；静力动作（平板等）
     可用 time（conditionTypeId 2，已验证 PLANK 40″ 可过）。
  4. 非跑步内容不要放进 running 课表的 interval 步——手表会显示为跑步段。
     混合日拆成两份课表：running（只留跑步）+ strength（动作库步骤）；
     或把替代练习放进 running 课表的 rest 步（手表显示为休息，可接受）。
  5. 推送生命周期：PUT update 后再 push 可能返回 []（空列表）且手表拿不到新版。
     **可靠做法是 delete_workout + 重新 create + push**（推送状态必返回 "new"）。
  6. 创建后必须 GET 回读验证字段存活（尤其 pace 值、重复组子步骤数量），
     验证通过再推表。

用法 / Usage:
  - 作为库导入：`from workout_builder import WorkoutBuilder, replace_workout`
  - 作为 MCP 工具的底层引擎：garmin_cn_mcp.py 的 smart_create_workout /
    replace_workout / search_exercise 都基于本模块。
  - 命令行演示：`python workout_builder.py demo`（输出示例课表 JSON，不联网）
"""

from __future__ import annotations

import json
from typing import Any, Optional

# ─── 常量表（实测 ID） ────────────────────────────────────────────────

SPORT_TYPES = {
    "running": {"sportTypeId": 1, "sportTypeKey": "running", "displayOrder": 1},
    "strength_training": {"sportTypeId": 5, "sportTypeKey": "strength_training", "displayOrder": 3},
    "cardio_training": {"sportTypeId": 6, "sportTypeKey": "cardio_training", "displayOrder": 6},
    "hiit": {"sportTypeId": 9, "sportTypeKey": "hiit", "displayOrder": 9},
}

STEP_TYPES = {
    "warmup": 1,     # 热身
    "cooldown": 2,   # 放冷
    "interval": 3,   # 主动作
    "recovery": 4,   # 恢复
    "rest": 5,       # 休息
    "repeat": 6,     # 重复组
}

CONDITION_TYPES = {
    "lap.button": 1,
    "time": 2,        # endConditionValue=秒
    "distance": 3,    # endConditionValue=米
    "iterations": 7,  # 仅重复组
    "reps": 10,       # 力量次数
}

TARGET_TYPES = {
    "no.target": 1,
    "pace.zone": 6,
}

METER_UNIT = {"unitId": 1, "unitKey": "meter", "factor": 100.0}

# 力量目标负重：weightValue 按克存储（kg×1000），unitId 8 = kilogram（国行实测可用）
WEIGHT_UNIT_KILOGRAM = {"unitId": 8, "unitKey": "kilogram", "factor": 1000.0}

_EMPTY_STROKE = {"strokeTypeId": 0, "strokeTypeKey": None, "displayOrder": 0}
_EMPTY_EQUIPMENT = {"equipmentTypeId": 0, "equipmentTypeKey": None, "displayOrder": 0}


def pace_to_mps(pace_str: str) -> float:
    """配速字符串转 m/s。'6:00' → 2.7778；'6:30' → 2.5641。"""
    parts = pace_str.strip().split(":")
    if len(parts) == 2:
        m, s = int(parts[0]), int(parts[1])
    elif len(parts) == 1:
        m, s = 0, int(float(parts[0]))
    else:
        raise ValueError(f"无法解析配速: {pace_str}")
    total = m * 60 + s
    if total <= 0:
        raise ValueError(f"配速必须为正: {pace_str}")
    return round(1000.0 / total, 5)


def pace_range(fast_pace: str, slow_pace: str) -> tuple:
    """配速区间 → (targetValueOne, targetValueTwo)。快端在前。
    '6:00','6:15' → (2.77778, 2.66667)。内部校验 快端>慢端。"""
    one = pace_to_mps(fast_pace)
    two = pace_to_mps(slow_pace)
    if one <= two:
        raise ValueError(f"快端配速 {fast_pace} 必须快于慢端 {slow_pace}")
    return one, two


# ─── 动作库（strength 步骤必须使用库内 category/exerciseName） ─────────

_CATALOG: Optional[list] = None


def _get_catalog() -> list:
    """懒加载 garminconnect.exercises 动作目录 [(display, category, exercise), ...]。"""
    global _CATALOG
    if _CATALOG is None:
        try:
            from garminconnect import exercises as _ex
            _CATALOG = list(_ex._RAW)
        except Exception:
            _CATALOG = []
    return _CATALOG


# 常用动作速查（display, category, exercise）——2026-11-20 实测全部可通过服务器校验
COMMON_EXERCISES = {
    "plank":        ("PLANK", "PLANK"),
    "dead_bug":     ("HIP_STABILITY", "DEAD_BUG"),
    "bird_dog":     ("HIP_STABILITY", "QUADRUPED_HIP_EXTENSION"),
    "suspended_row": ("LATERAL_RAISE", "SUSPENDED_ROW"),
    "push_up":      ("PUSH_UP", "PUSH_UP"),
    "y_raise":      ("SHOULDER_STABILITY", "FLOOR_Y_RAISE"),
    "t_raise":      ("SHOULDER_STABILITY", "FLOOR_T_RAISE"),
    "w_raise":      ("SHOULDER_STABILITY", "INCLINE_W_RAISE"),
    "squat":        ("SQUAT", "SQUAT"),
    "lunge":        ("LUNGE", "LUNGE"),
}


def validate_exercise(category: str, exercise: str) -> bool:
    """校验 (category, exercise) 是否在 garminconnect 动作库内。
    动作库不可用时放行（返回 True）——由服务器端校验兜底。"""
    cat = _get_catalog()
    if not cat:
        return True
    return any(c == category and (e == exercise or not e) for _, c, e in cat)


def search_exercise(keyword: str, limit: int = 20) -> list:
    """按关键词搜动作库，返回 [{display, category, exercise}]。"""
    kw = keyword.upper()
    out = []
    for display, cat, ex in _get_catalog():
        if kw in display.upper() or kw in cat or kw in ex:
            out.append({"display": display, "category": cat, "exercise": ex})
            if len(out) >= limit:
                break
    return out


# ─── 构建器 ──────────────────────────────────────────────────────────

class WorkoutBuilder:
    """训练课表构建器。stepOrder 全局递增；repeat 组自动对齐 childStepId。"""

    def __init__(self, sport: str = "running"):
        if sport not in SPORT_TYPES:
            raise ValueError(f"未知 sport: {sport}，可选 {list(SPORT_TYPES)}")
        self.sport = SPORT_TYPES[sport]
        self._counter = 0
        self._steps: list = []

    # ---- 内部 ----

    def _base_step(self, order, step_type, desc, cond_key, cond_val,
                   target=None, v1=None, v2=None, unit=None,
                   category=None, exercise=None, child=None,
                   weight_kg=None) -> dict:
        tgt = target or {"workoutTargetTypeId": TARGET_TYPES["no.target"],
                         "workoutTargetTypeKey": "no.target", "displayOrder": 1}
        return {
            "type": "ExecutableStepDTO",
            "stepOrder": order,
            "stepType": {"stepTypeId": STEP_TYPES[step_type],
                         "stepTypeKey": step_type, "displayOrder": STEP_TYPES[step_type]},
            "childStepId": child,
            "description": desc,
            "endCondition": {"conditionTypeId": CONDITION_TYPES[cond_key],
                             "conditionTypeKey": cond_key,
                             "displayOrder": CONDITION_TYPES[cond_key],
                             "displayable": True},
            "endConditionValue": float(cond_val) if cond_val is not None else None,
            "preferredEndConditionUnit": unit,
            "endConditionCompare": None,
            "targetType": tgt,
            "targetValueOne": v1, "targetValueTwo": v2,
            "targetValueUnit": None, "zoneNumber": None,
            "secondaryTargetType": None, "secondaryTargetValueOne": None,
            "secondaryTargetValueTwo": None, "secondaryTargetValueUnit": None,
            "secondaryZoneNumber": None, "endConditionZone": None,
            "strokeType": _EMPTY_STROKE,
            "equipmentType": _EMPTY_EQUIPMENT,
            "category": category,
            "exerciseName": exercise,
            "workoutProvider": None,
            "providerExerciseSourceId": None,
            "weightValue": (float(weight_kg) * 1000.0) if weight_kg is not None else None,
            "weightUnit": dict(WEIGHT_UNIT_KILOGRAM) if weight_kg is not None else None,
        }

    def _next(self) -> int:
        self._counter += 1
        return self._counter

    def _validate_pace(self, pace):
        if pace is None:
            return None, None
        if isinstance(pace, (tuple, list)) and len(pace) == 2 and all(isinstance(x, str) for x in pace):
            one, two = pace_range(pace[0], pace[1])
        else:
            one, two = float(pace[0]), float(pace[1])
            if one <= two:
                raise ValueError(f"pace 快端 {one} 必须大于慢端 {two}")
        return one, two

    # ---- 步骤 API ----

    def warmup(self, desc: str, secs: int) -> "WorkoutBuilder":
        self._steps.append(self._base_step(self._next(), "warmup", desc, "time", secs))
        return self

    def cooldown(self, desc: str, secs: int) -> "WorkoutBuilder":
        self._steps.append(self._base_step(self._next(), "cooldown", desc, "time", secs))
        return self

    def rest(self, desc: str, secs: int) -> "WorkoutBuilder":
        self._steps.append(self._base_step(self._next(), "rest", desc, "time", secs))
        return self

    def run_time(self, desc: str, secs: int, pace=None, hrm=None) -> "WorkoutBuilder":
        """计时跑步。pace=("6:00","6:15") 快端在前；HR 约束写 desc。"""
        v1, v2 = self._validate_pace(pace)
        tgt = None
        if pace is not None:
            tgt = {"workoutTargetTypeId": TARGET_TYPES["pace.zone"],
                   "workoutTargetTypeKey": "pace.zone", "displayOrder": 6}
        self._steps.append(self._base_step(self._next(), "interval", desc, "time", secs,
                                           target=tgt, v1=v1, v2=v2))
        return self

    def run_distance(self, desc: str, meters: int, pace=None) -> "WorkoutBuilder":
        """计距跑步（间歇组常用）。"""
        v1, v2 = self._validate_pace(pace)
        tgt = None
        if pace is not None:
            tgt = {"workoutTargetTypeId": TARGET_TYPES["pace.zone"],
                   "workoutTargetTypeKey": "pace.zone", "displayOrder": 6}
        self._steps.append(self._base_step(self._next(), "interval", desc, "distance", meters,
                                           target=tgt, v1=v1, v2=v2, unit=METER_UNIT))
        return self

    def strength(self, desc: str, category: str, exercise: str,
                 reps: Optional[int] = None, secs: Optional[int] = None,
                 weight_kg: Optional[float] = None) -> "WorkoutBuilder":
        """力量动作步。次数用 reps=，静力（平板等）用 secs=，目标负重用 weight_kg=。
        一个动作步 = 一组；每组不同重量就每组一个步（递增组同理）。
        (category, exercise) 必须来自动作库，可用 search_exercise() 查。"""
        if not validate_exercise(category, exercise):
            raise ValueError(f"动作 ({category}, {exercise}) 不在动作库内，用 search_exercise() 查合法值")
        if (reps is None) == (secs is None):
            raise ValueError("strength 步必须且只能指定 reps 或 secs 之一")
        cond = ("reps", reps) if reps is not None else ("time", secs)
        self._steps.append(self._base_step(self._next(), "interval", desc, cond[0], cond[1],
                                           category=category, exercise=exercise,
                                           weight_kg=weight_kg))
        return self

    def repeat(self, iterations: int, children: list) -> dict:
        """重复组。children 为已构建的步骤 dict 列表（通常 2 个：动作 + 休息）。
        经验：组内子步骤 childStepId 必须指向本组的 stepOrder（=组的 childStepId）。"""
        if iterations < 1:
            raise ValueError("iterations 必须 ≥1")
        if not children:
            raise ValueError("repeat 组至少要有一个子步骤")
        order = self._next()
        cid = order  # 组的 childStepId 与自身 stepOrder 同值（实测可用）
        for c in children:
            c["childStepId"] = cid
        grp = {
            "type": "RepeatGroupDTO",
            "stepOrder": order,
            "stepType": {"stepTypeId": STEP_TYPES["repeat"],
                         "stepTypeKey": "repeat", "displayOrder": STEP_TYPES["repeat"]},
            "childStepId": cid,
            "numberOfIterations": iterations,
            "endCondition": {"conditionTypeId": CONDITION_TYPES["iterations"],
                             "conditionTypeKey": "iterations",
                             "displayOrder": CONDITION_TYPES["iterations"],
                             "displayable": False},
            "endConditionValue": float(iterations),
            "workoutSteps": children,
        }
        self._steps.append(grp)
        return grp

    # ---- 组合快捷方式 ----

    def repeat_run(self, iterations: int, work_desc: str, meters: int, pace,
                   rest_desc: str, rest_secs: int) -> "WorkoutBuilder":
        """经典跑课间歇组：跑 distance + 休息 time。"""
        wb = WorkoutBuilder(self.sport["sportTypeKey"])
        wb._counter = self._counter  # 共享全局计数器
        wb.run_distance(work_desc, meters, pace)
        wb.rest(rest_desc, rest_secs)
        self._counter = wb._counter
        children = wb._steps
        self.repeat(iterations, children)
        return self

    def repeat_strength(self, iterations: int, work_desc: str, category: str,
                        exercise: str, reps: Optional[int], rest_secs: int,
                        secs: Optional[int] = None, weight_kg: Optional[float] = None) -> "WorkoutBuilder":
        """经典力量组：动作（次数或静力秒数）+ 休息。weight_kg= 目标负重，组内统一。"""
        wb = WorkoutBuilder(self.sport["sportTypeKey"])
        wb._counter = self._counter
        wb.strength(work_desc, category, exercise, reps=reps, secs=secs, weight_kg=weight_kg)
        wb.rest(f"休息 {rest_secs}″，换下一组", rest_secs)
        self._counter = wb._counter
        self.repeat(iterations, wb._steps)
        return self

    def build(self, name: str, description: str = "") -> dict:
        """输出完整 workout payload（可直接交给 upload_workout / create_workout）。"""
        if not self._steps:
            raise ValueError("课表至少要有一个步骤")
        return {
            "workoutName": name,
            "description": description,
            "shared": False,
            "sportType": self.sport,
            "workoutSegments": [{"segmentOrder": 1, "sportType": self.sport,
                                 "workoutSteps": self._steps}],
        }


# ─── DSL：用 JSON 描述课表（供 MCP 工具使用） ─────────────────────────

def build_from_spec(spec: dict) -> dict:
    """从简化 spec 构建 workout payload。

    spec 结构：
    {
      "sport": "running" | "strength_training" | ...,
      "name": "11/21训练计划",
      "description": "可选",
      "steps": [
        ["warmup",   "热身5′", 300],
        ["cooldown", "放冷5′", 300],
        ["run_time", "极轻松跑25′ HR≤135", 1500, {"pace": ["7:30", "8:15"]}],
        ["run_dist", "站间跑400m", 400, {"pace": ["6:30", "6:50"]}],
        ["time",     "自由计时段", 900],
        ["rest",     "休息60″", 60],
        ["strength", "TRX划船 ×15", "LATERAL_RAISE", "SUSPENDED_ROW", 15],
        ["hold",     "平板 40″", "PLANK", "PLANK", 40],
        ["repeat",   6, [ ...同格式的子步骤（可嵌套）... ]]
      ]
    }
    """
    wb = WorkoutBuilder(spec.get("sport", "running"))

    def _add_single(b: "WorkoutBuilder", s: list) -> None:
        kind = s[0]
        if kind == "warmup":
            b.warmup(s[1], int(s[2]))
        elif kind == "cooldown":
            b.cooldown(s[1], int(s[2]))
        elif kind == "rest":
            b.rest(s[1], int(s[2]))
        elif kind == "time":
            b.run_time(s[1], int(s[2]))
        elif kind == "run_time":
            opts = s[3] if len(s) > 3 else {}
            b.run_time(s[1], int(s[2]), pace=opts.get("pace"))
        elif kind == "run_dist":
            opts = s[3] if len(s) > 3 else {}
            b.run_distance(s[1], int(s[2]), pace=opts.get("pace"))
        elif kind == "strength":
            opts = s[5] if len(s) > 5 else {}
            b.strength(s[1], s[2], s[3], reps=int(s[4]), weight_kg=opts.get("weight_kg"))
        elif kind == "hold":
            opts = s[5] if len(s) > 5 else {}
            b.strength(s[1], s[2], s[3], secs=int(s[4]), weight_kg=opts.get("weight_kg"))
        else:
            raise ValueError(f"未知步骤类型: {kind}")

    def _add(steps: list, b: "WorkoutBuilder") -> None:
        for s in steps:
            if s[0] == "repeat":
                iterations = int(s[1])
                # 子步骤先在独立 builder 里展开（共享全局计数器），再交给 repeat 对齐 childStepId
                sub_wb = WorkoutBuilder(b.sport["sportTypeKey"])
                sub_wb._counter = b._counter
                _add(s[2], sub_wb)
                b._counter = sub_wb._counter
                b.repeat(iterations, sub_wb._steps)
            else:
                _add_single(b, s)

    _add(spec["steps"], wb)
    return wb.build(spec["name"], spec.get("description", ""))


# ─── 生命周期：验证 / 创建 / 更新 / 替换 / 推送 ────────────────────────

def strip_ids(node):
    """递归去掉 stepId/workoutId（PUT 全量重写时必须）。"""
    if isinstance(node, dict):
        return {k: strip_ids(v) for k, v in node.items()
                if k not in ("stepId", "workoutId")}
    if isinstance(node, list):
        return [strip_ids(x) for x in node]
    return node


def verify_workout(api, workout_id: int) -> dict:
    """GET 回读验证。返回 {ok, issues, summary}。
    校验：重复组子步骤齐全、pace.zone 值未被置空、strength 步带动作名。"""
    w = api.get_workout_by_id(int(workout_id))
    issues, summary = [], []

    def walk(steps, depth=0):
        for s in steps:
            stype = (s.get("stepType") or {}).get("stepTypeKey")
            if s.get("type") == "RepeatGroupDTO":
                kids = s.get("workoutSteps") or []
                summary.append(f"REPEAT×{s.get('numberOfIterations')} kids={[k.get('stepType', {}).get('stepTypeKey') for k in kids]}")
                if len(kids) < 1:
                    issues.append("重复组无子步骤（stepOrder/childStepId 未对齐的典型症状）")
                walk(kids, depth + 1)
                continue
            desc = (s.get("description") or "")[:24]
            tt = (s.get("targetType") or {}).get("workoutTargetTypeKey")
            if tt == "pace.zone":
                one, two = s.get("targetValueOne"), s.get("targetValueTwo")
                summary.append(f"{stype} pace {one}/{two} | {desc}")
                if not one or not two:
                    issues.append(f"pace 值被服务器置空: {desc}")
                elif one <= two:
                    issues.append(f"pace 快端 ≤ 慢端: {desc}")
            else:
                summary.append(f"{stype} {(s.get('endCondition') or {}).get('conditionTypeKey')}={s.get('endConditionValue')} | {desc}")
            if s.get("stepType", {}).get("stepTypeId") == 3 and not s.get("category") \
               and (s.get("endCondition") or {}).get("conditionTypeKey") in ("reps",):
                issues.append(f"interval+reps 步缺 category/exerciseName（手表会显示为空）: {desc}")

    for seg in w.get("workoutSegments", []):
        walk(seg.get("workoutSteps") or [])
    return {"ok": not issues, "issues": issues, "summary": summary, "workoutId": w.get("workoutId")}


def create_and_push(api, payload: dict, device_id: Optional[int] = None) -> dict:
    """创建 → 回读验证 → 推送（验证不过则不推送）。"""
    created = api.upload_workout(payload)
    wid = (created or {}).get("workoutId")
    if not wid:
        raise RuntimeError(f"创建失败: {created}")
    verify = verify_workout(api, wid)
    if not verify["ok"]:
        api.delete_workout(wid)
        raise RuntimeError(f"回读验证未通过（已删除新建课表 {wid}）: {verify['issues']}")
    dev = device_id or api.get_device_last_used()["userDeviceId"]
    res = api.push_workout_to_device(workout_id=wid, device_id=dev)
    r0 = res[0] if isinstance(res, list) and res and isinstance(res[0], dict) else {}
    return {"workoutId": wid, "verify": verify,
            "push": {"status": r0.get("messageStatus"), "device": r0.get("deviceName"),
                     "raw": json.dumps(res, ensure_ascii=False, default=str)[:300]}}


def replace_workout(api, old_workout_id: int, payload: dict, device_id: Optional[int] = None) -> dict:
    """可靠更新：删除旧课表 → 重新创建 → 验证 → 推送。

    经验：PUT update 后 push 常返回 []（空列表）且手表可能拿不到新版；
    删旧建新的 push 必返回 messageStatus="new"，是唯一可靠的更新路径。
    """
    api.delete_workout(int(old_workout_id))
    return create_and_push(api, payload, device_id=device_id)


def update_workout(api, workout_id: int, payload: dict) -> dict:
    """PUT 全量重写（保留 workoutId）。注意：更新后需走 delete+recreate 才能可靠推到手表。"""
    clean = strip_ids(payload)
    api.update_workout(int(workout_id), clean)
    return verify_workout(api, workout_id)


# ─── CLI 演示 ─────────────────────────────────────────────────────────

def _demo() -> None:
    """三种课表模板示例（2026-11-20 HYROX 实战课表），只输出 JSON 不联网。"""
    # 1) 跑课：极轻松跑 + pace.zone
    run = (WorkoutBuilder("running")
           .warmup("热身10′：快走 + 动态拉伸", 600)
           .run_time("极轻松跑25′：走跑结合，HR ≤135", 1500, pace=("7:30", "8:15"))
           .cooldown("放冷5′：步行 + 滚轴", 300)
           .build("极轻松跑", "准备度低时的降级版跑课"))
    # 2) 跑课间歇：400m ×6 组间跑
    itv = (WorkoutBuilder("running")
           .warmup("热身10′", 600)
           .repeat_run(6, "站间跑400m @6:30–6:50", 400, ("6:30", "6:50"),
                       "站替代循环约4′：波比20/TRX划船20/弓步20/农夫走50m", 240)
           .cooldown("放冷10′", 600)
           .build("流程间歇课", "Hyrox 站间跑模拟"))
    # 3) 力量课：动作库步骤
    trx = (WorkoutBuilder("strength_training")
           .warmup("热身3′：肩绕环 + 徒手激活", 180)
           .repeat_strength(3, "TRX划船 ×15：身体一条直线", *COMMON_EXERCISES["suspended_row"], 15, 60)
           .repeat_strength(3, "俯卧撑 ×12", *COMMON_EXERCISES["push_up"], 12, 60)
           .repeat_strength(3, "平板 40″", *COMMON_EXERCISES["plank"], None, 30, secs=40)
           .cooldown("放松3′：肩胸背拉伸", 180)
           .build("TRX上肢", "力量课示例：全部动作来自 Garmin 动作库"))
    print(json.dumps({"running": run, "interval": itv, "strength": trx},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        _demo()
    else:
        print(__doc__)
