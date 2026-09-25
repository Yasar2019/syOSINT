import subprocess

import pytest

from syosint import rss_gate
from syosint.rss_types import FeedSource


def source(source_id, *, enabled=True):
    return FeedSource(
        id=source_id,
        label={"en": source_id, "ar": source_id},
        feed_url=f"https://{source_id}.example/feed.xml",
        homepage_url=f"https://{source_id}.example/",
        language="en",
        enabled=enabled,
        topic_mode="keyword-filtered",
        required_terms=("Syria",),
        attribution="Example attribution",
        attribution_url=f"https://{source_id}.example/legal",
    )


def test_gate_checks_each_enabled_source_with_argument_array():
    calls = []

    def runner(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(
            command, 0, stdout='{"status":"ok","entries":2}', stderr=""
        )

    rss_gate.check_enabled_sources(
        (source("first"), source("disabled", enabled=False), source("second")),
        runner=runner,
        python="/safe/python",
    )

    assert [call[0] for call in calls] == [
        [
            "/safe/python",
            "-m",
            "syosint.rss_cli",
            "check-source",
            "--",
            "https://first.example/feed.xml",
        ],
        [
            "/safe/python",
            "-m",
            "syosint.rss_cli",
            "check-source",
            "--",
            "https://second.example/feed.xml",
        ],
    ]
    assert all(
        kwargs == {"check": False, "stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "text": True}
        for _, kwargs in calls
    )


def test_gate_rejects_zero_enabled_sources():
    with pytest.raises(rss_gate.GateFailure):
        rss_gate.check_enabled_sources((source("disabled", enabled=False),))


def test_gate_fails_closed_when_any_check_fails():
    def runner(command, **kwargs):
        raise subprocess.CalledProcessError(1, command)

    with pytest.raises(rss_gate.GateFailure):
        rss_gate.check_enabled_sources((source("failing"),), runner=runner)


def test_gate_discards_malicious_child_output_url_and_option_like_id(capsys):
    secret = "token=do-not-log"
    malicious = source("safe")
    malicious = FeedSource(
        id="--secret-source",
        label=malicious.label,
        feed_url=f"https://safe.example/feed.xml?{secret}",
        homepage_url=malicious.homepage_url,
        language=malicious.language,
        enabled=True,
        topic_mode=malicious.topic_mode,
        required_terms=malicious.required_terms,
        attribution=malicious.attribution,
        attribution_url=malicious.attribution_url,
    )

    def runner(command, **kwargs):
        return subprocess.CompletedProcess(
            command,
            1,
            stdout=f"remote body {secret}",
            stderr=f"Traceback /private/path response={secret}",
        )

    with pytest.raises(rss_gate.GateFailure):
        rss_gate.check_enabled_sources((malicious,), runner=runner)

    output = capsys.readouterr()
    combined = output.out + output.err
    assert combined == "source=invalid-source status=failed category=check-failed items=0\n"
    for forbidden in (secret, "https://", "/private/path", "Traceback", "check-source"):
        assert forbidden not in combined


def test_gate_discards_chained_internal_exception(capsys):
    def runner(command, **kwargs):
        try:
            raise ValueError("remote response secret-body")
        except ValueError as cause:
            raise OSError("/private/path?token=secret") from cause

    with pytest.raises(rss_gate.GateFailure):
        rss_gate.check_enabled_sources((source("failing"),), runner=runner)

    combined = "".join(capsys.readouterr())
    assert combined == "source=failing status=failed category=execution-failed items=0\n"
    assert "secret" not in combined
    assert "Traceback" not in combined
    assert "/private" not in combined


def test_gate_main_maps_configuration_and_internal_failures_without_traceback(
    monkeypatch, capsys, tmp_path
):
    config = tmp_path / "secret-config.json"
    config.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        rss_gate,
        "_load_sources",
        lambda path: (_ for _ in ()).throw(ValueError(f"bad /private/{path}?token=secret")),
    )

    assert rss_gate.main(["--config", str(config)]) == 1
    combined = "".join(capsys.readouterr())
    assert combined == "source=config status=failed category=config-failed items=0\n"
    assert "secret" not in combined
    assert "Traceback" not in combined

    monkeypatch.setattr(rss_gate, "_load_sources", lambda path: (source("checked"),))
    monkeypatch.setattr(
        rss_gate,
        "check_enabled_sources",
        lambda sources: (_ for _ in ()).throw(RuntimeError("internal secret /path")),
    )
    assert rss_gate.main(["--config", str(config)]) == 1
    assert "".join(capsys.readouterr()) == (
        "source=config status=failed category=internal-failed items=0\n"
    )


def test_gate_main_loads_validated_configuration(monkeypatch, tmp_path):
    config = tmp_path / "sources.json"
    config.write_text("{}", encoding="utf-8")
    expected = (source("checked"),)
    observed = []
    monkeypatch.setattr(rss_gate, "_load_sources", lambda path: expected)
    monkeypatch.setattr(
        rss_gate,
        "check_enabled_sources",
        lambda sources: observed.extend(sources),
    )

    assert rss_gate.main(["--config", str(config)]) == 0
    assert observed == list(expected)
