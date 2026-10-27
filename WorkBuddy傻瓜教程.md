# 🧑‍🏫 WorkBuddy 傻瓜教程：3 分钟让 AI 读你的佳明国行数据

> 适用对象：**完全没碰过命令行/GitHub 的普通用户**，Windows 电脑 + WorkBuddy。
> 保姆级程度：每一步告诉你「打开哪个网页、点哪个按钮、抄哪段字」。
> Mac 用户可参考，界面与路径略有不同，本教程以 Windows 为准。

---

## ✅ 开始前确认 3 件事

| 需要什么 | 说明 |
|---|---|
| WorkBuddy 已安装并登录 | 就是你在用的这个 AI 助手 |
| **佳明国行账号** | 中国大陆版佳明（能在 `connect.garmin.cn` 网页登录的账号），记住它的邮箱和密码 |
| Windows 电脑 | 能装软件、能上网 |

---

## 第 1 步：安装 Python（装过的直接跳到第 2 步）

1. 打开网址：**https://www.python.org/downloads/**
2. 点页面中间的**黄色大按钮**下载（比如 `Python 3.13.x`）。
3. 双击下载的安装包，在**第一屏**务必做一件事：
   - ☑️ 勾选窗口**最底部**的 **`Add python.exe to PATH`**
   - （不勾它后面必出问题！）
4. 点 **Install Now**，等进度条走完，点 Close。
5. 验证 + 记路径（第 4 步要用）：
   1. 按键盘 `Win + R`，输入 `cmd`，回车，打开黑色命令窗口。
   2. 输入 `python --version` 回车 → 显示 `Python 3.13.x` 就是装好了。
   3. 再输入 `where python` 回车 → 会打印一行路径（例如 `C:\Users\Jin\AppData\Local\Programs\Python\Python313\python.exe`）。
   4. **把这行路径复制到记事本存着**，第 4 步要粘贴。

> ❗ 如果显示「python 不是内部或外部命令」：说明第 3 步没勾那个框，卸载重装再勾上。

---

## 第 2 步：下载项目文件（不用会 GitHub）

1. 浏览器打开这个网址（国内网络可直接下载）：

   ```
   https://gh-proxy.com/https://codeload.github.com/BabeeJin/garmin-cn-mcp/zip/refs/heads/main
   ```

   > 如果你能正常上 GitHub，也可以用官方直链：
   > `https://github.com/BabeeJin/garmin-cn-mcp/archive/refs/heads/main.zip`

2. 会下载得到一个 `garmin-cn-mcp-main.zip`（约 20KB）。
3. 右键这个压缩包 → **全部解压** → 建议解压到 **`D:\garmin-cn-mcp`**。

> ⚠️ 注意：解压位置以后**不要移动、不要删除**——WorkBuddy 每次调用都会从这个文件夹启动服务。别放桌面随手清理的地方。

4. 打开解压后的文件夹，确认里面有这两个文件：
   - `garmin_cn_mcp.py`
   - `requirements.txt`

---

## 第 3 步：装依赖（复制粘贴一行命令）

1. 打开解压后的文件夹（如 `D:\garmin-cn-mcp`）。
2. 点击文件夹顶部的**地址栏**，输入 `cmd` 后按回车——会在当前文件夹打开黑色命令窗口。
3. 复制下面这一整行，粘贴到窗口里，回车：

   ```
   pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
   ```

4. 等它自动下载安装（约 1 分钟）。结束时**没有红色 ERROR 字样**就是成功（黄色 WARNING 不用管）。

> 这行命令用了**阿里云镜像源**（国内下载快、对 `mcp` 等包索引最稳）。装的是两个库：`mcp`（连接 WorkBuddy 用，已在 `requirements.txt` 锁定 **1.x 版本**）和 `garminconnect`（连佳明用）。
>
> ⚠️ **版本红线**：本项目只用 **mcp 1.x**。`requirements.txt` 已写死 `mcp>=1.0.0,<2`——**千万不要手动装 `mcp 2.x`**，否则启动会报 `ModuleNotFoundError: No module named 'mcp.server.fastmcp'`。万一装错，重跑 `pip install "mcp>=1.0.0,<2"` 降到 1.x 即可。
>
> 如果提示「找不到某个包的版本 / Could not find a version」，把上面命令里的镜像换成清华源再试：`-i https://pypi.tuna.tsinghua.edu.cn/simple`。

---

## 第 4 步：接入 WorkBuddy（核心步骤，照抄模板）

### 4.1 打开 WorkBuddy 的 MCP 配置文件

- 打开 WorkBuddy → 左下角 **＋（添加连接器）** → 找到 **「自定义 MCP / mcp.json」** 入口编辑配置。
- 如果找不到入口，也可以直接用记事本打开这个文件：
  ```
  C:\Users\你的Windows用户名\.workbuddy\mcp.json
  ```

### 4.2 照抄下面这段，只改 3 个地方

在 `mcpServers` 花括号里加入（如果文件里已有其他服务，注意在前面服务后补一个英文逗号 `,`）：

```json
{
  "mcpServers": {
    "garmin-cn": {
      "command": "C:\\Users\\你的Windows用户名\\AppData\\Local\\Programs\\Python\\Python313\\python.exe",
      "args": ["D:\\garmin-cn-mcp\\garmin_cn_mcp.py"],
      "env": {
        "GARMIN_CN_EMAIL": "你的佳明国行邮箱",
        "GARMIN_CN_PASSWORD": "你的佳明密码"
      }
    }
  }
}
```

**只需要改 3 个地方：**

| 改哪里 | 改成什么 | 注意 |
|---|---|---|
| `command` | 第 1 步第 5 点记下的 Python 路径 | 路径里的 `\` 必须写成 **`\\`**（两个斜杠） |
| `args` | `garmin_cn_mcp.py` 的完整位置（如 `D:\\garmin-cn-mcp\\garmin_cn_mcp.py`） | 同样用 `\\` |
| `env` 两行 | 你的佳明国行邮箱 + 密码 | 用英文双引号包住，别加多余空格 |

### 4.3 保存并启用

1. 保存 `mcp.json` 文件。
2. 回到 WorkBuddy 的连接器管理页面，找到新出现的 **garmin-cn** → 点**「信任 / 启用」**。
3. **完全退出 WorkBuddy 再重新打开**（托盘图标也要退出），配置才会生效。

---

## 第 5 步：验收 🎉

在 WorkBuddy 对话框里直接用中文问：

- 「**我昨天睡得怎么样？**」
- 「**我最近一次运动的配速和心率？**」
- 「**帮我建一个滑雪机 8×250m 间歇课，排到下周三，再推到我的手表**」

AI 能正常回答 / 操作 = 全部成功！

---

## 🛟 常见问题（对号入座）

| 现象 | 原因与解决 |
|---|---|
| `python 不是内部或外部命令` | 装 Python 时没勾 `Add python.exe to PATH` → 卸载重装并勾选 |
| `pip` 下载很慢或超时 / 找不到版本 | 确认用了第 3 步的完整命令（含阿里云镜像 `-i ...` 参数）；若提示「Could not find a version」，把镜像换成清华源 `-i https://pypi.tuna.tsinghua.edu.cn/simple` 重试 |
| 报错 `ModuleNotFoundError: No module named 'mcp.server.fastmcp'` | 装成了 **mcp 2.x**（`mcp` 1.x 与 2.x 接口不兼容）。正常 `pip install -r requirements.txt` 不会触发（已锁定 `<2`）；若手动装错，重跑 `pip install "mcp>=1.0.0,<2"` 降到 1.x 即可 |
| WorkBuddy 里看不到 garmin-cn | ① `mcp.json` 格式错了：检查少没少逗号、引号是不是英文的、`\` 是不是写成了 `\\`；② 没点「信任/启用」；③ 没重启 WorkBuddy |
| 登录失败 / 拉不到数据 | ① 确认是**国行**账号（能登录 connect.garmin.cn 的才是）；② 密码抄错或带了空格；③ 账号开了两步验证(MFA)暂不支持，先关闭 MFA 再试 |
| 报错 `Display name is not set` | 服务已内置修复；若仍出现，重启 WorkBuddy 再试一次 |
| 想换佳明账号 | 改 `mcp.json` 里 `env` 的邮箱密码，保存后重启 WorkBuddy |
| 用了一段时间突然全部失效 | 佳明官方改了接口，属正常现象 → 回本项目 GitHub 页看有没有更新 |

---

## 🔒 安全须知（务必读）

1. `mcp.json` 里保存的是**明文账号密码**：**不要截图发群里、不要把该文件发给别人**。
2. 本工具只能读写**你自己账号**的数据，无法访问别人的。
3. 它通过非官方接口访问佳明服务，请自行遵守佳明服务条款；作者不对账号风险负责（详见仓库 LICENSE 部分）。
4. 项目仓库：https://github.com/BabeeJin/garmin-cn-mcp （有问题去这里提 Issue）
