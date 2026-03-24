(function () {
  document.addEventListener('DOMContentLoaded', function () {
    if (typeof SimpleChatBot === 'undefined') {
      console.warn('SimpleChatBot is not loaded yet.');
      return;
    }

    if (document.querySelector('.chatbot-container')) {
      return;
    }

    new SimpleChatBot({
      apiUrl: 'http://localhost:8000',
      primaryColor: '#0f2eba',
      botName: 'Company Manager Assistant',
      placeholder: 'Ask me anything...',
      position: 'bottom-right'
    });
  });
})();
