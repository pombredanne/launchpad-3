
/*
  FOAF Sample Data
*/

-- Person
INSERT INTO Person ( displayname, givenname, familyname, name) VALUES 
	( 'Dave Miller', 'Dave', 'Miller', 'name2' );           
INSERT INTO Person ( displayname, givenname, familyname, name) VALUES 
	( 'Colin Watson', 'Colin', 'Watson', 'name3' );                 
INSERT INTO Person ( displayname, givenname, familyname, name) VALUES 
	( 'Scott James Remnant', 'Scott James', 'Remnant', 'name4' );   
INSERT INTO Person ( displayname, givenname, familyname, name) VALUES 
	( 'Jeff Waugh', 'Jeff', 'Waugh', 'name5' );                     
INSERT INTO Person ( displayname, givenname, familyname, name) VALUES 
	( 'Andrew Bennetts', 'Andrew', 'Bennetts', 'name6' );           
INSERT INTO Person ( displayname, givenname, familyname, name) VALUES 
	( 'James Blackwell', 'James', 'Blackwell', 'name7' );           
INSERT INTO Person ( displayname, givenname, familyname, name) VALUES 
	( 'Christian Reis', 'Christian', 'Reis', 'name8' );            
INSERT INTO Person ( displayname, givenname, familyname, name) VALUES 
	( 'Alexander Limi', 'Alexander', 'Limi', 'name9' );            
INSERT INTO Person ( displayname, givenname, familyname, name) VALUES 
	( 'Steve Alexander', 'Steve', 'Alexander', 'name10' );          
INSERT INTO Person ( displayname, givenname, familyname, name) VALUES
        ( 'Sample Person', 'Sample', 'Person', 'name11' );              

/*
  These sample people came from the Rosetta team. They all have password "test"
*/
INSERT INTO Person ( displayname, givenname, familyname, password )
VALUES ( 'Carlos Perelló Marín', 'Carlos', 'Perelló Marín', 'MdB+BoAdbza3BA6mIkMm6bFo1kv9hR2PKZ3U' );
INSERT INTO EmailAddress (email, person, status)
VALUES ('carlos@canonical.com',
	(SELECT id FROM Person WHERE givenname='Carlos'),
	2);
INSERT INTO Person ( displayname, givenname, familyname, password )
VALUES ( 'Dafydd Harries', 'Dafydd', 'Harries', 'EvSuSe4k4tkRHSp6p+g91vyQIwL5VJ3iTbRZ' );
INSERT INTO EmailAddress (email, person, status)
VALUES ('daf@canonical.com',
	(SELECT id FROM Person WHERE givenname='Dafydd'),
	2);
INSERT INTO Person ( displayname, givenname, familyname, password )
VALUES ( 'Lalo Martins', 'Lalo', 'Martins', 'K7Qmeansl6RbuPfulfcmyDQOzp70OxVh5Fcf' );
INSERT INTO EmailAddress (email, person, status)
VALUES ('lalo@canonical.com',
	(SELECT id FROM Person WHERE givenname='Lalo'),
	2);
INSERT INTO Person ( displayname, givenname, familyname, password )
VALUES ( 'Foo Bar', 'Foo', 'Bar', 'K7Qmeansl6RbuPfulfcmyDQOzp70OxVh5Fcf' );
INSERT INTO EmailAddress (email, person, status)
VALUES ('foo.bar@canonical.com',
	(SELECT id FROM Person WHERE givenname='Foo'),
	2);

-- Insert some Teams in Person following FOAF approach

INSERT INTO Person (teamowner, displayname, teamdescription) VALUES
	((SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
	'Ubuntu Team',
	'This Team is responsible for the Ubuntu Distribution');

INSERT INTO Person (teamowner, displayname, teamdescription) VALUES
	((SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
	'Ubuntu Gnome Team',
 	'This Team is responsible for the GNOME releases Issues on whole Ubuntu Distribution');

INSERT INTO Person (teamowner, displayname, teamdescription) VALUES
	((SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
	'Warty Gnome Team',
  	'This Team is responsible for GNOME release Issues on Warty Distribution Release');

INSERT INTO Person (teamowner, displayname, teamdescription) VALUES
	((SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
	'Warty Security Team',
 	'This Team is responsible for Security Issues on Warty Distribution Release');

INSERT INTO Person (teamowner, displayname, teamdescription) VALUES
	((SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
	'Hoary Gnome Team',
	'This team is responsible for Security Issues on Hoary Distribution Release');

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
INSERT INTO EmailAddress (email, person, status) VALUES
        ('justdave@bugzilla.org',
        (SELECT id FROM Person WHERE displayname='Dave Miller'),
        2
        );


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

INSERT INTO WikiName (person, wiki, wikiname) VALUES
	((SELECT id FROM Person WHERE displayname = 'Foo Bar'),
	'http://www.ubuntulinux.com/wiki/',
	'FooBar');

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
	(SELECT id FROM Person WHERE displayname = 'Ubuntu Team'),
	1, -- ADMIN (2 = MEMBER)
	2); -- CURRENT (1 = PROPOSED)	

INSERT INTO Membership(person, team, role, status) VALUES
	((SELECT id FROM Person WHERE displayname = 'Steve Alexander'),
	(SELECT id FROM Person WHERE displayname = 'Ubuntu Team'),
	2, -- MEMBER
	2); -- CURRENT

INSERT INTO Membership(person, team, role, status) VALUES
	((SELECT id FROM Person WHERE displayname = 'Alexander Limi'),
	(SELECT id FROM Person WHERE displayname = 'Ubuntu Team'),
	2, -- MEMBER
	1); -- PROPOSED

INSERT INTO Membership(person, team, role, status) VALUES
	((SELECT id FROM Person WHERE displayname = 'Colin Watson'),
	(SELECT id FROM Person WHERE displayname = 'Ubuntu Team'),
	2, -- MEMBER
	1); -- PROPOSED

INSERT INTO Membership(person, team, role, status) VALUES
	((SELECT id FROM Person WHERE displayname = 'Andrew Bennetts'),
	(SELECT id FROM Person WHERE displayname = 'Ubuntu Team'),
	2, -- MEMBER
	1); -- PROPOSED

INSERT INTO Membership(person, team, role, status) VALUES
	((SELECT id FROM Person WHERE displayname = 'Dave Miller'),
	(SELECT id FROM Person WHERE displayname = 'Ubuntu Team'),
	2, -- MEMBER
	1); -- PROPOSED

INSERT INTO Membership(person, team, role, status) VALUES
	((SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
	(SELECT id FROM Person WHERE displayname = 'Ubuntu Gnome Team'),
	1, -- ADMIN
	2); -- CURRENT	

INSERT INTO Membership(person, team, role, status) VALUES
	((SELECT id FROM Person WHERE displayname = 'Jeff Waugh'),
	(SELECT id FROM Person WHERE displayname = 'Ubuntu Gnome Team'),
	2, -- MEMBER
	2); -- CURRENT	
	

-- TeamParticipation	
INSERT INTO TeamParticipation (team, person) VALUES
	((SELECT id FROM Person WHERE displayname = 'Ubuntu Team'),
	(SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth')
	);
INSERT INTO TeamParticipation (team, person) VALUES
	((SELECT id FROM Person WHERE displayname = 'Ubuntu Team'),
	(SELECT id FROM Person WHERE displayname = 'Steve Alexander')
	);
INSERT INTO TeamParticipation (team, person) VALUES
	((SELECT id FROM Person WHERE displayname = 'Ubuntu Team'),
	(SELECT id FROM Person WHERE displayname = 'Alexander Limi')
	);
INSERT INTO TeamParticipation (team, person) VALUES
	((SELECT id FROM Person WHERE displayname = 'Ubuntu Team'),
	(SELECT id FROM Person WHERE displayname = 'Colin Watson')
	);
INSERT INTO TeamParticipation (team, person) VALUES
	((SELECT id FROM Person WHERE displayname = 'Ubuntu Team'),
	(SELECT id FROM Person WHERE displayname = 'Andrew Bennetts')
	);
INSERT INTO TeamParticipation (team, person) VALUES
	((SELECT id FROM Person WHERE displayname = 'Ubuntu Team'),
	(SELECT id FROM Person WHERE displayname = 'Dave Miller')
	);
INSERT INTO TeamParticipation (team, person) VALUES
	((SELECT id FROM Person WHERE displayname = 'Ubuntu Gnome Team'),
	(SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth')
	);
INSERT INTO TeamParticipation (team, person) VALUES
	((SELECT id FROM Person WHERE displayname = 'Ubuntu Gnome Team'),
	(SELECT id FROM Person WHERE displayname = 'Jeff Waugh')
	);

-- Nested Teams
INSERT INTO TeamParticipation (team, person) VALUES
	((SELECT id FROM Person WHERE displayname = 'Ubuntu Team'),
	(SELECT id FROM Person WHERE displayname = 'Warty Security Team')
	);
INSERT INTO TeamParticipation (team, person) VALUES
	((SELECT id FROM Person WHERE displayname = 'Ubuntu Gnome Team'),
	(SELECT id FROM Person WHERE displayname = 'Warty Gnome Team')
	);
INSERT INTO TeamParticipation (team, person) VALUES
	((SELECT id FROM Person WHERE displayname = 'Ubuntu Gnome Team'),
	(SELECT id FROM Person WHERE displayname = 'Hoary Gnome Team')
	);
