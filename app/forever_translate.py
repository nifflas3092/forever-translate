"""Forever Translate - companion window for the WoW: Forever addon.

Run:  python forever_translate.py          (normal)
      python forever_translate.py --demo   (fake chat, no WoW needed)
      python forever_translate.py --image screenshot.png   (check a screenshot)
"""

import json
import os
import queue
import sys
import threading
import time
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor

from translate import LANGUAGES, WOW_LOCALES, Translator
from winfocus import focus_wow
import theme as T
import chatframe as C

CONFIG_PATH = os.path.join(T.USER_DIR, "config.json")

DEFAULT_CONFIG = {
    "engine": "mymemory",
    "mymemory_email": "",
    "deepl_key": "",
    "claude_key": "",
    "claude_model": "claude-haiku-5-5",
    "my_language": "auto",
    "show_original": True,
    "show_english_messages": False,
    "always_on_top": True,
    "opacity": 0.92,
    "font_size": 11,
    "jump_to_wow": True,
}

def load_config():
    config = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                config.update(json.load(f))
        except Exception as exc:
            print("config.json could not be read:", exc)
    else:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
    return config


class App:
    def __init__(self, config, demo=False):
        self.config = config
        # "auto" = use the language the WoW client is set to (the addon tells us)
        self.auto_language = config.get("my_language", "auto") in ("auto", "")
        if self.auto_language:
            config["my_language"] = "en"  # until WoW tells us otherwise
        self.translator = Translator(config)
        self.pool = ThreadPoolExecutor(max_workers=3)
        self.events = queue.Queue()
        self.last_lang = "es"
        self.count = 0
        self.recent = {}

        T.set_app_id()
        T.make_dpi_aware()
        root = self.root = tk.Tk()
        k = T.setup_dpi(root)
        T.set_window_icon(root)
        root.title("Forever Translate")
        root.geometry(f"{int(560 * k)}x{int(400 * k)}")
        root.minsize(int(380 * k), int(240 * k))
        root.configure(bg="#000000")
        root.attributes("-topmost", bool(config["always_on_top"]))
        try:
            root.attributes("-alpha", float(config["opacity"]))
        except tk.TclError:
            pass

        size = int(config["font_size"])
        face = C.pick_chat_font(root)
        self.f_chat = (face, size + 2)
        self.f_small = (face, size)
        self.f_tab = (face, size - 1, "bold")
        self.target_code = self.last_lang

        frame = C.TooltipFrame(root)
        frame.place_in(fill="both", expand=True, padx=T.px(4), pady=T.px(4))

        self.tabs = C.ChatTabs(frame, self.f_tab, self.select_tab)
        self.tabs.pack(fill="x")

        # chat input bar, like the in-game edit box
        bar = tk.Frame(frame, bg=C.FRAME_BG)
        bar.pack(side="bottom", fill="x", padx=T.px(6), pady=(T.px(4), T.px(6)))
        self.hint = tk.Label(frame, text="Enter translates and copies your reply \u00b7 "
                             "then in WoW: Enter, Ctrl+V, Enter", font=self.f_small,
                             bg=C.FRAME_BG, fg=C.DIM, anchor="w")
        self.hint.pack(side="bottom", fill="x", padx=T.px(10))
        edge = tk.Frame(bar, bg=C.FRAME_EDGE, padx=1, pady=1)
        edge.pack(fill="x")
        box = tk.Frame(edge, bg=C.EDIT_BG)
        box.pack(fill="x")
        self.target_label = tk.Label(box, font=self.f_chat, bg=C.EDIT_BG, fg=C.WOW_GOLD,
                                     cursor="hand2", padx=T.px(6))
        self.target_label.pack(side="left")
        self.target_label.bind("<Button-1>", self.pick_language)
        self.lang_menu = tk.Menu(root, tearoff=0, bg=C.FRAME_BG, fg="#ffffff", font=self.f_small,
                                 activebackground=C.TAB_BG_ACTIVE, activeforeground=C.WOW_GOLD,
                                 bd=1, relief="solid")
        send = tk.Label(box, text="Send", font=self.f_tab, bg=C.EDIT_BG, fg=C.WOW_GOLD,
                        cursor="hand2", padx=T.px(8))
        send.pack(side="right")
        send.bind("<Button-1>", lambda e: self.send_reply())
        send.bind("<Enter>", lambda e: send.configure(fg="#ffffff"))
        send.bind("<Leave>", lambda e: send.configure(fg=C.WOW_GOLD))
        self.reply = tk.Entry(box, bg=C.EDIT_BG, fg="#ffffff", insertbackground="#ffffff",
                              relief="flat", font=self.f_chat, highlightthickness=0,
                              insertwidth=max(2, T.px(2)))
        self.reply.pack(side="left", fill="x", expand=True, ipady=T.px(5))
        self.reply.bind("<Return>", lambda e: self.send_reply())
        self._placeholder = "type your reply in English\u2026"
        self._show_placeholder()
        self.reply.bind("<FocusIn>", lambda e: self._hide_placeholder())
        self.reply.bind("<FocusOut>", lambda e: self._show_placeholder())
        self.refresh_targets()

        self.chat = C.ChatBox(frame, self.f_chat, self.f_small)
        self.chat.pack(fill="both", expand=True, padx=T.px(6), pady=(0, T.px(2)))

        root.protocol("WM_DELETE_WINDOW", self.close)
        root.after(50, self.pump)

        if demo:
            self.on_status("demo mode (no WoW needed)")
            threading.Thread(target=self.demo_feed, daemon=True).start()
        else:
            from bridge import BridgeReader
            self.reader = BridgeReader(self.on_message, self.on_status)
            self.reader.start()

    # ---- called from background threads -------------------------------

    def on_status(self, status):
        self.events.put(("status", status))

    def on_message(self, channel, sender, text):
        if channel == "\x01FT":
            self.events.put(("hello", text))
            return
        if channel.startswith("\x01"):
            return
        # ignore the same message from the same player repeated within a minute
        # (trade spam), so it can't flood the window or use up the free limit
        now = time.time()
        key = (sender, text)
        if now - self.recent.get(key, 0) < 60:
            return
        self.recent[key] = now
        if len(self.recent) > 500:
            self.recent = {k: t for k, t in self.recent.items() if now - t < 60}
        self.pool.submit(self._translate_incoming, channel, sender, text)

    def _translate_incoming(self, channel, sender, text):
        try:
            lang, out = self.translator.incoming(text)
            self.events.put(("msg", channel, sender, text, lang, out, None))
        except Exception as exc:
            self.events.put(("msg", channel, sender, text, "?", None, str(exc)))

    def demo_feed(self):
        samples = [
            ("Trade", "Pedro", "alguien para Minas de la Muerte? falta tanque y heal"),
            ("General", "Lucas", "vcs sabem onde fica o treinador de pesca em ventobravo?"),
            ("Say", "Ivan", "кто идёт в рейд сегодня?"),
            ("Party", "Sofia", "jaja perdon, me desconecté. ya vuelvo"),
            ("Say", "Mike", "anyone selling linen cloth?"),
            ("Guild", "Klaus", "Hat jemand Lust auf Gnomeregan heute Abend?"),
        ]
        for sample in samples:
            time.sleep(1.2)
            self.on_message(*sample)

    # ---- UI thread ----------------------------------------------------

    def pump(self):
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == "status":
                    self.show_status(event[1])
                elif event[0] == "msg":
                    self.show_message(*event[1:])
                elif event[0] == "hello":
                    self.on_hello(event[1])
                elif event[0] == "reply":
                    self.show_reply(*event[1:])
        except queue.Empty:
            pass
        self.root.after(50, self.pump)

    def show_status(self, status):
        text = {"searching": "\u25cf Looking for WoW\u2026",
                "connected": "\u25cf Connected"}.get(status, "\u25cf " + status)
        colour = C.GOOD if status == "connected" or status.startswith("demo") else C.WAIT
        if self.count:
            text += f"  \u00b7  {self.count} translated"
        self.tabs.set_status(text, colour)
        self._status_raw = status

    def select_tab(self, tab):
        self.chat.set_filter(tab)

    def system(self, text, colour=C.SYSTEM_YELLOW):
        self.chat.add("system", [(text, colour, self.f_chat, 0)])

    def refresh_targets(self):
        mine = self.config["my_language"]
        self.lang_menu.delete(0, "end")
        for code, name in LANGUAGES.items():
            if code != mine:
                self.lang_menu.add_command(label=name, command=lambda c=code: self.set_target(c))
        if self.target_code == mine:
            self.target_code = "en" if mine != "en" else "es"
        self.set_target(self.target_code)

    def pick_language(self, event):
        self.lang_menu.tk_popup(event.x_root, event.y_root)

    def on_hello(self, text):
        """The addon says e.g. 'connected ptBR' - use it as my language."""
        parts = text.split()
        code = WOW_LOCALES.get(parts[1]) if len(parts) > 1 else None  # only known values
        if not code or not self.auto_language or code == self.config["my_language"]:
            return
        self.config["my_language"] = code
        self.translator.cache.clear()
        self.refresh_targets()
        self.system(f"Your game is in {LANGUAGES[code]}, so chat will be translated into "
                    f"{LANGUAGES[code]}.")

    def show_message(self, channel, sender, original, lang, translated, error):
        if channel.startswith("\x01"):
            return
        if translated is None and not error and not self.config["show_english_messages"]:
            return
        if translated is not None:
            self.count += 1
            if lang and lang != "?":
                self.set_target(lang)
        colour = C.CHANNEL_COLORS.get(channel, C.CHANNEL_DEFAULT)
        lang_name = LANGUAGES.get(lang, LANGUAGES.get((lang or "").split("-")[0], lang or "?"))
        head = f"[{channel}] [{sender}]: "
        indent = T.px(16)
        if translated is not None:
            lines = [(head + translated, colour, self.f_chat, 0)]
            if self.config["show_original"]:
                lines.append((f"{lang_name}: {original}", C.DIM, self.f_small, indent))
        elif error:
            lines = [(head + original, colour, self.f_chat, 0),
                     (f"Translation failed: {error}", C.ERROR, self.f_small, indent)]
        else:
            lines = [(head + original, colour, self.f_chat, 0)]
        tab = C.tab_for(channel)
        self.chat.add(tab, lines)
        self.tabs.mark_unread(tab)
        self.show_status(getattr(self, "_status_raw", ""))

    def set_target(self, lang):
        code = lang if lang in LANGUAGES else lang.split("-")[0]
        if code in LANGUAGES and code != self.config["my_language"]:
            self.last_lang = self.target_code = code
            self.target_label.configure(text=f"[{LANGUAGES[code]}]:")

    def send_reply(self):
        text = self.reply.get().strip()
        if not text or self._placeholder_on:
            return
        code = self.target_code
        self.hint.configure(text="Translating\u2026", fg=C.DIM)

        def work():
            try:
                out = self.translator.outgoing(text, code)
                self.events.put(("reply", out, None))
            except Exception as exc:
                self.events.put(("reply", None, str(exc)))

        self.pool.submit(work)

    def show_reply(self, out, error):
        if error:
            self.hint.configure(text=f"Reply failed: {error}", fg=C.ERROR)
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(out)
        self.root.update()
        self.reply.delete(0, "end")
        self.system(f"Copied: {out}")
        jumped = self.config.get("jump_to_wow", True) and focus_wow()
        self.hint.configure(text=("Switched to WoW: " if jumped else "In WoW: ")
                            + "press Enter, Ctrl+V, Enter to send it", fg=C.SYSTEM_YELLOW)

    def _show_placeholder(self):
        if not self.reply.get():
            self._placeholder_on = True
            self.reply.configure(fg=C.DIM)
            self.reply.insert(0, self._placeholder)

    def _hide_placeholder(self):
        if getattr(self, "_placeholder_on", False):
            self._placeholder_on = False
            self.reply.delete(0, "end")
            self.reply.configure(fg="#ffffff")

    def close(self):
        if hasattr(self, "reader"):
            self.reader.stop()
        self.pool.shutdown(wait=False, cancel_futures=True)
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def check_image(path):
    """Debug helper: decode the strip from a saved screenshot."""
    import numpy as np
    from PIL import Image

    from bridge import decode, find_grid, parse_payload

    img = np.asarray(Image.open(path).convert("RGB"))
    found = find_grid(img)
    if not found:
        print("No strip found in that image.")
        return
    x, y, sx, sy = found
    print(f"Strip found at x={x:.0f}, y={y:.0f}, block size {sx:.2f} x {sy:.2f}px")
    result = decode(img, x, y, sx, sy)
    if result:
        seq, payload = result
        print(f"Message #{seq}:", parse_payload(payload))
    else:
        print("Strip found but the message could not be read (it may have been mid-change).")


if __name__ == "__main__":
    if getattr(sys, "frozen", False):
        # the .exe has no console window, so keep any errors in a log file
        # next to it (it holds only error messages, never chat)
        log = open(os.path.join(T.USER_DIR, "forever_translate.log"), "a", encoding="utf-8")
        sys.stderr = sys.stdout = log
    if "--image" in sys.argv:
        check_image(sys.argv[sys.argv.index("--image") + 1])
    else:
        App(load_config(), demo="--demo" in sys.argv).run()
