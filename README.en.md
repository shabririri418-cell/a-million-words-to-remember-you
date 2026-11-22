# A Million Words to Remember You

**百万字，记住你**

Can a million words remember your whole life? First, let us stop an AI companion from having to meet you again whenever its context fills up.

[中文](README.md) · [API and integration](docs/API.md) · [Privacy and data](docs/PRIVACY.md) · [Provenance](docs/PROVENANCE.md)

A source-backed hot/cold continuity layer extracted from the Dafeiyu companion bot. Keep recent original turns hot, archive older turns, summarize them in the background, and read the originals when details matter. Includes a Python library with no mandatory dependencies and an optional AstrBot adapter.

## What it provides

- **Archive before cooling.** Original request frames survive independently of summaries.
- **Whole-turn partitioning.** Tool calls and results stay together; the active turn is retained. Oversized active text can become a source-linked head/tail excerpt.
- **Background continuity.** Persistent, retryable summary jobs retain source references and unfinished commitments. Historical topics are reference data, not current instructions.
- **Grounded recall.** Literal search and bounded, cursor-based original-message reads stay within the current conversation.
- **Separate identity and conversation scopes.** `IdentityMemory` can share explicitly approved non-sensitive facts across chats for the same authenticated platform account. Facts are private by default; raw group histories are not merged.
- **Model-independent primitives.** Supply your own model callback and matching tokenizer. Budgeting includes tool schemas.

The title is a metaphor, not a fixed character limit, an unlimited-storage claim, or a promise of perfect recall.

## Quick start

Python **3.11+**:

```sh
git clone https://github.com/shabririri418-cell/a-million-words-to-remember-you.git
cd a-million-words-to-remember-you
python -m pip install .
python -m remember_you demo
```

The demo uses **synthetic data, a clearly labeled mock summary, and no network or model credentials**. Temporary files are removed on exit. To keep the demonstration database:

```sh
python -m remember_you demo --data-dir ./var/demo
```

For a real OpenAI-compatible provider, install `python -m pip install '.[openai,tokenizer]'`, set your own `OPENAI_API_KEY` and `CHAT_MODEL`, optionally set `OPENAI_BASE_URL`, `MODEL_TOKENIZER_PATH`, `MODEL_WINDOW_TOKENS`, and `HOT_TARGET_TOKENS`, then run `python examples/openai_chat.py`. This example sends synthetic messages only; real provider calls may incur charges.

## AstrBot installation

Install this repository URL through AstrBot's plugin installer. The plugin name is `astrbot_plugin_remember_you`.

1. Add explicitly authorized `unified_msg_origin` values to `enabled_scopes`; the initial allowlist is empty.
2. Set a verified `model_window_tokens`, a preferred `hot_target_tokens`, and an output reserve. The adapter also caps the window by the provider configuration when available.
3. Prefer a local `tokenizer.json` matching the actual model. Without one, a conservative UTF-8 text estimate is used; it is **not exact model token accounting**, especially for multimodal inputs and provider framing.
4. Set `enabled` to `true`. Unloading restores the original runner method; no host core file is overwritten.

The large-window defaults are a 350,000-token soft hot target, a 1,000,000-token declared model window, and an 8,192-token output reserve. Only use these with a capable model. Configure smaller windows explicitly; the repository title does not establish model capability. The SDK example uses a smaller illustrative configuration.

The adapter targets **AstrBot 4.29.0's native ToolLoopAgentRunner interfaces**. It uses internal extension points, so retest after host upgrades. Other agent runners are not covered. Do not enable it alongside a second hot/cold runner patch that already processes the same requests.

## Storage and privacy

The library writes to paths you supply. The AstrBot adapter uses its plugin data directory for `context_archive.sqlite3` and `hot_state.sqlite3`. There is no hosted storage service. A server deployment can continue when your chat device is off; it cannot operate while its own host is shut down.

Originals and summaries are **plaintext SQLite data**. Operators must handle participants' consent, provider disclosure, permissions, encryption, backups, retention and deletion. A scope is an isolation key, **not authentication**. Identity and scope values must come from a trusted application, never directly from a model or retrieved document. See [privacy and lifecycle](docs/PRIVACY.md).

## Limits

- This is a continuity/context layer, not a vector database, knowledge graph or repackaged LivingMemory UI. External components of the original deployment are credited in [provenance](docs/PROVENANCE.md).
- Summaries can omit or misread facts. Literal search does not understand paraphrases, and source references alone do not prove a summary's claims.
- Request snapshots overlap and consume disk space. There is no hidden deletion policy or infinite storage.
- Large hot contexts trade latency and cost for continuity. No universal ten-second latency guarantee is made.
- Shutdown cancels background work and preserves pending jobs. A later request in the same scope can resume them; there is no automatic sweep of every pending scope at startup.
- Use SQLite's online backup API for active databases; copying only the main file can miss committed WAL contents.

## Development and license

```sh
python -m pip install '.[test]'
python -m unittest discover -s tests -p 'test_*.py'
```

Tests use synthetic fixtures, not production transcripts or credentials. GitHub Actions configuration covers Windows/Linux with Python 3.11/3.12.

MIT, retaining the original implementation's notice. AstrBot, LivingMemory and operator-supplied tokenizer assets retain their own licenses and are not redistributed here.
