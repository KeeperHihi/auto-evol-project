from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from auto_evolution.config_loader import resolve_local_path_from_root
from auto_evolution.logging_utils import log
from auto_evolution.models import AppConfig, LlmAccessConfig


def read_text_file(path: Path, field_name: str, allow_empty: bool = False) -> str:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"读取 {field_name} 失败: {exc}") from exc

    text = content.strip()
    if not allow_empty and not text:
        raise ValueError(f"{field_name} 为空: {path}")
    return text


def build_llm_runtime_hint(config: LlmAccessConfig) -> str:
    if not (config.url and config.api_key and config.model):
        return ""

    return "\n".join(
        [
            "- 可选外部模型调用（运行时注入）：",
            f"  - url: {config.url}",
            f"  - model: {config.model}",
            "  - api_key_env: LLM_ACCESS_API_KEY（只读环境变量，禁止输出明文）",
        ]
    )


def render_system_prompt(template: str, llm_config: LlmAccessConfig) -> str:
    runtime_hint = build_llm_runtime_hint(llm_config)
    token = "{{LLM_RUNTIME_HINT}}"
    rendered = template
    if token in rendered:
        rendered = rendered.replace(token, runtime_hint)
    elif runtime_hint:
        rendered = f"{rendered.strip()}\n\n{runtime_hint}".strip()

    return re.sub(r"\n{3,}", "\n\n", rendered).strip()


def ask_user_prompt() -> str:
    try:
        return input("请输入你的一句话项目创意：").strip()
    except EOFError:
        return ""


def resolve_user_prompt(app_root: Path, cli_prompt: str | None, config: AppConfig) -> str:
    if cli_prompt and cli_prompt.strip():
        return cli_prompt.strip()

    prompt_file = resolve_local_path_from_root(app_root, config.user_prompt_file, "userPromptFile")
    file_prompt = read_text_file(prompt_file, "userPromptFile", allow_empty=True)
    if file_prompt:
        log(f"[SYSTEM] 已从文件读取用户创意：{prompt_file}")
        return file_prompt

    if sys.stdin.isatty():
        interactive_prompt = ask_user_prompt()
        if interactive_prompt:
            return interactive_prompt

    raise ValueError(
        f"用户创意为空，请填写 {prompt_file}，或通过 --prompt 参数传入一句项目创意"
    )


def build_iteration_prompt(
    system_prompt: str,
    user_prompt: str,
    iteration: int,
    total_iterations: int,
    previous_tail: str,
    append_iteration_context: bool,
) -> str:
    sections: list[str] = [
        "【系统提示词】",
        system_prompt.strip(),
        "",
        "【用户创意】",
        user_prompt.strip(),
        "",
    ]

    if append_iteration_context:
        sections.extend(
            [
                "【本轮迭代上下文】",
                f"- 轮次：第 {iteration}/{total_iterations} 轮",
                f"- 时间：{datetime.now(timezone.utc).isoformat()}",
            ]
        )
        if previous_tail:
            sections.extend(["- 上轮输出摘要（截断）：", previous_tail])
        sections.extend(
            [
                "- 要求：基于当前仓库最新状态继续推进，不要重复上一轮内容。",
                "",
            ]
        )

    sections.extend(
        [
            "【执行要求】",
            "1. 先审查当前仓库状态，选出本轮最有价值且可交付的改进。",
            "2. 直接修改代码并确保项目可运行。",
            "3. 至少执行一条有效验证命令（例如构建、测试或语法检查）。",
            "4. 结尾说明：本轮改动、验证结果、下一轮建议。",
            "5. 若本轮有代码变更，请最后单独输出：COMMIT_MESSAGE: <提交信息>。",
        ]
    )

    return "\n".join(sections).strip()
