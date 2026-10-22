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
