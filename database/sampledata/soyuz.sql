/*
   SOYUZ SAMPLE DATA
   
   This is some sample data for the Soyuz App components.  
   This requires the default data to be inserted first.
*/

/* 
 Sample data for Soyuz
*/


-- Component
INSERT INTO Component (name) VALUES ('default_component');

-- Section

INSERT INTO Section (name) VALUES ('default_section');

-- Schema
INSERT INTO schema (name, title, description, owner, extensible) VALUES
	('Mark schema', 'TITLE', 'description', 
	(SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'), 
	TRUE);

INSERT INTO Schema (name, title, description, owner, extensible) VALUES 
	('schema', 'SCHEMA', 'description', 
	(SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'), 
	TRUE);

INSERT INTO Schema (name, title, description, owner, extensible) VALUES
	('trema', 'XCHEMA', 'description', 
	(SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'), 
	TRUE);

INSERT INTO Schema (name, title, description, owner, extensible) VALUES 
	('enema', 'ENHEMA', 'description', 
	(SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'), 
	TRUE);


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


/*
--CodeRelease
INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcePackageRelease WHERE 
	dateuploaded = timestamp '2004-06-29 00:00'),
 (SELECT id FROM Manifest WHERE datecreated = timestamp '2004-06-29 00:00'));

INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcePackageRelease WHERE 
	dateuploaded = timestamp '2004-06-30 00:00'),
 (SELECT id FROM Manifest WHERE datecreated = timestamp '2004-06-30 00:00'));

INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcePackageRelease WHERE 
	dateuploaded = timestamp '2004-07-01 00:00'),
 (SELECT id FROM Manifest WHERE datecreated = timestamp '2004-07-01 00:00'));

INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcePackageRelease WHERE 
	dateuploaded = timestamp '2004-07-02 00:00'),
 (SELECT id FROM Manifest WHERE datecreated = timestamp '2004-07-02 00:00'));

INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcePackageRelease WHERE 
	dateuploaded = timestamp '2004-07-03 00:00'),
 (SELECT id FROM Manifest WHERE datecreated = timestamp '2004-07-03 00:00'));

INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcePackageRelease WHERE 
	dateuploaded = timestamp '2004-07-04 00:00'),
 (SELECT id FROM Manifest WHERE datecreated = timestamp '2004-07-04 00:00'));

INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcePackageRelease WHERE 
	dateuploaded = timestamp '2004-07-05 00:00'),
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

*/

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
         '386', 'Intel 386', 
	'Intel 386 and its many derivatives and clones, the basic 32-bit chip in the x86 family',
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
	1, 1, 3, 1);

INSERT INTO Distrorelease (name, title, description, distribution, version, 
	datereleased, components, sections, releasestate, owner) 
	VALUES ('six', 'Six Six Six', 
	'some text to describe the whole 666 release of RH', 
	(SELECT id FROM Distribution WHERE name = 'redhat'), 
	'6.0.1', 
	'2004-03-21',
	1, 1, 4, 8);

INSERT INTO Distrorelease (name, title, description, distribution, version, 
	datereleased, components, sections, releasestate, parentrelease, 
	owner) 
	VALUES ('hoary', 'Hoary Crazy-Unstable', 
	'Hoary is the next release of Ubuntu', 
	(SELECT id FROM Distribution WHERE name = 'ubuntu'), 
	'0.0.1',
	'2004-08-25', 
	1, 1, 2, 
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
	1, 1, 3, 
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
	1, 1, 1, 
	(SELECT id FROM Distrorelease WHERE name = 'warty'),
	1);

INSERT INTO Distrorelease (name, title, description, distribution, version, 
	datereleased, components, sections, releasestate, owner) 
	VALUES ('woody', 'WOODY', 
	'WOODY is the current stable verison of Debian GNU/Linux', 
	(SELECT id FROM Distribution WHERE name = 'debian'),
	'3.0', 
	'2003-01-01',
	1, 1, 4, 2);

INSERT INTO Distrorelease (name, title, description, distribution, version, 
	datereleased, components, sections, releasestate, parentrelease,
	owner) 
	VALUES ('sarge', 'Sarge', 
	'Sarge is the FROZEN unstable version of Debian GNU/Linux.', 
	(SELECT id FROM Distribution WHERE name = 'debian'),
	'3.1', 
	'2004-09-29',
	1, 1, 3, 
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
	1, 1, 1, 
	(SELECT id FROM Distrorelease WHERE name = 'woody'),
	6);

--Distroreleaserole Persons ?!

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

-- Distroreleaserole Teams ?!

INSERT INTO Distroreleaserole (person, distrorelease, role) 
	VALUES(
	(SELECT id from Person WHERE displayname = 'Warty Security Team'),
	(SELECT id from Distrorelease WHERE name = 'warty'),
	4);

INSERT INTO Distroreleaserole (person, distrorelease, role) 
	VALUES(
	(SELECT id from Person WHERE displayname = 'Warty Gnome Team'),
	(SELECT id from Distrorelease WHERE name = 'warty'),
	4);

INSERT INTO Distroreleaserole (person, distrorelease, role) 
	VALUES(
	(SELECT id from Person WHERE displayname = 'Hoary Gnome Team'),
	(SELECT id from Distrorelease WHERE name = 'hoary'),
	4);


--Distributionrole Persons ?!

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

-- DistributionRole Teams ?!

INSERT INTO Distributionrole (person, distribution, role) 
	VALUES(
	(SELECT id from Person WHERE displayname = 'Ubuntu Team'),
	(SELECT id from Distribution WHERE name = 'ubuntu'),
	3);

INSERT INTO Distributionrole (person, distribution, role) 
	VALUES(
	(SELECT id from Person WHERE displayname = 'Ubuntu Gnome Team'),
	(SELECT id from Distribution WHERE name = 'ubuntu'),
	3);


--DistroArchrelease
INSERT INTO Distroarchrelease(distrorelease, processorfamily, architecturetag, 
	owner) VALUES 
	((SELECT id FROM Distrorelease where name = 'warty'), 
	(SELECT id from Processorfamily where name = 'x86'), 
	'i386', 
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

