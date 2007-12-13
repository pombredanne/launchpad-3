# Copyright 2005-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'DistributionSourcePackageNavigation',
    'DistributionSourcePackageSOP',
    'DistributionSourcePackageFacets',
    'DistributionSourcePackageNavigation',
    'DistributionSourcePackageOverviewMenu',
    'DistributionSourcePackageBugContactsView',
    'DistributionSourcePackageView'
    ]

from operator import attrgetter

from zope.component import getUtility
from zope.formlib import form
from zope.schema import Choice, List
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary

from canonical.cachedproperty import cachedproperty
from canonical.launchpad import _
from canonical.launchpad.interfaces import (
    DuplicateBugContactError, IDistributionSourcePackage,
    IDistributionSourcePackageManageBugcontacts, IPackagingUtil)
from canonical.launchpad.browser.bugtask import BugTargetTraversalMixin
from canonical.launchpad.browser.launchpad import StructuralObjectPresentation
from canonical.launchpad.browser.questiontarget import (
        QuestionTargetFacetMixin, QuestionTargetTraversalMixin)
from canonical.launchpad.webapp import (
    action, StandardLaunchpadFacets, Link, ApplicationMenu,
    GetitemNavigation, canonical_url, redirection, LaunchpadFormView,
    custom_widget)
from canonical.launchpad.webapp.authorization import check_permission
from canonical.widgets import LabeledMultiCheckBoxWidget


class DistributionSourcePackageSOP(StructuralObjectPresentation):

    def getIntroHeading(self):
        return self.context.distribution.title + ' source package:'

    def getMainHeading(self):
        return self.context.name

    def listChildren(self, num):
        # XXX mpt 2006-10-04: package releases, most recent first
        return self.context.releases

    def listAltChildren(self, num):
        return None


class DistributionSourcePackageFacets(QuestionTargetFacetMixin,
                                      StandardLaunchpadFacets):

    usedfor = IDistributionSourcePackage
    enable_only = ['overview', 'bugs', 'answers']


class DistributionSourcePackageOverviewMenu(ApplicationMenu):

    usedfor = IDistributionSourcePackage
    facet = 'overview'
    links = ['managebugcontacts', 'publishinghistory']

    def managebugcontacts(self):
        return Link('+subscribe', 'Subscribe to bug mail', icon='edit')

    def publishinghistory(self):
        return Link('+publishinghistory', 'Show publishing history')


class DistributionSourcePackageBugsMenu(
        DistributionSourcePackageOverviewMenu):

    usedfor = IDistributionSourcePackage
    facet = 'bugs'
    links = ['managebugcontacts']


class DistributionSourcePackageNavigation(GetitemNavigation,
    BugTargetTraversalMixin, QuestionTargetTraversalMixin):

    usedfor = IDistributionSourcePackage

    redirection("+editbugcontact", "+subscribe")

    def breadcrumb(self):
        return self.context.sourcepackagename.name


class DistributionSourcePackageBugContactsView(LaunchpadFormView):
    """View class for bug contact settings."""

    schema = IDistributionSourcePackageManageBugcontacts

    custom_widget('bugmail_contact_team', LabeledMultiCheckBoxWidget)
    custom_widget('remove_other_bugcontacts', LabeledMultiCheckBoxWidget)

    def setUpFields(self):
        """See LaunchpadFormView."""
        LaunchpadFormView.setUpFields(self)
        team_contacts = self._createTeamBugContactsField()
        if team_contacts:
            self.form_fields += form.Fields(team_contacts)
        if self.userIsDistributionDriver():
            add_other = form.Fields(self._createAddOtherBugContactField())
            self.form_fields += add_other
            remove_other = self._createRemoveOtherBugContactsField()
            if remove_other:
                self.form_fields += form.Fields(remove_other)

    def _createTeamBugContactsField(self):
        """Create field with a list of the teams the user is a member of.

        Return a FormField instance, if the user is a member of at least
        one team, else return None.
        """
        teams = self.user_teams
        if not teams:
            return None
        teams.sort(key=attrgetter('displayname'))
        terms = [
            SimpleTerm(team, team.name, team.displayname)
            for team in teams]
        team_vocabulary = SimpleVocabulary(terms)
        team_contacts_field = List(
            __name__='bugmail_contact_team',
            title=u'Team bug contacts',
            description=(u'You can add the teams of which you are an '
                          'administrator to the bug contacts.'),
            value_type=Choice(vocabulary=team_vocabulary),
            required=False)
        return form.FormField(
            team_contacts_field,
            custom_widget=self.custom_widgets['bugmail_contact_team'])

    def _createRemoveOtherBugContactsField(self):
        """Create a field with a list of subscribers.

        Return a FormField instance, if bug contacts exist that can
        be removed, else return None.
        """
        teams = set(self.user_teams)
        other_contacts = set(
            contact.bugcontact for contact in self.context.bugcontacts)

        # Teams and the current user have their own UI elements. Remove
        # them to avoid duplicates.
        other_contacts.difference_update(teams)
        other_contacts.discard(self.user)

        if not other_contacts:
            return None

        other_contacts = sorted(other_contacts, key=attrgetter('displayname'))

        terms = [
            SimpleTerm(contact, contact.name, contact.displayname)
            for contact in other_contacts]

        contacts_vocabulary = SimpleVocabulary(terms)
        other_contacts_field = List(
            __name__='remove_other_bugcontacts',
            title=u'Remove bug contacts',
            value_type=Choice(vocabulary=contacts_vocabulary),
            required=False)
        return form.FormField(
            other_contacts_field,
            custom_widget=self.custom_widgets['remove_other_bugcontacts'])

    def _createAddOtherBugContactField(self):
        """Create a field for a new bug contact."""
        new_bugcontact_field = Choice(
            __name__='new_bugcontact',
            title=u'Add other bug contact',
            vocabulary='ValidPersonOrTeam',
            required=False)
        return form.FormField(new_bugcontact_field)

    @property
    def initial_values(self):
        """See `GeneralFormView`."""
        teams = set(self.user_teams)
        bugcontact_teams = set(team
                               for team in teams
                               if self.context.isBugContact(team))
        return {
            'make_me_a_bugcontact': self.currentUserIsBugContact(),
            'bugmail_contact_team': bugcontact_teams
            }

    def currentUserIsBugContact(self):
        """Return True, if the current user is a bug contact."""
        return self.context.isBugContact(self.user)

    @action(u'Save these changes', name='save')
    def save_action(self, action, data):
        """Process the bugmail settings submitted by the user."""
        self._handleUserSubscription(data)
        self._handleTeamSubscriptions(data)
        self._handleDriverChanges(data)
        self.next_url = canonical_url(self.context) + '/+subscribe'

    def _handleUserSubscription(self, data):
        """Process the bugmail settings for the use."""
        pkg = self.context
        # pkg.addBugContact raises an exception if called for an already
        # subscribed person, and pkg.removeBugContact raises an exception
        # for a non-subscriber, hence call these methods only, if the
        # subscription status changed.
        is_bugcontact = self.context.isBugContact(self.user)
        make_bugcontact = data['make_me_a_bugcontact']
        if (not is_bugcontact) and make_bugcontact:
            pkg.addBugContact(self.user)
            self.request.response.addNotification(
                "You have been successfully subscribed to all bugmail "
                "for %s" % pkg.displayname)
        elif is_bugcontact and not make_bugcontact:
            pkg.removeBugContact(self.user)
            self.request.response.addNotification(
                "You have been removed as a bug contact for %s. You "
                "will no longer automatically receive bugmail for this "
                "package." % pkg.displayname)
        else:
            # The subscription status did not change: nothing to do.
            pass

    def _handleTeamSubscriptions(self, data):
        """Process the bugmail settings for teams."""
        form_selected_teams = data.get('bugmail_contact_team', None)
        if form_selected_teams is None:
            return

        pkg = self.context
        teams = set(self.user_teams)
        form_selected_teams = teams & set(form_selected_teams)
        subscriptions = set(
            team for team in teams if self.context.isBugContact(team))

        for team in form_selected_teams - subscriptions:
            pkg.addBugContact(team)
            self.request.response.addNotification(
                'The "%s" team was successfully subscribed to all bugmail '
                'in %s' % (team.displayname, self.context.displayname))

        for team in subscriptions - form_selected_teams:
            pkg.removeBugContact(team)
            self.request.response.addNotification(
                'The "%s" team was successfully unsubscribed from all '
                'bugmail in %s' % (
                    team.displayname, self.context.displayname))

    def _handleDriverChanges(self, data):
        """Process the bugmail settings for other persons."""
        if not self.userIsDistributionDriver():
            return

        pkg = self.context
        new_bugcontact = data['new_bugcontact']
        if new_bugcontact is not None:
            try:
                pkg.addBugContact(new_bugcontact)
            except DuplicateBugContactError:
                self.request.response.addNotification(
                    '"%s" is already subscribed to all bugmail '
                    'in %s' % (
                        new_bugcontact.displayname,
                        self.context.displayname))
            else:
                self.request.response.addNotification(
                    '"%s" was successfully subscribed to all bugmail '
                    'in %s' % (
                        new_bugcontact.displayname,
                        self.context.displayname))

        contacts_to_remove = data.get('remove_other_bugcontacts', [])
        for contact in contacts_to_remove:
            pkg.removeBugContact(contact)
            self.request.response.addNotification(
                '"%s" was successfully unsubscribed from all bugmail '
                'in %s' % (
                    contact.displayname, self.context.displayname))

    def userIsDistributionDriver(self):
        """Has the current user driver permissions?"""
        return check_permission("launchpad.Driver", self.context.distribution)

    @cachedproperty
    def user_teams(self):
        """Return the teams that the current user is an administrator of."""
        return list(self.user.getAdministratedTeams())


class DistributionSourcePackageView(LaunchpadFormView):

    def setUpFields(self):
        """See `LaunchpadFormView`."""
        # No schema is set in this form, because all fields are created with
        # custom vocabularies. So we must not call the inherited setUpField
        # method.
        self.form_fields = self._createPackagingField()

    @property
    def can_delete_packaging(self):
        """Whether the user can delete existing packaging links."""
        return self.user is not None

    def _createPackagingField(self):
        """Create a field to specify a Packaging association.

        Create a contextual vocabulary that can specify one of the Packaging
        associated to this DistributionSourcePackage.
        """
        terms = []
        for sourcepackage in self.context.get_distroseries_packages():
            packaging = sourcepackage.direct_packaging
            if packaging is None:
                continue
            terms.append(SimpleTerm(packaging, packaging.id))
        return form.Fields(
            Choice(__name__='packaging', vocabulary=SimpleVocabulary(terms),
                   required=True))

    def _renderHiddenPackagingField(self, packaging):
        """Render a hidden input that fills in the packaging field."""
        if not self.can_delete_packaging:
            return None
        vocabulary = self.form_fields['packaging'].field.vocabulary
        return '<input type="hidden" name="field.packaging" value="%s" />' % (
            vocabulary.getTerm(packaging).token)

    def renderDeletePackagingAction(self):
        """Render a submit input for the delete_packaging_action."""
        assert self.can_delete_packaging, 'User cannot delete Packaging.'
        return ('<input type="submit" class="button" value="Delete Link" '
                'name="%s"/>' % (self.delete_packaging_action.__name__,))

    def handleDeletePackagingError(self, action, data, errors):
        """Handle errors on package link deletion.

        If 'packaging' is not set in the form data, we assume that means the
        provided Packaging id was not found, which should only happen if the
        same Packaging object was concurrently deleted. In this case, we want
        to display a more informative error message than the default 'Invalid
        value'.
        """
        if data.get('packaging') is None:
            self.setFieldError(
                'packaging',
                _("This upstream association was deleted already."))

    @action(_("Delete Link"), name='delete_packaging',
            failure=handleDeletePackagingError)
    def delete_packaging_action(self, action, data):
        """Delete a Packaging association."""
        packaging = data['packaging']
        productseries = packaging.productseries
        distroseries = packaging.distroseries
        getUtility(IPackagingUtil).deletePackaging(
            productseries, packaging.sourcepackagename, distroseries)
        self.request.response.addNotification(
            _("Removed upstream association between ${product} "
              "${productseries} and ${distroseries}.", mapping=dict(
              product=productseries.product.displayname,
              productseries=productseries.displayname,
              distroseries=distroseries.displayname)))

    def version_listing(self):
        result = []
        for sourcepackage in self.context.get_distroseries_packages():
            packaging = sourcepackage.direct_packaging
            if packaging is None:
                delete_packaging_form_id = None
                packaging_field = None
            else:
                delete_packaging_form_id = "delete_%s_%s_%s" % (
                    packaging.distroseries.name,
                    packaging.productseries.product.name,
                    packaging.productseries.name)
                packaging_field = self._renderHiddenPackagingField(packaging)
            series_result = []
            for published in \
                sourcepackage.published_by_pocket.iteritems():
                for drspr in published[1]:
                    series_result.append({
                        'series': sourcepackage.distroseries,
                        'pocket': published[0].name.lower(),
                        'package': drspr,
                        'packaging': packaging,
                        'delete_packaging_form_id': delete_packaging_form_id,
                        'packaging_field': packaging_field,
                        'sourcepackage': sourcepackage
                        })
            for row in range(len(series_result)-1, 0, -1):
                for column in ['series', 'pocket', 'package', 'packaging',
                               'packaging_field', 'sourcepackage']:
                    if (series_result[row][column] ==
                            series_result[row-1][column]):
                        series_result[row][column] = None
            for row in series_result:
                result.append(row)
        return result
