#import <Cocoa/Cocoa.h>
#import <Carbon/Carbon.h>
#import <ImageIO/ImageIO.h>

// All context, keyboard, image and URL operations terminate at synthetic boundaries.
@interface OwnershipContext : NSObject
+ (id)currentInputContext;
+ (NSString *)localizedNameForInputSource:(NSString *)source;
@property(copy) NSString *selectedKeyboardInputSource;
@property(copy) NSArray *allowedInputSourceLocales;
@property(readonly) NSArray *keyboardInputSources;
@end
@interface OwnershipURL : NSObject
- (id)initWithString:(NSString *)text;
@property(readonly) OwnershipURL *URLByDeletingPathExtension;
- (OwnershipURL *)URLByAppendingPathExtension:(NSString *)extension;
- (NSString *)absoluteString;
@end
@interface OwnershipImage : NSObject
- (id)initWithContentsOfURL:(OwnershipURL *)url;
- (id)initWithIconRef:(IconRef)icon;
- (NSSize)size;
- (CGImageRef)CGImageForProposedRect:(NSRect *)rect context:(id)context hints:(id)hints;
@end
extern NSString *OwnershipRoman;
TISInputSourceRef OwnershipInputSource(void);
void *OwnershipProperty(TISInputSourceRef, CFStringRef);
CFURLRef OwnershipCreateURL(CFAllocatorRef, CFStringRef, CFURLPathStyle, Boolean);
CFStringRef OwnershipCopyPath(CFURLRef, CFURLPathStyle);
CGImageDestinationRef OwnershipDestination(CFMutableDataRef, CFStringRef, size_t, CFDictionaryRef);
void OwnershipAddImage(CGImageDestinationRef, CGImageRef, CFDictionaryRef);
bool OwnershipFinalize(CGImageDestinationRef);
void OwnershipScale(CGContextRef, CGFloat, CGFloat);
void OwnershipTranslate(CGContextRef, CGFloat, CGFloat);

#define NSTextInputContext OwnershipContext
#define NSURL OwnershipURL
#define NSImage OwnershipImage
#define NSAllRomanInputSourcesLocaleIdentifier OwnershipRoman
#define TISCopyCurrentKeyboardInputSource OwnershipInputSource
#define TISGetInputSourceProperty OwnershipProperty
#define CFURLCreateWithFileSystemPath OwnershipCreateURL
#define CFURLCopyFileSystemPath OwnershipCopyPath
#define CGImageDestinationCreateWithData OwnershipDestination
#define CGImageDestinationAddImage OwnershipAddImage
#define CGImageDestinationFinalize OwnershipFinalize
#define CGContextScaleCTM OwnershipScale
#define CGContextTranslateCTM OwnershipTranslate
