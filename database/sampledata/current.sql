
SET client_encoding = 'UNICODE';
SET check_function_bodies = false;

SET search_path = public, pg_catalog;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'person'::pg_catalog.regclass;

INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp, name, "language", fti) VALUES (23, 'David Allouche', 'David', 'Allouche', NULL, NULL, NULL, 0, '2004-12-09 17:59:07.717254', 'ddaa', NULL, '''david'':1,3 ''allouch'':2,4');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp, name, "language", fti) VALUES (24, 'Buttress Source Administrators', NULL, NULL, NULL, 2, 'Ultimate control of the Buttress systems', 666, '2004-12-09 17:59:38.607384', 'buttsource', NULL, '''sourc'':2 ''buttress'':1 ''administr'':3');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp, name, "language", fti) VALUES (12, 'Sample Person', 'Sample', 'Person', 'K7Qmeansl6RbuPfulfcmyDQOzp70OxVh5Fcf', NULL, NULL, 0, '2004-10-12 06:57:28.753737', 'name12', NULL, '''sampl'':1,3 ''person'':2,4');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp, name, "language", fti) VALUES (16, 'Foo Bar', 'Foo', 'Bar', 'K7Qmeansl6RbuPfulfcmyDQOzp70OxVh5Fcf', NULL, NULL, 0, '2004-10-12 06:57:28.753737', 'name16', NULL, '''bar'':2,4 ''foo'':1,3');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp, name, "language", fti) VALUES (17, 'Ubuntu Team', NULL, NULL, NULL, 1, 'This Team is responsible for the Ubuntu Distribution', 0, '2004-10-12 06:57:28.753737', 'name17', NULL, '''team'':2 ''ubuntu'':1');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp, name, "language", fti) VALUES (18, 'Ubuntu Gnome Team', NULL, NULL, NULL, 1, 'This Team is responsible for the GNOME releases Issues on whole Ubuntu Distribution', 0, '2004-10-12 06:57:28.753737', 'name18', NULL, '''team'':3 ''gnome'':2 ''ubuntu'':1');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp, name, "language", fti) VALUES (19, 'Warty Gnome Team', NULL, NULL, NULL, 1, 'This Team is responsible for GNOME release Issues on Warty Distribution Release', 0, '2004-10-12 06:57:28.753737', 'name19', NULL, '''team'':3 ''gnome'':2 ''warti'':1');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp, name, "language", fti) VALUES (20, 'Warty Security Team', NULL, NULL, NULL, 1, 'This Team is responsible for Security Issues on Warty Distribution Release', 0, '2004-10-12 06:57:28.753737', 'name20', NULL, '''team'':3 ''secur'':2 ''warti'':1');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp, name, "language", fti) VALUES (21, 'Hoary Gnome Team', NULL, NULL, NULL, 1, 'This team is responsible for Security Issues on Hoary Distribution Release', 0, '2004-10-12 06:57:28.753737', 'name21', NULL, '''team'':3 ''gnome'':2 ''hoari'':1');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp, name, "language", fti) VALUES (1, 'Mark Shuttleworth', 'Mark', 'Shuttleworth', 'K7Qmeansl6RbuPfulfcmyDQOzp70OxVh5Fcf', NULL, NULL, 0, '2004-10-12 06:57:28.753737', 'sabdfl', NULL, '''mark'':1,3 ''shuttleworth'':2,4');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp, name, "language", fti) VALUES (2, 'Robert Collins', 'Robert', 'Collins', NULL, NULL, NULL, 0, '2004-10-12 06:57:28.753737', 'lifeless', NULL, '''collin'':2,4 ''robert'':1,3');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp, name, "language", fti) VALUES (3, 'Dave Miller', 'Dave', 'Miller', NULL, NULL, NULL, 0, '2004-10-12 06:57:28.753737', 'justdave', NULL, '''dave'':1,3 ''miller'':2,4');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp, name, "language", fti) VALUES (6, 'Jeff Waugh', 'Jeff', 'Waugh', NULL, NULL, NULL, 0, '2004-10-12 06:57:28.753737', 'jdub', NULL, '''jeff'':1,3 ''waugh'':2,4');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp, name, "language", fti) VALUES (7, 'Andrew Bennetts', 'Andrew', 'Bennetts', NULL, NULL, NULL, 0, '2004-10-12 06:57:28.753737', 'spiv', NULL, '''andrew'':1,3 ''bennett'':2,4');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp, name, "language", fti) VALUES (8, 'James Blackwell', 'James', 'Blackwell', NULL, NULL, NULL, 0, '2004-10-12 06:57:28.753737', 'jblack', NULL, '''jame'':1,3 ''blackwel'':2,4');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp, name, "language", fti) VALUES (9, 'Christian Reis', 'Christian', 'Reis', NULL, NULL, NULL, 0, '2004-10-12 06:57:28.753737', 'kiko', NULL, '''rei'':2,4 ''christian'':1,3');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp, name, "language", fti) VALUES (10, 'Alexander Limi', 'Alexander', 'Limi', NULL, NULL, NULL, 0, '2004-10-12 06:57:28.753737', 'limi', NULL, '''limi'':2,4 ''alexand'':1,3');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp, name, "language", fti) VALUES (11, 'Steve Alexander', 'Steve', 'Alexander', NULL, NULL, NULL, 0, '2004-10-12 06:57:28.753737', 'stevea', NULL, '''steve'':1,3 ''alexand'':2,4');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp, name, "language", fti) VALUES (13, 'Carlos Perelló Marín', 'Carlos', 'Perelló Marín', 'MdB+BoAdbza3BA6mIkMm6bFo1kv9hR2PKZ3U', NULL, NULL, 0, '2004-10-12 06:57:28.753737', 'carlos', NULL, '''carlo'':1,4 ''marín'':3,6 ''perelló'':2,5');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp, name, "language", fti) VALUES (14, 'Dafydd Harries', 'Dafydd', 'Harries', 'EvSuSe4k4tkRHSp6p+g91vyQIwL5VJ3iTbRZ', NULL, NULL, 0, '2004-10-12 06:57:28.753737', 'daf', NULL, '''harri'':2,4 ''dafydd'':1,3');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp, name, "language", fti) VALUES (15, 'Lalo Martins', 'Lalo', 'Martins', 'K7Qmeansl6RbuPfulfcmyDQOzp70OxVh5Fcf', NULL, NULL, 0, '2004-10-12 06:57:28.753737', 'lalo', NULL, '''lalo'':1,3 ''martin'':2,4');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp, name, "language", fti) VALUES (22, 'Stuart Bishop', 'Stuart', 'Bishop', 'I+lQozEFEr+uBuxQZuKGpL4jkiy6lE1dQsZx', NULL, NULL, 0, '2004-10-12 06:57:28.753737', 'stub', NULL, '''bishop'':2,4 ''stuart'':1,3');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp, name, "language", fti) VALUES (4, 'Colin Watson', 'Colin', 'Watson', NULL, NULL, NULL, 0, '2004-10-12 06:57:28.753737', 'kamion', NULL, '''colin'':1,3 ''watson'':2,4');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp, name, "language", fti) VALUES (5, 'Scott James Remnant', 'Scott James', 'Remnant', NULL, NULL, NULL, 0, '2004-10-12 06:57:28.753737', 'keybuk', NULL, '''jame'':2,5 ''scott'':1,4 ''remnant'':3,6');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp, name, "language", fti) VALUES (25, NULL, NULL, NULL, NULL, 1, 'Launchpad Administrators', 0, '2004-12-13 18:08:27.2609', 'admins', NULL, '');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp, name, "language", fti) VALUES (26, 'Daniel Silverstone', 'Daniel', 'Silverstone', NULL, NULL, NULL, 0, '2004-12-13 18:10:17.294019', 'kinnison', NULL, '''daniel'':1,3 ''silverston'':2,4');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'person'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'emailaddress'::pg_catalog.regclass;

INSERT INTO emailaddress (id, email, person, status) VALUES (1, 'mark@hbd.com', 1, 2);
INSERT INTO emailaddress (id, email, person, status) VALUES (2, 'robertc@robertcollins.net', 2, 2);
INSERT INTO emailaddress (id, email, person, status) VALUES (3, 'carlos@canonical.com', 13, 2);
INSERT INTO emailaddress (id, email, person, status) VALUES (4, 'daf@canonical.com', 14, 2);
INSERT INTO emailaddress (id, email, person, status) VALUES (5, 'lalo@canonical.com', 15, 2);
INSERT INTO emailaddress (id, email, person, status) VALUES (6, 'foo.bar@canonical.com', 16, 2);
INSERT INTO emailaddress (id, email, person, status) VALUES (7, 'steve.alexander@ubuntulinux.com', 11, 1);
INSERT INTO emailaddress (id, email, person, status) VALUES (8, 'colin.watson@ubuntulinux.com', 4, 1);
INSERT INTO emailaddress (id, email, person, status) VALUES (9, 'scott.james.remnant@ubuntulinux.com', 5, 1);
INSERT INTO emailaddress (id, email, person, status) VALUES (10, 'andrew.bennetts@ubuntulinux.com', 7, 1);
INSERT INTO emailaddress (id, email, person, status) VALUES (11, 'james.blackwell@ubuntulinux.com', 8, 1);
INSERT INTO emailaddress (id, email, person, status) VALUES (12, 'christian.reis@ubuntulinux.com', 9, 1);
INSERT INTO emailaddress (id, email, person, status) VALUES (13, 'jeff.waugh@ubuntulinux.com', 6, 1);
INSERT INTO emailaddress (id, email, person, status) VALUES (14, 'dave.miller@ubuntulinux.com', 3, 1);
INSERT INTO emailaddress (id, email, person, status) VALUES (15, 'justdave@bugzilla.org', 3, 2);
INSERT INTO emailaddress (id, email, person, status) VALUES (16, 'test@canonical.com', 12, 2);
INSERT INTO emailaddress (id, email, person, status) VALUES (17, 'testtest@canonical.com', 12, 1);
INSERT INTO emailaddress (id, email, person, status) VALUES (18, 'testtesttest@canonical.com', 12, 3);
INSERT INTO emailaddress (id, email, person, status) VALUES (19, 'testing@canonical.com', 12, 2);
INSERT INTO emailaddress (id, email, person, status) VALUES (20, 'stuart.bishop@canonical.com', 22, 1);
INSERT INTO emailaddress (id, email, person, status) VALUES (21, 'david.allouche@canonical.com', 23, 2);
INSERT INTO emailaddress (id, email, person, status) VALUES (22, 'david@canonical.com', 23, 2);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'emailaddress'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'gpgkey'::pg_catalog.regclass;

INSERT INTO gpgkey (id, person, keyid, fingerprint, pubkey, revoked, algorithm, keysize) VALUES (1, 1, '1024D/09F89725', 'XVHJ OU77 IYTD 0982 FTG6 OQFC 0GF8 09PO QW45 MJ76', '<-- sample pubkey ??? -->', false, 17, 1024);
INSERT INTO gpgkey (id, person, keyid, fingerprint, pubkey, revoked, algorithm, keysize) VALUES (2, 11, '1024D/09F89890', 'XVHJ OU77 IYTD 0981 FTG6 OQFC 0GF8 09PO QW45 MJ76', '<-- sample pubkey ??? -->', false, 17, 1024);
INSERT INTO gpgkey (id, person, keyid, fingerprint, pubkey, revoked, algorithm, keysize) VALUES (3, 10, '1024D/09F89321', 'XVHJ OU77 IYTD 0983 FTG6 OQFC 0GF8 09PO QW45 MJ76', '<-- sample pubkey ??? -->', false, 17, 1024);
INSERT INTO gpgkey (id, person, keyid, fingerprint, pubkey, revoked, algorithm, keysize) VALUES (4, 8, '1024D/09F89098', 'XVHJ OU77 IYTD 0984 FTG6 OQFC 0GF8 09PO QW45 MJ76', '<-- sample pubkey ??? -->', false, 17, 1024);
INSERT INTO gpgkey (id, person, keyid, fingerprint, pubkey, revoked, algorithm, keysize) VALUES (5, 9, '1024D/09F89123', 'XVHJ OU77 IYTD 0985 FTG6 OQFC 0GF8 09PO QW45 MJ76', '<-- sample pubkey ??? -->', false, 17, 1024);
INSERT INTO gpgkey (id, person, keyid, fingerprint, pubkey, revoked, algorithm, keysize) VALUES (6, 4, '1024D/09F89124', 'XVHJ OU77 IYTA 0985 FTG6 OQFC 0GF8 09PO QW45 MJ76', '<-- sample pubkey ??? -->', false, 17, 1024);
INSERT INTO gpgkey (id, person, keyid, fingerprint, pubkey, revoked, algorithm, keysize) VALUES (7, 5, '1024D/09F89125', 'XVHJ OU77 IYTQ 0985 FTG6 OQFC 0GF8 09PO QW45 MJ76', '<-- sample pubkey ??? -->', false, 17, 1024);
INSERT INTO gpgkey (id, person, keyid, fingerprint, pubkey, revoked, algorithm, keysize) VALUES (8, 7, '1024D/09F89126', 'XVHJ OU77 IYTX 0985 FTG6 OQFC 0GF8 09PO QW45 MJ76', '<-- sample pubkey ??? -->', false, 17, 1024);
INSERT INTO gpgkey (id, person, keyid, fingerprint, pubkey, revoked, algorithm, keysize) VALUES (9, 3, '1024D/09F89127', 'XVHJ OU77 IYTZ 0985 FTG6 OQFC 0GF8 09PO QW45 MJ76', '<-- sample pubkey ??? -->', false, 17, 1024);
INSERT INTO gpgkey (id, person, keyid, fingerprint, pubkey, revoked, algorithm, keysize) VALUES (10, 6, '1024D/09F89120', 'XVHJ OU77 IYTP 0985 FTG6 OQFC 0GF8 09PO QW45 MJ76', '<-- sample pubkey ??? -->', false, 17, 1024);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'gpgkey'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'archuserid'::pg_catalog.regclass;

INSERT INTO archuserid (id, person, archuserid) VALUES (1, 1, 'mark.shuttleworth');
INSERT INTO archuserid (id, person, archuserid) VALUES (2, 11, 'steve.alexander');
INSERT INTO archuserid (id, person, archuserid) VALUES (3, 10, 'alexander.limi');
INSERT INTO archuserid (id, person, archuserid) VALUES (4, 8, 'james.blackwell');
INSERT INTO archuserid (id, person, archuserid) VALUES (5, 9, 'christian.reis');
INSERT INTO archuserid (id, person, archuserid) VALUES (6, 4, 'colin.watson');
INSERT INTO archuserid (id, person, archuserid) VALUES (7, 5, 'scott.james.remnant');
INSERT INTO archuserid (id, person, archuserid) VALUES (8, 7, 'andrew.bennetts');
INSERT INTO archuserid (id, person, archuserid) VALUES (9, 3, 'dave.miller');
INSERT INTO archuserid (id, person, archuserid) VALUES (10, 6, 'jeff.waugh');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'archuserid'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'wikiname'::pg_catalog.regclass;

INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (1, 1, 'http://www.ubuntulinux.com/wiki/', 'MarkShuttleworth');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (2, 11, 'http://www.ubuntulinux.com/wiki/', 'SteveAlexander');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (3, 10, 'http://www.ubuntulinux.com/wiki/', 'AlexanderLimi');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (4, 8, 'http://www.ubuntulinux.com/wiki/', 'JamesBlackwell');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (5, 9, 'http://www.ubuntulinux.com/wiki/', 'ChristianReis');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (6, 4, 'http://www.ubuntulinux.com/wiki/', 'ColinWatson');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (7, 5, 'http://www.ubuntulinux.com/wiki/', 'ScottJamesRemnant');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (8, 7, 'http://www.ubuntulinux.com/wiki/', 'AndrewBennetts');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (9, 3, 'http://www.ubuntulinux.com/wiki/', 'DaveMiller');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (10, 6, 'http://www.ubuntulinux.com/wiki/', 'JeffWaugh');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'wikiname'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'jabberid'::pg_catalog.regclass;

INSERT INTO jabberid (id, person, jabberid) VALUES (1, 1, 'markshuttleworth@jabber.org');
INSERT INTO jabberid (id, person, jabberid) VALUES (2, 11, 'stevea@jabber.org');
INSERT INTO jabberid (id, person, jabberid) VALUES (3, 10, 'limi@jabber.org');
INSERT INTO jabberid (id, person, jabberid) VALUES (4, 8, 'jblack@jabber.org');
INSERT INTO jabberid (id, person, jabberid) VALUES (5, 9, 'kiko@jabber.org');
INSERT INTO jabberid (id, person, jabberid) VALUES (6, 4, 'colin@jabber.org');
INSERT INTO jabberid (id, person, jabberid) VALUES (7, 5, 'scott@jabber.org');
INSERT INTO jabberid (id, person, jabberid) VALUES (8, 7, 'spiv@jabber.org');
INSERT INTO jabberid (id, person, jabberid) VALUES (9, 3, 'justdave@jabber.org');
INSERT INTO jabberid (id, person, jabberid) VALUES (10, 6, 'jeff@jabber.org');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'jabberid'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'ircid'::pg_catalog.regclass;

INSERT INTO ircid (id, person, network, nickname) VALUES (1, 1, 'irc.freenode.net', 'mark');
INSERT INTO ircid (id, person, network, nickname) VALUES (2, 11, 'irc.freenode.net', 'SteveA');
INSERT INTO ircid (id, person, network, nickname) VALUES (3, 10, 'irc.freenode.net', 'limi');
INSERT INTO ircid (id, person, network, nickname) VALUES (4, 8, 'irc.freenode.net', 'jblack');
INSERT INTO ircid (id, person, network, nickname) VALUES (5, 3, 'irc.freenode.net', 'justdave');
INSERT INTO ircid (id, person, network, nickname) VALUES (6, 9, 'irc.freenode.net', 'kiko');
INSERT INTO ircid (id, person, network, nickname) VALUES (7, 4, 'irc.freenode.net', 'Kamion');
INSERT INTO ircid (id, person, network, nickname) VALUES (8, 5, 'irc.freenode.net', 'Keybuk');
INSERT INTO ircid (id, person, network, nickname) VALUES (9, 6, 'irc.freenode.net', 'jeff');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'ircid'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'membership'::pg_catalog.regclass;

INSERT INTO membership (id, person, team, role, status) VALUES (1, 1, 17, 1, 2);
INSERT INTO membership (id, person, team, role, status) VALUES (2, 11, 17, 2, 2);
INSERT INTO membership (id, person, team, role, status) VALUES (3, 10, 17, 2, 1);
INSERT INTO membership (id, person, team, role, status) VALUES (4, 4, 17, 2, 1);
INSERT INTO membership (id, person, team, role, status) VALUES (5, 7, 17, 2, 1);
INSERT INTO membership (id, person, team, role, status) VALUES (6, 3, 17, 2, 1);
INSERT INTO membership (id, person, team, role, status) VALUES (7, 1, 18, 1, 2);
INSERT INTO membership (id, person, team, role, status) VALUES (8, 6, 18, 2, 2);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'membership'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'teamparticipation'::pg_catalog.regclass;

INSERT INTO teamparticipation (id, team, person) VALUES (1, 17, 1);
INSERT INTO teamparticipation (id, team, person) VALUES (2, 17, 11);
INSERT INTO teamparticipation (id, team, person) VALUES (3, 17, 10);
INSERT INTO teamparticipation (id, team, person) VALUES (4, 17, 4);
INSERT INTO teamparticipation (id, team, person) VALUES (5, 17, 7);
INSERT INTO teamparticipation (id, team, person) VALUES (6, 17, 3);
INSERT INTO teamparticipation (id, team, person) VALUES (7, 18, 1);
INSERT INTO teamparticipation (id, team, person) VALUES (8, 18, 6);
INSERT INTO teamparticipation (id, team, person) VALUES (9, 17, 20);
INSERT INTO teamparticipation (id, team, person) VALUES (10, 18, 19);
INSERT INTO teamparticipation (id, team, person) VALUES (11, 18, 21);
INSERT INTO teamparticipation (id, team, person) VALUES (12, 24, 2);
INSERT INTO teamparticipation (id, team, person) VALUES (13, 24, 23);
INSERT INTO teamparticipation (id, team, person) VALUES (14, 25, 22);
INSERT INTO teamparticipation (id, team, person) VALUES (15, 25, 2);
INSERT INTO teamparticipation (id, team, person) VALUES (16, 25, 11);
INSERT INTO teamparticipation (id, team, person) VALUES (17, 25, 23);
INSERT INTO teamparticipation (id, team, person) VALUES (19, 25, 7);
INSERT INTO teamparticipation (id, team, person) VALUES (20, 25, 8);
INSERT INTO teamparticipation (id, team, person) VALUES (21, 25, 14);
INSERT INTO teamparticipation (id, team, person) VALUES (22, 25, 13);
INSERT INTO teamparticipation (id, team, person) VALUES (23, 25, 26);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'teamparticipation'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = '"schema"'::pg_catalog.regclass;

INSERT INTO "schema" (id, name, title, description, "owner", extensible) VALUES (2, 'schema', 'SCHEMA', 'description', 1, true);
INSERT INTO "schema" (id, name, title, description, "owner", extensible) VALUES (3, 'trema', 'XCHEMA', 'description', 1, true);
INSERT INTO "schema" (id, name, title, description, "owner", extensible) VALUES (4, 'enema', 'ENHEMA', 'description', 1, true);
INSERT INTO "schema" (id, name, title, description, "owner", extensible) VALUES (1, 'mark', 'TITLE', 'description', 1, true);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = '"schema"'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'label'::pg_catalog.regclass;

INSERT INTO label (id, "schema", name, title, description) VALUES (1, 1, 'blah', 'blah', 'blah');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'label'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'personlabel'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'personlabel'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'project'::pg_catalog.regclass;

INSERT INTO project (id, "owner", name, displayname, title, shortdesc, description, datecreated, homepageurl, wikiurl, lastdoap, sourceforgeproject, freshmeatproject, reviewed, active, fti) VALUES (5, 12, 'gnome', 'GNOME', 'The GNOME Project', 'The GNOME Project is an initiative to prduce a free desktop software framework. GNOME is more than a set of applications, it is a user interface standard (the Gnome HIG) and a set of libraries that allow applications to work together in a harmonious desktop-ish way.', 'The Gnome Project was founded (when?) to build on the success of early applications using the Gtk GUI toolkit. Many of those applications are still part of Gnome, and the Gtk toolkit remains an essential part of Gnome.

Gnome applications cover the full spectrum from office productivity applications to games, digital camera applications, and of course the Gnome Panel which acts as a launcher and general access point for apps on the desktop.', '2004-09-24 20:58:02.222154', 'http://www.gnome.org/', NULL, NULL, NULL, NULL, false, true, '''act'':114 ''app'':123 ''gtk'':70,84 ''gui'':71 ''hig'':35 ''ish'':52 ''set'':24,38 ''use'':68 ''way'':53 ''free'':15 ''full'':96 ''game'':103 ''mani'':73 ''part'':79,89 ''user'':30 ''work'':45 ''allow'':42 ''build'':61 ''cours'':109 ''cover'':94 ''digit'':104 ''earli'':66 ''found'':58 ''gnome'':1,2,4,7,19,34,55,81,91,92,111 ''initi'':11 ''offic'':99 ''panel'':112 ''point'':121 ''still'':78 ''access'':120 ''applic'':26,43,67,76,93,101,106 ''camera'':105 ''prduce'':13 ''remain'':86 ''togeth'':46 ''desktop'':16,51,126 ''essenti'':88 ''general'':119 ''harmoni'':49 ''librari'':40 ''product'':100 ''project'':5,8,56 ''softwar'':17 ''success'':64 ''toolkit'':72,85 ''interfac'':31 ''launcher'':117 ''spectrum'':97 ''standard'':32 ''framework'':18 ''desktop-ish'':50');
INSERT INTO project (id, "owner", name, displayname, title, shortdesc, description, datecreated, homepageurl, wikiurl, lastdoap, sourceforgeproject, freshmeatproject, reviewed, active, fti) VALUES (8, 16, 'gimp', 'the GiMP Project', 'The GIMP Project', 'The GIMP Project works in the field of image manipulation and reproduction. The Project is responsible for several pieces of software, such as The GiMP and GiMP-Print.', 'Founded by Spencer Kimball in 1996 with the simple aim of producing a "paint" program, the GIMP project has become one of the defining projects of the open source world. The GIMP itself is an image manipulation program that is beginning to rival even Adobe Photoshop in features and functionality.

The project is loosely organised, with about 15 people making regular contributions. There is no fixed release schedule other than "when it is done".', '2004-10-03 22:27:45.283741', 'http://www.gimp.org/', NULL, NULL, NULL, NULL, false, true, '''15'':94 ''aim'':46 ''fix'':102 ''one'':57 ''1996'':42 ''adob'':81 ''done'':110 ''even'':80 ''gimp'':1,3,6,9,32,35,53,68 ''imag'':16,72 ''loos'':90 ''make'':96 ''open'':64 ''piec'':26 ''work'':11 ''becom'':56 ''begin'':77 ''defin'':60 ''field'':14 ''found'':37 ''paint'':50 ''peopl'':95 ''print'':36 ''rival'':79 ''sever'':25 ''simpl'':45 ''sourc'':65 ''world'':66 ''featur'':84 ''kimbal'':40 ''produc'':48 ''releas'':103 ''manipul'':17,73 ''organis'':91 ''program'':51,74 ''project'':4,7,10,21,54,61,88 ''regular'':97 ''respons'':23 ''schedul'':104 ''softwar'':28 ''spencer'':39 ''function'':86 ''contribut'':98 ''photoshop'':82 ''reproduct'':19 ''gimp-print'':34');
INSERT INTO project (id, "owner", name, displayname, title, shortdesc, description, datecreated, homepageurl, wikiurl, lastdoap, sourceforgeproject, freshmeatproject, reviewed, active, fti) VALUES (1, 1, 'ubuntu', 'the Ubuntu Project', 'The Ubuntu Project', 'A community Linux distribution building a slick desktop for the global market. Ubuntu is absolutely free and will stay that way, contains no proprietary application software, always ships with the latest Gnome desktop software and Python integration.', 'The Ubuntu Project aims to create a freely redistributable OS that is easy to customize and derive from. Ubuntu is released every six months with contributions from a large community, especially the Gnome Project. While the full range of KDE and other desktop environments are available, Ubuntu''s Gnome desktop receives most of the polish and support work done for each release.

Ubuntu also includes work to unify the translation of common open source desktop applications and the tracking of bugs across multiple distributions.', '2004-09-24 20:58:00.633513', 'http://www.ubuntulinux.org/', NULL, NULL, NULL, NULL, false, true, '''os'':54 ''aim'':48 ''bug'':125 ''kde'':84 ''six'':67 ''way'':28 ''also'':108 ''done'':103 ''easi'':57 ''free'':23 ''full'':81 ''larg'':73 ''open'':117 ''rang'':82 ''ship'':35 ''stay'':26 ''work'':102,110 ''alway'':34 ''avail'':90 ''build'':12 ''creat'':50 ''deriv'':61 ''everi'':66 ''gnome'':39,77,93 ''linux'':10 ''month'':68 ''slick'':14 ''sourc'':118 ''track'':123 ''unifi'':112 ''across'':126 ''applic'':32,120 ''common'':116 ''commun'':9,74 ''custom'':59 ''especi'':75 ''freeli'':52 ''global'':18 ''includ'':109 ''integr'':44 ''latest'':38 ''market'':19 ''polish'':99 ''python'':43 ''receiv'':95 ''releas'':65,106 ''ubuntu'':1,3,6,20,46,63,91,107 ''absolut'':22 ''contain'':29 ''desktop'':15,40,87,94,119 ''environ'':88 ''multipl'':127 ''project'':4,7,47,78 ''softwar'':33,41 ''support'':101 ''translat'':114 ''contribut'':70 ''distribut'':11,128 ''proprietari'':31 ''redistribut'':53');
INSERT INTO project (id, "owner", name, displayname, title, shortdesc, description, datecreated, homepageurl, wikiurl, lastdoap, sourceforgeproject, freshmeatproject, reviewed, active, fti) VALUES (4, 12, 'mozilla', 'the Mozilla Project', 'The Mozilla Project', 'The Mozilla Project is the largest open source web browser collaborative project. Founded when Netscape released the source code to its pioneering browser in 1999, the Mozilla Project continues to set the standard for web browser technology.', 'The Mozilla Project produces several internet applications that are very widely used, and is also a center for collaboration on internet standards work by open source groups.

The Project now has several popular products, including the Firefox web browser, the Thunderbird mail client and the libraries that enable them to run on many platforms.

Organisationally, the Mozilla Project is hosted by the Mozilla Foundation, a not-for-profit company incorporated in the US.', '2004-09-24 20:58:02.177698', 'http://www.mozilla.org/', NULL, NULL, NULL, NULL, false, true, '''us'':118 ''run'':95 ''set'':38 ''use'':56 ''web'':16,42,82 ''1999'':32 ''also'':59 ''code'':26 ''host'':104 ''mail'':86 ''mani'':97 ''open'':14,69 ''wide'':55 ''work'':67 ''enabl'':92 ''found'':20 ''group'':71 ''sever'':49,76 ''sourc'':15,25,70 ''applic'':51 ''center'':61 ''client'':87 ''includ'':79 ''produc'':48 ''profit'':113 ''releas'':23 ''browser'':17,30,43,83 ''compani'':114 ''continu'':36 ''firefox'':81 ''foundat'':108 ''largest'':13 ''librari'':90 ''mozilla'':1,3,6,9,34,46,101,107 ''netscap'':22 ''organis'':99 ''pioneer'':29 ''popular'':77 ''product'':78 ''project'':4,7,10,19,35,47,73,102 ''collabor'':18,63 ''incorpor'':115 ''internet'':50,65 ''platform'':98 ''standard'':40,66 ''technolog'':44 ''thunderbird'':85 ''not-for-profit'':110');
INSERT INTO project (id, "owner", name, displayname, title, shortdesc, description, datecreated, homepageurl, wikiurl, lastdoap, sourceforgeproject, freshmeatproject, reviewed, active, fti) VALUES (3, 2, 'launchpad-mirrors', 'Launchpad SCM Mirrors', 'The Launchpad Mirroring Project', 'launchpad mirrors various revision control archives, that mirroring is managed here', 'A project to mirror revision control archives into Arch.', '2004-09-24 20:58:00.65398', 'http://arch.ubuntu.com/', NULL, NULL, NULL, NULL, false, true, '''scm'':5 ''arch'':30 ''manag'':20 ''revis'':14,26 ''archiv'':16,28 ''mirror'':3,6,9,12,18,25 ''control'':15,27 ''project'':10,23 ''various'':13 ''launchpad'':2,4,8,11 ''launchpad-mirror'':1');
INSERT INTO project (id, "owner", name, displayname, title, shortdesc, description, datecreated, homepageurl, wikiurl, lastdoap, sourceforgeproject, freshmeatproject, reviewed, active, fti) VALUES (6, 12, 'iso-codes', 'iso-codes', 'iso-codes', 'foo', 'bar', '2004-09-24 20:58:02.238443', 'http://www.gnome.org/', NULL, NULL, NULL, NULL, false, true, '''bar'':11 ''foo'':10 ''iso'':2,5,8 ''code'':3,6,9 ''iso-cod'':1,4,7');
INSERT INTO project (id, "owner", name, displayname, title, shortdesc, description, datecreated, homepageurl, wikiurl, lastdoap, sourceforgeproject, freshmeatproject, reviewed, active, fti) VALUES (7, 16, 'aaa', 'the Test Project', 'The Test Project', 'This is a small project that has no purpose by to serve as a test data point. The only thing this project has ever produced is products, most of which are largely unheard of. This short description is long enough.', 'Of course, one can''t say enough about the Test Project. Not only is it always there, it''s often exactly in the same state that you saw it last. And it has an amazing ability to pop up in places where you just didn''t think you''d expect to find it. Very noticeable when you least want it noticed, that sort of thing.

It would be very interesting to know whether this second paragraph of text about the test project is in fact rendered as a second paragraph, or if it all blurs together in a haze of testing. Only time will tell.', '2004-10-03 22:27:25.02843', 'http://www.testmenow.com', NULL, NULL, NULL, NULL, false, true, '''d'':96 ''aaa'':1 ''one'':50 ''pop'':85 ''saw'':75 ''say'':53 ''abil'':83 ''amaz'':82 ''blur'':142 ''data'':23 ''didn'':92 ''ever'':31 ''fact'':132 ''find'':99 ''haze'':146 ''know'':119 ''larg'':39 ''last'':77 ''long'':46 ''serv'':19 ''sort'':110 ''tell'':152 ''test'':3,6,22,57,128,148 ''text'':125 ''time'':150 ''want'':106 ''alway'':63 ''cours'':49 ''exact'':68 ''least'':105 ''notic'':102,108 ''often'':67 ''place'':88 ''point'':24 ''short'':43 ''small'':11 ''state'':72 ''thing'':27,112 ''think'':94 ''would'':114 ''enough'':47,54 ''expect'':97 ''produc'':32 ''purpos'':16 ''render'':133 ''second'':122,136 ''togeth'':143 ''product'':34 ''project'':4,7,12,29,58,129 ''unheard'':40 ''whether'':120 ''descript'':44 ''interest'':117 ''paragraph'':123,137');
INSERT INTO project (id, "owner", name, displayname, title, shortdesc, description, datecreated, homepageurl, wikiurl, lastdoap, sourceforgeproject, freshmeatproject, reviewed, active, fti) VALUES (2, 2, 'do-not-use-info-imports', 'DO NOT USE', 'DO NOT USE', 'DO NOT USE', 'TEMPORARY project till mirror jobs are assigned to correct project', '2004-09-24 20:58:00.637677', 'http://arch.ubuntu.com/', NULL, NULL, NULL, NULL, true, false, '''job'':20 ''use'':4,9,12,15 ''info'':5 ''till'':18 ''assign'':22 ''import'':6 ''mirror'':19 ''correct'':24 ''project'':17,25 ''temporari'':16 ''do-not-use-info-import'':1');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'project'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'projectrelationship'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'projectrelationship'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'projectrole'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'projectrole'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'product'::pg_catalog.regclass;

INSERT INTO product (id, project, "owner", name, displayname, title, shortdesc, description, datecreated, homepageurl, screenshotsurl, wikiurl, listurl, programminglang, downloadurl, lastdoap, sourceforgeproject, freshmeatproject, reviewed, active, autoupdate, fti) VALUES (5, 5, 12, 'evolution', 'Evolution', 'The Evolution Groupware Application', 'Evolution is an email client, addressbook and calendar application that is very well integrated with te Gnome desktop. Evolution is the standard mail client in the Ubuntu distribution, and supports all current mail system standards.', 'Recently, Evolution has seen significant work to make it interoperable with the proprietary Microsoft Exchange Server protocols and formats, allowing organisations to replace Outlook on Windows with Evolution and Linux.

The current stable release series of Evolution is 2.0.', '2004-09-24 20:58:02.240163', 'http://www.gnome.org/evolution/', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, false, true, false, '''te'':22 ''2.0'':80 ''mail'':29,39 ''make'':49 ''seen'':45 ''seri'':76 ''well'':19 ''work'':47 ''allow'':61 ''email'':10 ''gnome'':23 ''linux'':71 ''stabl'':74 ''applic'':6,15 ''client'':11,30 ''evolut'':1,2,4,7,25,43,69,78 ''format'':60 ''integr'':20 ''recent'':42 ''releas'':75 ''replac'':64 ''server'':57 ''system'':40 ''ubuntu'':33 ''window'':67 ''current'':38,73 ''desktop'':24 ''exchang'':56 ''organis'':62 ''outlook'':65 ''support'':36 ''calendar'':14 ''groupwar'':5 ''protocol'':58 ''signific'':46 ''standard'':28,41 ''distribut'':34 ''interoper'':51 ''microsoft'':55 ''addressbook'':12 ''proprietari'':54');
INSERT INTO product (id, project, "owner", name, displayname, title, shortdesc, description, datecreated, homepageurl, screenshotsurl, wikiurl, listurl, programminglang, downloadurl, lastdoap, sourceforgeproject, freshmeatproject, reviewed, active, autoupdate, fti) VALUES (6, 5, 12, 'gnome-terminal', 'GNOME Terminal', 'The GNOME Terminal Emulator', 'Gnome Terminal is a simple terminal application for your Gnome desktop. It allows quick access to console applications, supports all console types, and has many useful features such as tabbed consoles (many consoles in a single window with quick switching between them).', 'The Gnome Terminal application fully supports Gnome 2 and is a standard part of the Gnome Desktop.', '2004-09-24 20:58:02.256678', 'http://www.gnome.org/', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, false, true, false, '''2'':59 ''tab'':39 ''use'':35 ''emul'':9 ''mani'':34,41 ''part'':64 ''type'':31 ''allow'':22 ''fulli'':56 ''gnome'':2,4,7,10,19,53,58,67 ''quick'':23,48 ''simpl'':14 ''singl'':45 ''access'':24 ''applic'':16,27,55 ''consol'':26,30,40,42 ''featur'':36 ''switch'':49 ''termin'':3,5,8,11,15,54 ''window'':46 ''desktop'':20,68 ''support'':28,57 ''standard'':63 ''gnome-termin'':1');
INSERT INTO product (id, project, "owner", name, displayname, title, shortdesc, description, datecreated, homepageurl, screenshotsurl, wikiurl, listurl, programminglang, downloadurl, lastdoap, sourceforgeproject, freshmeatproject, reviewed, active, autoupdate, fti) VALUES (4, 4, 12, 'firefox', 'Mozilla Firefox', 'Mozilla Firefox', 'The Mozilla Firefox web browser', 'The Mozilla Firefox web browser', '2004-09-24 20:58:02.185708', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, false, true, false, '''web'':9,14 ''browser'':10,15 ''firefox'':1,3,5,8,13 ''mozilla'':2,4,7,12');
INSERT INTO product (id, project, "owner", name, displayname, title, shortdesc, description, datecreated, homepageurl, screenshotsurl, wikiurl, listurl, programminglang, downloadurl, lastdoap, sourceforgeproject, freshmeatproject, reviewed, active, autoupdate, fti) VALUES (7, 6, 12, 'iso-codes', 'iso-codes', 'The iso-codes', 'foo', 'bar', '2004-09-24 20:58:02.258743', 'http://www.novell.com/', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, false, true, false, '''bar'':12 ''foo'':11 ''iso'':2,5,9 ''code'':3,6,10 ''iso-cod'':1,4,8');
INSERT INTO product (id, project, "owner", name, displayname, title, shortdesc, description, datecreated, homepageurl, screenshotsurl, wikiurl, listurl, programminglang, downloadurl, lastdoap, sourceforgeproject, freshmeatproject, reviewed, active, autoupdate, fti) VALUES (8, 4, 12, 'thunderbird', 'Mozilla Thunderbird', 'Mozilla Thunderbird', 'The Mozilla Thunderbird email client', 'The Mozilla Thunderbird email client', '2004-09-24 20:58:04.478988', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, false, true, false, '''email'':9,14 ''client'':10,15 ''mozilla'':2,4,7,12 ''thunderbird'':1,3,5,8,13');
INSERT INTO product (id, project, "owner", name, displayname, title, shortdesc, description, datecreated, homepageurl, screenshotsurl, wikiurl, listurl, programminglang, downloadurl, lastdoap, sourceforgeproject, freshmeatproject, reviewed, active, autoupdate, fti) VALUES (9, 5, 16, 'applets', 'Gnome Applets', 'The Gnome Panel Applets', 'The Gnome Panel Applets are a collection of standard widgets that can be installed on your desktop Panel. These icons act as launchers for applications, or indicators of the status of your machine. For example, panel applets exist to show you your battery status or wifi network signal strength.', 'This is the collection of Panel Applets that is part of the default Gnome release. Additional Panel Applets are available from third parties. A complete set of Panel Applets is included in the Ubuntu OS, for example.

The Gnome Panel team includes Abel Kascinsky, Frederick Wurst and Andreas Andropovitch Axelsson.', '2004-10-03 16:46:09.113721', 'http://www.gnome.org/panel/', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, false, true, false, '''os'':91 ''act'':28 ''set'':82 ''abel'':99 ''icon'':27 ''part'':66 ''show'':47 ''team'':97 ''wifi'':53 ''addit'':72 ''avail'':76 ''exist'':45 ''gnome'':2,5,9,70,95 ''indic'':34 ''panel'':6,10,25,43,62,73,84,96 ''parti'':79 ''third'':78 ''wurst'':102 ''andrea'':104 ''applet'':1,3,7,11,44,63,74,85 ''applic'':32 ''exampl'':42,93 ''includ'':87,98 ''instal'':21 ''machin'':40 ''releas'':71 ''signal'':55 ''status'':37,51 ''ubuntu'':90 ''widget'':17 ''batteri'':50 ''collect'':14,60 ''complet'':81 ''default'':69 ''desktop'':24 ''network'':54 ''axelsson'':106 ''launcher'':30 ''standard'':16 ''strength'':56 ''frederick'':101 ''kascinski'':100 ''andropovitch'':105');
INSERT INTO product (id, project, "owner", name, displayname, title, shortdesc, description, datecreated, homepageurl, screenshotsurl, wikiurl, listurl, programminglang, downloadurl, lastdoap, sourceforgeproject, freshmeatproject, reviewed, active, autoupdate, fti) VALUES (1, 1, 1, 'ubuntu', 'Ubuntu', 'Ubuntu', 'An easy-to-install version of Linux that has a complete set of desktop applications ready to use immediately after installation.', 'Ubuntu is a desktop Linux that you can give your girlfriend to install. Works out of the box with recent Gnome desktop applications configured to make you productive immediately. Ubuntu is updated every six months, comes with security updates for peace of mind, and is available everywhere absolutely free of charge.', '2004-09-24 20:58:00.655518', 'http://www.ubuntu.com/', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, false, true, false, '''box'':43 ''set'':16 ''six'':59 ''use'':22 ''come'':61 ''easi'':6 ''free'':74 ''give'':34 ''make'':51 ''mind'':68 ''peac'':66 ''work'':39 ''avail'':71 ''charg'':76 ''everi'':58 ''gnome'':46 ''linux'':11,30 ''month'':60 ''readi'':20 ''secur'':63 ''updat'':57,64 ''applic'':19,48 ''immedi'':23,54 ''instal'':8,25,38 ''recent'':45 ''ubuntu'':1,2,3,26,55 ''absolut'':73 ''complet'':15 ''desktop'':18,29,47 ''product'':53 ''version'':9 ''configur'':49 ''everywher'':72 ''girlfriend'':36 ''easy-to-instal'':5');
INSERT INTO product (id, project, "owner", name, displayname, title, shortdesc, description, datecreated, homepageurl, screenshotsurl, wikiurl, listurl, programminglang, downloadurl, lastdoap, sourceforgeproject, freshmeatproject, reviewed, active, autoupdate, fti) VALUES (2, 2, 2, 'unassigned', 'unassigned syncs', 'unassigned syncs', 'syncs still not assigned to a real product', 'unassigned syncs, will not be processed, to be moved to real proejcts ASAP.', '2004-09-24 20:58:00.674409', 'http://arch.ubuntu.com/', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, true, false, false, '''asap'':26 ''move'':22 ''real'':12,24 ''sync'':3,5,6,15 ''still'':7 ''assign'':9 ''process'':19 ''product'':13 ''proejct'':25 ''unassign'':1,2,4,14');
INSERT INTO product (id, project, "owner", name, displayname, title, shortdesc, description, datecreated, homepageurl, screenshotsurl, wikiurl, listurl, programminglang, downloadurl, lastdoap, sourceforgeproject, freshmeatproject, reviewed, active, autoupdate, fti) VALUES (10, NULL, 2, 'python-gnome2-dev', 'python gnome2 dev', 'python gnome2 dev', 'Python bindings for the GNOME desktop environment', 'Python bindings for the GNOME desktop environment', '2004-09-24 20:58:00.674409', 'http://www.daa.com.au/~james/software/pygtk/', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, true, false, false, '''dev'':4,7,10 ''bind'':12,19 ''gnome'':15,22 ''gnome2'':3,6,9 ''python'':2,5,8,11,18 ''desktop'':16,23 ''environ'':17,24 ''python-gnome2-dev'':1');
INSERT INTO product (id, project, "owner", name, displayname, title, shortdesc, description, datecreated, homepageurl, screenshotsurl, wikiurl, listurl, programminglang, downloadurl, lastdoap, sourceforgeproject, freshmeatproject, reviewed, active, autoupdate, fti) VALUES (3, 3, 2, 'arch-mirrors', 'Arch mirrors', 'Arch archive mirrors', 'Arch Archive Mirroring project.', 'Arch archive full-archive mirror tasks', '2004-09-24 20:58:00.691047', 'http://arch.ubuntu.com/', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, false, true, false, '''arch'':2,4,6,9,13 ''full'':16 ''task'':19 ''archiv'':7,10,14,17 ''mirror'':3,5,8,11,18 ''project'':12 ''full-arch'':15 ''arch-mirror'':1');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'product'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'productlabel'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'productlabel'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'productrole'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'productrole'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'productseries'::pg_catalog.regclass;

INSERT INTO productseries (id, product, name, displayname, shortdesc) VALUES (1, 4, 'milestones', 'Milestone Releases', 'The Firefox milestone releases are development releases aimed at testing new features in the developer community. They are not intended for widespread end-user adoption, except among the very brave.');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'productseries'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'productrelease'::pg_catalog.regclass;

INSERT INTO productrelease (id, product, datereleased, "version", title, description, changelog, "owner", shortdesc, productseries) VALUES (3, 4, '2004-10-15 18:27:09.878302', '0.9', 'One Tree Hill', 'What''s New

Here''s what''s new in this release of Firefox:

    * New Default Theme

      An updated Default Theme now presents a uniform appearance across all three platforms - a new crisp, clear look for Windows users. Finetuning for GNOME will follow in future releases.
    * Comprehensive Data Migration

      Switching to Firefox has never been easier now that Firefox imports data like Favorites, History, Settings, Cookies and Passwords from Internet Explorer. Firefox can also import from Mozilla 1.x, Netscape 4.x, 6.x and 7.x, and Opera. MacOS X and Linux migrators for browsers like Safari, OmniWeb, Konqueror etc. will arrive in future releases.
    * Extension/Theme Manager

      New Extension and Theme Managers provide a convenient way to manage and update your add-ons. SmartUpdate also notifies you of updates to Firefox.
    * Smaller Download

      Windows users will find Firefox is now only 4.7MB to download.
    * Help

      A new online help system is available.
    * Lots of bug fixes and improvements

      Copy Image, the ability to delete individual items from Autocomplete lists, SMB/SFTP support on GNOME via gnome-vfs, better Bookmarks, Search and many other refinements fine tune the browsing experience.

For Linux/GTK2 Users

    * Installer

      Firefox now comes with an installer for Linux/GTK2 users. The new installer makes the installation process much simpler.
    * Look and Feel Updates

      Ongoing improvements have been made to improve the way Firefox adheres to your GTK2 themes, such as menus.
    * Talkback for GTK2

      Help us nail down crashes by submitting talkback reports with this crash reporting tool.

', NULL, 16, 'Release 0.9 of Firefox introduced a new theme as well as improved migration tools for people switching to Firefox.', 1);
INSERT INTO productrelease (id, product, datereleased, "version", title, description, changelog, "owner", shortdesc, productseries) VALUES (4, 4, '2004-10-15 18:31:19.164989', '0.9.1', 'One Tree Hill (v2)', '', NULL, 16, 'This was a bugfix release to patch up problems with the new extension system.', 1);
INSERT INTO productrelease (id, product, datereleased, "version", title, description, changelog, "owner", shortdesc, productseries) VALUES (5, 4, '2004-10-15 18:32:35.717695', '0.9.2', 'One (secure) Tree Hill', 'Security fixes

    * 250180 - [Windows] Disallow access to insecure shell: protocol.
', NULL, 16, 'This was a security fix release for 0.9.', 1);
INSERT INTO productrelease (id, product, datereleased, "version", title, description, changelog, "owner", shortdesc, productseries) VALUES (1, 4, '2004-06-28 00:00:00', '0.8', NULL, NULL, NULL, 12, NULL, NULL);
INSERT INTO productrelease (id, product, datereleased, "version", title, description, changelog, "owner", shortdesc, productseries) VALUES (2, 8, '2004-06-28 00:00:00', '0.8', NULL, NULL, NULL, 12, NULL, NULL);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'productrelease'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'productcvsmodule'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'productcvsmodule'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'productbkbranch'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'productbkbranch'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'productsvnmodule'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'productsvnmodule'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'archarchive'::pg_catalog.regclass;

INSERT INTO archarchive (id, name, title, description, visible, "owner") VALUES (2, 'thunderbird@arch.ubuntu.com', 'Thunderbid', 'text', false, NULL);
INSERT INTO archarchive (id, name, title, description, visible, "owner") VALUES (3, 'twisted@arch.ubuntu.com', 'Twisted', 'text', false, NULL);
INSERT INTO archarchive (id, name, title, description, visible, "owner") VALUES (4, 'bugzilla@arch.ubuntu.com', 'Bugzilla', 'text', false, NULL);
INSERT INTO archarchive (id, name, title, description, visible, "owner") VALUES (5, 'arch@arch.ubuntu.com', 'Arch', 'text', false, NULL);
INSERT INTO archarchive (id, name, title, description, visible, "owner") VALUES (6, 'kiwi2@arch.ubuntu.com', 'Kiwi2', 'text', false, NULL);
INSERT INTO archarchive (id, name, title, description, visible, "owner") VALUES (7, 'plone@arch.ubuntu.com', 'Plone', 'text', false, NULL);
INSERT INTO archarchive (id, name, title, description, visible, "owner") VALUES (8, 'gnome@arch.ubuntu.com', 'GNOME', 'The GNOME Project', false, NULL);
INSERT INTO archarchive (id, name, title, description, visible, "owner") VALUES (9, 'iso-codes@arch.ubuntu.com', 'iso-codes', 'The iso-codes', false, NULL);
INSERT INTO archarchive (id, name, title, description, visible, "owner") VALUES (1, 'mozilla@arch.ubuntu.com', 'Mozilla', 'text', false, NULL);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'archarchive'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'archarchivelocation'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'archarchivelocation'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'archarchivelocationsigner'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'archarchivelocationsigner'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'archnamespace'::pg_catalog.regclass;

INSERT INTO archnamespace (id, archarchive, category, branch, "version", visible) VALUES (1, 1, 'mozilla', NULL, NULL, true);
INSERT INTO archnamespace (id, archarchive, category, branch, "version", visible) VALUES (2, 2, 'tunderbird', NULL, NULL, true);
INSERT INTO archnamespace (id, archarchive, category, branch, "version", visible) VALUES (3, 3, 'twisted', NULL, NULL, true);
INSERT INTO archnamespace (id, archarchive, category, branch, "version", visible) VALUES (4, 4, 'bugzila', NULL, NULL, true);
INSERT INTO archnamespace (id, archarchive, category, branch, "version", visible) VALUES (5, 5, 'arch', NULL, NULL, true);
INSERT INTO archnamespace (id, archarchive, category, branch, "version", visible) VALUES (6, 6, 'kiwi2', NULL, NULL, true);
INSERT INTO archnamespace (id, archarchive, category, branch, "version", visible) VALUES (7, 7, 'plone', NULL, NULL, true);
INSERT INTO archnamespace (id, archarchive, category, branch, "version", visible) VALUES (8, 8, 'gnome', 'evolution', '2.0', false);
INSERT INTO archnamespace (id, archarchive, category, branch, "version", visible) VALUES (9, 9, 'iso-codes', 'iso-codes', '0.35', false);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'archnamespace'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'branch'::pg_catalog.regclass;

INSERT INTO branch (id, archnamespace, title, description, "owner", product) VALUES (3, 3, 'Python Twisted 0.9.1', 'text', 7, NULL);
INSERT INTO branch (id, archnamespace, title, description, "owner", product) VALUES (4, 4, 'Bugzila 0.9.1', 'text', 3, NULL);
INSERT INTO branch (id, archnamespace, title, description, "owner", product) VALUES (5, 5, 'Arch 0.9.1', 'text', 8, NULL);
INSERT INTO branch (id, archnamespace, title, description, "owner", product) VALUES (6, 6, 'Kiwi2 0.9.1', 'text', 9, NULL);
INSERT INTO branch (id, archnamespace, title, description, "owner", product) VALUES (7, 7, 'Plone 0.9.1', 'text', 10, NULL);
INSERT INTO branch (id, archnamespace, title, description, "owner", product) VALUES (1, 1, 'Mozilla Firefox 0.9.1', 'text', 1, 4);
INSERT INTO branch (id, archnamespace, title, description, "owner", product) VALUES (2, 2, 'Mozilla Thunderbird 0.9.1', 'text', 11, 8);
INSERT INTO branch (id, archnamespace, title, description, "owner", product) VALUES (9, 9, 'Iso-codes 0.35', 'text', 13, 7);
INSERT INTO branch (id, archnamespace, title, description, "owner", product) VALUES (8, 8, 'Evolution 2.0', 'text', 13, 5);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'branch'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'changeset'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'changeset'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'changesetfilename'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'changesetfilename'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'changesetfile'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'changesetfile'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'changesetfilehash'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'changesetfilehash'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'branchrelationship'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'branchrelationship'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'branchlabel'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'branchlabel'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'productbranchrelationship'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'productbranchrelationship'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'manifest'::pg_catalog.regclass;

INSERT INTO manifest (id, datecreated, "owner") VALUES (1, '2004-06-29 00:00:00', 1);
INSERT INTO manifest (id, datecreated, "owner") VALUES (2, '2004-06-30 00:00:00', 11);
INSERT INTO manifest (id, datecreated, "owner") VALUES (3, '2004-07-01 00:00:00', 7);
INSERT INTO manifest (id, datecreated, "owner") VALUES (4, '2004-07-02 00:00:00', 3);
INSERT INTO manifest (id, datecreated, "owner") VALUES (5, '2004-07-03 00:00:00', 8);
INSERT INTO manifest (id, datecreated, "owner") VALUES (6, '2004-07-04 00:00:00', 9);
INSERT INTO manifest (id, datecreated, "owner") VALUES (7, '2004-07-05 00:00:00', 10);
INSERT INTO manifest (id, datecreated, "owner") VALUES (8, '2004-06-29 00:00:00', 12);
INSERT INTO manifest (id, datecreated, "owner") VALUES (9, '2004-06-29 00:00:00', 12);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'manifest'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'manifestentry'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'manifestentry'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'archconfig'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'archconfig'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'archconfigentry'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'archconfigentry'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'processorfamily'::pg_catalog.regclass;

INSERT INTO processorfamily (id, name, title, description, "owner") VALUES (1, 'x86', 'Intel 386 compatible chips', 'Bring back the 8086!', 1);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'processorfamily'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'processor'::pg_catalog.regclass;

INSERT INTO processor (id, family, name, title, description, "owner") VALUES (1, 1, '386', 'Intel 386', 'Intel 386 and its many derivatives and clones, the basic 32-bit chip in the x86 family', 1);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'processor'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'builder'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'builder'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'component'::pg_catalog.regclass;

INSERT INTO component (id, name) VALUES (1, 'main');
INSERT INTO component (id, name) VALUES (2, 'restricted');
INSERT INTO component (id, name) VALUES (3, 'universe');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'component'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'section'::pg_catalog.regclass;

INSERT INTO section (id, name) VALUES (1, 'default_section');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'section'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'distribution'::pg_catalog.regclass;

INSERT INTO distribution (id, name, title, description, domainname, "owner", lucilleconfig, displayname, summary) VALUES (1, 'ubuntu', 'Ubuntu Linux', 'Ubuntu is a new
approach to Linux Distribution that includes regular releases, and a
simplified single-CD installation system.', 'ubuntulinux.org', 1, NULL, 'ubuntu', 'Ubuntu is a new
approach to Linux Distribution that includes regular releases, and a
simplified single-CD installation system.');
INSERT INTO distribution (id, name, title, description, domainname, "owner", lucilleconfig, displayname, summary) VALUES (2, 'redhat', 'Redhat Advanced Server', 'Red Hat is a
commercial distribution of the GNU/Linux Operating System.', 'redhat.com', 1, NULL, 'redhat', 'Red Hat is a
commercial distribution of the GNU/Linux Operating System.');
INSERT INTO distribution (id, name, title, description, domainname, "owner", lucilleconfig, displayname, summary) VALUES (3, 'debian', 'Debian GNU/Linux', 'Debian GNU/Linux is
a non commercial distribution of a GNU/Linux Operating System for many
platforms.', 'debian.org', 1, NULL, 'debian', 'Debian GNU/Linux is
a non commercial distribution of a GNU/Linux Operating System for many
platforms.');
INSERT INTO distribution (id, name, title, description, domainname, "owner", lucilleconfig, displayname, summary) VALUES (4, 'gentoo', 'The Gentoo Linux', 'Gentoo is a very
customizeable GNU/Linux Distribution that is designed to let you build every
single package yourself, with your own preferences.', 'gentoo.org', 1, NULL, 'gentoo', 'Gentoo is a very
customizeable GNU/Linux Distribution that is designed to let you build every
single package yourself, with your own preferences.');
INSERT INTO distribution (id, name, title, description, domainname, "owner", lucilleconfig, displayname, summary) VALUES (5, 'kubuntu', 'Kubuntu - Free KDE-based Linux', 'Kubuntu is an entirely free Linux distribution that uses the K Desktop
Environment as its default desktop after install.', 'kubuntu.org', 1, NULL, 'kubuntu', 'Kubuntu is an entirely free Linux distribution that uses the K Desktop
Environment as its default desktop after install.');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'distribution'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'distributionrole'::pg_catalog.regclass;

INSERT INTO distributionrole (person, distribution, role, id) VALUES (1, 1, 1, 1);
INSERT INTO distributionrole (person, distribution, role, id) VALUES (11, 1, 1, 2);
INSERT INTO distributionrole (person, distribution, role, id) VALUES (10, 1, 1, 3);
INSERT INTO distributionrole (person, distribution, role, id) VALUES (7, 1, 1, 4);
INSERT INTO distributionrole (person, distribution, role, id) VALUES (5, 1, 1, 5);
INSERT INTO distributionrole (person, distribution, role, id) VALUES (17, 1, 3, 6);
INSERT INTO distributionrole (person, distribution, role, id) VALUES (18, 1, 3, 7);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'distributionrole'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'distrorelease'::pg_catalog.regclass;

INSERT INTO distrorelease (id, distribution, name, title, description, "version", components, sections, releasestate, datereleased, parentrelease, "owner", lucilleconfig, shortdesc, displayname) VALUES (1, 1, 'warty', 'The Warty Warthog
Release', 'Warty was the first stable release of Ubuntu. Key feature goals
included releasing on time, with the latest version of the Gnome Desktop
Environment, and the creation of all the infrastructure required to manage
Ubuntu itself. Warty includes excellent support for Python, with most of the
widely used Python libraries installed by default.', '4.10', 1, 1, 3, '2004-08-20 00:00:00', NULL, 1, NULL, 'Warty is the first release of Ubuntu,
with a planned release date of October 2004.', 'warty');
INSERT INTO distrorelease (id, distribution, name, title, description, "version", components, sections, releasestate, datereleased, parentrelease, "owner", lucilleconfig, shortdesc, displayname) VALUES (2, 2, 'six', 'Six Six Six', 'some text to describe the whole 666 release of RH', '6.0.1', 1, 1, 4, '2004-03-21 00:00:00', NULL, 8, NULL, 'some text to describe the whole 666 release of RH', 'six');
INSERT INTO distrorelease (id, distribution, name, title, description, "version", components, sections, releasestate, datereleased, parentrelease, "owner", lucilleconfig, shortdesc, displayname) VALUES (3, 1, 'hoary', 'The Hoary
Hedgehod Release', 'Hoary is the second release of Ubuntu. Key feature goals
include the integration of Hoary with the Launchpad for bugs and translation
information, as well as Gnome 2.10 and the X.org window system.', '5.04', 1, 1, 2, '2004-08-25 00:00:00', 1, 1, NULL, 'Hoary is the second released of
Ubuntu, with release planned for April 2005.', 'hoary');
INSERT INTO distrorelease (id, distribution, name, title, description, "version", components, sections, releasestate, datereleased, parentrelease, "owner", lucilleconfig, shortdesc, displayname) VALUES (4, 2, '7.0', 'Seven', 'The release that we would not expect', '7.0.1', 1, 1, 3, '2004-04-01 00:00:00', 2, 7, NULL, 'The release that we would not expect', '7.0');
INSERT INTO distrorelease (id, distribution, name, title, description, "version", components, sections, releasestate, datereleased, parentrelease, "owner", lucilleconfig, shortdesc, displayname) VALUES (6, 3, 'woody', 'WOODY', 'WOODY is the current stable verison of Debian GNU/Linux', '3.0', 1, 1, 4, '2003-01-01 00:00:00', NULL, 2, NULL, 'WOODY is the current stable verison of Debian GNU/Linux', 'woody');
INSERT INTO distrorelease (id, distribution, name, title, description, "version", components, sections, releasestate, datereleased, parentrelease, "owner", lucilleconfig, shortdesc, displayname) VALUES (7, 3, 'sarge', 'Sarge', 'Sarge is the FROZEN unstable version of Debian GNU/Linux.', '3.1', 1, 1, 3, '2004-09-29 00:00:00', 6, 5, NULL, 'Sarge is the FROZEN unstable version of Debian GNU/Linux.', 'sarge');
INSERT INTO distrorelease (id, distribution, name, title, description, "version", components, sections, releasestate, datereleased, parentrelease, "owner", lucilleconfig, shortdesc, displayname) VALUES (8, 3, 'sid', 'Sid', 'Sid is the CRAZY unstable version of Debian GNU/Linux.', '3.2', 1, 1, 1, '2004-12-29 00:00:00', 6, 6, NULL, 'Sid is the CRAZY unstable version of Debian GNU/Linux.', 'sid');
INSERT INTO distrorelease (id, distribution, name, title, description, "version", components, sections, releasestate, datereleased, parentrelease, "owner", lucilleconfig, shortdesc, displayname) VALUES (5, 1, 'grumpy', 'The Grumpy
Groundhog Release', 'Grumpy, the third release of Ubuntu Linux, is not yet
in active development. This information is purely a placeholder.', '5.10', 1, 1, 1, '2004-08-29 00:00:00', 1, 1, NULL, 'Grumpy is the third release of
Ubuntu, planned for October 2005.', 'grumpy');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'distrorelease'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'distroreleaserole'::pg_catalog.regclass;

INSERT INTO distroreleaserole (person, distrorelease, role, id) VALUES (1, 1, 1, 1);
INSERT INTO distroreleaserole (person, distrorelease, role, id) VALUES (1, 3, 1, 2);
INSERT INTO distroreleaserole (person, distrorelease, role, id) VALUES (1, 5, 1, 3);
INSERT INTO distroreleaserole (person, distrorelease, role, id) VALUES (11, 1, 2, 4);
INSERT INTO distroreleaserole (person, distrorelease, role, id) VALUES (11, 3, 2, 5);
INSERT INTO distroreleaserole (person, distrorelease, role, id) VALUES (11, 5, 3, 6);
INSERT INTO distroreleaserole (person, distrorelease, role, id) VALUES (20, 1, 4, 7);
INSERT INTO distroreleaserole (person, distrorelease, role, id) VALUES (19, 1, 4, 8);
INSERT INTO distroreleaserole (person, distrorelease, role, id) VALUES (21, 3, 4, 9);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'distroreleaserole'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'distroarchrelease'::pg_catalog.regclass;

INSERT INTO distroarchrelease (id, distrorelease, processorfamily, architecturetag, "owner") VALUES (1, 1, 1, 'i386', 1);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'distroarchrelease'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'libraryfilecontent'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'libraryfilecontent'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'libraryfilealias'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'libraryfilealias'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'productreleasefile'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'productreleasefile'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'sourcepackagename'::pg_catalog.regclass;

INSERT INTO sourcepackagename (id, name) VALUES (1, 'mozilla-firefox-dummy');
INSERT INTO sourcepackagename (id, name) VALUES (9, 'evolution');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'sourcepackagename'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'sourcepackage'::pg_catalog.regclass;

INSERT INTO sourcepackage (id, maintainer, shortdesc, description, manifest, distro, sourcepackagename, srcpackageformat, fti) VALUES (1, 1, 'Mozilla Firefox Web Browser', 'Firefox is a redesign of the Mozilla browser component, similar to Galeon, 
	K-Meleon and Camino, but written using the XUL user interface language and 
	designed to lightweight and cross-platform.', NULL, 3, 1, 1, '''k'':18 ''use'':24 ''web'':3 ''xul'':26 ''user'':27 ''cross'':36 ''camino'':21 ''compon'':13 ''design'':31 ''galeon'':16 ''meleon'':19 ''browser'':4,12 ''firefox'':2,5 ''languag'':29 ''mozilla'':1,11 ''similar'':14 ''written'':23 ''interfac'':28 ''k-meleon'':17 ''platform'':37 ''redesign'':8 ''lightweight'':33 ''cross-platform'':35');
INSERT INTO sourcepackage (id, maintainer, shortdesc, description, manifest, distro, sourcepackagename, srcpackageformat, fti) VALUES (9, 1, 'Evolution-Dummy', 'This is evolution sample data package', NULL, 1, 9, 1, '''data'':8 ''dummi'':3 ''sampl'':7 ''evolut'':2,6 ''packag'':9 ''evolution-dummi'':1');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'sourcepackage'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'sourcepackagerelationship'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'sourcepackagerelationship'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'sourcepackagelabel'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'sourcepackagelabel'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'packaging'::pg_catalog.regclass;

INSERT INTO packaging (sourcepackage, packaging, product) VALUES (1, 1, 4);
INSERT INTO packaging (sourcepackage, packaging, product) VALUES (9, 1, 5);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'packaging'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'sourcepackagerelease'::pg_catalog.regclass;

INSERT INTO sourcepackagerelease (id, sourcepackage, creator, "version", dateuploaded, urgency, dscsigningkey, component, changelog, builddepends, builddependsindep, architecturehintlist, dsc, section, manifest, maintainer, sourcepackagename) VALUES (14, 1, 1, '0.9', '2004-09-27 11:57:13', 1, 1, 1, 'Mozilla dummy Changelog......', 'gcc-3.4-base, libc6 (>= 2.3.2.ds1-4), gcc-3.4 (>= 3.4.1-4sarge1), gcc-3.4 (<< 3.4.2), libstdc++6-dev (>= 3.4.1-4sarge1)', 'bacula-common (= 1.34.6-2), bacula-director-common (= 1.34.6-2), postgresql-client (>= 7.4)', NULL, NULL, 1, NULL, 1, 1);
INSERT INTO sourcepackagerelease (id, sourcepackage, creator, "version", dateuploaded, urgency, dscsigningkey, component, changelog, builddepends, builddependsindep, architecturehintlist, dsc, section, manifest, maintainer, sourcepackagename) VALUES (15, 9, 1, '1.0', '2004-09-27 11:57:13', 1, NULL, 1, NULL, NULL, NULL, NULL, NULL, 1, NULL, 1, 9);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'sourcepackagerelease'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'sourcepackagereleasefile'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'sourcepackagereleasefile'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'sourcepackagepublishing'::pg_catalog.regclass;

INSERT INTO sourcepackagepublishing (distrorelease, sourcepackagerelease, status, id, component, section, datepublished, scheduleddeletiondate) VALUES (1, 15, 2, 2, 1, 1, '2004-09-27 11:57:13', NULL);
INSERT INTO sourcepackagepublishing (distrorelease, sourcepackagerelease, status, id, component, section, datepublished, scheduleddeletiondate) VALUES (1, 14, 2, 1, 1, 1, '2004-09-27 11:57:13', NULL);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'sourcepackagepublishing'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'build'::pg_catalog.regclass;

INSERT INTO build (id, datecreated, processor, distroarchrelease, buildstate, datebuilt, buildduration, buildlog, builder, gpgsigningkey, changes, sourcepackagerelease) VALUES (2, '2004-09-27 11:57:13', 1, 1, 1, '2004-09-27 11:57:13', NULL, NULL, NULL, NULL, 'Sample changes :)....', 14);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'build'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'binarypackagename'::pg_catalog.regclass;

INSERT INTO binarypackagename (id, name) VALUES (8, 'mozilla-firefox-dummy');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'binarypackagename'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'binarypackage'::pg_catalog.regclass;

INSERT INTO binarypackage (id, binarypackagename, "version", shortdesc, description, build, binpackageformat, component, section, priority, shlibdeps, depends, recommends, suggests, conflicts, replaces, provides, essential, installedsize, copyright, licence, architecturespecific, fti) VALUES (12, 8, '0.9', 'Mozilla Firefox Web Browser', 'Mozilla Firefox Web Browser is .....', 2, 1, 1, 1, 1, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, true, '''web'':3,7 ''browser'':4,8 ''firefox'':2,6 ''mozilla'':1,5');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'binarypackage'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'binarypackagefile'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'binarypackagefile'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'packagepublishing'::pg_catalog.regclass;

INSERT INTO packagepublishing (id, binarypackage, distroarchrelease, component, section, priority, scheduleddeletiondate, status) VALUES (9, 12, 1, 1, 1, 1, NULL, 2);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'packagepublishing'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'packageselection'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'packageselection'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'coderelease'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'coderelease'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'codereleaserelationship'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'codereleaserelationship'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'osfile'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'osfile'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'osfileinpackage'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'osfileinpackage'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'pomsgid'::pg_catalog.regclass;

INSERT INTO pomsgid (id, msgid) VALUES (1, 'evolution addressbook');
INSERT INTO pomsgid (id, msgid) VALUES (2, 'current addressbook folder');
INSERT INTO pomsgid (id, msgid) VALUES (3, 'have ');
INSERT INTO pomsgid (id, msgid) VALUES (4, 'has ');
INSERT INTO pomsgid (id, msgid) VALUES (5, ' cards');
INSERT INTO pomsgid (id, msgid) VALUES (6, ' card');
INSERT INTO pomsgid (id, msgid) VALUES (7, 'contact''s header: ');
INSERT INTO pomsgid (id, msgid) VALUES (8, 'evolution minicard');
INSERT INTO pomsgid (id, msgid) VALUES (9, 'This addressbook could not be opened.');
INSERT INTO pomsgid (id, msgid) VALUES (10, 'This addressbook server might unreachable or the server name may be misspelled or your network connection could be down.');
INSERT INTO pomsgid (id, msgid) VALUES (11, 'Failed to authenticate with LDAP server.');
INSERT INTO pomsgid (id, msgid) VALUES (12, 'Check to make sure your password is spelled correctly and that you are using a supported login method. Remember that many passwords are case sensitive; your caps lock might be on.');
INSERT INTO pomsgid (id, msgid) VALUES (13, 'This addressbook server does not have any suggested search bases.');
INSERT INTO pomsgid (id, msgid) VALUES (14, 'This LDAP server may use an older version of LDAP, which does not support this functionality or it may be misconfigured. Ask your administrator for supported search bases.');
INSERT INTO pomsgid (id, msgid) VALUES (15, 'This server does not support LDAPv3 schema information.');
INSERT INTO pomsgid (id, msgid) VALUES (16, 'Could not get schema information for LDAP server.');
INSERT INTO pomsgid (id, msgid) VALUES (17, 'LDAP server did not respond with valid schema information.');
INSERT INTO pomsgid (id, msgid) VALUES (18, 'Could not remove addressbook.');
INSERT INTO pomsgid (id, msgid) VALUES (19, '{0}');
INSERT INTO pomsgid (id, msgid) VALUES (20, 'Category editor not available.');
INSERT INTO pomsgid (id, msgid) VALUES (21, '{1}');
INSERT INTO pomsgid (id, msgid) VALUES (22, 'Unable to open addressbook');
INSERT INTO pomsgid (id, msgid) VALUES (23, 'Error loading addressbook.');
INSERT INTO pomsgid (id, msgid) VALUES (24, 'Unable to perform search.');
INSERT INTO pomsgid (id, msgid) VALUES (25, 'Would you like to save your changes?');
INSERT INTO pomsgid (id, msgid) VALUES (26, 'You have made modifications to this contact. Do you want to save these changes?');
INSERT INTO pomsgid (id, msgid) VALUES (27, '_Discard');
INSERT INTO pomsgid (id, msgid) VALUES (28, 'Cannot move contact.');
INSERT INTO pomsgid (id, msgid) VALUES (29, 'You are attempting to move a contact from one addressbook to another but it cannot be removed from the source. Do you want to save a copy instead?');
INSERT INTO pomsgid (id, msgid) VALUES (30, 'Unable to save contact(s).');
INSERT INTO pomsgid (id, msgid) VALUES (31, 'Error saving contacts to {0}: {1}');
INSERT INTO pomsgid (id, msgid) VALUES (32, 'The Evolution addressbook has quit unexpectedly.');
INSERT INTO pomsgid (id, msgid) VALUES (33, 'Your contacts for {0} will not be available until Evolution is restarted.');
INSERT INTO pomsgid (id, msgid) VALUES (34, 'Default Sync Address:');
INSERT INTO pomsgid (id, msgid) VALUES (35, 'Could not load addressbook');
INSERT INTO pomsgid (id, msgid) VALUES (36, 'Could not read pilot''s Address application block');
INSERT INTO pomsgid (id, msgid) VALUES (37, '*Control*F2');
INSERT INTO pomsgid (id, msgid) VALUES (38, 'Autocompletion');
INSERT INTO pomsgid (id, msgid) VALUES (39, 'C_ontacts');
INSERT INTO pomsgid (id, msgid) VALUES (40, 'Certificates');
INSERT INTO pomsgid (id, msgid) VALUES (41, 'Configure autocomplete here');
INSERT INTO pomsgid (id, msgid) VALUES (42, 'Contacts');
INSERT INTO pomsgid (id, msgid) VALUES (43, 'Evolution Addressbook');
INSERT INTO pomsgid (id, msgid) VALUES (44, 'Evolution Addressbook address pop-up');
INSERT INTO pomsgid (id, msgid) VALUES (45, 'Evolution Addressbook address viewer');
INSERT INTO pomsgid (id, msgid) VALUES (46, 'Evolution Addressbook card viewer');
INSERT INTO pomsgid (id, msgid) VALUES (47, 'Evolution Addressbook component');
INSERT INTO pomsgid (id, msgid) VALUES (48, 'Evolution S/Mime Certificate Management Control');
INSERT INTO pomsgid (id, msgid) VALUES (49, 'Evolution folder settings configuration control');
INSERT INTO pomsgid (id, msgid) VALUES (50, 'Manage your S/MIME certificates here');
INSERT INTO pomsgid (id, msgid) VALUES (51, 'New Contact');
INSERT INTO pomsgid (id, msgid) VALUES (52, '_Contact');
INSERT INTO pomsgid (id, msgid) VALUES (53, 'Create a new contact');
INSERT INTO pomsgid (id, msgid) VALUES (54, 'New Contact List');
INSERT INTO pomsgid (id, msgid) VALUES (55, 'Contact _List');
INSERT INTO pomsgid (id, msgid) VALUES (56, 'Create a new contact list');
INSERT INTO pomsgid (id, msgid) VALUES (57, 'New Address Book');
INSERT INTO pomsgid (id, msgid) VALUES (58, 'Address _Book');
INSERT INTO pomsgid (id, msgid) VALUES (59, 'Create a new address book');
INSERT INTO pomsgid (id, msgid) VALUES (60, 'Failed upgrading Addressbook settings or folders.');
INSERT INTO pomsgid (id, msgid) VALUES (61, 'Migrating...');
INSERT INTO pomsgid (id, msgid) VALUES (62, 'Migrating `%s'':');
INSERT INTO pomsgid (id, msgid) VALUES (63, 'On This Computer');
INSERT INTO pomsgid (id, msgid) VALUES (64, 'Personal');
INSERT INTO pomsgid (id, msgid) VALUES (65, 'On LDAP Servers');
INSERT INTO pomsgid (id, msgid) VALUES (66, 'LDAP Servers');
INSERT INTO pomsgid (id, msgid) VALUES (67, 'Autocompletion Settings');
INSERT INTO pomsgid (id, msgid) VALUES (68, 'The location and hierarchy of the Evolution contact folders has changed since Evolution 1.x.

Please be patient while Evolution migrates your folders...');
INSERT INTO pomsgid (id, msgid) VALUES (69, 'The format of mailing list contacts has changed.

Please be patient while Evolution migrates your folders...');
INSERT INTO pomsgid (id, msgid) VALUES (70, 'The way Evolution stores some phone numbers has changed.

Please be patient while Evolution migrates your folders...');
INSERT INTO pomsgid (id, msgid) VALUES (71, 'Evolution''s Palm Sync changelog and map files have changed.

Please be patient while Evolution migrates your Pilot Sync data...');
INSERT INTO pomsgid (id, msgid) VALUES (72, 'Address book ''%s'' will be removed. Are you sure you want to continue?');
INSERT INTO pomsgid (id, msgid) VALUES (73, 'Delete');
INSERT INTO pomsgid (id, msgid) VALUES (74, 'Properties...');
INSERT INTO pomsgid (id, msgid) VALUES (75, 'Accessing LDAP Server anonymously');
INSERT INTO pomsgid (id, msgid) VALUES (76, 'Failed to authenticate.
');
INSERT INTO pomsgid (id, msgid) VALUES (77, '%sEnter password for %s (user %s)');
INSERT INTO pomsgid (id, msgid) VALUES (78, 'EFolderList xml for the list of completion uris');
INSERT INTO pomsgid (id, msgid) VALUES (79, 'Position of the vertical pane in main view');
INSERT INTO pomsgid (id, msgid) VALUES (80, 'The number of characters that must be typed before evolution will attempt to autocomplete');
INSERT INTO pomsgid (id, msgid) VALUES (81, 'URI for the folder last used in the select names dialog');
INSERT INTO pomsgid (id, msgid) VALUES (82, '*');
INSERT INTO pomsgid (id, msgid) VALUES (83, '1');
INSERT INTO pomsgid (id, msgid) VALUES (84, '3268');
INSERT INTO pomsgid (id, msgid) VALUES (85, '389');
INSERT INTO pomsgid (id, msgid) VALUES (86, '5');
INSERT INTO pomsgid (id, msgid) VALUES (87, '636');
INSERT INTO pomsgid (id, msgid) VALUES (88, '<b>Authentication</b>');
INSERT INTO pomsgid (id, msgid) VALUES (89, '<b>Display</b>');
INSERT INTO pomsgid (id, msgid) VALUES (90, '<b>Downloading</b>');
INSERT INTO pomsgid (id, msgid) VALUES (91, '<b>Searching</b>');
INSERT INTO pomsgid (id, msgid) VALUES (92, '<b>Server Information</b>');
INSERT INTO pomsgid (id, msgid) VALUES (93, '%d contact');
INSERT INTO pomsgid (id, msgid) VALUES (94, '%d contacts');
INSERT INTO pomsgid (id, msgid) VALUES (95, 'Opening %d contact will open %d new window as well.
Do you really want to display this contact?');
INSERT INTO pomsgid (id, msgid) VALUES (96, 'Opening %d contacts will open %d new windows as well.
Do you really want to display all of these contacts?');
INSERT INTO pomsgid (id, msgid) VALUES (97, '_Add Group');
INSERT INTO pomsgid (id, msgid) VALUES (98, '%d foo');
INSERT INTO pomsgid (id, msgid) VALUES (99, '%d bars');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'pomsgid'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'potranslation'::pg_catalog.regclass;

INSERT INTO potranslation (id, translation) VALUES (1, 'libreta de direcciones de Evolution');
INSERT INTO potranslation (id, translation) VALUES (2, 'carpeta de libretas de direcciones actual');
INSERT INTO potranslation (id, translation) VALUES (3, 'tiene');
INSERT INTO potranslation (id, translation) VALUES (4, '%d contacto');
INSERT INTO potranslation (id, translation) VALUES (5, '%d contactos');
INSERT INTO potranslation (id, translation) VALUES (6, 'La ubicación y jerarquía de las carpetas de contactos de Evolution ha cambiado desde Evolution 1.x.

Tenga paciencia mientras Evolution migra sus carpetas...');
INSERT INTO potranslation (id, translation) VALUES (7, 'Abrir %d contacto abrirá %d ventanas nuevas también.
¿Quiere realmente mostrar este contacto?');
INSERT INTO potranslation (id, translation) VALUES (8, 'Abrir %d contactos abrirá %d ventanas nuevas también.
¿Quiere realmente mostrar todos estos contactos?');
INSERT INTO potranslation (id, translation) VALUES (9, '_Añadir grupo');
INSERT INTO potranslation (id, translation) VALUES (10, '%d foo');
INSERT INTO potranslation (id, translation) VALUES (11, ' tarjetas');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'potranslation'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = '"language"'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = '"language"'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'country'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'country'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'spokenin'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'spokenin'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'license'::pg_catalog.regclass;

INSERT INTO license (id, legalese) VALUES (1, 'GPL-2');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'license'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'potemplate'::pg_catalog.regclass;

INSERT INTO potemplate (id, product, priority, branch, changeset, name, title, description, copyright, license, datecreated, "path", iscurrent, messagecount, "owner", rawfile, rawimporter, daterawimport, rawimportstatus) VALUES (1, 5, 2, 8, NULL, 'hoary-2.0', 'Template for Evolution 2.0', 'This is a PO template for Evolution 2.0.', 'Copyright (C) 2003  Ximian Inc.', 1, '2004-08-17 09:10:00', 'po/', true, 3, 13, NULL, NULL, '2004-11-25 01:11:50.721111', 0);
INSERT INTO potemplate (id, product, priority, branch, changeset, name, title, description, copyright, license, datecreated, "path", iscurrent, messagecount, "owner", rawfile, rawimporter, daterawimport, rawimportstatus) VALUES (2, 7, 2, 9, NULL, 'languages', 'POT file for the iso_639 strings', 'I suppose we should create a long description here....', 'Copyright', 1, '2004-08-17 09:10:00', 'iso_639/', true, 3, 13, NULL, NULL, '2004-11-25 01:11:50.722882', 0);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'potemplate'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'pofile'::pg_catalog.regclass;

INSERT INTO pofile (id, potemplate, "language", title, description, topcomment, header, fuzzyheader, lasttranslator, license, currentcount, updatescount, rosettacount, lastparsed, "owner", pluralforms, variant, filename, rawfile, rawimporter, daterawimport, rawimportstatus) VALUES (1, 1, 387, NULL, NULL, ' traducción de es.po al Spanish
 translation of es.po to Spanish
 translation of evolution.HEAD to Spanish
 Copyright © 2000-2002 Free Software Foundation, Inc.
 This file is distributed under the same license as the evolution package.
 Carlos Perelló Marín <carlos@gnome-db.org>, 2000-2001.
 Héctor García Álvarez <hector@scouts-es.org>, 2000-2002.
 Ismael Olea <Ismael@olea.org>, 2001, (revisiones) 2003.
 Eneko Lacunza <enlar@iname.com>, 2001-2002.
 Héctor García Álvarez <hector@scouts-es.org>, 2002.
 Pablo Gonzalo del Campo <pablodc@bigfoot.com>,2003 (revisión).
 Francisco Javier F. Serrador <serrador@cvs.gnome.org>, 2003, 2004.


', 'Project-Id-Version: es
POT-Creation-Date: 2004-08-17 11:10+0200
PO-Revision-Date: 2004-08-15 19:32+0200
Last-Translator: Francisco Javier F. Serrador <serrador@cvs.gnome.org>
Language-Team: Spanish <traductores@es.gnome.org>
MIME-Version: 1.0
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: 8bit
Report-Msgid-Bugs-To: serrador@hispalinux.es
X-Generator: KBabel 1.3.1
Plural-Forms: nplurals=2; plural=(n != 1);
', false, 13, NULL, 5, 0, 1, NULL, NULL, 2, NULL, NULL, NULL, NULL, '2004-11-25 01:11:50.726209', 0);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'pofile'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'pomsgset'::pg_catalog.regclass;

INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, fuzzy, commenttext, potmsgset) VALUES (1, 1, 1, true, false, false, NULL, 1);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, fuzzy, commenttext, potmsgset) VALUES (2, 2, 1, true, false, false, NULL, 2);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, fuzzy, commenttext, potmsgset) VALUES (3, 3, 1, false, false, true, NULL, 3);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, fuzzy, commenttext, potmsgset) VALUES (4, 4, 1, true, false, false, NULL, 15);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, fuzzy, commenttext, potmsgset) VALUES (5, 5, 1, true, false, false, ' This is an example of commenttext for a multiline msgset', 14);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, fuzzy, commenttext, potmsgset) VALUES (6, 6, 1, true, false, false, NULL, 16);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, fuzzy, commenttext, potmsgset) VALUES (7, 7, 1, true, true, false, NULL, 17);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, fuzzy, commenttext, potmsgset) VALUES (8, 8, 1, false, false, false, NULL, 18);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, fuzzy, commenttext, potmsgset) VALUES (9, 0, 1, false, false, false, NULL, 4);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, fuzzy, commenttext, potmsgset) VALUES (10, 0, 1, true, false, false, NULL, 5);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'pomsgset'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'pomsgidsighting'::pg_catalog.regclass;

INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (1, 1, 1, '2004-09-24 21:58:04.969875', '2004-09-24 21:58:04.969875', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (2, 2, 2, '2004-09-24 21:58:05.005673', '2004-09-24 21:58:05.005673', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (3, 3, 3, '2004-09-24 21:58:05.11396', '2004-09-24 21:58:05.11396', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (4, 4, 4, '2004-09-24 21:58:05.148051', '2004-09-24 21:58:05.148051', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (5, 5, 5, '2004-09-24 21:58:05.181877', '2004-09-24 21:58:05.181877', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (6, 6, 6, '2004-09-24 21:58:05.216203', '2004-09-24 21:58:05.216203', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (7, 7, 7, '2004-09-24 21:58:05.250458', '2004-09-24 21:58:05.250458', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (8, 8, 8, '2004-09-24 21:58:05.283205', '2004-09-24 21:58:05.283205', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (9, 9, 9, '2004-09-24 21:58:05.301434', '2004-09-24 21:58:05.301434', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (10, 10, 10, '2004-09-24 21:58:05.319483', '2004-09-24 21:58:05.319483', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (11, 11, 11, '2004-09-24 21:58:05.337554', '2004-09-24 21:58:05.337554', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (12, 12, 12, '2004-09-24 21:58:05.355659', '2004-09-24 21:58:05.355659', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (13, 13, 62, '2004-09-24 21:58:05.650973', '2004-09-24 21:58:05.650973', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (14, 14, 68, '2004-09-24 21:58:05.701435', '2004-09-24 21:58:05.701435', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (15, 15, 93, '2004-09-24 21:58:05.868655', '2004-09-24 21:58:05.868655', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (16, 15, 94, '2004-09-24 21:58:05.870713', '2004-09-24 21:58:05.870713', true, 1);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (17, 16, 95, '2004-09-24 21:58:05.870713', '2004-09-24 21:58:05.870713', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (18, 16, 96, '2004-09-24 21:58:05.870713', '2004-09-24 21:58:05.870713', true, 1);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (19, 17, 97, '2004-09-24 21:58:06.306292', '2004-09-24 21:58:06.306292', false, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (20, 18, 98, '2004-11-08 19:25:59.000014', '2004-11-08 19:25:59.000014', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (21, 18, 99, '2004-11-08 19:26:13.270815', '2004-11-08 19:26:13.270815', true, 1);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'pomsgidsighting'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'potranslationsighting'::pg_catalog.regclass;

INSERT INTO potranslationsighting (id, pomsgset, potranslation, license, datefirstseen, datelastactive, inlastrevision, pluralform, active, origin, person) VALUES (1, 1, 1, 1, '2004-09-24 21:58:05.989829', '2004-09-24 21:58:05.989829', true, 0, true, 0, 13);
INSERT INTO potranslationsighting (id, pomsgset, potranslation, license, datefirstseen, datelastactive, inlastrevision, pluralform, active, origin, person) VALUES (2, 2, 2, 1, '2004-09-24 21:58:06.036589', '2004-09-24 21:58:06.036589', true, 0, true, 0, 13);
INSERT INTO potranslationsighting (id, pomsgset, potranslation, license, datefirstseen, datelastactive, inlastrevision, pluralform, active, origin, person) VALUES (3, 3, 3, 1, '2004-09-24 21:58:06.086645', '2004-09-24 21:58:06.086645', true, 0, true, 0, 13);
INSERT INTO potranslationsighting (id, pomsgset, potranslation, license, datefirstseen, datelastactive, inlastrevision, pluralform, active, origin, person) VALUES (4, 4, 4, 1, '2004-09-24 21:58:06.154994', '2004-09-24 21:58:06.154994', true, 0, true, 0, 13);
INSERT INTO potranslationsighting (id, pomsgset, potranslation, license, datefirstseen, datelastactive, inlastrevision, pluralform, active, origin, person) VALUES (5, 4, 5, 1, '2004-09-24 21:58:06.15703', '2004-09-24 21:58:06.15703', true, 1, true, 0, 13);
INSERT INTO potranslationsighting (id, pomsgset, potranslation, license, datefirstseen, datelastactive, inlastrevision, pluralform, active, origin, person) VALUES (6, 5, 6, 1, '2004-09-24 21:58:06.206034', '2004-09-24 21:58:06.206034', true, 0, true, 0, 13);
INSERT INTO potranslationsighting (id, pomsgset, potranslation, license, datefirstseen, datelastactive, inlastrevision, pluralform, active, origin, person) VALUES (7, 6, 7, 1, '2004-09-24 21:58:06.256662', '2004-09-24 21:58:06.256662', true, 0, true, 0, 13);
INSERT INTO potranslationsighting (id, pomsgset, potranslation, license, datefirstseen, datelastactive, inlastrevision, pluralform, active, origin, person) VALUES (8, 6, 8, 1, '2004-09-24 21:58:06.273004', '2004-09-24 21:58:06.273004', true, 1, true, 0, 13);
INSERT INTO potranslationsighting (id, pomsgset, potranslation, license, datefirstseen, datelastactive, inlastrevision, pluralform, active, origin, person) VALUES (9, 7, 9, 1, '2004-09-24 21:58:06.307785', '2004-09-24 21:58:06.307785', true, 0, true, 0, 13);
INSERT INTO potranslationsighting (id, pomsgset, potranslation, license, datefirstseen, datelastactive, inlastrevision, pluralform, active, origin, person) VALUES (10, 8, 10, 1, '2004-11-08 19:32:21.604729', '2004-11-08 19:32:21.604729', true, 0, true, 0, 13);
INSERT INTO potranslationsighting (id, pomsgset, potranslation, license, datefirstseen, datelastactive, inlastrevision, pluralform, active, origin, person) VALUES (11, 10, 11, 1, '2004-11-15 16:04:49.157656', '2004-11-15 16:04:49.157656', false, 0, true, 2, 13);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'potranslationsighting'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'pocomment'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'pocomment'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'translationeffort'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'translationeffort'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'translationeffortpotemplate'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'translationeffortpotemplate'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'posubscription'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'posubscription'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'bug'::pg_catalog.regclass;

INSERT INTO bug (id, datecreated, name, title, description, "owner", duplicateof, communityscore, communitytimestamp, activityscore, activitytimestamp, hits, hitstimestamp, shortdesc, fti) VALUES (2, '2004-09-24 20:58:04.572546', 'blackhole', 'Blackhole Trash folder', 'The Trash folder seems to have significant problems! At the moment, dragging an item to the trash results in immediate deletion. The item does not appear in the Trash, it is just deleted from my hard disk. There is no undo or ability to recover the deleted file. Help!', 12, NULL, 0, '2004-09-24 00:00:00', 0, '2004-09-24 00:00:00', 0, '2004-09-24 00:00:00', 'Everything put into the folder "Trash" disappears!', '''put'':6 ''abil'':54 ''disk'':48 ''drag'':23 ''file'':59 ''hard'':47 ''help'':60 ''item'':25,34 ''seem'':15 ''undo'':52 ''delet'':32,44,58 ''recov'':56 ''trash'':3,10,13,28,40 ''appear'':37 ''folder'':4,9,14 ''immedi'':31 ''moment'':22 ''result'':29 ''everyth'':5 ''problem'':19 ''blackhol'':1,2 ''signific'':18 ''disappear'':11');
INSERT INTO bug (id, datecreated, name, title, description, "owner", duplicateof, communityscore, communitytimestamp, activityscore, activitytimestamp, hits, hitstimestamp, shortdesc, fti) VALUES (1, '2004-09-24 20:58:04.553583', NULL, 'Firefox does not support SVG', 'The SVG standard 1.0 is complete, and draft implementations for Firefox exist. One of these implementations needs to be integrated with the base install of Firefox. Ideally, the implementation needs to include support for the manipulation of SVG objects from JavaScript to enable interactive and dynamic SVG drawings.', 12, NULL, 0, '2004-09-24 00:00:00', 0, '2004-09-24 00:00:00', 0, '2004-09-24 00:00:00', 'Firefox needs to support embedded SVG images, now that the standard has been finalised.', '''1.0'':23 ''one'':32 ''svg'':5,11,21,57,66 ''base'':42 ''draw'':67 ''imag'':12 ''need'':7,36,49 ''draft'':27 ''dynam'':65 ''embed'':10 ''enabl'':62 ''exist'':31 ''ideal'':46 ''includ'':51 ''instal'':43 ''integr'':39 ''object'':58 ''complet'':25 ''finalis'':19 ''firefox'':1,6,30,45 ''manipul'':55 ''support'':4,9,52 ''interact'':63 ''standard'':16,22 ''implement'':28,35,48 ''javascript'':60');
INSERT INTO bug (id, datecreated, name, title, description, "owner", duplicateof, communityscore, communitytimestamp, activityscore, activitytimestamp, hits, hitstimestamp, shortdesc, fti) VALUES (3, '2004-10-05 00:00:00', NULL, 'Bug Title Test', 'y idu yifdxhfgffxShirtpkdf jlkdsj;lkd lkjd hlkjfds gkfdsg kfd glkfd gifdsytoxdiytxoiufdytoidxf yxoigfyoigfxuyfxoiug yxoiuy oiugf hyoifxugyoixgfuy xoiuyxoiyxoifuy xoShirtpkdf jlkdsj;lkd lkjd hlkjfds gkfdsg kfd glkfd gifdsytoxdiytxoiufdytoidxf yxoigfyoigfxuyfxoiug yxoiuy oiugf hyoifxugyoixgfuy xoiuyxoiyxoifuy xo
Shirtpkdf jlkdsj;lkd lkjd hlkjfds gkfdsg kfd glkfd gifdsytoxdiytxoiufdytoidxf yxoigfyoigfxuyfxoiug yxoiuy oiugf hyoifxugyoixgfuy xoiuyxoiyxoifuy xoShirtpkdf jlkdsj;lkd lkjd hlkjfds gkfdsg kfd glkfd gifdsytoxdiytxoiufdytoidxf yxoigfyoigfxuyfxoiug yxoiuy oiugf hyoifxugyoixgfuy xoiuyxoiyxoifuy xo

Shirtpkdf jlkdsj;lkd lkjd hlkjfds gkfdsg kfd glkfd gifdsytoxdiytxoiufdytoidxf yxoigfyoigfxuyfxoiug yxoiuy oiugf hyoifxugyoixgfuy xoiuyxoiyxoifuy xoShirtpkdf jlkdsj;lkd lkjd hlkjfds gkfdsg kfd glkfd gifdsytoxdiytxoiufdytoidxf yxoigfyoigfxuyfxoiug yxoiuy oiugf hyoifxugyoixgfuy xoiuyxoiyxoifuy xo', 16, NULL, 0, '2004-10-05 00:00:00', 0, '2004-10-05 00:00:00', 0, '2004-10-05 00:00:00', 'Shirtpkdf jlkdsj;lkd lkjd hlkjfds gkfdsg kfd glkfd gifdsytoxdiytxoiufdytoidxf yxoigfyoigfxuyfxoiug yxoiuy oiugf hyoifxugyoixgfuy xoiuyxoiyxoifuy xo', '''y'':19 ''xo'':18,49,78,107 ''bug'':1 ''idu'':20 ''kfd'':10,27,41,56,70,85,99 ''lkd'':6,23,37,52,66,81,95 ''lkjd'':7,24,38,53,67,82,96 ''test'':3 ''titl'':2 ''glkfd'':11,28,42,57,71,86,100 ''oiugf'':15,32,46,61,75,90,104 ''gkfdsg'':9,26,40,55,69,84,98 ''jlkdsj'':5,22,36,51,65,80,94 ''yxoiuy'':14,31,45,60,74,89,103 ''hlkjfds'':8,25,39,54,68,83,97 ''shirtpkdf'':4,50,79 ''xoshirtpkdf'':35,64,93 ''xoiuyxoiyxoifuy'':17,34,48,63,77,92,106 ''hyoifxugyoixgfuy'':16,33,47,62,76,91,105 ''yifdxhfgffxshirtpkdf'':21 ''yxoigfyoigfxuyfxoiug'':13,30,44,59,73,88,102 ''gifdsytoxdiytxoiufdytoidxf'':12,29,43,58,72,87,101');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'bug'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'bugsubscription'::pg_catalog.regclass;

INSERT INTO bugsubscription (id, person, bug, subscription) VALUES (1, 11, 1, 2);
INSERT INTO bugsubscription (id, person, bug, subscription) VALUES (2, 2, 1, 3);
INSERT INTO bugsubscription (id, person, bug, subscription) VALUES (3, 10, 1, 3);
INSERT INTO bugsubscription (id, person, bug, subscription) VALUES (4, 12, 1, 1);
INSERT INTO bugsubscription (id, person, bug, subscription) VALUES (5, 11, 2, 2);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'bugsubscription'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'sourcepackagebugassignment'::pg_catalog.regclass;

INSERT INTO sourcepackagebugassignment (id, bug, sourcepackage, bugstatus, priority, severity, binarypackagename, assignee, dateassigned, datecreated, "owner") VALUES (1, 1, 1, 20, 40, 20, NULL, NULL, '2004-10-11 11:07:20.584746', '2004-11-13 03:49:22.79024', 12);
INSERT INTO sourcepackagebugassignment (id, bug, sourcepackage, bugstatus, priority, severity, binarypackagename, assignee, dateassigned, datecreated, "owner") VALUES (2, 2, 1, 20, 40, 20, NULL, 12, '2004-10-11 11:07:20.584746', '2004-11-13 03:49:22.824591', 12);
INSERT INTO sourcepackagebugassignment (id, bug, sourcepackage, bugstatus, priority, severity, binarypackagename, assignee, dateassigned, datecreated, "owner") VALUES (3, 3, 1, 10, 20, 30, NULL, NULL, '2004-10-11 11:07:20.584746', '2004-11-13 03:49:22.825533', 16);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'sourcepackagebugassignment'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'productbugassignment'::pg_catalog.regclass;

INSERT INTO productbugassignment (id, bug, product, bugstatus, priority, severity, assignee, dateassigned, datecreated, "owner") VALUES (1, 1, 1, 10, 30, 20, 5, '2004-10-11 11:07:20.330975', '2004-11-13 03:49:22.910183', 12);
INSERT INTO productbugassignment (id, bug, product, bugstatus, priority, severity, assignee, dateassigned, datecreated, "owner") VALUES (5, 1, 4, 10, 10, 20, 1, '2004-10-11 11:07:20.330975', '2004-11-13 03:49:22.910878', 12);
INSERT INTO productbugassignment (id, bug, product, bugstatus, priority, severity, assignee, dateassigned, datecreated, "owner") VALUES (2, 2, 1, 10, 20, 20, NULL, '2004-10-11 11:07:20.330975', '2004-11-13 03:49:22.908491', 12);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'productbugassignment'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'bugactivity'::pg_catalog.regclass;

INSERT INTO bugactivity (id, bug, datechanged, person, whatchanged, oldvalue, newvalue, message) VALUES (1, 1, '2004-09-24 00:00:00', 1, 'title', 'A silly problem', 'An odd problem', 'Decided problem wasn''t silly after all');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'bugactivity'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'bugexternalref'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'bugexternalref'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'bugtrackertype'::pg_catalog.regclass;

INSERT INTO bugtrackertype (id, name, title, description, homepage, "owner") VALUES (1, 'bugzilla', 'BugZilla', 'Dave Miller''s Labour of Love, the Godfather of Open Source project issue tracking.', 'http://www.bugzilla.org/', 12);
INSERT INTO bugtrackertype (id, name, title, description, homepage, "owner") VALUES (2, 'debbugs', 'Debbugs System', 'Debbugs Bug Tracking System', 'http://bugs.debian.org/', 1);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'bugtrackertype'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'bugtracker'::pg_catalog.regclass;

INSERT INTO bugtracker (id, bugtrackertype, name, title, shortdesc, baseurl, "owner", contactdetails) VALUES (1, 1, 'mozilla.org', 'The Mozilla.org Bug Tracker', 'The Mozilla.org bug tracker is the grand-daddy of bugzillas. This is where Bugzilla was conceived, born and raised. This bugzilla instance covers all Mozilla products such as Firefox, Thunderbird and Bugzilla itself.', 'http://bugzilla.mozilla.org/', 12, 'Carrier pigeon only');
INSERT INTO bugtracker (id, bugtrackertype, name, title, shortdesc, baseurl, "owner", contactdetails) VALUES (2, 1, 'gnome-bugzilla', 'GnomeGBug GTracker', 'This is the Gnome Bugzilla bug tracking system. It covers all the applications in the Gnome Desktop and Gnome Fifth Toe.', 'http://bugzilla.gnome.org/', 16, 'Jeff Waugh, in his pants.');
INSERT INTO bugtracker (id, bugtrackertype, name, title, shortdesc, baseurl, "owner", contactdetails) VALUES (3, 2, 'debbugs', 'Debian Bug tracker', 'Bug tracker for debian project.', 'http://bugs.debian.org', 1, NULL);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'bugtracker'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'bugwatch'::pg_catalog.regclass;

INSERT INTO bugwatch (id, bug, bugtracker, remotebug, remotestatus, lastchanged, lastchecked, datecreated, "owner") VALUES (1, 2, 1, '42', 'FUBAR', '2004-09-24 20:58:04.740841', '2004-09-24 20:58:04.740841', '2004-09-24 20:58:04.740841', 12);
INSERT INTO bugwatch (id, bug, bugtracker, remotebug, remotestatus, lastchanged, lastchecked, datecreated, "owner") VALUES (2, 1, 1, '2000', '', '2004-10-04 00:00:00', '2004-10-04 00:00:00', '2004-10-04 00:00:00', 1);
INSERT INTO bugwatch (id, bug, bugtracker, remotebug, remotestatus, lastchanged, lastchecked, datecreated, "owner") VALUES (3, 1, 1, '123543', '', '2004-10-04 00:00:00', '2004-10-04 00:00:00', '2004-10-04 00:00:00', 1);
INSERT INTO bugwatch (id, bug, bugtracker, remotebug, remotestatus, lastchanged, lastchecked, datecreated, "owner") VALUES (4, 2, 2, '3224', '', '2004-10-05 00:00:00', '2004-10-05 00:00:00', '2004-10-05 00:00:00', 1);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'bugwatch'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'projectbugtracker'::pg_catalog.regclass;

INSERT INTO projectbugtracker (project, bugtracker, id) VALUES (5, 2, 1);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'projectbugtracker'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'buglabel'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'buglabel'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'bugrelationship'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'bugrelationship'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'message'::pg_catalog.regclass;

INSERT INTO message (id, datecreated, title, contents, "owner", parent, distribution, rfc822msgid, fti) VALUES (1, '2004-09-24 20:58:04.684057', 'PEBCAK', 'Problem exists between chair and keyboard', NULL, NULL, NULL, 'foo@example.com-332342--1231', '''chair'':5 ''exist'':3 ''pebcak'':1 ''problem'':2 ''keyboard'':7');
INSERT INTO message (id, datecreated, title, contents, "owner", parent, distribution, rfc822msgid, fti) VALUES (3, '2004-09-24 21:17:17.153792', 'Reproduced on AIX', 'We''ve seen something very similar on AIX with Gnome 2.6 when it is compiled with XFT support. It might be that the anti-aliasing is causing loopback devices to degrade, resulting in a loss of transparency at the system cache level and decoherence in the undelete function. This is only known to be a problem when the moon is gibbous.', 12, NULL, NULL, 'sdsdfsfd', '''ve'':5 ''2.6'':14 ''aix'':3,11 ''xft'':20 ''anti'':28 ''cach'':45 ''caus'':31 ''loss'':39 ''moon'':63 ''seen'':6 ''alias'':29 ''devic'':33 ''gnome'':13 ''known'':56 ''level'':46 ''might'':23 ''compil'':18 ''degrad'':35 ''result'':36 ''someth'':7 ''system'':44 ''decoher'':48 ''gibbous'':65 ''problem'':60 ''similar'':9 ''support'':21 ''undelet'':51 ''function'':52 ''loopback'':32 ''reproduc'':1 ''transpar'':41 ''anti-alias'':27');
INSERT INTO message (id, datecreated, title, contents, "owner", parent, distribution, rfc822msgid, fti) VALUES (4, '2004-09-24 21:24:03.922564', 'Re: Reproduced on AIX', 'Sorry, it was SCO unix which appears to have the same bug. For a brief moment I was confused there, since so much code is known to have been copied from SCO into AIX.', 12, NULL, NULL, 'sdfssfdfsd', '''re'':1 ''aix'':4,38 ''bug'':16 ''sco'':8,36 ''code'':28 ''copi'':34 ''much'':27 ''sinc'':25 ''unix'':9 ''brief'':19 ''known'':30 ''sorri'':5 ''appear'':11 ''confus'':23 ''moment'':20 ''reproduc'':2');
INSERT INTO message (id, datecreated, title, contents, "owner", parent, distribution, rfc822msgid, fti) VALUES (5, '2004-09-24 21:29:27.407354', 'Fantastic idea, I''d really like to see this', 'This would be a real killer feature. If there is already code to make it possible, why aren''t there tons of press announcements about the secuirty possibilities. Imagine - no more embarrassing emails for Mr Gates... everything they delete would actually disappear! I''m sure Redmond will switch over as soon as they hear about this. It''s not a bug, it''s a feature!', 12, NULL, NULL, 'dxssdfsdgf', '''d'':4 ''m'':53 ''mr'':44 ''bug'':70 ''see'':8 ''ton'':30 ''aren'':27 ''code'':21 ''gate'':45 ''hear'':63 ''idea'':2 ''like'':6 ''make'':23 ''real'':14 ''soon'':60 ''sure'':54 ''delet'':48 ''email'':42 ''press'':32 ''would'':11,49 ''actual'':50 ''featur'':16,74 ''imagin'':38 ''killer'':15 ''realli'':5 ''switch'':57 ''alreadi'':20 ''announc'':33 ''everyth'':46 ''fantast'':1 ''possibl'':25,37 ''redmond'':55 ''secuirti'':36 ''disappear'':51 ''embarrass'':41');
INSERT INTO message (id, datecreated, title, contents, "owner", parent, distribution, rfc822msgid, fti) VALUES (6, '2004-09-24 21:35:20.125564', 'Strange bug with duplicate messages.', 'Oddly enough the bug system seems only capable of displaying the first two comments that are made against a bug. I wonder why that is? Lets have a few more decent legth comments in here so we can see what the spacing is like. Also, at some stage, we''ll need a few comments that get displayed in a fixed-width font, so we have a clue about code-in-bug-comments etc.', 12, NULL, NULL, 'sdfsfwew', '''ll'':55 ''bug'':2,9,25,78 ''etc'':80 ''fix'':66 ''get'':61 ''let'':31 ''odd'':6 ''see'':44 ''two'':18 ''also'':50 ''clue'':73 ''code'':76 ''font'':68 ''like'':49 ''made'':22 ''need'':56 ''seem'':11 ''first'':17 ''legth'':37 ''space'':47 ''stage'':53 ''width'':67 ''capabl'':13 ''decent'':36 ''duplic'':4 ''enough'':7 ''messag'':5 ''strang'':1 ''system'':10 ''wonder'':27 ''comment'':19,38,59,79 ''display'':15,62 ''fixed-width'':65 ''code-in-bug-com'':75');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'message'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'bugattachment'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'bugattachment'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'sourcesource'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'sourcesource'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'componentselection'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'componentselection'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'sectionselection'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'sectionselection'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'bugproductinfestation'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'bugproductinfestation'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'bugpackageinfestation'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'bugpackageinfestation'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'distroreleasequeue'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'distroreleasequeue'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'distroreleasequeuesource'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'distroreleasequeuesource'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'distroreleasequeuebuild'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'distroreleasequeuebuild'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'personlanguage'::pg_catalog.regclass;

INSERT INTO personlanguage (id, person, "language") VALUES (1, 13, 387);
INSERT INTO personlanguage (id, person, "language") VALUES (4, 14, 449);
INSERT INTO personlanguage (id, person, "language") VALUES (3, 14, 196);
INSERT INTO personlanguage (id, person, "language") VALUES (2, 13, 68);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'personlanguage'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'potmsgset'::pg_catalog.regclass;

INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (1, 1, 1, 1, NULL, 'a11y/addressbook/ea-addressbook-view.c:94
a11y/addressbook/ea-addressbook-view.c:103
a11y/addressbook/ea-minicard-view.c:119', NULL, NULL);
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (2, 2, 2, 1, NULL, 'a11y/addressbook/ea-minicard-view.c:101', NULL, NULL);
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (3, 3, 3, 1, NULL, 'a11y/addressbook/ea-minicard-view.c:102', NULL, NULL);
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (4, 4, 4, 1, NULL, 'a11y/addressbook/ea-minicard-view.c:102', NULL, NULL);
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (5, 5, 5, 1, NULL, 'a11y/addressbook/ea-minicard-view.c:104', NULL, NULL);
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (6, 6, 6, 1, NULL, 'a11y/addressbook/ea-minicard-view.c:104', NULL, NULL);
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (7, 7, 7, 1, NULL, 'a11y/addressbook/ea-minicard-view.c:105', NULL, NULL);
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (8, 8, 8, 1, NULL, 'a11y/addressbook/ea-minicard.c:166', NULL, NULL);
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (9, 9, 9, 1, NULL, 'addressbook/addressbook-errors.xml.h:2', 'addressbook:ldap-init primary', NULL);
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (10, 10, 10, 1, NULL, 'addressbook/addressbook-errors.xml.h:4', 'addressbook:ldap-init secondary', NULL);
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (11, 11, 11, 1, NULL, 'addressbook/addressbook-errors.xml.h:6', 'addressbook:ldap-auth primary', NULL);
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (12, 12, 12, 1, NULL, 'addressbook/addressbook-errors.xml.h:8', 'addressbook:ldap-auth secondary', NULL);
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (13, 62, 13, 1, NULL, 'addressbook/gui/component/addressbook-migrate.c:124
calendar/gui/migration.c:188 mail/em-migrate.c:1201', NULL, 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (14, 68, 14, 1, NULL, 'addressbook/gui/component/addressbook-migrate.c:1123', NULL, NULL);
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (15, 93, 15, 1, NULL, 'addressbook/gui/widgets/e-addressbook-model.c:151', NULL, 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (16, 95, 16, 1, NULL, 'addressbook/gui/widgets/eab-gui-util.c:275', NULL, 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (17, 97, 0, 1, NULL, NULL, NULL, NULL);
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (18, 98, 17, 1, NULL, 'addressbook/gui/widgets/foo.c:345', NULL, 'c-format');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'potmsgset'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'launchpaddatabaserevision'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'launchpaddatabaserevision'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'bounty'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'bounty'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'bugmessage'::pg_catalog.regclass;

INSERT INTO bugmessage (id, bug, message) VALUES (1, 2, 1);
INSERT INTO bugmessage (id, bug, message) VALUES (2, 1, 3);
INSERT INTO bugmessage (id, bug, message) VALUES (3, 1, 4);
INSERT INTO bugmessage (id, bug, message) VALUES (4, 2, 5);
INSERT INTO bugmessage (id, bug, message) VALUES (5, 2, 6);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'bugmessage'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'cveref'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'cveref'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'karma'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'karma'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'sshkey'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'sshkey'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'bugtask'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'bugtask'::pg_catalog.regclass;


SELECT pg_catalog.setval('person_id_seq', 26, true);



SELECT pg_catalog.setval('emailaddress_id_seq', 22, true);



SELECT pg_catalog.setval('gpgkey_id_seq', 10, true);



SELECT pg_catalog.setval('archuserid_id_seq', 10, true);



SELECT pg_catalog.setval('wikiname_id_seq', 10, true);



SELECT pg_catalog.setval('jabberid_id_seq', 10, true);



SELECT pg_catalog.setval('ircid_id_seq', 9, true);



SELECT pg_catalog.setval('membership_id_seq', 8, true);



SELECT pg_catalog.setval('teamparticipation_id_seq', 23, true);



SELECT pg_catalog.setval('schema_id_seq', 4, true);



SELECT pg_catalog.setval('label_id_seq', 1, true);



SELECT pg_catalog.setval('project_id_seq', 8, true);



SELECT pg_catalog.setval('projectrelationship_id_seq', 1, false);



SELECT pg_catalog.setval('projectrole_id_seq', 1, false);



SELECT pg_catalog.setval('product_id_seq', 10, true);



SELECT pg_catalog.setval('productlabel_id_seq', 1, false);



SELECT pg_catalog.setval('productrole_id_seq', 1, false);



SELECT pg_catalog.setval('productseries_id_seq', 1, true);



SELECT pg_catalog.setval('productrelease_id_seq', 5, true);



SELECT pg_catalog.setval('productcvsmodule_id_seq', 1, false);



SELECT pg_catalog.setval('productbkbranch_id_seq', 1, false);



SELECT pg_catalog.setval('productsvnmodule_id_seq', 1, false);



SELECT pg_catalog.setval('archarchive_id_seq', 9, true);



SELECT pg_catalog.setval('archarchivelocation_id_seq', 1, false);



SELECT pg_catalog.setval('archnamespace_id_seq', 9, true);



SELECT pg_catalog.setval('branch_id_seq', 9, true);



SELECT pg_catalog.setval('changeset_id_seq', 1, false);



SELECT pg_catalog.setval('changesetfilename_id_seq', 1, false);



SELECT pg_catalog.setval('changesetfile_id_seq', 1, false);



SELECT pg_catalog.setval('changesetfilehash_id_seq', 1, false);



SELECT pg_catalog.setval('productbranchrelationship_id_seq', 1, false);



SELECT pg_catalog.setval('manifest_id_seq', 9, true);



SELECT pg_catalog.setval('manifestentry_id_seq', 1, false);



SELECT pg_catalog.setval('archconfig_id_seq', 1, false);



SELECT pg_catalog.setval('processorfamily_id_seq', 1, true);



SELECT pg_catalog.setval('processor_id_seq', 1, true);



SELECT pg_catalog.setval('builder_id_seq', 1, false);



SELECT pg_catalog.setval('component_id_seq', 1, true);



SELECT pg_catalog.setval('section_id_seq', 1, true);



SELECT pg_catalog.setval('distribution_id_seq', 5, true);



SELECT pg_catalog.setval('distrorelease_id_seq', 8, true);



SELECT pg_catalog.setval('distroarchrelease_id_seq', 1, true);



SELECT pg_catalog.setval('libraryfilecontent_id_seq', 1, false);



SELECT pg_catalog.setval('libraryfilealias_id_seq', 1, false);



SELECT pg_catalog.setval('sourcepackagename_id_seq', 9, true);



SELECT pg_catalog.setval('sourcepackage_id_seq', 12, true);



SELECT pg_catalog.setval('sourcepackagerelease_id_seq', 15, true);



SELECT pg_catalog.setval('build_id_seq', 2, true);



SELECT pg_catalog.setval('binarypackagename_id_seq', 8, true);



SELECT pg_catalog.setval('binarypackage_id_seq', 12, true);



SELECT pg_catalog.setval('packagepublishing_id_seq', 9, true);



SELECT pg_catalog.setval('packageselection_id_seq', 1, false);



SELECT pg_catalog.setval('coderelease_id_seq', 9, true);



SELECT pg_catalog.setval('osfile_id_seq', 1, false);



SELECT pg_catalog.setval('pomsgid_id_seq', 99, true);



SELECT pg_catalog.setval('potranslation_id_seq', 11, true);









SELECT pg_catalog.setval('license_id_seq', 1, true);



SELECT pg_catalog.setval('potemplate_id_seq', 2, true);



SELECT pg_catalog.setval('pofile_id_seq', 1, true);



SELECT pg_catalog.setval('pomsgset_id_seq', 10, true);



SELECT pg_catalog.setval('pomsgidsighting_id_seq', 21, true);



SELECT pg_catalog.setval('potranslationsighting_id_seq', 11, true);



SELECT pg_catalog.setval('pocomment_id_seq', 1, false);



SELECT pg_catalog.setval('translationeffort_id_seq', 1, false);



SELECT pg_catalog.setval('posubscription_id_seq', 1, false);



SELECT pg_catalog.setval('bug_id_seq', 3, true);



SELECT pg_catalog.setval('bugsubscription_id_seq', 5, true);



SELECT pg_catalog.setval('sourcepackagebugassignment_id_seq', 3, true);



SELECT pg_catalog.setval('productbugassignment_id_seq', 5, true);



SELECT pg_catalog.setval('bugactivity_id_seq', 1, true);



SELECT pg_catalog.setval('bugexternalref_id_seq', 4, true);



SELECT pg_catalog.setval('bugtrackertype_id_seq', 2, true);



SELECT pg_catalog.setval('bugtracker_id_seq', 3, true);



SELECT pg_catalog.setval('bugwatch_id_seq', 4, true);



SELECT pg_catalog.setval('message_id_seq', 6, true);



SELECT pg_catalog.setval('bugattachment_id_seq', 1, false);



SELECT pg_catalog.setval('sourcesource_id_seq', 1, false);



SELECT pg_catalog.setval('projectbugtracker_id_seq', 1, true);



SELECT pg_catalog.setval('distributionrole_id_seq', 7, true);



SELECT pg_catalog.setval('distroreleaserole_id_seq', 9, true);



SELECT pg_catalog.setval('componentselection_id_seq', 1, false);



SELECT pg_catalog.setval('sectionselection_id_seq', 1, false);



SELECT pg_catalog.setval('sourcepackagepublishing_id_seq', 2, true);



SELECT pg_catalog.setval('bugproductinfestation_id_seq', 1, false);



SELECT pg_catalog.setval('bugpackageinfestation_id_seq', 1, false);



SELECT pg_catalog.setval('distroreleasequeue_id_seq', 1, false);



SELECT pg_catalog.setval('distroreleasequeuesource_id_seq', 1, false);



SELECT pg_catalog.setval('distroreleasequeuebuild_id_seq', 1, false);



SELECT pg_catalog.setval('sourcepackagereleasefile_id_seq', 1, false);



SELECT pg_catalog.setval('binarypackagefile_id_seq', 1, false);



SELECT pg_catalog.setval('personlanguage_id_seq', 4, true);



SELECT pg_catalog.setval('potmsgset_id_seq', 18, true);



SELECT pg_catalog.setval('bounty_id_seq', 1, false);



SELECT pg_catalog.setval('bugmessage_id_seq', 5, true);



SELECT pg_catalog.setval('cveref_id_seq', 1, false);



SELECT pg_catalog.setval('karma_id_seq', 1, false);



SELECT pg_catalog.setval('spokenin_id_seq', 334, true);



SELECT pg_catalog.setval('sourcepackagerelationship_id_seq', 1, false);



SELECT pg_catalog.setval('sshkey_id_seq', 1, false);



SELECT pg_catalog.setval('bugtask_id_seq', 1, false);


