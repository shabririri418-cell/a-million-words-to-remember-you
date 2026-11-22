import pathlib
import tempfile
import types
import unittest
from remember_you import (
    ContextArchive,
    HotRuntime,
    HotState,
    MemoryConfig,
    UTF8BudgetTokenizer,
)
from remember_you.astrbot_bridge import RunnerBridge


class BridgeContract(unittest.IsolatedAsyncioTestCase):
    async def test_every_tool_step_is_archived_and_patch_is_restored(self):
        with tempfile.TemporaryDirectory() as folder:
            archive = ContextArchive(pathlib.Path(folder) / "a.sqlite3")
            state = HotState(pathlib.Path(folder) / "s.sqlite3")
            runtime = HotRuntime(archive, state, UTF8BudgetTokenizer(), target=2000)
            calls = []

            async def process(messages, **kw):
                calls.append(messages)
                return messages

            manager = types.SimpleNamespace(
                process=process,
                config=types.SimpleNamespace(
                    max_context_tokens=5000, enforce_max_turns=10
                ),
                token_counter=None,
            )

            class Runner:
                async def step(self):
                    self.run_context.messages = (
                        await self.request_context_manager.process(
                            self.run_context.messages, trusted_token_usage=999999
                        )
                    )
                    yield "step"

            runner = Runner()
            runner.request_context_manager = manager
            runner.run_context = types.SimpleNamespace(
                context=types.SimpleNamespace(
                    event=types.SimpleNamespace(unified_msg_origin="chat:one")
                ),
                messages=[
                    {"role": "system", "content": "instructions"},
                    {"role": "user", "content": "current topic"},
                ],
            )
            runner.provider = types.SimpleNamespace(
                provider_config={"max_context_tokens": 5000}
            )
            runner.req = types.SimpleNamespace(extra_user_content_parts=[])
            runner._func_tool_for_provider = lambda: None

            async def generate(prompt):
                return '{"summary":"Older context","pending":[]}'

            bridge = RunnerBridge(
                runtime,
                MemoryConfig(
                    hot_target_tokens=2000,
                    model_window_tokens=5000,
                    response_reserve_tokens=1000,
                ),
                {"chat:one"},
                generate_factory=lambda r: generate,
            )
            original = Runner.step
            bridge.install(Runner, lambda value: value)
            try:
                self.assertEqual([x async for x in runner.step()], ["step"])
                runner.run_context.messages += [
                    {"role": "assistant", "tool_calls": [{"id": "call-a"}]},
                    {
                        "role": "tool",
                        "tool_call_id": "call-a",
                        "content": "exact tool result",
                    },
                ]
                self.assertEqual([x async for x in runner.step()], ["step"])
                self.assertTrue(archive.search("chat:one", "exact tool result"))
                self.assertFalse(archive.search("chat:two", "exact tool result"))
                self.assertIs(manager.process, process)
                self.assertEqual(manager.config.max_context_tokens, 5000)
            finally:
                bridge.uninstall()
                await runtime.close()
            self.assertIs(Runner.step, original)
            self.assertEqual(len(calls), 2)

    async def test_other_scopes_never_invoke_archive(self):
        class Runner:
            async def step(self):
                yield "untouched"

        runner = Runner()
        runner.run_context = types.SimpleNamespace(
            context=types.SimpleNamespace(
                event=types.SimpleNamespace(unified_msg_origin="unconfigured")
            )
        )
        bridge = RunnerBridge(None, MemoryConfig(), set())
        bridge.install(Runner, lambda value: value)
        try:
            self.assertEqual([x async for x in runner.step()], ["untouched"])
        finally:
            bridge.uninstall()
