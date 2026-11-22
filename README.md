# 百万字，记住你

**A Million Words to Remember You**

一百万字够记住你的一生吗？我们先让 AI 不必在每次上下文变满时，从头认识你。

[English](README.en.md) · [接入与 API](docs/API.md) · [隐私与数据](docs/PRIVACY.md) · [来源与许可](docs/PROVENANCE.md)

从陪伴机器人「大肥鱼」中提取的热冷记忆系统。近期原话尽量留在热层，旧轮次降温到持久档案；摘要在后台生成，需要确认细节时回读原文。它既是一个零强制依赖的 Python 库，也带有可选 AstrBot 接入层。

## 它做什么

- **先存原文，再整理上下文。** 原文以带会话范围的 frame 保存，摘要不是唯一副本。
- **按完整轮次降温。** 保留最新用户轮次；工具调用与结果一起移动。超大的活动正文保留首尾节选和原文来源。
- **后台整理连续性。** 摘要和未完成事项带来源，不把旧任务重新当成当前话题；失败任务持久保留，后续同会话请求可重试。
- **可核实的回忆。** 按字面线索搜索，按来源与游标分页回读，限制回读结果大小。
- **会话与身份分开。** 群聊原文不跨群混用；可选 `IdentityMemory` 按平台账号统一个人事实，默认私有，只有显式分享的非敏感事实能跨会话读取。
- **不绑定某个模型。** 摘要模型与分词器由调用者提供；包含工具定义的预算一起计算。

“百万字”是名字，不是固定字数上限，也不是永不遗忘的保证。有限模型窗口、磁盘容量、摘要误差与召回能力依然存在。

## 一分钟运行

需要 Python **3.11+**。

```sh
git clone https://github.com/shabririri418-cell/a-million-words-to-remember-you.git
cd a-million-words-to-remember-you
python -m pip install .
python -m remember_you demo
```

这是**合成数据的离线演示**：没有网络请求，不调用真实模型；演示摘要明确标为模拟结果。可以看到旧内容转冷、最新话题保留、原文仍可搜索。默认临时数据会在结束时清理；若要查看文件：

```sh
python -m remember_you demo --data-dir ./var/demo
```

连接真实 OpenAI 兼容模型：安装 `python -m pip install '.[openai,tokenizer]'`，在自己的环境里设置 `OPENAI_API_KEY`、`CHAT_MODEL`，可选设置 `OPENAI_BASE_URL`、`MODEL_TOKENIZER_PATH`、`MODEL_WINDOW_TOKENS` 和 `HOT_TARGET_TOKENS`，运行 `python examples/openai_chat.py`。示例只发送合成聊天；调用真实模型可能产生费用。

## 接入 AstrBot

将这个仓库 URL 填入 AstrBot 的插件安装入口。插件名为 `astrbot_plugin_remember_you`，完成配置后再启用：

1. `enabled_scopes` 填入你从 AstrBot 获取的真实 `unified_msg_origin`，只启用希望保存的会话。初始列表为空。
2. `model_window_tokens` 必须是模型经确认支持的窗口；`hot_target_tokens` 是偏好的热层输入预算，包含系统提示、工具结构和历史。适配层会进一步取提供商配置中的较小窗口，并为回复预留空间。
3. 推荐指定该模型的本地 `tokenizer.json`。不提供时使用保守 UTF-8 文本估算，**不是模型的真实 token 计数**；图片、音频和服务商封装另有开销。
4. 将 `enabled` 改为 `true`。卸载或停用会恢复其原有 runner 方法，不覆写核心源码。

默认大窗口配置是热层 350,000、窗口 1,000,000、输出预留 8,192；只有相应模型才能这样使用。小窗口模型应主动调小，不要把项目名称当成模型能力声明。SDK 示例使用更保守的演示配置。

适配层针对 **AstrBot 4.29.0 原生 ToolLoopAgentRunner 接口**编写。它使用内部扩展点；升级 AstrBot 后应复测。其他 Agent runner 不在适配范围。不要在已注入另一份热冷处理补丁的部署上重复启用，否则同一请求可能处理两遍。

## 数据在哪里

Python 库使用你传入的本地路径。AstrBot 默认在插件数据目录保存 `context_archive.sqlite3` 与 `hot_state.sqlite3`；没有云存储账户或托管后端。部署在一直开机的服务器上时，聊天设备关机不影响服务器的数据；运行服务的机器关机后，本库不会自行继续工作。

原文和摘要都是**明文 SQLite 数据**。同意保存哪些人的聊天、模型服务商可读取哪些内容、目录权限、加密磁盘、备份和删除策略，均由部署者管理。`scope` 是隔离键，不是认证机制；不要直接信任模型或网页传入的身份与会话范围。详见 [隐私说明](docs/PRIVACY.md)。

## 边界

- 这是上下文与连续性层，**没有内置向量数据库、知识图谱或 LivingMemory 管理面板**。原部署使用的第三方层不被冒充为本项目原创，见 [来源说明](docs/PROVENANCE.md)。
- 摘要可能漏记或误解，字面检索不理解同义词；有来源也不等于结论已被逐条核实。重要事实应回读原文。
- 档案按请求快照保存，重叠历史会占用额外磁盘。没有自动清理原文的隐藏策略，也没有“无限记忆”。
- 默认保留模型可处理的大热层，但不承诺任意模型、硬件和上下文长度都在十秒内回复；请按自己的延迟预算实测。
- 关闭时会取消后台摘要；尚未完成的任务保留。没有新的请求时，不会自动恢复所有会话的任务。SQLite 在线备份要包含 WAL 中已提交的数据，不能随意只复制活动数据库主文件。

## 开发与许可

```sh
python -m pip install '.[test]'
python -m unittest discover -s tests -p 'test_*.py'
```

测试只用合成数据，不要求真实聊天、模型密钥或 QQ 登录。仓库附 GitHub Actions 的 Windows / Linux、Python 3.11 / 3.12 测试配置。

MIT。保留原实现的版权通知；AstrBot、LivingMemory 和用户提供的 tokenizer 各自保留其许可证。本库不重新分发它们的源码或模型资源。
