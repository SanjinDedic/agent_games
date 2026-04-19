const rawBase = import.meta.env.VITE_ASSETS_URL || "https://agent-games-assets.s3.ap-southeast-2.amazonaws.com";
const ASSETS_URL = rawBase.replace(/\/+$/, "");

export const imageUrl = (path) => `${ASSETS_URL}/images/${String(path).replace(/^\/+/, "")}`;

export const logoUrl = (path) => `${ASSETS_URL}/logos/${String(path).replace(/^\/+/, "")}`;

export const videoUrl = (path) => `${ASSETS_URL}/videos/${String(path).replace(/^\/+/, "")}`;

export default ASSETS_URL;
