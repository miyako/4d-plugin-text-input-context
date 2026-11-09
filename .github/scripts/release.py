"""Fail-closed, create-only publication; retain partial remote state for manual recovery."""

import argparse
import json
import os
from pathlib import Path
import plistlib
import re
import subprocess
import sys
from urllib.parse import quote
from xml.parsers.expat import ExpatError

sys.dont_write_bytecode = True


def run(*args, input=None):
    return subprocess.run(
        args, input=input, text=True, stdout=subprocess.PIPE, check=True
    ).stdout.strip()


def api(endpoint, payload=None, asset=None):
    command = ["gh", "api", "--method",
               "GET" if payload is None and asset is None else "POST", endpoint]
    if payload is not None:
        command += ["--input", "-"]
    if asset is not None:
        command += ["--header", "Content-Type: application/octet-stream", "--input", str(asset)]
    return json.loads(run(*command, input=json.dumps(payload) if payload is not None else None))


def selected_sha(sha):
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Expected immutable selected github.sha")
    if run("git", "rev-parse", "HEAD") != sha:
        raise ValueError("Checkout does not match selected github.sha")


def remote_ref(ref):
    output = run("git", "ls-remote", "--refs", "origin", ref)
    if not output:
        return None
    lines = output.splitlines()
    if len(lines) != 1:
        raise ValueError(f"Malformed remote ref response for {ref}")
    parts = lines[0].split()
    if len(parts) != 2 or parts[1] != ref or not re.fullmatch(r"[0-9a-f]{40}", parts[0]):
        raise ValueError(f"Malformed remote ref response for {ref}")
    return parts[0]


def available(repo, tag):
    if remote_ref(f"refs/tags/{tag}") is not None:
        raise ValueError(f"{tag} already exists remotely")
    page = 1
    while True:
        # Authenticated list calls include drafts; a tag lookup's 404 proves nothing.
        releases = api(f"repos/{repo}/releases?per_page=100&page={page}")
        if not isinstance(releases, list) or len(releases) > 100:
            raise ValueError("Malformed releases page")
        for release in releases:
            if (
                not isinstance(release, dict)
                or type(release.get("id")) is not int
                or release["id"] <= 0
                or not isinstance(release.get("tag_name"), str)
                or not release["tag_name"]
                or type(release.get("draft")) is not bool
                or type(release.get("prerelease")) is not bool
            ):
                raise ValueError("Malformed release entry")
            if release["tag_name"] == tag:
                raise ValueError(f"{tag} already has a draft or published release")
        if len(releases) < 100:
            return
        page += 1


def context(tag, sha):
    if not re.fullmatch(r"v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)", tag):
        raise ValueError("Expected tag vX.Y.Z without leading zeros")
    selected_sha(sha)
    from source_version import SOURCE_PATHS, read
    if run("git", "diff", "--name-only", sha, "--", *map(str, SOURCE_PATHS)):
        raise ValueError("Source version metadata differs from the selected commit")
    version = read()
    if tag != f"v{version}":
        raise ValueError("Tag does not match selected source version")
    repo = os.environ["GITHUB_REPOSITORY"]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise ValueError("Invalid repository")
    return repo, version, tag


def check(tag, sha):
    if run("git", "status", "--porcelain"):
        raise ValueError("Build preflight requires a clean source checkout")
    repo, version, tag = context(tag, sha)
    available(repo, tag)
    return version, tag


def publish(tag, sha, assets):
    repo, version, tag = context(tag, sha)
    expected = [f"Text Input Context-{version}.zip", f"Text Input Context-{version}.dmg"]
    if [str(path) for path in assets] != expected:
        raise ValueError(f"Expected release assets: {expected}")
    for path in assets:
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f"Missing or empty release asset: {path}")
    # Called only after every native/sign/notary/staple gate; never reuse early results.
    available(repo, tag)
    ref_name = f"refs/tags/{tag}"
    ref = api(f"repos/{repo}/git/refs", {"ref": ref_name, "sha": sha})
    if (
        not isinstance(ref, dict)
        or ref.get("ref") != ref_name
        or not isinstance(ref.get("object"), dict)
        or ref["object"].get("type") != "commit"
        or ref["object"].get("sha") != sha
        or remote_ref(ref_name) != sha
    ):
        raise ValueError("New remote tag failed exact-SHA verification; inspect retained remote state")
    print(f"Created remote tag {tag} at {sha}; retained if later steps fail", flush=True)
    # Preserve the original Text Input Context workflow's empty release body.
    payload = {
        "tag_name": tag, "target_commitish": sha, "name": tag,
        "draft": False, "prerelease": False, "body": "",
    }
    release = api(f"repos/{repo}/releases", payload)
    if (
        not isinstance(release, dict)
        or type(release.get("id")) is not int
        or release["id"] <= 0
        or release.get("tag_name") != tag
        or release.get("name") != tag
        or release.get("target_commitish") != sha
        or release.get("body") != ""
        or release.get("draft") is not False
        or release.get("prerelease") is not False
    ):
        raise ValueError("Malformed create-release response; inspect retained remote state")
    release_id = release["id"]
    print(f"Created {tag}, release ID {release_id}; uploading assets", flush=True)
    for asset in assets:
        result = api(
            f"https://uploads.github.com/repos/{repo}/releases/{release_id}/assets?name={quote(asset.name)}",
            asset=asset,
        )
        if (
            not isinstance(result, dict)
            or type(result.get("id")) is not int
            or result["id"] <= 0
            or result.get("name") != asset.name
            or type(result.get("size")) is not int
            or result["size"] != asset.stat().st_size
            or result.get("state") != "uploaded"
        ):
            raise ValueError(f"Malformed upload response for {asset}; inspect retained release")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "publish"))
    parser.add_argument("--sha", help="Selected github.sha; derive tag from source metadata")
    parser.add_argument("arguments", nargs="*", metavar="TAG SHA [ZIP DMG]")
    args = parser.parse_intermixed_args(argv)
    if args.sha is not None:
        selected_sha(args.sha)
        from source_version import read
        tag, sha, assets = f"v{read()}", args.sha, list(map(Path, args.arguments))
    else:
        if len(args.arguments) < 2:
            parser.error("requires TAG SHA, or --sha SHA to derive the source tag")
        tag, sha = args.arguments[:2]
        assets = list(map(Path, args.arguments[2:]))
    if args.command == "check":
        if assets:
            parser.error("check does not accept assets")
        version, tag = check(tag, sha)
        print(f"Available: {tag} at {sha}")
        if "GITHUB_OUTPUT" in os.environ:
            with open(os.environ["GITHUB_OUTPUT"], "a") as stream:
                stream.write(f"version={version}\ntag={tag}\n")
    else:
        publish(tag, sha, assets)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, plistlib.InvalidFileException,
            ExpatError, subprocess.CalledProcessError) as error:
        print(f"::error::{error}. Stopped without rollback/retry. Any remote tag, "
              "release and uploaded assets are retained. Manually inspect the exact tag, "
              "release and assets before deciding recovery; do not rerun to repair or overwrite.",
              file=sys.stderr)
        sys.exit(1)
