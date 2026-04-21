from app.application.context import RequestContext
from app.application.contracts import ApplicationInteraction, ApplicationResult


def test_request_context_shape():
    ctx = RequestContext("123", "telegram", "s1", "UTC", "trace", locale="en")

    assert ctx.actor_id == "123"
    assert ctx.channel == "telegram"
    assert ctx.locale == "en"


def test_application_result_and_interaction():
    interaction = ApplicationInteraction(kind="clarification", choices=["A", "B"])
    result = ApplicationResult(
        kind="needs_clarification", message="Pick one", interaction=interaction
    )

    assert result.kind == "needs_clarification"
    assert result.interaction.kind == "clarification"
