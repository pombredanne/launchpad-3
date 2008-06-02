#!/usr/bin/env python
# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Setup for the wadllib library."""

import ez_setup
ez_setup.use_setuptools()

from setuptools import setup, find_packages

from wadllib import __version__

setup(
    name        = 'wadllib',
    version     = __version__,
    description = """\
wadllib is a client-side package for inspecting and navigating between
HTTP resources described using the Web Application Description
Language.
""",
    author      = 'The Launchpad developers',
    download_url= 'https://launchpad.net/wadllib/+download',
    packages    = find_packages(),
    include_package_data = True,
    zip_safe    = True,
    setup_requires = [
        'setuptools_bzr',
        ]
    )
