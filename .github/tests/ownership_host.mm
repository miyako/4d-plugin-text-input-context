// Boundary model adapted from tab-ui 0783b28c28192645672aec5884f83bbf32a29b69.
#include "4DPlugin-Text-Input-Context.h"
#include "C_LONGINT.h"
#include "PrivateTypes.h"
#include "EntryPoints.h"
#include <codecvt>
#include <cstring>
#include <locale>
#include <type_traits>

static std::map<PA_Unichar*, size_t> strings;
static std::map<PA_Picture, int> pictures;
static std::map<PA_Handle, size_t> handles;
struct Reference {
    std::map<CUTF16String, PA_Variable> properties;
    std::vector<PA_Variable> elements;
    int owners = 1;
    bool collection;
};
static std::map<void*, Reference*> refs;
static bool nullEmpty, failHandle, failResize, missing, inMain;
static std::string kind;
static CUTF16String expected;
static NSString *fixture;
static OwnershipContext *context;
static NSString *selected;
static NSArray *locales;
static int callbacks, contextCalls, imageOwners, urlOwners;
NSString *OwnershipRoman = @"synthetic-roman";

static void check(bool valid, const char* message)
{
    if (!valid) { std::cerr << message << "\n"; std::exit(1); }
}
static CUTF16String utf16(const char* text)
{
    std::wstring_convert<std::codecvt_utf8_utf16<char16_t>, char16_t> codec;
    auto u = codec.from_bytes(text);
    return CUTF16String(reinterpret_cast<const PA_Unichar*>(u.data()), u.size());
}
static PA_Unistring makeString(const PA_Unichar* text)
{
    size_t units = 0;
    while (text && text[units]) ++units;
    PA_Unistring value = {};
    if (units || !nullEmpty) {
        value.fString = new PA_Unichar[units + 1];
        if (units) std::memcpy(value.fString, text, units * sizeof(PA_Unichar));
        value.fString[units] = 0;
        value.fLength = static_cast<PA_long32>(units);
        strings[value.fString] = units;
    }
    return value;
}
static void disposeString(PA_Unistring value)
{
    if (!value.fString) { check(!value.fLength, "null nonempty string"); return; }
    check(strings.count(value.fString), "duplicate/unowned string disposal");
    check(strings.at(value.fString) == static_cast<size_t>(value.fLength), "allocation length");
    strings.erase(value.fString);
    delete[] value.fString;
}
static void textEquals(PA_Unistring value, const CUTF16String& wanted)
{
    check(value.fLength == static_cast<PA_long32>(wanted.size()), "exact UTF16 unit length");
    check(value.fString || wanted.empty(), "missing string");
    if (value.fString) {
        check(strings.count(value.fString), "read after release");
        check(value.fString[value.fLength] == 0, "terminator boundary");
        check(CUTF16String(value.fString, value.fLength) == wanted, "exact text");
    }
}
static PA_Picture makePicture()
{
    PA_Picture p = new unsigned char(42);
    pictures[p] = 1;
    return p;
}
static void clear(PA_Variable*);
static Reference* makeRef(bool collection)
{
    auto r = new Reference;
    r->collection = collection;
    refs[r] = r;
    return r;
}
static void releaseRef(void* p)
{
    if (!p) return;
    check(refs.count(p), "release dead reference");
    auto r = refs.at(p);
    check(r->owners > 0, "invalid reference balance");
    if (--r->owners) return;
    for (auto& pair : r->properties) clear(&pair.second);
    for (auto& v : r->elements) clear(&v);
    refs.erase(p);
    delete r;
}
static PA_Variable clone(PA_Variable v)
{
    if (v.fType == eVK_Unistring) v.uValue.fString = makeString(v.uValue.fString.fString);
    else if (v.fType == eVK_Picture) {
        check(pictures.count(v.uValue.fPicture), "copy dead picture");
        ++pictures[v.uValue.fPicture];
    } else if (v.fType == eVK_Object || v.fType == eVK_Collection) {
        void* p = v.fType == eVK_Object ? v.uValue.fObject : v.uValue.fCollection;
        if (p) { check(refs.count(p), "copy dead reference"); ++refs.at(p)->owners; }
    }
    return v;
}
static void clear(PA_Variable* v)
{
    switch (v->fType) {
    case eVK_Unistring: disposeString(v->uValue.fString); break;
    case eVK_Picture:
        if (v->uValue.fPicture) {
            auto p = v->uValue.fPicture;
            check(pictures.count(p), "release dead picture");
            if (--pictures[p] == 0) { pictures.erase(p); delete static_cast<unsigned char*>(p); }
        }
        break;
    case eVK_Object: releaseRef(v->uValue.fObject); break;
    case eVK_Collection: releaseRef(v->uValue.fCollection); break;
    case eVK_ArrayUnicode: {
        auto h = v->uValue.fArray.fData;
        check(handles.count(h), "clear dead array");
        auto values = reinterpret_cast<PA_Unistring*>(*h);
        for (PA_long32 i = 0; i <= v->uValue.fArray.fNbElements; ++i) disposeString(values[i]);
        std::free(*h); delete h; handles.erase(h);
        break;
    }
    case eVK_Undefined: case static_cast<char>(eVK_Null):
    case eVK_Boolean: case eVK_Real: case eVK_Longint: break;
    default: check(false, "clear unspecified failed/raw-kind0 return");
    }
    v->fType = eVK_Undefined;
    v->fFiller = 0;
}
static PA_Variable resultValue()
{
    PA_Variable v = PA_CreateVariable(eVK_Undefined);
    if (kind == "string") {
        auto s = makeString(expected.c_str()); PA_SetStringVariable(&v, &s);
    } else if (kind == "picture") PA_SetPictureVariable(&v, makePicture());
    else if (kind == "object") PA_SetObjectVariable(&v, makeRef(false));
    else if (kind == "collection") PA_SetCollectionVariable(&v, makeRef(true));
    else if (kind == "boolean") PA_SetBooleanVariable(&v, true);
    else if (kind == "real") PA_SetRealVariable(&v, 3.25);
    else check(false, "unknown result kind");
    return v;
}
static void failedResult(PA_Variable* v)
{
    std::memset(v, kind == "error-poison" ? 0xa5 : 0, sizeof(*v));
}
static void host(short selector, EngineBlock* eb)
{
    switch (selector) {
    case EX_CREATE_UNISTRING:
        eb->fUniString1 = makeString(reinterpret_cast<PA_Unichar*>(eb->fHandle)); break;
    case EX_DISPOSE_UNISTRING: disposeString(eb->fUniString1); break;
    case EX_SET_UNISTRING: {
        auto replacement = makeString(reinterpret_cast<PA_Unichar*>(eb->fHandle));
        disposeString(eb->fUniString1); eb->fUniString1 = replacement; break;
    }
    case EX_VARIABLE_TO_STRING: {
        auto v = reinterpret_cast<PA_Variable*>(eb->fHandle);
        check(v->fType == eVK_Unistring, "reading failed/non-string variable");
        textEquals(v->uValue.fString, expected);
        eb->fUniString1 = v->uValue.fString; break;
    }
    case EX_CREATE_PICTURE: eb->fPicture = makePicture(); break;
    case EX_CLEAR_VARIABLE: clear(static_cast<PA_Variable*>(eb->fPtr1)); break;
    case EX_RUN_IN_MAIN_PROCESS:
        check(!inMain, "nested main callback");
        inMain = true; ++callbacks;
        reinterpret_cast<PA_RunInMainProcessProcPtr>(eb->fPtr1)(eb->fPtr2);
        inMain = false;
        break;
    case EX_GET_INFORMATION: eb->fParam2 = 0x00001630; break;
    case EX_SET_OBJ_VALUE: {
        check(refs.count(eb->fPtr1), "set dead object");
        auto r = refs.at(eb->fPtr1);
        auto value = clone(*static_cast<PA_Variable*>(eb->fPtr2));
        if (eb->fShort == eVK_Collection) {
            check(r->collection && eb->fLongint == static_cast<long>(r->elements.size()), "collection append");
            r->elements.push_back(value);
        } else {
            auto key = CUTF16String(eb->fUniString1.fString, eb->fUniString1.fLength);
            auto it = r->properties.find(key);
            if (it != r->properties.end()) clear(&it->second);
            r->properties[key] = value;
        }
        break;
    }
    case EX_GET_OBJ_VALUE: {
        check(refs.count(eb->fPtr1), "get dead object");
        auto v = static_cast<PA_Variable*>(eb->fPtr2);
        if (eb->fShort == eVK_Collection && eb->fLongint == -1) {
            PA_SetLongintVariable(v, static_cast<PA_long32>(refs.at(eb->fPtr1)->elements.size()));
        } else if (kind.find("error-") == 0) {
            failedResult(v); eb->fError = eER_IncompatibleTypes;
        } else *v = resultValue();
        break;
    }
    case EX_HANDLE_MANAGER: {
        auto h = eb->fHandle;
        switch (eb->fParam1) {
        case 1:
            if (failHandle) { eb->fHandle = nullptr; eb->fError = eER_IncompatibleTypes; break; }
            h = new char*;
            *h = static_cast<char*>(std::calloc(1, std::max<sLONG_PTR>(1, eb->fParam2)));
            check(*h, "test handle allocation failed");
            handles[h] = eb->fParam2; eb->fHandle = h; break;
        case 2:
            check(handles.count(h), "dispose dead handle");
            std::free(*h); delete h; handles.erase(h); break;
        case 3: {
            check(handles.count(h), "resize dead handle");
            if (failResize) { eb->fError = eER_IncompatibleTypes; break; }
            auto data = static_cast<char*>(std::realloc(*h, std::max<sLONG_PTR>(1, eb->fParam2)));
            check(data, "test resize allocation failed");
            *h = data; handles[h] = eb->fParam2; break;
        }
        case 4: check(handles.count(h), "size dead handle"); eb->fParam2 = handles[h]; break;
        case 5: check(handles.count(h), "lock dead handle"); eb->fParam3 = reinterpret_cast<sLONG_PTR>(*h); break;
        case 6: check(handles.count(h), "unlock dead handle"); break;
        default: check(false, "unexpected handle operation");
        }
        break;
    }
    case EX_EXECUTE_COMMAND_BY_ID: {
        auto args = static_cast<PA_Variable**>(eb->fPtr1);
        auto v = static_cast<PA_Variable*>(eb->fPtr2);
        check(v->fType == eVK_Undefined, "command result initialization");
        if (eb->fParam1 == 1471) PA_SetObjectVariable(v, makeRef(false));
        else if (eb->fParam1 == 1472) PA_SetCollectionVariable(v, makeRef(true));
        else if (eb->fParam1 == 1231) {
            check(refs.count(args[0]->uValue.fObject), "existence on dead object");
            textEquals(args[1]->uValue.fString, utf16("key"));
            PA_SetBooleanVariable(v, !missing);
        } else if (eb->fParam1 == 1225) {
            if (kind == "error-copy") {
                failedResult(v); eb->fError = eER_IncompatibleTypes;
            } else if (kind.find("copy-") == 0) {
                auto saved = kind;
                kind = kind.substr(5);
                *v = resultValue();
                kind = saved;
            } else {
                check(refs.count(args[0]->uValue.fObject), "copy dead object");
                PA_SetObjectVariable(v, makeRef(false));
                if (kind == "error-handle") failHandle = true;
            }
        } else if (eb->fParam1 == 1217) {
            check(refs.count(args[0]->uValue.fObject), "stringify dead argument");
            if (kind.find("error-") == 0) {
                failedResult(v); eb->fError = eER_IncompatibleTypes;
            } else *v = resultValue();
        } else check(false, "unexpected command");
        break;
    }
    default: std::cerr << "unexpected engine selector " << selector << "\n"; std::exit(1);
    }
}

@implementation OwnershipContext
+ (id)currentInputContext
{
    check(inMain, "context outside main callback"); ++contextCalls;
    return kind == "nil-context" ? nil : context;
}
+ (NSString *)localizedNameForInputSource:(NSString *)source
{
    check(inMain && [source isEqualToString:fixture], "unexpected localized name");
    return kind == "no-metadata" ? nil : fixture;
}
- (NSArray *)keyboardInputSources { check(inMain, "sources outside callback"); return @[fixture]; }
- (NSString *)selectedKeyboardInputSource { check(inMain, "selection outside callback"); return selected; }
- (void)setSelectedKeyboardInputSource:(NSString *)s
{ check(inMain, "selection setter outside callback"); [selected release]; selected = [s copy]; }
- (NSArray *)allowedInputSourceLocales { check(inMain, "locales outside callback"); return locales; }
- (void)setAllowedInputSourceLocales:(NSArray *)s
{ check(inMain, "locale setter outside callback"); [locales release]; locales = [s copy]; }
@end
@implementation OwnershipURL
- (id)initWithString:(NSString *)text
{ self = [super init]; if (self) ++urlOwners; return self; }
- (void)dealloc { --urlOwners; [super dealloc]; }
- (OwnershipURL *)URLByDeletingPathExtension { check(inMain, "URL outside callback"); return self; }
- (OwnershipURL *)URLByAppendingPathExtension:(NSString *)extension
{ check(inMain && [extension isEqualToString:@"tiff"], "unexpected URL extension"); return self; }
- (NSString *)absoluteString { check(false, "unexpected path operation"); return nil; }
@end
@implementation OwnershipImage
- (id)initWithContentsOfURL:(OwnershipURL *)url
{ check(inMain, "image outside callback"); self = [super init]; if (self) ++imageOwners; return self; }
- (id)initWithIconRef:(IconRef)icon
{ check(inMain, "icon outside callback"); self = [super init]; if (self) ++imageOwners; return self; }
- (void)dealloc { --imageOwners; [super dealloc]; }
- (NSSize)size { check(inMain, "image size outside callback"); return NSMakeSize(1, 1); }
- (CGImageRef)CGImageForProposedRect:(NSRect *)r context:(id)c hints:(id)h
{ check(inMain && !c && !h, "unexpected image conversion"); return reinterpret_cast<CGImageRef>(1); }
@end
TISInputSourceRef OwnershipInputSource()
{
    check(inMain, "TIS outside callback");
    return reinterpret_cast<TISInputSourceRef>(const_cast<void*>(
        static_cast<const void*>(CFStringCreateCopy(nullptr, CFSTR("fixture")))));
}
void *OwnershipProperty(TISInputSourceRef source, CFStringRef key)
{
    check(inMain && source, "TIS property outside callback");
    if (kind == "no-metadata") return nullptr;
    if (key == kTISPropertyInputSourceCategory || key == kTISPropertyInputSourceType)
        return fixture;
    if (key == kTISPropertyInputSourceLanguages) return locales;
    if (key == kTISPropertyIconImageURL) {
        if (kind == "icon-ref") return nullptr;
        return [[[OwnershipURL alloc] initWithString:@"synthetic"] autorelease];
    }
    if (key == kTISPropertyIconRef) return reinterpret_cast<void*>(1);
    check(false, "unexpected TIS property"); return nullptr;
}
CFURLRef OwnershipCreateURL(CFAllocatorRef, CFStringRef, CFURLPathStyle, Boolean)
{ check(false, "unexpected path creation"); return nullptr; }
CFStringRef OwnershipCopyPath(CFURLRef, CFURLPathStyle)
{ check(false, "unexpected path copy"); return nullptr; }
CGImageDestinationRef OwnershipDestination(CFMutableDataRef data, CFStringRef type, size_t count, CFDictionaryRef options)
{
    check(inMain && count == 1 && !options && CFEqual(type, CFSTR("public.tiff")), "image destination");
    return reinterpret_cast<CGImageDestinationRef>(const_cast<void*>(CFRetain(data)));
}
void OwnershipAddImage(CGImageDestinationRef d, CGImageRef image, CFDictionaryRef options)
{
    check(inMain && image == reinterpret_cast<CGImageRef>(1) && !options, "add image");
    const UInt8 bytes[] = {1, 2, 3};
    CFDataAppendBytes(reinterpret_cast<CFMutableDataRef>(d), bytes, sizeof(bytes));
}
bool OwnershipFinalize(CGImageDestinationRef)
{ check(inMain, "image finalize outside callback"); return kind != "image-failure"; }
void OwnershipScale(CGContextRef, CGFloat, CGFloat) { check(false, "unexpected drawing"); }
void OwnershipTranslate(CGContextRef, CGFloat, CGFloat) { check(false, "unexpected drawing"); }

static void arrayCase()
{
    auto ar = PA_CreateVariable(eVK_ArrayUnicode);
    PA_ResizeArray(&ar, 3);
    for (int repeat = 0; repeat < 20; ++repeat) {
        for (int i = 0; i <= 3; ++i) {
            auto owned = makeString(expected.c_str());
            PA_SetStringInArray(ar, i, &owned);
            textEquals(PA_GetStringInArray(ar, i), expected);
        }
        auto borrowed = PA_GetStringInArray(ar, 1);
        auto copied = PA_CreateUnistring(borrowed.fString);
        PA_SetStringInArray(ar, 1, &copied);
        for (int i = 0; i < 10; ++i) {
            auto churn = makeString(expected.c_str()); PA_DisposeUnistring(&churn);
        }
        textEquals(PA_GetStringInArray(ar, 1), expected);
    }
    PA_ResizeArray(&ar, 1);
    auto owned = makeString(expected.c_str());
    auto wrong = PA_CreateVariable(eVK_Longint);
    PA_SetStringInArray(wrong, 0, &owned);
    PA_SetStringInArray(ar, -1, &owned);
    PA_SetStringInArray(ar, 2, &owned);
    auto noData = ar; noData.uValue.fArray.fData = nullptr;
    PA_SetStringInArray(noData, 0, &owned);
    PA_SetStringInArray(ar, 0, nullptr);
    textEquals(owned, expected); PA_DisposeUnistring(&owned);
    PA_ClearVariable(&ar);
}
static void wrapperCase(const std::string& name)
{
#ifdef OWNERSHIP_BASELINE_COPY
    if (name == "copy-array") {
        ARRAY_TEXT a; a.appendUTF16String(expected.c_str());
        { ARRAY_TEXT b = a; check(b.getSize() == 1, "copy size"); }
        check(a.getSize() == 1, "original after copy destruction");
    } else if (name == "assign-array") {
        ARRAY_TEXT a, b;
        a.appendUTF16String(expected.c_str());
        b = a;
    } else
#endif
    if (name == "copy-traits") {
        check(!std::is_copy_constructible<ARRAY_TEXT>::value &&
              !std::is_copy_assignable<ARRAY_TEXT>::value, "ARRAY_TEXT must not shallow copy");
        check(!std::is_copy_constructible<C_TEXT>::value &&
              !std::is_copy_assignable<C_TEXT>::value, "C_TEXT noncopy prior art");
    } else {
        C_TEXT text; text.setUTF16String(expected.c_str(), expected.size());
        CUTF16String copy; text.copyUTF16String(&copy);
        check(copy == expected, "scalar independent text copy");
        CUTF8String bytes;
        text.copyUTF8String(&bytes);
        C_TEXT converted; converted.setUTF8String(&bytes);
        converted.copyUTF16String(&copy);
        check(copy == expected, "scalar UTF8/UTF16 units and content");
        ARRAY_TEXT convertedArray; convertedArray.appendUTF8String(&bytes);
        convertedArray.copyUTF16StringAtIndex(&copy, 0);
        check(copy == expected, "array UTF8/UTF16 units and content");
        ARRAY_TEXT a; a.appendUTF16String(expected.c_str());
        auto ar = PA_CreateVariable(eVK_Undefined);
        void* args[] = {&ar};
        a.toParamAtIndex(reinterpret_cast<PackagePtr>(args), 1);
        ARRAY_TEXT b; b.fromParamAtIndex(reinterpret_cast<PackagePtr>(args), 1);
        PA_ClearVariable(&ar);
        b.copyUTF16StringAtIndex(&copy, 0);
        check(copy == expected, "borrowed array copied before mutation");
        C_LONGINT n; n.setIntValue(42); PA_long32 number = 0;
        void* ints[] = {&number};
        n.toParamAtIndex(reinterpret_cast<PackagePtr>(ints), 1);
        check(number == 42, "integer wrapper");
    }
}
static void dispatchCase(int selector)
{
    callbacks = contextCalls = 0;
    context = [[OwnershipContext alloc] init];
    fixture = [[NSString alloc] initWithCharacters:expected.data() length:expected.size()];
    selected = [fixture copy];
    locales = [[NSArray alloc] initWithObjects:fixture, OwnershipRoman, nil];
    auto ar = PA_CreateVariable(eVK_ArrayUnicode);
    PA_ResizeArray(&ar, 1);
    auto s = makeString(expected.c_str()); PA_SetStringInArray(ar, 1, &s);
    auto scalar = makeString(expected.c_str()), output = makeString(nullptr);
    PA_Unistring* textResult = &output;
    void* args[] = {selector == 3 ? static_cast<void*>(&scalar) : static_cast<void*>(&ar)};
    void* referenceResult = nullptr;
    PluginBlock p = {}; p.fParameters = args;
    p.fResult = selector == 2 ? static_cast<void*>(&textResult) : &referenceResult;
    PluginMain(selector, &p);
    check(callbacks == 1 && contextCalls == 1, "actual selector callback counts");
    bool active = kind != "nil-context";
    if (selector == 1 || selector == 4) {
        check(ar.uValue.fArray.fNbElements == (active ? selector == 1 ? 1 : 2 : 0), "output array size");
        if (active) textEquals(PA_GetStringInArray(ar, 1), expected);
        if (active && selector == 4) textEquals(PA_GetStringInArray(ar, 2), utf16("ALL ROMAN INPUT SOURCES"));
    } else if (selector == 2) textEquals(output, active ? expected : CUTF16String());
    else if (selector == 3 && active) {
        check([selected isEqualToString:fixture] && [locales isEqualToArray:@[OwnershipRoman]], "source setter");
    } else if (selector == 5 && active) {
        check([locales count] == (expected.empty() ? 0 : 1), "locale setter");
    } else if (selector == 6) {
        auto r = refs.at(referenceResult);
        check(r->collection && r->elements.size() == (active ? 1 : 0), "sources collection");
        if (active) textEquals(refs.at(r->elements[0].uValue.fObject)->properties.at(utf16("id")).uValue.fString, expected);
        PA_DisposeCollection(referenceResult);
    } else if (selector == 7) {
        auto r = refs.at(referenceResult);
        check(!r->collection && r->properties.size() == (active ? kind == "no-metadata" ? 1 : kind == "image-failure" ? 5 : 6 : 0), "source object properties");
        if (active) {
            textEquals(r->properties.at(utf16("id")).uValue.fString, expected);
            if (kind != "no-metadata") {
                auto langs = refs.at(r->properties.at(utf16("languages")).uValue.fCollection);
                check(langs->elements.size() == 2, "language count");
                textEquals(langs->elements[0].uValue.fString, expected);
                textEquals(langs->elements[1].uValue.fString, utf16("synthetic-roman"));
            }
        }
        PA_DisposeObject(referenceResult);
    }
    PA_ClearVariable(&ar); PA_DisposeUnistring(&scalar); PA_DisposeUnistring(&output);
    [context release]; [fixture release]; [selected release]; [locales release];
    context = nil; fixture = selected = nil; locales = nil;
    PluginMain(0, nullptr); PluginMain(999, nullptr);
}
static void helperCase(const std::string& name, const char* raw)
{
    auto object = makeRef(false);
    if (name == "set-narrow") ob_set_s(object, "key", raw);
    else if (name == "set-wide") ob_set_s(object, L"key", raw);
    else if (name == "set-wchars") {
        std::wstring_convert<std::codecvt_utf8<wchar_t>> codec;
        auto wide = codec.from_bytes(raw); ob_set_a(object, L"key", wide.c_str());
    } else if (name == "set-utf16") ob_set_a(object, L"key", &expected);
    else if (name == "set-picture") {
        ob_set_p(object, L"key", makePicture());
        check(pictures.at(object->properties.at(utf16("key")).uValue.fPicture) == 1, "property retains transferred picture");
    } else if (name == "get-a") {
        CUTF8String value(reinterpret_cast<const uint8_t*>("unchanged"));
        check(ob_get_a(object, L"key", &value) == !missing, "existence boolean preserved");
        const char* wanted = kind == "string" && !missing ? raw : "unchanged";
        check(value == CUTF8String(reinterpret_cast<const uint8_t*>(wanted)), "getter output");
    } else if (name == "get-b") check(ob_get_b(object, L"key") == (kind == "boolean" && !missing), "boolean getter");
    else if (name == "get-n") check(ob_get_n(object, L"key") == (kind == "real" && !missing ? 3.25 : 0.0), "real getter");
    else if (name == "get-c") {
        auto c = ob_get_c(object, L"key");
        check((c != nullptr) == (kind == "collection" && !missing), "collection handoff");
        if (c) { check(refs.count(c), "premature collection release"); PA_DisposeCollection(c); }
    } else if (name == "get-o") {
        auto o = ob_get_o(object, L"key");
        check((o != nullptr) == (kind == "object" && !missing), "object handoff");
        if (o) { check(refs.count(o), "premature object release"); PA_DisposeObject(o); }
    } else if (name == "stringify") {
        CUTF8String value(reinterpret_cast<const uint8_t*>("unchanged"));
        if (kind == "error-first-handle") failHandle = true;
        ob_stringify(object, &value);
        const char* wanted = kind == "string" ? raw : "unchanged";
        check(value == CUTF8String(reinterpret_cast<const uint8_t*>(wanted)), "stringify output");
    } else if (name == "values") {
        ob_set_i(object, L"key", 42);
        check(object->properties.at(utf16("key")).uValue.fLongint == 42, "integer setter");
        ob_set_n(object, L"key", 3.25); ob_set_n(object, "key", 3.25);
        check(object->properties.at(utf16("key")).uValue.fReal == 3.25, "real setters");
        ob_set_b(object, L"key", true);
        check(object->properties.at(utf16("key")).uValue.fBoolean, "boolean setter");
        ob_set_0(object, L"key"); ob_set_0(object, "key");
        check(object->properties.at(utf16("key")).fType == static_cast<char>(eVK_Null), "null setters");
        auto child = makeRef(false); ob_set_o(object, L"key", child);
        check(refs.at(child)->owners == 1, "wide object transfer");
        auto other = makeRef(false); ob_set_o(object, "key", other);
        check(refs.at(other)->owners == 1, "narrow object transfer");
        auto collection = makeRef(true); ob_set_c(object, L"key", collection);
        check(refs.at(collection)->owners == 1, "collection transfer");
        check(ob_is_defined(object, L"key"), "defined property");
    } else check(false, "unknown helper");
    if (name.find("set-") == 0 && name != "set-picture")
        textEquals(object->properties.at(utf16("key")).uValue.fString, expected);
    PA_DisposeObject(object);
}
int main(int argc, char** argv)
{
    @autoreleasepool {
        check(argc == 5, "arguments");
        gCall4D = host;
        const std::string name = argv[1];
        expected = utf16(argv[2]); nullEmpty = std::string(argv[3]) == "null"; kind = argv[4];
        if (name == "array") arrayCase();
        else if (name.find("dispatch-") == 0) dispatchCase(std::stoi(name.substr(9)));
        else if (name == "wrappers" || name == "copy-traits") wrapperCase(name);
#ifdef OWNERSHIP_BASELINE_COPY
        else if (name == "copy-array" || name == "assign-array") wrapperCase(name);
#endif
        else if (name == "missing") {
            missing = true;
            for (const char* getter : {"get-a", "get-b", "get-n", "get-c", "get-o"}) helperCase(getter, argv[2]);
        } else if (name == "null-controls") {
            CUTF8String value(reinterpret_cast<const uint8_t*>("unchanged"));
            check(!ob_get_a(nullptr, L"key", &value), "null string getter");
            check(!ob_get_b(nullptr, L"key") && ob_get_n(nullptr, L"key") == 0.0 &&
                  !ob_get_c(nullptr, L"key") && !ob_get_o(nullptr, L"key") &&
                  !ob_is_defined(nullptr, L"key"), "null getters");
            ob_set_s(nullptr, "key", "text"); ob_set_s(nullptr, L"key", "text");
            ob_set_a(nullptr, L"key", L"text"); ob_set_a(nullptr, L"key", &expected);
            ob_set_p(nullptr, L"key", nullptr); ob_set_o(nullptr, L"key", nullptr);
            ob_set_o(nullptr, "key", nullptr); ob_set_c(nullptr, L"key", nullptr);
            ob_set_s(nullptr, L"key", nullptr); ob_set_a(nullptr, L"key", static_cast<const wchar_t*>(nullptr));
            ob_stringify(nullptr, &value);
            check(value == CUTF8String(reinterpret_cast<const uint8_t*>("unchanged")), "null output");
        } else if (name == "sdk-failures") {
            failHandle = true; auto h = PA_NewHandle(8);
            check(!h && PA_GetLastError() != eER_NoErr, "handle failure predicate");
            failHandle = false; h = PA_NewHandle(8); failResize = true;
            check(!PA_SetHandleSize(h, 16) && PA_GetLastError() != eER_NoErr, "resize failure predicate");
            check(handles.at(h) == 8, "model preserved capacity");
            failResize = false; PA_DisposeHandle(h);
        } else helperCase(name, argv[2]);
        check(strings.empty(), "unreleased string owner");
        check(pictures.empty(), "unreleased picture owner");
        check(handles.empty(), "unreleased handle owner");
        check(refs.empty(), "unreleased object/collection owner");
        check(!imageOwners && !urlOwners, "unreleased synthetic platform owner");
        std::cout << "strings=0 pictures=0 handles=0 objects=0 collections=0\n";
    }
    check(!imageOwners && !urlOwners, "platform autorelease balance");
}
