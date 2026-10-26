import pytest

from pbremaster.data import gamedir
from pbremaster.settings import Settings


@pytest.fixture(scope="session")
def game():
    try:
        return gamedir.find()
    except FileNotFoundError:
        pytest.skip("original Pandora's Box files not available")


@pytest.fixture(autouse=True)
def windowed(monkeypatch):
    """The game starts full screen by default; tests click in 800x600 game coordinates,
    so they run in a plain window of that size."""
    load = Settings.load.__func__

    def load_windowed(cls, path=None):
        s = load(cls, path)
        s.fullscreen = False
        s.window_size = [800, 600]
        return s

    monkeypatch.setattr(Settings, "load", classmethod(load_windowed))
