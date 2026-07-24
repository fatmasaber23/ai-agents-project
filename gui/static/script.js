// ============================================================
// State
// ============================================================
let projectData = { A: {}, B: {} };
let executionMode = 'single'; // 'single' | 'compare'
let lastCompareResults = {}; // agentKey -> response json
let activeTraceTab = null;
 
const AGENT_ORDER = ['reactive', 'routing', 'constrained', 'unconstrained'];
const AGENT_NAMES = {
    reactive: 'Reactive Agent',
    routing: 'Routing Agent',
    constrained: 'Constrained ReAct Agent',
    unconstrained: 'Unconstrained LLM Agent'
};
const AGENT_DESCRIPTIONS = {
    reactive: 'Reactive Agent: A pure if/then rule chain. No AI calls — stops at the first rule that matches.',
    routing: 'Routing Agent: An LLM classifies the case into a review category from pre-computed differences, then deterministic Python code makes the final call.',
    constrained: 'Constrained ReAct Agent: Collects evidence step-by-step using tools, evaluates all factors together, and escalates to a human when evidence is balanced.',
    unconstrained: 'Unconstrained LLM Agent: The model freely chooses its own tools, order, and stopping point while investigating the case.'
};
 
// ============================================================
// Tiny markdown renderer
// (The model's free-text answers use **bold**, ### headings, - bullets,
// and --- dividers. Without converting these, they show up as raw
// symbols on screen. This turns them into real HTML so the answer reads
// like normal formatted text instead of a wall of asterisks.)
// ============================================================
function inlineMarkdown(text) {
    return text
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/`(.+?)`/g, '<code>$1</code>');
}
 
function renderMarkdown(md) {
    if (!md) return '';
    const lines = md.split('\n');
    let html = '';
    let listBuffer = [];
    let listType = null;
 
    function flushList() {
        if (listBuffer.length) {
            html += `<${listType}>` + listBuffer.map(item => `<li>${item}</li>`).join('') + `</${listType}>`;
            listBuffer = [];
            listType = null;
        }
    }
 
    lines.forEach(rawLine => {
        const line = rawLine.trim();
        let m;
 
        if (line === '') { flushList(); return; }
        if (/^-{3,}$/.test(line)) { flushList(); html += '<hr>'; return; }
 
        if ((m = line.match(/^(#{1,4})\s+(.*)$/))) {
            flushList();
            const level = Math.min(m[1].length + 2, 4);
            html += `<h${level}>${inlineMarkdown(m[2])}</h${level}>`;
            return;
        }
 
        if ((m = line.match(/^[-*]\s+(.*)$/))) {
            if (listType !== 'ul') { flushList(); listType = 'ul'; }
            listBuffer.push(inlineMarkdown(m[1]));
            return;
        }
 
        if ((m = line.match(/^\d+\.\s+(.*)$/))) {
            if (listType !== 'ol') { flushList(); listType = 'ol'; }
            listBuffer.push(inlineMarkdown(m[1]));
            return;
        }
 
        flushList();
        html += `<p>${inlineMarkdown(line)}</p>`;
    });
 
    flushList();
    return html;
}
 
function stripMarkdown(text) {
    if (!text) return '';
    return text.replace(/[#*`_>-]/g, ' ').replace(/\s+/g, ' ').trim();
}
 
// Pulls "Project A" / "ProjectB" (any spacing/case) out of the unconstrained
// agent's free-text answer so it can be shown as a short headline, the same
// way the other three agents already report their pick.
function extractRecommendedProject(text) {
    if (!text) return null;
    const m = text.match(/Project\s*([AB])\b/i);
    return m ? m[1].toUpperCase() : null;
}
 
// Turns a trace "detail" (plain string OR an object of raw field values)
// into readable markdown bullets instead of a raw JSON blob.
function humanizeKey(key) {
    return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}
function humanizeDetail(detail) {
    if (detail && typeof detail === 'object') {
        return Object.entries(detail)
            .map(([k, v]) => `- **${humanizeKey(k)}:** ${v}`)
            .join('\n');
    }
    return detail ? String(detail) : '';
}

// Compact, single-line version of humanizeDetail for use inside a <li> —
// e.g. "Greater Delay Impact: Project A, Project A Delay Days: 15" instead
// of a raw JSON blob.
function summarizeDetail(detail) {
    if (detail && typeof detail === 'object') {
        return Object.entries(detail)
            .map(([k, v]) => `${humanizeKey(k)}: ${v}`)
            .join(', ');
    }
    return detail ? String(detail) : '';
}

// Lightly tokenizes the raw agent log (the exact text the terminal run
// prints) so it reads like syntax-highlighted output instead of a flat
// wall of monospace text. Purely cosmetic — never changes the text itself.
function formatTrace(text) {
    const esc = (text || '(no raw output returned)')
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return esc.split('\n').map(line => {
        if (/^=+$/.test(line.trim())) return `<span class="tk-rule">${line}</span>`;
        if (/^\s*(REACTIVE|ROUTING|CONSTRAINED REACT|UNCONSTRAINED LLM).*RESULT\s*$/.test(line)) return `<span class="tk-head">${line}</span>`;
        if (/^\s*=== FINAL ANSWER ===/.test(line)) return `<span class="tk-final">${line}</span>`;
        if (/^\s*Step \d+/.test(line)) return line.replace(/^(\s*Step \d+[:.]?)/, '<span class="tk-step">$1</span>');
        if (/→\s*(Called|Observation|Escalated|Final Answer)/.test(line)) return line.replace(/(→\s*(Called|Observation|Escalated|Final Answer))/, '<span class="tk-arrow">$1</span>');
        if (/^\s*Observation/.test(line)) return line.replace(/^(\s*Observation[:.]?)/, '<span class="tk-obs">$1</span>');
        if (/^\s*[•·]/.test(line)) return line.replace(/^(\s*[•·])/, '<span class="tk-bullet">$1</span>');
        if (/^\s*(Status|Steps Used|Recommended|Rule fired|Reason|Selected Review|Equipment Assigned To|Escalation Reason)\s*:/.test(line)) return line.replace(/^(\s*[A-Za-z ]+:)/, '<span class="tk-head">$1</span>');
        return line;
    }).join('\n');
}

// Copy-to-clipboard for the terminal-style trace boxes.
async function copyTraceText(bodyId, btn) {
    const body = document.getElementById(bodyId);
    const text = body.innerText;
    try {
        await navigator.clipboard.writeText(text);
    } catch (e) {
        const ta = document.createElement('textarea');
        ta.value = text; document.body.appendChild(ta); ta.select();
        document.execCommand('copy'); document.body.removeChild(ta);
    }
    const original = btn.textContent;
    btn.classList.add('copied');
    btn.textContent = 'Copied ✓';
    setTimeout(() => { btn.classList.remove('copied'); btn.textContent = original; }, 1500);
}
 
// Builds a readable "why did the agent decide this" explanation for any
// agent, in the same prose/markdown style the unconstrained agent already
// produces on its own, so all four agents feel equally explained.
function buildExplanationMarkdown(agentKey, data) {
    if (agentKey === 'unconstrained') {
        return data.final_answer || '';
    }
 
    if (agentKey === 'reactive') {
        const step = (data.trace || [])[0];
        if (!step) return '';
        return `### Rule Applied: ${step.label}\n${step.detail}`;
    }
 
    if (agentKey === 'routing') {
        const step = (data.trace || [])[0];
        let md = `### Category: ${step ? step.label : '—'}\n`;
        if (step && step.detail) {
            md += step.detail.split(';').map(r => `- ${r.trim()}`).join('\n') + '\n';
        }
        if (data.other_project) {
            md += `\n**${data.other_project} should:** ${data.other_project_action}`;
        }
        return md;
    }
 
    if (agentKey === 'constrained') {
        let md = '';
        (data.trace || []).forEach(step => {
            md += `### Step ${step.step}: ${step.label}\n`;
            md += humanizeDetail(step.detail) + '\n\n';
        });
        return md;
    }
 
    return '';
}
 
// ============================================================
// Reading form data into state
// ============================================================
function getBool(id) {
    const wrap = document.querySelector(`.toggle-pair[data-target="${id}"]`);
    const active = wrap.querySelector('.toggle-btn.active');
    return active.dataset.value === 'true';
}
 
function collectProjectData() {
    ['A', 'B'].forEach(p => {
        projectData[p] = {
            delay: parseFloat(document.getElementById(`${p}-delay`).value) || 0,
            hasPenalty: getBool(`${p}-hasPenalty`),
            penaltyAmount: parseFloat(document.getElementById(`${p}-penaltyAmount`).value) || 0,
            hasAlt: getBool(`${p}-hasAlt`),
            rentalCost: parseFloat(document.getElementById(`${p}-rentalCost`).value) || 0
        };
    });
}
 
// Toggle buttons (Yes/No pairs)
document.addEventListener('click', function (e) {
    const btn = e.target.closest('.toggle-btn');
    if (!btn) return;
    const wrap = btn.closest('.toggle-pair');
    wrap.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
});
 
// ============================================================
// Navigation: Data -> Mode
// ============================================================
function goToMode() {
    collectProjectData();
    goTo('screen-mode');
}
 
function selectMode(mode) {
    executionMode = mode;
    document.getElementById('mode-single').classList.toggle('active', mode === 'single');
    document.getElementById('mode-compare').classList.toggle('active', mode === 'compare');
    document.getElementById('agentPicker').style.display = mode === 'single' ? 'block' : 'none';
    document.getElementById('runAnalysisBtn').textContent = mode === 'single' ? 'Run Analysis →' : 'Run Comparison →';
    updateAgentDesc();
}
 
function updateAgentDesc() {
    const key = document.getElementById('agentSelect').value;
    document.getElementById('agentDescBox').textContent = AGENT_DESCRIPTIONS[key];
}
 
// ============================================================
// API call helper
// ============================================================
async function callAgent(agentKey) {
    collectProjectData();
    const res = await fetch(`/api/run/${agentKey}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ projectA: projectData.A, projectB: projectData.B })
    });
    if (!res.ok) {
        let msg = `Request failed (${res.status})`;
        try { const j = await res.json(); if (j.error) msg = j.error; } catch (e) {}
        throw new Error(msg);
    }
    return res.json();
}
 
// ============================================================
// Run Analysis (entry point from screen-mode)
// ============================================================
function runAnalysis() {
    if (executionMode === 'single') {
        runSingleAgent();
    } else {
        runCompareAll();
    }
}
 
// ---------- Single agent flow ----------
async function runSingleAgent() {
    const agentKey = document.getElementById('agentSelect').value;
    const btn = document.getElementById('runAnalysisBtn');
    btn.disabled = true;
    btn.textContent = '⏳ Running...';
 
    try {
        const data = await callAgent(agentKey);
        renderSingleResult(agentKey, data);
        goTo('screen-single');
    } catch (err) {
        alert('Error running agent: ' + err.message);
    } finally {
        btn.disabled = false;
        btn.textContent = executionMode === 'single' ? 'Run Analysis →' : 'Run Comparison →';
    }
}
 
function renderSingleResult(agentKey, data) {
    document.getElementById('single-agentName').textContent = AGENT_NAMES[agentKey];
 
    // Status
    const statusEl = document.getElementById('single-status');
    if (data.status === 'escalated' || (data.recommended || '').toLowerCase() === 'escalated') {
        statusEl.innerHTML = `<span class="agent-result-outcome escalated">⚖️ Escalated to Executive Review</span>`;
    } else {
        statusEl.innerHTML = `<span class="agent-result-outcome">✅ Final decision reached</span>`;
    }
 
    // Recommendation line — always a short, bold headline, same as every
    // other agent, even for the unconstrained agent's free-text answer.
    const recEl = document.getElementById('single-recommend');
    recEl.className = 'recommend-line';
    if (agentKey === 'unconstrained') {
        const project = extractRecommendedProject(data.final_answer);
        if (project) {
            recEl.textContent = `🏗️ Project ${project} gets the equipment`;
        } else {
            recEl.className = 'recommend-line escalated';
            recEl.textContent = '⚖️ See explanation below';
        }
    } else if (data.recommended && data.recommended !== 'Escalated') {
        recEl.textContent = `🏗️ ${data.recommended} gets the equipment`;
    } else {
        recEl.className = 'recommend-line escalated';
        recEl.textContent = '⚖️ Escalated — requires executive review';
    }
 
    // Detailed "why" explanation — built for every agent, hidden behind a
    // button by default so the panel isn't cluttered with a wall of text.
    const explainEl = document.getElementById('single-explain');
    explainEl.innerHTML = renderMarkdown(buildExplanationMarkdown(agentKey, data))
        || '<p>No additional explanation available.</p>';
    explainEl.hidden = true;
    document.getElementById('toggleExplainBtn').textContent = '🧠 Explain this decision';
 
    // WHY THIS OUTCOME? -- built from the trace (this section is always kept)
    const whyEl = document.getElementById('single-why');
    whyEl.innerHTML = '';
    if (Array.isArray(data.trace)) {
        data.trace.forEach(step => {
            const li = document.createElement('li');
            const label = step.label || step.action || '';
            const detail = summarizeDetail(step.detail);
            const thought = step.thought ? step.thought + ' ' : '';
            li.innerHTML = `${thought}<br><span style="color:var(--text-muted);font-size:12.5px;">${label}${detail ? ': ' + detail : ''}</span>`;
            whyEl.appendChild(li);
        });
    }
    if (agentKey === 'routing' && data.other_project) {
        const li = document.createElement('li');
        li.textContent = `${data.other_project} should: ${data.other_project_action}`;
        whyEl.appendChild(li);
    }
    if (agentKey === 'unconstrained') {
        const li = document.createElement('li');
        li.textContent = 'The agent freely investigated the case using its own tools before answering (see raw trace).';
        whyEl.appendChild(li);
    }
 
    // Raw trace — the exact terminal-style log the backend captured (or
    // rebuilt) for this agent, lightly tokenized so it reads like a real log.
    document.getElementById('single-raw-title').textContent = `${agentKey}_agent_output.log`;
    document.getElementById('single-raw').innerHTML = formatTrace(data.raw_log);

    // Collapse the raw trace again on every fresh run
    document.getElementById('single-raw-wrap').hidden = true;
    document.getElementById('toggleRawBtn').textContent = '🖥 View raw trace';
}
 
function toggleExplain() {
    const el = document.getElementById('single-explain');
    const btn = document.getElementById('toggleExplainBtn');
    el.hidden = !el.hidden;
    btn.textContent = el.hidden ? '🧠 Explain this decision' : '🔼 Hide explanation';
}
 
function toggleRawTrace() {
    const wrap = document.getElementById('single-raw-wrap');
    const btn = document.getElementById('toggleRawBtn');
    wrap.hidden = !wrap.hidden;
    btn.textContent = wrap.hidden ? '🖥 View raw trace' : '🔼 Hide raw trace';
}
 
// ---------- Compare all flow ----------
async function runCompareAll() {
    collectProjectData();
    goTo('screen-running');
    buildProgressList();
 
    lastCompareResults = {};
    let completed = 0;
 
    for (const agentKey of AGENT_ORDER) {
        setAgentProgress(agentKey, 'running', 20);
        try {
            const data = await callAgent(agentKey);
            lastCompareResults[agentKey] = data;
            const escalated = data.status === 'escalated';
            setAgentProgress(agentKey, escalated ? 'escalated' : 'done', 100);
        } catch (err) {
            lastCompareResults[agentKey] = { agent: agentKey, error: err.message };
            setAgentProgress(agentKey, 'escalated', 100, 'Error');
        }
        completed++;
        const overall = Math.round((completed / AGENT_ORDER.length) * 100);
        document.getElementById('overallLabel').textContent = overall + '%';
        document.getElementById('etaLabel').textContent =
            completed === AGENT_ORDER.length ? '00:00:00' : `~00:00:0${AGENT_ORDER.length - completed}`;
    }
 
    renderComparisonReport();
    goTo('screen-comparison');
}
 
function buildProgressList() {
    const list = document.getElementById('progressList');
    list.innerHTML = '';
    AGENT_ORDER.forEach(key => {
        const item = document.createElement('div');
        item.className = 'progress-item';
        item.id = `progress-${key}`;
        item.innerHTML = `
            <div class="progress-item-top">
                <span>${AGENT_NAMES[key]}</span>
                <span class="progress-status" id="progress-status-${key}">Waiting...</span>
            </div>
            <div class="progress-bar-track"><div class="progress-bar-fill" id="progress-fill-${key}"></div></div>
        `;
        list.appendChild(item);
    });
    document.getElementById('overallLabel').textContent = '0%';
    document.getElementById('etaLabel').textContent = `~00:00:0${AGENT_ORDER.length}`;
}
 
function setAgentProgress(key, state, pct, label) {
    const fill = document.getElementById(`progress-fill-${key}`);
    const status = document.getElementById(`progress-status-${key}`);
    fill.style.width = pct + '%';
    status.classList.remove('running', 'done', 'escalated');
    if (state === 'running') { status.textContent = label || 'Running...'; status.classList.add('running'); }
    else if (state === 'done') { status.textContent = label || 'Completed'; status.classList.add('done'); }
    else if (state === 'escalated') { status.textContent = label || 'Escalated'; status.classList.add('escalated'); }
}
 
function renderComparisonReport() {
    const resultsEl = document.getElementById('agentResults');
    resultsEl.innerHTML = '';
    const insightsEl = document.getElementById('keyInsights');
    insightsEl.innerHTML = '';
 
    const recommendationCounts = {};
 
    AGENT_ORDER.forEach(key => {
        const data = lastCompareResults[key] || {};
        let outcomeText, isEscalated = false, recommendedProject = null;
 
        if (data.error) {
            outcomeText = `Error: ${data.error}`;
        } else if (key === 'unconstrained') {
            const plain = stripMarkdown(data.final_answer);
            outcomeText = plain ? plain.slice(0, 120) + (plain.length > 120 ? '…' : '') : '—';
            const proj = extractRecommendedProject(data.final_answer);
            if (proj) recommendedProject = `Project ${proj}`;
        } else if (data.status === 'escalated' || data.recommended === 'Escalated') {
            outcomeText = 'Escalated — evidence was balanced';
            isEscalated = true;
        } else {
            recommendedProject = data.recommended;
            outcomeText = data.recommended ? `Project ${data.recommended} recommended` : '—';
        }
 
        if (recommendedProject) {
            recommendationCounts[recommendedProject] = (recommendationCounts[recommendedProject] || 0) + 1;
        }
 
        const row = document.createElement('div');
        row.className = 'agent-result-row';
        row.innerHTML = `
            <div>
                <div class="agent-result-name">${AGENT_NAMES[key]}</div>
                <div class="agent-result-outcome ${isEscalated ? 'escalated' : ''}">${outcomeText}</div>
            </div>
            <button class="view-trace-btn" onclick="showTrace('${key}')">View trace</button>
        `;
        resultsEl.appendChild(row);
 
        const li = document.createElement('li');
        li.textContent = `${AGENT_NAMES[key]}: ${isEscalated ? 'escalated — evidence was balanced' : (recommendedProject ? 'recommends ' + recommendedProject : outcomeText)}`;
        insightsEl.appendChild(li);
    });
 
    // Consensus
    let topProject = null, topCount = 0, totalVotes = 0;
    Object.entries(recommendationCounts).forEach(([proj, count]) => {
        totalVotes += count;
        if (count > topCount) { topCount = count; topProject = proj; }
    });
    document.getElementById('consensusScore').textContent = totalVotes ? `${topCount}/${AGENT_ORDER.length}` : '—';
    document.getElementById('consensusSub').textContent = topProject ? `Agents recommend ${topProject}` : 'No clear consensus';
 
    // Trace tabs -- built now, but kept hidden until the person chooses to
    // open them (via the "View full agent traces" button, or a per-agent
    // "View trace" button), instead of appearing automatically.
    document.getElementById('traceTabsWrap').style.display = 'none';
    const toggleBtn = document.getElementById('toggleTracesBtn');
    if (toggleBtn) toggleBtn.textContent = '🖥 View full agent traces';
 
    const tabsEl = document.getElementById('traceTabs');
    tabsEl.innerHTML = '';
    AGENT_ORDER.forEach(key => {
        const tab = document.createElement('button');
        tab.className = 'trace-tab-btn';
        tab.textContent = AGENT_NAMES[key];
        tab.onclick = () => showTrace(key);
        tab.id = `trace-tab-${key}`;
        tabsEl.appendChild(tab);
    });
    populateTraceContent(AGENT_ORDER[0]);
}
 
// Fills in the trace content/active tab without touching visibility.
function populateTraceContent(agentKey) {
    activeTraceTab = agentKey;
    document.querySelectorAll('.trace-tab-btn').forEach(b => b.classList.remove('active'));
    const tabBtn = document.getElementById(`trace-tab-${agentKey}`);
    if (tabBtn) tabBtn.classList.add('active');
    const data = lastCompareResults[agentKey] || {};
    document.getElementById('traceContentTitle').textContent = `${agentKey}_agent_output.log`;
    document.getElementById('traceContent').innerHTML = formatTrace(data.raw_log || data.error);
}
 
function openTraces() {
    document.getElementById('traceTabsWrap').style.display = 'block';
    const btn = document.getElementById('toggleTracesBtn');
    if (btn) btn.textContent = '🔼 Hide full agent traces';
    document.getElementById('traceTabsWrap').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}
 
// Clicking "View trace" on a specific agent row: shows that agent's trace
// and opens the traces panel if it isn't already open.
function showTrace(agentKey) {
    populateTraceContent(agentKey);
    openTraces();
}
 
// The standalone "View full agent traces" button: just toggles the panel
// open/closed, using whichever tab was last selected.
function toggleAllTraces() {
    const wrap = document.getElementById('traceTabsWrap');
    const isHidden = wrap.style.display === 'none' || !wrap.style.display;
    if (isHidden) {
        openTraces();
    } else {
        wrap.style.display = 'none';
        document.getElementById('toggleTracesBtn').textContent = '🖥 View full agent traces';
    }
}
 
// ============================================================
// Screen navigation (back / home / reset)
// ============================================================
let history = ['screen-landing'];
 
function goTo(pageId, addToHistory = true) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    document.getElementById(pageId).classList.add('active');
    if (addToHistory) history.push(pageId);
    document.getElementById('backBtn').disabled = (history.length <= 1);
 
    const titles = {
        'screen-landing': 'ConstructAI',
        'screen-data': 'Enter Project Data',
        'screen-mode': 'Select Execution Mode',
        'screen-single': 'Single Agent Result',
        'screen-running': 'Running Analysis',
        'screen-comparison': 'Comparison Report'
    };
    document.getElementById('chromeTitle').textContent = titles[pageId] || 'ConstructAI';
    window.scrollTo({ top: 0, behavior: 'smooth' });
}
 
function goBack() {
    if (history.length <= 1) return;
    history.pop();
    const prev = history[history.length - 1];
    goTo(prev, false);
}
 
function resetApp() {
    history = ['screen-landing'];
    goTo('screen-landing', false);
    projectData = { A: {}, B: {} };
    lastCompareResults = {};
}