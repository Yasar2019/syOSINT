import json
from argparse import Namespace
from pathlib import Path

import pytest

from syosint import rss_cli
from syosint.rss_collect import CollectionResult, SourceOutcome
from syosint.rss_cli import _load_sources
from syosint.safe_http import FeedFetchError, FetchResult


REPOSITORY = Path(__file__).resolve().parents[3]


def source_config(**overrides):
    source = {
        "id": "example",
        "label": {"en": "Example", "ar": "مثال"},
        "feedUrl": "https://example.org/rss",
        "homepageUrl": "https://example.org/",
        "language": "en",
        "enabled": True,
        "topicMode": "keyword-filtered",
        "requiredTerms": ["Syria"],
        "excludedTerms": [],
        "attribution": "Example feed attribution",
        "attributionUrl": "https://example.org/legal",
    }
    source.update(overrides)
    return {"schemaVersion": "1.0.0", "sources": [source]}


def write_config(tmp_path, config):
    path = tmp_path / "sources.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return path


def test_check_source_reports_bounded_http_failure_without_sensitive_text(monkeypatch, capsys):
    secret = "token=do-not-log"

    class FailingClient:
        def fetch(self, url):
            raise FeedFetchError("http-status", status_code=403) from ValueError(secret)

    monkeypatch.setattr(rss_cli, "SafeFeedClient", FailingClient)
    assert rss_cli.main(["check-source", "--", f"https://example.org/feed?{secret}"]) == 1
    output = capsys.readouterr()
    assert json.loads(output.out) == {
        "status": "failed", "category": "http-status", "httpStatus": 403
    }
    assert output.err == ""
    assert secret not in output.out


def test_check_source_reports_parse_failure_without_payload(monkeypatch, capsys):
    class Client:
        def fetch(self, url):
            return FetchResult(200, b"<unsafe secret='token'>", None)

    monkeypatch.setattr(rss_cli, "SafeFeedClient", Client)
    assert rss_cli.main(["check-source", "--", "https://example.org/feed"]) == 1
    output = capsys.readouterr()
    assert json.loads(output.out) == {"status": "failed", "category": "parse-failed"}
    assert output.err == ""


@pytest.mark.parametrize("category", ["secret\ncategory=ok", ["secret"]])
def test_check_source_sanitizes_unexpected_fetch_category_and_status(
    monkeypatch, capsys, category
):
    class FailingClient:
        def fetch(self, url):
            raise FeedFetchError(category, status_code=True)

    monkeypatch.setattr(rss_cli, "SafeFeedClient", FailingClient)
    assert rss_cli.main(["check-source", "--", "https://example.org/feed"]) == 1
    output = capsys.readouterr()
    assert json.loads(output.out) == {"status": "failed", "category": "internal-failed"}
    assert output.err == ""


def test_public_allowlist_is_balanced_and_reviewed():
    sources = _load_sources(REPOSITORY / "config/rss-sources.json")
    enabled = [source for source in sources if source.enabled]

    assert 8 <= len(enabled) <= 12
    assert {source.language for source in enabled} == {"en", "ar"}
    assert not any(source.id.startswith("european-parliament-") for source in enabled)
    assert "global-affairs-canada" in {source.id for source in enabled}
    assert {
        "sana-english", "north-press-english", "north-press-arabic",
    } <= {source.id for source in enabled}
    assert all(source.attribution for source in enabled)
    assert all(source.attribution_url for source in enabled)
    assert all(source.topic_mode in {"syria-only", "keyword-filtered"} for source in enabled)
    configured = json.loads((REPOSITORY / "config/rss-sources.json").read_text())
    assert all("topicMode" in source for source in configured["sources"] if source["enabled"])
    review = (REPOSITORY / "docs/source-policy/RSS-SOURCE-REVIEWS.md").read_text()
    assert all(source.id in review for source in enabled)


def test_keyword_mode_requires_terms(tmp_path):
    config = source_config(topicMode="keyword-filtered", requiredTerms=[])
    with pytest.raises(ValueError, match="requiredTerms"):
        _load_sources(write_config(tmp_path, config))


@pytest.mark.parametrize("terms", ["Syria", [" "], ["Syria", ""], [42]])
def test_rejects_malformed_required_terms(tmp_path, terms):
    config = source_config(requiredTerms=terms)
    with pytest.raises(ValueError, match="requiredTerms"):
        _load_sources(write_config(tmp_path, config))


@pytest.mark.parametrize("terms", ["sports", [""], ["sports", "  "], [None]])
def test_rejects_malformed_excluded_terms(tmp_path, terms):
    config = source_config(excludedTerms=terms)
    with pytest.raises(ValueError, match="excludedTerms"):
        _load_sources(write_config(tmp_path, config))


def test_unknown_topic_mode_is_rejected(tmp_path):
    config = source_config(topicMode="everything")
    with pytest.raises(ValueError, match="topicMode"):
        _load_sources(write_config(tmp_path, config))


def test_explicit_syria_only_mode_can_omit_required_terms(tmp_path):
    config = source_config(
        topicMode="syria-only", requiredTerms=[], excludedTerms=["sports"]
    )
    loaded = _load_sources(write_config(tmp_path, config))

    assert loaded[0].topic_mode == "syria-only"
    assert loaded[0].required_terms == ()
    assert loaded[0].excluded_terms == ("sports",)


def test_legacy_sources_default_to_keyword_filtered(tmp_path):
    config = source_config()
    del config["sources"][0]["topicMode"]
    loaded = _load_sources(write_config(tmp_path, config))

    assert loaded[0].topic_mode == "keyword-filtered"
    assert loaded[0].required_terms == ("Syria",)
    assert loaded[0].excluded_terms == ()


@pytest.mark.parametrize("field", ["feedUrl", "homepageUrl", "attributionUrl"])
@pytest.mark.parametrize(
    "unsafe_url",
    [
        "-option",
        "http://example.org/feed",
        "https://user:password@example.org/feed",
        "https://example.org:444/feed",
        "https://example.org/feed#fragment",
        "https://8.8.8.8/feed",
        "https://-option.example/feed",
        "https://example.org/feed path",
    ],
)
def test_source_configuration_rejects_unsafe_urls(tmp_path, field, unsafe_url):
    config = source_config(**{field: unsafe_url})
    with pytest.raises(ValueError, match=field):
        _load_sources(write_config(tmp_path, config))


@pytest.mark.parametrize("missing", ["attribution", "attributionUrl"])
def test_enabled_source_requires_complete_attribution(tmp_path, missing):
    config = source_config()
    del config["sources"][0][missing]

    with pytest.raises(ValueError, match=missing):
        _load_sources(write_config(tmp_path, config))


def previous_wire():
    return {
        "schemaVersion": "1.0.0",
        "generatedAt": "2026-09-23T15:30:00Z",
        "lastSuccessfulRefreshAt": "2026-09-23T15:30:00Z",
        "sources": {"healthy": 1, "delayed": 0},
        "entries": [
            {
                "id": "example:previous",
                "sourceId": "example",
                "sourceLabel": {"en": "Example", "ar": "مثال"},
                "language": "en",
                "headline": "Earlier Syria report",
                "url": "https://example.org/earlier",
                "publishedAt": "2026-09-23T15:00:00Z",
                "collectedAt": "2026-09-23T15:30:00Z",
            }
        ],
    }


def load_previous_from(monkeypatch, value):
    class PreviousClient:
        def __init__(self, **kwargs):
            pass

        def fetch(self, url):
            assert url == "https://pages.example/news-wire.json"
            return FetchResult(200, json.dumps(value).encode(), None)

    monkeypatch.setattr(rss_cli, "SafeFeedClient", PreviousClient)
    return rss_cli._load_previous("https://pages.example/news-wire.json")


def test_previous_1_0_wire_is_validated_and_retains_entries(monkeypatch):
    previous = load_previous_from(monkeypatch, previous_wire())

    assert previous is not None
    assert [entry.id for entry in previous.entries] == ["example:previous"]


@pytest.mark.parametrize("private_field", ["body", "exception", "feedUrl"])
def test_previous_1_0_wire_rejects_private_fields(monkeypatch, private_field):
    value = previous_wire()
    value["entries"][0][private_field] = "private trace"

    assert load_previous_from(monkeypatch, value) is None


def test_previous_wire_rejects_unrecognized_version(monkeypatch):
    value = previous_wire()
    value["schemaVersion"] = "0.9.0"

    assert load_previous_from(monkeypatch, value) is None


def test_cli_validates_1_1_source_states_and_unique_ids(monkeypatch):
    value = previous_wire()
    value.update(
        schemaVersion="1.1.0",
        sources={"configured": 2, "healthy": 2, "delayed": 0},
        sourceStates=[
            {
                "id": "example",
                "label": {"en": "Example", "ar": "مثال"},
                "language": "en",
                "attribution": "Example feed attribution",
                "attributionUrl": "https://example.org/legal",
                "status": "healthy",
                "lastSuccessfulRefreshAt": "2026-09-23T15:30:00Z",
                "entryCount": 1,
            },
            {
                "id": "other",
                "label": {"en": "Other", "ar": "آخر"},
                "language": "ar",
                "attribution": "Other feed attribution",
                "attributionUrl": "https://other.example/legal",
                "status": "not-modified",
                "lastSuccessfulRefreshAt": None,
                "entryCount": 0,
            },
        ],
    )
    assert load_previous_from(monkeypatch, value) is not None

    duplicate = json.loads(json.dumps(value))
    duplicate["sourceStates"][1]["id"] = "example"
    assert load_previous_from(monkeypatch, duplicate) is None

    orphan = json.loads(json.dumps(value))
    orphan["entries"][0]["sourceId"] = "missing-source"
    assert load_previous_from(monkeypatch, orphan) is None

    value["sourceStates"][0]["error"] = "socket trace"
    assert load_previous_from(monkeypatch, value) is None


def _run_fake_collection(monkeypatch, tmp_path, outcomes):
    result = CollectionResult((object(),) * len(outcomes), tuple(outcomes))
    wire = {
        "schemaVersion": "1.1.0",
        "sources": {"configured": len(outcomes), "healthy": 1, "delayed": 1},
        "entries": [],
    }
    monkeypatch.setattr(rss_cli, "_load_sources", lambda path: result.sources)
    monkeypatch.setattr(rss_cli, "_load_previous", lambda url: None)
    monkeypatch.setattr(rss_cli, "collect_sources", lambda *args: result)
    monkeypatch.setattr(rss_cli, "build_public_wire", lambda *args: wire)
    monkeypatch.setattr(rss_cli, "_validate_wire", lambda value: None)
    monkeypatch.setattr(rss_cli, "_write_atomic", lambda path, value: None)
    return rss_cli.collect_public(
        Namespace(
            config=str(tmp_path / "sources.json"),
            output=str(tmp_path / "wire.json"),
            previous_url=None,
        )
    )


def test_cli_logs_safe_per_source_status(monkeypatch, tmp_path, capsys):
    outcomes = (
        SourceOutcome("syria-untold-english", "delayed", (), "timeout", None),
        SourceOutcome("govuk-syria-news", "healthy", (object(),), None, None),
    )

    assert _run_fake_collection(monkeypatch, tmp_path, outcomes) == 0

    output = capsys.readouterr().out
    assert (
        "source=syria-untold-english status=delayed category=timeout items=0"
        in output
    )
    assert "source=govuk-syria-news status=healthy category=none items=1" in output


def test_cli_redacts_unapproved_log_values(monkeypatch, tmp_path, capsys):
    secret = "response body https://user:password@example.org/private"
    outcomes = (
        SourceOutcome(secret, "delayed", (), secret, None),
        SourceOutcome("govuk-syria-news", "healthy", (), None, None),
    )

    _run_fake_collection(monkeypatch, tmp_path, outcomes)

    output = capsys.readouterr().out
    assert "source=invalid-source status=delayed category=other items=0" in output
    assert secret not in output
    assert "password" not in output
    assert "response body" not in output


def test_cli_replaces_oversized_source_log_tokens(monkeypatch, tmp_path, capsys):
    oversized = "a" * 81
    outcomes = (
        SourceOutcome(oversized, "delayed", (), "timeout", None),
        SourceOutcome("govuk-syria-news", "healthy", (), None, None),
    )

    _run_fake_collection(monkeypatch, tmp_path, outcomes)

    output = capsys.readouterr().out
    assert "source=invalid-source status=delayed category=timeout items=0" in output
    assert oversized not in output


def test_cli_writes_aggregate_only_github_summary(monkeypatch, tmp_path):
    summary = tmp_path / "step-summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    outcomes = (
        SourceOutcome("syria-untold-english", "delayed", (), "timeout", None),
        SourceOutcome(
            "govuk-syria-news", "healthy", (object(), object()), None, None
        ),
    )

    _run_fake_collection(monkeypatch, tmp_path, outcomes)

    value = summary.read_text(encoding="utf-8")
    assert "Configured: 2" in value
    assert "Healthy: 1" in value
    assert "Delayed: 1" in value
    assert "Items: 2" in value
    assert "syria-untold-english" not in value
    assert "timeout" not in value
