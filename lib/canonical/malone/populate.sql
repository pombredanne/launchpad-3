-- Usage: psql -f populate.sql -d launchpad

-- Mark Shuttleworth
INSERT INTO Person (presentationname, givenname, familyname)
VALUES ('Mark Shuttleworth', 'Mark', 'Shuttleworth' );

INSERT INTO EmailAddress (email, person, status)
VALUES ('mark@hbd.com', currval('Person_id_seq'), 2);

INSERT INTO EmailAddress (email, person, status)
VALUES ('marks@thawte.com', currval('Person_id_seq'), 3);

INSERT INTO EmailAddress (email, person, status)
VALUES ('markshuttle@yahoo.co.uk', currval('Person_id_seq'), 1);

INSERT INTO Project (owner, name, title, description, homepageurl)
VALUES (currval('Person_id_seq'), 'ubuntu', 'The Ubuntu Project',
        'The Ubuntu Project aims to create a freely redistributable OS that is easy to customize and derive from. Ubuntu is released every six months with contributions from a large community. Ubuntu also includes work to unify the translation of common opens source desktop applications and the tracking of bugs across multiple distributions.',
        'http://www.no-name-yet.com/');

-- Dave Miller
INSERT INTO Person (presentationname, givenname, familyname)
VALUES ('Dave Miller', 'David', 'Miller');

INSERT INTO EmailAddress (email, person, status)
VALUES ('justdave@bugzilla.org', currval('Person_id_seq'), 2);

INSERT INTO BugSystemType (name, title, description, homepage, owner)
VALUES ('bugzilla', 'BugZilla',
        'Dave Miller\'s Labour of Love, the Godfather of Open Source project issue tracking.',
        'http://www.bugzilla.org/', currval('Person_id_seq'));

INSERT INTO Project (owner, name, title, description, homepageurl) 
VALUES (currval('Person_id_seq'), 'mozilla', 'The Mozilla Project',
        'The Mozilla Project is the largest open source web browser collaborative project. The Mozilla Project produces several internet applications that are very widely used, and is also a center for collaboration on internet standards work by open source groups.', 
        'http://www.mozilla.org/');

INSERT INTO Product (project, owner, name, title, description)
VALUES (currval('Person_id_seq'), currval('Project_id_seq'), 'firefox',
        'Mozilla Firefox', 'The Mozilla Firefox web browser');

INSERT INTO ProductRelease (product, datereleased, version, owner)
VALUES (currval('Product_id_seq'), timestamp '2004-06-28 00:00',
        'mozilla-firefox-0.9.1', currval('Person_id_seq'));

INSERT INTO Sourcepackage (maintainer, name, title, description)
VALUES (currval('Person_id_seq'), 'mozilla-firefox',
        'Ubuntu Mozilla Firefox Source Package', 'text');

INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES (currval('Sourcepackage_id_seq'), 1, currval('Person_id_seq'), '0.9.1-1',
        timestamp '2004-06-29 00:00', 1);

INSERT INTO Manifest (datecreated, owner)
VALUES (timestamp '2004-06-29 00:00', currval('Person_id_seq'));

INSERT INTO CodeRelease (sourcepackagerelease, manifest)
VALUES (currval('Sourcepackage_id_seq'), currval('Manifest_id_seq'));

INSERT INTO Bug (nickname, title, description, owner, communityscore,
                 communitytimestamp, activityscore, activitytimestamp, hits,
                 hitstimestamp)
VALUES ('bob', 'An odd problem', 'Something strange is wrong somewhere',
        currval('Person_id_seq'), 0, CURRENT_DATE, 0, CURRENT_DATE, 0,
        CURRENT_DATE);

INSERT INTO BugActivity (bug, datechanged, person, whatchanged, oldvalue,
                         newvalue, message)
VALUES (currval('Bug_id_seq'), CURRENT_DATE, 1, 'title', 'A silly problem',
        'An odd problem', 'Decided problem wasn\'t silly after all');

INSERT INTO BugAttachment (bug, title, description)
VALUES (currval('Bug_id_seq'), 'A screenshot', 'A screenshot of the traceback');

INSERT INTO BugattachmentContent (bugattachment, daterevised, changecomment,
                                  content, filename, mimetype, owner)
VALUES (currval('BugAttachment_id_seq'), CURRENT_DATE, 'Initial version',
        'Test attachment', 'text.txt', 'text/plain', currval('Person_id_seq'));
INSERT INTO BugExternalref (bug, bugreftype, data, description, owner)
VALUES (currval('Bug_id_seq'), 1, '12345', 'Some description here',
        currval('Person_id_seq'));

INSERT INTO BugMessage (bug, title, contents)
VALUES (currval('Bug_id_seq'), 'A brief comment',
        'My thoughts on the bug are quite profound.');

INSERT INTO BugSubscription (person, bug, subscription)
VALUES (currval('Person_id_seq'), currval('Bug_id_seq'), 1);

INSERT INTO ProductBugAssignment (bug, product, bugstatus, priority, severity)
VALUES (currval('Bug_id_seq'), currval('Product_id_seq'), 1, 1, 1);

-- Colin Watson
INSERT INTO Person (presentationname, givenname, familyname)
VALUES ('Colin Watson', 'Colin', 'Watson');

INSERT INTO EmailAddress (email, person, status)
VALUES ('colin.watson@canonical.com', currval('Person_id_seq'), 2);

INSERT INTO BugSystemType (name, title, description, homepage, owner)
VALUES ('debbugs', 'DebBugs',
        'The Debian bug tracking system, ugly as sin but fast and productive as a rabbit in high heels.',
        'http://bugs.debian.org/', currval('Person_id_seq'));

INSERT INTO Project (owner, name, title, description, homepageurl)
VALUES(currval('Person_id_seq'), 'apache', 'The Apache Project',
       'The Apache Project produces some of the worlds most widely used web and internet server software.',
       'http://www.apache.org/');

-- Steve Alexander
INSERT INTO Person (presentationname, givenname, familyname)
VALUES ('Steve Alexander', 'Steve', 'Alexander' );

INSERT INTO EmailAddress (email, person, status)
VALUES ('steve.alexander@canonical.com', currval('Person_id_seq'), 2 );

INSERT INTO BugSystemType (name, title, description, homepage, owner)
VALUES ('roundup', 'Round-Up',
        'Python-based open source bug tracking system with an elegant design and reputation for cleanliness and usability.',
        'http://www.roundup.org/', currval('Person_id_seq'));

-- Scott James Remnant
INSERT INTO Person (presentationname, givenname, familyname)
VALUES ('Scott James Remnant', 'Scott James', 'Remnant');

INSERT INTO EmailAddress (email, person, status)
VALUES ('scott@netsplit.com', currval('Person_id_seq'), 2 );

-- Robert Collines
INSERT INTO Person (presentationname, givenname, familyname)
VALUES ('Robert Collins', 'Robert', 'Collins');

INSERT INTO EmailAddress (email, person, status)
VALUES ('robertc@cygwin.com', currval('Person_id_seq'), 2);

INSERT INTO EmailAddress (email, person, status)
VALUES ('robert.collins@canonical.com', currval('Person_id_seq'), 2);

-- Jeff Waugh
INSERT INTO Person (presentationname, givenname, familyname)
VALUES ('Jeff Waugh', 'Jeff', 'Waugh');

INSERT INTO Project (owner, name, title, description, homepageurl) 
VALUES (currval('Person_id_seq'), 'gnome', 'The Gnome Project',
        'The Gnome project aims to create a desktop environment and core desktop applications that bring simplicity and ease of use to the open source desktop.',
        'http://www.gnome.org/');

-- Second bug

INSERT INTO Bug (nickname, title, description, owner, communityscore,
                 communitytimestamp, activityscore, activitytimestamp, hits,
                 hitstimestamp)
VALUES ('The Blackhole', 'The Missing Data Bug',
        'Data just vanishes in an odd and unexplained way.',
        currval('Person_id_seq'), 0, CURRENT_TIMESTAMP, 0, CURRENT_TIMESTAMP, 0,
        CURRENT_TIMESTAMP);

INSERT INTO BugActivity (bug, datechanged, person, whatchanged, oldvalue,
                         newvalue, message)
VALUES (currval('Bug_id_seq'), CURRENT_DATE, 1, 'nickname', 'xxx',
        'The Blackhole', 'Finally thought of a nickname.');

INSERT INTO BugAttachment (bug, title, description)
VALUES (currval('Bug_id_seq'), 'CSV that fails',
        'This CSV file breaks the import.');

INSERT INTO BugattachmentContent (bugattachment, daterevised, changecomment,
                                  content, filename, mimetype, owner)
VALUES (currval('BugAttachment_id_seq'), CURRENT_TIMESTAMP, 'Initial version',
        '2nd Test attachment', 'test.txt', 'text/plain',
         currval('Person_id_seq'));
