# connector.py
from js import window
from pyodide.ffi import create_proxy
import traceback, json

import importlib
import sys  # needed earlier for module registration

ACTIVE_TEXTINPUT = None  # utilisé pour recevoir les frappes clavier
ACTIVE_SLIDER = None  # slider actuellement en cours de « drag »

# --- Base widget ---
class WidgetLite:
    def __init__(self, **kwargs):
        self.x = kwargs.get('x', 0)
        self.y = kwargs.get('y', 0)
        self.size = kwargs.get('size', (100, 30))
        # Layout hints (Kivy style, optional)
        self.size_hint_x = kwargs.get('size_hint_x', None)
        self.size_hint_y = kwargs.get('size_hint_y', None)
        self.spacing = kwargs.get('spacing', 0)
        # Generic transparency like Kivy's `opacity` (0‒1 float)
        self.opacity = kwargs.get('opacity', 1.0)
        self.width = self.size[0]
        self.height = self.size[1]
        self.children = []
        self._bindings = {}
    # ------------------------------------------------------------------
    #  Notify `bind()` listeners when an attribute value changes.
    # ------------------------------------------------------------------
    def __setattr__(self, name, value):
        """
        Extended setattr that preserves normal assignment semantics
        *and* triggers callbacks registered via ``bind(attr=callback)``.

        This keeps the syntax ``widget.bind(active=fn)`` working for
        arbitrary properties (e.g. Checkbox → `active`) just like in
        real Kivy, without requiring widgets to manually call bound
        functions every time they mutate their own attributes.
        """
        # Previous value (may be missing during __init__)
        old_val = self.__dict__.get(name, None)

        # Standard attribute assignment
        super().__setattr__(name, value)

        # Fire callbacks only when the attribute really changed
        if (name in getattr(self, "_bindings", {})) and (old_val != value):
            for cb in self._bindings.get(name, []):
                try:
                    cb(self, value)
                except Exception:
                    # Silently ignore callback errors to avoid breaking the draw loop
                    pass

    def add_widget(self, widget): self.children.append(widget)
    def remove_widget(self, widget): self.children.remove(widget)
    def clear_widgets(self):
        """Remove all child widgets (Kivy compatibility)."""
        self.children.clear()

    def bind(self, **kwargs):
        """Register callbacks for attribute changes (simplified)."""
        for attr, callback in kwargs.items():
            if not callable(callback):
                continue
            self._bindings.setdefault(attr, []).append(callback)
        # Return a noop object to mimic Kivy's Binding reference
        return lambda *a, **k: None

    def setter(self, attr_name):
        """Return a simple setter function (Kivy compatibility)."""
        def _set(instance, value):
            setattr(self, attr_name, value)
            if attr_name == 'size' and isinstance(value, (tuple, list)) and len(value) == 2:
                self._update_scalar_sizes()
            elif attr_name == 'width':
                self.size = (value, self.size[1]);
            elif attr_name == 'height':
                self.size = (self.size[0], value);
            # Notify bound callbacks if any
            for cb in self._bindings.get(attr_name, []):
                try:
                    cb(instance, value)
                except Exception:
                    pass
        return _set
    # keep scalar attributes synced
    def _update_scalar_sizes(self):
        self.width, self.height = self.size
    def on_touch_down(self, touch):
        # Parcourt les enfants en sens inverse pour gérer le z‑order implicite
        for child in reversed(self.children):
            if hasattr(child, 'on_touch_down') and child.on_touch_down(touch):
                return True  # événement consommé
        return False
    def draw(self):
        """Dessine récursivement en ignorant les objets sans .draw(),
        et loggue les erreurs plutôt que de casser la boucle JS."""
        for child in self.children:
            if not isinstance(child, WidgetLite):
                continue
            draw_fn = getattr(child, "draw", None)
            if callable(draw_fn):
                try:
                    draw_fn()
                except Exception as exc:
                    from js import console
                    console.error(f"Draw error in child {child!r}: {exc}")

# Alias pour compatibilité Kivy
class Widget(WidgetLite):
    """Alias minimal pour `kivy.uix.widget.Widget`."""
    pass

# --- Primitive drawings ---

COLOR_MAP = {
    'primary':'#6200EE', 'accent':'#03DAC6', 'error':'#B00020',
    'white':'#FFFFFF','black':'#000000','gray':'#9E9E9E',
    'red':'crimson','green':'seagreen','blue':'steelblue'
}

# --- Simple fallback for a few Material‑Design icons ----------------------
ICON_MAP = {
    "close": "\u2715",   # ×
    "add":   "\u2795",   # ➕
    "cog":   "\u2699",   # ⚙
    "star":  "\u2605",   # ★
}

def set_fill(color): ctx.fillStyle = COLOR_MAP.get(color, color)

def set_stroke(color): ctx.strokeStyle = COLOR_MAP.get(color, color)

# ------------------------------------------------------------
#  Kivy helper: dp() — density-independent pixels (simplifié)
# ------------------------------------------------------------
from math import ceil as _ceil_dp

def dp(value):
    """Convertit une valeur « dp » en pixels (calcul grossier)."""
    return int(_ceil_dp(float(value)))

# Ensure top‑level "kivy" package exists so `import kivy` succeeds
import types
import sys
kivy = types.ModuleType('kivy')
sys.modules['kivy'] = kivy

# Register kivy.metrics module with dp helper
kivy_metrics = types.ModuleType('kivy.metrics')
kivy_metrics.dp = dp
sys.modules['kivy.metrics'] = kivy_metrics
# Expose as attribute of top‑level kivy
setattr(kivy, 'metrics', kivy_metrics)
    
class StringProperty:
    def __init__(self, default=""):
        self.value = default
    def __get__(self, instance, owner):
        return self.value
    def __set__(self, instance, value):
        self.value = str(value)
        
class Popup(WidgetLite):
    """Popup minimaliste."""
    def __init__(self, title="", content=None, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.content = content or WidgetLite()
        self.opened = False
    def open(self):    self.opened = True
    def dismiss(self): self.opened = False
    def draw(self):
        if self.opened:
            w, h = 300, 200
            x = (window.innerWidth - w) / 2
            y = (window.innerHeight - h) / 2
            set_fill('white'); ctx.fillRect(x, y, w, h)
            ctx.font = '18px sans-serif'; set_fill('black')
            ctx.fillText(self.title, x + 10, y + 30)
            # contenu
            self.content.x, self.content.y = x + 10, y + 50
            if hasattr(self.content, 'draw') and callable(self.content.draw):
                self.content.draw()
        super().draw()
        
        
class MDDropdownMenu(WidgetLite):
    def __init__(self, caller=None, items=None, width_mult=4, **kwargs):
        super().__init__(**kwargs)
        self.caller = caller
        self.items = items or []
        self.opened = False
    def open(self):    self.opened = True
    def dismiss(self): self.opened = False
    def draw(self):
        if self.opened:
            for i, item in enumerate(self.items):
                text = item.get('text', '')
                ctx.font = '14px sans-serif'; set_fill('black')
                ctx.fillText(text, self.x + 10, self.y + 20 + i*18)
        super().draw()

# --- Labels ---
class Label(WidgetLite):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.text = kwargs.get('text','')
        self.font = kwargs.get('font','16px sans-serif')
        self.color = kwargs.get('color','black')
    def draw(self):
        ctx.font = self.font
        set_fill(self.color)
        ctx.fillText(self.text, self.x, self.y + self.size[1])
        super().draw()

# --- Buttons ---
class Button(WidgetLite):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.text = kwargs.get('text', 'Button')
        # accept both on_press and on_release (KivyMD often uses on_release)
        self.on_press = kwargs.get('on_press') or kwargs.get('on_release', None)
        self.on_release = kwargs.get('on_release', None)
        self.bg_color = kwargs.get('bg_color','gray')
        self.text_color = kwargs.get('text_color','white')
        self.radius = kwargs.get('radius',5)
    def draw(self):
        ctx.save()
        # Apply widget‑level opacity if different from 1
        if hasattr(self, "opacity"):
            ctx.globalAlpha = max(0, min(1, self.opacity))
        # background
        set_fill(self.bg_color)
        ctx.beginPath()
        ctx.roundRect(self.x, self.y, self.size[0], self.size[1], self.radius)
        ctx.fill()
        ctx.closePath()

        # choose a font size that fits horizontally
        font_size = 16
        ctx.font = f"{font_size}px sans-serif"
        tw = ctx.measureText(self.text).width
        padding = 10
        while tw + padding * 2 > self.size[0] and font_size > 8:
            font_size -= 1
            ctx.font = f"{font_size}px sans-serif"
            tw = ctx.measureText(self.text).width

        # clip text so it never spills vertically
        ctx.save()
        ctx.beginPath()
        ctx.roundRect(self.x + padding, self.y + 2, self.size[0] - padding * 2, self.size[1] - 4, self.radius)
        ctx.clip()
        # draw text
        set_fill(self.text_color)
        tx = self.x + (self.size[0] - tw) / 2
        ty = self.y + (self.size[1] + font_size / 2) / 2
        ctx.fillText(self.text, tx, ty)
        ctx.restore()
        ctx.restore()
        super().draw()
    def on_touch_down(self, touch):
        x, y = touch.clientX, touch.clientY
        if self.x <= x <= self.x + self.size[0] and self.y <= y <= self.y + self.size[1]:
            if callable(self.on_press):
                self.on_press()
            if callable(self.on_release) and self.on_release is not self.on_press:
                self.on_release()
            # Trigger callbacks registered via .bind()
            for cb in self._bindings.get('on_press', []):
                try:
                    cb(self)
                except Exception:
                    pass
            for cb in self._bindings.get('on_release', []):
                try:
                    cb(self)
                except Exception:
                    pass
            return True
        return super().on_touch_down(touch)

# --- TextInput ---
class TextInput(WidgetLite):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.text = kwargs.get('text', '')
        self.font = '16px sans-serif'
        self.color = kwargs.get('color', 'black')
        self.bg_color = kwargs.get('bg_color', 'white')
        self.cursor_color = 'black'
        self.focused = False
    def draw(self):
        # fond
        set_fill(self.bg_color)
        ctx.fillRect(self.x, self.y, self.size[0], self.size[1])
        # texte
        ctx.font = self.font
        set_fill(self.color)
        ctx.fillText(self.text, self.x + 5, self.y + self.size[1] - 8)
        # curseur
        if self.focused:
            tw = ctx.measureText(self.text).width
            cursor_x = self.x + 5 + tw + 1
            set_fill(self.cursor_color)
            ctx.fillRect(cursor_x, self.y + 4, 1, self.size[1] - 8)
        super().draw()
    def on_touch_down(self, touch):
        global ACTIVE_TEXTINPUT
        x, y = touch.clientX, touch.clientY
        inside = self.x <= x <= self.x + self.size[0] and self.y <= y <= self.y + self.size[1]
        self.focused = inside
        # mettre à jour le pointeur global
        if inside:
            ACTIVE_TEXTINPUT = self
            return True
        return super().on_touch_down(touch)

# --- Slider ---
class Slider(WidgetLite):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.min = kwargs.get('min',0)
        self.max = kwargs.get('max',100)
        self.value = kwargs.get('value',(self.min+self.max)/2)
        self.on_value = kwargs.get('on_value', lambda v: None)
    def _set_value_from_x(self, x):
        self.value = self.min + (x - self.x) / self.size[0] * (self.max - self.min)
        self.on_value(self.value)
    def draw(self):
        # track
        set_fill('gray'); ctx.fillRect(self.x, self.y+self.size[1]/3, self.size[0], self.size[1]/3)
        # thumb
        pos = self.x + (self.value-self.min)/(self.max-self.min)*self.size[0]
        set_fill('primary'); ctx.beginPath(); ctx.arc(pos,self.y+self.size[1]/2,self.size[1]/2,0,2*3.14); ctx.fill(); ctx.closePath()
        super().draw()
    def on_touch_down(self, touch):
        global ACTIVE_SLIDER
        x, y = touch.clientX, touch.clientY
        inside = (self.x <= x <= self.x + self.size[0] and
                  self.y <= y <= self.y + self.size[1])
        if inside:
            ACTIVE_SLIDER = self
            self._set_value_from_x(x)
            return True
        return super().on_touch_down(touch)

# --- Switch ---
class Switch(WidgetLite):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.active = kwargs.get('active',False)
        self.on_active = kwargs.get('on_active', lambda a: None)
    def draw(self):
        set_fill('gray' if not self.active else 'primary')
        ctx.fillRect(self.x,self.y,self.size[0],self.size[1])
        set_fill('white'); r = self.size[1]-4
        cx = self.x+ (self.size[0]-r-2 if self.active else 2)
        ctx.beginPath(); ctx.arc(cx,self.y+2+r/2,r/2,0,2*3.14); ctx.fill(); ctx.closePath()
        super().draw()
    def on_touch_down(self, touch):
        x,y=touch.clientX,touch.clientY
        if self.x<=x<=self.x+self.size[0] and self.y<=y<=self.y+self.size[1]:
            self.active = not self.active; self.on_active(self.active)
        super().on_touch_down(touch)

# --- ProgressBar ---
class ProgressBar(WidgetLite):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.value = kwargs.get('value',0)
        self.max = kwargs.get('max',100)
    def draw(self):
        set_fill('gray'); ctx.fillRect(self.x,self.y,self.size[0],self.size[1])
        set_fill('accent'); ctx.fillRect(self.x,self.y,self.size[0]*self.value/self.max,self.size[1])
        super().draw()

# --- Layouts ---
class BoxLayout(WidgetLite):
    def __init__(self, orientation='horizontal', spacing=5, **kwargs):
        super().__init__(**kwargs)
        self.orientation, self.spacing = orientation, spacing
    def draw(self):
        """
        Improved draw that honours size_hint_x / size_hint_y like real Kivy.

        * In an **horizontal** layout we share the parent width between children
          following each child's ``size_hint_x`` (``None`` → keep current width).
        * In a **vertical** layout we do the same with ``size_hint_y`` and the
          parent height.

        Widgets without size hints keep their explicit ``size``.  After sizing,
        children are positioned sequentially with the configured ``spacing``.
        """
        parent_w, parent_h = self.size

        if self.orientation == 'horizontal':
            total_hint = sum((c.size_hint_x or 0) for c in self.children)
        else:
            total_hint = sum((c.size_hint_y or 0) for c in self.children)

        # Avoid division by zero
        total_hint = total_hint if total_hint else 1

        offset = 0
        for c in self.children:
            if not isinstance(c, WidgetLite):
                continue  # ignore stray objects

            if self.orientation == 'horizontal':
                # Width allocation
                if c.size_hint_x is not None:
                    share = (c.size_hint_x or 0) / total_hint
                    c.size = (parent_w * share, c.size[1])
                    # Always take full cross-axis (height)
                    c.size = (c.size[0], parent_h)
                    c._update_scalar_sizes()
                else:
                    # Even if no hint, still take full cross-axis
                    c.size = (c.size[0], parent_h)
                    c._update_scalar_sizes()
                c.x, c.y = self.x + offset, self.y
                offset += c.size[0] + self.spacing
            else:  # vertical
                if c.size_hint_y is not None:
                    share = (c.size_hint_y or 0) / total_hint
                    c.size = (c.size[0], parent_h * share)
                    # Always take full cross-axis (width)
                    c.size = (parent_w, c.size[1])
                    c._update_scalar_sizes()
                else:
                    # Even if no hint, still take full cross-axis
                    c.size = (parent_w, c.size[1])
                    c._update_scalar_sizes()
                c.x, c.y = self.x, self.y + offset
                offset += c.size[1] + self.spacing

            # Safe draw
            draw_child = getattr(c, 'draw', None)
            if callable(draw_child):
                try:
                    draw_child()
                except Exception as exc:
                    from js import console
                    console.error('Draw error (BoxLayout child):', exc)

class GridLayout(BoxLayout):
    def __init__(self, cols=2, **kwargs): super().__init__(**kwargs); self.cols=cols
    def draw(self):
        w, h = self.size
        rows = (len(self.children) + self.cols - 1) // self.cols or 1
        cw = w / self.cols
        ch = h / rows
        # Auto‑grow vertically if height is zero so children become visible
        if self.size[1] == 0:
            self.size = (self.size[0] or cw * self.cols, rows * ch)
        for i in range(len(self.children)):
            c = self.children[i]
            if not isinstance(c, WidgetLite):
                continue
            row, col = divmod(i, self.cols)
            c.x = self.x + col * cw
            c.y = self.y + row * ch
            c.size = (cw, ch)
            if hasattr(c, 'draw') and callable(c.draw):
                try:
                    c.draw()
                except Exception as exc:
                    from js import console
                    console.error('Draw error (GridLayout child):', exc)

# --- Screen & Manager ---
class Screen(WidgetLite):
    def __init__(self, name, **kwargs): super().__init__(**kwargs); self.name=name

# Replacement ScreenManager implementation

class ScreenManager:
    def __init__(self, transition=None, **kwargs):
        # Accepts optional 'transition' and other kwargs for compatibility
        self.transition = transition
        self.screens = {}
        self.current = None
    def add_widget(self, s):
        self.screens[s.name] = s
        if self.current is None:
            self.current = s
    def switch_to(self, name):
        self.current = self.screens.get(name, self.current)
    def draw(self):
        if self.current:
            self.current.draw()
    def on_touch_down(self, t):
        if self.current:
            return self.current.on_touch_down(t)
        return False

# Ensure the stub with updated signature is exposed in the faux module
if 'kivy.uix.screenmanager' in sys.modules:
    sys.modules['kivy.uix.screenmanager'].ScreenManager = ScreenManager

#
# ------------------------------------------------------------
#  Theme system (theme_cls) -- very light implementation
# ------------------------------------------------------------

class _ThemeStub:
    """Mimic kivymd.theming.ThemeManager enough for demos."""
    def __init__(self):
        self._primary_palette = 'Blue'
        self._accent_palette = 'Amber'
        self._update_maps()
        self.theme_style = 'Light'  # or 'Dark'
    # --- helpers ---
    def _update_maps(self):
        # Map web colors; default to COLOR_MAP lookup or literal css string
        COLOR_MAP['primary'] = COLOR_MAP.get(self._primary_palette.lower(), self._primary_palette.lower())
        COLOR_MAP['accent']  = COLOR_MAP.get(self._accent_palette.lower(),  self._accent_palette.lower())
    # --- properties ---
    @property
    def primary_palette(self):
        return self._primary_palette
    @primary_palette.setter
    def primary_palette(self, val):
        self._primary_palette = val.capitalize()
        self._update_maps()
    @property
    def accent_palette(self):
        return self._accent_palette
    @accent_palette.setter
    def accent_palette(self, val):
        self._accent_palette = val.capitalize()
        self._update_maps()
    # Convenience colors
    @property
    def primary_color(self):
        return COLOR_MAP['primary']
    @property
    def accent_color(self):
        return COLOR_MAP['accent']

# --- KivyMD stubs ---
class MDCard(WidgetLite):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.elevation = kwargs.get('elevation', 8)
    def draw(self):
        ctx.save()
        # Ombre portée pour simuler l'élévation
        ctx.shadowColor = 'rgba(0,0,0,0.25)'
        ctx.shadowBlur = self.elevation
        ctx.shadowOffsetX = 0
        ctx.shadowOffsetY = self.elevation / 2
        set_fill('white')
        ctx.fillRect(self.x, self.y, self.size[0], self.size[1])
        ctx.restore()
        super().draw()

class MDToolbar(WidgetLite):
    def __init__(self, **kwargs): super().__init__(**kwargs); self.title=kwargs.get('title','')
    def draw(self):
        set_fill('primary'); ctx.fillRect(self.x,self.y,self.size[0],50)
        ctx.font='20px sans-serif'; set_fill('white'); ctx.fillText(self.title,self.x+10,self.y+30)
        super().draw()
        
class Rectangle(WidgetLite):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.color = COLOR_MAP.get(kwargs.get('color'), 'gray')

    def draw(self):
        ctx.fillStyle = self.color
        ctx.fillRect(self.x, self.y, self.size[0], self.size[1])
        super().draw()

# --- Graphics primitive stubs (Color, Line, Ellipse) ---
class Color:
    """Simplified stand‑in for `kivy.graphics.Color`. Accepts RGBA floats 0‑1."""
    def __init__(self, r=1, g=1, b=1, a=1):
        self.r, self.g, self.b, self.a = r, g, b, a
    def to_css(self):
        return f"rgba({int(self.r*255)},{int(self.g*255)},{int(self.b*255)},{self.a})"

class Line(WidgetLite):
    def __init__(self, points, width=1, color='black', **kwargs):
        super().__init__(**kwargs)
        self.points = points  # [x1,y1,x2,y2,...]
        self.width = width
        self.color = color if isinstance(color, str) else COLOR_MAP.get(color, 'black')
    def draw(self):
        set_stroke(self.color)
        ctx.lineWidth = self.width
        ctx.beginPath()
        ctx.moveTo(self.points[0], self.points[1])
        for i in range(2, len(self.points), 2):
            ctx.lineTo(self.points[i], self.points[i+1])
        ctx.stroke()
        super().draw()

class Ellipse(WidgetLite):
    def __init__(self, pos, size, color='black', **kwargs):
        super().__init__(**kwargs)
        self.pos = pos  # (x,y)
        self.size = size  # (w,h)
        self.color = color if isinstance(color, str) else COLOR_MAP.get(color, 'black')
    def draw(self):
        x, y = self.pos
        w, h = self.size
        set_fill(self.color)
        ctx.beginPath()
        ctx.ellipse(x + w/2, y + h/2, w/2, h/2, 0, 0, 2*3.14)
        ctx.fill()
        super().draw()

class MDIconButton(Button):
    """
    Lightweight replacement for KivyMD's MDIconButton.

    • Accepts ``icon="close"`` (or any key in ICON_MAP) or plain text.
    • Defaults to a 36×36‑dp square button.
    """
    def __init__(self, **kwargs):
        icon_name = kwargs.pop("icon", kwargs.get("text", ""))
        glyph = ICON_MAP.get(icon_name, icon_name[:1] if icon_name else "?")
        kwargs["text"] = glyph
        kwargs.setdefault("size", (dp(36), dp(36)))
        kwargs.setdefault("bg_color", "white")
        kwargs.setdefault("text_color", "black")
        super().__init__(**kwargs)
class MDRaisedButton(Button): pass
class MDCheckbox(Switch): pass
class MDSlider(Slider): pass
class MDProgressBar(ProgressBar): pass


# ----- sous-packages vides pour satisfaire l'import -----
kivy_uix = types.ModuleType('kivy.uix')
sys.modules['kivy.uix'] = kivy_uix
setattr(kivy, 'uix', kivy_uix)
# Mark as package so sub‑modules can be imported
kivy_uix.__path__ = []

kivy_core = types.ModuleType('kivy.core')
sys.modules['kivy.core'] = kivy_core
setattr(kivy, 'core', kivy_core)

kivy_uix_widget = types.ModuleType('kivy.uix.widget')
kivy_uix_widget = types.ModuleType('kivy.uix.widget')
kivy_uix_widget.Widget = Widget
sys.modules['kivy.uix.widget'] = kivy_uix_widget

kivy_graphics = types.ModuleType('kivy.graphics')
kivy_graphics.Color = Color
kivy_graphics.Line = Line
kivy_graphics.Ellipse = Ellipse
sys.modules['kivy.graphics'] = kivy_graphics




# ============================================================
#  Additional stubs for extended Kivy / KivyMD compatibility
# ============================================================

# Simplified properties implementation
class ObjectProperty:
    def __init__(self, default=None):
        self.value = default
    def __get__(self, instance, owner):
        return self.value
    def __set__(self, instance, value):
        self.value = value

# Core Window stub
class _Window:
    width  = window.innerWidth
    height = window.innerHeight
    size   = (width, height)
    def bind(self, **kwargs):
        pass
Window = _Window()

# Layout & widget stubs
after_scroll_y = 0  # track scroll for ScrollView stub
class ScrollView(WidgetLite):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.scroll_y = 1
    def draw(self):
        global after_scroll_y
        ctx.save()
        ctx.beginPath()
        ctx.rect(self.x, self.y, self.size[0], self.size[1])
        ctx.clip()
        for c in self.children:
            if not isinstance(c, WidgetLite):
                continue  # ignore stray JS proxies or primitives
            c.y = self.y - (1 - self.scroll_y) * (c.height or c.size[1])
            if hasattr(c, 'draw') and callable(c.draw):
                try:
                    c.draw()
                except Exception as exc:
                    from js import console
                    console.error('Draw error (ScrollView child):', exc)
        ctx.restore()
        after_scroll_y = self.scroll_y

class Spinner(Button):
    """Very simple dropdown replacement (always shows selected text)."""
    pass

class Image(WidgetLite):
    def __init__(self, source='', **kwargs):
        super().__init__(**kwargs)
        self.source = source
    def draw(self):
        # For simplicity draw a gray rect placeholder
        set_fill('gray')
        ctx.fillRect(self.x, self.y, self.size[0], self.size[1])
        super().draw()

# KivyMD stubs
class MDFlatButton(Button):
    def __init__(self, **kwargs):
        kwargs.setdefault('bg_color', 'white')
        kwargs.setdefault('text_color', 'primary')
        super().__init__(**kwargs)
class MDLabel(Label):
    pass
class MDTextField(TextInput):
    pass
class MDDialog(WidgetLite):
    def __init__(self, title='', text='', **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.text = text
        self.opened = False
    def open(self):
        self.opened = True
    def dismiss(self):
        self.opened = False
    def draw(self):
        if self.opened:
            set_fill('white')
            ctx.fillRect(self.x, self.y, self.size[0], self.size[1])
            ctx.font = '16px sans-serif'
            set_fill('black')
            ctx.fillText(self.title, self.x + 10, self.y + 20)
            ctx.fillText(self.text,  self.x + 10, self.y + 40)
        super().draw()

class MDApp:
    """Stub KivyMD App with basic theme_cls support."""
    def __init__(self, **kwargs):
        self.theme_cls = _ThemeStub()
    def run(self):
        pass  # no‑op in browser

# Lists
class OneLineListItem(Button):
    def __init__(self, text='', **kwargs):
        super().__init__(text=text, **kwargs)
class MDList(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', spacing=2, **kwargs)

# ScreenManager FadeTransition stub
class FadeTransition:
    pass

# MDTopAppBar alias
MDTopAppBar = MDToolbar

# ------------------------------------------------------------
# Register additional faux modules so `import` works
# ------------------------------------------------------------

# kivy.core.window
kivy_core_window = types.ModuleType('kivy.core.window')
kivy_core_window.Window = Window
sys.modules['kivy.core.window'] = kivy_core_window

# kivy.properties
kivy_properties = types.ModuleType('kivy.properties')
kivy_properties.ObjectProperty = ObjectProperty
kivy_properties.StringProperty = StringProperty
sys.modules['kivy.properties'] = kivy_properties
setattr(kivy, 'properties', kivy_properties)



kivy_uix_popup = types.ModuleType('kivy.uix.popup')
kivy_uix_popup.Popup = Popup
sys.modules['kivy.uix.popup'] = kivy_uix_popup

kivymd_menu = types.ModuleType('kivymd.uix.menu')
kivymd_menu.MDDropdownMenu = MDDropdownMenu
sys.modules['kivymd.uix.menu'] = kivymd_menu

# kivy.uix.*
kivy_uix_screenmanager = types.ModuleType('kivy.uix.screenmanager')
kivy_uix_screenmanager.Screen = Screen
kivy_uix_screenmanager.ScreenManager = ScreenManager
kivy_uix_screenmanager.FadeTransition = FadeTransition
sys.modules['kivy.uix.screenmanager'] = kivy_uix_screenmanager


kivy_uix_boxlayout = types.ModuleType('kivy.uix.boxlayout')
kivy_uix_boxlayout.BoxLayout = BoxLayout
sys.modules['kivy.uix.boxlayout'] = kivy_uix_boxlayout

# kivy.uix.gridlayout
kivy_uix_gridlayout = types.ModuleType('kivy.uix.gridlayout')
kivy_uix_gridlayout.GridLayout = GridLayout
sys.modules['kivy.uix.gridlayout'] = kivy_uix_gridlayout
setattr(kivy_uix, 'gridlayout', kivy_uix_gridlayout)

kivy_uix_scrollview = types.ModuleType('kivy.uix.scrollview')
kivy_uix_scrollview.ScrollView = ScrollView
sys.modules['kivy.uix.scrollview'] = kivy_uix_scrollview

kivy_uix_spinner = types.ModuleType('kivy.uix.spinner')
kivy_uix_spinner.Spinner = Spinner
sys.modules['kivy.uix.spinner'] = kivy_uix_spinner


kivy_uix_image = types.ModuleType('kivy.uix.image')
kivy_uix_image.Image = Image
sys.modules['kivy.uix.image'] = kivy_uix_image

# kivy.uix.textinput
kivy_uix_textinput = types.ModuleType('kivy.uix.textinput')
kivy_uix_textinput.TextInput = TextInput
sys.modules['kivy.uix.textinput'] = kivy_uix_textinput
setattr(kivy_uix, 'textinput', kivy_uix_textinput)

# kivymd.* modules
kivymd_app = types.ModuleType('kivymd.app')
kivymd_app.MDApp = MDApp
sys.modules['kivymd.app'] = kivymd_app

kivymd_toolbar = types.ModuleType('kivymd.uix.toolbar')
kivymd_toolbar.MDTopAppBar = MDTopAppBar
sys.modules['kivymd.uix.toolbar'] = kivymd_toolbar

kivymd_button = types.ModuleType('kivymd.uix.button')
kivymd_button.MDRaisedButton = MDRaisedButton
kivymd_button.MDFlatButton = MDFlatButton
kivymd_button.MDIconButton = MDIconButton
sys.modules['kivymd.uix.button'] = kivymd_button

kivymd_label = types.ModuleType('kivymd.uix.label')
kivymd_label.MDLabel = MDLabel
sys.modules['kivymd.uix.label'] = kivymd_label

kivymd_dialog = types.ModuleType('kivymd.uix.dialog')
kivymd_dialog.MDDialog = MDDialog
sys.modules['kivymd.uix.dialog'] = kivymd_dialog

kivymd_textfield = types.ModuleType('kivymd.uix.textfield')
kivymd_textfield.MDTextField = MDTextField
sys.modules['kivymd.uix.textfield'] = kivymd_textfield

kivymd_list = types.ModuleType('kivymd.uix.list')
kivymd_list.MDList = MDList
kivymd_list.OneLineListItem = OneLineListItem
sys.modules['kivymd.uix.list'] = kivymd_list

kivymd_card = types.ModuleType('kivymd.uix.card')
kivymd_card.MDCard = MDCard
sys.modules['kivymd.uix.card'] = kivymd_card


setattr(kivy_uix, 'widget', kivy_uix_widget)
setattr(kivy_uix, 'boxlayout', kivy_uix_boxlayout)
setattr(kivy_uix, 'spinner', kivy_uix_spinner)
setattr(kivy_uix, 'image',    kivy_uix_image)
setattr(kivy_uix, 'screenmanager', kivy_uix_screenmanager)
setattr(kivy_uix, 'boxlayout', kivy_uix_boxlayout)
setattr(kivy_uix, 'scrollview', kivy_uix_scrollview)

# --- Launcher ---
def run_kivy_app(app_module, app_class):
    mod = importlib.import_module(app_module)
    AppClass = getattr(mod, app_class)
    app = AppClass(); root = getattr(app,'root',None) or app.build(); app.root=root
    # Ensure root takes the full browser viewport
    root.size = (window.innerWidth, window.innerHeight)
    if hasattr(root, '_update_scalar_sizes'):
        root._update_scalar_sizes()

    # Keep root sized on window resize
    def _on_resize(evt):
        root.size = (window.innerWidth, window.innerHeight)
        if hasattr(root, '_update_scalar_sizes'):
            root._update_scalar_sizes()
    window.addEventListener('resize', create_proxy(_on_resize))
    manager = getattr(app,'screen_manager',None)
    handler = create_proxy(lambda e: (manager or root).on_touch_down(e))
    window.addEventListener('mousedown',handler)
    def loop(_):
        # Refresh root size each frame (in case of dynamic changes)
        root.size = (window.innerWidth, window.innerHeight)
        if hasattr(root, '_update_scalar_sizes'):
            root._update_scalar_sizes()
        ctx.clearRect(0,0,window.innerWidth,window.innerHeight)
        try:
            (manager or root).draw()
#        except Exception as exc:
#            from js import console
#            console.error("Draw cycle error:", exc);
        except Exception as exc:
            from js import console
            tb = traceback.format_exc()
            console.error("Draw cycle error:", exc, "\n", tb)
        window.requestAnimationFrame(create_proxy(loop))
    # Gestion clavier pour TextInput
    def key_handler(evt):
        if ACTIVE_TEXTINPUT is None:
            return
        key = evt.key
        if key == 'Backspace':
            ACTIVE_TEXTINPUT.text = ACTIVE_TEXTINPUT.text[:-1]
        elif len(key) == 1:
            ACTIVE_TEXTINPUT.text += key
    window.addEventListener('keydown', create_proxy(key_handler))
    # Drag support pour Slider
    def mouse_move(evt):
        if ACTIVE_SLIDER is not None:
            ACTIVE_SLIDER._set_value_from_x(evt.clientX)
    def mouse_up(evt):
        global ACTIVE_SLIDER
        ACTIVE_SLIDER = None
    window.addEventListener('mousemove', create_proxy(mouse_move))
    window.addEventListener('mouseup', create_proxy(mouse_up))
    window.requestAnimationFrame(create_proxy(loop))
