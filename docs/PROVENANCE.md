# 来源与许可证 / Provenance and licenses

本项目发布的是大肥鱼工作区里自主维护的热冷连续性、原文归档和相关测试的可移植版本。`remember_you/hot_memory.py` 和 `archive.py` 从该实现提取，去除了私人账号、固定会话和专用部署路径，并补充独立生命周期及平台接入接口。原项目的 MIT 通知保留在 `LICENSE` 与 `NOTICE` 中。

This release generalizes the Dafeiyu workspace's hot/cold continuity and source-archive implementation. It retains the original MIT attribution. Public API, identity-storage, lifecycle and integration additions are supplied under the same license.

| 项目 / Project | 关系 / Relationship | 授权边界 / Licensing boundary |
| --- | --- | --- |
| Dafeiyu workspace | 提取的核心实现 / extracted core | MIT; original attribution retained |
| AstrBot | 可选外部宿主 / optional host | Not bundled; its AGPL license remains applicable to AstrBot |
| LivingMemory | 原部署另用的语义/图谱层 / original deployment's separate semantic/graph layer | Not bundled; its AGPL license remains applicable to that project |
| Model tokenizers | 用户自行指定 / supplied by the operator | No tokenizer files or model weights redistributed |

这个仓库不是 LivingMemory 的重新命名分发，也不声称包含它的向量检索、图谱、实体原子生命周期或管理面板。需要该能力时可另外安装原项目，遵守其许可并测试两个系统的召回与预算关系。

This repository is not a renamed distribution of LivingMemory. It does not include LivingMemory's vector search, knowledge graph, atom lifecycle or UI. Install that project separately if required and respect its own terms. No third-party license is replaced by this repository's MIT license.

The AstrBot adapter is newly written integration code using host interfaces. Full upstream runner files and private deployment patches are intentionally excluded. Public packaging tests do not assert compatibility with every AstrBot version.
