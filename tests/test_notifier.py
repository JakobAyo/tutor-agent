from tutor_agent import notifier, paths
from tutor_agent.store import Concept


def concept(name, category="Testing"):
    return Concept(id=name.lower(), name=name, category=category, summary="s")


def test_one_notification_names_all_concepts(fake_notify):
    assert notifier.notify([concept("Fakes"), concept("Canary run")], muted=False)
    [argv] = fake_notify.calls
    assert argv[0] == "--app-name=Tutor"
    assert argv[-2] == "2 new concepts to learn"
    assert argv[-1] == "• Fakes (Testing)\n• Canary run (Testing)"


def test_singular_title():
    assert notifier.message([concept("Fakes")])[0] == "1 new concept to learn"


def test_muted_sends_nothing(fake_notify):
    assert not notifier.notify([concept("Fakes")], muted=True)
    assert fake_notify.calls == []
    assert "muted" in paths.log_file().read_text()


def test_nothing_new_sends_nothing(fake_notify):
    assert not notifier.notify([], muted=False)
    assert fake_notify.calls == []


def test_missing_notify_send_is_logged_not_raised(tmp_path):
    assert not notifier.notify([concept("Fakes")], muted=False, notify_bin=str(tmp_path / "nope"))
    assert "notification failed" in paths.log_file().read_text()
