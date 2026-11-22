from dataclasses import dataclass


@dataclass(frozen=True)
class MemoryConfig:
    hot_target_tokens: int = 350_000
    model_window_tokens: int = 1_000_000
    response_reserve_tokens: int = 8192
    summary_timeout_seconds: int = 90
    summary_chunk_tokens: int = 24_000
    max_parallel_summaries: int = 2

    def __post_init__(self):
        for name in (
            "hot_target_tokens",
            "model_window_tokens",
            "summary_timeout_seconds",
            "summary_chunk_tokens",
            "max_parallel_summaries",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(name + " must be a positive integer")
        reserve = self.response_reserve_tokens
        if isinstance(reserve, bool) or not isinstance(reserve, int) or reserve < 0:
            raise ValueError("response_reserve_tokens must be nonnegative")
        if self.model_window_tokens <= reserve:
            raise ValueError("Response reserve must be smaller than the model window")

    @property
    def effective_target(self):
        return min(
            self.hot_target_tokens,
            self.model_window_tokens - self.response_reserve_tokens,
        )
