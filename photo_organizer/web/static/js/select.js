/* Select (print scoring) page */

registerPage("select", function (container) {
    container.innerHTML = `
        <h2>Print Selection</h2>
        <p class="muted">Score photos for print quality and tag the best ones.</p>
        <div class="card">
            <div class="form-group">
                <label>Directory</label>
                <div id="sel-dir-input"></div>
            </div>
            <div class="form-row">
                <div class="form-group" style="flex:1">
                    <label>Minimum score (0-100)</label>
                    <input type="number" id="sel-min" value="0" min="0" max="100" style="width:100px">
                </div>
                <div class="form-group" style="flex:1">
                    <label>Top N (leave empty for all)</label>
                    <input type="number" id="sel-top" min="1" style="width:100px">
                </div>
            </div>
            <button id="sel-score" class="btn-primary">Score Photos</button>
        </div>
        <div id="sel-results"></div>
    `;

    document.getElementById("sel-dir-input").appendChild(pathInput("sel-dir", "Photo folder", "dir"));

    document.getElementById("sel-score").addEventListener("click", async () => {
        const directory = document.getElementById("sel-dir").value.trim();
        if (!directory) return;
        const min_score = parseFloat(document.getElementById("sel-min").value) || 0;
        const topVal = document.getElementById("sel-top").value;
        const top = topVal ? parseInt(topVal) : null;

        const results = document.getElementById("sel-results");
        showLoading(results, "Scoring photos...");

        try {
            const data = await api("/api/select/score", { directory, min_score, top });

            if (data.candidates_count === 0) {
                results.innerHTML = '<div class="results"><p class="muted">No photos matched the criteria.</p></div>';
                return;
            }

            let html = `<div class="card"><h3>${data.candidates_count} candidate(s) from ${data.total_scored} scored</h3>`;
            html += '<table><tr><th></th><th>Photo</th><th>Score</th><th>Resolution</th><th>Sharpness</th><th>Size</th><th>MP</th><th><input type="checkbox" id="sel-check-all"></th></tr>';

            for (const s of data.scores) {
                const barColor = s.overall_score >= 70 ? "#69db7c" : s.overall_score >= 40 ? "#ffd43b" : "#ff6b6b";
                html += `<tr>
                    <td><img src="/api/thumbnail?path=${encodeURIComponent(s.filepath)}" style="width:50px; height:40px; object-fit:cover; border-radius:3px" loading="lazy"></td>
                    <td>${esc(s.name)}</td>
                    <td>${s.overall_score}<span class="score-bar"><span class="score-bar-fill" style="width:${s.overall_score}%; background:${barColor}"></span></span></td>
                    <td>${s.resolution_score}</td>
                    <td>${s.sharpness_score}</td>
                    <td>${s.size_score}</td>
                    <td>${s.megapixels}</td>
                    <td><input type="checkbox" class="sel-check" value="${esc(s.filepath)}"></td>
                </tr>`;
            }
            html += '</table>';

            html += `<div class="action-bar">
                <input type="text" id="sel-tag-name" value="print" placeholder="Tag name" style="width:120px">
                <button id="sel-tag" class="btn-primary btn-small">Tag Selected</button>
                <button id="sel-export" class="btn-secondary btn-small">Export Selected</button>
            </div></div>`;

            results.innerHTML = html;

            // Check all toggle
            document.getElementById("sel-check-all").addEventListener("change", (e) => {
                results.querySelectorAll(".sel-check").forEach(cb => cb.checked = e.target.checked);
            });

            // Tag selected
            document.getElementById("sel-tag").addEventListener("click", async () => {
                const files = getSelected();
                if (!files.length) return;
                const tag = document.getElementById("sel-tag-name").value.trim() || "print";
                try {
                    const r = await api("/api/select/tag", { files, tag });
                    alert(`Tagged ${r.tagged} photo(s) as "${tag}"`);
                } catch (err) {
                    alert("Error: " + err.message);
                }
            });

            // Export selected
            document.getElementById("sel-export").addEventListener("click", async () => {
                const files = getSelected();
                if (!files.length) return;
                try {
                    const r = await api("/api/select/export", { files, output_file: directory + "/selection.txt" });
                    alert(`Exported ${r.exported} file(s) to ${r.output_file}`);
                } catch (err) {
                    alert("Error: " + err.message);
                }
            });

            function getSelected() {
                return Array.from(results.querySelectorAll(".sel-check:checked")).map(cb => cb.value);
            }
        } catch (err) {
            showError(results, err.message);
        }
    });
});
