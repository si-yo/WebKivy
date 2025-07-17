# app_kivy.py
from connector import (
    Label, Button, TextInput, Slider, Switch, ProgressBar,
    BoxLayout, GridLayout, Screen, ScreenManager,
    MDCard, MDToolbar, MDIconButton, MDRaisedButton,
    MDCheckbox, MDSlider, MDProgressBar, Rectangle,
    run_kivy_app
)
from js import window

class MyKivyApp:
    def build(self):
        # --- Écran principal ---
        home = Screen(name='home')
        # Barre d’outils
        toolbar = MDToolbar(x=0, y=0, size=(window.innerWidth, 50), title='Kivy-Web Demo')
        home.add_widget(toolbar)

        # Conteneur principal
        content = BoxLayout(
            x=20, y=70,
            size=(window.innerWidth-40, 200),
            orientation='vertical', spacing=10
        )

        # Lignes de widgets
        # 1) Ligne de Label + TextInput
        row1 = BoxLayout(orientation='horizontal', spacing=10, size=(content.size[0], 30))
        lbl = Label(text='Nom :', x=0, y=0, size=(80, 30))
        txt = TextInput(text='Alice', x=0, y=0, size=(content.size[0]-100, 30))
        row1.add_widget(lbl)
        row1.add_widget(txt)

        # 2) Ligne de Slider + Label affichant la valeur
        slider_val = Label(text='50', x=0, y=0, size=(30, 30))
        def on_slider(v):
            slider_val.text = f"{int(v)}"
        sldr = Slider(x=0, y=0, size=(content.size[0]-50, 30), value=50, on_value=on_slider)
        row2 = BoxLayout(orientation='horizontal', spacing=10, size=(content.size[0], 30))
        row2.add_widget(sldr)
        row2.add_widget(slider_val)

        # 3) Ligne de Switch + ProgressBar
        def on_switch(active):
            pbar.value = 100 if active else 0
        sw = Switch(x=0, y=0, size=(50,30), active=False, on_active=on_switch)
        pbar = ProgressBar(x=60, y=0, size=(content.size[0]-60, 30), value=0)
        row3 = BoxLayout(orientation='horizontal', spacing=10, size=(content.size[0], 30))
        row3.add_widget(sw)
        row3.add_widget(pbar)

        content.add_widget(row1)
        content.add_widget(row2)
        content.add_widget(row3)
        home.add_widget(content)

        # Bouton de navigation
        btn_to_detail = MDRaisedButton(
            x=20, y=290, size=(120, 40), text='Voir détails',
            on_press=lambda: manager.switch_to('detail')
        )
        home.add_widget(btn_to_detail)

        # --- Écran Détails ---
        detail = Screen(name='detail')
        toolbar2 = MDToolbar(x=0, y=0, size=(window.innerWidth, 50), title='Détails')
        detail.add_widget(toolbar2)

        # Grille de composants KivyMD
        grid = GridLayout(
            x=20, y=70, size=(window.innerWidth-40, 200),
            cols=2
        )
#        grid.add_widget(MDCard(x=0, y=0, size=(0,0), elevation=6))
        self.ic = MDIconButton(x=0, y=0, size=(50,50), text='☆')
        self.cb = MDCheckbox(x=0, y=0, size=(30,30), active=True)
      
        self.cb.bind(active=self.ch)
        grid.add_widget(self.cb)
        grid.add_widget(self.ic)
        
#        grid.add_widget(MDSlider(x=0, y=0, size=(content.size[0], 30), value=30))
#        grid.add_widget(MDProgressBar(x=0, y=0, size=(content.size[0], 20), value=70))
        detail.add_widget(grid)

        # Bouton Retour
        btn_back = Button(
            x=20, y=290, size=(100, 40), text='← Retour',
            on_press=lambda: manager.switch_to('home')
        )
        detail.add_widget(btn_back)

        # --- ScreenManager ---
        global manager
        manager = ScreenManager()
        manager.add_widget(home)
        manager.add_widget(detail)
        return manager
        
    # Callback triggered when the checkbox state changes
    # `value` is True when the checkbox is checked, False otherwise.
    def ch(self, inst, value):
        # Affiche/masque l’icône en fonction de l’état du checkbox
        self.ic.opacity = 1 if value else 0

def _auto_run(app_class_name='MainApp'):
    try:                # Pyodide ?
        import js
        run_kivy_app(__name__, app_class_name)
    except ImportError: # Bureau natif
        globals()[app_class_name]().run()

if __name__ == '__main__':
    _auto_run('MyKivyApp')
