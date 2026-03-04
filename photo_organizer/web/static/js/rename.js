/* Rename page */

registerPage("rename", function (container) {
    container.innerHTML = `
        <h2>Batch Rename</h2>
        <p class="muted">Rename photos using metadata placeholders: {date}, {datetime}, {year}, {month}, {day}, {camera}, {model}, {seq}, {original}, {location}</p>
        <div class="card">
            <div class="form-group">
                <label>Directory</label>
                <div id="ren-dir-input"></div>
            </div>
            <div class="form-group">
                <label>Pattern</label>
                <input type="text" id="ren-pattern" value="{date}_{seq}" placeholder="{date}_{camera}_{seq}">
            </div>
            <div class="form-group">
                <label>Gap hours (for {location} grouping)</label>
                <input type="number" id="ren-gap" value="3" min="0.5" step="0.5" style="width:100px">
            </div>
            <div class="action-bar" style="border-top:none; padding-top:0">
                <button id="ren-preview" class="btn-primary">Preview</button>
                <button id="ren-execute" class="btn-danger" disabled>Execute</button>
                <button id="ren-undo" class="btn-secondary" disabled>Undo Last</button>
            </div>
        </div>
        <div id="ren-locations" class="hidden"></div>
        <div id="ren-results"></div>
    `;

    document.getElementById("ren-dir-input").appendChild(pathInput("ren-dir", "Photo folder", "dir"));

    let lastUndoLog = null;

    document.getElementById("ren-preview").addEventListener("click", async () => {
        const directory = document.getElementById("ren-dir").value.trim();
        const pattern = document.getElementById("ren-pattern").value.trim();
        if (!directory || !pattern) return;

        const gap_hours = parseFloat(document.getElementById("ren-gap").value) || 3.0;
        const results = document.getElementById("ren-results");
        const locDiv = document.getElementById("ren-locations");
        locDiv.classList.add("hidden");
        showLoading(results, "Planning renames...");

        try {
            const data = await api("/api/rename/plan", { directory, pattern, gap_hours });

            if (data.needs_location_names) {
                results.innerHTML = "";
                locDiv.classList.remove("hidden");
                let html = '<div class="card"><h3>Name these groups</h3>';
                for (const c of data.clusters) {
                    if (c.needs_name) {
                        html += `<div class="inline-field">
                            <label>Group ${c.index + 1} (${c.photo_count} photos, ${esc(c.date_range)})</label>
                            <input type="text" class="loc-name" data-idx="${c.index}" placeholder="e.g. Beach_Trip">
                        </div>`;
                    } else {
                        html += `<div class="inline-field">
                            <label>Group ${c.index + 1}</label>
                            <span class="muted">${esc(c.location)}</span>
                        </div>`;
                    }
                }
                html += '<button id="ren-apply-names" class="btn-primary" style="margin-top:12px">Apply Names & Preview</button>';
                html += '</div>';
                locDiv.innerHTML = html;

                document.getElementById("ren-apply-names").addEventListener("click", async () => {
                    const names = {};
                    locDiv.querySelectorAll(".loc-name").forEach(input => {
                        if (input.value.trim()) {
                            names[input.dataset.idx] = input.value.trim();
                        }
                    });
                    showLoading(results, "Planning renames with locations...");
                    try {
                        const data2 = await api("/api/rename/plan", { directory, pattern, gap_hours, location_names: names });
                        locDiv.classList.add("hidden");
                        results.innerHTML = `<div class="card"><h3>${data2.count} file(s) to rename</h3>
                            <div class="preview">${esc(data2.preview)}</div></div>`;
                        document.getElementById("ren-execute").disabled = data2.count === 0;
                    } catch (err) {
                        showError(results, err.message);
                    }
                });
                return;
            }

            results.innerHTML = `<div class="card"><h3>${data.count} file(s) to rename</h3>
                <div class="preview">${esc(data.preview)}</div></div>`;
            document.getElementById("ren-execute").disabled = data.count === 0;
        } catch (err) {
            showError(results, err.message);
        }
    });

    document.getElementById("ren-execute").addEventListener("click", async () => {
        const directory = document.getElementById("ren-dir").value.trim();
        const pattern = document.getElementById("ren-pattern").value.trim();
        const gap_hours = parseFloat(document.getElementById("ren-gap").value) || 3.0;
        const results = document.getElementById("ren-results");
        showLoading(results, "Renaming files...");

        try {
            const data = await api("/api/rename/execute", { directory, pattern, gap_hours });
            results.innerHTML = "";
            showResults(results, data);
            if (data.undo_log) {
                lastUndoLog = data.undo_log;
                document.getElementById("ren-undo").disabled = false;
            }
        } catch (err) {
            showError(results, err.message);
        }
    });

    document.getElementById("ren-undo").addEventListener("click", async () => {
        if (!lastUndoLog) return;
        const results = document.getElementById("ren-results");
        showLoading(results, "Undoing renames...");
        try {
            const data = await api("/api/rename/undo", { undo_log: lastUndoLog });
            results.innerHTML = "";
            showResults(results, data);
            lastUndoLog = null;
            document.getElementById("ren-undo").disabled = true;
        } catch (err) {
            showError(results, err.message);
        }
    });
});
