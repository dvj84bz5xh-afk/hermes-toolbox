# Hermes Toolbox

一键部署 Hermes Agent + Claude Code + Codex 的 Windows 环境工具箱。

## 快速开始

```powershell
# 检测环境状态
hermes-toolbox.exe check

# 一键安装所有组件
hermes-toolbox.exe install

# 检查并更新组件
hermes-toolbox.exe update

# 写入配置模板（不含 API Key）
hermes-toolbox.exe config
```

## 安装后需手动操作

安装完成后，编辑 `%LOCALAPPDATA%\hermes\.env`，填入你的 DeepSeek API Key。

## 组件清单

| 组件 | 版本 | 来源 |
|------|------|------|
| Hermes Agent | v0.15.1 | 国内镜像 |
| Claude Code | v2.1.158 | npm + DeepSeek 驱动 |
| Codex CLI | v0.135.0 | npm + Moon Bridge |
| PowerShell 7 | 7.4.6 | GitHub Releases |
| Go | 1.24.2 | GitHub Releases |
| Moon Bridge | latest | GitHub 克隆 |

## 资源下载优先级

1. GitHub 仓库（你的发布版）
2. 国内镜像（Tuna / GHProxy）
3. 官方源

## 不包含的内容

- API Key（用户自行填写）
- Ollama 模型（因算力限制跳过）
