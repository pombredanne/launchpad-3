# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""See canonical.librarian.testing.fake."""

import warnings

from canonical.librarian.testing.fake import FakeLibrarian as _FakeLibrarian


def FakeLibrarian(*args, **kwargs):
    """Forward to the new home with a deprecation warning."""
    warnings.warn("Stale import: please import FakeLibrarian from "
        "canonical.librarian.testing.fake instead.", DeprecationWarning,
        stacklevel=2)
    return _FakeLibrarian(*args, **kwargs)
