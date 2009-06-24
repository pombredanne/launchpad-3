#!/usr/bin/env python

# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import ez_setup
ez_setup.use_setuptools()

import sys
from setuptools import setup, find_packages

__version__ = '2.2.3'

setup(
    name='lp',
    version=__version__,
    packages=find_packages('lib'),
    package_dir={'': 'lib'},
    include_package_data=True,
    zip_safe=False,
    maintainer='Launchpad Developers',
    description=('A unique collaboration and Bazaar code hosting platform '
                 'for software projects.'),
    license='LGPL v3',
    install_requires=[
        'feedvalidator',
        'launchpadlib',
        'lazr.uri',
        'oauth',
        'python-openid',
        'pytz',
        'setuptools',
        'sourcecodegen',
        'storm',
        'chameleon.core',
        'chameleon.zpt',
        'z3c.pt',
        'z3c.ptcompat',
        'wadllib',
        # Loggerhead dependencies. These should be removed once
        # bug 383360 is fixed and we include it as a source dist.
        'Paste',
        'PasteDeploy',
        'SimpleTal'
    ],
    url='https://launchpad.net/',
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
    ],
    extras_require=dict(
        docs=[
            'Sphinx',
            'z3c.recipe.sphinxdoc',
        ]
    ),
    entry_points=dict(
        console_scripts=[ # `console_scripts` is a magic name to setuptools
            'apiindex = lp.scripts.utilities.apiindex:main',
            'killservice = lp.scripts.utilities.killservice:main',
            'run = canonical.launchpad.scripts.runlaunchpad:start_launchpad',
            'harness = canonical.database.harness:python',
            'twistd = twisted.scripts.twistd:run',
        ]
    ),
)
