# Copyright 2009-2017 Canonical Ltd.  This software is licensed under the GNU
# Affero General Public License version 3 (see the file LICENSE).

__all__ = [
    'InProcessKeyServerFixture',
    'KeyServerTac',
    ]

from lp.testing.keyserver.harness import KeyServerTac
from lp.testing.keyserver.inprocess import InProcessKeyServerFixture
