import pytest

from syosint.telegram_session import TelegramSettings, safe_auth_state, session_path


def test_missing_credentials_is_not_configured(monkeypatch, tmp_path):
    monkeypatch.delenv("SYOSINT_TELEGRAM_API_ID", raising=False)
    monkeypatch.delenv("SYOSINT_TELEGRAM_API_HASH", raising=False)

    settings = TelegramSettings.load(private_dir=tmp_path)

    assert not settings.configured
    assert safe_auth_state(settings) == "not-configured"


def test_session_path_stays_under_private_directory(monkeypatch, tmp_path):
    monkeypatch.setenv("SYOSINT_TELEGRAM_API_ID", "12345")
    monkeypatch.setenv("SYOSINT_TELEGRAM_API_HASH", "example-hash")
    settings = TelegramSettings.load(private_dir=tmp_path)

    assert settings.configured
    assert session_path(settings) == tmp_path / "telegram" / "syosint.session"


def test_configured_session_file_does_not_prove_network_auth(monkeypatch, tmp_path):
    monkeypatch.setenv("SYOSINT_TELEGRAM_API_ID", "12345")
    monkeypatch.setenv("SYOSINT_TELEGRAM_API_HASH", "example-hash")
    settings = TelegramSettings.load(private_dir=tmp_path)
    (tmp_path / "telegram").mkdir()
    (tmp_path / "telegram" / "syosint.session").touch()

    assert safe_auth_state(settings) == "reauthentication-required"


def test_private_dir_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("SYOSINT_PRIVATE_DIR", str(tmp_path))
    settings = TelegramSettings.load()

    assert settings.private_dir == tmp_path


@pytest.mark.parametrize("api_id", ["nope", "0", "-3"])
def test_invalid_api_id_does_not_expose_input(monkeypatch, tmp_path, api_id):
    monkeypatch.setenv("SYOSINT_TELEGRAM_API_ID", api_id)

    with pytest.raises(
        ValueError, match="SYOSINT_TELEGRAM_API_ID must be a positive integer"
    ) as exc:
        TelegramSettings.load(private_dir=tmp_path)
    assert api_id not in str(exc.value)


def test_symlinked_session_directory_cannot_escape_private_directory(tmp_path):
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    (tmp_path / "telegram").symlink_to(outside, target_is_directory=True)
    settings = TelegramSettings(api_id=12345, api_hash="example-hash", private_dir=tmp_path)

    with pytest.raises(ValueError, match="outside private directory"):
        session_path(settings)
