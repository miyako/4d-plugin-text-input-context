![version](https://img.shields.io/badge/version-17%2B-3E8B93)
![platform](https://img.shields.io/static/v1?label=platform&message=mac-intel%20|%20mac-arm&color=blue)
[![license](https://img.shields.io/github/license/miyako/4d-plugin-text-input-context)](LICENSE)
![downloads](https://img.shields.io/github/downloads/miyako/4d-plugin-text-input-context/total)
![deprecated](https://img.shields.io/badge/-deprecated-inactive)

---

# 4d-plugin-text-input-context

Text Input Context lets 4D read and change the macOS keyboard input source (keyboard layout or input method, e.g. U.S., ABC, Japanese Romaji) of the text area that has focus. It can also restrict which input sources the user can switch to. It drives AppKit's `NSTextInputContext` API, and for the detailed source info it also uses the Text Input Source Services API (`TISCopyCurrentKeyboardInputSource`). Results come back as `Text`, `Text array`, `Collection` and `Object`, and the current source's icon comes back as a `Picture`.

| Command | Returns | Purpose |
|---|---|---|
| [`Input sources list`](#input-sources-list) | `Collection` | Enabled input sources, each as `{id; name}` |
| [`Get input source`](#get-input-source) | `Object` | Details of the selected input source, including its icon |
| [`SET INPUT SOURCE`](#set-input-source) | — | Select an input source by ID |
| [`GET INPUT SOURCE LOCALES`](#get-input-source-locales) | `Text array` (by reference) | Current locale restriction |
| [`SET INPUT SOURCE LOCALES`](#set-input-source-locales) | — | Restrict or unrestrict the allowed input sources |
| [`_o_INPUT SOURCES LIST`](#_o_input-sources-list) | `Text array` (by reference) | **Obsolete.** IDs only; use [`Input sources list`](#input-sources-list) |
| [`_o_Get input source`](#_o_get-input-source) | `Text` | **Obsolete.** ID only; use [`Get input source`](#get-input-source) |

**Platforms:** macOS only (Intel and Apple silicon), 4D v17 or later. The plugin has no Windows implementation.

---

## Requirements & platform notes

- **Everything applies to the current input context.** macOS keeps one input context per text area. The "current" one belongs to the text object that has keyboard focus in the active window. If nothing has focus (no form open, a button has focus, or the method runs without a UI), there may be no current context. In that case:
  - getters return an empty result (empty array, empty collection, empty object or `""`)
  - setters do nothing
  - no 4D error is raised in either case

  Call these commands from form code while the intended field has focus, for example in `On Getting Focus`.
- **Settings are per context, not system-wide.** A source or locale restriction you set applies to the focused text area's context. Expect to apply it again when focus moves to another field. Exactly when AppKit carries a setting across fields depends on the macOS version, so test it in your own forms.
- **Failure is silent.** No command in this plugin raises a 4D error. An invalid input-source ID, an unknown locale, or a missing context leaves things unchanged, or returns an empty value.
- **Call from the application process, not a preemptive worker.** The manifest marks every command thread-safe. Internally, though, each command hands its work to 4D's main process (`PA_RunInMainProcess`), and the plugin's own README states that this mechanism is not thread safe. A preemptive process has no focused text area anyway, so you would only get empty results. Call the commands from cooperative or form code.
- **Only enabled sources are listed.** The lists contain the input sources the user has added in System Settings › Keyboard › Input Sources, not every source macOS ships with.
- **The project is marked deprecated** in its README. It still works as documented here, but don't expect new features.
- **Behaviour that depends on the reviewed source build.** Two behaviours below are only guaranteed in a build of the reviewed source (October 2026). Earlier binaries may differ:
  - the `name` property being omitted, rather than the plugin failing, when macOS has no localized name for a source
  - an empty locale array being passed to macOS as "no restriction"

---

## Input sources list

### Syntax

```
Input sources list -> sources
```

| Parameter | Type | Description |
|---|---|---|
| Result | `Collection` | One object per enabled input source; empty collection if there is no current input context |

Each element:

| Property | Type | Description |
|---|---|---|
| `id` | `Text` | Input-source identifier, e.g. `com.apple.keylayout.US`, `com.apple.inputmethod.Kotoeri.RomajiTyping.Japanese` |
| `name` | `Text` | Localized display name as shown in the macOS input menu (in the system language). Omitted if macOS returns no name for that ID |

### Description

Returns the input sources the user can switch to in the current input context. The order is the one macOS returns. Use an element's `id` with [`SET INPUT SOURCE`](#set-input-source).

### Example

From the plugin's own test method (`TEST.4dm`):

```4d
C_COLLECTION:C1488($colSources)
$colSources:=Input sources list   //OK
```

Find the first Japanese input method and keep its ID:

```4d
C_COLLECTION($colSources)
C_OBJECT($source)
C_TEXT($japaneseID)

$colSources:=Input sources list
For each ($source;$colSources)
	If ($japaneseID="")
		If (Position("Japanese";$source.id)>0)
			$japaneseID:=$source.id
		End if 
	End if 
End for each 
```

---

## Get input source

### Syntax

```
Get input source -> info
```

| Parameter | Type | Description |
|---|---|---|
| Result | `Object` | Details of the selected input source; empty object if there is no current input context |

| Property | Type | Description |
|---|---|---|
| `id` | `Text` | Identifier of the selected input source in the current context |
| `name` | `Text` | Localized display name. Omitted if unavailable |
| `category` | `Text` | Text Input Source category, e.g. `TISCategoryKeyboardInputSource` |
| `type` | `Text` | Text Input Source type, e.g. `TISTypeKeyboardLayout` (a plain layout) or `TISTypeKeyboardInputMode` (a mode of an input method such as Japanese) |
| `languages` | `Collection` of `Text` | Language codes the source supports, e.g. `["ja"]`, `["en"]` |
| `icon` | `Picture` | The source's menu-bar icon, encoded as TIFF. Omitted if macOS gives no icon or it can't be rendered |

### Description

`id` and `name` come from the current input context (AppKit). `category`, `type`, `languages` and `icon` describe the system's current keyboard input source (Text Input Source Services). Normally both refer to the same source.

Each property is set only when macOS provides it, so test for it before using it (e.g. `If ($info.icon#Null)`).

**Performance:** every call reads the icon file from disk and converts it to TIFF. If you poll this command (for example in `On Timer`) and only need the ID, call it less often or keep the last result.

### Example

From the plugin's own test method (`TEST.4dm`):

```4d
$objSsource:=Get input source   //OK
```

Show the current source's name and icon in a form:

```4d
C_OBJECT($info)
C_PICTURE(vInputIcon)

$info:=Get input source
If ($info.id#Null)
	If ($info.icon#Null)
		vInputIcon:=$info.icon
	End if 
	If ($info.name#Null)
		ALERT("Current input source: "+$info.name)
	End if 
End if 
```

---

## SET INPUT SOURCE

### Syntax

```
SET INPUT SOURCE ( sourceID )
```

| Parameter | Type | Description |
|---|---|---|
| `sourceID` | `Text` | Identifier of the input source to select, e.g. an `id` from [`Input sources list`](#input-sources-list) |
| Result | — | None |

### Description

Selects `sourceID` in the current input context.

**After selecting the source, the command also limits the context to Roman input sources** (the same effect as calling [`SET INPUT SOURCE LOCALES`](#set-input-source-locales) with `ALL ROMAN INPUT SOURCES`). Two consequences:

- After `SET INPUT SOURCE`, the user can only switch between Roman sources in that context.
- Selecting a **non-Roman** source (Japanese, Chinese, Korean input methods, and so on) may not stay selected, because the restriction applied immediately afterwards excludes it.

To lift the restriction, call [`SET INPUT SOURCE LOCALES`](#set-input-source-locales) with an empty array.

An unknown or disabled ID, or an empty string, does nothing visible and raises no error. Check the result with [`Get input source`](#get-input-source) if it matters.

### Example

The plugin's test methods don't call this command. Illustrative usage, typically in a field's object method:

```4d
Case of 
	: (Form event code=On Getting Focus)
		SET INPUT SOURCE("com.apple.keylayout.US")
End case 
```

Return to whatever was selected before:

```4d
C_OBJECT($before)

$before:=Get input source
// ... user edits ...
If ($before.id#Null)
	SET INPUT SOURCE($before.id)
End if 
```

---

## GET INPUT SOURCE LOCALES

### Syntax

```
GET INPUT SOURCE LOCALES ( locales )
```

| Parameter | Type | Description |
|---|---|---|
| `locales` | `Text array` | Receives the locale restriction of the current input context |
| Result | — | None |

### Description

Fills `locales` with the locale identifiers the current input context is restricted to. The Roman-only restriction comes back as the text `ALL ROMAN INPUT SOURCES`.

As with any 4D array, element 0 is not used. Values start at element 1.

`locales` comes back with **0 elements** when there is no restriction or no current input context. You can't tell these two cases apart from the array alone.

### Example

```4d
ARRAY TEXT($locales;0)
GET INPUT SOURCE LOCALES($locales)
If (Size of array($locales)=0)
	// no restriction (or no focused text area)
Else 
	If (Find in array($locales;"ALL ROMAN INPUT SOURCES")>0)
		// Roman-only
	End if 
End if 
```

---

## SET INPUT SOURCE LOCALES

### Syntax

```
SET INPUT SOURCE LOCALES ( locales )
```

| Parameter | Type | Description |
|---|---|---|
| `locales` | `Text array` | Locales to allow (elements 1…N); empty array to remove the restriction |
| Result | — | None |

### Description

Restricts the current input context to input sources for the given locales. The user can then only switch between those sources.

- The value `ALL ROMAN INPUT SOURCES` (exact text, case-sensitive) means all Roman-script input sources.
- Other elements are passed to macOS as locale identifiers, for example `ja` or `en`.
- Empty elements are ignored.
- An empty array, or one with only empty elements, removes the restriction.

The plugin's test method assigns `ALL ROMAN INPUT SOURCES` without quotes, so the plugin evidently ships a constant with that name. The constants file wasn't available for this reference. Either way, the plugin matches the text `"ALL ROMAN INPUT SOURCES"`, so the quoted string literal works too.

### Example

From the plugin's own test method (`TEST.4dm`):

```4d
ARRAY TEXT:C222($locales;1)
$locales{1}:=ALL ROMAN INPUT SOURCES
SET INPUT SOURCE LOCALES ($locales)  //limit to ascii

ARRAY TEXT:C222($locales;0)
SET INPUT SOURCE LOCALES ($locales)  //any locale
```

Allow only Japanese input sources in a field:

```4d
Case of 
	: (Form event code=On Getting Focus)
		ARRAY TEXT($locales;1)
		$locales{1}:="ja"
		SET INPUT SOURCE LOCALES($locales)
	: (Form event code=On Losing Focus)
		ARRAY TEXT($locales;0)
		SET INPUT SOURCE LOCALES($locales)
End case 
```

---

## _o_INPUT SOURCES LIST

### Syntax

```
_o_INPUT SOURCES LIST ( sources )
```

| Parameter | Type | Description |
|---|---|---|
| `sources` | `Text array` | Receives the input-source IDs |
| Result | — | None |

### Description

**Obsolete.** Kept for compatibility. Use [`Input sources list`](#input-sources-list), which also returns display names.

Fills `sources` with the IDs of the enabled input sources, starting at element 1. The array has 0 elements if there is no current input context.

### Example

From the plugin's own test methods (`TEST_LIST.4dm`, `TEST.4dm`):

```4d
ARRAY TEXT:C222($sources;0)
_o_INPUT SOURCES LIST ($sources)  //OK
```

---

## _o_Get input source

### Syntax

```
_o_Get input source -> sourceID
```

| Parameter | Type | Description |
|---|---|---|
| Result | `Text` | ID of the selected input source; `""` if there is no current input context |

### Description

**Obsolete.** Kept for compatibility. Use [`Get input source`](#get-input-source) and read its `id` property.

### Example

From the plugin's own test method (`TEST.4dm`):

```4d
$source:=_o_Get input source   //OK
```

---

## Error handling & troubleshooting

- **Everything comes back empty.** No text area has focus, so there is no current input context. Call the command from form code while a text field or text variable has focus (e.g. `On Getting Focus`), not from a startup method, a button, or a worker.
- **No 4D errors, ever.** Invalid IDs, unknown locales and a missing context all fail silently. To confirm a change worked, read the value back with [`Get input source`](#get-input-source) or [`GET INPUT SOURCE LOCALES`](#get-input-source-locales).
- **A Japanese/Chinese/Korean source won't stay selected after `SET INPUT SOURCE`.** [`SET INPUT SOURCE`](#set-input-source) also restricts the context to Roman sources. To use non-Roman sources, call [`SET INPUT SOURCE LOCALES`](#set-input-source-locales) with an empty array, or with the matching locale.
- **After `SET INPUT SOURCE`, the user can't switch to their usual input method.** The Roman-only restriction is still active. Clear it with [`SET INPUT SOURCE LOCALES`](#set-input-source-locales) and an empty array (e.g. in `On Losing Focus`).
- **The setting is lost when moving to another field.** Restrictions and selections belong to each text area's input context. Apply them again in each field's `On Getting Focus`.
- **A source is missing from the list.** Only sources enabled in System Settings › Keyboard › Input Sources are returned.
- **`name`, `icon` or another property is missing.** macOS provided no value for that source. Test with `#Null` before using it.
- **UI stutters when polling.** [`Get input source`](#get-input-source) builds the icon on every call. Poll less often, or cache the result and compare `id`.
- **Empty results in a preemptive process.** Workers have no focused text area, and the plugin's main-process mechanism isn't meant for preemptive use. Call from the application process.

---

## Quick reference

```4d
C_COLLECTION($all)
C_OBJECT($info)

$all:=Input sources list                 // [{id;name}]
$info:=Get input source                  // {id;name;category;type;languages;icon}

SET INPUT SOURCE("com.apple.keylayout.US")   // also limits to Roman sources

ARRAY TEXT($locales;1)
$locales{1}:="ALL ROMAN INPUT SOURCES"
SET INPUT SOURCE LOCALES($locales)       // Roman only
ARRAY TEXT($locales;0)
SET INPUT SOURCE LOCALES($locales)       // no restriction

GET INPUT SOURCE LOCALES($locales)       // 0 elements = no restriction
```
