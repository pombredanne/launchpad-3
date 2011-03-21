# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Constants that refer to values in sampledata.

If ever you use a literal in a test that refers to sample data, even if it's
just a small number, then you should define it as a constant here.
"""

__metaclass__ = type
__all__ = [
    'ADMIN_EMAIL',
    'BOB_THE_BUILDER_NAME',
    'BUILDD_ADMIN_USERNAME',
    'CHROOT_LIBRARYFILEALIAS',
    'COMMERCIAL_ADMIN_EMAIL',
    'FROG_THE_BUILDER_NAME',
    'HOARY_DISTROSERIES_NAME',
    'I386_ARCHITECTURE_NAME',
    'LAUNCHPAD_ADMIN',
    'LAUNCHPAD_DBUSER_NAME',
    'MAIN_COMPONENT_NAME',
    'NO_PRIVILEGE_EMAIL',
    'SAMPLE_PERSON_EMAIL',
    'UBUNTU_DEVELOPER_ADMIN_NAME',
    'UBUNTU_DISTRIBUTION_NAME',
    'UBUNTU_UPLOAD_TEAM_NAME',
    'UBUNTUTEST_DISTRIBUTION_NAME',
    'USER_EMAIL',
    'WARTY_DISTROSERIES_NAME',
    'WARTY_ONLY_SOURCEPACKAGENAME',
    'WARTY_ONLY_SOURCEPACKAGEVERSION',
    'WARTY_UPDATES_SUITE_NAME',
    ]

# Please use names that reveal intent, rather than being purely
# descriptive, i.e. USER16_NAME isn't as good as
# UBUNTU_DEVELOPER_NAME. Where intent is tricky to convey in the
# name, please leave a comment as well.

# A user with Launchpad Admin privileges.
ADMIN_EMAIL = 'foo.bar@canonical.com'

# A user with buildd admin rights and upload rights to Ubuntu.
BUILDD_ADMIN_USERNAME = 'cprov'
# A couple of builders.
BOB_THE_BUILDER_NAME = 'bob'
FROG_THE_BUILDER_NAME = 'frog'
# The LibraryFileAlias of a chroot for attaching to a DistroArchSeries
CHROOT_LIBRARYFILEALIAS = 1
HOARY_DISTROSERIES_NAME = 'hoary'
I386_ARCHITECTURE_NAME = 'i386'
LAUNCHPAD_ADMIN = 'admin@canonical.com'
LAUNCHPAD_DBUSER_NAME = 'launchpad'
MAIN_COMPONENT_NAME = 'main'

NO_PRIVILEGE_EMAIL = 'no-priv@canonical.com'
USER_EMAIL = 'test@canonical.com'
VCS_IMPORTS_MEMBER_EMAIL = 'david.allouche@canonical.com'
COMMERCIAL_ADMIN_EMAIL = 'commercial-member@canonical.com'
SAMPLE_PERSON_EMAIL = USER_EMAIL
# A user that is an admin of ubuntu-team, which has upload rights
# to Ubuntu.
UBUNTU_DEVELOPER_ADMIN_NAME = 'name16'
UBUNTU_DISTRIBUTION_NAME = 'ubuntu'
# A team that has upload rights to Ubuntu
UBUNTU_UPLOAD_TEAM_NAME = 'ubuntu-team'
WARTY_DISTROSERIES_NAME = 'warty'
# A source package name and version for a package only published in
# warty
WARTY_ONLY_SOURCEPACKAGENAME = 'mozilla-firefox'
WARTY_ONLY_SOURCEPACKAGEVERSION = '0.9'
WARTY_UPDATES_SUITE_NAME = WARTY_DISTROSERIES_NAME + '-updates'
