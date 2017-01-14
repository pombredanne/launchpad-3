# Copyright 2009-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""OpenID consumer configuration."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

__all__ = [
    'set_default_openid_fetcher',
    ]

from functools import partial
import os.path
import urllib2

from openid.fetchers import (
    setDefaultFetcher,
    Urllib2Fetcher,
    )

from lp.services.config import config


# The Python OpenID package uses pycurl by default, but pycurl chokes on
# self-signed certificates (like the ones we use when developing), so we
# change the default to urllib2 here.  That's also a good thing because it
# ensures we test the same thing that we run on production.
def set_default_openid_fetcher():
    fetcher = Urllib2Fetcher()
    if config.launchpad.enable_test_openid_provider:
        cafile = os.path.join(config.root, "configs/development/launchpad.crt")
        fetcher.urlopen = partial(urllib2.urlopen, cafile=cafile)
    setDefaultFetcher(fetcher)
