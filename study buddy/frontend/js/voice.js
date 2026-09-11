// Multilingual Web Speech API Voice Recognition & Synthesis Engine
let recognition = null;
let isRecording = false;
let currentUtterance = null;
let currentSpeakingBtn = null;
let autoSpeakEnabled = false;

const LANG_MAP = {
    'Telugu': 'te-IN',
    'Hindi': 'hi-IN',
    'English': 'en-IN',
    'Tamil': 'ta-IN',
    'Kannada': 'kn-IN'
};

document.addEventListener('DOMContentLoaded', () => {
    initSpeechRecognition();

    const micBtn = document.getElementById('micBtn');
    if (micBtn) {
        micBtn.setAttribute('aria-label', 'Start voice input');
        micBtn.addEventListener('click', (e) => {
            e.preventDefault();
            toggleVoiceRecording();
        });
    }

    const autoSpeakToggle = document.getElementById('autoSpeakToggle');
    if (autoSpeakToggle) {
        autoSpeakToggle.addEventListener('change', (e) => {
            autoSpeakEnabled = e.target.checked;
            showToast(autoSpeakEnabled ? '🔊 Auto-Speak Enabled' : '🔇 Auto-Speak Disabled', 'info');
        });
    }

    // Warm up available voices for Web Speech Synthesis
    if ('speechSynthesis' in window) {
        window.speechSynthesis.getVoices();
        if (typeof window.speechSynthesis.onvoiceschanged !== 'undefined') {
            window.speechSynthesis.onvoiceschanged = () => {
                window.speechSynthesis.getVoices();
            };
        }
    }
});

function initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        console.warn('[VOICE] Web Speech Recognition API is not supported in this browser.');
        return;
    }

    try {
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = true;

        recognition.onstart = () => {
            console.log('[VOICE] Recognition started');
            isRecording = true;
            updateVoiceUI('listening');
        };

        recognition.onresult = (event) => {
            updateVoiceUI('processing');
            let transcript = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                transcript += event.results[i][0].transcript;
            }

            const input = document.getElementById('chatInput');
            if (input && transcript) {
                input.value = transcript;
            }
            console.log('[VOICE] Transcript received:', transcript);
        };

        recognition.onerror = (event) => {
            console.error('[VOICE] Speech recognition error:', event.error);
            isRecording = false;
            let userMsg = 'Could not process audio. Please try again.';
            if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
                userMsg = 'Microphone access was denied. Please check your browser permissions.';
                updateVoiceUI('error', 'Permission Denied');
            } else if (event.error === 'no-speech') {
                userMsg = 'No speech was detected. Please try speaking again.';
                updateVoiceUI('idle');
            } else if (event.error === 'network') {
                userMsg = 'Network error during speech recognition.';
                updateVoiceUI('error', 'Network Error');
            } else if (event.error === 'audio-capture') {
                userMsg = 'No microphone was found or microphone is busy.';
                updateVoiceUI('error', 'Mic Unavailable');
            } else {
                updateVoiceUI('idle');
            }
            showToast(userMsg, 'error');
        };

        recognition.onend = () => {
            console.log('[VOICE] Recognition ended');
            isRecording = false;
            const input = document.getElementById('chatInput');
            if (input && input.value.trim().length > 0) {
                updateVoiceUI('transcribed');
            } else {
                updateVoiceUI('idle');
            }
        };
    } catch (err) {
        console.error('[VOICE] Failed to initialize SpeechRecognition:', err);
    }
}

function toggleVoiceRecording() {
    console.log('[VOICE] Microphone button clicked');
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognition && !recognition) {
        showToast('Voice input is not supported in this browser.', 'error');
        simulateBackendVoiceTranscribe();
        return;
    }

    if (!recognition) {
        initSpeechRecognition();
    }

    if (!recognition) {
        simulateBackendVoiceTranscribe();
        return;
    }

    if (isRecording) {
        try {
            recognition.stop();
        } catch (e) {
            console.error('[VOICE] Error stopping recognition:', e);
        }
        isRecording = false;
        updateVoiceUI('idle');
    } else {
        const langSelect = document.getElementById('languageSelect');
        const selectedLang = langSelect ? langSelect.value : 'English';
        recognition.lang = LANG_MAP[selectedLang] || 'en-IN';

        try {
            recognition.start();
        } catch (e) {
            console.error('[VOICE] Failed to start recognition:', e);
            if (e.name === 'InvalidStateError' || (e.message && e.message.includes('already started'))) {
                try { recognition.stop(); } catch (_) {}
            }
            isRecording = false;
            updateVoiceUI('idle');
        }
    }
}

async function simulateBackendVoiceTranscribe() {
    const langSelect = document.getElementById('languageSelect');
    const selectedLang = langSelect ? langSelect.value : 'English';

    updateVoiceUI('listening');

    setTimeout(async () => {
        updateVoiceUI('processing');
        try {
            const data = await API.request('/voice/transcribe', {
                method: 'POST',
                body: JSON.stringify({ language: selectedLang })
            });

            const input = document.getElementById('chatInput');
            if (input && data.text) {
                input.value = data.text;
                showToast(`✓ Voice Transcribed (${selectedLang})`, 'success');
            }
        } catch (e) {
            showToast('Voice transcription failed.', 'error');
        } finally {
            updateVoiceUI('transcribed');
        }
    }, 1500);
}

function updateVoiceUI(state, customTooltip = null) {
    const micBtn = document.getElementById('micBtn');
    const input = document.getElementById('chatInput');

    if (!micBtn) return;

    if (state === 'listening') {
        micBtn.innerHTML = '<i class="fa-solid fa-microphone-slash"></i>';
        micBtn.classList.add('mic-active', 'btn-danger');
        micBtn.classList.remove('btn-mic');
        micBtn.title = customTooltip || '🎙 Listening... Click to stop';
        micBtn.setAttribute('aria-label', 'Listening. Click to stop voice input');
        if (input) input.placeholder = '🎙 Listening to your voice... Speak now!';
    } else if (state === 'processing') {
        micBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
        micBtn.title = customTooltip || '⏳ Processing speech...';
        micBtn.setAttribute('aria-label', 'Processing speech');
        if (input) input.placeholder = '⏳ Transcribing speech...';
    } else if (state === 'transcribed') {
        micBtn.innerHTML = '<i class="fa-solid fa-check"></i>';
        micBtn.classList.remove('mic-active', 'btn-danger');
        micBtn.classList.add('btn-mic');
        micBtn.title = customTooltip || '✓ Transcribed! Edit or click send.';
        micBtn.setAttribute('aria-label', 'Transcribed. Click microphone to record again');
        if (input) input.placeholder = 'Ask any doubt in English, Telugu, or Hindi...';
    } else if (state === 'error') {
        micBtn.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i>';
        micBtn.classList.remove('mic-active');
        micBtn.classList.add('btn-danger');
        micBtn.title = customTooltip || '⚠ Voice input error';
        micBtn.setAttribute('aria-label', 'Voice input error');
        if (input) input.placeholder = 'Ask any doubt in English, Telugu, or Hindi...';
        setTimeout(() => {
            updateVoiceUI('idle');
        }, 3000);
    } else {
        micBtn.innerHTML = '<i class="fa-solid fa-microphone"></i>';
        micBtn.classList.remove('mic-active', 'btn-danger');
        micBtn.classList.add('btn-mic');
        micBtn.title = customTooltip || '🎤 Start Speaking';
        micBtn.setAttribute('aria-label', 'Start voice input');
        if (input) input.placeholder = 'Ask any doubt in English, Telugu, or Hindi...';
    }
}

/* =========================================
   TEXT-TO-SPEECH (TTS) VOICE SYNTHESIS
   ========================================= */

function getBestVoice(langCode) {
    if (!('speechSynthesis' in window)) return null;
    const voices = window.speechSynthesis.getVoices();
    if (!voices || voices.length === 0) return null;

    let voice = voices.find(v => v.lang === langCode || v.lang.replace('_', '-') === langCode);
    if (voice) return voice;

    const prefix = langCode.split('-')[0];
    voice = voices.find(v => v.lang.startsWith(prefix));
    if (voice) return voice;

    return null;
}

function cleanTextForSpeech(rawText) {
    if (!rawText) return '';
    return rawText
        .replace(/<[^>]*>/g, ' ')
        .replace(/```[\s\S]*?```/g, '')
        .replace(/`([^`]+)`/g, '$1')
        .replace(/\[([^\]]+)\]\([^\)]+\)/g, '$1')
        .replace(/[\*\#\_`~\-\+\>\=]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
}

function speakText(rawText, language = 'English', btnElement = null) {
    console.log('[TTS] Listen button clicked');
    if (!('speechSynthesis' in window)) {
        showToast('Text-to-Speech is not supported by your browser.', 'error');
        return;
    }

    const cleanText = cleanTextForSpeech(rawText);
    if (!cleanText) {
        showToast('No response available to read.', 'warning');
        return;
    }

    console.log('[TTS] Text length:', cleanText.length, '| Language:', language);

    // Stop any existing playback
    stopSpeech();

    currentUtterance = new SpeechSynthesisUtterance(cleanText);
    const targetLangCode = LANG_MAP[language] || 'en-IN';
    currentUtterance.lang = targetLangCode;
    currentUtterance.rate = 0.95; // Slightly clear pace for educational clarity

    const voice = getBestVoice(targetLangCode);
    if (voice) {
        currentUtterance.voice = voice;
    }

    currentSpeakingBtn = btnElement;

    currentUtterance.onstart = () => {
        console.log('[TTS] Speech started');
        if (btnElement) {
            btnElement.innerHTML = '<i class="fa-solid fa-square"></i> Stop';
            btnElement.classList.remove('btn-outline-primary');
            btnElement.classList.add('btn-danger');
            btnElement.setAttribute('aria-label', 'Stop listening to AI response');
            btnElement.onclick = () => stopSpeech(btnElement);
        }
    };

    currentUtterance.onend = () => {
        console.log('[TTS] Speech ended');
        resetAudioBtn(btnElement);
        currentSpeakingBtn = null;
    };

    currentUtterance.onerror = (e) => {
        console.error('[TTS] Speech error:', e);
        if (e.error !== 'interrupted' && e.error !== 'canceled') {
            showToast('Could not play the response audio.', 'error');
        }
        resetAudioBtn(btnElement);
        currentSpeakingBtn = null;
    };

    window.speechSynthesis.cancel();
    setTimeout(() => {
        try {
            window.speechSynthesis.speak(currentUtterance);
        } catch (err) {
            console.error('[TTS] Failed to execute speak:', err);
            resetAudioBtn(btnElement);
        }
    }, 50);
}

function stopSpeech(btnElement = null) {
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
    }
    const targetBtn = btnElement || currentSpeakingBtn;
    if (targetBtn) {
        resetAudioBtn(targetBtn);
    } else {
        document.querySelectorAll('.btn-tts-listen').forEach(b => resetAudioBtn(b));
    }
    currentSpeakingBtn = null;
}

function resetAudioBtn(btnElement) {
    if (!btnElement) return;
    btnElement.innerHTML = '<i class="fa-solid fa-volume-high"></i> Listen';
    btnElement.classList.remove('btn-danger');
    btnElement.classList.add('btn-outline-primary');
    btnElement.setAttribute('aria-label', 'Listen to AI response');
    const text = btnElement.getAttribute('data-raw-text') || '';
    const lang = btnElement.getAttribute('data-lang') || 'English';
    btnElement.onclick = () => speakText(text, lang, btnElement);
}

// Expose functions globally for inline handlers and chat module
window.initSpeechRecognition = initSpeechRecognition;
window.toggleVoiceRecording = toggleVoiceRecording;
window.speakText = speakText;
window.stopSpeech = stopSpeech;
window.resetAudioBtn = resetAudioBtn;
window.updateVoiceUI = updateVoiceUI;
