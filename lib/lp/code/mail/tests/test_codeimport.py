# Copyright 2010-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for code import related mailings"""

from email import message_from_string
import textwrap

import transaction

from lp.code.enums import (
    CodeImportReviewStatus,
    RevisionControlSystems,
    TargetRevisionControlSystems,
    )
from lp.code.tests.helpers import GitHostingFixture
from lp.services.mail import stub
from lp.testing import (
    login_celebrity,
    login_person,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class TestNewCodeImports(TestCaseWithFactory):
    """Test the emails sent out for new code imports."""

    layer = DatabaseFunctionalLayer

    def test_cvs_to_bzr_import(self):
        # Test the email for a new CVS-to-Bazaar import.
        eric = self.factory.makePerson(name='eric')
        fooix = self.factory.makeProduct(name='fooix')
        # Eric needs to be logged in for the mail to be sent.
        login_person(eric)
        self.factory.makeProductCodeImport(
            cvs_root=':pserver:anonymouse@cvs.example.com:/cvsroot',
            cvs_module='a_module', branch_name='import',
            product=fooix, registrant=eric)
        transaction.commit()
        msg = message_from_string(stub.test_emails[0][2])
        self.assertEqual('code-import', msg['X-Launchpad-Notification-Type'])
        self.assertEqual('~eric/fooix/import', msg['X-Launchpad-Branch'])
        self.assertEqual(
            'A new CVS code import has been requested by Eric:\n'
            '    http://code.launchpad.dev/~eric/fooix/import\n'
            'from\n'
            '    :pserver:anonymouse@cvs.example.com:/cvsroot, a_module\n'
            '\n'
            '-- \nYou are getting this email because you are a member of the '
            'vcs-imports team.\n', msg.get_payload(decode=True))

    def test_svn_to_bzr_import(self):
        # Test the email for a new Subversion-to-Bazaar import.
        eric = self.factory.makePerson(name='eric')
        fooix = self.factory.makeProduct(name='fooix')
        # Eric needs to be logged in for the mail to be sent.
        login_person(eric)
        self.factory.makeProductCodeImport(
            svn_branch_url='svn://svn.example.com/fooix/trunk',
            branch_name='trunk', product=fooix, registrant=eric,
            rcs_type=RevisionControlSystems.BZR_SVN)
        transaction.commit()
        msg = message_from_string(stub.test_emails[0][2])
        self.assertEqual('code-import', msg['X-Launchpad-Notification-Type'])
        self.assertEqual('~eric/fooix/trunk', msg['X-Launchpad-Branch'])
        self.assertEqual(
            'A new subversion code import has been requested by Eric:\n'
            '    http://code.launchpad.dev/~eric/fooix/trunk\n'
            'from\n'
            '    svn://svn.example.com/fooix/trunk\n'
            '\n'
            '-- \nYou are getting this email because you are a member of the '
            'vcs-imports team.\n', msg.get_payload(decode=True))

    def test_git_to_bzr_import(self):
        # Test the email for a new git-to-Bazaar import.
        eric = self.factory.makePerson(name='eric')
        fooix = self.factory.makeProduct(name='fooix')
        # Eric needs to be logged in for the mail to be sent.
        login_person(eric)
        self.factory.makeProductCodeImport(
            git_repo_url='git://git.example.com/fooix.git',
            branch_name='master', product=fooix, registrant=eric)
        transaction.commit()
        msg = message_from_string(stub.test_emails[0][2])
        self.assertEqual('code-import', msg['X-Launchpad-Notification-Type'])
        self.assertEqual('~eric/fooix/master', msg['X-Launchpad-Branch'])
        self.assertEqual(
            'A new git code import has been requested '
            'by Eric:\n'
            '    http://code.launchpad.dev/~eric/fooix/master\n'
            'from\n'
            '    git://git.example.com/fooix.git\n'
            '\n'
            '-- \nYou are getting this email because you are a member of the '
            'vcs-imports team.\n', msg.get_payload(decode=True))

    def test_git_to_git_import(self):
        # Test the email for a new git-to-git import.
        self.useFixture(GitHostingFixture())
        eric = self.factory.makePerson(name='eric')
        fooix = self.factory.makeProduct(name='fooix')
        # Eric needs to be logged in for the mail to be sent.
        login_person(eric)
        self.factory.makeProductCodeImport(
            git_repo_url='git://git.example.com/fooix.git',
            branch_name=u'master', product=fooix, registrant=eric,
            target_rcs_type=TargetRevisionControlSystems.GIT)
        transaction.commit()
        msg = message_from_string(stub.test_emails[0][2])
        self.assertEqual('code-import', msg['X-Launchpad-Notification-Type'])
        self.assertEqual('~eric/fooix/+git/master', msg['X-Launchpad-Branch'])
        self.assertEqual(
            'A new git code import has been requested '
            'by Eric:\n'
            '    http://code.launchpad.dev/~eric/fooix/+git/master\n'
            'from\n'
            '    git://git.example.com/fooix.git\n'
            '\n'
            '-- \nYou are getting this email because you are a member of the '
            'vcs-imports team.\n', msg.get_payload(decode=True))

    def test_new_source_package_import(self):
        # Test the email for a new sourcepackage import.
        eric = self.factory.makePerson(name='eric')
        distro = self.factory.makeDistribution(name='foobuntu')
        series = self.factory.makeDistroSeries(
            name='manic', distribution=distro)
        fooix = self.factory.makeSourcePackage(
            sourcepackagename='fooix', distroseries=series)
        # Eric needs to be logged in for the mail to be sent.
        login_person(eric)
        self.factory.makePackageCodeImport(
            git_repo_url='git://git.example.com/fooix.git',
            branch_name='master', sourcepackage=fooix, registrant=eric)
        transaction.commit()
        msg = message_from_string(stub.test_emails[0][2])
        self.assertEqual('code-import', msg['X-Launchpad-Notification-Type'])
        self.assertEqual(
            '~eric/foobuntu/manic/fooix/master', msg['X-Launchpad-Branch'])
        self.assertEqual(
            'A new git code import has been requested '
            'by Eric:\n'
            '    http://code.launchpad.dev/~eric/foobuntu/manic/fooix/master\n'
            'from\n'
            '    git://git.example.com/fooix.git\n'
            '\n'
            '-- \nYou are getting this email because you are a member of the '
            'vcs-imports team.\n', msg.get_payload(decode=True))


class TestUpdatedCodeImports(TestCaseWithFactory):
    """Test the emails sent out for updated code imports."""

    layer = DatabaseFunctionalLayer

    def assertSameDetailsEmail(self, details, unique_name):
        msg = message_from_string(stub.test_emails[0][2])
        self.assertEqual(
            'code-import-updated', msg['X-Launchpad-Notification-Type'])
        self.assertEqual(unique_name, msg['X-Launchpad-Branch'])
        self.assertEqual(
            'Hello,\n\n'
            'The import has been marked as failing.\n\n'
            'This code import is from:\n'
            '    %(details)s\n\n'
            '-- \nhttp://code.launchpad.dev/%(unique_name)s\n'
            'You are getting this email because you are a member of the '
            'vcs-imports team.\n' % {
                'details': details,
                'unique_name': unique_name,
                },
            msg.get_payload(decode=True))

    def assertDifferentDetailsEmail(self, old_details, new_details,
                                    unique_name):
        msg = message_from_string(stub.test_emails[0][2])
        self.assertEqual(
            'code-import-updated', msg['X-Launchpad-Notification-Type'])
        self.assertEqual(unique_name, msg['X-Launchpad-Branch'])
        self.assertEqual(
            'Hello,\n\n'
            '%(details_change_message)s\n'
            '    %(new_details)s\n'
            'instead of:\n'
            '    %(old_details)s\n'
            '\n'
            '-- \nhttp://code.launchpad.dev/%(unique_name)s\n'
            'You are getting this email because you are a member of the '
            'vcs-imports team.\n' % {
                'details_change_message': textwrap.fill(
                    '%s is now being imported from:' % unique_name),
                'old_details': old_details,
                'new_details': new_details,
                'unique_name': unique_name,
                },
            msg.get_payload(decode=True))

    def test_cvs_to_bzr_import_same_details(self):
        code_import = self.factory.makeProductCodeImport(
            cvs_root=':pserver:anonymouse@cvs.example.com:/cvsroot',
            cvs_module='a_module')
        unique_name = code_import.target.unique_name
        user = login_celebrity('vcs_imports')
        code_import.updateFromData(
            {'review_status': CodeImportReviewStatus.FAILING}, user)
        transaction.commit()
        self.assertSameDetailsEmail(
            'a_module from :pserver:anonymouse@cvs.example.com:/cvsroot',
            unique_name)

    def test_cvs_to_bzr_import_different_details(self):
        code_import = self.factory.makeProductCodeImport(
            cvs_root=':pserver:anonymouse@cvs.example.com:/cvsroot',
            cvs_module='a_module')
        unique_name = code_import.target.unique_name
        user = login_celebrity('vcs_imports')
        code_import.updateFromData({'cvs_module': 'another_module'}, user)
        transaction.commit()
        self.assertDifferentDetailsEmail(
            'a_module from :pserver:anonymouse@cvs.example.com:/cvsroot',
            'another_module from :pserver:anonymouse@cvs.example.com:/cvsroot',
            unique_name)

    def test_svn_to_bzr_import_same_details(self):
        code_import = self.factory.makeProductCodeImport(
            svn_branch_url='svn://svn.example.com/fooix/trunk')
        unique_name = code_import.target.unique_name
        user = login_celebrity('vcs_imports')
        code_import.updateFromData(
            {'review_status': CodeImportReviewStatus.FAILING}, user)
        transaction.commit()
        self.assertSameDetailsEmail(
            'svn://svn.example.com/fooix/trunk', unique_name)

    def test_svn_to_bzr_import_different_details(self):
        code_import = self.factory.makeProductCodeImport(
            svn_branch_url='svn://svn.example.com/fooix/trunk')
        unique_name = code_import.target.unique_name
        user = login_celebrity('vcs_imports')
        code_import.updateFromData(
            {'url': 'https://svn.example.com/fooix/trunk'}, user)
        transaction.commit()
        self.assertDifferentDetailsEmail(
            'svn://svn.example.com/fooix/trunk',
            'https://svn.example.com/fooix/trunk', unique_name)

    def test_git_to_bzr_import_same_details(self):
        code_import = self.factory.makeProductCodeImport(
            git_repo_url='git://git.example.com/fooix.git')
        unique_name = code_import.target.unique_name
        user = login_celebrity('vcs_imports')
        code_import.updateFromData(
            {'review_status': CodeImportReviewStatus.FAILING}, user)
        transaction.commit()
        self.assertSameDetailsEmail(
            'git://git.example.com/fooix.git', unique_name)

    def test_git_to_bzr_import_different_details(self):
        code_import = self.factory.makeProductCodeImport(
            git_repo_url='git://git.example.com/fooix.git')
        unique_name = code_import.target.unique_name
        user = login_celebrity('vcs_imports')
        code_import.updateFromData(
            {'url': 'https://git.example.com/fooix.git'}, user)
        transaction.commit()
        self.assertDifferentDetailsEmail(
            'git://git.example.com/fooix.git',
            'https://git.example.com/fooix.git', unique_name)

    def test_git_to_git_import_same_details(self):
        self.useFixture(GitHostingFixture())
        code_import = self.factory.makeProductCodeImport(
            git_repo_url='git://git.example.com/fooix.git',
            target_rcs_type=TargetRevisionControlSystems.GIT)
        unique_name = code_import.target.unique_name
        user = login_celebrity('vcs_imports')
        code_import.updateFromData(
            {'review_status': CodeImportReviewStatus.FAILING}, user)
        transaction.commit()
        self.assertSameDetailsEmail(
            'git://git.example.com/fooix.git', unique_name)

    def test_git_to_git_import_different_details(self):
        self.useFixture(GitHostingFixture())
        code_import = self.factory.makeProductCodeImport(
            git_repo_url='git://git.example.com/fooix.git',
            target_rcs_type=TargetRevisionControlSystems.GIT)
        unique_name = code_import.target.unique_name
        user = login_celebrity('vcs_imports')
        code_import.updateFromData(
            {'url': 'https://git.example.com/fooix.git'}, user)
        transaction.commit()
        self.assertDifferentDetailsEmail(
            'git://git.example.com/fooix.git',
            'https://git.example.com/fooix.git', unique_name)
