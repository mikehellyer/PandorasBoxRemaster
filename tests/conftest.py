import pytest

from pbremaster.data import gamedir


@pytest.fixture(scope="session")
def game():
    try:
        return gamedir.find()
    except FileNotFoundError:
        pytest.skip("original Pandora's Box files not available")
