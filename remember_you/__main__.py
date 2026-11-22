"""Run a synthetic offline demonstration, never a real conversation export."""

import argparse
import asyncio
import json
import tempfile
from pathlib import Path
from . import ContextArchive, HotState, HotRuntime, UTF8BudgetTokenizer


async def demo(directory):
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    archive = ContextArchive(root / "archive.sqlite3")
    state = HotState(root / "state.sqlite3")
    runtime = HotRuntime(archive, state, UTF8BudgetTokenizer(), target=1800)

    async def synthetic_summary(prompt):
        return json.dumps(
            {
                "summary": "OFFLINE DEMO: older synthetic messages were archived. This is not an LLM-generated summary.",
                "pending": [],
            }
        )

    messages = [
        {
            "role": "system",
            "content": "Current user messages take priority over historical references.",
        },
        {"role": "user", "content": "Alice likes astronomy. " * 150},
        {"role": "assistant", "content": "We discussed a star chart."},
        {"role": "user", "content": "Now let us talk about tea."},
    ]
    try:
        hot = await runtime.process("demo:room", messages, [], [], synthetic_summary)
        tasks = [
            task
            for worker in runtime.workers.values()
            for task in worker.tasks.values()
        ]
        if tasks:
            await asyncio.wait_for(asyncio.gather(*tasks), 10)
        hits = archive.search("demo:room", "astronomy")
        print(
            json.dumps(
                {
                    "mode": "offline synthetic demo; no model or network",
                    "original_messages": len(messages),
                    "hot_messages": len(hot),
                    "latest_message": hot[-1]["content"],
                    "recall_hits": len(hits),
                    "source_frame": hits[0]["frame"] if hits else None,
                    "continuity_ready": bool(state.read("demo:room").get("summary")),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        await runtime.close()


def main():
    parser = argparse.ArgumentParser(description="A Million Words to Remember You")
    parser.add_argument("command", choices=["demo"])
    parser.add_argument("--data-dir")
    args = parser.parse_args()
    if args.data_dir:
        asyncio.run(demo(args.data_dir))
    else:
        with tempfile.TemporaryDirectory(prefix="remember-you-demo-") as folder:
            asyncio.run(demo(folder))


if __name__ == "__main__":
    main()
