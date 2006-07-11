# Copyright 2006 Canonical Ltd.  All rights reserved.

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
    import cElementTree as ET
except:
    import elementtree.ElementTree as ET

from zope.component import getUtility
from zope.app.content_types import guess_content_type

from canonical.lp.dbschema import (
    BugTaskImportance, BugTaskStatus, BugAttachmentType)
from canonical.launchpad.interfaces import (
    IPersonSet, IEmailAddressSet, IBugSet, IMessageSet, IBugAttachmentSet,
    ILibraryFileAliasSet)

logger = logging.getLogger('canonical.launchpad.scripts.sftracker')

# when accessed anonymously, Sourceforge returns dates in this timezone:
SOURCEFORGE_TZ = pytz.timezone('US/Pacific')
UTC = pytz.timezone('UTC')

def _parse_date(datestr):
    year, month, day, hour, minute = time.strptime(datestr,
                                                   '%Y-%m-%d %H:%M')[:5]
    return datetime.datetime(year, month, day, hour, minute,
                             tzinfo=SOURCEFORGE_TZ).astimezone(UTC)


class TrackerAttachment:
    """An attachment associated with a SF tracker item"""

    def __init__(self, attachment_node):
        self.file_id = attachment_node.get('file_id')
        self.content_type = attachment_node.find('content_type').text
        self.title = attachment_node.find('description').text
        self.filename = attachment_node.find('title').text
        if self.filename.strip() == '':
            self.filename = 'untitled'
        el = attachment_node.find('date')
        if el:
            self.date = _parse_date(el.text)
        else:
            self.date = None
        el = attachment_node.find('sender')
        if el:
            self.sender = el.text
        else:
            self.sender = None
        self.data = attachment_node.find('data').text.decode('base-64')

    @property
    def is_patch(self):
        """True if this attachment is a patch

        As the sourceforge tracker does not differentiate between
        patches and other attachments, we need to use heuristics to
        differentiate.
        """
        return (self.filename.endswith('patch') or
                self.filename.endswith('diff'))


class TrackerItem:
    """An SF tracker item"""

    def __init__(self, item_node, summary_node):
        self.item_id = item_node.get('id')
        self.datecreated = _parse_date(item_node.find('date_submitted').text)
        self.date_last_updated = _parse_date(
            item_node.find('date_last_updated').text)
        self.title = item_node.find('summary').text
        self.description = item_node.find('description').text
        self.category = item_node.find('category').text
        self.group = item_node.find('group').text
        self.priority = item_node.find('priority').text
        self.resolution = item_node.find('resolution').text
        self.status = item_node.find('status').text
        # We get these two from the summary file because it contains user IDs
        self.reporter = summary_node.find('submitted_by').text
        self.assignee = summary_node.find('assigned_to').text
        # initial comment:
        self.comments = [(self.datecreated, self.reporter, self.description)]
        # remaining comments ...
        for comment_node in item_node.findall('comment'):
            dt = _parse_date(comment_node.find('date').text)
            sender = comment_node.find('sender').text
            description = comment_node.find('description').text
            # does this comment have headers?
            if description.startswith('Date:'):
                headers, description = description.split('\n\n', 1)
            self.comments.append((dt, sender, description))
        # attachments
        self.attachments = [TrackerAttachment(node)
                            for node in item_node.findall('attachment')]

    @property
    def lp_importance(self):
        """The Launchpad importance value for this item"""
        try:
            priority = int(self.priority)
        except ValueError:
            return BugTaskImportance.UNTRIAGED
        # make priority >= 9 CRITICAL
        if priority >= 9:
            return BugTaskImportance.CRITICAL
        elif priority >= 7:
            return BugTaskImportance.HIGH
        elif priority >= 4:
            return BugTaskImportance.MEDIUM
        else:
            return BugTaskImportance.LOW

    @property
    def lp_status(self):
        if self.status == 'Open':
            if self.resolution == 'Accepted':
                return BugTaskStatus.CONFIRMED
            else:
                return BugTaskStatus.UNCONFIRMED
        elif self.status == 'Closed':
            if self.resolution == 'Fixed':
                return BugTaskStatus.FIXRELEASED
            else:
                return BugTaskStatus.REJECTED
        elif self.status == 'Deleted':
            # XXXX: 2006-07-10 jamesh
            # do we ever get exported bugs with this status?
            return BugTaskStatus.UNCONFIRMED
        elif self.status == 'Pending':
            if self.resolution == 'Fixed':
                return BugTaskStatus.FIXCOMMITTED
            else:
                return BugTaskStatus.INPROGRESS
        raise AssertionError('Unhandled item status: (%s, %s)'
                             % (self.status, self.resolution))


class Tracker:
    """An SF tracker"""

    def __init__(self, dumpfile, dumpdir=None):
        """Create a Tracker instance.

        Dumpfile is a dump of the tracker as generated by xml-export.py
        Dumpdir contains the individual tracker item XML files.
        """
        self.data = ET.parse(dumpfile).getroot()
        if dumpdir is None:
            self.dumpdir = os.path.join(os.path.dirname(dumpfile),
                                        self.data.get('id'))
        else:
            self.dumpdir = dumpdir

    def __iter__(self):
        for item_node in self.data.findall('item'):
            # open the summary file
            summary_file = os.path.join(self.dumpdir,
                                        'item-%s.xml' % item_node.get('id'))
            summary_node = ET.parse(summary_file)
            yield TrackerItem(item_node, summary_node)


class TrackerImporter:
    """Helper class for importing SF tracker items into Launchpad"""

    def __init__(self, product, verify_users=False):
        self.product = product
        self.verify_users = verify_users
        self._person_id_cache = {}

    def person(self, userid):
        """Get the Launchpad user corresponding to the given SF user ID"""
        if userid is None or userid == 'nobody':
            return None
        
        email = '%s@users.sourceforge.net' % userid

        launchpad_id = self._person_id_cache.get(userid)
        if launchpad_id is not None:
            person = getUtility(IPersonSet).get(launchpad_id)
            if person is not None and person.merged is not None:
                person = None

        if person is None:
            person = getUtility(IPersonSet).getByEmail(email)
            if person is None:
                person, dummy = getUtility(IPersonSet).createPersonAndEmail(
                    email=email, name=userid)
            self._person_id_cache[userid] = person.id

        # if we are auto-verifying new accounts, make sure the person
        # has a preferred email
        if self.verify_users and person.preferredemail is None:
            emailaddr = getUtility(IEmailAddressSet).getByEmail(email)
            assert emailaddr is not None
            person.setPreferredEmail(emailaddr)

        return person

    def _createMessage(self, subject, date, userid, text):
        """Create an IMessage for a particular comment."""
        if not text.strip():
            text = '<empty comment>'
        return getUtility(IMessageSet).fromText(subject, text,
                                                self.person(userid), date)

    def importTrackerItem(self, item):
        """Import an SF tracker item into Launchpad.

        We identify SF tracker items by setting their nick name to
        'sf1234' where the SF item id was 1234.  If such a bug already
        exists, the import is skipped.
        """
        logger.info('Handling Sourceforge tracker item #%d', item.item_id)
        
        nickname = 'sf%s' % item.item_id
        try:
            bug = getUtility(IBugSet).getByNameOrID(nickname)
        except NotFoundError:
            bug = None

        if bug is not None:
            logger.info('Sourceforge bug %s has already been imported',
                        item.item_id)
            return bug

        comments_by_date_and_user = {}
        comments = item.comments[:]
        
        date, userid, text = comments.pop(0)
        msg = self._createMessage(bug.title, date, userid, text)
        comments_by_date_and_user[(date, userid)] = msg

        bug = getUtility(IBugSet).createBug(msg=msg,
                                            datecreated=item.datecreated,
                                            title=item.title,
                                            owner=self.person(item.reporter),
                                            product=self.product)
        bug.name = nickname
        bugtask = bug.bugtasks[0]

        # attach comments and create CVE links.
        bug.findCvesInText(text)
        for (date, userid, text) in comments:
            msg = self._createMessage(bug.followup_subject(), date,
                                      userid, text)
            bug.linkMessage(msg)
            bug.findCvesInText(text)
            comments_by_date_and_user[(date, userid)] = msg

        # set up bug task
        bugtask.datecreated = item.datecreated
        bugtask.importance = item.lp_importance
        bugtask.transitionToStatus(item.lp_status)
        bugtask.transitionToAssignee(self.person(item.assignee))

        # XXXX: 2006-07-11 jamesh
        # Need to translate item.category to keywords
        # Need to translate item.group to a milestone

        # Convert attachments
        for attachment in item.attachments:
            if attachment.is_patch:
                attach_type = BugAttachmentType.PATCH
                mimetype = 'text/plain'
            else:
                attach_type = BugAttachmentType.UNSPECIFIED
                # we can't trust the content type given by SF
                mimetype, encoding = guess_content_type(
                    name=attachment.filename, body=attachment.data)

            # do we already have the message for this bug?
            msg = comments_by_date_and_user.get((attachment.date,
                                                 attachment.sender))
            if msg is None:
                msg = self._createMessage(
                    attachment.title,
                    attachment.date,
                    attachment.sender,
                    'Created attachment %s' % attachment.filename)
                bug.linkMessage(msg)
                comments_by_date_and_user[(attachment.date,
                                           attachment.sender)] = msg

            # upload the attachment and add to the bug.
            filealias = getUtility(ILibraryFileAliasSet).create(
                name=attachment.filename,
                size=len(attachment.data),
                file=StringIO(attachment.data),
                contentType=mimetype)

            getUtility(IBugAttachmentSet).create(
                bug=bug,
                filealias=filealias,
                attach_type=attach_type,
                title=attachment.title,
                message=msg)

        return bug

    def importTracker(self, ztm, tracker):
        """Import bugs from the given tracker"""
        for item in tracker:
            ztm.begin()
            try:
                self.importTrackerItem(item)
            except (SystemExit, KeyboardInterrupt):
                raise
            except:
                logger.exception('Could not import item #%d', item.item_id)
                ztm.abort()
            else:
                ztm.commit()
