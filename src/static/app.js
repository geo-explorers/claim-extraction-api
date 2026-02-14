// --- State ---
let currentClaims = [];

// --- DOM Elements ---
const sourceText = document.getElementById("source-text");
const generateBtn = document.getElementById("generate-btn");
const loading = document.getElementById("loading");
const errorDiv = document.getElementById("error");
const results = document.getElementById("results");
const totalCount = document.getElementById("total-count");
const claimsBody = document.getElementById("claims-body");
const exportBtn = document.getElementById("export-btn");

// --- Event Listeners ---
generateBtn.addEventListener("click", handleGenerate);
exportBtn.addEventListener("click", handleExport);

// --- Handlers ---
async function handleGenerate() {
    const text = sourceText.value.trim();
    if (!text) return;

    // Confirmation dialog if results already exist
    if (currentClaims.length > 0) {
        if (!confirm("This will replace the current results. Continue?")) return;
    }

    setLoading(true);
    hideError();

    try {
        const response = await fetch("/generate/claims", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ source_text: text }),
        });

        if (!response.ok) {
            let message = "An unexpected error occurred";
            try {
                const err = await response.json();
                message = err.detail || message;
            } catch {
                message = response.statusText || message;
            }
            throw new Error(message);
        }

        const data = await response.json();
        currentClaims = data.claims;
        renderClaims(currentClaims);
    } catch (err) {
        showError(err.message);
        results.classList.add("hidden");
    } finally {
        setLoading(false);
    }
}

// --- Rendering ---
function renderClaims(claims) {
    const grouped = groupByTopic(claims);
    totalCount.textContent = `${claims.length} claims extracted`;
    claimsBody.innerHTML = "";

    for (const [topic, topicClaims] of Object.entries(grouped)) {
        // Topic header row
        const headerRow = document.createElement("tr");
        headerRow.className = "bg-gray-100";
        headerRow.innerHTML = `<td class="border border-gray-200 px-3 py-2 font-bold text-sm">
            ${escapeHTML(topic)} (${topicClaims.length} claims)
        </td>`;
        claimsBody.appendChild(headerRow);

        // Claim rows
        for (const claim of topicClaims) {
            const row = document.createElement("tr");
            row.innerHTML = `<td class="border border-gray-200 px-3 py-2 text-sm">${escapeHTML(claim)}</td>`;
            claimsBody.appendChild(row);
        }
    }

    results.classList.remove("hidden");
}

// --- Helpers ---
function groupByTopic(claims) {
    const groups = {};
    for (const c of claims) {
        if (!groups[c.claim_topic]) groups[c.claim_topic] = [];
        groups[c.claim_topic].push(c.claim);
    }
    return groups;
}

function escapeHTML(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

function setLoading(on) {
    loading.classList.toggle("hidden", !on);
    generateBtn.disabled = on;
}

function showError(message) {
    errorDiv.textContent = message;
    errorDiv.classList.remove("hidden");
}

function hideError() {
    errorDiv.classList.add("hidden");
}

// --- CSV Export ---
function handleExport() {
    if (!currentClaims.length) return;
    const header = "claim_topic,claim";
    const rows = currentClaims.map(
        (c) => escapeCSV(c.claim_topic) + "," + escapeCSV(c.claim)
    );
    const csv = "\uFEFF" + [header, ...rows].join("\r\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "claims.csv";
    a.click();
    URL.revokeObjectURL(url);
}

function escapeCSV(value) {
    if (/[",\n\r]/.test(value)) {
        return '"' + value.replace(/"/g, '""') + '"';
    }
    return value;
}
