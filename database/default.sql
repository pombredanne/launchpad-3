/*
   LAUNCHPAD INITIAL DATA

# arch-tag: 72b5bbef-19d6-4a07-b434-60f2a121ade2

this is initial data for launchpad. unlike the sample data, this will be loaded into our production install.

*/

-- Person
INSERT INTO Person ( displayname, givenname, familyname ) VALUES ( 'Mark Shuttleworth', 'Mark', 'Shuttleworth' );       -- 1
INSERT INTO Person ( displayname, givenname, familyname ) VALUES ( 'Robert Collins', 'Robert', 'Collins' );             -- 2
/*
INSERT INTO Person ( displayname, givenname, familyname ) VALUES ( 'Dave Miller', 'David', 'Miller' );                  -- 2
INSERT INTO Person ( displayname, givenname, familyname ) VALUES ( 'Colin Watson', 'Colin', 'Watson' );                 -- 3
INSERT INTO Person ( displayname, givenname, familyname ) VALUES ( 'Scott James Remnant', 'Scott James', 'Remnant' );   -- 4
INSERT INTO Person ( displayname, givenname, familyname ) VALUES ( 'Jeff Waugh', 'Jeff', 'Waugh' );                     -- 6
INSERT INTO Person ( displayname, givenname, familyname ) VALUES ( 'Andrew Bennetts', 'Andrew', 'Bennetts' );           -- 7
INSERT INTO Person ( displayname, givenname, familyname ) VALUES ( 'James Blackwell', 'James', 'Blackwell' );           -- 8
INSERT INTO Person ( displayname, givenname, familyname ) VALUES ( 'Christian Reis', 'Christian', 'Reis' );             -- 9
INSERT INTO Person ( displayname, givenname, familyname ) VALUES ( 'Alexander Limi', 'Alexander', 'Limi' );             -- 10
INSERT INTO Person ( displayname, givenname, familyname ) VALUES ( 'Steve Alexander', 'Steve', 'Alexander' );           -- 11
INSERT INTO Person ( displayname, givenname, familyname ) VALUES ( 'Carlos Perelló Marín', 'Carlos', 'Perelló Marín' ); -- 12
*/

---

---

-- EmailAddress
INSERT INTO EmailAddress ( email, person, status ) VALUES ( 'mark@hbd.com', 1, 2 );
INSERT INTO EmailAddress ( email, person, status ) VALUES ( 'robertc@robertcollins.net', 2, 2 );

/*
-- BugSystemType
INSERT INTO BugSystemType VALUES ( 1, 'bugzilla', 'BugZilla', 'Dave Miller\'s Labour of Love, the Godfather of Open Source project issue tracking.', 'http://www.bugzilla.org/', 2 );
INSERT INTO BugSystemType VALUES ( 2, 'debbugs', 'DebBugs', 'The Debian bug tracking system, ugly as sin but fast and productive as a rabbit in high heels.', 'http://bugs.debian.org/', 3 );
INSERT INTO BugSystemType VALUES ( 3, 'roundup', 'Round-Up', 'Python-based open source bug tracking system with an elegant design and reputation for cleanliness and usability.', 'http://www.roundup.org/', 4 );
*/


-- Project
INSERT INTO Project ( owner, name, displayname, title, shortdesc, description, homepageurl ) VALUES ( 1, 'ubuntu', 'Ubuntu', 'The Ubuntu Project', 'A community Linux distribution building building a slick desktop for the global market.', 'The Ubuntu Project aims to create a freely redistributable OS that is easy to customize and derive from. Ubuntu is released every six months with contributions from a large community. Ubuntu also includes work to unify the translation of common opens source desktop applications and the tracking of bugs across multiple distributions.', 'http://www.no-name-yet.com/' ); -- 1
INSERT INTO Project ( owner, name, displayname, title, shortdesc, description, homepageurl ) VALUES ( 2, 'do-not-use-info-imports', 'DO NOT USE', 'DO NOT USE', 'DO NOT USE', 'TEMPORARY project till mirror jobs are assigned to correct project', 'http://arch.ubuntu.com/' ); -- 2
INSERT INTO Project ( owner, name, displayname, title, shortdesc, description, homepageurl ) VALUES ( 2, 'launchpad-mirrors', 'Launchpad SCM Mirrors', 'The Launchpad Mirroring Project', 'launchpad mirrors various revision control archives, that mirroring is managed here', 'A project to mirror revision control archives into Arch.', 'http://arch.ubuntu.com/' ); -- 3



-- Product
INSERT INTO Product ( project, owner, name, displayname, title, shortdesc, description, homepageurl ) VALUES ( 1, 1, 'ubuntu', 'Ubuntu', 'Ubuntu', 'An easy-to-install version of Linux that has a complete set of desktop applications ready to use immediately after installation.', 'Ubuntu is a desktop Linux that you can give your girlfriend to install. Works out of the box with recent Gnome desktop applications configured to make you productive immediately. Ubuntu is updated every six months, comes with security updates for peace of mind, and is avaialble everywhere absolutely free of charge.', 'http://www.ubuntu.com/' );
INSERT INTO Product ( project, owner, name, displayname, title, shortdesc, description, homepageurl ) VALUES ( 2, 2, 'unassigned', 'unassigned syncs', 'unassigned syncs', 'syncs still not assigned to a real product', 'unassigned syncs, will not be processed, to be moved to real proejcts ASAP.', 'http://arch.ubuntu.com/' );
INSERT INTO Product ( project, owner, name, displayname, title, shortdesc, description, homepageurl ) VALUES ( 3, 2, 'arch-mirrors', 'Arch mirrors', 'Arch archive mirrors', 'Arch Archive Mirroring project.', 'Arch archive full-archive mirror tasks', 'http://arch.ubuntu.com/' );

/*
-- SourcePackage
INSERT INTO SourcePackage (maintainer, name, title, description)
VALUES ((SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
         'mozilla-firefox', 'Ubuntu Mozilla Firefox', 
         'text');

INSERT INTO SourcePackage (maintainer, name, title, description)
VALUES ((SELECT id FROM Person WHERE displayname = 'Steve Alexander'),
         'mozilla-thunderbird', 'Ubuntu Mozilla Thunderbird', 
         'text');

INSERT INTO SourcePackage (maintainer, name, title, description)
VALUES ((SELECT id FROM Person WHERE displayname = 'Andrew Bennetts'),
         'python-twisted', 'Python Twisted', 
         'text');
INSERT INTO SourcePackage (maintainer, name, title, description)
VALUES ((SELECT id FROM Person WHERE displayname = 'Dave Miller'),
         'bugzilla', 'Bugzilla', 
         'text');
INSERT INTO SourcePackage (maintainer, name, title, description)
VALUES ((SELECT id FROM Person WHERE displayname = 'James Blackwell'),
         'arch', 'Arch(TLA)', 
         'text');
INSERT INTO SourcePackage (maintainer, name, title, description)
VALUES ((SELECT id FROM Person WHERE displayname = 'Christian Reis'),
         'kiwi2', 'Kiwi2', 
         'text');
INSERT INTO SourcePackage (maintainer, name, title, description)
VALUES ((SELECT id FROM Person WHERE displayname = 'Alexander Limi'),
         'plone', 'Plone', 
         'text');
INSERT INTO SourcePackage (maintainer, name, title, description)
VALUES ((SELECT id FROM Person WHERE displayname = 'Jeff Waugh'),
        'evolution', 'Evolution', 
        'text');


--SourcePackageRelease
INSERT INTO SourcePackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM SourcePackage WHERE name = 'mozilla-firefox'),
 	1,
        (SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
        '0.9.1-1',
        timestamp '2004-06-29 00:00',
        1);

INSERT INTO SourcePackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM SourcePackage WHERE name = 'mozilla-thunderbird'),
 	1,
        (SELECT id FROM Person WHERE displayname = 'Steve Alexander'),
        '0.9.1-2',
        timestamp '2004-06-30 00:00',
        1);

INSERT INTO SourcePackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM SourcePackage WHERE name = 'python-twisted'),
 	1,
        (SELECT id FROM Person WHERE displayname = 'Andrew Bennetts'),
        '0.9.1-3',
        timestamp '2004-07-01 00:00',
        1);

INSERT INTO SourcePackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM SourcePackage WHERE name = 'bugzilla'),
 	1,
        (SELECT id FROM Person WHERE displayname = 'Dave Miller'),
        '0.9.1-4',
        timestamp '2004-07-02 00:00',
        1);

INSERT INTO SourcePackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM SourcePackage WHERE name = 'arch'),
 	1,
        (SELECT id FROM Person WHERE displayname = 'James Blackwell'),
        '0.9.1-5',
        timestamp '2004-07-03 00:00',
        1);

INSERT INTO SourcePackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM SourcePackage WHERE name = 'kiwi2'),
 	1,
        (SELECT id FROM Person WHERE displayname = 'Christian Reis'),
        '0.9.1-6',
        timestamp '2004-07-04 00:00',
        1);

INSERT INTO SourcePackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM SourcePackage WHERE name = 'plone'),
 	1,
        (SELECT id FROM Person WHERE displayname = 'Alexander Limi'),
        '0.9.1-7',
        timestamp '2004-07-05 00:00',
        1);


--Manifest
INSERT INTO Manifest (datecreated, owner)
VALUES (timestamp '2004-06-29 00:00',  
 (SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth')
 );

INSERT INTO Manifest (datecreated, owner)
VALUES (timestamp '2004-06-30 00:00',  
 (SELECT id FROM Person WHERE displayname = 'Steve Alexander')
 );

INSERT INTO Manifest (datecreated, owner)
VALUES (timestamp '2004-07-01 00:00',  
 (SELECT id FROM Person WHERE displayname = 'Andrew Bennetts')
 );

INSERT INTO Manifest (datecreated, owner)
VALUES (timestamp '2004-07-02 00:00',  
 (SELECT id FROM Person WHERE displayname = 'Dave Miller')
 );

INSERT INTO Manifest (datecreated, owner)
VALUES (timestamp '2004-07-03 00:00',  
 (SELECT id FROM Person WHERE displayname = 'James Blackwell')
 );

INSERT INTO Manifest (datecreated, owner)
VALUES (timestamp '2004-07-04 00:00',  
 (SELECT id FROM Person WHERE displayname = 'Christian Reis')
 );

INSERT INTO Manifest (datecreated, owner)
VALUES (timestamp '2004-07-05 00:00',  
 (SELECT id FROM Person WHERE displayname = 'Alexander Limi')
 );


--CodeRelease
INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcePackageRelease WHERE dateuploaded = timestamp '2004-06-29 00:00'),
 (SELECT id FROM Manifest WHERE datecreated = timestamp '2004-06-29 00:00'));

INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcePackageRelease WHERE dateuploaded = timestamp '2004-06-30 00:00'),
 (SELECT id FROM Manifest WHERE datecreated = timestamp '2004-06-30 00:00'));

INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcePackageRelease WHERE dateuploaded = timestamp '2004-07-01 00:00'),
 (SELECT id FROM Manifest WHERE datecreated = timestamp '2004-07-01 00:00'));

INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcePackageRelease WHERE dateuploaded = timestamp '2004-07-02 00:00'),
 (SELECT id FROM Manifest WHERE datecreated = timestamp '2004-07-02 00:00'));

INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcePackageRelease WHERE dateuploaded = timestamp '2004-07-03 00:00'),
 (SELECT id FROM Manifest WHERE datecreated = timestamp '2004-07-03 00:00'));

INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcePackageRelease WHERE dateuploaded = timestamp '2004-07-04 00:00'),
 (SELECT id FROM Manifest WHERE datecreated = timestamp '2004-07-04 00:00'));

INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcePackageRelease WHERE dateuploaded = timestamp '2004-07-05 00:00'),
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

INSERT INTO ArchArchive (name, title, description, visible)
VALUES ('gnome', 'GNOME', 'The GNOME Project', false);


--Archnamespace
INSERT INTO Archnamespace (archarchive, category, visible) 
VALUES (1, 'mozilla', true);

INSERT INTO Archnamespace (archarchive, category, visible) 
VALUES (2, 'tunderbird', true);

INSERT INTO Archnamespace (archarchive, category, visible) 
VALUES (3, 'twisted', true);

INSERT INTO Archnamespace (archarchive, category, visible) 
VALUES (4, 'bugzila', true);

INSERT INTO Archnamespace (archarchive, category, visible) 
VALUES (5, 'arch', true);

INSERT INTO Archnamespace (archarchive, category, visible) 
VALUES (6, 'kiwi2', true);

INSERT INTO Archnamespace (archarchive, category, visible) 
VALUES (7, 'plone', true);

INSERT INTO ArchNamespace (archarchive, category, branch, version, visible)
VALUES ((SELECT id FROM ArchArchive WHERE name = 'gnome'), 'gnome', 'evolution',
	'1.5.90', false);

--Branch
INSERT INTO Branch (archnamespace, title, description, owner)
VALUES ((SELECT id FROM ArchArchive WHERE name = 'mozilla'),
        'Mozilla Firefox 0.9.1', 'text',
 (SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth')); 

INSERT INTO Branch (archnamespace, title, description, owner)
VALUES ((SELECT id FROM ArchArchive WHERE name = 'thunderbird'),
        'Mozilla Thunderbird 0.9.1', 'text',
 (SELECT id FROM Person WHERE displayname = 'Steve Alexander')); 

INSERT INTO Branch (archnamespace, title, description, owner)
VALUES ((SELECT id FROM ArchArchive WHERE name = 'twisted'),
        'Python Twisted 0.9.1', 'text',
 (SELECT id FROM Person WHERE displayname = 'Andrew Bennetts')); 

INSERT INTO Branch (archnamespace, title, description, owner)
VALUES ((SELECT id FROM ArchArchive WHERE name = 'bugzila'),
        'Bugzila 0.9.1', 'text',
 (SELECT id FROM Person WHERE displayname = 'Dave Miller')); 

INSERT INTO Branch (archnamespace, title, description, owner)
VALUES ((SELECT id FROM ArchArchive WHERE name = 'arch'),
        'Arch 0.9.1', 'text',
 (SELECT id FROM Person WHERE displayname = 'James Blackwell')); 

INSERT INTO Branch (archnamespace, title, description, owner)
VALUES ((SELECT id FROM ArchArchive WHERE name = 'kiwi2'),
        'Kiwi2 0.9.1', 'text',
 (SELECT id FROM Person WHERE displayname = 'Christian Reis')); 

INSERT INTO Branch (archnamespace, title, description, owner)
VALUES ((SELECT id FROM ArchArchive WHERE name = 'plone'),
        'Plone 0.9.1', 'text',
 (SELECT id FROM Person WHERE displayname = 'Alexander Limi'));

INSERT INTO Branch (archnamespace, title, description, owner)
VALUES ((SELECT id FROM ArchNamespace
	 WHERE category = 'gnome' AND
	       branch = 'evolution' AND
	       version = '1.5.90'),
	'Evolution 1.5.90', 'text',
	(SELECT id FROM Person WHERE displayname = 'Jeff Waugh'));
*/

/*
--Manifest
INSERT INTO Manifest (owner) 
VALUES ((select id from Person where presentationname='Mark Shuttleworth'));
*/


