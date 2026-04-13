"""Root conftest.py — global test fixtures applied to ALL test files."""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture(autouse=True)
def block_real_anthropic_api():
    """SAFETY NET: Block all real Anthropic API calls during tests.

    Individual tests that need Claude responses must mock at a higher level
    (e.g., @patch('translate_app.services.anthropic.Anthropic')).
    This fixture ensures that if any test forgets to mock, it gets a
    MagicMock instead of a real API call.
    """
    mock_client = MagicMock()
    # Return a realistic-looking but empty response by default
    mock_block = MagicMock()
    mock_block.type = "text"
    mock_block.text = '{"error": "UNMOCKED_TEST: This test hit the Anthropic safety net. Add a proper mock."}'
    mock_client.messages.create.return_value = MagicMock(content=[mock_block])

    with patch("translate_app.services.anthropic.Anthropic", return_value=mock_client):
        yield mock_client
