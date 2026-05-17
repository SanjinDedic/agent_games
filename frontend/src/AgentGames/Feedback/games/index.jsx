// Auto-collected per-game manifest.
// Drop a folder with an `index.jsx` exporting the standard shape
// ({ name, displayName, description, thumbnail, Feedback, ResultsDisplay, ... })
// and it lights up everywhere that imports from here.

const modules = import.meta.glob('./*/index.jsx', { eager: true });

const games = Object.values(modules)
  .map((m) => m.default)
  .filter(Boolean);

export const gamesByName = Object.fromEntries(
  games.map((g) => [g.name, g])
);

export const gamesList = [...games].sort(
  (a, b) => (a.order ?? 999) - (b.order ?? 999)
);

export const featuredGames = gamesList.filter((g) => g.featured);

export const getGame = (name) => gamesByName[name] || null;

export default gamesByName;
