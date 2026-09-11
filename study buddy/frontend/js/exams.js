// AI Exam Generator & Active Test Workspace Engine
let activeExam = null;
let currentQuestionIndex = 0;
let studentAnswersMap = {}; // { question_id: answer_text }
let timerInterval = null;
let secondsRemaining = 0;

document.addEventListener('DOMContentLoaded', () => {
    // Check if on active exam page (exam.html)
    const path = window.location.pathname;
    if (path.includes('exam.html')) {
        const urlParams = new URLSearchParams(window.location.search);
        const examId = urlParams.get('id');
        if (examId) {
            loadActiveExam(parseInt(examId));
        } else {
            window.location.href = 'exams.html';
        }
    }

    // Handle Exam Generation Form (exams.html)
    const genForm = document.getElementById('generateExamForm');
    if (genForm) {
        genForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const subject = document.getElementById('examSubject').value;
            const language = document.getElementById('examLanguage').value;
            const difficulty = document.getElementById('examDifficulty').value;
            const question_types = document.getElementById('questionTypes').value;
            const total_questions = parseInt(document.getElementById('totalQuestions').value);
            const time_limit_minutes = parseInt(document.getElementById('timeLimit').value);
            const docVal = document.getElementById('examDocSelect').value;
            const doc_id = docVal ? parseInt(docVal) : null;
            const submitBtn = document.getElementById('btnSubmitGenerate');

            try {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i> Generating Exam...';
                showToast('Generating personalized AI questions...', 'info');

                const examDetail = await API.request('/exams/generate', {
                    method: 'POST',
                    body: JSON.stringify({
                        subject,
                        language,
                        difficulty,
                        question_types,
                        total_questions,
                        time_limit_minutes,
                        document_id: doc_id
                    })
                });

                showToast('Exam generated successfully!', 'success');
                // Redirect immediately to active test taking workspace
                setTimeout(() => {
                    window.location.href = `exam.html?id=${examDetail.id}`;
                }, 800);
            } catch (err) {
                showToast(err.message || 'Failed to generate exam. Please try again.', 'error');
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = 'Generate Exam <i class="fa-solid fa-sparkles ms-1"></i>';
            }
        });
    }
});

async function loadActiveExam(examId) {
    try {
        activeExam = await API.request(`/exams/${examId}`);
        if (!activeExam || !activeExam.questions || activeExam.questions.length === 0) {
            showToast('Failed to load exam questions.', 'error');
            return;
        }

        document.getElementById('examTitle').innerText = activeExam.title;

        // Initialize Timer if timed exam
        if (activeExam.time_limit_minutes > 0) {
            secondsRemaining = activeExam.time_limit_minutes * 60;
            document.getElementById('timerContainer').classList.remove('d-none');
            startTimerCountdown();
        }

        renderQuestionNavGrid();
        renderCurrentQuestion();
    } catch (e) {
        showToast('Error loading active exam.', 'error');
    }
}

function renderCurrentQuestion() {
    if (!activeExam || !activeExam.questions) return;
    const q = activeExam.questions[currentQuestionIndex];
    const total = activeExam.questions.length;

    document.getElementById('examMetaBadge').innerText = `Question ${currentQuestionIndex + 1} of ${total}`;

    const container = document.getElementById('questionContainer');
    const existingAnswer = studentAnswersMap[q.id] || '';

    let optionsHTML = '';
    if (q.options) {
        try {
            const optionsArray = JSON.parse(q.options);
            optionsHTML = optionsArray.map((opt, idx) => {
                const isChecked = existingAnswer === opt ? 'checked' : '';
                const selectedClass = existingAnswer === opt ? 'selected' : '';
                return `
                    <label class="option-pill ${selectedClass}">
                        <input type="radio" name="option_q_${q.id}" value="${opt.replace(/"/g, '&quot;')}" ${isChecked} onchange="saveStudentAnswer(${q.id}, this.value)">
                        <span><strong>${String.fromCharCode(65 + idx)}.</strong> ${opt}</span>
                    </label>
                `;
            }).join('');
        } catch (e) {}
    } else {
        // Text Area / Short Answer Input
        optionsHTML = `
            <div class="mb-3">
                <textarea class="form-control" rows="4" placeholder="Write your step-by-step answer here..." oninput="saveStudentAnswer(${q.id}, this.value)">${existingAnswer}</textarea>
            </div>
        `;
    }

    container.innerHTML = `
        <div class="d-flex justify-content-between align-items-center mb-3">
            <span class="badge bg-primary bg-opacity-25 text-info">Question ${q.question_number}</span>
            <span class="badge bg-secondary bg-opacity-25 text-secondary">${q.question_type} • ${q.difficulty}</span>
        </div>
        <h4 class="fw-bold mb-4">${q.question_text}</h4>
        <div class="options-group mb-2">
            ${optionsHTML}
        </div>
    `;

    // Navigation buttons state
    document.getElementById('btnPrev').disabled = (currentQuestionIndex === 0);
    const nextBtn = document.getElementById('btnNext');
    if (currentQuestionIndex === total - 1) {
        nextBtn.innerHTML = 'Review & Submit <i class="fa-solid fa-check ms-1"></i>';
        nextBtn.classList.remove('btn-primary-gradient');
        nextBtn.classList.add('btn-success');
    } else {
        nextBtn.innerHTML = 'Next <i class="fa-solid fa-chevron-right ms-1"></i>';
        nextBtn.classList.remove('btn-success');
        nextBtn.classList.add('btn-primary-gradient');
    }

    renderQuestionNavGrid();
}

function saveStudentAnswer(questionId, value) {
    studentAnswersMap[questionId] = value;
    renderQuestionNavGrid();
    
    // Highlight active option pill
    document.querySelectorAll('.option-pill').forEach(pill => {
        const radio = pill.querySelector('input[type="radio"]');
        if (radio && radio.checked) {
            pill.classList.add('selected');
        } else {
            pill.classList.remove('selected');
        }
    });
}

function navigateQuestion(direction) {
    const total = activeExam.questions.length;
    const newIdx = currentQuestionIndex + direction;
    
    if (newIdx >= 0 && newIdx < total) {
        currentQuestionIndex = newIdx;
        renderCurrentQuestion();
    } else if (newIdx >= total) {
        confirmSubmitExam();
    }
}

function jumpToQuestion(idx) {
    currentQuestionIndex = idx;
    renderCurrentQuestion();
}

function renderQuestionNavGrid() {
    const navGrid = document.getElementById('questionNavGrid');
    if (!navGrid || !activeExam) return;

    navGrid.innerHTML = activeExam.questions.map((q, idx) => {
        const isCurrent = idx === currentQuestionIndex;
        const isAnswered = studentAnswersMap[q.id] && studentAnswersMap[q.id].trim() !== '';
        
        let cls = 'btn-q-nav';
        if (isCurrent) cls += ' active';
        else if (isAnswered) cls += ' answered';

        return `<div class="${cls}" onclick="jumpToQuestion(${idx})">${idx + 1}</div>`;
    }).join('');
}

function startTimerCountdown() {
    timerInterval = setInterval(() => {
        secondsRemaining--;
        if (secondsRemaining <= 0) {
            clearInterval(timerInterval);
            showToast('⏱ Time is up! Submitting exam automatically...', 'warning');
            submitExamAnswers();
            return;
        }

        const mins = Math.floor(secondsRemaining / 60);
        const secs = secondsRemaining % 60;
        const formatted = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        document.getElementById('timerText').innerText = formatted;

        if (secondsRemaining === 60) {
            showToast('⚠️ 1 minute remaining before automatic submission!', 'warning');
        }
    }, 1000);
}

function confirmSubmitExam() {
    const total = activeExam.questions.length;
    const answeredCount = Object.keys(studentAnswersMap).filter(k => studentAnswersMap[k] && studentAnswersMap[k].trim() !== '').length;
    const unansweredCount = total - answeredCount;

    let msg = `You have answered ${answeredCount} out of ${total} questions.`;
    if (unansweredCount > 0) {
        msg += ` ${unansweredCount} question(s) remain unanswered.`;
    }
    msg += ` Are you ready to submit?`;

    if (confirm(msg)) {
        if (timerInterval) clearInterval(timerInterval);
        submitExamAnswers();
    }
}

async function submitExamAnswers() {
    if (timerInterval) clearInterval(timerInterval);

    showToast('Submitting and evaluating exam answers...', 'info');

    // Build submission payload array
    const answersPayload = activeExam.questions.map(q => ({
        question_id: q.id,
        student_answer_text: studentAnswersMap[q.id] || ""
    }));

    try {
        const result = await API.request(`/exams/${activeExam.id}/submit`, {
            method: 'POST',
            body: JSON.stringify({ answers: answersPayload })
        });

        renderExamResults(result);
    } catch (err) {
        showToast(err.message || 'Failed to evaluate exam.', 'error');
    }
}

function renderExamResults(res) {
    // Hide header timer and submit buttons
    const timerContainer = document.getElementById('timerContainer');
    if (timerContainer) timerContainer.classList.add('d-none');
    const submitBtnTop = document.getElementById('btnSubmitExamTop');
    if (submitBtnTop) submitBtnTop.classList.add('d-none');

    document.getElementById('examMetaBadge').innerHTML = `<i class="fa-solid fa-trophy me-1"></i> Score: ${res.score}/${res.max_score} (${res.percentage}%)`;

    const mainContainer = document.querySelector('main.container');
    mainContainer.innerHTML = `
        <div class="row g-4 justify-content-center">
            <div class="col-lg-10">
                <!-- Score Summary Banner -->
                <div class="glass-card p-4 p-md-5 mb-4 text-center">
                    <div class="display-3 fw-bold gradient-text mb-2">${res.percentage}%</div>
                    <h4 class="fw-bold mb-3">🎯 Final Score: ${res.score} / ${res.max_score}</h4>
                    <div class="d-flex justify-content-center gap-4 text-secondary mb-4">
                        <span class="text-success"><i class="fa-solid fa-circle-check me-1"></i> Correct: ${res.correct_count}</span>
                        <span class="text-danger"><i class="fa-solid fa-circle-xmark me-1"></i> Incorrect: ${res.incorrect_count}</span>
                        <span class="text-secondary"><i class="fa-solid fa-circle-minus me-1"></i> Unanswered: ${res.unanswered_count}</span>
                    </div>

                    <!-- AI Personalized Feedback -->
                    <div class="alert alert-info border border-info border-opacity-25 bg-dark text-start p-4 mb-0">
                        <div class="fw-bold mb-2 text-info"><i class="fa-solid fa-sparkles me-2"></i>AI Tutor Feedback & Recommendations:</div>
                        <div class="text-light" style="line-height: 1.7;">
                            ${res.feedback.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>')}
                        </div>
                    </div>
                </div>

                <!-- Detailed Question-by-Question Solution Review -->
                <h4 class="fw-bold mb-3"><i class="fa-solid fa-list-check text-primary me-2"></i>Question-by-Question Review</h4>
                <div class="d-flex flex-column gap-3 mb-4">
                    ${res.detailed_answers.map(ans => {
                        const statusBadge = ans.is_correct
                            ? `<span class="badge bg-success bg-opacity-25 text-success border border-success border-opacity-25"><i class="fa-solid fa-check me-1"></i>Correct (+1)</span>`
                            : `<span class="badge bg-danger bg-opacity-25 text-danger border border-danger border-opacity-25"><i class="fa-solid fa-xmark me-1"></i>Incorrect</span>`;
                        
                        return `
                            <div class="glass-card p-4">
                                <div class="d-flex justify-content-between align-items-center mb-2">
                                    <span class="fw-bold text-secondary">Question ${ans.question_number} • ${ans.topic}</span>
                                    ${statusBadge}
                                </div>
                                <h5 class="fw-bold mb-3">${ans.question_text}</h5>

                                <div class="bg-dark p-3 rounded-md mb-2 border border-secondary border-opacity-10">
                                    <div class="small text-secondary fw-bold">Your Response:</div>
                                    <div class="${ans.is_correct ? 'text-success' : 'text-danger'}">${ans.student_answer_text || '<em>No answer provided</em>'}</div>
                                </div>

                                <div class="bg-dark p-3 rounded-md mb-2 border border-secondary border-opacity-10">
                                    <div class="small text-secondary fw-bold">Correct Solution:</div>
                                    <div class="text-info">${ans.correct_answer}</div>
                                </div>

                                ${ans.explanation ? `
                                    <div class="small text-secondary mt-2">
                                        <strong>💡 Explanation:</strong> ${ans.explanation}
                                    </div>
                                ` : ''}
                            </div>
                        `;
                    }).join('')}
                </div>

                <!-- Action Buttons -->
                <div class="d-flex justify-content-center gap-3">
                    <a href="exams.html" class="btn btn-outline-light rounded-pill px-4">
                        <i class="fa-solid fa-arrow-left me-2"></i>Back to Exams
                    </a>
                    <a href="chat.html" class="btn btn-primary-gradient px-4">
                        <i class="fa-solid fa-comments me-2"></i>Ask AI Tutor About Weak Topics
                    </a>
                </div>
            </div>
        </div>
    `;
}
