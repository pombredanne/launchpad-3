# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Fake transaction manager."""

__metaclass__ = type
__all__ = ['FakeTransaction']


class FakeTransaction:
    def begin(self):
        pass
    def commit(self):
        pass
    def abort(self):
        pass
