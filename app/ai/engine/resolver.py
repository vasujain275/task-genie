from __future__ import annotations

from dataclasses import dataclass


def normalize_text(value: str) -> str:
    return " ".join(value.lower().strip().split())


@dataclass(frozen=True)
class TaskCandidate:
    task_id: str
    title: str
    status: str | None = None


@dataclass(frozen=True)
class ResolutionResult:
    matched: TaskCandidate | None
    candidates: list[TaskCandidate]

    @property
    def ambiguous(self) -> bool:
        return len(self.candidates) > 1


class TaskReferenceResolver:
    def __init__(self, task_query):
        self._task_query = task_query

    async def resolve(self, user_id: int, reference: str) -> ResolutionResult:
        tasks = await self._task_query(user_id)
        normalized_reference = normalize_text(reference)

        candidates: list[tuple[int, TaskCandidate]] = []
        for task in tasks:
            candidate = TaskCandidate(
                task_id=str(getattr(task, "id", "")),
                title=str(getattr(task, "title", "")),
                status=getattr(task, "status", None),
            )
            title = normalize_text(candidate.title)
            score = 0
            if candidate.task_id == reference:
                score = 120
            elif title == normalized_reference:
                score = 100
            elif title.startswith(normalized_reference):
                score = 80
            elif normalized_reference in title:
                score = 60
            if score:
                candidates.append((score, candidate))

        if not candidates:
            return ResolutionResult(matched=None, candidates=[])

        candidates.sort(
            key=lambda item: (-item[0], item[1].title.lower(), item[1].task_id)
        )
        best_score = candidates[0][0]
        best_candidates = [
            candidate for score, candidate in candidates if score == best_score
        ]
        matched = best_candidates[0] if len(best_candidates) == 1 else None
        return ResolutionResult(matched=matched, candidates=best_candidates)
