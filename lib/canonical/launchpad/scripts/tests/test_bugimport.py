
import os
import pytz
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.database.sqlbase import cursor
from canonical.launchpad.components.externalbugtracker import (
    ExternalBugTracker)
from canonical.launchpad.database import BugNotification
from canonical.launchpad.interfaces import (
    BugAttachmentType, BugTaskImportance, BugTaskStatus, CreateBugParams,
    IBugSet, IEmailAddressSet, IPersonSet, IProductSet,
    PersonCreationRationale, UNKNOWN_REMOTE_IMPORTANCE)
from canonical.launchpad.scripts import bugimport
from canonical.launchpad.scripts.bugimport import ET
from canonical.launchpad.scripts.checkwatches import BugWatchUpdater

from canonical.testing import LaunchpadZopelessLayer
from canonical.launchpad.ftests import login, logout


class UtilsTestCase(unittest.TestCase):
    """Tests for the various utility functions used by the importer."""

    def test_parse_date(self):
        # Test that the parse_date() helper can correctly parse
        # timestamp strings.
        self.assertEqual(bugimport.parse_date(None), None)
        self.assertEqual(bugimport.parse_date(''), None)
        dt = bugimport.parse_date('2006-12-01T08:00:00Z')
        self.assertEqual(dt.year, 2006)
        self.assertEqual(dt.month, 12)
        self.assertEqual(dt.day, 1)
        self.assertEqual(dt.hour, 8)
        self.assertEqual(dt.minute, 0)
        self.assertEqual(dt.second, 0)
        self.assertEqual(dt.tzinfo, pytz.timezone('UTC'))

    def test_get_text(self):
        # Test that the get_text() helper can correctly return the
        # text content of an element.
        self.assertEqual(bugimport.get_text(None), None)
        node = ET.fromstring('<a/>')
        self.assertEqual(bugimport.get_text(node), '')
        node = ET.fromstring('<a>x</a>')
        self.assertEqual(bugimport.get_text(node), 'x')
        # whitespace at the beginning or end is stripped
        node = ET.fromstring('<a>  x\n  </a>')
        self.assertEqual(bugimport.get_text(node), 'x')
        # but internal whitespace is not normalised
        node = ET.fromstring('<a>  x    y\n  </a>')
        self.assertEqual(bugimport.get_text(node), 'x    y')
        # get_text() raises an error if there are subelements
        node = ET.fromstring('<a>x<b/></a>')
        self.assertRaises(bugimport.BugXMLSyntaxError,
                          bugimport.get_text, node)


    def test_get_enum_value(self):
        # Test that the get_enum_value() function returns the
        # appropriate enum value, or raises BugXMLSyntaxError if it is
        # not found.
        from canonical.launchpad.interfaces import BugTaskStatus
        self.assertEqual(bugimport.get_enum_value(BugTaskStatus,
                                                  'FIXRELEASED'),
                         BugTaskStatus.FIXRELEASED)
        self.assertRaises(bugimport.BugXMLSyntaxError,
                          bugimport.get_enum_value, BugTaskStatus,
                          'NO-SUCH-ENUM-VALUE')

    def test_get_element(self):
        # Test that the get_element() function returns the correct
        # element.
        node = ET.fromstring('''\
        <foo xmlns="https://launchpad.net/xmlns/2006/bugs">
          <bar xmlns="http://some/other/namespace">
            <baz/>
          </bar>
          <bar>
            <baz/>
          </bar>
        </foo>''')
        self.assertEqual(bugimport.get_element(node, 'no-element'), None)
        subnode = bugimport.get_element(node, 'bar')
        self.assertNotEqual(subnode, None)
        self.assertEqual(subnode.tag,
                         '{https://launchpad.net/xmlns/2006/bugs}bar')
        subnode = bugimport.get_element(node, 'bar/baz')
        self.assertNotEqual(subnode, None)
        self.assertEqual(subnode.tag,
                         '{https://launchpad.net/xmlns/2006/bugs}baz')

    def test_get_value(self):
        # Test that the get_value() helper correctly returns the text
        # content of the named element.
        node = ET.fromstring('''\
        <foo xmlns="https://launchpad.net/xmlns/2006/bugs">
          <bar xmlns="http://some/other/namespace">Bad Value</bar>
          <bar>   value 1</bar>
          <tag>
            <baz>
              value 2
            </baz>
          </tag>
        </foo>''')
        self.assertEqual(bugimport.get_value(node, 'no-element'), None)
        self.assertEqual(bugimport.get_value(node, 'bar'), 'value 1')
        self.assertEqual(bugimport.get_value(node, 'tag/baz'), 'value 2')

    def test_get_all(self):
        # Test that the get_all() helper returns all matching elements
        # in the bugs namespace.
        node = ET.fromstring('''\
        <foo xmlns="https://launchpad.net/xmlns/2006/bugs">
          <bar/>
          <bar/>
          <bar xmlns="http://some/other/namespace"/>
          <something>
            <bar/>
          </something>
        </foo>''')
        self.assertEqual(bugimport.get_all(node, 'no-element'), [])
        # get_all() only returns the direct children
        self.assertEqual(len(bugimport.get_all(node, 'bar')), 2)
        self.assertEqual(len(bugimport.get_all(node, 'something/bar')), 1)
        # list items are bar elements:
        self.assertEqual(bugimport.get_all(node, 'bar')[0].tag,
                         '{https://launchpad.net/xmlns/2006/bugs}bar')


class GetPersonTestCase(unittest.TestCase):
    """Tests for the BugImporter.getPerson() method."""
    layer = LaunchpadZopelessLayer

    def test_create_person(self):
        # Test that getPerson() can create new users.
        person = getUtility(IPersonSet).getByEmail('foo@example.com')
        self.assertEqual(person, None)

        product = getUtility(IProductSet).getByName('netapplet')
        importer = bugimport.BugImporter(product, 'bugs.xml', 'bug-map.pickle')
        personnode = ET.fromstring('''\
        <person xmlns="https://launchpad.net/xmlns/2006/bugs"
                name="foo" email="foo@example.com">Foo User</person>''')
        person = importer.getPerson(personnode)
        self.assertNotEqual(person, None)
        self.assertEqual(person.name, 'foo')
        self.assertEqual(person.displayname, 'Foo User')
        self.assertEqual(person.guessedemails.count(), 1)
        self.assertEqual(person.guessedemails[0].email,
                         'foo@example.com')
        self.assertEqual(person.creation_rationale,
                         PersonCreationRationale.BUGIMPORT)
        self.assertEqual(person.creation_comment,
            'when importing bugs for NetApplet')

    def test_create_person_conflicting_name(self):
        # Test that getPerson() can correctly create new users when
        # they have a short name that conflicts with an existing user
        # in the database.
        person1 = getUtility(IPersonSet).getByName('sabdfl')
        self.assertNotEqual(person1, None)

        product = getUtility(IProductSet).getByName('netapplet')
        importer = bugimport.BugImporter(product, 'bugs.xml', 'bug-map.pickle')
        personnode = ET.fromstring('''\
        <person xmlns="https://launchpad.net/xmlns/2006/bugs"
                name="sabdfl" email="foo@example.com">Foo User</person>''')
        person2 = importer.getPerson(personnode)
        self.assertNotEqual(person2, None)
        self.assertNotEqual(person1.id, person2.id)
        self.assertNotEqual(person2.name, 'sabdfl')

    def test_find_existing_person(self):
        # Test that getPerson() returns an existing person.
        person = getUtility(IPersonSet).getByEmail('foo@example.com')
        self.assertEqual(person, None)
        person, email = getUtility(IPersonSet).createPersonAndEmail(
            email='foo@example.com',
            rationale=PersonCreationRationale.OWNER_CREATED_LAUNCHPAD)
        self.assertNotEqual(person, None)

        product = getUtility(IProductSet).getByName('netapplet')
        importer = bugimport.BugImporter(product, 'bugs.xml', 'bug-map.pickle')
        personnode = ET.fromstring('''\
        <person xmlns="https://launchpad.net/xmlns/2006/bugs"
                name="sabdfl" email="foo@example.com">Foo User</person>''')
        self.assertEqual(importer.getPerson(personnode), person)

    def test_nobody_person(self):
        # Test that BugImporter.getPerson() returns None where appropriate
        product = getUtility(IProductSet).getByName('netapplet')
        importer = bugimport.BugImporter(product, 'bugs.xml', 'bug-map.pickle')
        self.assertEqual(importer.getPerson(None), None)
        personnode = ET.fromstring('''\
        <person xmlns="https://launchpad.net/xmlns/2006/bugs"
                name="nobody" />''')
        self.assertEqual(importer.getPerson(personnode), None)

    def test_verify_new_person(self):
        # Test that getPerson() creates new users with their preferred
        # email address set when verify_users=True.
        product = getUtility(IProductSet).getByName('netapplet')
        importer = bugimport.BugImporter(product, 'bugs.xml', 'bug-map.pickle',
                                         verify_users=True)
        personnode = ET.fromstring('''\
        <person xmlns="https://launchpad.net/xmlns/2006/bugs"
                name="foo" email="foo@example.com">Foo User</person>''')
        person = importer.getPerson(personnode)
        self.assertNotEqual(person, None)
        self.assertNotEqual(person.preferredemail, None)
        self.assertEqual(person.preferredemail.email,
                         'foo@example.com')
        self.assertEqual(person.creation_rationale,
                         PersonCreationRationale.BUGIMPORT)
        self.assertEqual(person.creation_comment,
            'when importing bugs for NetApplet')

    def test_verify_existing_person(self):
        # Test that getPerson() will validate the email of an existing
        # user when verify_users=True.
        person, email = getUtility(IPersonSet).createPersonAndEmail(
            'foo@example.com', PersonCreationRationale.OWNER_CREATED_LAUNCHPAD)
        self.assertEqual(person.preferredemail, None)

        product = getUtility(IProductSet).getByName('netapplet')
        importer = bugimport.BugImporter(product, 'bugs.xml', 'bug-map.pickle',
                                         verify_users=True)
        personnode = ET.fromstring('''\
        <person xmlns="https://launchpad.net/xmlns/2006/bugs"
                name="foo" email="foo@example.com">Foo User</person>''')
        person = importer.getPerson(personnode)
        self.assertNotEqual(person.preferredemail, None)
        self.assertEqual(person.preferredemail.email,
                         'foo@example.com')

    def test_verify_doesnt_clobber_preferred_email(self):
        # Test that getPerson() does not clobber an existing verified
        # email address when verify_users=True.
        person, email = getUtility(IPersonSet).createPersonAndEmail(
            'foo@example.com', PersonCreationRationale.OWNER_CREATED_LAUNCHPAD)
        email = getUtility(IEmailAddressSet).new('foo@preferred.com',
                                                 person.id)
        person.setPreferredEmail(email)
        self.assertEqual(person.preferredemail.email, 'foo@preferred.com')

        product = getUtility(IProductSet).getByName('netapplet')
        importer = bugimport.BugImporter(product, 'bugs.xml', 'bug-map.pickle',
                                         verify_users=True)
        personnode = ET.fromstring('''\
        <person xmlns="https://launchpad.net/xmlns/2006/bugs"
                name="foo" email="foo@example.com">Foo User</person>''')
        person = importer.getPerson(personnode)
        self.assertNotEqual(person.preferredemail, None)
        self.assertEqual(person.preferredemail.email, 'foo@preferred.com')


class GetMilestoneTestCase(unittest.TestCase):
    """Tests for the BugImporter.getMilestone() method."""
    layer = LaunchpadZopelessLayer

    def test_create_milestone(self):
        # Test that getMilestone() can create new milestones.
        product = getUtility(IProductSet).getByName('netapplet')
        importer = bugimport.BugImporter(product, 'bugs.xml', 'bug-map.pickle')
        milestone = importer.getMilestone('foo-bar')
        self.assertEqual(milestone.name, 'foo-bar')
        self.assertEqual(milestone.product, product)
        self.assertEqual(milestone.productseries, product.development_focus)

    def test_use_existing_milestone(self):
        # Test that existing milestones are returned by getMilestone().
        product = getUtility(IProductSet).getByName('firefox')
        one_point_zero = product.getMilestone('1.0')
        self.assertNotEqual(one_point_zero, None)
        importer = bugimport.BugImporter(product, 'bugs.xml', 'bug-map.pickle')
        milestone = importer.getMilestone('1.0')
        self.assertEqual(one_point_zero, milestone)


sample_bug = '''\
<bug xmlns="https://launchpad.net/xmlns/2006/bugs" id="42">
  <private>True</private>
  <security_related>True</security_related>
  <datecreated>2004-10-12T12:00:00Z</datecreated>
  <nickname>some-bug</nickname>
  <title>A test bug</title>
  <description>A modified bug description</description>
  <reporter name="foo" email="foo@example.com">Foo User</reporter>
  <status>CONFIRMED</status>
  <importance>HIGH</importance>
  <milestone>future</milestone>
  <assignee email="bar@example.com">Bar User</assignee>
  <cves>
    <cve>2005-2736</cve>
    <cve>2005-2737</cve>
  </cves>
  <tags>
    <tag>foo</tag>
    <tag>bar</tag>
  </tags>
  <bugwatches>
    <bugwatch href="http://bugzilla.mozilla.org/show_bug.cgi?id=42" />
    <!-- The following tracker has not been registered -->
    <bugwatch href="http://bugzilla.gnome.org/show_bug.cgi?id=43" />
  </bugwatches>
  <subscriptions>
    <subscriber email="test@canonical.com">Sample Person</subscriber>
    <subscriber name="nobody">Nobody (will not get imported)</subscriber>
  </subscriptions>
  <comment>
    <sender name="foo" email="foo@example.com">Foo User</sender>
    <date>2004-10-12T12:00:00Z</date>
    <title>A test bug</title>
    <text>Original description</text>
    <attachment>
      <type>UNSPECIFIED</type>
      <filename>hello.txt</filename>
      <title>Hello</title>
      <mimetype>text/plain</mimetype>
      <contents>SGVsbG8gd29ybGQ=</contents>
    </attachment>
  </comment>
  <comment>
    <!-- anonymous comment -->
    <sender name="nobody"/>
    <date>2005-01-01T11:00:00Z</date>
    <text>A comment from an anonymous user</text>
  </comment>
  <comment>
    <sender email="mark@hbd.com">Mark Shuttleworth</sender>
    <date>2005-01-01T13:00:00Z</date>
    <text>
A comment from mark about CVE-2005-2730

 * list item 1
 * list item 2

Another paragraph

    </text>
    <attachment>
      <mimetype>application/octet-stream;key=value</mimetype>
      <contents>PGh0bWw+</contents>
    </attachment>
    <attachment>
      <type>PATCH</type>
      <filename>foo.patch</filename>
      <mimetype>text/html</mimetype>
      <contents>QSBwYXRjaA==</contents>
    </attachment>
  </comment>
</bug>'''

duplicate_bug = '''\
<bug xmlns="https://launchpad.net/xmlns/2006/bugs" id="100">
  <duplicateof>42</duplicateof>
  <datecreated>2004-10-12T12:00:00Z</datecreated>
  <title>A duplicate bug</title>
  <description>A duplicate description</description>
  <reporter name="foo" email="foo@example.com">Foo User</reporter>
  <status>CONFIRMED</status>
  <importance>LOW</importance>
  <comment>
    <sender name="foo" email="foo@example.com">Foo User</sender>
    <date>2004-10-12T12:00:00Z</date>
    <title>A duplicate bug</title>
    <text>A duplicate description</text>
  </comment>
</bug>'''

public_security_bug = '''\
<bug xmlns="https://launchpad.net/xmlns/2006/bugs" id="101">
  <private>False</private>
  <security_related>True</security_related>
  <datecreated>2004-10-12T12:00:00Z</datecreated>
  <title>A non private security bug</title>
  <description>Description</description>
  <reporter name="foo" email="foo@example.com">Foo User</reporter>
  <status>TRIAGED</status>
  <importance>LOW</importance>
  <comment>
    <sender name="foo" email="foo@example.com">Foo User</sender>
    <date>2004-10-12T12:00:00Z</date>
    <text>Description</text>
  </comment>
</bug>'''

class ImportBugTestCase(unittest.TestCase):
    """Test importing of a bug from XML"""
    layer = LaunchpadZopelessLayer

    def setUp(self):
        login('bug-importer@launchpad.net')

    def tearDown(self):
        logout()

    def assertNoPendingNotifications(self, bug):
        notifications = BugNotification.selectBy(bug=bug, date_emailed=None)
        count = notifications.count()
        self.assertEqual(count, 0,
                         'Found %d pending notifications for bug %d'
                         % (count, bug.id))

    def test_import_bug(self):
        # Test that various features of the bug are imported from the XML.
        product = getUtility(IProductSet).getByName('netapplet')
        importer = bugimport.BugImporter(product, 'bugs.xml', 'bug-map.pickle',
                                         verify_users=True)
        bugnode = ET.fromstring(sample_bug)
        bug = importer.importBug(bugnode)

        self.assertNotEqual(bug, None)
        # check bug attributes
        self.assertEqual(bug.owner.preferredemail.email, 'foo@example.com')
        self.assertEqual(bug.datecreated.isoformat(),
                         '2004-10-12T12:00:00+00:00')
        self.assertEqual(bug.title, 'A test bug')
        self.assertEqual(bug.description, 'A modified bug description')
        self.assertEqual(bug.private, True)
        self.assertEqual(bug.security_related, True)
        self.assertEqual(bug.name, 'some-bug')
        self.assertEqual(sorted(cve.sequence for cve in bug.cves),
                         ['2005-2730', '2005-2736', '2005-2737'])
        self.assertEqual(bug.tags, ['bar', 'foo'])
        self.assertEqual(len(bug.getDirectSubscribers()), 2)
        self.assertEqual(sorted(person.preferredemail.email
                                for person in bug.getDirectSubscribers()),
                         ['foo@example.com', 'test@canonical.com'])
        # There are two bug watches
        self.assertEqual(bug.watches.count(), 2)
        self.assertEqual(sorted(watch.url for watch in bug.watches),
                         ['http://bugzilla.gnome.org/bugs/show_bug.cgi?id=43',
                          'https://bugzilla.mozilla.org/show_bug.cgi?id=42'])

        # There should only be one bug task (on netapplet):
        self.assertEqual(len(bug.bugtasks), 1)
        bugtask = bug.bugtasks[0]
        self.assertEqual(bugtask.product, product)
        self.assertEqual(bugtask.datecreated.isoformat(),
                         '2004-10-12T12:00:00+00:00')
        self.assertEqual(bugtask.importance, BugTaskImportance.HIGH)
        self.assertEqual(bugtask.status, BugTaskStatus.CONFIRMED)
        self.assertEqual(bugtask.assignee.preferredemail.email,
                         'bar@example.com')
        self.assertNotEqual(bugtask.milestone, None)
        self.assertEqual(bugtask.milestone.name, 'future')

        # there are three comments:
        self.assertEqual(bug.messages.count(), 3)
        message1 = bug.messages[0]
        message2 = bug.messages[1]
        message3 = bug.messages[2]

        # Message 1:
        self.assertEqual(message1.owner.preferredemail.email,
                         'foo@example.com')
        self.assertEqual(message1.datecreated.isoformat(),
                         '2004-10-12T12:00:00+00:00')
        self.assertEqual(message1.subject, 'A test bug')
        self.assertEqual(message1.text_contents, 'Original description')
        self.assertEqual(message1.bugattachments.count(), 1)
        attachment = message1.bugattachments[0]
        self.assertEqual(attachment.type, BugAttachmentType.UNSPECIFIED)
        self.assertEqual(attachment.title, 'Hello')
        self.assertEqual(attachment.libraryfile.filename, 'hello.txt')
        self.assertEqual(attachment.libraryfile.mimetype, 'text/plain')

        # Message 2:
        self.assertEqual(message2.owner.preferredemail.email,
                         'bug-importer@launchpad.net')
        self.assertEqual(message2.datecreated.isoformat(),
                         '2005-01-01T11:00:00+00:00')
        self.assertEqual(message2.subject, 'Re: A test bug')
        self.assertEqual(message2.text_contents,
                         'A comment from an anonymous user')

        # Message 3:
        self.assertEqual(message3.owner.preferredemail.email, 'mark@hbd.com')
        self.assertEqual(message3.datecreated.isoformat(),
                         '2005-01-01T13:00:00+00:00')
        self.assertEqual(message3.subject, 'Re: A test bug')
        self.assertEqual(message3.text_contents,
                         'A comment from mark about CVE-2005-2730\n\n'
                         ' * list item 1\n * list item 2\n\nAnother paragraph')
        self.assertEqual(message3.bugattachments.count(), 2)
        # grab the attachments in the appropriate order
        [attachment1, attachment2] = list(message3.bugattachments)
        if attachment1.type == BugAttachmentType.PATCH:
            attachment1, attachment2 = attachment2, attachment1
        self.assertEqual(attachment1.type, BugAttachmentType.UNSPECIFIED)
        # default title and filename
        self.assertEqual(attachment1.title, 'unknown')
        self.assertEqual(attachment1.libraryfile.filename, 'unknown')
        # mime type guessed from content
        self.assertEqual(attachment1.libraryfile.mimetype, 'text/html')
        self.assertEqual(attachment2.type, BugAttachmentType.PATCH)
        # title defaults to filename
        self.assertEqual(attachment2.title, 'foo.patch')
        self.assertEqual(attachment2.libraryfile.filename, 'foo.patch')
        # mime type forced to text/plain because we have a patch
        self.assertEqual(attachment2.libraryfile.mimetype, 'text/plain')

        self.assertNoPendingNotifications(bug)

    def test_duplicate_bug(self):
        # Process two bugs, the second being a duplicate of the first.
        product = getUtility(IProductSet).getByName('netapplet')
        importer = bugimport.BugImporter(product, 'bugs.xml', 'bug-map.pickle',
                                         verify_users=True)
        bugnode = ET.fromstring(sample_bug)
        bug42 = importer.importBug(bugnode)
        self.assertNotEqual(bug42, None)

        bugnode = ET.fromstring(duplicate_bug)
        bug100 = importer.importBug(bugnode)
        self.assertNotEqual(bug100, None)

        self.assertEqual(bug100.duplicateof, bug42)

        self.assertNoPendingNotifications(bug100)
        self.assertNoPendingNotifications(bug42)

    def test_pending_duplicate_bug(self):
        # Same as above, but process the pending duplicate bug first.
        product = getUtility(IProductSet).getByName('netapplet')
        importer = bugimport.BugImporter(product, 'bugs.xml', 'bug-map.pickle',
                                         verify_users=True)
        bugnode = ET.fromstring(duplicate_bug)
        bug100 = importer.importBug(bugnode)
        self.assertNotEqual(bug100, None)
        self.assertTrue(42 in importer.pending_duplicates)
        self.assertEqual(importer.pending_duplicates[42], [bug100.id])

        bugnode = ET.fromstring(sample_bug)
        bug42 = importer.importBug(bugnode)
        self.assertNotEqual(bug42, None)
        # bug 42 removed from pending duplicates
        self.assertTrue(42 not in importer.pending_duplicates)

        self.assertEqual(bug100.duplicateof, bug42)

        self.assertNoPendingNotifications(bug100)
        self.assertNoPendingNotifications(bug42)

    def test_public_security_bug(self):
        # Test that we can import a public security bug.
        # The createBug() method does not let us create such a bug
        # directly, so this checks that it works.
        product = getUtility(IProductSet).getByName('netapplet')
        importer = bugimport.BugImporter(product, 'bugs.xml', 'bug-map.pickle',
                                         verify_users=True)
        bugnode = ET.fromstring(public_security_bug)
        bug101 = importer.importBug(bugnode)
        self.assertNotEqual(bug101, None)
        self.assertEqual(bug101.private, False)
        self.assertEqual(bug101.security_related, True)


class BugImportCacheTestCase(unittest.TestCase):
    """Test of bug mapping cache load/save routines."""
    layer = LaunchpadZopelessLayer

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_load_no_cache(self):
        # Test that loadCache() when no cache file exists resets the
        # bug ID map and pending duplicates lists.
        cache_filename = os.path.join(self.tmpdir, 'bug-map.pickle')
        self.assertFalse(os.path.exists(cache_filename))
        importer = bugimport.BugImporter(None, None, cache_filename)
        importer.bug_id_map = 'bogus'
        importer.pending_duplicates = 'bogus'
        importer.loadCache()
        self.assertEqual(importer.bug_id_map, {})
        self.assertEqual(importer.pending_duplicates, {})

    def test_load_cache(self):
        # Test that loadCache() restores the state set by saveCache().
        cache_filename = os.path.join(self.tmpdir, 'bug-map.pickle')
        self.assertFalse(os.path.exists(cache_filename))
        importer = bugimport.BugImporter(None, None, cache_filename)
        importer.bug_id_map = {42: 1, 100:2}
        importer.pending_duplicates = {50: [1,2]}
        importer.saveCache()
        self.assertTrue(os.path.exists(cache_filename))
        importer.bug_id_map = 'bogus'
        importer.pending_duplicates = 'bogus'
        importer.loadCache()
        self.assertEqual(importer.bug_id_map, {42: 1, 100:2})
        self.assertEqual(importer.pending_duplicates, {50: [1,2]})

    def test_failed_import_does_not_update_cache(self):
        # Test that failed bug imports do not update the mapping cache.
        product = getUtility(IProductSet).getByName('netapplet')
        xml_file = os.path.join(self.tmpdir, 'bugs.xml')
        fp = open(xml_file, 'w')
        fp.write(
            '<launchpad-bugs xmlns="https://launchpad.net/xmlns/2006/bugs">\n')
        fp.write(sample_bug)
        fp.write('</launchpad-bugs>\n')
        fp.close()
        cache_filename = os.path.join(self.tmpdir, 'bug-map.pickle')
        class MyBugImporter(bugimport.BugImporter):
            def importBug(self, bugnode):
                raise bugnode.BugXMLSyntaxError('not imported')
        importer = MyBugImporter(product, xml_file, cache_filename)
        importer.importBugs(self.layer.txn)
        importer.loadCache()
        self.assertEqual(importer.bug_id_map, {})

    def test_repeated_import(self):
        # Test that importing a bug twice does not result in two bugs
        # being imported.
        product = getUtility(IProductSet).getByName('netapplet')
        xml_file = os.path.join(self.tmpdir, 'bugs.xml')
        fp = open(xml_file, 'w')
        fp.write(
            '<launchpad-bugs xmlns="https://launchpad.net/xmlns/2006/bugs">\n')
        fp.write(sample_bug)
        fp.write('</launchpad-bugs>\n')
        fp.close()
        cache_filename = os.path.join(self.tmpdir, 'bug-map.pickle')
        fail = self.fail
        class MyBugImporter(bugimport.BugImporter):
            def importBug(self, bugnode):
                fail('Should not have imported bug')
        importer = MyBugImporter(product, xml_file, cache_filename)
        # Mark the bug as imported
        importer.bug_id_map = {42: 1}
        importer.saveCache()
        # Import the file.  The fail() statement in importBug() shows
        # that the bug does not get reimported.
        importer.importBugs(self.layer.txn)


class BugImportScriptTestCase(unittest.TestCase):
    """Test that the driver script can be called, and does its job."""
    layer = LaunchpadZopelessLayer

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        # We ran a subprocess that may have changed the database, so
        # force the test system to treat it as dirty.
        self.layer.force_dirty_database()

    def test_bug_import_script(self):
        # Test that the bug import script can do its job
        xml_file = os.path.join(self.tmpdir, 'bugs.xml')
        fp = open(xml_file, 'w')
        fp.write(
            '<launchpad-bugs xmlns="https://launchpad.net/xmlns/2006/bugs">\n')
        fp.write(sample_bug)
        fp.write('</launchpad-bugs>\n')
        fp.close()
        cache_filename = os.path.join(self.tmpdir, 'bug-map.pickle')
        # Run the bug import script as a subprocess:
        proc = subprocess.Popen(
            [sys.executable,
             os.path.join(config.root, 'scripts', 'bug-import.py'),
             '--product', 'netapplet',
             '--cache', cache_filename,
             xml_file],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        output, error = proc.communicate()
        self.assertEqual(proc.returncode, 0)
        # Find the imported bug number:
        match = re.search(r'Creating Launchpad bug #(\d+)', error)
        self.assertNotEqual(match, None)
        bug_id = int(match.group(1))
        # Abort transaction so we can see the result:
        self.layer.txn.abort()
        bug = getUtility(IBugSet).get(bug_id)
        self.assertEqual(bug.title, 'A test bug')
        self.assertEqual(bug.bugtasks[0].product.name, 'netapplet')


class TestBugWatch:
    """A mock bug watch object for testing `ExternalBugTracker.updateWatches`.

    This bug watch is guaranteed to trigger a DB failure when `updaateStatus`
    is called if its `failing` attribute is True."""
    def __init__(self, id, bug, failing):
        """Initialize the object."""
        self.id = id
        self.remotebug = str(self.id)
        self.bug = bug
        self.failing = failing

    def updateStatus(self, new_remote_status, new_malone_status):
        """See `IBugWatch`."""
        for bugtask in self.bug.bugtasks:
            if bugtask.conjoined_master is not None:
                continue
            bugtask = removeSecurityProxy(bugtask)
            bugtask.status = new_malone_status
        if self.failing:
            cur = cursor()
            cur.execute("""
            UPDATE BugTask
            SET assignee = -1
            WHERE id = %s
            """ % self.bug.bugtasks[0].id)
            cur.close()

    def updateImportance(self,
                         new_remote_importance,
                         new_malone_importance):
        """Do nothing, just to provide the interface."""
        pass


class TestResultSequence(list):
    """A mock `SelectResults` object.

    Returns a list with a `count` method.
    """

    def count(self):
        """See `SelectResults`."""
        return len(self)


class TestBugTracker:
    """A mock `BugTracker` object.

    This bug tracker is used for testing `ExternalBugTracker.updateWatches`.
    It exposes two bug watches, one of them is guaranteed to trigger an error.
    """
    baseurl = 'http://example.com/'

    def __init__(self, test_bug_one, test_bug_two):
        self.test_bug_one = test_bug_one
        self.test_bug_two = test_bug_two
    
    def getBugWatchesNeedingUpdate(self, hours):
        """Returns a sequence of teo bug watches for testing."""
        return TestResultSequence([
            TestBugWatch(1, self.test_bug_one, failing=True),
            TestBugWatch(2, self.test_bug_two, failing=False)])


class TestExternalBugTracker(ExternalBugTracker):
    """A mock `ExternalBugTracker` object.

    This external bug tracker is used for testing
    `ExternalBugTracker.updateWatches`. It overrides several methods
    in order to simulate the syncing of two bug watches, one of which
    is guaranteed to trigger a database error.
    """
    def getRemoteBug(self, bug_id):
        """Return the bug_id and an empty dictionary for data.

        The result will be ignored, since we force a specific status
        in `getRemoteStatus` and `convertRemoteStatus`.
        """
        return bug_id, {}
    
    def getRemoteStatus(self, bug_id):
        """Returns a remote status as a string.

        The result will be ignored, since we force a specific malone
        status in `convertRemoteStatus`.
        """
        return 'TEST_STATUS'

    def convertRemoteStatus(self, remote_status):
        """Returns a hard-coded malone status - `FIXRELEASED`.

        We rely on the result for comparison in
        `test_checkbugwatches_error_recovery`.
        """
        return BugTaskStatus.FIXRELEASED

    def _getBugWatch(self, bug_watch_id):
        """Returns a mock bug watch object.

        We override this method to force one of our two bug watches
        to be returned. The first is guaranteed to trigger a db error,
        the second should update successfuly.
        """
        return self.bugtracker.getBugWatchesNeedingUpdate(0)[bug_watch_id - 1]

    def getRemoteImportance(self, bug_id):
        """See `ExternalBugTracker`.

        This method is implemented here as a stub to ensure that
        existing functionality is preserved. As a result,
        UNKNOWN_REMOTE_IMPORTANCE will always be returned.
        """
        return UNKNOWN_REMOTE_IMPORTANCE

    def convertRemoteImportance(self, remote_importance):
        """See `ExternalBugTracker`.

        This method is implemented here as a stub to ensure that
        existing functionality is preserved. As a result,
        BugTaskImportance.UNKNOWN will always be returned.
        """
        return BugTaskImportance.UNKNOWN



class TestBugWatchUpdater(BugWatchUpdater):
    """A mock `BugWatchUpdater` object."""
    
    def _getExternalBugTracker(self, bug_tracker):
        """See `BugWatchUpdater`."""
        return TestExternalBugTracker(self.txn, bug_tracker)


class CheckBugWatchesErrorRecoveryTestCase(unittest.TestCase):
    """Test that errors in the bugwatch import process don't
    invalidate the entire run.
    """
    layer = LaunchpadZopelessLayer

    def test_checkbugwatches_error_recovery(self):

        firefox = getUtility(IProductSet).get(4)
        foobar = getUtility(IPersonSet).get(16)
        params = CreateBugParams(
            title="test bug one", comment="test bug one", owner=foobar)
        params.setBugTarget(product=firefox)
        test_bug_one = getUtility(IBugSet).createBug(params)
        params = CreateBugParams(
            title="test bug two", comment="test bug two", owner=foobar)
        params.setBugTarget(product=firefox)
        test_bug_two = getUtility(IBugSet).createBug(params)
        self.layer.txn.commit()

        # We use a test bug tracker, which is guaranteed to
        # try and update two bug watches - the first will
        # trigger a DB error, the second updates successfully.
        bug_tracker = TestBugTracker(test_bug_one, test_bug_two)
        bug_watch_updater = TestBugWatchUpdater(self.layer.txn)
        bug_watch_updater.updateBugTracker(bug_tracker)
        # We verify that the first bug watch didn't update the status,
        # and the second did.
        for bugtask in test_bug_one.bugtasks:
            self.assertNotEqual(bugtask.status, BugTaskStatus.FIXRELEASED)
        for bugtask in test_bug_two.bugtasks:
            self.assertEqual(bugtask.status, BugTaskStatus.FIXRELEASED)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
