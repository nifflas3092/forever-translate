"""WoW chat-frame look for Forever Translate: chat tabs, chat-coloured lines
with the game's drop shadow, a dark tooltip-style box and a chat input bar.
Everything is drawn here; no Blizzard art is used."""

import tkinter as tk
import tkinter.font as tkfont

from theme import px

# Colours
FRAME_BG = "#0b0b0d"        # chat box (close to the game's translucent black)
FRAME_EDGE = "#5c5c66"      # tooltip-style silver border
FRAME_EDGE_DARK = "#26262c"
TAB_BG = "#141418"
TAB_BG_ACTIVE = "#17171c"
TAB_TEXT = "#9a9aa3"
WOW_GOLD = "#ffd100"        # the game's gold UI text
SYSTEM_YELLOW = "#ffff00"   # system messages
DIM = "#8c8c96"             # originals and hints
EDIT_BG = "#060607"
GOOD = "#40ff40"
WAIT = "#ffb000"
ERROR = "#ff4040"

# WoW's default chat colours
CHANNEL_COLORS = {
    "Say": "#ffffff", "Yell": "#ff4040", "Whisper": "#ff80ff", "Party": "#aaaaff",
    "Raid": "#ff7f00", "Instance": "#ff7f00", "Guild": "#40ff40", "Officer": "#40c040",
    "Test": "#66ccff",
}
CHANNEL_DEFAULT = "#ffc0c0"  # General, Trade, LookingForGroup...

# Which tab each chat type shows under
TABS = [("all", "All"), ("party", "Party"), ("guild", "Guild"),
        ("whisper", "Whispers"), ("world", "World")]
TAB_OF = {"Party": "party", "Raid": "party", "Instance": "party",
          "Guild": "guild", "Officer": "guild", "Whisper": "whisper"}


def tab_for(channel):
    return TAB_OF.get(channel, "world")


def pick_chat_font(root):
    families = set(tkfont.families(root))
    for name in ("Arial Narrow", "Arial", "Liberation Sans Narrow", "Liberation Sans",
                 "DejaVu Sans"):
        if name in families:
            return name
    return "TkDefaultFont"


class ChatTabs(tk.Canvas):
    """Chat tabs along the top, like the in-game chat frame. A dot appears on
    a tab that has new messages you haven't looked at."""

    def __init__(self, parent, font, on_select):
        super().__init__(parent, bg=FRAME_BG, highlightthickness=0, height=px(30))
        self.font, self.on_select = font, on_select
        self.current = "all"
        self.unread = set()
        self.status_text, self.status_colour = "", DIM
        self.hit = []
        self.bind("<Configure>", lambda e: self.draw())
        self.bind("<Button-1>", self._click)

    def mark_unread(self, tab):
        if tab != self.current and self.current != "all":
            self.unread.add(tab)
            self.draw()

    def set_status(self, text, colour):
        self.status_text, self.status_colour = text, colour
        self.draw()

    def draw(self):
        self.delete("all")
        self.hit = []
        h = int(self["height"])
        x = px(6)
        for key, label in TABS:
            text = label + ("  •" if key in self.unread else "")
            width = tkfont.Font(root=self, font=self.font).measure(text) + px(22)
            active = key == self.current
            top = px(3) if active else px(6)
            r = px(6)
            fill = TAB_BG_ACTIVE if active else TAB_BG
            edge = FRAME_EDGE if active else FRAME_EDGE_DARK
            # rounded-top tab
            pts = [x, h, x, top + r, x, top, x + r, top, x + width - r, top, x + width, top,
                   x + width, top + r, x + width, h]
            self.create_polygon(pts, smooth=True, fill=fill, outline=edge)
            if active:
                self.create_line(x + 1, h - 1, x + width - 1, h - 1, fill=fill, width=2)
            colour = WOW_GOLD if active else TAB_TEXT
            cy = (top + h) / 2 + px(1)
            self.create_text(x + width / 2 + 1, cy + 1, text=text, font=self.font, fill="#000000")
            self.create_text(x + width / 2, cy, text=text, font=self.font, fill=colour)
            self.hit.append((x, x + width, key))
            x += width + px(3)
        # connection status on the right
        if self.status_text:
            w = self.winfo_width()
            self.create_text(w - px(10) + 1, h / 2 + 1, text=self.status_text, font=self.font,
                             fill="#000000", anchor="e")
            self.create_text(w - px(10), h / 2, text=self.status_text, font=self.font,
                             fill=self.status_colour, anchor="e")
        self.create_line(0, h - 1, self.winfo_width(), h - 1, fill=FRAME_EDGE_DARK)
        # redraw the active tab's bottom so it opens into the chat box
        for x0, x1, key in self.hit:
            if key == self.current:
                self.create_line(x0 + 1, h - 1, x1, h - 1, fill=TAB_BG_ACTIVE, width=2)

    def _click(self, event):
        for x0, x1, key in self.hit:
            if x0 <= event.x <= x1:
                self.current = key
                self.unread.discard(key)
                self.draw()
                self.on_select(key)
                return


class ChatBox(tk.Canvas):
    """The chat lines, drawn the way the game draws them: one colour per line
    and a 1-pixel black drop shadow."""

    MAX_MESSAGES = 300

    def __init__(self, parent, font, small_font):
        super().__init__(parent, bg=TAB_BG_ACTIVE, highlightthickness=0, yscrollincrement=px(18))
        self.font, self.small_font = font, small_font
        self.messages = []     # (tab, [(text, colour, font, indent)])
        self.filter = "all"
        self.bottom = 0
        self.width_now = 0
        self.bind("<Configure>", self._on_resize)
        self.bind_all("<MouseWheel>", self._on_wheel, add="+")
        self.bind("<Button-4>", lambda e: self.yview_scroll(-1, "units"))
        self.bind("<Button-5>", lambda e: self.yview_scroll(1, "units"))

    def add(self, tab, lines):
        at_end = self.yview()[1] > 0.98
        self.messages.append((tab, lines))
        if len(self.messages) > self.MAX_MESSAGES:
            self.messages = self.messages[-self.MAX_MESSAGES:]
            self._relayout()
        elif self._visible(tab):
            self._draw(lines)
            self._update_region()
        if at_end:
            self.yview_moveto(1.0)

    def set_filter(self, tab):
        self.filter = tab
        self._relayout()
        self.yview_moveto(1.0)

    def _visible(self, tab):
        return self.filter == "all" or tab in (self.filter, "system")

    def _draw(self, lines):
        w = max(self.width_now, 200)
        left = px(10)
        y = self.bottom
        for text, colour, font, indent in lines:
            x = left + indent
            width = w - x - px(10)
            self.create_text(x + 1, y + 1, text=text, font=font, fill="#000000", anchor="nw",
                             width=width, tags="msg")
            item = self.create_text(x, y, text=text, font=font, fill=colour, anchor="nw",
                                    width=width, tags="msg")
            y = self.bbox(item)[3] + px(1)
        self.bottom = y + px(5)

    def _relayout(self):
        self.delete("msg")
        self.bottom = px(6)
        for tab, lines in self.messages:
            if self._visible(tab):
                self._draw(lines)
        self._update_region()

    def _update_region(self):
        self.configure(scrollregion=(0, 0, self.width_now,
                                     max(self.bottom + px(4), self.winfo_height())))

    def _on_resize(self, event):
        if event.width != self.width_now:
            self.width_now = event.width
            self._relayout()
        self._update_region()
        self.yview_moveto(1.0)

    def _on_wheel(self, event):
        if str(event.widget).startswith(str(self)):
            self.yview_scroll(-1 if event.delta > 0 else 1, "units")


class TooltipFrame(tk.Frame):
    """A dark box with a thin silver edge, like the game's tooltips."""

    def __init__(self, parent, **kw):
        outer = tk.Frame(parent, bg=FRAME_EDGE, padx=1, pady=1)
        self.outer = outer
        inner = tk.Frame(outer, bg=FRAME_EDGE_DARK, padx=1, pady=1)
        inner.pack(fill="both", expand=True)
        super().__init__(inner, bg=FRAME_BG, **kw)
        super().pack(fill="both", expand=True)

    def place_in(self, **pack_options):
        self.outer.pack(**pack_options)
