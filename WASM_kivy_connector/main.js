// main.js
// ─────────────────────────────────────────────────────────────
// IMPORTANT : ouvrez la page via http://localhost:8000 et non   //
//             pas en file://, sinon les imports seront bloqués //
// ─────────────────────────────────────────────────────────────
if (location.protocol === 'file:') {
  console.error('⚠️ Veuillez servir cette page via un petit serveur HTTP, '
               + 'ex. :  python3 -m http.server');
}

// Import ES-module de Pyodide
import { loadPyodide } from 'https://cdn.jsdelivr.net/pyodide/v0.26.0/full/pyodide.mjs';

async function main() {
  try {
    // 1) Initialiser Pyodide
    const pyodide = await loadPyodide({
      indexURL: 'https://cdn.jsdelivr.net/pyodide/v0.26.0/full/'
    });

    // 2) Exposer le <canvas> côté Python
    await pyodide.runPythonAsync(`
import js
canvas = js.document.getElementById("kivy-canvas")
canvas.width  = js.window.innerWidth
canvas.height = js.window.innerHeight
ctx = canvas.getContext("2d")
`);

    // 3) (optionnel) charger micropip pour installer d’autres wheels Pyodide
    await pyodide.loadPackage('micropip')

    // 4) Charger le connecteur Kivy-Lite et votre application
    await pyodide.runPythonAsync(await (await fetch('connector.py')).text())
      // Enregistrer le code exécuté comme module "connector"
    await pyodide.runPythonAsync(`
import types, sys, __main__
connector = types.ModuleType('connector')
connector.__dict__.update(__main__.__dict__)
sys.modules['connector'] = connector
  `)
    await pyodide.runPythonAsync(await (await fetch('kivy_app.py')).text())

  } catch (err) {
    console.error('Erreur Pyodide :', err)
  }
}

main();
