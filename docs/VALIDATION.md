# 验证记录 / Validation

Initial public extraction: **2026-11-22**, version **0.1.0**.

| Check | Result | What it establishes |
| --- | --- | --- |
| Core tests on Windows | 24 passed | Archive isolation, whole-turn cooling, tool-pair retention, current-topic priority, background retry, shutdown, identity permissions, concurrent same-scope handling and runner restoration |
| Core tests on Linux / Python 3.12 | 24 passed | The same synthetic suite in the original deployment's Python environment |
| Actual AstrBot 4.29.0 imports and plugin lifecycle, in an isolated process | Passed | Plugin initialization, scope-bound source tools, unauthorized-scope rejection, native runner patch restoration and rebuilding real AstrBot Message objects |
| Python wheel build | Passed | Pure-Python distribution builds and carries LICENSE/NOTICE |
| Demo from the extracted wheel, outside the source tree | Passed | Standalone installation layout runs without the private workspace or network |
| Publication audit | Passed for initial source set | Only source/docs/synthetic tests; no production databases, conversations, deployed account identifiers, server endpoints or credential patterns |

The AstrBot probe used temporary directories and a mock model boundary. It did **not** install this new plugin into the running companion, send a QQ message, or establish end-to-end compatibility with every provider or host version. The real-model SDK example is provided for operators to test with their own credentials; no private benchmark transcripts are distributed.

GitHub Actions additionally runs the core suite and offline demo on Windows/Linux and Python 3.11/3.12. The workflow uses read-only repository permissions and immutable revisions of the official [checkout](https://github.com/actions/checkout) and [setup-python](https://github.com/actions/setup-python) actions. Inspect the repository's Actions page for current CI results rather than treating this static document as a permanent green status.

没有把大肥鱼私有部署的功能全部照搬：情绪/好感、QQ 路由、具体人设、服务器运维、第三方向量与图谱插件都不是这个发布包的组成部分。24 项测试是这个公开核心与接入接口的验证，不是对所有机器人能力的统一认证。
