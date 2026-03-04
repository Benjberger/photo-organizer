/* Duplicates page */

registerPage("duplicates", function (container) {
    container.innerHTML = `
        <h2>Find Duplicates</h2>
        <p class="muted">Detect duplicate photos by content hash (SHA-256).</p>
        <div class="card">
            <div class="form-group">
                <label>Directory to scan</label>
                <div id="dup-dir-input"></div>
            </div>
            <button id="dup-scan" class="btn-primary">Scan for Duplicates</button>
        </div>
        <div id="dup-results"></div>
    `;

    document.getElementById("dup-dir-input").appendChild(pathInput("dup-dir", "Photo folder", "dir"));

    document.getElementById("dup-scan").addEventListener("click", async () => {
        const directory = document.getElementById("dup-dir").value.trim();
        if (!directory) return;

        const results = document.getElementById("dup-results");
        showLoading(results, "Scanning for duplicates...");

        try {
            const data = await api("/api/duplicates/scan", { directory });
            if (data.total_groups === 0) {
                results.innerHTML = '<div class="results"><p class="success">No duplicates found.</p></div>';
                return;
            }

            let html = `<div class="card"><h3>${data.total_groups} group(s), ${data.total_duplicates} duplicate(s)</h3>`;
            for (const group of data.groups) {
                html += '<div class="dupe-group">';
                html += `<div class="dupe-keep">Keep: ${esc(group.files[0].name)} (${humanSize(group.files[0].size)})</div>`;
                for (let i = 1; i < group.files.length; i++) {
                    html += `<div class="dupe-remove">Duplicate: ${esc(group.files[i].name)}</div>`;
                }
                html += '<div class="thumb-grid" style="margin-top:8px">';
                for (const f of group.files.slice(0, 4)) {
                    html += `<div class="thumb-item">
                        <img src="/api/thumbnail?path=${encodeURIComponent(f.path)}" loading="lazy">
                        <div class="name">${esc(f.name)}</div>
                    </div>`;
                }
                html += '</div></div>';
            }

            html += `<div class="action-bar">
                <select id="dup-action" style="width:auto">
                    <option value="report">Report only</option>
                    <option value="move">Move to duplicates folder</option>
                    <option value="delete">Delete duplicates</option>
                </select>
                <button id="dup-handle" class="btn-danger">Handle Duplicates</button>
            </div></div>`;

            results.innerHTML = html;

            document.getElementById("dup-handle").addEventListener("click", async () => {
                const action = document.getElementById("dup-action").value;
                if (action === "delete" && !confirm("This will permanently delete duplicate files. Continue?")) {
                    return;
                }
                showLoading(results, "Handling duplicates...");
                try {
                    const handleData = await api("/api/duplicates/handle", {
                        directory,
                        action,
                        duplicates_dir: directory + "/_duplicates",
                    });
                    results.innerHTML = "";
                    showResults(results, { success: handleData.processed, failed: 0, errors: handleData.errors });
                } catch (err) {
                    showError(results, err.message);
                }
            });
        } catch (err) {
            showError(results, err.message);
        }
    });
});
