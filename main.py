import json
import os
import threading

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image as KivyImage
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen, ScreenManager, SlideTransition
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.video import Video

try:
    from android.permissions import request_permissions, Permission
except ImportError:  # يعمل على الكمبيوتر بدون أندرويد
    request_permissions = None
    Permission = None

from lang import get_text
from ri_engine import RIDownloaderEngine

BG = (0.07, 0.075, 0.085, 1)
PRIMARY = (0.16, 0.45, 0.88, 1)
SURFACE = (0.15, 0.16, 0.19, 0.92)
DARK_BTN = (0.18, 0.19, 0.22, 0.92)
DANGER = (0.6, 0.18, 0.18, 1)
TEXT = (0.96, 0.97, 0.98, 1)
MUTED = (0.72, 0.75, 0.8, 1)

KIND_CODES = ["av", "v", "a"]
KIND_KEYS = ["fmt_av", "fmt_v", "fmt_a"]
QUALITY_VALUES = ["360p", "720p", "1080p"]


class BaseScreen(Screen):
    """شاشة فيها خلفية قابلة للتغيير وشريط تنقل سفلي."""

    def __init__(self, app_ref, name, **kwargs):
        super().__init__(name=name, **kwargs)
        self.app_ref = app_ref
        self.lang = app_ref.lang

        root = FloatLayout()
        self.bg_holder = FloatLayout(size_hint=(1, 1))
        with self.bg_holder.canvas.before:
            Color(*BG)
            self.bg_rect = Rectangle(pos=self.bg_holder.pos, size=self.bg_holder.size)
        self.bg_holder.bind(pos=self._sync_bg, size=self._sync_bg)

        self.content = BoxLayout(
            orientation="vertical",
            padding=[dp(18), dp(16), dp(18), dp(12)],
            spacing=dp(10),
            size_hint=(1, 1),
        )
        root.add_widget(self.bg_holder)
        root.add_widget(self.content)
        self.add_widget(root)

        self.nav_items = []
        self.nav = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(6))
        for scr, key in (("home", "nav_home"), ("library", "nav_library"), ("settings", "nav_settings")):
            b = Button(background_normal="")
            b.bind(on_press=lambda _b, s=scr: self.app_ref.go(s))
            self.nav.add_widget(b)
            self.nav_items.append((b, scr, key))
        self.content.add_widget(self.nav)
        self.refresh_nav()
        self.apply_background(app_ref.bg_type, app_ref.bg_path)

    def _sync_bg(self, inst, _value):
        self.bg_rect.pos = inst.pos
        self.bg_rect.size = inst.size

    def apply_background(self, bg_type, bg_path):
        self.bg_holder.clear_widgets()
        if bg_type == "image" and bg_path and os.path.exists(bg_path):
            self.bg_holder.add_widget(KivyImage(source=bg_path, allow_stretch=True, keep_ratio=False))
        elif bg_type == "video" and bg_path and os.path.exists(bg_path):
            try:
                self.bg_holder.add_widget(Video(
                    source=bg_path, state="play", options={"eos": "loop"},
                    allow_stretch=True, keep_ratio=False,
                ))
            except Exception:
                pass

    def refresh_nav(self):
        for b, scr, key in self.nav_items:
            b.text = get_text(key, self.app_ref.lang)
            b.background_color = PRIMARY if self.name == scr else DARK_BTN

    def wrap_label(self, lbl):
        lbl.bind(size=lambda l, s: setattr(l, "text_size", (l.width, None)))
        return lbl


class HomeScreen(BaseScreen):
    def __init__(self, app_ref, **kwargs):
        super().__init__(app_ref, "home", **kwargs)
        c = self.content

        top = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        self.btn_ar = Button(text="العربية", background_normal="")
        self.btn_en = Button(text="English", background_normal="")
        self.btn_ar.bind(on_press=lambda _: self.app_ref.set_language("ar"))
        self.btn_en.bind(on_press=lambda _: self.app_ref.set_language("en"))
        top.add_widget(self.btn_ar)
        top.add_widget(self.btn_en)
        c.add_widget(top)

        self.title_lbl = Label(font_size="30sp", bold=True, size_hint_y=None, height=dp(50), color=TEXT)
        self.sub_lbl = Label(font_size="14sp", size_hint_y=None, height=dp(26), color=MUTED)
        c.add_widget(self.title_lbl)
        c.add_widget(self.sub_lbl)

        self.url_input = TextInput(
            multiline=True,
            size_hint_y=None,
            height=dp(96),
            padding=[dp(14), dp(12)],
            background_normal="",
            background_color=(0.14, 0.15, 0.18, 0.94),
            foreground_color=TEXT,
            hint_text_color=(0.56, 0.6, 0.66, 1),
        )
        c.add_widget(self.url_input)

        # نوع التحميل
        self.kind = "av"
        kind_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        self.kind_buttons = {}
        for code, key in zip(KIND_CODES, KIND_KEYS):
            tb = ToggleButton(group="kind", background_normal="", state="down" if code == "av" else "normal")
            tb.code = code
            tb.key = key
            tb.bind(on_press=lambda _b, cd=code: self.set_kind(cd))
            kind_row.add_widget(tb)
            self.kind_buttons[code] = tb
        c.add_widget(kind_row)

        # الجودة
        q_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        self.quality_lbl = Label(size_hint_x=0.4, color=MUTED)
        self.quality = Spinner(text="720p", values=QUALITY_VALUES, background_normal="", background_color=SURFACE)
        q_row.add_widget(self.quality_lbl)
        q_row.add_widget(self.quality)
        c.add_widget(q_row)

        # الأزرار
        btn_row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
        self.download_btn = Button(bold=True, background_normal="", background_color=PRIMARY)
        self.download_btn.bind(on_press=self.start_download)
        self.cancel_btn = Button(background_normal="", background_color=DANGER, disabled=True, size_hint_x=0.35)
        self.cancel_btn.bind(on_press=self.cancel_download)
        btn_row.add_widget(self.download_btn)
        btn_row.add_widget(self.cancel_btn)
        c.add_widget(btn_row)

        self.progress_bar = ProgressBar(max=100, value=0, size_hint_y=None, height=dp(22))
        c.add_widget(self.progress_bar)

        self.status_lbl = self.wrap_label(Label(text="", font_size="13sp", color=(0.88, 0.9, 0.94, 1)))
        c.add_widget(self.status_lbl)

        self.credit_lbl = Label(font_size="13sp", bold=True, size_hint_y=None, height=dp(28), color=(0.78, 0.82, 0.88, 1))
        c.add_widget(self.credit_lbl)

        self.cancel_event = None
        self.refresh_texts()

    def refresh_texts(self):
        self.lang = self.app_ref.lang
        self.title_lbl.text = get_text("app_name", self.lang)
        self.sub_lbl.text = get_text("subtitle", self.lang)
        self.url_input.hint_text = get_text("url_hint", self.lang)
        self.download_btn.text = get_text("download_btn", self.lang)
        self.cancel_btn.text = get_text("cancel_btn", self.lang)
        self.quality_lbl.text = get_text("quality", self.lang)
        self.credit_lbl.text = get_text("developer_credit", self.lang)
        for code, tb in self.kind_buttons.items():
            tb.text = get_text(tb.key, self.lang)
        self.btn_ar.background_color = PRIMARY if self.lang == "ar" else SURFACE
        self.btn_en.background_color = PRIMARY if self.lang == "en" else SURFACE
        self.refresh_nav()
        self.set_kind(self.kind)

    def set_kind(self, code):
        self.kind = code
        for k, tb in self.kind_buttons.items():
            tb.background_color = PRIMARY if k == code else SURFACE
        self.quality.disabled = code == "a"  # الصوت لا يحتاج جودة فيديو

    def _set_running(self, running):
        self.download_btn.disabled = running
        self.cancel_btn.disabled = not running

    def _update_ui(self, progress=None, status_text=None):
        if progress is not None:
            self.progress_bar.value = progress
        if status_text is not None:
            self.status_lbl.text = status_text

    def start_download(self, _):
        urls = [u.strip() for u in self.url_input.text.splitlines() if u.strip()]
        if not urls:
            self.status_lbl.text = get_text("empty_url", self.lang)
            return

        quality = self.quality.text.replace("p", "")
        kind = self.kind
        self.cancel_event = threading.Event()
        self._set_running(True)
        self._update_ui(progress=0, status_text=get_text("fetching_info", self.lang))
        engine = self.app_ref.engine
        event = self.cancel_event

        def worker():
            def on_progress(idx, total, pct, msg):
                suffix = f"  ({idx + 1}/{total})" if total > 1 else ""
                Clock.schedule_once(lambda _dt: self._update_ui(progress=pct, status_text=msg + suffix))

            results = engine.download_many(urls, kind, quality, on_progress, event)
            Clock.schedule_once(lambda _dt: self._finish(results, event.is_set()))

        threading.Thread(target=worker, daemon=True).start()

    def cancel_download(self, _):
        if self.cancel_event is not None:
            self.cancel_event.set()

    def _finish(self, results, cancelled):
        self._set_running(False)
        ok = [r for r in results if r.get("ok")]
        if cancelled and not ok:
            msg = get_text("cancelled", self.lang)
        elif len(ok) > 1:
            msg = get_text("success_many", self.lang, n=len(ok))
        elif ok:
            msg = f"{get_text('success', self.lang)}\n{ok[0].get('message', '')}"
        else:
            err = results[-1].get("error") if results else get_text("empty_url", self.lang)
            msg = err or get_text("error_prefix", self.lang, error="unknown")
        self._update_ui(progress=100 if ok else 0, status_text=msg)


class LibraryScreen(BaseScreen):
    def __init__(self, app_ref, **kwargs):
        super().__init__(app_ref, "library", **kwargs)
        c = self.content

        self.title_lbl = Label(font_size="26sp", bold=True, size_hint_y=None, height=dp(44), color=TEXT)
        self.count_lbl = Label(font_size="13sp", size_hint_y=None, height=dp(24), color=MUTED)
        c.add_widget(self.title_lbl)
        c.add_widget(self.count_lbl)

        self.scroll = ScrollView(size_hint=(1, 1))
        self.list = GridLayout(cols=1, size_hint_y=None, spacing=dp(8))
        self.list.bind(minimum_height=self.list.setter("height"))
        self.scroll.add_widget(self.list)
        c.add_widget(self.scroll)
        self.refresh_texts()

    def on_pre_enter(self, *_args):
        self.refresh()

    def refresh_texts(self):
        self.lang = self.app_ref.lang
        self.title_lbl.text = get_text("library_title", self.lang)
        self.refresh_nav()
        self.refresh()

    def refresh(self):
        self.list.clear_widgets()
        files = self.app_ref.engine.list_files()
        self.count_lbl.text = get_text("library_count", self.lang, n=len(files))
        if not files:
            self.list.add_widget(self.wrap_label(Label(
                text=get_text("library_empty", self.lang), size_hint_y=None, height=dp(60), color=MUTED)))
            return
        for f in files:
            row = BoxLayout(size_hint_y=None, height=dp(58), spacing=dp(8))
            name = self.wrap_label(Label(
                text=f"{f['name']}\n{f['size'] / (1024 * 1024):.1f} MB",
                halign="left", valign="middle", font_size="13sp", color=TEXT, size_hint_x=0.7,
            ))
            delete = Button(
                text=get_text("delete", self.lang), size_hint_x=0.3,
                background_normal="", background_color=DANGER,
            )
            delete.bind(on_press=lambda _b, p=f["path"]: self._delete(p))
            row.add_widget(name)
            row.add_widget(delete)
            self.list.add_widget(row)

    def _delete(self, path):
        self.app_ref.engine.delete_file(path)
        self.refresh()


class SettingsScreen(BaseScreen):
    def __init__(self, app_ref, **kwargs):
        super().__init__(app_ref, "settings", **kwargs)
        c = self.content

        self.title_lbl = Label(font_size="24sp", bold=True, size_hint_y=None, height=dp(46), color=TEXT)
        self.bg_section_lbl = Label(font_size="16sp", bold=True, size_hint_y=None, height=dp(32), color=MUTED)
        self.btn_pick_image = Button(size_hint_y=None, height=dp(50), background_normal="", background_color=PRIMARY)
        self.btn_pick_image.bind(on_press=lambda _: self._open_chooser("image"))
        self.btn_pick_video = Button(size_hint_y=None, height=dp(50), background_normal="", background_color=PRIMARY)
        self.btn_pick_video.bind(on_press=lambda _: self._open_chooser("video"))
        self.btn_reset_bg = Button(size_hint_y=None, height=dp(48), background_normal="", background_color=DARK_BTN)
        self.btn_reset_bg.bind(on_press=self._reset_background)
        self.info_lbl = self.wrap_label(Label(text="", font_size="13sp", color=(0.75, 0.88, 0.8, 1)))
        self.credit_lbl = Label(font_size="13sp", bold=True, size_hint_y=None, height=dp(28), color=(0.78, 0.82, 0.88, 1))

        for w in (self.title_lbl, self.bg_section_lbl, self.btn_pick_image, self.btn_pick_video,
                  self.btn_reset_bg, self.info_lbl, self.credit_lbl):
            c.add_widget(w)
        c.add_widget(BoxLayout())  # مسافة قبل شريط التنقل
        self.refresh_texts()

    def refresh_texts(self):
        self.lang = self.app_ref.lang
        self.title_lbl.text = get_text("settings_title", self.lang)
        self.bg_section_lbl.text = get_text("bg_section", self.lang)
        self.btn_pick_image.text = get_text("pick_image", self.lang)
        self.btn_pick_video.text = get_text("pick_video", self.lang)
        self.btn_reset_bg.text = get_text("reset_bg", self.lang)
        self.credit_lbl.text = get_text("developer_credit", self.lang)
        self.refresh_nav()

    def _open_chooser(self, media_type: str):
        start_path = "/sdcard" if os.path.exists("/sdcard") else os.path.expanduser("~")
        if media_type == "image":
            filters = ["*.png", "*.jpg", "*.jpeg", "*.webp"]
        else:
            filters = ["*.mp4", "*.mkv", "*.webm", "*.mov", "*.gif"]

        chooser = FileChooserIconView(path=start_path, filters=filters)
        box = BoxLayout(orientation="vertical", spacing=8, padding=8)
        box.add_widget(chooser)

        btn_row = BoxLayout(size_hint_y=None, height=44, spacing=8)
        btn_cancel = Button(text=get_text("cancel_btn", self.lang))
        btn_select = Button(text=get_text("bg_section", self.lang), background_normal="", background_color=PRIMARY)
        btn_row.add_widget(btn_cancel)
        btn_row.add_widget(btn_select)
        box.add_widget(btn_row)

        popup = Popup(title=get_text("bg_section", self.lang), content=box, size_hint=(0.92, 0.85))
        btn_cancel.bind(on_press=popup.dismiss)

        def _confirm(_):
            if chooser.selection:
                selected = chooser.selection[0]
                self.app_ref.set_background(media_type, selected)
                self.info_lbl.text = f"{get_text('bg_set', self.lang)}\n{selected}"
                popup.dismiss()

        btn_select.bind(on_press=_confirm)
        popup.open()

    def _reset_background(self, _):
        self.app_ref.set_background("none", "")
        self.info_lbl.text = get_text("bg_reset", self.lang)


class RIApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.lang = "ar"
        self.bg_type = "none"
        self.bg_path = ""
        self.config_file = "ri_config.json"

    def _load_config(self):
        cfg_path = os.path.join(self.user_data_dir, self.config_file)
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.lang = data.get("lang", "ar")
                self.bg_type = data.get("bg_type", "none")
                self.bg_path = data.get("bg_path", "")
            except Exception:
                pass

    def _save_config(self):
        try:
            os.makedirs(self.user_data_dir, exist_ok=True)
            cfg_path = os.path.join(self.user_data_dir, self.config_file)
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump({"lang": self.lang, "bg_type": self.bg_type, "bg_path": self.bg_path},
                          f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _pick_output_dir(self) -> str:
        # نجرّب مجلد التنزيلات العام، وإذا لم يُسمح بالكتابة نستخدم مجلد التطبيق الخاص
        public_dir = "/sdcard/Download/RI"
        try:
            os.makedirs(public_dir, exist_ok=True)
            if os.access(public_dir, os.W_OK):
                return public_dir
        except OSError:
            pass
        private_dir = os.path.join(self.user_data_dir, "downloads")
        os.makedirs(private_dir, exist_ok=True)
        return private_dir

    def build(self):
        self.title = "RI"
        Window.clearcolor = BG
        self._load_config()

        if request_permissions and Permission:
            request_permissions([
                Permission.INTERNET,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_EXTERNAL_STORAGE,
                Permission.READ_MEDIA_IMAGES,
                Permission.READ_MEDIA_VIDEO,
            ])

        self.engine = RIDownloaderEngine(output_dir=self._pick_output_dir(), lang=self.lang)

        self.sm = ScreenManager(transition=SlideTransition(duration=0.2))
        self.home = HomeScreen(self)
        self.library = LibraryScreen(self)
        self.settings = SettingsScreen(self)
        for s in (self.home, self.library, self.settings):
            self.sm.add_widget(s)
        return self.sm

    def go(self, name):
        self.sm.current = name

    def _refresh_all(self):
        for s in (self.home, self.library, self.settings):
            s.refresh_texts()

    def set_language(self, new_lang: str):
        self.lang = new_lang
        self.engine.set_language(new_lang)
        self._refresh_all()
        self._save_config()

    def set_background(self, bg_type: str, bg_path: str):
        self.bg_type = bg_type
        self.bg_path = bg_path
        for s in (self.home, self.library, self.settings):
            s.apply_background(bg_type, bg_path)
        self._save_config()


if __name__ == "__main__":
    RIApp().run()
