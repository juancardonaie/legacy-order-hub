// Cliente HTTP del backend (mismo origen: sin CORS ni proxy).
//
// Reglas:
// - Añade Authorization: Bearer cuando la petición es autenticada.
// - Un 401 en una petición autenticada limpia la sesión (kind "session_expired").
// - Un 403 NO cierra la sesión: el usuario sigue identificado, solo le falta rol.

import { clearSession, getToken } from "./session.js";

export class ApiError extends Error {
    constructor(kind, status, message) {
        super(message);
        this.kind = kind;
        this.status = status;
    }
}

async function readJson(response) {
    try {
        return await response.json();
    } catch (error) {
        return null;
    }
}

export async function request(path, { method = "GET", body, authenticated = true } = {}) {
    const headers = { Accept: "application/json" };
    if (body !== undefined) {
        headers["Content-Type"] = "application/json";
    }
    if (authenticated) {
        const token = getToken();
        if (token) {
            headers.Authorization = `Bearer ${token}`;
        }
    }

    let response;
    try {
        response = await fetch(path, {
            method,
            headers,
            body: body === undefined ? undefined : JSON.stringify(body),
        });
    } catch (error) {
        throw new ApiError("network", 0, "No se pudo conectar con el servidor");
    }

    const data = await readJson(response);

    if (response.ok) {
        return data;
    }
    if (response.status === 401 && authenticated) {
        clearSession();
        throw new ApiError("session_expired", 401, "Tu sesión expiró. Inicia sesión de nuevo");
    }

    const message = (data && (data.message || data.error)) || "Error inesperado del servidor";
    throw new ApiError("http", response.status, message);
}

// --- Explorador de API -------------------------------------------------------
//
// send() es el cliente "crudo" del explorador: no lanza en respuestas no 2xx y
// devuelve status, tiempo y cuerpo tal como llegaron. Solo llama a endpoints
// del catálogo (static/endpoints.json) y es el único lugar que adjunta el token.

const CATALOG_PATH = "/static/endpoints.json";

let catalog = [];

function isCatalogEntry(entry) {
    return (
        entry !== null &&
        typeof entry === "object" &&
        typeof entry.method === "string" &&
        typeof entry.path === "string"
    );
}

export async function loadCatalog() {
    let response;
    try {
        response = await fetch(CATALOG_PATH, {
            headers: { Accept: "application/json" },
            cache: "no-store",
        });
    } catch (error) {
        throw new ApiError("network", 0, "No se pudo conectar con el servidor");
    }

    const data = response.ok ? await readJson(response) : null;
    if (!Array.isArray(data) || !data.every(isCatalogEntry)) {
        throw new ApiError("catalog", response.status, "No se pudo cargar el catálogo de endpoints");
    }
    catalog = data;
    return catalog;
}

function findEndpoint(method, path) {
    return catalog.find((entry) => entry.method === method && entry.path === path) || null;
}

function isSameOriginPath(path) {
    return (
        typeof path === "string" &&
        path.startsWith("/") &&
        !path.startsWith("//") &&
        !path.includes("\\")
    );
}

function parseJson(text) {
    try {
        return { valid: true, value: JSON.parse(text) };
    } catch (error) {
        return { valid: false, value: null };
    }
}

export async function send({ method, path, body, withToken = true }) {
    const endpoint = isSameOriginPath(path) ? findEndpoint(method, path) : null;
    if (endpoint === null) {
        throw new ApiError("invalid_endpoint", 0, "El endpoint no está en el catálogo");
    }

    const headers = { Accept: "application/json" };
    if (body !== undefined) {
        headers["Content-Type"] = "application/json";
    }
    let tokenSent = false;
    if (endpoint.auth === true && withToken) {
        const token = getToken();
        if (token) {
            headers.Authorization = `Bearer ${token}`;
            tokenSent = true;
        }
    }

    const started = performance.now();
    let response;
    let text;
    try {
        response = await fetch(path, {
            method,
            headers,
            body: body === undefined ? undefined : JSON.stringify(body),
        });
        text = await response.text();
    } catch (error) {
        throw new ApiError("network", 0, "No se pudo conectar con el servidor");
    }
    const ms = performance.now() - started;

    if (response.status === 401 && tokenSent) {
        clearSession();
        throw new ApiError("session_expired", 401, "Tu sesión expiró. Inicia sesión de nuevo");
    }

    const parsed = parseJson(text);
    return {
        status: response.status,
        ms,
        body: parsed.valid ? parsed.value : text,
        isJson: parsed.valid,
    };
}
