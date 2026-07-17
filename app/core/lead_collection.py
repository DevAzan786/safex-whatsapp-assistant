import re
from app.core.session import set_session, clear_session
from app.core.crm import sync_lead

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

def process_lead_message(sender: str, message: str, current_state: str, session: dict) -> tuple:
    """
    Processes a message from a user who is currently in the Lead Collection flow.
    Returns: (reply_text, next_state)
    """
    message = message.strip()
    session_data = session.get("data", {})
    
    if current_state == "lead_name":
        # Save the name
        session_data["name"] = message
        set_session(sender, state="lead_email", data=session_data)
        reply = f"Thank you, {message}! What is your email address so our team can reach out to you?"
        return reply, "lead_email"
        
    elif current_state == "lead_email":
        # Validate email
        if not EMAIL_REGEX.match(message):
            reply = "That doesn't look like a valid email. Please enter a valid email address (e.g., name@example.com):"
            return reply, "lead_email"
            
        session_data["email"] = message
        set_session(sender, state="lead_requirements", data=session_data)
        reply = "Got it. Finally, could you briefly describe your project or the services you are interested in?"
        return reply, "lead_requirements"
        
    elif current_state == "lead_requirements":
        # Save requirements
        requirements = message
        name = session_data.get("name", "Customer")
        email = session_data.get("email", "")
        
        # Save lead to mock CRM
        sync_lead(sender, name, email, requirements)
        
        # Reset session state
        clear_session(sender)
        
        reply = "Thank you! We've captured your details and our team will get in touch with you shortly. Have a great day!"
        return reply, "idle"
        
    else:
        # Default starting point
        set_session(sender, state="lead_name", data={})
        reply = "We would love to help you! To get started, could you please tell me your name?"
        return reply, "lead_name"
