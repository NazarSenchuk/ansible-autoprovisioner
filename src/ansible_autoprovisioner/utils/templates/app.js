let currentTheme = 'light';
let refreshTimer = null;
const REFRESH_INTERVAL = 5000;

// Log viewer state
let currentLogInstanceId = null;
let currentLogTabs = {};
let activeLogTab = null;

function setTheme(theme) {
    currentTheme = theme;
    document.body.className = theme + '-theme';
    document.getElementById('theme-light').classList.toggle('active', theme === 'light');
    document.getElementById('theme-dark').classList.toggle('active', theme === 'dark');
    localStorage.setItem('theme', theme);
}

function loadTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    setTheme(savedTheme);
}

async function fetchJSON(url, opts) {
    const r = await fetch(url, opts);
    const ct = r.headers.get('content-type') || '';
    if (!r.ok) {
        let msg = `HTTP ${r.status}`;
        if (ct.includes('application/json')) {
            const j = await r.json().catch(() => null);
            if (j && (j.error || j.details)) msg = j.error || j.details;
        } else {
            const t = await r.text().catch(() => '');
            if (t) msg = t;
        }
        throw new Error(msg);
    }
    if (ct.includes('application/json')) return r.json();
    return r.text();
}

async function fetchData() {
    try {
        const [instances, stats, config] = await Promise.all([
            fetchJSON('/api/instances'),
            fetchJSON('/api/stats'),
            fetchJSON('/api/config')
        ]);

        updateUI(instances || [], stats || {}, config || {});
        updateTime();
    } catch (e) {
        console.error('Error fetching data:', e);
        document.getElementById('update-time').textContent =
            `Last update failed: ${new Date().toLocaleTimeString()}`;
    }
}

function updateUI(instances, stats, config) {
    document.getElementById('stat-instances').textContent = stats.total_instances ?? instances.length ?? 0;
    document.getElementById('stat-successful').textContent = stats.successful ?? 0;
    document.getElementById('stat-failed').textContent = stats.failed ?? 0;
    document.getElementById('stat-active').textContent = stats.pending ?? 0;

    document.getElementById('config-interval').textContent = `${config.interval ?? '-'}s`;
    document.getElementById('config-retries').textContent = config.max_retries ?? '-';
    document.getElementById('config-state-file').textContent = config.state_file ?? '-';
    document.getElementById('config-log-dir').textContent = config.log_dir ?? '-';
    document.getElementById('config-rules').textContent = config.rules_count ?? '-';
    document.getElementById('config-ui').textContent = (config.ui ?? true) ? 'Yes' : 'No';

    document.getElementById('instance-count').textContent =
        `${instances.length} instance${instances.length !== 1 ? 's' : ''}`;

    renderDetectors(config.detectors || []);
    renderInstances(instances);
}

function renderDetectors(detectors) {
    const container = document.getElementById('detectors-list');
    if (!detectors || detectors.length === 0) {
        container.innerHTML = `
      <div class="empty-state">
        <i class="fas fa-exclamation-circle"></i>
        <p>No detectors configured</p>
      </div>`;
        return;
    }

    container.innerHTML = detectors.map(d => `
    <div class="detector-item">
      <div class="detector-header">
        <i class="fas fa-search"></i>
        <span class="detector-name">${escapeHtml(d.name || 'detector')}</span>
        <span class="detector-badge">${Object.keys(d.options || {}).length} options</span>
      </div>
      ${d.options && Object.keys(d.options).length > 0 ? `
        <div class="detector-options">
          ${Object.entries(d.options).map(([k, v]) => `
            <div class="detector-option">
              <span class="option-key">${escapeHtml(k)}</span>
              <span class="option-value">${escapeHtml(formatOptionValue(v))}</span>
            </div>
          `).join('')}
        </div>
      ` : ''}
    </div>
  `).join('');
}

function formatOptionValue(value) {
    if (value === null || value === undefined) return 'null';
    if (typeof value === 'boolean') return value ? 'true' : 'false';
    if (typeof value === 'number') return String(value);
    if (typeof value === 'object') return JSON.stringify(value);
    return String(value);
}

function renderInstances(instances) {
    const tbody = document.getElementById('instances-body');
    if (!instances || instances.length === 0) {
        tbody.innerHTML = `
      <tr>
        <td colspan="7" class="empty-state">
          <i class="fas fa-inbox"></i>
          <p>No instances detected yet</p>
        </td>
      </tr>`;
        return;
    }

    tbody.innerHTML = instances.map(inst => {
        const instanceId = inst.instance_id || inst.id || 'unknown';
        const ip = inst.ip_address || 'N/A';
        const status = (inst.overall_status || inst.status || 'unknown');
        const statusIcon = getStatusIcon(status);
        const statusClass = `status-${status}`;

        const groups = Array.isArray(inst.groups) ? inst.groups : [];
        const playbooks = Array.isArray(inst.playbooks) ? inst.playbooks : [];
        const playbookResults = inst.playbook_results || {};

        const hasLogs = Object.keys(playbookResults).length > 0;

        const restartBtn = `
      <button class="btn-icon btn-warning" onclick="restartInstance('${escapeAttr(instanceId)}')" title="Restart">
        <i class="fas fa-redo"></i>
      </button>`;

        const logsBtn = hasLogs ? `
      <button class="btn-icon btn-info" onclick="showLogs('${escapeAttr(instanceId)}')" title="View Logs">
        <i class="fas fa-file-alt"></i>
      </button>` : '';

        return `
      <tr>
        <td class="instance-id">
          <i class="fas fa-hashtag"></i>
          <span class="id-text">${escapeHtml(instanceId)}</span>
        </td>
        <td><code class="ip-address">${escapeHtml(ip)}</code></td>
        <td>
          <span class="status-badge ${escapeAttr(statusClass)}">
            <i class="fas ${escapeAttr(statusIcon)}"></i>
            ${escapeHtml(String(status).toUpperCase())}
          </span>
        </td>
        <td>
          ${groups.map(g => `<span class="group-tag">${escapeHtml(typeof g === 'object' ? g.name : g)}</span>`).join('')}
        </td>
        <td><span class="playbook-count">${(inst.playbook_tasks || []).length}</span></td>
        <td class="timestamp">${escapeHtml(formatTimestamp(inst.updated_at))}</td>
        <td class="actions">
          <div class="action-buttons">
            <button class="btn-icon btn-info" onclick="showDetails('${escapeAttr(instanceId)}')" title="Details">
              <i class="fas fa-info-circle"></i>
            </button>
            ${logsBtn}
            ${restartBtn}
            <button class="btn-icon btn-danger" onclick="deleteInstance('${escapeAttr(instanceId)}')" title="Delete">
              <i class="fas fa-trash"></i>
            </button>
          </div>
        </td>
      </tr>
    `;
    }).join('');
}

function getStatusIcon(status) {
    const icons = {
        new: 'fa-clock',
        provisioning: 'fa-sync fa-spin',
        provisioned: 'fa-check-circle',
        failed: 'fa-times-circle',
        partial_failure: 'fa-exclamation-triangle',
        retrying: 'fa-redo',
        skipped: 'fa-forward',
        orphaned: 'fa-question-circle',
        unknown: 'fa-circle'
    };
    return icons[status] || 'fa-circle';
}

function formatTimestamp(timestamp) {
    if (!timestamp) return 'N/A';
    const d = new Date(timestamp);
    if (Number.isNaN(d.getTime())) return 'N/A';
    const now = new Date();
    const diff = Math.floor((now - d) / 1000);

    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return d.toLocaleDateString();
}

function updateTime() {
    const now = new Date();
    document.getElementById('update-time').textContent = `Last updated: ${now.toLocaleTimeString()}`;
    document.getElementById('current-time').textContent =
        now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function showModal(id) {
    document.getElementById(id).classList.remove('hidden');
    document.getElementById('overlay').classList.remove('hidden');
}

function closeModal(id) {
    document.getElementById(id).classList.add('hidden');
    document.getElementById('overlay').classList.add('hidden');
}

function closeAllModals() {
    document.querySelectorAll('.modal').forEach(m => m.classList.add('hidden'));
    document.getElementById('advanced-log-viewer').classList.add('hidden');
    document.getElementById('overlay').classList.add('hidden');
}

function openAddModal() {
    document.getElementById('add-instance-form').reset();
    showModal('add-modal');
}

async function submitAddInstance() {
    const form = document.getElementById('add-instance-form');
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }

    const instanceId = document.getElementById('instance-id').value.trim();
    const ipAddress = document.getElementById('ip-address').value.trim();
    const groups = document.getElementById('groups').value
        .split(',')
        .map(x => x.trim())
        .filter(Boolean);

    const playbooks = document.getElementById('playbooks').value
        .split(',')
        .map(x => x.trim())
        .filter(Boolean);

    try {
        const res = await fetchJSON('/api/instances', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                instance_id: instanceId,
                ip_address: ipAddress,
                groups,
                playbooks
            })
        });

        if (res && res.success === false) throw new Error(res.error || 'Failed to add instance');

        closeModal('add-modal');
        await fetchData();
    } catch (e) {
        alert(`Error: ${e.message}`);
    }
}

async function showDetails(instanceId) {
    try {
        const data = await fetchJSON(`/api/instance/${encodeURIComponent(instanceId)}`);
        const instance = data.instance ?? data;
        document.getElementById('details-content').textContent = JSON.stringify(instance, null, 2);
        showModal('details-modal');
    } catch (e) {
        alert(`Error: ${e.message}`);
    }
}

async function restartInstance(instanceId) {
    if (!confirm(`Restart provisioning for "${instanceId}"?`)) return;
    try {
        const data = await fetchJSON(`/api/instance/${encodeURIComponent(instanceId)}/retry`, {
            method: 'POST'
        });
        if (data && data.success === false) throw new Error(data.error || 'Restart failed');
        await fetchData();
    } catch (e) {
        alert(`Error: ${e.message}`);
    }
}

async function restartPlaybook(instanceId, playbookName) {
    if (!confirm(`Restart playbook "${playbookName}" for instance "${instanceId}"?`)) return;
    try {
        const data = await fetchJSON(`/api/instance/${encodeURIComponent(instanceId)}/playbook/${encodeURIComponent(playbookName)}/retry`, {
            method: 'POST'
        });
        if (data && data.success === false) throw new Error(data.error || 'Restart failed');
        await fetchData();
        // Refresh the log viewer if it's open
        const tabId = `tab-${instanceId}-${playbookName}`;
        if (currentLogTabs[tabId]) {
            setTimeout(() => showLogs(instanceId), 500);
        }
    } catch (e) {
        alert(`Error: ${e.message}`);
    }
}

async function restartAllInstances() {
    if (!confirm('Restart ALL instances? This will reset their status to NEW.')) return;

    try {
        const instancesRes = await fetchJSON('/api/instances');
        const instances = instancesRes || [];

        let successCount = 0;
        let errorCount = 0;

        for (const inst of instances) {
            const instanceId = inst.instance_id || inst.id;
            if (instanceId) {
                try {
                    await fetchJSON(`/api/instance/${encodeURIComponent(instanceId)}/retry`, {
                        method: 'POST'
                    });
                    successCount++;
                } catch (e) {
                    console.error(`Failed to restart instance ${instanceId}:`, e);
                    errorCount++;
                }
            }
        }

        await fetchData();
        alert(`Restarted ${successCount} instance(s) successfully. ${errorCount > 0 ? `Failed to restart ${errorCount} instance(s).` : ''}`);
    } catch (e) {
        alert(`Error: ${e.message}`);
    }
}

async function deleteInstance(instanceId) {
    if (!confirm(`Delete instance "${instanceId}"?`)) return;
    try {
        const data = await fetchJSON(`/api/instance/${encodeURIComponent(instanceId)}/delete`, {
            method: 'POST'
        });
        if (data && data.success === false) throw new Error(data.error || 'Delete failed');
        await fetchData();
    } catch (e) {
        alert(`Error: ${e.message}`);
    }
}

// ===== LOG VIEWER FUNCTIONS =====
async function showLogs(instanceId) {
    currentLogInstanceId = instanceId;

    try {
        const instanceRes = await fetchJSON(`/api/instance/${encodeURIComponent(instanceId)}`);
        const instance = instanceRes.instance || instanceRes;

        if (!instance || !instance.playbook_results) {
            alert('No logs available for this instance');
            return;
        }

        const playbookResults = instance.playbook_results;
        const playbooks = Object.entries(playbookResults).filter(([name, pb]) => pb);

        if (playbooks.length === 0) {
            alert('No playbook results found for this instance');
            return;
        }

        // Open all playbook logs in tabbed viewer directly
        await openAllLogs(instanceId);
    } catch (e) {
        console.error('Error fetching instance logs:', e);
        alert(`Error: ${e.message}`);
    }
}

async function openAllLogs(instanceId) {
    try {
        const instanceRes = await fetchJSON(`/api/instance/${encodeURIComponent(instanceId)}`);
        const instance = instanceRes.instance || instanceRes;

        if (!instance || !instance.playbook_results) {
            alert('No logs available for this instance');
            return;
        }

        const playbookResults = instance.playbook_results;
        const playbooks = Object.entries(playbookResults).filter(([name, pb]) => pb);

        if (playbooks.length === 0) {
            alert('No playbook results found');
            return;
        }

        // Clear existing tabs
        currentLogTabs = {};
        document.getElementById('log-tabs').innerHTML = '';
        document.getElementById('log-content').textContent = '';

        // Create tabs for each playbook
        for (const [name, pb] of playbooks) {
            await addLogTab(instanceId, name, pb);
        }

        // Activate first tab
        if (Object.keys(currentLogTabs).length > 0) {
            const firstTab = Object.keys(currentLogTabs)[0];
            activateLogTab(firstTab);
        } else {
            // If no tabs were created (no logs), show empty state
            document.getElementById('log-content').textContent = 'No logs available for this playbook';
        }

        // Show the advanced log viewer
        document.getElementById('advanced-log-viewer').classList.remove('hidden');
        document.getElementById('overlay').classList.remove('hidden');
        document.getElementById('log-viewer-title').textContent = `Logs: ${instanceId}`;

    } catch (e) {
        console.error('Error opening all logs:', e);
        alert(`Error: ${e.message}`);
    }
}

async function addLogTab(instanceId, playbookName, pbInfo) {
    const tabId = `log-tab-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

    try {
        // Try different log file extensions
        const logExtensions = ['.log', '.txt', ''];
        let logContent = null;
        let logError = null;

        for (const ext of logExtensions) {
            try {
                const logRes = await fetch(`/api/instance/${encodeURIComponent(instanceId)}/logs/${encodeURIComponent(playbookName)}${ext}`);

                if (logRes.ok) {
                    logContent = await logRes.text();
                    break;
                }
            } catch (e) {
                logError = e;
            }
        }

        // If no log file found, create tab with status info
        if (!logContent) {
            logContent = `No log file found for playbook: ${playbookName}\n\n`;
            logContent += `Status: ${pbInfo.status || 'unknown'}\n`;
            if (pbInfo.started_at) logContent += `Started: ${new Date(pbInfo.started_at).toLocaleString()}\n`;
            if (pbInfo.completed_at) logContent += `Completed: ${new Date(pbInfo.completed_at).toLocaleString()}\n`;
            if (pbInfo.duration_sec) logContent += `Duration: ${pbInfo.duration_sec.toFixed(2)}s\n`;
            if (pbInfo.error) logContent += `Error: ${pbInfo.error}\n`;
        }

        // Create tab element
        const tab = document.createElement('div');
        tab.className = 'log-tab';
        tab.id = tabId;
        tab.innerHTML = `
      <i class="fas ${getPlaybookStatusIcon(pbInfo.status)}"></i>
      <span>${escapeHtml(playbookName)}</span>
      <button class="tab-retry" onclick="event.stopPropagation(); restartPlaybook('${escapeAttr(instanceId)}', '${escapeAttr(playbookName)}')" title="Retry individual playbook">
        <i class="fas fa-redo"></i>
      </button>
      <span class="tab-close" onclick="event.stopPropagation(); closeLogTab('${tabId}')">×</span>
    `;
        tab.onclick = () => activateLogTab(tabId);

        document.getElementById('log-tabs').appendChild(tab);

        // Store log content
        currentLogTabs[tabId] = {
            instanceId,
            playbookName,
            content: logContent,
            timestamp: new Date().toISOString(),
            pbInfo
        };

        return tabId;

    } catch (e) {
        console.error('Error adding log tab:', e);
        // Create tab with error state
        const tab = document.createElement('div');
        tab.className = 'log-tab';
        tab.id = tabId;
        tab.innerHTML = `
      <i class="fas fa-exclamation-circle"></i>
      <span>${escapeHtml(playbookName)} (Error)</span>
      <button class="tab-retry" onclick="event.stopPropagation(); restartPlaybook('${escapeAttr(instanceId)}', '${escapeAttr(playbookName)}')" title="Retry individual playbook">
        <i class="fas fa-redo"></i>
      </button>
      <span class="tab-close" onclick="event.stopPropagation(); closeLogTab('${tabId}')">×</span>
    `;
        tab.onclick = () => activateLogTab(tabId);

        document.getElementById('log-tabs').appendChild(tab);

        currentLogTabs[tabId] = {
            instanceId,
            playbookName,
            content: `Error loading log: ${e.message}`,
            timestamp: new Date().toISOString(),
            pbInfo,
            error: true
        };

        return tabId;
    }
}

function getPlaybookStatusIcon(status) {
    const icons = {
        'success': 'fa-check-circle',
        'failed': 'fa-times-circle',
        'running': 'fa-sync fa-spin',
        'pending': 'fa-clock',
        'timeout': 'fa-hourglass-end',
        'unknown': 'fa-question-circle'
    };
    return icons[status] || 'fa-file-alt';
}

function activateLogTab(tabId) {
    if (!currentLogTabs[tabId]) return;

    // Update tab classes
    document.querySelectorAll('.log-tab').forEach(tab => {
        tab.classList.remove('active');
    });

    const tabElement = document.getElementById(tabId);
    if (tabElement) {
        tabElement.classList.add('active');
    }

    // Display content
    const tabData = currentLogTabs[tabId];
    displayLogContent(tabData.content);

    activeLogTab = tabId;

    // Update title
    document.getElementById('log-viewer-title').textContent =
        `Logs: ${tabData.instanceId} - ${tabData.playbookName}`;
}

function displayLogContent(content) {
    const logContentEl = document.getElementById('log-content');

    // Apply syntax highlighting for Ansible logs (basic)
    let highlighted = escapeHtml(content);

    // Highlight common patterns
    highlighted = highlighted.replace(
        /(INFO|WARNING|ERROR|CRITICAL|DEBUG|changed|ok|failed|skipped)/g,
        '<span class="log-highlight log-$1">$&</span>'
    );

    // Highlight timestamps
    highlighted = highlighted.replace(
        /(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}|\d{2}:\d{2}:\d{2})/g,
        '<span class="log-timestamp">$&</span>'
    );

    // Highlight IP addresses
    highlighted = highlighted.replace(
        /(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})/g,
        '<span class="log-ip">$&</span>'
    );

    // Highlight task names
    highlighted = highlighted.replace(
        /TASK \[(.*?)\]/g,
        '<span class="log-task">TASK [$1]</span>'
    );

    // Highlight play names
    highlighted = highlighted.replace(
        /PLAY \[(.*?)\]/g,
        '<span class="log-play">PLAY [$1]</span>'
    );

    logContentEl.innerHTML = highlighted;

    // Auto-scroll to bottom
    logContentEl.scrollTop = logContentEl.scrollHeight;
}

function closeLogTab(tabId) {
    if (!currentLogTabs[tabId]) return;

    // Remove tab element
    const tabElement = document.getElementById(tabId);
    if (tabElement) {
        tabElement.remove();
    }

    // Remove from tracking
    delete currentLogTabs[tabId];

    // If no tabs left, close the viewer
    if (Object.keys(currentLogTabs).length === 0) {
        closeAdvancedLogViewer();
        return;
    }

    // If active tab was closed, activate another tab
    if (activeLogTab === tabId) {
        const remainingTabs = Object.keys(currentLogTabs);
        if (remainingTabs.length > 0) {
            activateLogTab(remainingTabs[0]);
        }
    }
}

async function copyLogToClipboard() {
    if (!activeLogTab || !currentLogTabs[activeLogTab]) return;

    const content = currentLogTabs[activeLogTab].content;

    try {
        await navigator.clipboard.writeText(content);
        alert('Log copied to clipboard!');
    } catch (e) {
        console.error('Error copying to clipboard:', e);
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = content;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        alert('Log copied to clipboard!');
    }
}

function closeAdvancedLogViewer() {
    document.getElementById('advanced-log-viewer').classList.add('hidden');
    document.getElementById('overlay').classList.add('hidden');

    // Reset state
    currentLogTabs = {};
    activeLogTab = null;
    document.getElementById('log-tabs').innerHTML = '';
    document.getElementById('log-content').textContent = '';
}

function manualRefresh() {
    clearTimeout(refreshTimer);
    fetchData();
    startRefreshTimer();
}

function startRefreshTimer() {
    refreshTimer = setTimeout(() => {
        fetchData();
        startRefreshTimer();
    }, REFRESH_INTERVAL);
}

function escapeHtml(s) {
    return String(s)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
}

function escapeAttr(s) {
    return escapeHtml(s);
}

function init() {
    loadTheme();
    fetchData();
    startRefreshTimer();
    setInterval(updateTime, 60000);
}

init();
