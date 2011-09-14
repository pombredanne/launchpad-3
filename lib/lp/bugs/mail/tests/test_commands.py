# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from lazr.lifecycle.interfaces import (
    IObjectModifiedEvent,
    )

from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.bugs.interfaces.bug import CreateBugParams
from lp.bugs.mail.commands import (
    AffectsEmailCommand,
    BugEmailCommand,
    PrivateEmailCommand,
    SecurityEmailCommand,
    SubscribeEmailCommand,
    UnsubscribeEmailCommand,
    )
from lp.services.mail.interfaces import (
    BugTargetNotFound,
    EmailProcessingError,
    )
from lp.testing import (
    login_celebrity,
    login_person,
    TestCaseWithFactory,
    )


class AffectsEmailCommandTestCase(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test__splitPath_with_slashes(self):
        self.assertEqual(
            ('foo', 'bar/baz'), AffectsEmailCommand._splitPath('foo/bar/baz'))

    def test__splitPath_no_slashes(self):
        self.assertEqual(
            ('foo', ''), AffectsEmailCommand._splitPath('foo'))

    def test__normalizePath_leading_slash(self):
        self.assertEqual(
            'foo/bar', AffectsEmailCommand._normalizePath('/foo/bar'))

    def test__normalizePath_distros(self):
        self.assertEqual(
            'foo/bar', AffectsEmailCommand._normalizePath('/distros/foo/bar'))

    def test__normalizePath_products(self):
        self.assertEqual(
            'foo/bar',
            AffectsEmailCommand._normalizePath('/products/foo/bar'))

    def test_getBugTarget_no_pillar_error(self):
        message = "There is no project named 'fnord' registered in Launchpad."
        self.assertRaisesWithContent(
            BugTargetNotFound, message,
            AffectsEmailCommand.getBugTarget, 'fnord')

    def test_getBugTarget_project_group_error(self):
        owner = self.factory.makePerson()
        login_person(owner)
        project_group = self.factory.makeProject(name='fnord', owner=owner)
        project_1 = self.factory.makeProduct(name='pting', owner=owner)
        project_1.project = project_group
        project_2 = self.factory.makeProduct(name='snarf', owner=owner)
        project_2.project = project_group
        message = (
            "fnord is a group of projects. To report a bug, you need to "
            "specify which of these projects the bug applies to: "
            "pting, snarf")
        self.assertRaisesWithContent(
            BugTargetNotFound, message,
            AffectsEmailCommand.getBugTarget, 'fnord')

    def test_getBugTarget_deactivated_project_error(self):
        project = self.factory.makeProduct(name='fnord')
        login_celebrity('admin')
        project.active = False
        message = "There is no project named 'fnord' registered in Launchpad."
        self.assertRaisesWithContent(
            BugTargetNotFound, message,
            AffectsEmailCommand.getBugTarget, 'fnord')

    def test_getBugTarget_project(self):
        project = self.factory.makeProduct(name='fnord')
        self.assertEqual(project, AffectsEmailCommand.getBugTarget('fnord'))

    def test_getBugTarget_no_project_series_error(self):
        self.factory.makeProduct(name='fnord')
        message = "Fnord doesn't have a series named 'pting'."
        self.assertRaisesWithContent(
            BugTargetNotFound, message,
            AffectsEmailCommand.getBugTarget, 'fnord/pting')

    def test_getBugTarget_project_series(self):
        project = self.factory.makeProduct(name='fnord')
        series = self.factory.makeProductSeries(name='pting', product=project)
        self.assertEqual(
            series, AffectsEmailCommand.getBugTarget('fnord/pting'))

    def test_getBugTarget_product_extra_path_error(self):
        product = self.factory.makeProduct(name='fnord')
        self.factory.makeProductSeries(name='pting', product=product)
        message = "Unexpected path components: snarf"
        self.assertRaisesWithContent(
            BugTargetNotFound, message,
            AffectsEmailCommand.getBugTarget, 'fnord/pting/snarf')

    def test_getBugTarget_no_series_or_package_error(self):
        self.factory.makeDistribution(name='fnord')
        message = (
            "Fnord doesn't have a series or source package named 'pting'.")
        self.assertRaisesWithContent(
            BugTargetNotFound, message,
            AffectsEmailCommand.getBugTarget, 'fnord/pting')

    def test_getBugTarget_distribution(self):
        distribution = self.factory.makeDistribution(name='fnord')
        self.assertEqual(
            distribution, AffectsEmailCommand.getBugTarget('fnord'))

    def test_getBugTarget_distroseries(self):
        distribution = self.factory.makeDistribution(name='fnord')
        series = self.factory.makeDistroSeries(
            name='pting', distribution=distribution)
        self.assertEqual(
            series, AffectsEmailCommand.getBugTarget('fnord/pting'))

    def test_getBugTarget_source_package(self):
        distribution = self.factory.makeDistribution(name='fnord')
        series = self.factory.makeDistroSeries(
            name='pting', distribution=distribution)
        package = self.factory.makeSourcePackage(
            sourcepackagename='snarf', distroseries=series, publish=True)
        self.assertEqual(
            package, AffectsEmailCommand.getBugTarget('fnord/pting/snarf'))

    def test_getBugTarget_distribution_source_package(self):
        distribution = self.factory.makeDistribution(name='fnord')
        series = self.factory.makeDistroSeries(
            name='pting', distribution=distribution)
        package = self.factory.makeSourcePackage(
            sourcepackagename='snarf', distroseries=series, publish=True)
        dsp = distribution.getSourcePackage(package.name)
        self.assertEqual(
            dsp, AffectsEmailCommand.getBugTarget('fnord/snarf'))

    def test_getBugTarget_distribution_extra_path_error(self):
        distribution = self.factory.makeDistribution(name='fnord')
        series = self.factory.makeDistroSeries(
            name='pting', distribution=distribution)
        self.factory.makeSourcePackage(
            sourcepackagename='snarf', distroseries=series, publish=True)
        message = "Unexpected path components: thrup"
        self.assertRaisesWithContent(
            BugTargetNotFound, message,
            AffectsEmailCommand.getBugTarget, 'fnord/pting/snarf/thrup')


class BugEmailCommandTestCase(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def test_execute_bug_id(self):
        bug = self.factory.makeBug()
        command = BugEmailCommand('bug', [str(bug.id)])
        self.assertEqual((bug, None), command.execute(None, None))

    def test_execute_bug_id_wrong_type(self):
        command = BugEmailCommand('bug', ['nickname'])
        error = self.assertRaises(
            EmailProcessingError, command.execute, None, None)
        message = str(error).split('\n')
        self.assertEqual(
            "The 'bug' command expects either 'new' or a bug id.", message[0])

    def test_execute_bug_id_not_found(self):
        command = BugEmailCommand('bug', ['9999999'])
        error = self.assertRaises(
            EmailProcessingError, command.execute, None, None)
        message = str(error).split('\n')
        self.assertEqual(
            "There is no such bug in Launchpad: 9999999", message[0])

    def test_execute_bug_id_new(self):
        user = self.factory.makePerson()
        login_person(user)
        message = self.factory.makeSignedMessage(
            body='borked\n affects fnord',
            subject='title borked',
            to_address='new@bugs.launchpad.dev')
        filealias = self.factory.makeLibraryFileAlias()
        command = BugEmailCommand('bug', ['new'])
        params, event = command.execute(message, filealias)
        self.assertEqual(None, event)
        self.assertEqual(user, params.owner)
        self.assertEqual('title borked', params.title)
        self.assertEqual(message['Message-Id'], params.msg.rfc822msgid)


class PrivateEmailCommandTestCase(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_execute_bug(self):
        bug = self.factory.makeBug()
        login_person(bug.bugtasks[0].target.owner)
        command = PrivateEmailCommand('private', ['yes'])
        exec_bug, event = command.execute(bug, None)
        self.assertEqual(bug, exec_bug)
        self.assertEqual(True, bug.private)
        self.assertTrue(IObjectModifiedEvent.providedBy(event))

    def test_execute_bug_params(self):
        user = self.factory.makePerson()
        login_person(user)
        bug_params = CreateBugParams(title='bug title', owner=user)
        command = PrivateEmailCommand('private', ['yes'])
        dummy_event = object()
        params, event = command.execute(bug_params, dummy_event())
        self.assertEqual(bug_params, params)
        self.assertEqual(True, bug_params.private)
        self.assertEqual(dummy_event, event)


class SecurityEmailCommandTestCase(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_execute_bug(self):
        bug = self.factory.makeBug()
        login_person(bug.bugtasks[0].target.owner)
        command = SecurityEmailCommand('security', ['yes'])
        exec_bug, event = command.execute(bug, None)
        self.assertEqual(bug, exec_bug)
        self.assertEqual(True, bug.security_related)
        self.assertTrue(IObjectModifiedEvent.providedBy(event))

    def test_execute_bug_params(self):
        user = self.factory.makePerson()
        login_person(user)
        bug_params = CreateBugParams(title='bug title', owner=user)
        command = SecurityEmailCommand('security', ['yes'])
        dummy_event = object()
        params, event = command.execute(bug_params, dummy_event)
        self.assertEqual(bug_params, params)
        self.assertEqual(True, bug_params.security_related)
        self.assertEqual(dummy_event, event)


class SubscribeEmailCommandTestCase(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_execute_bug_with_user_name(self):
        bug = self.factory.makeBug()
        login_person(bug.bugtasks[0].target.owner)
        subscriber = self.factory.makePerson()
        command = SubscribeEmailCommand('subscribe', [subscriber.name])
        dummy_event = object()
        exec_bug, event = command.execute(bug, dummy_event)
        self.assertEqual(bug, exec_bug)
        self.assertContentEqual(
            [bug.owner, subscriber], bug.getDirectSubscribers())
        self.assertEqual(dummy_event, event)

    def test_execute_bug_without_user_name(self):
        bug = self.factory.makeBug()
        target_owner = bug.bugtasks[0].target.owner
        login_person(target_owner)
        command = SubscribeEmailCommand('subscribe', [])
        dummy_event = object()
        exec_bug, event = command.execute(bug, dummy_event)
        self.assertEqual(bug, exec_bug)
        self.assertContentEqual(
            [bug.owner, target_owner], bug.getDirectSubscribers())
        self.assertEqual(dummy_event, event)

    def test_execute_bug_params_one_subscriber(self):
        user = self.factory.makePerson()
        login_person(user)
        subscriber = self.factory.makePerson()
        bug_params = CreateBugParams(title='bug title', owner=user)
        command = SubscribeEmailCommand('subscribe', [subscriber.name])
        dummy_event = object()
        params, event = command.execute(bug_params, dummy_event)
        self.assertEqual(bug_params, params)
        self.assertContentEqual([subscriber], bug_params.subscribers)
        self.assertEqual(dummy_event, event)

    def test_execute_bug_params_many_subscriber(self):
        user = self.factory.makePerson()
        login_person(user)
        subscriber_1 = self.factory.makePerson()
        subscriber_2 = self.factory.makePerson()
        bug_params = CreateBugParams(
            title='bug title', owner=user, subscribers=[subscriber_1])
        command = SubscribeEmailCommand('subscribe', [subscriber_2.name])
        dummy_event = object()
        params, event = command.execute(bug_params, dummy_event)
        self.assertEqual(bug_params, params)
        self.assertContentEqual(
            [subscriber_1, subscriber_2], bug_params.subscribers)
        self.assertEqual(dummy_event, event)


class UnsubscribeEmailCommandTestCase(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_execute_bug_with_user_name(self):
        bug = self.factory.makeBug()
        target_owner = bug.bugtasks[0].target.owner
        login_person(target_owner)
        bug.subscribe(target_owner, target_owner)
        command = UnsubscribeEmailCommand('unsubscribe', [target_owner.name])
        dummy_event = object()
        exec_bug, event = command.execute(bug, dummy_event)
        self.assertEqual(bug, exec_bug)
        self.assertContentEqual(
            [bug.owner], bug.getDirectSubscribers())
        self.assertEqual(dummy_event, event)

    def test_execute_bug_without_user_name(self):
        bug = self.factory.makeBug()
        target_owner = bug.bugtasks[0].target.owner
        login_person(target_owner)
        bug.subscribe(target_owner, target_owner)
        command = UnsubscribeEmailCommand('unsubscribe', [])
        dummy_event = object()
        exec_bug, event = command.execute(bug, dummy_event)
        self.assertEqual(bug, exec_bug)
        self.assertContentEqual(
            [bug.owner], bug.getDirectSubscribers())
        self.assertEqual(dummy_event, event)

    def test_execute_bug_params(self):
        # Unsubscribe does nothing because the is not yet a bug.
        # Any value can be used for the user name.
        user = self.factory.makePerson()
        login_person(user)
        bug_params = CreateBugParams(title='bug title', owner=user)
        command = UnsubscribeEmailCommand('unsubscribe', ['non-existant'])
        dummy_event = object()
        params, event = command.execute(bug_params, dummy_event)
        self.assertEqual(bug_params, params)
        self.assertEqual(dummy_event, event)
