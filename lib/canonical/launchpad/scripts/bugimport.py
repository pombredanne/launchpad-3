# Copyright 2006 Canonical Ltd.  All rights reserved.

"""An XML bug importer

This code can import an XML bug dump into Launchpad.  The XML format
is described in the RELAX-NG schema 'doc/bug-export.rnc'.
"""


__metaclass__ = type

__all__ = [
    'BugXMLSyntaxError',
    'BugImporter',
    ]

import cPickle
from cStringIO import StringIO
import datetime
import logging
import os
import time

try:
    import xml.elementtree.cElementTree as ET
except ImportError:
    import cElementTree as ET

import pytz

from zope.component import getUtility
from zope.app.content_types import guess_content_type

from canonical.database.constants import UTC_NOW
from canonical.launchpad.interfaces import (
    IBugSet, IBugActivitySet, IBugAttachmentSet, IBugExternalRefSet,
    ICveSet, IEmailAddressSet, ILaunchpadCelebrities, PersonCreationRationale,
    ILibraryFileAliasSet, IMessageSet, IPersonSet, CreateBugParams)
from canonical.launchpad.scripts.bugexport import BUGS_XMLNS
from canonical.lp.dbschema import (
    BugTaskImportance, BugTaskStatus, BugAttachmentType)


logger = logging.getLogger('canonical.launchpad.scripts.bugimport')

UTC = pytz.timezone('UTC')


class BugXMLSyntaxError(Exception):
    """A syntax error was detected in the input."""


def parse_date(datestr):
    """Parse a date in the format 'YYYY-MM-DDTHH:MM:SSZ' to a dattime."""
    if datestr in ['', None]:
        return None
    year, month, day, hour, minute, second = time.strptime(
        datestr, '%Y-%m-%dT%H:%M:%SZ')[:6]
    return datetime.datetime(year, month, day, hour, minute, tzinfo=UTC)


def get_text(node):
    """Get the text content of an element."""
    if node is None:
        return None
    if len(node) != 0:
        raise BugXMLSyntaxError('No child nodes are expected for <%s>'
                                % node.tag)
    if node.text is None:
        return ''
    return node.text.strip()


def get_enum_value(enumtype, name):
    """Get the dbschema enum value with the given name."""
    try:
        return enumtype.items[name]
    except KeyError:
        raise BugXMLSyntaxError('%s is not a valid %s enumeration value' %
                                (name, enumtype.__name__))


def get_element(node, name):
    """Get the first element with the given name in the bugs XML namespace."""
    # alter the name to use the Launchpad bugs XML namespace
    name = '/'.join(['{%s}%s' % (BUGS_XMLNS, part)
                     for part in name.split('/')])
    return node.find(name)


def get_value(node, name):
    """Return the text value of the element with the given name."""
    childnode = get_element(node, name)
    return get_text(childnode)


def get_all(node, name):
    """Get a list of all elements with the given name."""
    # alter the name to use the Launchpad bugs XML namespace
    name = '/'.join(['{%s}%s' % (BUGS_XMLNS, part)
                     for part in name.split('/')])
    return node.findall(name)


class BugImporter:
    """Import bugs into Launchpad"""

    def __init__(self, product, bugs_filename, cache_filename,
                 verify_users=False):
        self.product = product
        self.bugs_filename = bugs_filename
        self.cache_filename = cache_filename
        self.verify_users = verify_users
        self.person_id_cache = {}
        self.bug_importer = getUtility(ILaunchpadCelebrities).bug_importer

        # A mapping of old bug IDs to new Launchpad Bug IDs
        self.bug_id_map = {}
        # A mapping of old bug IDs to a list of Launchpad Bug IDs that are
        # duplicates of this bug.
        self.pending_duplicates = {}

    def getPerson(self, node):
        """Get the Launchpad user corresponding to the given XML node"""
        if node is None:
            return None

        # special case for "nobody"
        name = node.get('name')
        if name == 'nobody':
            return None

        # We require an email address:
        email = node.get('email')
        if email is None:
            raise BugXMLSyntaxError('element %s (name=%s) has no email address'
                                    % (node.tag, name))

        displayname = get_text(node)
        if not displayname:
            displayname = None

        launchpad_id = self.person_id_cache.get(email)
        if launchpad_id is not None:
            person = getUtility(IPersonSet).get(launchpad_id)
            if person is not None and person.merged is not None:
                person = None
        else:
            person = None

        if person is None:
            person = getUtility(IPersonSet).getByEmail(email)
            if person is None:
                logger.debug('creating person for %s' % email)
                # has the short name been taken?
                if name is not None:
                    person = getUtility(IPersonSet).getByName(name)
                    if person is not None:
                        name = None
                person, address = getUtility(IPersonSet).createPersonAndEmail(
                    email=email, name=name, displayname=displayname,
                    rationale=PersonCreationRationale.BUGIMPORT,
                    comment='when importing bugs for %s'
                            % self.product.displayname)
            self.person_id_cache[email] = person.id

        # if we are auto-verifying new accounts, make sure the person
        # has a preferred email
        if self.verify_users and person.preferredemail is None:
            address = getUtility(IEmailAddressSet).getByEmail(email)
            assert address is not None
            person.setPreferredEmail(address)

        return person

    def getMilestone(self, name):
        if name in ['', None]:
            return None

        milestone = self.product.getMilestone(name)
        if milestone is not None:
            return milestone

        # Add the milestones to the development focus series of the product
        series = self.product.development_focus
        return series.newMilestone(name)

    def loadCache(self):
        """Load the Bug ID mapping and pending duplicates list from cache."""
        if not os.path.exists(self.cache_filename):
            self.bug_id_map = {}
            self.pending_duplicates = {}
        else:
            self.bug_id_map, self.pending_duplicates = cPickle.load(
                open(self.cache_filename, 'rb'))

    def saveCache(self):
        """Save the bug ID mapping and pending duplicates list to cache."""
        tmpfilename = '%s.tmp' % self.cache_filename
        fp = open(tmpfilename, 'wb')
        cPickle.dump((self.bug_id_map, self.pending_duplicates),
                     fp, protocol=2)
        fp.close()
        os.rename(tmpfilename, self.cache_filename)

    def haveImportedBug(self, bugnode):
        """Return True if the given bug has been imported already."""
        bug_id = int(bugnode.get('id'))
        # XXX: jamesh 2007-03-16:
        # This should be extended to cover other cases like identity
        # based on bug nickname.
        return bug_id in self.bug_id_map

    def importBugs(self, ztm):
        """Import bugs from a file."""
        tree = ET.parse(self.bugs_filename)
        root = tree.getroot()
        assert root.tag == '{%s}launchpad-bugs' % BUGS_XMLNS, (
            "Root element is wrong: %s" % root.tag)
        for bugnode in get_all(root, 'bug'):
            if self.haveImportedBug(bugnode):
                continue
            ztm.begin()
            try:
                # The cache is loaded before we import the bug so that
                # changes to the bug mapping and pending duplicates
                # made by failed bug imports don't affect this bug.
                self.loadCache()
                self.importBug(bugnode)
                self.saveCache()
            except (SystemExit, KeyboardInterrupt):
                raise
            except:
                logger.exception('Could not import bug #%s',
                                 bugnode.get('id'))
                ztm.abort()
            else:
                ztm.commit()

    def importBug(self, bugnode):
        assert not self.haveImportedBug(bugnode), (
            'the bug has already been imported')
        bug_id = int(bugnode.get('id'))
        logger.info('Handling bug %d', bug_id)

        comments = get_all(bugnode, 'comment')

        owner = self.getPerson(get_element(bugnode, 'reporter'))
        datecreated = parse_date(get_value(bugnode, 'datecreated'))
        title = get_value(bugnode, 'title')

        private = get_value(bugnode, 'private') == 'True'
        security_related = get_value(bugnode, 'security_related') == 'True'

        if owner is None:
            owner = self.bug_importer
        commentnode = comments.pop(0)
        msg = self.createMessage(commentnode, defaulttitle=title)

        bug = self.product.createBug(CreateBugParams(
            msg=msg,
            datecreated=datecreated,
            title=title,
            private=private or security_related,
            security_related=security_related,
            owner=owner))
        bug.private = private
        bugtask = bug.bugtasks[0]
        logger.info('Creating Launchpad bug #%d', bug.id)

        # Remaining setup for first comment
        self.createAttachments(bug, msg, commentnode)
        bug.findCvesInText(msg.text_contents, bug.owner)

        # Process remaining comments
        for commentnode in comments:
            msg = self.createMessage(commentnode,
                                     defaulttitle=bug.followup_subject())
            bug.linkMessage(msg)
            self.createAttachments(bug, msg, commentnode)

        # set up bug
        bug.private = get_value(bugnode, 'private') == 'True'
        bug.security_related = get_value(bugnode, 'security_related') == 'True'
        bug.name = get_value(bugnode, 'nickname')
        description = get_value(bugnode, 'description')
        if description:
            bug.description = description

        for urlnode in get_all(bugnode, 'urls/url'):
            getUtility(IBugExternalRefSet).createBugExternalRef(
                bug=bug,
                url=urlnode.get('href'),
                title=get_text(urlnode),
                owner=bug.owner)

        for cvenode in get_all(bugnode, 'cves/cve'):
            cve = getUtility(ICveSet)[get_text(cvenode)]
            if cve is None:
                raise BugXMLSyntaxError('Unknown CVE: %s' %
                                        get_text(cvenode))
            bug.linkCVE(cve, self.bug_importer)

        tags = []
        for tagnode in get_all(bugnode, 'tags/tag'):
            tags.append(get_text(tagnode))
        bug.tags = tags

        for subscribernode in get_all(bugnode, 'subscriptions/subscriber'):
            person = self.getPerson(subscribernode)
            if person is not None:
                bug.subscribe(person)

        # set up bug task
        bugtask.datecreated = datecreated
        bugtask.importance = get_enum_value(BugTaskImportance,
                                            get_value(bugnode, 'importance'))
        bugtask.transitionToStatus(
            get_enum_value(BugTaskStatus, get_value(bugnode, 'status')),
            self.bug_importer)
        bugtask.transitionToAssignee(
            self.getPerson(get_element(bugnode, 'assignee')))
        bugtask.milestone = self.getMilestone(get_value(bugnode, 'milestone'))

        # Make a note of the import in the activity log:
        getUtility(IBugActivitySet).new(
            bug=bug.id,
            datechanged=UTC_NOW,
            person=self.bug_importer,
            whatchanged='bug',
            message='Imported external bug #%s' % bug_id)

        self.handleDuplicate(bug, bug_id, get_value(bugnode, 'duplicateof'))
        self.bug_id_map[bug_id] = bug.id

        # clear any pending bug notifications
        bug.expireNotifications()
        return bug

    def createMessage(self, commentnode, defaulttitle=None):
        """Create an IMessage representing a <comment> element."""
        title = get_value(commentnode, 'title')
        if title is None:
            title = defaulttitle
        sender = self.getPerson(get_element(commentnode, 'sender'))
        if sender is None:
            sender = self.bug_importer
        date = parse_date(get_value(commentnode, 'date'))
        if date is None:
            raise BugXMLSyntaxError('No date for comment %r' % title)
        text = get_value(commentnode, 'text')
        if text is None or text == '':
            text = '<empty comment>'
        return getUtility(IMessageSet).fromText(title, text, sender, date)

    def createAttachments(self, bug, message, commentnode):
        """Create attachments that were attached to the given comment."""
        for attachnode in get_all(commentnode, 'attachment'):
            if get_value(attachnode, 'type'):
                attach_type = get_enum_value(BugAttachmentType,
                                             get_value(attachnode, 'type'))
            else:
                attach_type = BugAttachmentType.UNSPECIFIED
            filename = get_value(attachnode, 'filename')
            title = get_value(attachnode, 'title')
            mimetype = get_value(attachnode, 'mimetype')
            contents = get_value(attachnode, 'contents').decode('base-64')
            if filename is None:
                # if filename is None, use the last component of the URL
                if attachnode.get('href') is not None:
                    filename = attachnode.get('href').split('/')[-1]
                else:
                    filename = 'unknown'
            if title is None:
                title = filename
            # force mimetype to text/plain if it is a patch
            if attach_type == BugAttachmentType.PATCH:
                mimetype = 'text/plain'
            # If we don't have a mime type, or it is classed as
            # straight binary data, sniff the mimetype
            if (mimetype is None or
                mimetype.startswith('application/octet-stream')):
                mimetype, encoding = guess_content_type(
                    name=filename, body=contents)

            # Create the file in the librarian
            filealias = getUtility(ILibraryFileAliasSet).create(
                name=filename,
                size=len(contents),
                file=StringIO(contents),
                contentType=mimetype)

            getUtility(IBugAttachmentSet).create(
                bug=bug,
                filealias=filealias,
                attach_type=attach_type,
                title=title,
                message=message)

    def handleDuplicate(self, bug, bug_id, duplicateof=None):
        """Handle duplicate processing for the given bug report."""
        # update the bug ID map
        self.bug_id_map[bug_id] = bug.id
        # Are there any pending bugs that are duplicates of this bug?
        if bug_id in self.pending_duplicates:
            for other_bug_id in self.pending_duplicates[bug_id]:
                other_bug = getUtility(IBugSet).get(other_bug_id)
                logger.info('Marking bug %d as duplicate of bug %d',
                            other_bug.id, bug.id)
                other_bug.duplicateof = bug
            del self.pending_duplicates[bug_id]
        # Process this bug as a duplicate
        if duplicateof is not None:
            duplicateof = int(duplicateof)
            # Have we already imported the bug?
            if duplicateof in self.bug_id_map:
                other_bug = getUtility(IBugSet).get(
                    self.bug_id_map[duplicateof])
                logger.info('Marking bug %d as duplicate of bug %d',
                            bug.id, other_bug.id)
                bug.duplicateof = other_bug
            else:
                self.pending_duplicates.setdefault(
                    duplicateof, []).append(bug.id)
