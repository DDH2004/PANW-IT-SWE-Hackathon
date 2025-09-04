"""Backend package initializer.

Ensures subpackages (models, routes utils) are discoverable when running tests
with just PYTHONPATH set to project root in minimal CI.
"""

# Eager import models to avoid certain test runners failing to find backend.models
try:  # pragma: no cover
	from . import models  # noqa: F401
except Exception:  # pragma: no cover
	pass
