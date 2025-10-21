// French Tutor WebUI - Client-side JavaScript

class FrenchTutorApp {
    constructor() {
        // State
        this.isRecording = false;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.level = 'A2';
        this.difficulty = 2;
        this.topic = 'free';
        this.targetLang = 'fr';
        this.autoMode = false;
        this.lastTutorReply = '';
        
        // DOM elements
        this.talkBtn = document.getElementById('talkBtn');
        this.talkText = document.getElementById('talkText');
        this.autoModeCheckbox = document.getElementById('autoMode');
        this.levelA2Btn = document.getElementById('levelA2');
        this.levelB1Btn = document.getElementById('levelB1');
        this.difficultySlider = document.getElementById('difficulty');
        this.difficultyValue = document.getElementById('difficultyValue');
        this.targetLangSelect = document.getElementById('targetLang');
        this.topicSelect = document.getElementById('topic');
        this.userTranscript = document.getElementById('userTranscript');
        this.tutorTranscript = document.getElementById('tutorTranscript');
        this.statusEl = document.getElementById('status');
        this.audioIndicator = document.getElementById('audio-indicator');
        this.audioPlayer = document.getElementById('audioPlayer');
        this.toast = document.getElementById('toast');
        
        // Teaching control buttons
        this.repeatBtn = document.getElementById('repeatBtn');
        this.slowerBtn = document.getElementById('slowerBtn');
        this.fasterBtn = document.getElementById('fasterBtn');
        this.explainBtn = document.getElementById('explainBtn');
        this.translateBtn = document.getElementById('translateBtn');
        this.saveVocabBtn = document.getElementById('saveVocabBtn');
        this.exportBtn = document.getElementById('exportBtn');
        this.clearBtn = document.getElementById('clearBtn');
        
        this.init();
    }
    
    async init() {
        // Setup event listeners
        this.talkBtn.addEventListener('mousedown', () => this.startRecording());
        this.talkBtn.addEventListener('mouseup', () => this.stopRecording());
        this.talkBtn.addEventListener('touchstart', (e) => {
            e.preventDefault();
            this.startRecording();
        });
        this.talkBtn.addEventListener('touchend', (e) => {
            e.preventDefault();
            this.stopRecording();
        });
        
        this.autoModeCheckbox.addEventListener('change', (e) => {
            this.autoMode = e.target.checked;
            if (this.autoMode) {
                this.showToast('Auto mode enabled', 'success');
            }
        });
        
        this.levelA2Btn.addEventListener('click', () => this.setLevel('A2'));
        this.levelB1Btn.addEventListener('click', () => this.setLevel('B1'));
        
        this.difficultySlider.addEventListener('input', (e) => {
            this.difficulty = parseInt(e.target.value);
            this.difficultyValue.textContent = this.difficulty;
        });
        
        this.targetLangSelect.addEventListener('change', (e) => {
            this.targetLang = e.target.value;
            this.showToast(`Target language: ${e.target.options[e.target.selectedIndex].text}`, 'success');
        });
        
        this.topicSelect.addEventListener('change', (e) => {
            this.topic = e.target.value;
        });
        
        // Teaching controls
        this.repeatBtn.addEventListener('click', () => this.handleRepeat());
        this.slowerBtn.addEventListener('click', () => this.handleSlower());
        this.fasterBtn.addEventListener('click', () => this.handleFaster());
        this.explainBtn.addEventListener('click', () => this.handleExplain());
        this.translateBtn.addEventListener('click', () => this.handleTranslate());
        this.saveVocabBtn.addEventListener('click', () => this.handleSaveVocab());
        this.exportBtn.addEventListener('click', () => this.handleExport());
        this.clearBtn.addEventListener('click', () => this.handleClear());
        
        // Audio player events
        this.audioPlayer.addEventListener('ended', () => {
            this.audioIndicator.classList.remove('playing');
            if (this.autoMode && !this.isRecording) {
                // Auto-restart recording after playback
                setTimeout(() => this.startRecording(), 500);
            }
        });
        
        // Initialize microphone
        try {
            await this.initMicrophone();
            this.talkBtn.disabled = false;
            this.setStatus('Ready - Press and hold to talk');
        } catch (error) {
            console.error('Microphone initialization failed:', error);
            this.showToast('Microphone access denied', 'error');
            this.setStatus('Error: No microphone access');
        }
    }
    
    async initMicrophone() {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        this.mediaRecorder = new MediaRecorder(stream, {
            mimeType: 'audio/webm'
        });
        
        this.mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                this.audioChunks.push(event.data);
            }
        };
        
        this.mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
            this.audioChunks = [];
            
            if (audioBlob.size > 0) {
                await this.processAudio(audioBlob);
            }
        };
    }
    
    startRecording() {
        if (this.isRecording || !this.mediaRecorder) return;
        
        this.isRecording = true;
        this.audioChunks = [];
        this.mediaRecorder.start();
        
        this.talkBtn.classList.add('recording');
        this.talkText.textContent = 'Recording...';
        this.audioIndicator.classList.add('recording');
        this.setStatus('🎤 Recording...');
    }
    
    stopRecording() {
        if (!this.isRecording || !this.mediaRecorder) return;
        
        this.isRecording = false;
        this.mediaRecorder.stop();
        
        this.talkBtn.classList.remove('recording');
        this.talkText.textContent = 'Hold to Talk';
        this.audioIndicator.classList.remove('recording');
        this.setStatus('Processing...');
    }
    
    async processAudio(audioBlob) {
        try {
            // 1. Transcribe audio
            this.setStatus('📝 Transcribing...');
            const transcription = await this.transcribeAudio(audioBlob);
            
            if (!transcription.text || transcription.text.trim() === '') {
                this.setStatus('No speech detected');
                return;
            }
            
            this.addUserMessage(transcription.text);
            
            // 2. Generate reply
            this.setStatus('🧠 Generating reply...');
            const reply = await this.generateReply(transcription.text, 'normal');
            
            if (!reply.text) {
                this.showToast('No response generated', 'error');
                return;
            }
            
            this.lastTutorReply = reply.text;
            this.addTutorMessage(reply.text);
            
            // 3. Synthesize speech
            this.setStatus('🔊 Generating speech...');
            await this.speakText(reply.text, 'normal');
            
            this.setStatus('Ready');
            
        } catch (error) {
            console.error('Audio processing error:', error);
            this.showToast(`Error: ${error.message}`, 'error');
            this.setStatus('Error');
        }
    }
    
    async transcribeAudio(audioBlob) {
        const formData = new FormData();
        formData.append('file', audioBlob, 'audio.webm');
        
        const response = await fetch('/api/transcribe', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`Transcription failed: ${response.statusText}`);
        }
        
        return await response.json();
    }
    
    async generateReply(text, mode = 'normal', translateTo = null) {
        const response = await fetch('/api/reply', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text,
                level: this.level,
                difficulty: this.difficulty,
                topic: this.topic,
                target_lang: this.targetLang,
                mode,
                translate_to: translateTo
            })
        });
        
        if (!response.ok) {
            throw new Error(`Reply generation failed: ${response.statusText}`);
        }
        
        return await response.json();
    }
    
    async speakText(text, speed = 'normal') {
        this.setStatus('🔊 Speaking...');
        this.audioIndicator.classList.add('playing');
        
        try {
            const response = await fetch('/api/speak', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text, speed })
            });
            
            if (!response.ok) {
                throw new Error(`Speech synthesis failed: ${response.statusText}`);
            }
            
            const audioBlob = await response.blob();
            
            if (audioBlob.size === 0) {
                // No TTS available
                this.audioIndicator.classList.remove('playing');
                this.setStatus('Ready (TTS unavailable)');
                return;
            }
            
            const audioUrl = URL.createObjectURL(audioBlob);
            this.audioPlayer.src = audioUrl;
            await this.audioPlayer.play();
            
        } catch (error) {
            console.error('Speech synthesis error:', error);
            this.audioIndicator.classList.remove('playing');
            this.showToast('TTS unavailable', 'error');
        }
    }
    
    // Teaching control handlers
    async handleRepeat() {
        if (!this.lastTutorReply) {
            this.showToast('Nothing to repeat yet', 'error');
            return;
        }
        
        this.setStatus('↻ Repeating...');
        const reply = await this.generateReply('', 'repeat');
        this.addTutorMessage(`🔁 ${reply.text}`);
        await this.speakText(reply.text, 'normal');
        this.setStatus('Ready');
    }
    
    async handleSlower() {
        if (!this.lastTutorReply) {
            this.showToast('No previous message', 'error');
            return;
        }
        
        this.setStatus('🐢 Speaking slower...');
        const reply = await this.generateReply(this.lastTutorReply, 'slower');
        this.lastTutorReply = reply.text;
        this.addTutorMessage(`🐢 ${reply.text}`);
        await this.speakText(reply.text, 'slow');
        this.setStatus('Ready');
    }
    
    async handleFaster() {
        if (!this.lastTutorReply) {
            this.showToast('No previous message', 'error');
            return;
        }
        
        this.setStatus('⚡ Speaking faster...');
        const reply = await this.generateReply(this.lastTutorReply, 'faster');
        this.lastTutorReply = reply.text;
        this.addTutorMessage(`⚡ ${reply.text}`);
        await this.speakText(reply.text, 'fast');
        this.setStatus('Ready');
    }
    
    async handleExplain() {
        if (!this.lastTutorReply) {
            this.showToast('No previous message', 'error');
            return;
        }
        
        this.setStatus('💡 Explaining...');
        const reply = await this.generateReply(this.lastTutorReply, 'explain');
        this.addTutorMessage(`💡 ${reply.text}`);
        this.setStatus('Ready');
    }
    
    async handleTranslate() {
        if (!this.lastTutorReply) {
            this.showToast('No previous message', 'error');
            return;
        }
        
        const translateTo = this.targetLang === 'fr' ? 'en' : 'fr';
        this.setStatus('🔁 Translating...');
        const reply = await this.generateReply(this.lastTutorReply, 'translate', translateTo);
        this.addTutorMessage(`🔁 ${reply.text}`);
        this.setStatus('Ready');
    }
    
    async handleSaveVocab() {
        // Get selected text or use last key phrase from tutor reply
        const selection = window.getSelection().toString();
        const term = selection || this.extractKeyTerm(this.lastTutorReply);
        
        if (!term) {
            this.showToast('Select text to save', 'error');
            return;
        }
        
        try {
            await fetch('/api/vocab', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    term,
                    context: this.lastTutorReply
                })
            });
            
            this.showToast(`Saved: ${term}`, 'success');
        } catch (error) {
            this.showToast('Failed to save vocab', 'error');
        }
    }
    
    async handleExport() {
        try {
            const fmt = 'json'; // Could add UI to choose json/csv
            const response = await fetch(`/api/session/export?fmt=${fmt}`);
            
            if (!response.ok) {
                throw new Error('Export failed');
            }
            
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `session_${new Date().toISOString().slice(0,10)}.${fmt}`;
            a.click();
            URL.revokeObjectURL(url);
            
            this.showToast('Session exported', 'success');
        } catch (error) {
            this.showToast('Export failed', 'error');
        }
    }
    
    async handleClear() {
        if (!confirm('Clear session and start fresh?')) {
            return;
        }
        
        try {
            await fetch('/api/session/clear', { method: 'POST' });
            this.userTranscript.innerHTML = '';
            this.tutorTranscript.innerHTML = '';
            this.lastTutorReply = '';
            this.showToast('Session cleared', 'success');
            this.setStatus('Ready');
        } catch (error) {
            this.showToast('Clear failed', 'error');
        }
    }
    
    // UI helpers
    setLevel(level) {
        this.level = level;
        if (level === 'A2') {
            this.levelA2Btn.classList.add('active');
            this.levelB1Btn.classList.remove('active');
        } else {
            this.levelB1Btn.classList.add('active');
            this.levelA2Btn.classList.remove('active');
        }
        this.showToast(`Level: ${level}`, 'success');
    }
    
    addUserMessage(text) {
        const time = new Date().toLocaleTimeString();
        const messageEl = document.createElement('div');
        messageEl.className = 'message message-user';
        messageEl.innerHTML = `
            <div class="message-time">${time}</div>
            <div class="message-text">${this.escapeHtml(text)}</div>
        `;
        this.userTranscript.appendChild(messageEl);
        this.userTranscript.scrollTop = this.userTranscript.scrollHeight;
    }
    
    addTutorMessage(text) {
        const time = new Date().toLocaleTimeString();
        const messageEl = document.createElement('div');
        messageEl.className = 'message message-tutor';
        messageEl.innerHTML = `
            <div class="message-time">${time}</div>
            <div class="message-text">${this.escapeHtml(text)}</div>
        `;
        this.tutorTranscript.appendChild(messageEl);
        this.tutorTranscript.scrollTop = this.tutorTranscript.scrollHeight;
    }
    
    setStatus(message) {
        this.statusEl.textContent = message;
    }
    
    showToast(message, type = 'info') {
        this.toast.textContent = message;
        this.toast.className = `toast show ${type}`;
        setTimeout(() => {
            this.toast.classList.remove('show');
        }, 3000);
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    extractKeyTerm(text) {
        // Simple extraction: get first significant word (> 3 chars)
        const words = text.split(/\s+/);
        for (const word of words) {
            const clean = word.replace(/[^\w\u00C0-\u017F]/g, '');
            if (clean.length > 3) {
                return clean;
            }
        }
        return words[0] || '';
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new FrenchTutorApp();
});
