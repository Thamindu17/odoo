(function () {
  function getCurrentUserNameFromGlobals() {
    const odooGlobal = window.odoo || {};
    const sessionInfo = odooGlobal.__session_info__ || odooGlobal.session_info || {};
    return sessionInfo.name || sessionInfo.username || '';
  }

  async function getCurrentUserName() {
    const globalName = getCurrentUserNameFromGlobals();
    if (globalName) {
      return globalName;
    }

    try {
      const response = await fetch('/web/session/get_session_info', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'same-origin',
        body: JSON.stringify({
          jsonrpc: '2.0',
          method: 'call',
          params: {}
        })
      });

      if (!response.ok) {
        return '';
      }

      const payload = await response.json();
      const result = payload && payload.result ? payload.result : {};
      return result.name || result.username || '';
    } catch (_err) {
      return '';
    }
  }

  document.addEventListener('DOMContentLoaded', async function () {
    if (typeof SimpleChatBot === 'undefined') {
      console.warn('SimpleChatBot is not loaded yet.');
      return;
    }

    if (document.querySelector('.chatbot-container')) {
      return;
    }

    const currentUserName = await getCurrentUserName();

    new SimpleChatBot({
      apiUrl: 'http://127.0.0.1:9000',
      primaryColor: '#0f2eba',
      botName: 'Chat Assistant',
      placeholder: 'Ask me anything...',
      currentUserName,
      position: 'bottom-right'
    });
  });
})();
