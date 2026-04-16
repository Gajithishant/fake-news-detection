async function detectNews(id) {
  const btn = document.querySelector(`[data-id="${id}"]`);
  const box = document.getElementById(`result-${id}`);

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Analysing…';
  }

  try {
    const res = await fetch(`/detect/${id}`, { method: 'POST' });
    const data = await res.json();

    if (data.error) {
      box.innerHTML = `<div style="padding:12px 16px;font-size:13px;color:var(--fake-red)">${data.error}</div>`;
      return;
    }

    const isFake = data.is_fake === 'Fake';
    const cls   = isFake ? 'verdict-fake' : 'verdict-real';
    const icon  = isFake ? '✕' : '✓';
    const label = isFake ? 'Fake News Detected' : 'Verified Real News';
    const conf  = parseFloat(data.confidence) || 0;

    box.innerHTML = `
      <div class="analysis-box ${cls}">
        <div class="verdict-header">
          <div class="verdict-icon">${icon}</div>
          <div class="verdict-label">${label}</div>
          <div class="verdict-confidence">${conf.toFixed(1)}% confidence</div>
        </div>
        <div class="confidence-bar">
          <div class="confidence-fill" id="cf-${id}" style="width:0%"></div>
        </div>
        <div class="verdict-body">
          <div class="verdict-row">
            <span class="vr-label">Beneficiary</span>
            <span class="vr-value">${data.beneficiary}</span>
          </div>
          <div class="verdict-row">
            <span class="vr-label">Source</span>
            <span class="vr-value">${data.origin}</span>
          </div>
        </div>
      </div>
    `;

    // Animate confidence bar
    requestAnimationFrame(() => {
      const fill = document.getElementById(`cf-${id}`);
      if (fill) fill.style.width = conf + '%';
    });

  } catch (e) {
    box.innerHTML = `<div style="padding:12px 16px;font-size:13px;color:var(--fake-red)">Network error — please try again.</div>`;
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '🔍 Re-analyse';
    }
  }
}

function toggleFullNews(id) {
  const excerpt = document.getElementById(`excerpt-${id}`);
  const btn = excerpt.nextElementSibling;

  excerpt.classList.toggle('expanded');
  btn.textContent = excerpt.classList.contains('expanded') ? 'Show Less' : 'Read More';
}