# 隐私与数据生命周期 / Privacy and data lifecycle

## 默认边界 / Defaults

- AstrBot 默认未启用，且会话白名单为空。只有部署者明确选中的会话才进入热冷处理。
- 原文及连续性摘要按会话隔离。跨会话的个人事实使用单独的显式 API，默认私有；平台账号和显示昵称不是同一回事。
- Archive and state are local, unencrypted SQLite files. There is no telemetry, hosted database or built-in public HTTP server.
- The library has no authentication layer. Scope/user IDs must be derived from authenticated platform events by a trusted application. A model must not be allowed to choose whose data it reads.
- The summary callback receives older messages and previous continuity state. If it uses a remote provider, those contents leave the host under that provider's policies. The chat provider receives the selected hot context. Do not store credentials in conversation text.

Summaries are untrusted derived data, not authority. Prompt instructions reduce accidental obedience to historical messages but cannot establish a mathematical guarantee against prompt injection or hallucination. Important details should be checked against originals.

## 备份 / Backups

`ContextArchive.backup(destination)` uses SQLite online backup, including committed WAL data. It backs up the archive database only. For hot-state and identity databases, use SQLite's backup API too, or stop all writers before copying all relevant files. Store backups with the same access controls as live data. A normal Git repository is not a conversation backup destination.

## 删除 / Deletion

Stop accepting new requests and close the runtime before deleting data. `archive.delete_scope(scope)` deletes that scope's originals only; **it does not delete derived hot-state summaries, queued jobs, identity facts, backups, provider-side logs or external plugin data**.

For a full local erase, with all runtimes stopped, remove the relevant scope's rows from `hot_state` and `cold_jobs` in the hot-state database as well. Use `IdentityMemory.delete_person(platform, user_id)` where authorized; shared facts can otherwise remain. When retiring the entire deployment, delete the archive, state and identity databases plus their WAL/SHM files and backups after stopping writers. Encrypted storage is recommended when secure erasure matters; SQLite deletion alone is not a guarantee of physical-byte erasure.

The archive is snapshot-based: earlier snapshots may retain a message after later context edits. There is no automatic raw-data retention or expiration policy in this release. Operators must define one, disclose it to participants, and account for disk growth.

## 发布内容 / Publication boundary

The repository contains code, synthetic tests and sample configuration only. It does not contain production transcripts, databases, embeddings, server addresses, personal account lists, private keys, model credentials, tokenizer assets or model weights. Dependencies and hosted CI providers have their own policies. Local examples write under ignored `var/` paths or temporary directories.
