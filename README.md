# Garmin Connect China MCP Server

**佳明中国大陆版（garmin.cn）MCP 数据读取与训练写入服务**

A Model Context Protocol (MCP) server that lets AI assistants (Claude, CodeBuddy, or any MCP client) **read and write** your Garmin **China** (garmin.cn) health, activity and training data — including <span style="background-color:#ffff00; font-weight:bold;">creating, scheduling and pushing workouts to your devices</span>.

通过 MCP 协议，让 AI 助手（Claude、WorkBuddy 及任意 MCP 客户端）**读取并写入**你的佳明中国大陆版（garmin.cn）健康、运动与训练数据——包括<span style="background-color:#ffff00; font-weight:bold;">创建、排程、推送训练到设备</span>。

> 📖 **新手保姆级教程 / Beginner step-by-step tutorial**: [WorkBuddy傻瓜教程.md](WorkBuddy傻瓜教程.md) — 从装 Python 到接入 WorkBuddy，全程点哪里抄哪里，零基础可用。

---

## ✨ Features / 功能

| Category 类别      | Tool 工具                          | 说明                  | Description                       |
| ---------------- | -------------------------------- | ------------------- | --------------------------------- |
| 🏃 Activity 运动   | `get_last_activities`            | 最近运动列表              | Recent activities                 |
|                  | `get_activities_by_date`         | 按日期查运动              | Activities within a date range    |
|                  | `get_activity_details`           | 运动详细数据              | Activity data (laps, HR, etc.)    |
|                  | `get_activity_splits`            | 每公里/每段配速            | Per-km / per-segment splits       |
|                  | `get_last_activity`              | 最近一次运动              | Most recent activity              |
| 📊 Training 训练   | `get_training_status`            | 训练状态 / VO2 Max      | Training status / VO2 Max         |
|                  | `get_morning_training_readiness` | 晨间训练准备度             | Morning training readiness        |
| 💤 Sleep 睡眠      | `get_sleep_data`                 | 睡眠数据 / 得分 / 阶段      | Sleep data / score / stages       |
| ❤️ HRV           | `get_hrv_data`                   | 心率变异性               | Heart-rate variability            |
| 👤 Profile 资料    | `get_devices`                    | 设备列表                | Paired devices                    |
|                  | `get_user_profile`               | 用户资料（含 displayName） | User profile (incl. displayName)  |
| 🏋️ Workouts 训练库 | `get_workouts`                   | 训练库列表               | List workouts in library          |
|                  | `create_workout`                 | **创建训练（进训练库）**      | **Create workout (into library)** |
|                  | `schedule_workout`               | **排程到指定日期**         | **Schedule workout to a date**    |
|                  | `push_workout_to_device`         | **推送到手表**           | **Push workout to device**        |

> Read **and** write. Creating / scheduling / pushing workouts requires a valid Garmin China account.  
> 既**可读也可写**。创建 / 排程 / 推送训练需要有效的佳明国行账号。

---

## 🤔 Why this exists / 为什么需要这个

The Garmin China (`garmin.cn`) API architecture is different from the international (`garmin.com`) one, but the official `garminconnect` Python library **does** support China via the `is_cn=True` flag.

佳明中国版（`garmin.cn`）的 API 架构与国际版（`garmin.com`）不同，但官方 `garminconnect` Python 库通过 `is_cn=True` 参数**确实支持**中国版。

- This server is built on `garminconnect` with `is_cn=True`, so it can both **read** health/activity data **and write** (create / schedule / push workouts).  
  本服务基于 `garminconnect` 库 + `is_cn=True`，因此既能**读取**健康/运动数据，也能**写入**（创建 / 排程 / 推送训练）。
- `is_cn=True` connects to `connect.garmin.cn`. A small CN-specific quirk (the `display_name` not loading when login skips MFA) is handled by re-loading the profile once after login.  
  `is_cn=True` 连接到 `connect.garmin.cn`。国行有个小坑（跳过 MFA 登录后 `display_name` 不加载），本服务在登录后补一次 profile 加载即可修复。
- *Alternative approach / 替代方案*: a reverse-engineered `/gc-api/` proxy (using `curl_cffi` Chrome TLS fingerprint) can reach more read-only China endpoints and stays independent of the library — useful if you only need broad read coverage. This published server chooses `garminconnect` for simplicity and built-in write support.  
  *替代方案*：逆向的 `/gc-api/` 代理（用 `curl_cffi` 的 Chrome TLS 指纹）能覆盖更多**只读**国行接口、且不依赖该库——若你只需要广度只读覆盖会更合适。本仓库选择 `garminconnect`，因为它简单且自带写能力。

---

## 📦 Installation / 安装

```bash
# Clone the repo / 克隆仓库
git clone https://github.com/<your-username>/garmin-cn-mcp.git
cd garmin-cn-mcp

# (Optional) Create a virtual environment / 可选：创建虚拟环境
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies / 安装依赖
pip install -r requirements.txt
```

---

## ⚙️ Configuration / 配置

You have **two** ways to provide your Garmin China credentials. **Never commit real credentials.**

提供佳明国行账号凭据有**两种**方式。**切勿提交真实凭据。**

### Option A — `.env` file（推荐 / recommended）

Copy the template and fill in your account:

复制模板并填入账号：

```bash
cp .env.example .env
# then edit .env with your GARMIN_CN_EMAIL and GARMIN_CN_PASSWORD
```

The server auto-loads `.env` on startup (no extra dependency). `.env` is git-ignored.  
服务启动时自动加载 `.env`（无需额外依赖），且 `.env` 已被 git 忽略。

### Option B — MCP client `env` block

Point your MCP client at this server. Copy `.mcp.json.example` → `.mcp.json` (git-ignored) and set the absolute path + credentials:

在 MCP 客户端配置中指向本服务。复制 `.mcp.json.example` 为 `.mcp.json`（已被 git 忽略），填上绝对路径与凭据：

```json
{
  "mcpServers": {
    "garmin-cn": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["/absolute/path/to/garmin_cn_mcp.py"],
      "env": {
        "GARMIN_CN_EMAIL": "your-garmin-email@example.com",
        "GARMIN_CN_PASSWORD": "your-password"
      }
    }
  }
}
```

> Tip: if you already use `.env`, the `env` block above can be omitted — the server reads `.env` automatically.  
> 提示：若已使用 `.env`，上面的 `env` 块可省略，服务会自动读取 `.env`。

---

## 💡 Usage / 使用示例

### Natural language / 自然语言

Once configured, ask your AI assistant naturally:

配置好后，直接用自然语言向 AI 助手提问：

- "我昨天睡得怎么样？" / *"How did I sleep yesterday?"*
- "最近一周的运动记录" / *"My workouts in the last week"*
- "今天的 HRV 和压力数据" / *"Today's HRV and stress"*
- "给我建一个周三的滑雪机 8×250m 间歇课，排到 2026-11-05，并推到手表" / *"Build a ski-erg 8×250m interval workout for Wed, schedule it to 2026-11-05 and push to my watch"*

### Calling tools directly / 直接调用工具

Each tool is exposed over MCP (stdio). The AI client picks the right tool automatically, but you can also call them explicitly. Below is the parameter cheat-sheet:

每个工具都通过 MCP（stdio）暴露。AI 客户端会自动选用合适的工具，你也可以显式调用。参数速查表如下：

| Tool 工具                          | Parameters 参数                                 | Default 默认值 |
| -------------------------------- | --------------------------------------------- | ----------- |
| `get_last_activities`            | `limit:int` (≤50)                             | `10`        |
| `get_activities_by_date`         | `start:date`, `end:date`, `activity_type:str` | 7 天前, 今天, 空 |
| `get_activity_details`           | `activity_id:str`                             | —           |
| `get_activity_splits`            | `activity_id:str`                             | —           |
| `get_last_activity`              | —                                             | —           |
| `get_training_status`            | `date:str` (YYYY-MM-DD)                       | 今天          |
| `get_morning_training_readiness` | `date:str` (YYYY-MM-DD)                       | 今天          |
| `get_sleep_data`                 | `date:str` (YYYY-MM-DD)                       | 昨天          |
| `get_hrv_data`                   | `date:str` (YYYY-MM-DD)                       | 昨天          |
| `get_devices`                    | —                                             | —           |
| `get_user_profile`               | —                                             | —           |
| `get_workouts`                   | `limit:int`                                   | `50`        |
| `create_workout`                 | `workout_json:str` (JSON)                     | —           |
| `schedule_workout`               | `workout_id:str`, `date:str`                  | —, 明天       |
| `push_workout_to_device`         | `workout_id:str`, `device_id:str`             | 空, 最近设备     |

### Write workflow / 写入流程（建训练计划）

A "training plan" on Garmin is a set of workouts scheduled on the calendar. The typical flow is:

佳明的"训练计划"本质上是一组排到日历上的训练。典型流程：

1. **`create_workout(workout_json)`** → returns `workoutId` (the workout enters your Garmin workout library).  
   **`create_workout(workout_json)`** → 返回 `workoutId`（训练进入佳明训练库）。
2. **`schedule_workout(workout_id, date)`** → the workout shows on your watch's training calendar that day.  
   **`schedule_workout(workout_id, date)`** → 该训练当天出现在手表训练日历。
3. **`push_workout_to_device(workout_id, device_id)`** → push the FIT file to the watch immediately (no wait for sync).  
   **`push_workout_to_device(workout_id, device_id)`** → 立即把 FIT 推到手表（不等同步）。

**Example / 示例** — a simple HIIT workout (ski-erg intervals) built and scheduled:

**示例** — 一个简单的 HIIT 训练（滑雪机间歇）创建并排程：

```json
{
  "workoutName": "滑雪机 8×250m",
  "sportType": {"sportTypeId": 9, "sportTypeKey": "hiit", "displayOrder": 9},
  "estimatedDurationInSecs": 1800,
  "workoutSegments": [
    {"segmentOrder": 0, "sportType": {"sportTypeId": 9, "sportTypeKey": "hiit", "displayOrder": 9},
     "workoutSteps": [
       {"stepOrder": 1, "type": "ExecutableStepDTO",
        "stepType": {"stepTypeId": 8, "stepTypeKey": "main", "displayOrder": 8},
        "endCondition": {"conditionTypeId": 1, "conditionTypeKey": "lap.button", "displayOrder": 1, "displayable": true},
        "targetType": {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target", "displayOrder": 1},
        "description": "滑雪机 250m 计时"},
       {"stepOrder": 2, "type": "ExecutableStepDTO",
        "stepType": {"stepTypeId": 5, "stepTypeKey": "rest", "displayOrder": 5},
        "endCondition": {"conditionTypeId": 2, "conditionTypeKey": "time", "displayOrder": 2, "displayable": true},
        "endConditionValue": 90.0,
        "targetType": {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target", "displayOrder": 1},
        "description": "休息 90s"}
     ]}
  ],
  "description": "示例：滑雪机 250m ×8，间休 90s",
  "author": {}
}
```

> `stepTypeKey`: `main` (active step) / `rest` (rest). `endConditionKey`: `lap.button` (press LAP to finish) / `time` (seconds, with `endConditionValue`) / `distance` (meters). The returned object contains `workoutId`.  
> `stepTypeKey`：`main`（主动作）/`rest`（休息）。`endConditionKey`：`lap.button`（手动按 LAP 结束）/`time`（秒，配 `endConditionValue`）/`distance`（米）。返回体含 `workoutId`。

### Client integration / 客户端接入

This is a **stdio** MCP server. Merge the `garmin-cn` block (from Option B above) into your client's MCP config:

这是一个 **stdio** 类型的 MCP 服务。把上面的 `garmin-cn` 配置块合并进你所用客户端的 MCP 配置即可：

- **Claude Desktop**: `claude_desktop_config.json`
- **WorkBuddy / Cursor / VS Code**: its `mcp.json` / MCP settings
- **Any MCP client**: add the block under `mcpServers`

Restart the client after editing. The server starts on first tool call.  
修改后重启客户端。服务在首次调用工具时启动。

---

## 🔧 Technical Details / 技术细节

### How it works / 工作原理

- Built on the official `garminconnect` library with `is_cn=True` → connects to `connect.garmin.cn`.  
  基于官方 `garminconnect` 库 + `is_cn=True` → 连接 `connect.garmin.cn`。
- Auth: `Garmin(email, password, is_cn=True, return_on_mfa=True).login()`.  
  认证：`Garmin(email, password, is_cn=True, return_on_mfa=True).login()`。
- `display_name` fix: if `display_name` is `None` after login (a CN quirk when MFA is skipped), the server calls the library's internal `_load_profile_and_settings()` once to avoid "Display name is not set" errors on some endpoints.  
  `display_name` 修复：登录后若为 `None`（跳过 MFA 时的国行坑），服务补调一次库内部的 `_load_profile_and_settings()`，避免部分接口报 "Display name is not set"。
- Session handling (re-login on expiry) is managed by the library.  
  会话管理（过期重登）由库负责。

### Write endpoints / 写接口

| Action 动作           | Tool 工具                  | Library method 库方法                   |
| ------------------- | ------------------------ | ------------------------------------ |
| Create workout 创建训练 | `create_workout`         | `upload_workout(payload)`            |
| Schedule 排程         | `schedule_workout`       | `schedule_workout(workout_id, date)` |
| Push to device 推送   | `push_workout_to_device` | `push_workout_to_device(...)`        |
| List library 训练库    | `get_workouts`           | `get_workouts(start, limit)`         |


### Return fields overview / 返回字段概览

Each tool returns the **raw JSON** from Garmin China (via `garminconnect`). Below are the **typical** key fields (names/availability vary by device & account; the server does no post-processing).

每个工具返回的是佳明国行的**原始 JSON**（经 `garminconnect`）。下列为**常见**字段（具体字段名/有无取决于设备与账号；服务不二次归一化）。

| Tool 工具                                                                | Typical key fields 常见字段                                                                                                                                                                     |
| ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `get_last_activities` / `get_activities_by_date` / `get_last_activity` | `activityId`, `activityName`, `activityType` (`typeKey`), `startTimeLocal`, `duration`, `distance`, `calories`, `averageHR`, `maxHR`                                                        |
| `get_activity_details`                                                 | `clockDetails` (laps), `heartRateValues`, `geoCoordinateDTOList`, `metrics`                                                                                                                 |
| `get_activity_splits`                                                  | `splits` (per-km: `distance`, `duration`, `pace`, `averageHR`)                                                                                                                              |
| `get_training_status`                                                  | `trainingStatus`, `trainingLoad`, `recoveryTime`, `vo2Max`, `acuteLoad`, `chronicLoad`                                                                                                      |
| `get_morning_training_readiness`                                       | `trainingReadiness`, `hrvStatus`, `recoveryTime`, `sleepScore`, `recoveryScore`                                                                                                             |
| `get_sleep_data`                                                       | `sleepTimeSeconds`, `deepSleepSeconds`, `lightSleepSeconds`, `remSleepSeconds`, `awakeSleepSeconds`, `sleepScore`, `sleepQualityType`, `averageHeartRate`, `sleepStartTime`, `sleepEndTime` |
| `get_hrv_data`                                                         | `hrvValue` (latest), `status`, `weeklyAverage`, `lastNightAverage`                                                                                                                          |
| `get_devices`                                                          | `deviceId`, `nickname`, `manufacturer`, `modelName`, `serialNumber`, `softwareVersion`, `lastPaired`                                                                                        |
| `get_user_profile`                                                     | `displayName`, `fullName`, `profileImageUrlSmall/Large`, `userId`, `location`                                                                                                               |
| `get_workouts`                                                         | `workoutId`, `workoutName`, `sportType`, `estimatedDurationInSecs`, `updatedDate`                                                                                                           |
| `create_workout` (returns)                                             | `workoutId`, `workoutName`                                                                                                                                                                  |
| `schedule_workout` (returns)                                           | `workoutScheduleId`, `workoutId`, `date`                                                                                                                                                    |
| `push_workout_to_device` (returns)                                     | push confirmation / status                                                                                                                                                                  |

---

## ⚠️ Limitations / 已知限制

- **Depends on `garminconnect` / 依赖 garminconnect 库**：This server relies on the official library's CN support (`is_cn=True`). If a future library version breaks China access, this server is affected — a `/gc-api/` reverse-engineered variant would be needed instead.  
  本服务依赖官方库的国行支持（`is_cn=True`）。若未来库版本破坏国行访问，本服务会受影响——届时需改用逆向 `/gc-api/` 方案。
- **No MFA flow beyond `return_on_mfa=True` / 仅支持 `return_on_mfa=True`**：The account is assumed to have **no MFA** (the `display_name` workaround covers that case). Accounts with active MFA may need additional handling.  
  假设账号**无 MFA**（上面的 `display_name` 修复覆盖了该情形）。开启 MFA 的账号可能需要额外处理。
- **Fields not normalized / 字段未归一化**：Returns are the **raw** `garminconnect` JSON; field names and availability vary by device & account, and the server does no post-processing.  
  返回的是**原始** `garminconnect` JSON，字段名与有无随设备、账号而异，服务不做二次加工。
- **No plan-level API / 无"计划级"接口**：Garmin has no single "create training plan" endpoint — a plan is built by creating individual workouts and scheduling them (see Write workflow). This server exposes the per-workout primitives.  
  佳明没有单一的"创建训练计划"接口——计划由"逐个创建训练 + 排程"构成（见写入流程）。本服务提供的是单训练粒度的原语。

---

## 📋 Dependencies / 依赖

- Python 3.10+
- `mcp` (MCP SDK)
- `garminconnect` (official Garmin library, `is_cn=True` for China)

---

## 📄 License / 许可证

[MIT License](LICENSE) — free for personal and commercial use.  
[MIT 许可证](LICENSE) — 个人与商业使用均免费。

> ⚠️ **Disclaimer / 免责声明**: This tool accesses your own Garmin China (`garmin.cn`) account via the unofficial `garminconnect` library. Use is subject to Garmin's Terms of Service; the author is not responsible for any ToS violation, account suspension, or misuse arising from use of this software.  
> ⚠️ **免责声明**：本工具通过非官方的 `garminconnect` 库访问你**自己的**佳明国行（`garmin.cn`）账号。使用须遵守 Garmin 服务条款；作者不对任何因使用本软件导致的服务条款违约、账号封禁或滥用承担责任。
