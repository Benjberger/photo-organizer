/* Organize page */

registerPage("organize", function (container) {
    container.innerHTML = `
        <h2>Organize Photos</h2>
        <p class="muted">Sort photos into YYYY/YYYY-MM-DD folders by EXIF date.</p>
        <div class="card">
            <div class="form-group">
                <label>Source directory</label>
                <div id="org-src-input"></div>
            </div>
            <div class="form-group">
                <label>Destination directory</label>
                <div id="org-dest-input"></div>
            </div>
            <div class="form-group">
                <label>Mode</label>
                <select id="org-mode" style="width:auto">
                    <option value="copy">Copy</option>
                    <option value="move">Move</option>
                </select>
            </div>
            <div class="action-bar" style="border-top:none; padding-top:0">
                <button id="org-preview" class="btn-primary">Preview</button>
                <button id="org-execute" class="btn-danger" disabled>Execute</button>
            </div>
        </div>
        <div id="org-results"></div>
    `;

    document.getElementById("org-src-input").appendChild(pathInput("org-src", "Source folder", "dir"));
    document.getElementById("org-dest-input").appendChild(pathInput("org-dest", "Destination folder", "dir"));

    document.getElementById("org-preview").addEventListener("click", async () => {
        const source = document.getElementById("org-src").value.trim();
        const destination = document.getElementById("org-dest").value.trim();
        if (!source || !destination) return;

        const results = document.getElementById("org-results");
        showLoading(results, "Scanning photos...");

        try {
            const data = await api("/api/organize/plan", { source, destination });
            results.innerHTML = `
                <div class="card">
                    <h3>${data.count} file(s) to organize</h3>
                    <div class="preview">${esc(data.preview)}</div>
                </div>
            `;
            document.getElementById("org-execute").disabled = data.count === 0;
        } catch (err) {
            showError(results, err.message);
        }
    });

    document.getElementById("org-execute").addEventListener("click", async () => {
        const source = document.getElementById("org-src").value.trim();
        const destination = document.getElementById("org-dest").value.trim();
        const mode = document.getElementById("org-mode").value;

        const results = document.getElementById("org-results");
        showLoading(results, "Organizing files...");

        try {
            const data = await api("/api/organize/execute", { source, destination, mode });
            results.innerHTML = "";
            showResults(results, data);
        } catch (err) {
            showError(results, err.message);
        }
    });
});
