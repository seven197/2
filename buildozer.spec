[app]

# (str) Title of your application
title = Roguelike Survival

# (str) Package name
package.name = roguelikesurvival

# (str) Package domain (needed for android/ios packaging)
package.domain = org.roguegame

# (str) Source code where the main.py is located
source.dir = .

# (list) Source files to include (let empty to include all files)
source.include_exts = py,png,jpg,kv,atlas

# (list) Source files to ignore
source.ignore_exts = pyc,pyo

# (list) Application requirements
requirements = python3,kivy

# (str) Supported orientation
orientation = landscape

# (bool) Indicate whether the application should be fullscreen or not
fullscreen = 1

# (int) Target Android API
android.api = 33

# (int) Minimum API your APK will support
android.minapi = 21

# (list) The Android archs to build for
android.archs = arm64-v8a, armeabi-v7a

# (str) android build mode (debug or release)
android.build_mode = debug

# (list) Permissions - 我们只需要基本权限
android.permissions = INTERNET

# (str) Android logcat filters
android.logcat_filters = *:S python:D

# (bool) Copy library instead of making a libpython.so symlink
android.copy_libs = 1