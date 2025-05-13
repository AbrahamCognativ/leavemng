import os
import sys
from types import SimpleNamespace

# Ensure parent directory is in sys.path for standalone execution
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from app.utils.email_utils import send_email

def main():
    recipient = "abraham@cognativ.com"

    # Simulate FastAPI request with settings
    class FakeApp:
        state = SimpleNamespace(settings=SimpleNamespace(
            SENDGRID_API_KEY="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",
            EMAIL_USER="abraham@cognativ.com",
            EMAIL_HOST="localhost"
        ))
    fake_request = SimpleNamespace(app=FakeApp())

    try:
        send_email(
            subject="SendGrid Standalone Script Test",
            body="This is a standalone test email sent via SendGrid integration.",
            to_emails=[recipient],
            request=fake_request,
            html="<b>This is a standalone test email sent via <i>SendGrid</i> integration.</b>"
        )
        print(f"Email sent to {recipient}")
    except Exception as e:
        print(f"Failed to send email: {e}")

if __name__ == "__main__":
    main()
