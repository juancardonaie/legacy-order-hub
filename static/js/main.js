// Punto de entrada: decide qué vista mostrar y conecta los eventos.

import { ApiError } from "./api.js";
import { login, logout } from "./auth.js";
import { mountExplorer, unmountExplorer } from "./explorer.js";
import { clearSession, getExpiryMs, getToken, getUser, hasValidSession } from "./session.js";
import {
    clearNewPassword,
    clearPassword,
    onCreateUserSubmit,
    onLoginSubmit,
    onLogoutClick,
    readCredentials,
    readNewUser,
    resetCreateUser,
    setCreatingUser,
    setLoading,
    showCreateUser,
    showCreateUserMessage,
    showLogin,
    showMessage,
    showProtected,
} from "./ui.js";
import { createUser } from "./users.js";

// setTimeout no admite retrasos mayores a ~24 días.
const MAX_TIMER_MS = 2 ** 31 - 1;

const ADMIN_ROLE = "admin";
const CLIENT_ROLE = "client";

let expiryTimer = null;
let creatingUser = false;

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
    showCreateUser(false);
    showLogin("Tu sesión expiró. Inicia sesión de nuevo");
}

function renderSession() {
    const expiryMs = getExpiryMs(getToken());
    const user = getUser();
    showProtected(user, expiryMs);
    // El formulario es solo para admin; el backend lo exige igualmente (403).
    showCreateUser(user.role === ADMIN_ROLE);
    mountExplorer({ user, onSessionExpired: expireSession });

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

async function handleCreateUser() {
    if (creatingUser) {
        return;
    }
    const { username, password, isAdmin } = readNewUser();
    if (username === "" || password === "") {
        showCreateUserMessage("Escribe usuario y contraseña");
        return;
    }

    creatingUser = true;
    setCreatingUser(true);
    showCreateUserMessage("");
    try {
        const created = await createUser(username, password, isAdmin ? ADMIN_ROLE : CLIENT_ROLE);
        resetCreateUser();
        showCreateUserMessage(`Usuario ${created.username} creado con rol ${created.role}`, true);
    } catch (error) {
        if (error instanceof ApiError && error.kind === "session_expired") {
            expireSession();
            return;
        }
        // 400, 403, 409 y 429 llegan aquí con el mensaje del servidor; ninguno
        // cierra la sesión (solo el 401 lo hace, dentro de api.js).
        showCreateUserMessage(
            error instanceof ApiError ? error.message : "Ocurrió un error inesperado"
        );
    } finally {
        clearNewPassword();
        setCreatingUser(false);
        creatingUser = false;
    }
}

function handleLogout() {
    logout();
    cancelExpiryTimer();
    unmountExplorer();
    showCreateUser(false);
    showLogin();
}

function start() {
    onLoginSubmit(handleLogin);
    onLogoutClick(handleLogout);
    onCreateUserSubmit(handleCreateUser);

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
