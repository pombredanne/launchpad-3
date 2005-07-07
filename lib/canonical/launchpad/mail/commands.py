# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['emailcommands']

from zope.component import getUtility
from zope.event import notify
from zope.exceptions import NotFoundError
from zope.interface import implements, providedBy
from zope.publisher.interfaces.browser import IBrowserRequest

from canonical.config import config
from canonical.launchpad.helpers import Snapshot, get_attribute_names
from canonical.launchpad.pathlookup import get_object
from canonical.launchpad.pathlookup.exceptions import PathStepNotFoundError
from canonical.launchpad.database import BugMessage, BugFactory, BugTaskSet
from canonical.launchpad.interfaces import (
        IProduct, IDistribution, IPersonSet, ISourcePackage, IBugEmailCommand,
        IBugEditEmailCommand, IEmailCommand, IBugSet, ILaunchBag, IBugTaskSet)
from canonical.launchpad.event import (
    SQLObjectModifiedEvent, SQLObjectToBeModifiedEvent, SQLObjectCreatedEvent)
from canonical.launchpad.event.interfaces import ISQLObjectCreatedEvent

from canonical.lp import decorates
from canonical.lp.dbschema import (
    BugSeverity, BugPriority, BugTaskStatus, BugSubscription)


class EmailCommand:
    """Represents a command.

    Both name the values in the args list are strings.
    """
    _subCommandNames = []
    _numberOfArguments = None

    def __init__(self, name, string_args):
        self.name = name
        self.string_args = string_args
        self._subCommandsToBeExecuted = []

    def _ensureNumberOfArguments(self):
        """Checks that the number of arguments is correct.
        
        A ValueError is raise if not.
        """
        if self._numberOfArguments is not None: 
            if self._numberOfArguments != len(self.string_args): 
                raise ValueError(
                    "'%s' expects exactly %s argument(s)." % (
                        self.name, self._numberOfArguments))
    
    def convertArguments(self):
        """Converts the string argument to Python objects.

        Returns a dict with names as keys, and the Python objects as
        values.
        """
        raise NotImplementedError

    def isSubCommand(self, command):
        """See IEmailCommand."""
        return command.name in self._subCommandNames

    def addSubCommandToBeExecuted(self, sub_command):
        """See IEmailCommand."""
        self.string_args += [sub_command.name] + sub_command.string_args


class BugEmailCommand(EmailCommand):
    implements(IBugEmailCommand)
    
    _numberOfArguments = 1

    def execute(self, message):
        self._ensureNumberOfArguments()
        bugid = self.string_args[0] 

        if bugid == 'new':
            bug = BugFactory(msg=message,
                             title=message.title,
                             owner=getUtility(ILaunchBag).user)
            return bug, SQLObjectCreatedEvent(bug)
        else:
            bugid = int(bugid)
            bug = getUtility(IBugSet).get(bugid)
            bug_message = BugMessage(bug=bug, message=message)
            return bug, None
    

class EditEmailCommand(EmailCommand):

    def execute(self, context, current_event):
        self._ensureNumberOfArguments()
        args = self.convertArguments()
        context_snapshot = Snapshot(
            context, providing=providedBy(context))
        if not ISQLObjectCreatedEvent.providedBy(current_event):
            notify(SQLObjectToBeModifiedEvent(context, args))
        edited = False
        for attr_name, attr_value in args.items():
            if getattr(context, attr_name) != attr_value:
                setattr(context, attr_name, attr_value)
                edited = True
        if edited and not ISQLObjectCreatedEvent.providedBy(current_event):
            event = SQLObjectModifiedEvent(
                context, context_snapshot, args.keys())
        else:
            event = None

        return context, event


class PrivateEmailCommand(EditEmailCommand):
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
            raise ValueError("'private' expects either 'yes' or 'no'")


class SubscribeEmailCommand(EmailCommand):
    implements(IBugEditEmailCommand)

    def execute(self, bug, current_event):
        string_args = self.string_args
        if len(string_args) == 2:
            subscription_name = string_args.pop()
            subscription = BugSubscription.items[subscription_name.upper()]
        else:
            subscription = BugSubscription.CC

        if len(string_args) == 1:
            person_name_or_email = string_args.pop()
            personset = getUtility(IPersonSet)
            person = personset.getByName(person_name_or_email)
            if person is None:
                person = personset.getByEmail(person_name_or_email)
            if person is None:
                raise ValueError(
                    "Couldn't find a person with the specified name or email:"
                    " %s" % person_name_or_email)
        elif len(string_args) == 0:
            # Subscribe the sender of the email.
            person = getUtility(ILaunchBag).user
        else:
            raise ValueError(
                "'subscribe' commands expects at most two arguments."
                " Got %s: %s" % (len(string_args), ' '.join(string_args)))
      
        if bug.isSubscribed(person):
            for bugsubscription in bug.subscriptions:
                if bugsubscription.person == person:
                    snapshot = Snapshot(
                        bugsubscription, names=['subscription'])
                    bugsubscription.subscription = subscription
                    event = SQLObjectModifiedEvent(
                        bugsubscription, snapshot, ['subscription'])
                    break

        else:
            bugsubscription = bug.subscribe(person, subscription)
            event = SQLObjectCreatedEvent(bugsubscription)

        return bugsubscription, event


class AffectsEmailCommand(EditEmailCommand):
    implements(IBugEditEmailCommand)
    _subCommandNames = ['status', 'assignee']

    def execute(self, bug, current_event):
        try:
            path = self.string_args.pop(0)
        except IndexError:
            raise ValueError(
                "'affects' command requires at least one argument.")
        bugtask, event = self.getBugTask(bug, path)
        
        return EditEmailCommand.execute(self, bugtask, event)

    def convertArguments(self):
        """See EmailCommand."""
        args = {}
        while len(self.string_args) > 0:
            # Get the sub command name.
            subcmd_name = self.string_args.pop(0)
            # Get the sub command's argument 
            try:
                subcmd_arg = self.string_args.pop(0)
            except IndexError:
                raise ValueError(
                    "'affects' sub command '%s' requires at least"
                    " one argument." % subcmd_name)
            try:
                command = emailcommands.get(subcmd_name, [subcmd_arg])
            except NoSuchCommand:
                raise ValueError(
                    "'affects' got an unexpected argument: %s" % subcmd_name)
            args.update(command.convertArguments())
        return args

    #XXX: This method should be moved to helpers.py or BugTaskSet.
    #     -- Bjorn Tillenius, 2005-06-10
    def getBugTask(self, bug, path):
        """Returns a bug task that's has the path as a target."""
        try:
            obj = get_object(path, path_only=True)
        except PathStepNotFoundError, error:
            raise ValueError(
                "'%s' couldn't be found in command 'affects %s'" % (
                    error.step, path))
            
        bugtask_params = {}
        if IProduct.providedBy(obj):
            bugtask_params['product'] = obj
        elif IDistribution.providedBy(obj):
            bugtask_params['distribution'] = obj
        elif ISourcePackage.providedBy(obj):
            bugtask_params['sourcepackagename'] = obj.sourcepackagename
            bugtask_params['distribution'] = obj.distribution

        bugtaskset = getUtility(IBugTaskSet) 
        bug_tasks = bugtaskset.search(
                bug=bug,
                distribution=bugtask_params.get('distribution'),
                distrorelease=bugtask_params.get('distrorelease'),
                product=bugtask_params.get('product'))
        bug_tasks = list(bug_tasks)
        if len(bug_tasks) > 1:
            # XXX: This shouldn't happen   
            raise ValueError('Found more than one bug task.')
        if len(bug_tasks) == 0:
            bugtask = bugtaskset.createTask(
                bug, getUtility(ILaunchBag).user, **bugtask_params)
            event = SQLObjectCreatedEvent(bugtask)
        else:
            bugtask = bug_tasks[0]
            event = None

        return bugtask, event



class AssigneeEmailCommand(EmailCommand):
    implements(IBugEditEmailCommand)
    
    _numberOfArguments = 1

    def convertArguments(self):
        """See EmailCommand."""
        person_name = self.string_args.pop()
        personset = getUtility(IPersonSet)
        person = personset.getByName(person_name)
        if person is None:
            raise ValueError(
                    "Couldn't find a person named '%s' in 'assignee %s'" % (
                        person_name, person_name))
        else:
            return {self.name: person}


class StatusEmailCommand(EditEmailCommand):
    implements(IBugEditEmailCommand)

    _numberOfArguments = 1

    def convertArguments(self):
        """See EmailCommand."""
        status_name = self.string_args.pop()
        try:
            return {self.name: BugTaskStatus.items[status_name.upper()]}
        except KeyError:
            raise ValueError(
                    "'status' expects any of: %s" % (
                        [item.name.lower() for item in BugTaskStatus], ))


class NoSuchCommand(KeyError):
    """A command with the given name couldn't be found."""

class EmailCommands:
    """A collection of email commands."""
    
    _commands = {
        'bug': BugEmailCommand,
        'private': PrivateEmailCommand,
        'subscribe': SubscribeEmailCommand,
        'affects': AffectsEmailCommand,
        'assignee': AssigneeEmailCommand,
        'status': StatusEmailCommand,
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
