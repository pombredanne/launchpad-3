/*
   SOYUZ SAMPLE DATA
   
   This is some sample data for the Soyuz App components.  
   This requires the default data to be inserted first.
*/

/* 
 Sample data for Soyuz
*/
-- Person
INSERT INTO Person ( displayname, givenname, familyname ) VALUES ( 'Dave Miller', 'David', 'Miller' );                  -- 2
INSERT INTO Person ( displayname, givenname, familyname ) VALUES ( 'Colin Watson', 'Colin', 'Watson' );                 -- 3
INSERT INTO Person ( displayname, givenname, familyname ) VALUES ( 'Scott James Remnant', 'Scott James', 'Remnant' );   -- 4
INSERT INTO Person ( displayname, givenname, familyname ) VALUES ( 'Jeff Waugh', 'Jeff', 'Waugh' );                     -- 6
INSERT INTO Person ( displayname, givenname, familyname ) VALUES ( 'Andrew Bennetts', 'Andrew', 'Bennetts' );           -- 7
INSERT INTO Person ( displayname, givenname, familyname ) VALUES ( 'James Blackwell', 'James', 'Blackwell' );           -- 8
INSERT INTO Person ( displayname, givenname, familyname ) VALUES ( 'Christian Reis', 'Christian', 'Reis' );             -- 9
INSERT INTO Person ( displayname, givenname, familyname ) VALUES ( 'Alexander Limi', 'Alexander', 'Limi' );             -- 10
INSERT INTO Person ( displayname, givenname, familyname ) VALUES ( 'Steve Alexander', 'Steve', 'Alexander' );           -- 11


--EmailAdress




-- Component
INSERT INTO Component (name) VALUES ('default_component');

-- Section

INSERT INTO Section (name) VALUES ('default_section');

-- Schema
INSERT INTO schema (name, title, description, owner, extensible) VALUES('Mark schema', 'TITLE', 'description', (Select id from Person where displayname = 'Mark Shuttleworth'), true);
INSERT INTO Schema (name, title, description, owner, extensible) values('schema', 'SCHEMA', 'description', (Select id from Person where displayname = 'Mark Shuttleworth'), true);
INSERT INTO Schema (name, title, description, owner, extensible) values('trema', 'XCHEMA', 'description', (Select id from Person where displayname = 'Mark Shuttleworth'), true);
INSERT INTO Schema (name, title, description, owner, extensible) values('enema', 'ENHEMA', 'description', (Select id from Person where displayname = 'Mark Shuttleworth'), true);

-- Sourcepackage
INSERT INTO Sourcepackage (maintainer, name, title, description)
VALUES ((SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
         'mozilla-firefox', 'Ubuntu Mozilla Firefox', 
         'text');

INSERT INTO Sourcepackage (maintainer, name, title, description)
VALUES ((SELECT id FROM Person WHERE displayname = 'Steve Alexander'),
         'mozilla-thunderbird', 'Ubuntu Mozilla Thunderbird', 
         'text');

INSERT INTO Sourcepackage (maintainer, name, title, description)
VALUES ((SELECT id FROM Person WHERE displayname = 'Andrew Bennetts'),
         'python-twisted', 'Python Twisted', 
         'text');
INSERT INTO Sourcepackage (maintainer, name, title, description)
VALUES ((SELECT id FROM Person WHERE displayname = 'Dave Miller'),
         'bugzilla', 'Bugzilla', 
         'text');
INSERT INTO Sourcepackage (maintainer, name, title, description)
VALUES ((SELECT id FROM Person WHERE displayname = 'James Blackwell'),
         'arch', 'Arch(TLA)', 
         'text');
INSERT INTO Sourcepackage (maintainer, name, title, description)
VALUES ((SELECT id FROM Person WHERE displayname = 'Christian Reis'),
         'kiwi2', 'Kiwi2', 
         'text');
INSERT INTO Sourcepackage (maintainer, name, title, description)
VALUES ((SELECT id FROM Person WHERE displayname = 'Alexander Limi'),
         'plone', 'Plone', 
         'text');
INSERT INTO Sourcepackage (maintainer, name, title, description)
VALUES ((SELECT id FROM Person WHERE displayname = 'Jeff Waugh'),
        'evolution', 'Evolution', 
        'text');


--SourcepackageRelease
INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE name = 'mozilla-firefox'),
 	1,
        (SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
        '0.9.0-6',
        timestamp '2004-06-17 00:00',
        1);


INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE name = 'mozilla-firefox'),
 	1,
        (SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
        '0.9.0-7',
        timestamp '2004-06-18 00:00',
        1);


INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE name = 'mozilla-firefox'),
 	1,
        (SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
        '0.9.0-8',
        timestamp '2004-06-19 00:00',
        1);

INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE name = 'mozilla-firefox'),
 	1,
        (SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
        '0.9.0-9',
        timestamp '2004-06-20 00:00',
        1);

INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE name = 'mozilla-firefox'),
 	1,
        (SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
        '0.9.1-1',
        timestamp '2004-06-29 00:00',
        1);

INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE name = 'mozilla-thunderbird'),
 	1,
        (SELECT id FROM Person WHERE displayname = 'Steve Alexander'),
        '0.9.1-2',
        timestamp '2004-06-30 00:00',
        1);

INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE name = 'python-twisted'),
 	1,
        (SELECT id FROM Person WHERE displayname = 'Andrew Bennetts'),
        '0.9.1-3',
        timestamp '2004-07-01 00:00',
        1);

INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE name = 'bugzilla'),
 	1,
        (SELECT id FROM Person WHERE displayname = 'Dave Miller'),
        '0.9.1-4',
        timestamp '2004-07-02 00:00',
        1);

INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE name = 'arch'),
 	1,
        (SELECT id FROM Person WHERE displayname = 'James Blackwell'),
        '0.9.1-5',
        timestamp '2004-07-03 00:00',
        1);

INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE name = 'kiwi2'),
 	1,
        (SELECT id FROM Person WHERE displayname = 'Christian Reis'),
        '0.9.1-6',
        timestamp '2004-07-04 00:00',
        1);

INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE name = 'plone'),
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


 -- Label
INSERT INTO Label (schema, name, title, description)
VALUES ((SELECT id FROM Schema WHERE name = 'Mark schema'),
         'blah', 'blah', 'blah');
 -- ProcessorFamily
INSERT INTO ProcessorFamily (name, title, description, owner) 
VALUES ('x86', 'Intel 386 compatible chips', 'Bring back the 8086!', 
         (SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'));
 
 -- Processor
INSERT INTO Processor (family, name, title, description, owner)
VALUES ((SELECT id FROM ProcessorFamily WHERE name = 'x86'),
         '386', 'Intel 386', 'Intel 386 and its many derivatives and clones, the basic 32-bit chip in the x86 family',
        (SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'));

-- Distribution
INSERT INTO Distribution (name, title, description, domainname, owner) 
	values ('ubuntu', 'Ubuntu', 
	'Ubuntu is a new concept of GNU/Linux Distribution based on Debian GNU/Linux.', 
	'domain', 1);

INSERT INTO Distribution (name, title, description, domainname, owner) 
	values ('redhat', 'Redhat Advanced Server', 
	'Red Hat is a commercial distribution of GNU/Linux Operating System.', 
	'domain', 1);

INSERT INTO Distribution (name, title, description, domainname, owner) 
	values ('debian', 'Debian GNU/Linux', 
	'Debian GNU/Linux is a non commercial distribution of a GNU/Linux Operating System for many platforms.', 
	'domain', 1);

INSERT INTO Distribution (name, title, description, domainname, owner) 
	values ('gentoo', 'The Gentoo Linux', 
	'Gentoo is a very customizeable GNU/Linux Distribution', 
	'domain', 1);

INSERT INTO Distribution (name, title, description, domainname, owner) 
	values ('porkypigpolka', 'Porky Pig Polka Distribution', 
	'Should be near the Spork concept of GNU/Linux Distribution',
	'domain', 1);



-- Distrorelease
INSERT INTO Distrorelease (name, title, description, distribution, version, 
	datereleased, components, sections, releasestate, owner) 
	values 
	('warty', 'Warty', 'This is the first stable release of Ubuntu', 
	(SELECT id FROM Distribution WHERE name = 'ubuntu'), 
	'1.0.0', 
	'2004-08-20',
	1, 1, 0, 1);

INSERT INTO Distrorelease (name, title, description, distribution, version, 
	datereleased, components, sections, releasestate, owner) 
	VALUES ('six', 'Six Six Six', 
	'some text to describe the whole 666 release of RH', 
	(SELECT id FROM Distribution WHERE name = 'redhat'), 
	'6.0.1', 
	'2004-03-21',
	1, 1, 0, 8);

INSERT INTO Distrorelease (name, title, description, distribution, version, 
	datereleased, components, sections, releasestate, parentrelease, 
	owner) 
	VALUES ('hoary', 'Hoary Crazy-Unstable', 
	'Hoary is the next release of Ubuntu', 
	(SELECT id FROM Distribution WHERE name = 'ubuntu'), 
	'0.0.1',
	'2004-08-25', 
	1, 1, 0, 
	(SELECT id FROM Distrorelease WHERE name = 'warty'),
	1);

INSERT INTO Distrorelease (name, title, description, distribution, version, 
	datereleased, components, sections, releasestate, parentrelease,
	owner) 
	VALUES ('7.0', 'Seven', 
	'The release that we would not expect', 
	(SELECT id FROM Distribution WHERE name = 'redhat'), 
	'7.0.1', 
	'2004-04-01',
	1, 1, 0, 
	(SELECT id FROM Distrorelease WHERE name = 'six'),
	7);

INSERT INTO Distrorelease (name, title, description, distribution, version, 
	datereleased, components, sections, releasestate, parentrelease,
	owner) 
	VALUES ('grumpy', 'G-R-U-M-P-Y', 
	'Grumpy is far far away, but should be the third release of Ubuntu', 
	(SELECT id FROM Distribution WHERE name = 'ubuntu'),
	'-0.0.1', 
	'2004-08-29',
	1, 1, 0, 
	(SELECT id FROM Distrorelease WHERE name = 'warty'),
	1);

INSERT INTO Distrorelease (name, title, description, distribution, version, 
	datereleased, components, sections, releasestate, owner) 
	VALUES ('woody', 'WOODY', 
	'WOODY is the current stable verison of Debian GNU/Linux', 
	(SELECT id FROM Distribution WHERE name = 'debian'),
	'3.0', 
	'2003-01-01',
	1, 1, 0, 2);

INSERT INTO Distrorelease (name, title, description, distribution, version, 
	datereleased, components, sections, releasestate, parentrelease,
	owner) 
	VALUES ('sarge', 'Sarge', 
	'Sarge is the FROZEN unstable version of Debian GNU/Linux.', 
	(SELECT id FROM Distribution WHERE name = 'debian'),
	'3.1', 
	'2004-09-29',
	1, 1, 0, 
	(SELECT id FROM Distrorelease WHERE name = 'woody'),
	5);

INSERT INTO Distrorelease (name, title, description, distribution, version, 
	datereleased, components, sections, releasestate, parentrelease,
	owner) 
	VALUES ('sid', 'Sid', 
	'Sid is the CRAZY unstable version of Debian GNU/Linux.', 
	(SELECT id FROM Distribution WHERE name = 'debian'),
	'3.2', 
	'2004-12-29',
	1, 1, 0, 
	(SELECT id FROM Distrorelease WHERE name = 'woody'),
	6);

--Distroreleaserole

INSERT INTO Distroreleaserole (person, distrorelease, role) 
	VALUES(
	(SELECT id from Person WHERE displayname = 'Mark Shuttleworth'),
	(SELECT id from Distrorelease WHERE name = 'warty'),
	1);
INSERT INTO Distroreleaserole (person, distrorelease, role) 
	VALUES(
	(SELECT id from Person WHERE displayname = 'Mark Shuttleworth'),
	(SELECT id from Distrorelease WHERE name = 'hoary'),
	1);
INSERT INTO Distroreleaserole (person, distrorelease, role) 
	VALUES(
	(SELECT id from Person WHERE displayname = 'Mark Shuttleworth'),
	(SELECT id from Distrorelease WHERE name = 'grumpy'),
	1);

INSERT INTO Distroreleaserole (person, distrorelease, role) 
	VALUES(
	(SELECT id from Person WHERE displayname = 'Steve Alexander'),
	(SELECT id from Distrorelease WHERE name = 'warty'),
	2);
INSERT INTO Distroreleaserole (person, distrorelease, role) 
	VALUES(
	(SELECT id from Person WHERE displayname = 'Steve Alexander'),
	(SELECT id from Distrorelease WHERE name = 'hoary'),
	2);
INSERT INTO Distroreleaserole (person, distrorelease, role) 
	VALUES(
	(SELECT id from Person WHERE displayname = 'Steve Alexander'),
	(SELECT id from Distrorelease WHERE name = 'grumpy'),
	3);


--Distributionrole

INSERT INTO Distributionrole (person, distribution, role) 
	VALUES(
	(SELECT id from Person WHERE displayname = 'Mark Shuttleworth'),
	(SELECT id from Distribution WHERE name = 'ubuntu'),
	1);

INSERT INTO Distributionrole (person, distribution, role) 
	VALUES(
	(SELECT id from Person WHERE displayname = 'Steve Alexander'),
	(SELECT id from Distribution WHERE name = 'ubuntu'),
	1);

INSERT INTO Distributionrole (person, distribution, role) 
	VALUES(
	(SELECT id from Person WHERE displayname = 'Alexander Limi'),
	(SELECT id from Distribution WHERE name = 'ubuntu'),
	1);

INSERT INTO Distributionrole (person, distribution, role) 
	VALUES(
	(SELECT id from Person WHERE displayname = 'Andrew Bennetts'),
	(SELECT id from Distribution WHERE name = 'ubuntu'),
	1);

INSERT INTO Distributionrole (person, distribution, role) 
	VALUES(
	(SELECT id from Person WHERE displayname = 'Scott James Remnant'),
	(SELECT id from Distribution WHERE name = 'ubuntu'),
	1);

--DistroArchrelease
INSERT INTO Distroarchrelease(distrorelease, processorfamily, architecturetag, 
	owner) VALUES 
	((SELECT id FROM Distrorelease where name = 'warty'), 
	(SELECT id from Processorfamily where name = 'x86'), 
	'warty--x86--devel--0', 
	(SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth')
	);

-- Build

INSERT INTO Build (datecreated, processor, distroarchrelease, buildstate)
	VALUES
	('2004-08-24',
	(SELECT id FROM Processor where name = '386'),
	1, -- hardcoded ?!?! use query instead
	1  -- ??
	);	

--Binarypackagename
INSERT INTO Binarypackagename(name) VALUES ('mozilla-firefox');
INSERT INTO Binarypackagename(name) VALUES ('mozilla-thunderbird');
INSERT INTO Binarypackagename(name) VALUES ('python-twisted');
INSERT INTO Binarypackagename(name) VALUES ('bugzilla');
INSERT INTO Binarypackagename(name) VALUES ('arch');
INSERT INTO Binarypackagename(name) VALUES ('kiwi');
INSERT INTO Binarypackagename(name) VALUES ('plone');




-- Binarypackage
INSERT INTO Binarypackage (sourcepackagerelease, binarypackagename, 
version, shortdesc, description, build, binpackageformat, component, 
section, priority) 
	VALUES (
(SELECT id from Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where name = 'mozilla-firefox')  and version='0.9.1-1'),
(SELECT id from Binarypackagename WHERE name = 'mozilla-firefox'), 
'0.8', 'Mozilla Firefox 0.8', 'some text', 
	1, -- hardcoded ?? use query instead
	1, -- DEB ?
	1, -- default component
	1, -- default section
	3); -- highest priority

INSERT INTO Binarypackage (sourcepackagerelease, binarypackagename, 
version, shortdesc, description, build, binpackageformat, component, 
section, priority) 
	VALUES (
(SELECT id from Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where name = 'mozilla-thunderbird')),
(SELECT id from Binarypackagename WHERE name = 'mozilla-thunderbird'), 
'1.5', 'Mozilla Thunderbird 1.5', 'some text', 
	1, -- hardcoded ?? use query instead
	1, -- DEB ?
	1, -- default component
	1, -- default section
	3); -- highest priority

INSERT INTO Binarypackage (sourcepackagerelease, binarypackagename, 
version, shortdesc, description, build, binpackageformat, component, 
section, priority) 
	VALUES (
(SELECT id from Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where name = 'python-twisted')),
(SELECT id from Binarypackagename WHERE name = 'python-twisted'), 
'1.3', 'Python Twisted 1.3', 'some text', 
	1, -- hardcoded ?? use query instead
	1, -- DEB ?
	1, -- default component
	1, -- default section
	3); -- highest priority

INSERT INTO Binarypackage (sourcepackagerelease, binarypackagename, 
version, shortdesc, description, build, binpackageformat, component, 
section, priority) 
	VALUES (
(SELECT id from Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where name = 'bugzilla')),
(SELECT id from Binarypackagename WHERE name = 'bugzilla'), 
'2.18', 'Bugzilla 2.18', 'some text', 
	1, -- hardcoded ?? use query instead
	1, -- DEB ?
	1, -- default component
	1, -- default section
	3); -- highest priority

INSERT INTO Binarypackage (sourcepackagerelease, binarypackagename, 
version, shortdesc, description, build, binpackageformat, component, 
section, priority) 
	VALUES (
(SELECT id from Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where name = 'arch')),
(SELECT id from Binarypackagename WHERE name = 'arch'), 
'1.0', 'ARCH 1.0', 'some text', 
	1, -- hardcoded ?? use query instead
	1, -- DEB ?
	1, -- default component
	1, -- default section
	3); -- highest priority

INSERT INTO Binarypackage (sourcepackagerelease, binarypackagename, 
version, shortdesc, description, build, binpackageformat, component, 
section, priority) 
	VALUES (
(SELECT id from Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where name = 'kiwi2')),
(SELECT id from Binarypackagename WHERE name = 'kiwi'), 
'2.0', 'Python Kiwi 2.0', 'some text', 
	1, -- hardcoded ?? use query instead
	1, -- DEB ?
	1, -- default component
	1, -- default section
	3); -- highest priority

INSERT INTO Binarypackage (sourcepackagerelease, binarypackagename, 
version, shortdesc, description, build, binpackageformat, component, 
section, priority) 
	VALUES (
(SELECT id from Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where name = 'plone')),
(SELECT id from Binarypackagename WHERE name = 'plone'), 
'1.0', 'Plone 1.0', 'some text', 
	1, -- hardcoded ?? use query instead
	1, -- DEB ?
	1, -- default component
	1, -- default section
	3); -- highest priority

-- Packagepublishing

INSERT INTO Packagepublishing (binarypackage, distroarchrelease, component, 
	section, priority) 
	VALUES
	((SELECT id FROM Binarypackage where binarypackagename = 
	  (SELECT id FROM Binarypackagename where name = 'mozilla-firefox')
	),
	(SELECT id FROM Distroarchrelease WHERE architecturetag = 
	   'warty--x86--devel--0'),
	1, -- default_component
	1, -- default_section
	3); -- ???

INSERT INTO Packagepublishing (binarypackage, distroarchrelease, component, 
	section, priority) 
	VALUES
	((SELECT id FROM Binarypackage where binarypackagename = 
	  (SELECT id FROM Binarypackagename where name = 
	     'mozilla-thunderbird')
	),
	(SELECT id FROM Distroarchrelease WHERE architecturetag = 
	   'warty--x86--devel--0'),
	1, -- default_component
	1, -- default_section
	3); -- ???

INSERT INTO Packagepublishing (binarypackage, distroarchrelease, component, 
	section, priority) 
	VALUES
	((SELECT id FROM Binarypackage where binarypackagename = 
	  (SELECT id FROM Binarypackagename where name = 'python-twisted')
	),
	(SELECT id FROM Distroarchrelease WHERE architecturetag = 
	   'warty--x86--devel--0'),
	1, -- default_component
	1, -- default_section
	3); -- ???

INSERT INTO Packagepublishing (binarypackage, distroarchrelease, component, 
	section, priority) 
	VALUES
	((SELECT id FROM Binarypackage where binarypackagename = 
	  (SELECT id FROM Binarypackagename where name = 'kiwi')
	),
	(SELECT id FROM Distroarchrelease WHERE architecturetag = 
           'warty--x86--devel--0'),
	1, -- default_component
	1, -- default_section
	3); -- ???


--SourcePackageUpload


INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'warty'),
        (SELECT id FROM Sourcepackagerelease WHERE 
	 sourcepackage = (SELECT id from Sourcepackage where name = 'plone')),
	1);
INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'warty'),
        (SELECT id FROM Sourcepackagerelease WHERE 
	 sourcepackage = (SELECT id from Sourcepackage where name = 'kiwi2')),
	1);
INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'warty'),
        (SELECT id FROM Sourcepackagerelease WHERE 
	 sourcepackage = (SELECT id from Sourcepackage where name = 'mozilla-firefox') and version='0.9.0-6'),
	6);
INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'warty'),
        (SELECT id FROM Sourcepackagerelease WHERE 
	 sourcepackage = (SELECT id from Sourcepackage where name = 'mozilla-firefox') and version='0.9.0-7'),
	6);
INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'warty'),
        (SELECT id FROM Sourcepackagerelease WHERE 
	 sourcepackage = (SELECT id from Sourcepackage where name = 'mozilla-firefox') and version='0.9.0-8'),
	6);
INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'warty'),
        (SELECT id FROM Sourcepackagerelease WHERE 
	 sourcepackage = (SELECT id from Sourcepackage where name = 'mozilla-firefox') and version='0.9.0-9'),
	4);
INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'warty'),
        (SELECT id FROM Sourcepackagerelease WHERE 
	 sourcepackage = (SELECT id from Sourcepackage where name = 'mozilla-firefox') and version='0.9.1-1'),
	1);
INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'warty'),
        (SELECT id FROM Sourcepackagerelease WHERE 
	 sourcepackage = (SELECT id from Sourcepackage where name = 'mozilla-thunderbird')),
	1);
INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'hoary'),
        (SELECT id FROM Sourcepackagerelease WHERE 
	 sourcepackage = (SELECT id from Sourcepackage where name = 'python-twisted')),
	1);
INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'hoary'),
        (SELECT id FROM Sourcepackagerelease WHERE 
	 sourcepackage = (SELECT id from Sourcepackage where name = 'kiwi2')),
	1);
INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'hoary'),
        (SELECT id FROM Sourcepackagerelease WHERE 
	sourcepackage = (SELECT id from Sourcepackage where name = 'bugzilla')),
	1);

INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'grumpy'),
        (SELECT id FROM Sourcepackagerelease WHERE 
	sourcepackage = (SELECT id from Sourcepackage where name = 'bugzilla')),
	1);

INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'grumpy'),
        (SELECT id FROM Sourcepackagerelease WHERE 
	sourcepackage = (SELECT id from Sourcepackage where name = 'arch')),
	1);
