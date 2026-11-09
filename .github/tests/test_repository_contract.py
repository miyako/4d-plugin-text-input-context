"""Text Input Context preservation evidence, also valid after a source bump."""

import importlib.util
from pathlib import Path
import plistlib
import re
import stat
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
BASE = "45a4dcc87cb9ab5db4f2d655c77747ee3d971702"
sys.dont_write_bytecode = True
SPEC = importlib.util.spec_from_file_location(
    "contract_source", ROOT / ".github/scripts/source_version.py"
)
source = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(source)


def original(path):
    return subprocess.check_output(["git", "-C", str(ROOT), "show", f"{BASE}:{path}"])


class RepositoryContractTests(unittest.TestCase):
    def test_existing_coordinated_contract_and_original_trigger(self):
        bump = original(".github/workflows/bump-version.yml").decode()
        header, body = bump.split("name: Bump version", 1)
        self.assertIn("MARKETING_VERSION/CURRENT_PROJECT_VERSION AND Info.plist", header)
        self.assertIn("CFBundleShortVersionString/CFBundleVersion", header)
        self.assertIn('KEY="MARKETING_VERSION"', body)
        self.assertIn('KEY="CURRENT_PROJECT_VERSION"', body)
        release = original(".github/workflows/release.yml").decode()
        self.assertIn("  push:\n    tags:\n      - 'v*.*.*'", release)
        self.assertIn("  workflow_dispatch:", release)
        self.assertNotIn("pull_request:", release)
        self.assertNotIn("branches:", release)
        self.assertEqual(
            re.findall(r"^  ([a-z][a-z-]+):\n", release.split("\njobs:\n", 1)[1],
                       re.MULTILINE),
            ["version", "build-macos"],
        )

    def test_source_has_only_authorized_version_token_changes(self):
        current = source.read(ROOT)
        self.assertEqual(source.SETTING_COUNTS,
                         {"MARKETING_VERSION": 3, "CURRENT_PROJECT_VERSION": 6})
        for path in source.SOURCE_PATHS:
            with self.subTest(path=path):
                before = original(path)
                if path == source.LOCALIZED:
                    expected = before.replace(
                        b'CFBundleShortVersionString = "2.1.3";',
                        f'CFBundleShortVersionString = "{current}";'.encode(),
                    ).replace(
                        b"Text Input Context version 2.1.3, Copyright 2021 miyako.",
                        f"Text Input Context version {current}, Copyright 2021 miyako.".encode(),
                    )
                    self.assertNotIn(b"\n", before)
                    self.assertIn(b"\r", before)
                elif path == source.PROJECT:
                    expected = before.replace(
                        b"MARKETING_VERSION = 2.1.8;",
                        f"MARKETING_VERSION = {current};".encode(),
                    ).replace(
                        b"CURRENT_PROJECT_VERSION = 2.1.3;",
                        f"CURRENT_PROJECT_VERSION = {current};".encode(),
                    )
                else:
                    expected = before
                self.assertEqual((ROOT / path).read_bytes(), expected)
                mode = 0o755 if path == source.PLIST else 0o644
                self.assertEqual(stat.S_IMODE((ROOT / path).stat().st_mode), mode)
        self.assertEqual(
            plistlib.loads((ROOT / source.PLIST).read_bytes())["CFBundleShortVersionString"],
            "$(CURRENT_PROJECT_VERSION)",
        )
        self.assertNotIn(b"<key>CFBundleVersion</key>", (ROOT / source.PLIST).read_bytes())

    def test_all_unrelated_original_files_preserved(self):
        paths = subprocess.check_output(
            ["git", "-C", str(ROOT), "ls-tree", "-rz", "--name-only", BASE], text=True,
        ).rstrip("\0").split("\0")
        allowed = {*map(str, source.SOURCE_PATHS), "README.md",
                   ".github/workflows/bump-version.yml", ".github/workflows/release.yml"}
        for name in paths:
            if name in allowed:
                continue
            with self.subTest(path=name):
                self.assertEqual((ROOT / name).read_bytes(), original(name))

    def test_entire_prebuilt_plugin_tree_is_byte_identical(self):
        prefix = "test/Plugins/"
        entries = subprocess.check_output(
            ["git", "-C", str(ROOT), "ls-tree", "-rz", BASE, "--", prefix], text=True,
        ).rstrip("\0").split("\0")
        expected = set()
        for entry in entries:
            metadata, name = entry.split("\t", 1)
            mode = int(metadata.split()[0], 8)
            expected.add(name)
            with self.subTest(path=name):
                path = ROOT / name
                self.assertEqual(path.read_bytes(), original(name))
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), stat.S_IMODE(mode))
        actual = {
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / prefix).rglob("*") if path.is_file()
        }
        self.assertEqual(actual, expected)
        self.assertTrue(any("Text Input Service.bundle/" in name for name in expected))
        self.assertIn(
            "test/Plugins/Text Input Context.bundle/Contents/Windows64/Text Input Context.4DX",
            expected,
        )

    def test_unmodified_native_steps_and_secret_names(self):
        before = original(".github/workflows/release.yml").decode()
        after = (ROOT / ".github/workflows/release.yml").read_text()

        def block(workflow, name):
            return workflow.split(f"      - name: {name}\n", 1)[1].split(
                "\n      - name:", 1
            )[0].rstrip()

        for name in ("import Developer ID certificate", "store notarytool credentials"):
            with self.subTest(step=name):
                expected = block(before, name)
                if name == "store notarytool credentials":
                    expected = expected.replace("        run: |\n",
                                                "        run: |\n          set -euo pipefail\n")
                self.assertEqual(expected, block(after, name))
        secrets = r"\$\{\{ secrets\.([A-Z_]+) \}\}"
        self.assertEqual(re.findall(secrets, before), re.findall(secrets, after))
        for required in (
            'xcrun stapler staple "$DMG_PATH"', 'ARCHS="arm64 x86_64"',
            "-configuration Default", "CODE_SIGNING_ALLOWED=NO",
            "MACOS_DEPLOYMENT_TARGET: '11.0'", "ONLY_ACTIVE_ARCH=NO",
            'ditto -c -k --keepParent "$BUNDLE_PATH" "$ZIP_PATH"',
            'hdiutil create -format UDBZ -volname "${{ env.PRODUCT_NAME }}" -srcfolder "$BUNDLE_PATH" "$DMG_PATH"',
        ):
            if required != "CODE_SIGNING_ALLOWED=NO":
                self.assertIn(required, before)
            self.assertIn(required, after)
        for command in (
            'codesign --verbose --deep --timestamp --force --options=runtime',
            '--sign "$IDENTITY" "$BUNDLE_PATH"',
            'codesign --verify --deep --strict --verbose=2 "$BUNDLE_PATH"',
            'security find-identity -v -p codesigning "$KEYCHAIN_PATH"',
        ):
            self.assertIn(command, before)
            self.assertIn(command, after)
        self.assertIn('if [ -z "$IDENTITY" ]; then', after)
        self.assertIn('::error::', block(after, "codesign"))
        self.assertRegex(after,
                         r'CONFIGURATION_BUILD_DIR="\$PWD/(?:test/Plugins|\$PLUGINS_DIR)"')
        self.assertNotIn("runs-on: windows-", before)
        self.assertNotIn("runs-on: windows-", after)
        for required in ('notarize "$ZIP_PATH"', 'notarize "$DMG_PATH"',
                         'if [ "$STATUS" != "Accepted" ]; then'):
            self.assertIn(required, after)


if __name__ == "__main__":
    unittest.main()
