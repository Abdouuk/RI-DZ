import json
import os
import threading
from functools import partial

from kivy.app import App
from kivy.clock import Clock
from kivy.core.text import LabelBase
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

from arabic import shape
from lang import get_text
from ri_engine import RIDownloaderEngine

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# الاسم الافتراضي لخط Kivy هو Roboto، فنسجّل الخط العربي باسمه ليصبح خط كل النصوص
LabelBase.register(
    name="Roboto",
    fn_regular=os.path.join(BASE_DIR, "fonts", "Tajawal-Regular.ttf"),
    fn_bold=os.path.join(BASE_DIR, "fonts", "Tajawal-Bold.ttf"),
)

ACCENT = "#6d4cff"
BG_CHOICES = ["#0b0c1a", "#14122b", "#1e1b4b", "#f4f3fa", "#fff7ed", "#e6f7f1"]
FG_CHOICES = ["#f1f0ff", "#14122b", "#f5c451", "#67e8f9", "#f9a8d4", "#86efac"]
QUALITIES = ["360", "720", "1080"]
DEFAULTS = {"lang": "ar", "quality": "720", "bg": "#0b0c1a", "fg": "#f1f0ff"}


def rgba(hex_color, alpha=1.0):
    h = hex_color.lstrip("#")
    return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)] + [alpha]


def wrap(label):
    label.bind(width=lambda w, v: setattr(w, "text_size", (v, None)))
    return label


class Store:
    """يحفظ الإعدادات في ملف JSON داخل مجلد التطبيق."""

    def __init__(self, path):
        self.path = path
        self.data = dict(DEFAULTS)
        try:
            with open(path, encoding="utf-8") as f:
                self.data.update(json.load(f))
        except Exception:
            pass

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False)
        except Exception:
            pass


class HomeScreen(Screen):
    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app = app
        self.worker_running = False
        box = BoxLayout(orientation="vertical", padding=[dp(16), dp(12)], spacing=dp(10))

        # الجودة في أعلى الشاشة
        box.add_widget(wrap(Label(text=app.tx("quality"), size_hint_y=None, height=dp(26),
                                  bold=True, color=app.fg())))
        q_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        self.q_buttons = {}
        for q in QUALITIES:
            b = Button(text=f"{q}p", background_normal="")
            b.bind(on_release=partial(self.set_quality, q))
            self.q_buttons[q] = b
            q_row.add_widget(b)
        box.add_widget(q_row)
        self.refresh_quality()

        self.url = TextInput(
            hint_text=app.tx("url_hint"), multiline=True, size_hint_y=None, height=dp(150),
            foreground_color=app.fg(), cursor_color=app.fg(),
            hint_text_color=rgba(app.store.data["fg"], 0.5),
            background_color=rgba("#ffffff", 0.08),
        )
        box.add_widget(self.url)

        row = BoxLayout(size_hint_y=None, height=dp(54), spacing=dp(8))
        self.go_btn = Button(text=app.tx("download_btn"), bold=True, background_normal="",
                             background_color=rgba(ACCENT))
        self.go_btn.bind(on_release=self.open_options)
        self.cancel_btn = Button(text=app.tx("cancel_btn"), size_hint_x=None, width=dp(110),
                                 disabled=True, background_normal="",
                                 background_color=rgba("#ef4444"))
        self.cancel_btn.bind(on_release=self.cancel)
        row.add_widget(self.go_btn)
        row.add_widget(self.cancel_btn)
        box.add_widget(row)

        self.bar = ProgressBar(max=100, value=0, size_hint_y=None, height=dp(14))
        box.add_widget(self.bar)
        self.status = wrap(Label(text=app.tx("idle"), size_hint_y=None, height=dp(24), color=app.fg()))
        box.add_widget(self.status)
        self.result = wrap(Label(text="", size_hint_y=None, height=dp(56), color=app.fg()))
        box.add_widget(self.result)

        self.add_widget(box)

    # ----- الجودة -----
    def set_quality(self, q, *args):
        self.app.store.data["quality"] = q
        self.app.store.save()
        self.refresh_quality()

    def refresh_quality(self):
        cur = self.app.store.data["quality"]
        for q, b in self.q_buttons.items():
            active = q == cur
            b.background_color = rgba(ACCENT if active else "#ffffff", 1 if active else 0.12)
            b.color = rgba("#ffffff") if active else self.app.fg()

    # ----- خيارات التحميل تظهر بعد الضغط على تحميل -----
    def open_options(self, *args):
        if not self.url.text.strip():
            self.show_result(self.app.tx("empty_url"), error=True)
            return
        pop = ModalView(size_hint=(0.92, None), height=dp(340), background_color=rgba("#000000", 0.6))
        box = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10))
        box.add_widget(wrap(Label(text=self.app.tx("fmt_title"), size_hint_y=None, height=dp(30),
                                  bold=True, color=self.app.fg())))
        for kind, key in (("av", "fmt_av"), ("v", "fmt_v"), ("a", "fmt_a")):
            b = Button(text=self.app.tx(key), size_hint_y=None, height=dp(56), background_normal="",
                       background_color=rgba(ACCENT))
            b.bind(on_release=partial(self._choose, kind, pop))
            box.add_widget(b)
        close = Button(text=self.app.tx("close"), size_hint_y=None, height=dp(44),
                       background_normal="", background_color=rgba("#ffffff", 0.15))
        close.bind(on_release=lambda *a: pop.dismiss())
        box.add_widget(close)
        pop.add_widget(box)
        pop.open()

    def _choose(self, kind, pop, *args):
        pop.dismiss()
        self.start(kind)

    # ----- التحميل -----
    def start(self, kind):
        if self.worker_running:
            return
        urls = [line.strip() for line in self.url.text.splitlines() if line.strip()]
        if not urls:
            self.show_result(self.app.tx("empty_url"), error=True)
            return
        self.app.cancel_event.clear()
        self.worker_running = True
        self.go_btn.disabled = True
        self.cancel_btn.disabled = False
        self.result.text = ""
        quality = self.app.store.data["quality"]
        threading.Thread(target=self._worker, args=(urls, kind, quality), daemon=True).start()

    def _worker(self, urls, kind, quality):
        try:
            results = self.app.engine.download_many(
                urls, kind, quality, self._on_progress, self.app.cancel_event)
        except Exception as e:
            results = [{"ok": False, "error": str(e)}]
        Clock.schedule_once(partial(self._finish, results, len(urls)))

    def _on_progress(self, idx, total, pct, msg):
        Clock.schedule_once(partial(self._set_progress, idx, total, pct))

    def _set_progress(self, idx, total, pct, *args):
        self.bar.value = pct
        self.status.text = f"{self.app.tx('downloading')} {idx + 1}/{total}"

    def _finish(self, results, total, *args):
        self.worker_running = False
        self.go_btn.disabled = False
        self.cancel_btn.disabled = True
        self.status.text = self.app.tx("idle")
        ok = [r for r in results if r.get("ok")]
        if self.app.cancel_event.is_set():
            self.bar.value = 0
            self.show_result(self.app.tx("cancelled"), error=True)
        elif results and len(ok) == len(results):
            self.bar.value = 100
            msg = self.app.tx("success_many", n=len(ok)) if len(ok) > 1 else self.app.tx("success")
            self.show_result(msg)
        else:
            bad = next((r for r in results if not r.get("ok")), {})
            err = self.app.fmt(bad.get("error", "?"))
            self.show_result(f"{len(ok)}/{total}: {err}", error=True)

    def cancel(self, *args):
        self.app.cancel_event.set()
        self.status.text = self.app.tx("cancelled")

    def show_result(self, text, error=False):
        self.result.text = text
        self.result.color = rgba("#f87171") if error else rgba("#34d399")


class LibraryScreen(Screen):
    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app = app
        outer = BoxLayout(orientation="vertical", padding=[dp(16), dp(12)], spacing=dp(8))
        self.count = Label(text="", size_hint_y=None, height=dp(24), color=app.fg())
        outer.add_widget(self.count)
        self.scroll = ScrollView()
        self.list = GridLayout(cols=1, spacing=dp(8), size_hint_y=None)
        self.list.bind(minimum_height=self.list.setter("height"))
        self.scroll.add_widget(self.list)
        outer.add_widget(self.scroll)
        self.add_widget(outer)

    def refresh(self):
        self.list.clear_widgets()
        files = self.app.engine.list_files()
        self.count.text = self.app.tx("library_count", n=len(files))
        if not files:
            self.list.add_widget(Label(text=self.app.tx("library_empty"), size_hint_y=None,
                                       height=dp(60), color=self.app.fg()))
            return
        for f in files:
            self.list.add_widget(self._row(f))

    def _row(self, f):
        row = BoxLayout(size_hint_y=None, height=dp(64), spacing=dp(6))
        info = Label(text=f["name"], shorten=True, halign="left", valign="middle",
                     color=self.app.fg(), font_size=dp(14))
        info.bind(size=lambda w, v: setattr(w, "text_size", v))
        play = Button(text=self.app.tx("play"), size_hint_x=None, width=dp(80),
                      background_normal="", background_color=rgba(ACCENT))
        play.bind(on_release=partial(self.app.play_file, f["path"]))
        delete = Button(text=self.app.tx("delete"), size_hint_x=None, width=dp(80),
                        background_normal="", background_color=rgba("#ef4444"))
        delete.bind(on_release=partial(self._delete, f["path"]))
        row.add_widget(info)
        row.add_widget(play)
        row.add_widget(delete)
        return row

    def _delete(self, path, *args):
        self.app.engine.delete_file(path)
        self.refresh()


class SettingsScreen(Screen):
    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app = app
        box = BoxLayout(orientation="vertical", padding=[dp(16), dp(12)], spacing=dp(10))

        box.add_widget(self._title("language"))
        lang_row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        for code, label in (("ar", "العربية"), ("en", "English")):
            active = app.store.data["lang"] == code
            b = Button(text=shape(label) if code == "ar" else label, background_normal="",
                       background_color=rgba(ACCENT if active else "#ffffff", 1 if active else 0.12))
            b.bind(on_release=partial(self.set_lang, code))
            lang_row.add_widget(b)
        box.add_widget(lang_row)

        box.add_widget(self._title("bg_section"))
        box.add_widget(self._swatches(BG_CHOICES, "bg"))
        box.add_widget(self._title("text_color"))
        box.add_widget(self._swatches(FG_CHOICES, "fg"))

        reset = Button(text=app.tx("color_reset"), size_hint_y=None, height=dp(46),
                       background_normal="", background_color=rgba("#ffffff", 0.12))
        reset.bind(on_release=self.reset_colors)
        box.add_widget(reset)

        box.add_widget(Label(text=app.tx("developer_credit"), size_hint_y=None, height=dp(30),
                             bold=True, color=rgba(ACCENT)))
        self.add_widget(box)

    def _title(self, key):
        return wrap(Label(text=self.app.tx(key), size_hint_y=None, height=dp(26),
                          bold=True, color=self.app.fg()))

    def _swatches(self, choices, key):
        grid = GridLayout(cols=6, size_hint_y=None, height=dp(44), spacing=dp(6))
        for c in choices:
            b = Button(text="", background_normal="", background_color=rgba(c))
            b.bind(on_release=partial(self.set_color, key, c))
            grid.add_widget(b)
        return grid

    def set_lang(self, code, *args):
        self.app.store.data["lang"] = code
        self.app.apply_settings("settings")

    def set_color(self, key, color, *args):
        self.app.store.data[key] = color
        self.app.apply_settings("settings")

    def reset_colors(self, *args):
        self.app.store.data["bg"] = DEFAULTS["bg"]
        self.app.store.data["fg"] = DEFAULTS["fg"]
        self.app.apply_settings("settings")


class RIApp(App):
    def build(self):
        self.store = Store(os.path.join(self.user_data_dir, "settings.json"))
        self.output_dir = self._pick_output_dir()
        self.engine = RIDownloaderEngine(self.output_dir, self.store.data["lang"])
        self.cancel_event = threading.Event()
        self.request_permissions()

        self.root_box = BoxLayout(orientation="vertical")
        with self.root_box.canvas.before:
            self._bg_color = Color(*rgba(self.store.data["bg"]))
            self._bg_rect = Rectangle()
        self.root_box.bind(pos=self._sync_bg, size=self._sync_bg)
        self.build_ui()
        return self.root_box

    def _sync_bg(self, *args):
        self._bg_rect.pos = self.root_box.pos
        self._bg_rect.size = self.root_box.size

    def build_ui(self, pending_url="", start="home"):
        self._bg_color.rgba = rgba(self.store.data["bg"])
        self.root_box.clear_widgets()
        self.sm = ScreenManager()
        self.home = HomeScreen(self, name="home")
        self.library = LibraryScreen(self, name="library")
        self.settings = SettingsScreen(self, name="settings")
        for s in (self.home, self.library, self.settings):
            self.sm.add_widget(s)
        self.home.url.text = pending_url
        self.root_box.add_widget(self.sm)
        self.root_box.add_widget(self.make_nav())
        self.go(start)

    def make_nav(self):
        bar = BoxLayout(size_hint_y=None, height=dp(62), spacing=dp(6), padding=[dp(10), dp(6)])
        self.nav = {}
        for name, key in (("home", "nav_home"), ("library", "nav_library"), ("settings", "nav_settings")):
            b = Button(text=self.tx(key), background_normal="")
            b.bind(on_release=partial(self.go, name))
            self.nav[name] = b
            bar.add_widget(b)
        return bar

    def go(self, name, *args):
        self.sm.current = name
        for key, b in self.nav.items():
            active = key == name
            b.background_color = rgba(ACCENT if active else self.store.data["fg"], 1 if active else 0.1)
            b.color = rgba("#ffffff") if active else self.fg()
        if name == "library":
            self.library.refresh()

    def apply_settings(self, screen):
        self.store.save()
        self.engine.set_language(self.store.data["lang"])
        self.build_ui(self.home.url.text, screen)

    # ----- نصوص وألوان -----
    def fmt(self, text):
        return shape(text) if self.store.data["lang"] == "ar" else text

    def tx(self, key, **kw):
        return self.fmt(get_text(key, self.store.data["lang"], **kw))

    def fg(self):
        return rgba(self.store.data["fg"])

    def toast(self, msg):
        Popup(title="RI", content=Label(text=self.fmt(msg), color=self.fg()),
              size_hint=(0.85, 0.3)).open()

    # ----- تشغيل الملف بمشغل الهاتف -----
    def play_file(self, path, *args):
        try:
            from jnius import autoclass
            # تجاوز قيد Android على مشاركة روابط file:// (مناسب للتشغيل المحلي فقط)
            StrictMode = autoclass("android.os.StrictMode")
            VmBuilder = autoclass("android.os.StrictMode$VmPolicy$Builder")
            StrictMode.setVmPolicy(VmBuilder().build())
            Intent = autoclass("android.content.Intent")
            Uri = autoclass("android.net.Uri")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            intent = Intent(Intent.ACTION_VIEW)
            intent.setDataAndType(Uri.parse("file://" + path), self._mime(path))
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            PythonActivity.mActivity.startActivity(intent)
        except Exception as e:
            self.toast(str(e))

    @staticmethod
    def _mime(path):
        p = path.lower()
        if p.endswith((".m4a", ".mp3")):
            return "audio/*"
        return "video/*"

    # ----- مجلد الحفظ والصلاحيات -----
    def _pick_output_dir(self):
        for path in ("/sdcard/Download/RI", os.path.join(self.user_data_dir, "downloads")):
            try:
                os.makedirs(path, exist_ok=True)
                if os.access(path, os.W_OK):
                    return path
            except OSError:
                continue
        return os.path.join(self.user_data_dir, "downloads")

    def request_permissions(self):
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])
        except Exception:
            pass


if __name__ == "__main__":
    RIApp().run()
