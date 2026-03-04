/* Photo Organizer — SPA Router & Shared Utilities */

const pages = {};

function registerPage(name, renderFn) {
    pages[name] = renderFn;
}

function navigate(pageName) {
    const content = document.getElementById("content");
    content.innerHTML = "";
    if (pages[pageName]) {
        pages[pageName](content);
    } else {
        content.innerHTML = "<h2>Welcome</h2><p>Select a tool from the sidebar.</p>";
    }
    document.querySelectorAll("#sidebar a").forEach(a => {
        a.classList.toggle("active", a.dataset.page === pageName);
    });
}

window.addEventListener("hashchange", () => {
    navigate(location.hash.slice(1) || "metadata");
});

window.addEventListener("DOMContentLoaded", () => {
    navigate(location.hash.slice(1) || "metadata");
});

/* Shared API helper — POST JSON, return parsed response */
async function api(endpoint, body = {}) {
    const resp = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    const data = await resp.json();
    if (!resp.ok) {
        throw new Error(data.error || resp.statusText);
    }
    return data;
}

/* Shared API helper — GET with query params */
async function apiGet(endpoint) {
    const resp = await fetch(endpoint);
    const data = await resp.json();
    if (!resp.ok) {
        throw new Error(data.error || resp.statusText);
    }
    return data;
}

/* Create a lazy-loaded thumbnail <img> */
function thumbImg(filePath) {
    const img = document.createElement("img");
    img.src = "/api/thumbnail?path=" + encodeURIComponent(filePath);
    img.loading = "lazy";
    img.alt = filePath.split(/[/\\]/).pop();
    return img;
}

/* Show success/failure results in a container */
function showResults(container, results) {
    const div = document.createElement("div");
    div.className = "results" + (results.failed > 0 ? " error" : "");
    let html = `<p class="success">Success: ${results.success}</p>`;
    if (results.failed > 0) {
        html += `<p class="error">Failed: ${results.failed}</p>`;
    }
    if (results.errors && results.errors.length) {
        html += "<ul>" + results.errors.map(e => `<li class="error">${esc(e)}</li>`).join("") + "</ul>";
    }
    div.innerHTML = html;
    container.appendChild(div);
}

/* Show an error message */
function showError(container, message) {
    const div = document.createElement("div");
    div.className = "results error";
    div.innerHTML = `<p class="error">${esc(message)}</p>`;
    container.appendChild(div);
}

/* Show loading state */
function showLoading(container, message) {
    container.innerHTML = `<p class="loading"><span class="spinner"></span>${esc(message)}</p>`;
}

/* Escape HTML */
function esc(str) {
    const d = document.createElement("div");
    d.textContent = str;
    return d.innerHTML;
}

/* Format file size */
function humanSize(bytes) {
    if (bytes >= 1e9) return (bytes / 1e9).toFixed(1) + " GB";
    if (bytes >= 1e6) return (bytes / 1e6).toFixed(1) + " MB";
    if (bytes >= 1e3) return (bytes / 1e3).toFixed(1) + " KB";
    return bytes + " bytes";
}

/* Create a path input with browse button */
function pathInput(id, placeholder, mode) {
    const div = document.createElement("div");
    div.className = "form-row";
    div.innerHTML = `
        <input type="text" id="${id}" placeholder="${placeholder}" style="flex:1">
        <button class="btn-browse" data-browse-for="${id}" data-browse-mode="${mode}">Browse</button>
    `;
    div.querySelector(".btn-browse").addEventListener("click", () => {
        openBrowseModal(mode, path => {
            document.getElementById(id).value = path;
        });
    });
    return div;
}
