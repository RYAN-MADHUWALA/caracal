from io import StringIO

from rich.console import Console

from caracal.flow.screens import onboarding


class _WizardStub:
    def __init__(self, context: dict | None = None) -> None:
        self.context = context or {}
        self.console = Console(file=StringIO(), force_terminal=False, width=120)


def test_step_principal_skips_for_existing_workspace() -> None:
    wizard = _WizardStub({"workspace_existing": True})

    result = onboarding._step_principal(wizard)

    assert result is None
    assert "first_principal" not in wizard.context


def test_step_principal_collects_identity_for_new_workspace(monkeypatch) -> None:
    wizard = _WizardStub({"workspace_existing": False})

    monkeypatch.setattr(onboarding.FlowPrompt, "select", lambda self, *args, **kwargs: "human")

    def _fake_text(self, label: str, **kwargs):
        if label == "Principal name":
            return "alice"
        if label == "Owner email":
            return "alice@example.com"
        raise AssertionError(f"Unexpected prompt label: {label}")

    monkeypatch.setattr(onboarding.FlowPrompt, "text", _fake_text)

    result = onboarding._step_principal(wizard)

    assert result == {
        "name": "alice",
        "owner": "alice@example.com",
        "kind": "human",
    }
    assert wizard.context["first_principal"] == result
