# Copyright 2009-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""OpenID consumer configuration."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

__all__ = [
    'set_default_openid_fetcher',
    ]

from functools import partial
import inspect
import os.path
import urllib2

from openid.fetchers import (
    setDefaultFetcher,
    Urllib2Fetcher,
    )

from lp.services.config import config


def set_default_openid_fetcher():
    # Make sure we're using the same fetcher that we use in production, even
    # if pycurl is installed.
    fetcher = Urllib2Fetcher()
    # XXX cjwatson 2017-01-26: Remove inspect hack once we no longer need to
    # run on Ubuntu 12.04 LTS.
    if (config.launchpad.enable_test_openid_provider and
            "cafile" in inspect.getargspec(urllib2.urlopen).args):
        cafile = os.path.join(config.root, "configs/development/launchpad.crt")
        fetcher.urlopen = partial(urllib2.urlopen, cafile=cafile)
    setDefaultFetcher(fetcher)
