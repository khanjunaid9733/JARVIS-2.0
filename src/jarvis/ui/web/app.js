/**
 * JARVIS 2.0 — Spatial Cognitive Interface Engine
 * Holographic Arc Core Canvas Renderer & Event Telemetry Controller
 */

class JarvisCoreRenderer {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext('2d');
    this.status = 'idle'; // idle, listening, thinking, acting, emergency_stopped, blinded
    this.audioLevel = 0.0;
    this.angle = 0;
    this.particles = [];
    this.initParticles();
    this.resize();
    window.addEventListener('resize', () => this.resize());
    this.render();
  }

  resize() {
    const rect = this.canvas.parentElement.getBoundingClientRect();
    this.canvas.width = rect.width * window.devicePixelRatio;
    this.canvas.height = rect.height * window.devicePixelRatio;
    this.ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    this.width = rect.width;
    this.height = rect.height;
  }

  initParticles() {
    this.particles = [];
    for (let i = 0; i < 70; i++) {
      this.particles.push({
        x: (Math.random() - 0.5) * 300,
        y: (Math.random() - 0.5) * 300,
        z: Math.random() * 200,
        radius: Math.random() * 2 + 1,
        speed: (Math.random() * 0.02) + 0.005,
        theta: Math.random() * Math.PI * 2
      });
    }
  }

  setStatus(status) {
    this.status = status;
  }

  getStatusColors() {
    switch (this.status) {
      case 'listening':
        return { primary: '#00ff88', glow: 'rgba(0, 255, 136, 0.4)', core: '#80ffc4' };
      case 'thinking':
        return { primary: '#ffb700', glow: 'rgba(255, 183, 0, 0.4)', core: '#ffe280' };
      case 'acting':
        return { primary: '#00e5ff', glow: 'rgba(0, 229, 255, 0.6)', core: '#ffffff' };
      case 'emergency_stopped':
        return { primary: '#ff0055', glow: 'rgba(255, 0, 85, 0.6)', core: '#ff80aa' };
      case 'blinded':
        return { primary: '#778899', glow: 'rgba(119, 136, 153, 0.3)', core: '#b0c4de' };
      case 'idle':
      default:
        return { primary: '#00e5ff', glow: 'rgba(0, 229, 255, 0.3)', core: '#80f2ff' };
    }
  }

  render() {
    const ctx = this.ctx;
    const w = this.width;
    const h = this.height;
    const cx = w / 2;
    const cy = h / 2;

    ctx.clearRect(0, 0, w, h);

    const colors = this.getStatusColors();
    const speedMultiplier = this.status === 'thinking' ? 2.5 : this.status === 'acting' ? 3.0 : 1.0;
    this.angle += 0.015 * speedMultiplier;

    // 1. Draw 3D Particle Orbit Cloud
    ctx.save();
    ctx.translate(cx, cy);
    for (const p of this.particles) {
      p.theta += p.speed * speedMultiplier;
      const radius = 110 + Math.sin(p.theta * 2) * 20;
      const px = Math.cos(p.theta) * radius;
      const py = Math.sin(p.theta) * radius * 0.45; // ellipse perspective

      ctx.beginPath();
      ctx.arc(px, py, p.radius, 0, Math.PI * 2);
      ctx.fillStyle = colors.primary;
      ctx.shadowColor = colors.primary;
      ctx.shadowBlur = 6;
      ctx.globalAlpha = 0.5 + Math.sin(p.theta) * 0.4;
      ctx.fill();
    }
    ctx.restore();

    // 2. Outer Rotating Segmented Ring
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(this.angle * 0.4);
    ctx.strokeStyle = colors.primary;
    ctx.lineWidth = 2;
    ctx.shadowColor = colors.glow;
    ctx.shadowBlur = 14;

    const segments = 12;
    const rOuter = 135;
    for (let i = 0; i < segments; i++) {
      const start = (i * Math.PI * 2) / segments;
      const end = start + (Math.PI / segments) * 0.65;
      ctx.beginPath();
      ctx.arc(0, 0, rOuter, start, end);
      ctx.stroke();
    }
    ctx.restore();

    // 3. Counter-Rotating Interlocked Gear Ring
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(-this.angle * 0.7);
    ctx.strokeStyle = colors.glow;
    ctx.lineWidth = 1.5;

    const rMid = 105;
    const ticks = 36;
    for (let i = 0; i < ticks; i++) {
      const a = (i * Math.PI * 2) / ticks;
      const len = i % 3 === 0 ? 8 : 4;
      const x1 = Math.cos(a) * (rMid - len);
      const y1 = Math.sin(a) * (rMid - len);
      const x2 = Math.cos(a) * rMid;
      const y2 = Math.sin(a) * rMid;
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();
    }
    ctx.restore();

    // 4. Inner Waveform Reactor Circle
    ctx.save();
    ctx.translate(cx, cy);
    ctx.beginPath();
    const rInner = 68;
    const wavePoints = 48;
    for (let i = 0; i <= wavePoints; i++) {
      const a = (i * Math.PI * 2) / wavePoints;
      const wave = Math.sin(a * 6 + this.angle * 4) * (this.status === 'listening' ? 8 : 3);
      const r = rInner + wave;
      const x = Math.cos(a) * r;
      const y = Math.sin(a) * r;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.strokeStyle = colors.primary;
    ctx.lineWidth = 2.5;
    ctx.shadowColor = colors.primary;
    ctx.shadowBlur = 18;
    ctx.stroke();

    // 5. Central Pulsing Arc Core
    const pulse = Math.sin(this.angle * 3) * 6;
    const coreGrad = ctx.createRadialGradient(0, 0, 5, 0, 0, 45 + pulse);
    coreGrad.addColorStop(0, colors.core);
    coreGrad.addColorStop(0.4, colors.primary);
    coreGrad.addColorStop(1, 'transparent');

    ctx.beginPath();
    ctx.arc(0, 0, 45 + pulse, 0, Math.PI * 2);
    ctx.fillStyle = coreGrad;
    ctx.globalAlpha = 0.85;
    ctx.fill();

    // Central geometric aperture
    ctx.rotate(this.angle);
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(0, 0, 16, 0, Math.PI * 2);
    ctx.stroke();
    ctx.restore();

    requestAnimationFrame(() => this.render());
  }
}

// ---------------------------------------------------------------------------
// Telemetry & Backend Interface Controller
// ---------------------------------------------------------------------------

class JarvisUIController {
  constructor() {
    this.coreRenderer = new JarvisCoreRenderer('jarvis-core-canvas');
    this.knownEventIds = new Set();
    this.uptimeSeconds = 0;
    this.isBlinded = false;
    this.isEstopTripped = false;
    this.isWakeWordActive = false;
    this.wakeRecognition = null;

    this.bindDOM();
    this.startPolling();
    this.startUptimeClock();
  }

  bindDOM() {
    // Mode Buttons
    document.querySelectorAll('.mode-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const status = e.currentTarget.dataset.status;
        this.setCompanionStatus(status);
      });
    });

    // Chat Form
    const form = document.getElementById('chat-form');
    const input = document.getElementById('chat-input');
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const val = input.value.trim();
      if (!val) return;
      this.sendUserMessage(val);
      input.value = '';
    });

    // Voice Mic Button
    const micBtn = document.getElementById('btn-mic');
    micBtn.addEventListener('click', () => this.toggleVoiceRecognition());

    // Wake-Word Button (Option 2)
    const wakeBtn = document.getElementById('btn-wakeword');
    if (wakeBtn) {
      wakeBtn.addEventListener('click', () => this.toggleContinuousWakeWord());
    }

    // E-Stop Button
    const estopBtn = document.getElementById('btn-estop');
    estopBtn.addEventListener('click', () => this.triggerEstop());

    // Shutter Button
    const shutterBtn = document.getElementById('btn-shutter');
    shutterBtn.addEventListener('click', () => this.toggleShutter());

    // Quick Skill Tiles
    document.querySelectorAll('.skill-tile').forEach(tile => {
      tile.addEventListener('click', () => {
        const goal = tile.dataset.goal;
        this.sendUserMessage(`Run skill: ${goal}`);
      });
    });

    // Clear Stream & Replay
    document.getElementById('btn-clear-stream').addEventListener('click', () => {
      document.getElementById('event-stream').innerHTML = '<div class="stream-empty-hint">Stream cleared.</div>';
      this.knownEventIds.clear();
    });

    document.getElementById('btn-replay-verify').addEventListener('click', async () => {
      this.appendChatMessage('System', 'Verifying cryptographic hash chain across all log events...');
      try {
        const res = await fetch('/api/verify');
        const data = await res.json();
        if (data.ok) {
          this.appendChatMessage('JARVIS 2.0', `Hash chain verification SUCCESSFUL. Total events: ${data.event_count}, digest: ${data.digest}`);
        } else {
          this.appendChatMessage('JARVIS 2.0', `Verification FAILED: ${data.error}`);
        }
      } catch (err) {
        this.appendChatMessage('JARVIS 2.0', `Error verifying log chain: ${err.message}`);
      }
    });
  }

  setCompanionStatus(status) {
    document.querySelectorAll('.mode-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.status === status);
    });

    this.coreRenderer.setStatus(status);

    const pill = document.getElementById('companion-status-pill');
    pill.className = `card-value status-pill status-${status}`;
    pill.textContent = status.toUpperCase();

    const title = document.getElementById('core-state-title');
    const sub = document.getElementById('core-state-sub');

    switch (status) {
      case 'listening':
        title.textContent = 'LISTENING';
        title.style.color = '#00ff88';
        sub.textContent = 'AUDIO SENSORS ACTIVE & BUFFERING';
        break;
      case 'thinking':
        title.textContent = 'NEURAL COMPUTATION';
        title.style.color = '#ffb700';
        sub.textContent = 'DECOMPOSING INTENT VIA HTN PLANNER';
        break;
      case 'acting':
        title.textContent = 'DISPATCHING EFFECT';
        title.style.color = '#00e5ff';
        sub.textContent = 'EXECUTING WORKFLOW UNDER CONTAINMENT';
        break;
      case 'emergency_stopped':
        title.textContent = 'EMERGENCY HALT';
        title.style.color = '#ff0055';
        sub.textContent = 'ALL AUTOMATION LOCKED BY SAFETY LATCH';
        break;
      case 'blinded':
        title.textContent = 'PRIVACY SHUTTER ENGAGED';
        title.style.color = '#778899';
        sub.textContent = 'SCREEN PERCEPTION AIR-GAPPED & BLINDED';
        break;
      default:
        title.textContent = 'SYSTEM ONLINE';
        title.style.color = '#00e5ff';
        sub.textContent = 'AWAITING CREATOR INSTRUCTIONS';
    }

    // Inform backend of state change
    fetch('/api/status', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status })
    }).catch(() => {});
  }

  async sendUserMessage(text) {
    this.appendChatMessage('You', text, true);
    this.setCompanionStatus('thinking');

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
      this.setCompanionStatus('acting');

      if (data.reply) {
        this.appendChatMessage('JARVIS 2.0', data.reply);
        this.speakUtterance(data.reply);
      } else if (data.message) {
        this.appendChatMessage('JARVIS 2.0', `[${data.status || 'STATUS'}] ${data.message}`);
      }

      if (data.url && (data.action === 'media_playback' || data.action === 'web_search' || data.action === 'open_url')) {
        try {
          window.open(data.url, '_blank');
        } catch (e) {}
      }

      setTimeout(() => this.setCompanionStatus('idle'), 1500);
    } catch (err) {
      this.setCompanionStatus('idle');
      this.appendChatMessage('JARVIS 2.0', `Communication fault: ${err.message}`);
    }
  }

  appendChatMessage(sender, text, isUser = false) {
    const history = document.getElementById('chat-history');
    const msg = document.createElement('div');
    msg.className = `chat-msg ${isUser ? 'user-msg' : 'jarvis-msg'}`;
    msg.innerHTML = `
      <div class="msg-avatar">${isUser ? 'U' : 'J'}</div>
      <div class="msg-body">
        <div class="msg-header">${sender} <span class="msg-time">${new Date().toLocaleTimeString()}</span></div>
        <div class="msg-text">${this.escapeHTML(text)}</div>
      </div>
    `;
    history.appendChild(msg);
    history.scrollTop = history.scrollHeight;
  }

  speakUtterance(text) {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utter = new SpeechSynthesisUtterance(text);
      utter.rate = 1.05;
      utter.pitch = 0.95;
      window.speechSynthesis.speak(utter);
    }
  }

  toggleVoiceRecognition() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      alert('Speech recognition is not supported in this browser. Please type your command.');
      return;
    }
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRec();
    recognition.lang = 'en-US';
    recognition.interimResults = false;

    this.setCompanionStatus('listening');
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      document.getElementById('chat-input').value = transcript;
      this.sendUserMessage(transcript);
    };
    recognition.onerror = () => this.setCompanionStatus('idle');
    recognition.onend = () => {
      if (this.coreRenderer.status === 'listening') {
        this.setCompanionStatus('idle');
      }
    };
    recognition.start();
  }

  toggleContinuousWakeWord() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      alert('Speech recognition is not supported in this browser.');
      return;
    }

    this.isWakeWordActive = !this.isWakeWordActive;
    const btn = document.getElementById('btn-wakeword');
    const label = document.getElementById('wakeword-label');

    if (this.isWakeWordActive) {
      if (btn) btn.classList.add('active');
      if (label) label.textContent = 'VOICE WAKE: ON';
      this.appendChatMessage('JARVIS 2.0', "Acoustic wake-word engine ENGAGED. Say 'Hey JARVIS' or 'JARVIS' to activate.");
      this.startWakeWordLoop();
    } else {
      if (btn) btn.classList.remove('active');
      if (label) label.textContent = 'VOICE WAKE: OFF';
      this.appendChatMessage('JARVIS 2.0', 'Acoustic wake-word engine disengaged.');
      if (this.wakeRecognition) {
        try { this.wakeRecognition.abort(); } catch (e) {}
        this.wakeRecognition = null;
      }
    }
  }

  startWakeWordLoop() {
    if (!this.isWakeWordActive) return;

    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    this.wakeRecognition = new SpeechRec();
    this.wakeRecognition.lang = 'en-US';
    this.wakeRecognition.continuous = true;
    this.wakeRecognition.interimResults = false;

    this.wakeRecognition.onresult = (event) => {
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript.trim().toLowerCase();
        if (transcript.includes('jarvis')) {
          let cmd = transcript.replace(/.*?\b(hey\s+)?jarvis\b[,:\s]*/i, '').trim();
          this.setCompanionStatus('listening');
          this.playWakeChime();

          if (cmd) {
            document.getElementById('chat-input').value = cmd;
            this.sendUserMessage(cmd);
          } else {
            this.speakUtterance('Yes, sir?');
            setTimeout(() => {
              this.toggleVoiceRecognition();
            }, 700);
          }
        }
      }
    };

    this.wakeRecognition.onerror = () => {};

    this.wakeRecognition.onend = () => {
      if (this.isWakeWordActive) {
        setTimeout(() => this.startWakeWordLoop(), 300);
      }
    };

    try {
      this.wakeRecognition.start();
    } catch (e) {}
  }

  playWakeChime() {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(587.33, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(880.0, ctx.currentTime + 0.15);
      gain.gain.setValueAtTime(0.2, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.25);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.25);
    } catch (e) {}
  }

  async triggerEstop() {
    this.isEstopTripped = !this.isEstopTripped;
    const estopLabel = document.getElementById('estop-status');

    if (this.isEstopTripped) {
      this.setCompanionStatus('emergency_stopped');
      estopLabel.textContent = 'TRIPPED (HALT)';
      estopLabel.className = 'card-value text-red font-bold';
      this.appendChatMessage('JARVIS 2.0', 'EMERGENCY STOP ENGAGED. All autonomous dispatches and computer-use pipelines are halted.');
      await fetch('/api/estop', { method: 'POST', body: JSON.stringify({ trip: true }) }).catch(() => {});
    } else {
      this.setCompanionStatus('idle');
      estopLabel.textContent = 'ENGAGED (SAFE)';
      estopLabel.className = 'card-value text-green font-bold';
      this.appendChatMessage('JARVIS 2.0', 'Safety latch reset. Automation re-enabled.');
      await fetch('/api/estop', { method: 'POST', body: JSON.stringify({ trip: false }) }).catch(() => {});
    }
  }

  async toggleShutter() {
    this.isBlinded = !this.isBlinded;
    const shutterLabel = document.getElementById('shutter-label');
    const shutterState = document.getElementById('shutter-state');

    if (this.isBlinded) {
      this.setCompanionStatus('blinded');
      shutterLabel.textContent = 'SHUTTER: CLOSED';
      shutterState.textContent = 'BLINDED';
      shutterState.className = 'card-value text-amber font-bold';
      this.appendChatMessage('JARVIS 2.0', 'Privacy Shutter closed. Screen perception air-gap engaged.');
    } else {
      this.setCompanionStatus('idle');
      shutterLabel.textContent = 'SHUTTER: OPEN';
      shutterState.textContent = 'ACTIVE';
      shutterState.className = 'card-value text-cyan font-bold';
      this.appendChatMessage('JARVIS 2.0', 'Privacy Shutter opened. Screen perception active.');
    }

    await fetch('/api/shutter', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ blind: this.isBlinded })
    }).catch(() => {});
  }

  startUptimeClock() {
    setInterval(() => {
      this.uptimeSeconds++;
      const hrs = String(Math.floor(this.uptimeSeconds / 3600)).padStart(2, '0');
      const mins = String(Math.floor((this.uptimeSeconds % 3600) / 60)).padStart(2, '0');
      const secs = String(this.uptimeSeconds % 60).padStart(2, '0');
      document.getElementById('uptime-ticker').textContent = `${hrs}:${mins}:${secs}`;
    }, 1000);
  }

  startPolling() {
    const poll = async () => {
      try {
        // Poll status
        const statusRes = await fetch('/api/status');
        if (statusRes.ok) {
          const s = await statusRes.json();
          document.getElementById('event-depth').textContent = `${s.event_count || 0} EVENTS`;
          document.getElementById('node-id').textContent = s.node_id || 'WORKSTATION_PRIMARY';
          if (s.creator_fp) {
            document.getElementById('creator-fp').textContent = s.creator_fp;
          }
        }

        // Poll events
        const eventRes = await fetch('/api/events?limit=25');
        if (eventRes.ok) {
          const events = await eventRes.json();
          this.renderEvents(events);
        }
      } catch (err) {
        // server temporarily offline or booting
      }
      setTimeout(poll, 1500);
    };
    poll();
  }

  renderEvents(events) {
    const container = document.getElementById('event-stream');
    const counter = document.getElementById('stream-count');
    counter.textContent = events.length;

    let hasNew = false;
    for (const ev of events) {
      if (!this.knownEventIds.has(ev.event_id)) {
        hasNew = true;
        this.knownEventIds.add(ev.event_id);

        const row = document.createElement('div');
        const streamClass = `stream-${(ev.stream_id || 'general').replace(/[^a-z0-9]/gi, '')}`;
        row.className = `event-row ${streamClass}`;
        row.innerHTML = `
          <div class="event-meta">
            <span class="event-stream-tag">[${ev.stream_id || 'kernel'}]</span>
            <span class="event-ulid font-mono">${(ev.event_id || '').slice(0, 10)}</span>
          </div>
          <div class="event-type">${ev.event_type}</div>
          <div class="event-payload-preview font-mono">${JSON.stringify(ev.payload || {})}</div>
        `;
        // Insert at top of stream
        if (container.firstChild) {
          container.insertBefore(row, container.firstChild);
        } else {
          container.appendChild(row);
        }
      }
    }

    // Remove empty hint if events arrived
    const hint = container.querySelector('.stream-empty-hint');
    if (hint && this.knownEventIds.size > 0) {
      hint.remove();
    }
  }

  escapeHTML(str) {
    return str.replace(/[&<>'"]/g, 
      tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
    );
  }
}

// Boot UI
window.addEventListener('DOMContentLoaded', () => {
  window.jarvisUI = new JarvisUIController();
});
