// PDF Study Material Management Engine
document.addEventListener('DOMContentLoaded', () => {
    loadDocumentsGrid();

    const uploadForm = document.getElementById('uploadDocForm');
    if (uploadForm) {
        uploadForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const fileInput = document.getElementById('pdfFile');
            const subjectInput = document.getElementById('docSubject');
            const submitBtn = document.getElementById('btnSubmitUpload');

            if (!fileInput.files || fileInput.files.length === 0) {
                showToast('Please select a PDF file to upload.', 'error');
                return;
            }

            const file = fileInput.files[0];
            if (!file.name.toLowerCase().endsWith('.pdf')) {
                showToast('Only PDF (.pdf) documents are accepted.', 'error');
                return;
            }

            // Close upload modal
            const modalEl = document.getElementById('uploadModal');
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();

            // Show live progress banner
            showUploadProgress('Uploading PDF...', 'Reading document pages & building knowledge base...');

            const formData = new FormData();
            formData.append('file', file);
            formData.append('subject', subjectInput.value);

            try {
                const token = API.getToken();
                const response = await fetch('http://127.0.0.1:8000/api/documents/upload', {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`
                    },
                    body: formData
                });

                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.detail || 'Failed to upload PDF document.');
                }

                showUploadProgress('Ready ✓', 'Document indexed successfully!', 'success');
                showToast(`✓ '${file.name}' processed successfully!`, 'success');
                uploadForm.reset();
                loadDocumentsGrid();
            } catch (err) {
                showUploadProgress('Upload Failed ✗', err.message, 'danger');
                showToast(err.message || 'PDF upload failed.', 'error');
            } finally {
                setTimeout(() => {
                    hideUploadProgress();
                }, 3500);
            }
        });
    }
});

async function loadDocumentsGrid() {
    const grid = document.getElementById('documentsGrid');
    if (!grid) return;

    try {
        const documents = await API.request('/documents');
        if (!documents || documents.length === 0) {
            grid.innerHTML = `
                <div class="col-12 text-center py-5">
                    <i class="fa-solid fa-file-pdf fs-1 text-secondary opacity-50 mb-3"></i>
                    <h5 class="fw-bold">No study materials uploaded yet</h5>
                    <p class="text-secondary small">Upload your first PDF textbook or chapter notes to get started!</p>
                    <button class="btn btn-primary-gradient rounded-pill px-4 mt-2" data-bs-toggle="modal" data-bs-target="#uploadModal">
                        <i class="fa-solid fa-cloud-arrow-up me-2"></i>Upload PDF Notes
                    </button>
                </div>
            `;
            return;
        }

        grid.innerHTML = documents.map(doc => {
            const sizeMB = (doc.file_size_bytes / (1024 * 1024)).toFixed(2);
            return `
                <div class="col-md-6 col-lg-4">
                    <div class="glass-card p-4 h-100 d-flex flex-column justify-content-between">
                        <div>
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <span class="badge bg-danger bg-opacity-25 text-danger border border-danger border-opacity-25 px-3 py-1">
                                    <i class="fa-solid fa-file-pdf me-1"></i>PDF
                                </span>
                                <span class="badge bg-primary bg-opacity-25 text-info px-2 py-1">${doc.subject}</span>
                            </div>
                            <h5 class="fw-bold mb-2 text-truncate" title="${doc.filename}">${doc.filename}</h5>
                            <div class="text-secondary small mb-3">
                                <div><i class="fa-solid fa-book-open me-2 text-primary"></i>${doc.page_count} Pages</div>
                                <div><i class="fa-solid fa-hard-drive me-2 text-info"></i>${sizeMB} MB • ${new Date(doc.created_at).toLocaleDateString()}</div>
                            </div>
                        </div>

                        <div class="d-flex gap-2 pt-3 border-top border-secondary border-opacity-25">
                            <a href="chat.html?doc_id=${doc.id}" class="btn btn-primary-gradient btn-sm flex-grow-1">
                                <i class="fa-solid fa-comments me-1"></i>Ask Questions
                            </a>
                            <button onclick="viewDocInfo(${doc.id})" class="btn btn-outline-info btn-sm" title="Info"><i class="fa-solid fa-circle-info"></i></button>
                            <button onclick="deleteDoc(${doc.id}, '${doc.filename}')" class="btn btn-outline-danger btn-sm" title="Delete"><i class="fa-solid fa-trash"></i></button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    } catch (err) {
        grid.innerHTML = `<div class="col-12 text-danger">Failed to load study materials.</div>`;
    }
}

async function viewDocInfo(id) {
    try {
        const doc = await API.request(`/documents/${id}`);
        document.getElementById('infoModalTitle').innerText = doc.filename;
        const sizeMB = (doc.file_size_bytes / (1024 * 1024)).toFixed(2);
        
        document.getElementById('infoModalBody').innerHTML = `
            <div class="mb-3">
                <strong>Subject:</strong> ${doc.subject}<br>
                <strong>Total Pages:</strong> ${doc.page_count}<br>
                <strong>File Size:</strong> ${sizeMB} MB<br>
                <strong>Status:</strong> <span class="text-success">${doc.status} ✓</span><br>
                <strong>Uploaded On:</strong> ${new Date(doc.created_at).toLocaleString()}<br>
                <strong>Extracted Text Chunks:</strong> ${doc.chunks ? doc.chunks.length : 0} chunks
            </div>
            <hr class="border-secondary border-opacity-25">
            <h6>Sample Extracted Context (Page 1):</h6>
            <div class="bg-dark p-3 rounded-md text-secondary small" style="max-height: 150px; overflow-y: auto;">
                ${doc.chunks && doc.chunks.length > 0 ? doc.chunks[0].text_content.substring(0, 300) + '...' : 'No preview available.'}
            </div>
        `;
        const modal = new bootstrap.Modal(document.getElementById('infoModal'));
        modal.show();
    } catch (e) {
        showToast('Failed to load document details.', 'error');
    }
}

async function deleteDoc(id, name) {
    if (confirm(`Are you sure you want to delete '${name}'?`)) {
        try {
            await API.request(`/documents/${id}`, { method: 'DELETE' });
            showToast('Document deleted successfully.', 'success');
            loadDocumentsGrid();
        } catch (e) {
            showToast('Failed to delete document.', 'error');
        }
    }
}

function showUploadProgress(title, subtitle, type = 'info') {
    const banner = document.getElementById('uploadStatusBanner');
    if (!banner) return;
    banner.classList.remove('d-none');
    document.getElementById('uploadStatusTitle').innerText = title;
    document.getElementById('uploadStatusSubtitle').innerText = subtitle;
}

function hideUploadProgress() {
    const banner = document.getElementById('uploadStatusBanner');
    if (banner) banner.classList.add('d-none');
}
