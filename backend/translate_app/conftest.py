import pytest
from unittest.mock import patch
from django.core.cache import cache
from translate_app import services


@pytest.fixture(autouse=True)
def reset_anthropic_singleton():
    """Reset the Anthropic client singleton before each test so patch decorators work correctly."""
    services._anthropic_client = None
    yield
    services._anthropic_client = None


@pytest.fixture(autouse=True)
def disable_tiered_throttling(db):
    """Disable all tiered throttles in tests unless a test explicitly needs them."""
    cache.clear()
    with patch('translate_app.throttles.TieredThrottle.allow_request', return_value=True):
        yield
    cache.clear()
