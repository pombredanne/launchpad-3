# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['emailcommands', 'get_error_message']

import os.path
import re

from zope.component import getUtility
from zope.event import notify
from zope.interface import implements, providedBy
from zope.schema import ValidationError

from canonical.launchpad.vocabularies import ValidPersonOrTeamVocabulary
from canonical.launchpad.interfaces import (
        IProduct, IDistribution, IDistroSeries, IBug,
        IBugEmailCommand, IBugTaskEmailCommand, IBugEditEmailCommand,
        IBugTaskEditEmailCommand, IBugSet, ICveSet, ILaunchBag,
        IBugTaskSet, IMessageSet, IDistroBugTask,
        IDistributionSourcePackage, EmailProcessingError,
        NotFoundError, CreateBugParams, IPillarNameSet,
        BugTargetNotFound, IProject, ISourcePackage, IProductSeries,
        BugTaskStatus)
from canonical.launchpad.event import (
    SQLObjectModifiedEvent, SQLObjectToBeModifiedEvent, SQLObjectCreatedEvent)
from canonical.launchpad.event.interfaces import (
    ISQLObjectCreatedEvent, ISQLObjectModifiedEvent)

from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.snapshot import Snapshot

from canonical.lp.dbschema import BugTaskImportance


def get_error_message(filename, **interpolation_items):
    """Returns the error message that's in the given filename.

    If the error message requires some parameters, those are given in
    interpolation_items.

    The files are searched for in lib/canonical/launchpad/mail/errortemplates.
    """
    base = os.path.dirname(__file__)
    fullpath = os.path.join(base, 'errortemplates', filename)
    error_template = open(fullpath).read()
    return error_template % interpolation_items


def normalize_arguments(string_args):
    """Normalizes the string arguments.

    The string_args argument is simply the argument string whitespace
    splitted. Sometimes arguments may be quoted, though, so that they can
    contain space characters. For example "This is a long string".

    This function loops through all the argument and joins the quoted strings
    into a single arguments.

        >>> normalize_arguments(['"This', 'is', 'a', 'long', 'string."'])
        ['This is a long string.']

        >>> normalize_arguments(
        ...     ['"First', 'string"', '"Second', 'string"', 'foo'])
        ['First string', 'Second string', 'foo']
    """
    result = []
    quoted_string = False
    for item in string_args:
        if item.startswith('"'):
            quoted_string = True
            result.append(item[1:])
        elif quoted_string and item.endswith('"'):
            result[-1] += ' ' + item[:-1]
            quoted_string = False
        elif quoted_string:
            result[-1] += ' ' + item
        else:
            result.append(item)

    return result


class EmailCommand:
    """Represents a command.

    Both name the values in the args list are strings.
    """
    _numberOfArguments = None

    def __init__(self, name, string_args):
        self.name = name
        self.string_args = normalize_arguments(string_args)

    def _ensureNumberOfArguments(self):
        """Check that the number of arguments is correct.

        Raise an EmailProcessingError
        """
        if self._numberOfArguments is not None:
            num_arguments_got = len(self.string_args)
            if self._numberOfArguments != num_arguments_got:
                raise EmailProcessingError(
                    get_error_message(
                        'num-arguments-mismatch.txt',
                        command_name=self.name,
                        num_arguments_expected=self._numberOfArguments,
                        num_arguments_got=num_arguments_got))

    def convertArguments(self, context):
        """Converts the string argument to Python objects.

        Returns a dict with names as keys, and the Python objects as
        values.
        """
        raise NotImplementedError


    def __str__(self):
        """See IEmailCommand."""
        return ' '.join([self.name] + self.string_args)


class BugEmailCommand(EmailCommand):
    """Creates new bug, or returns an existing one."""
    implements(IBugEmailCommand)

    _numberOfArguments = 1

    def execute(self, parsed_msg, filealias):
        """See IBugEmailCommand."""
        self._ensureNumberOfArguments()
        bugid = self.string_args[0]

        if bugid == 'new':
            message = getUtility(IMessageSet).fromEmail(
                parsed_msg.as_string(),
                owner=getUtility(ILaunchBag).user,
                filealias=filealias,
                parsed_message=parsed_msg)
            if message.text_contents.strip() == '':
                 raise EmailProcessingError(
                    get_error_message('no-affects-target-on-submit.txt'))

            params = CreateBugParams(
                msg=message, title=message.title,
                owner=getUtility(ILaunchBag).user)
            bug = getUtility(IBugSet).createBug(params)
            return bug, SQLObjectCreatedEvent(bug)
        else:
            try:
                bugid = int(bugid)
            except ValueError:
                raise EmailProcessingError(
                    get_error_message('bug-argument-mismatch.txt'))

            try:
                bug = getUtility(IBugSet).get(bugid)
            except NotFoundError:
                raise EmailProcessingError(
                    get_error_message('no-such-bug.txt', bug_id=bugid))
            return bug, None


class EditEmailCommand(EmailCommand):
    """Helper class for commands that edits the context.

    It makes sure that the correct events are notified.
    """

    def execute(self, context, current_event):
        """See IEmailCommand."""
        self._ensureNumberOfArguments()
        args = self.convertArguments(context)

        edited_fields = set()
        if ISQLObjectModifiedEvent.providedBy(current_event):
            context_snapshot = current_event.object_before_modification
            edited_fields.update(current_event.edited_fields)
        else:
            context_snapshot = Snapshot(context, providing=providedBy(context))

        if not ISQLObjectCreatedEvent.providedBy(current_event):
            notify(SQLObjectToBeModifiedEvent(context, args))
        edited = False
        for attr_name, attr_value in args.items():
            if getattr(context, attr_name) != attr_value:
                self.setAttributeValue(context, attr_name, attr_value)
                edited = True
        if edited and not ISQLObjectCreatedEvent.providedBy(current_event):
            edited_fields.update(args.keys())
            current_event = SQLObjectModifiedEvent(
                context, context_snapshot, list(edited_fields))

        return context, current_event

    def setAttributeValue(self, context, attr_name, attr_value):
        """See IEmailCommand."""
        setattr(context, attr_name, attr_value)


class PrivateEmailCommand(EditEmailCommand):
    """Marks a bug public or private."""

    implements(IBugEditEmailCommand)

    _numberOfArguments = 1

    def convertArguments(self, context):
        """See EmailCommand."""
        private_arg = self.string_args[0]
        if private_arg == 'yes':
            return {'private': True}
        elif private_arg == 'no':
            return {'private': False}
        else:
            raise EmailProcessingError(
                get_error_message('private-parameter-mismatch.txt'))


class SecurityEmailCommand(EditEmailCommand):
    """Marks a bug as security related."""

    implements(IBugEditEmailCommand)

    _numberOfArguments = 1

    def convertArguments(self, context):
        """See EmailCommand."""
        [security_flag] = self.string_args
        if security_flag == 'yes':
            return {'security_related': True, 'private': True}
        elif security_flag == 'no':
            return {'security_related': False}
        else:
            raise EmailProcessingError(
                get_error_message('security-parameter-mismatch.txt'))


class SubscribeEmailCommand(EmailCommand):
    """Subscribes someone to the bug."""

    implements(IBugEditEmailCommand)

    def execute(self, bug, current_event):
        """See IEmailCommand."""
        string_args = list(self.string_args)
        # preserve compatibility with the original command that let you
        # specify a subscription type
        if len(string_args) == 2:
            subscription_name = string_args.pop()

        if len(string_args) == 1:
            person_name_or_email = string_args.pop()
            valid_person_vocabulary = ValidPersonOrTeamVocabulary()
            try:
                person_term = valid_person_vocabulary.getTermByToken(
                    person_name_or_email)
            except LookupError:
                raise EmailProcessingError(
                    get_error_message(
                        'no-such-person.txt',
                        name_or_email=person_name_or_email))
            person = person_term.value
        elif len(string_args) == 0:
            # Subscribe the sender of the email.
            person = getUtility(ILaunchBag).user
        else:
            raise EmailProcessingError(
                get_error_message('subscribe-too-many-arguments.txt'))

        if bug.isSubscribed(person):
            # but we still need to find the subscription
            for bugsubscription in bug.subscriptions:
                if bugsubscription.person == person:
                    break

        else:
            bugsubscription = bug.subscribe(person)
            notify(SQLObjectCreatedEvent(bugsubscription))

        return bug, current_event


class UnsubscribeEmailCommand(EmailCommand):
    """Unsubscribes someone from the bug."""

    implements(IBugEditEmailCommand)

    def execute(self, bug, current_event):
        """See IEmailCommand."""
        string_args = list(self.string_args)
        if len(string_args) == 1:
            person_name_or_email = string_args.pop()
            valid_person_vocabulary = ValidPersonOrTeamVocabulary()
            try:
                person_term = valid_person_vocabulary.getTermByToken(
                    person_name_or_email)
            except LookupError:
                raise EmailProcessingError(
                    get_error_message(
                        'no-such-person.txt',
                        name_or_email=person_name_or_email))
            person = person_term.value
        elif len(string_args) == 0:
            # Subscribe the sender of the email.
            person = getUtility(ILaunchBag).user
        else:
            raise EmailProcessingError(
                get_error_message('unsubscribe-too-many-arguments.txt'))

        if bug.isSubscribed(person):
            bug.unsubscribe(person)
        if bug.isSubscribedToDupes(person):
            bug.unsubscribeFromDupes(person)

        return bug, current_event


class SummaryEmailCommand(EditEmailCommand):
    """Changes the title of the bug."""

    implements(IBugEditEmailCommand)
    _numberOfArguments = 1

    def execute(self, bug, current_event):
        """See IEmailCommand."""
        # Do a manual control of the number of arguments, in order to
        # provide a better error message than the default one.
        if len(self.string_args) > 1:
            raise EmailProcessingError(
                get_error_message('summary-too-many-arguments.txt'))

        return EditEmailCommand.execute(self, bug, current_event)

    def convertArguments(self, context):
        """See EmailCommand."""
        return {'title': self.string_args[0]}


class DuplicateEmailCommand(EditEmailCommand):
    """Marks a bug as a duplicate of another bug."""

    implements(IBugEditEmailCommand)
    _numberOfArguments = 1

    def convertArguments(self, context):
        """See EmailCommand."""
        [bug_id] = self.string_args
        if bug_id == 'no':
            # 'no' is a special value for unmarking a bug as a duplicate.
            return {'duplicateof': None}
        try:
            bug = getUtility(IBugSet).getByNameOrID(bug_id)
        except NotFoundError:
            raise EmailProcessingError(
                get_error_message('no-such-bug.txt', bug_id=bug_id))
        duplicate_field = IBug['duplicateof'].bind(context)
        try:
            duplicate_field.validate(bug)
        except ValidationError, error:
            raise EmailProcessingError(error.doc())

        return {'duplicateof': bug}


class CVEEmailCommand(EmailCommand):
    """Links a CVE to a bug."""

    implements(IBugEditEmailCommand)

    _numberOfArguments = 1

    def execute(self, bug, current_event):
        """See IEmailCommand."""
        [cve_sequence] = self.string_args
        cve = getUtility(ICveSet)[cve_sequence]
        if cve is None:
            raise EmailProcessingError(
                'Launchpad can\'t find the CVE "%s".' % cve_sequence)
        bug.linkCVE(cve, getUtility(ILaunchBag).user)
        return bug, current_event


class AffectsEmailCommand(EmailCommand):
    """Either creates a new task, or edits an existing task."""

    implements(IBugTaskEmailCommand)
    _numberOfArguments = 1

    @classmethod
    def _splitPath(cls, path):
        """Split the path part into two.

        The first part is the part before any slash, and the other is
        the part behind the slash:

            >>> AffectsEmailCommand._splitPath('foo/bar/baz')
            ('foo', 'bar/baz')

        If No slash is in the path, the other part will be empty.

            >>> AffectsEmailCommand._splitPath('foo')
            ('foo', '')
        """
        if '/' not in path:
            return path, ''
        else:
            return tuple(path.split('/', 1))

    @classmethod
    def _normalizePath(cls, path):
        """Normalize the path.

        Previously the path had to start with either /distros/ or
        /products/. Simply remove any such prefixes to stay backward
        compatible.

            >>> AffectsEmailCommand._normalizePath('/distros/foo/bar')
            'foo/bar'
            >>> AffectsEmailCommand._normalizePath('/distros/foo/bar')
            'foo/bar'

        Also remove a starting slash, since that's a common mistake.

            >>> AffectsEmailCommand._normalizePath('/foo/bar')
            'foo/bar'
        """
        for prefix in ['/distros/', '/products/', '/']:
            if path.startswith(prefix):
                path = path[len(prefix):]
                break
        return path

    @classmethod
    def getBugTarget(cls, path):
        """Return the IBugTarget with the given path.

        Path should be in any of the following forms:

            $product
            $product/$product_series
            $distribution
            $distribution/$source_package
            $distribution/$distro_series
            $distribution/$distro_series/$source_package
        """
        path = cls._normalizePath(path)
        name, rest = cls._splitPath(path)
        pillar = getUtility(IPillarNameSet).getByName(
            name, ignore_inactive=True)
        if pillar is None:
            raise BugTargetNotFound(
                "There is no project named '%s' registered in Launchpad." %
                    name)

        # We can't check for IBugTarget, since Project is an IBugTarget
        # we don't allow bugs to be filed against.
        if IProject.providedBy(pillar):
            products = ", ".join(product.name for product in pillar.products)
            raise BugTargetNotFound(
                "%s is a group of projects. To report a bug, you need to"
                " specify which of these projects the bug applies to: %s" % (
                    pillar.name, products))
        assert IDistribution.providedBy(pillar) or IProduct.providedBy(pillar)

        if not rest:
            return pillar
        # Resolve the path that is after the pillar name.
        if IProduct.providedBy(pillar):
            series_name, rest = cls._splitPath(rest)
            product_series = pillar.getSeries(series_name)
            if product_series is None:
                raise BugTargetNotFound(
                    "%s doesn't have a series named '%s'." % (
                        pillar.displayname, series_name))
            elif not rest:
                return product_series
        else:
            assert IDistribution.providedBy(pillar)
            # The next step can be either a distro series or a source
            # package.
            series_name, rest = cls._splitPath(rest)
            try:
                series = pillar.getSeries(series_name)
            except NotFoundError:
                package_name = series_name
            else:
                if not rest:
                    return series
                else:
                    pillar = series
                    package_name, rest = cls._splitPath(rest)
            package = pillar.getSourcePackage(package_name)
            if package is None:
                raise BugTargetNotFound(
                    "%s doesn't have a series or source package named '%s'."
                    % (pillar.displayname, package_name))
            elif not rest:
                return package

        assert rest, "This is the fallback for unexpected path components."
        raise BugTargetNotFound("Unexpected path components: %s" % rest)

    def execute(self, bug):
        """See IEmailCommand."""
        string_args = list(self.string_args)
        try:
            path = string_args.pop(0)
        except IndexError:
            raise EmailProcessingError(
                get_error_message('affects-no-arguments.txt'))
        try:
            bug_target = self.getBugTarget(path)
        except BugTargetNotFound, error:
            raise EmailProcessingError(unicode(error))
        event = None
        bugtask = bug.getBugTask(bug_target)
        if (bugtask is None and
            IDistributionSourcePackage.providedBy(bug_target)):
            # If there's a distribution task with no source package, use
            # that one.
            bugtask = bug.getBugTask(bug_target.distribution)
            if bugtask is not None:
                bugtask_before_edit = Snapshot(
                    bugtask, providing=IDistroBugTask)
                bugtask.sourcepackagename = bug_target.sourcepackagename
                event = SQLObjectModifiedEvent(
                    bugtask, bugtask_before_edit, ['sourcepackagename'])

        if bugtask is None:
            bugtask = self._create_bug_task(bug, bug_target)
            event = SQLObjectCreatedEvent(bugtask)

        return bugtask, event

    def _targetBug(self, user, bug, series, sourcepackagename=None):
        """Try to target the bug the the given distroseries.

        If the user doesn't have permission to target the bug directly,
        only a nomination will be created.
        """
        product = None
        distribution = None
        if IDistroSeries.providedBy(series):
            distribution = series.distribution
            if sourcepackagename:
                general_target = distribution.getSourcePackage(
                    sourcepackagename)
            else:
                general_target = distribution
        else:
            assert IProductSeries.providedBy(series), (
                "Unknown series target: %r" % series)
            assert sourcepackagename is None, (
                "A product series can't have a source package.")
            product = series.product
            general_target = product
        general_task = bug.getBugTask(general_target)
        if general_task is None:
            # A series task has to have a corresponding
            # distribution/product task.
            general_task = getUtility(IBugTaskSet).createTask(
                bug, user, distribution=distribution,
                product=product, sourcepackagename=sourcepackagename)
        if not bug.canBeNominatedFor(series):
            # A nomination has already been created.
            nomination = bug.getNominationFor(series)
            # Automatically approve an existing nomination if a series
            # manager targets it.
            if not nomination.isApproved() and nomination.canApprove(user):
                nomination.approve(user)
        else:
            nomination = bug.addNomination(target=series, owner=user)

        if nomination.isApproved():
            if sourcepackagename:
                return bug.getBugTask(
                    series.getSourcePackage(sourcepackagename))
            else:
                return bug.getBugTask(series)
        else:
            # We can't return a nomination, so return the
            # distribution/product bugtask instead.
            return general_task

    def _create_bug_task(self, bug, bug_target):
        """Creates a new bug task with bug_target as the target."""
        # XXX kiko 2005-09-05 Bug 1690:
        # We could fix this by making createTask be a method on
        # IBugTarget, but I'm not going to do this now.
        bugtaskset = getUtility(IBugTaskSet)
        user = getUtility(ILaunchBag).user
        if IProduct.providedBy(bug_target):
            return bugtaskset.createTask(bug, user, product=bug_target)
        elif IProductSeries.providedBy(bug_target):
            return self._targetBug(user, bug, bug_target)
        elif IDistribution.providedBy(bug_target):
            return bugtaskset.createTask(bug, user, distribution=bug_target)
        elif IDistroSeries.providedBy(bug_target):
            return self._targetBug(user, bug, bug_target)
        elif ISourcePackage.providedBy(bug_target):
            return self._targetBug(
                user, bug, bug_target.distroseries,
                bug_target.sourcepackagename)
        elif IDistributionSourcePackage.providedBy(bug_target):
            return bugtaskset.createTask(
                bug, user, distribution=bug_target.distribution,
                sourcepackagename=bug_target.sourcepackagename)
        else:
            assert False, "Not a valid bug target: %r" % bug_target


class AssigneeEmailCommand(EditEmailCommand):
    """Assigns someone to the bug."""

    implements(IBugTaskEditEmailCommand)

    _numberOfArguments = 1

    def convertArguments(self, context):
        """See EmailCommand."""
        person_name_or_email = self.string_args[0]

        # "nobody" is a special case that means assignee == None.
        if person_name_or_email == "nobody":
            return {self.name: None}

        valid_person_vocabulary = ValidPersonOrTeamVocabulary()
        try:
            person_term = valid_person_vocabulary.getTermByToken(
                person_name_or_email)
        except LookupError:
            raise EmailProcessingError(
                get_error_message(
                    'no-such-person.txt', name_or_email=person_name_or_email))

        return {self.name: person_term.value}

    def setAttributeValue(self, context, attr_name, attr_value):
        """See EmailCommand."""
        context.transitionToAssignee(attr_value)


class MilestoneEmailCommand(EditEmailCommand):
    """Sets the milestone for the bugtask."""

    implements(IBugTaskEditEmailCommand)

    _numberOfArguments = 1

    def convertArguments(self, context):
        """See EmailCommand."""
        user = getUtility(ILaunchBag).user
        milestone_name = self.string_args[0]

        if milestone_name == '-':
            # Remove milestone
            return {self.name: None}
        elif self._userCanEditMilestone(user, context):
            pillar = context.pillar
            milestone = pillar.getMilestone(milestone_name)
            if milestone is None:
                addmilestone_url = canonical_url(pillar) + '/+addmilestone'
                raise EmailProcessingError(
                    "The milestone %s does not exist for %s. Note that "
                    "milestones are not automatically created from emails; "
                    "they must be created on the website at %s" % (
                        milestone_name, context.pillar.title,
                        addmilestone_url))
            else:
                return {self.name: milestone}
        else:
            raise EmailProcessingError(
                "You do not have permission to set the milestone for %s. "
                "Only owners, drivers and bug contacts may assign "
                "milestones." % (context.pillar.title,))

    def _userCanEditMilestone(self, user, bugtask):
        """Can the user edit the Milestone field?"""
        # Adapted from BugTaskEditView.userCanEditMilestone.

        # XXX: Consider refactoring this method and the
        # userCanEditMilestone method on BugTaskEditView into a new
        # method on IBugTask. This is non-trivial because
        # check_permission cannot be used in a database class.
        #   -- Gavin Panella, 2007-10-18.

        pillar = bugtask.pillar
        bugcontact = pillar.bugcontact
        if user is not None and bugcontact is not None:
            if user.inTeam(bugcontact):
                return True
        return check_permission("launchpad.Edit", pillar)


class DBSchemaEditEmailCommand(EditEmailCommand):
    """Helper class for edit DBSchema attributes.

    Subclasses should set 'dbschema' to the correct schema.

    For example, if context.foo can be assigned to values in
    FooDBSchema, the follwing command class could be created:

        class FooEmailCommand(DBSchemaEditEmailCommand):
            dbschema = FooDBSchema
    """

    implements(IBugTaskEditEmailCommand)

    _numberOfArguments = 1

    def convertArguments(self, context):
        """See EmailCommand."""
        item_name = self.string_args[0]
        dbschema = self.dbschema
        try:
            dbitem = dbschema.items[item_name.upper()]
        except KeyError:
            dbitem = None

        if dbitem is None or dbitem.name == 'UNKNOWN':
            possible_items = [
                item.name.lower() for item in dbschema.items
                if item.name != 'UNKNOWN']
            possible_values = ', '.join(possible_items)
            raise EmailProcessingError(
                    get_error_message(
                        'dbschema-command-wrong-argument.txt',
                         command_name=self.name,
                         arguments=possible_values,
                         example_argument=possible_items[0]))

        return {self.name: dbitem}


class StatusEmailCommand(DBSchemaEditEmailCommand):
    """Changes a bug task's status."""
    dbschema = BugTaskStatus

    def setAttributeValue(self, context, attr_name, attr_value):
        """See EmailCommand."""
        user = getUtility(ILaunchBag).user

        if not context.canTransitionToStatus(attr_value, user):
            raise EmailProcessingError(
                'The status cannot be changed to %s because you are not '
                'the registrant or a bug contact for %s.' % (
                    attr_value.name.lower(), context.pillar.displayname))

        context.transitionToStatus(attr_value, user)


class ImportanceEmailCommand(DBSchemaEditEmailCommand):
    """Changes a bug task's importance."""
    dbschema = BugTaskImportance


class ReplacedByImportanceCommand(EmailCommand):
    """This command has been replaced by the 'importance' command."""
    implements(IBugTaskEditEmailCommand)

    def execute(self, context, current_event):
        raise EmailProcessingError(
                get_error_message('bug-importance.txt', argument=self.name))


class TagEmailCommand(EmailCommand):
    """Assigns a tag to or removes a tag from bug."""

    implements(IBugEditEmailCommand)

    def execute(self, bug, current_event):
        """See `IEmailCommand`."""
        string_args = list(self.string_args)
        # Bug.tags returns a Zope List, which does not support Python list
        # operations so we need to convert it.
        tags = list(bug.tags)

        # XXX: DaveMurphy 2007-07-11: in the following loop we process each
        # tag in turn. Each tag that is either invalid or unassigned will
        # result in a mail to the submitter. This may result in several mails
        # for a single command. This will need to be addressed if that becomes
        # a problem.

        for arg in string_args:
            # Are we adding or removing a tag?
            if arg.startswith('-'):
                remove = True
                tag = arg[1:]
            else:
                remove = False
                tag = arg
            # Tag must contain only alphanumeric characters
            if re.search('[^a-zA-Z0-9]', tag):
                raise EmailProcessingError(
                    get_error_message('invalid-tag.txt', tag=tag))
            if remove:
                try:
                    tags.remove(tag)
                except ValueError:
                    raise EmailProcessingError(
                        get_error_message('unassigned-tag.txt', tag=tag))
            else:
                tags.append(arg)

        # Duplicates are dealt with when the tags are stored in the DB (which
        # incidentally uses a set to achieve this). Since the code already
        # exists we don't duplicate it here.

        # Bug.tags expects to be given a Python list, so there is no need to
        # convert it back.
        bug.tags = tags

        return bug, current_event


class NoSuchCommand(KeyError):
    """A command with the given name couldn't be found."""


class EmailCommands:
    """A collection of email commands."""

    _commands = {
        'bug': BugEmailCommand,
        'private': PrivateEmailCommand,
        'security': SecurityEmailCommand,
        'summary': SummaryEmailCommand,
        'subscribe': SubscribeEmailCommand,
        'unsubscribe': UnsubscribeEmailCommand,
        'duplicate': DuplicateEmailCommand,
        'cve': CVEEmailCommand,
        'affects': AffectsEmailCommand,
        'assignee': AssigneeEmailCommand,
        'milestone': MilestoneEmailCommand,
        'status': StatusEmailCommand,
        'importance': ImportanceEmailCommand,
        'severity': ReplacedByImportanceCommand,
        'priority': ReplacedByImportanceCommand,
        'tag': TagEmailCommand,
    }

    def names(self):
        """Returns all the command names."""
        return self._commands.keys()

    def get(self, name, string_args):
        """Returns a command object with the given name and arguments.

        If a command with the given name can't be found, a NoSuchCommand
        error is raised.
        """
        command_class = self._commands.get(name)
        if command_class is None:
            raise NoSuchCommand(name)
        return command_class(name, string_args)

emailcommands = EmailCommands()
