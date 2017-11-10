# Copyright 2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Beautiful Soup wrapper for Launchpad.

With Beautiful Soup 3, this is mostly for future migration convenience.
With Beautiful Soup 4, it will do a little more work to avoid warnings.
"""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'BeautifulSoup',
    'SoupStrainer',
    ]


from BeautifulSoup import (
    BeautifulSoup as _BeautifulSoup,
    SoupStrainer,
    )


class BeautifulSoup(_BeautifulSoup):

    def __init__(self, markup="", **kwargs):
        if not isinstance(markup, unicode) and "fromEncoding" not in kwargs:
            kwargs["fromEncoding"] = "UTF-8"
        super(BeautifulSoup, self).__init__(markup=markup, **kwargs)
