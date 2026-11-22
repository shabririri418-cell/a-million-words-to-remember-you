"""Source-backed memory primitives; no platform, model or network imports."""

from .archive import ContextArchive
from .config import MemoryConfig
from .hot_memory import (
    HotRuntime,
    HotState,
    ModelTokenCounter,
    bound_cold_result,
    partition_rounds,
)
from .tokenization import UTF8BudgetTokenizer

__version__ = "0.1.0"
__all__ = [
    "ContextArchive",
    "MemoryConfig",
    "HotRuntime",
    "HotState",
    "ModelTokenCounter",
    "UTF8BudgetTokenizer",
    "partition_rounds",
    "bound_cold_result",
]
