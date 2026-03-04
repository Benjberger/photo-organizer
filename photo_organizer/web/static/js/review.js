/* Review (contact sheet) page */

registerPage("review", function (container) {
    container.innerHTML = `
        <h2>Review Photos</h2>
        <p class="muted">Browse photos grouped by time with thumbnails.</p>
        <div class="card">
            <div class="form-group">
                <label>Directory</label>
                <div id="rev-dir-input"></div>
            </div>
            <div class="form-group">
                <label>Gap hours (time between groups)</label>
                <input type="number" id="rev-gap" value="3" min="0.5" step="0.5" style="width:100px">
            </div>
            <button id="rev-generate" class="btn-primary">Generate Contact Sheet</button>
        </div>
        <div id="rev-results"></div>
    `;

    document.getElementById("rev-dir-input").appendChild(pathInput("rev-dir", "Photo folder", "dir"));

    document.getElementById("rev-generate").addEventListener("click", async () => {
        const directory = document.getElementById("rev-dir").value.trim();
        if (!directory) return;
        const gap_hours = parseFloat(document.getElementById("rev-gap").value) || 3.0;

        const results = document.getElementById("rev-results");
        showLoading(results, "Clustering photos...");

        try {
            const data = await api("/api/review/generate", { directory, gap_hours });

            let html = `<p class="muted" style="margin-bottom:16px">${data.total_photos} photos in ${data.total_groups} group(s)</p>`;

            for (const cluster of data.clusters) {
                html += '<div class="card">';
                html += `<h3>${esc(cluster.location || "Unnamed Group")} — ${cluster.photo_count} photos</h3>`;
                html += `<p class="muted">${esc(cluster.date_range)}</p>`;
                html += '<div class="thumb-grid">';
                for (const photo of cluster.photos) {
                    html += `<div class="thumb-item">
                        <img src="/api/thumbnail?path=${encodeURIComponent(photo.path)}" loading="lazy">
                        <div class="name">${esc(photo.name)}</div>
                    </div>`;
                }
                html += '</div></div>';
            }

            results.innerHTML = html;
        } catch (err) {
            showError(results, err.message);
        }
    });
});
