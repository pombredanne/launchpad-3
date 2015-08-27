# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'TeamMailer',
    ]

from collections import OrderedDict
from datetime import datetime

import pytz
from zope.component import getUtility

from lp.app.browser.tales import DurationFormatterAPI
from lp.registry.enums import (
    TeamMembershipPolicy,
    TeamMembershipRenewalPolicy,
    )
from lp.registry.interfaces.teammembership import (
    ITeamMembershipSet,
    TeamMembershipStatus,
    )
from lp.registry.model.person import get_recipients
from lp.services.config import config
from lp.services.mail.basemailer import (
    BaseMailer,
    RecipientReason,
    )
from lp.services.mail.helpers import get_email_template
from lp.services.mail.sendmail import format_address
from lp.services.webapp.interfaces import ILaunchpadRoot
from lp.services.webapp.publisher import canonical_url
from lp.services.webapp.url import urlappend


class TeamRecipientReason(RecipientReason):

    @classmethod
    def forInvitation(cls, admin, team, recipient, proposed_member, **kwargs):
        header = cls.makeRationale(
            "Invitation (%s)" % team.name, proposed_member)
        reason = (
            "You received this email because %%(lc_entity_is)s an admin of "
            "the %s team." % proposed_member.displayname)
        return cls(admin, recipient, header, reason, **kwargs)

    @classmethod
    def forMember(cls, member, team, recipient, **kwargs):
        header = cls.makeRationale("Member (%s)" % team.name, member)
        reason = (
            "You received this email because %(lc_entity_is)s the affected "
            "member.")
        return cls(member, recipient, header, reason, **kwargs)

    @classmethod
    def forNewMember(cls, new_member, team, recipient, **kwargs):
        # From a filtering point of view, this is identical to forMember;
        # filtering on X-Launchpad-Notification-Type is more useful for
        # determining the type of notification sent to a particular member.
        # It's worth having a footer that makes a little more sense, though.
        header = cls.makeRationale("Member (%s)" % team.name, new_member)
        reason = (
            "You received this email because %(lc_entity_is)s the new member.")
        return cls(new_member, recipient, header, reason, **kwargs)

    @classmethod
    def forAdmin(cls, admin, team, recipient, **kwargs):
        header = cls.makeRationale("Admin (%s)" % team.name, admin)
        reason = (
            "You received this email because %%(lc_entity_is)s an admin of "
            "the %s team." % team.displayname)
        return cls(admin, recipient, header, reason, **kwargs)

    @classmethod
    def forOwner(cls, owner, team, recipient, **kwargs):
        header = cls.makeRationale("Owner (%s)" % team.name, owner)
        reason = (
            "You received this email because %%(lc_entity_is)s the owner "
            "of the %s team." % team.displayname)
        return cls(owner, recipient, header, reason, **kwargs)

    def __init__(self, subscriber, recipient, mail_header, reason_template,
                 subject=None, template_name=None, reply_to=None,
                 recipient_class=None):
        super(TeamRecipientReason, self).__init__(
            subscriber, recipient, mail_header, reason_template)
        self.subject = subject
        self.template_name = template_name
        self.reply_to = reply_to
        self.recipient_class = recipient_class


class TeamMailer(BaseMailer):

    app = 'registry'

    @classmethod
    def forInvitationToJoinTeam(cls, member, team):
        """Create a mailer for notifying about team joining invitations.

        XXX: Guilherme Salgado 2007-05-08:
        At some point we may want to extend this functionality to allow
        invites to be sent to users as well, but for now we only use it for
        teams.
        """
        assert member.is_team
        membership = getUtility(ITeamMembershipSet).getByPersonAndTeam(
            member, team)
        assert membership is not None
        recipients = OrderedDict()
        for admin in member.adminmembers:
            for recipient in get_recipients(admin):
                recipients[recipient] = TeamRecipientReason.forAdmin(
                    admin, member, recipient)
        from_addr = format_address(
            team.displayname, config.canonical.noreply_from_address)
        subject = "Invitation for %s to join" % member.name
        return cls(
            subject, "membership-invitation.txt", recipients, from_addr,
            "membership-invitation", member, team, membership.proposed_by,
            membership=membership)

    @classmethod
    def forTeamJoin(cls, member, team):
        """Create a mailer for notifying about a new member joining a team."""
        membership = getUtility(ITeamMembershipSet).getByPersonAndTeam(
            member, team)
        assert membership is not None
        subject = None
        template_name = None
        notification_type = "new-member"
        recipients = OrderedDict()
        reviewer = membership.proposed_by
        if reviewer != member and membership.status in [
                TeamMembershipStatus.APPROVED, TeamMembershipStatus.ADMIN]:
            reviewer = membership.reviewed_by
            # Somebody added this person as a member, we better send a
            # notification to the person too.
            if member.is_team:
                template_name = "new-member-notification-for-teams.txt"
                subject = "%s joined %s" % (member.name, team.name)
            else:
                template_name = "new-member-notification.txt"
                subject = "You have been added to %s" % team.name
            for recipient in get_recipients(member):
                recipients[recipient] = TeamRecipientReason.forNewMember(
                    member, team, recipient, subject=subject,
                    template_name=template_name)
        # Open teams do not notify admins about new members.
        if team.membership_policy != TeamMembershipPolicy.OPEN:
            reply_to = None
            if membership.status in [
                    TeamMembershipStatus.APPROVED, TeamMembershipStatus.ADMIN]:
                template_name = "new-member-notification-for-admins.txt"
                subject = "%s joined %s" % (member.name, team.name)
            elif membership.status == TeamMembershipStatus.PROPOSED:
                # In the UI, a user can only propose themselves or a team
                # they admin.  Some users of the REST API have a workflow
                # where they propose users that are designated as undergoing
                # mentorship (Bug 498181).
                if reviewer != member:
                    reply_to = reviewer.preferredemail.email
                    template_name = (
                        "pending-membership-approval-for-third-party.txt")
                else:
                    reply_to = member.preferredemail.email
                    template_name = "pending-membership-approval.txt"
                notification_type = "pending-membership-approval"
                subject = "%s wants to join" % member.name
            else:
                raise AssertionError(
                    "Unexpected membership status: %s" % membership.status)
            for admin in team.adminmembers:
                for recipient in get_recipients(admin):
                    # The new member may also be a team admin; don't send
                    # two notifications in that case.
                    if recipient not in recipients:
                        if recipient == team.teamowner:
                            reason_factory = TeamRecipientReason.forOwner
                        else:
                            reason_factory = TeamRecipientReason.forAdmin
                        recipients[recipient] = reason_factory(
                            admin, team, recipient, subject=subject,
                            template_name=template_name, reply_to=reply_to)
        from_addr = format_address(
            team.displayname, config.canonical.noreply_from_address)
        return cls(
            subject, template_name, recipients, from_addr, notification_type,
            member, team, membership.proposed_by, membership=membership)

    @classmethod
    def forMembershipStatusChange(cls, member, team, reviewer,
                                  old_status, new_status, last_change_comment):
        """Create a mailer for a membership status change."""
        notification_type = 'membership-statuschange'
        subject = (
            'Membership change: %(member)s in %(team)s' %
            {'member': member.name, 'team': team.name})
        if new_status == TeamMembershipStatus.EXPIRED:
            notification_type = 'membership-expired'
            subject = '%s expired from team' % member.name
        elif (new_status == TeamMembershipStatus.APPROVED and
            old_status != TeamMembershipStatus.ADMIN):
            if old_status == TeamMembershipStatus.INVITED:
                notification_type = 'membership-invitation-accepted'
                subject = (
                    'Invitation to %s accepted by %s' %
                    (member.name, reviewer.name))
            elif old_status == TeamMembershipStatus.PROPOSED:
                subject = '%s approved by %s' % (member.name, reviewer.name)
            else:
                subject = '%s added by %s' % (member.name, reviewer.name)
        elif new_status == TeamMembershipStatus.INVITATION_DECLINED:
            notification_type = 'membership-invitation-declined'
            subject = (
                'Invitation to %s declined by %s' %
                (member.name, reviewer.name))
        elif new_status == TeamMembershipStatus.DEACTIVATED:
            subject = '%s deactivated by %s' % (member.name, reviewer.name)
        elif new_status == TeamMembershipStatus.ADMIN:
            subject = '%s made admin by %s' % (member.name, reviewer.name)
        elif new_status == TeamMembershipStatus.DECLINED:
            subject = '%s declined by %s' % (member.name, reviewer.name)
        else:
            # Use the default template and subject.
            pass
        template_name = notification_type + "-%(recipient_class)s.txt"

        if last_change_comment:
            comment = "\n%s said:\n %s\n" % (
                reviewer.displayname, last_change_comment.strip())
        else:
            comment = ""

        recipients = OrderedDict()
        if reviewer != member:
            for recipient in get_recipients(member):
                if member.is_team:
                    recipient_class = "bulk"
                else:
                    recipient_class = "personal"
                recipients[recipient] = TeamRecipientReason.forMember(
                    member, team, recipient, recipient_class=recipient_class)
        # Don't send admin notifications for open teams: they're
        # unrestricted, so notifications on join/leave do not help the
        # admins.
        if team.membership_policy != TeamMembershipPolicy.OPEN:
            for admin in team.adminmembers:
                for recipient in get_recipients(admin):
                    # The new member may also be a team admin; don't send
                    # two notifications in that case.
                    if recipient not in recipients:
                        recipients[recipient] = TeamRecipientReason.forAdmin(
                            admin, team, recipient, recipient_class="bulk")

        extra_params = {
            "old_status": old_status,
            "new_status": new_status,
            "comment": comment,
            }
        from_addr = format_address(
            team.displayname, config.canonical.noreply_from_address)
        return cls(
            subject, template_name, recipients, from_addr, notification_type,
            member, team, reviewer, extra_params=extra_params)

    @classmethod
    def forExpiringMembership(cls, member, team, membership, dateexpires):
        """Create a mailer for warning about expiring membership."""
        if member.is_team:
            target = member.teamowner
            template_name = "membership-expiration-warning-bulk.txt"
            subject = "%s will expire soon from %s" % (member.name, team.name)
        else:
            target = member
            template_name = "membership-expiration-warning-personal.txt"
            subject = "Your membership in %s is about to expire" % team.name

        if team.renewal_policy == TeamMembershipRenewalPolicy.ONDEMAND:
            how_to_renew = (
                "If you want, you can renew this membership at\n"
                "<%s/+expiringmembership/%s>" %
                (canonical_url(member), team.name))
        elif not membership.canChangeExpirationDate(target):
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

        recipients = OrderedDict()
        for recipient in get_recipients(target):
            recipients[recipient] = TeamRecipientReason.forMember(
                member, team, recipient)

        formatter = DurationFormatterAPI(dateexpires - datetime.now(pytz.UTC))
        extra_params = {
            "how_to_renew": how_to_renew,
            "expiration_date": dateexpires.strftime("%Y-%m-%d"),
            "approximate_duration": formatter.approximateduration(),
            }

        from_addr = format_address(
            team.displayname, config.canonical.noreply_from_address)
        return cls(
            subject, template_name, recipients, from_addr,
            "membership-expiration-warning", member, team,
            membership.proposed_by, membership=membership,
            extra_params=extra_params, wrap=False, force_wrap=False)

    @classmethod
    def forSelfRenewal(cls, member, team, dateexpires):
        """Create a mailer for notifying about a self-renewal."""
        assert team.renewal_policy == TeamMembershipRenewalPolicy.ONDEMAND
        template_name = "membership-member-renewed.txt"
        subject = "%s extended their membership" % member.name
        recipients = OrderedDict()
        for admin in team.adminmembers:
            for recipient in get_recipients(admin):
                recipients[recipient] = TeamRecipientReason.forAdmin(
                    admin, team, recipient)
        extra_params = {"dateexpires": dateexpires.strftime("%Y-%m-%d")}
        from_addr = format_address(
            team.displayname, config.canonical.noreply_from_address)
        return cls(
            subject, template_name, recipients, from_addr,
            "membership-member-renewed", member, team, None,
            extra_params=extra_params)

    def __init__(self, subject, template_name, recipients, from_address,
                 notification_type, member, team, reviewer, membership=None,
                 extra_params={}, wrap=True, force_wrap=True):
        """See `BaseMailer`."""
        super(TeamMailer, self).__init__(
            subject, template_name, recipients, from_address,
            notification_type=notification_type, wrap=wrap,
            force_wrap=force_wrap)
        self.member = member
        self.team = team
        self.reviewer = reviewer
        self.membership = membership
        self.extra_params = extra_params

    def _getSubject(self, email, recipient):
        """See `BaseMailer`."""
        reason, _ = self._recipients.getReason(email)
        if reason.subject is not None:
            subject_template = reason.subject
        else:
            subject_template = self._subject_template
        return subject_template % self._getTemplateParams(email, recipient)

    def _getReplyToAddress(self, email, recipient):
        """See `BaseMailer`."""
        reason, _ = self._recipients.getReason(email)
        return reason.reply_to

    def _getTemplateName(self, email, recipient):
        """See `BaseMailer`."""
        reason, _ = self._recipients.getReason(email)
        if reason.template_name is not None:
            template_name = reason.template_name
        else:
            template_name = self._template_name
        return template_name % self._getTemplateParams(email, recipient)

    def _getTemplateParams(self, email, recipient):
        """See `BaseMailer`."""
        params = super(TeamMailer, self)._getTemplateParams(email, recipient)
        params["recipient"] = recipient.displayname
        reason, _ = self._recipients.getReason(email)
        if reason.recipient_class is not None:
            params["recipient_class"] = reason.recipient_class
        params["member"] = self.member.unique_displayname
        params["membership_invitations_url"] = "%s/+invitation/%s" % (
            canonical_url(self.member), self.team.name)
        params["team"] = self.team.unique_displayname
        params["team_url"] = canonical_url(self.team)
        if self.membership is not None:
            params["membership_url"] = canonical_url(self.membership)
        if reason.recipient_class == "bulk" and self.reviewer == self.member:
            params["reviewer"] = "the user"
        elif self.reviewer is not None:
            params["reviewer"] = self.reviewer.unique_displayname
        if self.team.mailing_list is not None:
            template = get_email_template(
                "team-list-subscribe-block.txt", app="registry")
            editemails_url = urlappend(
                canonical_url(getUtility(ILaunchpadRoot)),
                "~/+editmailinglists")
            list_instructions = template % {"editemails_url": editemails_url}
        else:
            list_instructions = ""
        params["list_instructions"] = list_instructions
        params.update(self.extra_params)
        return params

    def _getFooter(self, email, recipient, params):
        """See `BaseMailer`."""
        return "%(reason)s\n" % params
