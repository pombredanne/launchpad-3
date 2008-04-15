# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

from zope.interface import Interface, Attribute

__all__ = ['IStubPackager']


class IStubPackager(Interface):
    """Helper for packaging operations."""

    sandbox_path = Attribute(
        'Temporary directory where the packages are generated.')

    name = Attribute('Upstream source package name.')

    version = Attribute('Upstream source package version')

    gpg_key_id = Attribute('GPG key ID set to signed packages.')

    upstream_directory = Attribute(
        'Current upstream directory used to generate packages.')

    debian_path = Attribute(
        'Path to the debian directory generated for the current '
        'upstream source.')

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

        'build_orig' indicates whether or now to prepare a orig.tar.gz
        containing the pristine upstream code. If generated it will be
        used for subsequent versions.
        """

    def buildVersion(version, changelog_text="nicht !",
                     suite=None, author='Foo Bar',
                     email='foo.bar@canonical.com',
                     timestamp=None):
        """Intialise a new version of extracted package."""

    def buildSource(include_orig=True, key_id=None):
        """Build a new version of the source package.

        'include_orig' controls whether or not the upstream tarball should
        be included in the changesfile.
        'key_id' if not passed will result in unsigned sources, if a signed
        package is wanted it should be the key ID (in '0xAABBCCDD' form) of
        a password less GPG key.
        """

    def listAvailableUploads():
        """Return the path for all available changesfiles."""


