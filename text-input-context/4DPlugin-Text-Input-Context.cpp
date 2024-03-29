/* --------------------------------------------------------------------------------
 #
 #	4DPlugin.cpp
 #	source generated by 4D Plugin Wizard
 #	Project : Text Input Context
 #	author : miyako
 #	2019/06/27
 #
 # --------------------------------------------------------------------------------*/

#include "4DPlugin-Text-Input-Context.h"

void PluginMain(PA_long32 selector, PA_PluginParameters params) {
    
	try
	{
		CommandDispatcherInMainProcess (selector, params);
	}
	catch(...)
	{

	}
}

void CommandDispatcherInMainProcess (PA_long32 selector, PA_PluginParameters params) {
    
    switch(selector)
    {
            // --- Text Input Context
                        
        case 1 :
            _o_INPUT_SOURCES_LIST(params);
            break;
            
        case 2 :
            _o_Get_input_source(params);
            break;
            
        case 3 :
            SET_INPUT_SOURCE(params);
            break;
            
        case 4 :
            GET_INPUT_SOURCE_LOCALES(params);
            break;
            
        case 5 :
            SET_INPUT_SOURCE_LOCALES(params);
            break;
            
        case 6 :
            INPUT_SOURCES_LIST(params);
            break;
            
        case 7 :
            Get_input_source(params);
            break;
    }
}

// ------------------------------ Text Input Context ------------------------------

static void main_o_INPUT_SOURCES_LIST(NSArray<NSString *> **keyboardInputSources) {
    
    NSTextInputContext *currentInputContext = [NSTextInputContext currentInputContext];
    
    if(currentInputContext)
    {
        *keyboardInputSources = currentInputContext.keyboardInputSources;
    }
}

void _o_INPUT_SOURCES_LIST(PA_PluginParameters params) {
    
    /* -[NSTextInputContext keyboardInputSources] must be used from main thread only */
    
    NSArray<NSString *> *keyboardInputSources = nil;
    
    PA_RunInMainProcess((PA_RunInMainProcessProcPtr)main_o_INPUT_SOURCES_LIST, &keyboardInputSources);
    
    PackagePtr pParams = (PackagePtr)params->fParameters;
    
    ARRAY_TEXT Param1;
    Param1.setSize(0);
        
    if(keyboardInputSources)
    {
        Param1.appendUTF16String(@"");

        for (NSUInteger i = 0; i < [keyboardInputSources count]; ++i)
        {
            NSString *keyboardInputSource = [keyboardInputSources objectAtIndex:i];
            Param1.appendUTF16String(keyboardInputSource);
        }
    }

    Param1.toParamAtIndex(pParams, 1);
}

static void main_INPUT_SOURCES_LIST(NSArray<NSString *> **keyboardInputSources) {
    
   NSTextInputContext *currentInputContext = [NSTextInputContext currentInputContext];

    if(currentInputContext)
    {
        *keyboardInputSources = currentInputContext.keyboardInputSources;
    }
}

void INPUT_SOURCES_LIST(PA_PluginParameters params) {
    
    PA_CollectionRef sources = PA_CreateCollection();
    
    NSArray<NSString *> *keyboardInputSources = nil;
    
    PA_RunInMainProcess((PA_RunInMainProcessProcPtr)main_INPUT_SOURCES_LIST, &keyboardInputSources);
    
    if(keyboardInputSources) {

        for (NSUInteger i = 0; i < [keyboardInputSources count]; ++i)
        {
            NSString *keyboardInputSource = [keyboardInputSources objectAtIndex:i];
            
            PA_ObjectRef source = PA_CreateObject();

            ob_set_s(source, L"id", [keyboardInputSource UTF8String]);
            ob_set_s(source, L"name", [[NSTextInputContext localizedNameForInputSource:keyboardInputSource] UTF8String]);

            PA_Variable vObj = PA_CreateVariable(eVK_Object);
            PA_SetObjectVariable(&vObj, source);
            PA_SetCollectionElement(sources, PA_GetCollectionLength(sources), vObj);
            PA_ClearVariable(&vObj);
        }
        
    }

    PA_ReturnCollection(params, sources);
}




static void main_SET_INPUT_SOURCE_LOCALES(NSMutableArray<NSString *> *allowedInputSourceLocales) {
    
    NSTextInputContext *currentInputContext = [NSTextInputContext currentInputContext];
    
    if(currentInputContext)
    {
        currentInputContext.allowedInputSourceLocales = allowedInputSourceLocales;
    }
    
}

void SET_INPUT_SOURCE_LOCALES(PA_PluginParameters params) {
    
    PackagePtr pParams = (PackagePtr)params->fParameters;
    
    ARRAY_TEXT Param1;

    Param1.fromParamAtIndex(pParams, 1);

    NSMutableArray<NSString *> *allowedInputSourceLocales = [[NSMutableArray<NSString *> alloc]initWithCapacity:Param1.getSize()];
    
    for(int i = 1; i < Param1.getSize(); ++i)
    {
        NSString *allowedInputSourceLocale = Param1.copyUTF16StringAtIndex(i);
        
        if([allowedInputSourceLocale isLike:@"ALL ROMAN INPUT SOURCES"])
        {
            [allowedInputSourceLocales addObject:NSAllRomanInputSourcesLocaleIdentifier];
        }else{
            if(![allowedInputSourceLocale isLike:@""])
            {
                [allowedInputSourceLocales addObject:allowedInputSourceLocale];
            }
        }
        
        [allowedInputSourceLocale release];
    }
    
    PA_RunInMainProcess((PA_RunInMainProcessProcPtr)main_SET_INPUT_SOURCE_LOCALES, allowedInputSourceLocales);
    
    [allowedInputSourceLocales release];
}

static void main_GET_INPUT_SOURCE_LOCALES(NSArray<NSString *> **allowedInputSourceLocales) {
    
   NSTextInputContext *currentInputContext = [NSTextInputContext currentInputContext];
    
    if(currentInputContext)
    {
        *allowedInputSourceLocales = currentInputContext.allowedInputSourceLocales;
    }
    
}

void GET_INPUT_SOURCE_LOCALES(PA_PluginParameters params) {
    
    PackagePtr pParams = (PackagePtr)params->fParameters;
    
    ARRAY_TEXT Param1;
    Param1.setSize(0);
    
    NSArray<NSString *> *allowedInputSourceLocales = nil;
    
    PA_RunInMainProcess((PA_RunInMainProcessProcPtr)main_GET_INPUT_SOURCE_LOCALES, &allowedInputSourceLocales);
    
    if(allowedInputSourceLocales) {

        Param1.appendUTF16String(@"");
            
        for (NSUInteger i = 0; i < [allowedInputSourceLocales count]; ++i)
        {
            NSString *allowedInputSourceLocale = [allowedInputSourceLocales objectAtIndex:i];
            
            if([allowedInputSourceLocale isLike:NSAllRomanInputSourcesLocaleIdentifier])
            {
                Param1.appendUTF16String(@"ALL ROMAN INPUT SOURCES");
            }else{
                Param1.appendUTF16String(allowedInputSourceLocale);
            }
        }
        
    }

    Param1.toParamAtIndex(pParams, 1);
}

static void main_Get_input_source(NSString **selectedKeyboardInputSource) {
    
    NSTextInputContext *currentInputContext = [NSTextInputContext currentInputContext];
    
    if(currentInputContext)
    {
        *selectedKeyboardInputSource = currentInputContext.selectedKeyboardInputSource;
    }
    
}

void Get_input_source(PA_PluginParameters params) {
    
    PA_ObjectRef returnValue = PA_CreateObject();
    
    NSString *selectedKeyboardInputSource = nil;
    
    PA_RunInMainProcess((PA_RunInMainProcessProcPtr)main_Get_input_source, &selectedKeyboardInputSource);
    
    if(selectedKeyboardInputSource)
    {
        /* these are obtained using cocoa API */
        
        ob_set_s(returnValue, L"id", [selectedKeyboardInputSource UTF8String]);
        ob_set_s(returnValue, L"name", [[NSTextInputContext localizedNameForInputSource:selectedKeyboardInputSource] UTF8String]);
        
        /* these are obtained using carbon API */
        
        TISInputSourceRef inputSource = TISCopyCurrentKeyboardInputSource();
        if(inputSource)
        {
            CFStringRef category = (CFStringRef)TISGetInputSourceProperty(inputSource, kTISPropertyInputSourceCategory);
            if(category)
            {
                ob_set_s(returnValue, L"category", [(__bridge NSString *)category UTF8String]);
            }
            CFStringRef type = (CFStringRef)TISGetInputSourceProperty(inputSource, kTISPropertyInputSourceType);
            if(type)
            {
                ob_set_s(returnValue, L"type", [(__bridge NSString *)type UTF8String]);
            }
            
            CFArrayRef languages = (CFArrayRef)TISGetInputSourceProperty(inputSource, kTISPropertyInputSourceLanguages);
            if(languages)
            {
                PA_CollectionRef colLanguages = PA_CreateCollection();
                
                for(CFIndex i =0; i < CFArrayGetCount(languages); ++i)
                {
                    CFStringRef language = (CFStringRef)CFArrayGetValueAtIndex(languages, i);
                    if(language)
                    {
                        NSString *__language = (__bridge NSString *)language;
                        NSUInteger len = [__language length];
                        size_t size = (len * sizeof(PA_Unichar)) + sizeof(PA_Unichar);
                        std::vector<uint8_t> buf(size);
                        PA_Unistring uStr;
                        
                        if([__language getCString:(char *)&buf[0] maxLength:size encoding:NSUnicodeStringEncoding])
                        {
                            uStr = PA_CreateUnistring((PA_Unichar *)&buf[0]);
                            PA_Variable vObj = PA_CreateVariable(eVK_Unistring);
                            PA_SetStringVariable(&vObj, &uStr);
                            PA_SetCollectionElement(colLanguages, PA_GetCollectionLength(colLanguages), vObj);
                            PA_ClearVariable(&vObj);
                        }
                    }
                }
                
                ob_set_c(returnValue, L"languages", colLanguages);
            }
            
            NSImage *icon;
            NSURL *url = (NSURL *)TISGetInputSourceProperty(inputSource, kTISPropertyIconImageURL);
            if(url)
            {
                icon = [[NSImage alloc]initWithContentsOfURL:url];
                if(!icon)
                {
                    //the extension is sometimes wrong; try again png -> tiff
                    url = [url.URLByDeletingPathExtension URLByAppendingPathExtension:@"tiff"];
                    icon = [[NSImage alloc]initWithContentsOfURL:url];
                }
                if(icon)
                {
                    //return picture without memory leak; avoid the use of - TIFFRepresentation
                    NSRect imageRect = NSMakeRect(0, 0, icon.size.width , icon.size.height);
                    CGImageRef image = [icon CGImageForProposedRect:(NSRect *)&imageRect context:NULL hints:NULL];
                    CFMutableDataRef data = CFDataCreateMutable(kCFAllocatorDefault, 0);
                    CGImageDestinationRef destination = CGImageDestinationCreateWithData(data, kUTTypeTIFF, 1, NULL);
                    CFMutableDictionaryRef properties = CFDictionaryCreateMutable(kCFAllocatorDefault, 0, NULL, NULL);
                    CGImageDestinationAddImage(destination, image, properties);
                    CGImageDestinationFinalize(destination);
                    PA_Picture picture = PA_CreatePicture((void *)CFDataGetBytePtr(data), (PA_long32)CFDataGetLength(data));
                    ob_set_p(returnValue, L"icon", picture);
                    CFRelease(destination);
                    CFRelease(properties);
                    CFRelease(data);
                    [icon release];
                }
            }
            else
            {
                IconRef iconRef = (IconRef)TISGetInputSourceProperty(inputSource, kTISPropertyIconRef);
                if(iconRef)
                {
                    NSImage *icon = [[NSImage alloc]initWithIconRef:iconRef];
                    //return picture without memory leak; avoid the use of - TIFFRepresentation
                    NSRect imageRect = NSMakeRect(0, 0, icon.size.width , icon.size.height);
                    CGImageRef image = [icon CGImageForProposedRect:(NSRect *)&imageRect context:NULL hints:NULL];
                    CFMutableDataRef data = CFDataCreateMutable(kCFAllocatorDefault, 0);
                    CGImageDestinationRef destination = CGImageDestinationCreateWithData(data, kUTTypeTIFF, 1, NULL);
                    CFMutableDictionaryRef properties = CFDictionaryCreateMutable(kCFAllocatorDefault, 0, NULL, NULL);
                    CGImageDestinationAddImage(destination, image, properties);
                    CGImageDestinationFinalize(destination);
                    PA_Picture picture = PA_CreatePicture((void *)CFDataGetBytePtr(data), (PA_long32)CFDataGetLength(data));
                    ob_set_p(returnValue, L"icon", picture);
                    CFRelease(destination);
                    CFRelease(properties);
                    CFRelease(data);
                    [icon release];
                }
            }
            
            CFRelease(inputSource);
        }
    }
    
    PA_ReturnObject(params, returnValue);
}


static void main_o_Get_input_source(NSString **selectedKeyboardInputSource) {
    
    NSTextInputContext *currentInputContext = [NSTextInputContext currentInputContext];
    
    if(currentInputContext)
    {
        *selectedKeyboardInputSource = currentInputContext.selectedKeyboardInputSource;
    }
    
}

void _o_Get_input_source(PA_PluginParameters params) {
    
    sLONG_PTR *pResult = (sLONG_PTR *)params->fResult;
    
    C_TEXT returnValue;
    
    NSString *selectedKeyboardInputSource = nil;
    
    PA_RunInMainProcess((PA_RunInMainProcessProcPtr)main_o_Get_input_source, &selectedKeyboardInputSource);
        
    if(selectedKeyboardInputSource)
    {
        returnValue.setUTF16String(selectedKeyboardInputSource);
    }
    
    returnValue.setReturn(pResult);
}

static void main_SET_INPUT_SOURCE(NSString *selectedKeyboardInputSource) {
    
    NSTextInputContext *currentInputContext = [NSTextInputContext currentInputContext];
    
    if(currentInputContext)
    {
        currentInputContext.selectedKeyboardInputSource = selectedKeyboardInputSource;

        currentInputContext.allowedInputSourceLocales = @[NSAllRomanInputSourcesLocaleIdentifier];
        
    }
    
}

void SET_INPUT_SOURCE(PA_PluginParameters params) {
    
    PackagePtr pParams = (PackagePtr)params->fParameters;
    
    C_TEXT Param1;
    
    Param1.fromParamAtIndex(pParams, 1);
    
    NSString *selectedKeyboardInputSource = Param1.copyUTF16String();
    
    PA_RunInMainProcess((PA_RunInMainProcessProcPtr)main_SET_INPUT_SOURCE, selectedKeyboardInputSource);
    
    [selectedKeyboardInputSource release];

}

/*
 
         
         CFArrayRef sources = TISCreateInputSourceList(NULL, FALSE);
         
         if(sources) {
             
             for(NSUInteger i = 0; i < CFArrayGetCount(sources); ++ i) {
                 
                 TISInputSourceRef source = (TISInputSourceRef)CFArrayGetValueAtIndex(sources, i);
                 NSString *inputSourceID = (NSString *)TISGetInputSourceProperty(source, kTISPropertyInputSourceID);
                 if(![inputSourceID isEqualToString:selectedKeyboardInputSource]) {
                     
     
                      use filter dictionary to check validity
                      https:github.com/harciga/text-input-source-selector/blob/master/textinputsource/main.c
                    
                     CFStringRef keys[] = { kTISPropertyInputSourceID };
                     CFStringRef values[] = { (CFStringRef)inputSourceID };
                     CFDictionaryRef dict = CFDictionaryCreate(kCFAllocatorDefault,
                                                               (const void **)keys,
                                                               (const void **)values,
                                                               1, NULL, NULL);
                     CFArrayRef array = TISCreateInputSourceList(dict, true);
                     CFRelease(dict);
                     if (array)
                     {
                         TISInputSourceRef tis = (TISInputSourceRef) CFArrayGetValueAtIndex(array, 0);
                        
                         if(TISGetInputSourceProperty(tis, kTISPropertyInputSourceIsSelectCapable)){
 //                            TISDeselectInputSource(tis);//removes from the menu!!!
 //                            TISDisableInputSource(tis);
                         }

                         CFRelease(array);
                         
                     }
                 }
             }
             CFRelease(sources);
         }
 */
