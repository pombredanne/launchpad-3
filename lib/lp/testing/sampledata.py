# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Constants that refer to values in sampledata.

If ever you use a literal in a test that refers to sample data, even if it's
just a small number, then you should define it as a constant here.
"""

__metaclass__ = type
__all__ = [
    'CHROOT_LFA',
    'CPROV_NAME',
    'HOARY_DISTROSERIES_NAME',
    'I386_ARCHITECTURE_NAME',
    'LAUNCHPAD_DBUSER_NAME',
    'MAIN_COMPONENT_NAME',
    'MOZILLA_FIREFOX_SOURCEPACKAGENAME',
    'MOZILLA_FIREFOX_SOURCEPACKAGEVERSION',
    'NAME16_PERSON_NAME',
    'NO_PRIVILEGE_EMAIL',
    'UBUNTU_DISTRIBUTION_NAME',
    'UBUNTU_TEAM_NAME',
    'UBUNTUTEST_DISTRIBUTION_NAME',
    'WARTY_DISTROSERIES_NAME',
    'WARTY_UPDATES_SUITE_NAME',
    ]


CHROOT_LFA = 1
CPROV_NAME = 'cprov'
HOARY_DISTROSERIES_NAME = 'hoary'
I386_ARCHITECTURE_NAME = 'i386'
LAUNCHPAD_DBUSER_NAME = 'launchpad'
MAIN_COMPONENT_NAME = 'main'
MOZILLA_FIREFOX_SOURCEPACKAGENAME = 'mozilla-firefox'
MOZILLA_FIREFOX_SOURCEPACKAGEVERSION = '0.9'
NAME16_PERSON_NAME = 'name16'
NO_PRIVILEGE_EMAIL = 'no-priv@canonical.com'
UBUNTU_DISTRIBUTION_NAME = 'ubuntu'
UBUNTU_TEAM_NAME = 'ubuntu-team'
WARTY_DISTROSERIES_NAME = 'warty'
WARTY_UPDATES_SUITE_NAME = WARTY_DISTROSERIES_NAME + '-updates'
