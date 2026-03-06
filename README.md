# Auto-Evolution-Web (Python)

当前主版本已迁移到 Python，主入口是 `evolution.py`。  
旧版 JavaScript 实现保留在 `JS-version/`，仅作为历史参考。

## 核心工作流

- `webs/<siteName>` 下每个子目录都是一个独立网站仓库。
- 用户可以从空仓库开始，只提供一句创意（idea）逐轮进化。
- 每轮执行后，脚本会在该子仓库内自动执行：
  - `git add -A`
  - `git commit -m "<Codex 提供的提交信息>"`
  - `git push -u origin main`

## 代码结构

- `evolution.py`：命令行入口（仅负责启动）。
- `auto_evolution/cli.py`：参数解析。
- `auto_evolution/workflow.py`：主流程编排。
- `auto_evolution/config_loader.py`：配置读取与兼容性归一化。
- `auto_evolution/logging_utils.py`：彩色日志与 Codex 输出分类（继承旧版 JS 的标签着色逻辑）。
- `auto_evolution/prompt_tools.py`：提示词读取与迭代 Prompt 组装。
- `auto_evolution/codex_runner.py`：Codex 执行、重试、会话恢复、提交信息提取。
- `auto_evolution/git_tools.py`：站点仓库检查、分支与远端检查、自动提交推送。

## 快速开始

1. 确保本机可用：`python3`、`git`、`codex`。
   若要启用 `autoGitInit`，还需安装并登录 `gh`（`gh auth login`）。

2. 准备配置文件：

```bash
cp config.template.json config.json
```

3. 准备站点空仓库（示例站点名：`demo`）：

```bash
mkdir -p webs/demo
cd webs/demo
git init
git checkout -B main
git remote add origin <你的空仓库地址>
```

4. 填写你的创意（建议一句话）到 `prompts/user-prompt.md`。

5. 回到项目根目录，启动进化：

```bash
python3 evolution.py --iteration 10
```

可选参数：

```bash
python3 evolution.py --site demo --iterations 10
python3 evolution.py --prompt "做一个极简但高级的作品集网站"
python3 evolution.py --dry-run
```

## 配置字段（`config.json`）

- `siteName`：目标站点目录名，对应 `webs/<siteName>`。
- `iterations`：默认迭代轮次。
- `intervalSeconds`：轮次间隔秒数。
- `appendIterationContext`：是否在每轮 Prompt 附带迭代上下文。
- `systemPromptFile`：系统提示词路径。
- `userPromptFile`：用户创意提示词路径。
- `llmAccess`：可选运行时外部模型注入信息。
- `codex.command`：Codex 命令名。
- `codex.model`：Codex 模型参数。
- `codex.profile`：可选 profile。
- `codex.dangerouslyBypassApprovalsAndSandbox`：是否追加该参数。
- `codex.timeoutSeconds`：单轮超时秒数。
- `codex.retries`：单轮失败重试次数。
- `codex.extraArgs`：追加给 Codex 的参数。
- `codex.dryRun`：仅演练，不调用 Codex。
- `codex.autoGitCommit`：每轮后是否自动提交。
- `codex.autoGitPush`：每轮后是否自动推送。
- `codex.gitRemote`：推送远端名，默认 `origin`。
- `codex.gitBranch`：推送分支名，默认 `main`。
- `codex.gitCommitPrefix`：提交信息前缀（可留空）。
- `codex.autoGitInit`：自动初始化仓库机制。启用后若本地站点目录未绑定远端，会自动检测当前 GitHub 账号下是否有同名仓库；有则绑定并拉取，无则自动创建后绑定。

## 说明

- `webs/**` 已在本仓库 `.gitignore` 中忽略，因为它属于用户网站仓库。
- `config.json` 已忽略，避免本地密钥被提交。
