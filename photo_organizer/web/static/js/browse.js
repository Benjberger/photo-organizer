/* Directory/File Browser Modal */

let browseCallback = null;
let browseMode = "dir";
let browseSelected = null;

function openBrowseModal(mode, onSelect) {
    browseMode = mode;
    browseCallback = onSelect;
    browseSelected = null;
    const modal = document.getElementById("browse-modal");
    modal.classList.remove("hidden");
    document.getElementById("browse-title").textContent =
        mode === "dir" ? "Select Folder" : mode === "file" ? "Select File" : "Browse";
    loadBrowseDir("");
}

function closeBrowseModal() {
    document.getElementById("browse-modal").classList.add("hidden");
    browseCallback = null;
    browseSelected = null;
}

async function loadBrowseDir(path) {
    const list = document.getElementById("browse-list");
    const pathDisplay = document.getElementById("browse-path");
    list.innerHTML = '<p class="loading" style="padding:20px"><span class="spinner"></span>Loading...</p>';

    try {
        const params = new URLSearchParams();
        if (path) params.set("path", path);
        params.set("mode", browseMode === "dir" ? "dir" : "both");
        const data = await apiGet("/api/browse?" + params);

        pathDisplay.textContent = data.current;
        browseSelected = null;
        list.innerHTML = "";

        // Parent directory entry
        if (data.parent) {
            const item = document.createElement("div");
            item.className = "browse-item";
            item.innerHTML = '<span class="icon">&#x1F4C1;</span> ..';
            item.addEventListener("click", () => loadBrowseDir(data.parent));
            list.appendChild(item);
        }

        for (const entry of data.entries) {
            const item = document.createElement("div");
            item.className = "browse-item";
            if (entry.type === "dir") {
                item.innerHTML = `<span class="icon">&#x1F4C1;</span> ${esc(entry.name)}`;
                item.addEventListener("dblclick", () => loadBrowseDir(entry.path));
                item.addEventListener("click", () => {
                    list.querySelectorAll(".browse-item").forEach(i => i.classList.remove("selected"));
                    item.classList.add("selected");
                    browseSelected = entry.path;
                });
            } else {
                item.innerHTML = `<span class="icon">&#x1F4F7;</span> ${esc(entry.name)}` +
                    `<span class="size">${humanSize(entry.size)}</span>`;
                item.addEventListener("click", () => {
                    list.querySelectorAll(".browse-item").forEach(i => i.classList.remove("selected"));
                    item.classList.add("selected");
                    browseSelected = entry.path;
                });
                item.addEventListener("dblclick", () => {
                    if (browseCallback) browseCallback(entry.path);
                    closeBrowseModal();
                });
            }
            list.appendChild(item);
        }

        // If browsing for directories, also allow selecting current directory
        if (browseMode === "dir") {
            browseSelected = data.current;
        }
    } catch (err) {
        list.innerHTML = `<p class="error" style="padding:20px">${esc(err.message)}</p>`;
    }
}

// Event listeners
document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("browse-close").addEventListener("click", closeBrowseModal);
    document.getElementById("browse-cancel").addEventListener("click", closeBrowseModal);
    document.getElementById("browse-select").addEventListener("click", () => {
        if (browseSelected && browseCallback) {
            browseCallback(browseSelected);
        }
        closeBrowseModal();
    });

    // Close on backdrop click
    document.getElementById("browse-modal").addEventListener("click", (e) => {
        if (e.target.id === "browse-modal") closeBrowseModal();
    });
});
