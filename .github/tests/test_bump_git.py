import contextlib
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / ".github/scripts"))
spec = importlib.util.spec_from_file_location("bump_source", ROOT / ".github/scripts/bump.py")
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)


@contextlib.contextmanager
def cwd(path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def git(path, *args, input=None):
    location = ["--git-dir", str(path)] if path.name.endswith(".git") else ["-C", str(path)]
    return subprocess.run(
        ["git", *location, *args], input=input, check=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ).stdout.strip()


class GitTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(os.environ, GIT_CONFIG_NOSYSTEM="1",
                                 GIT_CONFIG_GLOBAL=os.devnull)
        environment.start()
        self.addCleanup(environment.stop)
        self.temp = tempfile.TemporaryDirectory(prefix=".bump-git-tests-", dir=ROOT)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.remote = self.root / "remote.git"
        self.local = self.root / "local"
        self.peer = self.root / "peer"
        git(self.root, "init", "--bare", str(self.remote))
        git(self.root, "init", "-b", "selected", str(self.local))
        for key, value in (("user.name", "Bump Test"), ("user.email", "test@example.invalid"),
                           ("push.followTags", "true"), ("commit.gpgsign", "false")):
            git(self.local, "config", key, value)
        git(self.local, "commit", "--allow-empty", "-m", "ancestor")
        self.ancestor = git(self.local, "rev-parse", "HEAD")
        for path in source.SOURCE_PATHS:
            target = self.local / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / path, target)
        project = self.local / source.metadata.PROJECT
        project.write_bytes(project.read_bytes().replace(
            b"MARKETING_VERSION = 2.1.8;", b"MARKETING_VERSION = 2.1.3;").replace(
            b"CURRENT_PROJECT_VERSION = 2.1.8;", b"CURRENT_PROJECT_VERSION = 2.1.3;"))
        localized = self.local / source.metadata.LOCALIZED
        localized.write_bytes(localized.read_bytes().replace(b"2.1.8", b"2.1.3"))
        shutil.copytree(ROOT / ".github/scripts", self.local / ".github/scripts",
                        ignore=shutil.ignore_patterns("__pycache__"))
        git(self.local, "add", ".")
        git(self.local, "commit", "-m", "fixture")
        git(self.local, "remote", "add", "origin", str(self.remote))
        git(self.local, "push", "origin", "HEAD:refs/heads/selected")
        self.sha = git(self.local, "rev-parse", "HEAD")
        git(self.root, "clone", "--branch", "selected", str(self.remote), str(self.peer))
        git(self.peer, "config", "user.name", "Peer")
        git(self.peer, "config", "user.email", "peer@example.invalid")
        git(self.peer, "config", "commit.gpgsign", "false")
        enter = cwd(self.local)
        enter.__enter__()
        self.addCleanup(enter.__exit__, None, None, None)

    def assert_remote_unchanged(self):
        self.assertEqual(source.remote_ref("refs/heads/selected"), self.sha)
        self.assertEqual(git(self.remote, "tag", "--list"), "")

    def advance_peer(self):
        (self.peer / "peer.txt").write_text("concurrent branch update")
        git(self.peer, "add", ".")
        git(self.peer, "commit", "-m", "peer")
        git(self.peer, "push", "origin", "HEAD:refs/heads/selected")

    def test_explicit_nonforce_selected_branch_metadata_trailer_no_follow_tags(self):
        git(self.local, "tag", "-a", "unrelated-annotated", "-m", "must not follow")
        git(self.remote, "update-ref", "refs/heads/other", self.sha)
        original_plist = (self.local / source.metadata.PLIST).read_bytes()
        with patch.object(source, "run", wraps=source.run) as run:
            self.assertEqual(source.bump_branch(self.sha, "selected", "patch"), "2.1.4")
        new = git(self.local, "rev-parse", "HEAD")
        self.assertEqual(git(self.remote, "rev-parse", "refs/heads/selected"), new)
        self.assertEqual(git(self.remote, "rev-parse", "refs/heads/other"), self.sha)
        self.assertEqual(git(self.remote, "tag", "--list"), "")
        self.assertEqual(git(self.local, "rev-list", "--parents", "-n", "1", new),
                         f"{new} {self.sha}")
        self.assertEqual(git(self.local, "status", "--porcelain"), "")
        self.assertEqual(set(git(self.local, "diff-tree", "--no-commit-id", "--name-only",
                                 "-r", "HEAD").splitlines()),
                         {str(source.metadata.PROJECT), str(source.metadata.LOCALIZED)})
        self.assertEqual((self.local / source.metadata.PLIST).read_bytes(), original_plist)
        self.assertIn(source.TRAILER, git(self.local, "log", "-1", "--format=%B"))
        pushes = [call for call in run.call_args_list if "push" in call.args]
        self.assertEqual(len(pushes), 1)
        self.assertEqual(pushes[0].args, (
            "git", "-c", f"core.hooksPath={ROOT / '.github/scripts/bump-hooks'}",
            "-c", "push.followTags=false", "push", "--porcelain", "--no-follow-tags",
            "origin", f"{new}:refs/heads/selected"))

    def test_cli_no_bytecode_keeps_checkout_clean(self):
        env = os.environ.copy()
        env.pop("PYTHONDONTWRITEBYTECODE", None)
        subprocess.run(
            [sys.executable, ".github/scripts/bump.py", "bump",
             "--sha", self.sha, "--branch", "selected", "--mode", "patch"],
            env=env, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(git(self.local, "status", "--porcelain"), "")
        self.assertEqual(git(self.remote, "tag", "--list"), "")

    def test_cli_rejects_missing_or_invalid_intake_without_mutation(self):
        command = [sys.executable, ".github/scripts/bump.py"]
        valid = ["bump", "--sha", self.sha, "--branch", "selected", "--mode", "patch"]
        cases = [
            [], ["bump"], valid[:-2], valid[:1] + valid[3:], valid[:3] + valid[5:],
            [*valid[:-1], "invalid"], ["publish", *valid[1:]], [*valid, "--force"],
        ]
        for args in cases:
            with self.subTest(args=args):
                result = subprocess.run(command + args, check=False, capture_output=True,
                                        text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(git(self.local, "rev-parse", "HEAD"), self.sha)
                self.assertEqual(git(self.local, "status", "--porcelain"), "")
        self.assert_remote_unchanged()

    def test_initial_moved_or_missing_remote(self):
        self.advance_peer()
        for absent in (False, True):
            if absent:
                git(self.remote, "update-ref", "-d", "refs/heads/selected")
            with self.subTest(absent=absent), self.assertRaisesRegex(ValueError, "moved"):
                source.bump_branch(self.sha, "selected", "patch")
            self.assertEqual(git(self.local, "rev-parse", "HEAD"), self.sha)

    def test_dirty_tracked_untracked_and_staged_checkouts(self):
        for state in ("tracked", "untracked", "staged"):
            path = self.local / (str(source.metadata.PLIST) if state == "tracked" else "new.txt")
            original = path.read_bytes() if path.exists() else None
            path.write_bytes(b"dirty")
            if state == "staged":
                git(self.local, "add", ".")
            with self.subTest(state=state), self.assertRaisesRegex(ValueError, "clean checkout"):
                source.bump_branch(self.sha, "selected", "patch")
            git(self.local, "reset", "--hard", self.sha)
            if original is None and path.exists():
                path.unlink()
        self.assert_remote_unchanged()

    def test_race_during_preparation(self):
        real_bump = source.bump

        def concurrent_bump(mode):
            result = real_bump(mode)
            self.advance_peer()
            return result

        with patch.object(source, "bump", side_effect=concurrent_bump):
            with self.assertRaisesRegex(ValueError, "moved during"):
                source.bump_branch(self.sha, "selected", "minor")
        self.assertEqual(source.remote_ref("refs/heads/selected"),
                         git(self.peer, "rev-parse", "HEAD"))

    def advertised_race(self, kind):
        real_run = source.run
        expected = None
        pushes = 0

        def concurrent_push(*args, **kwargs):
            nonlocal expected, pushes
            if "push" in args:
                pushes += 1
                if kind == "rewind":
                    expected = self.ancestor
                    git(self.remote, "update-ref", "refs/heads/selected", expected)
                elif kind == "delete":
                    git(self.remote, "update-ref", "-d", "refs/heads/selected")
                elif kind == "advance":
                    self.advance_peer()
                    expected = git(self.peer, "rev-parse", "HEAD")
                elif kind == "same-result":
                    expected = git(self.local, "rev-parse", "HEAD")
                    git(self.remote, "fetch", "--no-tags", str(self.local), "HEAD")
                    git(self.remote, "update-ref", "refs/heads/selected", expected)
                else:
                    self.fail(kind)
            return real_run(*args, **kwargs)

        with patch.object(source, "run", side_effect=concurrent_push):
            with self.assertRaises(subprocess.CalledProcessError):
                source.bump_branch(self.sha, "selected", "patch")
        self.assertEqual(pushes, 1)
        self.assertEqual(source.remote_ref("refs/heads/selected"), expected)
        self.assertEqual(git(self.remote, "tag", "--list"), "")

    def test_after_final_read_rewind(self):
        self.advertised_race("rewind")

    def test_after_final_read_deletion(self):
        self.advertised_race("delete")

    def test_after_final_read_advance(self):
        self.advertised_race("advance")

    def test_after_final_read_same_result_zero_updates(self):
        self.advertised_race("same-result")

    def guard_loss(self, late, missing):
        runtime = self.root / "runtime"
        shutil.copytree(self.local / ".github/scripts", runtime)
        guard = runtime / "bump-hooks/pre-push"
        real_remote_ref = source.remote_ref
        reads = 0

        def lose_guard():
            if missing:
                guard.unlink()
            else:
                guard.chmod(0o644)

        def remote(ref):
            nonlocal reads
            result = real_remote_ref(ref)
            reads += 1
            if reads == 2:
                lose_guard()
            return result

        if not late:
            lose_guard()
        with patch.object(source, "__file__", str(runtime / "bump.py")), \
                patch.object(source, "remote_ref", side_effect=remote), \
                patch.object(source, "run", wraps=source.run) as run:
            with self.assertRaisesRegex(ValueError, "guard is missing or not executable"):
                source.bump_branch(self.sha, "selected", "patch")
            self.assertFalse(any("push" in call.args for call in run.call_args_list))
        self.assertEqual(reads, 2 if late else 0)
        if not late:
            self.assertEqual(git(self.local, "rev-parse", "HEAD"), self.sha)
        self.assert_remote_unchanged()

    def test_initial_missing_guard(self):
        self.guard_loss(False, True)

    def test_initial_nonexecutable_guard(self):
        self.guard_loss(False, False)

    def test_late_missing_guard(self):
        self.guard_loss(True, True)

    def test_late_nonexecutable_guard(self):
        self.guard_loss(True, False)

    def test_immutable_invalid_sha_and_branch(self):
        for sha in ("selected", "a" * 40, "a" * 39, "a" * 41, self.sha.upper()):
            with self.subTest(sha=sha), self.assertRaises(ValueError):
                source.selected_sha(sha)
        source.selected_sha(self.sha)
        for branch in ("invalid..branch", "-bad", "", "selected:other"):
            with self.subTest(branch=branch), \
                    self.assertRaises((subprocess.CalledProcessError, ValueError)):
                source.bump_branch(self.sha, branch, "patch")
        self.assert_remote_unchanged()

    def test_final_exact_remote_verification(self):
        real_remote_ref = source.remote_ref
        reads = 0

        def wrong_verification(ref):
            nonlocal reads
            result = real_remote_ref(ref)
            reads += 1
            return self.sha if reads == 3 else result

        with patch.object(source, "remote_ref", side_effect=wrong_verification):
            with self.assertRaisesRegex(ValueError, "Pushed branch failed exact-SHA"):
                source.bump_branch(self.sha, "selected", "patch")
        self.assertEqual(reads, 3)
        self.assertEqual(real_remote_ref("refs/heads/selected"),
                         git(self.local, "rev-parse", "HEAD"))

    def corrupt_commit(self, kind):
        real_run = source.run

        def after_commit(*args, **kwargs):
            result = real_run(*args, **kwargs)
            if args[:2] == ("git", "commit"):
                if kind == "non-source":
                    (self.local / "unrelated.txt").write_text("not metadata")
                    git(self.local, "add", ".")
                    git(self.local, "commit", "--amend", "--no-edit")
                else:
                    tree = git(self.local, "rev-parse",
                               f"{self.sha}^{{tree}}" if kind == "empty" else "HEAD^{tree}")
                    parents = ["-p", self.sha]
                    if kind == "merge":
                        parents += ["-p", self.ancestor]
                    elif kind == "wrong-parent":
                        parents = ["-p", self.ancestor]
                    message = "corrupted fixture\n\n" + (
                        "" if kind == "trailer" else source.TRAILER + "\n")
                    new = git(self.local, "commit-tree", tree, *parents, input=message)
                    git(self.local, "reset", "--hard", new)
            return result

        with patch.object(source, "run", side_effect=after_commit) as run:
            with self.assertRaises(ValueError):
                source.bump_branch(self.sha, "selected", "patch")
            self.assertFalse(any("push" in call.args for call in run.call_args_list))
        self.assert_remote_unchanged()

    def test_multiparent_commit_rejected_before_push(self):
        self.corrupt_commit("merge")

    def test_wrong_parent_rejected_before_push(self):
        self.corrupt_commit("wrong-parent")

    def test_non_source_commit_rejected_before_push(self):
        self.corrupt_commit("non-source")

    def test_empty_commit_rejected_before_push(self):
        self.corrupt_commit("empty")

    def test_missing_trailer_rejected_before_push(self):
        self.corrupt_commit("trailer")

    def test_guard_advertised_fields_single_update_and_required_env(self):
        guard = ROOT / ".github/scripts/bump-hooks/pre-push"
        git(self.local, "commit", "--allow-empty", "-m", "direct child")
        new = git(self.local, "rev-parse", "HEAD")
        env = {**os.environ, "BUMP_EXPECTED_SHA": self.sha,
               "BUMP_EXPECTED_REF": "refs/heads/selected", "BUMP_NEW_SHA": new}
        valid = f"{new} {new} refs/heads/selected {self.sha}\n"

        def invoke(row, environment):
            return subprocess.run([str(guard)], input=row, env=environment, text=True,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self.assertEqual(invoke(valid, env).returncode, 0)
        for row in (
            f"{new} {new} refs/heads/wrong {self.sha}\n",
            f"HEAD {new} refs/heads/selected {self.sha}\n",
            f"{new} {self.ancestor} refs/heads/selected {self.sha}\n",
            f"{new} {new} refs/heads/selected {self.ancestor}\n",
            f"{new} {new} refs/heads/selected {'0' * 40}\n",
            valid * 2, "", "malformed\n",
        ):
            with self.subTest(row=row):
                self.assertNotEqual(invoke(row, env).returncode, 0)
        for key in ("BUMP_EXPECTED_SHA", "BUMP_EXPECTED_REF", "BUMP_NEW_SHA"):
            with self.subTest(missing=key):
                self.assertNotEqual(invoke(valid, {k: v for k, v in env.items()
                                                   if k != key}).returncode, 0)
        git(self.local, "reset", "--hard", self.sha)
        self.assertNotEqual(invoke(valid, env).returncode, 0)
        self.assert_remote_unchanged()

    def test_guard_rejects_multiple_parents_with_selected_first_parent(self):
        tree = git(self.local, "rev-parse", "HEAD^{tree}")
        new = git(self.local, "commit-tree", tree, "-p", self.sha, "-p", self.ancestor,
                  input="merge fixture\n")
        git(self.local, "update-ref", "HEAD", new)
        guard = ROOT / ".github/scripts/bump-hooks/pre-push"
        result = subprocess.run(
            [str(guard)], input=f"{new} {new} refs/heads/selected {self.sha}\n",
            env={**os.environ, "BUMP_EXPECTED_SHA": self.sha,
                 "BUMP_EXPECTED_REF": "refs/heads/selected", "BUMP_NEW_SHA": new},
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("advertised branch state differs", result.stderr)
        result = subprocess.run(
            ["git", "-c", f"core.hooksPath={guard.parent}", "-c", "push.followTags=false",
             "push", "--porcelain", "--no-follow-tags", "origin",
             f"{new}:refs/heads/selected"],
            env={**os.environ, "BUMP_EXPECTED_SHA": self.sha,
                 "BUMP_EXPECTED_REF": "refs/heads/selected", "BUMP_NEW_SHA": new},
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("advertised branch state differs", result.stderr)
        self.assert_remote_unchanged()

    def test_real_push_rejects_multiple_branch_updates(self):
        git(self.remote, "update-ref", "refs/heads/other", self.sha)
        git(self.local, "commit", "--allow-empty", "-m", "direct child")
        new = git(self.local, "rev-parse", "HEAD")
        guard = ROOT / ".github/scripts/bump-hooks/pre-push"
        result = subprocess.run(
            ["git", "-c", f"core.hooksPath={guard.parent}", "-c", "push.followTags=false",
             "push", "--porcelain", "--no-follow-tags", "origin",
             f"{new}:refs/heads/selected", f"{new}:refs/heads/other"],
            env={**os.environ, "BUMP_EXPECTED_SHA": self.sha,
                 "BUMP_EXPECTED_REF": "refs/heads/selected", "BUMP_NEW_SHA": new},
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(git(self.remote, "rev-parse", "refs/heads/other"), self.sha)
        self.assert_remote_unchanged()

    def test_success_without_exactly_one_new_porcelain_update_fails_closed(self):
        real_run = source.run

        def fake_push(*args, **kwargs):
            if "push" in args:
                return "To origin\n=\tHEAD:refs/heads/selected\t[up to date]\nDone"
            return real_run(*args, **kwargs)

        with patch.object(source, "run", side_effect=fake_push):
            with self.assertRaisesRegex(ValueError, "not a new update"):
                source.bump_branch(self.sha, "selected", "patch")
        self.assert_remote_unchanged()

    def test_malformed_remote_responses_fail_closed(self):
        for output in (f"{self.sha} refs/heads/other", "broken", "a refs/heads/selected",
                       f"{self.sha} refs/heads/selected\n{self.sha} refs/heads/selected"):
            with self.subTest(output=output), patch.object(source, "run", return_value=output):
                with self.assertRaises(ValueError):
                    source.remote_ref("refs/heads/selected")


if __name__ == "__main__":
    unittest.main()
