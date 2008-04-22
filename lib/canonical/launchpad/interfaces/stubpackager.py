# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213
from zope.interface import Interface
from zope.schema import TextLine

from canonical.launchpad import _

__all__ = ['IStubPackager']


class IStubPackager(Interface):
    """Helper for packaging operations."""

    name = TextLine(
        title=_('Upstream source name'),
        description=_('Upstream source package name.'))

    version = TextLine(
        title=_('Upstream source version'),
        description=_('Upstream source package version'))

    gpg_key_id = TextLine(
        title=_('Current GPG key ID'),
        description=_('GPG key ID set to signed packages.'))

    sandbox_path = TextLine(
        title=_('Sandbox path'),
        description=_('Temporary directory where the packages '
                      'are generated.'))

    upstream_directory = TextLine(
        title=_('Upstream directory path'),
        description=_('Current upstream directory used to generate '
                      'packages.'))

    debian_path = TextLine(
        title=_('Upstream debian directory path'),
        description=_('Path to the debian directory generated for '
                      'the current upstream source.'))

    def reset():
        """Reset sandbox directory used to generate packages.

        It actually purges the current tempdir and created a new one.
        It also undefine upstream 'name' and 'version' to avoid user
        mistakes.
        """

    def setSourceNameAndVersion(name, version):
        """Set the context source name and version."""

    def setGPGKey(key_path):
        """Import and use the give secret GPG key to sign packages."""

    def buildUpstream(build_orig=True):
        """Build a stub source upstream version.

        param: build_orig: boolean indicating whether or not to prepare
            a orig.tar.gz containing the pristine upstream code. If
            generated it can be used for subsequent versions.
        """

    def buildVersion(version, changelog_text="nicht !",
                     suite=None, author='Foo Bar',
                     email='foo.bar@canonical.com',
                     timestamp=None):
        """Initialise a new version of extracted package."""

    def buildSource(include_orig=True, key_id=None):
        """Build a new version of the source package.

        :param  include_orig: boolean, controls whether or not the
             upstream tarball should be included in the changesfile.
        :param key_id: if not passed will result in unsigned sources,
             if a signed package is wanted it should be the key ID
             (in '0xAABBCCDD' form) of a password-less GPG key.
        """

    def listAvailableUploads():
        """Return the path for all available changesfiles."""


