#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Garmin Connect China MCP Server (read + write)
通过 MCP 协议读取并写入佳明中国大陆版 (garmin.cn) 的健康、运动与训练数据。

Read & write Garmin China (garmin.cn) health, activity and training data via MCP.
Built on the official `garminconnect` library with `is_cn=True`.

依赖 / Dependencies:
  - mcp
  - garminconnect>=0.3.11

登录凭据从环境变量读取（由 .env 或 MCP 客户端 env 注入）：
  - GARMIN_CN_EMAIL
  - GARMIN_CN_PASSWORD
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from garminconnect import Garmin


def _load_dotenv():
    """Load environment variables from a local .env file (no extra dependency).

    从本地 .env 文件加载环境变量（无需额外依赖）。已存在的 os.environ 不会被覆盖。
    """
    for cand in (Path(__file__).resolve().parent / ".env", Path.cwd() / ".env"):
        if cand.is_file():
            try:
                for line in cand.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    key, val = key.strip(), val.strip().strip('"').strip("'")
                    os.environ.setdefault(key, val)
            except Exception:
                pass
            break


_load_dotenv()

mcp = FastMCP(
    "garmin-cn",
    instructions="佳明中国大陆版数据读取与训练写入服务。基于官方 garminconnect 库连接 garmin.cn，支持读取运动/睡眠/HRV/训练状态，以及创建、排程、推送训练。",
)

_api = None


def _get_api() -> Garmin:
    global _api
    if _api is not None:
        return _api

    email = os.environ.get("GARMIN_CN_EMAIL") or os.environ.get("GARMIN_EMAIL")
    password = os.environ.get("GARMIN_CN_PASSWORD") or os.environ.get("GARMIN_PASSWORD")
    if not email or not password:
        raise RuntimeError(
            "缺少 Garmin 凭据。请在 .env 或 MCP 客户端 env 中配置 GARMIN_CN_EMAIL 和 GARMIN_CN_PASSWORD。"
        )

    api = Garmin(email=email, password=password, is_cn=True, return_on_mfa=True)
    api.login()
    # return_on_mfa=True 时 login() 会提前 return、跳过 _load_profile_and_settings()，
    # 导致 display_name 为 None → 睡眠/静息心率等接口报 "Display name is not set"。
    # 此账号无 MFA，这里补一次 profile 加载即可修复。
    if getattr(api, "display_name", None) is None:
        try:
            api._load_profile_and_settings()
        except Exception:
            pass
    _api = api
    return api


def _dump(data) -> str:
    def conv(obj):
        if isinstance(obj, dict):
            return {k: conv(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [conv(v) for v in obj]
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, "__dict__"):
            return conv(obj.__dict__)
        return obj

    try:
        return json.dumps(conv(data), ensure_ascii=False, indent=2, default=str)
    except TypeError:
        return json.dumps(str(data), ensure_ascii=False)


def _safe(fn):
    try:
        return fn()
    except Exception as e:
        return json.dumps({"error": type(e).__name__, "message": str(e)[:500]}, ensure_ascii=False)


# ─── 运动 Activities ────────────────────────────────────────────────


@mcp.tool()
def get_last_activities(limit: int = 10) -> str:
    """获取最近的运动记录列表（跑步/骑行/划船/HIIT 等）。

    Args:
        limit: 返回数量，默认10，最大50。
    """
    limit = max(1, min(int(limit), 50))
    return _safe(lambda: _dump(_get_api().get_activities(0, limit)))


@mcp.tool()
def get_activities_by_date(start: str = "", end: str = "", activity_type: str = "") -> str:
    """按日期范围获取运动记录。

    Args:
        start: 开始日期 YYYY-MM-DD，默认7天前。
        end: 结束日期 YYYY-MM-DD，默认今天。
        activity_type: 可选运动类型过滤，如 running、cycling、strength_training。
    """
    end = end or datetime.now().strftime("%Y-%m-%d")
    start = start or (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    return _safe(
        lambda: _dump(
            _get_api().get_activities_by_date(
                startdate=start, enddate=end, activitytype=activity_type or None
            )
        )
    )


@mcp.tool()
def get_activity_details(activity_id: str) -> str:
    """获取单个运动的详细数据。

    Args:
        activity_id: 运动ID（从 get_last_activities 获取）。
    """
    return _safe(lambda: _dump(_get_api().get_activity_details(str(activity_id))))


@mcp.tool()
def get_activity_splits(activity_id: str) -> str:
    """获取运动的分段数据（每公里/每段配速），用于分析跑步节奏。

    Args:
        activity_id: 运动ID。
    """
    return _safe(lambda: _dump(_get_api().get_activity_splits(str(activity_id))))


@mcp.tool()
def get_last_activity() -> str:
    """获取最近一次运动记录。"""
    return _safe(lambda: _dump(_get_api().get_last_activity()))


# ─── 训练与健康 Training & Health ──────────────────────────────────


@mcp.tool()
def get_training_status(date: str = "") -> str:
    """获取训练状态（训练负荷、恢复、VO2 Max 等）。

    Args:
        date: 日期 YYYY-MM-DD，默认今天。
    """
    date = date or datetime.now().strftime("%Y-%m-%d")
    return _safe(lambda: _dump(_get_api().get_training_status(date)))


@mcp.tool()
def get_morning_training_readiness(date: str = "") -> str:
    """获取今日/指定日的晨间训练准备度。

    Args:
        date: 日期 YYYY-MM-DD，默认今天。
    """
    date = date or datetime.now().strftime("%Y-%m-%d")
    return _safe(lambda: _dump(_get_api().get_morning_training_readiness(date)))


@mcp.tool()
def get_sleep_data(date: str = "") -> str:
    """获取某天睡眠数据（时长、深睡/浅睡/REM、睡眠得分等）。

    Args:
        date: 日期 YYYY-MM-DD，默认昨天。
    """
    date = date or (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    return _safe(lambda: _dump(_get_api().get_sleep_data(date)))


@mcp.tool()
def get_hrv_data(date: str = "") -> str:
    """获取某天 HRV（心率变异性）。

    Args:
        date: 日期 YYYY-MM-DD，默认昨天。
    """
    date = date or (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    return _safe(lambda: _dump(_get_api().get_hrv_data(date)))


# ─── 资料与设备 Profile & Devices ──────────────────────────────────


@mcp.tool()
def get_devices() -> str:
    """获取已绑定的 Garmin 设备列表。"""
    return _safe(lambda: _dump(_get_api().get_devices()))


@mcp.tool()
def get_user_profile() -> str:
    """获取用户资料信息（含 displayName 等）。"""
    return _safe(lambda: _dump(_get_api().get_user_profile()))


# ─── 训练库与写入 Workouts (read + write) ─────────────────────────


@mcp.tool()
def get_workouts(limit: int = 50) -> str:
    """获取训练库中的自定义训练列表。"""
    return _safe(lambda: _dump(_get_api().get_workouts(0, max(1, int(limit)))))


@mcp.tool()
def create_workout(workout_json: str = "") -> str:
    """在 Garmin Connect 创建自定义引导训练（进入训练库）。

    Args:
        workout_json: 训练定义的 JSON 字符串。结构参考 garminconnect.workout：
            {
              "workoutName": "...",
              "sportType": {"sportTypeId": 6, "sportTypeKey": "cardio_training", "displayOrder": 6},
              "estimatedDurationInSecs": 1200,
              "workoutSegments": [
                {"segmentOrder": 0, "sportType": {同 sportType},
                 "workoutSteps": [ {训步DIO} ]}
              ]
            }
            训步 stepTypeKey: "main"(主动作) / "rest"(休息)；
            结束条件 endConditionKey: "lap.button"(手动按LAP) / "time"(秒, 配 endConditionValue) / "distance"(米)；
            返回体含 workoutId。
    """
    payload = json.loads(workout_json or "{}")
    return _safe(lambda: _dump(_get_api().upload_workout(payload)))


@mcp.tool()
def schedule_workout(workout_id: str, date: str = "") -> str:
    """把训练排程到指定日期（手表当天在训练日历可见）。

    Args:
        workout_id: 训练ID（create_workout 返回的 workoutId，或 get_workouts 获取）。
        date: 目标日期 YYYY-MM-DD，默认明天。
    """
    date = date or (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    return _safe(lambda: _dump(_get_api().schedule_workout(int(workout_id), date)))


@mcp.tool()
def push_workout_to_device(workout_id: str = "", device_id: str = "") -> str:
    """把训练FIT立即推送到手表（不等同步）。

    Args:
        workout_id: 训练ID；为空则推送训练库最新的一个。
        device_id: 设备ID；为空则推送到最近使用设备。
    """
    def run():
        kwargs = {}
        if workout_id:
            kwargs["workout_id"] = int(workout_id)
        if device_id:
            kwargs["device_id"] = int(device_id)
        return _get_api().push_workout_to_device(**kwargs)

    return _safe(lambda: _dump(run()))


if __name__ == "__main__":
    mcp.run(transport="stdio")
