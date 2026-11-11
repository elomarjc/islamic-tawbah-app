/**
 * frontend/js/app.js
 * Main SPA Controller for Tawbah Guiden (Islamisk Opgørelse & Anger App)
 */

import { ApiClient } from './api.js';
import { VoiceConfessionRecorder } from './audio_recorder.js';
import {
  escapeHtml,
  showToast,
  renderClassificationBadge,
  renderAssessmentResult,
} from './ui.js';

const DRAFT_STORAGE_KEY = 'tawbah_confession_draft';

export const CANONICAL_DEMO_SCENARIOS = [
  {
    id: 'combined_prompt',
    label: 'Eksempel (Mor + Far 25 kr.)',
    text: 'Jeg talte respektløst til min mor i dag og gjorde grin med hendes vægt. Senere stjal jeg 25 kroner fra min far.',
  },
  {
    id: 'scen_1_mother',
    label: '1. Fornærmelse af mor',
    text: 'Jeg blev sur på min mor i morges, hævede stemmen ad hende og sagde sårende ord til hende.',
  },
  {
    id: 'scen_2_father',
    label: '2. Stjæle penge fra far',
    text: 'Jeg tog 500 kroner fra min fars pung uden hans viden eller tilladelse.',
  },
  {
    id: 'scen_3_backbiting',
    label: '3. Bagtalelse af ven/kollega',
    text: 'Jeg bagtalte min ven og kollega i frokostpausen, mens han ikke var til stede, og han ved det ikke.',
  },
  {
    id: 'scen_4_fajr',
    label: '4. Manglende Fajr-bøn',
    text: 'Jeg slukkede bevidst vækkeuret i morges og sov videre uden at bede den obligatoriske Fajr-bøn.',
  },
  {
    id: 'scen_5_spouse',
    label: '5. Løgn over for ægtefælle',
    text: 'Jeg løj over for min ægtefælle om, hvor jeg havde været, og hvad jeg havde brugt vores penge på.',
  },
  {
    id: 'scen_6_property',
    label: '6. Skade på nabos ejendom',
    text: 'Jeg kom til at beskadige min nabos cykel og hegn i går, men gik derfra uden at sige noget.',
  },
  {
    id: 'scen_7_restitution',
    label: '7. Tilbagelevering af penge',
    text: 'Jeg tog 200 kroner fra en kollegas skrivebord uden tilladelse og ønsker nu at levere dem tilbage uden skandale.',
  },
  {
    id: 'scen_8_private',
    label: '8. Privat synd (Al-Sitr)',
    text: 'Jeg begik en privat synd alene om natten mellem mig og Allah, som ingen andre mennesker kender til.',
  },
  {
    id: 'scen_9_slander',
    label: '9. Falsk anklage (Buhtan)',
    text: 'Jeg spredte en falsk anklage om en bekendt i vores fælles gruppe og beskyldte ham for noget, han ikke har gjort.',
  },
  {
    id: 'scen_10_trust',
    label: '10. Brud på tillid (Underslæb)',
    text: 'Som kasserer i foreningen brugte jeg 5.000 kroner af de betroede midler til mine egne private udgifter.',
  },
];

class TawbahApp {
  constructor() {
    this.currentPage = 'hjem';
    this.intakeMode = 'voice'; // 'voice' | 'text'
    this.currentAnalysis = null;
    this.actionFilter = 'all'; // 'all' | 'pending' | 'completed'
    this.knowledgeCategory = 'all';

    this.recorder = new VoiceConfessionRecorder({
      onStateChange: (state, payload) => this.handleRecorderState(state, payload),
      onTranscriptUpdate: (text) => {
        const transcriptInput = document.getElementById('voice-transcript-preview');
        if (transcriptInput) transcriptInput.value = text;
      },
      onTimerTick: (formatted) => {
        const timerEl = document.getElementById('recorder-timer');
        if (timerEl) timerEl.textContent = formatted;
      },
      onLevelsUpdate: (levels) => this.updateWaveformBars(levels),
    });
  }

  async init() {
    this.setupNavigation();
    this.setupScenarioChips();
    this.setupIntakeControls();
    this.setupHistoryAndJournalControls();
    this.setupKnowledgeControls();
    this.setupSettingsAndAuthControls();

    // Restore saved text draft if any
    const savedDraft = sessionStorage.getItem(DRAFT_STORAGE_KEY);
    const textarea = document.getElementById('confession-text-input');
    if (savedDraft && textarea) {
      textarea.value = savedDraft;
      this.updateCharCounter();
    }

    this.updateAuthUI();
    await this.refreshHomeAndBadges();
  }

  setupNavigation() {
    document.querySelectorAll('[data-nav-target]').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        const target = btn.getAttribute('data-nav-target');
        const mode = btn.getAttribute('data-intake-mode');
        this.navigateTo(target, mode);
      });
    });
  }

  async navigateTo(pageId, preferredIntakeMode = null) {
    this.currentPage = pageId;

    document.querySelectorAll('.page-view').forEach((sec) => {
      sec.classList.toggle('active', sec.id === `page-${pageId}`);
    });

    document.querySelectorAll('[data-nav-target]').forEach((btn) => {
      const target = btn.getAttribute('data-nav-target');
      btn.classList.toggle('active', target === pageId);
    });

    if (pageId === 'ny-bekendelse' && preferredIntakeMode) {
      this.switchIntakeMode(preferredIntakeMode);
    }

    window.scrollTo({ top: 0, behavior: 'smooth' });

    if (pageId === 'hjem') {
      await this.refreshHomeAndBadges();
    } else if (pageId === 'handlinger') {
      await this.loadActionsPage();
    } else if (pageId === 'historik') {
      await this.loadHistoryAndJournalPage();
    } else if (pageId === 'viden') {
      await this.loadKnowledgePage();
    } else if (pageId === 'indstillinger') {
      this.updateAuthUI();
    }
  }

  switchIntakeMode(mode) {
    this.intakeMode = mode === 'text' ? 'text' : 'voice';
    const tabVoice = document.getElementById('tab-mode-voice');
    const tabText = document.getElementById('tab-mode-text');
    const panelVoice = document.getElementById('panel-intake-voice');
    const panelText = document.getElementById('panel-intake-text');

    if (tabVoice) tabVoice.classList.toggle('active', this.intakeMode === 'voice');
    if (tabText) tabText.classList.toggle('active', this.intakeMode === 'text');
    if (panelVoice) panelVoice.style.display = this.intakeMode === 'voice' ? 'block' : 'none';
    if (panelText) panelText.style.display = this.intakeMode === 'text' ? 'block' : 'none';
  }

  setupScenarioChips() {
    const homeChips = document.getElementById('home-scenario-chips');
    const intakeChips = document.getElementById('intake-scenario-chips');

    const renderChips = (container, autoNavigate) => {
      if (!container) return;
      container.innerHTML = CANONICAL_DEMO_SCENARIOS.map(
        (s) =>
          `<button type="button" class="scenario-chip" data-scenario-id="${escapeHtml(s.id)}">${escapeHtml(s.label)}</button>`
      ).join('');

      container.querySelectorAll('.scenario-chip').forEach((btn) => {
        btn.addEventListener('click', () => {
          const sid = btn.getAttribute('data-scenario-id');
          const found = CANONICAL_DEMO_SCENARIOS.find((x) => x.id === sid);
          if (!found) return;

          const textarea = document.getElementById('confession-text-input');
          const voicePreview = document.getElementById('voice-transcript-preview');
          if (textarea) {
            textarea.value = found.text;
            sessionStorage.setItem(DRAFT_STORAGE_KEY, found.text);
            this.updateCharCounter();
          }
          if (voicePreview) {
            voicePreview.value = found.text;
            this.recorder.liveTranscript = found.text;
          }

          if (autoNavigate) {
            this.navigateTo('ny-bekendelse', 'text');
          } else {
            this.switchIntakeMode('text');
          }
          showToast(`Indsat eksempel: ${found.label}`);
        });
      });
    };

    renderChips(homeChips, true);
    renderChips(intakeChips, false);
  }

  setupIntakeControls() {
    const tabVoice = document.getElementById('tab-mode-voice');
    const tabText = document.getElementById('tab-mode-text');
    if (tabVoice) tabVoice.addEventListener('click', () => this.switchIntakeMode('voice'));
    if (tabText) tabText.addEventListener('click', () => this.switchIntakeMode('text'));

    // Build waveform bars
    const waveContainer = document.getElementById('waveform-bars');
    if (waveContainer) {
      waveContainer.innerHTML = Array.from({ length: 24 }, () => `<div class="wave-bar"></div>`).join('');
    }

    // Microphone buttons
    const btnStartRec = document.getElementById('btn-mic-toggle');
    const btnPauseRec = document.getElementById('btn-rec-pause');
    const btnStopRec = document.getElementById('btn-rec-stop');
    const btnDeleteRec = document.getElementById('btn-rec-delete');

    if (btnStartRec) {
      btnStartRec.addEventListener('click', () => {
        if (this.recorder.state === 'IDLE' || this.recorder.state === 'REVIEW') {
          this.recorder.startRecording();
        } else if (this.recorder.state === 'RECORDING' || this.recorder.state === 'PAUSED') {
          this.recorder.stopRecording();
        }
      });
    }

    if (btnPauseRec) {
      btnPauseRec.addEventListener('click', () => {
        if (this.recorder.state === 'RECORDING') {
          this.recorder.pauseRecording();
        } else if (this.recorder.state === 'PAUSED') {
          this.recorder.resumeRecording();
        }
      });
    }

    if (btnStopRec) {
      btnStopRec.addEventListener('click', () => this.recorder.stopRecording());
    }

    if (btnDeleteRec) {
      btnDeleteRec.addEventListener('click', () => {
        this.recorder.clearRecording();
        const tp = document.getElementById('voice-transcript-preview');
        if (tp) tp.value = '';
        showToast('Optagelse slettet fra hukommelsen.');
      });
    }

    // Textarea counter & draft save
    const textarea = document.getElementById('confession-text-input');
    if (textarea) {
      textarea.addEventListener('input', () => {
        sessionStorage.setItem(DRAFT_STORAGE_KEY, textarea.value);
        this.updateCharCounter();
      });
    }

    // Privacy explanation toggle
    const btnPrivacy = document.getElementById('btn-toggle-privacy-info');
    const privacyDrawer = document.getElementById('privacy-explanation-drawer');
    if (btnPrivacy && privacyDrawer) {
      btnPrivacy.addEventListener('click', () => {
        const isHidden = privacyDrawer.style.display === 'none';
        privacyDrawer.style.display = isHidden ? 'block' : 'none';
      });
    }

    // Submit Confession Button
    const btnSubmit = document.getElementById('btn-submit-confession');
    if (btnSubmit) {
      btnSubmit.addEventListener('click', () => this.handleConfessionSubmit());
    }
  }

  updateCharCounter() {
    const textarea = document.getElementById('confession-text-input');
    const counter = document.getElementById('text-char-counter');
    if (textarea && counter) {
      const len = textarea.value.length;
      counter.textContent = `${len} / 10.000 tegn`;
    }
  }

  updateWaveformBars(levels) {
    const bars = document.querySelectorAll('#waveform-bars .wave-bar');
    bars.forEach((bar, i) => {
      const pct = levels[i] || 10;
      bar.style.height = `${Math.max(6, Math.round((pct / 100) * 36))}px`;
    });
  }

  handleRecorderState(state, payload = {}) {
    const micBtn = document.getElementById('btn-mic-toggle');
    const statusLabel = document.getElementById('recorder-status-text');
    const activeControls = document.getElementById('recorder-active-controls');
    const reviewPanel = document.getElementById('recorder-review-panel');
    const pauseBtn = document.getElementById('btn-rec-pause');
    const audioPlayer = document.getElementById('recorded-audio-player');

    if (state === 'IDLE') {
      if (micBtn) {
        micBtn.classList.remove('recording');
        micBtn.innerHTML = '🎙️';
        micBtn.title = 'Start optagelse';
      }
      if (statusLabel) statusLabel.textContent = 'Tryk på mikrofonen for at starte din stemmebekendelse';
      if (activeControls) activeControls.style.display = 'none';
      if (reviewPanel) reviewPanel.style.display = 'none';
    } else if (state === 'RECORDING') {
      if (micBtn) {
        micBtn.classList.add('recording');
        micBtn.innerHTML = '⏹️';
        micBtn.title = 'Stop optagelse';
      }
      if (statusLabel) statusLabel.textContent = 'Optager... Tal roligt og oprigtigt på dansk';
      if (activeControls) activeControls.style.display = 'flex';
      if (pauseBtn) pauseBtn.textContent = '⏸️ Pause';
      if (reviewPanel) reviewPanel.style.display = 'none';
    } else if (state === 'PAUSED') {
      if (statusLabel) statusLabel.textContent = 'Optagelse sat på pause';
      if (pauseBtn) pauseBtn.textContent = '▶️ Genoptag';
    } else if (state === 'REVIEW') {
      if (micBtn) {
        micBtn.classList.remove('recording');
        micBtn.innerHTML = '🎙️';
      }
      if (statusLabel) statusLabel.textContent = 'Optagelse færdig — Lyt igennem eller slet før indsendelse';
      if (activeControls) activeControls.style.display = 'none';
      if (reviewPanel) reviewPanel.style.display = 'block';
      if (audioPlayer && payload.audioUrl) {
        audioPlayer.src = payload.audioUrl;
      }
    }
  }

  async handleConfessionSubmit() {
    const consentCb = document.getElementById('confession-consent-checkbox');
    const errorBanner = document.getElementById('intake-error-banner');
    const btnSubmit = document.getElementById('btn-submit-confession');

    if (errorBanner) errorBanner.style.display = 'none';

    if (!consentCb || !consentCb.checked) {
      if (errorBanner) {
        errorBanner.textContent =
          'Du skal afkrydse samtykkeboksen før vi må uploade eller analysere din bekendelse.';
        errorBanner.style.display = 'block';
      }
      return;
    }

    try {
      if (btnSubmit) {
        btnSubmit.disabled = true;
        btnSubmit.textContent = '⏳ Analyserer ifølge Koranen og autentisk Sunnah...';
      }

      let analysisResult = null;

      if (this.intakeMode === 'voice') {
        const transcriptHintEl = document.getElementById('voice-transcript-preview');
        const transcriptHint = transcriptHintEl ? transcriptHintEl.value.trim() : '';

        if (!this.recorder.audioBlob) {
          throw new Error(
            'Optag venligst din stemmebekendelse først (eller skift til fanen "Skriv bekendelse").'
          );
        }

        analysisResult = await ApiClient.submitVoiceConfession(
          this.recorder.audioBlob,
          this.recorder.filename,
          true,
          transcriptHint
        );
      } else {
        const textarea = document.getElementById('confession-text-input');
        const text = textarea ? textarea.value.trim() : '';
        if (!text) {
          throw new Error('Skriv venligst din bekendelse i tekstfeltet før indsendelse.');
        }
        analysisResult = await ApiClient.submitTextConfession(text, true);
        sessionStorage.removeItem(DRAFT_STORAGE_KEY);
      }

      this.currentAnalysis = analysisResult;
      renderAssessmentResult(this.currentAnalysis, (actionId, isChecked, container) =>
        this.handleChecklistToggle(actionId, isChecked, container)
      );
      await this.navigateTo('resultat');
      await this.refreshHomeAndBadges();
      showToast('Din islamiske vurdering og handlingsplan er klar.');
    } catch (err) {
      if (errorBanner) {
        errorBanner.textContent = err.message || 'Der opstod en fejl under analysen.';
        errorBanner.style.display = 'block';
      }
    } finally {
      if (btnSubmit) {
        btnSubmit.disabled = false;
        btnSubmit.textContent = '🔍 Indsend til islamisk vurdering';
      }
    }
  }

  async handleChecklistToggle(actionId, isChecked, resultContainer = null) {
    try {
      await ApiClient.toggleAction(actionId, isChecked);
    } catch {
      // Even if action ID was local, update local state smoothly
    }

    if (this.currentAnalysis) {
      for (const listKey of ['required_actions', 'recommended_actions']) {
        for (const item of this.currentAnalysis[listKey] || []) {
          if (item.id === actionId || String(actionId).endsWith(`_${item.id}`)) {
            item.completed = isChecked;
          }
        }
      }
      if (resultContainer) {
        const all = [
          ...(this.currentAnalysis.required_actions || []),
          ...(this.currentAnalysis.recommended_actions || []),
        ];
        const done = all.filter((a) => a.completed).length;
        const pct = all.length > 0 ? Math.round((done / all.length) * 100) : 0;
        const badge = document.getElementById('result-checklist-counter');
        const fill = document.getElementById('result-progress-fill');
        if (badge) badge.textContent = `${done} af ${all.length} gennemført (${pct}%)`;
        if (fill) fill.style.width = `${pct}%`;
      }
    }

    await this.refreshHomeAndBadges();
    showToast(isChecked ? 'Handling markeret som gennemført ✓' : 'Handling markeret som udestående');
  }

  async refreshHomeAndBadges() {
    try {
      const [summary, actions] = await Promise.all([
        ApiClient.getDashboardSummary(),
        ApiClient.getActions(),
      ]);

      const navBadge = document.getElementById('nav-pending-actions-badge');
      if (navBadge) {
        const pendingCount = summary.pending_actions || 0;
        navBadge.textContent = pendingCount;
        navBadge.style.display = pendingCount > 0 ? 'inline-block' : 'none';
      }

      // Render outstanding actions on Home page
      const homeActionsList = document.getElementById('home-outstanding-actions');
      if (homeActionsList) {
        const pending = (actions || []).filter((a) => !a.completed).slice(0, 4);
        if (pending.length === 0) {
          homeActionsList.innerHTML = `
            <p style="color:var(--color-text-muted); font-size:0.92rem;">
              Du har ingen udestående handlinger i øjeblikket. Start en ny bekendelse ovenfor for at få en personlig handlingsplan.
            </p>
          `;
        } else {
          homeActionsList.innerHTML = pending
            .map(
              (a) => `
              <label class="checklist-item" data-action-id="${escapeHtml(a.id)}">
                <input type="checkbox" class="checklist-checkbox home-action-cb" data-action-id="${escapeHtml(a.id)}" />
                <div class="checklist-content">
                  <div class="checklist-title">${escapeHtml(a.title || a.description)}</div>
                  <div class="checklist-desc">${escapeHtml(a.description || '')}</div>
                </div>
              </label>
            `
            )
            .join('');

          homeActionsList.querySelectorAll('.home-action-cb').forEach((cb) => {
            cb.addEventListener('change', async (e) => {
              const aid = e.target.getAttribute('data-action-id');
              await this.handleChecklistToggle(aid, e.target.checked);
              await this.refreshHomeAndBadges();
            });
          });
        }
      }
    } catch {
      // Ignore network errors on initial boot
    }
  }

  async loadActionsPage() {
    const listEl = document.getElementById('master-actions-list');
    const summaryBadge = document.getElementById('master-actions-summary');
    const progressFill = document.getElementById('master-actions-progress');
    if (!listEl) return;

    try {
      const actions = await ApiClient.getActions();
      const total = actions.length;
      const done = actions.filter((a) => a.completed).length;
      const pct = total > 0 ? Math.round((done / total) * 100) : 0;

      if (summaryBadge) summaryBadge.textContent = `${done} af ${total} gennemført (${pct}%)`;
      if (progressFill) progressFill.style.width = `${pct}%`;

      const filtered = actions.filter((a) => {
        if (this.actionFilter === 'pending') return !a.completed;
        if (this.actionFilter === 'completed') return a.completed;
        return true;
      });

      if (filtered.length === 0) {
        listEl.innerHTML = `
          <div class="card" style="text-align:center; color:var(--color-text-muted);">
            Ingen handlingspunkter i denne visning.
          </div>
        `;
        return;
      }

      listEl.innerHTML = filtered
        .map(
          (a, i) => `
          <label class="checklist-item ${a.completed ? 'completed' : ''}">
            <input type="checkbox" class="checklist-checkbox master-action-cb" data-action-id="${escapeHtml(a.id)}" ${a.completed ? 'checked' : ''} />
            <div class="checklist-content">
              <div style="display:flex; justify-content:space-between; align-items:center; gap:0.5rem;">
                <span class="checklist-title">${i + 1}. ${escapeHtml(a.title || a.description)}</span>
                <span class="badge ${a.category === 'wajib' ? 'badge-people' : 'badge-allah'}" style="font-size:0.72rem;">
                  ${a.category === 'wajib' ? 'Obligatorisk (Wajib)' : 'Anbefalet (Mustahabb)'}
                </span>
              </div>
              <p class="checklist-desc">${escapeHtml(a.description || '')}</p>
            </div>
          </label>
        `
        )
        .join('');

      listEl.querySelectorAll('.master-action-cb').forEach((cb) => {
        cb.addEventListener('change', async (e) => {
          const aid = e.target.getAttribute('data-action-id');
          await this.handleChecklistToggle(aid, e.target.checked);
          await this.loadActionsPage();
        });
      });
    } catch (err) {
      listEl.innerHTML = `<p style="color:var(--color-status-danger);">${escapeHtml(err.message)}</p>`;
    }

    // Bind filter buttons
    document.querySelectorAll('[data-action-filter]').forEach((btn) => {
      btn.onclick = () => {
        this.actionFilter = btn.getAttribute('data-action-filter');
        document.querySelectorAll('[data-action-filter]').forEach((b) =>
          b.classList.toggle('active', b === btn)
        );
        this.loadActionsPage();
      };
    });
  }

  setupHistoryAndJournalControls() {
    const btnSaveJournal = document.getElementById('btn-save-journal');
    if (btnSaveJournal) {
      btnSaveJournal.addEventListener('click', async () => {
        const titleInput = document.getElementById('journal-title-input');
        const textInput = document.getElementById('journal-reflection-input');
        const tagsInput = document.getElementById('journal-tags-input');

        const reflection = textInput ? textInput.value.trim() : '';
        if (!reflection) {
          showToast('Skriv venligst din refleksion først.');
          return;
        }
        const title = titleInput && titleInput.value.trim() ? titleInput.value.trim() : 'Personlig Tawbah-refleksion';
        const tags = tagsInput && tagsInput.value.trim()
          ? tagsInput.value.split(',').map((t) => t.trim()).filter(Boolean)
          : ['tawbah', 'muhasabah'];

        try {
          await ApiClient.createJournalEntry(title, reflection, tags);
          if (titleInput) titleInput.value = '';
          if (textInput) textInput.value = '';
          if (tagsInput) tagsInput.value = '';
          showToast('Refleksion gemt i din private dagbog.');
          await this.loadHistoryAndJournalPage();
        } catch (err) {
          showToast(err.message);
        }
      });
    }
  }

  async loadHistoryAndJournalPage() {
    const kpiConf = document.getElementById('kpi-total-confessions');
    const kpiPend = document.getElementById('kpi-pending-actions');
    const kpiComp = document.getElementById('kpi-completed-actions');
    const kpiJour = document.getElementById('kpi-journal-entries');
    const confListEl = document.getElementById('history-confessions-list');
    const journalListEl = document.getElementById('history-journal-list');

    try {
      const [summary, confessions, journalEntries] = await Promise.all([
        ApiClient.getDashboardSummary(),
        ApiClient.getConfessions(),
        ApiClient.getJournal(),
      ]);

      if (kpiConf) kpiConf.textContent = summary.total_confessions || 0;
      if (kpiPend) kpiPend.textContent = summary.pending_actions || 0;
      if (kpiComp) kpiComp.textContent = summary.completed_actions || 0;
      if (kpiJour) kpiJour.textContent = summary.journal_entries ?? journalEntries.length;

      if (confListEl) {
        if (!confessions || confessions.length === 0) {
          confListEl.innerHTML = `<p style="color:var(--color-text-muted);">Ingen gemte bekendelser endnu.</p>`;
        } else {
          confListEl.innerHTML = confessions
            .map(
              (c) => `
              <div class="card" style="margin-bottom:0.85rem;">
                <div class="section-header" style="margin-bottom:0.4rem;">
                  <div>
                    <span style="font-size:0.78rem; color:var(--color-text-muted);">
                      ${c.raw_input_type === 'voice' ? '🎙️ Stemmebekendelse' : '✏️ Skriftlig bekendelse'} • ${new Date(c.created_at).toLocaleString('da-DK')}
                    </span>
                    <h4 style="color:var(--color-brand-primary); margin-top:0.2rem;">${escapeHtml(c.summary || c.raw_text || 'Islamisk vurdering')}</h4>
                  </div>
                  ${renderClassificationBadge(c.sin_classification)}
                </div>
                <div style="display:flex; gap:0.5rem; margin-top:0.75rem;">
                  <button type="button" class="btn btn-secondary btn-sm btn-view-confession" data-conf-id="${escapeHtml(c.id)}">
                    📖 Se fuld vurdering
                  </button>
                  <button type="button" class="btn btn-danger btn-sm btn-delete-confession" data-conf-id="${escapeHtml(c.id)}">
                    🗑️ Slet bekendelse
                  </button>
                </div>
              </div>
            `
            )
            .join('');

          confListEl.querySelectorAll('.btn-view-confession').forEach((btn) => {
            btn.addEventListener('click', async () => {
              const cid = btn.getAttribute('data-conf-id');
              const fullData = await ApiClient.getConfessionById(cid);
              this.currentAnalysis = fullData;
              renderAssessmentResult(this.currentAnalysis, (actionId, isChecked, container) =>
                this.handleChecklistToggle(actionId, isChecked, container)
              );
              await this.navigateTo('resultat');
            });
          });

          confListEl.querySelectorAll('.btn-delete-confession').forEach((btn) => {
            btn.addEventListener('click', async () => {
              const cid = btn.getAttribute('data-conf-id');
              await ApiClient.deleteConfession(cid);
              showToast('Bekendelse og tilhørende optagelse/data slettet.');
              await this.loadHistoryAndJournalPage();
              await this.refreshHomeAndBadges();
            });
          });
        }
      }

      if (journalListEl) {
        if (!journalEntries || journalEntries.length === 0) {
          journalListEl.innerHTML = `<p style="color:var(--color-text-muted);">Ingen personlige refleksioner i dagbogen endnu.</p>`;
        } else {
          journalListEl.innerHTML = journalEntries
            .map(
              (j) => `
              <div class="card" style="margin-bottom:0.75rem; background:var(--color-surface-elevated);">
                <div class="section-header" style="margin-bottom:0.35rem;">
                  <strong>${escapeHtml(j.title || 'Refleksion')}</strong>
                  <span style="font-size:0.76rem; color:var(--color-text-muted);">${new Date(j.created_at).toLocaleString('da-DK')}</span>
                </div>
                <p style="font-size:0.92rem; margin-bottom:0.5rem;">${escapeHtml(j.content)}</p>
                <div style="display:flex; justify-content:space-between; align-items:center;">
                  <div>
                    ${(j.tags || []).map((t) => `<span class="badge badge-both" style="font-size:0.7rem; margin-right:0.3rem;">#${escapeHtml(t)}</span>`).join('')}
                  </div>
                  <button type="button" class="btn btn-danger btn-sm btn-delete-journal" data-entry-id="${escapeHtml(j.id)}">
                    Slet
                  </button>
                </div>
              </div>
            `
            )
            .join('');

          journalListEl.querySelectorAll('.btn-delete-journal').forEach((btn) => {
            btn.addEventListener('click', async () => {
              const eid = btn.getAttribute('data-entry-id');
              await ApiClient.deleteJournalEntry(eid);
              showToast('Refleksion slettet.');
              await this.loadHistoryAndJournalPage();
            });
          });
        }
      }
    } catch (err) {
      showToast(err.message);
    }
  }

  setupKnowledgeControls() {
    const searchInput = document.getElementById('knowledge-search-input');
    if (searchInput) {
      searchInput.addEventListener('input', () => this.loadKnowledgePage());
    }
    document.querySelectorAll('[data-knowledge-cat]').forEach((btn) => {
      btn.addEventListener('click', () => {
        this.knowledgeCategory = btn.getAttribute('data-knowledge-cat');
        document.querySelectorAll('[data-knowledge-cat]').forEach((b) =>
          b.classList.toggle('active', b === btn)
        );
        this.loadKnowledgePage();
      });
    });
  }

  async loadKnowledgePage() {
    const container = document.getElementById('knowledge-results-container');
    const searchInput = document.getElementById('knowledge-search-input');
    if (!container) return;

    const q = searchInput ? searchInput.value.trim() : '';
    const cat = this.knowledgeCategory === 'all' ? '' : this.knowledgeCategory;

    try {
      const kb = await ApiClient.getKnowledgeBase(q, cat);
      let html = '';

      if (kb.quran && kb.quran.length > 0) {
        html += `<h3 class="section-title" style="margin:1rem 0 0.75rem;">📖 Koranvers (${kb.quran.length})</h3>`;
        html += kb.quran
          .map(
            (v) => `
            <div class="scripture-card">
              <div class="scripture-header">
                <span class="scripture-ref">Surah ${escapeHtml(v.surah)} (${escapeHtml(v.surah_number || '')}:${escapeHtml(v.ayah)})</span>
                <span class="badge badge-sahih">Den Ædle Koran</span>
              </div>
              <div class="arabic-text" lang="ar" dir="rtl">${escapeHtml(v.arabic_text)}</div>
              <p class="danish-translation">"${escapeHtml(v.danish_translation || v.translation_da)}"</p>
              <div class="scripture-explanation">${escapeHtml(v.explanation || v.relevance || '')}</div>
            </div>
          `
          )
          .join('');
      }

      if (kb.hadith && kb.hadith.length > 0) {
        html += `<h3 class="section-title" style="margin:1.5rem 0 0.75rem;">📜 Autentiske Hadith (${kb.hadith.length})</h3>`;
        html += kb.hadith
          .map(
            (h) => `
            <div class="scripture-card">
              <div class="scripture-header">
                <span class="scripture-ref">${escapeHtml(h.collection)} — nr. ${escapeHtml(h.hadith_number)}</span>
                <span class="badge badge-sahih">${escapeHtml(h.authenticity_grading || h.grade || 'Sahih')}</span>
              </div>
              <div class="arabic-text" lang="ar" dir="rtl">${escapeHtml(h.arabic_text)}</div>
              <p class="danish-translation">"${escapeHtml(h.danish_translation || h.translation_da)}"</p>
              <div class="scripture-explanation">${escapeHtml(h.explanation || h.relevance || '')}</div>
            </div>
          `
          )
          .join('');
      }

      if (kb.duas && kb.duas.length > 0) {
        html += `<h3 class="section-title" style="margin:1.5rem 0 0.75rem;">🤲 Autentiske Duaer for Tawbah (${kb.duas.length})</h3>`;
        html += kb.duas
          .map(
            (d) => `
            <div class="scripture-card">
              <div class="scripture-header">
                <span class="scripture-ref">${escapeHtml(d.title)}</span>
                <span class="badge badge-both">${escapeHtml(d.source)}</span>
              </div>
              <div class="arabic-text" lang="ar" dir="rtl">${escapeHtml(d.arabic_text)}</div>
              ${d.transliteration ? `<p style="font-size:0.86rem; color:var(--color-accent-dark); margin-bottom:0.4rem;"><em>${escapeHtml(d.transliteration)}</em></p>` : ''}
              <p class="danish-translation">"${escapeHtml(d.danish_translation || d.translation_da)}"</p>
              <div class="scripture-explanation">${escapeHtml(d.context || d.when_to_recite || '')}</div>
            </div>
          `
          )
          .join('');
      }

      if (!html) {
        html = `<div class="card">Ingen kilder matchede din søgning.</div>`;
      }
      container.innerHTML = html;
    } catch (err) {
      container.innerHTML = `<div class="card">${escapeHtml(err.message)}</div>`;
    }
  }

  setupSettingsAndAuthControls() {
    const btnRegister = document.getElementById('btn-auth-register');
    const btnLogin = document.getElementById('btn-auth-login');
    const btnLogout = document.getElementById('btn-auth-logout');
    const btnWipe = document.getElementById('btn-panic-wipe');
    const btnExport = document.getElementById('btn-export-data');

    if (btnRegister) {
      btnRegister.addEventListener('click', async () => {
        const u = document.getElementById('auth-username')?.value.trim();
        const p = document.getElementById('auth-password')?.value.trim();
        if (!u || !p) {
          showToast('Indtast brugernavn og adgangskode.');
          return;
        }
        try {
          await ApiClient.register(u, p);
          this.updateAuthUI();
          await this.refreshHomeAndBadges();
          showToast(`Konto oprettet og logget ind som ${u}.`);
        } catch (err) {
          showToast(err.message);
        }
      });
    }

    if (btnLogin) {
      btnLogin.addEventListener('click', async () => {
        const u = document.getElementById('auth-username')?.value.trim();
        const p = document.getElementById('auth-password')?.value.trim();
        if (!u || !p) {
          showToast('Indtast brugernavn og adgangskode.');
          return;
        }
        try {
          await ApiClient.login(u, p);
          this.updateAuthUI();
          await this.refreshHomeAndBadges();
          showToast(`Logget ind som ${u}.`);
        } catch (err) {
          showToast(err.message);
        }
      });
    }

    if (btnLogout) {
      btnLogout.addEventListener('click', async () => {
        ApiClient.logout();
        this.updateAuthUI();
        await this.refreshHomeAndBadges();
        showToast('Du er nu logget ud.');
      });
    }

    if (btnExport) {
      btnExport.addEventListener('click', async () => {
        const [confessions, actions, journal] = await Promise.all([
          ApiClient.getConfessions(),
          ApiClient.getActions(),
          ApiClient.getJournal(),
        ]);
        const blob = new Blob([JSON.stringify({ confessions, actions, journal }, null, 2)], {
          type: 'application/json',
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'tawbah_data_export.json';
        a.click();
        URL.revokeObjectURL(url);
        showToast('Dine data er eksporteret som JSON.');
      });
    }

    if (btnWipe) {
      btnWipe.addEventListener('click', async () => {
        await ApiClient.wipeAccountData();
        sessionStorage.removeItem(DRAFT_STORAGE_KEY);
        showToast('Al historik, bekendelser, handlingspunkter og dagbogsnotater er permanent slettet.');
        await this.refreshHomeAndBadges();
      });
    }
  }

  updateAuthUI() {
    const user = ApiClient.getUser();
    const statusBox = document.getElementById('auth-current-status');
    const btnLogout = document.getElementById('btn-auth-logout');
    if (statusBox) {
      if (user && user.username) {
        statusBox.innerHTML = `Aktiv privat konto: <strong>${escapeHtml(user.username)}</strong> (Beskyttet med bruger-isolering)`;
        if (btnLogout) btnLogout.style.display = 'inline-flex';
      } else {
        statusBox.innerHTML = `Privat lokal session (Du kan oprette en personlig adgangskodebeskyttet konto nedenfor)`;
        if (btnLogout) btnLogout.style.display = 'none';
      }
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const app = new TawbahApp();
  app.init();
});
