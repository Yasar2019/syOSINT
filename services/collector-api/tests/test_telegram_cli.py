import asyncio
import stat

import pytest
from telethon.errors import SessionPasswordNeededError

from syosint.telegram_cli import TerminalPrompts, run_cli
from syosint.telegram_client import TelethonAuthClient
from syosint.telegram_session import TelegramSettings


@pytest.fixture
def settings(tmp_path):
    return TelegramSettings(12345, "synthetic-api-hash", tmp_path / "private-data")


class Prompts:
    def __init__(self, interactive=True, confirmed=True):
        self.interactive = interactive
        self.confirmed = confirmed
        self.labels = []

    def is_interactive(self):
        return self.interactive

    def secret(self, label):
        self.labels.append(label)
        return {
            "Phone: ": "+15555550123",
            "Code: ": "synthetic-code",
            "Two-factor password: ": "synthetic-password",
        }[label]

    def confirm_logout(self):
        self.labels.append("confirm")
        return self.confirmed


class FakeClient:
    def __init__(self, authorized=False, failure=None, login_authorizes=True):
        self.authorized = authorized
        self.failure = failure
        self.login_authorizes = login_authorizes
        self.disconnected = False

    async def is_authorized(self):
        if self.failure:
            raise self.failure
        return self.authorized

    async def start(self, phone, code_callback, password_callback):
        assert phone == "+15555550123"
        assert code_callback() == "synthetic-code"
        assert password_callback() == "synthetic-password"
        self.authorized = self.login_authorizes

    async def disconnect(self):
        self.disconnected = True


def test_status_verifies_authorization_without_printing_identity(settings, capsys):
    client = FakeClient(authorized=True)
    assert run_cli(["status"], settings=settings, client=client) == 0
    assert capsys.readouterr() == ("authenticated\n", "")
    assert client.disconnected


def test_existing_file_does_not_prove_authorization(settings, capsys):
    directory = settings.private_dir / "telegram"
    directory.mkdir(parents=True)
    (directory / "syosint.session").touch()
    assert run_cli(["status"], settings=settings, client=FakeClient()) == 1
    assert capsys.readouterr() == ("reauthentication-required\n", "")


def test_unconfigured_status_does_not_construct_client(settings, capsys, monkeypatch):
    import syosint.telegram_cli as cli

    def forbidden(*args):
        pytest.fail("unconfigured client must not be constructed")

    monkeypatch.setattr(cli, "TelethonAuthClient", forbidden)
    missing = TelegramSettings(None, None, settings.private_dir)
    assert run_cli(["status"], settings=missing) == 1
    assert capsys.readouterr() == ("not-configured\n", "")
    assert not settings.private_dir.exists()


def test_login_uses_secret_callbacks_and_secures_session(settings, capsys):
    prompts = Prompts()
    client = FakeClient()
    assert run_cli(["login"], settings=settings, client=client, prompts=prompts) == 0
    assert prompts.labels == ["Phone: ", "Code: ", "Two-factor password: "]
    assert capsys.readouterr() == ("authenticated\n", "")
    assert client.disconnected
    directory = settings.private_dir / "telegram"
    assert stat.S_IMODE(directory.stat().st_mode) == 0o700
    assert stat.S_IMODE((directory / "syosint.session").stat().st_mode) == 0o600


def test_login_rechecks_authorization(settings, capsys):
    assert run_cli(["login"], settings=settings, client=FakeClient(login_authorizes=False), prompts=Prompts()) == 1
    assert capsys.readouterr() == ("reauthentication-required\n", "")


@pytest.mark.parametrize("command", ["login", "logout"])
def test_mutating_commands_require_terminal(settings, capsys, command):
    prompts = Prompts(interactive=False)
    assert run_cli([command], settings=settings, client=FakeClient(), prompts=prompts) == 1
    assert capsys.readouterr() == ("interactive-required\n", "")
    assert prompts.labels == []
    assert not settings.private_dir.exists()


def test_already_authenticated_login_never_prompts(settings, capsys):
    prompts = Prompts()
    assert run_cli(["login"], settings=settings, client=FakeClient(True), prompts=prompts) == 0
    assert prompts.labels == []
    assert capsys.readouterr() == ("authenticated\n", "")


@pytest.mark.parametrize("failure", [RuntimeError("synthetic-secret"), KeyboardInterrupt()])
def test_auth_errors_are_redacted_and_disconnect(settings, capsys, failure):
    client = FakeClient(failure=failure)
    assert run_cli(["status"], settings=settings, client=client) == 1
    assert capsys.readouterr() == ("reauthentication-required\n", "")
    assert client.disconnected


def test_logout_removes_only_own_files_without_credentials(settings, capsys):
    directory = settings.private_dir / "telegram"
    directory.mkdir(parents=True)
    owned = [directory / ("syosint.session" + suffix) for suffix in ("", "-journal", "-wal", "-shm")]
    unrelated = [directory / "other.session", directory / "syosint.session.backup", directory / "media"]
    for path in owned + unrelated:
        path.write_text("synthetic-fixture")
    missing = TelegramSettings(None, None, settings.private_dir)
    assert run_cli(["logout"], settings=missing, prompts=Prompts()) == 0
    assert all(not path.exists() for path in owned)
    assert all(path.read_text() == "synthetic-fixture" for path in unrelated)
    assert capsys.readouterr() == ("logged-out\n", "")


def test_logout_cancellation_preserves_session(settings, capsys):
    directory = settings.private_dir / "telegram"
    directory.mkdir(parents=True)
    path = directory / "syosint.session"
    path.write_text("synthetic-fixture")
    assert run_cli(["logout"], settings=settings, prompts=Prompts(confirmed=False)) == 1
    assert path.read_text() == "synthetic-fixture"
    assert capsys.readouterr() == ("cancelled\n", "")


@pytest.mark.parametrize("command", ["login", "status", "logout"])
@pytest.mark.parametrize("link_target", ["directory", "session", "sidecar"])
def test_symlinks_are_rejected_without_touching_targets(settings, tmp_path, capsys, command, link_target):
    outside = tmp_path / "outside"
    outside.mkdir()
    target = outside / "valuable"
    target.write_text("preserve")
    directory = settings.private_dir / "telegram"
    settings.private_dir.mkdir()
    if link_target == "directory":
        directory.symlink_to(outside, target_is_directory=True)
    else:
        directory.mkdir()
        name = "syosint.session" if link_target == "session" else "syosint.session-wal"
        (directory / name).symlink_to(target)
    assert run_cli([command], settings=settings, client=FakeClient(True), prompts=Prompts()) == 1
    assert target.read_text() == "preserve"
    assert capsys.readouterr() == ("session-unavailable\n", "")


def test_unknown_arguments_are_not_echoed(settings, capsys):
    assert run_cli(["login", "synthetic-secret"], settings=settings) == 2
    assert capsys.readouterr() == ("invalid-command\n", "")


def test_terminal_secret_uses_getpass(monkeypatch):
    import syosint.telegram_cli as cli

    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt: "synthetic-secret")
    assert TerminalPrompts().secret("Code: ") == "synthetic-secret"


class FakeTransport:
    def __init__(self, two_factor=False):
        self.connected = False
        self.authorized = False
        self.two_factor = two_factor

    async def connect(self):
        self.connected = True

    async def is_user_authorized(self):
        assert self.connected
        return self.authorized

    async def send_code_request(self, phone):
        assert phone == "+15555550123"

    async def sign_in(self, *, phone=None, code=None, password=None):
        if password is not None:
            assert password == "synthetic-password"
        else:
            assert phone == "+15555550123"
            assert code == "synthetic-code"
            if self.two_factor:
                raise SessionPasswordNeededError(request=None)
        self.authorized = True

    async def disconnect(self):
        self.connected = False


@pytest.mark.parametrize("two_factor", [False, True])
def test_adapter_signs_in_without_telethon_identity_output(settings, capsys, two_factor):
    transport = FakeTransport(two_factor)
    client = TelethonAuthClient(settings, transport=transport)

    async def authenticate():
        assert not await client.is_authorized()
        await client.start("+15555550123", lambda: "synthetic-code", lambda: "synthetic-password")
        assert await client.is_authorized()
        await client.disconnect()

    asyncio.run(authenticate())
    assert not transport.connected
    assert capsys.readouterr() == ("", "")


def test_main_routes_telegram_commands_without_starting_server(monkeypatch):
    import syosint.__main__ as main
    import syosint.telegram_cli as cli

    monkeypatch.setattr(cli, "run_cli", lambda argv: 17 if argv == ["status"] else 99)
    assert main.main(["telegram", "status"]) == 17


def test_adapter_suppresses_sdk_child_logs(settings, monkeypatch, caplog):
    import syosint.telegram_client as adapter

    def constructor(*args, **kwargs):
        kwargs["base_logger"].getChild("network").warning("synthetic-sensitive-error")
        return FakeTransport()

    monkeypatch.setattr(adapter, "TelegramClient", constructor)
    TelethonAuthClient(settings)
    assert "synthetic-sensitive-error" not in caplog.text


def test_terminal_secret_refuses_echo_fallback(monkeypatch):
    import syosint.telegram_cli as cli
    import warnings

    def fallback(prompt):
        warnings.warn("echo-unavailable", cli.getpass.GetPassWarning)
        pytest.fail("must not continue with echoed input")

    monkeypatch.setattr(cli.getpass, "getpass", fallback)
    with pytest.raises(cli.getpass.GetPassWarning):
        TerminalPrompts().secret("Code: ")


def test_logout_rejects_hardlinks_before_deleting_anything(settings, tmp_path, capsys):
    directory = settings.private_dir / "telegram"
    directory.mkdir(parents=True)
    session = directory / "syosint.session"
    session.write_text("preserve")
    target = tmp_path / "valuable"
    target.write_text("preserve")
    (directory / "syosint.session-wal").hardlink_to(target)
    assert run_cli(["logout"], settings=settings, prompts=Prompts()) == 1
    assert session.read_text() == "preserve"
    assert target.read_text() == "preserve"
    assert capsys.readouterr() == ("session-unavailable\n", "")
