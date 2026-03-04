/* Group wizard page */

registerPage("group", function (container) {
    const state = {
        wizardId: null,
        step: 1,
        clusters: [],
        duplicates: {},
        config: {},
    };

    container.innerHTML = `
        <h2>Group Organize</h2>
        <p class="muted">Cluster photos by time, name groups, handle duplicates, and organize into folders.</p>
        <div id="grp-steps" class="wizard-steps"></div>
        <div id="grp-content"></div>
    `;

    const STEPS = ["Scan", "Name", "Dates", "Duplicates", "Preview", "Done"];

    function renderSteps() {
        const stepsDiv = document.getElementById("grp-steps");
        stepsDiv.innerHTML = STEPS.map((name, i) => {
            const num = i + 1;
            let cls = "wizard-step";
            if (num < state.step) cls += " completed";
            if (num === state.step) cls += " active";
            return `<div class="${cls}">${num}. ${name}</div>`;
        }).join("");
    }

    function render() {
        renderSteps();
        const content = document.getElementById("grp-content");
        switch (state.step) {
            case 1: renderScan(content); break;
            case 2: renderName(content); break;
            case 3: renderDates(content); break;
            case 4: renderDuplicates(content); break;
            case 5: renderPreview(content); break;
            case 6: renderDone(content); break;
        }
    }

    function renderScan(el) {
        el.innerHTML = `
            <div class="card">
                <div class="form-group">
                    <label>Source directory</label>
                    <div id="grp-src-input"></div>
                </div>
                <div class="form-group">
                    <label>Destination directory</label>
                    <div id="grp-dest-input"></div>
                </div>
                <div class="form-group">
                    <label>Naming pattern</label>
                    <input type="text" id="grp-pattern" value="{location}_{date}_{seq}">
                </div>
                <div class="form-group">
                    <label>Gap hours (time between groups)</label>
                    <input type="number" id="grp-gap" value="3" min="0.5" step="0.5" style="width:100px">
                </div>
                <button id="grp-scan" class="btn-primary">Scan & Group</button>
            </div>
        `;
        document.getElementById("grp-src-input").appendChild(pathInput("grp-src", "Source folder", "dir"));
        document.getElementById("grp-dest-input").appendChild(pathInput("grp-dest", "Destination folder", "dir"));

        document.getElementById("grp-scan").addEventListener("click", async () => {
            const source = document.getElementById("grp-src").value.trim();
            const destination = document.getElementById("grp-dest").value.trim();
            const pattern = document.getElementById("grp-pattern").value.trim();
            const gap_hours = parseFloat(document.getElementById("grp-gap").value) || 3.0;
            if (!source || !destination) return;

            state.config = { source, destination, pattern, gap_hours };
            showLoading(el, "Clustering photos...");

            try {
                const data = await api("/api/group/start", { source, destination, pattern, gap_hours });
                state.wizardId = data.wizard_id;
                state.clusters = data.clusters;
                state.duplicates = data.duplicates;
                state.step = 2;
                render();
            } catch (err) {
                showError(el, err.message);
            }
        });
    }

    function renderName(el) {
        const unnamed = state.clusters.filter(c => c.needs_name);
        if (unnamed.length === 0) {
            state.step = 3;
            render();
            return;
        }

        let html = '<div class="card"><h3>Name these groups</h3>';
        for (const c of state.clusters) {
            html += '<div class="inline-field" style="margin-bottom:12px">';
            html += `<label style="min-width:200px">Group ${c.index + 1} (${c.photo_count} photos, ${esc(c.date_range)})</label>`;
            if (c.needs_name) {
                html += `<input type="text" class="grp-name" data-idx="${c.index}" placeholder="e.g. Beach_Trip">`;
            } else {
                html += `<span class="muted">${esc(c.location)}</span>`;
            }
            html += '</div>';
            // Show sample thumbnails
            if (c.thumbnail_paths && c.thumbnail_paths.length) {
                html += '<div class="thumb-grid" style="margin-bottom:16px">';
                for (const p of c.thumbnail_paths) {
                    html += `<div class="thumb-item">
                        <img src="/api/thumbnail?path=${encodeURIComponent(p)}" loading="lazy">
                    </div>`;
                }
                html += '</div>';
            }
        }
        html += '<div class="action-bar"><button id="grp-name-next" class="btn-primary">Next</button></div>';
        html += '</div>';
        el.innerHTML = html;

        document.getElementById("grp-name-next").addEventListener("click", async () => {
            const names = {};
            el.querySelectorAll(".grp-name").forEach(input => {
                if (input.value.trim()) {
                    names[input.dataset.idx] = input.value.trim();
                }
            });
            showLoading(el, "Applying names...");
            try {
                const data = await api("/api/group/name", { wizard_id: state.wizardId, names });
                state.clusters = data.clusters;
                state.step = 3;
                render();
            } catch (err) {
                showError(el, err.message);
            }
        });
    }

    function renderDates(el) {
        const undated = state.clusters.filter(c => !c.has_date && !c.has_date_override);
        if (undated.length === 0) {
            state.step = 4;
            render();
            return;
        }

        // Show date context
        const dated = state.clusters.filter(c => c.has_date);
        let contextHtml = "";
        if (dated.length) {
            const ranges = dated.map(c => c.date_range);
            contextHtml = `<p class="muted" style="margin-bottom:12px">Other groups span: ${esc(ranges[0].split(" to ")[0])} to ${esc(ranges[ranges.length - 1].split(" to ")[1])}</p>`;
        }

        let html = `<div class="card"><h3>Set dates for undated groups</h3>${contextHtml}`;
        html += '<p class="muted" style="margin-bottom:16px">Enter a date (YYYY-MM-DD) or freeform text (e.g. "March_2023"). Leave blank to keep "undated".</p>';

        for (const c of undated) {
            html += `<div class="inline-field">
                <label style="min-width:200px">Group ${c.index + 1} — ${esc(c.location || "unnamed")} (${c.photo_count} photos)</label>
                <input type="text" class="grp-date" data-idx="${c.index}" placeholder="YYYY-MM-DD or freeform">
            </div>`;
        }
        html += '<div class="action-bar">';
        html += '<button id="grp-date-back" class="btn-secondary">Back</button>';
        html += '<button id="grp-date-next" class="btn-primary">Next</button>';
        html += '</div></div>';
        el.innerHTML = html;

        document.getElementById("grp-date-back").addEventListener("click", () => {
            state.step = 2;
            render();
        });

        document.getElementById("grp-date-next").addEventListener("click", async () => {
            const dates = {};
            el.querySelectorAll(".grp-date").forEach(input => {
                if (input.value.trim()) {
                    dates[input.dataset.idx] = input.value.trim();
                }
            });
            if (Object.keys(dates).length) {
                showLoading(el, "Setting dates...");
                try {
                    const data = await api("/api/group/dates", { wizard_id: state.wizardId, dates });
                    state.clusters = data.clusters;
                } catch (err) {
                    showError(el, err.message);
                    return;
                }
            }
            state.step = 4;
            render();
        });
    }

    function renderDuplicates(el) {
        const hasDupes = Object.keys(state.duplicates).length > 0;
        if (!hasDupes) {
            state.step = 5;
            render();
            return;
        }

        let html = '<div class="card"><h3>Handle Duplicates</h3>';
        html += '<p class="muted" style="margin-bottom:12px">Uncheck any files you want to keep.</p>';

        for (const [idx, groups] of Object.entries(state.duplicates)) {
            const cluster = state.clusters[parseInt(idx)];
            const groupName = cluster ? (cluster.location || `Group ${parseInt(idx) + 1}`) : `Group ${parseInt(idx) + 1}`;
            html += `<h4 style="margin:12px 0 8px; color:#aaa">${esc(groupName)}</h4>`;

            for (const group of groups) {
                html += '<div class="dupe-group">';
                html += `<div class="dupe-keep">Keep: ${esc(group.keep.name)}</div>`;
                for (const dupe of group.dupes) {
                    html += `<div class="dupe-remove">
                        <label><input type="checkbox" class="grp-dupe-check" value="${esc(dupe.path)}" checked>
                        Remove: ${esc(dupe.name)}</label>
                    </div>`;
                }
                html += '</div>';
            }
        }

        html += '<div class="action-bar">';
        html += '<button id="grp-dupe-back" class="btn-secondary">Back</button>';
        html += '<button id="grp-dupe-next" class="btn-primary">Next</button>';
        html += '</div></div>';
        el.innerHTML = html;

        document.getElementById("grp-dupe-back").addEventListener("click", () => {
            state.step = 3;
            render();
        });

        document.getElementById("grp-dupe-next").addEventListener("click", async () => {
            const exclude = Array.from(el.querySelectorAll(".grp-dupe-check:checked")).map(cb => cb.value);
            showLoading(el, "Confirming duplicates...");
            try {
                await api("/api/group/duplicates", { wizard_id: state.wizardId, exclude });
                state.step = 5;
                render();
            } catch (err) {
                showError(el, err.message);
            }
        });
    }

    function renderPreview(el) {
        showLoading(el, "Generating preview...");

        api("/api/group/preview", { wizard_id: state.wizardId }).then(data => {
            let html = '<div class="card">';
            html += `<h3>${data.count} file(s) to move`;
            if (data.excluded_count) html += `, ${data.excluded_count} duplicate(s) excluded`;
            html += '</h3>';
            html += `<div class="preview">${esc(data.preview)}</div>`;
            html += '<div class="action-bar">';
            html += '<button id="grp-prev-back" class="btn-secondary">Back</button>';
            html += '<button id="grp-prev-exec" class="btn-danger">Execute</button>';
            html += '</div></div>';
            el.innerHTML = html;

            document.getElementById("grp-prev-back").addEventListener("click", () => {
                state.step = 2;
                render();
            });

            document.getElementById("grp-prev-exec").addEventListener("click", async () => {
                showLoading(el, "Moving files...");
                try {
                    const result = await api("/api/group/execute", { wizard_id: state.wizardId });
                    state.executeResult = result;
                    state.step = 6;
                    render();
                } catch (err) {
                    showError(el, err.message);
                }
            });
        }).catch(err => {
            showError(el, err.message);
        });
    }

    function renderDone(el) {
        const result = state.executeResult || {};
        let html = '<div class="card"><h3>Complete</h3>';
        html += `<p class="success">Successfully moved ${result.success || 0} file(s).</p>`;
        if (result.failed > 0) {
            html += `<p class="error">${result.failed} file(s) failed.</p>`;
        }
        if (result.errors && result.errors.length) {
            html += '<ul>' + result.errors.map(e => `<li class="error">${esc(e)}</li>`).join("") + '</ul>';
        }
        if (result.undo_log) {
            html += `<p class="muted" style="margin-top:8px">Undo log: ${esc(result.undo_log)}</p>`;
            html += `<button id="grp-undo" class="btn-secondary" style="margin-top:8px">Undo</button>`;
        }
        html += `<div class="action-bar"><button id="grp-new" class="btn-primary">Start New</button></div>`;
        html += '</div>';
        el.innerHTML = html;

        if (result.undo_log) {
            document.getElementById("grp-undo").addEventListener("click", async () => {
                showLoading(el, "Undoing moves...");
                try {
                    const data = await api("/api/group/undo", { undo_log: result.undo_log });
                    el.innerHTML = "";
                    showResults(el, data);
                    const btn = document.createElement("button");
                    btn.className = "btn-primary";
                    btn.style.marginTop = "16px";
                    btn.textContent = "Start New";
                    btn.addEventListener("click", resetWizard);
                    el.appendChild(btn);
                } catch (err) {
                    showError(el, err.message);
                }
            });
        }

        document.getElementById("grp-new").addEventListener("click", resetWizard);
    }

    function resetWizard() {
        if (state.wizardId) {
            api("/api/group/cancel", { wizard_id: state.wizardId }).catch(() => {});
        }
        state.wizardId = null;
        state.step = 1;
        state.clusters = [];
        state.duplicates = {};
        state.executeResult = null;
        render();
    }

    render();
});
