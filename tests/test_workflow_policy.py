from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def test_active_workflows_use_node24_compatible_action_majors():
    expected = {
        "actions/checkout": 7,
        "actions/setup-node": 7,
        "actions/setup-python": 7,
        "actions/upload-artifact": 7,
    }
    for path in sorted(WORKFLOWS.glob("*.yml")):
        source = path.read_text(encoding="utf-8")
        for action, major in expected.items():
            for match in re.finditer(rf"uses:\s*{re.escape(action)}@(v\d+)", source):
                assert match.group(1) == f"v{major}", (
                    f"{path.name} still uses {action}@{match.group(1)}; "
                    f"expected the Node 24-compatible v{major} line"
                )
        if "actions/setup-node@" in source:
            assert "package-manager-cache: false" in source, (
                f"{path.name} must not enable implicit npm caching in CI"
            )


def test_main_build_and_chat_checks_do_not_use_pull_requests_or_feature_branches():
    master = (WORKFLOWS / "master.yml").read_text(encoding="utf-8")
    chat = (WORKFLOWS / "chat-check.yml").read_text(encoding="utf-8")

    assert re.search(r"(?m)^\s*pull_request\s*:", master) is None
    assert re.search(r"(?m)^\s*pull_request\s*:", chat) is None
    assert "branches: [main]" in master
    assert "branches: [main]" in chat
    assert "feature/" not in chat
    assert "Chat checks are main-only" in chat

def test_every_manually_dispatchable_workflow_refuses_non_main_refs():
    for path in sorted(WORKFLOWS.glob("*.yml")):
        source = path.read_text(encoding="utf-8")
        if re.search(r"(?m)^\\s*workflow_dispatch\\s*:", source):
            assert "main-only; refusing ref" in source, (
                f"{path.name} allows manual execution without a main-branch guard"
            )
