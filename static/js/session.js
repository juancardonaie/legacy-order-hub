// Almacén de la sesión en sessionStorage (se borra al cerrar la pestaña).
//
// Riesgo conocido: cualquier XSS podría leer el token (DT-16). Por eso el resto
// de la UI pinta datos solo con textContent y la página declara una CSP.
//
// La lectura de `exp` es solo para UX (avisar antes de que el servidor
// responda 401). No valida la firma: la autoridad es siempre el backend.

const TOKEN_KEY = "orderhub.token";
const USER_KEY = "orderhub.user";

function storage() {
    try {
        return window.sessionStorage;
    } catch (error) {
        return null;
    }
}

export function saveSession(token, user) {
    const store = storage();
    if (!store) {
        return false;
    }
    store.setItem(TOKEN_KEY, token);
    store.setItem(USER_KEY, JSON.stringify(user));
    return true;
}

export function clearSession() {
    const store = storage();
    if (!store) {
        return;
    }
    store.removeItem(TOKEN_KEY);
    store.removeItem(USER_KEY);
}

export function getToken() {
    const store = storage();
    return store ? store.getItem(TOKEN_KEY) : null;
}

export function getUser() {
    const store = storage();
    const raw = store ? store.getItem(USER_KEY) : null;
    if (!raw) {
        return null;
    }
    try {
        const user = JSON.parse(raw);
        if (typeof user.username === "string" && typeof user.role === "string") {
            return user;
        }
    } catch (error) {
        // JSON corrupto: se trata como si no hubiera usuario.
    }
    return null;
}

// Devuelve el `exp` del token en milisegundos, o null si no se puede leer.
export function getExpiryMs(token) {
    try {
        const payloadPart = token.split(".")[1];
        const base64 = payloadPart.replace(/-/g, "+").replace(/_/g, "/");
        const padded = base64 + "=".repeat((4 - (base64.length % 4)) % 4);
        const payload = JSON.parse(atob(padded));
        return typeof payload.exp === "number" ? payload.exp * 1000 : null;
    } catch (error) {
        return null;
    }
}

// Sesión utilizable: hay token, hay usuario y el token no ha expirado.
export function hasValidSession() {
    const token = getToken();
    if (!token || !getUser()) {
        return false;
    }
    const expiry = getExpiryMs(token);
    return expiry !== null && expiry > Date.now();
}
