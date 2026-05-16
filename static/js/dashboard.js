// Dashboard JavaScript functions

function showAddStudentModal() {
    document.getElementById('addStudentModal').style.display = 'flex';
    document.getElementById('studentName').focus();
}

function closeModal() {
    document.getElementById('addStudentModal').style.display = 'none';
}

function showWeaknessForm() {
    document.getElementById('weaknessForm').style.display = 'block';
}

function showGenerateModal() {
    document.getElementById('generateModal').style.display = 'flex';
}

function closeGenerateModal() {
    document.getElementById('generateModal').style.display = 'none';
}

function generateProblem(studentId) {
    var topicEl = document.getElementById('genTopic');
    if (!topicEl) {
        alert('请先添加薄弱环节，再生成题目。');
        return;
    }
    var topic = topicEl.value;
    var difficulty = parseInt(document.getElementById('genDifficulty').value) || 3;
    var resultDiv = document.getElementById('genResult');

    resultDiv.innerHTML = '<p class="text-muted">正在生成题目...</p>';

    fetch('/api/problems/generate/' + studentId, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic: topic, difficulty: difficulty })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.success && data.problem) {
            var p = data.problem;
            var html = '<div class="card" style="margin-top:12px;"><h4>题目</h4><p>' + p.question + '</p>';
            html += '<p><strong>答案：</strong><span style="color:var(--success);">' + (p.answer || '') + '</span></p>';
            if (p.solution_steps && p.solution_steps.length > 0) {
                html += '<details><summary>解题步骤</summary><ol>';
                p.solution_steps.forEach(function(s) { html += '<li>' + s + '</li>'; });
                html += '</ol></details>';
            }
            if (p.hints && p.hints.length > 0) {
                html += '<details><summary>提示</summary><ul>';
                p.hints.forEach(function(h) { html += '<li>' + h + '</li>'; });
                html += '</ul></details>';
            }
            html += '<p class="text-muted text-sm">难度：' + '⭐'.repeat(p.difficulty || 3) + '</p></div>';
            resultDiv.innerHTML = html;
        } else {
            resultDiv.innerHTML = '<p class="flash flash-error">题目生成失败：' + (data.error || '未知错误') + '</p>';
        }
    })
    .catch(function(e) {
        resultDiv.innerHTML = '<p class="flash flash-error">请求失败，请检查 API Key 是否正确配置</p>';
        console.error('Generate error:', e);
    });
}

// Settings
document.getElementById('nav-settings').addEventListener('click', function(e) {
    e.preventDefault();
    document.getElementById('settingsModal').style.display = 'flex';
});

function closeSettingsModal() {
    document.getElementById('settingsModal').style.display = 'none';
}

function saveSettings() {
    var apiKey = document.getElementById('apiKey').value.trim();
    var msg = document.getElementById('settingsMsg');

    if (!apiKey) {
        msg.innerHTML = '<span style="color:var(--danger);">请输入 API Key</span>';
        return;
    }

    fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ deepseek_api_key: apiKey })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.success) {
            msg.innerHTML = '<span style="color:var(--success);">设置已保存</span>';
            setTimeout(closeSettingsModal, 1000);
        } else {
            msg.innerHTML = '<span style="color:var(--danger);">保存失败</span>';
        }
    })
    .catch(function(e) {
        msg.innerHTML = '<span style="color:var(--danger);">请求失败</span>';
    });
}

// Close modals on background click
window.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal')) {
        e.target.style.display = 'none';
    }
});
