import uuid

import pytest

from app.agents.state import PipelineState
from app.providers.bundle import build_mock_providers


@pytest.fixture
def providers():
    return build_mock_providers()


@pytest.fixture
def base_state():
    return PipelineState(verification_id=uuid.uuid4())
