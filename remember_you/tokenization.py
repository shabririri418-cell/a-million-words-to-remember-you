"""A conservative text-only fallback; use your model's actual tokenizer instead."""

from types import SimpleNamespace


class UTF8BudgetTokenizer:
    model_exact = False

    def encode(self, text, add_special_tokens=False):
        return SimpleNamespace(ids=list(str(text).encode("utf8")))

    def decode(self, ids):
        return bytes(ids).decode("utf8", errors="ignore")


def load_tokenizer(path=None):
    if path:
        from tokenizers import Tokenizer

        return Tokenizer.from_file(str(path))
    return UTF8BudgetTokenizer()
