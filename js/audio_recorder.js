/**
 * frontend/js/audio_recorder.js
 * Voice Confession System (Feature #26):
 * - Start recording, Pause/Resume, Stop recording
 * - Listen to recording playback
 * - Delete and rerecord (clears memory and revokes blob URLs)
 * - Browser Danish SpeechRecognition (da-DK) + simulated demo voice recording fallback
 */

export class VoiceConfessionRecorder {
  constructor(options = {}) {
    this.onStateChange = options.onStateChange || (() => {});
    this.onTranscriptUpdate = options.onTranscriptUpdate || (() => {});
    this.onTimerTick = options.onTimerTick || (() => {});
    this.onLevelsUpdate = options.onLevelsUpdate || (() => {});

    this.state = 'IDLE'; // IDLE | RECORDING | PAUSED | REVIEW
    this.mediaRecorder = null;
    this.mediaStream = null;
    this.audioChunks = [];
    this.audioBlob = null;
    this.audioUrl = null;
    this.mimeType = 'audio/webm';
    this.filename = 'confession.webm';

    this.elapsedSeconds = 0;
    this.timerInterval = null;

    this.audioContext = null;
    this.analyser = null;
    this.animFrameId = null;

    this.recognition = null;
    this.liveTranscript = '';
  }

  _detectSupportedMime() {
    if (typeof MediaRecorder === 'undefined') return 'audio/wav';
    const candidates = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/mp4',
      'audio/ogg;codecs=opus',
      'audio/wav',
    ];
    for (const mime of candidates) {
      if (MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported(mime)) {
        return mime;
      }
    }
    return 'audio/webm';
  }

  async startRecording() {
    this.clearRecording();
    this.liveTranscript = '';
    this.onTranscriptUpdate('');

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      // Create simulated recording session for environments without physical mic
      return this._startSimulatedRecording();
    }

    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.mimeType = this._detectSupportedMime();
      const baseMime = this.mimeType.split(';')[0];
      const ext = baseMime.includes('mp4') ? 'mp4' : baseMime.includes('wav') ? 'wav' : 'webm';
      this.filename = `confession.${ext}`;

      this.audioChunks = [];
      this.mediaRecorder = new MediaRecorder(this.mediaStream, { mimeType: this.mimeType });

      this.mediaRecorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          this.audioChunks.push(e.data);
        }
      };

      this.mediaRecorder.onstop = () => {
        const cleanMime = this.mimeType.split(';')[0] || 'audio/webm';
        this.audioBlob = new Blob(this.audioChunks, { type: cleanMime });
        this.audioUrl = URL.createObjectURL(this.audioBlob);
        this._stopStreamAndTimers();
        this.state = 'REVIEW';
        this.onStateChange(this.state, {
          audioUrl: this.audioUrl,
          audioBlob: this.audioBlob,
          duration: this.elapsedSeconds,
          transcript: this.liveTranscript,
        });
      };

      this.mediaRecorder.start(200);
      this._startVisualizer(this.mediaStream);
      this._startBrowserSpeechRecognition();
      this._startTimer();

      this.state = 'RECORDING';
      this.onStateChange(this.state);
    } catch (err) {
      // Fallback to simulated audio recording if mic permission is denied or unavailable
      this._startSimulatedRecording();
    }
  }

  _startSimulatedRecording() {
    this.mimeType = 'audio/wav';
    this.filename = 'confession_combined.wav';
    this.elapsedSeconds = 0;
    this._startTimer();

    // Animate waveform bars gently
    const animateSimulated = () => {
      if (this.state === 'RECORDING') {
        const levels = Array.from({ length: 24 }, () => Math.floor(15 + Math.random() * 75));
        this.onLevelsUpdate(levels);
      }
      if (this.state === 'RECORDING' || this.state === 'PAUSED') {
        this.animFrameId = requestAnimationFrame(animateSimulated);
      }
    };

    this.state = 'RECORDING';
    if (!this.liveTranscript) {
      this.liveTranscript =
        'Jeg talte respektløst til min mor i dag og gjorde grin med hendes vægt. Senere stjal jeg 25 kroner fra min far.';
      this.onTranscriptUpdate(this.liveTranscript);
    }
    this.onStateChange(this.state, { simulated: true });
    this.animFrameId = requestAnimationFrame(animateSimulated);
  }

  pauseRecording() {
    if (this.state !== 'RECORDING') return;
    if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
      this.mediaRecorder.pause();
    }
    this._stopTimer();
    this.state = 'PAUSED';
    this.onStateChange(this.state);
  }

  resumeRecording() {
    if (this.state !== 'PAUSED') return;
    if (this.mediaRecorder && this.mediaRecorder.state === 'paused') {
      this.mediaRecorder.resume();
    }
    this._startTimer();
    this.state = 'RECORDING';
    this.onStateChange(this.state);
  }

  stopRecording() {
    if (this.state !== 'RECORDING' && this.state !== 'PAUSED') return;

    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop();
      return;
    }

    // Finalize simulated WAV recording (valid 1-second 8kHz mono PCM WAV with gentle tone)
    this._stopStreamAndTimers();
    this.audioBlob = this._createValidWavBlob(Math.max(2, this.elapsedSeconds || 3));
    this.audioUrl = URL.createObjectURL(this.audioBlob);
    this.state = 'REVIEW';
    this.onStateChange(this.state, {
      audioUrl: this.audioUrl,
      audioBlob: this.audioBlob,
      duration: Math.max(2, this.elapsedSeconds),
      transcript: this.liveTranscript,
    });
  }

  clearRecording() {
    this._stopStreamAndTimers();
    if (this.audioUrl) {
      URL.revokeObjectURL(this.audioUrl);
      this.audioUrl = null;
    }
    this.audioBlob = null;
    this.audioChunks = [];
    this.elapsedSeconds = 0;
    this.state = 'IDLE';
    this.onTimerTick('00:00');
    this.onLevelsUpdate(new Array(24).fill(10));
    this.onStateChange(this.state);
  }

  _startTimer() {
    this._stopTimer();
    this.timerInterval = setInterval(() => {
      this.elapsedSeconds += 1;
      const mins = String(Math.floor(this.elapsedSeconds / 60)).padStart(2, '0');
      const secs = String(this.elapsedSeconds % 60).padStart(2, '0');
      this.onTimerTick(`${mins}:${secs}`);
      if (this.elapsedSeconds >= 300) {
        this.stopRecording();
      }
    }, 1000);
  }

  _stopTimer() {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
  }

  _startVisualizer(stream) {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      this.audioContext = new AudioCtx();
      const source = this.audioContext.createMediaStreamSource(stream);
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 64;
      source.connect(this.analyser);

      const bufferLength = this.analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      const draw = () => {
        if (this.state !== 'RECORDING' && this.state !== 'PAUSED') return;
        this.analyser.getByteFrequencyData(dataArray);
        const bars = [];
        for (let i = 0; i < 24; i++) {
          const val = dataArray[i % bufferLength] || 10;
          bars.push(Math.max(10, Math.min(100, Math.round((val / 255) * 100))));
        }
        this.onLevelsUpdate(bars);
        this.animFrameId = requestAnimationFrame(draw);
      };
      this.animFrameId = requestAnimationFrame(draw);
    } catch {
      // Ignore visualizer errors
    }
  }

  _startBrowserSpeechRecognition() {
    try {
      const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRec) return;
      this.recognition = new SpeechRec();
      this.recognition.lang = 'da-DK';
      this.recognition.continuous = true;
      this.recognition.interimResults = true;

      let finalTranscript = '';
      this.recognition.onresult = (event) => {
        let interim = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const piece = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalTranscript += piece + ' ';
          } else {
            interim += piece;
          }
        }
        this.liveTranscript = (finalTranscript + interim).trim();
        this.onTranscriptUpdate(this.liveTranscript);
      };
      this.recognition.start();
    } catch {
      // Browser speech recognition optional
    }
  }

  _stopStreamAndTimers() {
    this._stopTimer();
    if (this.animFrameId) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }
    if (this.recognition) {
      try {
        this.recognition.stop();
      } catch {}
      this.recognition = null;
    }
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((t) => t.stop());
      this.mediaStream = null;
    }
    if (this.audioContext) {
      try {
        this.audioContext.close();
      } catch {}
      this.audioContext = null;
    }
  }

  _createValidWavBlob(durationSec = 2) {
    const sampleRate = 8000;
    const numSamples = sampleRate * durationSec;
    const buffer = new ArrayBuffer(44 + numSamples * 2);
    const view = new DataView(buffer);

    const writeStr = (offset, str) => {
      for (let i = 0; i < str.length; i++) {
        view.setUint8(offset + i, str.charCodeAt(i));
      }
    };

    writeStr(0, 'RIFF');
    view.setUint32(4, 36 + numSamples * 2, true);
    writeStr(8, 'WAVE');
    writeStr(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true); // PCM
    view.setUint16(22, 1, true); // Mono
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeStr(36, 'data');
    view.setUint32(40, numSamples * 2, true);

    for (let i = 0; i < numSamples; i++) {
      const sample = Math.sin((2 * Math.PI * 440 * i) / sampleRate) * 0.08;
      view.setInt16(44 + i * 2, sample * 32767, true);
    }

    return new Blob([buffer], { type: 'audio/wav' });
  }
}
