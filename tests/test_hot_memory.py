import importlib.util
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "hot_memory", ROOT / "remember_you/hot_memory.py"
)


class HotMemoryTest(unittest.TestCase):
    def setUp(self):
        self.m = importlib.util.module_from_spec(SPEC)
        SPEC.loader.exec_module(self.m)

    def count(self, messages):
        return sum(len(str(x)) for x in messages)

    def test_no_premature_compression(self):
        messages = [
            {"role": "system", "content": "人设"},
            {"role": "user", "content": "旧话题"},
            {"role": "assistant", "content": "回应"},
            {"role": "user", "content": "新话题"},
        ]
        hot, cold = self.m.partition_rounds(messages, self.count, 10000)
        self.assertEqual(hot, messages)
        self.assertFalse(cold)

    def test_cold_keeps_whole_tool_round_and_latest_user(self):
        messages = [
            {"role": "system", "content": "人设"},
            {"role": "user", "content": "旧" * 1000},
            {"role": "assistant", "tool_calls": [{"id": "a"}]},
            {"role": "tool", "tool_call_id": "a", "content": "结果"},
            {"role": "user", "content": "新话题"},
        ]
        hot, cold = self.m.partition_rounds(messages, self.count, 500)
        self.assertEqual([x["role"] for x in cold], ["user", "assistant", "tool"])
        self.assertEqual(hot[-1]["content"], "新话题")
        self.assertEqual(hot[0]["role"], "system")

    def test_fixed_part_cannot_discard_latest_or_raise_byte_error(self):
        messages = [
            {"role": "system", "content": "人设" * 1000},
            {"role": "user", "content": "最新问题"},
        ]
        hot, cold = self.m.partition_rounds(messages, self.count, 500)
        self.assertEqual(hot, messages)
        self.assertEqual(cold, [])

    def test_topic_updates_and_scope_survives_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            store = self.m.HotState(pathlib.Path(folder) / "state.db")
            store.update_topic("group", "旧话题")
            store.update_topic("group", "新话题")
            store.save_summary(
                "group",
                "带来源的旧事",
                [{"text": "未完成的约定", "source": "frame1"}],
                "frame1",
            )
            again = self.m.HotState(store.path)
            self.assertEqual(again.read("group")["topic"], "新话题")
            self.assertEqual(again.read("private"), {})
            self.assertEqual(again.read("group")["pending"][0]["source"], "frame1")


class PartitionEfficiencyTest(unittest.TestCase):
    def test_large_history_uses_logarithmic_budget_checks(self):
        m = importlib.util.module_from_spec(SPEC)
        SPEC.loader.exec_module(m)
        calls = []

        def count(messages):
            calls.append(1)
            return len(messages) * 10

        messages = [{"role": "user", "content": str(i)} for i in range(1000)]
        hot, cold = m.partition_rounds(messages, count, 1000)
        self.assertLessEqual(len(calls), 15)
        self.assertEqual(len(hot), 100)
        self.assertEqual(len(cold), 900)


class ContinuityWorkerTest(unittest.IsolatedAsyncioTestCase):
    async def test_async_summary_keeps_topic_and_recovers_pending_job(self):
        import asyncio

        m = importlib.util.module_from_spec(SPEC)
        SPEC.loader.exec_module(m)
        with tempfile.TemporaryDirectory() as folder:
            state = m.HotState(pathlib.Path(folder) / "state.db")
            state.update_topic("group", "新话题")
            gate = asyncio.Event()

            async def generate(prompt):
                await gate.wait()
                return '{"summary":"person-a说下次唱测试歌曲","pending":["还未唱测试歌曲"]}'

            worker = m.ContinuityWorker(
                state, generate, lambda messages: len(str(messages))
            )
            await worker.enqueue(
                "group", "frame1", [{"role": "user", "content": "下次唱测试歌曲"}]
            )
            self.assertEqual(state.read("group")["topic"], "新话题")
            self.assertNotIn("summary", state.read("other"))
            gate.set()
            await worker.tasks["group"]
            self.assertEqual(state.read("group")["pending"][0]["source"], "frame1")
            self.assertEqual(state.read("group")["topic"], "新话题")

    async def test_failed_summary_remains_retryable(self):
        m = importlib.util.module_from_spec(SPEC)
        SPEC.loader.exec_module(m)
        with tempfile.TemporaryDirectory() as folder:
            state = m.HotState(pathlib.Path(folder) / "state.db")

            async def fail(prompt):
                raise RuntimeError("temporary outage")

            worker = m.ContinuityWorker(state, fail, lambda x: len(str(x)))
            await worker.enqueue(
                "group", "frame2", [{"role": "user", "content": "约定"}]
            )
            await worker.tasks["group"]
            self.assertEqual(worker.pending_count("group"), 1)
            self.assertEqual(state.read("group"), {})


class RuntimeTest(unittest.IsolatedAsyncioTestCase):
    async def test_cooling_is_nonblocking_and_latest_topic_wins(self):
        import asyncio
        import types

        m = importlib.util.module_from_spec(SPEC)
        SPEC.loader.exec_module(m)
        with tempfile.TemporaryDirectory() as folder:
            state = m.HotState(pathlib.Path(folder) / "state.db")
            saved = []
            archive = types.SimpleNamespace(
                save=lambda scope, records: saved.append((scope, records)) or "frame"
            )
            tokenizer = types.SimpleNamespace(
                encode=lambda text, **kw: types.SimpleNamespace(ids=list(text))
            )
            gate = asyncio.Event()

            async def generate(prompt):
                await gate.wait()
                return '{"summary":"旧约定未完成","pending":["旧约定"]}'

            runtime = m.HotRuntime(archive, state, tokenizer, target=500)
            messages = [
                {"role": "system", "content": "人设"},
                {"role": "user", "content": "旧" * 1000},
                {"role": "assistant", "content": "旧回答"},
                {"role": "user", "content": "现在换话题：晴天"},
            ]
            hot = await asyncio.wait_for(
                runtime.process("group", messages, [], [], generate), timeout=1
            )
            self.assertEqual(hot[-1]["content"], "现在换话题：晴天")
            self.assertEqual(state.read("group")["topic"], "现在换话题：晴天")
            gate.set()
            await runtime.workers["group"].tasks["group"]
            self.assertEqual(state.read("group")["topic"], "现在换话题：晴天")
            self.assertTrue(saved)
            self.assertEqual(state.read("private"), {})


class RecoveryTest(unittest.IsolatedAsyncioTestCase):
    async def test_failed_job_resumes_after_restart(self):
        m = importlib.util.module_from_spec(SPEC)
        SPEC.loader.exec_module(m)
        with tempfile.TemporaryDirectory() as folder:
            state = m.HotState(pathlib.Path(folder) / "state.db")

            async def fail(prompt):
                raise RuntimeError("outage")

            first = m.ContinuityWorker(state, fail, lambda x: len(str(x)))
            await first.enqueue("group", "f", [{"role": "user", "content": "约定"}])
            await first.tasks["group"]

            async def success(prompt):
                return '{"summary":"约定尚未完成","pending":["约定"]}'

            second = m.ContinuityWorker(
                m.HotState(state.path), success, lambda x: len(str(x))
            )
            await second.enqueue("group", "f", [{"role": "user", "content": "约定"}])
            await second.tasks["group"]
            self.assertEqual(second.pending_count("group"), 0)
            self.assertEqual(state.read("group")["pending"][0]["text"], "约定")


class HugeActiveTurnTest(unittest.TestCase):
    def test_clips_text_with_source_and_preserves_tool_ids(self):
        import types

        m = importlib.util.module_from_spec(SPEC)
        SPEC.loader.exec_module(m)
        tok = types.SimpleNamespace(
            encode=lambda text, **kw: types.SimpleNamespace(ids=list(text)),
            decode=lambda ids: "".join(ids),
        )
        messages = [
            {"role": "system", "content": "人设"},
            {"role": "user", "content": "查资料"},
            {"role": "assistant", "tool_calls": [{"id": "a"}]},
            {
                "role": "tool",
                "tool_call_id": "a",
                "content": "前" * 10000 + "尾部重要信息",
            },
        ]
        counter = m.ModelTokenCounter(tok, safety_factor=1)
        out = m.clip_active_text(messages, counter, tok, 2000, "frame123")
        self.assertLessEqual(counter.count_tokens(out), 2000)
        self.assertEqual(out[-1]["tool_call_id"], "a")
        self.assertIn("frame123", out[-1]["content"])
        self.assertIn("尾部重要信息", out[-1]["content"])
        self.assertEqual(len(messages[-1]["content"]), 10006)


class ColdBudgetTest(unittest.TestCase):
    def test_budget_preserves_source_and_page_offset(self):
        import types

        m = importlib.util.module_from_spec(SPEC)
        SPEC.loader.exec_module(m)
        tokenizer = types.SimpleNamespace(
            encode=lambda text, **kw: types.SimpleNamespace(ids=list(text))
        )
        page = {
            "frame": "source",
            "position": 3,
            "offset": 500,
            "text": "原" * 10000,
            "next_offset": 10500,
        }
        out = m.bound_cold_result(page, 1000, tokenizer)
        self.assertLessEqual(
            len(__import__("json").dumps(out, ensure_ascii=False)), 1000
        )
        self.assertEqual(out["frame"], "source")
        self.assertEqual(out["next_offset"], 500 + len(out["text"]))
