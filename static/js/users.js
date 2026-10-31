// Creación de usuarios (solo administradores). La petición pasa por request()
// de api.js, que adjunta el token; este módulo no usa fetch.
//
// Ocultar el formulario a quien no es admin es solo comodidad: la autorización
// real es el 403 del backend (POST /users exige rol admin).

import { ApiError, request } from "./api.js";

export async function createUser(username, password, role) {
    const data = await request("/users", {
        method: "POST",
        body: { username, password, role },
        authenticated: true,
    });

    if (!data || !data.user || typeof data.user.username !== "string") {
        throw new ApiError("http", 201, "Respuesta de creación de usuario inesperada");
    }
    return data.user;
}
