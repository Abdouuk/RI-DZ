[app]

# اسم التطبيق وحزمة الملف
title = RI
package.name = ri
package.domain = org.ri.downloader

# مسار ملفات المشروع وأيقونة التطبيق الخارجية
source.dir = .
source.include_exts = py,png,jpg,jpeg,webp,gif,mp4,mkv,webm,mov,kv,atlas,json,md,txt
icon.filename = %(source.dir)s/icon.jpg

# إصدار التطبيق
version = 0.2.0

# المكتبات المطلوبة داخل التطبيق
requirements = python3,kivy,requests,certifi,urllib3,idna,charset-normalizer,yt-dlp

# توجيه الشاشة وصلاحيات أندرويد
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,READ_MEDIA_IMAGES,READ_MEDIA_VIDEO
android.api = 33
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True

[buildozer]

log_level = 2
warn_on_root = 1
