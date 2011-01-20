# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Job classes related to PersonTransferJob."""

__metaclass__ = type
__all__ = [
    'MembershipNotificationJob',
    'PersonTransferJob',
    ]

from lazr.delegates import delegates
import simplejson
from sqlobject import SQLObjectNotFound
from storm.expr import And
from storm.locals import (
    Int,
    Reference,
    Unicode,
    )
from zope.component import getUtility
from zope.interface import (
    classProvides,
    implements,
    )

from canonical.config import config
from canonical.database.enumcol import EnumCol
from canonical.launchpad.helpers import (
    get_contact_email_addresses,
    get_email_template,
    )
from canonical.launchpad.interfaces.lpstorm import IMasterStore
from canonical.launchpad.mail import (
    format_address,
    simple_sendmail,
    )
from canonical.launchpad.mailnotification import MailWrapper
from canonical.launchpad.webapp import canonical_url
from lp.registry.enum import PersonTransferJobType
from lp.registry.interfaces.person import (
    IPerson,
    IPersonSet,
    ITeam,
    )
from lp.registry.interfaces.persontransferjob import (
    IMembershipNotificationJob,
    IMembershipNotificationJobSource,
    IPersonTransferJob,
    IPersonTransferJobSource,
    )
from lp.registry.interfaces.teammembership import TeamMembershipStatus
from lp.registry.model.person import Person
from lp.services.job.model.job import Job
from lp.services.job.runner import BaseRunnableJob
from lp.services.database.stormbase import StormBase


class PersonTransferJob(StormBase):
    """Base class for team membership and person merge jobs."""

    implements(IPersonTransferJob)

    __storm_table__ = 'PersonTransferJob'

    id = Int(primary=True)

    job_id = Int(name='job')
    job = Reference(job_id, Job.id)

    major_person_id = Int(name='major_person')
    major_person = Reference(major_person_id, Person.id)

    minor_person_id = Int(name='minor_person')
    minor_person = Reference(minor_person_id, Person.id)

    job_type = EnumCol(enum=PersonTransferJobType, notNull=True)

    _json_data = Unicode('json_data')

    @property
    def metadata(self):
        return simplejson.loads(self._json_data)

    def __init__(self, minor_person, major_person, job_type, metadata):
        """Constructor.

        :param minor_person: The person or team being added to or removed
                             from the major_person.
        :param major_person: The person or team that is receiving or losing
                             the minor person.
        :param job_type: The specific membership action being performed.
        :param metadata: The type-specific variables, as a JSON-compatible
                         dict.
        """
        super(PersonTransferJob, self).__init__()
        self.job = Job()
        self.job_type = job_type
        self.major_person = major_person
        self.minor_person = minor_person

        json_data = simplejson.dumps(metadata)
        # XXX AaronBentley 2009-01-29 bug=322819: This should be a bytestring,
        # but the DB representation is unicode.
        self._json_data = json_data.decode('utf-8')


class PersonTransferJobDerived(BaseRunnableJob):
    """Intermediate class for deriving from PersonTransferJob.

    Storm classes can't simply be subclassed or you can end up with
    multiple objects referencing the same row in the db. This class uses
    lazr.delegates, which is a little bit simpler than storm's
    infoheritance solution to the problem. Subclasses need to override
    the run() method.
    """

    delegates(IPersonTransferJob)
    classProvides(IPersonTransferJobSource)

    def __init__(self, job):
        self.context = job

    def __repr__(self):
        return (
            '<%(job_type)s branch job (%(id)s) for %(minor_person)s '
            'as part of %(major_person)s. status=%(status)s>' % {
                'job_type': self.context.job_type.name,
                'id': self.context.id,
                'minor_person': self.minor_person.name,
                'major_person': self.major_person.name,
                'status': self.job.status,
                })

    @classmethod
    def create(cls, minor_person, major_person, metadata):
        """See `IPersonTransferJob`."""
        if not IPerson.providedBy(minor_person):
            raise TypeError("minor_person must be IPerson: %s"
                            % repr(minor_person))
        if not IPerson.providedBy(major_person):
            raise TypeError("major_person must be IPerson: %s"
                            % repr(major_person))
        job = PersonTransferJob(
            minor_person=minor_person,
            major_person=major_person,
            job_type=cls.class_job_type,
            metadata=metadata)
        return cls(job)

    @classmethod
    def iterReady(cls):
        """Iterate through all ready PersonTransferJobs."""
        store = IMasterStore(PersonTransferJob)
        jobs = store.find(
            PersonTransferJob,
            And(PersonTransferJob.job_type == cls.class_job_type,
                PersonTransferJob.job_id.is_in(Job.ready_jobs)))
        return (cls(job) for job in jobs)

    def getOopsVars(self):
        """See `IRunnableJob`."""
        vars = BaseRunnableJob.getOopsVars(self)
        vars.extend([
            ('major_person_name', self.context.major_person.name),
            ('minor_person_name', self.context.minor_person.name),
            ])
        return vars


class MembershipNotificationJob(PersonTransferJobDerived):
    """A Job that sends notifications about team membership changes."""

    implements(IMembershipNotificationJob)
    classProvides(IMembershipNotificationJobSource)

    class_job_type = PersonTransferJobType.MEMBERSHIP_NOTIFICATION

    @classmethod
    def create(cls, member, team, reviewer, old_status, new_status,
               last_change_comment=None):
        if not ITeam.providedBy(team):
            raise TypeError('team must be ITeam: %s' % repr(team))
        if not IPerson.providedBy(reviewer):
            raise TypeError('reviewer must be IPerson: %s' % repr(reviewer))
        if old_status not in TeamMembershipStatus:
            raise TypeError("old_status must be TeamMembershipStatus: %s"
                            % repr(old_status))
        if new_status not in TeamMembershipStatus:
            raise TypeError("new_status must be TeamMembershipStatus: %s"
                            % repr(new_status))
        metadata = {
            'reviewer': reviewer.id,
            'old_status': old_status.name,
            'new_status': new_status.name,
            'last_change_comment': last_change_comment,
            }
        return super(MembershipNotificationJob, cls).create(
            minor_person=member, major_person=team, metadata=metadata)

    @property
    def member(self):
        return self.minor_person

    @property
    def team(self):
        return self.major_person

    @property
    def reviewer(self):
        return getUtility(IPersonSet).get(self.metadata['reviewer'])

    @property
    def old_status(self):
        return TeamMembershipStatus.items[self.metadata['old_status']]

    @property
    def new_status(self):
        return TeamMembershipStatus.items[self.metadata['new_status']]

    @property
    def last_change_comment(self):
        return self.metadata['last_change_comment']

    def run(self):
        """See `IMembershipNotificationJob`."""
        from canonical.launchpad.scripts import log
        from_addr = format_address(
            self.team.displayname, config.canonical.noreply_from_address)
        admin_emails = self.team.getTeamAdminsEmailAddresses()
        # person might be a self.team, so we can't rely on its preferredemail.
        self.member_email = get_contact_email_addresses(self.member)
        # Make sure we don't send the same notification twice to anybody.
        for email in self.member_email:
            if email in admin_emails:
                admin_emails.remove(email)

        if self.reviewer != self.member:
            self.reviewer_name = self.reviewer.unique_displayname
        else:
            # The user himself changed his self.membership.
            self.reviewer_name = 'the user himself'

        if self.last_change_comment:
            comment = ("\n%s said:\n %s\n" % (
                self.reviewer.displayname, self.last_change_comment.strip()))
        else:
            comment = ""

        replacements = {
            'member_name': self.member.unique_displayname,
            'recipient_name': self.member.displayname,
            'team_name': self.team.unique_displayname,
            'team_url': canonical_url(self.team),
            'old_status': self.old_status.title,
            'new_status': self.new_status.title,
            'reviewer_name': self.reviewer_name,
            'comment': comment}

        template_name = 'membership-statuschange'
        subject = (
            'Membership change: %(member)s in %(team)s'
            % {
                'member': self.member.name,
                'team': self.team.name,
              })
        if self.new_status == TeamMembershipStatus.EXPIRED:
            template_name = 'membership-expired'
            subject = '%s expired from team' % self.member.name
        elif (self.new_status == TeamMembershipStatus.APPROVED and
            self.old_status != TeamMembershipStatus.ADMIN):
            if self.old_status == TeamMembershipStatus.INVITED:
                subject = ('Invitation to %s accepted by %s'
                        % (self.member.name, self.reviewer.name))
                template_name = 'membership-invitation-accepted'
            elif self.old_status == TeamMembershipStatus.PROPOSED:
                subject = '%s approved by %s' % (
                    self.member.name, self.reviewer.name)
            else:
                subject = '%s added by %s' % (
                    self.member.name, self.reviewer.name)
        elif self.new_status == TeamMembershipStatus.INVITATION_DECLINED:
            subject = ('Invitation to %s declined by %s'
                    % (self.member.name, self.reviewer.name))
            template_name = 'membership-invitation-declined'
        elif self.new_status == TeamMembershipStatus.DEACTIVATED:
            subject = '%s deactivated by %s' % (
                self.member.name, self.reviewer.name)
        elif self.new_status == TeamMembershipStatus.ADMIN:
            subject = '%s made admin by %s' % (
                self.member.name, self.reviewer.name)
        elif self.new_status == TeamMembershipStatus.DECLINED:
            subject = '%s declined by %s' % (
                self.member.name, self.reviewer.name)
        else:
            # Use the default template and subject.
            pass

        if len(admin_emails) != 0:
            admin_template = get_email_template(
                "%s-bulk.txt" % template_name)
            for address in admin_emails:
                recipient = getUtility(IPersonSet).getByEmail(address)
                replacements['recipient_name'] = recipient.displayname
                msg = MailWrapper().format(
                    admin_template % replacements, force_wrap=True)
                simple_sendmail(from_addr, address, subject, msg)

        # The self.member can be a self.self.team without any
        # self.members, and in this case we won't have a single email
        # address to send this notification to.
        if self.member_email and self.reviewer != self.member:
            if self.member.isTeam():
                template = '%s-bulk.txt' % template_name
            else:
                template = '%s-personal.txt' % template_name
            self.member_template = get_email_template(template)
            for address in self.member_email:
                recipient = getUtility(IPersonSet).getByEmail(address)
                replacements['recipient_name'] = recipient.displayname
                msg = MailWrapper().format(
                    self.member_template % replacements, force_wrap=True)
                simple_sendmail(from_addr, address, subject, msg)
        log.debug('MembershipNotificationJob sent email')
