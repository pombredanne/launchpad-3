# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Bug Import code"""


"""Sourceforge.net Tracker import logic.

This code relies on the output of Frederik Lundh's Sourceforge tracker
screen-scraping tools:

  http://effbot.org/zone/sandbox-sourceforge.htm
"""

__metaclass__ = type

__all__ = [
    'Tracker',
    'TrackerImporter'
    ]

from cStringIO import StringIO
import datetime
import logging
import os
import sys
import time

import pytz

# use cElementTree if it is available ...
try:
    import xml.elementtree.cElementTree as ET
except ImportError:
    import cElementTree as ET

from zope.component import getUtility
from zope.app.content_types import guess_content_type

from canonical.database.constants import UTC_NOW
from canonical.launchpad.interfaces import (
    IBugSet, IBugActivitySet, IBugAttachmentSet, IBugExternalRefSet,
    ICveSet, IEmailAddressSet, ILaunchpadCelebrities, ILibraryFileAliasSet,
    IMessageSet, IMilestoneSet, IPersonSet, CreateBugParams,
    NotFoundError)
from canonical.launchpad.scripts.bugexport import BUGS_XMLNS
from canonical.lp.dbschema import (
    BugTaskImportance, BugTaskStatus, BugAttachmentType,
    PersonCreationRationale)


logger = logging.getLogger('canonical.launchpad.scripts.bugimport')

# when accessed anonymously, Sourceforge returns dates in this timezone:
UTC = pytz.timezone('UTC')


class BugXMLSyntaxError(Exception):
    pass


def parse_date(datestr):
    if datestr in ['', None]:
        return None
    year, month, day, hour, minute, second = time.strptime(
        datestr, '%Y-%m-%dT%H:%M:%SZ')[:6]
    return datetime.datetime(year, month, day, hour, minute, tzinfo=UTC)


def get_enum_value(enumtype, name):
    for item in enumtype.items:
        if item.name == name:
            return item
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
    childnode =  get_element(node, name)
    if childnode is None:
        return None
    return childnode.text.strip()


def get_all(node, name):
    """Get a list of all elements with the given name."""
    # alter the name to use the Launchpad bugs XML namespace
    name = '/'.join(['{%s}%s' % (BUGS_XMLNS, part)
                     for part in name.split('/')])
    return node.findall(name)


class BugImporter:
    """Import bugs into Launchpad"""

    def __init__(self, product, filename, verify_users=False):
        self.product = product
        self.filename = filename
        self.verify_users = verify_users
        self.person_id_cache = {}
        self.bug_importer = getUtility(ILaunchpadCelebrities).bug_importer
        
        self.bug_id_map = {}
        self.duplicate_bugs = {}

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

        displayname = node.text.strip()
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

    def haveImportedBug(self, bugnode):
        """Return True if the given bug has been imported already."""
        bug_id = int(bugnode.get('id'))
        # XXX: this should be extended to cover other cases like
        # identity based on bug nickname.
        return bug_id in self.bug_id_map

    def importBugs(self, ztm):
        """Import bugs from a file."""
        tree = ET.parse(self.filename)
        root = tree.getroot()
        # Basic sanity check that we have the correct type of XML:
        assert root.tag == '{%s}launchpad-bugs' % BUGS_XMLNS
        for bugnode in get_all(root, 'bug'):
            if self.haveImportedBug(bugnode):
                continue
            ztm.begin()
            try:
                self.importBug(bugnode)
            except (SystemExit, KeyboardInterrupt):
                raise
            except:
                logger.exception('Could not import bug #%s',
                                 bugnode.get('id'))
                ztm.abort()
            else:
                ztm.commit()

    def importBug(self, bugnode):
        if self.haveImportedBug(bugnode):
            return
        bug_id = int(bugnode.get('id'))
        logger.info('Handling bug %d', bug_id)

        comments = get_all(bugnode, 'comment')

        owner = self.getPerson(get_element(bugnode, 'reporter'))
        datecreated = parse_date(get_value(bugnode, 'datecreated'))
        title = get_value(bugnode, 'title')
        
        if owner is None:
            owner = self.bug_importer
        commentnode = comments.pop(0)
        msg = self.createMessage(commentnode, defaulttitle=title)

        bug = self.product.createBug(CreateBugParams(
            msg=msg,
            datecreated=datecreated,
            title=title,
            owner=owner))
        bugtask = bug.bugtasks[0]
        logger.info('Creating Launchpad bug #%d', bug.id)

        # Remaining setup for first comment
        self.createAttachments(bug, msg, commentnode)
        bug.findCvesInText(msg.text_contents)

        # Process remaining comments
        for commentnode in comments:
            msg = self.createMessage(commentnode,
                                     defaulttitle=bug.followup_subject())
            bug.linkMessage(msg)
            self.createAttachments(bug, msg, commentnode)
            bug.findCvesInText(msg.text_contents)

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
                title=urlnode.text.strip(),
                owner=bug.owner)

        for cvenode in get_all(bugnode, 'cves/cve'):
            cve = getUtility(ICveSet)[cvenode.text.strip()]
            if cve is None:
                raise BugXMLSyntaxError('Unknown CVE: %s' %
                                        cvenode.text.strip())
            bug.linkCVE(cve)

        tags = []
        for tagnode in get_all(bugnode, 'tags/tag'):
            tags.append(tagnode.text.strip())
        bug.tags = tags

        for subscribernode in get_all(bugnode, 'subscriptions/subscriber'):
            person = self.getPerson(subscribernode)
            bug.subscribe(person)

        # set up bug task
        bugtask.datecreated = datecreated
        bugtask.importance = get_enum_value(BugTaskImportance,
                                            get_value(bugnode, 'importance'))
        bugtask.transitionToStatus(
            get_enum_value(BugTaskStatus, get_value(bugnode, 'status')))
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

        self.bug_id_map[bug_id] = bug.id
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
        if text is None or text.strip() == '':
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
