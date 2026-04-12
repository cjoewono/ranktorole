import pytest
from translate_app import services


@pytest.fixture(autouse=True)
def reset_anthropic_singleton():
    """Reset the Anthropic client singleton before each test so patch decorators work correctly."""
    services._anthropic_client = None
    yield
    services._anthropic_client = None
