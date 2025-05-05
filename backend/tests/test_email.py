import pytest
from unittest.mock import patch
from app.utils import email

def test_send_invite_email():
    with patch('app.utils.email.send_email') as mock_send:
        email.send_invite_email('test@example.com', 'http://invite-link')
        mock_send.assert_called_once()
        args, kwargs = mock_send.call_args
        assert 'Invite' in args[0]
        assert 'test@example.com' in args[2]

def test_send_leave_request_notification():
    with patch('app.utils.email.send_email') as mock_send:
        email.send_leave_request_notification('manager@example.com', 'Alice', 'Annual Leave: 2025-05-05')
        mock_send.assert_called_once()
        args, kwargs = mock_send.call_args
        assert 'Leave Request' in args[0]
        assert 'manager@example.com' in args[2]

def test_send_leave_approval_notification():
    with patch('app.utils.email.send_email') as mock_send:
        email.send_leave_approval_notification('user@example.com', 'Annual Leave: 2025-05-05', True)
        mock_send.assert_called_once()
        args, kwargs = mock_send.call_args
        assert 'approved' in args[0].lower() or 'rejected' in args[0].lower()
        assert 'user@example.com' in args[2]
