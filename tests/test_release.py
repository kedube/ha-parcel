"""The release workflow's version numbers, manifest stamping and release notes."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from awesomeversion import AwesomeVersion, AwesomeVersionStrategy
import pytest

SCRIPT = Path(__file__).parent.parent / "scripts" / "release.py"
_spec = importlib.util.spec_from_file_location("parcel_release", SCRIPT)
release = importlib.util.module_from_spec(_spec)
sys.modules["parcel_release"] = release
_spec.loader.exec_module(release)

Version = release.Version


def nxt(tags: list[str], kind: str) -> str:
    return str(release.next_version(tags, kind))


# Numbering -----------------------------------------------------------------


def test_numbering_starts_at_0_01_and_rolls_over_at_99() -> None:
    """0.01 → 0.02 … 0.99 → 1.00 → 1.01."""
    tags: list[str] = []
    seen = []
    for _ in range(101):
        tags.append(nxt(tags, "minor"))
        seen.append(tags[-1])
    assert seen[:3] == ["0.01", "0.02", "0.03"]
    assert seen[8:11] == ["0.09", "0.10", "0.11"]
    assert seen[97:] == ["0.98", "0.99", "1.00", "1.01"]
    assert nxt(["1.99"], "minor") == "2.00"
    assert nxt(["9.99"], "minor") == "10.00"


def test_major_goes_to_the_next_whole_number() -> None:
    assert nxt([], "major") == "1.00"
    assert nxt(["0.37"], "major") == "1.00"
    assert nxt(["1.00", "1.05"], "major") == "2.00"


def test_beta_counts_up_then_minor_finishes_it() -> None:
    """beta, beta, minor → 0.02b1, 0.02b2, 0.02; the next beta starts a new series."""
    tags = ["0.01"]
    assert nxt(tags, "beta") == "0.02b1"
    tags.append("0.02b1")
    assert nxt(tags, "beta") == "0.02b2"
    tags.append("0.02b2")
    assert nxt(tags, "minor") == "0.02"
    tags.append("0.02")
    assert nxt(tags, "beta") == "0.03b1"
    assert nxt([], "beta") == "0.01b1"


def test_betas_of_a_major() -> None:
    """major-beta leads up to the next whole number; minors can still ship meanwhile."""
    tags = ["0.36", "0.37"]
    assert nxt(tags, "major-beta") == "1.00b1"
    tags.append("1.00b1")
    assert nxt(tags, "major-beta") == "1.00b2"
    assert nxt(tags, "beta") == "0.38b1"
    assert nxt(tags, "minor") == "0.38"
    assert nxt([*tags, "0.38"], "major-beta") == "1.00b2"
    assert nxt([*tags, "1.00b2"], "major") == "1.00"
    # At x.99 the next minor and the next major are the same release.
    assert nxt(["0.99"], "beta") == nxt(["0.99"], "major-beta") == "1.00b1"
    assert nxt(["0.99", "1.00b1"], "beta") == "1.00b2"


def test_other_tags_are_ignored() -> None:
    tags = ["v1.2.3", "0.1", "0.001", "00.01", "0.02b0", "nightly", "0.01"]
    assert nxt(tags, "minor") == "0.02"
    assert [str(v) for v in release.released(tags)] == ["0.01"]


def test_unknown_release_type() -> None:
    with pytest.raises(release.ReleaseError):
        release.next_version([], "patch")


def test_order_puts_betas_before_the_finished_version() -> None:
    names = ["1.00", "0.02", "0.02b2", "0.01", "1.00b1", "0.02b10", "0.99", "0.02b1"]
    ordered = sorted((Version.parse(n) for n in names), key=lambda v: v.order)
    assert [str(v) for v in ordered] == [
        "0.01", "0.02b1", "0.02b2", "0.02b10", "0.02", "0.99", "1.00b1", "1.00",
    ]  # fmt: skip


def test_previous_release_for_notes() -> None:
    tags = ["0.01", "0.02b1", "0.02b2", "0.02", "0.37", "1.00b1", "1.00b2", "0.38"]
    prev = lambda name: str(release.previous_release(tags, Version.parse(name)))  # noqa: E731
    assert prev("0.02b2") == "0.02b1"  # a beta: since the release just below it
    assert prev("0.02") == "0.01"  # finished: since the finished release before
    assert prev("1.00b3") == "1.00b2"
    assert prev("1.00") == "0.38"
    assert prev("0.39b1") == "0.38"
    assert release.previous_release([], Version.parse("0.01")) is None


# What Home Assistant accepts ---------------------------------------------------

# The version formats Home Assistant's loader accepts in a custom integration's
# manifest. An integration with any other version is not loaded at all.
HA_ACCEPTS = [
    AwesomeVersionStrategy.CALVER,
    AwesomeVersionStrategy.SEMVER,
    AwesomeVersionStrategy.SIMPLEVER,
    AwesomeVersionStrategy.BUILDVER,
    AwesomeVersionStrategy.PEP440,
]


def test_every_manifest_version_loads_and_orders_in_home_assistant() -> None:
    """Whatever the workflow writes into the manifest, Home Assistant can read and order."""
    version = Version(0, 0)
    previous = AwesomeVersion(str(version), ensure_strategy=HA_ACCEPTS)
    for _ in range(1250):  # 0.01 … 12.50
        version = version.next_minor()
        for candidate in (version, Version(version.major, version.minor, beta=3)):
            written = release.manifest_version(candidate)
            current = AwesomeVersion(written, ensure_strategy=HA_ACCEPTS)
        assert current > previous, f"{current} should be newer than {previous}"
        previous = current


def test_beta_marker_never_reaches_the_manifest() -> None:
    """0.02b1 is refused by Home Assistant, so a beta is stamped as the version it leads to."""
    with pytest.raises(Exception):  # noqa: B017
        AwesomeVersion("0.02b1", ensure_strategy=HA_ACCEPTS)
    assert release.manifest_version(Version.parse("0.02b1")) == "0.02"
    assert release.manifest_version(Version.parse("1.00b12")) == "1.00"
    assert release.manifest_version(Version.parse("0.02")) == "0.02"


# Stamping ----------------------------------------------------------------------


def test_stamp_changes_only_the_version(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    original = (
        '{\n  "domain": "parcel",\n  "name": "Parcel",\n  "codeowners": ["@kedube"],\n'
        '  "requirements": [],\n  "version": "0.00"\n}\n'
    )
    manifest.write_text(original)
    assert release.stamp(manifest, Version.parse("0.01")) is True
    assert manifest.read_text() == original.replace('"0.00"', '"0.01"')
    assert release.stamp(manifest, Version.parse("0.01")) is False
    # A beta carries the version it leads up to.
    assert release.stamp(manifest, Version.parse("0.02b1")) is True
    assert json.loads(manifest.read_text())["version"] == "0.02"
    assert release.stamp(manifest, Version.parse("0.02b2")) is False
    assert release.stamp(manifest, Version.parse("0.02")) is False


def test_stamp_needs_a_version_key(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"domain": "parcel"}')
    with pytest.raises(release.ReleaseError):
        release.stamp(manifest, Version.parse("0.01"))


def test_the_real_manifest_can_be_stamped(tmp_path: Path) -> None:
    """The repository's manifest has the shape the workflow expects."""
    manifest = tmp_path / "manifest.json"
    manifest.write_text(release.MANIFEST.read_text(encoding="utf-8"))
    current = json.loads(manifest.read_text())["version"]
    AwesomeVersion(current, ensure_strategy=HA_ACCEPTS)
    assert release.stamp(manifest, Version.parse("98.76")) is True
    assert json.loads(manifest.read_text())["version"] == "98.76"


# Release notes -------------------------------------------------------------------


def test_notes_for_a_finished_release() -> None:
    notes = release.release_notes(
        Version.parse("0.02"),
        Version.parse("0.01"),
        [("abc1234", "Add a morning briefing"), ("def5678", "Thanks @someone for the idea")],
        summary="Bigger panel.",
        repo="kedube/ha-parcel",
    )
    assert notes.startswith("Bigger panel.\n\n## Changes\n\n- Add a morning briefing (abc1234)\n")
    assert "`@someone`" in notes  # written so that nobody gets notified
    assert notes.endswith("https://github.com/kedube/ha-parcel/compare/0.01...0.02\n")
    assert "beta" not in notes


def test_notes_for_a_beta_and_for_no_changes() -> None:
    beta = release.release_notes(Version.parse("0.02b1"), Version.parse("0.01"), [("a1", "Fix")])
    assert "test build of the upcoming 0.02" in beta
    promoted = release.release_notes(Version.parse("0.02"), Version.parse("0.01"), [])
    assert "No code changes since 0.01." in promoted
    first = release.release_notes(Version.parse("0.01"), None, [("a1", "First version")])
    assert "compare" not in first


# With a real git history -----------------------------------------------------------


class Repo:
    """A throwaway git repository shaped like this one."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.env = {
            **os.environ,
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.invalid",
        }
        self.git("init", "--quiet", "--initial-branch=main")
        manifest = path / "custom_components" / "parcel" / "manifest.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text('{\n  "domain": "parcel",\n  "version": "0.00"\n}\n')
        self.commit("First version")

    def git(self, *args: str) -> str:
        done = subprocess.run(
            ["git", *args], cwd=self.path, env=self.env, capture_output=True, text=True, check=True
        )
        return done.stdout

    def commit(self, subject: str) -> None:
        (self.path / "log.txt").open("a").write(subject + "\n")
        self.git("add", "-A")
        self.git("commit", "--quiet", "-m", subject)

    def release(self, kind: str) -> str:
        """Do what the workflow does: work out the version, stamp, commit, tag."""
        tags = release.git_tags()
        version = release.next_version(tags, kind)
        release.check_something_changed(tags, version)
        if release.stamp(self.path / "custom_components" / "parcel" / "manifest.json", version):
            self.git("commit", "--quiet", "-am", f"Release {version}")
        self.git("tag", "-a", str(version), "-m", f"Release {version}")
        return str(version)


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Repo:
    monkeypatch.setattr(release, "ROOT", tmp_path)
    return Repo(tmp_path)


def test_a_release_history_end_to_end(repo: Repo) -> None:
    """The sequence of releases a maintainer would actually make."""
    assert repo.release("minor") == "0.01"

    # A second click with nothing new is refused.
    with pytest.raises(release.ReleaseError, match=re.escape("Nothing has changed since 0.01")):
        repo.release("minor")

    repo.commit("Add a morning briefing")
    assert repo.release("beta") == "0.02b1"
    with pytest.raises(release.ReleaseError, match=re.escape("Nothing has changed since 0.02b1")):
        repo.release("beta")

    repo.commit("Fix the briefing time")
    assert repo.release("beta") == "0.02b2"

    # Promoting the last beta unchanged is allowed.
    assert repo.release("minor") == "0.02"
    with pytest.raises(release.ReleaseError, match=re.escape("Nothing has changed since 0.02")):
        repo.release("beta")

    manifest = json.loads((repo.path / "custom_components/parcel/manifest.json").read_text())
    assert manifest["version"] == "0.02"
    assert release.git_tags() == ["0.01", "0.02", "0.02b1", "0.02b2"]

    # Notes for the finished release cover everything since the last finished one,
    # without the workflow's own "Release …" commits.
    tags = [t for t in release.git_tags() if t != "0.02"]
    previous = release.previous_release(tags, Version.parse("0.02"))
    subjects = [subject for _sha, subject in release.commits_since(str(previous))]
    assert subjects == ["Fix the briefing time", "Add a morning briefing"]


def test_command_line(repo: Repo, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    """The commands the workflow runs, and the values it hands to later steps."""
    output = tmp_path / "github_output.txt"
    env_before = os.environ.get("GITHUB_OUTPUT")
    os.environ["GITHUB_OUTPUT"] = str(output)
    try:
        assert release.main(["next", "beta"]) == 0
    finally:
        if env_before is None:
            del os.environ["GITHUB_OUTPUT"]
        else:
            os.environ["GITHUB_OUTPUT"] = env_before
    assert output.read_text().splitlines() == [
        "version=0.01b1",
        "manifest_version=0.01",
        "prerelease=true",
        "previous=",
    ]
    manifest = repo.path / "custom_components" / "parcel" / "manifest.json"
    assert release.main(["stamp", "0.01b1", "--manifest", str(manifest)]) == 0
    assert json.loads(manifest.read_text())["version"] == "0.01"
    capsys.readouterr()

    assert release.main(["notes", "0.01b1", "--summary", "Try it out", "--repo", "o/r"]) == 0
    notes = capsys.readouterr().out
    assert notes.startswith("Try it out\n\nThis is a beta")
    assert "- First version (" in notes

    assert release.main(["stamp", "one.two"]) == 1
    assert "isn't a version" in capsys.readouterr().err
