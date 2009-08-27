# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Helper to analyze cookies in a zope.testbrowser browser.

This API and idea has been accepted into zope.testbrowser, upstream, so this
code will be removed from here once that change has landed and we are able to
use it.  https://bugs.edge.launchpad.net/zope3/+bug/286842
"""

__metaclass__ = type
__all__ = [
    'Cookies',
    ]

from UserDict import DictMixin
import datetime
import pytz

class Cookies(DictMixin):
    """Cookies for testbrowser.  Currently does not implement setting.
    """

    def __init__(self, testbrowser):
        self.testbrowser = testbrowser

    @property
    def _jar(self):
        for handler in self.testbrowser.mech_browser.handlers:
            if getattr(handler, 'cookiejar', None) is not None:
                return handler.cookiejar
        raise RuntimeError('no cookiejar found')

    def _get(self, key):
        for ck in self._jar:
            if ck.name == key:
                return ck

    def __getitem__(self, key):
        ck = self._get(key)
        if ck is None:
            raise KeyError(key)
        return ck.value

    def keys(self):
        return [ck.name for ck in self._jar]

    def __contains__(self, key):
        return self._get(key) is not None

    def getInfo(self, key):
        ck = self._get(key)
        if ck is None:
            raise KeyError(key)
        res = {'value': ck.value,
               'port': ck.port,
               'domain': ck.domain,
               'path': ck.path,
               'secure': ck.secure,
               'expires': None}
        if ck.expires is not None:
            res['expires'] = datetime.datetime.fromtimestamp(
                ck.expires, pytz.UTC)
        return res

    def __len__(self):
        return len(self._jar)
