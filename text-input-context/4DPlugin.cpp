/* --------------------------------------------------------------------------------
 #
 #	4DPlugin.cpp
 #	source generated by 4D Plugin Wizard
 #	Project : Text Input Context
 #	author : miyako
 #	2019/06/27
 #
 # --------------------------------------------------------------------------------*/


#include "4DPluginAPI.h"
#include "4DPlugin.h"

void PluginMain(PA_long32 selector, PA_PluginParameters params) {
    
	try
	{
		CommandDispatcherInMainProcess (selector, params);
	}
	catch(...)
	{

	}
}

void CommandDispatcherInMainProcess (int32_t pProcNum, PA_PluginParameters params) {
    
    switch(pProcNum)
    {
        // --- Text Input Context
        
        case 1 :
        PA_RunInMainProcess((PA_RunInMainProcessProcPtr)INPUT_SOURCES_LIST, params);
        break;
        
        case 2 :
        PA_RunInMainProcess((PA_RunInMainProcessProcPtr)Get_input_source, params);
        break;
        
        case 3 :
        PA_RunInMainProcess((PA_RunInMainProcessProcPtr)SET_INPUT_SOURCE, params);
        break;
        
        case 4 :
        PA_RunInMainProcess((PA_RunInMainProcessProcPtr)GET_INPUT_SOURCE_LOCALES, params);
        break;
        
        case 5 :
        PA_RunInMainProcess((PA_RunInMainProcessProcPtr)SET_INPUT_SOURCE_LOCALES, params);
        break;
    }
}

void CommandDispatcher (PA_long32 pProcNum, sLONG_PTR *pResult, PackagePtr pParams) {
    
}

// ------------------------------ Text Input Context ------------------------------

void INPUT_SOURCES_LIST(PA_PluginParameters params) {
    
    PackagePtr pParams = (PackagePtr)params->fParameters;
    
    ARRAY_TEXT Param1;
    Param1.setSize(0);
    
    NSTextInputContext *currentInputContext = [NSTextInputContext currentInputContext];
    
    if(currentInputContext)
    {
        Param1.appendUTF16String(@"");
        NSArray<NSString *> *keyboardInputSources = currentInputContext.keyboardInputSources;

        for (NSUInteger i = 0; i < [keyboardInputSources count]; ++i)
        {
            NSString *keyboardInputSource = [keyboardInputSources objectAtIndex:i];
            Param1.appendUTF16String(keyboardInputSource);
        }
    }

    Param1.toParamAtIndex(pParams, 1);
}

void Get_input_source(PA_PluginParameters params) {
    
    sLONG_PTR *pResult = (sLONG_PTR *)params->fResult;
    
    C_TEXT returnValue;

    NSTextInputContext *currentInputContext = [NSTextInputContext currentInputContext];

    if(currentInputContext)
    {
        NSString *selectedKeyboardInputSource = currentInputContext.selectedKeyboardInputSource;
        if(selectedKeyboardInputSource)
        {
            returnValue.setUTF16String(selectedKeyboardInputSource);
        }
    }
    
    returnValue.setReturn(pResult);
}

void SET_INPUT_SOURCE(PA_PluginParameters params) {
    
    PackagePtr pParams = (PackagePtr)params->fParameters;
    
    C_TEXT Param1;
    
    Param1.fromParamAtIndex(pParams, 1);
    
    NSTextInputContext *currentInputContext = [NSTextInputContext currentInputContext];
    
    if(currentInputContext)
    {
        NSString *selectedKeyboardInputSource = Param1.copyUTF16String();
        
        currentInputContext.selectedKeyboardInputSource = selectedKeyboardInputSource;
        
        [selectedKeyboardInputSource release];

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
    
    NSTextInputContext *currentInputContext = [NSTextInputContext currentInputContext];
    
    if(currentInputContext)
    {
        currentInputContext.allowedInputSourceLocales = allowedInputSourceLocales;
    }
    
    [allowedInputSourceLocales release];
}

void GET_INPUT_SOURCE_LOCALES(PA_PluginParameters params) {
    
    PackagePtr pParams = (PackagePtr)params->fParameters;
    
    ARRAY_TEXT Param1;
    Param1.setSize(0);
    
    NSTextInputContext *currentInputContext = [NSTextInputContext currentInputContext];
    
    if(currentInputContext)
    {
        Param1.appendUTF16String(@"");
        NSArray<NSString *> *allowedInputSourceLocales = currentInputContext.allowedInputSourceLocales;
        
        
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

