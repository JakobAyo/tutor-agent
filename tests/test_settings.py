import pytest

from tutor_agent import paths, settings
from tutor_agent.settings import Settings, SettingsError


def test_defaults_without_file():
    assert settings.load() == Settings()


def test_partial_file_overrides_only_given_keys():
    paths.settings_file().write_text('detect_model = "sonnet"\nmuted = true\nclaude_timeout_s = 30\n')
    s = settings.load()
    assert (s.detect_model, s.muted, s.claude_timeout_s, s.lesson_model) == ("sonnet", True, 30, "sonnet")


@pytest.mark.parametrize("content", ['bogus = 1', 'muted = "yes"', 'claude_timeout_s = true', 'detect_model = ['])
def test_bad_files_raise(content):
    paths.settings_file().write_text(content)
    with pytest.raises(SettingsError):
        settings.load()
