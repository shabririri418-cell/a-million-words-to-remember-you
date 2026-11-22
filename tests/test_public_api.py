import asyncio
import pathlib
import tempfile
import unittest
from remember_you import (
    ContextArchive,
    HotRuntime,
    HotState,
    MemoryConfig,
    UTF8BudgetTokenizer,
)
from remember_you.identity import IdentityMemory


class ArchiveContract(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.archive = ContextArchive(pathlib.Path(self.temp.name) / "memory.sqlite3")

    def test_originals_are_idempotent_and_never_cross_scopes(self):
        rows = [{"role": "user", "content": "private sample", "sender_id": "alice"}]
        frame = self.archive.save("dm:alice", rows)
        self.assertEqual(frame, self.archive.save("dm:alice", rows))
        self.assertEqual(self.archive.read("dm:alice", frame), rows)
        self.assertEqual(self.archive.read("group:demo", frame), [])
        self.assertEqual(self.archive.search("group:demo", "sample"), [])

    def test_pages_and_literal_search(self):
        frame = self.archive.save(
            "a", [{"role": "user", "content": "A" * 9000 + "needle"}]
        )
        self.assertTrue(self.archive.search("a", "needle"))
        self.assertFalse(self.archive.search("a", "%_"))
        page = self.archive.read_page("a", frame, max_chars=100)
        self.assertEqual(len(page["text"]), 100)
        self.assertEqual(page["next_offset"], 100)
        self.assertEqual(self.archive.read_page("b", frame), {})

    def test_scoped_deletion_and_online_backup(self):
        self.archive.save("a", [{"role": "user", "content": "alpha"}])
        self.archive.save("b", [{"role": "user", "content": "bravo"}])
        destination = pathlib.Path(self.temp.name) / "backup.sqlite3"
        self.archive.backup(destination)
        self.archive.delete_scope("a")
        self.assertFalse(self.archive.search("a", "alpha"))
        self.assertTrue(self.archive.search("b", "bravo"))
        self.assertTrue(ContextArchive(destination).search("a", "alpha"))


class IdentityContract(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = IdentityMemory(pathlib.Path(self.temp.name) / "identity.sqlite3")

    def test_same_platform_person_can_share_one_confirmed_fact_across_chats(self):
        self.store.remember(
            "chat",
            "alice",
            "dm:alice",
            "Likes astronomy",
            source="frame-a",
            visibility="shared",
        )
        self.assertEqual(
            self.store.recall("chat", "alice", "group:one")[0]["text"],
            "Likes astronomy",
        )
        self.assertEqual(
            self.store.recall("chat", "alice", "group:two")[0]["source"], "frame-a"
        )
        self.assertEqual(self.store.recall("other-platform", "alice", "group:one"), [])
        self.assertEqual(self.store.recall("chat", "bob", "group:one"), [])

    def test_private_is_default_and_sensitive_is_never_shared(self):
        self.store.remember(
            "chat", "alice", "dm:alice", "A private appointment", source="frame-private"
        )
        self.assertEqual(self.store.recall("chat", "alice", "group:one"), [])
        self.assertEqual(len(self.store.recall("chat", "alice", "dm:alice")), 1)
        with self.assertRaises(ValueError):
            self.store.remember(
                "chat",
                "alice",
                "dm:alice",
                "Appointment",
                source="f",
                visibility="shared",
                sensitive=True,
            )

    def test_sharing_requires_provenance_and_explicit_visibility(self):
        for kwargs in [{"source": ""}, {"source": "frame", "visibility": "public"}]:
            with self.assertRaises(ValueError):
                self.store.remember("chat", "alice", "dm:alice", "fact", **kwargs)

    def test_delete_person_preserves_other_people(self):
        for person in ["alice", "bob"]:
            self.store.remember(
                "chat",
                person,
                "group:demo",
                "Example fact",
                source="frame",
                visibility="shared",
            )
        self.store.delete_person("chat", "alice")
        self.assertEqual(self.store.recall("chat", "alice", "group:demo"), [])
        self.assertTrue(self.store.recall("chat", "bob", "group:demo"))


class ConfigurationContract(unittest.TestCase):
    def test_model_budget_is_validated(self):
        self.assertGreater(MemoryConfig().hot_target_tokens, 0)
        for values in [
            {"hot_target_tokens": 0},
            {"model_window_tokens": 100, "response_reserve_tokens": 100},
            {"hot_target_tokens": True},
        ]:
            with self.assertRaises(ValueError):
                MemoryConfig(**values)

    def test_byte_fallback_never_claims_to_be_a_model_tokenizer(self):
        tokenizer = UTF8BudgetTokenizer()
        self.assertFalse(tokenizer.model_exact)
        self.assertEqual(tokenizer.decode(tokenizer.encode("你好").ids), "你好")


class LifecycleContract(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_same_scope_does_not_create_competing_workers(self):
        with tempfile.TemporaryDirectory() as folder:
            runtime = HotRuntime(
                ContextArchive(pathlib.Path(folder) / "a.sqlite3"),
                HotState(pathlib.Path(folder) / "s.sqlite3"),
                UTF8BudgetTokenizer(),
                target=900,
            )

            async def generate(prompt):
                return '{"summary":"Source-backed example","pending":[]}'

            def records(label):
                return [
                    {"role": "system", "content": "instructions"},
                    {"role": "user", "content": "old " * 1000},
                    {"role": "assistant", "content": "old response"},
                    {"role": "user", "content": label},
                ]

            first, second = await asyncio.gather(
                runtime.process("same", records("first"), [], [], generate),
                runtime.process("same", records("second"), [], [], generate),
            )
            self.assertEqual(runtime.state.read("same")["topic"], "second")
            self.assertEqual(len(runtime.workers), 1)
            await runtime.close()

    async def test_shutdown_preserves_pending_jobs_and_can_resume(self):
        with tempfile.TemporaryDirectory() as folder:
            archive = ContextArchive(pathlib.Path(folder) / "archive.sqlite3")
            state = HotState(pathlib.Path(folder) / "state.sqlite3")
            started = asyncio.Event()

            async def slow(prompt):
                started.set()
                await asyncio.Event().wait()

            runtime = HotRuntime(archive, state, UTF8BudgetTokenizer(), target=1000)
            await runtime.process(
                "group:demo",
                [
                    {"role": "system", "content": "Instructions"},
                    {"role": "user", "content": "old " * 4000},
                    {"role": "assistant", "content": "old answer"},
                    {"role": "user", "content": "new topic"},
                ],
                [],
                [],
                slow,
            )
            await asyncio.wait_for(started.wait(), 1)
            await runtime.close()
            self.assertGreater(
                runtime.workers["group:demo"].pending_count("group:demo"), 0
            )
