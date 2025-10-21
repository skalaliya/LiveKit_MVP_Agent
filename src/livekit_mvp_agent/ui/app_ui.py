"""
French Tutor Voice App - Main UI
Production-grade PySide6 desktop interface for interactive French learning
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal, Slot, QTimer
from PySide6.QtGui import QAction, QKeySequence, QFont
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QTextEdit,
    QProgressBar,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QGroupBox,
    QSplitter,
    QTabWidget,
    QSlider,
    QFrame,
)

# Add src to path if needed
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from livekit_mvp_agent.config import get_settings
from livekit_mvp_agent.ui.audio_io import AudioInputStream, AudioOutputStream, AudioDevice, AudioConfig
from livekit_mvp_agent.ui.pipeline_worker import PipelineWorker

logger = logging.getLogger(__name__)


class FrenchTutorUI(QMainWindow):
    """Main window for French Tutor Voice App"""
    
    def __init__(self):
        super().__init__()
        
        # Load settings
        self.settings = get_settings()
        
        # Audio state
        self.audio_in: Optional[AudioInputStream] = None
        self.audio_out: Optional[AudioOutputStream] = None
        self.ptt_active = False
        self.auto_vad = True
        
        # Pipeline worker
        self.pipeline: Optional[PipelineWorker] = None
        
        # Setup UI
        self.init_ui()
        self.setup_shortcuts()
        self.setup_audio()
        self.setup_pipeline()
        
        logger.info("French Tutor UI initialized")
    
    def init_ui(self):
        """Initialize user interface"""
        self.setWindowTitle("🇫🇷 French Tutor - Mon Coach de Français")
        self.setGeometry(100, 100, 1200, 800)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Top controls
        controls = self.create_controls()
        layout.addWidget(controls)
        
        # Main content (transcripts)
        content = self.create_content()
        layout.addWidget(content, stretch=1)
        
        # Status bar
        self.create_status_bar()
        
        # Settings panel (hidden by default)
        self.settings_panel = self.create_settings_panel()
        layout.addWidget(self.settings_panel)
        self.settings_panel.hide()
    
    def create_controls(self) -> QWidget:
        """Create top control panel"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        # Big TALK button
        self.talk_btn = QPushButton("🎤 TALK")
        self.talk_btn.setFixedSize(150, 80)
        self.talk_btn.setFont(QFont("Arial", 16, QFont.Bold))
        self.talk_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 10px;
            }
            QPushButton:pressed {
                background-color: #45a049;
            }
            QPushButton:checked {
                background-color: #ff5722;
            }
        """)
        self.talk_btn.setCheckable(True)
        self.talk_btn.clicked.connect(self.toggle_talk)
        layout.addWidget(self.talk_btn)
        
        # Mode toggle
        mode_group = QGroupBox("Mode")
        mode_layout = QVBoxLayout(mode_group)
        
        self.auto_vad_cb = QCheckBox("Auto-VAD")
        self.auto_vad_cb.setChecked(True)
        self.auto_vad_cb.toggled.connect(self.toggle_vad_mode)
        mode_layout.addWidget(self.auto_vad_cb)
        
        self.ptt_cb = QCheckBox("Push-to-Talk")
        self.ptt_cb.toggled.connect(self.toggle_ptt_mode)
        mode_layout.addWidget(self.ptt_cb)
        
        layout.addWidget(mode_group)
        
        # Volume meters
        meters_group = QGroupBox("Audio")
        meters_layout = QVBoxLayout(meters_group)
        
        # Input meter
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Input:"))
        self.input_meter = QProgressBar()
        self.input_meter.setRange(0, 100)
        self.input_meter.setTextVisible(False)
        self.input_meter.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 3px;
                background-color: #f0f0f0;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
        """)
        input_layout.addWidget(self.input_meter)
        meters_layout.addLayout(input_layout)
        
        # VAD indicator
        vad_layout = QHBoxLayout()
        vad_layout.addWidget(QLabel("VAD:"))
        self.vad_indicator = QLabel("⚫ Inactive")
        vad_layout.addWidget(self.vad_indicator)
        vad_layout.addStretch()
        meters_layout.addLayout(vad_layout)
        
        layout.addWidget(meters_group)
        
        # Status indicators
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout(status_group)
        
        self.stt_status = QLabel("STT: Ready")
        status_layout.addWidget(self.stt_status)
        
        self.llm_status = QLabel("LLM: Ready")
        status_layout.addWidget(self.llm_status)
        
        self.tts_status = QLabel("TTS: Ready")
        status_layout.addWidget(self.tts_status)
        
        layout.addWidget(status_group)
        
        # Lesson tools
        tools_group = QGroupBox("Lesson Tools")
        tools_layout = QHBoxLayout(tools_group)
        
        self.repeat_btn = QPushButton("🔁 Répète")
        self.repeat_btn.clicked.connect(lambda: self.send_command("répète"))
        tools_layout.addWidget(self.repeat_btn)
        
        self.slow_btn = QPushButton("🐌 Plus lentement")
        self.slow_btn.clicked.connect(lambda: self.send_command("plus lentement"))
        tools_layout.addWidget(self.slow_btn)
        
        self.explain_btn = QPushButton("💡 Explique")
        self.explain_btn.clicked.connect(lambda: self.send_command("explique"))
        tools_layout.addWidget(self.explain_btn)
        
        self.quiz_btn = QPushButton("📝 Quiz me")
        self.quiz_btn.clicked.connect(lambda: self.send_command("donne-moi un quiz"))
        tools_layout.addWidget(self.quiz_btn)
        
        self.translate_btn = QPushButton("🌍 Translate")
        self.translate_btn.clicked.connect(lambda: self.send_command("translate to English"))
        tools_layout.addWidget(self.translate_btn)
        
        layout.addWidget(tools_group)
        
        # Settings button
        self.settings_btn = QPushButton("⚙️ Settings")
        self.settings_btn.clicked.connect(self.toggle_settings)
        layout.addWidget(self.settings_btn)
        
        layout.addStretch()
        return widget
    
    def create_content(self) -> QWidget:
        """Create main content area with transcripts"""
        splitter = QSplitter(Qt.Horizontal)
        
        # Left: User transcripts
        left_panel = QGroupBox("👤 You (English/French)")
        left_layout = QVBoxLayout(left_panel)
        
        self.user_transcript = QTextEdit()
        self.user_transcript.setReadOnly(True)
        self.user_transcript.setFont(QFont("Courier", 12))
        self.user_transcript.setPlaceholderText("Your speech will appear here...")
        left_layout.addWidget(self.user_transcript)
        
        splitter.addWidget(left_panel)
        
        # Right: Agent responses
        right_panel = QGroupBox("🇫🇷 Coach (French)")
        right_layout = QVBoxLayout(right_panel)
        
        self.agent_transcript = QTextEdit()
        self.agent_transcript.setReadOnly(True)
        self.agent_transcript.setFont(QFont("Courier", 12))
        self.agent_transcript.setStyleSheet("""
            QTextEdit {
                background-color: #f0f8ff;
                color: #000080;
            }
        """)
        self.agent_transcript.setPlaceholderText("Le coach répondra ici...")
        right_layout.addWidget(self.agent_transcript)
        
        splitter.addWidget(right_panel)
        
        return splitter
    
    def create_settings_panel(self) -> QWidget:
        """Create settings panel"""
        panel = QGroupBox("⚙️ Settings")
        layout = QVBoxLayout(panel)
        
        tabs = QTabWidget()
        
        # Audio tab
        audio_tab = QWidget()
        audio_layout = QVBoxLayout(audio_tab)
        
        # Input device
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Input Device:"))
        self.input_device_combo = QComboBox()
        input_layout.addWidget(self.input_device_combo)
        audio_layout.addLayout(input_layout)
        
        # Output device
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Output Device:"))
        self.output_device_combo = QComboBox()
        output_layout.addWidget(self.output_device_combo)
        audio_layout.addLayout(output_layout)
        
        # Populate devices after both combos are created
        self.populate_audio_devices()
        
        # VAD threshold
        vad_layout = QHBoxLayout()
        vad_layout.addWidget(QLabel("VAD Threshold:"))
        self.vad_slider = QSlider(Qt.Horizontal)
        self.vad_slider.setRange(0, 100)
        self.vad_slider.setValue(50)
        vad_layout.addWidget(self.vad_slider)
        self.vad_value_label = QLabel("0.5")
        vad_layout.addWidget(self.vad_value_label)
        self.vad_slider.valueChanged.connect(
            lambda v: self.vad_value_label.setText(f"{v/100:.2f}")
        )
        audio_layout.addLayout(vad_layout)
        
        audio_layout.addStretch()
        tabs.addTab(audio_tab, "Audio")
        
        # Models tab
        models_tab = QWidget()
        models_layout = QVBoxLayout(models_tab)
        
        # Whisper model
        whisper_layout = QHBoxLayout()
        whisper_layout.addWidget(QLabel("STT Model:"))
        self.whisper_combo = QComboBox()
        self.whisper_combo.addItems(["tiny", "base", "small", "medium", "large"])
        self.whisper_combo.setCurrentText(self.settings.whisper_model)
        whisper_layout.addWidget(self.whisper_combo)
        models_layout.addLayout(whisper_layout)
        
        # LLM model
        llm_layout = QHBoxLayout()
        llm_layout.addWidget(QLabel("LLM Model:"))
        self.llm_combo = QComboBox()
        self.llm_combo.addItems([
            "llama3.2:3b",
            "llama3.1:8b-instruct-q4_K_M",
            "mistral:7b-instruct-q4_K_M",
        ])
        self.llm_combo.setCurrentText(self.settings.llm_model)
        llm_layout.addWidget(self.llm_combo)
        models_layout.addLayout(llm_layout)
        
        # TTS voice
        voice_layout = QHBoxLayout()
        voice_layout.addWidget(QLabel("TTS Voice:"))
        self.voice_combo = QComboBox()
        self.voice_combo.addItems([
            "Rachel (EN Female)",
            "Charlotte (FR Female)",
            "Antoine (FR Male)",
        ])
        voice_layout.addWidget(self.voice_combo)
        models_layout.addLayout(voice_layout)
        
        # Speech rate
        rate_layout = QHBoxLayout()
        rate_layout.addWidget(QLabel("Speech Rate:"))
        self.rate_combo = QComboBox()
        self.rate_combo.addItems(["Slow", "Normal", "Fast"])
        self.rate_combo.setCurrentText("Normal")
        rate_layout.addWidget(self.rate_combo)
        models_layout.addLayout(rate_layout)
        
        models_layout.addStretch()
        tabs.addTab(models_tab, "Models")
        
        # Tutor tab
        tutor_tab = QWidget()
        tutor_layout = QVBoxLayout(tutor_tab)
        
        # Target level
        level_layout = QHBoxLayout()
        level_layout.addWidget(QLabel("Target Level:"))
        self.level_combo = QComboBox()
        self.level_combo.addItems(["A1", "A2", "B1", "B2"])
        self.level_combo.setCurrentText("A2")
        level_layout.addWidget(self.level_combo)
        tutor_layout.addLayout(level_layout)
        
        # Language mode
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("Language:"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["French", "Bilingual"])
        self.lang_combo.setCurrentText("French")
        lang_layout.addWidget(self.lang_combo)
        tutor_layout.addLayout(lang_layout)
        
        # Corrections
        self.corrections_cb = QCheckBox("Enable gentle corrections")
        self.corrections_cb.setChecked(True)
        tutor_layout.addWidget(self.corrections_cb)
        
        # IPA pronunciations
        self.ipa_cb = QCheckBox("Show IPA pronunciations")
        self.ipa_cb.setChecked(True)
        tutor_layout.addWidget(self.ipa_cb)
        
        tutor_layout.addStretch()
        tabs.addTab(tutor_tab, "Tutor")
        
        layout.addWidget(tabs)
        
        # Apply/Close buttons
        button_layout = QHBoxLayout()
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self.apply_settings)
        button_layout.addWidget(apply_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(lambda: self.settings_panel.hide())
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        return panel
    
    def create_status_bar(self):
        """Create status bar"""
        self.statusBar().showMessage("Ready")
    
    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # Space = PTT
        self.talk_shortcut = QAction("Talk", self)
        self.talk_shortcut.setShortcut(QKeySequence(Qt.Key_Space))
        self.talk_shortcut.triggered.connect(self.ptt_press)
        self.addAction(self.talk_shortcut)
        
        # Cmd/Ctrl+L = Clear
        clear_action = QAction("Clear", self)
        clear_action.setShortcut(QKeySequence.StandardKey.New)
        clear_action.triggered.connect(self.clear_transcripts)
        self.addAction(clear_action)
        
        # Cmd/Ctrl+S = Save session
        save_action = QAction("Save", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_session)
        self.addAction(save_action)
    
    def setup_audio(self):
        """Setup audio I/O"""
        config = AudioConfig(
            sample_rate=16000,
            channels=1,
            chunk_size=320,  # 20ms
        )
        
        # Input stream
        self.audio_in = AudioInputStream(
            config=config,
            callback=self.on_audio_input,
            device=AudioDevice.get_default_input(),
        )
        
        # Output stream
        self.audio_out = AudioOutputStream(
            config=config,
            device=AudioDevice.get_default_output(),
        )
        
        # Start streams
        self.audio_in.start()
        self.audio_out.start()
        
        logger.info("Audio streams started")
    
    def setup_pipeline(self):
        """Setup AI pipeline worker thread"""
        self.pipeline = PipelineWorker()
        
        # Connect pipeline signals to UI slots
        self.pipeline.user_transcript.connect(self.on_user_transcript)
        self.pipeline.agent_transcript.connect(self.on_agent_transcript)
        self.pipeline.agent_audio.connect(self.on_agent_audio)
        self.pipeline.status_update.connect(self.on_status_update)
        self.pipeline.error_occurred.connect(self.on_error)
        self.pipeline.vad_active.connect(self.on_vad_active)
        
        # Start pipeline worker
        self.pipeline.start()
        
        logger.info("Pipeline worker started")
    
    def populate_audio_devices(self):
        """Populate audio device dropdowns"""
        devices = AudioDevice.list_devices()
        
        for device in devices:
            if device["inputs"] > 0:
                self.input_device_combo.addItem(
                    f"{device['name']} ({device['inputs']}ch)",
                    device["index"],
                )
            if device["outputs"] > 0:
                self.output_device_combo.addItem(
                    f"{device['name']} ({device['outputs']}ch)",
                    device["index"],
                )
    
    @Slot()
    def toggle_talk(self):
        """Toggle talk button"""
        if self.talk_btn.isChecked():
            self.talk_btn.setText("🔴 LISTENING")
            self.ptt_active = True
        else:
            self.talk_btn.setText("🎤 TALK")
            self.ptt_active = False
    
    @Slot()
    def toggle_vad_mode(self, checked):
        """Toggle auto-VAD mode"""
        self.auto_vad = checked
        if checked:
            self.ptt_cb.setChecked(False)
        logger.info(f"Auto-VAD: {checked}")
    
    @Slot()
    def toggle_ptt_mode(self, checked):
        """Toggle push-to-talk mode"""
        if checked:
            self.auto_vad_cb.setChecked(False)
            self.auto_vad = False
        logger.info(f"Push-to-talk: {checked}")
    
    @Slot()
    def ptt_press(self):
        """Handle PTT shortcut (space bar)"""
        if not self.ptt_cb.isChecked():
            return
        self.talk_btn.setChecked(True)
        self.toggle_talk()
    
    @Slot()
    def toggle_settings(self):
        """Toggle settings panel"""
        self.settings_panel.setVisible(not self.settings_panel.isVisible())
    
    @Slot()
    def clear_transcripts(self):
        """Clear all transcripts"""
        self.user_transcript.clear()
        self.agent_transcript.clear()
        if self.pipeline:
            self.pipeline.clear_history()
        logger.info("Transcripts cleared")
    
    @Slot()
    def save_session(self):
        """Save session to file"""
        # TODO: Implement session saving
        logger.info("Save session requested")
        self.statusBar().showMessage("Session saved!", 3000)
    
    @Slot()
    def apply_settings(self):
        """Apply settings changes"""
        # TODO: Apply settings to pipeline
        logger.info("Settings applied")
        self.statusBar().showMessage("Settings applied!", 3000)
    
    @Slot()
    def send_command(self, command: str):
        """Send a lesson command"""
        logger.info(f"Command: {command}")
        self.user_transcript.append(f"[Command] {command}\n")
        # TODO: Send to pipeline
    
    def on_audio_input(self, audio_data, level: float):
        """Handle audio input from microphone"""
        # Update input meter
        self.input_meter.setValue(int(level * 100))
        
        # Send to pipeline if talking (VAD or PTT active)
        if self.pipeline and (self.auto_vad or self.ptt_active):
            # If user starts talking while agent is speaking, cancel agent (barge-in)
            if level > 0.1:  # Voice activity threshold
                if self.audio_out and not self.audio_out._queue.empty():
                    self.audio_out.cancel()  # Stop playback
                    self.pipeline.cancel_speech()  # Cancel TTS generation
            
            self.pipeline.process_audio(audio_data)
    
    @Slot(str)
    def on_user_transcript(self, text: str):
        """Handle user transcript from pipeline"""
        self.append_user_text(text, is_partial=False)
    
    @Slot(str)
    def on_agent_transcript(self, text: str):
        """Handle agent transcript from pipeline"""
        self.append_agent_text(text)
    
    @Slot(bytes)
    def on_agent_audio(self, audio_data: bytes):
        """Handle agent audio from pipeline"""
        if self.audio_out:
            self.audio_out.write(audio_data)
    
    @Slot(str)
    def on_status_update(self, message: str):
        """Handle status updates from pipeline"""
        self.statusBar().showMessage(message)
        logger.debug(f"Status: {message}")
    
    @Slot(str)
    def on_error(self, error_msg: str):
        """Handle errors from pipeline"""
        self.statusBar().showMessage(f"Error: {error_msg}")
        logger.error(f"Pipeline error: {error_msg}")
    
    @Slot(bool)
    def on_vad_active(self, active: bool):
        """Handle VAD activity updates"""
        # Visual feedback for voice activity
        if active:
            self.talk_btn.setStyleSheet("background-color: #4CAF50;")
        else:
            self.talk_btn.setStyleSheet("")
    
    def append_user_text(self, text: str, is_partial: bool = False):
        """Append user transcript"""
        if is_partial:
            # Update last line
            cursor = self.user_transcript.textCursor()
            cursor.movePosition(cursor.End)
            cursor.select(cursor.LineUnderCursor)
            cursor.removeSelectedText()
            self.user_transcript.append(f"[partial] {text}")
        else:
            self.user_transcript.append(f"✓ {text}\n")
    
    def append_agent_text(self, text: str):
        """Append agent transcript"""
        self.agent_transcript.append(f"🇫🇷 {text}\n")
    
    def closeEvent(self, event):
        """Handle window close"""
        if self.pipeline:
            self.pipeline.stop()
        if self.audio_in:
            self.audio_in.stop()
        if self.audio_out:
            self.audio_out.stop()
        logger.info("French Tutor UI closed")
        event.accept()


def main():
    """Main entry point"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("French Tutor")
    app.setOrganizationName("LiveKit MVP Agent")
    
    # Create and show main window
    window = FrenchTutorUI()
    window.show()
    
    # Run event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
