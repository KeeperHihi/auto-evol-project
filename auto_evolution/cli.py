from __future__ import annotations

import argparse
import sys

from auto_evolution.logging_utils import log_error
from auto_evolution.workflow import run_evolution


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="自动进化脚本入口（在 webs/<siteName> 独立仓库中执行迭代）",
        usage="python evolution.py [--site 网站仓库名] [--iterations 轮次] [--prompt 创意] [--dry-run]",
        add_help=False,
        allow_abbrev=False,
    )
    parser._positionals.title = "位置参数"
    parser._optionals.title = "可选参数"
    parser.add_argument("-h", "--help", action="help", help="显示帮助信息并退出")
    parser.add_argument("--site", help="覆盖 config.json 中的 siteName（目标网站仓库目录名）")
    parser.add_argument(
        "--iterations",
        type=int,
        help="覆盖 config.json 中的迭代轮次",
    )
    parser.add_argument("--prompt", help="直接传入一句网站创意，优先级高于 userPromptFile")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅做本地只读演练，不调用 Codex、不执行 autoGitInit、不切换分支、不做远端检查",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        exit_code = run_evolution(
            site_override=args.site,
            iterations_override=args.iterations,
            prompt_override=args.prompt,
            dry_run_override=args.dry_run,
        )
    except Exception as exc:
        log_error(f"[ERROR] {exc}")
        sys.exit(1)

    sys.exit(exit_code)
