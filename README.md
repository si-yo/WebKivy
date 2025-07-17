WebKivy

WebKivy est un wrapper minimaliste qui permet d’exécuter des applications Kivy/KivyMD directement dans un navigateur grâce à Pyodide.

⸻

Sommaire
	1.	Pourquoi ?
	2.	Fonctionnement
	3.	Prise en main rapide
	4.	Structure du dépôt
	5.	Compatibilité et limitations
	6.	Roadmap
	7.	Contribuer
	8.	Licence

⸻

Pourquoi ?
	•	Pas d’installation : votre appli Kivy devient un simple bundle HTML + JS.
	•	Démo instantanée : partagez un lien ou un fichier .zip, le public teste immédiatement.
	•	Isolation : le code Python tourne dans le sandbox WebAssembly de Pyodide ; pas de risque pour l’OS ou l’environnement système.
	•	Apprentissage : idéal pour des ateliers ou des MOOC où les apprenants n’ont qu’un navigateur à disposition.

⸻

Fonctionnement
	1.	Pyodide est chargé côté client (via un CDN).
	2.	Le fichier connector.py reconstitue un sous-ensemble de Kivy.
	•	Widgets de base : Label, Button, Slider, TextInput, ScreenManager…
	•	Surcouche KivyMD légère : MDToolbar, MDRaisedButton, MDCard, etc.
	•	Canvas HTML5 (<canvas id="kivy-canvas">) pour le rendu 2D.
	3.	Votre code importe ces classes comme s’il exécutait la vraie librairie :

from connector import BoxLayout, Label, Slider


	4.	La boucle d’affichage JavaScript appelle chaque frame la méthode draw() des widgets, gère les events (on_touch_down, clavier, resize…) et notifie les bindings (widget.bind(...)).

⸻

Prise en main rapide

git clone https://github.com/votrecompte/WebKivy.git
cd WebKivy
# lance un petit serveur – obligatoire pour les imports ES + Pyodide
python3 -m http.server 8000

Ouvrez http://localhost:8000 puis sélectionnez / éditez kivy_app.py pour coder votre interface.

# kivy_app.py
from connector import Button, BoxLayout, run_kivy_app

class HelloApp:
    def build(self):
        root = BoxLayout(orientation='vertical', size=(500,300))
        root.add_widget(Button(text="Clique-moi", on_press=lambda: print("🎉")))
        return root

if __name__ == '__main__':
    run_kivy_app(__name__, 'HelloApp')

Enregistrez, rafraîchissez → votre appli s’exécute dans le navigateur !

⸻

Structure du dépôt

Fichier / dossier	Rôle
index.html	Page d’accueil, charge main.js et prépare le <canvas>
main.js	Initialise Pyodide, charge connector.py puis kivy_app.py
connector.py	Wrapper Kivy : stub widgets, layout, canvas, bindings…
kivy_app.py	Votre application; libre à vous d’en créer plusieurs
examples/	Recettes, mini-démos KivyMD, sliders, popup, ScreenManager…
assets/	Icônes, images de test, etc. (chargées via Image(source=...))


⸻

Compatibilité et limitations

Fonctionnalité	Support	Notes
Widgets Kivy de base	✓ partiel	Position/size : x, y, size, size_hint simplifiés
Canvas (Line, Ellipse…)	✓ minimal	Couleurs unies, pas de transformations avancées
KivyMD	✓ light	Buttons, Toolbar, Card, Dialog, Checkbox, Slider…
Animations / Clock	✕	Non implémenté (à prévoir)
Fichiers / Storage	✕	Pas d’accès disque : utiliser localStorage, IPFS…
Multitouch / Gestures	✕	Support souris/simple touch seulement
OpenGL / Shaders	✕	Incompatible WebAssembly + Canvas2D


⸻

Roadmap
	•	Support Clock.schedule_once / Animation
	•	Widgets complexes (Tab, RecycleView)
	•	Thème sombre / clair automatique
	•	Bridge WebSockets pour communiquer avec des back-ends Python réels
	•	Générateur offline (bundle Pyodide + app dans un .html auto-contenu)

⸻

Contribuer
	1.	Fork puis git clone.
	2.	Créez une branche : git checkout -b feat/ma-feature.
	3.	Codez ; n’hésitez pas à ajouter un exemple dans examples/.
	4.	Ouvrez une Pull Request
 
 Merci ! 

Bugs ? Ouvrez un Issue avec un script minimal reproductible + capture console.
