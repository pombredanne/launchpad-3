# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = [
    'TeamMembership',
    'TeamMembershipSet',
    'TeamParticipation',
    ]

from datetime import (
    datetime,
    timedelta,
    )

import pytz
from sqlobject import (
    ForeignKey,
    StringCol,
    )
from storm.store import Store
from zope.component import getUtility
from zope.interface import implements

from canonical.config import config
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import (
    cursor,
    flush_database_updates,
    SQLBase,
    sqlvalues,
    )
from canonical.launchpad.helpers import (
    get_contact_email_addresses,
    get_email_template,
    )
from canonical.launchpad.interfaces.lpstorm import IStore
from canonical.launchpad.mailnotification import MailWrapper
from canonical.launchpad.webapp import canonical_url
from lp.app.browser.tales import DurationFormatterAPI
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.registry.errors import (
    TeamMembershipTransitionError,
    UserCannotChangeMembershipSilently,
    )
from lp.registry.interfaces.person import (
    IPersonSet,
    TeamMembershipRenewalPolicy,
    validate_public_person,
    )
from lp.registry.interfaces.persontransferjob import (
    IMembershipNotificationJobSource,
    )
from lp.registry.interfaces.teammembership import (
    ACTIVE_STATES,
    CyclicalTeamMembershipError,
    DAYS_BEFORE_EXPIRATION_WARNING_IS_SENT,
    ITeamMembership,
    ITeamMembershipSet,
    ITeamParticipation,
    TeamMembershipStatus,
    )
from lp.services.mail.sendmail import (
    format_address,
    simple_sendmail,
    )


class TeamMembership(SQLBase):
    """See `ITeamMembership`."""

    implements(ITeamMembership)

    _table = 'TeamMembership'
    _defaultOrder = 'id'

    team = ForeignKey(dbName='team', foreignKey='Person', notNull=True)
    person = ForeignKey(
        dbName='person', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)
    last_changed_by = ForeignKey(
        dbName='last_changed_by', foreignKey='Person',
        storm_validator=validate_public_person, default=None)
    proposed_by = ForeignKey(
        dbName='proposed_by', foreignKey='Person',
        storm_validator=validate_public_person, default=None)
    acknowledged_by = ForeignKey(
        dbName='acknowledged_by', foreignKey='Person',
        storm_validator=validate_public_person, default=None)
    reviewed_by = ForeignKey(
        dbName='reviewed_by', foreignKey='Person',
        storm_validator=validate_public_person, default=None)
    status = EnumCol(
        dbName='status', notNull=True, enum=TeamMembershipStatus)
    # XXX: salgado, 2008-03-06: Need to rename datejoined and dateexpires to
    # match their db names.
    datejoined = UtcDateTimeCol(dbName='date_joined', default=None)
    dateexpires = UtcDateTimeCol(dbName='date_expires', default=None)
    date_created = UtcDateTimeCol(default=UTC_NOW)
    date_proposed = UtcDateTimeCol(default=None)
    date_acknowledged = UtcDateTimeCol(default=None)
    date_reviewed = UtcDateTimeCol(default=None)
    date_last_changed = UtcDateTimeCol(default=None)
    last_change_comment = StringCol(default=None)
    proponent_comment = StringCol(default=None)
    acknowledger_comment = StringCol(default=None)
    reviewer_comment = StringCol(default=None)

    def isExpired(self):
        """See `ITeamMembership`."""
        return self.status == TeamMembershipStatus.EXPIRED

    def canBeRenewedByMember(self):
        """See `ITeamMembership`."""
        ondemand = TeamMembershipRenewalPolicy.ONDEMAND
        admin = TeamMembershipStatus.APPROVED
        approved = TeamMembershipStatus.ADMIN
        date_limit = datetime.now(pytz.UTC) + timedelta(
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
            team.displayname, config.canonical.noreply_from_address)
        replacements = {'member_name': member.unique_displayname,
                        'team_name': team.unique_displayname,
                        'team_url': canonical_url(team),
                        'dateexpires': self.dateexpires.strftime('%Y-%m-%d')}
        subject = '%s extended their membership' % member.name
        template = get_email_template(
            'membership-member-renewed.txt', app='registry')
        admins_addrs = self.team.getTeamAdminsEmailAddresses()
        for address in admins_addrs:
            recipient = getUtility(IPersonSet).getByEmail(address)
            replacements['recipient_name'] = recipient.displayname
            msg = MailWrapper().format(
                template % replacements, force_wrap=True)
            simple_sendmail(from_addr, address, subject, msg)

    def sendAutoRenewalNotification(self):
        """See `ITeamMembership`."""
        team = self.team
        member = self.person
        assert team.renewal_policy == TeamMembershipRenewalPolicy.AUTOMATIC

        from_addr = format_address(
            team.displayname, config.canonical.noreply_from_address)
        replacements = {'member_name': member.unique_displayname,
                        'team_name': team.unique_displayname,
                        'team_url': canonical_url(team),
                        'dateexpires': self.dateexpires.strftime('%Y-%m-%d')}
        subject = '%s renewed automatically' % member.name

        if member.isTeam():
            member_addrs = get_contact_email_addresses(member.teamowner)
            template_name = 'membership-auto-renewed-bulk.txt'
        else:
            template_name = 'membership-auto-renewed-personal.txt'
            member_addrs = get_contact_email_addresses(member)
        template = get_email_template(template_name, app='registry')
        for address in member_addrs:
            recipient = getUtility(IPersonSet).getByEmail(address)
            replacements['recipient_name'] = recipient.displayname
            msg = MailWrapper().format(
                template % replacements, force_wrap=True)
            simple_sendmail(from_addr, address, subject, msg)

        template_name = 'membership-auto-renewed-bulk.txt'
        admins_addrs = self.team.getTeamAdminsEmailAddresses()
        admins_addrs = set(admins_addrs).difference(member_addrs)
        template = get_email_template(template_name, app='registry')
        for address in admins_addrs:
            recipient = getUtility(IPersonSet).getByEmail(address)
            replacements['recipient_name'] = recipient.displayname
            msg = MailWrapper().format(
                template % replacements, force_wrap=True)
            simple_sendmail(from_addr, address, subject, msg)

    def canChangeStatusSilently(self, user):
        """Ensure that the user is in the Launchpad Administrators group.

        Then the user can silently make changes to their membership status.
        """
        return user.inTeam(getUtility(ILaunchpadCelebrities).admin)

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
        self._setExpirationDate(date, user)

    def _setExpirationDate(self, date, user):
        UTC = pytz.timezone('UTC')
        assert date is None or date.date() >= datetime.now(UTC).date(), (
            "The given expiration date must be None or be in the future: %s"
            % date.strftime('%Y-%m-%d'))
        self.dateexpires = date
        self.last_changed_by = user

    def sendExpirationWarningEmail(self):
        """See `ITeamMembership`."""
        if self.dateexpires is None:
            raise AssertionError(
                '%s in team %s has no membership expiration date.' %
                (self.person.name, self.team.name))
        if self.team.renewal_policy == TeamMembershipRenewalPolicy.AUTOMATIC:
            # An email will be sent later by handleMembershipsExpiringToday()
            # when the membership is automatically renewed.
            raise AssertionError(
                'Team %s with automatic renewals should not send expiration '
                'warnings.' % self.team.name)
        if self.dateexpires < datetime.now(pytz.timezone('UTC')):
            # The membership has reached expiration. Silently return because
            # there is nothing to do. The member will have received emails
            # from previous calls by flag-expired-memberships.py
            return
        member = self.person
        team = self.team
        if member.isTeam():
            recipient = member.teamowner
            templatename = 'membership-expiration-warning-bulk.txt'
            subject = '%s will expire soon from %s' % (member.name, team.name)
        else:
            recipient = member
            templatename = 'membership-expiration-warning-personal.txt'
            subject = 'Your membership in %s is about to expire' % team.name

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
                    "To prevent this membership from expiring, you should "
                    "contact the\nteam's administrator, %s.\n<%s>"
                    % (admin.unique_displayname, canonical_url(admin)))
            else:
                for admin in admins:
                    # Do not tell the member to contact himself when he can't
                    # extend his membership.
                    if admin != member:
                        admins_names.append(
                            "%s <%s>" % (admin.unique_displayname,
                                         canonical_url(admin)))

                how_to_renew = (
                    "To prevent this membership from expiring, you should "
                    "get in touch\nwith one of the team's administrators:\n")
                how_to_renew += "\n".join(admins_names)
        else:
            how_to_renew = (
                "To stay a member of this team you should extend your "
                "membership at\n<%s/+member/%s>"
                % (canonical_url(team), member.name))

        to_addrs = get_contact_email_addresses(recipient)
        if len(to_addrs) == 0:
            # The user does not have a preferred email address, he was
            # probably suspended.
            return
        formatter = DurationFormatterAPI(
            self.dateexpires - datetime.now(pytz.timezone('UTC')))
        replacements = {
            'recipient_name': recipient.displayname,
            'member_name': member.unique_displayname,
            'team_url': canonical_url(team),
            'how_to_renew': how_to_renew,
            'team_name': team.unique_displayname,
            'expiration_date': self.dateexpires.strftime('%Y-%m-%d'),
            'approximate_duration': formatter.approximateduration()}

        msg = get_email_template(templatename, app='registry') % replacements
        from_addr = format_address(
            team.displayname, config.canonical.noreply_from_address)
        simple_sendmail(from_addr, to_addrs, subject, msg)

    def setStatus(self, status, user, comment=None, silent=False):
        """See `ITeamMembership`."""
        if status == self.status:
            return False

        if silent and not self.canChangeStatusSilently(user):
            raise UserCannotChangeMembershipSilently(
                "Only Launchpad administrators may change membership "
                "statuses silently.")

        approved = TeamMembershipStatus.APPROVED
        admin = TeamMembershipStatus.ADMIN
        expired = TeamMembershipStatus.EXPIRED
        declined = TeamMembershipStatus.DECLINED
        deactivated = TeamMembershipStatus.DEACTIVATED
        proposed = TeamMembershipStatus.PROPOSED
        invited = TeamMembershipStatus.INVITED
        invitation_declined = TeamMembershipStatus.INVITATION_DECLINED

        self.person.clearInTeamCache()

        # Make sure the transition from the current status to the given one
        # is allowed. All allowed transitions are in the TeamMembership spec.
        state_transition = {
            admin: [approved, expired, deactivated],
            approved: [admin, expired, deactivated],
            deactivated: [proposed, approved, admin, invited],
            expired: [proposed, approved, admin, invited],
            proposed: [approved, admin, declined],
            declined: [proposed, approved, admin, invited],
            invited: [approved, admin, invitation_declined],
            invitation_declined: [invited, approved, admin]}

        if self.status not in state_transition:
            raise TeamMembershipTransitionError(
                "Unknown status: %s" % self.status.name)
        if status not in state_transition[self.status]:
            raise TeamMembershipTransitionError(
                "Bad state transition from %s to %s"
                % (self.status.name, status.name))

        if status in ACTIVE_STATES and self.team in self.person.allmembers:
            raise CyclicalTeamMembershipError(
                "Cannot make %(person)s a member of %(team)s because "
                "%(team)s is a member of %(person)s."
                % dict(person=self.person.name, team=self.team.name))

        old_status = self.status
        self.status = status

        now = datetime.now(pytz.timezone('UTC'))
        if status in [proposed, invited]:
            self.proposed_by = user
            self.proponent_comment = comment
            self.date_proposed = now
        elif ((status in ACTIVE_STATES and old_status not in ACTIVE_STATES)
              or status == declined):
            self.reviewed_by = user
            self.reviewer_comment = comment
            self.date_reviewed = now
            if self.datejoined is None and status in ACTIVE_STATES:
                # This is the first time this membership is made active.
                self.datejoined = now
        else:
            # No need to set proponent or reviewer.
            pass

        if old_status == invited:
            # This member has been invited by an admin and is now accepting or
            # declining the invitation.
            self.acknowledged_by = user
            self.date_acknowledged = now
            self.acknowledger_comment = comment

        self.last_changed_by = user
        self.last_change_comment = comment
        self.date_last_changed = now

        if status in ACTIVE_STATES:
            _fillTeamParticipation(self.person, self.team)
        elif old_status in ACTIVE_STATES:
            _cleanTeamParticipation(self.person, self.team)
        else:
            # Changed from an inactive state to another inactive one, so no
            # need to fill/clean the TeamParticipation table.
            pass

        # Flush all updates to ensure any subsequent calls to this method on
        # the same transaction will operate on the correct data.  That is the
        # case with our script to expire team memberships.
        flush_database_updates()

        # When a member proposes himself, a more detailed notification is
        # sent to the team admins by a subscriber of JoinTeamEvent; that's
        # why we don't send anything here.
        if ((self.person != self.last_changed_by or self.status != proposed)
            and not silent):
            self._sendStatusChangeNotification(old_status)
        return True

    def _sendStatusChangeNotification(self, old_status):
        """Send a status change notification to all team admins and the
        member whose membership's status changed.
        """
        reviewer = self.last_changed_by
        new_status = self.status
        getUtility(IMembershipNotificationJobSource).create(
            self.person, self.team, reviewer, old_status, new_status,
            self.last_change_comment)


class TeamMembershipSet:
    """See `ITeamMembershipSet`."""

    implements(ITeamMembershipSet)

    _defaultOrder = ['Person.displayname', 'Person.name']

    def new(self, person, team, status, user, dateexpires=None, comment=None):
        """See `ITeamMembershipSet`."""
        proposed = TeamMembershipStatus.PROPOSED
        approved = TeamMembershipStatus.APPROVED
        admin = TeamMembershipStatus.ADMIN
        invited = TeamMembershipStatus.INVITED
        assert status in [proposed, approved, admin, invited]

        person.clearInTeamCache()

        tm = TeamMembership(
            person=person, team=team, status=status, dateexpires=dateexpires)

        now = datetime.now(pytz.timezone('UTC'))
        tm.proposed_by = user
        tm.date_proposed = now
        tm.proponent_comment = comment
        if status in [approved, admin]:
            tm.datejoined = now
            tm.reviewed_by = user
            tm.date_reviewed = now
            tm.reviewer_comment = comment
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

    def getMembershipsToExpire(self, when=None, exclude_autorenewals=False):
        """See `ITeamMembershipSet`."""
        if when is None:
            when = datetime.now(pytz.timezone('UTC'))
        conditions = [
            TeamMembership.dateexpires <= when,
            TeamMembership.status.is_in(
                [TeamMembershipStatus.ADMIN, TeamMembershipStatus.APPROVED]),
            ]
        if exclude_autorenewals:
            # Avoid circular import.
            from lp.registry.model.person import Person
            conditions.append(TeamMembership.team == Person.id)
            conditions.append(
                Person.renewal_policy !=
                    TeamMembershipRenewalPolicy.AUTOMATIC)
        return IStore(TeamMembership).find(TeamMembership, *conditions)

    def deactivateActiveMemberships(self, team, comment, reviewer):
        """See `ITeamMembershipSet`."""
        now = datetime.now(pytz.timezone('UTC'))
        cur = cursor()
        all_members = list(team.activemembers)
        cur.execute("""
            UPDATE TeamMembership
            SET status=%(status)s,
                last_changed_by=%(last_changed_by)s,
                last_change_comment=%(comment)s,
                date_last_changed=%(date_last_changed)s
            WHERE
                TeamMembership.team = %(team)s
                AND TeamMembership.status IN %(original_statuses)s
            """,
            dict(
                status=TeamMembershipStatus.DEACTIVATED,
                last_changed_by=reviewer.id,
                comment=comment,
                date_last_changed=now,
                team=team.id,
                original_statuses=ACTIVE_STATES))
        for member in all_members:
            # store.invalidate() is called for each iteration.
            _cleanTeamParticipation(member, team)


class TeamParticipation(SQLBase):
    implements(ITeamParticipation)

    _table = 'TeamParticipation'

    team = ForeignKey(dbName='team', foreignKey='Person', notNull=True)
    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)


def _cleanTeamParticipation(child, parent):
    """Remove child from team and clean up child's subteams.

    A participant of child is removed from parent's TeamParticipation
    entries if the only path from the participant to parent is via
    child.
    """
    # Delete participation entries for the child and the child's
    # direct/indirect members in other ancestor teams, unless those
    # ancestor teams have another path the the child besides the
    # membership that has just been deactivated.
    store = Store.of(parent)
    store.execute("""
        DELETE FROM TeamParticipation
        USING (
            /* Get all the participation entries that might need to be
             * deleted, i.e. all the entries where the
             * TeamParticipation.person is a participant of child, and
             * where child participated in TeamParticipation.team until
             * child was removed from parent.
             */
            SELECT person, team
            FROM TeamParticipation
            WHERE person IN (
                    SELECT person
                    FROM TeamParticipation
                    WHERE team = %(child)s
                )
                AND team IN (
                    SELECT team
                    FROM TeamParticipation
                    WHERE person = %(child)s
                        AND team != %(child)s
                )


            EXCEPT (

                /* Compute the TeamParticipation entries that we need to
                 * keep by walking the tree in the TeamMembership table.
                 */
                WITH RECURSIVE parent(person, team) AS (
                    /* Start by getting all the ancestors of the child
                     * from the TeamParticipation table, then get those
                     * ancestors' direct members to recurse through the
                     * tree from the top.
                     */
                    SELECT ancestor.person, ancestor.team
                    FROM TeamMembership ancestor
                    WHERE ancestor.status IN %(active_states)s
                        AND ancestor.team IN (
                            SELECT team
                            FROM TeamParticipation
                            WHERE person = %(child)s
                        )

                    UNION

                    /* Find the next level of direct members, but hold
                     * onto the parent.team, since we want the top and
                     * bottom of the hierarchy to calculate the
                     * TeamParticipation. The query above makes sure
                     * that we do this for all the ancestors.
                     */
                    SELECT child.person, parent.team
                    FROM TeamMembership child
                        JOIN parent ON child.team = parent.person
                    WHERE child.status IN %(active_states)s
                )
                SELECT person, team
                FROM parent
            )
        ) AS keeping
        WHERE TeamParticipation.person = keeping.person
            AND TeamParticipation.team = keeping.team
        """ % sqlvalues(
            child=child.id,
            active_states=ACTIVE_STATES))
    store.invalidate()


def _fillTeamParticipation(member, accepting_team):
    """Add relevant entries in TeamParticipation for given member and team.

    Add a tuple "member, team" in TeamParticipation for the given team and all
    of its superteams. More information on how to use the TeamParticipation
    table can be found in the TeamParticipationUsage spec.
    """
    if member.isTeam():
        # The submembers will be all the members of the team that is
        # being added as a member. The superteams will be all the teams
        # that the accepting_team belongs to, so all the members will
        # also be joining the superteams indirectly. It is important to
        # remember that teams are members of themselves, so the member
        # team will also be one of the submembers, and the
        # accepting_team will also be one of the superteams.
        query = """
            INSERT INTO TeamParticipation (person, team)
            SELECT submember.person, superteam.team
            FROM TeamParticipation submember
                JOIN TeamParticipation superteam ON TRUE
            WHERE submember.team = %(member)d
                AND superteam.person = %(accepting_team)d
                AND NOT EXISTS (
                    SELECT 1
                    FROM TeamParticipation
                    WHERE person = submember.person
                        AND team = superteam.team
                    )
            """ % dict(member=member.id, accepting_team=accepting_team.id)
    else:
        query = """
            INSERT INTO TeamParticipation (person, team)
            SELECT %(member)d, superteam.team
            FROM TeamParticipation superteam
            WHERE superteam.person = %(accepting_team)d
                AND NOT EXISTS (
                    SELECT 1
                    FROM TeamParticipation
                    WHERE person = %(member)d
                        AND team = superteam.team
                    )
            """ % dict(member=member.id, accepting_team=accepting_team.id)

    store = Store.of(member)
    store.execute(query)
