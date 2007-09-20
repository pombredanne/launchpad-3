# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['TeamMembership', 'TeamMembershipSet', 'TeamParticipation']

from datetime import datetime, timedelta
import itertools
import pytz

from zope.component import getUtility
from zope.interface import implements

from sqlobject import ForeignKey, StringCol

from canonical.database.sqlbase import (
    flush_database_updates, SQLBase, sqlvalues)
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol

from canonical.config import config

from canonical.launchpad.mail import simple_sendmail, format_address
from canonical.launchpad.mailnotification import MailWrapper
from canonical.launchpad.helpers import (
    get_email_template, contactEmailAddresses)
from canonical.launchpad.interfaces import (
    DAYS_BEFORE_EXPIRATION_WARNING_IS_SENT, ILaunchpadCelebrities,
    IMailingListSubscriptionSet, ITeamMembership, ITeamParticipation,
    ITeamMembershipSet, TeamMembershipRenewalPolicy, TeamMembershipStatus)
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.tales import DurationFormatterAPI


class TeamMembership(SQLBase):
    """See `ITeamMembership`."""

    implements(ITeamMembership)

    _table = 'TeamMembership'
    _defaultOrder = 'id'

    team = ForeignKey(dbName='team', foreignKey='Person', notNull=True)
    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)
    reviewer = ForeignKey(dbName='reviewer', foreignKey='Person', default=None)
    status = EnumCol(
        dbName='status', notNull=True, enum=TeamMembershipStatus)
    datejoined = UtcDateTimeCol(
        dbName='datejoined', default=UTC_NOW, notNull=True)
    dateexpires = UtcDateTimeCol(dbName='dateexpires', default=None)
    reviewercomment = StringCol(dbName='reviewercomment', default=None)

    @property
    def statusname(self):
        """See `ITeamMembership`."""
        return self.status.title

    def isExpired(self):
        """See `ITeamMembership`."""
        return self.status == TeamMembershipStatus.EXPIRED

    def canBeRenewedByMember(self):
        """See `ITeamMembership`."""
        ondemand = TeamMembershipRenewalPolicy.ONDEMAND
        admin = TeamMembershipStatus.APPROVED
        approved = TeamMembershipStatus.ADMIN
        date_limit = datetime.now(pytz.timezone('UTC')) + timedelta(
            days=DAYS_BEFORE_EXPIRATION_WARNING_IS_SENT)
        return (self.status in (admin, approved)
                and self.team.renewal_policy == ondemand
                and self.dateexpires is not None
                and self.dateexpires < date_limit)

    def sendSelfRenewalNotification(self):
        """See `ITeamMembership`."""
        team = self.team
        member = self.person
        assert team.renewal_policy == TeamMembershipRenewalPolicy.ONDEMAND

        from_addr = format_address(
            "Launchpad Team Membership Notifier", config.noreply_from_address)
        replacements = {'member_name': member.unique_displayname,
                        'team_name': team.unique_displayname,
                        'dateexpires': self.dateexpires.strftime('%Y-%m-%d')}
        subject = ('Launchpad: renewed %s as member of %s'
                   % (member.name, team.name))
        template = get_email_template('membership-member-renewed.txt')
        msg = MailWrapper().format(template % replacements)
        admins_addrs = self.team.getTeamAdminsEmailAddresses()
        for address in admins_addrs:
            simple_sendmail(from_addr, address, subject, msg)

    def sendAutoRenewalNotification(self):
        """See `ITeamMembership`."""
        team = self.team
        member = self.person
        assert team.renewal_policy == TeamMembershipRenewalPolicy.AUTOMATIC

        from_addr = format_address(
            "Launchpad Team Membership Notifier", config.noreply_from_address)
        replacements = {'member_name': member.unique_displayname,
                        'team_name': team.unique_displayname,
                        'dateexpires': self.dateexpires.strftime('%Y-%m-%d')}
        subject = ('Launchpad: renewed %s as member of %s'
                   % (member.name, team.name))

        if member.isTeam():
            member_addrs = contactEmailAddresses(member.teamowner)
            template_name = 'membership-auto-renewed-impersonal.txt'
        else:
            template_name = 'membership-auto-renewed-personal.txt'
            member_addrs = contactEmailAddresses(member)
        template = get_email_template(template_name)
        msg = MailWrapper().format(template % replacements)
        for address in member_addrs:
            simple_sendmail(from_addr, address, subject, msg)

        template_name = 'membership-auto-renewed-impersonal.txt'
        admins_addrs = self.team.getTeamAdminsEmailAddresses()
        admins_addrs = set(admins_addrs).difference(member_addrs)
        template = get_email_template(template_name)
        msg = MailWrapper().format(template % replacements)
        for address in admins_addrs:
            simple_sendmail(from_addr, address, subject, msg)

    def canChangeExpirationDate(self, person):
        """See `ITeamMembership`."""
        person_is_admin = self.team in person.getAdministratedTeams()
        if (person.inTeam(self.team.teamowner) or
                person.inTeam(getUtility(ILaunchpadCelebrities).admin)):
            # The team owner and Launchpad admins can change the expiration
            # date of anybody's membership.
            return True
        elif person_is_admin and person != self.person:
            # A team admin can only change other member's expiration date.
            return True
        else:
            return False

    def setExpirationDate(self, date, user):
        """See `ITeamMembership`."""
        if date == self.dateexpires:
            return

        assert self.canChangeExpirationDate(user), (
            "This user can't change this membership's expiration date.")
        assert date is None or date > datetime.now(pytz.timezone('UTC')), (
            "The given expiration date must be None or be in the future: %s"
            % date.strftime('%Y-%m-%d'))
        self.dateexpires = date
        self.reviewer = user

    def sendExpirationWarningEmail(self):
        """See `ITeamMembership`."""
        assert self.dateexpires is not None, (
            'This membership has no expiration date')
        assert self.dateexpires > datetime.now(pytz.timezone('UTC')), (
            "This membership's expiration date must be in the future: %s"
            % self.dateexpires.strftime('%Y-%m-%d'))
        member = self.person
        if member.isTeam():
            recipient = member.teamowner
            templatename = 'membership-expiration-warning-impersonal.txt'
        else:
            recipient = member
            templatename = 'membership-expiration-warning-personal.txt'
        team = self.team
        subject = 'Launchpad: %s team membership about to expire' % team.name

        if team.renewal_policy == TeamMembershipRenewalPolicy.ONDEMAND:
            how_to_renew = (
                "If you want, you can renew this membership at\n"
                "<%s/+expiringmembership/%s>"
                % (canonical_url(member), team.name))
        elif not self.canChangeExpirationDate(recipient):
            admins_names = []
            admins = team.getDirectAdministrators()
            assert admins.count() >= 1
            if admins.count() == 1:
                admin = admins[0]
                how_to_renew = (
                    "To prevent this membership from expiring, you should"
                    "contact the\nteam's administrator, %s.\n<%s>"
                    % (admin.unique_displayname, canonical_url(admin)))
            else:
                for admin in admins:
                    # Do not tell the member to contact himself when he can't
                    # extend his membership.
                    if admin != member:
                        admins_names.append(
                            "%s <%s>"
                            % (admin.unique_displayname, canonical_url(admin)))

                how_to_renew = (
                    "To prevent this membership from expiring, you should get "
                    "in touch\nwith one of the team's administrators:\n")
                how_to_renew += "\n".join(admins_names)
        else:
            how_to_renew = (
                "To stay a member of this team you should extend your "
                "membership at\n<%s/+member/%s>"
                % (canonical_url(team), member.name))

        to_addrs = contactEmailAddresses(recipient)
        formatter = DurationFormatterAPI(
            self.dateexpires - datetime.now(pytz.timezone('UTC')))
        replacements = {
            'member_name': member.unique_displayname,
            'member_displayname': member.displayname,
            'team_url': canonical_url(team),
            'how_to_renew': how_to_renew,
            'team_name': team.unique_displayname,
            'expiration_date': self.dateexpires.strftime('%Y-%m-%d'),
            'approximate_duration': formatter.approximateduration()}

        msg = get_email_template(templatename) % replacements
        from_addr = format_address(
            "Launchpad Team Membership Notifier", config.noreply_from_address)
        simple_sendmail(from_addr, to_addrs, subject, msg)

    def setStatus(self, status, reviewer, reviewercomment=None):
        """See `ITeamMembership`."""
        if status == self.status:
            return

        approved = TeamMembershipStatus.APPROVED
        admin = TeamMembershipStatus.ADMIN
        expired = TeamMembershipStatus.EXPIRED
        declined = TeamMembershipStatus.DECLINED
        deactivated = TeamMembershipStatus.DEACTIVATED
        proposed = TeamMembershipStatus.PROPOSED
        invited = TeamMembershipStatus.INVITED
        invitation_declined = TeamMembershipStatus.INVITATION_DECLINED

        # Flush the cache used by the Person.inTeam method
        self.person._inTeam_cache = {}

        # Make sure the transition from the current status to the given one
        # is allowed. All allowed transitions are in the TeamMembership spec.
        state_transition = {
            admin: [approved, expired, deactivated],
            approved: [admin, expired, deactivated],
            deactivated: [proposed, approved, invited],
            expired: [proposed, approved, invited],
            proposed: [approved, admin, declined],
            declined: [proposed, approved],
            invited: [approved, invitation_declined],
            invitation_declined: [invited, approved, admin]}
        assert self.status in state_transition, (
            "Unknown status: %s" % self.status.name)
        assert status in state_transition[self.status], (
            "Bad state trasition from %s to %s"
            % (self.status.name, status.name))

        old_status = self.status
        self.status = status
        self.reviewer = reviewer
        self.reviewercomment = reviewercomment

        if (old_status not in [admin, approved]
            and status in [admin, approved]):
            # Inactive member has become active; update datejoined
            self.datejoined = datetime.now(pytz.timezone('UTC'))

        if status in [admin, approved]:
            _fillTeamParticipation(self.person, self.team)
        else:
            _cleanTeamParticipation(self.person, self.team)

        # Flush all updates to ensure any subsequent calls to this method on
        # the same transaction will operate on the correct data.  That is the
        # case with our script to expire team memberships.
        flush_database_updates()

        # When a member proposes himself, a more detailed notification is
        # sent to the team admins by a subscriber of JoinTeamEvent; that's
        # why we don't send anything here.
        if self.person == self.reviewer and self.status == proposed:
            return

        self._sendStatusChangeNotification(old_status)

    def _sendStatusChangeNotification(self, old_status):
        """Send a status change notification to all team admins and the
        member whose membership's status changed.
        """
        from_addr = format_address(
            "Launchpad Team Membership Notifier", config.noreply_from_address)
        new_status = self.status
        admins_emails = self.team.getTeamAdminsEmailAddresses()
        # self.person might be a team, so we can't rely on its preferredemail.
        member_email = contactEmailAddresses(self.person)
        # Make sure we don't send the same notification twice to anybody.
        for email in member_email:
            if email in admins_emails:
                admins_emails.remove(email)

        team = self.team
        member = self.person
        reviewer = self.reviewer

        if reviewer != member:
            reviewer_name = reviewer.unique_displayname
        else:
            # The user himself changed his membership.
            reviewer_name = 'the user himself'

        if self.reviewercomment:
            comment = ("Comment:\n%s\n\n" % self.reviewercomment.strip())
        else:
            comment = ""

        replacements = {
            'member_name': member.unique_displayname,
            'team_name': team.unique_displayname,
            'old_status': old_status.title,
            'new_status': new_status.title,
            'reviewer_name': reviewer_name,
            'comment': comment}

        template_name = 'membership-statuschange'
        subject = ('Launchpad: Membership change: %(member)s in %(team)s'
                   % {'member': member.name, 'team': team.name})
        if new_status == TeamMembershipStatus.EXPIRED:
            template_name = 'membership-expired'
            subject = (
                'Launchpad: %s expired from %s' % (member.name, team.name))
        elif (new_status == TeamMembershipStatus.APPROVED and
              old_status != TeamMembershipStatus.ADMIN):
            subject = 'Launchpad: %s added to %s' % (member.name, team.name)
            if old_status == TeamMembershipStatus.INVITED:
                template_name = 'membership-invitation-accepted'
        elif new_status == TeamMembershipStatus.INVITATION_DECLINED:
            subject = ('Launchpad: %s decline invitation to join %s'
                       % (member.name, team.name))
            template_name = 'membership-invitation-declined'
        else:
            # Use the default template and subject.
            pass

        if admins_emails:
            admins_template = get_email_template(
                "%s-impersonal.txt" % template_name)
            admins_msg = MailWrapper().format(admins_template % replacements)
            simple_sendmail(from_addr, admins_emails, subject, admins_msg)

        # The member can be a team without any members, and in this case we
        # won't have a single email address to send this notification to.
        if member_email and self.reviewer != member:
            if member.isTeam():
                template = '%s-impersonal.txt' % template_name
            else:
                template = '%s-personal.txt' % template_name
            member_template = get_email_template(template)
            member_msg = MailWrapper().format(member_template % replacements)
            simple_sendmail(from_addr, member_email, subject, member_msg)


class TeamMembershipSet:
    """See `ITeamMembershipSet`."""

    implements(ITeamMembershipSet)

    _defaultOrder = ['Person.displayname', 'Person.name']

    def new(self, person, team, status, dateexpires=None, reviewer=None,
            reviewercomment=None):
        """See `ITeamMembershipSet`."""
        proposed = TeamMembershipStatus.PROPOSED
        approved = TeamMembershipStatus.APPROVED
        admin = TeamMembershipStatus.ADMIN
        invited = TeamMembershipStatus.INVITED
        assert status in [proposed, approved, admin, invited]
        tm = TeamMembership(
            person=person, team=team, status=status, dateexpires=dateexpires,
            reviewer=reviewer, reviewercomment=reviewercomment)

        if status in (approved, admin):
            _fillTeamParticipation(person, team)

        return tm

    def handleMembershipsExpiringToday(self, reviewer):
        """See `ITeamMembershipSet`."""
        memberships = self.getMembershipsToExpire()
        for membership in memberships:
            team = membership.team
            if team.renewal_policy == TeamMembershipRenewalPolicy.AUTOMATIC:
                # Keep the same status, change the expiration date and send a
                # notification explaining the membership has been renewed.
                assert (team.defaultrenewalperiod is not None
                        and team.defaultrenewalperiod > 0), (
                    'Teams with a renewal policy of AUTOMATIC must specify '
                    'a default renewal period greater than 0.')
                membership.dateexpires += timedelta(
                    days=team.defaultrenewalperiod)
                membership.sendAutoRenewalNotification()
            else:
                membership.setStatus(TeamMembershipStatus.EXPIRED, reviewer)

    def getByPersonAndTeam(self, person, team):
        """See `ITeamMembershipSet`."""
        return TeamMembership.selectOneBy(person=person, team=team)

    def getMembershipsToExpire(self, when=None):
        """See `ITeamMembershipSet`."""
        if when is None:
            when = datetime.now(pytz.timezone('UTC'))
        query = ("dateexpires <= %s AND status IN (%s, %s)"
                 % sqlvalues(when, TeamMembershipStatus.ADMIN,
                             TeamMembershipStatus.APPROVED))
        return TeamMembership.select(query)


class TeamParticipation(SQLBase):
    implements(ITeamParticipation)

    _table = 'TeamParticipation'

    team = ForeignKey(foreignKey='Person', dbName='team', notNull=True)
    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)


def _cleanTeamParticipation(person, team):
    """Remove relevant entries in TeamParticipation for <person> and <team>.

    Remove all tuples "person, team" from TeamParticipation for the given
    person and team (together with all its superteams), unless this person is
    an indirect member of the given team. More information on how to use the
    TeamParticipation table can be found in the TeamParticipationUsage spec or
    the teammembership.txt system doctest.
    """
    # First of all, we remove <person> from <team> (and its superteams).
    _removeParticipantFromTeamAndSuperTeams(person, team)

    # Then, if <person> is a team, we remove all its participants from <team>
    # (and its superteams).
    if person.isTeam():
        for submember in person.allmembers:
            if submember not in team.activemembers:
                _cleanTeamParticipation(submember, team)


def _removeParticipantFromTeamAndSuperTeams(person, team):
    """If <person> is a participant (that is, has a TeamParticipation entry)
    of any team that is a subteam of <team>, then <person> should be kept as
    a participant of <team> and (as a consequence) all its superteams.
    Otherwise, <person> is removed from <team> and we repeat this process for
    each superteam of <team>.
    """
    for subteam in team.getSubTeams():
        if person.hasParticipationEntryFor(subteam) and person != subteam:
            # This is an indirect member of the given team, so we must not
            # remove his participation entry for that team.
            return

    result = TeamParticipation.selectOneBy(person=person, team=team)
    if result is not None:
        result.destroySelf()

    # If this team has a mailing list and the person is subscribed to that
    # mailing list, they must be unsubscribed now.
    getUtility(IMailingListSubscriptionSet).deleteSubscription(person, team)

    for superteam in team.getSuperTeams():
        if person not in superteam.activemembers:
            _removeParticipantFromTeamAndSuperTeams(person, superteam)


def _fillTeamParticipation(member, team):
    """Add relevant entries in TeamParticipation for given member and team.

    Add a tuple "member, team" in TeamParticipation for the given team and all
    of its superteams. More information on how to use the TeamParticipation
    table can be found in the TeamParticipationUsage spec.
    """
    members = [member]
    if member.isTeam():
        # The given member is, in fact, a team, and in this case we must
        # add all of its members to the given team and to its superteams.
        members.extend(member.allmembers)

    for m in members:
        for t in itertools.chain(team.getSuperTeams(), [team]):
            if not m.hasParticipationEntryFor(t):
                TeamParticipation(person=m, team=t)

