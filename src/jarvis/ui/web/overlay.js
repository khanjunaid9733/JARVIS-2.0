/**
 * JARVIS 2.0 — Transparent Desktop HUD Overlay Engine
 *
 * Cinematic arc reactor renderer, ambient floating particles,
 * chat drawer controller, voice recognition, event stream polling,
 * and full backend integration.
 */

// ==========================================================================
//  ARC REACTOR RENDERER — Cinematic holographic core
// ==========================================================================

class ArcReactorRenderer {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext('2d');
    this.status = 'idle';
    this.angle = 0;
    this.bootPhase = 0;  // 0 → 1 over ~2 seconds for boot-up animation
    this.bootStart = performance.now();
    this.particles = [];

    // Pre-generate orbital particles
    for (let i = 0; i < 50; i++) {
      this.particles.push({
        theta: Math.random() * Math.PI * 2,
        radius: 55 + Math.random() * 35,
        speed: (Math.random() * 0.015) + 0.004,
        size: Math.random() * 1.8 + 0.5,
        brightness: Math.random() * 0.6 + 0.4,
        orbit: Math.random() * 0.3 + 0.3, // y-squish for 3D perspective
      });
    }

    this._resize();
    this._render();
  }

  _resize() {
    const dpr = window.devicePixelRatio || 1;
    this.canvas.width = 200 * dpr;
    this.canvas.height = 200 * dpr;
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this.w = 200;
    this.h = 200;
  }

  setStatus(s) { this.status = s; }

  _colors() {
    const map = {
      listening:         { pri: '#00ff88', glow: 'rgba(0,255,136,0.4)',  core: '#b0ffd8' },
      thinking:          { pri: '#ffb700', glow: 'rgba(255,183,0,0.4)',  core: '#ffe58a' },
      acting:            { pri: '#00e5ff', glow: 'rgba(0,229,255,0.6)',  core: '#ffffff' },
      emergency_stopped: { pri: '#ff0055', glow: 'rgba(255,0,85,0.6)',   core: '#ff80aa' },
      blinded:           { pri: '#778899', glow: 'rgba(119,136,153,0.3)',core: '#b0c4de' },
    };
    return map[this.status] || { pri: '#00e5ff', glow: 'rgba(0,229,255,0.35)', core: '#80f2ff' };
  }

  _render() {
    const ctx = this.ctx;
    const w = this.w, h = this.h;
    const cx = w / 2, cy = h / 2;
    const c = this._colors();

    // Boot-up animation: 0 → 1 over 2 seconds
    const elapsed = (performance.now() - this.bootStart) / 2000;
    this.bootPhase = Math.min(1, elapsed);
    const bp = this.bootPhase;

    const speed = this.status === 'thinking' ? 2.5 : this.status === 'acting' ? 3 : 1;
    this.angle += 0.012 * speed;

    ctx.clearRect(0, 0, w, h);
    ctx.globalAlpha = bp;

    // --- Layer 1: Orbital Particle Cloud ---
    ctx.save();
    ctx.translate(cx, cy);
    for (const p of this.particles) {
      p.theta += p.speed * speed;
      const px = Math.cos(p.theta) * p.radius;
      const py = Math.sin(p.theta) * p.radius * p.orbit;
      ctx.beginPath();
      ctx.arc(px, py, p.size, 0, Math.PI * 2);
      ctx.fillStyle = c.pri;
      ctx.globalAlpha = bp * p.brightness * (0.4 + Math.sin(p.theta) * 0.3);
      ctx.shadowColor = c.pri;
      ctx.shadowBlur = 4;
      ctx.fill();
    }
    ctx.restore();
    ctx.globalAlpha = bp;

    // --- Layer 2: Outer Segmented Ring ---
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(this.angle * 0.35);
    ctx.strokeStyle = c.pri;
    ctx.lineWidth = 1.8;
    ctx.shadowColor = c.glow;
    ctx.shadowBlur = 12;
    const segs = 10;
    const rO = 82 * bp;
    for (let i = 0; i < segs; i++) {
      const a = (i * Math.PI * 2) / segs;
      const gap = (Math.PI / segs) * 0.35;
      ctx.beginPath();
      ctx.arc(0, 0, rO, a, a + (Math.PI * 2 / segs) - gap);
      ctx.stroke();
    }
    ctx.restore();

    // --- Layer 3: Counter-Rotating Tick Ring ---
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(-this.angle * 0.6);
    ctx.strokeStyle = c.glow;
    ctx.lineWidth = 1;
    ctx.shadowBlur = 6;
    const rM = 66 * bp;
    const ticks = 30;
    for (let i = 0; i < ticks; i++) {
      const a = (i * Math.PI * 2) / ticks;
      const len = i % 5 === 0 ? 7 : 3;
      ctx.beginPath();
      ctx.moveTo(Math.cos(a) * (rM - len), Math.sin(a) * (rM - len));
      ctx.lineTo(Math.cos(a) * rM, Math.sin(a) * rM);
      ctx.stroke();
    }
    ctx.restore();

    // --- Layer 4: Inner Waveform Ring ---
    ctx.save();
    ctx.translate(cx, cy);
    ctx.beginPath();
    const rI = 42 * bp;
    const wPts = 40;
    for (let i = 0; i <= wPts; i++) {
      const a = (i * Math.PI * 2) / wPts;
      const wAmp = this.status === 'listening' ? 6 : this.status === 'thinking' ? 4 : 2;
      const wave = Math.sin(a * 5 + this.angle * 3.5) * wAmp;
      const r = rI + wave;
      const x = Math.cos(a) * r, y = Math.sin(a) * r;
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.strokeStyle = c.pri;
    ctx.lineWidth = 2;
    ctx.shadowColor = c.pri;
    ctx.shadowBlur = 16;
    ctx.stroke();
    ctx.restore();

    // --- Layer 5: Central Core Glow ---
    ctx.save();
    ctx.translate(cx, cy);
    const pulse = Math.sin(this.angle * 2.5) * 4;
    const coreR = (28 + pulse) * bp;
    const grad = ctx.createRadialGradient(0, 0, 2, 0, 0, coreR);
    grad.addColorStop(0, c.core);
    grad.addColorStop(0.35, c.pri);
    grad.addColorStop(1, 'transparent');
    ctx.beginPath();
    ctx.arc(0, 0, coreR, 0, Math.PI * 2);
    ctx.fillStyle = grad;
    ctx.globalAlpha = bp * 0.9;
    ctx.fill();

    // Central geometric ring
    ctx.globalAlpha = bp;
    ctx.rotate(this.angle * 0.8);
    ctx.strokeStyle = 'rgba(255,255,255,0.7)';
    ctx.lineWidth = 1;
    ctx.shadowBlur = 0;
    ctx.beginPath();
    ctx.arc(0, 0, 10 * bp, 0, Math.PI * 2);
    ctx.stroke();

    // Inner triangle
    ctx.beginPath();
    for (let i = 0; i < 3; i++) {
      const a = (i * Math.PI * 2) / 3 - Math.PI / 2;
      const x = Math.cos(a) * 7 * bp;
      const y = Math.sin(a) * 7 * bp;
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.strokeStyle = 'rgba(255,255,255,0.5)';
    ctx.stroke();
    ctx.restore();

    ctx.globalAlpha = 1;
    requestAnimationFrame(() => this._render());
  }
}


// ==========================================================================
//  AMBIENT PARTICLES — Floating holographic dust across the screen
// ==========================================================================

class AmbientParticleLayer {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext('2d');
    this.particles = [];
    this._resize();
    window.addEventListener('resize', () => this._resize());

    for (let i = 0; i < 35; i++) {
      this.particles.push({
        x: Math.random() * this.w,
        y: Math.random() * this.h,
        vx: (Math.random() - 0.5) * 0.3,
        vy: (Math.random() - 0.5) * 0.15 - 0.1,
        size: Math.random() * 1.5 + 0.5,
        alpha: Math.random() * 0.3 + 0.1,
        color: Math.random() > 0.7 ? '#00ff88' : '#00e5ff',
      });
    }

    this._render();
  }

  _resize() {
    const dpr = window.devicePixelRatio || 1;
    this.w = window.innerWidth;
    this.h = window.innerHeight;
    this.canvas.width = this.w * dpr;
    this.canvas.height = this.h * dpr;
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  _render() {
    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.w, this.h);

    for (const p of this.particles) {
      p.x += p.vx;
      p.y += p.vy;

      // Wrap around screen edges
      if (p.x < 0) p.x = this.w;
      if (p.x > this.w) p.x = 0;
      if (p.y < 0) p.y = this.h;
      if (p.y > this.h) p.y = 0;

      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fillStyle = p.color;
      ctx.globalAlpha = p.alpha;
      ctx.shadowColor = p.color;
      ctx.shadowBlur = 6;
      ctx.fill();
    }

    ctx.globalAlpha = 1;
    requestAnimationFrame(() => this._render());
  }
}


// ==========================================================================
//  HUD OVERLAY CONTROLLER — Chat, voice, events, backend
// ==========================================================================

class HUDOverlayController {
  constructor() {
    this.reactor = new ArcReactorRenderer('reactor-canvas');
    this.ambient = new AmbientParticleLayer('ambient-canvas');
    this.knownEventIds = new Set();
    this.uptimeSeconds = 0;
    this.isEstopTripped = false;
    this.isBlinded = false;
    this.isChatOpen = false;
    this.currentStatus = 'idle';
    this.isWakeWordActive = true;
    this.speechState = 'WAKE'; // 'WAKE' | 'COMMAND'
    this.recognition = null;
    this.commandTimer = null;

    this._bindDOM();
    this._startPolling();
    this._startUptimeClock();
    this._playBootChime();

    // Auto-engage hands-free acoustic wake word after bootup
    setTimeout(() => this._startRecognition(), 1200);
  }

  _bindDOM() {
    // Wake Word Toggle
    const wakeBtn = document.getElementById('btn-wakeword');
    if (wakeBtn) {
      wakeBtn.addEventListener('click', () => this._toggleContinuousWakeWord());
    }

    // Chat toggle
    document.getElementById('btn-toggle-chat').addEventListener('click', () => this._toggleChat());
    document.getElementById('btn-close-chat').addEventListener('click', () => this._toggleChat(false));

    // Chat form
    const form = document.getElementById('chat-form');
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const input = document.getElementById('chat-input');
      const val = input.value.trim();
      if (!val) return;
      this._sendMessage(val);
      input.value = '';
    });

    // Voice mic
    document.getElementById('btn-mic').addEventListener('click', () => this._toggleVoice());

    // E-Stop
    document.getElementById('btn-estop').addEventListener('click', () => this._triggerEstop());

    // Shutter
    document.getElementById('btn-shutter').addEventListener('click', () => this._toggleShutter());

    // Enable desktop dragging on the Arc Reactor
    this._makeDraggable('reactor-anchor');
  }

  _setStatus(status) {
    this.currentStatus = status;
    this.reactor.setStatus(status);

    // Update body class for CSS status modes
    document.body.className = `status-${status}`;

    // Update ticker
    const statusEl = document.getElementById('companion-status');
    statusEl.textContent = status.toUpperCase().replace('_', ' ');

    // Update reactor label
    const stateEl = document.getElementById('reactor-state');
    const subEl = document.getElementById('reactor-sub');
    const labels = {
      idle:              ['ONLINE',            'STANDING BY'],
      listening:         ['LISTENING',          'AUDIO SENSORS ACTIVE'],
      thinking:          ['PROCESSING',         'NEURAL COMPUTATION'],
      acting:            ['DISPATCHING',        'EXECUTING EFFECT'],
      emergency_stopped: ['EMERGENCY HALT',     'AUTOMATION LOCKED'],
      blinded:           ['SHUTTER ENGAGED',    'PERCEPTION BLINDED'],
    };
    const [s, sub] = labels[status] || ['ONLINE', 'STANDING BY'];
    stateEl.textContent = s;
    subEl.textContent = sub;

    // Inform backend
    fetch('/api/status', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status })
    }).catch(() => {});
  }

  _toggleChat(forceState) {
    this.isChatOpen = forceState !== undefined ? forceState : !this.isChatOpen;
    document.getElementById('chat-drawer').classList.toggle('open', this.isChatOpen);
    if (this.isChatOpen) {
      setTimeout(() => document.getElementById('chat-input').focus(), 350);
    }
  }

  _appendMessage(sender, text, isUser = false) {
    const history = document.getElementById('chat-history');
    const msg = document.createElement('div');
    msg.className = `chat-msg ${isUser ? 'user-msg' : 'jarvis-msg'}`;
    msg.innerHTML = `
      <div class="msg-indicator"></div>
      <div class="msg-content">
        <span class="msg-sender">${isUser ? 'YOU' : 'JARVIS'}</span>
        <span class="msg-text">${this._escapeHTML(text)}</span>
      </div>
    `;
    history.appendChild(msg);
    history.scrollTop = history.scrollHeight;
  }

  async _sendMessage(text) {
    // Auto-open chat drawer
    this._toggleChat(true);
    this._appendMessage('You', text, true);
    this._setStatus('thinking');

    try {
      let endpoint = '/api/say';
      let payload = { text };

      if (text.toLowerCase().startsWith('run skill:') || text.toLowerCase().startsWith('execute:')) {
        endpoint = '/api/skill/auto';
        payload = { goal: text.replace(/^(run skill:|execute:)/i, '').trim() };
      }

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      this._setStatus('acting');

      if (data.reply) {
        this._appendMessage('JARVIS', data.reply);
        this._speak(data.reply);
      } else if (data.message) {
        this._appendMessage('JARVIS', `[${data.status || 'RESULT'}] ${data.message}`);
      }

      // Browser URLs are handled directly by the JARVIS desktop backend to prevent duplicate tabs
      setTimeout(() => this._setStatus('idle'), 1800);
    } catch (err) {
      this._setStatus('idle');
      this._appendMessage('JARVIS', `Communication fault: ${err.message}`);
    }
  }

  _speak(text) {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utter = new SpeechSynthesisUtterance(text);
      utter.rate = 1.0;
      utter.pitch = 0.94;
      utter.volume = 1.0;

      // Select authentic British English voice for Paul Bettany cadence
      const voices = window.speechSynthesis.getVoices();
      const ukVoice = voices.find(v =>
        (v.lang === 'en-GB' || v.lang.startsWith('en-GB')) &&
        (v.name.includes('Ryan') || v.name.includes('George') || v.name.includes('Male') || v.name.includes('Oliver') || v.name.includes('David'))
      ) || voices.find(v => v.lang === 'en-GB') || voices.find(v => v.lang.startsWith('en'));

      if (ukVoice) {
        utter.voice = ukVoice;
      }

      window.speechSynthesis.speak(utter);
    }
  }

  _toggleVoice() {
    if (this.speechState === 'COMMAND') {
      this._exitCommandMode('idle');
    } else {
      this._playConfirmChime();
      this._enterCommandMode('');
    }
  }

  _toggleContinuousWakeWord() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      this._appendMessage('JARVIS', 'Speech recognition not supported in this browser.');
      return;
    }

    this.isWakeWordActive = !this.isWakeWordActive;
    const btn = document.getElementById('btn-wakeword');

    if (this.isWakeWordActive) {
      if (btn) btn.classList.add('active');
      this._appendMessage('JARVIS', "Acoustic wake engine ENGAGED. Say 'Hey JARVIS' to speak.");
      this._startRecognition();
    } else {
      if (btn) btn.classList.remove('active');
      this._appendMessage('JARVIS', 'Acoustic wake engine paused.');
      this._stopRecognition();
    }
  }

  _stopRecognition() {
    if (this.recognition) {
      try {
        this.recognition.onend = null;
        this.recognition.onerror = null;
        this.recognition.abort();
      } catch (e) {}
      this.recognition = null;
    }
    this._exitCommandMode('idle');
  }

  _startRecognition() {
    if (!this.isWakeWordActive) return;
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) return;

    if (this.recognition) {
      try {
        this.recognition.onend = null;
        this.recognition.onerror = null;
        this.recognition.abort();
      } catch (e) {}
      this.recognition = null;
    }

    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    const rec = new SpeechRec();
    this.recognition = rec;
    rec.lang = 'en-US';
    rec.continuous = true;
    rec.interimResults = true;

    rec.onresult = (event) => {
      let interim = '';
      let finalStr = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const item = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalStr += item + ' ';
        } else {
          interim += item;
        }
      }

      const raw = (finalStr || interim).trim();
      if (!raw) return;

      if (this.speechState === 'WAKE') {
        const lower = raw.toLowerCase();
        if (lower.includes('jarvis')) {
          this._playWakeChime();

          // Check if user spoke a command in the same breath: "hey jarvis open chrome"
          let inlineCmd = raw.replace(/.*?\b(?:hey\s+|hi\s+|ok\s+)?jarvis\b[,:\s]*/i, '').trim();

          const lastResult = event.results[event.results.length - 1];
          if (inlineCmd.length > 1 && lastResult.isFinal) {
            // One-breath completed command
            this._setStatus('thinking');
            this._sendMessage(inlineCmd);
          } else if (inlineCmd.length > 1 && !lastResult.isFinal) {
            // One-breath interim in progress -> transition to command mode and show live text
            this._enterCommandMode(inlineCmd);
          } else {
            // User said "Hey JARVIS" and paused -> transition to command mode
            this._enterCommandMode('');
          }
        }
      } else if (this.speechState === 'COMMAND') {
        // Strip any repeated wake word calls
        let clean = raw.replace(/.*?\b(?:hey\s+|hi\s+|ok\s+)?jarvis\b[,:\s]*/i, '').trim();
        const display = clean || raw;

        const inputField = document.getElementById('chat-input');
        if (inputField && display) {
          inputField.value = display;
        }

        const lastResult = event.results[event.results.length - 1];
        if (lastResult.isFinal && display.length > 1) {
          this._executeCommandFromSpeech(display);
        }
      }
    };

    rec.onerror = (err) => {
      if (err.error !== 'no-speech' && err.error !== 'aborted') {
        console.warn('[HUD Speech] Notice:', err.error);
      }
    };

    rec.onend = () => {
      // Chromium speech engines automatically time out after ~60s of silence
      if (this.isWakeWordActive) {
        setTimeout(() => this._startRecognition(), 250);
      }
    };

    try {
      rec.start();
    } catch (e) {
      setTimeout(() => this._startRecognition(), 1000);
    }
  }

  _enterCommandMode(initialText = '') {
    this.speechState = 'COMMAND';
    this._setStatus('listening');
    this._toggleChat(true);

    const micBtn = document.getElementById('btn-mic');
    if (micBtn) micBtn.classList.add('listening');

    const inputField = document.getElementById('chat-input');
    if (inputField) {
      inputField.value = initialText;
      inputField.placeholder = "Listening for command, sir... speak now";
    }

    if (this.commandTimer) clearTimeout(this.commandTimer);
    // 8-second window to speak command
    this.commandTimer = setTimeout(() => {
      if (this.speechState === 'COMMAND') {
        const pending = inputField ? inputField.value.trim() : '';
        if (pending.length > 1) {
          this._executeCommandFromSpeech(pending);
        } else {
          this._exitCommandMode('idle');
        }
      }
    }, 8000);
  }

  _exitCommandMode(targetStatus = 'idle') {
    if (this.commandTimer) {
      clearTimeout(this.commandTimer);
      this.commandTimer = null;
    }
    this.speechState = 'WAKE';

    const micBtn = document.getElementById('btn-mic');
    if (micBtn) micBtn.classList.remove('listening');

    const inputField = document.getElementById('chat-input');
    if (inputField) {
      inputField.value = '';
      inputField.placeholder = "Type an autonomous instruction or speak...";
    }

    this._setStatus(targetStatus);
  }

  _executeCommandFromSpeech(cmd) {
    this._exitCommandMode('thinking');
    this._sendMessage(cmd);
  }

  _playWakeChime() {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(587.33, ctx.currentTime); // D5
      osc.frequency.exponentialRampToValueAtTime(880.0, ctx.currentTime + 0.15); // A5
      gain.gain.setValueAtTime(0.2, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.25);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.25);
    } catch (e) {}
  }

  _playConfirmChime() {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(1046.5, ctx.currentTime); // C6
      gain.gain.setValueAtTime(0.18, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.12);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.12);
    } catch (e) {}
  }

  async _triggerEstop() {
    this.isEstopTripped = !this.isEstopTripped;
    const btn = document.getElementById('btn-estop');

    if (this.isEstopTripped) {
      btn.classList.add('tripped');
      this._setStatus('emergency_stopped');
      this._toggleChat(true);
      this._appendMessage('JARVIS', 'EMERGENCY STOP ENGAGED. All autonomous dispatches halted.');
      await fetch('/api/estop', { method: 'POST', body: JSON.stringify({ trip: true }) }).catch(() => {});
    } else {
      btn.classList.remove('tripped');
      this._setStatus('idle');
      this._appendMessage('JARVIS', 'Safety latch reset. Automation re-enabled.');
      await fetch('/api/estop', { method: 'POST', body: JSON.stringify({ trip: false }) }).catch(() => {});
    }
  }

  async _toggleShutter() {
    this.isBlinded = !this.isBlinded;
    if (this.isBlinded) {
      this._setStatus('blinded');
      this._appendMessage('JARVIS', 'Privacy Shutter closed. Screen perception air-gapped.');
    } else {
      this._setStatus('idle');
      this._appendMessage('JARVIS', 'Privacy Shutter opened. Screen perception active.');
    }
    await fetch('/api/shutter', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ blind: this.isBlinded })
    }).catch(() => {});
  }

  _startUptimeClock() {
    setInterval(() => {
      this.uptimeSeconds++;
      const hrs = String(Math.floor(this.uptimeSeconds / 3600)).padStart(2, '0');
      const mins = String(Math.floor((this.uptimeSeconds % 3600) / 60)).padStart(2, '0');
      const secs = String(this.uptimeSeconds % 60).padStart(2, '0');
      document.getElementById('uptime-ticker').textContent = `${hrs}:${mins}:${secs}`;
    }, 1000);
  }

  _startPolling() {
    const poll = async () => {
      try {
        const statusRes = await fetch('/api/status');
        if (statusRes.ok) {
          const s = await statusRes.json();
          document.getElementById('event-depth').textContent = s.event_count || 0;
          if (s.node_id) document.getElementById('node-id').textContent = s.node_id;

          // Update live hardware telemetry gauges
          if (s.cpu_percent !== undefined) {
            const cpuEl = document.getElementById('cpu-stat');
            const cpuBar = document.getElementById('cpu-bar');
            if (cpuEl) cpuEl.textContent = `${s.cpu_percent}%`;
            if (cpuBar) cpuBar.style.width = `${Math.min(100, Math.max(2, s.cpu_percent))}%`;
          }
          if (s.ram_percent !== undefined) {
            const ramEl = document.getElementById('ram-stat');
            const ramBar = document.getElementById('ram-bar');
            if (ramEl) ramEl.textContent = `${s.ram_percent}%`;
            if (ramBar) ramBar.style.width = `${Math.min(100, Math.max(2, s.ram_percent))}%`;
          }

          // External wake trigger (e.g. from Alt+J hotkey hitting /api/wake)
          if (s.companion_status === 'listening' && this.currentStatus !== 'listening') {
            this._playWakeChime();
            this._toggleVoice();
          }
        }

        const eventRes = await fetch('/api/events?limit=20');
        if (eventRes.ok) {
          const events = await eventRes.json();
          this._renderEvents(events);
        }
      } catch (err) { /* server offline */ }
      setTimeout(poll, 2000);
    };
    poll();
  }

  _renderEvents(events) {
    const container = document.getElementById('event-stream');
    const counter = document.getElementById('stream-count');
    counter.textContent = events.length;

    for (const ev of events) {
      if (this.knownEventIds.has(ev.event_id)) continue;
      this.knownEventIds.add(ev.event_id);

      const row = document.createElement('div');
      const sid = (ev.stream_id || 'general').replace(/[^a-z0-9]/gi, '');
      row.className = `event-row stream-${sid}`;
      row.innerHTML = `
        <div class="event-type">${ev.event_type}</div>
        <div class="event-meta">
          <span>[${ev.stream_id || 'kernel'}]</span>
          <span>${(ev.event_id || '').slice(0, 8)}</span>
        </div>
      `;

      if (container.firstChild) {
        container.insertBefore(row, container.firstChild);
      } else {
        container.appendChild(row);
      }
    }
  }

  _playBootChime() {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();

      // Two-tone ascending chime
      const notes = [523.25, 659.25, 783.99]; // C5, E5, G5
      notes.forEach((freq, i) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(freq, ctx.currentTime + i * 0.12);
        gain.gain.setValueAtTime(0.12, ctx.currentTime + i * 0.12);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + i * 0.12 + 0.5);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(ctx.currentTime + i * 0.12);
        osc.stop(ctx.currentTime + i * 0.12 + 0.5);
      });
    } catch (e) {}
  }

  _makeDraggable(elementId) {
    const el = document.getElementById(elementId);
    if (!el) return;

    let isDragging = false;
    let startX = 0, startY = 0, origX = 0, origY = 0;

    el.addEventListener('mousedown', (e) => {
      if (e.target.closest('button')) return;
      isDragging = true;
      startX = e.clientX;
      startY = e.clientY;
      const rect = el.getBoundingClientRect();
      origX = rect.left;
      origY = rect.top;
      el.style.bottom = 'auto';
      el.style.right = 'auto';
      el.style.left = `${origX}px`;
      el.style.top = `${origY}px`;
      el.classList.add('dragging');
    });

    window.addEventListener('mousemove', (e) => {
      if (!isDragging) return;
      const dx = e.clientX - startX;
      const dy = e.clientY - startY;
      el.style.left = `${origX + dx}px`;
      el.style.top = `${origY + dy}px`;
    });

    window.addEventListener('mouseup', () => {
      if (isDragging) {
        isDragging = false;
        el.classList.remove('dragging');
      }
    });
  }

  _escapeHTML(str) {
    return str.replace(/[&<>'"]/g,
      tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
    );
  }
}


// ==========================================================================
//  BOOT
// ==========================================================================

window.addEventListener('DOMContentLoaded', () => {
  window.jarvisHUD = new HUDOverlayController();
});
