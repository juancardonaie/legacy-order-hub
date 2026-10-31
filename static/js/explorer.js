// Explorador de API: lista los endpoints del catálogo y permite enviar
// peticiones sin usar curl. Todo dato dinámico se escribe con textContent.
//
// El token nunca se pinta: lo adjunta api.js y la respuesta de /login se
// muestra con el campo `token` enmascarado.

import { ApiError, loadCatalog, send } from "./api.js";

const MASKED_VALUE = "[oculto]";
const LOGIN_PATH = "/login";

// Evita pintar un catálogo viejo si la sesión cambió mientras cargaba.
let mountCounter = 0;

function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) {
        node.className = className;
    }
    if (text !== undefined) {
        node.textContent = text;
    }
    return node;
}

function statusClass(status) {
    if (status >= 200 && status < 300) {
        return "status--ok";
    }
    if (status >= 400 && status < 500) {
        return "status--client";
    }
    return "status--server";
}

// Copia para mostrar; nunca muta el dato original.
function displayBody(endpoint, result) {
    if (!result.isJson) {
        return String(result.body);
    }
    let shown = result.body;
    const isLogin = endpoint.path === LOGIN_PATH;
    if (isLogin && shown !== null && typeof shown === "object" && "token" in shown) {
        shown = { ...shown, token: MASKED_VALUE };
    }
    return JSON.stringify(shown, null, 2);
}

function describeAccess(endpoint) {
    if (!endpoint.auth) {
        return "Pública (sin token)";
    }
    return endpoint.role ? `Requiere token y rol ${endpoint.role}` : "Requiere token";
}

function buildFields(endpoint) {
    const list = el("ul", "explorer-fields");
    for (const field of endpoint.body_fields || []) {
        const requirement = field.required ? "obligatorio" : "opcional";
        list.appendChild(
            el("li", "", `${field.name} (${field.type}, ${requirement}): ${field.description}`)
        );
    }
    return list;
}

function renderResult(output, endpoint, result) {
    output.status.className = `status ${statusClass(result.status)}`;
    output.status.textContent = String(result.status);
    output.time.textContent = `${Math.round(result.ms)} ms`;
    output.body.textContent = displayBody(endpoint, result);
    output.box.hidden = false;
}

function renderFailure(output, message) {
    output.status.className = "status status--server";
    output.status.textContent = "Sin respuesta";
    output.time.textContent = "";
    output.body.textContent = message;
    output.box.hidden = false;
}

function buildEndpoint(endpoint, index, onSessionExpired) {
    const details = el("details", "explorer-endpoint");

    const summary = el("summary");
    summary.appendChild(el("span", `method method--${endpoint.method.toLowerCase()}`, endpoint.method));
    summary.appendChild(el("span", "path", endpoint.path));
    details.appendChild(summary);

    const content = el("div", "explorer-content");
    content.appendChild(el("p", "", endpoint.summary));
    content.appendChild(el("p", "explorer-access", describeAccess(endpoint)));

    let bodyInput = null;
    if (endpoint.body_example) {
        content.appendChild(buildFields(endpoint));
        const bodyId = `explorer-body-${index}`;
        const label = el("label", "", "Body (JSON)");
        label.htmlFor = bodyId;
        bodyInput = el("textarea", "explorer-body");
        bodyInput.id = bodyId;
        bodyInput.rows = 6;
        bodyInput.spellcheck = false;
        bodyInput.value = JSON.stringify(endpoint.body_example, null, 2);
        content.appendChild(label);
        content.appendChild(bodyInput);
    }

    let noTokenInput = null;
    if (endpoint.auth) {
        const noTokenId = `explorer-notoken-${index}`;
        const noTokenLabel = el("label", "explorer-inline", "");
        noTokenLabel.htmlFor = noTokenId;
        noTokenInput = el("input");
        noTokenInput.type = "checkbox";
        noTokenInput.id = noTokenId;
        noTokenLabel.appendChild(noTokenInput);
        noTokenLabel.appendChild(el("span", "", "Enviar sin token"));
        content.appendChild(noTokenLabel);
    }

    const button = el("button", "explorer-send", "Enviar");
    button.type = "button";
    content.appendChild(button);

    const message = el("p", "message", "");
    message.hidden = true;
    message.setAttribute("role", "alert");
    content.appendChild(message);

    const box = el("div", "explorer-output");
    box.hidden = true;
    const meta = el("p", "explorer-meta");
    const status = el("span", "status", "");
    const time = el("span", "explorer-time", "");
    meta.appendChild(status);
    meta.appendChild(time);
    const body = el("pre", "explorer-response", "");
    box.appendChild(meta);
    box.appendChild(body);
    content.appendChild(box);
    const output = { box, status, time, body };

    button.addEventListener("click", async () => {
        message.hidden = true;

        let payload;
        if (bodyInput !== null && bodyInput.value.trim() !== "") {
            try {
                payload = JSON.parse(bodyInput.value);
            } catch (error) {
                message.textContent = "El body no es JSON válido";
                message.hidden = false;
                return;
            }
        }

        button.disabled = true;
        button.textContent = "Enviando…";
        try {
            const result = await send({
                method: endpoint.method,
                path: endpoint.path,
                body: payload,
                withToken: noTokenInput === null || !noTokenInput.checked,
            });
            renderResult(output, endpoint, result);
        } catch (error) {
            if (error instanceof ApiError && error.kind === "session_expired") {
                onSessionExpired();
                return;
            }
            renderFailure(
                output,
                error instanceof ApiError ? error.message : "Ocurrió un error inesperado"
            );
        } finally {
            button.disabled = false;
            button.textContent = "Enviar";
        }
    });

    details.appendChild(content);
    return details;
}

// Mostrar solo lo que el rol de la sesión puede usar es comodidad: la
// autorización real es el 403 del backend.
function visibleFor(endpoints, user) {
    const role = user ? user.role : null;
    return endpoints.filter((endpoint) => endpoint.role === null || endpoint.role === role);
}

export async function mountExplorer({ user, onSessionExpired }) {
    const root = document.getElementById("explorer");
    mountCounter += 1;
    const current = mountCounter;
    root.replaceChildren();

    let endpoints;
    try {
        endpoints = await loadCatalog();
    } catch (error) {
        if (current === mountCounter) {
            const text = error instanceof ApiError ? error.message : "Ocurrió un error inesperado";
            root.appendChild(el("p", "message", text));
        }
        return;
    }
    if (current !== mountCounter) {
        return;
    }

    root.appendChild(el("h2", "", "Explorador de API"));
    visibleFor(endpoints, user).forEach((endpoint, index) => {
        root.appendChild(buildEndpoint(endpoint, index, onSessionExpired));
    });
}

export function unmountExplorer() {
    mountCounter += 1;
    document.getElementById("explorer").replaceChildren();
}
