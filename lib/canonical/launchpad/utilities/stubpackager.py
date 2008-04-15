#!/usr/bin/env python

# Copyright 2008 Canonical Ltd.  All rights reserved.

""" ... """

__metaclass__ = type
__all__ = ['StubPackager']

import atexit
import os
import shutil
import subprocess
import tarfile
import tempfile
import time

from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.ftests.keys_for_tests import import_secret_test_key
from canonical.launchpad.interfaces import IGPGHandler
from canonical.launchpad.interfaces import IStubPackager


changelog_entry_template = (
    """%(source_name)s (%(version)s) %(suite)s; urgency=low

  * %(changelog_text)s

 -- %(author)s <%(email)s>  %(timestamp)s

""")

control_file_template = """
Source: %(source)s
Section: %(section)s
Priority: %(priority)s
Maintainer: Launchpad team <launchpad@lists.canonical.com>
Standards-Version: 3.7.3

Package: %(binary)s
Architecture: %(arch)s
Section: %(section)s
Description: Stuff for testing
 This package is simply used for testing soyuz

"""

rules_file_template = """#!/usr/bin/make -f

build:
\t@echo Built

binary-indep:
\t@echo Nothing to do

binary-arch:
\tmkdir debian/tmp
\tmkdir debian/tmp/DEBIAN
\tcp contents debian/tmp/%(name)s-contents
\tdpkg-gencontrol -isp
\tdpkg-deb -b debian/tmp ..

clean:
\trm -rf debian/tmp

binary: binary-arch
"""


class StubPackager:
    """See IStubPackager."""

    implements(IStubPackager)

    name = None
    version = None
    gpg_key_id = None

    def __init__(self):
        self._createNewSandbox()

    def _createNewSandbox(self):
        self.sandbox_path = tempfile.mkdtemp(prefix='stubpackager-')
        # Create a local atexit handler to remove the sandbox directory
        # on normal termination.
        def removeSandbox(sandbox):
            """Remove GNUPGHOME directory."""
            if os.path.exists(sandbox):
                shutil.rmtree(sandbox)

        atexit.register(removeSandbox, self.sandbox_path)

    def setSourceNameAndVersion(self, name, version):
        """See IStubPackager."""
        self.name = name
        self.version = version

    def setGPGKey(self, key_path=None):
        """See IStubPackager."""
        gpghandler = getUtility(IGPGHandler)

        if key_path is None:
            self.gpg_key_id = None
            return

        import_secret_test_key(key_path)
        key = list(gpghandler.localKeys())[0]
        self.gpg_key_id = '0x%s' % key.keyid

    @property
    def upstream_directory(self):
        """See IStubPackager."""
        assert self.sandbox_path is not None, (
            "Sandbox directory path is not set.")

        assert self.name is not None and self.version is not None, (
            'Undefined name and version.')

        directory_name = '%s-%s' % (self.name, self.version)
        return os.path.join(self.sandbox_path, directory_name)

    @property
    def debian_path(self):
        """ """
        return os.path.join(self.upstream_directory, 'debian')

    @property
    def changelog_path(self):
        """ """
        return os.path.join(self.debian_path, 'changelog')

    @property
    def copyright_path(self):
        """ """
        return os.path.join(self.debian_path, 'copyright')

    @property
    def rules_path(self):
        """ """
        return os.path.join(self.debian_path, 'rules')

    @property
    def control_path(self):
        """ """
        return os.path.join(self.debian_path, 'control')

    def _appendContents(self, content):
        """ """
        contents_file = open(
            os.path.join(self.upstream_directory, 'contents'), 'a')
        contents_file.write("%s\n" % content)
        contents_file.close()

    def _buildOrig(self):
        """ """
        orig_filename = '%s_%s.orig.tar.gz' % (self.name, self.version)
        orig_path = os.path.join(self.sandbox_path, orig_filename)
        orig = tarfile.open(orig_path, 'w:gz')
        orig.add(self.upstream_directory)
        orig.close()

    def _touch(self, path, content=''):
        """ """
        fd = open(path, 'w')
        fd.write('%s\n' % content)
        fd.close()

    def _populateChangelog(self):
        """ """
        self._touch(self.changelog_path)

    def _populateControl(self):
        """ """
        replacements = {
            'source': self.name,
            'binary': self.name,
            'section': 'devel',
            'priority': 'optional',
            'arch': 'any',
            }
        self._touch(
            self.control_path, control_file_template % replacements)

    def _populateCopyright(self):
        """ """
        self._touch(
            self.copyright_path, 'No ones land ...')

    def _populateRules(self):
        """ """
        replacements = {
            'name': self.name,
            }
        self._touch(
            self.rules_path, rules_file_template % replacements)

    def _populateDebian(self):
        """ """
        os.mkdir(self.debian_path)
        self._populateChangelog()
        self._populateControl()
        self._populateCopyright()
        self._populateRules()

    def _prependChangelogEntry(self, changelog_replacements):
        """ """
        changelog_file = open(self.changelog_path)
        previous_content = changelog_file.read()
        changelog_file.close()

        changelog_entry = changelog_entry_template % changelog_replacements
        changelog_file = open(self.changelog_path, 'w')
        changelog_file.write(changelog_entry)
        changelog_file.write(previous_content)
        changelog_file.close()

    def _runSubProcess(self, script, extra_args=None):
        """ """
        if extra_args is None:
            extra_args = []
        args = [script]
        args.extend(extra_args)
        process = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            stdin=subprocess.PIPE)
        stdout, stderr = process.communicate()

        assert process.returncode == 0, (
            'Out:\n%sErr:\n%s' % (stdout, stderr))

        return (stdout, stderr)

    def buildUpstream(self, build_orig=True):
        """See IStubPackager."""
        assert not os.path.exists(self.upstream_directory), (
            'Selected upstream directory already exists: %s' % (
                os.path.basename(self.upstream_directory)))

        os.mkdir(self.upstream_directory)
        self._appendContents(self.version)

        if build_orig:
            self._buildOrig()

        self._populateDebian()
        first_version = '%s-1' % self.version
        self.buildVersion(
            first_version, changelog_text='Initial Upstream package')

    def buildVersion(self, version, changelog_text="nicht !",
                     suite=None, author='Foo Bar',
                     email='foo.bar@canonical.com',
                     timestamp=None):
        """See IStubPackager."""
        assert version.startswith(self.version), (
            'New versions should starts with the upstream version: %s ' % (
                self.version))

        if suite is None:
            suite = 'hardy'

        if timestamp is None:
            timestamp = time.strftime('%a, %d %b %Y %T %z')

        changelog_replacements = {
            'source_name': self.name,
            'version': version,
            'suite': suite,
            'changelog_text': changelog_text,
            'author': author,
            'email': email,
            'timestamp': timestamp,
            }

        self._prependChangelogEntry(changelog_replacements)
        self._appendContents(version)

    def buildSource(self, include_orig=True, signed=True):
        """See IStubPackager."""
        assert os.path.exists(self.upstream_directory), (
            'Selected upstream directory does not exist: %s' % (
                os.path.basename(self.upstream_directory)))

        debuild_options = ['-S']

        if not signed:
            debuild_options.extend(['-uc', '-us'])
        else:
            assert self.gpg_key_id is not None, (
                'Cannot build signed packages because the key is not set.')
            debuild_options.append('-k%s' % self.gpg_key_id)

        if include_orig:
            debuild_options.append('-sa')

        current_path = os.getcwd()
        os.chdir(self.upstream_directory)

        self._runSubProcess('debuild', debuild_options)

        os.chdir(current_path)

    def listAvailableUploads(self):
        """See IStubPackager."""
        changes = [os.path.join(self.sandbox_path, filename)
                   for filename in os.listdir(self.sandbox_path)
                   if filename.endswith('.changes')]

        return sorted(changes)

    def reset(self):
        """See IStubPackager."""
        shutil.rmtree(self.sandbox_path)

        self.name = None
        self.version = None

        self._createNewSandbox()


if __name__ == '__main__':

    from zope.component import getUtility
    from canonical.launchpad.interfaces import IStubPackager
    from canonical.launchpad import scripts
    from canonical.lp import initZopeless

    scripts.execute_zcml_for_scripts(use_web_security=True)
    initZopeless(dbuser='ro')

    packager = getUtility(IStubPackager)

    packager.setSourceNameAndVersion('biscuit', '1.0')
    packager.setGPGKey('foo.bar@canonical.com-passwordless.sec')

    packager.buildUpstream(build_orig=True)
    packager.buildSource(include_orig=True)

    packager.buildVersion('1.0-2', changelog_text="cookies")
    packager.buildVersion('1.0-3', changelog_text="butter cookies")
    packager.buildSource(include_orig=False)

    packager.buildVersion('1.0-4', changelog_text="uhmmm, leker")
    packager.buildSource(include_orig=False)

    packager.setSourceNameAndVersion('zeca', '1.0')
    packager.buildUpstream(build_orig=True)
    packager.buildSource(include_orig=True)

    packager.buildVersion('1.0-2', changelog_text="cookies")
    packager.buildSource(include_orig=False)

    for changesfile in packager.listAvailableUploads():
        print changesfile

    packager.cleanSandbox()
