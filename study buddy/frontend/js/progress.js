// Progress Analytics & Adaptive Recommendation Engine
document.addEventListener('DOMContentLoaded', () => {
    loadProgressDashboard();
});

async function loadProgressDashboard() {
    try {
        const data = await API.request('/progress');

        // Populate top metrics
        document.getElementById('progAsked').innerText = data.total_questions_asked || 0;
        document.getElementById('progDocs').innerText = data.total_docs_uploaded || 0;
        document.getElementById('progExams').innerText = data.total_exams_completed || 0;
        document.getElementById('progScore').innerText = `${data.average_score_percentage || 0}%`;

        // Render Adaptive Recommendations
        renderRecommendations(data.recommendations);

        // Render Strong vs Weak Topics
        renderTopicBadges(data.strong_topics, 'strongTopicsList', 'success');
        renderTopicBadges(data.weak_topics, 'weakTopicsList', 'warning');

        // Render Topic Performance Table
        renderTopicTable(data.topic_performances);
    } catch (e) {
        showToast('Failed to load progress analytics.', 'error');
    }
}

function renderRecommendations(recs) {
    const container = document.getElementById('recommendationsContainer');
    if (!container) return;

    if (!recs || recs.length === 0) {
        container.innerHTML = `<div class="col-12 text-secondary small">No recommendations active right now.</div>`;
        return;
    }

    container.innerHTML = recs.map(r => `
        <div class="col-md-4">
            <div class="p-3 rounded-md bg-dark bg-opacity-50 border border-secondary border-opacity-10 h-100 d-flex flex-column justify-content-between">
                <div>
                    <div class="fw-bold mb-1"><i class="${r.icon_class} me-2"></i>${r.title}</div>
                    <div class="text-secondary small mb-3">${r.subtitle}</div>
                </div>
                <a href="${r.target_url}" class="btn btn-outline-light btn-sm rounded-pill w-100">
                    Launch Action <i class="fa-solid fa-arrow-right ms-1"></i>
                </a>
            </div>
        </div>
    `).join('');
}

function renderTopicBadges(topics, containerId, type) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (!topics || topics.length === 0) {
        container.innerHTML = `<div class="text-secondary small">No ${type === 'success' ? 'strong' : 'weak'} topics recorded yet.</div>`;
        return;
    }

    const badgeClass = type === 'success' ? 'bg-success bg-opacity-25 text-success border-success' : 'bg-warning bg-opacity-25 text-warning border-warning';

    container.innerHTML = topics.map(t => `
        <div class="badge ${badgeClass} border p-2 mb-2 me-2 fs-6">
            <i class="fa-solid ${type === 'success' ? 'fa-circle-check' : 'fa-triangle-exclamation'} me-1"></i> ${t}
        </div>
    `).join('');
}

function renderTopicTable(performances) {
    const tbody = document.getElementById('topicPerformanceTable');
    if (!tbody) return;

    if (!performances || performances.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center text-secondary py-4">No topic performance records available yet. Complete a test to track your topic stats!</td></tr>`;
        return;
    }

    tbody.innerHTML = performances.map(p => `
        <tr>
            <td class="fw-bold">${p.subject}</td>
            <td>${p.topic}</td>
            <td>${p.correct_count} / ${p.total_questions_attempted}</td>
            <td>
                <div class="d-flex align-items-center gap-2">
                    <div class="progress flex-grow-1" style="height: 6px; background-color: rgba(255,255,255,0.1);">
                        <div class="progress-bar ${p.proficiency_percentage >= 70 ? 'bg-success' : 'bg-warning'}" style="width: ${p.proficiency_percentage}%;"></div>
                    </div>
                    <span class="small fw-bold">${p.proficiency_percentage}%</span>
                </div>
            </td>
            <td>
                <span class="badge ${p.proficiency_percentage >= 70 ? 'bg-success bg-opacity-25 text-success' : 'bg-warning bg-opacity-25 text-warning'}">
                    ${p.status}
                </span>
            </td>
        </tr>
    `).join('');
}
