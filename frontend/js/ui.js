/**
 * frontend/js/ui.js
 * UI Rendering Helpers for Tawbah Guiden (Islamisk Opgørelse & Anger App)
 */

export function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export function showToast(message) {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const el = document.createElement('div');
  el.className = 'toast';
  el.textContent = message;
  container.appendChild(el);
  setTimeout(() => {
    el.remove();
  }, 3600);
}

export function renderClassificationBadge(classification) {
  const cls = String(classification || '').toLowerCase();
  if (cls === 'huqooq_allah') {
    return `<span class="badge badge-allah">🕌 Allahs rettigheder (Huqooq Allah)</span>`;
  }
  if (cls === 'huqooq_al_ibad') {
    return `<span class="badge badge-people">🤝 Menneskers rettigheder (Huqooq al-Ibad)</span>`;
  }
  return `<span class="badge badge-both">⚖️ Både Allahs og menneskers rettigheder (Huqooq Allah &amp; Huqooq al-Ibad)</span>`;
}

export function renderConfidenceBadge(level) {
  const map = {
    high: 'Høj kilde-sikkerhed',
    medium: 'Middel sikkerhed (nuanceret spørgsmål)',
    low: 'Lav sikkerhed — kræver lærd vurdering',
  };
  return `<span class="badge badge-sahih">✓ ${escapeHtml(map[level] || map.high)}</span>`;
}

export function renderAssessmentResult(analysis, onToggleAction) {
  const container = document.getElementById('result-content');
  if (!container || !analysis) return;

  const reqActions = analysis.required_actions || [];
  const recActions = analysis.recommended_actions || [];
  const allActions = [...reqActions, ...recActions];
  const completedCount = allActions.filter((a) => a.completed).length;
  const totalCount = allActions.length;
  const pct = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  const incidentsHtml = (analysis.incidents || [])
    .map(
      (inc, idx) => `
      <div class="card" style="margin-bottom:0.85rem; border-left: 4px solid var(--color-brand-primary);">
        <div class="section-header" style="margin-bottom:0.4rem;">
          <h4 style="font-family:var(--font-serif); color:var(--color-brand-primary);">
            Hændelse ${idx + 1}: ${escapeHtml(inc.incident_title || 'Identificeret handling')}
          </h4>
          ${renderClassificationBadge(inc.sin_classification)}
        </div>
        <p style="margin-bottom:0.5rem;">${escapeHtml(inc.description)}</p>
        ${
          inc.affected_parties && inc.affected_parties.length > 0
            ? `<p style="font-size:0.86rem; color:var(--color-text-muted);"><strong>Berørte parter:</strong> ${inc.affected_parties.map(escapeHtml).join(', ')}</p>`
            : `<p style="font-size:0.86rem; color:var(--color-text-muted);"><strong>Berørte parter:</strong> Kun mellem dig og Allah (ingen menneskelige ofre)</p>`
        }
      </div>
    `
    )
    .join('');

  const allahRightsHtml = (analysis.allah_rights || [])
    .map((r) => `<li style="margin-bottom:0.35rem;">${escapeHtml(r)}</li>`)
    .join('');

  const peopleRightsHtml =
    analysis.people_rights && analysis.people_rights.length > 0
      ? analysis.people_rights.map((r) => `<li style="margin-bottom:0.35rem;">${escapeHtml(r)}</li>`).join('')
      : `<li>Ingen krænkelse af andre menneskers direkte rettigheder identificeret (bevar synden skjult under Allahs slør — <em>Al-Sitr</em>).</li>`;

  const renderActionRow = (act, indexNum, isRequired) => {
    const checked = act.completed ? 'checked' : '';
    const doneClass = act.completed ? 'completed' : '';
    const badgeLabel = isRequired
      ? `<span class="badge badge-people" style="font-size:0.7rem;">Obligatorisk (Wajib)</span>`
      : `<span class="badge badge-allah" style="font-size:0.7rem;">Anbefalet (Mustahabb)</span>`;

    return `
      <label class="checklist-item ${doneClass}" data-action-id="${escapeHtml(act.id)}">
        <input type="checkbox" class="checklist-checkbox" data-action-id="${escapeHtml(act.id)}" ${checked} />
        <div class="checklist-content">
          <div style="display:flex; justify-content:space-between; align-items:center; gap:0.5rem; flex-wrap:wrap;">
            <span class="checklist-title">${indexNum}. ${escapeHtml(act.title || act.description)}</span>
            ${badgeLabel}
          </div>
          ${
            act.title && act.description && act.title !== act.description
              ? `<p class="checklist-desc">${escapeHtml(act.description)}</p>`
              : ''
          }
          ${
            act.explanation
              ? `<p class="checklist-desc" style="color:var(--color-brand-soft);"><em>Begrundelse:</em> ${escapeHtml(act.explanation)}</p>`
              : ''
          }
        </div>
      </label>
    `;
  };

  let counter = 1;
  const reqChecklistHtml = reqActions.map((a) => renderActionRow(a, counter++, true)).join('');
  const recChecklistHtml = recActions.map((a) => renderActionRow(a, counter++, false)).join('');

  const quranHtml = (analysis.quran_references || [])
    .map(
      (q) => `
      <div class="scripture-card">
        <div class="scripture-header">
          <span class="scripture-ref">📖 Koranen — Surah ${escapeHtml(q.surah)}, Ayah ${escapeHtml(q.ayah)}</span>
          <span class="badge badge-sahih">Verificeret Koran-reference</span>
        </div>
        <div class="arabic-text" lang="ar" dir="rtl">${escapeHtml(q.arabic_text)}</div>
        <p class="danish-translation">"${escapeHtml(q.danish_translation)}"</p>
        <div class="scripture-explanation"><strong>Relevans:</strong> ${escapeHtml(q.explanation)}</div>
      </div>
    `
    )
    .join('');

  const hadithHtml = (analysis.hadith_references || [])
    .map(
      (h) => `
      <div class="scripture-card">
        <div class="scripture-header">
          <span class="scripture-ref">📜 ${escapeHtml(h.collection)} — Hadith nr. ${escapeHtml(h.hadith_number)}</span>
          <span class="badge badge-sahih">Autenticitet: ${escapeHtml(h.authenticity_grading)}</span>
        </div>
        ${
          h.arabic_text
            ? `<div class="arabic-text" lang="ar" dir="rtl">${escapeHtml(h.arabic_text)}</div>`
            : ''
        }
        <p class="danish-translation">"${escapeHtml(h.danish_translation)}"</p>
        <div class="scripture-explanation"><strong>Forklaring:</strong> ${escapeHtml(h.explanation)}</div>
      </div>
    `
    )
    .join('');

  const duasHtml = (analysis.recommended_duas || [])
    .map(
      (d) => `
      <div class="scripture-card">
        <div class="scripture-header">
          <span class="scripture-ref">🤲 ${escapeHtml(d.title)}</span>
          <span class="badge badge-both">Kilde: ${escapeHtml(d.source)}</span>
        </div>
        <div class="arabic-text" lang="ar" dir="rtl">${escapeHtml(d.arabic_text)}</div>
        ${
          d.transliteration
            ? `<p style="font-size:0.88rem; color:var(--color-accent-dark); margin-bottom:0.45rem;"><strong>Udtale (Transskription):</strong> <em>${escapeHtml(d.transliteration)}</em></p>`
            : ''
        }
        <p class="danish-translation">"${escapeHtml(d.danish_translation)}"</p>
        <div class="scripture-explanation"><strong>Hvornår og hvordan den bruges:</strong> ${escapeHtml(d.context)}</div>
      </div>
    `
    )
    .join('');

  container.innerHTML = `
    ${
      analysis.offline_mode || analysis.demonstration_mode
        ? `<div class="card card-gold" style="padding:0.9rem 1.2rem; margin-bottom:1.15rem;">
            <strong>ℹ️ Udviklings- og demonstrationstilstand (Verificeret Ahlus-Sunnah Regelmotor):</strong>
            Denne vurdering er genereret med applikationens deterministiske islamiske vidensbase (uden ekstern API-nøgle) og er baseret på verificerede vers fra Koranen og autentisk Sunnah. Den udgør vejledende undervisning og ikke en bindende juridisk fatwa.
          </div>`
        : ''
    }

    ${
      analysis.transcript
        ? `<div class="card" style="background-color:var(--color-surface-subtle);">
            <h4 style="color:var(--color-brand-primary); margin-bottom:0.35rem;">🎙️ Transskriberet stemmebekendelse (Dansk):</h4>
            <p style="font-style:italic;">"${escapeHtml(analysis.transcript)}"</p>
          </div>`
        : ''
    }

    <!-- 1. DIN ISLAMISKE VURDERING (KLASSIFIKATION) -->
    <div class="card">
      <div class="section-header">
        <div>
          <span style="font-size:0.76rem; text-transform:uppercase; letter-spacing:0.06em; color:var(--color-text-muted); font-weight:700;">
            DIN ISLAMISKE VURDERING (YOUR ISLAMIC ASSESSMENT)
          </span>
          <h2 class="section-title" style="margin-top:0.2rem;">Klassifikation af forpligtelser og rettigheder</h2>
        </div>
        <div style="display:flex; gap:0.5rem; flex-wrap:wrap;">
          ${renderClassificationBadge(analysis.sin_classification)}
          ${renderConfidenceBadge(analysis.confidence_level)}
        </div>
      </div>

      ${
        analysis.scholar_consultation_required
          ? `<div class="card card-gold" style="margin-top:0.75rem; margin-bottom:0; border-left:4px solid var(--color-status-warning);">
              <strong>⚠️ Anbefaling om konsultation med kvalificeret lærd (Imam/Mufti):</strong>
              Denne sag indeholder alvorlige eller komplekse omstændigheder, hvor personlig rådgivning hos en kvalificeret islamisk lærd anbefales.
            </div>`
          : ''
      }
    </div>

    <!-- 2. HVAD DU HAR GJORT -->
    <div class="card">
      <h3 class="section-title" style="margin-bottom:0.5rem;">Hvad du har gjort (Opsummering uden fordømmelse)</h3>
      <p style="margin-bottom:1rem;">${escapeHtml(analysis.incident_summary)}</p>
      ${incidentsHtml}
    </div>

    <!-- 3. ISLAMISK VURDERING & RETLIG FORKLARING -->
    <div class="card">
      <h3 class="section-title" style="margin-bottom:0.5rem;">Islamisk vurdering (Koranen &amp; Autentisk Sunnah)</h3>
      <p style="margin-bottom:1rem;">${escapeHtml(analysis.severity_explanation)}</p>

      ${
        analysis.scholarly_disagreement
          ? `<div style="background-color:var(--color-accent-tint); border:1px solid var(--color-accent-border); padding:1rem; border-radius:var(--radius-sm); margin-top:0.75rem;">
              <strong style="color:var(--color-accent-dark);">📚 Lærdes nuancer og meningsforskelle (Ikhtilaf):</strong>
              <p style="font-size:0.9rem; margin-top:0.3rem;">${escapeHtml(analysis.scholarly_disagreement)}</p>
            </div>`
          : ''
      }

      <div style="background-color:var(--color-brand-tint); border:1px solid var(--color-brand-border); padding:1rem; border-radius:var(--radius-sm); margin-top:0.9rem;">
        <strong style="color:var(--color-brand-primary);">De 4 grundbetingelser for oprigtig Tawbah i Ahlus-Sunnah wal-Jama'ah:</strong>
        <ol style="margin-top:0.45rem; padding-left:1.35rem; font-size:0.9rem;">
          <li><strong>Ophør (Al-Iqla'):</strong> Stop den syndige handling øjeblikkeligt for Allahs skyld.</li>
          <li><strong>Fortrydelse (An-Nadam):</strong> Føl oprigtig anger og sorg i hjertet over det skete.</li>
          <li><strong>Fast beslutning (Al-Azm):</strong> Beslut oprigtigt aldrig at vende tilbage til synden.</li>
          <li><strong>Genopretning af menneskers rettigheder (Radd al-Mazalim):</strong> Når et andet menneske er krænket, skal uretten gøres god igen (tilbagelevering, erstatning eller undskyldning).</li>
        </ol>
      </div>
    </div>

    <!-- 4. HVIS RETTIGHEDER ER BLEVET KRÆNKET? -->
    <div class="card">
      <h3 class="section-title" style="margin-bottom:0.75rem;">Hvis rettigheder er blevet krænket?</h3>
      <p style="margin-bottom:0.85rem; font-size:0.92rem;">
        <strong>Berørte parter:</strong>
        ${
          analysis.affected_parties && analysis.affected_parties.length > 0
            ? analysis.affected_parties.map((p) => `<span class="badge badge-people" style="margin-right:0.35rem;">${escapeHtml(p)}</span>`).join('')
            : `<span class="badge badge-allah">Kun Allahs rettigheder (Ingen menneskelige parter krænket)</span>`
        }
      </p>

      <div class="grid-2">
        <div style="background:var(--color-surface-subtle); padding:1rem; border-radius:var(--radius-sm);">
          <h4 style="color:var(--color-status-allah); margin-bottom:0.45rem;">🕌 Allahs rettigheder (Huqooq Allah)</h4>
          <ul style="padding-left:1.2rem; font-size:0.9rem;">${allahRightsHtml}</ul>
        </div>
        <div style="background:var(--color-surface-subtle); padding:1rem; border-radius:var(--radius-sm);">
          <h4 style="color:var(--color-status-people); margin-bottom:0.45rem;">🤝 Menneskers rettigheder (Huqooq al-Ibad)</h4>
          <ul style="padding-left:1.2rem; font-size:0.9rem;">${peopleRightsHtml}</ul>
        </div>
      </div>

      ${
        analysis.apology_guidance
          ? `<div style="margin-top:1rem; padding:1rem; background:var(--color-surface-elevated); border-left:4px solid var(--color-brand-primary); border-radius:var(--radius-sm);">
              <strong>🗣️ Vejledning om undskyldning &amp; hvorvidt offeret skal informeres:</strong>
              <p style="font-size:0.92rem; margin-top:0.25rem;">${escapeHtml(analysis.apology_guidance)}</p>
            </div>`
          : ''
      }

      ${
        analysis.restitution_guidance
          ? `<div style="margin-top:0.85rem; padding:1rem; background:var(--color-surface-elevated); border-left:4px solid var(--color-accent-gold); border-radius:var(--radius-sm);">
              <strong>💳 Vejledning om tilbagelevering og økonomisk kompensation (Radd al-Mazalim):</strong>
              <p style="font-size:0.92rem; margin-top:0.25rem;">${escapeHtml(analysis.restitution_guidance)}</p>
            </div>`
          : ''
      }
    </div>

    <!-- 5. HVAD SKAL DU GØRE NU? (INTERAKTIV TJEKLISTE) -->
    <div class="card">
      <div class="section-header">
        <div>
          <h3 class="section-title">Hvad skal du gøre nu? (Handlingsplan)</h3>
          <p style="font-size:0.88rem; color:var(--color-text-muted);">
            Marker hvert punkt, efterhånden som du udfører det. Status gemmes automatisk.
          </p>
        </div>
        <span id="result-checklist-counter" class="badge badge-both">
          ${completedCount} af ${totalCount} gennemført (${pct}%)
        </span>
      </div>

      <div class="progress-track">
        <div id="result-progress-fill" class="progress-fill" style="width:${pct}%;"></div>
      </div>

      <h4 style="color:var(--color-brand-primary); margin:1rem 0 0.6rem;">Påkrævede handlinger (Obligatorisk / Wajib)</h4>
      <div id="result-required-list">
        ${reqChecklistHtml || '<p>Ingen specifikke obligatoriske punkter.</p>'}
      </div>

      <h4 style="color:var(--color-brand-soft); margin:1.25rem 0 0.6rem;">Anbefalede gode handlinger (Mustahabb / Sunnah)</h4>
      <div id="result-recommended-list">
        ${recChecklistHtml || '<p>Ingen yderligere anbefalede punkter.</p>'}
      </div>
    </div>

    <!-- 6. BEVISER FRA KORANEN -->
    <div class="card">
      <h3 class="section-title" style="margin-bottom:0.85rem;">Beviser fra Den Ædle Koran</h3>
      ${quranHtml || '<p>Ingen specifikke koranvers fundet.</p>'}
    </div>

    <!-- 7. BEVISER FRA DEN AUTENTISKE SUNNAH -->
    <div class="card">
      <h3 class="section-title" style="margin-bottom:0.85rem;">Beviser fra den Autentiske Sunnah</h3>
      ${hadithHtml || '<p>Ingen specifikke hadith fundet.</p>'}
    </div>

    <!-- 8. ANBEFALEDE DUAER OG TILBEDELSE -->
    <div class="card">
      <h3 class="section-title" style="margin-bottom:0.85rem;">Anbefalede Duaer og Tilbedelse</h3>
      ${duasHtml || '<p>Ingen specifikke duaer fundet.</p>'}
    </div>

    <!-- 9. AFSLUTTENDE PÅMINDELSE -->
    <div class="card card-green-tint" style="border-left:5px solid var(--color-brand-primary);">
      <h3 class="section-title" style="margin-bottom:0.5rem;">🌿 Afsluttende påmindelse om ansvar og Allahs barmhjertighed</h3>
      <p style="font-size:1rem; line-height:1.7;">${escapeHtml(analysis.final_reminder)}</p>
    </div>
  `;

  // Bind interactive checklist toggles
  container.querySelectorAll('.checklist-checkbox').forEach((cb) => {
    cb.addEventListener('change', async (e) => {
      const actionId = e.target.getAttribute('data-action-id');
      const isChecked = e.target.checked;
      const itemEl = e.target.closest('.checklist-item');
      if (itemEl) {
        itemEl.classList.toggle('completed', isChecked);
      }
      if (onToggleAction) {
        await onToggleAction(actionId, isChecked, container);
      }
    });
  });
}
