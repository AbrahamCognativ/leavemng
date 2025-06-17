from unittest.mock import patch
from app.utils import email_utils as email


def test_send_invite_email():
    from unittest.mock import MagicMock
    mock_request = MagicMock()
    with patch('app.utils.email_utils.send_email') as mock_send:
        email.send_invite_email(
            'abraham@cognativ.com',
            'http://invite-link',
            mock_request)
        mock_send.assert_called_once()
        args, kwargs = mock_send.call_args
        assert 'Invite' in args[0]
        assert 'abraham@cognativ.com' in args[2]


def test_send_leave_request_notification():
    from unittest.mock import MagicMock
    mock_request = MagicMock()
    with patch('app.utils.email_utils.send_email') as mock_send:
        email.send_leave_request_notification(
            'abraham@cognativ.com',
            'Alice',
            'Annual Leave: 2025-05-05',
            mock_request)
        mock_send.assert_called_once()
        args, kwargs = mock_send.call_args
        assert 'Leave Request' in args[0]
        assert 'abraham@cognativ.com' in args[2]


def test_send_leave_approval_notification():
    from unittest.mock import MagicMock
    mock_request = MagicMock()
    with patch('app.utils.email_utils.send_email') as mock_send:
        email.send_leave_approval_notification(
            'abraham@cognativ.com',
            'Annual Leave: 2025-05-05',
            True,
            mock_request)
        mock_send.assert_called_once()
        args, kwargs = mock_send.call_args
        assert 'approved' in args[0].lower() or 'rejected' in args[0].lower()
        assert 'abraham@cognativ.com' in args[2]
