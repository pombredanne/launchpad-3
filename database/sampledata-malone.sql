/*
   MALONE SAMPLE DATA
   
   This is some sample data for Malone.  This requires the default
   data to be inserted first.
*/

/* 
INSERT INTO Person (displayname, givenname, familyname)
VALUES  ('Dave Miller', 'David', 'Miller');
*/

INSERT INTO Person (displayname) VALUES ('Sample Person');

INSERT INTO EmailAddress (email, person, status) VALUES (
'justdave@bugzilla.org',
(SELECT id FROM Person WHERE displayname='Dave Miller'),
2
);
INSERT INTO BugSystemType (name, title, description, homepage, owner)
VALUES ('bugzilla', 'BugZilla', 'Dave Miller\'s Labour of Love, '
|| 'the Godfather of Open Source project issue tracking.',
'http://www.bugzilla.org/', 
(SELECT id FROM Person WHERE displayname='Dave Miller')
);
INSERT INTO Project (owner, name, displayname, title, shortdesc, 
description, homepageurl)
VALUES (
(SELECT id FROM Person WHERE displayname='Sample Person'),
'mozilla', 'The Mozilla Project', 'The Mozilla Project',
'The Mozilla Project is the largest open source web browser collaborative project.',
'The Mozilla Project is the largest open source web browser '
|| 'collaborative project. The Mozilla Project produces several internet '
|| 'applications that are very widely used, and is also a center for '
|| 'collaboration on internet standards work by open source groups.',
'http://www.mozilla.org/'
);

-- Mozilla Firefox
INSERT INTO Product (project, owner, name, displayname,  title, shortdesc,
description)
VALUES (
(SELECT id FROM Project WHERE name='mozilla'),
(SELECT id FROM Person WHERE displayname='Sample Person'),
'firefox', 'Mozilla Firefox', 'Mozilla Firefox',
'The Mozilla Firefox web browser',
'The Mozilla Firefox web browser'
);
INSERT INTO ProductRelease (product, datereleased, version, owner)
VALUES (
(SELECT id FROM Product WHERE name='firefox'),
timestamp '2004-06-28 00:00', 'mozilla-firefox-0.9.1',
(SELECT id FROM Person WHERE displayname='Sample Person')
);

INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
version, dateuploaded, urgency)
VALUES (
(SELECT id FROM Sourcepackage WHERE sourcepackagename=
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-firefox')),
1, (SELECT id FROM Person WHERE displayname='Sample Person'),
'0.9.1-1', timestamp '2004-06-29 00:00', 1
);

INSERT INTO Manifest (datecreated, owner)
VALUES (
timestamp '2004-06-29 00:00', 
(SELECT id FROM Person WHERE displayname='Sample Person')
);

INSERT INTO CodeRelease (sourcepackagerelease, manifest)
VALUES (
(SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-firefox')),
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

INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
version, dateuploaded, urgency)
VALUES (
(SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-thunderbird')),
1, (SELECT id FROM Person WHERE displayname='Sample Person'),
'0.8.0-1', timestamp '2004-06-29 00:00', 1
);

INSERT INTO Manifest (datecreated, owner)
VALUES (
timestamp '2004-06-29 00:00', 
(SELECT id FROM Person WHERE displayname='Sample Person')
);

INSERT INTO CodeRelease (sourcepackagerelease, manifest)
VALUES (
(SELECT id FROM Sourcepackage WHERE sourcepackagename =
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-thunderbird')),
(SELECT max(id) FROM Manifest)
);


INSERT INTO Bug (name, title, shortdesc, description, owner, communityscore,
communitytimestamp, activityscore, activitytimestamp, hits,
hitstimestamp)
VALUES ('bob', 'An odd problem', 'Something strange is wrong somewhere',
'Something strange is wrong somewhere',
(SELECT id FROM Person WHERE displayname='Sample Person'),
0, CURRENT_DATE, 0, CURRENT_DATE, 0, CURRENT_DATE
);

INSERT INTO Bug (name, title, shortdesc, description, owner, communityscore,
communitytimestamp, activityscore, activitytimestamp, hits, hitstimestamp)
VALUES ('blackhole', 'Blackhole folder', 
'Everything put into the folder "Trash" disappears!', 'Where is my email!',
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
INSERT INTO ProductBugAssignment (bug, product, bugstatus, priority, severity)
VALUES (
    (SELECT id FROM Bug WHERE name='bob'),
    (SELECT id FROM Product WHERE name='firefox'),
    1, 2, 2
);

-- Assign bug 'bob' to the mozilla-firefox sourcepackage and firefox-0.81
-- binary package (OPEN, WONTFIX, 2)
INSERT INTO SourcepackageBugAssignment 
    (bug, sourcepackage, bugstatus, priority, severity, binarypackage)
VALUES (
    (SELECT id FROM Bug WHERE name='bob'),
    (SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-firefox')),
    2, 4, 2,
    (SELECT id FROM BinaryPackage WHERE version='0.8' 
        AND binarypackagename = (
            SELECT id FROM BinarypackageName WHERE name='mozilla-firefox'
            )
    )
);

-- Remove the nickname 'bob', so we have an unnamed bug
UPDATE Bug SET name=NULL WHERE name='bob';

/*
INSERT INTO SourcepackageBugAssignment
    (bug, sourcepackage, bugstatus, priority, severity, binarypackage)
VALUES (
    (SELECT id FROM Bug WHERE name='blackhole'),
    (SELECT id FROM Sourcepackage WHERE name='mozilla-thunderbird'),
    2, 4, 2, NULL
    );
*/
INSERT INTO ProductBugAssignment (bug, product, bugstatus, priority, severity)
VALUES (
    (SELECT id FROM Bug WHERE name='blackhole'),
    (SELECT id FROM Product WHERE name='thunderbird'),
    1, 2, 2
);


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
INSERT INTO BugWatch (bug, bugsystem, remotebug, remotestatus, owner) VALUES (
    (SELECT id FROM Bug WHERE name='blackhole'),
    (SELECT id FROM BugSystem WHERE name='mozilla.org'),
    '42',
    'FUBAR',
    (SELECT id FROM Person WHERE displayname='Sample Person')
    );
