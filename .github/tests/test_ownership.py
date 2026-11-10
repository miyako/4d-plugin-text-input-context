"""Compile actual consumers and complete bundled SDK; never build the plugin project."""

import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(os.environ.get("OWNERSHIP_SOURCE_ROOT", ROOT)).resolve()
SDK = {
    "4DPluginAPI.c": "204e69ce84415ac2dc1a884a466d9bff6a182e05",
    "4DPluginAPI.h": "a5bbd591457ec2c3f39e2ad025c4e32f72604f9b",
    "4DPluginAPI.def": "5bbdb82fb724b6f8e307feb01d9f158b802de89d",
    "EntryPoints.h": "4ae62f8ede4c7817caa5a32b12ea8a34c8c2e110",
    "Flags.h": "7a5a35539f27430a3fd9cb711d6b789051316471",
    "PrivateTypes.h": "a3098cb662cdbc43ba574fdef72a059c4c6d1cd4",
    "PublicTypes.h": "9ae20b001bff9128f690fff3e6c3f873b6238333",
}


@unittest.skipUnless(sys.platform == "darwin", "macOS synthetic host")
class OwnershipTests(unittest.TestCase):
    runs = 0
    passes = 0

    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="text-input-ownership-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.binary = Path(cls.temp.name) / "ownership"
        api = SOURCE / "4D Plugin API"
        for name, expected in SDK.items():
            contents = (api / name).read_bytes()
            blob = hashlib.sha1(f"blob {len(contents)}\0".encode() + contents).hexdigest()
            if blob != expected:
                raise AssertionError(f"Re-audit changed SDK: {name}: {blob}")
        flags = ["-DOWNERSHIP_BASELINE_COPY"] if os.environ.get("OWNERSHIP_BASELINE_COPY") else []
        result = subprocess.run([
            "clang++", "-std=c++14", "-x", "objective-c++", "-fblocks",
            "-include", str(ROOT / ".github/tests/ownership_platform.h"),
            "-I", str(api), "-I", str(api / "Classes"), "-I", str(SOURCE / "support"),
            "-I", str(SOURCE), *flags,
            "-fsanitize=address,undefined", "-fno-sanitize=alignment",
            "-fno-omit-frame-pointer", "-g",
            "-Wno-deprecated-declarations", "-Wno-return-type-c-linkage",
            "-Wno-ignored-attributes", "-Wno-writable-strings",
            str(api / "4DPluginAPI.c"),
            *map(str, sorted((api / "Classes").glob("*.cpp"))),
            str(SOURCE / "support/4DPlugin-JSON.cpp"),
            str(SOURCE / "4DPlugin-Text-Input-Context.cpp"),
            str(ROOT / ".github/tests/ownership_host.mm"),
            "-framework", "Cocoa", "-framework", "Carbon", "-o", str(cls.binary),
        ], capture_output=True, text=True)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        imports = subprocess.check_output(["nm", "-u", str(cls.binary)], text=True)
        linked = {line.split()[-1] for line in imports.splitlines() if line.split()}
        allowed_classes = {
            "_OBJC_CLASS_$_NSObject", "_OBJC_CLASS_$_NSString",
            "_OBJC_CLASS_$_NSMutableString", "_OBJC_CLASS_$_NSArray",
            "_OBJC_CLASS_$_NSMutableArray",
        }
        denied = {name for name in linked if name.startswith("_OBJC_CLASS_$_")
                  and name not in allowed_classes}
        denied |= {name for name in linked if name.startswith((
            "_TIS", "_CGImage", "_CGContext", "_CFURL", "_AX", "_IO",
            "_Audio", "_AVAudio", "_dispatch_", "_NSAllRoman",
        ))}
        denied |= {
            "_system", "_popen", "_execve", "_posix_spawn", "_kill", "_NSApp",
            "_open", "_fopen", "_socket", "_connect", "_getenv",
        } & linked
        if denied:
            raise AssertionError(f"Real platform boundary linked: {denied}")

    @classmethod
    def tearDownClass(cls):
        print(f"LEAF runs={cls.runs} passed={cls.passes} "
              f"failed={cls.runs - cls.passes}", file=sys.stderr)

    def case(self, name, text="ASCII", empty="allocated", kind="string"):
        type(self).runs += 1
        result = subprocess.run(
            [str(self.binary), name, text, empty, kind],
            env={**os.environ, "ASAN_OPTIONS": "detect_leaks=0",
                 "UBSAN_OPTIONS": "halt_on_error=1"},
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            type(self).passes += 1
        self.assertEqual(result.returncode, 0, f"{name}/{text}/{empty}/{kind}: "
                         f"{result.stdout}{result.stderr}")
        self.assertIn("strings=0 pictures=0 handles=0 objects=0 collections=0", result.stdout)

    def test_setter_empty_owner_overwrite(self):
        for setter in ("set-narrow", "set-wide", "set-wchars", "set-utf16"):
            for text in ("ASCII", "\u65e5", "\U0001f600", ""):
                for empty in ("allocated", "null"):
                    with self.subTest(setter=setter, text=text, empty=empty):
                        self.case(setter, text, empty)
        self.case("set-picture")

    def test_getter_success_owners_and_mismatches(self):
        for getter in ("get-a", "get-b", "get-n", "get-c", "get-o"):
            for kind in ("string", "picture", "object", "collection", "boolean", "real"):
                for empty in ("allocated", "null"):
                    with self.subTest(getter=getter, kind=kind, empty=empty):
                        self.case(getter, "\u65e5\U0001f600", empty, kind)
            for empty in ("allocated", "null"):
                with self.subTest(getter=getter, empty=empty):
                    self.case(getter, "", empty, "string")

    def test_failed_unspecified_returns_and_stringify(self):
        for text in ("ASCII", "\u65e5", "\U0001f600", ""):
            for empty in ("allocated", "null"):
                with self.subTest(text=text, empty=empty):
                    self.case("stringify", text, empty)
        for kind in ("picture", "object", "collection", "boolean", "real"):
            with self.subTest(kind=kind):
                self.case("stringify", kind=kind)
        for case in ("get-a", "get-b", "get-n", "get-c", "get-o", "stringify"):
            for kind in ("error-poison", "error-kind0"):
                with self.subTest(case=case, kind=kind):
                    self.case(case, kind=kind)
        for kind in ("error-handle", "error-first-handle", "error-copy",
                     "copy-string", "copy-picture", "copy-collection", "copy-boolean", "copy-real"):
            with self.subTest(kind=kind):
                self.case("stringify", kind=kind)

    def test_actual_dispatcher_and_array_controls(self):
        for empty in ("allocated", "null"):
            for text in ("ASCII", "\u65e5", "\U0001f600", ""):
                for name in (*(f"dispatch-{i}" for i in range(1, 8)), "array", "wrappers"):
                    with self.subTest(name=name, text=text, empty=empty):
                        self.case(name, text, empty)
            for i in range(1, 8):
                with self.subTest(selector=i, empty=empty, kind="nil-context"):
                    self.case(f"dispatch-{i}", empty=empty, kind="nil-context")
        for kind in ("no-metadata", "icon-ref", "image-failure"):
            with self.subTest(kind=kind):
                self.case("dispatch-7", kind=kind)
        for case in ("sdk-failures", "values", "null-controls", "missing", "copy-traits"):
            with self.subTest(case=case):
                self.case(case)

    @unittest.skipUnless(os.environ.get("OWNERSHIP_BASELINE_COPY"), "baseline-only unsafe copies")
    def test_baseline_copy_sanitizer(self):
        for case in ("copy-array", "assign-array"):
            with self.subTest(case=case):
                self.case(case)


if __name__ == "__main__":
    unittest.main()
