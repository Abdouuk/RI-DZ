[app]

# اسم التطبيق وحزمة الملف
title = RI
package.name = ri
package.domain = org.ri.downloader

# مسار ملفات المشروع وأيقونة التطبيق الخارجية
source.dir = .
source.include_exts = py,png,jpg,jpeg,webp,gif,mp4,mkv,webm,mov,kv,atlas,json,md,txt,ttf
icon.filename = %(source.dir)s/icon.jpg

# شاشة البداية: الأيقونة على خلفية داكنة بدل شاشة Loading الافتراضية
presplash.filename = %(source.dir)s/icon.jpg
android.presplash_color = #0b0c1a

# إصدار التطبيق
version = 0.3.0

# المكتبات المطلوبة داخل التطبيق
requirements = python3,kivy,requests,certifi,urllib3,idna,charset-normalizer,yt-dlp,arabic-reshaper,python-bidi

# توجيه الشاشة وصلاحيات أندرويد
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,READ_MEDIA_IMAGES,READ_MEDIA_VIDEO
android.api = 34
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True

# إصدار python-for-android المجرَّب في البناء الناجح
p4a.branch = v2024.01.21

# مسار Android SDK الموجود على GitHub Actions
android.sdk_path = /usr/local/lib/android/sdk

[buildozer]

log_level = 2
warn_on_root = 1