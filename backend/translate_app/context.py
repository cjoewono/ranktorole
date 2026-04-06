from __future__ import annotations


class DecisionsLog:
    """Tracks bullet-level approve/reject decisions. Never pruned."""

    def __init__(self) -> None:
        self._entries: list[dict] = []

    def approve(self, bullet: str, section: str, reasoning: str) -> None:
        self._entries.append(
            {"action": "approve", "bullet": bullet, "section": section, "reasoning": reasoning}
        )

    def reject(self, bullet: str, reason: str) -> None:
        self._entries.append({"action": "reject", "bullet": bullet, "reason": reason})

    def to_prompt_block(self) -> str:
        if not self._entries:
            return ""
        lines = ["Decisions log:"]
        for entry in self._entries:
            if entry["action"] == "approve":
                lines.append(
                    f"  APPROVED [{entry['section']}]: {entry['bullet']} — {entry['reasoning']}"
                )
            else:
                lines.append(f"  REJECTED: {entry['bullet']} — {entry['reason']}")
        return "\n".join(lines)

    def token_estimate(self) -> int:
        return len(self.to_prompt_block()) // 4


class RollingChatWindow:
    """Rolling chat history. Prunes oldest turns first; always retains min 2 turns."""

    MAX_TOKENS = 2000

    def __init__(self) -> None:
        self._turns: list[dict] = []

    def add_turn(self, role: str, content: str) -> None:
        self._turns.append({"role": role, "content": content})
        self._prune()

    def _token_count(self) -> int:
        return sum(len(t["content"]) for t in self._turns) // 4

    def _prune(self) -> None:
        while self._token_count() > self.MAX_TOKENS and len(self._turns) > 2:
            self._turns.pop(0)

    def to_messages(self) -> list[dict]:
        return list(self._turns)
