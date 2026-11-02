/**
 * Mail AI — Intelligent Business Email Classification
 * Frontend Application Controller & Chart.js Visualizations
 */

document.addEventListener("DOMContentLoaded", () => {
    // Global State
    let categoryChartInstance = null;
    let urgencyChartInstance = null;
    let riskChartInstance = null;
    let activePresetMap = {};
    let presetsByCategory = new Map();
    let selectedPresetId = null;
    let selectedEmailId = null;
    let classificationInFlight = false;

    // DOM Elements
    const kpiTotalEmails = document.getElementById("kpiTotalEmails");
    const kpiUrgentEmails = document.getElementById("kpiUrgentEmails");
    const kpiHighRisk = document.getElementById("kpiHighRisk");
    const kpiAccuracy = document.getElementById("kpiAccuracy");
    const kpiSampleCount = document.getElementById("kpiSampleCount");
    const refreshStatsBtn = document.getElementById("refreshStatsBtn");
    const resetDemoBtn = document.getElementById("resetDemoBtn");

    // Form Elements
    const classifyForm = document.getElementById("classifyForm");
    const emailSender = document.getElementById("emailSender");
    const emailSubject = document.getElementById("emailSubject");
    const emailBody = document.getElementById("emailBody");
    const sampleCategorySelect = document.getElementById("sampleCategorySelect");
    const relatedEmailList = document.getElementById("relatedEmailList");
    const analyzeSelectedEmailBtn = document.getElementById("analyzeSelectedEmailBtn");
    const classifyBtn = document.getElementById("classifyBtn");
    const saveToInboxBtn = document.getElementById("saveToInboxBtn");
    const clearFormBtn = document.getElementById("clearFormBtn");

    // Result Card Elements
    const resultCard = document.getElementById("resultCard");
    const resultPlaceholder = document.getElementById("resultPlaceholder");
    const resultContent = document.getElementById("resultContent");
    const resultConfidence = document.getElementById("resultConfidence");
    const resultCategory = document.getElementById("resultCategory");
    const resultUrgency = document.getElementById("resultUrgency");
    const resultRisk = document.getElementById("resultRisk");
    const resultRiskNote = document.getElementById("resultRiskNote");
    const resultSummary = document.getElementById("resultSummary");
    const categoryEvidenceList = document.getElementById("categoryEvidenceList");
    const priorityEvidenceList = document.getElementById("priorityEvidenceList");
    const resultAction = document.getElementById("resultAction");
    const resultActionDesc = document.getElementById("resultActionDesc");
    const resultDept = document.getElementById("resultDept");
    const resultSLA = document.getElementById("resultSLA");
    const riskIndicatorsContainer = document.getElementById("riskIndicatorsContainer");
    const riskIndicatorsTitle = document.getElementById("riskIndicatorsTitle");
    const riskIndicatorsList = document.getElementById("riskIndicatorsList");
    const riskIndicatorsDisclaimer = document.getElementById("riskIndicatorsDisclaimer");
    const resultKeyPhrases = document.getElementById("resultKeyPhrases");
    const probBarsList = document.getElementById("probBarsList");

    // Inbox Elements
    const inboxTableBody = document.getElementById("inboxTableBody");
    const inboxSearchInput = document.getElementById("inboxSearchInput");
    const filterCategory = document.getElementById("filterCategory");
    const filterUrgency = document.getElementById("filterUrgency");
    const filterRisk = document.getElementById("filterRisk");
    const filterStatus = document.getElementById("filterStatus");
    const resetFiltersBtn = document.getElementById("resetFiltersBtn");
    const inboxCountBadge = document.getElementById("inboxCountBadge");

    // Modal Elements
    const emailModal = document.getElementById("emailModal");
    const closeModalBtn = document.getElementById("closeModalBtn");
    const modalSubject = document.getElementById("modalSubject");
    const modalBody = document.getElementById("modalBody");
    const modalFooter = document.getElementById("modalFooter");
    const toastContainer = document.getElementById("toastContainer");

    async function apiRequest(url, options = {}) {
        let response;
        try {
            response = await fetch(url, options);
        } catch (error) {
            throw new Error("Mail AI is unavailable. Check that the Flask server is running and try again.");
        }

        let payload;
        try {
            payload = await response.json();
        } catch (error) {
            throw new Error("The server returned an unreadable response. Please try again.");
        }

        if (!response.ok || !payload.success) {
            throw new Error(payload.error || `Request failed (${response.status}).`);
        }
        return payload;
    }

    function setBusy(element, busy, loadingLabel = "Loading...") {
        if (!element) return;
        if (!element.dataset.idleMarkup) element.dataset.idleMarkup = element.innerHTML;
        element.disabled = busy;
        element.setAttribute("aria-busy", String(busy));
        element.classList.toggle("is-loading", busy);
        element.innerHTML = busy
            ? `<span class="loading-spinner" aria-hidden="true"></span>${escapeHtml(loadingLabel)}`
            : element.dataset.idleMarkup;
    }

    // --- Toast Notifications ---
    function showToast(message, type = "info") {
        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        const icon = document.createElement("span");
        icon.textContent = type === "success" ? "✓" : type === "error" ? "✕" : "ℹ";
        const text = document.createElement("span");
        text.textContent = message;
        toast.append(icon, text);
        toastContainer.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateX(100%)";
            toast.style.transition = "all 0.3s ease";
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }

    // --- Chart.js Configuration Helper ---
    Chart.defaults.color = "#9CA3AF";
    Chart.defaults.font.family = "'Plus Jakarta Sans', system-ui, sans-serif";

    function updateChart(instance, canvasId, config, hasData) {
        const canvas = document.getElementById(canvasId);
        if (!hasData) {
            canvas.hidden = true;
            if (instance) instance.destroy();
            return null;
        }

        canvas.hidden = false;
        if (instance) {
            instance.data.labels = config.data.labels;
            instance.data.datasets = config.data.datasets;
            instance.options = config.options;
            instance.update("none");
            return instance;
        }
        return new Chart(canvas.getContext("2d"), config);
    }

    function initCharts(stats) {
        const categoryCounts = stats.category_counts || {};
        const priorityCounts = stats.priority_counts || stats.urgency_counts || {};
        const riskCounts = stats.risk_counts || {};
        const classifiedCount = Number(stats.classified_emails ?? Object.values(categoryCounts).reduce((sum, count) => sum + count, 0));
        const hasData = classifiedCount > 0;
        document.getElementById("dashboardEmptyState").hidden = hasData;
        document.getElementById("dashboardCharts").hidden = !hasData;

        if (!hasData) {
            categoryChartInstance = updateChart(categoryChartInstance, "categoryChart", {}, false);
            urgencyChartInstance = updateChart(urgencyChartInstance, "urgencyChart", {}, false);
            riskChartInstance = updateChart(riskChartInstance, "riskChart", {}, false);
            return;
        }

        const categoryLabels = Object.keys(categoryCounts);
        const categoryColors = ["#3B82F6", "#8B5CF6", "#F59E0B", "#06B6D4", "#10B981", "#EF4444", "#9CA3AF"];
        categoryChartInstance = updateChart(categoryChartInstance, "categoryChart", {
            type: "doughnut",
            data: {
                labels: categoryLabels,
                datasets: [{
                    data: categoryLabels.map(label => categoryCounts[label]),
                    backgroundColor: categoryLabels.map((_, index) => categoryColors[index % categoryColors.length]),
                    borderWidth: 2,
                    borderColor: "#111827"
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: { boxWidth: 12, padding: 10, font: { size: 10 } }
                    }
                },
                cutout: "68%"
            }
        }, true);

        const priorityOrder = ["Urgent", "High", "Medium", "Low"];
        urgencyChartInstance = updateChart(urgencyChartInstance, "urgencyChart", {
            type: "bar",
            data: {
                labels: priorityOrder.map(priority => `${priority} Priority`),
                datasets: [{
                    label: "Classified emails",
                    data: priorityOrder.map(priority => priorityCounts[priority] || 0),
                    backgroundColor: ["#EF4444", "#F87171", "#F59E0B", "#6B7280"],
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: true, position: "top" }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { stepSize: 1 },
                        grid: { color: "rgba(255, 255, 255, 0.05)" }
                    },
                    x: { grid: { display: false } }
                }
            }
        }, true);

        const riskOrder = ["High", "Medium", "Low"];
        riskChartInstance = updateChart(riskChartInstance, "riskChart", {
            type: "doughnut",
            data: {
                labels: ["High Risk Prediction", "Medium Risk", "Low Risk"],
                datasets: [{
                    data: riskOrder.map(level => riskCounts[level] || 0),
                    backgroundColor: ["#EF4444", "#F59E0B", "#10B981"],
                    borderWidth: 2,
                    borderColor: "#111827"
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: { boxWidth: 12, padding: 12, font: { size: 11 } }
                    }
                },
                cutout: "62%"
            }
        }, true);
    }

    // --- Fetch Dashboard Analytics ---
    async function loadDashboardStats() {
        setBusy(refreshStatsBtn, true, "Refreshing...");
        try {
            const json = await apiRequest("/api/dashboard/stats");
            const data = json.data;
            kpiTotalEmails.textContent = data.classified_emails ?? data.total_emails ?? 0;
            kpiUrgentEmails.textContent = data.urgent_emails ?? data.priority_counts?.Urgent ?? 0;
            kpiHighRisk.textContent = data.high_risk_emails ?? 0;

            if (data.model_metrics && Number.isFinite(data.model_metrics.category_accuracy)) {
                const accPercent = (data.model_metrics.category_accuracy * 100).toFixed(1);
                kpiAccuracy.textContent = `${accPercent}%`;
                if (Number.isFinite(data.model_metrics.sample_count)) {
                    kpiSampleCount.textContent = `${data.model_metrics.sample_count} training samples`;
                }
            }

            initCharts(data);
        } catch (err) {
            console.error("Dashboard stats error:", err);
            showToast(err.message, "error");
        } finally {
            setBusy(refreshStatsBtn, false);
        }
    }

    // --- Load Demo Presets ---
    async function loadPresets() {
        try {
            const json = await apiRequest("/api/dashboard/presets");

            sampleCategorySelect.innerHTML = '<option value="">-- Choose a category --</option>';
            activePresetMap = {};
            presetsByCategory = new Map();

            json.data.forEach(preset => {
                activePresetMap[preset.id] = preset;
                const category = preset.title.split(":", 1)[0].trim();
                if (!presetsByCategory.has(category)) {
                    presetsByCategory.set(category, []);
                }
                presetsByCategory.get(category).push(preset);
            });

            [...presetsByCategory.keys()].sort().forEach(category => {
                const option = document.createElement("option");
                option.value = category;
                option.textContent = category;
                sampleCategorySelect.appendChild(option);
            });

            renderRelatedEmails();
        } catch (err) {
            console.error("Presets error:", err);
            showToast(err.message, "error");
        }
    }

    function renderRelatedEmails() {
        const category = sampleCategorySelect.value;
        const presets = presetsByCategory.get(category) || [];
        analyzeSelectedEmailBtn.disabled = !selectedPresetId;

        if (!category) {
            relatedEmailList.innerHTML = '<p class="related-email-empty">Choose a category to see related emails.</p>';
            return;
        }
        if (presets.length === 0) {
            relatedEmailList.innerHTML = '<p class="related-email-empty">No sample emails are available for this category.</p>';
            return;
        }

        relatedEmailList.innerHTML = presets.map(preset => {
            const title = preset.title.split(":").slice(1).join(":").trim();
            return `
                <button type="button" class="related-email-option ${String(preset.id) === selectedPresetId ? "selected" : ""}"
                    data-preset-id="${escapeHtml(preset.id)}"
                    aria-pressed="${String(preset.id) === selectedPresetId}">
                    <span class="related-email-option-title">${escapeHtml(title)}</span>
                    <span class="related-email-option-preview">${escapeHtml(preset.subject)}</span>
                </button>
            `;
        }).join("");
    }

    sampleCategorySelect.addEventListener("change", (e) => {
        selectedPresetId = null;
        renderRelatedEmails();
    });

    relatedEmailList.addEventListener("click", (e) => {
        const option = e.target.closest(".related-email-option");
        if (!option) return;
        const preset = activePresetMap[option.dataset.presetId];
        if (!preset) {
            showToast("That sample email is no longer available. Refresh and try again.", "error");
            return;
        }

        selectedPresetId = String(preset.id);
        emailSender.value = preset.sender;
        emailSubject.value = preset.subject;
        emailBody.value = preset.body;
        renderRelatedEmails();
        showToast(`Selected email: ${preset.title}`, "info");
    });

    clearFormBtn.addEventListener("click", () => {
        classifyForm.reset();
        sampleCategorySelect.value = "";
        selectedPresetId = null;
        renderRelatedEmails();
        selectedEmailId = null;
        document.querySelectorAll("#inboxTableBody tr.selected").forEach(row => row.classList.remove("selected"));
        emailModal.classList.add("hidden");
        resultCard.classList.add("hidden");
        resultContent.classList.add("hidden");
        resultPlaceholder.style.display = "flex";
    });

    // --- Render Classification UI ---
    function renderClassificationResult(data, displayOnPage = true) {
        if (displayOnPage) {
            resultCard.classList.remove("hidden");
            resultPlaceholder.style.display = "none";
            resultContent.classList.remove("hidden");
        }

        const confidence = Number(data.confidence ?? data.category_confidence);
        const conf = Number.isFinite(confidence) ? Math.round(Math.max(0, Math.min(1, confidence)) * 100) : 0;
        resultConfidence.textContent = `${conf}% category model score (uncalibrated)`;

        // Category
        resultCategory.textContent = data.category;

        // Priority / Urgency
        const prioVal = data.priority || data.urgency || "Low";
        resultUrgency.className = `badge-urgency ${safeClassToken(prioVal, ["low", "medium", "high", "urgent"], "low")}`;
        resultUrgency.textContent = `${prioVal} Priority`;

        // Risk Level
        resultRisk.className = `badge-risk ${safeClassToken(data.risk_level, ["low", "medium", "high"], "low")}`;
        resultRisk.textContent = `${data.risk_level} Risk`;
        resultRiskNote.textContent = data.risk_level === "High"
            ? "High-risk model prediction. Human review required; this is not proof of maliciousness."
            : "Model risk estimate; not a guarantee.";

        resultSummary.textContent = data.summary || "No extractive summary is available for this email.";

        function renderEvidence(container, features) {
            container.replaceChildren();
            if (!Array.isArray(features) || features.length === 0) {
                const empty = document.createElement("span");
                empty.className = "text-muted text-sm";
                empty.textContent = "No supported feature signals.";
                container.appendChild(empty);
                return;
            }
            features.forEach(feature => {
                const tag = document.createElement("span");
                tag.className = "nlp-tag";
                tag.textContent = feature;
                container.appendChild(tag);
            });
        }
        renderEvidence(categoryEvidenceList, data.category_evidence);
        renderEvidence(priorityEvidenceList, data.priority_evidence);

        // Suggested Action
        resultAction.textContent = data.suggested_action || "PROCESS";
        resultActionDesc.textContent = data.action_description || "";
        resultDept.textContent = data.routed_department || "General";
        resultSLA.textContent = data.sla || "Normal";

        // Risk Triggers
        const indicators = data.risk_indicators || [];
        const needsRiskReview = indicators.length > 0 || data.risk_level === "High";
        if (needsRiskReview) {
            riskIndicatorsContainer.classList.remove("hidden");
            riskIndicatorsTitle.textContent = indicators.length
                ? "Potential risk indicators for human review:"
                : "High-risk model prediction for human review:";
            riskIndicatorsDisclaimer.textContent = data.risk_indicators_disclaimer
                || "Keyword and pattern matches are review cues; they do not prove malicious intent.";
            riskIndicatorsList.innerHTML = indicators.length ? indicators
                .map(ind => `<span class="indicator-tag">⚠️ ${escapeHtml(ind)}</span>`)
                .join("")
                : '<span class="text-muted text-sm">No configured pattern matched; review the email context.</span>';
        } else {
            riskIndicatorsContainer.classList.add("hidden");
            riskIndicatorsList.innerHTML = "";
        }

        // Key Phrases
        const phrases = data.key_phrases || [];
        if (phrases.length > 0) {
            resultKeyPhrases.innerHTML = phrases
                .map(p => `<span class="nlp-tag">#${escapeHtml(p)}</span>`)
                .join("");
        } else {
            resultKeyPhrases.innerHTML = '<span class="text-muted text-sm">None detected</span>';
        }

        // Probability Distribution Bars
        const probs = data.category_probabilities || {};
        const sortedCats = Object.entries(probs).sort((a, b) => b[1] - a[1]);
        probBarsList.innerHTML = sortedCats.map(([cat, score]) => {
            const numericScore = Number(score);
            const pct = Number.isFinite(numericScore)
                ? Math.round(Math.max(0, Math.min(1, numericScore)) * 100)
                : 0;
            return `
                <div class="prob-bar-row">
                    <div class="prob-bar-info">
                        <span>${escapeHtml(cat)}</span>
                        <span>${pct}%</span>
                    </div>
                    <div class="prob-progress">
                        <div class="prob-fill" style="width: ${pct}%"></div>
                    </div>
                </div>
            `;
        }).join("");
    }

    async function classifyAndSave(endpoint) {
        if (classificationInFlight) return;
        if (!classifyForm.reportValidity()) return;

        const payload = {
            sender: emailSender.value.trim(),
            subject: emailSubject.value.trim(),
            body: emailBody.value.trim()
        };

        if (!payload.subject) {
            showToast("Enter an email subject with meaningful text.", "error");
            emailSubject.focus();
            return;
        }
        if (!payload.body) {
            showToast("Enter an email body with meaningful text.", "error");
            emailBody.focus();
            return;
        }

        classificationInFlight = true;
        setBusy(classifyBtn, true, "Classifying...");
        setBusy(saveToInboxBtn, true, "Classifying...");
        setBusy(analyzeSelectedEmailBtn, true, "Classifying...");
        try {
            const json = await apiRequest(endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            renderClassificationResult(json.data);
            selectedEmailId = json.data.id ? String(json.data.id) : null;
            showToast("Email classified and saved to the inbox.", "success");
            await Promise.all([loadDashboardStats(), loadInbox()]);
        } catch (err) {
            console.error("Classification error:", err);
            showToast(err.message, "error");
        } finally {
            setBusy(classifyBtn, false);
            setBusy(saveToInboxBtn, false);
            setBusy(analyzeSelectedEmailBtn, false);
            analyzeSelectedEmailBtn.disabled = !selectedPresetId;
            classificationInFlight = false;
        }
    }

    // --- Classify Email ---
    classifyForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        await classifyAndSave("/api/emails/classify");
    });

    // --- Save to Inbox Button ---
    saveToInboxBtn.addEventListener("click", async () => {
        await classifyAndSave("/api/emails");
    });

    analyzeSelectedEmailBtn.addEventListener("click", async () => {
        await classifyAndSave("/api/emails/classify");
    });

    // --- Load Inbox Table ---
    async function loadInbox() {
        inboxTableBody.setAttribute("aria-busy", "true");
        inboxCountBadge.textContent = "Loading...";
        inboxTableBody.innerHTML = '<tr><td colspan="8" class="text-center py-4"><span class="loading-spinner" aria-hidden="true"></span> Loading inbox...</td></tr>';
        const params = new URLSearchParams();
        if (inboxSearchInput.value.trim()) params.append("search", inboxSearchInput.value.trim());
        if (filterCategory.value) params.append("category", filterCategory.value);
        if (filterUrgency.value) params.append("priority", filterUrgency.value);
        if (filterRisk.value) params.append("risk_level", filterRisk.value);
        if (filterStatus.value) params.append("status", filterStatus.value);

        try {
            const json = await apiRequest(`/api/emails?${params.toString()}`);

            const emails = json.data || [];
            inboxCountBadge.textContent = `${json.total ?? emails.length} Emails`;

            if (emails.length === 0) {
                inboxTableBody.innerHTML = `
                    <tr>
                        <td colspan="8" class="text-center py-4" style="color: var(--text-muted);">
                            No emails matched the selected filters.
                        </td>
                    </tr>
                `;
                return;
            }

            inboxTableBody.innerHTML = emails.map(email => {
                const statusCls = safeClassToken(email.status, ["unread", "read", "resolved", "escalated", "archived"], "unread");
                const prioVal = email.priority || email.urgency || "Low";
                const urgCls = safeClassToken(prioVal, ["low", "medium", "high", "urgent"], "low");
                const riskCls = safeClassToken(email.risk_level, ["low", "medium", "high"], "low");

                return `
                    <tr data-id="${email.id}" class="${String(email.id) === selectedEmailId ? "selected" : ""}">
                        <td>
                            <span class="badge-status ${statusCls}">${escapeHtml(email.status)}</span>
                        </td>
                        <td class="email-sender-col" title="${escapeHtml(email.sender)}">
                            ${escapeHtml(email.sender)}
                        </td>
                        <td class="email-subject-col">
                            <span class="email-subject-title">${escapeHtml(email.subject)}</span>
                            <span class="email-subject-preview">${escapeHtml(email.body.slice(0, 75))}...</span>
                        </td>
                        <td>
                            <span class="badge-category">${escapeHtml(email.category)}</span>
                        </td>
                        <td>
                            <span class="badge-urgency ${urgCls}">${escapeHtml(prioVal)}</span>
                        </td>
                        <td>
                            <span class="badge-risk ${riskCls}">${escapeHtml(email.risk_level)}</span>
                        </td>
                        <td style="font-size: 0.78rem; color: var(--text-muted);">
                            ${escapeHtml(email.routed_department || "General")}
                        </td>
                        <td>
                            <div class="row-actions">
                                <button class="action-btn view-btn" data-id="${email.id}" title="View Analysis Details">View</button>
                                <button class="action-btn resolve-btn" data-id="${email.id}" title="Mark Resolved">✓</button>
                                <button class="action-btn delete delete-btn" data-id="${email.id}" title="Delete Email">✕</button>
                            </div>
                        </td>
                    </tr>
                `;
            }).join("");

            // Attach Row Action Listeners
            document.querySelectorAll(".view-btn").forEach(btn => {
                btn.addEventListener("click", (e) => {
                    e.stopPropagation();
                    openEmailModal(btn.dataset.id);
                });
            });

            document.querySelectorAll(".resolve-btn").forEach(btn => {
                btn.addEventListener("click", (e) => {
                    e.stopPropagation();
                    updateEmailStatus(btn.dataset.id, "Resolved");
                });
            });

            document.querySelectorAll(".delete-btn").forEach(btn => {
                btn.addEventListener("click", (e) => {
                    e.stopPropagation();
                    deleteEmail(btn.dataset.id);
                });
            });

            // Clicking row also opens modal
            document.querySelectorAll("#inboxTableBody tr").forEach(row => {
                row.addEventListener("click", () => {
                    const id = row.dataset.id;
                    if (id) openEmailModal(id);
                });
            });

        } catch (err) {
            console.error("Inbox load error:", err);
            inboxCountBadge.textContent = "Inbox unavailable";
            inboxTableBody.innerHTML = `<tr><td colspan="8" class="text-center py-4">${escapeHtml(err.message)}</td></tr>`;
            showToast(err.message, "error");
        } finally {
            inboxTableBody.setAttribute("aria-busy", "false");
        }
    }

    // --- Search & Filters Handlers ---
    let debounceTimer = null;
    inboxSearchInput.addEventListener("input", () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(loadInbox, 300);
    });

    [filterCategory, filterUrgency, filterRisk, filterStatus].forEach(el => {
        el.addEventListener("change", loadInbox);
    });

    resetFiltersBtn.addEventListener("click", () => {
        inboxSearchInput.value = "";
        filterCategory.value = "";
        filterUrgency.value = "";
        filterRisk.value = "";
        filterStatus.value = "";
        loadInbox();
    });

    // --- Email Modal ---
    async function openEmailModal(emailId) {
        selectedEmailId = String(emailId);
        document.querySelectorAll("#inboxTableBody tr").forEach(row => {
            row.classList.toggle("selected", row.dataset.id === selectedEmailId);
        });
        emailModal.classList.remove("hidden");
        modalBody.setAttribute("aria-busy", "true");
        modalBody.innerHTML = '<span class="loading-spinner" aria-hidden="true"></span> Loading email details...';
        try {
            const json = await apiRequest(`/api/emails/${emailId}`);

            const email = json.data;
            renderClassificationResult(email, false);
            modalSubject.textContent = email.subject;

            const confidence = Number(email.confidence ?? email.category_confidence);
            const conf = Number.isFinite(confidence) ? Math.round(Math.max(0, Math.min(1, confidence)) * 100) : 0;
            const statusCls = safeClassToken(email.status, ["unread", "read", "resolved", "escalated", "archived"], "unread");
            const prioVal = email.priority || email.urgency || "Low";
            const urgCls = safeClassToken(prioVal, ["low", "medium", "high", "urgent"], "low");
            const riskCls = safeClassToken(email.risk_level, ["low", "medium", "high"], "low");

            modalBody.innerHTML = `
                <div class="modal-meta-grid">
                    <div><strong>From:</strong> ${escapeHtml(email.sender)}</div>
                    <div><strong>To:</strong> ${escapeHtml(email.recipient || "support@mailai.enterprise.com")}</div>
                    <div><strong>Status:</strong> <span class="badge-status ${statusCls}">${escapeHtml(email.status)}</span></div>
                    <div><strong>Received:</strong> ${escapeHtml(email.received_at || email.created_at || "Just now")}</div>
                </div>

                <div class="result-badges-row">
                    <div class="classification-pill-card">
                        <span class="card-label">Predicted Category</span>
                        <div class="badge-category">${escapeHtml(email.category)}</div>
                        <span style="font-size: 0.72rem; color: #34D399;">Category score: ${conf}% (uncalibrated)</span>
                    </div>

                    <div class="classification-pill-card">
                        <span class="card-label">Priority SLA</span>
                        <div class="badge-urgency ${urgCls}">${escapeHtml(prioVal)} Priority</div>
                        <span style="font-size: 0.72rem; color: var(--text-muted);">SLA: ${escapeHtml(email.sla || "Normal")}</span>
                    </div>

                    <div class="classification-pill-card">
                        <span class="card-label">Security Risk</span>
                        <div class="badge-risk ${riskCls}">${escapeHtml(email.risk_level)} Risk</div>
                        <span style="font-size: 0.72rem; color: var(--text-muted);">${email.risk_level === 'High' ? 'High model risk; review required' : `Model-assigned level: ${escapeHtml(email.risk_level)}`}</span>
                    </div>
                </div>

                <div class="modal-insight-block">
                    <strong>Extractive email summary</strong>
                    <p>${escapeHtml(email.summary || "No extractive summary is available for this email.")}</p>
                    <small>Lead sentences copied from the email; no new facts generated.</small>
                </div>

                <div class="modal-insight-block">
                    <strong>Text features associated with predictions</strong>
                    <p>Positive TF-IDF and model-coefficient signals; these are context, not verified facts.</p>
                    <div class="evidence-columns">
                        <div><span class="card-label">Category</span><div class="tags-row">${(email.category_evidence || []).map(feature => `<span class="nlp-tag">${escapeHtml(feature)}</span>`).join("") || '<span class="text-muted text-sm">No supported feature signals.</span>'}</div></div>
                        <div><span class="card-label">Priority</span><div class="tags-row">${(email.priority_evidence || []).map(feature => `<span class="nlp-tag">${escapeHtml(feature)}</span>`).join("") || '<span class="text-muted text-sm">No supported feature signals.</span>'}</div></div>
                    </div>
                </div>

                <div class="action-recommendation-box">
                    <span class="action-label">Suggested workflow action (not executed):</span>
                    <h4 class="action-title">${escapeHtml(email.suggested_action)}</h4>
                    <p class="action-desc">${escapeHtml(email.action_description || 'Route to appropriate department queue.')}</p>
                    <div class="routing-meta">
                        <div><strong>Target Department:</strong> ${escapeHtml(email.routed_department || "General")}</div>
                        <div><strong>SLA Target:</strong> ${escapeHtml(email.sla || "Normal")}</div>
                    </div>
                </div>

                ${(email.risk_indicators?.length || email.risk_level === 'High') ? `
                    <div class="risk-indicators-box">
                        <span class="risk-indicators-title">Potential risk indicators for human review:</span>
                        <div class="indicators-list">
                            ${(email.risk_indicators || []).map(ind => `<span class="indicator-tag">⚠️ ${escapeHtml(ind)}</span>`).join('') || '<span class="text-muted text-sm">No configured pattern matched; review the email context.</span>'}
                        </div>
                        <p class="evidence-note">${escapeHtml(email.risk_indicators_disclaimer || "Keyword and pattern matches are review cues; they do not prove malicious intent.")}</p>
                    </div>
                ` : ''}

                <div>
                    <strong style="font-size: 0.8rem; text-transform: uppercase; color: var(--text-muted); display: block; margin-bottom: 0.4rem;">Email Body Content:</strong>
                    <div class="modal-email-body">${escapeHtml(email.body)}</div>
                </div>
            `;

            modalFooter.innerHTML = `
                <button class="btn btn-secondary btn-sm" id="modalCloseAction">Close</button>
                <button class="btn btn-secondary btn-sm" id="modalEscalateAction">Escalate</button>
                <button class="btn btn-primary btn-sm" id="modalResolveAction">Mark Resolved</button>
            `;

            document.getElementById("modalCloseAction").onclick = () => emailModal.classList.add("hidden");
            document.getElementById("modalEscalateAction").onclick = () => {
                updateEmailStatus(emailId, "Escalated");
                emailModal.classList.add("hidden");
            };
            document.getElementById("modalResolveAction").onclick = () => {
                updateEmailStatus(emailId, "Resolved");
                emailModal.classList.add("hidden");
            };

            emailModal.classList.remove("hidden");
        } catch (err) {
            console.error("Modal error:", err);
            modalBody.textContent = err.message;
            showToast(err.message, "error");
        } finally {
            modalBody.setAttribute("aria-busy", "false");
        }
    }

    closeModalBtn.addEventListener("click", () => emailModal.classList.add("hidden"));
    emailModal.addEventListener("click", (e) => {
        if (e.target === emailModal) emailModal.classList.add("hidden");
    });

    // --- Status & Delete Operations ---
    async function updateEmailStatus(emailId, newStatus) {
        try {
            await apiRequest(`/api/emails/${emailId}/status`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ status: newStatus })
            });

            showToast(`Status updated to '${newStatus}'`, "success");
            await Promise.all([loadInbox(), loadDashboardStats()]);
        } catch (err) {
            console.error("Status update error:", err);
            showToast(err.message, "error");
        }
    }

    async function deleteEmail(emailId) {
        if (!confirm("Are you sure you want to delete this email record?")) return;

        try {
            await apiRequest(`/api/emails/${emailId}`, { method: "DELETE" });

            if (selectedEmailId === String(emailId)) {
                selectedEmailId = null;
                emailModal.classList.add("hidden");
                resultContent.classList.add("hidden");
                resultPlaceholder.style.display = "flex";
            }

            showToast("Email deleted successfully.", "success");
            await Promise.all([loadInbox(), loadDashboardStats()]);
        } catch (err) {
            console.error("Delete error:", err);
            showToast(err.message, "error");
        }
    }

    // --- Reset Demo Database ---
    resetDemoBtn.addEventListener("click", async () => {
        if (!confirm("Reset database to initial demo state? All newly classified items will be restored to defaults.")) return;

        setBusy(resetDemoBtn, true, "Resetting...");
        try {
            await apiRequest("/api/dashboard/reset-demo", { method: "POST" });

            selectedEmailId = null;
            emailModal.classList.add("hidden");
            showToast("Database restored to demo dataset!", "success");
            await Promise.all([loadDashboardStats(), loadInbox()]);
        } catch (err) {
            console.error("Reset error:", err);
            showToast(err.message, "error");
        } finally {
            setBusy(resetDemoBtn, false);
        }
    });

    refreshStatsBtn.addEventListener("click", async () => {
        await Promise.all([loadDashboardStats(), loadInbox()]);
        showToast("Telemetry metrics refreshed.", "info");
    });

    // --- Utility: HTML Escape ---
    function safeClassToken(value, allowedValues, fallback) {
        const normalized = typeof value === "string" ? value.toLowerCase() : "";
        return allowedValues.includes(normalized) ? normalized : fallback;
    }

    function escapeHtml(str) {
        if (typeof str !== "string") return "";
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // Initial Load
    loadDashboardStats();
    loadPresets();
    loadInbox();
});
