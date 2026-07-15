"""
WhatsApp Business Cloud API client.
- send_message(to, text)
- verify_webhook(request)
- parse_incoming_message(payload)
Note: full webhook handling may live in a separate teammate's module;
this file only covers what this FAQ module needs to send/receive directly
for local testing.
TODO: implement Cloud API request wrapper using real credentials from .env.
"""
