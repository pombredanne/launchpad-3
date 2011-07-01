# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Long-poll infrastructure."""

__metaclass__ = type
__all__ = [
    "emit",
    "subscribe",
    ]

from .adapters import (
    emit,
    subscribe,
    )


