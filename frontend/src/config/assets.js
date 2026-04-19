const rawBase = process.env.REACT_APP_ASSETS_URL || "http://localhost:9000/agent-games-assets";
const ASSETS_URL = rawBase.replace(/\/+$/, "");

export const imageUrl = (path) => `${ASSETS_URL}/images/${String(path).replace(/^\/+/, "")}`;

export const logoUrl = (path) => `${ASSETS_URL}/logos/${String(path).replace(/^\/+/, "")}`;

export default ASSETS_URL;
