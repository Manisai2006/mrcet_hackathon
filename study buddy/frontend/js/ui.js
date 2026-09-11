// Global UI Helper Component Engine
document.addEventListener('DOMContentLoaded', () => {
    // Add active navbar link highlighting
    highlightActiveNavLink();
});

function highlightActiveNavLink() {
    const path = window.location.pathname;
    document.querySelectorAll('.navbar-custom a.nav-link, .navbar-custom a.btn').forEach(link => {
        const href = link.getAttribute('href');
        if (href && path.includes(href) && href !== '#' && href !== 'index.html') {
            link.classList.add('fw-bold', 'text-primary');
        }
    });
}

function renderSkeletonCards(containerId, count = 3) {
    const container = document.getElementById(containerId);
    if (!container) return;

    let html = '';
    for (let i = 0; i < count; i++) {
        html += `
            <div class="col-md-4">
                <div class="glass-card p-4 h-100">
                    <div class="skeleton mb-3" style="height: 24px; width: 60%;"></div>
                    <div class="skeleton mb-2" style="height: 16px; width: 90%;"></div>
                    <div class="skeleton mb-4" style="height: 16px; width: 75%;"></div>
                    <div class="skeleton" style="height: 40px; width: 100%; border-radius: 20px;"></div>
                </div>
            </div>
        `;
    }
    container.innerHTML = html;
}
