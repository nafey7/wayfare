"""Conftest for booking service tests.

Patches ``FLIGHTLOGIC_STRIPE_ACCOUNT_ID`` on the transaction model module before tests
import the booking stack. Uses ``importlib.import_module("app.database.models.transaction")``
so the real submodule loads (``patch("app.database.models.transaction....")`` fails because
``app.database.models`` does not expose ``transaction`` as a plain attribute).
"""

import importlib
from unittest.mock import patch

_txn = importlib.import_module("app.database.models.transaction")
_patcher = patch.object(_txn, "FLIGHTLOGIC_STRIPE_ACCOUNT_ID", "acct_test")
_patcher.start()
