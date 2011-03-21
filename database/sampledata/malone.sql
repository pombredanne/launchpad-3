/*
   MALONE SAMPLE DATA

   Copyright 2009 Canonical Ltd.  This software is licensed under the
   GNU Affero General Public License version 3 (see the file LICENSE).

   This is some sample data for Malone.  This requires the default
   data to be inserted first.
*/

INSERT INTO BugSystemType (name, title, description, homepage, owner)
VALUES ('bugzilla', 'BugZilla', 'Dave Miller\'s Labour of Love, '
|| 'the Godfather of Open Source project issue tracking.',
'http://www.bugzilla.org/',
(SELECT id FROM Person WHERE displayname='Sample Person')
);

INSERT INTO Manifest (datecreated, owner)
VALUES (
timestamp '2004-06-29 00:00',
(SELECT id FROM Person WHERE displayname='Sample Person')
);

INSERT INTO CodeRelease (sourcepackagerelease, manifest)
VALUES (
(SELECT id FROM SourcePackage WHERE sourcepackagename =
	(SELECT id FROM SourcePackagename WHERE name = 'mozilla-firefox')),
(SELECT max(id) FROM Manifest)
);

-- Mozilla Thunderbird
INSERT INTO Product (project, owner, name, displayname,  title, shortdesc,
description)
VALUES (
(SELECT id FROM Project WHERE name='mozilla'),
(SELECT id FROM Person WHERE displayname='Sample Person'),
'thunderbird', 'Mozilla Thunderbird', 'Mozilla Thunderbird',
'The Mozilla Thunderbird email client',
'The Mozilla Thunderbird email client'
);
INSERT INTO ProductRelease (product, datereleased, version, owner)
VALUES (
(SELECT id FROM Product WHERE name='thunderbird'),
timestamp '2004-06-28 00:00', 'mozilla-thunderbird-0.8.0',
(SELECT id FROM Person WHERE displayname='Sample Person')
);

/*
INSERT INTO SourcePackageRelease (sourcepackage, srcpackageformat, creator,
version, dateuploaded, urgency)
VALUES (
(SELECT id FROM SourcePackage WHERE sourcepackagename =
	(SELECT id FROM SourcePackagename WHERE name = 'mozilla-thunderbird')),
1, (SELECT id FROM Person WHERE displayname='Sample Person'),
'0.8.0-1', timestamp '2004-06-29 00:00', 1
);
*/

INSERT INTO Manifest (datecreated, owner)
VALUES (
timestamp '2004-06-29 00:00',
(SELECT id FROM Person WHERE displayname='Sample Person')
);

INSERT INTO CodeRelease (sourcepackagerelease, manifest)
VALUES (
(SELECT id FROM SourcePackage WHERE sourcepackagename =
	(SELECT id FROM SourcePackagename WHERE name = 'mozilla-thunderbird')),
(SELECT max(id) FROM Manifest)
);


INSERT INTO Bug (name, title, shortdesc, description, owner, communityscore,
communitytimestamp, activityscore, activitytimestamp, hits,
hitstimestamp)
VALUES ('bob', 'Firefox does not support SVG', 'Firefox needs to support embedded SVG images, now that the standard has been finalised.',
'The SVG standard 1.0 is complete, and draft implementations for Firefox exist. One of these implementations needs to be integrated with the base install of Firefox. Ideally, the implementation needs to include support for the manipulation of SVG objects from JavaScript to enable interactive and dynamic SVG drawings.',
(SELECT id FROM Person WHERE displayname='Sample Person'),
0, CURRENT_DATE, 0, CURRENT_DATE, 0, CURRENT_DATE
);

INSERT INTO Bug (name, title, shortdesc, description, owner, communityscore,
communitytimestamp, activityscore, activitytimestamp, hits, hitstimestamp)
VALUES ('blackhole', 'Blackhole Trash folder',
'Everything put into the folder "Trash" disappears!', 'The Trash folder seems to have significant problems! At the moment, dragging an item to the trash results in immediate deletion. The item does not appear in the Trash, it is just deleted from my hard disk. There is no undo or ability to recover the deleted file. Help!',
(SELECT id FROM Person WHERE displayname='Sample Person'),
0, CURRENT_DATE, 0, CURRENT_DATE, 0, CURRENT_DATE
);

INSERT INTO BugActivity (bug, datechanged, person, whatchanged, oldvalue,
newvalue, message)
VALUES (
(SELECT id FROM Bug WHERE name='bob'),
CURRENT_DATE, 1, 'title', 'A silly problem',
'An odd problem', 'Decided problem wasn\'t silly after all'
);

-- Assign bug 'bob' to the firefox product (NEW, HIGH, MAJOR)
INSERT INTO ProductBugAssignment (
    bug, product, bugstatus, priority, severity, assignee
    )
VALUES (
    (SELECT id FROM Bug WHERE name='bob'),
    (SELECT id FROM Product WHERE name='firefox'),
    1, 2, 2,
    (SELECT id FROM Person WHERE displayname='Sample Person')
);

-- Assign bug 'bob' to the mozilla-firefox sourcepackage and firefox-0.81
-- binary package (OPEN, WONTFIX, 2)
INSERT INTO SourcePackageBugAssignment (
    bug, sourcepackage, bugstatus, priority, severity, binarypackage, assignee
    )
VALUES (
    (SELECT id FROM Bug WHERE name='bob'),
    (SELECT id FROM SourcePackage WHERE sourcepackagename =
	(SELECT id FROM SourcePackagename WHERE name = 'mozilla-firefox')),
    20, 4, 2,
    (SELECT id FROM BinaryPackage WHERE version='0.8' AND binarypackagename = (
        SELECT id FROM BinaryPackageName WHERE name='mozilla-firefox'
        )),
    (SELECT id FROM Person WHERE displayname='Sample Person')
);

-- Remove the nickname 'bob', so we have an unnamed bug
UPDATE Bug SET name=NULL WHERE name='bob';

/*
INSERT INTO SourcePackageBugAssignment
    (bug, sourcepackage, bugstatus, priority, severity, binarypackage)
VALUES (
    (SELECT id FROM Bug WHERE name='blackhole'),
    (SELECT id FROM SourcePackage WHERE name='mozilla-thunderbird'),
    2, 4, 2, NULL
    );
*/
INSERT INTO ProductBugAssignment (
    bug, product, bugstatus, priority, severity, assignee
    )
VALUES (
    (SELECT id FROM Bug WHERE name='blackhole'),
    (SELECT id FROM Product WHERE name='thunderbird'),
    10, 2, 2,
    (SELECT id FROM Person WHERE displayname='Sample Person')
);

INSERT INTO SourcePackageRelease (
    sourcepackage, srcpackageformat, creator, version, urgency, "section")
VALUES (
    (SELECT id FROM SourcePackage WHERE shortdesc = 'Mozilla Firefox Web Browser'),
    1,
    1,
    'mozilla-firefox-0.9.1',
    1,
    (SELECT id FROM "section" WHERE name = 'default_section'));

INSERT INTO SourcePackageRelease (
    sourcepackage, srcpackageformat, creator, version, urgency, "section")
VALUES (
    (SELECT id FROM SourcePackage WHERE shortdesc = 'Mozilla Firefox Web Browser'),
    1,
    1,
    'mozilla-thunderbird-0.9.0',
    1,
    (SELECT id FROM "section" WHERE name = 'default_section'));

INSERT INTO BugMessage (bug, title, contents, rfc822msgid) VALUES (
    (SELECT id FROM Bug WHERE name='blackhole'),
    'PEBCAK',
    'Problem exists between chair and keyboard',
    'foo@example.com-332342--1231'
    );

INSERT INTO BugExternalRef (bug, bugreftype, data, description, owner) VALUES (
    (SELECT id FROM Bug WHERE name='blackhole'),
    1,
    45,
    'Some junk has to go here because the field is NOT NULL',
    (SELECT id FROM Person WHERE displayname='Sample Person')
    );
INSERT INTO BugExternalRef (bug, bugreftype, data, description, owner) VALUES (
    (SELECT id FROM Bug WHERE name='blackhole'),
    2,
    'http://www.mozilla.org',
    'The homepage of the project this bug is on, for no particular reason',
    (SELECT id FROM Person WHERE displayname='Sample Person')
    );

INSERT INTO BugSystem (bugsystemtype, name, title, shortdesc, baseurl, owner,
    contactdetails) VALUES (
    (SELECT id FROM BugSystemType WHERE name='bugzilla'),
    'mozilla.org',
    'The Mozilla.org Bug Tracker',
    'The Mozilla.org bug tracker',
    'http://www.example.com/bugtracker',
    (SELECT id FROM Person WHERE displayname='Sample Person'),
    'Carrier pidgeon only'
    );
INSERT INTO BugWatch (bug, bugsystem, remotebug, remotestatus, remote_importance, owner) VALUES (
    (SELECT id FROM Bug WHERE name='blackhole'),
    (SELECT id FROM BugSystem WHERE name='mozilla.org'),
    '42',
    'FUBAR',
    'BAZBAZ',
    (SELECT id FROM Person WHERE displayname='Sample Person')
    );
