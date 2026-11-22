# 接入 / Integration

## Core API

```python
from remember_you import ContextArchive, HotState, HotRuntime, MemoryConfig
from remember_you.tokenization import load_tokenizer

config = MemoryConfig()
tokenizer = load_tokenizer()  # conservative fallback; supply a model tokenizer path
archive = ContextArchive("var/archive.sqlite3")
state = HotState("var/state.sqlite3")
runtime = HotRuntime(
    archive, state, tokenizer,
    target=config.effective_target,
    max_parallel_summaries=config.max_parallel_summaries,
    summary_timeout=config.summary_timeout_seconds,
    chunk_tokens=config.summary_chunk_tokens,
)
```

在应用自己的 async 生命周期内调用 / inside your application's async lifecycle:

```python
hot = await runtime.process(
    scope=authenticated_conversation_id,
    messages=provider_messages,
    tools=provider_tool_schemas,
    extra=provider_extra_content,
    generate=async_summary_callback,
)
# Send `hot` to the provider. This library does not call your chat API for you.
# On shutdown:
await runtime.close()
```

`async_summary_callback(prompt)` returns JSON text with `summary: str` and `pending: list[str]`. Use a real model in production; the CLI's fixed summary exists solely to demonstrate the offline workflow. A failed callback leaves the queued job retryable. The callback must cooperate with asyncio cancellation. Sync archive/state methods perform local SQLite IO; the runtime moves foreground storage operations to threads. Same-scope processing is serialized; background summary concurrency is bounded globally per runtime.

`ModelTokenCounter` counts the currently supplied text request plus tool/extra framing with a safety factor, not stale usage from the previous reply. It does not guarantee provider-equivalent multimodal accounting. The soft target does not authorize exceeding an actual model limit; fixed instructions and protocol structure may require a larger budget or application-level handling.

## Source recall

```python
hits = archive.search(authenticated_scope, "literal clue", limit=3)
page = archive.read_page(
    authenticated_scope,
    hits[0]["frame"],
    position=hits[0]["position"],
    offset=0,
)
# Continue with page["next_offset"] until it is None.
```

Each page is part of an original JSON message, so a page boundary can split JSON syntax. It is evidence text, not necessarily a standalone parsable object. A guessed frame identifier from another scope cannot be read with the current scope. Applications must still authenticate callers and bind their scope server-side.

## Identity facts

```python
from remember_you.identity import IdentityMemory

facts = IdentityMemory("var/identity.sqlite3")
facts.remember(
    "example-platform", "alice", "dm:alice", "Enjoys astronomy",
    source="verified-source-reference", visibility="shared",
)
facts.recall("example-platform", "alice", "group:observatory")
```

`visibility` defaults to `private`; the example explicitly opts into sharing. `sensitive=True` cannot be combined with `shared`. This flag is **not an automatic PII or calendar detector**: trusted ingestion must classify sensitive facts and obtain consent. This generalized API deliberately replaces the original deployment's one-owner hardcoding; it does not copy private regexes, profiles or agenda data. It is not automatically exposed as a model write tool by the AstrBot adapter.

## AstrBot extension boundary

`RunnerBridge.install()` wraps the native runner's `step` and, during each opted-in step, intercepts that instance's context-manager `process` call. This runs after the host's begin hooks, archives tool-loop frames, and retains checkpoint metadata when rebuilding host messages. Temporary manager settings are restored after processing; `uninstall()` restores its own class patch without replacing a newer owner's patch. Keep one bridge per runner class.

Archive tools derive the scope from `event.unified_msg_origin`; their model-facing arguments never accept an arbitrary target scope. The adapter supplies only source search/read tools and continuity guidance; it does not change the host's wake-up rules or persona. Test other memory/compression plugins for duplicate processing before combining them.
