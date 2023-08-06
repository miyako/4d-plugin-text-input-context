# 4d-plugin-text-input-context
Better way to control text input source from 4D

![version](https://img.shields.io/badge/version-17%2B-3E8B93)
![platform](https://img.shields.io/static/v1?label=platform&message=mac-intel%20|%20mac-arm&color=blue)
[![license](https://img.shields.io/github/license/miyako/4d-plugin-text-input-context)](LICENSE)
![downloads](https://img.shields.io/github/downloads/miyako/4d-plugin-text-input-context/total)
![deprecated](https://img.shields.io/badge/-deprecated-inactive)

### Syntax

[miyako.github.io](https://miyako.github.io/2019/06/27/4d-plugin-text-input-context.html)

### Discussion

The previous version [4d-plugin-text-input-service](https://github.com/miyako/4d-plugin-text-input-service) was directly calling Text Input Service APIs (part of carbon framework, but 64-bit compatible). Incidentally, it was necessary to call them via ``PA_RunInMainProcess`` since v16 to avoid a crash.  

This version calls Text Input Context API, which seems to be more compatible with cocoa apps. It also seems no longer necessary to use ``PA_RunInMainProcess``, so the plugin is thread safe (``PA_RunInMainProcess`` is not thread safe). It can also return objects and collections (again, ``PA_RunInMainProcess`` is incompatible). Also, thanks to the improvements made to the SDK in v17, plugins can receive array parameters in thread safe mode.
