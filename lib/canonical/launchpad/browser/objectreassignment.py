# Copyright 2007 Canonical Ltd.  All rights reserved.

"""A view for changing the owner or registrant of an object.

This view needs to be refactored to use the Launchpad form infrastructure.
See bug 151161.
"""

__metaclass__ = type
__all__ = ["ObjectReassignmentView"]


from zope.app.form.interfaces import (
    IInputWidget, ConversionError, WidgetInputError)
from zope.app.form.utility import setUpWidgets
from zope.component import getUtility

from canonical.launchpad.interfaces import (
    ILaunchBag, IObjectReassignment, IPersonSet)
from canonical.launchpad.validators.name import valid_name


class ObjectReassignmentView:
    """A view class used when reassigning an object that implements IHasOwner.

    By default we assume that the owner attribute is IHasOwner.owner and the
    vocabulary for the owner widget is ValidPersonOrTeam (which is the one
    used in IObjectReassignment). If any object has special needs, it'll be
    necessary to subclass ObjectReassignmentView and redefine the schema
    and/or ownerOrMaintainerAttr attributes.

    Subclasses can also specify a callback to be called after the reassignment
    takes place. This callback must accept three arguments (in this order):
    the object whose owner is going to be changed, the old owner and the new
    owner.

    Also, if the object for which you're using this view doesn't have a
    displayname or name attribute, you'll have to subclass it and define the
    contextName property in your subclass.
    """

    ownerOrMaintainerAttr = 'owner'
    schema = IObjectReassignment
    callback = None

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.user = getUtility(ILaunchBag).user
        self.errormessage = ''
        setUpWidgets(self, self.schema, IInputWidget)

    @property
    def ownerOrMaintainer(self):
        return getattr(self.context, self.ownerOrMaintainerAttr)

    @property
    def contextName(self):
        return self.context.displayname or self.context.name

    nextUrl = '.'

    def processForm(self):
        if self.request.method == 'POST':
            self.changeOwner()

    def changeOwner(self):
        """Change the owner of self.context to the one choosen by the user."""
        newOwner = self._getNewOwner()
        if newOwner is None:
            return

        if not self.isValidOwner(newOwner):
            return

        oldOwner = getattr(self.context, self.ownerOrMaintainerAttr)
        setattr(self.context, self.ownerOrMaintainerAttr, newOwner)
        if callable(self.callback):
            self.callback(self.context, oldOwner, newOwner)
        self.request.response.redirect(self.nextUrl)

    def isValidOwner(self, newOwner):
        """Check whether the new owner is acceptable for the context object.

        If it's not acceptable, return False and assign an error message to
        self.errormessage to inform the user.
        """
        return True

    def _getNewOwner(self):
        """Return the new owner for self.context, as specified by the user.

        If anything goes wrong, return None and assign an error message to
        self.errormessage to inform the user about what happened.
        """
        personset = getUtility(IPersonSet)
        request = self.request
        owner_name = request.form.get(self.owner_widget.name)
        if not owner_name:
            self.errormessage = (
                "You have to specify the name of the person/team that's "
                "going to be the new %s." % self.ownerOrMaintainerAttr)
            return None

        if request.form.get('existing') == 'existing':
            try:
                # By getting the owner using getInputValue() we make sure
                # it's valid according to the vocabulary of self.schema's
                # owner widget.
                owner = self.owner_widget.getInputValue()
            except WidgetInputError:
                self.errormessage = (
                    "The person/team named '%s' is not a valid owner for %s."
                    % (owner_name, self.contextName))
                return None
            except ConversionError:
                self.errormessage = (
                    "There's no person/team named '%s' in Launchpad."
                    % owner_name)
                return None
        else:
            if personset.getByName(owner_name):
                self.errormessage = (
                    "There's already a person/team with the name '%s' in "
                    "Launchpad. Please choose a different name or select "
                    "the option to make that person/team the new owner, "
                    "if that's what you want." % owner_name)
                return None

            if not valid_name(owner_name):
                self.errormessage = (
                    "'%s' is not a valid name for a team. Please make sure "
                    "it contains only the allowed characters and no spaces."
                    % owner_name)
                return None

            owner = personset.newTeam(
                self.user, owner_name, owner_name.capitalize())

        return owner


