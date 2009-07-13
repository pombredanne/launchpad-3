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
    package_dir={'': 'lib'},
    include_package_data=True,
    zip_safe=False,
    maintainer='Launchpad Developers',
    description=('A unique collaboration and Bazaar code hosting platform '
                 'for software projects.'),
    license='LGPL v3',
    # this list should only contain direct dependencies--things imported or
    # used in zcml.
    install_requires=[
        'chameleon.core',
        'chameleon.zpt',
        'feedvalidator',
        'launchpadlib',
        'lazr.uri',
        'mechanize',
        'oauth',
        'python-openid',
        'pytz',
        'setuptools',
        'sourcecodegen',
        'storm',
        'transaction',
        'wadllib',
        'z3c.pt',
        'z3c.ptcompat',
        'zc.zservertracelog',
        'zope.app.appsetup',
        'zope.app.component',
        'zope.app.dav', # ./package-includes/dav-configure.zcml
        'zope.app.error',
        'zope.app.exception',
        'zope.app.file',
        'zope.app.form',
        'zope.app.pagetemplate',
        'zope.app.pluggableauth',
        'zope.app.publication',
        'zope.app.publisher',
        'zope.app.security',
        'zope.app.securitypolicy',
        'zope.app.server',
        'zope.app.session',
        'zope.app.testing',
        'zope.app.wsgi',
        'zope.app.zapi',
        'zope.contenttype',
        'zope.component[zcml]',
        'zope.datetime',
        'zope.thread',
        'zope.error',
        'zope.event',
        'zope.exceptions',
        'zope.formlib',
        'zope.i18n',
        'zope.interface',
        'zope.lifecycleevent',
        'zope.location',
        'zope.pagetemplate',
        'zope.publisher',
        'zope.proxy',
        'zope.schema',
        'zope.security',
        'zope.sendmail',
        'zope.server',
        'zope.session',
        'zope.tal',
        'zope.tales',
        'zope.testbrowser',
        'zope.testing',
        'zope.traversing',
        'zope.viewlet', # only fixing a broken dependency
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
