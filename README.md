# 🌌 Antigravity Token

<p align="center">
  <b>Google Antigravity 优雅的独立桌面 Token 用量看板与托盘小部件</b>
  <br>
  <i>采用 OpenAI Codex 极简精美设计风格 · 随官方客户端无感启动 · 零开机自启</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-3776AB?logo=python&logoColor=white" alt="Python Version">
  <img src="https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6?logo=windows&logoColor=white" alt="Platform">
  <img src="https://img.shields.io/badge/Style-OpenAI%20Codex-00A67E" alt="Style">
  <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License">
</p>

---

## ✨ 核心特性

- 💎 **OpenAI Codex 级精美看板**：
  - **5 项核心用量指标**：历史总消耗、今日消耗、单日使用峰值、活跃天数、日均消耗。
  - **28 周高密度热力图**：类 GitHub / Codex 提交矩阵，悬停感知边缘自适应防遮挡气泡。
  - **日用量走势与累计增长曲线**：双图表直观呈现消耗趋势。
- 🌟 **原生右下角小部件体验**：
  - 任务栏托盘常驻蓝粉渐变星芒图标，悬停即可预览今日与历史 Token 总数。
  - 点击呼出 680×680 悬浮看板，**点击窗口外部任意位置自动关闭**（防打扰）。
- 🚀 **与 Antigravity App 完美联动**：
  - **零开机自启（0 Boot Autorun）**：不修改 Windows 开机自启文件夹、不添加任何注册表启动项、不常驻计划任务。
  - **纯随应用启动**：平时静默，仅当你从「开始菜单」或「桌面」主动打开 Antigravity 时，托盘小部件随同唤起。
- 🛡️ **绿色非侵入 & 一键还原**：
  - 本地离线解析 Antigravity 官方日志，不修改任何官方程序文件。
  - 自带 `uninstall.bat`，随时一键还原官方原始启动链路。

---

## 📦 使用方法

### 方法一：下载后一键运行（推荐普通用户）

1. 点击仓库右上角的 **Code -> Download ZIP**（或使用 `git clone`）将本项目下载到电脑任意文件夹并解压。
2. 确保电脑已安装 Python 3.8+ 并已勾选添加到环境变量（PATH）。
3. **鼠标双击运行 `install.bat`**。
   * 脚本会自动安装所需依赖（`pystray`, `pillow`）。
   * 自动将 Antigravity 的开始菜单与桌面快捷方式配置为静默联动启动。
4. **大功告成！** 之后你只需像平时一样从【开始菜单】或【桌面】打开 Antigravity，右下角就会自动伴随出现蓝粉星芒用量看板！

---

### 方法二：复制给 AI Agent 直接安装（推荐 AI 助手重度用户）

如果你正在使用 Antigravity、Cursor、Windsurf、Claude Code 或其他 AI 编程助手，**直接复制以下 Prompt 发送给 Agent**，Agent 会自动为你全自动配置完毕：

```markdown
请帮我安装并配置 Antigravity Token 看板工具：
1. 运行命令克隆仓库：
   git clone https://github.com/Hanako-777/Antigravity-Token.git "%USERPROFILE%\Antigravity-Token"
2. 进入目录并运行一键安装脚本：
   cmd /c "%USERPROFILE%\Antigravity-Token\install.bat"
3. 安装完成后验证开始菜单与桌面快捷方式是否已绑定。
```

---

## 🔄 卸载与还原

如果你想恢复为官方原本的启动方式，只需：
- 双击运行项目目录下的 **`uninstall.bat`**。
- 快捷方式将瞬间恢复为官方原版，同时关闭托盘进程，电脑内不留任何残留。

---

## 🛠️ 技术原理

- **启动代理模式**：通过 VBS 包装脚本代理原快捷方式，在启动官方 `Antigravity.exe` 的同时静默检测并唤醒托盘 Python 守护，实现 0 秒延迟无感知并发启动。
- **独立 HUD 容器**：利用 Edge Application 模式构建无边框轻量级悬浮窗口，配合工作区边缘计算精准停靠在任务栏托盘上方。

---

## 📄 开源许可

本项目基于 [MIT License](LICENSE) 开源协议，欢迎 Star ⭐ 与提 PR！
