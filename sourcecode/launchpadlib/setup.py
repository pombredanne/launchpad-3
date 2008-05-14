#!/usr/bin/env python
# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Setup for launchpadlib library."""

import ez_setup
ez_setup.use_setuptools()

from setuptools import setup, find_packages

from launchpadlib import __version__

setup(
    name        = 'launchpadlib',
    version     = __version__,
    description = """\
launchpadlib is a client-side package for scripting Launchpad through its web
services interface.  Launchpad <http://launchpad.net> is a a free software
hosting and development website, making it easy to collaborate across multiple
projects.""",
    author      = 'The Launchpad developers',
    author_email= 'launchpadlib@lists.launchpad.net',
    license     = 'LGPLv2.1 or later',
    url         = 'https://help.launchpad.net/API/launchpadlib',
    download_url= 'https://launchpad.net/launchpadlib/+download',
    packages    = find_packages(),
    include_package_data = True,
    zip_safe    = True,
    setup_requires = [
        'setuptools_bzr',
        ]
    )
