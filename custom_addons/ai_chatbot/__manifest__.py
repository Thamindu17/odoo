{
    'name': 'AI Chatbot',
    'version': '1.0',
    'category': 'Tools',
    'depends': ['website'],
    'data': [
        'views/chatbot.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'ai_chatbot/static/src/js/chatbot.js',
        ],
    },
    'installable': True,
    'application': True,
}