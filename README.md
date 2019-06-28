# 4d-plugin-text-input-context
Better way to control text input source from 4D

### Platform

| carbon | cocoa | win32 | win64 |
|:------:|:-----:|:---------:|:---------:|
||<img src="https://cloud.githubusercontent.com/assets/1725068/22371562/1b091f0a-e4db-11e6-8458-8653954a7cce.png" width="24" height="24" /> | | 

### Version

<img src="https://user-images.githubusercontent.com/1725068/41266195-ddf767b2-6e30-11e8-9d6b-2adf6a9f57a5.png" width="32" height="32" />

### Syntax

[miyako.github.io](https://miyako.github.io/2019/06/27/4d-plugin-text-input-context.html)

### Discussion

The previous version [4d-plugin-text-input-service](https://github.com/miyako/4d-plugin-text-input-service) was directly calling Text Input Service APIs (part of carbon framework, but 64-bit compatible). Incidentally, it was necessary to call them via ``PA_RunInMainProcess`` since v16 to avoid a crash.  

This version calls Text Input Context API, which seems to be more compatible with cocoa apps. It also seems no longer necessary to use ``PA_RunInMainProcess``, so the plugin is thread safe again (``PA_RunInMainProcess`` in not thread safe). It can also return objects and collections (again, ``PA_RunInMainProcess`` is incompatible). Thanks to the improvements made to the SDK, plugins can receive array parameters in thread safe mode.
