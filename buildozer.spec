[app]

title = RI
package.name = ri
package.domain = org.ri.downloader

source.dir = .
source.include_exts = py,png,jpg,jpeg,webp,gif,mp4,mkv,webm,mov,kv,atlas,json,md,txt
icon.filename = %(source.dir)s/icon.jpg

version = 0.2.0

requirements = python3,kivy,requests,certifi,urllib3,idna,charset-normalizer,yt-dlp

# إصدار مستقر من python-for-android يبني Python 3.11
p4a.branch = v2024.01.21

orientation = portrait
fullscreen = 0
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,READ_MEDIA_IMAGES,READ_MEDIA_VIDEO
android.api = 33
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True

# استخدام Android SDK الجاهز في بيئة GitHub بدلاً من تحميل SDK فارغ
android.sdk_path = /usr/local/lib/android/sdk

[buildozer]

log_level = 2
warn_on_root = 1