// Punto de entrada: decide qué vista mostrar y conecta los eventos.

import { ApiError } from "./api.js";
import { login, logout } from "./auth.js";
import { mountExplorer, unmountExplorer } from "./explorer.js";
import { clearSession, getExpiryMs, getToken, getUser, hasValidSession } from "./session.js";
import {
    clearPassword,
    onLoginSubmit,
    onLogoutClick,
    readCredentials,
    setLoading,
    showLogin,
    showMessage,
    showProtected,
} from "./ui.js";

// setTimeout no admite retrasos mayores a ~24 días.
const MAX_TIMER_MS = 2 ** 31 - 1;

let expiryTimer = null;

function cancelExpiryTimer() {
    if (expiryTimer !== null) {
        clearTimeout(expiryTimer);
        expiryTimer = null;
    }
}

function expireSession() {
    clearSession();
    cancelExpiryTimer();
    unmountExplorer();
    showLogin("Tu sesión expiró. Inicia sesión de nuevo");
}

function renderSession() {
    const expiryMs = getExpiryMs(getToken());
    showProtected(getUser(), expiryMs);
    mountExplorer({ onSessionExpired: expireSession });

    cancelExpiryTimer();
    const remaining = Math.min(Math.max(expiryMs - Date.now(), 0), MAX_TIMER_MS);
    expiryTimer = setTimeout(expireSession, remaining);
}

async function handleLogin() {
    const { username, password } = readCredentials();
    if (username === "" || password === "") {
        showMessage("Escribe usuario y contraseña");
        return;
    }

    setLoading(true);
    showMessage("");
    try {
        await login(username, password);
        if (!hasValidSession()) {
            clearSession();
            showMessage("El servidor devolvió una sesión inválida");
            return;
        }
        renderSession();
    } catch (error) {
        showMessage(
            error instanceof ApiError ? error.message : "Ocurrió un error inesperado"
        );
    } finally {
        clearPassword();
        setLoading(false);
    }
}

function handleLogout() {
    logout();
    cancelExpiryTimer();
    unmountExplorer();
    showLogin();
}

function start() {
    onLoginSubmit(handleLogin);
    onLogoutClick(handleLogout);

    if (hasValidSession()) {
        renderSession();
        return;
    }
    // Token vencido o corrupto: se limpia y se avisa solo si existía uno.
    const hadToken = getToken() !== null;
    clearSession();
    showLogin(hadToken ? "Tu sesión expiró. Inicia sesión de nuevo" : "");
}

start();
