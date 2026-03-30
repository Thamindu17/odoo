/**
 * AsthraAI ChatBot - A lightweight, embeddable chat UI library
 * Usage: new SimpleChatBot({ apiUrl: 'http://127.0.0.1:9000' })
 * 
 * Features: Text, Tables, Charts (Plotly), Analytics, Reports, CSV Export
 */
class SimpleChatBot {
  constructor(config = {}) {
    this.config = {
      apiUrl: config.apiUrl || 'http://127.0.0.1:9000',
      primaryColor: config.primaryColor || '#007bff',
      botName: config.botName || 'Assistant',
      placeholder: config.placeholder || 'Type a message...',
      currentUserName: config.currentUserName || '',
      welcomeMessage: config.welcomeMessage || '',
      position: config.position || 'bottom-right', // bottom-right, bottom-left
      ...config
    };
    
    this.isOpen = false;
    this.conversationHistory = [];
    this.vizCounter = 0;
    this.recognition = null;
    this.isListening = false;
    this.init();
  }

  init() {
    this.injectStyles();
    this.createChatWidget();
    this.attachEventListeners();
    this.loadPlotly();
    this.initVoiceRecognition();
  }

  loadPlotly() {
    if (!window.Plotly) {
      const s = document.createElement('script');
      s.src = 'https://cdn.plot.ly/plotly-2.35.2.min.js';
      s.async = true;
      document.head.appendChild(s);
    }
  }

  injectStyles() {
    const style = document.createElement('style');
    style.textContent = `
      .chatbot-container {
        position: fixed;
        ${this.config.position.includes('right') ? 'right: 20px;' : 'left: 20px;'}
        bottom: 20px;
        z-index: 9999;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      }

      .chatbot-button {
        width: 60px;
        height: 60px;
        border-radius: 50%;
        background: ${this.config.primaryColor};
        border: none;
        cursor: pointer;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        display: flex;
        align-items: center;
        justify-content: center;
        transition: transform 0.2s, box-shadow 0.2s;
      }

      .chatbot-button:hover {
        transform: scale(1.05);
        box-shadow: 0 6px 16px rgba(0,0,0,0.2);
      }

      .chatbot-button svg {
        width: 28px;
        height: 28px;
        fill: white;
      }

      .chatbot-window {
        position: absolute;
        bottom: 80px;
        ${this.config.position.includes('right') ? 'right: 0;' : 'left: 0;'}
        width: 420px;
        height: 620px;
        max-height: 80vh;
        background: white;
        border-radius: 12px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.12);
        display: none;
        flex-direction: column;
        overflow: hidden;
      }

      .chatbot-window.open {
        display: flex;
        animation: slideUp 0.3s ease-out;
      }

      @keyframes slideUp {
        from {
          opacity: 0;
          transform: translateY(20px);
        }
        to {
          opacity: 1;
          transform: translateY(0);
        }
      }

      .chatbot-header {
        background: ${this.config.primaryColor};
        color: white;
        padding: 16px 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
      }

      .chatbot-header h3 {
        margin: 0;
        font-size: 18px;
        font-weight: 600;
      }

      .chatbot-close {
        background: none;
        border: none;
        color: white;
        cursor: pointer;
        font-size: 24px;
        padding: 0;
        width: 30px;
        height: 30px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 4px;
        transition: background 0.2s;
      }

      .chatbot-close:hover {
        background: rgba(255,255,255,0.1);
      }

      .chatbot-messages {
        flex: 1;
        overflow-y: auto;
        padding: 20px;
        background: #f8f9fa;
      }

      .chatbot-message {
        margin-bottom: 16px;
        display: flex;
        gap: 8px;
      }

      .chatbot-message.user {
        flex-direction: row-reverse;
      }

      .chatbot-message-content {
        max-width: 75%;
        padding: 10px 14px;
        border-radius: 12px;
        word-wrap: break-word;
        line-height: 1.4;
      }

      .chatbot-message.bot .chatbot-message-content {
        background: white;
        color: #333;
        border-bottom-left-radius: 4px;
      }

      .chatbot-message.user .chatbot-message-content {
        background: ${this.config.primaryColor};
        color: white;
        border-bottom-right-radius: 4px;
      }

      /* Rich content: wider for bot messages with data */
      .chatbot-message.bot .chatbot-rich-content {
        max-width: 95%;
        padding: 14px;
      }

      .chatbot-input-container {
        padding: 16px;
        background: white;
        border-top: 1px solid #e0e0e0;
        display: flex;
        gap: 8px;
      }

      .chatbot-input {
        flex: 1;
        padding: 10px 14px;
        border: 1px solid #ddd;
        border-radius: 20px;
        font-size: 14px;
        outline: none;
        transition: border-color 0.2s;
      }

      .chatbot-input:focus {
        border-color: ${this.config.primaryColor};
      }

      .chatbot-send {
        background: ${this.config.primaryColor};
        color: white;
        border: none;
        width: 40px;
        height: 40px;
        border-radius: 50%;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: opacity 0.2s;
      }

      .chatbot-voice {
        background: white;
        color: ${this.config.primaryColor};
        border: 2px solid ${this.config.primaryColor};
        width: 40px;
        height: 40px;
        border-radius: 50%;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.2s;
      }

      .chatbot-voice:hover {
        background: ${this.config.primaryColor};
        color: white;
      }

      .chatbot-voice.listening {
        background: #dc3545;
        border-color: #dc3545;
        color: white;
        animation: pulse 1.5s infinite;
      }

      @keyframes pulse {
        0%, 100% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.05); opacity: 0.9; }
      }

      .chatbot-voice svg {
        width: 20px;
        height: 20px;
      }

      .chatbot-send:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }

      .chatbot-send:not(:disabled):hover {
        opacity: 0.9;
      }

      .chatbot-typing {
        display: flex;
        gap: 4px;
        padding: 10px 14px;
        background: white;
        border-radius: 12px;
        width: fit-content;
      }

      .chatbot-typing span {
        width: 8px;
        height: 8px;
        background: #999;
        border-radius: 50%;
        animation: typing 1.4s infinite;
      }

      .chatbot-typing span:nth-child(2) {
        animation-delay: 0.2s;
      }

      .chatbot-typing span:nth-child(3) {
        animation-delay: 0.4s;
      }

      @keyframes typing {
        0%, 60%, 100% {
          transform: translateY(0);
          opacity: 0.7;
        }
        30% {
          transform: translateY(-10px);
          opacity: 1;
        }
      }

      /* ===== Rich Content Styles ===== */

      .cb-section-label {
        font-size: 12px;
        font-weight: 700;
        color: #555;
        margin: 14px 0 6px 0;
        text-transform: uppercase;
        letter-spacing: 0.4px;
      }

      .cb-agent-badge {
        display: inline-block;
        padding: 3px 8px;
        background: #e8f5e9;
        color: #2e7d32;
        border-radius: 10px;
        font-size: 11px;
        font-weight: 600;
        margin: 2px;
      }

      .cb-table-wrap {
        overflow-x: auto;
        margin: 10px 0;
      }

      .cb-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 12px;
        background: #fff;
        border-radius: 6px;
        overflow: hidden;
      }

      .cb-table th {
        background: ${this.config.primaryColor};
        color: white;
        padding: 8px 10px;
        text-align: left;
        font-weight: 600;
        white-space: nowrap;
      }

      .cb-table td {
        padding: 7px 10px;
        border-bottom: 1px solid #f0f0f0;
        white-space: nowrap;
      }

      .cb-table tr:last-child td {
        border-bottom: none;
      }

      .cb-table tr:hover td {
        background: #f5f8ff;
      }

      .cb-viz-box {
        margin: 10px 0;
        background: #fff;
        border-radius: 8px;
        padding: 8px;
        min-height: 250px;
      }

      .cb-analytics-box {
        margin: 10px 0;
        padding: 10px 12px;
        background: #f3e5f5;
        border-radius: 8px;
        border-left: 3px solid #9C27B0;
        font-size: 13px;
        line-height: 1.6;
        white-space: pre-wrap;
      }

      .cb-report-box {
        margin: 10px 0;
        padding: 12px;
        background: #e3f2fd;
        border-radius: 8px;
        border-left: 3px solid #2196F3;
      }

      .cb-report-title {
        font-weight: 600;
        color: #1565c0;
        margin-bottom: 8px;
        font-size: 13px;
      }

      .cb-btn {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 7px 14px;
        border: none;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 600;
        cursor: pointer;
        color: white;
        transition: opacity 0.2s;
      }

      .cb-btn:hover {
        opacity: 0.85;
      }

      .cb-btn-blue {
        background: #2196F3;
      }

      .cb-btn-green {
        background: #4CAF50;
      }

      .cb-sql-toggle {
        font-size: 12px;
        color: #888;
        cursor: pointer;
        margin: 6px 0;
        padding: 6px 10px;
        background: #f5f5f5;
        border-radius: 4px;
        user-select: none;
      }

      .cb-sql-toggle:hover {
        background: #eee;
      }

      .cb-sql-code {
        display: none;
        background: #2d2d2d;
        color: #f8f8f2;
        padding: 10px 12px;
        border-radius: 6px;
        font-family: 'Courier New', monospace;
        font-size: 11px;
        overflow-x: auto;
        margin-top: 6px;
        white-space: pre-wrap;
        word-break: break-all;
      }

      .cb-sql-code.open {
        display: block;
      }

      @media (max-width: 480px) {
        .chatbot-window {
          width: calc(100vw - 40px);
          height: calc(100vh - 100px);
        }
      }
    `;
    document.head.appendChild(style);
  }

  createChatWidget() {
    const container = document.createElement('div');
    container.className = 'chatbot-container';
    container.innerHTML = `
      <button class="chatbot-button" aria-label="Open chat">
        <svg viewBox="0 0 24 24">
          <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/>
        </svg>
      </button>
      <div class="chatbot-window">
        <div class="chatbot-header">
          <h3>${this.config.botName}</h3>
          <button class="chatbot-close" aria-label="Close chat">&times;</button>
        </div>
        <div class="chatbot-messages"></div>
        <div class="chatbot-input-container">
          <button class="chatbot-voice" aria-label="Voice input" title="Click to speak">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
              <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
            </svg>
          </button>
          <input type="text" class="chatbot-input" placeholder="${this.config.placeholder}" />
          <button class="chatbot-send" aria-label="Send message">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="white">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
            </svg>
          </button>
        </div>
      </div>
    `;
    
    document.body.appendChild(container);
    this.elements = {
      container,
      button: container.querySelector('.chatbot-button'),
      window: container.querySelector('.chatbot-window'),
      close: container.querySelector('.chatbot-close'),
      messages: container.querySelector('.chatbot-messages'),
      input: container.querySelector('.chatbot-input'),
      send: container.querySelector('.chatbot-send'),
      voice: container.querySelector('.chatbot-voice')
    };
  }

  attachEventListeners() {
    this.elements.button.addEventListener('click', () => this.toggleChat());
    this.elements.close.addEventListener('click', () => this.toggleChat());
    this.elements.send.addEventListener('click', () => this.sendMessage());
    this.elements.voice.addEventListener('click', () => this.toggleVoiceInput());
    this.elements.input.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') this.sendMessage();
    });
  }

  toggleChat() {
    this.isOpen = !this.isOpen;
    this.elements.window.classList.toggle('open', this.isOpen);
    
    if (this.isOpen && this.elements.messages.children.length === 0) {
      this.addBotMessage(this.getWelcomeMessage());
    }
    
    if (this.isOpen) {
      this.elements.input.focus();
    }
  }

  getWelcomeMessage() {
    const userName = (this.config.currentUserName || '').trim();
    if (userName) {
      return `Hi ${userName}! How can I help you today?`;
    }
    if (this.config.welcomeMessage) {
      return this.config.welcomeMessage;
    }
    return 'Hi! How can I help you today?';
  }

  // ===== Simple text message (user + fallback) =====
  addMessage(content, isUser = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `chatbot-message ${isUser ? 'user' : 'bot'}`;
    messageDiv.innerHTML = `<div class="chatbot-message-content">${this.escapeHtml(content)}</div>`;
    this.elements.messages.appendChild(messageDiv);
    this.scrollToBottom();
  }

  addBotMessage(content) {
    this.addMessage(content, false);
  }

  addUserMessage(content) {
    this.addMessage(content, true);
  }

  // ===== Rich bot message with all features =====
  addRichBotMessage(data) {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'chatbot-message bot';

    const content = document.createElement('div');
    content.className = 'chatbot-message-content chatbot-rich-content';

    // 1. Text answer (with markdown support)
    const answer = data.answer || data.response || '';
    if (answer) {
      const textDiv = document.createElement('div');
      textDiv.style.cssText = 'line-height:1.55; margin-bottom:8px;';
      textDiv.innerHTML = this.renderMarkdown(answer);
      content.appendChild(textDiv);
    }

    // 2. Agent badges
    const agents = data.agents_used || [];
    if (agents.length > 0) {
      const badgeRow = document.createElement('div');
      badgeRow.style.margin = '8px 0';
      agents.forEach(a => {
        const b = document.createElement('span');
        b.className = 'cb-agent-badge';
        b.textContent = a.replace('_agent', '');
        badgeRow.appendChild(b);
      });
      content.appendChild(badgeRow);
    }

    msgDiv.appendChild(content);
    this.elements.messages.appendChild(msgDiv);

    // 3. Visualizations
    if (data.visualizations) {
      this._renderViz(data.visualizations, content);
    }

    // 4. Analytics
    if (data.analytics) {
      const label = document.createElement('div');
      label.className = 'cb-section-label';
      label.textContent = '📈 Analytics Insights';
      content.appendChild(label);

      const box = document.createElement('div');
      box.className = 'cb-analytics-box';
      box.innerHTML = this.renderMarkdown(data.analytics);
      content.appendChild(box);
    }

    // 5. Data tables (SQL references)
    if (data.references) {
      data.references.forEach(ref => {
        if (ref.type === 'sql' && ref.data && ref.data.length > 0) {
          const label = document.createElement('div');
          label.className = 'cb-section-label';
          label.textContent = `📊 Data Results (${ref.row_count} rows)`;
          content.appendChild(label);

          content.appendChild(this._buildTable(ref.data));
          content.appendChild(this._buildCSVBtn(ref.data));

          // SQL query toggle
          if (ref.query) {
            const uid = 'sql_' + (++this.vizCounter);
            const toggle = document.createElement('div');
            toggle.className = 'cb-sql-toggle';
            toggle.textContent = '🔍 View SQL Query';
            toggle.onclick = () => {
              const codeEl = document.getElementById(uid);
              codeEl.classList.toggle('open');
              toggle.textContent = codeEl.classList.contains('open') ? '🔍 Hide SQL Query' : '🔍 View SQL Query';
            };
            content.appendChild(toggle);

            const code = document.createElement('pre');
            code.className = 'cb-sql-code';
            code.id = uid;
            code.textContent = ref.query;
            content.appendChild(code);
          }
        }
      });
    }

    // 5b. CRM list records from chatbot_backend/main.py ChatResponse.details.records
    const records = data && data.details && Array.isArray(data.details.records) ? data.details.records : [];
    if (records.length > 0) {
      const label = document.createElement('div');
      label.className = 'cb-section-label';
      label.textContent = `📋 Lead Results (${records.length} rows)`;
      content.appendChild(label);

      content.appendChild(this._buildTable(records));
      content.appendChild(this._buildCSVBtn(records));
    }

    // 6. Report download
    if (data.report && data.report.file) {
      this._renderReport(data.report, content);
    }

    this.scrollToBottom();
  }

  // ===== Build HTML table from array of objects =====
  _buildTable(rows) {
    if (!rows || rows.length === 0) return document.createElement('span');

    const cols = Object.keys(rows[0]);
    const wrap = document.createElement('div');
    wrap.className = 'cb-table-wrap';

    const table = document.createElement('table');
    table.className = 'cb-table';

    // thead
    const thead = document.createElement('thead');
    const headRow = document.createElement('tr');
    cols.forEach(c => {
      const th = document.createElement('th');
      th.textContent = c;
      headRow.appendChild(th);
    });
    thead.appendChild(headRow);
    table.appendChild(thead);

    // tbody (max 50 rows in chat)
    const tbody = document.createElement('tbody');
    const display = rows.slice(0, 50);
    display.forEach(row => {
      const tr = document.createElement('tr');
      cols.forEach(c => {
        const td = document.createElement('td');
        td.textContent = row[c] !== null && row[c] !== undefined ? row[c] : '-';
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    wrap.appendChild(table);

    if (rows.length > 50) {
      const note = document.createElement('div');
      note.style.cssText = 'font-size:11px; color:#888; margin-top:4px; text-align:center;';
      note.textContent = `Showing 50 of ${rows.length} rows. Download CSV for all data.`;
      wrap.appendChild(note);
    }

    return wrap;
  }

  // ===== CSV download button =====
  _buildCSVBtn(rows) {
    const btn = document.createElement('button');
    btn.className = 'cb-btn cb-btn-green';
    btn.style.marginTop = '6px';
    btn.innerHTML = '⬇ Download CSV';
    btn.onclick = () => {
      const cols = Object.keys(rows[0]);
      let csv = cols.join(',') + '\n';
      rows.forEach(r => {
        csv += cols.map(c => {
          let v = r[c] === null || r[c] === undefined ? '' : String(r[c]);
          v = v.replace(/"/g, '""');
          return v.includes(',') || v.includes('\n') || v.includes('"') ? `"${v}"` : v;
        }).join(',') + '\n';
      });
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `data_${Date.now()}.csv`;
      a.click();
      URL.revokeObjectURL(a.href);
    };
    return btn;
  }

  // ===== Render Plotly visualizations =====
  _renderViz(visualizations, container) {
    console.log('[VIZ] _renderViz called with:', typeof visualizations, visualizations);

    const label = document.createElement('div');
    label.className = 'cb-section-label';
    label.textContent = '📊 Visualizations';
    container.appendChild(label);

    const vizArr = Array.isArray(visualizations) ? visualizations : [visualizations];
    console.log('[VIZ] vizArr length:', vizArr.length);

    const tryRender = (attempts) => {
      console.log('[VIZ] tryRender attempt', attempts, 'Plotly loaded:', !!window.Plotly);
      if (!window.Plotly) {
        if (attempts < 20) {
          setTimeout(() => tryRender(attempts + 1), 300);
        } else {
          const err = document.createElement('div');
          err.style.cssText = 'color:#e74c3c; font-size:12px; padding:10px;';
          err.textContent = '⚠️ Could not load chart library. Please refresh the page.';
          container.appendChild(err);
        }
        return;
      }

      vizArr.forEach((viz, i) => {
        console.log(`[VIZ] Processing viz ${i}:`, viz ? Object.keys(viz) : 'null/undefined');
        if (!viz) return;

        const box = document.createElement('div');
        box.className = 'cb-viz-box';
        const uid = 'cbviz_' + (++this.vizCounter) + '_' + i;
        box.id = uid;
        box.style.minHeight = '300px';
        box.style.width = '100%';
        container.appendChild(box);

        try {
          if (viz.json) {
            console.log(`[VIZ] viz.json type: ${typeof viz.json}, length: ${typeof viz.json === 'string' ? viz.json.length : 'N/A'}`);
            const plotData = typeof viz.json === 'string' ? JSON.parse(viz.json) : viz.json;
            console.log('[VIZ] plotData keys:', Object.keys(plotData));
            console.log('[VIZ] traces:', plotData.data ? plotData.data.length : 0);
            if (plotData.data && plotData.data[0]) {
              const t0 = plotData.data[0];
              console.log('[VIZ] trace0 type:', t0.type, 'keys:', Object.keys(t0));
            }

            if (plotData.data && Array.isArray(plotData.data)) {
              // Make layout fit in chat
              const layout = plotData.layout || {};
              layout.autosize = true;
              layout.margin = layout.margin || { l: 40, r: 20, t: 30, b: 40 };
              layout.height = layout.height || 280;

              // Use DOM element directly (avoids getElementById issues)
              console.log('[VIZ] Calling Plotly.newPlot, box in DOM:', box.isConnected);

              window.Plotly.newPlot(box, plotData.data, layout, {
                responsive: true,
                displayModeBar: true,
                displaylogo: false,
                modeBarButtonsToRemove: ['lasso2d', 'select2d']
              }).then(() => {
                console.log('[VIZ] Plotly.newPlot SUCCESS for', uid);
                // Caption after chart renders
                const cap = document.createElement('div');
                cap.style.cssText = 'font-size:11px; color:#888; text-align:center; margin-top:4px;';
                cap.textContent = `Chart ${i + 1}: ${(viz.type || 'chart')} chart`;
                box.appendChild(cap);
                this.scrollToBottom();
              }).catch(err => {
                console.error('[VIZ] Plotly.newPlot FAILED:', err);
                // Fallback: render chart in an iframe using viz.html
                if (viz.html) {
                  console.log('[VIZ] Falling back to iframe HTML render');
                  const iframe = document.createElement('iframe');
                  iframe.style.cssText = 'width:100%; height:350px; border:none; border-radius:8px;';
                  iframe.srcdoc = '<!DOCTYPE html><html><head><meta charset="utf-8"></head><body style="margin:0">' + viz.html + '</body></html>';
                  box.innerHTML = '';
                  box.appendChild(iframe);
                } else {
                  box.innerHTML = '<div style="color:#e74c3c; font-size:12px; padding:10px;">' +
                    '\u26A0\uFE0F Chart render error: ' + (err.message || err) + '</div>';
                }
              });
            } else {
              throw new Error('Invalid Plotly data');
            }
          } else if (viz.html) {
            console.log('[VIZ] Using HTML render for viz', i);
            box.innerHTML = viz.html;
          } else if (viz.image) {
            console.log('[VIZ] Using image render for viz', i);
            box.innerHTML = '<img src="data:image/png;base64,' + viz.image +
              '" style="max-width:100%; height:auto; border-radius:6px;" />';
          } else {
            console.log('[VIZ] No json/html/image in viz', i, 'keys:', Object.keys(viz));
          }
        } catch (e) {
          console.error('[VIZ] Exception in viz rendering:', e);
          // Fallback: render chart in an iframe using viz.html
          if (viz && viz.html) {
            const iframe = document.createElement('iframe');
            iframe.style.cssText = 'width:100%; height:350px; border:none; border-radius:8px;';
            iframe.srcdoc = '<!DOCTYPE html><html><head><meta charset="utf-8"></head><body style="margin:0">' + viz.html + '</body></html>';
            box.innerHTML = '';
            box.appendChild(iframe);
          } else {
            box.innerHTML = '<div style="color:#e74c3c; font-size:12px; padding:10px;">' +
              '\u26A0\uFE0F Chart error: ' + e.message + '</div>';
          }
        }
      });

      this.scrollToBottom();
    };

    tryRender(0);
  }

  // ===== Report download =====
  _renderReport(report, container) {
    const label = document.createElement('div');
    label.className = 'cb-section-label';
    label.textContent = '📄 Generated Report';
    container.appendChild(label);

    const box = document.createElement('div');
    box.className = 'cb-report-box';

    const title = document.createElement('div');
    title.className = 'cb-report-title';
    title.textContent = (report.structure && report.structure.report_title) || 'Report Ready';
    box.appendChild(title);

    const btn = document.createElement('button');
    btn.className = 'cb-btn cb-btn-blue';
    btn.innerHTML = `⬇ Download ${report.filename || 'report'}`;
    btn.onclick = () => {
      try {
        const bytes = atob(report.file);
        const arr = new Uint8Array(bytes.length);
        for (let i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i);
        const blob = new Blob([arr], { type: report.mime_type || 'application/pdf' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = report.filename || 'report.pdf';
        a.click();
        URL.revokeObjectURL(a.href);
      } catch (e) {
        alert('Error downloading report: ' + e.message);
      }
    };
    box.appendChild(btn);
    container.appendChild(box);
  }

  showTyping() {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'chatbot-message bot';
    typingDiv.innerHTML = `
      <div class="chatbot-typing">
        <span></span><span></span><span></span>
      </div>
    `;
    typingDiv.id = 'typing-indicator';
    this.elements.messages.appendChild(typingDiv);
    this.scrollToBottom();
  }

  hideTyping() {
    const typing = document.getElementById('typing-indicator');
    if (typing) typing.remove();
  }

  scrollToBottom() {
    this.elements.messages.scrollTop = this.elements.messages.scrollHeight;
  }

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // ===== Simple Markdown renderer =====
  renderMarkdown(text) {
    if (!text) return '';
    
    // Escape HTML first
    let html = this.escapeHtml(text);
    
    // Bold: **text** (must be done before single * for italic)
    html = html.replace(/\*\*([^*]+?)\*\*/g, '<strong>$1</strong>');
    
    // Italic: *text* (after bold to avoid conflicts)
    html = html.replace(/\*([^*]+?)\*/g, '<em>$1</em>');
    
    // Code: `code`
    html = html.replace(/`([^`]+?)`/g, '<code style="background:#f0f0f0; padding:2px 4px; border-radius:3px; font-family:monospace; font-size:0.9em;">$1</code>');
    
    // Line breaks
    html = html.replace(/\n/g, '<br>');
    
    return html;
  }

  async sendMessage() {
    const message = this.elements.input.value.trim();
    if (!message) return;

    this.addUserMessage(message);
    this.elements.input.value = '';
    this.elements.send.disabled = true;
    this.showTyping();

    // Track conversation
    this.conversationHistory.push({ role: 'user', content: message });

    try {
      // Call backend chat endpoint
      const response = await fetch(`${this.config.apiUrl}/chat/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: message
        })
      });

      if (!response.ok) {
        let detail = `HTTP ${response.status}`;
        try {
          const errData = await response.json();
          if (errData && errData.detail) {
            detail = errData.detail;
          }
        } catch (_parseErr) {
          // Keep fallback HTTP status when error body is not JSON.
        }
        throw new Error(detail);
      }

      const data = await response.json();
      this.hideTyping();

      // Track assistant response
      this.conversationHistory.push({ role: 'assistant', content: data.response || data.answer || '' });

      // Check if response has any rich content
      const hasRich = data.visualizations || data.analytics || data.report ||
        (data.references && data.references.some(r => r.type === 'sql' && r.data && r.data.length > 0)) ||
        (data.details && Array.isArray(data.details.records) && data.details.records.length > 0);

      console.log('Response data:', { hasViz: !!data.visualizations, hasAnalytics: !!data.analytics, hasReport: !!data.report });

      if (hasRich) {
        this.addRichBotMessage(data);
      } else {
        // Simple text-only response
        this.addBotMessage(data.answer || data.response || 'No response');
      }

    } catch (error) {
      this.hideTyping();
      const errMsg = error && error.message ? error.message : 'Unknown error';
      this.addBotMessage(`Sorry, I encountered an error: ${errMsg}`);
      console.error('Chat error:', error);
    } finally {
      this.elements.send.disabled = false;
      this.elements.input.focus();
    }
  }

  // ===== Voice Recognition Methods =====
  initVoiceRecognition() {
    // Check browser support
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
      console.warn('Speech recognition not supported in this browser');
      // Hide voice button if not supported
      if (this.elements.voice) {
        this.elements.voice.style.display = 'none';
      }
      return;
    }

    this.recognition = new SpeechRecognition();
    this.recognition.continuous = false;
    this.recognition.interimResults = false; // Changed to false for better reliability
    this.recognition.lang = 'en-US'; // Default language
    this.recognition.maxAlternatives = 1;

    this.recognition.onstart = () => {
      console.log('Voice recognition started');
      this.isListening = true;
      this.elements.voice.classList.add('listening');
      this.elements.voice.title = 'Listening... Click to stop';
      this.elements.input.placeholder = '🎤 Listening... Speak now!';
    };

    this.recognition.onresult = (event) => {
      console.log('Recognition result:', event);
      
      // Get the most recent result
      const last = event.results.length - 1;
      const transcript = event.results[last][0].transcript;
      
      console.log('Transcript:', transcript);
      
      // Set the input value
      this.elements.input.value = transcript;
      this.elements.input.focus();
    };

    this.recognition.onend = () => {
      console.log('Voice recognition ended');
      this.isListening = false;
      this.elements.voice.classList.remove('listening');
      this.elements.voice.title = 'Click to speak';
      this.elements.input.placeholder = this.config.placeholder;
    };

    this.recognition.onerror = (event) => {
      console.error('Speech recognition error:', event.error);
      this.isListening = false;
      this.elements.voice.classList.remove('listening');
      this.elements.voice.title = 'Click to speak';
      this.elements.input.placeholder = this.config.placeholder;
      
      if (event.error === 'no-speech') {
        this.elements.input.placeholder = '❌ No speech detected. Try again.';
        setTimeout(() => {
          this.elements.input.placeholder = this.config.placeholder;
        }, 3000);
      } else if (event.error === 'not-allowed') {
        alert('🎤 Microphone access denied. Please allow microphone access in your browser settings.');
      } else if (event.error === 'aborted') {
        console.log('Recognition aborted');
      } else {
        this.elements.input.placeholder = `❌ Error: ${event.error}`;
        setTimeout(() => {
          this.elements.input.placeholder = this.config.placeholder;
        }, 3000);
      }
    };
  }

  toggleVoiceInput() {
    if (!this.recognition) {
      alert('Voice input is not supported in your browser. Please use Chrome, Edge, or Safari.');
      return;
    }

    if (this.isListening) {
      console.log('Stopping voice recognition...');
      this.recognition.stop();
    } else {
      console.log('Starting voice recognition...');
      try {
        // Clear input before starting
        this.elements.input.value = '';
        this.recognition.start();
      } catch (error) {
        console.error('Error starting recognition:', error);
        alert('Failed to start voice recognition. Please try again.');
      }
    }
  }
}

// Auto-initialize if config is provided
if (typeof window !== 'undefined') {
  window.SimpleChatBot = SimpleChatBot;
}