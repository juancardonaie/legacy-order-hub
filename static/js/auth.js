// Operaciones de autenticación. El logout es solo del lado del cliente: el
// backend no tiene revocación de tokens, el token vive hasta su `exp`.

import { ApiError, request } from "./api.js";
import { clearSession, saveSession } from "./session.js";

export async function login(username, password) {
    let data;
    try {
        data = await request("/login", {
            method: "POST",
            body: { username, password },
            authenticated: false,
        });
    } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
            throw new ApiError("invalid_credentials", 401, "Usuario o contraseña incorrectos");
        }
        throw error;
    }

    if (!data || typeof data.token !== "string" || !data.user) {
        throw new ApiError("http", 200, "Respuesta de login inesperada");
    }
    if (!saveSession(data.token, data.user)) {
        throw new ApiError("storage", 0, "El navegador no permite guardar la sesión");
    }
    return data.user;
}

export function logout() {
    clearSession();
}
