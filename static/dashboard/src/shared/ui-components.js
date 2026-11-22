/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Design System: Apple macOS & iPadOS Dark Glassmorphism
 * Reusable UI Component Factory & Modal / Toast Framework
 */

const UI = {
  /**
   * Lucide-style Outline SVG Icon System
   */
  Icons: {
    dashboard: '<rect width="7" height="9" x="3" y="3" rx="1"></rect><rect width="7" height="5" x="14" y="3" rx="1"></rect><rect width="7" height="9" x="14" y="12" rx="1"></rect><rect width="7" height="5" x="3" y="16" rx="1"></rect>',
    check: '<polyline points="20 6 9 17 4 12"></polyline>',
    checkCircle: '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline>',
    x: '<line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line>',
    xCircle: '<circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line>',
    alertTriangle: '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line>',
    info: '<circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line>',
    refresh: '<path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path><path d="M3 3v5h5"></path><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"></path><path d="M16 16h5v5"></path>',
    search: '<circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line>',
    settings: '<circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>',
    user: '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle>',
    users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M22 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path>',
    trash: '<polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>',
    server: '<rect width="20" height="8" x="2" y="2" rx="2" ry="2"></rect><rect width="20" height="8" x="2" y="14" rx="2" ry="2"></rect><line x1="6" x2="6.01" y1="6" y2="6"></line><line x1="6" x2="6.01" y1="18" y2="18"></line>',
    terminal: '<polyline points="4 17 10 11 4 5"></polyline><line x1="12" x2="20" y1="19" y2="19"></line>',
    database: '<ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M3 5V19A9 3 0 0 0 21 19V5"></path><path d="M3 12A9 3 0 0 0 21 12"></path>',
    shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>',
    upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" x2="12" y1="3" y2="15"></line>',
    download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" x2="12" y1="15" y2="3"></line>',
    copy: '<rect width="14" height="14" x="8" y="8" rx="2" ry="2"></rect><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"></path>',
    mail: '<rect width="20" height="16" x="2" y="4" rx="2"></rect><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"></path>',
    inbox: '<polyline points="22 12 16 12 14 15 10 15 8 12 2 12"></polyline><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"></path>',
    fileText: '<path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" x2="8" y1="13" y2="13"></line><line x1="16" x2="8" y1="17" y2="17"></line><line x1="10" x2="8" y1="9" y2="9"></line>',
    zap: '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>',
    sparkles: '<path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"></path>',
    gamepad: '<line x1="6" x2="10" y1="12" y2="12"></line><line x1="8" x2="8" y1="10" y2="14"></line><line x1="15" x2="15.01" y1="13" y2="13"></line><line x1="18" x2="18.01" y1="11" y2="11"></line><rect width="20" height="12" x="2" y="6" rx="6"></rect>',
    package: '<path d="m16.5 9.4-9-5.19M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.29 7 12 12 20.71 7"></polyline><line x1="12" x2="12" y1="22" y2="12"></line>',
    plus: '<line x1="12" x2="12" y1="5" y2="19"></line><line x1="5" x2="19" y1="12" y2="12"></line>',
    external: '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" x2="21" y1="14" y2="3"></line>',
    diamond: '<polygon points="12 2 22 8.5 12 22 2 8.5 12 2"></polygon><line x1="2" y1="8.5" x2="22" y2="8.5"></line><line x1="12" y1="2" x2="7" y2="8.5"></line><line x1="12" y1="2" x2="17" y2="8.5"></line><line x1="7" y1="8.5" x2="12" y2="22"></line><line x1="17" y1="8.5" x2="12" y2="22"></line>',
    coins: '<circle cx="8" cy="8" r="6"></circle><path d="M18.09 10.37A6 6 0 1 1 10.34 18"></path><path d="M7 6h1v4"></path><path d="m16.71 13.88.7.71-2.82 2.82"></path>',
    ticket: '<path d="M2 9a3 3 0 0 1 0 6v2a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-2a3 3 0 0 1 0-6V7a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z"></path><path d="M13 5v2"></path><path d="M13 17v2"></path><path d="M13 11v2"></path>',
    flame: '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"></path>',
    hammer: '<path d="m15 12-8.373 8.373a1 1 0 1 1-3-3L12 9"></path><path d="m18 15 4-4"></path><path d="m21.5 11.5-1.914-1.914A2 2 0 0 1 19 8.172V7l-2.26-2.26a6 6 0 0 0-4.242-1.74H12L2 13l1 1 9-10h.414a2 2 0 0 1 1.414.586L16 6.828V8a2 2 0 0 1 .586 1.414L18.5 11.34"></path>',
    dices: '<rect width="12" height="12" x="2" y="10" rx="2" ry="2"></rect><path d="m17.92 14 3.5-3.5a2.41 2.41 0 0 0 0-3.41l-4.5-4.5a2.41 2.41 0 0 0-3.41 0L10 6.08"></path><path d="M6 16h.01"></path><path d="M10 16h.01"></path><path d="M10 12h.01"></path><path d="M6 12h.01"></path><path d="m14 4h.01"></path><path d="m16 8h.01"></path>',
    trophy: '<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"></path><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"></path><path d="M4 22h16"></path><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"></path><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"></path><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"></path>',
    lock: '<rect width="18" height="11" x="3" y="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path>',
    unlock: '<rect width="18" height="11" x="3" y="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 9.9-1"></path>',
    ban: '<circle cx="12" cy="12" r="10"></circle><path d="m4.9 4.9 14.2 14.2"></path>',
    userCheck: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><polyline points="16 11 18 13 22 9"></polyline>',
    userX: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><line x1="17" x2="22" y1="8" y2="13"></line><line x1="22" x2="17" y1="8" y2="13"></line>',
    shirt: '<path d="M20.38 3.46 16 2a4 4 0 0 1-8 0L3.62 3.46a2 2 0 0 0-1.34 2.23l.58 3.47a1 1 0 0 0 .99.84H6v10c0 1.1.9 2 2 2h8a2 2 0 0 0 2-2V10h2.15a1 1 0 0 0 .99-.84l.58-3.47a2 2 0 0 0-1.34-2.23z"></path>',
    pawPrint: '<circle cx="12" cy="5" r="2"></circle><circle cx="8" cy="8" r="2"></circle><circle cx="16" cy="8" r="2"></circle><circle cx="9" cy="14" r="2"></circle><circle cx="15" cy="14" r="2"></circle><path d="M12 18c-2 0-3-1-3-2 0-1.5 1.5-3 3-3s3 1.5 3 3c0 1-1 2-3 2Z"></path>',
    heart: '<path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"></path>',
    award: '<circle cx="12" cy="8" r="6"></circle><path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11"></path>',
    creditCard: '<rect width="20" height="14" x="2" y="5" rx="2"></rect><line x1="2" x2="22" y1="10" y2="10"></line>',
    map: '<polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"></polygon><line x1="9" x2="9" y1="3" y2="18"></line><line x1="15" x2="15" y1="6" y2="21"></line>',
    activity: '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>',
    clock: '<circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline>',
    filter: '<polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon>',
    eye: '<path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"></path><circle cx="12" cy="12" r="3"></circle>',
    eyeOff: '<path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"></path><path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"></path><path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"></path><line x1="2" x2="22" y1="2" y2="22"></line>',
    crosshair: '<circle cx="12" cy="12" r="10"></circle><line x1="22" x2="18" y1="12" y2="12"></line><line x1="6" x2="2" y1="12" y2="12"></line><line x1="12" x2="12" y1="6" y2="2"></line><line x1="12" x2="12" y1="22" y2="18"></line>',
    sliders: '<line x1="4" x2="4" y1="21" y2="14"></line><line x1="4" x2="4" y1="10" y2="3"></line><line x1="12" x2="12" y1="21" y2="12"></line><line x1="12" x2="12" y1="8" y2="3"></line><line x1="20" x2="20" y1="21" y2="16"></line><line x1="20" x2="20" y1="12" y2="3"></line><line x1="1" x2="7" y1="14" y2="14"></line><line x1="9" x2="15" y1="8" y2="8"></line><line x1="17" x2="23" y1="16" y2="16"></line>',
    chevronRight: '<polyline points="9 18 15 12 9 6"></polyline>',
    chevronDown: '<polyline points="6 9 12 15 18 9"></polyline>',
    moreHorizontal: '<circle cx="12" cy="12" r="1"></circle><circle cx="19" cy="12" r="1"></circle><circle cx="5" cy="12" r="1"></circle>'
  },

  /**
   * Render Lucide-style Outline SVG Icon
   */
  Icon(name, size = 14, className = '', color = 'currentColor') {
    const iconBody = UI.Icons[name] || UI.Icons.info;
    return `<svg class="ui-icon ${className}" viewBox="0 0 24 24" width="${size}" height="${size}" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display: inline-block; vertical-align: middle;">${iconBody}</svg>`;
  },

  /**
   * Reusable Glass Card Component
   */
  Card(title, subtitle = '', contentHtml = '', actionsHtml = '', footerHtml = '') {
    if (typeof title === 'object' && title !== null) {
      const opts = title;
      title = opts.title || '';
      subtitle = opts.subtitle || '';
      contentHtml = opts.content || opts.body || '';
      actionsHtml = opts.actions || '';
      footerHtml = opts.footer || '';
    }

    return `
      <div class="glass-card">
        <div class="glass-card-header">
          <div>
            <div class="glass-card-title">${title}</div>
            ${subtitle ? `<div class="glass-card-subtitle">${subtitle}</div>` : ''}
          </div>
          ${actionsHtml ? `<div class="glass-card-actions">${actionsHtml}</div>` : ''}
        </div>
        <div class="glass-card-body">
          ${contentHtml}
        </div>
        ${footerHtml ? `<div class="glass-card-footer">${footerHtml}</div>` : ''}
      </div>
    `;
  },

  /**
   * Stat / Metric Widget Card
   */
  StatCard(label, value, delta = '', icon = '', variant = 'cyan') {
    if (typeof label === 'object' && label !== null) {
      const opts = label;
      label = opts.label || '';
      value = opts.value || '0';
      delta = opts.delta || '';
      icon = opts.icon || '';
      variant = opts.variant || 'cyan';
    }

    return `
      <div class="stat-card">
        <div class="stat-label">
          <span>${label}</span>
          ${icon ? `<span style="opacity: 0.8; display: inline-flex; align-items: center;">${icon}</span>` : ''}
        </div>
        <div class="stat-value" style="color: var(--accent-${variant}, var(--text-primary));">
          ${value}
        </div>
        ${delta ? `<div class="stat-subtext">${delta}</div>` : ''}
      </div>
    `;
  },

  /**
   * Badges with Apple dark glass accents
   */
  Badge(text, variant = 'cyan', icon = '') {
    const validVariants = ['cyan', 'blue', 'emerald', 'amber', 'rose', 'violet', 'indigo', 'neutral'];
    const v = validVariants.includes(variant) ? variant : 'cyan';
    return `
      <span class="badge badge-${v}">
        ${icon ? `<span style="display: inline-flex; align-items: center; margin-right: 3px;">${icon}</span>` : ''}
        <span>${text}</span>
      </span>
    `.trim();
  },

  /**
   * Buttons with Apple Glass styling
   */
  Button(label, variant = 'secondary', onClickStr = '', icon = '', extraAttrs = '') {
    let size = '';
    let id = '';
    let disabled = false;

    if (typeof label === 'object' && label !== null) {
      const opts = label;
      label = opts.label || '';
      variant = opts.variant || 'secondary';
      onClickStr = opts.onClick || opts.onClickStr || '';
      icon = opts.icon || '';
      extraAttrs = opts.extraAttrs || '';
      size = opts.size ? `btn-${opts.size}` : '';
      id = opts.id ? `id="${opts.id}"` : '';
      disabled = !!opts.disabled;
    }

    const clickAttr = onClickStr ? `onclick="${onClickStr}"` : '';
    const disabledAttr = disabled ? 'disabled' : '';

    return `
      <button class="btn btn-${variant} ${size}" ${id} ${clickAttr} ${disabledAttr} ${extraAttrs}>
        ${icon ? `<span style="display: inline-flex; align-items: center;">${icon}</span>` : ''}
        <span>${label}</span>
      </button>
    `.trim();
  },

  /**
   * Form Input with optional label and hint
   */
  Input(optionsOrLabel, id = '', value = '', placeholder = '', type = 'text', onChangeStr = '', hint = '') {
    let label = '';
    let error = '';
    let disabled = false;
    let readonly = false;
    let extraAttrs = '';
    let oninput = '';

    if (typeof optionsOrLabel === 'object' && optionsOrLabel !== null) {
      const opts = optionsOrLabel;
      label = opts.label || '';
      id = opts.id || '';
      value = opts.value !== undefined ? opts.value : '';
      placeholder = opts.placeholder || '';
      type = opts.type || 'text';
      onChangeStr = opts.onChange || opts.onChangeStr || '';
      oninput = opts.onInput || opts.oninput || '';
      hint = opts.hint || '';
      error = opts.error || '';
      disabled = !!opts.disabled;
      readonly = !!opts.readonly;
      extraAttrs = opts.extraAttrs || '';
    } else {
      label = optionsOrLabel || '';
    }

    const changeAttr = onChangeStr ? `onchange="${onChangeStr}"` : '';
    const inputAttr = oninput ? `oninput="${oninput}"` : '';
    const idAttr = id ? `id="${id}" name="${id}"` : '';
    const disAttr = disabled ? 'disabled' : '';
    const readAttr = readonly ? 'readonly' : '';

    const inputHtml = `
      <input
        type="${type}"
        class="form-input"
        ${idAttr}
        value="${value}"
        placeholder="${placeholder}"
        ${changeAttr}
        ${inputAttr}
        ${disAttr}
        ${readAttr}
        ${extraAttrs}
      />
    `.trim();

    if (!label && !hint && !error) {
      return inputHtml;
    }

    return `
      <div class="form-group">
        ${label ? `<label class="form-label" ${id ? `for="${id}"` : ''}>${label}</label>` : ''}
        ${inputHtml}
        ${error ? `<div class="form-error">${error}</div>` : (hint ? `<div class="form-hint">${hint}</div>` : '')}
      </div>
    `;
  },

  /**
   * Form Select Dropdown
   */
  Select(optionsOrLabel, id = '', optionsList = [], selectedValue = '', onChangeStr = '', hint = '') {
    let label = '';
    let extraAttrs = '';

    if (typeof optionsOrLabel === 'object' && optionsOrLabel !== null && !Array.isArray(optionsOrLabel)) {
      const opts = optionsOrLabel;
      label = opts.label || '';
      id = opts.id || '';
      optionsList = opts.options || [];
      selectedValue = opts.selected !== undefined ? opts.selected : '';
      onChangeStr = opts.onChange || opts.onChangeStr || '';
      hint = opts.hint || '';
      extraAttrs = opts.extraAttrs || '';
    } else {
      label = optionsOrLabel || '';
    }

    const changeAttr = onChangeStr ? `onchange="${onChangeStr}"` : '';
    const idAttr = id ? `id="${id}" name="${id}"` : '';

    const optionsHtml = (optionsList || []).map(opt => {
      const val = typeof opt === 'object' ? opt.value : opt;
      const lbl = typeof opt === 'object' ? opt.label : opt;
      const isSel = String(val) === String(selectedValue) ? 'selected' : '';
      return `<option value="${val}" ${isSel}>${lbl}</option>`;
    }).join('');

    const selectHtml = `
      <select class="form-select" ${idAttr} ${changeAttr} ${extraAttrs}>
        ${optionsHtml}
      </select>
    `.trim();

    if (!label && !hint) {
      return selectHtml;
    }

    return `
      <div class="form-group">
        ${label ? `<label class="form-label" ${id ? `for="${id}"` : ''}>${label}</label>` : ''}
        ${selectHtml}
        ${hint ? `<div class="form-hint">${hint}</div>` : ''}
      </div>
    `;
  },

  /**
   * macOS Glass Toggle Switch
   */
  Toggle(id, label, checked = false, onChangeStr = '', description = '') {
    const changeAttr = onChangeStr ? `onchange="${onChangeStr}"` : '';
    const chkAttr = checked ? 'checked' : '';

    return `
      <div style="display: flex; align-items: center; justify-content: space-between; padding: 6px 0;">
        <div>
          <span style="font-size: 12.5px; font-weight: 500; color: var(--text-primary);">${label}</span>
          ${description ? `<div style="font-size: 11px; color: var(--text-tertiary); margin-top: 1px;">${description}</div>` : ''}
        </div>
        <label class="mac-toggle">
          <input type="checkbox" id="${id}" ${chkAttr} ${changeAttr}>
          <span class="mac-toggle-track">
            <span class="mac-toggle-thumb"></span>
          </span>
        </label>
      </div>
    `;
  },

  /**
   * Glass Table Component
   */
  Table(columns, rowsHtml, emptyMsg = 'No records found') {
    if (!rowsHtml || rowsHtml.trim() === '') {
      return UI.EmptyState('No Records', emptyMsg, UI.Icon('fileText', 32, '', 'var(--text-tertiary)'));
    }
    const ths = (columns || []).map(col => `<th>${col}</th>`).join('');
    return `
      <div class="glass-table-container">
        <table class="glass-table">
          <thead>
            <tr>${ths}</tr>
          </thead>
          <tbody>
            ${rowsHtml}
          </tbody>
        </table>
      </div>
    `;
  },

  /**
   * Empty State Box
   */
  EmptyState(title = 'No Data Available', message = 'There are no records to display.', icon = '', actionBtnHtml = '') {
    const renderedIcon = icon || UI.Icon('inbox', 36, '', 'var(--text-tertiary)');
    return `
      <div class="empty-state-box">
        <div class="empty-state-icon">${renderedIcon}</div>
        <div class="empty-state-title">${title}</div>
        <div class="empty-state-desc">${message}</div>
        ${actionBtnHtml ? `<div class="empty-state-action">${actionBtnHtml}</div>` : ''}
      </div>
    `;
  },

  /**
   * Unavailable State Box (Backend route gap)
   */
  UnavailableState(featureName, requiredEndpoint = '', notes = '') {
    return `
      <div class="unavailable-box">
        <div class="unavailable-icon">${UI.Icon('server', 32, '', 'var(--accent-cyan)')}</div>
        <div class="unavailable-title">${featureName}</div>
        <div class="unavailable-desc">
          This operational domain requires live backend endpoint support.
          ${requiredEndpoint ? `<br><span class="unavailable-endpoint">${requiredEndpoint}</span>` : ''}
          ${notes ? `<span class="unavailable-notes">${notes}</span>` : ''}
        </div>
      </div>
    `;
  },

  /**
   * Loading Activity Spinner
   */
  Loading(text = 'Loading telemetry...', subtext = '') {
    return `
      <div class="loading-container">
        <div class="loading-spinner"></div>
        <div class="loading-text">${text}</div>
        ${subtext ? `<div class="loading-subtext">${subtext}</div>` : ''}
      </div>
    `;
  },

  /**
   * Toast Notifications Framework (with Lucide SVG outlines)
   */
  Toast(message, type = 'info', duration = 3200) {
    if (typeof document === 'undefined') return;

    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    let iconHtml = UI.Icon('info', 16, '', 'var(--accent-cyan)');
    if (type === 'success') iconHtml = UI.Icon('checkCircle', 16, '', 'var(--accent-emerald)');
    else if (type === 'error') iconHtml = UI.Icon('xCircle', 16, '', 'var(--accent-rose)');
    else if (type === 'warning') iconHtml = UI.Icon('alertTriangle', 16, '', 'var(--accent-amber)');

    toast.innerHTML = `
      <span style="display: inline-flex; align-items: center;">${iconHtml}</span>
      <span style="flex: 1; line-height: 1.4;">${message}</span>
    `;

    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px) scale(0.96)';
      toast.style.transition = 'all 0.22s cubic-bezier(0.16, 1, 0.3, 1)';
      setTimeout(() => toast.remove(), 220);
    }, duration);
  },

  /**
   * Global Modal Dialog
   */
  Modal(title, bodyHtml, footerButtonsHtml = '', options = {}) {
    if (typeof document === 'undefined') return;

    UI.CloseModal();

    const overlay = document.createElement('div');
    overlay.id = 'global-modal-overlay';
    overlay.className = 'modal-overlay';

    overlay.innerHTML = `
      <div class="modal-card" style="${options.maxWidth ? `max-width: ${options.maxWidth};` : ''}">
        <div class="modal-header">
          <h3 class="modal-title">${title}</h3>
          <button class="modal-close-btn" onclick="UI.CloseModal()" title="Close dialog">
            ${UI.Icon('x', 14, '', 'currentColor')}
          </button>
        </div>
        <div class="modal-body">
          ${bodyHtml}
        </div>
        ${footerButtonsHtml ? `
          <div class="modal-footer">
            ${footerButtonsHtml}
          </div>
        ` : ''}
      </div>
    `;

    if (options.backdropClose !== false) {
      overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
          UI.CloseModal();
        }
      });
    }

    const onKeyDown = (e) => {
      if (e.key === 'Escape') {
        UI.CloseModal();
        document.removeEventListener('keydown', onKeyDown);
      }
    };
    document.addEventListener('keydown', onKeyDown);

    document.body.appendChild(overlay);
  },

  /**
   * Close Global Modal
   */
  CloseModal() {
    if (typeof document === 'undefined') return;
    const existing = document.getElementById('global-modal-overlay');
    if (existing) existing.remove();
  },

  /**
   * Apple Confirmation Dialog
   */
  Confirm(title, message, onConfirmCallback, isDestructive = false, options = {}) {
    const confirmLabel = options.confirmLabel || (isDestructive ? 'Proceed / Delete' : 'Confirm');
    const cancelLabel = options.cancelLabel || 'Cancel';

    const footer = `
      <button class="btn ${isDestructive ? 'btn-danger' : 'btn-primary'}" id="modal-confirm-btn">
        ${confirmLabel}
      </button>
      <button class="btn btn-secondary" onclick="UI.CloseModal()">${cancelLabel}</button>
    `;

    UI.Modal(
      title,
      `<p style="color: var(--text-secondary); line-height: 1.6;">${message}</p>`,
      footer,
      options
    );

    const btn = document.getElementById('modal-confirm-btn');
    if (btn) {
      btn.onclick = () => {
        UI.CloseModal();
        if (typeof onConfirmCallback === 'function') {
          try {
            onConfirmCallback();
          } catch (e) {
            console.error('Confirm callback error:', e);
          }
        }
      };
    }
  },

  /**
   * Standardized Page Header with Title, Icon, Subtitle & Action Bar
   */
  PageHeader(title, subtitle = '', actionsHtml = '', iconName = '') {
    const iconHtml = iconName ? UI.Icon(iconName, 20, '', 'var(--accent-cyan)') : '';
    return `
      <div class="page-header">
        <div class="page-title-group">
          <div class="page-title">
            ${iconHtml ? `<span style="display: inline-flex; align-items: center;">${iconHtml}</span>` : ''}
            <span>${title}</span>
          </div>
          ${subtitle ? `<div class="page-subtitle">${subtitle}</div>` : ''}
        </div>
        ${actionsHtml ? `<div class="page-actions">${actionsHtml}</div>` : ''}
      </div>
    `.trim();
  },

  /**
   * Apple Segmented Control Bar
   */
  SegmentedControl(items = [], activeIndex = 0, onChangeCallbackStr = '') {
    const buttonsHtml = (items || []).map((item, idx) => {
      const val = typeof item === 'object' ? item.value : item;
      const lbl = typeof item === 'object' ? item.label : item;
      const icon = typeof item === 'object' && item.icon ? UI.Icon(item.icon, 13, '', 'currentColor') : '';
      const isActive = idx === activeIndex ? 'active' : '';
      const clickAction = onChangeCallbackStr ? `onclick="${onChangeCallbackStr}('${val}', ${idx})"` : '';
      return `
        <button class="segmented-btn ${isActive}" ${clickAction} data-value="${val}">
          ${icon ? `<span style="display: inline-flex; align-items: center;">${icon}</span>` : ''}
          <span>${lbl}</span>
        </button>
      `;
    }).join('');

    return `<div class="segmented-control">${buttonsHtml}</div>`;
  },

  /**
   * Currency Chip (Standardized Luxury Glass Token Indicator)
   */
  CurrencyChip(type = 'diamond', amount = 0, delta = '') {
    const formattedAmount = Number(amount || 0).toLocaleString();
    let iconName = 'diamond';
    let chipClass = 'diamond';

    if (type === 'gold' || type === 'coins') {
      iconName = 'coins';
      chipClass = 'gold';
    } else if (type === 'stone') {
      iconName = 'sparkles';
      chipClass = 'stone';
    } else if (type === 'badge' || type === 'badges') {
      iconName = 'award';
      chipClass = 'badge';
    }

    return `
      <div class="currency-chip ${chipClass}">
        <span style="display: inline-flex; align-items: center;">${UI.Icon(iconName, 13, '', 'currentColor')}</span>
        <span>${formattedAmount}</span>
        ${delta ? `<span style="font-size: 10px; opacity: 0.8;">(${delta})</span>` : ''}
      </div>
    `.trim();
  },

  /**
   * Status Activity Indicator Dot
   */
  StatusDot(status = 'active', pulse = false) {
    const valid = ['active', 'inactive', 'warning', 'danger'];
    const s = valid.includes(status) ? status : 'active';
    return `<span class="status-dot ${s}"></span>`;
  },

  /**
   * Slide-Out Side Inspection Drawer
   */
  Drawer(title, bodyHtml, footerHtml = '', options = {}) {
    if (typeof document === 'undefined') return;

    UI.CloseDrawer();

    const overlay = document.createElement('div');
    overlay.id = 'global-drawer-overlay';
    overlay.className = 'drawer-overlay';

    overlay.innerHTML = `
      <div class="drawer-panel" style="${options.width ? `width: ${options.width};` : ''}">
        <div class="drawer-header">
          <h3 class="drawer-title">${title}</h3>
          <button class="drawer-close-btn" onclick="UI.CloseDrawer()" title="Close panel">
            ${UI.Icon('x', 14, '', 'currentColor')}
          </button>
        </div>
        <div class="drawer-body">
          ${bodyHtml}
        </div>
        ${footerHtml ? `
          <div class="drawer-footer">
            ${footerHtml}
          </div>
        ` : ''}
      </div>
    `;

    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        UI.CloseDrawer();
      }
    });

    const onKeyDown = (e) => {
      if (e.key === 'Escape') {
        UI.CloseDrawer();
        document.removeEventListener('keydown', onKeyDown);
      }
    };
    document.addEventListener('keydown', onKeyDown);

    document.body.appendChild(overlay);
  },

  /**
   * Close Slide-Out Drawer
   */
  CloseDrawer() {
    if (typeof document === 'undefined') return;
    const existing = document.getElementById('global-drawer-overlay');
    if (existing) existing.remove();
  }
};

if (typeof window !== 'undefined') {
  window.UI = UI;
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = UI;
}
