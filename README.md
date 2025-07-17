WebKivy

<!-- GIF + lien vers YouTube (rendu partout) -->
[![WebKivy demo](WebKivy_Example_presentation.gif)](https://youtu.be/Ng7Pyy2f_kk)



WebKivy is a minimalist wrapper that allows you to run Kivy/KivyMD applications directly in a browser using Pyodide.

⸻

Summary
1. Why?
2. How it works
3. Quick Start
4. Repository Structure
5. Compatibility and Limitations
6. Roadmap
7. Contribute
8. License

⸻

Why?
• No installation: Your Kivy app becomes a simple HTML + JS bundle.
• Instant demo: Share a link or a .zip file, and the public can test it immediately.
• Isolation: Python code runs in Pyodide's WebAssembly sandbox; no risk to the OS or system environment.
• Learning: Ideal for workshops or MOOCs where learners only have a browser at their disposal.

⸻

How it works
1. Pyodide is loaded client-side (via a CDN).
2. The connector.py file reconstructs a subset of Kivy.
• Base widgets: Label, Button, Slider, TextInput, ScreenManager, etc.
• Lightweight KivyMD overlay: MDToolbar, MDRaisedButton, MDCard, etc.
• HTML5 Canvas (<canvas id="kivy-canvas">) for 2D rendering.
3. Your code imports these classes as if it were running the real library:

from connector import BoxLayout, Label, Slider

4. The JavaScript rendering loop calls the widgets' draw() method each frame, handles events (on_touch_down, keyboard, resize, etc.), and notifies the bindings (widget.bind(...)).

⸻

## Quick Start:

git clone https://github.com/youraccount/WebKivy.git
cd WebKivy
# launches a small server – required for ES + Pyodide imports
python3 -m http.server 8000

Open http://localhost:8000 then select/edit kivy_app.py to code your interface.

# kivy_app.py
from connector import Button, BoxLayout, run_kivy_app

class HelloApp:
def build(self):
root = BoxLayout(orientation='vertical', size=(500,300))
root.add_widget(Button(text="Click me", on_press=lambda: print("🎉")))
return root

if __name__ == '__main__':
run_kivy_app(__name__, 'HelloApp')

Save, refresh → your app is running in the browser!

⸻

## Repository structure:

File / folder Role
index.html Home page, loads main.js and prepares the <canvas>
main.js Initializes Pyodide, loads connector.py then kivy_app.py
connector.py Kivy wrapper: stub widgets, layout, canvas, bindings, etc.
kivy_app.py Your application; you're free to create several
examples/ Recipes, KivyMD mini-demos, sliders, popups, ScreenManager, etc.
assets/ Icons, test images, etc. (loaded via Image(source=...))

⸻

## Compatibility and Limitations:

Feature Support Notes
Basic Kivy Widgets ✓ Partial Position/Size: simplified x, y, size, size_hint
Canvas (Line, Ellipse, etc.) ✓ Minimal Solid colors, no advanced transformations
KivyMD ✓ Light Buttons, Toolbar, Card, Dialog, Checkbox, Slider, etc.
Animations / Clock ✕ Not implemented (to be planned)
Files / Storage ✕ No disk access: use localStorage, IPFS, etc.
Multitouch / Gestures ✕ Mouse/single touch support only
OpenGL / Shaders ✕ Incompatible with WebAssembly + Canvas2D

⸻

## Roadmap:
• Clock.schedule_once / Animation support
• Complex Widgets (Tab, RecycleView)
• Automatic dark/light theme
• WebSockets bridge to communicate with real Python backends
• Offline generator (Pyodide bundle + app in a self-contained .html)

⸻

## Contribute:
1. Fork then git clone.
2. Create a branch: git checkout -b feat/my-feature.
3. Code; feel free to add an example in examples/.
4. Open a Pull Request

Thanks!

Bugs? Open an Issue with a minimal, reproducible script + console capture.
