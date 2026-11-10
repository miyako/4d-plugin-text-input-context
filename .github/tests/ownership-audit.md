# Native ownership audit

## Provenance and scope

Baseline: `80ff2bc01c7b1543c65d323a269564a33899c654`,
tree `ac49423dea734afdd997db5349acf73977a38545`.
Guidance: `miyako/skills/4d-skills/skills/4dplugin/SKILL.md` at immutable
`e6b492fcb81e5e1a7f7db723594b420e63bf6eb9`, read through the GitHub API.
Boundary-model prior art: `miyako/4d-plugin-tab-ui` at
`0783b28c28192645672aec5884f83bbf32a29b69`; results below are from this
repository's actual sources, not copied prior-art results.

The complete bundled SDK is compiled unchanged, not extracted functions or
replacement implementations. Its source header says "rev : v14", which is
not proof of a specific upstream release. Pinned Git blob identities:

| SDK file under `4D Plugin API/` | Git blob |
|---|---|
| `4DPluginAPI.c` | `204e69ce84415ac2dc1a884a466d9bff6a182e05` |
| `4DPluginAPI.h` | `a5bbd591457ec2c3f39e2ad025c4e32f72604f9b` |
| `4DPluginAPI.def` | `5bbdb82fb724b6f8e307feb01d9f158b802de89d` |
| `EntryPoints.h` | `4ae62f8ede4c7817caa5a32b12ea8a34c8c2e110` |
| `Flags.h` | `7a5a35539f27430a3fd9cb711d6b789051316471` |
| `PrivateTypes.h` | `a3098cb662cdbc43ba574fdef72a059c4c6d1cd4` |
| `PublicTypes.h` | `9ae20b001bff9128f690fff3e6c3f873b6238333` |

## Complete native inventory

Tracked native translation units are the SDK above, the actual
`4DPlugin-Text-Input-Context.cpp` dispatcher, `support/4DPlugin-JSON.cpp`,
and exactly three wrappers: `ARRAY_TEXT.cpp`, `C_TEXT.cpp`, `C_LONGINT.cpp`.
Their headers, `Classes/C_TYPES.h`, the dispatcher header and JSON header
were included in the review. No alternative SDK or platform-specific native
source copy is tracked. SDK exports are `FourDPackex`; that entry forwards
to `PluginMain`, which dispatches selectors 1-7.

Xcode compiles SDK + dispatcher + JSON + `ARRAY_TEXT` + `C_TEXT`.
`C_LONGINT` is dormant in Xcode but is compiled and exercised by the harness.
Both legacy Windows project files list SDK + `ARRAY_TEXT`, `C_TEXT`,
`C_LONGINT`, thirteen absent wrapper sources, and absent `4DPlugin.cpp`;
they do not list this actual dispatcher or JSON helper. Those stale project
memberships are not repaired by this ownership change. README and source
identify this plugin as macOS-only; compiling macOS is not Windows evidence.

Baseline wrapper blobs (all under `4D Plugin API/Classes/`):

| File | Git blob |
|---|---|
| `ARRAY_TEXT.cpp` | `534855e0959020ce9a66cef08f8434799c174495` |
| `ARRAY_TEXT.h` | `cf8a458fc8519b824c726a59d346c44d4c26e845` |
| `C_TEXT.cpp` | `45ea6432dff52b681a5c6a7cea58ad5fc15df66b` |
| `C_TEXT.h` | `6967390757db569ffcd3cfea8696bf14045cc748` |
| `C_LONGINT.cpp` | `005b83a4aec2c1466b8b219cb27ab845eb58de91` |
| `C_LONGINT.h` | `71e24df633aed7155cba1ffddc07d6a1dfc12fa9` |
| `C_TYPES.h` | `972cf3f597a8c21881a8c9aa69bc1699455be373` |

The manifest has text-array parameters at selectors 1, 4 and 5, scalar
text at 2 and 3, collection return at 6, and object return at 7.
Selector 7 internally constructs a collection of language strings and a
picture property. JSON helpers include dormant scalar, object, collection,
picture and stringify paths; all are included, not excluded by the manifest.
The packaged manifest copies and binaries are prebuilt artifacts, not
authoritative native source, and are unchanged.

There is no tracked `CPicture`, pointer wrapper, `setBytes` or `createCopy`
implementation in this target. The concrete picture path is
`PA_CreatePicture` -> `ob_set_p` -> property copy/retain -> variable clear:
it had an empty-picture overwrite leak, not a second explicit picture
dispose or a borrowed-picture escape. No generic cross-repository picture
fix or pointer metadata is invented here.

## Source-derived contracts and fixes

`PA_CreateVariable(eVK_Unistring/eVK_Picture)` creates an initial empty
owner (SDK lines 3920-4060). `PA_SetStringVariable` (4254) and
`PA_SetPictureVariable` (4280) shallow-assign and do not clear that owner.
The four JSON text setter overloads, picture setter and selector 7 language
temporary now start Undefined before adopting their distinct owned value.
Their final variable clear is retained. The property/collection engine
boundary copies strings or retains reference/picture values before the
temporary is cleared.

`PA_GetObjectProperty` (637) and `PA_GetCollectionElement` (587) explicitly
require clearing successful owning results. Scalar JSON getters now clear
after copying, including mismatches. Object/collection getters clear only
successful mismatches, preserving a matching owned reference for the caller.
Every property getter captures the error immediately and does not inspect,
adopt or clear an unspecified failed result. Raw failed `fType == 0` is
particularly important because `UnifyVarKind` (1713) normalizes it to text.

`ob_stringify` captures duplicate/execute errors before kind inspection or
argument cleanup. It executes OB Copy through the actual SDK command
boundary rather than using `PA_DuplicateObject`, whose implementation
extracts a reference before the caller can check the command error.
Successful wrong-kind copy/results are cleared; successful strings are
copied before result cleanup. Synchronous argument cleanup remains correct
and independent of the returned owner.

`PA_SetStringInArray` (4933) disposes the previous element and shallow
transfers the incoming allocation only for Unicode-array kind, non-null
data, `0 <= index <= count`, non-null descriptor. Index zero is accepted.
Rejections retain caller ownership. `ARRAY_TEXT::toParamAtIndex` already
has no post-transfer disposal; that behavior is preserved. Its getter
copies borrowed element content into C++ storage before later array
mutation. `C_TEXT` uses SDK content setters for parameters/results and
already prohibits copying. `C_LONGINT` owns no heap allocation.

`ARRAY_TEXT` alone still had implicit copies of its raw owned vector.
Named baseline probes `copy-array` and `assign-array` produce ASan
heap-use-after-free reports; fixed traits reject both operations, using
the existing `C_TEXT` noncopyable pattern. Every actual consumer compiles
with the restriction. No production wrapper-copy call was found: this is
a latent ownership defect, not a demonstrated production invocation.

## Isolated regression evidence

Run on macOS, without project builds or a 4D host:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 .github/tests/test_ownership.py
```

For comparison, export baseline native sources using `git archive` at the
full baseline SHA above (`4D Plugin API`, `support`, dispatcher .cpp/.h),
then run the exact same final test files with
`OWNERSHIP_SOURCE_ROOT=/absolute/archive/path`. Set
`OWNERSHIP_BASELINE_COPY=1` only for the two intentionally unsafe baseline
copy probes; fixed builds omit that code and assert noncopyable traits.

| Final harness group | Baseline leaves | Baseline failures | Fixed leaves | Fixed failures |
|---|---:|---:|---:|---:|
| Dispatcher, wrappers, arrays and controls | 94 | 16 | 94 | 0 |
| Setter empty-owner overwrite | 33 | 17 | 33 | 0 |
| Getter owners and mismatches | 70 | 41 | 70 | 0 |
| Failed results, stringify, wrong-kind copy | 33 | 16 | 33 | 0 |
| Baseline-only unsafe copy probes | 2 | 2 | 0 | 0 |
| Total | 232 | 92 | 230 | 0 |

Baseline: 140 passing controls, 92 failures. Fixed: 230/230 pass.
The two extra baseline leaves are intentional sanitizer probes, not
silently skipped regressions. The shared `copy-traits` assertion fails on
baseline and passes on fixed. Named failure families include
`set-narrow/wide/wchars/utf16`, `set-picture`, `get-a/b/n/c/o`,
`dispatch-6/7`, `stringify/error-poison`, `stringify/error-kind0`,
`stringify/error-handle`, `stringify/error-first-handle`,
`stringify/error-copy`, `stringify/copy-*`, and the two copy probes.

Final harness SHA-256:

| File | SHA-256 |
|---|---|
| `ownership_host.mm` | `ad6b72e546f43db2ece798d9c499842bdd718cf1831917e8218bb5f646e65d64` |
| `ownership_platform.h` | `252fb54103dae7fbc9e764b018c3545450822b50a975668db3c80c18b9476a9e` |
| `test_ownership.py` | `eece0784427425049ba10177554d9922751ed6a48b2f02b83cd79e7522c28a8b` |

The harness compiles full SDK, all three actual wrapper .cpp files, JSON
and the actual dispatcher under ASan/UBSan (alignment excluded for packed
SDK structures). macOS LeakSanitizer is disabled; explicit final string,
picture, handle, object and collection balances must all be zero.
Picture/reference retain counts are checked across property/collection
copy and final cleanup. Synthetic image/URL owners are checked before
and after the outer autorelease pool.

Fixtures cover ASCII, BMP, supplementary surrogate pairs, empty text,
allocated/null engine-empty descriptors, exact UTF-16 lengths/content and
terminator bounds, scalar/array UTF-8 round trips, repeated replacement,
allocator churn, resize/clear, borrowed-copy independence, index-zero
assignment, all rejection predicates, nil context, metadata absence,
icon-reference path and image encoding failure.

Before any dispatch, a linked-import gate rejects real context, keyboard,
window, UI, URL/path, image, dispatch, I/O and process APIs. Every actual
context/TIS/image/URL boundary is replaced before compilation. Unexpected
engine selectors and synthetic operations fail closed; context operations
also require the synthetic main callback. Foundation strings/arrays and
CoreFoundation in-memory string/data conversion remain real pure-memory
operations. No context activation, keyboard enumeration, user settings,
input capture/injection, UI, real image/file access or platform dispatch
is performed.

## Limits and unchanged failure policy

This is synthetic ownership/sanitizer evidence, not a Windows or native
4D ABI test, real IME integration test, or reproduction of a host crash.
Windows conversion branches are not compiled/executed. Foundation and the
modeled engine's successful copy/retain contracts do not certify every
host version or allocation failure.

The SDK resize helper updates count even after failed storage growth and
may dispose removed elements before a failed shrink. OOM state preservation
and safe wrapper rollback require a verified engine contract; SDK/ABI
rewrites are deliberately deferred. `sdk-failures` checks only low-level
handle/resize failure predicates and modeled capacity, not array OOM
safety. Creation failures, null array data, pathological counts, C++
allocation exceptions and embedded-NUL behavior of NUL-terminated SDK
setters are not certified by the successful fixtures.

Existing command/helper failure behavior remains silent (unchanged output,
false/zero/null or empty command results); no new exception/error channel
is added. An unspecified failed engine return is not a successful owner.
This fixes unsafe inspection/cleanup but does not close the existing
diagnostic gap. Existing exception-path resource cleanup outside these
confirmed paths is not certified.

Both existing workflows (`Build`, `Bump version`) are manual-only. All
workflow scripts and native build phases were inspected; Xcode Deployment
signs, packages and submits notarization. Neither project build, release
script nor publication workflow is invoked. The new ownership workflow is
read-only, unsigned, path-filtered and push-only on the exact audit branch
and `master`; it runs only the synthetic harness and publishes no binary.
Existing projects, workflows, manifests, versions and binaries are untouched.
