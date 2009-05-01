#!/usr/bin/env python

# Copyright 2009 Canonical Ltd.  All rights reserved.

import ez_setup
ez_setup.use_setuptools()

import sys
from setuptools import setup, find_packages

__version__ = '2.2.3'

setup(
    name='lp',
    version=__version__,
    packages=find_packages('lib'),
    package_dir={'':'lib'},
    include_package_data=True,
    zip_safe=False,
    maintainer='Launchpad Developers',
    description=('A unique collaboration and Bazaar code hosting platform '
                 'for software projects.'),
    license='LGPL v3',
    install_requires=[
        'setuptools',
        'zope.interface',
        ],
    url='https://launchpad.net/',
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Programming Language :: Python"],
    extras_require=dict(
        docs=['Sphinx',
              'z3c.recipe.sphinxdoc']
    ),
    entry_points=dict(
        console_scripts=[ # `console_scripts` is a magic name to zc.buildout
            'killservice = lp.scripts.utilities.killservice:main',
            'run = canonical.launchpad.scripts.runlaunchpad:start_launchpad',
            'harness = canonical.database.harness:python',
        ]
    ),
)
