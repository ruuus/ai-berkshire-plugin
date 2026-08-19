# AI Berkshire Codex Plugin

将 [xbtlin/ai-berkshire](https://github.com/xbtlin/ai-berkshire) 的价值投资研究工作流打包为可安装的 Codex 插件。

## 最简安装

已安装并登录最新版 Codex CLI 后执行：

```bash
codex plugin marketplace add ruuus/ai-berkshire-plugin --ref codex-plugin --sparse .agents/plugins --sparse plugins/ai-berkshire
codex plugin add ai-berkshire@ai-berkshire-plugin
```

安装后重启 Codex 或新建线程，并在 `/plugins` 中确认 **AI Berkshire** 已启用。

更新：

```bash
codex plugin marketplace upgrade ai-berkshire-plugin
codex plugin add ai-berkshire@ai-berkshire-plugin
```

卸载：

```bash
codex plugin remove ai-berkshire@ai-berkshire-plugin
codex plugin marketplace remove ai-berkshire-plugin
```

## 离线安装

无法访问 GitHub 仓库时，可从 [GitHub Releases](https://github.com/ruuus/ai-berkshire-plugin/releases) 下载所需版本的 ZIP 或 tar.gz 与 `SHA256SUMS`。校验后先解压，再把解压目录作为本地 marketplace：

```bash
codex plugin marketplace add /absolute/path/to/ai-berkshire-plugin-vX.Y.Z
codex plugin add ai-berkshire@ai-berkshire-plugin
```

Codex CLI 不能直接安装压缩包。离线升级、卸载和可选依赖说明见 [PLUGIN.md](PLUGIN.md#release-离线安装)。

## 分支定位

| 分支 | 用途 |
| --- | --- |
| `main` | 完整跟踪上游 `xbtlin/ai-berkshire` |
| `codex-plugin` | 仅保留 marketplace、插件产物、构建工具和维护文档 |
| `vX.Y.Z` | 固定离线安装包对应的发布快照 |

`codex-plugin` 是生成型发布分支，不再合并 `main`。维护者通过独立上游 checkout 重新生成 `plugins/ai-berkshire/`，并在 `UPSTREAM.lock.json` 中记录来源提交。

## 插件内容

- 21 个公司、行业、财报、管理层、组合与投资论文研究技能。
- 财务验算、数据获取、筛选和报告审计工具。
- 面向插件安装目录的可移植路径适配。
- 雪球抓取所需 Playwright 为可选依赖，核心技能无需额外 Python 包。

示例：

```text
使用 ai-berkshire:investment-team 研究一家上市公司
使用 ai-berkshire:earnings-review 精读最新财报
使用 ai-berkshire:industry-funnel 筛选一个行业
```

本项目仅供学习和研究，不构成投资建议。

## 精简分支结构

```text
.agents/plugins/marketplace.json       # marketplace 清单
.github/workflows/                    # 校验与 Release 自动化
plugin-packaging/                     # 同步、校验、打包与覆盖层
plugins/ai-berkshire/                 # 可安装插件
UPSTREAM.lock.json                    # 上游提交与生成信息
README.md / PLUGIN.md / AGENTS.md     # 用户与维护文档
LICENSE                               # 上游 MIT 许可证
```

完整的安装方式、上游同步、版本升级和发布流程见 [PLUGIN.md](PLUGIN.md)。

## 来源与许可证

业务工作流与共享工具来自 [xbtlin/ai-berkshire](https://github.com/xbtlin/ai-berkshire)。本分支只维护 Codex marketplace 打包、路径适配、验证和发布自动化。

项目采用 MIT 许可证。再分发插件时请保留 `plugins/ai-berkshire/LICENSE` 与 `plugins/ai-berkshire/NOTICE`。
