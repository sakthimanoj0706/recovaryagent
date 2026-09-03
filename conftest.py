import os
import pytest

@pytest.fixture(autouse=True)
def setup_env():
    # Keep development so existing UI/API tests pass without auth headers
    os.environ["RECOVERAI_ENV"] = "development"
