# Copyright 2017-2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Beautiful Soup wrapper for Launchpad.

With Beautiful Soup 3, this is mostly for future migration convenience.
With Beautiful Soup 4, it does a little more work to avoid warnings.
"""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'BeautifulSoup',
    'BeautifulSoup4',
    'SoupStrainer',
    'SoupStrainer4',
    ]


from BeautifulSoup import (
    BeautifulSoup as _BeautifulSoup,
    SoupStrainer,
    )
from bs4 import BeautifulSoup as _BeautifulSoup4
from bs4.element import SoupStrainer as SoupStrainer4


class BeautifulSoup(_BeautifulSoup):

    def __init__(self, markup="", **kwargs):
        if not isinstance(markup, unicode) and "fromEncoding" not in kwargs:
            kwargs["fromEncoding"] = "UTF-8"
        super(BeautifulSoup, self).__init__(markup=markup, **kwargs)


class BeautifulSoup4(_BeautifulSoup4):

    def __init__(self, markup="", features="html.parser", **kwargs):
        if not isinstance(markup, unicode) and "from_encoding" not in kwargs:
            kwargs["from_encoding"] = "UTF-8"
        super(BeautifulSoup4, self).__init__(
            markup=markup, features=features, **kwargs)
