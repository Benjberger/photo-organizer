/* Metadata page */

registerPage("metadata", function (container) {
    container.innerHTML = `
        <h2>Photo Metadata</h2>
        <div class="card">
            <div class="form-group">
                <label>Photo file</label>
                <div id="meta-path-input"></div>
            </div>
            <button id="meta-submit" class="btn-primary">Read Metadata</button>
        </div>
        <div id="meta-results"></div>
    `;

    const pathDiv = document.getElementById("meta-path-input");
    pathDiv.appendChild(pathInput("meta-file", "C:\\path\\to\\photo.jpg", "file"));

    document.getElementById("meta-submit").addEventListener("click", async () => {
        const file = document.getElementById("meta-file").value.trim();
        if (!file) return;
        const results = document.getElementById("meta-results");
        showLoading(results, "Reading metadata...");
        try {
            const data = await api("/api/metadata", { file });
            let html = '<div class="card">';
            html += '<div class="form-row" style="gap:20px; align-items:flex-start">';
            html += `<img src="/api/thumbnail?path=${encodeURIComponent(file)}" style="width:200px; height:auto; border-radius:4px; border:1px solid #444">`;
            html += '<table style="flex:1">';
            for (const [key, value] of Object.entries(data.metadata)) {
                html += `<tr><td style="color:#aaa; width:200px">${esc(key)}</td><td>${esc(value)}</td></tr>`;
            }
            html += "</table></div></div>";
            results.innerHTML = html;
        } catch (err) {
            showError(results, err.message);
        }
    });
});
