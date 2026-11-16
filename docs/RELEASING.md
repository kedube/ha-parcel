# Releasing

Releases are made by a GitHub Actions workflow that you start by hand. You choose the kind of release; the workflow works out the version number, runs the checks, and publishes.

## Version numbers

Versions count in hundredths: `0.01`, `0.02` … `0.99`, `1.00`, `1.01` and so on. After `x.99` comes the next whole number.

A **beta** is a test build of an upcoming version. It is named after that version, with `b` and a counter: `0.02b1`, `0.02b2`, and then the finished `0.02`.

The released versions are the repository's tags. The workflow reads them to decide what comes next, so you never type a version number.

## Make a release

1. Check that `main` contains what you want to release and that CI is green.
2. On GitHub, open **Actions › Release › Run workflow** and leave the branch on `main`.
3. Choose the **kind of release**:

   | Kind | What you get | Example |
   | --- | --- | --- |
   | `minor` | The next hundredth | `0.01` → `0.02`, and `0.99` → `1.00` |
   | `major` | The next whole number | `0.37` → `1.00` |
   | `beta` | A test build of the next minor | `0.02b1`, then `0.02b2` |
   | `major-beta` | A test build of the next major | `1.00b1`, then `1.00b2` |

4. Optionally fill in **What's new**. It appears at the top of the release notes, which HACS shows to people when it offers the update.
5. Optionally tick **Preview only** to see what would happen without publishing anything.
6. Select **Run workflow**. The run's summary page shows the version and, at the end, a link to the release.

From a terminal, the same thing is:

```sh
gh workflow run release.yml -f release_type=minor
gh workflow run release.yml -f release_type=beta -f summary="Try the new morning briefing" -f dry_run=true
```

## What the workflow does

1. **Works out the version** from the existing tags. It stops if nothing has changed since the last release, so a double click can't publish the same thing twice.
2. **Runs the checks**: the same ones CI runs on every push (lint, type checks, tests for the integration and the panel, Home Assistant's manifest check, the HACS check, and that the built panel and brand images match their sources).
3. **Sets the version** in `custom_components/parcel/manifest.json`, commits that to `main` as "Release 0.02", and tags the commit.
4. **Pushes** the commit and the tag together. If `main` has moved on since the run started, the push is refused and nothing is released.
5. **Publishes the GitHub release** with the release notes and `parcel.zip` (the integration folder, for people who install by hand). A beta is marked as a pre-release; a minor or major becomes the latest release.

## Betas

- **Finishing a beta.** When a beta is good, run `minor` (or `major` after a `major-beta`). The last beta can be promoted as it is, without further changes.
- **Who gets betas.** A beta is a GitHub pre-release. HACS only offers pre-releases to people who have turned on beta versions for Parcel.
- **What a beta reports inside Home Assistant.** Home Assistant refuses to load an integration whose version it can't read, and it can't read a beta marker next to these version numbers. So `0.02b1` is the name on GitHub and in HACS, while the integration itself reports `0.02`. To know exactly which build someone runs, look in HACS.
- **A minor during a major beta.** You can still release `0.38` while `1.00b2` is out. There is one line of development, so `0.38` contains everything that is on `main`, including the beta's changes.

## Release notes

The notes are your **What's new** text, then the subject line of every commit since the previous release, then a link comparing the two versions. A finished release lists everything since the previous finished release, including what went through beta.

Commit subjects end up in front of users, so write them as changes a user would recognise. You can also edit the notes on the release page afterwards.

## If something goes wrong

| What you see | What to do |
| --- | --- |
| A check failed | Nothing was published. Fix the problem on `main` and run the workflow again. |
| "Nothing has changed since 0.02" | There are no new commits to release. |
| The push was refused | `main` changed while the workflow was running. Run it again. |
| It failed after the tag was pushed | Use **Re-run failed jobs** on that run. It continues from the tag and publishes that same version. (A fresh run won't do it: it will say nothing has changed.) |
| A release went out that shouldn't have | If people may already have installed it, fix the problem and release the next version. Otherwise delete it with `gh release delete 0.02 --cleanup-tag`; the number becomes available again. |

## Good to know

- **Permission to push.** The workflow pushes the release commit to `main` with GitHub's built-in token, which works while `main` is unprotected. If you add branch protection, allow GitHub Actions to bypass it.
- **Other tags.** Tags that aren't release versions (anything not shaped like `0.02` or `0.02b1`) are ignored.
- **The pieces.** The workflow is [`.github/workflows/release.yml`](../.github/workflows/release.yml), the checks are [`.github/workflows/ci.yml`](../.github/workflows/ci.yml), and the version logic is [`scripts/release.py`](../scripts/release.py) with tests in [`tests/test_release.py`](../tests/test_release.py). A preview run works on any branch, which is the way to try a change to the pipeline.
