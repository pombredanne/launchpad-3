# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Bugzilla to Launchpad import logic"""


# Bugzilla schema:
#  http://lxr.mozilla.org/mozilla/source/webtools/bugzilla/Bugzilla/DB/Schema.pm

# XXX: 20051018 jamesh
# Currently unhandled bug info:
#  * Operating system and platform
#  * version (not really used in Ubuntu bugzilla though)
#  * keywords
#  * private bugs (none of the canonical-only bugs seem sensitive though)
#  * bug dependencies
#  * "bug XYZ" references inside comment text (at the moment we just
#    insert the full URL to the bug afterwards).
#
# Not all of these are necessary though

__metaclass__ = type

from cStringIO import StringIO
import re
import logging
import datetime
import pytz
import urlparse

from zope.component import getUtility
from canonical.launchpad.interfaces import (
    IPersonSet, IEmailAddressSet, IDistributionSet, IBugSet,
    IBugTaskSet, IBugTrackerSet, IBugExternalRefSet,
    IBugAttachmentSet, IMessageSet, ILibraryFileAliasSet, ICveSet,
    IBugWatchSet, ILaunchpadCelebrities, IMilestoneSet, NotFoundError)
from canonical.lp.dbschema import (
    BugTaskSeverity, BugTaskStatus, BugTaskPriority, BugAttachmentType)

logger = logging.getLogger('canonical.launchpad.scripts.bugzilla')

def _add_tz(dt):
    """Convert a naiive datetime value to a UTC datetime value."""
    assert dt.tzinfo is None, 'add_tz() only accepts naiive datetime values'
    return datetime.datetime(dt.year, dt.month, dt.day,
                             dt.hour, dt.minute, dt.second,
                             dt.microsecond, tzinfo=pytz.timezone('UTC'))

class BugzillaBackend:
    """A wrapper for all the MySQL database access.

    The main purpose of this is to make it possible to test the rest
    of the import code without access to a MySQL database.
    """
    def __init__(self, conn, charset='UTF-8'):
        self.conn = conn
        self.cursor = conn.cursor()
        self.charset = charset

    def _decode(self, s):
        if s is not None:
            return s.decode(self.charset, 'replace')
        else:
            return None

    def lookup_user(self, user_id):
        """Look up information about a particular Bugzilla user ID"""
        self.cursor.execute('SELECT login_name, realname '
                            '  FROM profiles '
                            '  WHERE userid = %d' % user_id)
        if self.cursor.rowcount != 1:
            raise NotFoundError('could not look up user %d' % user_id)
        (login_name, realname) = self.cursor.fetchone()
        realname = self._decode(realname)
        return (login_name, realname)

    def get_bug_info(self, bug_id):
        """Retrieve information about a bug."""
        self.cursor.execute(
            'SELECT bug_id, assigned_to, bug_file_loc, bug_severity, '
            '    bug_status, creation_ts, short_desc, op_sys, priority, '
            '    products.name, rep_platform, reporter, version, '
            '    components.name, resolution, target_milestone, qa_contact, '
            '    status_whiteboard, keywords, alias '
            '  FROM bugs '
            '    INNER JOIN products ON bugs.product_id = products.id '
            '    INNER JOIN components ON bugs.component_id = components.id '
            '  WHERE bug_id = %d' % bug_id)
        if self.cursor.rowcount != 1:
            raise NotFoundError('could not look up bug %d' % bug_id)
        (bug_id, assigned_to, bug_file_loc, bug_severity, bug_status,
         creation_ts, short_desc, op_sys, priority, product,
         rep_platform, reporter, version, component, resolution,
         target_milestone, qa_contact, status_whiteboard, keywords,
         alias) = self.cursor.fetchone()

        bug_file_loc = self._decode(bug_file_loc)
        creation_ts = _add_tz(creation_ts)
        product = self._decode(product)
        version = self._decode(version)
        component = self._decode(component)
        status_whiteboard = self._decode(status_whiteboard)
        keywords = self._decode(keywords)
        alias = self._decode(alias)

        return (bug_id, assigned_to, bug_file_loc, bug_severity,
                bug_status, creation_ts, short_desc, op_sys, priority,
                product, rep_platform, reporter, version, component,
                resolution, target_milestone, qa_contact,
                status_whiteboard, keywords, alias)

    def get_bug_ccs(self, bug_id):
        """Get the IDs of the people CC'd to the bug."""
        self.cursor.execute('SELECT who FROM cc WHERE bug_id = %d'
                            % bug_id)
        return [row[0] for row in self.cursor.fetchall()]

    def get_bug_comments(self, bug_id):
        """Get the comments for the bug."""
        self.cursor.execute('SELECT who, bug_when, thetext '
                            '  FROM longdescs '
                            '  WHERE bug_id = %d '
                            '  ORDER BY bug_when' % bug_id)
        # XXX: 2005-12-07 jamesh
        # Due to a bug in Debzilla, Ubuntu bugzilla bug 248 has > 7800
        # duplicate comments,consisting of someone's signature.
        # For the import, just ignore those comments.
        return [(who, _add_tz(when), self._decode(thetext))
                 for (who, when, thetext) in self.cursor.fetchall()
                 if thetext != '\n--=20\n   Jacobo Tarr=EDo     |     '
                               'http://jacobo.tarrio.org/\n\n\n']

    def get_bug_attachments(self, bug_id):
        """Get the attachments for the bug."""
        self.cursor.execute('SELECT attach_id, creation_ts, description, '
                            '    mimetype, ispatch, filename, thedata, '
                            '    submitter_id '
                            '  FROM attachments '
                            '  WHERE bug_id = %d '
                            '  ORDER BY attach_id' % bug_id)
        return [(attach_id, _add_tz(creation_ts),
                 self._decode(description), mimetype,
                 ispatch, self._decode(filename), thedata, submitter_id)
                for (attach_id, creation_ts, description,
                     mimetype, ispatch, filename, thedata,
                     submitter_id) in self.cursor.fetchall()]

    def find_bugs(self, product=[], component=[], status=[]):
        """Returns the requested bug IDs as a list"""
        joins = []
        conditions = []
        if product:
            joins.append('INNER JOIN products ON bugs.product_id = products.id')
            conditions.append('products.name IN (%s)' %
                ', '.join([self.conn.escape(p) for p in product]))
        if component:
            joins.append('INNER JOIN components ON bugs.component_id = components.id')
            conditions.append('components.name IN (%s)' %
                ', '.join([self.conn.escape(c) for c in component]))
        if status:
            conditions.append('bugs.bug_status IN (%s)' %
                ', '.join([self.conn.escape(s) for s in status]))
        if conditions:
            conditions = 'WHERE %s' % ' AND '.join(conditions)
        else:
            conditions = ''
        self.cursor.execute('SELECT bug_id FROM bugs %s %s ORDER BY bug_id' %
                            (' '.join(joins), conditions))
        return [bug_id for (bug_id,) in self.cursor.fetchall()]

    def get_duplicates(self):
        """Returns a list of (dupe_of, dupe) relations."""
        self.cursor.execute('SELECT dupe_of, dupe FROM duplicates '
                            'ORDER BY dupe, dupe_of')
        return [(dupe_of, dupe) for (dupe_of, dupe) in self.cursor.fetchall()]

class Bug:
    """Representation of a Bugzilla Bug"""
    def __init__(self, backend, bug_id):
        self.backend = backend
        (self.bug_id, self.assigned_to, self.bug_file_loc, self.bug_severity,
         self.bug_status, self.creation_ts, self.short_desc, self.op_sys,
         self.priority, self.product, self.rep_platform, self.reporter,
         self.version, self.component, self.resolution,
         self.target_milestone, self.qa_contact, self.status_whiteboard,
         self.keywords, self.alias) = backend.get_bug_info(bug_id)

        self._ccs = None
        self._comments = None
        self._attachments = None

    @property
    def ccs(self):
        """Return the IDs of people CC'd to this bug"""
        if self._ccs is not None: return self._ccs
        self._ccs = self.backend.get_bug_ccs(self.bug_id)
        return self._ccs

    @property
    def comments(self):
        """Return the comments attached to this bug"""
        if self._comments is not None: return self._comments
        self._comments = self.backend.get_bug_comments(self.bug_id)
        return self._comments

    @property
    def attachments(self):
        """Return the attachments for this bug"""
        if self._attachments is not None: return self._attachments
        self._attachments = self.backend.get_bug_attachments(self.bug_id)
        return self._attachments

    def map_severity(self, bugtask):
        """Set a Launchpad bug task's severity based on this bug's severity."""
        bugtask.severity = {
            'blocker': BugTaskSeverity.CRITICAL,
            'critical': BugTaskSeverity.CRITICAL,
            'major': BugTaskSeverity.MAJOR,
            'normal': BugTaskSeverity.NORMAL,
            'minor': BugTaskSeverity.MINOR,
            'trivial': BugTaskSeverity.MINOR,
            'enhancement': BugTaskSeverity.WISHLIST
            }.get(self.bug_severity, BugTaskSeverity.NORMAL)

    def map_priority(self, bugtask):
        """Set a Launchpad bug task's priority based on this bug's priority."""
        bugtask.priority = {
            'P1': BugTaskPriority.HIGH,
            'P2': BugTaskPriority.MEDIUM,
            'P3': BugTaskPriority.MEDIUM,
            'P4': BugTaskPriority.LOW,
            'P5': BugTaskPriority.LOW
            }.get(self.priority, BugTaskPriority.MEDIUM)

    def map_status(self, bugtask):
        """Set a Launchpad bug task's status based on this bug's status.

        If the bug is in the RESOLVED, VERIFIED or CLOSED states, the
        bug resolution is also taken into account when mapping the
        status.

        If the bug is marked WONTFIX, set the bug task's priority to
        WONTFIX.

        Additional information about the bugzilla status is appended
        to the bug task's status explanation.
        """
        if self.bug_status == 'ASSIGNED':
            bugtask.status = BugTaskStatus.ACCEPTED
        elif self.bug_status == 'NEEDINFO':
            bugtask.status = BugTaskStatus.NEEDINFO
        elif self.bug_status == 'PENDINGUPLOAD':
            bugtask.status = BugTaskStatus.PENDINGUPLOAD
        elif self.bug_status in ['RESOLVED', 'VERIFIED', 'CLOSED']:
            # depends on the resolution:
            if self.resolution == 'FIXED':
                bugtask.status = BugTaskStatus.FIXED
            elif self.resolution == 'WONTFIX':
                bugtask.status = BugTaskStatus.REJECTED
                bugtask.priority = BugTaskPriority.WONTFIX
            else:
                bugtask.status = BugTaskStatus.REJECTED
        else:
            bugtask.status = BugTaskStatus.NEW

        # add the status to the notes section, to account for any lost
        # information
        bugzilla_status = 'Bugzilla status=%s' % self.bug_status
        if self.resolution:
            bugzilla_status += ' %s' % self.resolution
        bugzilla_status += ', product=%s' % self.product
        bugzilla_status += ', component=%s' % self.component

        if bugtask.statusexplanation:
            bugtask.statusexplanation = '%s (%s)' % (bugtask.statusexplanation,
                                                     bugzilla_status)
        else:
            bugtask.statusexplanation = bugzilla_status


class Bugzilla:
    """Representation of a bugzilla instance"""

    def __init__(self, conn):
        if conn is not None:
            self.backend = BugzillaBackend(conn)
        else:
            self.backend = None
        self.ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        self.debian = getUtility(ILaunchpadCelebrities).debian
        self.bugtracker = getUtility(ILaunchpadCelebrities).ubuntu_bugzilla
        self.debbugs = getUtility(ILaunchpadCelebrities).debbugs
        self.bugset = getUtility(IBugSet)
        self.bugtaskset = getUtility(IBugTaskSet)
        self.bugwatchset = getUtility(IBugWatchSet)
        self.cveset = getUtility(ICveSet)
        self.milestoneset = getUtility(IMilestoneSet)
        self.extrefset = getUtility(IBugExternalRefSet)
        self.personset = getUtility(IPersonSet)
        self.emailset = getUtility(IEmailAddressSet)
        self.person_mapping = {}

    def person(self, bugzilla_id):
        """Get the Launchpad person corresponding to the given Bugzilla ID"""
        # Bugzilla treats a user ID of 0 as a NULL
        if bugzilla_id == 0:
            return None

        # Try and get the person using a cache of the mapping.  We
        # check to make sure the person still exists and has not been
        # merged.
        person = None
        launchpad_id = self.person_mapping.get(bugzilla_id)
        if launchpad_id is not None:
            try:
                person = self.personset[launchpad_id]
                if person.merged is not None:
                    person = None
            except NotFoundError:
                pass

        # look up the person
        if person is None:
            email, displayname = self.backend.lookup_user(bugzilla_id)

            person = self.personset.ensurePerson(
                email=email, displayname=displayname)

            # Bugzilla performs similar address checks to Launchpad, so
            # if the Launchpad account has no preferred email, use the
            # Bugzilla one.
            emailaddr = self.emailset.getByEmail(email)
            assert emailaddr is not None
            if person.preferredemail != emailaddr:
                person.validateAndEnsurePreferredEmail(emailaddr)
                
            self.person_mapping[bugzilla_id] = person.id

        return person

    def get_launchpad_bug_target(self, bug):
        """Returns a dictionary of arguments to createBug() that correspond
        to the given bugzilla bug.
        """
        # we currently only support mapping Ubuntu bugs ...
        if bug.product != 'Ubuntu':
            raise AssertionError('product must be Ubuntu')
        
        # XXX: 20051208 jamesh
        # ValueError is caught here because of https://launchpad.net/bugs/4810
        try:
            srcpkg, binpkg = self.ubuntu.getPackageNames(
                bug.component.encode('ASCII'))
        except ValueError:
            logger.warning('could not find package name for "%s"',
                           bug.component.encode('ASCII'), exc_info=True)
            srcpkg = binpkg = None

        return {
            'distribution': self.ubuntu,
            'sourcepackagename': srcpkg,
            'binarypackagename': binpkg
            }

    def get_launchpad_milestone(self, bug):
        """Return the Launchpad milestone for a Bugzilla bug.

        If the milestone does not exist, then it is created.
        """
        if bug.product != 'Ubuntu':
            raise AssertionError('product must be Ubuntu')

        # Bugzilla uses a value of "---" to represent "no selected Milestone"
        # Launchpad represents this by setting the milestone column to NULL.
        if bug.target_milestone is None or bug.target_milestone == '---':
            return None

        # generate a Launchpad name from the Milestone name:
        name = re.sub(r'[^a-z0-9\+\.\-]', '-', bug.target_milestone.lower())

        for milestone in self.ubuntu.milestones:
            if milestone.name == name:
                return milestone
        else:
            milestone = self.milestoneset.new(name, distribution=self.ubuntu)
            return milestone

    def get_launchpad_upstream_product(self, bug):
        """Find the upstream product for the given Bugzilla bug.

        This function relies on the package -> product linkage having been
        entered in advance.
        """
        # we currently only support mapping Ubuntu bugs ...
        if bug.product != 'Ubuntu':
            raise AssertionError('product must be Ubuntu')

        # XXX: 20051208 jamesh
        # ValueError is caught here because of https://launchpad.net/bugs/4810
        try:
            srcpkgname, binpkgname = self.ubuntu.getPackageNames(
                bug.component.encode('ASCII'))
        except ValueError:
            logger.warning('could not find package name for "%s"',
                           bug.component.encode('ASCII'), exc_info=True)
            return None

        # find a product series
        series = None
        for release in self.ubuntu.releases:
            srcpkg = release.getSourcePackage(srcpkgname)
            if srcpkg:
                series = srcpkg.productseries
                if series:
                    return series.product
        else:
            logger.warning('could not find upstream product for '
                           'source package "%s"', srcpkgname.name)
            return None
        
    _bug_re = re.compile('bug\s*#?\s*(?P<id>\d+)', re.IGNORECASE)
    def replace_bug_ref(self, match):
        # XXX: 20051024 jamesh
        # this is where bug number rewriting would be plugged in
        bug_id = int(match.group('id'))
        url = urlparse.urljoin(self.bugtracker.baseurl,
                               'show_bug.cgi?id=%d' % bug_id)
        return '%s [%s]' % (match.group(0), url)


    def handle_bug(self, bug_id):
        """Maybe import a single bug.

        If the bug has already been imported (detected by checking for
        a bug watch), it is skipped.
        """
        logger.info('Handling Bugzilla bug %d', bug_id)
        
        # is there a bug watch on the bug?
        lp_bug = self.bugset.queryByRemoteBug(self.bugtracker, bug_id)

        # if we already have an associated bug, don't add a new one.
        if lp_bug is not None:
            logger.info('Bugzilla bug %d is already being watched by '
                        'Launchpad bug %d', bug_id, lp_bug.id)
            return lp_bug

        bug = Bug(self.backend, bug_id)

        comments = bug.comments[:]

        # create a message for the initial comment:
        msgset = getUtility(IMessageSet)
        who, when, text = comments.pop(0)
        text = self._bug_re.sub(self.replace_bug_ref, text)
        # the initial comment can't be empty
        if not text.strip():
            text = '<empty comment>'
        msg = msgset.fromText(bug.short_desc, text, self.person(who), when)

        # create the bug
        target = self.get_launchpad_bug_target(bug)
        lp_bug = self.bugset.createBug(msg=msg,
                                       datecreated=bug.creation_ts,
                                       title=bug.short_desc,
                                       owner=self.person(bug.reporter),
                                       **target)

        # add the bug watch:
        lp_bug.addWatch(self.bugtracker, bug.bug_id, lp_bug.owner)

        # add remaining comments, and add CVEs found in all text
        lp_bug.findCvesInText(text)
        for (who, when, text) in comments:
            text = self._bug_re.sub(self.replace_bug_ref, text)
            msg = msgset.fromText(msg.followup_title, text,
                                  self.person(who), when)
            lp_bug.linkMessage(msg)
            lp_bug.findCvesInText(text)

        # subscribe QA contact and CC's
        if bug.qa_contact:
            lp_bug.subscribe(self.person(bug.qa_contact))
        for cc in bug.ccs:
            lp_bug.subscribe(self.person(cc))

        # if a URL is associated with the bug, add it:
        if bug.bug_file_loc:
            self.extrefset.createBugExternalRef(lp_bug, bug.bug_file_loc,
                                                bug.bug_file_loc,
                                                lp_bug.owner)

        # translate bugzilla status and severity to LP equivalents
        task = lp_bug.bugtasks[0]
        task.datecreated = bug.creation_ts
        task.assignee = self.person(bug.assigned_to)
        task.statusexplanation = bug.status_whiteboard
        bug.map_severity(task)
        bug.map_priority(task)
        bug.map_status(task)

        # bugs with an alias of the form "deb1234" have been imported
        # from the Debian bug tracker by the "debzilla" program.  For
        # these bugs, generate a task and watch on the corresponding
        # bugs.debian.org bug.
        if bug.alias and re.match(r'^deb\d+$', bug.alias):
            watch = self.bugwatchset.createBugWatch(
                lp_bug, lp_bug.owner, self.debbugs, int(bug.alias[3:]))
            debtask = self.bugtaskset.createTask(
                lp_bug,
                owner=lp_bug.owner,
                distribution=self.debian,
                binarypackagename=target['binarypackagename'],
                sourcepackagename=target['sourcepackagename'])
            debtask.datecreated = bug.creation_ts
            debtask.bugwatch = watch

        # for UPSTREAM bugs, try to find whether the URL field contains
        # a bug reference.
        if bug.bug_status == 'UPSTREAM':
            # see if the URL field contains a bug tracker reference
            watches = self.bugwatchset.fromText(bug.bug_file_loc,
                                                lp_bug, lp_bug.owner)
            # find the upstream product for this bug
            product = self.get_launchpad_upstream_product(bug)

            # if we created a watch, and there is an upstream product,
            # create a new task and link it to the watch.
            if len(watches) > 0:
                if product:
                    upstreamtask = self.bugtaskset.createTask(
                        lp_bug, product=product, owner=lp_bug.owner)
                    upstreamtask.datecreated = bug.creation_ts
                    upstreamtask.bugwatch = watches[0]
                else:
                    logger.warning('Could not find upstream product to link '
                                   'bug %d to', lp_bug.id)

        # translate milestone linkage
        task.milestone = self.get_launchpad_milestone(bug)

        # import attachments
        for (attach_id, creation_ts, description, mimetype, ispatch,
             filename, thedata, submitter_id) in bug.attachments:
            logger.debug('Creating attachment %s for bug %d',
                         filename, bug.bug_id)
            if ispatch:
                attach_type = BugAttachmentType.PATCH
                mimetype = 'text/plain'
            else:
                attach_type = BugAttachmentType.UNSPECIFIED

            # look for a message starting with "Created an attachment (id=NN)"
            for msg in lp_bug.messages:
                if msg.contents.startswith('Created an attachment (id=%d)'
                                           % attach_id):
                    break
            else:
                # could not find the add message, so create one:
                msg = msgset.fromText(description,
                                      'Created attachment %s' % filename,
                                      self.person(submitter_id),
                                      creation_ts)
                lp_bug.linkMessage(msg)

            filealias = getUtility(ILibraryFileAliasSet).create(
                name=filename,
                size=len(thedata),
                file=StringIO(thedata),
                contentType=mimetype)

            getUtility(IBugAttachmentSet).create(
                bug=lp_bug, filealias=filealias, attach_type=attach_type,
                title=description, message=msg)

        return lp_bug

    def process_duplicates(self, trans):
        """Mark Launchpad bugs as duplicates based on Bugzilla duplicates.

        Launchpad bug A will be marked as a duplicate of bug B if:
         * bug A watches bugzilla bug A'
         * bug B watches bugzilla bug B'
         * bug A' is a duplicate of bug B'
         * bug A is not currently a duplicate of any other bug.
        """
        logger.info('Processing duplicate bugs')
        bugmap = {}
        def getlpbug(bugid):
            """Get the Launchpad bug corresponding to the given remote ID

            This function makes use of a cache dictionary to reduce the
            number of lookups.
            """
            lpbugid = bugmap.get(bugid)
            if lpbugid is not None:
                if lpbugid != 0:
                    lpbug = self.bugset.get(lpbugid)
                else:
                    lpbug = None
            else:
                lpbug = self.bugset.queryByRemoteBug(self.bugtracker, bugid)
                if lpbug is not None:
                    bugmap[bugid] = lpbug.id
                else:
                    bugmap[bugid] = 0
            return lpbug

        for (dupe_of, dupe) in self.backend.get_duplicates():
            # get the Launchpad bugs corresponding to the two Bugzilla bugs:
            trans.begin()
            lpdupe_of = getlpbug(dupe_of)
            lpdupe = getlpbug(dupe)
            # if both bugs exist in Launchpad, and lpdupe is not already
            # a duplicate, mark it as a duplicate of lpdupe_of.
            if (lpdupe_of is not None and lpdupe is not None and
                lpdupe.duplicateof is None):
                logger.info('Marking %d as a duplicate of %d',
                            lpdupe.id, lpdupe_of.id)
                lpdupe.duplicateof = lpdupe_of
            trans.commit()

    def import_bugs(self, trans, product=[], component=[], status=[]):
        """Import Bugzilla bugs matching the given constraints.

        Each of product, component and status gives a list of
        products, components or statuses to limit the import to.  An
        empty list matches all products, components or statuses.
        """
        bugs = self.backend.find_bugs(product=product,
                                      component=component,
                                      status=status)
        for bug_id in bugs:
            trans.begin()
            try:
                self.handle_bug(bug_id)
            except (SystemExit, KeyboardInterrupt):
                raise
            except:
                logger.exception('Could not import Bugzilla bug #%d', bug_id)
                trans.abort()
            else:
                trans.commit()
