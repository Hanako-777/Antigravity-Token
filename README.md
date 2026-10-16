# Antigravity Token

Antigravity Token 是一个专为 Google Antigravity 客户端设计的桌面用量统计工具与系统托盘小部件。该工具通过解析本地会话日志，提供类似 OpenAI Codex 风格的 Token 消耗看板与活跃度矩阵，并与官方客户端实现无感联动启动。

---

## 功能特性

- **多维用量分析**：
  - 核心指标统计：展示历史总 Token、今日消耗、单日使用峰值、累计活跃天数及日均消耗。
  - 活跃度热力图：提供连续 28 周的日均活跃矩阵，支持鼠标悬停查看每日详细输入、输出及对话轮次。
  - 消耗趋势图表：可视化展示近期 Token 日消耗与累计增长曲线。
- **系统托盘集成**：
  - 常驻 Windows 任务栏系统托盘，鼠标悬停即可快速预览当前用量摘要。
  - 单击托盘图标呼出悬浮看板，窗口失焦（点击外部区域）时自动隐藏/关闭。
- **生命周期联动**：
  - **无开机自启**：本工具不修改系统启动项（`shell:startup`）、不写入注册表自启键值、不注册系统后台服务。
  - **应用伴生启动**：通过代理快捷方式，仅在用户主动运行 Antigravity 客户端时同步拉起托盘服务。
- **非侵入式设计**：
  - 仅读取本地公开日志文件（`transcript.jsonl`），不修改 Antigravity 的任何二进制文件或程序配置。
  - 提供完整的一键还原脚本，可随时将快捷方式恢复至初始状态。

---

## 系统要求

- Windows 10 / Windows 11
- Python 3.8 或更高版本（需勾选添加至环境变量 PATH）
- Google Antigravity 客户端

---

## 安装与配置

### 方式一：手动下载并运行安装脚本

1. 将本项目下载或克隆至本地任意目录：
   ```bash
   git clone https://github.com/Hanako-777/Antigravity-Token.git
   ```
2. 进入项目根目录，双击运行 `install.bat`：
   - 脚本将自动安装所需的 Python 依赖库（`pystray`、`pillow`）。
   - 脚本将更新开始菜单与桌面上的 Antigravity 快捷方式，绑定静默联动启动器。
3. 从开始菜单或桌面正常启动 Antigravity 客户端，托盘图标将随之启动。

### 方式二：通过 AI Agent 自动安装

在 Antigravity、Cursor、Windsurf 等支持终端执行的 AI 编程助手对话框中，发送以下 Prompt：

```text
请帮我安装 Antigravity Token 工具：
1. 执行命令将仓库克隆至用户目录：
   git clone https://github.com/Hanako-777/Antigravity-Token.git "%USERPROFILE%\Antigravity-Token"
2. 运行一键安装脚本完成环境与快捷方式配置：
   cmd /c "%USERPROFILE%\Antigravity-Token\install.bat"
3. 检查开始菜单与桌面 Antigravity 快捷方式是否配置成功。
```

---

## 卸载与还原

如需还原系统设置并移除联动，请在项目根目录下运行 `uninstall.bat`：

- 自动终止正在运行的托盘进程。
- 将开始菜单和桌面的 Antigravity 快捷方式恢复为指向官方原版可执行文件。
- 不会在系统中残留任何后台服务或注册表项。

---

## 技术实现简述

1. **启动调度**：`install.bat` 基于当前系统的 Python 运行时及 Antigravity 安装路径生成 `launch_antigravity.vbs`，通过 Windows Script Host 以前台无窗口（WindowStyle=0）方式唤起 Python 托盘脚本，并直接启动主客户端。
2. **轻量看板**：基于 Microsoft Edge 应用程序模式（`--app` 参数）渲染独立的无边框悬浮界面，结合 Windows 工作区 API（`SPI_GETWORKAREA`）动态计算坐标，精准吸附于托盘区域上方。
3. **数据解析**：后台线程按需扫描用户目录下的 `~/.gemini/antigravity/brain/*/transcript.jsonl` 记录，聚合统计模型调用产生的 token 指标。

---

## 开源协议

本项目采用 [MIT 许可证](LICENSE)。
