// Render de las vistas. Todo dato dinámico se escribe con textContent.

const $ = (id) => document.getElementById(id);

export function showLogin(message = "") {
    $("protected-view").hidden = true;
    $("login-view").hidden = false;
    $("app").classList.remove("container--wide");
    showMessage(message);
    $("login-form").reset();
}

export function showProtected(user, expiryMs) {
    $("login-view").hidden = true;
    $("protected-view").hidden = false;
    $("app").classList.add("container--wide");
    $("user-name").textContent = user.username;
    $("user-role").textContent = user.role;
    $("session-expiry").textContent = new Date(expiryMs).toLocaleTimeString();
}

export function showMessage(message) {
    const element = $("login-message");
    element.textContent = message;
    element.hidden = message === "";
}

export function setLoading(isLoading) {
    $("login-button").disabled = isLoading;
    $("login-button").textContent = isLoading ? "Entrando…" : "Entrar";
}

export function readCredentials() {
    return {
        username: $("username").value.trim(),
        password: $("password").value,
    };
}

export function clearPassword() {
    $("password").value = "";
}

export function onLoginSubmit(handler) {
    $("login-form").addEventListener("submit", (event) => {
        event.preventDefault();
        handler();
    });
}

export function onLogoutClick(handler) {
    $("logout-button").addEventListener("click", handler);
}

// --- Formulario "Crear usuario" (solo admin) ---------------------------------

export function showCreateUser(visible) {
    $("create-user-view").hidden = !visible;
    if (!visible) {
        resetCreateUser();
    }
}

export function resetCreateUser() {
    $("create-user-form").reset();
    showCreateUserMessage("");
}

export function readNewUser() {
    return {
        username: $("new-username").value.trim(),
        password: $("new-password").value,
        isAdmin: $("new-is-admin").checked,
    };
}

export function clearNewPassword() {
    $("new-password").value = "";
}

export function showCreateUserMessage(message, isSuccess = false) {
    const element = $("create-user-message");
    element.textContent = message;
    element.className = isSuccess ? "message message--ok" : "message";
    element.hidden = message === "";
}

export function setCreatingUser(isCreating) {
    $("create-user-button").disabled = isCreating;
    $("create-user-button").textContent = isCreating ? "Creando…" : "Crear usuario";
}

export function onCreateUserSubmit(handler) {
    $("create-user-form").addEventListener("submit", (event) => {
        event.preventDefault();
        handler();
    });
}
