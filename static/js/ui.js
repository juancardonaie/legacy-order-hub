// Render de las vistas. Todo dato dinámico se escribe con textContent.

const $ = (id) => document.getElementById(id);

export function showLogin(message = "") {
    $("protected-view").hidden = true;
    $("login-view").hidden = false;
    showMessage(message);
    $("login-form").reset();
}

export function showProtected(user, expiryMs) {
    $("login-view").hidden = true;
    $("protected-view").hidden = false;
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
