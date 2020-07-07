import pytest

from bluesky.tests.conftest import RE
import ophyd.sim


@pytest.fixture(scope="function")
def hw(request):
    return ophyd.sim.hw()
