/*
   SOYUZ SAMPLE DATA
   
   This is some sample data for the Soyuz App components.  
   This requires the default data to be inserted first.
*/

/* 
 Sample data for Soyuz
*/
-- Person
INSERT INTO Person ( displayname, givenname, familyname ) VALUES 
	( 'Dave Miller', 'Dave', 'Miller' );                  -- 2
INSERT INTO Person ( displayname, givenname, familyname ) VALUES 
	( 'Colin Watson', 'Colin', 'Watson' );                 -- 3
INSERT INTO Person ( displayname, givenname, familyname ) VALUES 
	( 'Scott James Remnant', 'Scott James', 'Remnant' );   -- 4
INSERT INTO Person ( displayname, givenname, familyname ) VALUES 
	( 'Jeff Waugh', 'Jeff', 'Waugh' );                     -- 6
INSERT INTO Person ( displayname, givenname, familyname ) VALUES 
	( 'Andrew Bennetts', 'Andrew', 'Bennetts' );           -- 7
INSERT INTO Person ( displayname, givenname, familyname ) VALUES 
	( 'James Blackwell', 'James', 'Blackwell' );           -- 8
INSERT INTO Person ( displayname, givenname, familyname ) VALUES 
	( 'Christian Reis', 'Christian', 'Reis' );             -- 9
INSERT INTO Person ( displayname, givenname, familyname ) VALUES 
	( 'Alexander Limi', 'Alexander', 'Limi' );             -- 10
INSERT INTO Person ( displayname, givenname, familyname ) VALUES 
	( 'Steve Alexander', 'Steve', 'Alexander' );           -- 11

-- Insert some Teams in Person following FOAF approach

INSERT INTO Person (teamowner, teamdescription) VALUES
	((SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
	'Ubuntu Security Team');

INSERT INTO Person (teamowner, teamdescription) VALUES
	((SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
	'Ubuntu Gnome Team');

INSERT INTO Person (teamowner, teamdescription) VALUES
	((SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
	'Warty Gnome Team');

INSERT INTO Person (teamowner, teamdescription) VALUES
	((SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
	'Warty Security Team');

INSERT INTO Person (teamowner, teamdescription) VALUES
	((SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
	'Hoary Gnome Team');

-- EmailAdress

INSERT INTO EmailAddress (email, person, status) VALUES
	('steve.alexander@ubuntulinux.com',
	(SELECT id FROM Person WHERE displayname = 'Steve Alexander'),
	1 -- NEW (or 2 = VALIDATED and 3 = OLD) 
	);
INSERT INTO EmailAddress (email, person, status) VALUES
	('colin.watson@ubuntulinux.com',
	(SELECT id FROM Person WHERE displayname = 'Colin Watson'),
	1 -- NEW (or 2 = VALIDATED and 3 = OLD) 
	);
INSERT INTO EmailAddress (email, person, status) VALUES
	('scott.james.remnant@ubuntulinux.com',
	(SELECT id FROM Person WHERE displayname = 'Scott James Remnant'),
	1 -- NEW (or 2 = VALIDATED and 3 = OLD) 
	);
INSERT INTO EmailAddress (email, person, status) VALUES
	('andrew.bennetts@ubuntulinux.com',
	(SELECT id FROM Person WHERE displayname = 'Andrew Bennetts'),
	1 -- NEW (or 2 = VALIDATED and 3 = OLD) 
	);
INSERT INTO EmailAddress (email, person, status) VALUES
	('james.blackwell@ubuntulinux.com',
	(SELECT id FROM Person WHERE displayname = 'James Blackwell'),
	1 -- NEW (or 2 = VALIDATED and 3 = OLD) 
	);
INSERT INTO EmailAddress (email, person, status) VALUES
	('christian.reis@ubuntulinux.com',
	(SELECT id FROM Person WHERE displayname = 'Christian Reis'),
	1 -- NEW (or 2 = VALIDATED and 3 = OLD) 
	);
INSERT INTO EmailAddress (email, person, status) VALUES
	('jeff.waugh@ubuntulinux.com',
	(SELECT id FROM Person WHERE displayname = 'Jeff Waugh'),
	1 -- NEW (or 2 = VALIDATED and 3 = OLD) 
	);
INSERT INTO EmailAddress (email, person, status) VALUES
	('dave.miller@ubuntulinux.com',
	(SELECT id FROM Person WHERE displayname = 'Dave Miller'),
	1 -- NEW (or 2 = VALIDATED and 3 = OLD) 
	);


-- GPGKey

INSERT INTO GPGKey (person, keyid, fingerprint, pubkey, revoked) VALUES
	((SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
	'1024D/09F89725',
	'XVHJ OU77 IYTD 0982 FTG6 OQFC 0GF8 09PO QW45 MJ76',
	'<-- sample pubkey ??? -->',
	FALSE);
INSERT INTO GPGKey (person, keyid, fingerprint, pubkey, revoked) VALUES
	((SELECT id FROM Person WHERE displayname = 'Steve Alexander'),
	'1024D/09F89890',
	'XVHJ OU77 IYTD 0981 FTG6 OQFC 0GF8 09PO QW45 MJ76',
	'<-- sample pubkey ??? -->',
	FALSE);

INSERT INTO GPGKey (person, keyid, fingerprint, pubkey, revoked) VALUES
	((SELECT id FROM Person WHERE displayname = 'Alexander Limi'),
	'1024D/09F89321',
	'XVHJ OU77 IYTD 0983 FTG6 OQFC 0GF8 09PO QW45 MJ76',
	'<-- sample pubkey ??? -->',
	FALSE);
INSERT INTO GPGKey (person, keyid, fingerprint, pubkey, revoked) VALUES
	((SELECT id FROM Person WHERE displayname = 'James Blackwell'),
	'1024D/09F89098',
	'XVHJ OU77 IYTD 0984 FTG6 OQFC 0GF8 09PO QW45 MJ76',
	'<-- sample pubkey ??? -->',
	FALSE);
INSERT INTO GPGKey (person, keyid, fingerprint, pubkey, revoked) VALUES
	((SELECT id FROM Person WHERE displayname = 'Christian Reis'),
	'1024D/09F89123',
	'XVHJ OU77 IYTD 0985 FTG6 OQFC 0GF8 09PO QW45 MJ76',
	'<-- sample pubkey ??? -->',
	FALSE);
INSERT INTO GPGKey (person, keyid, fingerprint, pubkey, revoked) VALUES
	((SELECT id FROM Person WHERE displayname = 'Colin Watson'),
	'1024D/09F89124',
	'XVHJ OU77 IYTA 0985 FTG6 OQFC 0GF8 09PO QW45 MJ76',
	'<-- sample pubkey ??? -->',
	FALSE);
INSERT INTO GPGKey (person, keyid, fingerprint, pubkey, revoked) VALUES
	((SELECT id FROM Person WHERE displayname = 'Scott James Remnant'),
	'1024D/09F89125',
	'XVHJ OU77 IYTQ 0985 FTG6 OQFC 0GF8 09PO QW45 MJ76',
	'<-- sample pubkey ??? -->',
	FALSE);
INSERT INTO GPGKey (person, keyid, fingerprint, pubkey, revoked) VALUES
	((SELECT id FROM Person WHERE displayname = 'Andrew Bennetts'),
	'1024D/09F89126',
	'XVHJ OU77 IYTX 0985 FTG6 OQFC 0GF8 09PO QW45 MJ76',
	'<-- sample pubkey ??? -->',
	FALSE);
INSERT INTO GPGKey (person, keyid, fingerprint, pubkey, revoked) VALUES
	((SELECT id FROM Person WHERE displayname = 'Dave Miller'),
	'1024D/09F89127',
	'XVHJ OU77 IYTZ 0985 FTG6 OQFC 0GF8 09PO QW45 MJ76',
	'<-- sample pubkey ??? -->',
	FALSE);
INSERT INTO GPGKey (person, keyid, fingerprint, pubkey, revoked) VALUES
	((SELECT id FROM Person WHERE displayname = 'Jeff Waugh'),
	'1024D/09F89120',
	'XVHJ OU77 IYTP 0985 FTG6 OQFC 0GF8 09PO QW45 MJ76',
	'<-- sample pubkey ??? -->',
	FALSE);

-- ArchUserID
INSERT INTO ArchUserID (person, archuserid) VALUES
	((SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
	'mark.shuttleworth');
INSERT INTO ArchUserID (person, archuserid) VALUES
	((SELECT id FROM Person WHERE displayname = 'Steve Alexander'),
	'steve.alexander');
INSERT INTO ArchUserID (person, archuserid) VALUES
	((SELECT id FROM Person WHERE displayname = 'Alexander Limi'),
	'alexander.limi');
INSERT INTO ArchUserID (person, archuserid) VALUES
	((SELECT id FROM Person WHERE displayname = 'James Blackwell'),
	'james.blackwell');
INSERT INTO ArchUserID (person, archuserid) VALUES
	((SELECT id FROM Person WHERE displayname = 'Christian Reis'),
	'christian.reis');
INSERT INTO ArchUserID (person, archuserid) VALUES
	((SELECT id FROM Person WHERE displayname = 'Colin Watson'),
	'colin.watson');
INSERT INTO ArchUserID (person, archuserid) VALUES
	((SELECT id FROM Person WHERE displayname = 'Scott James Remnant'),
	'scott.james.remnant');
INSERT INTO ArchUserID (person, archuserid) VALUES
	((SELECT id FROM Person WHERE displayname = 'Andrew Bennetts'),
	'andrew.bennetts');
INSERT INTO ArchUserID (person, archuserid) VALUES
	((SELECT id FROM Person WHERE displayname = 'Dave Miller'),
	'dave.miller');
INSERT INTO ArchUserID (person, archuserid) VALUES
	((SELECT id FROM Person WHERE displayname = 'Jeff Waugh'),
	'jeff.waugh');


-- WikiName
INSERT INTO WikiName (person, wiki, wikiname) VALUES
	((SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
	'http://www.ubuntulinux.com/wiki/',
	'MarkShuttleworth');
INSERT INTO WikiName (person, wiki, wikiname) VALUES
	((SELECT id FROM Person WHERE displayname = 'Steve Alexander'),
	'http://www.ubuntulinux.com/wiki/',
	'SteveAlexander');
INSERT INTO WikiName (person, wiki, wikiname) VALUES
	((SELECT id FROM Person WHERE displayname = 'Alexander Limi'),
	'http://www.ubuntulinux.com/wiki/',
	'AlexanderLimi');
INSERT INTO WikiName (person, wiki, wikiname) VALUES
	((SELECT id FROM Person WHERE displayname = 'James Blackwell'),
	'http://www.ubuntulinux.com/wiki/',
	'JamesBlackwell');
INSERT INTO WikiName (person, wiki, wikiname) VALUES
	((SELECT id FROM Person WHERE displayname = 'Christian Reis'),
	'http://www.ubuntulinux.com/wiki/',
	'ChristianReis');
INSERT INTO WikiName (person, wiki, wikiname) VALUES
	((SELECT id FROM Person WHERE displayname = 'Colin Watson'),
	'http://www.ubuntulinux.com/wiki/',
	'ColinWatson');
INSERT INTO WikiName (person, wiki, wikiname) VALUES
	((SELECT id FROM Person WHERE displayname = 'Scott James Remnant'),
	'http://www.ubuntulinux.com/wiki/',
	'ScottJamesRemnant');
INSERT INTO WikiName (person, wiki, wikiname) VALUES
	((SELECT id FROM Person WHERE displayname = 'Andrew Bennetts'),
	'http://www.ubuntulinux.com/wiki/',
	'AndrewBennetts');
INSERT INTO WikiName (person, wiki, wikiname) VALUES
	((SELECT id FROM Person WHERE displayname = 'Dave Miller'),
	'http://www.ubuntulinux.com/wiki/',
	'DaveMiller');
INSERT INTO WikiName (person, wiki, wikiname) VALUES
	((SELECT id FROM Person WHERE displayname = 'Jeff Waugh'),
	'http://www.ubuntulinux.com/wiki/',
	'JeffWaugh');

-- JabberID
INSERT INTO JabberID (person, jabberid) VALUES
	((SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
	'markshuttleworth@jabber.org');
INSERT INTO JabberID (person, jabberid) VALUES
	((SELECT id FROM Person WHERE displayname = 'Steve Alexander'),
	'stevea@jabber.org');
INSERT INTO JabberID (person, jabberid) VALUES
	((SELECT id FROM Person WHERE displayname = 'Alexander Limi'),
	'limi@jabber.org');
INSERT INTO JabberID (person, jabberid) VALUES
	((SELECT id FROM Person WHERE displayname = 'James Blackwell'),
	'jblack@jabber.org');
INSERT INTO JabberID (person, jabberid) VALUES
	((SELECT id FROM Person WHERE displayname = 'Christian Reis'),
	'kiko@jabber.org');
INSERT INTO JabberID (person, jabberid) VALUES
	((SELECT id FROM Person WHERE displayname = 'Colin Watson'),
	'colin@jabber.org');
INSERT INTO JabberID (person, jabberid) VALUES
	((SELECT id FROM Person WHERE displayname = 'Scott James Remnant'),
	'scott@jabber.org');
INSERT INTO JabberID (person, jabberid) VALUES
	((SELECT id FROM Person WHERE displayname = 'Andrew Bennetts'),
	'spiv@jabber.org');
INSERT INTO JabberID (person, jabberid) VALUES
	((SELECT id FROM Person WHERE displayname = 'Dave Miller'),
	'justdave@jabber.org');
INSERT INTO JabberID (person, jabberid) VALUES
	((SELECT id FROM Person WHERE displayname = 'Jeff Waugh'),
	'jeff@jabber.org');

-- IrcID
INSERT INTO IrcID (person, network, nickname) VALUES
	((SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
	'irc.freenode.net',
	'mark');
INSERT INTO IrcID (person, network, nickname) VALUES
	((SELECT id FROM Person WHERE displayname = 'Steve Alexander'),
	'irc.freenode.net',
	'SteveA');
INSERT INTO IrcID (person, network, nickname) VALUES
	((SELECT id FROM Person WHERE displayname = 'Alexander Limi'),
	'irc.freenode.net',
	'limi');
INSERT INTO IrcID (person, network, nickname) VALUES
	((SELECT id FROM Person WHERE displayname = 'James Blackwell'),
	'irc.freenode.net',
	'jblack');
INSERT INTO IrcID (person, network, nickname) VALUES
	((SELECT id FROM Person WHERE displayname = 'Dave Miller'),
	'irc.freenode.net',
	'justdave');
INSERT INTO IrcID (person, network, nickname) VALUES
	((SELECT id FROM Person WHERE displayname = 'Christian Reis'),
	'irc.freenode.net',
	'kiko');
INSERT INTO IrcID (person, network, nickname) VALUES
	((SELECT id FROM Person WHERE displayname = 'Colin Watson'),
	'irc.freenode.net',
	'Kamion');
INSERT INTO IrcID (person, network, nickname) VALUES
	((SELECT id FROM Person WHERE displayname = 'Scott James Remnant'),
	'irc.freenode.net',
	'Keybuk');
INSERT INTO IrcID (person, network, nickname) VALUES
	((SELECT id FROM Person WHERE displayname = 'Jeff Waugh'),
	'irc.freenode.net',
	'jeff');

-- Membership
INSERT INTO Membership(person, team, role, status) VALUES
	((SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
	(SELECT id FROM Person WHERE teamdescription = 'Ubuntu Security Team'),
	1, -- ADMIN (2 = MEMBER)
	2); -- CURRENT (1 = PROPOSED)	

INSERT INTO Membership(person, team, role, status) VALUES
	((SELECT id FROM Person WHERE displayname = 'Steve Alexander'),
	(SELECT id FROM Person WHERE teamdescription = 'Ubuntu Security Team'),
	2, -- MEMBER
	2); -- CURRENT

INSERT INTO Membership(person, team, role, status) VALUES
	((SELECT id FROM Person WHERE displayname = 'Alexander Limi'),
	(SELECT id FROM Person WHERE teamdescription = 'Ubuntu Security Team'),
	2, -- MEMBER
	1); -- PROPOSED

INSERT INTO Membership(person, team, role, status) VALUES
	((SELECT id FROM Person WHERE displayname = 'Colin Watson'),
	(SELECT id FROM Person WHERE teamdescription = 'Ubuntu Security Team'),
	2, -- MEMBER
	1); -- PROPOSED

INSERT INTO Membership(person, team, role, status) VALUES
	((SELECT id FROM Person WHERE displayname = 'Andrew Bennetts'),
	(SELECT id FROM Person WHERE teamdescription = 'Ubuntu Security Team'),
	2, -- MEMBER
	1); -- PROPOSED

INSERT INTO Membership(person, team, role, status) VALUES
	((SELECT id FROM Person WHERE displayname = 'Dave Miller'),
	(SELECT id FROM Person WHERE teamdescription = 'Ubuntu Security Team'),
	2, -- MEMBER
	1); -- PROPOSED

INSERT INTO Membership(person, team, role, status) VALUES
	((SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
	(SELECT id FROM Person WHERE teamdescription = 'Ubuntu Gnome Team'),
	1, -- ADMIN
	2); -- CURRENT	

INSERT INTO Membership(person, team, role, status) VALUES
	((SELECT id FROM Person WHERE displayname = 'Jeff Waugh'),
	(SELECT id FROM Person WHERE teamdescription = 'Ubuntu Gnome Team'),
	2, -- MEMBER
	2); -- CURRENT	
	

-- TeamParticipation	
INSERT INTO TeamParticipation (team, person) VALUES
	((SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
	(SELECT id FROM Person WHERE teamdescription = 'Ubuntu Security Team')
	);
INSERT INTO TeamParticipation (team, person) VALUES
	((SELECT id FROM Person WHERE displayname = 'Steve Alexander'),
	(SELECT id FROM Person WHERE teamdescription = 'Ubuntu Security Team')
	);
INSERT INTO TeamParticipation (team, person) VALUES
	((SELECT id FROM Person WHERE displayname = 'Alexander Limi'),
	(SELECT id FROM Person WHERE teamdescription = 'Ubuntu Security Team')
	);
INSERT INTO TeamParticipation (team, person) VALUES
	((SELECT id FROM Person WHERE displayname = 'Colin Watson'),
	(SELECT id FROM Person WHERE teamdescription = 'Ubuntu Security Team')
	);
INSERT INTO TeamParticipation (team, person) VALUES
	((SELECT id FROM Person WHERE displayname = 'Andrew Bennetts'),
	(SELECT id FROM Person WHERE teamdescription = 'Ubuntu Security Team')
	);
INSERT INTO TeamParticipation (team, person) VALUES
	((SELECT id FROM Person WHERE displayname = 'Dave Miller'),
	(SELECT id FROM Person WHERE teamdescription = 'Ubuntu Security Team')
	);
INSERT INTO TeamParticipation (team, person) VALUES
	((SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
	(SELECT id FROM Person WHERE teamdescription = 'Ubuntu Gnome Team')
	);
INSERT INTO TeamParticipation (team, person) VALUES
	((SELECT id FROM Person WHERE displayname = 'Jeff Waugh'),
	(SELECT id FROM Person WHERE teamdescription = 'Ubuntu Gnome Team')
	);

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
-- Sourcepackagename
INSERT INTO Sourcepackagename (name)
	VALUES('mozilla-firefox'); 
INSERT INTO Sourcepackagename (name)
	VALUES('mozilla-thunderbird'); 
INSERT INTO Sourcepackagename (name)
	VALUES('python-twisted'); 
INSERT INTO Sourcepackagename (name)
	VALUES('bugzilla'); 
INSERT INTO Sourcepackagename (name)
	VALUES('arch'); 
INSERT INTO Sourcepackagename (name)
	VALUES('kiwi2'); 
INSERT INTO Sourcepackagename (name)
	VALUES('plone'); 
INSERT INTO Sourcepackagename (name)
	VALUES('evolution'); 


-- Sourcepackage
INSERT INTO Sourcepackage (maintainer, sourcepackagename, shortdesc, 
	description)
VALUES ((SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-firefox'),
	'Mozilla Firefox Web Browser', 
        'Firefox is a redesign of the Mozilla browser component, similar to Galeon, 
	K-Meleon and Camino, but written using the XUL user interface language and 
	designed to lightweight and cross-platform.');

INSERT INTO Sourcepackage (maintainer, sourcepackagename, shortdesc, 
	description)
VALUES ((SELECT id FROM Person WHERE displayname = 'Steve Alexander'),
        (SELECT id FROM Sourcepackagename WHERE name = 'mozilla-thunderbird'),
	'Mozilla Thunderbird Mail Reader', 
         'Mozilla Thunderbird is a redesign of the Mozilla mail component. 
	The goal is to produce a cross platform stand alone mail application 
	using the XUL user interface language. Mozilla Thunderbird leaves a 
	somewhat smaller memory footprint than the Mozilla suite.');

INSERT INTO Sourcepackage (maintainer, sourcepackagename, shortdesc, 
	description)
VALUES ((SELECT id FROM Person WHERE displayname = 'Andrew Bennetts'),
        (SELECT id FROM Sourcepackagename WHERE name = 'python-twisted'),
	'Python Twisted', 
         'It includes a web server, a telnet server, a multiplayer RPG engine, 
	a generic client and server for remote object access, and APIs for 
	creating new protocols.');

INSERT INTO Sourcepackage (maintainer, sourcepackagename, shortdesc, 
	description)
VALUES ((SELECT id FROM Person WHERE displayname = 'Dave Miller'),
        (SELECT id FROM Sourcepackagename WHERE name = 'bugzilla'),
	'Bugzilla', 
        'Bugzilla is a "Defect Tracking System" or "Bug-Tracking System". 
	Defect Tracking Systems allow individual or groups of developers 
	to keep track of outstanding bugs in their product effectively.');

INSERT INTO Sourcepackage (maintainer, sourcepackagename, shortdesc, 
	description)
VALUES ((SELECT id FROM Person WHERE displayname = 'James Blackwell'),
        (SELECT id FROM Sourcepackagename WHERE name = 'arch'),
	'Arch(TLA)', 
        'arch is a revision control system with features that are ideal for 
	projects characterised by widely distributed development, concurrent 
	support of multiple releases, and substantial amounts of development
	on branches. It can be a replacement for CVS and corrects many 
	mis-features of that system.');

INSERT INTO Sourcepackage (maintainer, sourcepackagename, shortdesc, 
	description)
VALUES ((SELECT id FROM Person WHERE displayname = 'Christian Reis'),
        (SELECT id FROM Sourcepackagename WHERE name = 'kiwi2'),
	'Kiwi2', 
         ' Kiwi2 consists of a set of classes and wrappers for PyGTK-2 that were 
	developed to provide a sort of framework for applications. Fully object-oriented, 
	and roughly modeled after Smalltalk\'s MVC, Kiwi provides a simple, practical 
	way to build forms, windows and widgets that transparently access and display
	your object data. Kiwi was primarily designed to make implementing the UI for
	 Stoq easier, and it is released under the LGPL');

INSERT INTO Sourcepackage (maintainer, sourcepackagename, shortdesc, 
	description)
VALUES ((SELECT id FROM Person WHERE displayname = 'Alexander Limi'),
        (SELECT id FROM Sourcepackagename WHERE name = 'plone'),
	'Plone', 
        'Plone is powerful and flexible. It is ideal as an intranet and extranet 
	server, as a document publishing system, a portal server and as a groupware
	 tool for collaboration between separately located entities.');

INSERT INTO Sourcepackage (maintainer, sourcepackagename, shortdesc, 
	description)
VALUES ((SELECT id FROM Person WHERE displayname = 'Jeff Waugh'),
        (SELECT id FROM Sourcepackagename WHERE name = 'evolution'),
	'Evolution', 
        'Evolution is the integrated mail, calendar, task and address book 
	distributed suite from Ximian, Inc.');


--SourcepackageRelease
INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM SOurcepackagename WHERE name = 'mozilla-firefox')),
 	1,
        (SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
        '0.9.0-6',
        timestamp '2004-06-17 00:00',
        1);


INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-firefox')),
 	1,
        (SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
        '0.9.0-7',
        timestamp '2004-06-18 00:00',
        1);


INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-firefox')),
 	1,
        (SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
        '0.9.0-8',
        timestamp '2004-06-19 00:00',
        1);

INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-firefox')),
 	1,
        (SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
        '0.9.0-9',
        timestamp '2004-06-20 00:00',
        1);

INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-firefox')),
 	1,
        (SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
        '0.9.1-1',
        timestamp '2004-06-29 00:00',
        1);

INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-thunderbird')),
 	1,
        (SELECT id FROM Person WHERE displayname = 'Steve Alexander'),
        '0.9.1-2',
        timestamp '2004-06-30 00:00',
        1);

INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM SOurcepackagename WHERE name = 'python-twisted')),
 	1,
        (SELECT id FROM Person WHERE displayname = 'Andrew Bennetts'),
        '0.9.1-3',
        timestamp '2004-07-01 00:00',
        1);

INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'bugzilla')),
 	1,
        (SELECT id FROM Person WHERE displayname = 'Dave Miller'),
        '0.9.1-4',
        timestamp '2004-07-02 00:00',
        1);

INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'arch')),
 	1,
        (SELECT id FROM Person WHERE displayname = 'James Blackwell'),
        '0.9.1-5',
        timestamp '2004-07-03 00:00',
        1);

INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'kiwi2')),
 	1,
        (SELECT id FROM Person WHERE displayname = 'Christian Reis'),
        '0.9.1-6',
        timestamp '2004-07-04 00:00',
        1);

INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'plone')),
 	1,
        (SELECT id FROM Person WHERE displayname = 'Alexander Limi'),
        '0.9.1-7',
        timestamp '2004-07-05 00:00',
        1);

UPDATE sourcepackagerelease set builddepends = 
	'mozilla-firefox (>= 0.9.0-9), mozilla-thunderbird, arch'
--	'fontconfig, psmisc, libatk1.0-0 (>= 1.6.0), libc6 (>= 2.3.2.ds1-4), libfontconfig1 (>= 2.2.1)' 
	where sourcepackage = 
	(SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-firefox'))
	;

UPDATE sourcepackagerelease set builddepends = 
	'mozilla-firefox (>= 0.9.0-9), mozilla-thunderbird, arch'
--	'libatk1.0-0 (>= 1.4.1), libc6 (>= 2.3.2.ds1-4), libfontconfig1 (>= 2.2.1), libfreetype6 (>= 2.1.5-1)' 
	where sourcepackage = 
	(SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-thunderbird'))
	;

UPDATE sourcepackagerelease set builddepends = 
	'mozilla-firefox (>= 0.9.0-9), mozilla-thunderbird, arch'
--	'python2.3, python2.3-twisted-bin' 
	where sourcepackage = 
	(SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'python-twisted'))
	;

UPDATE sourcepackagerelease set builddepends = 
	'mozilla-firefox  (>= 0.9.0-9), mozilla-thunderbird, arch'
--	'apache (>=1.9.2), perl (>=1.0.0)' 
	where sourcepackage = 
	(SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'bugzilla'))
	;

UPDATE sourcepackagerelease set builddepends = 
	'mozilla-firefox  (>= 0.9.0-9), mozilla-thunderbird, arch'
--	'libc6 (>= 2.3.2.ds1-4), libg2c0 (>= 1:3.3.3-1), debconf (>= 0.5) | debconf-2.0' 
	where sourcepackage = 
	(SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'arch'))
	;

UPDATE sourcepackagerelease set builddepends = 
	'mozilla-firefox  (>= 0.9.0-9), mozilla-thunderbird, arch'
--	'python2.3, python2.3-gtk2, python2.3-glade' 
	where sourcepackage = 
	(SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'kiwi2'))
	;

UPDATE sourcepackagerelease set builddepends = 
	'mozilla-firefox  (>= 0.9.0-9), mozilla-thunderbird, arch'
--	'python2.3, zopex3' 
	where sourcepackage = 
	(SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'plone'))
	;

UPDATE sourcepackagerelease set builddepends = 
	'mozilla-firefox  (>= 0.9.0-9), mozilla-thunderbird, arch'
--	'gtkhtml3.0 (>= 3.0.10), libart-2.0-2 (>= 2.3.16), libasn1-6-heimdal (>= 0.6.2), libatk1.0-0 (>= 1.6.0)' 
	where sourcepackage = 
	(SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'evolution'))
	;

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
VALUES ((SELECT id FROM SourcepackageRelease WHERE 
	dateuploaded = timestamp '2004-06-29 00:00'),
 (SELECT id FROM Manifest WHERE datecreated = timestamp '2004-06-29 00:00'));

INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcepackageRelease WHERE 
	dateuploaded = timestamp '2004-06-30 00:00'),
 (SELECT id FROM Manifest WHERE datecreated = timestamp '2004-06-30 00:00'));

INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcepackageRelease WHERE 
	dateuploaded = timestamp '2004-07-01 00:00'),
 (SELECT id FROM Manifest WHERE datecreated = timestamp '2004-07-01 00:00'));

INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcepackageRelease WHERE 
	dateuploaded = timestamp '2004-07-02 00:00'),
 (SELECT id FROM Manifest WHERE datecreated = timestamp '2004-07-02 00:00'));

INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcepackageRelease WHERE 
	dateuploaded = timestamp '2004-07-03 00:00'),
 (SELECT id FROM Manifest WHERE datecreated = timestamp '2004-07-03 00:00'));

INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcepackageRelease WHERE 
	dateuploaded = timestamp '2004-07-04 00:00'),
 (SELECT id FROM Manifest WHERE datecreated = timestamp '2004-07-04 00:00'));

INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcepackageRelease WHERE 
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
	(SELECT id from Person WHERE teamdescription = 'Warty Security Team'),
	(SELECT id from Distrorelease WHERE name = 'warty'),
	4);

INSERT INTO Distroreleaserole (person, distrorelease, role) 
	VALUES(
	(SELECT id from Person WHERE teamdescription = 'Warty Gnome Team'),
	(SELECT id from Distrorelease WHERE name = 'warty'),
	4);

INSERT INTO Distroreleaserole (person, distrorelease, role) 
	VALUES(
	(SELECT id from Person WHERE teamdescription = 'Hoary Gnome Team'),
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
	(SELECT id from Person WHERE teamdescription='Ubuntu Security Team'),
	(SELECT id from Distribution WHERE name = 'ubuntu'),
	3);

INSERT INTO Distributionrole (person, distribution, role) 
	VALUES(
	(SELECT id from Person WHERE teamdescription = 'Ubuntu Gnome Team'),
	(SELECT id from Distribution WHERE name = 'ubuntu'),
	3);


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
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-firefox'))  
	and version='0.9.1-1'),
	(SELECT id from Binarypackagename WHERE name = 'mozilla-firefox'), 
	'0.8', 
	'Mozilla Firefox Web Browser', 
        'Firefox is a redesign of the Mozilla browser component, similar to Galeon, 
	K-Meleon and Camino, but written using the XUL user interface language and 
	designed to lightweight and cross-platform.',
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
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-thunderbird'))
	),
	(SELECT id from Binarypackagename WHERE name = 'mozilla-thunderbird'), 
	'1.5', 
	'Mozilla Thunderbird Mail Reader', 
        'Mozilla Thunderbird is a redesign of the Mozilla mail component. 
	The goal is to produce a cross platform stand alone mail application 
	using the XUL user interface language. Mozilla Thunderbird leaves a 
	somewhat smaller memory footprint than the Mozilla suite.',
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
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'python-twisted'))),
	(SELECT id from Binarypackagename WHERE name = 'python-twisted'), 
	'1.3', 
	'Python Twisted', 
        'It includes a web server, a telnet server, a multiplayer RPG engine, 
	a generic client and server for remote object access, and APIs for 
	creating new protocols.',
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
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'bugzilla'))),
	(SELECT id from Binarypackagename WHERE name = 'bugzilla'), 
	'2.18', 
	'Bugzilla',
        'Bugzilla is a "Defect Tracking System" or "Bug-Tracking System". 
	Defect Tracking Systems allow individual or groups of developers 
	to keep track of outstanding bugs in their product effectively.',
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
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'arch'))),
	(SELECT id from Binarypackagename WHERE name = 'arch'), 
	'1.0', 
	'ARCH',
        'arch is a revision control system with features that are ideal for 
	projects characterised by widely distributed development, concurrent 
	support of multiple releases, and substantial amounts of development
	on branches. It can be a replacement for CVS and corrects many 
	mis-features of that system.',
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
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'kiwi2'))),
	(SELECT id from Binarypackagename WHERE name = 'kiwi'), 
	'2.0', 'Python Kiwi',
        ' Kiwi2 consists of a set of classes and wrappers for PyGTK-2 that were 
	developed to provide a sort of framework for applications. Fully object-oriented, 
	and roughly modeled after Smalltalk\'s MVC, Kiwi provides a simple, practical 
	way to build forms, windows and widgets that transparently access and display
	your object data. Kiwi was primarily designed to make implementing the UI for
	 Stoq easier, and it is released under the LGPL',
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
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'plone'))),
	(SELECT id from Binarypackagename WHERE name = 'plone'), 
	'1.0', 'Plone', 
        'Plone is powerful and flexible. It is ideal as an intranet and extranet 
	server, as a document publishing system, a portal server and as a groupware
	 tool for collaboration between separately located entities.',
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
        (SELECT id FROM Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'plone'))),
	1);

INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'warty'),
        (SELECT id FROM Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'kiwi2'))),
	1);
INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'warty'),
        (SELECT id FROM Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-firefox'))
	 and version='0.9.0-6'),
	6);
INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'warty'),
        (SELECT id FROM Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-firefox')) 
	and version='0.9.0-7'),
	6);
INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'warty'),
        (SELECT id FROM Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-firefox')) 
	and version='0.9.0-8'),
	6);
INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'warty'),
        (SELECT id FROM Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-firefox')) 
	and version='0.9.0-9'),
	4);
INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'warty'),
        (SELECT id FROM Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-firefox'))
	 and version='0.9.1-1'),
	1);
INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'warty'),
        (SELECT id FROM Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name='mozilla-thunderbird'))),
	1);

INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'hoary'),
        (SELECT id FROM Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'python-twisted'))),
	1);
INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'hoary'),
        (SELECT id FROM Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'kiwi2'))),
	1);
INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'hoary'),
        (SELECT id FROM Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'bugzilla'))),
	1);

INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'grumpy'),
        (SELECT id FROM Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'bugzilla'))),
	1);

INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'grumpy'),
        (SELECT id FROM Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'arch'))),
	1);






