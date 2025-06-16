import os
import pytest
from fastapi import Request
from types import SimpleNamespace
from app.utils.email_utils import send_email

def test_sendgrid_real_email():
    """
    Sends a real email using SendGrid API and current settings.
    Set TEST_EMAIL_RECIPIENT env var to control the recipient.
    """
    recipient = os.environ.get("TEST_EMAIL_RECIPIENT")
    assert recipient, "Set TEST_EMAIL_RECIPIENT env var to your email."

    # Simulate FastAPI request with settings
    class FakeApp:
        state = SimpleNamespace(settings=SimpleNamespace(
            SENDGRID_API_KEY=os.environ["SENDGRID_API_KEY"],
            EMAIL_USER=os.environ.get("EMAIL_USER"),
            EMAIL_HOST=os.environ.get("EMAIL_HOST")
        ))
    fake_request = SimpleNamespace(app=FakeApp())

    send_email(
        subject="SendGrid Real Email Test",
        body="This is a test email sent via SendGrid integration.",
        to_emails=[recipient],
        request=fake_request,
        html="<b>This is a test email sent via <i>SendGrid</i> integration.</b>"
    )
    print("Email sent to", recipient)

