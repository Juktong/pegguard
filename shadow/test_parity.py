from __future__ import annotations

from . import constants as C
from .parity import assert_parity


def test_pipeline_parity_against_eventdiff_baseline() -> None:
    results = assert_parity(C.repo_root())

    calm = results["calm"]
    vol = results["vol"]

    assert calm.rows == 629
    assert calm.valid_rows == 628
    assert calm.priced_rows == 628
    assert calm.charged_rows == 470
    assert calm.dev_mae_e2 == 158

    assert vol.rows == 3882
    assert vol.valid_rows == 3882
    assert vol.priced_rows == 3881
    assert vol.charged_rows == 1662
    assert vol.dev_mae_e2 == 224

