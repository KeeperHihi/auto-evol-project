from __future__ import annotations

import subprocess
from pathlib import Path

from auto_evolution.config_loader import normalize_branch_name
from auto_evolution.logging_utils import log
from auto_evolution.models import AppConfig
from auto_evolution.text_tools import extract_tail, sanitize_commit_message


def run_git(workspace: Path, args: list[str], timeout_seconds: int = 60) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("未找到 git 命令，请先安装 git") from exc


def resolve_workspace(app_root: Path, site_name: str) -> Path:
    webs_root = (app_root / "webs").resolve()
    webs_root.mkdir(parents=True, exist_ok=True)
    workspace = (webs_root / site_name).resolve()

    if workspace != webs_root and webs_root not in workspace.parents:
        raise ValueError("siteName 非法，必须位于 webs 目录内")

    if not workspace.exists() or not workspace.is_dir():
        raise FileNotFoundError(
            f"未找到站点目录: {workspace}\n"
            "请先创建空仓库目录，例如: mkdir -p webs/<siteName> && cd webs/<siteName> && git init"
        )

    return workspace


def ensure_workspace_is_git_repo(workspace: Path) -> None:
    check = run_git(workspace, ["rev-parse", "--is-inside-work-tree"])
    if check.returncode != 0 or check.stdout.strip() != "true":
        raise RuntimeError(
            f"{workspace} 不是 git 仓库。\n"
            "请先在该目录执行 git init，并按需配置远端。"
        )


def get_current_branch_name(workspace: Path) -> str:
    result = run_git(workspace, ["symbolic-ref", "--quiet", "--short", "HEAD"])
    if result.returncode != 0:
        details = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"读取当前分支失败: {details}")
    return normalize_branch_name(result.stdout)


def ensure_branch_ready(workspace: Path, branch_name: str) -> None:
    current = get_current_branch_name(workspace)
    target = normalize_branch_name(branch_name)
    if current == target:
        return

    exists = run_git(workspace, ["show-ref", "--verify", "--quiet", f"refs/heads/{target}"])
    if exists.returncode == 0:
        switch = run_git(workspace, ["checkout", target])
    else:
        switch = run_git(workspace, ["checkout", "-B", target])

    if switch.returncode != 0:
        details = (switch.stderr or switch.stdout).strip()
        raise RuntimeError(f"切换到分支 {target} 失败: {details}")

    log(f"[GIT] 已切换到分支: {target}")


def ensure_remote_ready(workspace: Path, remote_name: str) -> None:
    result = run_git(workspace, ["remote", "get-url", remote_name])
    if result.returncode != 0:
        raise RuntimeError(
            f"未找到远端 {remote_name}。\n"
            f"请先在 {workspace} 执行: git remote add {remote_name} <你的仓库地址>"
        )


def inspect_workspace_state(workspace: Path) -> str:
    has_commit = run_git(workspace, ["rev-parse", "--verify", "HEAD"]).returncode == 0

    tracked = run_git(workspace, ["ls-files"])
    if tracked.returncode != 0:
        raise RuntimeError(f"读取仓库文件列表失败：{extract_tail(tracked.stderr or tracked.stdout, 400)}")
    tracked_files = [line.strip() for line in tracked.stdout.splitlines() if line.strip()]

    uncommitted = run_git(workspace, ["status", "--porcelain"])
    if uncommitted.returncode != 0:
        raise RuntimeError(
            f"读取仓库状态失败：{extract_tail(uncommitted.stderr or uncommitted.stdout, 400)}"
        )
    pending = [line.strip() for line in uncommitted.stdout.splitlines() if line.strip()]

    if not has_commit and not tracked_files and not pending:
        return "empty"
    return "non_empty"


def count_changed_files(workspace: Path) -> int:
    status = run_git(workspace, ["status", "--porcelain"])
    if status.returncode != 0:
        return -1
    return len([line for line in status.stdout.splitlines() if line.strip()])


def build_commit_message(config: AppConfig, codex_message: str, iteration: int) -> str:
    base = sanitize_commit_message(codex_message) or f"第{iteration}轮自动进化更新"
    prefix = sanitize_commit_message(config.codex.git_commit_prefix)
    if prefix and not base.startswith(prefix):
        return f"{prefix} {base}".strip()
    return base


def commit_and_push_changes(
    config: AppConfig,
    workspace: Path,
    codex_message: str,
    iteration: int,
) -> tuple[bool, bool]:
    if not config.codex.auto_git_commit:
        log("[GIT] 已关闭自动提交（autoGitCommit=false）")
        return False, False

    add_result = run_git(workspace, ["add", "-A"], timeout_seconds=120)
    if add_result.returncode != 0:
        raise RuntimeError(f"git add 失败：{extract_tail(add_result.stderr or add_result.stdout, 600)}")

    staged = run_git(workspace, ["diff", "--cached", "--name-only"])
    if staged.returncode != 0:
        raise RuntimeError(f"读取暂存区失败：{extract_tail(staged.stderr or staged.stdout, 600)}")

    staged_files = [line.strip() for line in staged.stdout.splitlines() if line.strip()]
    if not staged_files:
        log("[GIT] 未检测到可提交改动，跳过提交与推送")
        return False, False

    message = build_commit_message(config, codex_message, iteration)
    commit_result = run_git(workspace, ["commit", "-m", message], timeout_seconds=120)
    if commit_result.returncode != 0:
        details = extract_tail(commit_result.stderr or commit_result.stdout, 1000)
        if "Author identity unknown" in details:
            raise RuntimeError(
                "git commit 失败：未配置用户信息，请先执行\n"
                'git config user.name "<你的名字>"\n'
                'git config user.email "<你的邮箱>"'
            )
        raise RuntimeError(f"git commit 失败：{details}")

    log(f"[GIT] 已提交：{message}")

    if not config.codex.auto_git_push:
        log("[GIT] 已关闭自动推送（autoGitPush=false）")
        return True, False

    remote = config.codex.git_remote
    branch = normalize_branch_name(config.codex.git_branch)
    push_result = run_git(workspace, ["push", "-u", remote, branch], timeout_seconds=180)
    if push_result.returncode != 0:
        raise RuntimeError(f"git push 失败：{extract_tail(push_result.stderr or push_result.stdout, 1000)}")

    log(f"[GIT] 已推送到 {remote}/{branch}")
    return True, True
