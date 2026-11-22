import hashlib
import os
import re
from urllib.parse import urlparse

import requests
import yt_dlp

from lang import get_text

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# نوع التحميل: av = فيديو + صوت، v = فيديو بدون صوت، a = صوت فقط
# ملاحظة: بدون ffmpeg لا يمكن دمج أو تحويل الصيغ، لذلك نستخدم صيغاً جاهزة من المنصة.
FORMAT_SELECTORS = {
    "av": "best[ext=mp4][height<={h}]/best[height<={h}]/best",
    "v": "bestvideo[ext=mp4][height<={h}]/bestvideo[height<={h}]/bestvideo",
    "a": "bestaudio[ext=m4a]/bestaudio/best",
}
FILE_SUFFIX = {"av": "", "v": "-no-audio", "a": "-audio"}
MEDIA_EXTS = (".mp4", ".m4a", ".webm", ".mkv", ".mov", ".mp3", ".jpg", ".jpeg", ".png", ".webp")


class Cancelled(Exception):
    pass


class RIDownloaderEngine:
    def __init__(self, output_dir: str = "downloads", lang: str = "ar"):
        self.output_dir = output_dir
        self.lang = lang
        os.makedirs(self.output_dir, exist_ok=True)

    def set_language(self, lang: str) -> None:
        if lang in ("ar", "en"):
            self.lang = lang

    @staticmethod
    def detect_platform(url: str) -> str:
        domain = urlparse(url.lower()).netloc
        if "tiktok.com" in domain:
            return "tiktok"
        if "instagram.com" in domain:
            return "instagram"
        if "twitter.com" in domain or "x.com" in domain:
            return "twitter"
        if "youtube.com" in domain or "youtu.be" in domain:
            return "youtube"
        if "pinterest." in domain or "pin.it" in domain:
            return "pinterest"
        return "other"

    def download(self, url, kind="av", quality="720", progress_callback=None, cancel_event=None) -> dict:
        url = (url or "").strip()
        if not url:
            return {"ok": False, "error": get_text("empty_url", self.lang)}
        if kind not in FORMAT_SELECTORS:
            kind = "av"

        platform = self.detect_platform(url)
        result = self._download_with_ytdlp(url, platform, kind, quality, progress_callback, cancel_event)
        if result["ok"] or result.get("cancelled"):
            return result

        if platform == "pinterest" and kind == "av":
            return self._download_pinterest_fallback(url)
        return result

    def download_many(self, urls, kind="av", quality="720", progress_callback=None, cancel_event=None) -> list:
        results = []
        total = len(urls)
        for i, url in enumerate(urls):
            if cancel_event is not None and cancel_event.is_set():
                break

            def cb(pct, msg, idx=i):
                if progress_callback:
                    progress_callback(idx, total, pct, msg)

            results.append(self.download(url, kind, quality, cb, cancel_event))
        return results

    def _download_with_ytdlp(self, url, platform, kind, quality, progress_callback=None, cancel_event=None) -> dict:
        downloaded_file = None

        def hook(d):
            nonlocal downloaded_file
            if cancel_event is not None and cancel_event.is_set():
                raise Cancelled()
            if d.get("status") == "downloading" and progress_callback:
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes") or 0
                if total > 0:
                    pct = round((downloaded / total) * 100, 1)
                    progress_callback(pct, get_text("downloading", self.lang, progress=pct))
            elif d.get("status") == "finished":
                downloaded_file = d.get("filename")

        ydl_opts = {
            "outtmpl": os.path.join(self.output_dir, f"{platform}_%(id)s{FILE_SUFFIX[kind]}.%(ext)s"),
            "format": FORMAT_SELECTORS[kind].format(h=quality),
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [hook],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if not downloaded_file and info:
                    downloaded_file = ydl.prepare_filename(info)

            if downloaded_file and os.path.exists(downloaded_file):
                return {
                    "ok": True,
                    "platform": platform,
                    "file": downloaded_file,
                    "message": get_text("saved_to", self.lang, path=downloaded_file),
                }
            return {
                "ok": False,
                "platform": platform,
                "error": get_text("error_prefix", self.lang, error="file not saved"),
            }
        except Exception as e:
            if isinstance(e, Cancelled) or (cancel_event is not None and cancel_event.is_set()):
                return {"ok": False, "cancelled": True, "platform": platform,
                        "error": get_text("cancelled", self.lang)}
            return {
                "ok": False,
                "platform": platform,
                "error": get_text("error_prefix", self.lang, error=str(e)),
            }

    def _download_pinterest_fallback(self, url: str) -> dict:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
            resp.raise_for_status()
            media_url, ext = self._extract_pinterest_media(resp.text)
            if not media_url:
                return {
                    "ok": False,
                    "platform": "pinterest",
                    "error": get_text("error_prefix", self.lang, error="no media found"),
                }

            digest = hashlib.sha256(media_url.encode("utf-8")).hexdigest()[:12]
            filepath = os.path.join(self.output_dir, f"pinterest_{digest}.{ext}")

            with requests.get(media_url, headers=HEADERS, timeout=60, stream=True) as r:
                r.raise_for_status()
                with open(filepath, "wb") as f:
                    for chunk in r.iter_content(16384):
                        if chunk:
                            f.write(chunk)

            if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                return {
                    "ok": True,
                    "platform": "pinterest",
                    "file": filepath,
                    "message": get_text("saved_to", self.lang, path=filepath),
                }
            return {
                "ok": False,
                "platform": "pinterest",
                "error": get_text("error_prefix", self.lang, error="empty file"),
            }
        except Exception as e:
            return {
                "ok": False,
                "platform": "pinterest",
                "error": get_text("error_prefix", self.lang, error=str(e)),
            }

    @staticmethod
    def _extract_pinterest_media(html: str):
        for prop in ("og:video", "og:video:secure_url"):
            m = re.search(rf'<meta[^>]+property=["\']{prop}["\'][^>]+content=["\']([^"\']+)', html, re.I)
            if m:
                return m.group(1).replace("&amp;", "&"), "mp4"

        m_json = re.search(r'"contentUrl":"(https://v1\.pinimg\.com/[^"]+?\.mp4[^"]*)"', html)
        if m_json:
            return m_json.group(1).replace("\\u002F", "/").replace("\\/", "/"), "mp4"

        for prop in ("og:image", "twitter:image"):
            m = re.search(rf'<meta[^>]+property=["\']{prop}["\'][^>]+content=["\']([^"\']+)', html, re.I)
            if m:
                return m.group(1).replace("&amp;", "&"), "jpg"

        return None, None

    # ---------- المكتبة ----------
    def list_files(self) -> list:
        items = []
        try:
            names = os.listdir(self.output_dir)
        except OSError:
            return items
        for name in names:
            path = os.path.join(self.output_dir, name)
            if os.path.isfile(path) and name.lower().endswith(MEDIA_EXTS):
                st = os.stat(path)
                items.append({"name": name, "path": path, "size": st.st_size, "mtime": st.st_mtime})
        items.sort(key=lambda x: x["mtime"], reverse=True)
        return items

    def delete_file(self, path: str) -> bool:
        real = os.path.realpath(path)
        if os.path.dirname(real) != os.path.realpath(self.output_dir):
            return False
        try:
            os.remove(real)
            return True
        except OSError:
            return False
