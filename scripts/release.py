#!/usr/bin/env python3
"""Version numbers and release notes for the release workflow.

Versions count in hundredths: 0.01, 0.02 ... 0.99, 1.00, 1.01 ...
A beta is a test build of an upcoming version. It is named with "b" and a counter
(0.02b1, 0.02b2, then the finished 0.02).

The released versions are the git tags; nothing else is consulted to decide what
comes next. Standard library only, so the workflow can run it as-is.

    release.py next minor            # what a release of this kind would be called
    release.py stamp 0.02            # write the version into manifest.json
    release.py notes 0.02            # release notes (Markdown) for that version
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "custom_components" / "parcel" / "manifest.json"

RELEASE_TYPES = ("minor", "major", "beta", "major-beta")
VERSION_RE = re.compile(r"^(0|[1-9]\d*)\.(\d{2})(?:b([1-9]\d*))?$")
RELEASE_COMMIT_RE = re.compile(r"^Release \d+\.\d{2}(?:b\d+)?$")
MENTION_RE = re.compile(r"(?<![\w`])@(\w[\w-]*)")


class ReleaseError(Exception):
    """Something that should stop a release, with a message for a person."""


@dataclass(frozen=True)
class Version:
    """A version such as 0.02, or a beta of one such as 0.02b1."""

    major: int
    minor: int  # 0-99, written with two digits
    beta: int | None = None

    @classmethod
    def parse(cls, text: str) -> Version | None:
        """Read a version, or return None when the text isn't one."""
        match = VERSION_RE.match(text.strip())
        if not match:
            return None
        return cls(int(match[1]), int(match[2]), int(match[3]) if match[3] else None)

    def __str__(self) -> str:
        """Write the version the way tags and release names show it."""
        text = f"{self.major}.{self.minor:02d}"
        return f"{text}b{self.beta}" if self.beta else text

    @property
    def is_beta(self) -> bool:
        """Whether this is a beta."""
        return self.beta is not None

    @property
    def target(self) -> Version:
        """The finished version a beta leads up to (the version itself if finished)."""
        return replace(self, beta=None)

    @property
    def order(self) -> tuple[int, int, int, int]:
        """Sort key: betas come before the version they lead up to."""
        return (self.major, self.minor, 0 if self.is_beta else 1, self.beta or 0)

    def next_minor(self) -> Version:
        """One hundredth up: 0.01 → 0.02, and 0.99 → 1.00."""
        if self.minor == 99:
            return Version(self.major + 1, 0)
        return Version(self.major, self.minor + 1)

    def next_major(self) -> Version:
        """The next whole number: 0.37 → 1.00."""
        return Version(self.major + 1, 0)


def released(tags: list[str]) -> list[Version]:
    """The tags that are releases; other tags are ignored."""
    return [version for tag in tags if (version := Version.parse(tag))]


def latest_finished(tags: list[str]) -> Version:
    """The highest finished (non-beta) release, or 0.00 when there is none yet."""
    finished = [version for version in released(tags) if not version.is_beta]
    return max(finished, key=lambda v: v.order, default=Version(0, 0))


def next_version(tags: list[str], release_type: str) -> Version:
    """What a release of this kind is called, given the releases so far.

    minor       the next hundredth after the latest finished release
    major       the next whole number after it
    beta        the next beta of the upcoming minor
    major-beta  the next beta of the upcoming major
    """
    if release_type not in RELEASE_TYPES:
        raise ReleaseError(
            f"Unknown release type {release_type!r}. Use one of: {', '.join(RELEASE_TYPES)}."
        )
    latest = latest_finished(tags)
    target = latest.next_major() if release_type.startswith("major") else latest.next_minor()
    if not release_type.endswith("beta"):
        return target
    earlier = [v.beta for v in released(tags) if v.is_beta and v.target == target]
    return replace(target, beta=max(earlier, default=0) + 1)


def previous_release(tags: list[str], version: Version) -> Version | None:
    """Where the release notes for a version start from.

    A finished release is compared with the finished release before it, so its notes
    cover everything that went through beta. A beta is compared with whatever was
    released just below it.
    """
    below = [v for v in released(tags) if v.order < version.order]
    if not version.is_beta:
        below = [v for v in below if not v.is_beta]
    return max(below, key=lambda v: v.order, default=None)


def manifest_version(version: Version) -> str:
    """The version written inside the integration.

    Home Assistant refuses to load a custom integration whose manifest version it
    can't parse, and it can't parse a beta marker next to a zero-padded number
    (0.02b1). So a beta build carries the version it leads up to (0.02); only the
    tag and the release name say which beta it is.
    """
    return str(version.target)


def stamp(manifest: Path, version: Version) -> bool:
    """Write the version into manifest.json. Returns False if it was already there."""
    text = manifest.read_text(encoding="utf-8")
    before = json.loads(text)
    wanted = manifest_version(version)
    if before.get("version") == wanted:
        return False
    # Replace just the value, so the file's formatting and key order stay as they are.
    stamped, count = re.subn(
        r'("version"\s*:\s*")[^"]*(")', lambda m: f"{m[1]}{wanted}{m[2]}", text, count=1
    )
    after = json.loads(stamped) if count else None
    if after != {**before, "version": wanted}:
        raise ReleaseError(f"Couldn't set the version in {manifest}.")
    manifest.write_text(stamped, encoding="utf-8")
    return True


# Git -----------------------------------------------------------------------


def git(*args: str) -> str:
    """Run git in the repository and return what it printed."""
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise ReleaseError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def git_tags() -> list[str]:
    """Every tag in the repository."""
    return git("tag", "--list").split()


def commits_since(tag: str | None, ref: str = "HEAD") -> list[tuple[str, str]]:
    """(short hash, subject) of each commit after a tag, newest first.

    The workflow's own "Release 0.02" commits are left out.
    """
    span = f"{tag}..{ref}" if tag else ref
    lines = git("log", "--no-merges", "--format=%h%x09%s", span).splitlines()
    commits = [tuple(line.split("\t", 1)) for line in lines if "\t" in line]
    return [(sha, subject) for sha, subject in commits if not RELEASE_COMMIT_RE.match(subject)]


def nearest_release(tags: list[str], ref: str = "HEAD") -> Version | None:
    """The most recent release in the history of a commit."""
    reachable = set(git("tag", "--merged", ref).split())
    candidates = [v for v in released(tags) if str(v) in reachable]
    if not candidates:
        return None

    # The fewest commits between the tag and the ref wins; on a tie (two tags on one
    # commit, as when a beta is promoted unchanged) the higher version does.
    def distance(version: Version) -> tuple[int, tuple[int, ...]]:
        count = int(git("rev-list", "--count", f"{version}..{ref}").strip())
        return (count, tuple(-part for part in version.order))

    return min(candidates, key=distance)


def check_something_changed(tags: list[str], version: Version, ref: str = "HEAD") -> None:
    """Stop a release that would be identical to the one before it.

    Turning the latest beta into the finished version without further changes is
    the one case where that is intended.
    """
    last = nearest_release(tags, ref)
    if last is None or commits_since(str(last), ref):
        return
    promoting = last.is_beta and not version.is_beta and last.target == version
    if not promoting:
        raise ReleaseError(
            f"Nothing has changed since {last}, so there is nothing to release as {version}."
        )


# Release notes ---------------------------------------------------------------


def release_notes(
    version: Version,
    previous: Version | None,
    commits: list[tuple[str, str]],
    *,
    summary: str = "",
    repo: str = "",
) -> str:
    """Markdown for the GitHub release (HACS shows it in the update dialog)."""
    parts: list[str] = []
    if summary.strip():
        parts.append(summary.strip())
    if version.is_beta:
        parts.append(
            f"This is a beta: a test build of the upcoming {version.target}. "
            "It is published as a pre-release, so HACS only offers it if you have "
            "turned on beta versions for Parcel."
        )
    if commits:
        lines = [f"- {_plain(subject)} ({sha})" for sha, subject in commits]
        parts.append("## Changes\n\n" + "\n".join(lines))
    elif previous is not None:
        parts.append(f"No code changes since {previous}.")
    if previous is not None and repo:
        parts.append(
            f"**Full changelog:** https://github.com/{repo}/compare/{previous}...{version}"
        )
    return "\n\n".join(parts) + "\n"


def _plain(subject: str) -> str:
    """Keep a commit subject from notifying people: `@name` instead of @name."""
    return MENTION_RE.sub(r"`@\1`", subject.strip())


# Command line --------------------------------------------------------------


def _output(**values: str) -> None:
    """Print values, and hand them to later workflow steps when run by GitHub Actions."""
    for key, value in values.items():
        print(f"{key}={value}")
    if path := os.environ.get("GITHUB_OUTPUT"):
        with open(path, "a", encoding="utf-8") as handle:
            for key, value in values.items():
                handle.write(f"{key}={value}\n")


def _require(text: str) -> Version:
    version = Version.parse(text)
    if version is None:
        raise ReleaseError(f"{text!r} isn't a version like 0.02 or 0.02b1.")
    return version


def main(argv: list[str] | None = None) -> int:
    """Run a subcommand."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    commands = parser.add_subparsers(dest="command", required=True)

    plan = commands.add_parser("next", help="work out the next version")
    plan.add_argument("release_type", choices=RELEASE_TYPES)

    stamping = commands.add_parser("stamp", help="write a version into manifest.json")
    stamping.add_argument("version")
    stamping.add_argument("--manifest", type=Path, default=MANIFEST)

    notes = commands.add_parser("notes", help="write release notes for a version")
    notes.add_argument("version")
    notes.add_argument("--summary", default=os.environ.get("RELEASE_SUMMARY", ""))
    notes.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))

    args = parser.parse_args(argv)
    try:
        if args.command == "next":
            tags = git_tags()
            version = next_version(tags, args.release_type)
            check_something_changed(tags, version)
            previous = previous_release(tags, version)
            _output(
                version=str(version),
                manifest_version=manifest_version(version),
                prerelease="true" if version.is_beta else "false",
                previous=str(previous) if previous else "",
            )
        elif args.command == "stamp":
            changed = stamp(args.manifest, _require(args.version))
            _output(changed="true" if changed else "false")
        elif args.command == "notes":
            version = _require(args.version)
            tags = [tag for tag in git_tags() if tag != str(version)]
            previous = previous_release(tags, version)
            commits = commits_since(str(previous) if previous else None)
            sys.stdout.write(
                release_notes(version, previous, commits, summary=args.summary, repo=args.repo)
            )
    except ReleaseError as err:
        print(
            f"::error::{err}" if os.environ.get("GITHUB_ACTIONS") else f"Error: {err}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
