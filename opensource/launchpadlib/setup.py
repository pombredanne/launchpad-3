#!/usr/bin/env python
# Copyright 2008 Canonical Ltd.

# This file is part of launchpadlib.
#
# launchpadlib is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# launchpadlib is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# launchpadlib.  If not, see <http://www.gnu.org/licenses/>.

"""Setup for the launchpadlib library."""

import ez_setup
ez_setup.use_setuptools()

from setuptools import setup, find_packages
from launchpadlib import __version__


setup(
    name        = 'launchpadlib',
    version     = __version__,
    description = 'a client-side library for scripting Launchpad.net',
    description = """\
launchpadlib is a client-side library for scripting Launchpad through its web
services interface.  Launchpad <http://launchpad.net> is a a free software
hosting and development website, making it easy to collaborate across multiple
projects.""",
    author      = 'The Launchpad developers',
    author_email= 'launchpadlib@lists.launchpad.net',
    url         = 'https://help.launchpad.net/API/launchpadlib',
    license     = 'GNU GPLv3 or later',
    download_url= 'https://launchpad.net/launchpadlib/+download',
    packages    = find_packages(),
    include_package_data = True,
    zip_safe    = True,
    install_requires = [
        'httplib2',
        'simplejson',
        ],
    setup_requires = [
        'setuptools_bzr',
        ]
    )
