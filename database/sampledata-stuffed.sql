/*
   LAUNCHPAD SAMPLE DATA
   
   This is some sample data for the launchpad system.  This requires the default
   data to be inserted first.
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
	values ('ubuntu', 'Ubuntu Distribution', 
	'Ubuntu Distribution introducing new concept of Linux Distribution', 
	'domain', 1);

INSERT INTO Distribution (name, title, description, domainname, owner) 
	values ('redhat', 'Redhat Advanced Server', 'some text', 'domain', 1);

INSERT INTO Distribution (name, title, description, domainname, owner) 
	values ('debian', 'Debian Crazy-Unstable', 'text ...', 'domain', 1);

INSERT INTO Distribution (name, title, description, domainname, owner) 
	values ('gentoo', 'The Gentoo bits', 'another ...', 'domain', 1);

INSERT INTO Distribution (name, title, description, domainname, owner) 
	values ('porkypigpolka', 'Porky Pig Polka Distribution', 
	'Porky Pig Distribution based on SPORK (jblack newest work)',
	'domain', 1);



-- Distrorelease
INSERT INTO Distrorelease (name, title, description, distribution, version, 
	components, sections, releasestate, datereleased, owner) 
	values 
	('warty', 'Warty', 
	'The Warty Release of Ubuntu Distribution, the first stable release', 
	1, 'PONG', 1, 1, 0, '2004-08-25', 1);

INSERT INTO Distrorelease (name, title, description, distribution, version, 
	components, sections, releasestate, datereleased, owner) 
	values 
	('6.0', 'Six Six Six', 'some text', 2, '12321.XX', 1, 1, 0,
	'2004-08-25', 1);

INSERT INTO Distrorelease (name, title, description, distribution, version, 
	components, sections, releasestate, datereleased, owner) 
	values ('hoary', 'Hoary', 'Hoary Crazy-Unstable Branch from Ubuntu', 
	1, '0.0.1', 
	1, 1, 0, '2004-08-25', 1);

INSERT INTO Distrorelease (name, title, description, distribution, version, 
	components, sections, releasestate, datereleased, owner) 
	values ('7.0', 'Seven', 'another ...', 2, 'ACK ACK', 1, 1, 0, 
	'2004-08-25', 1);

INSERT INTO Distrorelease (name, title, description, distribution, version, 
	components, sections, releasestate, datereleased, owner) 
	values ('grumpy', 'G-R-U-M-P-Y', 'does it really exists ???', 1, 
	'-1e+15', 
	1, 1, 0, '2004-08-25', 1);

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

/*
    Duplicate? Remove

 -- ProcessorFamily
INSERT INTO ProcessorFamily (name, title, description, owner) 
VALUES ('x86', 'Intel 386 compatible chips', 'Bring back the 8086!', 
         (SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'));
 
 -- Processor
INSERT INTO Processor (family, name, title, description, owner)
VALUES ((SELECT id FROM ProcessorFamily WHERE name = 'x86'),
         '386', 'Intel 386', 'Intel 386 and its many derivatives and clones, the basic 32-bit chip in the x86 family',
        (SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'));
*/
 
 -- DistroArchRelease
INSERT INTO DistroArchRelease (distrorelease, processorfamily, architecturetag, owner)
VALUES ((SELECT id FROM DistroRelease WHERE name = 'warty'),
         (SELECT id FROM ProcessorFamily WHERE name = 'x86'),
	'warty--x86--devel--0',
 	(SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'));
  

 -- Build
INSERT INTO Build (processor, distroarchrelease, datecreated, buildstate)
VALUES ((SELECT id FROM Processor WHERE name = '386'),
 	1, -- warty--x86--devel--0
        timestamp '2004-06-28 00:00', 1);

INSERT INTO Build (processor, distroarchrelease, datecreated, buildstate)
VALUES ((SELECT id FROM Processor WHERE name = '386'),
 	1, -- warty--x86--devel--0
        timestamp '2004-07-29 00:00', 1);

INSERT INTO Build (processor, distroarchrelease, datecreated, buildstate)
VALUES ((SELECT id FROM Processor WHERE name = '386'),
 	1, -- warty--x86--devel--0
        timestamp '2004-05-29 00:00', 1);

INSERT INTO Build (processor, distroarchrelease, datecreated, buildstate)
VALUES ((SELECT id FROM Processor WHERE name = '386'),
 	1, -- warty--x86--devel--0
        timestamp '2004-05-29 00:00', 1);

INSERT INTO Build (processor, distroarchrelease, datecreated, buildstate)
VALUES ((SELECT id FROM Processor WHERE name = '386'),
 	1, -- warty--x86--devel--0
        timestamp '2004-06-29 00:00', 1);

INSERT INTO Build (processor, distroarchrelease, datecreated, buildstate)
VALUES ((SELECT id FROM Processor WHERE name = '386'),
 	1, -- warty--x86--devel--0
        timestamp '2004-03-29 00:00', 1);

INSERT INTO Build (processor, distroarchrelease, datecreated, buildstate)
VALUES ((SELECT id FROM Processor WHERE name = '386'),
 	1, -- warty--x86--devel--0
        timestamp '2004-06-23 00:00', 1);


-- BinarypackageName
INSERT INTO BinarypackageName (name) values ('mozilla-firefox');
INSERT INTO BinarypackageName (name) values ('mozilla-thunderbird');
INSERT INTO BinarypackageName (name) values ('python-twisted');
INSERT INTO BinarypackageName (name) values ('bugzilla');
INSERT INTO BinarypackageName (name) values ('arch');
INSERT INTO BinarypackageName (name) values ('kiwi');
INSERT INTO BinarypackageName (name) values ('plone');

-- Binarypackage
INSERT INTO Binarypackage (binarypackagename, shortdesc, description, sourcepackagerelease, version, build, binpackageformat, component, section) values ((SELECT id FROM BinarypackageName WHERE name = 'mozilla-firefox'), 'Mozilla Firefox', 'The Mozilla Firefox web browser', (SELECT SourcepackageRelease.id FROM SourcepackageRelease, Sourcepackage WHERE SourcepackageRelease.sourcepackage = Sourcepackage.id AND Sourcepackage.name = 'mozilla-firefox'), '0.9.0-1', 1, 1, 1, 1);
INSERT INTO Binarypackage (binarypackagename, shortdesc, description, sourcepackagerelease, version, build, binpackageformat, component, section) values ((SELECT id FROM BinarypackageName WHERE name = 'mozilla-thunderbird'), 'Mozilla Thunderbird', 'The Mozilla Thunderbird mail client', (SELECT SourcepackageRelease.id FROM SourcepackageRelease, Sourcepackage WHERE SourcepackageRelease.sourcepackage = Sourcepackage.id AND Sourcepackage.name = 'mozilla-thunderbird'), '0.9.1-2', 1, 1, 1, 1);
INSERT INTO Binarypackage (binarypackagename, shortdesc, description, sourcepackagerelease, version, build, binpackageformat, component, section) values ((SELECT id FROM BinarypackageName WHERE name = 'python-twisted'), 'Twisted', 'Twisted is an asynchronous networking library for Python.  It rocks.', (SELECT SourcepackageRelease.id FROM SourcePackageRelease, SourcePackage WHERE SourcepackageRelease.sourcepackage = Sourcepackage.id AND Sourcepackage.name = 'python-twisted'), '0.9.1-3', 1, 1, 1, 1);
INSERT INTO Binarypackage (binarypackagename, shortdesc, description, sourcepackagerelease, version, build, binpackageformat, component, section) values ((SELECT id FROM BinarypackageName WHERE name = 'bugzilla'), 'Bugzilla bug tracking system', 'Whee!', (SELECT SourcepackageRelease.id FROM SourcepackageRelease, Sourcepackage WHERE SourcepackageRelease.sourcepackage = Sourcepackage.id AND Sourcepackage.name = 'bugzilla'), '0.9.1-4', 1, 1, 1, 1);
INSERT INTO Binarypackage (binarypackagename, shortdesc, description, sourcepackagerelease, version, build, binpackageformat, component, section) values ((SELECT id FROM BinarypackageName WHERE name = 'arch'), 'Foo!', 'Bar!', (SELECT SourcepackageRelease.id FROM SourcepackageRelease, Sourcepackage WHERE SourcepackageRelease.sourcepackage = Sourcepackage.id AND Sourcepackage.name = 'arch'), '0.9.1-5', 1, 1, 1, 1);
INSERT INTO Binarypackage (binarypackagename, shortdesc, description, sourcepackagerelease, version, build, binpackageformat, component, section) values ((SELECT id FROM BinarypackageName WHERE name = 'kiwi'), 'Hello?', 'Is this thing on?', (SELECT SourcepackageRelease.id FROM SourcepackageRelease, Sourcepackage WHERE SourcepackageRelease.sourcepackage = Sourcepackage.id AND Sourcepackage.name = 'kiwi'), '0.9.1-6', 1, 1, 1, 1);
INSERT INTO Binarypackage (binarypackagename, shortdesc, description, sourcepackagerelease, version, build, binpackageformat, component, section) values ((SELECT id FROM BinarypackageName WHERE name = 'plone'), 'Plone', 'Zope 2 + love == Plone', (SELECT SourcepackageRelease.id FROM SourcepackageRelease, Sourcepackage WHERE SourcepackageRelease.sourcepackage = Sourcepackage.id AND Sourcepackage.name = 'plone'), '0.9.1-7', 1, 1, 1, 1);
INSERT INTO Binarypackage (binarypackagename, shortdesc, description, sourcepackagerelease, version, build, binpackageformat, component, section) values ((SELECT id FROM BinarypackageName WHERE name = 'mozilla-firefox'), 'Mozilla Firefox', 'The Mozilla Firefox web browser', (SELECT SourcepackageRelease.id FROM SourcepackageRelease, Sourcepackage WHERE SourcepackageRelease.sourcepackage = Sourcepackage.id AND Sourcepackage.name = 'mozilla-firefox'), '0.9.1-1', 1, 1, 1, 1);
 
-- PackagePublishing

INSERT INTO PackagePublishing (binarypackage, distroarchrelease, component, section, priority) 
VALUES ((SELECT id FROM Binarypackage WHERE version = '0.9.1-1'),
 	(SELECT id FROM DistroArchRelease WHERE architecturetag = 'warty--x86--devel--0'),
 	1, -- FIXME
 	1, -- FIXME
 	3 -- Standard
 	);

INSERT INTO PackagePublishing (binarypackage, distroarchrelease, component, section, priority) 
VALUES ((SELECT id FROM Binarypackage WHERE version = '0.9.1-2'),
 	(SELECT id FROM DistroArchRelease WHERE architecturetag = 'warty--x86--devel--0'),
 	1, -- FIXME
 	1, -- FIXME
 	3 -- Standard
 	);

INSERT INTO PackagePublishing (binarypackage, distroarchrelease, component, section, priority) 
VALUES ((SELECT id FROM Binarypackage WHERE version = '0.9.1-3'),
 	(SELECT id FROM DistroArchRelease WHERE architecturetag = 'warty--x86--devel--0'),
 	1, -- FIXME
 	1, -- FIXME
 	3 -- Standard
 	);

INSERT INTO PackagePublishing (binarypackage, distroarchrelease, component, section, priority) 
VALUES ((SELECT id FROM Binarypackage WHERE version = '0.9.1-4'),
 	(SELECT id FROM DistroArchRelease WHERE architecturetag = 'warty--x86--devel--0'),
 	1, -- FIXME
 	1, -- FIXME
 	3 -- Standard
 	);

INSERT INTO PackagePublishing (binarypackage, distroarchrelease, component, section, priority) 
VALUES ((SELECT id FROM Binarypackage WHERE version = '0.9.1-5'),
 	(SELECT id FROM DistroArchRelease WHERE architecturetag = 'warty--x86--devel--0'),
 	1, -- FIXME
 	1, -- FIXME
 	3 -- Standard
 	);

INSERT INTO PackagePublishing (binarypackage, distroarchrelease, component, section, priority) 
VALUES ((SELECT id FROM Binarypackage WHERE version = '0.9.1-6'),
 	(SELECT id FROM DistroArchRelease WHERE architecturetag = 'warty--x86--devel--0'),
 	1, -- FIXME
 	1, -- FIXME
 	3 -- Standard
 	);

INSERT INTO PackagePublishing (binarypackage, distroarchrelease, component, section, priority) 
VALUES ((SELECT id FROM Binarypackage WHERE version = '0.9.1-7'),
 	(SELECT id FROM DistroArchRelease WHERE architecturetag = 'warty--x86--devel--0'),
 	1, -- FIXME
 	1, -- FIXME
 	3 -- Standard
 	);
 
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
	 sourcepackage = (SELECT id from Sourcepackage where name = 'mozilla-firefox')),
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

INSERT INTO Bug (name, title, shortdesc, description, owner, communityscore,
communitytimestamp, activityscore, activitytimestamp, hits,
hitstimestamp)
VALUES ('bob', 'An odd problem', 'Something strange is wrong somewhere',
'Something strange is wrong somewhere',
(SELECT id FROM Person WHERE displayname='Mark Shuttleworth'),
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
    (SELECT id FROM Sourcepackage WHERE name='mozilla-firefox'),
    2, 4, 2,
    (SELECT id FROM BinaryPackage WHERE version='0.8' 
        AND binarypackagename = (
            SELECT id FROM BinarypackageName WHERE name='mozilla-firefox'
            )
    )
);
