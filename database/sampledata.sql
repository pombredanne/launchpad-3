/*
   LAUNCHPAD SAMPLE DATA
   
   This is some sample data for the launchpad system.  This requires the default
   data to be inserted first.
*/

/* 
 Sample data for Soyuz
*/

-- Schema
INSERT INTO schema (name, title, description, owner, extensible) VALUES('Mark schema', 'TITLE', 'description', (Select id from Person where presentationname = 'Mark Shuttleworth'), true);
INSERT INTO Schema (name, title, description, owner, extensible) values('schema', 'SCHEMA', 'description', (Select id from Person where presentationname = 'Mark Shuttleworth'), true);
INSERT INTO Schema (name, title, description, owner, extensible) values('trema', 'XCHEMA', 'description', (Select id from Person where presentationname = 'Mark Shuttleworth'), true);
INSERT INTO Schema (name, title, description, owner, extensible) values('enema', 'ENHEMA', 'description', (Select id from Person where presentationname = 'Mark Shuttleworth'), true);

-- Distribution
INSERT INTO Distribution (name, title, description, domainname, owner) values ('ubuntu', 'Ubuntu Distribution', 'text ...', 'domain', 1);
INSERT INTO Distribution (name, title, description, domainname, owner) values ('redhat', 'Redhat Advanced Server', 'some text', 'domain', 1);
INSERT INTO Distribution (name, title, description, domainname, owner) values ('debian', 'Debian Crazy-Unstable', 'text ...', 'domain', 1);
INSERT INTO Distribution (name, title, description, domainname, owner) values ('gentoo', 'The Gentoo bits', 'another ...', 'domain', 1);
INSERT INTO Distribution (name, title, description, domainname, owner) values ('porkypigpolka', 'Porky Pig Polka Swine-oriented Distribution', 'blabla', 'domain', 1);

INSERT INTO Distrorelease (name, title, description, distribution, version, components, sections, releasestate, owner) values ('warty', 'Warty', 'text ...', 1, 'PONG', 1, 1, 0, 1);
INSERT INTO Distrorelease (name, title, description, distribution, version, components, sections, releasestate, owner) values ('6.0', 'Six Six Six', 'some text', 2, '12321.XX', 1, 1, 0, 1);
INSERT INTO Distrorelease (name, title, description, distribution, version, components, sections, releasestate, owner) values ('hoary', 'Hoary Crazy-Unstable', 'text ...', 1, 'EWEpp##', 1, 1, 0, 1);
INSERT INTO Distrorelease (name, title, description, distribution, version, components, sections, releasestate, owner) values ('7.0', 'Seven', 'another ...', 2, 'ACK ACK', 1, 1, 0, 1);
INSERT INTO Distrorelease (name, title, description, distribution, version, components, sections, releasestate, owner) values ('grumpy', 'G-R-U-M-P-Y', 'blabla', 1, 'PINKPY POLLY', 1, 1, 0, 1);


-- Binarypackage
INSERT INTO Binarypackage (name, title, description) values ('mozilla-firefox-0.8', 'Mozilla Firefox', 'some text');
INSERT INTO Binarypackage (name, title, description) values ('mozilla-thunderbird-1.5', 'Mozilla Thunderbird', 'text');
INSERT INTO Binarypackage (name, title, description) values ('mozilla-browser-1.4', 'Mozilla Browser', 'text and so');
INSERT INTO Binarypackage (name, title, description) values ('emacs21-1.6', 'Emacs21 Programming Editor', 'fofofof');
INSERT INTO Binarypackage (name, title, description) values ('bash-1.8', 'Bash', 'another data');

 
 -- ProcessorFamily
INSERT INTO ProcessorFamily (name, title, description, owner) 
VALUES ('x86', 'Intel 386 compatible chips', 'Bring back the 8086!', 
         (SELECT id FROM Person WHERE presentationname = 'Mark Shuttleworth'));
 
 -- Processor
INSERT INTO Processor (family, name, title, description, owner)
VALUES ((SELECT id FROM ProcessorFamily WHERE name = 'x86'),
         '386', 'Intel 386', 'Intel 386 and its many derivatives and clones, the basic 32-bit chip in the x86 family',
        (SELECT id FROM Person WHERE presentationname = 'Mark Shuttleworth'));
 
 -- BinarypackageBuild
INSERT INTO BinarypackageBuild (sourcepackagerelease, binarypackage, processor,
                                 binpackageformat, version, datebuilt)
VALUES ((SELECT id FROM SourcepackageRelease WHERE version = '0.9.1-1'),
         (SELECT id FROM Binarypackage WHERE name = 'mozilla-firefox-0.8'),
 	(SELECT id FROM Processor WHERE name = '386'),
 	1, -- DEB
 	'0.9.1-1',
        timestamp '2004-06-29 00:00');
 
 -- DistroArchRelease
INSERT INTO DistroArchRelease (distrorelease, processorfamily, architecturetag, owner)
VALUES ((SELECT id FROM DistroRelease WHERE name = 'warty'),
         (SELECT id FROM ProcessorFamily WHERE name = 'x86'),
	'Foo',
 	(SELECT id FROM Person WHERE presentationname = 'Mark Shuttleworth'));
 
 -- Schema
INSERT INTO Schema (name, title, description, owner)
VALUES ('blah', 'blah', 'blah',
         (SELECT id FROM Person WHERE presentationname = 'Mark Shuttleworth'));
 
 -- Label
INSERT INTO Label (schema, name, title, description)
VALUES ((SELECT id FROM Schema WHERE name = 'blah'),
         'blah', 'blah', 'blah');
 
-- BinarypackageUpload
INSERT INTO BinarypackageUpload (binarypackagebuild, distroarchrelease, uploadstatus, component, section, priority) 
VALUES ((SELECT id FROM BinarypackageBuild WHERE version = '0.9.1-1'),
 	(SELECT id FROM DistroArchRelease WHERE architecturetag = 'Foo'),
 	4, -- Published
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



