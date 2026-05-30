#!/usr/bin/env python3
"""
Hermes Toolbox — One-click environment setup & health check for Hermes Agent + CC + Codex.

Usage:
    hermes-toolbox.exe check      检测环境状态
    hermes-toolbox.exe install    安装缺失组件
    hermes-toolbox.exe update     检查并更新组件
    hermes-toolbox.exe config     写入配置模板

Architecture:
    All download URLs and versioning are managed via versions.json
    in the GitHub repo: dvj84bz5xh-afk/hermes-toolbox
"""

import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.error
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

# ─── Constants ───────────────────────────────────────────────────────────────

GITHUB_RAW = "https://raw.githubusercontent.com/dvj84bz5xh-afk/hermes-toolbox/main"
VERSIONS_URL = f"{GITHUB_RAW}/versions.json"

HERMES_HOME = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "hermes"
OLLAMA_EXE = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"

# ─── Data structures ─────────────────────────────────────────────────────────

@dataclass
class ToolInfo:
    name: str
    version: str
    description: str
    download_urls: dict
    install_type: str = "download"  # download | npm | git_repo | install_script
    check_cmd: str = ""
    expected_output: str = ""
    npm_package: str = ""
    needs_go: bool = False
    repo_url: str = ""

@dataclass
class CheckResult:
    name: str
    installed: bool
    version_found: str
    expected_version: str
    status: str  # OK | MISSING | OUTDATED | ERROR

# ─── Utilities ───────────────────────────────────────────────────────────────

def color(s: str, code: str) -> str:
    """Simple terminal coloring."""
    codes = {"green": "32", "red": "31", "yellow": "33", "blue": "34", "bold": "1"}
    c = codes.get(code, "0")
    if not sys.stdout.isatty():
        return s
    return f"\033[{c}m{s}\033[0m"

def print_header():
    print("=" * 56)
    print("  Hermes Toolbox  v1.0  —  Environment Manager")
    print(f"  Repo: github.com/dvj84bz5xh-afk/hermes-toolbox")
    print("=" * 56)
    print()

def run_cmd(cmd: str, timeout: int = 15) -> tuple[int, str]:
    """Run a shell command, return (exit_code, output)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, (result.stdout + result.stderr).strip()
    except FileNotFoundError:
        return -1, "command not found"
    except subprocess.TimeoutExpired:
        return -1, "timeout"
    except Exception as e:
        return -1, str(e)

def download_file(url: str, dest: Path, desc: str = "") -> bool:
    """Download a file from url to dest. Returns True on success."""
    print(f"  ↓ 下载 {desc or url.split('/')[-1]}...", end=" ", flush=True)
    try:
        urllib.request.urlretrieve(url, dest)
        size = dest.stat().st_size
        print(f"✅ {size // 1024 // 1024}MB" if size > 1024 * 1024 else f"✅ {size // 1024}KB")
        return True
    except Exception as e:
        print(f"❌ {e}")
        return False

def try_download(name: str, urls: dict, dest: Path) -> bool:
    """Try multiple download URLs in priority order."""
    priority_order = ["github_repo", "mirror_cn", "official"]
    for key in priority_order:
        url = urls.get(key)
        if url and download_file(url, dest, f"{name} ({key})"):
            return True
    # Try remaining keys
    for key, url in urls.items():
        if key not in priority_order:
            if download_file(url, dest, f"{name} ({key})"):
                return True
    return False

def fetch_json(url: str) -> Optional[dict]:
    """Fetch and parse JSON from url."""
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None

# ─── Detection ───────────────────────────────────────────────────────────────

def check_tool(name: str, check_cmd: str, expected: str) -> CheckResult:
    """Run a version check command and parse the result."""
    code, output = run_cmd(check_cmd)
    if code != 0 or not output:
        return CheckResult(name, False, "", expected, "MISSING")
    
    # Parse version
    version_found = output.strip()
    is_ok = expected in version_found
    
    if is_ok:
        return CheckResult(name, True, version_found, expected, "OK")
    else:
        return CheckResult(name, True, version_found, expected, "OUTDATED")

def check_windows_features() -> list[CheckResult]:
    """Check basic Windows environment."""
    results = []
    
    # Windows version
    win_ver = platform.version()
    results.append(CheckResult("Windows 10/11", True, win_ver, "10+", "OK"))
    
    return results

def check_all(versions: dict) -> list[CheckResult]:
    """Run all environment checks."""
    results = check_windows_features()
    
    tools = versions.get("tools", {})
    for name, info in tools.items():
        if info.get("check_cmd"):
            result = check_tool(
                info.get("description", name),
                info["check_cmd"],
                info.get("expected_output", "")
            )
            results.append(result)
    
    return results

# ─── Commands ────────────────────────────────────────────────────────────────

def cmd_check():
    """Check environment status."""
    print_header()
    
    versions = fetch_json(VERSIONS_URL)
    if not versions:
        print(f" {color('⚠', 'yellow')} 无法获取版本清单，使用内置版本信息")
        versions = {}
    
    results = check_all(versions)
    
    print(f" {'Component':<30} {'Status':<10} {'Version'}")
    print(f" {'-'*30} {'-'*10} {'-'*20}")
    
    ok_count = 0
    for r in results:
        status_str = {
            "OK": color("✅ OK", "green"),
            "MISSING": color("❌ MISS", "red"),
            "OUTDATED": color("⚠ OLD", "yellow"),
            "ERROR": color("💥 ERR", "red"),
        }.get(r.status, r.status)
        
        print(f" {r.name:<30} {status_str:<10} {r.version_found or r.expected_version}")
        if r.status == "OK":
            ok_count += 1
    
    print(f"\n {ok_count}/{len(results)} 组件正常")
    
    # Check API keys
    print()
    print("─" * 56)
    print(" API Key 检查")
    print("─" * 56)
    
    hermes_env = HERMES_HOME / ".env"
    if hermes_env.exists():
        content = hermes_env.read_text(encoding="utf-8")
        if "sk-" in content and "YOUR_" not in content:
            print(f"  {color('✅', 'green')} DeepSeek API Key 已配置")
        else:
            print(f"  {color('⚠', 'yellow')} DeepSeek API Key 未填写 → 请编辑 {hermes_env}")
    else:
        print(f"  {color('❌', 'red')} .env 文件不存在 → 运行 config 命令创建")

def cmd_install():
    """Install all missing components."""
    print_header()
    print(" 开始安装缺失组件...\n")
    
    versions = fetch_json(VERSIONS_URL)
    if not versions:
        print(f" {color('✗', 'red')} 无法获取版本清单，请检查网络连接")
        return
    
    results = check_all(versions)
    tools = versions.get("tools", {})
    missing = [r for r in results if r.status == "MISSING"]
    
    if not missing:
        print(f" {color('✅', 'green')} 所有组件已安装！")
        return
    
    print(f" 发现 {len(missing)} 个组件需要安装:\n")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        for m in missing:
            tool_name = [k for k, v in tools.items() if v.get("description") == m.name]
            tool_key = tool_name[0] if tool_name else None
            if not tool_key:
                continue
            
            info = tools[tool_key]
            print(f" [{color('→', 'blue')}] {m.name}")
            
            if info.get("install_type") == "npm":
                # npm global install
                pkg = info.get("npm_package", "")
                if pkg:
                    code, out = run_cmd(f"npm install -g {pkg}", timeout=120)
                    print(f"     {'✅' if code == 0 else '❌'} npm install {pkg}")
            
            elif info.get("install_type") == "install_script":
                # Hermes install script
                urls = info.get("download_urls", {})
                script_path = Path(tmpdir) / "install.ps1"
                if try_download("Hermes installer", urls, script_path):
                    code, out = run_cmd(
                        f'pwsh -NoProfile -Command "& \'{script_path}\' -SkipSetup"',
                        timeout=300
                    )
                    print(f"     {'✅' if code == 0 else '❌'} Hermes 安装")
            
            elif info.get("install_type") == "git_repo":
                # Git clone for Moon Bridge
                repo = info.get("repo_url", "")
                if repo and info.get("needs_go"):
                    dest = HERMES_HOME / "moon-bridge"
                    if not dest.exists():
                        code, out = run_cmd(f"git clone {repo} \"{dest}\"", timeout=120)
                        print(f"     {'✅' if code == 0 else '❌'} git clone moon-bridge")
                    else:
                        print(f"     ⏩ 已存在")
            
            else:
                # Regular download
                urls = info.get("download_urls", {})
                dest = Path(tmpdir) / f"{tool_key}.exe"
                if try_download(m.name, urls, dest):
                    # Execute installer
                    if dest.suffix == ".msi":
                        code, out = run_cmd(f'msiexec /i "{dest}" /quiet /norestart', timeout=180)
                        print(f"     {'✅' if code == 0 else '❌'} msiexec 安装")
                    elif dest.suffix == ".exe":
                        code, out = run_cmd(f'"{dest}" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART', timeout=180)
                        print(f"     {'✅' if code == 0 else '❌'} exe 安装")
            
            print()
    
    # Final check
    print(" 安装完成，重新检测...")
    cmd_check()

def cmd_update():
    """Check for updates and update components."""
    print_header()
    print(" 检查组件更新...\n")
    
    versions = fetch_json(VERSIONS_URL)
    if not versions:
        print(f" {color('✗', 'red')} 无法获取版本清单")
        return
    
    results = check_all(versions)
    outdated = [r for r in results if r.status == "OUTDATED"]
    
    if not outdated:
        print(f" {color('✅', 'green')} 所有组件已是最新版本！")
        return
    
    print(f" 发现 {len(outdated)} 个组件需要更新:\n")
    for o in outdated:
        print(f"  {o.name}: {o.version_found} → {o.expected_version}")
    
    print(f"\n 运行 '{sys.argv[0]} install' 来更新组件")

def cmd_config():
    """Write configuration templates."""
    print_header()
    print(" 写入配置模板...\n")
    
    # Ensure HERMES_HOME exists
    HERMES_HOME.mkdir(parents=True, exist_ok=True)
    
    # Download hermes.env template
    env_url = f"{GITHUB_RAW}/templates/hermes.env"
    env_dest = HERMES_HOME / ".env"
    
    if not env_dest.exists():
        if download_file(env_url, env_dest, ".env 模板"):
            print(f"  → {env_dest}")
    else:
        print(f"  ⏩ .env 已存在，跳过")
    
    # Download config template
    config_url = f"{GITHUB_RAW}/templates/hermes.config.yaml"
    config_dest = HERMES_HOME / "config.yaml"
    
    if not config_dest.exists():
        if download_file(config_url, config_dest, "config.yaml 模板"):
            print(f"  → {config_dest}")
    else:
        print(f"  ⏩ config.yaml 已存在，跳过")
    
    print(f"\n {color('✅', 'green')} 配置模板已写入")
    print(f" 请编辑 {env_dest} 填入你的 DeepSeek API Key")

# ─── CLI Entrypoint ──────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return
    
    command = sys.argv[1]
    commands = {
        "check": cmd_check,
        "install": cmd_install,
        "update": cmd_update,
        "config": cmd_config,
    }
    
    if command in commands:
        commands[command]()
    else:
        print(f"未知命令: {command}")
        print("可用命令: check, install, update, config")

if __name__ == "__main__":
    main()
