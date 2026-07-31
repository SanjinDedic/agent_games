import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { viteStaticCopy } from 'vite-plugin-static-copy';

// Pyodide is self-hosted (schools may block CDNs): the runtime assets are
// copied out of the npm package to /pyodide/, served by the dev server and
// emitted into build/pyodide/ on build. The exercise worker loads
// /pyodide/pyodide.mjs at runtime — nothing imports the npm package directly,
// so all five files must stay version-matched via the pyodide devDependency.
const pyodideAssets = [
  {
    src: 'node_modules/pyodide/{pyodide.mjs,pyodide.asm.mjs,pyodide.asm.wasm,python_stdlib.zip,pyodide-lock.json}',
    dest: 'pyodide',
    // Flat copy: without this the plugin (v4+) recreates the whole
    // node_modules/pyodide/ path under dest.
    rename: { stripBase: true },
  },
];

export default defineConfig({
  plugins: [react(), viteStaticCopy({ targets: pyodideAssets })],
  server: {
    port: 3000,
    host: true,
  },
  build: {
    outDir: 'build',
  },
});
