/*
   LAUNCHPAD SAMPLE DATA
   
   This is some sample data for the launchpad system.
*/


-- Person
INSERT INTO Person ( presentationname, givenname, familyname ) VALUES ( 'Mark Shuttleworth', 'Mark', 'Shuttleworth' );     -- 1
INSERT INTO Person ( presentationname, givenname, familyname ) VALUES ( 'Dave Miller', 'David', 'Miller' );                -- 2
INSERT INTO Person ( presentationname, givenname, familyname ) VALUES ( 'Colin Watson', 'Colin', 'Watson' );               -- 3
INSERT INTO Person ( presentationname, givenname, familyname ) VALUES ( 'Steve Alexander', 'Steve', 'Alexander' );         -- 4
INSERT INTO Person ( presentationname, givenname, familyname ) VALUES ( 'Scott James Remnant', 'Scott James', 'Remnant' ); -- 5
INSERT INTO Person ( presentationname, givenname, familyname ) VALUES ( 'Robert Collins', 'Robert', 'Collins' );           -- 6
INSERT INTO Person ( presentationname, givenname, familyname ) VALUES ( 'Jeff Waugh', 'Jeff', 'Waugh' );                   -- 7


-- EmailAddress
INSERT INTO EmailAddress ( email, person, status ) VALUES ( 'mark@hbd.com', 1, 2 );
INSERT INTO EmailAddress ( email, person, status ) VALUES ( 'marks@thawte.com', 1, 3 );
INSERT INTO EmailAddress ( email, person, status ) VALUES ( 'markshuttle@yahoo.co.uk', 1, 1 );
INSERT INTO EmailAddress ( email, person, status ) VALUES ( 'justdave@bugzilla.org', 2, 2 );
INSERT INTO EmailAddress ( email, person, status ) VALUES ( 'colin.watson@canonical.com', 3, 2 );
INSERT INTO EmailAddress ( email, person, status ) VALUES ( 'steve.alexander@canonical.com', 4, 2 );
INSERT INTO EmailAddress ( email, person, status ) VALUES ( 'scott@netsplit.com', 5, 2 );
INSERT INTO EmailAddress ( email, person, status ) VALUES ( 'robertc@cygwin.com', 6, 2 );
INSERT INTO EmailAddress ( email, person, status ) VALUES ( 'robert.collins@canonical.com', 6, 2 );


-- BugSystemType
INSERT INTO BugSystemType VALUES ( 1, 'bugzilla', 'BugZilla', 'Dave Miller\'s Labour of Love, the Godfather of Open Source project issue tracking.', 'http://www.bugzilla.org/', 2 );
INSERT INTO BugSystemType VALUES ( 2, 'debbugs', 'DebBugs', 'The Debian bug tracking system, ugly as sin but fast and productive as a rabbit in high heels.', 'http://bugs.debian.org/', 3 );
INSERT INTO BugSystemType VALUES ( 3, 'roundup', 'Round-Up', 'Python-based open source bug tracking system with an elegant design and reputation for cleanliness and usability.', 'http://www.roundup.org/', 4 );



-- Project
INSERT INTO Project ( owner, name, title, description, homepageurl ) VALUES ( 1, 'ubuntu', 'The Ubuntu Project', 'The Ubuntu Project aims to create a freely redistributable OS that is easy to customize and derive from. Ubuntu is released every six months with contributions from a large community. Ubuntu also includes work to unify the translation of common opens source desktop applications and the tracking of bugs across multiple distributions.', 'http://www.no-name-yet.com/' ); -- 1
INSERT INTO Project ( owner, name, title, description, homepageurl ) VALUES ( 2, 'mozilla', 'The Mozilla Project', 'The Mozilla Project is the largest open source web browser collaborative project. The Mozilla Project produces several internet applications that are very widely used, and is also a center for collaboration on internet standards work by open source groups.', 'http://www.mozilla.org/' ); -- 2
INSERT INTO Project ( owner, name, title, description, homepageurl ) VALUES ( 7, 'gnome', 'The Gnome Project', 'The Gnome project aims to create a desktop environment and core desktop applications that bring simplicity and ease of use to the open source desktop.', 'http://www.gnome.org/' ); -- 3
INSERT INTO Project ( owner, name, title, description, homepageurl ) VALUES ( 3, 'apache', 'The Apache Project', 'The Apache Project produces some of the worlds most widely used web and internet server software.', 'http://www.apache.org/' ); -- 4



-- Product
INSERT INTO Product ( project, owner, name, title, description, homepageurl ) VALUES ( 1, 1, 'ubuntu', 'Ubuntu', 'A desktop Linux that you can give your girlfriend to install. Works out of the box with recent Gnome desktop applications configured to make you productive immediately. Ubuntu is updated every six months, comes with security updates for peace of mind, and is avaialble everywhere absolutely free of charge.', 'http://www.ubuntu.com/' );
INSERT INTO Product ( project, owner, name, title, description, homepageurl ) VALUES ( 3, 7, 'gdm', 'Gnome Display Manager', 'The Gnome Display Manager is a login manager for the Gnome Desktop Environment. It allows for configurable login screens with face browsers and system actions such as shutdown and restart.', 'http://gdm.gnome.org' );
INSERT INTO Product ( project, owner, name, title, description, homepageurl ) VALUES ( 3, 7, 'glib', 'Glib', 'Glib is one of the core Gnome libraries, used by most Gnome applications.', 'http://www.gnome.org/' );
INSERT INTO Product ( project, owner, name, title, description, homepageurl ) VALUES ( 3, 7, 'gtk+', 'Gnome Toolkit GTK+', 'The GTK+ libaries are the foundation of Gnome application look and feel. They allow for strongly themed applications, hundreds of themes are available.', 'http://www.gnome.org/' );
INSERT INTO Product ( project, owner, name, title, description, homepageurl ) VALUES ( 3, 7, 'themes', 'Gnome Themes', 'This package of standard themes is usually available on any Gnome installation.', 'http://themes.gnome.org/' );
INSERT INTO Product ( project, owner, name, title, description, homepageurl ) VALUES ( 2, 2, 'app-suite', 'Mozilla App Suite', 'The Mozilla application suite is the modern-day descendent of the Netscape browser that launched a thousand dot-com ships. The browser code was open sourced and is now driven by The Mozilla Foundation. The Mozilla App Suite includes a mail reader, web browser, news reader, web page editor and an addressbook.', 'http:///www.mozilla.org/' );
INSERT INTO Product ( project, owner, name, title, description, homepageurl ) VALUES ( 2, 2, 'firefox', 'Mozilla Firefox', 'Firefox is a web browser derived from the Mozilla App Suite. It is designed to be smaller and faster than app-suite since it includes just the web browser, but it comes with the same world-beating standards support and speed.', 'http://www.mozilla.org/' );
INSERT INTO Product ( project, owner, name, title, description, homepageurl ) VALUES ( 2, 2, 'thunderbird', 'Mozilla Thunderbird', 'Thunderbird is email software derived from Mozilla App Suite in the same way that Firefox is. Thunderbird supports excellent spam filtering and has hundreds of extensions for such things as encryption, mouse gestures and offline work.', 'http://www.mozilla.org/' );
INSERT INTO Product ( project, owner, name, title, description, homepageurl ) VALUES ( 2, 2, 'bugzilla', 'Bugzilla', 'Bugzilla is the big daddy of all open source bug tracking systems and is still used at several large open source projects. It\'s better known for scale than beauty.', 'http://www.bugzilla.org/' );
INSERT INTO Product ( project, owner, name, title, description, homepageurl ) VALUES ( 4, 3, 'apache', 'The Apache Web Server', 'The worlds most popular web server. Used on more than half of the worlds web servers, and most of the servers that carry heavy traffic, Apache is the undisputed champion of the web server business.', 'http://httpd.apache.org/' );
INSERT INTO Product ( project, owner, name, title, description, homepageurl ) VALUES ( 4, 3, 'tomcat', 'Tomcat Java Application Server', 'Tomcat description goes here. A good description has at least a full paragraph of text, explaining what\'s unique about that product, why and when you would use it.', 'http://tomcat.apache.org/' );
INSERT INTO Product ( project, owner, name, title, description, homepageurl ) VALUES ( 4, 3, 'spamassassin', 'Spamassassin Spam Filter Daemon', 'Spamassassin description goes here. A good description has at least a full paragraph of text, explaining what\'s unique about that product, why and when you would use it.', 'http://spamassassin.apache.org/' );
INSERT INTO Product ( project, owner, name, title, description, homepageurl ) VALUES ( 4, 3, 'apr', 'Apache Portable Runtime Library', 'APR description goes here. A good description has at least a full paragraph of text, explaining what\'s unique about that product, why and when you would use it.', 'http://apr.apache.org/' );
INSERT INTO Product ( project, owner, name, title, description, homepageurl ) VALUES ( 4, 3, 'cocoon', 'XML Publishing Engine', 'Cocoon description goes here. A good description has at least a full paragraph of text, explaining what\'s unique about that product, why and when you would use it.', 'http://cocoon.apache.org/' );




-- ProductRelease
INSERT INTO ProductRelease ( product, datereleased, version, owner ) VALUES ( , , '',  );
INSERT INTO ProductRelease ( product, datereleased, version, owner ) VALUES ( , , '',  );
INSERT INTO ProductRelease ( product, datereleased, version, owner ) VALUES ( , , '',  );
INSERT INTO ProductRelease ( product, datereleased, version, owner ) VALUES ( , , '',  );
INSERT INTO ProductRelease ( product, datereleased, version, owner ) VALUES ( , , '',  );



/* 
 SQL data to populate Soyuz DB and get some results
*/


--Sourcepackage
INSERT INTO Sourcepackage (maintainer, name, title, description)
VALUES ((SELECT id FROM Person WHERE presentationname = 'Mark Shuttleworth'),
         'mozilla-firefox', 'Ubuntu Mozilla Firefox Source Package', 
         'text');

INSERT INTO Sourcepackage (maintainer, name, title, description)
VALUES ((SELECT id FROM Person WHERE presentationname = 'Steve Alexander'),
         'mozilla-thunderbird', 'Ubuntu Mozilla Thunderbird Source Package', 
         'text');

INSERT INTO Sourcepackage (maintainer, name, title, description)
VALUES ((SELECT id FROM Person WHERE presentationname = 'Andrew Bennetts'),
         'python-twisted', 'Python Twisted Source Package', 
         'text');
INSERT INTO Sourcepackage (maintainer, name, title, description)
VALUES ((SELECT id FROM Person WHERE presentationname = 'Dave Miller'),
         'bugzila', 'Bugzila Source Package', 
         'text');
INSERT INTO Sourcepackage (maintainer, name, title, description)
VALUES ((SELECT id FROM Person WHERE presentationname = 'James Blackwell'),
         'tla-arch', 'Arch tla Source Package', 
         'text');
INSERT INTO Sourcepackage (maintainer, name, title, description)
VALUES ((SELECT id FROM Person WHERE presentationname = 'Christian Reis'),
         'kiwi2', 'Kiwi2 Source Package', 
         'text');
INSERT INTO Sourcepackage (maintainer, name, title, description)
VALUES ((SELECT id FROM Person WHERE presentationname = 'Alexander Limi'),
         'plone', 'Plone Source Package', 
         'text');


--SourcepackageRelease
INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE name = 'mozilla-firefox'),
 	1,
        (SELECT id FROM Person WHERE presentationname = 'Mark Shuttleworth'),
        '0.9.1-1',
        timestamp '2004-06-29 00:00',
        1);

INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE name = 'mozilla-thunderbird'),
 	1,
        (SELECT id FROM Person WHERE presentationname = 'Steve Alexander'),
        '0.9.1-2',
        timestamp '2004-06-30 00:00',
        1);

INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE name = 'python-twisted'),
 	1,
        (SELECT id FROM Person WHERE presentationname = 'Andrew Bennetts'),
        '0.9.1-3',
        timestamp '2004-07-01 00:00',
        1);

INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE name = 'bugzila'),
 	1,
        (SELECT id FROM Person WHERE presentationname = 'Dave Miller'),
        '0.9.1-4',
        timestamp '2004-07-02 00:00',
        1);

INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE name = 'tla-arch'),
 	1,
        (SELECT id FROM Person WHERE presentationname = 'James Blackwell'),
        '0.9.1-5',
        timestamp '2004-07-03 00:00',
        1);

INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE name = 'kiwi2'),
 	1,
        (SELECT id FROM Person WHERE presentationname = 'Christian Reis'),
        '0.9.1-6',
        timestamp '2004-07-04 00:00',
        1);

INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE name = 'plone'),
 	1,
        (SELECT id FROM Person WHERE presentationname = 'Alexander Limi'),
        '0.9.1-7',
        timestamp '2004-07-05 00:00',
        1);


--Manifest
INSERT INTO Manifest (datecreated, owner)
VALUES (timestamp '2004-06-29 00:00',  
 (SELECT id FROM Person WHERE presentationname = 'Mark Shuttleworth')
 );

INSERT INTO Manifest (datecreated, owner)
VALUES (timestamp '2004-06-30 00:00',  
 (SELECT id FROM Person WHERE presentationname = 'Steve Alexander')
 );

INSERT INTO Manifest (datecreated, owner)
VALUES (timestamp '2004-07-01 00:00',  
 (SELECT id FROM Person WHERE presentationname = 'Andrew Bennetts')
 );

INSERT INTO Manifest (datecreated, owner)
VALUES (timestamp '2004-07-02 00:00',  
 (SELECT id FROM Person WHERE presentationname = 'Dave Miller')
 );

INSERT INTO Manifest (datecreated, owner)
VALUES (timestamp '2004-07-03 00:00',  
 (SELECT id FROM Person WHERE presentationname = 'James Blackwell')
 );

INSERT INTO Manifest (datecreated, owner)
VALUES (timestamp '2004-07-04 00:00',  
 (SELECT id FROM Person WHERE presentationname = 'Christian Reis')
 );

INSERT INTO Manifest (datecreated, owner)
VALUES (timestamp '2004-07-05 00:00',  
 (SELECT id FROM Person WHERE presentationname = 'Alexander Limi')
 );


--CodeRelease
INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcepackageRelease WHERE dateuploaded = timestamp '2004-06-29 00:00'),
 (SELECT id FROM Manifest WHERE datecreated = timestamp '2004-06-29 00:00'));

INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcepackageRelease WHERE dateuploaded = timestamp '2004-06-30 00:00'),
 (SELECT id FROM Manifest WHERE datecreated = timestamp '2004-06-30 00:00'));

INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcepackageRelease WHERE dateuploaded = timestamp '2004-07-01 00:00'),
 (SELECT id FROM Manifest WHERE datecreated = timestamp '2004-07-01 00:00'));

INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcepackageRelease WHERE dateuploaded = timestamp '2004-07-02 00:00'),
 (SELECT id FROM Manifest WHERE datecreated = timestamp '2004-07-02 00:00'));

INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcepackageRelease WHERE dateuploaded = timestamp '2004-07-03 00:00'),
 (SELECT id FROM Manifest WHERE datecreated = timestamp '2004-07-03 00:00'));

INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcepackageRelease WHERE dateuploaded = timestamp '2004-07-04 00:00'),
 (SELECT id FROM Manifest WHERE datecreated = timestamp '2004-07-04 00:00'));

INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcepackageRelease WHERE dateuploaded = timestamp '2004-07-05 00:00'),
 (SELECT id FROM Manifest WHERE datecreated = timestamp '2004-06-29 00:00'));


--ArchArchive
INSERT INTO ArchArchive (name, title, description, visible)
VALUES ('mozilla', 'Mozilla', 'text', false);

INSERT INTO ArchArchive (name, title, description, visible)
VALUES ('thunderbird', 'Thunderbid', 'text', false);

INSERT INTO ArchArchive (name, title, description, visible)
VALUES ('twisted', 'Twisted', 'text', false);

INSERT INTO ArchArchive (name, title, description, visible)
VALUES ('bugzila', 'Bugzila', 'text', false);

INSERT INTO ArchArchive (name, title, description, visible)
VALUES ('arch', 'Arch', 'text', false);

INSERT INTO ArchArchive (name, title, description, visible)
VALUES ('kiwi2', 'Kiwi2', 'text', false);

INSERT INTO ArchArchive (name, title, description, visible)
VALUES ('plone', 'Plone', 'text', false);

--Archnamespace
INSERT INTO Archnamespace (archarchive, category,visible) 
VALUES (1, 'mozilla', true);

INSERT INTO Archnamespace (archarchive, category,visible) 
VALUES (2, 'tunderbird', true);

INSERT INTO Archnamespace (archarchive, category,visible) 
VALUES (3, 'twisted', true);

INSERT INTO Archnamespace (archarchive, category,visible) 
VALUES (4, 'bugzila', true);

INSERT INTO Archnamespace (archarchive, category,visible) 
VALUES (5, 'arch', true);

INSERT INTO Archnamespace (archarchive, category,visible) 
VALUES (6, 'kiwi2', true);

INSERT INTO Archnamespace (archarchive, category,visible) 
VALUES (7, 'plone', true);


--Branch
INSERT INTO Branch (archnamespace, title, description, owner)
VALUES ((SELECT id FROM ArchArchive WHERE name = 'mozilla'),
        'Mozilla Firefox 0.9.1', 'text',
 (SELECT id FROM Person WHERE presentationname = 'Mark Shuttleworth')); 

INSERT INTO Branch (archnamespace, title, description, owner)
VALUES ((SELECT id FROM ArchArchive WHERE name = 'thunderbird'),
        'Mozilla Thunderbird 0.9.1', 'text',
 (SELECT id FROM Person WHERE presentationname = 'Steve Alexander')); 

INSERT INTO Branch (archnamespace, title, description, owner)
VALUES ((SELECT id FROM ArchArchive WHERE name = 'twisted'),
        'Python Twisted 0.9.1', 'text',
 (SELECT id FROM Person WHERE presentationname = 'Andrew Bennetts')); 

INSERT INTO Branch (archnamespace, title, description, owner)
VALUES ((SELECT id FROM ArchArchive WHERE name = 'bugzila'),
        'Bugzila 0.9.1', 'text',
 (SELECT id FROM Person WHERE presentationname = 'Dave Miller')); 

INSERT INTO Branch (archnamespace, title, description, owner)
VALUES ((SELECT id FROM ArchArchive WHERE name = 'arch'),
        'Arch 0.9.1', 'text',
 (SELECT id FROM Person WHERE presentationname = 'James Blackwell')); 

INSERT INTO Branch (archnamespace, title, description, owner)
VALUES ((SELECT id FROM ArchArchive WHERE name = 'kiwi2'),
        'Kiwi2 0.9.1', 'text',
 (SELECT id FROM Person WHERE presentationname = 'Christian Reis')); 

INSERT INTO Branch (archnamespace, title, description, owner)
VALUES ((SELECT id FROM ArchArchive WHERE name = 'plone'),
        'Plone 0.9.1', 'text',
 (SELECT id FROM Person WHERE presentationname = 'Alexander Limi')); 

--schema
INSERT INTO schema (name, title, description, owner) 
VALUES('Mark schema', 'TITLE', 'description', (Select id from Person where presentationname = 'Mark Shuttleworth'));

--label
INSERT INTO label (schema, name, title, description) 
VALUES(1, 'TAR', 'TAR title', 'TAR Description');

/*
--Manifest
INSERT INTO Manifest (owner) 
VALUES ((select id from Person where presentationname='Mark Shuttleworth'));
*/



/* 
 SQL data to populate Soyuz DB and get some results
 

Canonical Software
cprov
debonzi
*/


--CodeRelease
INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcepackageRelease WHERE dateuploaded = timestamp '2004-06-29 00:00'),
 (SELECT id FROM Manifest WHERE datecreated = timestamp '2004-06-29 00:00'));

INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcepackageRelease WHERE dateuploaded = timestamp '2004-06-30 00:00'),
 (SELECT id FROM Manifest WHERE datecreated = timestamp '2004-06-30 00:00'));

INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcepackageRelease WHERE dateuploaded = timestamp '2004-07-01 00:00'),
 (SELECT id FROM Manifest WHERE datecreated = timestamp '2004-07-01 00:00'));

INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcepackageRelease WHERE dateuploaded = timestamp '2004-07-02 00:00'),
 (SELECT id FROM Manifest WHERE datecreated = timestamp '2004-07-02 00:00'));

INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcepackageRelease WHERE dateuploaded = timestamp '2004-07-03 00:00'),
 (SELECT id FROM Manifest WHERE datecreated = timestamp '2004-07-03 00:00'));

INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcepackageRelease WHERE dateuploaded = timestamp '2004-07-04 00:00'),
 (SELECT id FROM Manifest WHERE datecreated = timestamp '2004-07-04 00:00'));

INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcepackageRelease WHERE dateuploaded = timestamp '2004-07-05 00:00'),
 (SELECT id FROM Manifest WHERE datecreated = timestamp '2004-06-29 00:00'));


--ArchArchive
INSERT INTO ArchArchive (name, title, description, visible)
VALUES ('mozilla', 'Mozilla', 'text', false);

INSERT INTO ArchArchive (name, title, description, visible)
VALUES ('thunderbird', 'Thunderbid', 'text', false);

INSERT INTO ArchArchive (name, title, description, visible)
VALUES ('twisted', 'Twisted', 'text', false);

INSERT INTO ArchArchive (name, title, description, visible)
VALUES ('bugzila', 'Bugzila', 'text', false);

INSERT INTO ArchArchive (name, title, description, visible)
VALUES ('arch', 'Arch', 'text', false);

INSERT INTO ArchArchive (name, title, description, visible)
VALUES ('kiwi2', 'Kiwi2', 'text', false);

INSERT INTO ArchArchive (name, title, description, visible)
VALUES ('plone', 'Plone', 'text', false);

--Archnamespace
INSERT INTO Archnamespace (archarchive, category,visible) 
VALUES (1, 'mozilla', true);

INSERT INTO Archnamespace (archarchive, category,visible) 
VALUES (2, 'tunderbird', true);

INSERT INTO Archnamespace (archarchive, category,visible) 
VALUES (3, 'twisted', true);

INSERT INTO Archnamespace (archarchive, category,visible) 
VALUES (4, 'bugzila', true);

INSERT INTO Archnamespace (archarchive, category,visible) 
VALUES (5, 'arch', true);

INSERT INTO Archnamespace (archarchive, category,visible) 
VALUES (6, 'kiwi2', true);

INSERT INTO Archnamespace (archarchive, category,visible) 
VALUES (7, 'plone', true);


--schema
INSERT INTO schema (name, title, description, owner) 
VALUES('Mark schema', 'TITLE', 'description', (Select id from Person where presentationname = 'Mark Shuttleworth'));

--label
INSERT INTO label (schema, name, title, description) 
VALUES(1, 'TAR', 'TAR title', 'TAR Description');

/*
--Manifest
INSERT INTO Manifest (owner) 
VALUES ((select id from Person where presentationname='Mark Shuttleworth'));
*/



