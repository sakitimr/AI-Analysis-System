import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from unittest.mock import MagicMock
from src.tools.sample_data import get_sample_data

@pytest.fixture
def sample_data():
    return get_sample_data()

@pytest.fixture
def mock_llm():
    mock = MagicMock()
    mock.invoke.return_value = MagicMock(content="Mock response")
    return mock
