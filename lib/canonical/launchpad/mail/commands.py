# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['emailcommands', 'get_error_message']

import os.path

from zope.component import getUtility
from zope.event import notify
from zope.interface import implements, providedBy

from canonical.launchpad.helpers import Snapshot
from canonical.launchpad.pathlookup import get_object
from canonical.launchpad.pathlookup.exceptions import PathStepNotFoundError
from canonical.launchpad.vocabularies import ValidPersonOrTeamVocabulary
from canonical.launchpad.interfaces import (
        IProduct, IDistribution, IDistroRelease, IPersonSet,
        ISourcePackage, IBugEmailCommand, IBugTaskEmailCommand,
        IBugEditEmailCommand, IBugTaskEditEmailCommand, IBugSet, ILaunchBag,
        IBugTaskSet, BugTaskSearchParams, IBugTarget, IMessageSet,
        IDistributionSourcePackage, EmailProcessingError, NotFoundError)
from canonical.launchpad.event import (
    SQLObjectModifiedEvent, SQLObjectToBeModifiedEvent, SQLObjectCreatedEvent)
from canonical.launchpad.event.interfaces import (
    ISQLObjectCreatedEvent, ISQLObjectModifiedEvent)

from canonical.lp.dbschema import (
    BugTaskStatus, BugTaskSeverity, BugTaskPriority)


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

    def convertArguments(self):
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
            if message.contents.strip() == '':
                 raise EmailProcessingError(
                    get_error_message('no-affects-target-on-submit.txt'))

            bug = getUtility(IBugSet).createBug(
                msg=message,
                title=message.title,
                owner=getUtility(ILaunchBag).user)
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
        args = self.convertArguments()

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
                setattr(context, attr_name, attr_value)
                edited = True
        if edited and not ISQLObjectCreatedEvent.providedBy(current_event):
            edited_fields.update(args.keys())
            current_event = SQLObjectModifiedEvent(
                context, context_snapshot, list(edited_fields))

        return context, current_event


class PrivateEmailCommand(EditEmailCommand):
    """Marks a bug public or private."""

    implements(IBugEditEmailCommand)

    _numberOfArguments = 1

    def convertArguments(self):
        """See EmailCommand."""
        private_arg = self.string_args[0]
        if private_arg == 'yes':
            return {'private': True}
        elif private_arg == 'no':
            return {'private': False}
        else:
            raise EmailProcessingError(
                get_error_message('private-parameter-mismatch.txt'))


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

    def convertArguments(self):
        """See EmailCommand."""
        return {'title': self.string_args[0]}


class AffectsEmailCommand(EmailCommand):
    """Either creates a new task, or edits an existing task."""

    implements(IBugTaskEmailCommand)
    _subCommandNames = ['status', 'severity', 'assignee', 'priority']

    def execute(self, bug):
        """See IEmailCommand."""
        string_args = list(self.string_args)
        try:
            path = string_args.pop(0)
        except IndexError:
            raise EmailProcessingError(
                get_error_message('affects-no-arguments.txt'))
        try:
            path_target = get_object(path, path_only=True)
        except PathStepNotFoundError, error:
            raise EmailProcessingError(
                get_error_message(
                    'affects-path-not-found.txt',
                    pathstep_not_found=error.step, path=path))
        if ISourcePackage.providedBy(path_target):
            bug_target = path_target.distribution
        else:
            bug_target = path_target

        bugtask = self.getBugTask(bug, bug_target)
        if bugtask is None:
            bugtask = self._create_bug_task(bug, bug_target)
            event = SQLObjectCreatedEvent(bugtask)
        else:
            event = None

        # The user may change the source package by issuing
        # 'affects /distros/$distro/$sourcepackage'. Let's handle that here.
        if ISourcePackage.providedBy(path_target):
            bugtask_before_edit = Snapshot(bugtask, names='sourcepackagename')
            if bugtask.sourcepackagename != path_target.sourcepackagename:
                bugtask.sourcepackagename = path_target.sourcepackagename
            event = SQLObjectModifiedEvent(
                bugtask, bugtask_before_edit, ['sourcepackagename'])

        # Process the sub commands.
        while len(string_args) > 0:
            # Get the sub command name.
            subcmd_name = string_args.pop(0)
            # Get the sub command's argument
            try:
                subcmd_args = [string_args.pop(0)]
            except IndexError:
                # Let the sub command handle the error.
                subcmd_args = []

            if subcmd_name not in self._subCommandNames:
                raise EmailProcessingError(
                    get_error_message(
                        'affects-unexpected-argument.txt',
                        argument=subcmd_name))

            command = emailcommands.get(subcmd_name, subcmd_args)
            bugtask, event = command.execute(bugtask, event)

        return bugtask, event

    def _create_bug_task(self, bug, bug_target):
        """Creates a new bug task with bug_target as the target."""
        # XXX kiko: we could fix this by making createTask be a method on
        # IBugTarget, but I'm not going to do this now. Bug 1690
        bugtaskset = getUtility(IBugTaskSet)
        user = getUtility(ILaunchBag).user
        if IProduct.providedBy(bug_target):
            return bugtaskset.createTask(bug, user, product=bug_target)
        elif IDistribution.providedBy(bug_target):
            return bugtaskset.createTask(bug, user, distribution=bug_target)
        elif IDistroRelease.providedBy(bug_target):
            return bugtaskset.createTask(bug, user, distrorelease=bug_target)
        elif IDistributionSourcePackage.providedBy(bug_target):
            return bugtaskset.createTask(
                bug, user, distribution=bug_target.distribution,
                sourcepackagename=bug_target.sourcepackagename)
        else:
            assert False, "Not a valid bug target: %r" % bug_target


    #XXX: This method should be moved to helpers.py or BugTaskSet.
    #     -- Bjorn Tillenius, 2005-06-10
    def getBugTask(self, bug, target):
        """Returns a bug task that has the path as a target.

        Returns None if no such bugtask is found.
        """
        assert IBugTarget.providedBy(target), target
        user = getUtility(ILaunchBag).user

        # Listify the results in order to avoid unnecessary SQL queries.
        bug_tasks = list(
            target.searchTasks(BugTaskSearchParams(user, bug=bug)))

        assert len(bug_tasks) <= 1, 'Found more than one bug task.'
        if len(bug_tasks) == 0:
            return None
        else:
            bugtask = bug_tasks[0]

        return bugtask


class AssigneeEmailCommand(EditEmailCommand):
    """Assigns someone to the bug."""

    implements(IBugTaskEditEmailCommand)

    _numberOfArguments = 1

    def convertArguments(self):
        """See EmailCommand."""
        person_name_or_email = self.string_args[0]
        valid_person_vocabulary = ValidPersonOrTeamVocabulary()
        try:
            person_term = valid_person_vocabulary.getTermByToken(
                person_name_or_email)
        except LookupError:
            raise EmailProcessingError(
                get_error_message(
                    'no-such-person.txt', name_or_email=person_name_or_email))

        return {self.name: person_term.value}


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

    def convertArguments(self):
        """See EmailCommand."""
        item_name = self.string_args[0]
        dbschema = self.dbschema
        try:
            return {self.name: dbschema.items[item_name.upper()]}
        except KeyError:
            possible_items = [item.name.lower() for item in dbschema.items]
            possible_values = ', '.join(possible_items)
            raise EmailProcessingError(
                    get_error_message(
                        'dbschema-command-wrong-argument.txt',
                         command_name=self.name,
                         arguments=possible_values,
                         example_argument=possible_items[0]))


class StatusEmailCommand(DBSchemaEditEmailCommand):
    """Changes a bug task's status."""
    dbschema = BugTaskStatus


class SeverityEmailCommand(DBSchemaEditEmailCommand):
    """Changes a bug task's severity."""
    dbschema = BugTaskSeverity


class PriorityEmailCommand(DBSchemaEditEmailCommand):
    """Changes the bug task's priority."""
    dbschema = BugTaskPriority


class NoSuchCommand(KeyError):
    """A command with the given name couldn't be found."""


class EmailCommands:
    """A collection of email commands."""

    _commands = {
        'bug': BugEmailCommand,
        'private': PrivateEmailCommand,
        'summary': SummaryEmailCommand,
        'subscribe': SubscribeEmailCommand,
        'unsubscribe': UnsubscribeEmailCommand,
        'affects': AffectsEmailCommand,
        'assignee': AssigneeEmailCommand,
        'status': StatusEmailCommand,
        'priority': PriorityEmailCommand,
        'severity': SeverityEmailCommand,
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
