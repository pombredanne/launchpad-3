--
-- PostgreSQL database dump
--



--
-- Name: person; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp) VALUES (1, 'Mark Shuttleworth', 'Mark', 'Shuttleworth', NULL, NULL, NULL, NULL, NULL);
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp) VALUES (2, 'Robert Collins', 'Robert', 'Collins', NULL, NULL, NULL, NULL, NULL);
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp) VALUES (3, 'Dave Miller', 'Dave', 'Miller', NULL, NULL, NULL, NULL, NULL);
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp) VALUES (4, 'Colin Watson', 'Colin', 'Watson', NULL, NULL, NULL, NULL, NULL);
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp) VALUES (5, 'Scott James Remnant', 'Scott James', 'Remnant', NULL, NULL, NULL, NULL, NULL);
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp) VALUES (6, 'Jeff Waugh', 'Jeff', 'Waugh', NULL, NULL, NULL, NULL, NULL);
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp) VALUES (7, 'Andrew Bennetts', 'Andrew', 'Bennetts', NULL, NULL, NULL, NULL, NULL);
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp) VALUES (8, 'James Blackwell', 'James', 'Blackwell', NULL, NULL, NULL, NULL, NULL);
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp) VALUES (9, 'Christian Reis', 'Christian', 'Reis', NULL, NULL, NULL, NULL, NULL);
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp) VALUES (10, 'Alexander Limi', 'Alexander', 'Limi', NULL, NULL, NULL, NULL, NULL);
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp) VALUES (11, 'Steve Alexander', 'Steve', 'Alexander', NULL, NULL, NULL, NULL, NULL);
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp) VALUES (12, 'Sample Person', 'Sample', 'Person', 'K7Qmeansl6RbuPfulfcmyDQOzp70OxVh5Fcf', NULL, NULL, NULL, NULL);
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp) VALUES (13, 'Carlos Perelló Marín', 'Carlos', 'Perelló Marín', 'MdB+BoAdbza3BA6mIkMm6bFo1kv9hR2PKZ3U', NULL, NULL, NULL, NULL);
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp) VALUES (14, 'Dafydd Harries', 'Dafydd', 'Harries', 'EvSuSe4k4tkRHSp6p+g91vyQIwL5VJ3iTbRZ', NULL, NULL, NULL, NULL);
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp) VALUES (15, 'Lalo Martins', 'Lalo', 'Martins', 'K7Qmeansl6RbuPfulfcmyDQOzp70OxVh5Fcf', NULL, NULL, NULL, NULL);
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp) VALUES (16, 'Foo Bar', 'Foo', 'Bar', 'K7Qmeansl6RbuPfulfcmyDQOzp70OxVh5Fcf', NULL, NULL, NULL, NULL);
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp) VALUES (17, 'Ubuntu Team', NULL, NULL, NULL, 1, 'This Team is responsible for the Ubuntu Distribution', NULL, NULL);
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp) VALUES (18, 'Ubuntu Gnome Team', NULL, NULL, NULL, 1, 'This Team is responsible for the GNOME releases Issues on whole Ubuntu Distribution', NULL, NULL);
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp) VALUES (19, 'Warty Gnome Team', NULL, NULL, NULL, 1, 'This Team is responsible for GNOME release Issues on Warty Distribution Release', NULL, NULL);
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp) VALUES (20, 'Warty Security Team', NULL, NULL, NULL, 1, 'This Team is responsible for Security Issues on Warty Distribution Release', NULL, NULL);
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, karma, karmatimestamp) VALUES (21, 'Hoary Gnome Team', NULL, NULL, NULL, 1, 'This team is responsible for Security Issues on Hoary Distribution Release', NULL, NULL);


--
-- Name: emailaddress; Type: TABLE DATA; Schema: public; Owner: mark
--

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


--
-- Name: gpgkey; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO gpgkey (id, person, keyid, fingerprint, pubkey, revoked) VALUES (1, 1, '1024D/09F89725', 'XVHJ OU77 IYTD 0982 FTG6 OQFC 0GF8 09PO QW45 MJ76', '<-- sample pubkey ??? -->', false);
INSERT INTO gpgkey (id, person, keyid, fingerprint, pubkey, revoked) VALUES (2, 11, '1024D/09F89890', 'XVHJ OU77 IYTD 0981 FTG6 OQFC 0GF8 09PO QW45 MJ76', '<-- sample pubkey ??? -->', false);
INSERT INTO gpgkey (id, person, keyid, fingerprint, pubkey, revoked) VALUES (3, 10, '1024D/09F89321', 'XVHJ OU77 IYTD 0983 FTG6 OQFC 0GF8 09PO QW45 MJ76', '<-- sample pubkey ??? -->', false);
INSERT INTO gpgkey (id, person, keyid, fingerprint, pubkey, revoked) VALUES (4, 8, '1024D/09F89098', 'XVHJ OU77 IYTD 0984 FTG6 OQFC 0GF8 09PO QW45 MJ76', '<-- sample pubkey ??? -->', false);
INSERT INTO gpgkey (id, person, keyid, fingerprint, pubkey, revoked) VALUES (5, 9, '1024D/09F89123', 'XVHJ OU77 IYTD 0985 FTG6 OQFC 0GF8 09PO QW45 MJ76', '<-- sample pubkey ??? -->', false);
INSERT INTO gpgkey (id, person, keyid, fingerprint, pubkey, revoked) VALUES (6, 4, '1024D/09F89124', 'XVHJ OU77 IYTA 0985 FTG6 OQFC 0GF8 09PO QW45 MJ76', '<-- sample pubkey ??? -->', false);
INSERT INTO gpgkey (id, person, keyid, fingerprint, pubkey, revoked) VALUES (7, 5, '1024D/09F89125', 'XVHJ OU77 IYTQ 0985 FTG6 OQFC 0GF8 09PO QW45 MJ76', '<-- sample pubkey ??? -->', false);
INSERT INTO gpgkey (id, person, keyid, fingerprint, pubkey, revoked) VALUES (8, 7, '1024D/09F89126', 'XVHJ OU77 IYTX 0985 FTG6 OQFC 0GF8 09PO QW45 MJ76', '<-- sample pubkey ??? -->', false);
INSERT INTO gpgkey (id, person, keyid, fingerprint, pubkey, revoked) VALUES (9, 3, '1024D/09F89127', 'XVHJ OU77 IYTZ 0985 FTG6 OQFC 0GF8 09PO QW45 MJ76', '<-- sample pubkey ??? -->', false);
INSERT INTO gpgkey (id, person, keyid, fingerprint, pubkey, revoked) VALUES (10, 6, '1024D/09F89120', 'XVHJ OU77 IYTP 0985 FTG6 OQFC 0GF8 09PO QW45 MJ76', '<-- sample pubkey ??? -->', false);


--
-- Name: archuserid; Type: TABLE DATA; Schema: public; Owner: mark
--

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


--
-- Name: wikiname; Type: TABLE DATA; Schema: public; Owner: mark
--

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


--
-- Name: jabberid; Type: TABLE DATA; Schema: public; Owner: mark
--

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


--
-- Name: ircid; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO ircid (id, person, network, nickname) VALUES (1, 1, 'irc.freenode.net', 'mark');
INSERT INTO ircid (id, person, network, nickname) VALUES (2, 11, 'irc.freenode.net', 'SteveA');
INSERT INTO ircid (id, person, network, nickname) VALUES (3, 10, 'irc.freenode.net', 'limi');
INSERT INTO ircid (id, person, network, nickname) VALUES (4, 8, 'irc.freenode.net', 'jblack');
INSERT INTO ircid (id, person, network, nickname) VALUES (5, 3, 'irc.freenode.net', 'justdave');
INSERT INTO ircid (id, person, network, nickname) VALUES (6, 9, 'irc.freenode.net', 'kiko');
INSERT INTO ircid (id, person, network, nickname) VALUES (7, 4, 'irc.freenode.net', 'Kamion');
INSERT INTO ircid (id, person, network, nickname) VALUES (8, 5, 'irc.freenode.net', 'Keybuk');
INSERT INTO ircid (id, person, network, nickname) VALUES (9, 6, 'irc.freenode.net', 'jeff');


--
-- Name: membership; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO membership (id, person, team, role, status) VALUES (1, 1, 17, 1, 2);
INSERT INTO membership (id, person, team, role, status) VALUES (2, 11, 17, 2, 2);
INSERT INTO membership (id, person, team, role, status) VALUES (3, 10, 17, 2, 1);
INSERT INTO membership (id, person, team, role, status) VALUES (4, 4, 17, 2, 1);
INSERT INTO membership (id, person, team, role, status) VALUES (5, 7, 17, 2, 1);
INSERT INTO membership (id, person, team, role, status) VALUES (6, 3, 17, 2, 1);
INSERT INTO membership (id, person, team, role, status) VALUES (7, 1, 18, 1, 2);
INSERT INTO membership (id, person, team, role, status) VALUES (8, 6, 18, 2, 2);


--
-- Name: teamparticipation; Type: TABLE DATA; Schema: public; Owner: mark
--

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


--
-- Name: schema; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO "schema" (id, name, title, description, "owner", extensible) VALUES (1, 'Mark schema', 'TITLE', 'description', 1, true);
INSERT INTO "schema" (id, name, title, description, "owner", extensible) VALUES (2, 'schema', 'SCHEMA', 'description', 1, true);
INSERT INTO "schema" (id, name, title, description, "owner", extensible) VALUES (3, 'trema', 'XCHEMA', 'description', 1, true);
INSERT INTO "schema" (id, name, title, description, "owner", extensible) VALUES (4, 'enema', 'ENHEMA', 'description', 1, true);
INSERT INTO "schema" (id, name, title, description, "owner", extensible) VALUES (5, 'translation-languages', 'Translation Languages', 'Languages that a person can translate into', 13, false);


--
-- Name: label; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO label (id, "schema", name, title, description) VALUES (1, 1, 'blah', 'blah', 'blah');
INSERT INTO label (id, "schema", name, title, description) VALUES (2, 5, 'aa', 'Translates into Afar', 'A person with this label says that knows how to translate into Afar');
INSERT INTO label (id, "schema", name, title, description) VALUES (3, 5, 'ab', 'Translates into Abkhazian', 'A person with this label says that knows how to translate into Abkhazian');
INSERT INTO label (id, "schema", name, title, description) VALUES (4, 5, 'ace', 'Translates into Achinese', 'A person with this label says that knows how to translate into Achinese');
INSERT INTO label (id, "schema", name, title, description) VALUES (5, 5, 'ach', 'Translates into Acoli', 'A person with this label says that knows how to translate into Acoli');
INSERT INTO label (id, "schema", name, title, description) VALUES (6, 5, 'ada', 'Translates into Adangme', 'A person with this label says that knows how to translate into Adangme');
INSERT INTO label (id, "schema", name, title, description) VALUES (7, 5, 'ady', 'Translates into Adyghe; Adygei', 'A person with this label says that knows how to translate into Adyghe; Adygei');
INSERT INTO label (id, "schema", name, title, description) VALUES (8, 5, 'afa', 'Translates into Afro-Asiatic (Other)', 'A person with this label says that knows how to translate into Afro-Asiatic (Other)');
INSERT INTO label (id, "schema", name, title, description) VALUES (9, 5, 'afh', 'Translates into Afrihili', 'A person with this label says that knows how to translate into Afrihili');
INSERT INTO label (id, "schema", name, title, description) VALUES (10, 5, 'af', 'Translates into Afrikaans', 'A person with this label says that knows how to translate into Afrikaans');
INSERT INTO label (id, "schema", name, title, description) VALUES (11, 5, 'aka', 'Translates into Akan', 'A person with this label says that knows how to translate into Akan');
INSERT INTO label (id, "schema", name, title, description) VALUES (12, 5, 'ak', 'Translates into Akkadian', 'A person with this label says that knows how to translate into Akkadian');
INSERT INTO label (id, "schema", name, title, description) VALUES (13, 5, 'sq', 'Translates into Albanian', 'A person with this label says that knows how to translate into Albanian');
INSERT INTO label (id, "schema", name, title, description) VALUES (14, 5, 'ale', 'Translates into Aleut', 'A person with this label says that knows how to translate into Aleut');
INSERT INTO label (id, "schema", name, title, description) VALUES (15, 5, 'alg', 'Translates into Algonquian languages', 'A person with this label says that knows how to translate into Algonquian languages');
INSERT INTO label (id, "schema", name, title, description) VALUES (16, 5, 'am', 'Translates into Amharic', 'A person with this label says that knows how to translate into Amharic');
INSERT INTO label (id, "schema", name, title, description) VALUES (17, 5, 'ang', 'Translates into English, Old (ca.450-1100)', 'A person with this label says that knows how to translate into English, Old (ca.450-1100)');
INSERT INTO label (id, "schema", name, title, description) VALUES (18, 5, 'apa', 'Translates into Apache languages', 'A person with this label says that knows how to translate into Apache languages');
INSERT INTO label (id, "schema", name, title, description) VALUES (19, 5, 'ar', 'Translates into Arabic', 'A person with this label says that knows how to translate into Arabic');
INSERT INTO label (id, "schema", name, title, description) VALUES (20, 5, 'arc', 'Translates into Aramaic', 'A person with this label says that knows how to translate into Aramaic');
INSERT INTO label (id, "schema", name, title, description) VALUES (21, 5, 'an', 'Translates into Aragonese', 'A person with this label says that knows how to translate into Aragonese');
INSERT INTO label (id, "schema", name, title, description) VALUES (22, 5, 'hy', 'Translates into Armenian', 'A person with this label says that knows how to translate into Armenian');
INSERT INTO label (id, "schema", name, title, description) VALUES (23, 5, 'arn', 'Translates into Araucanian', 'A person with this label says that knows how to translate into Araucanian');
INSERT INTO label (id, "schema", name, title, description) VALUES (24, 5, 'arp', 'Translates into Arapaho', 'A person with this label says that knows how to translate into Arapaho');
INSERT INTO label (id, "schema", name, title, description) VALUES (25, 5, 'art', 'Translates into Artificial (Other)', 'A person with this label says that knows how to translate into Artificial (Other)');
INSERT INTO label (id, "schema", name, title, description) VALUES (26, 5, 'arw', 'Translates into Arawak', 'A person with this label says that knows how to translate into Arawak');
INSERT INTO label (id, "schema", name, title, description) VALUES (27, 5, 'as', 'Translates into Assamese', 'A person with this label says that knows how to translate into Assamese');
INSERT INTO label (id, "schema", name, title, description) VALUES (28, 5, 'ast', 'Translates into Asturian; Bable', 'A person with this label says that knows how to translate into Asturian; Bable');
INSERT INTO label (id, "schema", name, title, description) VALUES (29, 5, 'ath', 'Translates into Athapascan language', 'A person with this label says that knows how to translate into Athapascan language');
INSERT INTO label (id, "schema", name, title, description) VALUES (30, 5, 'aus', 'Translates into Australian languages', 'A person with this label says that knows how to translate into Australian languages');
INSERT INTO label (id, "schema", name, title, description) VALUES (31, 5, 'av', 'Translates into Avaric', 'A person with this label says that knows how to translate into Avaric');
INSERT INTO label (id, "schema", name, title, description) VALUES (32, 5, 'ae', 'Translates into Avestan', 'A person with this label says that knows how to translate into Avestan');
INSERT INTO label (id, "schema", name, title, description) VALUES (33, 5, 'awa', 'Translates into Awadhi', 'A person with this label says that knows how to translate into Awadhi');
INSERT INTO label (id, "schema", name, title, description) VALUES (34, 5, 'ay', 'Translates into Aymara', 'A person with this label says that knows how to translate into Aymara');
INSERT INTO label (id, "schema", name, title, description) VALUES (35, 5, 'az', 'Translates into Azerbaijani', 'A person with this label says that knows how to translate into Azerbaijani');
INSERT INTO label (id, "schema", name, title, description) VALUES (36, 5, 'bad', 'Translates into Banda', 'A person with this label says that knows how to translate into Banda');
INSERT INTO label (id, "schema", name, title, description) VALUES (37, 5, 'bai', 'Translates into Bamileke languages', 'A person with this label says that knows how to translate into Bamileke languages');
INSERT INTO label (id, "schema", name, title, description) VALUES (38, 5, 'ba', 'Translates into Bashkir', 'A person with this label says that knows how to translate into Bashkir');
INSERT INTO label (id, "schema", name, title, description) VALUES (39, 5, 'bal', 'Translates into Baluchi', 'A person with this label says that knows how to translate into Baluchi');
INSERT INTO label (id, "schema", name, title, description) VALUES (40, 5, 'bm', 'Translates into Bambara', 'A person with this label says that knows how to translate into Bambara');
INSERT INTO label (id, "schema", name, title, description) VALUES (41, 5, 'ban', 'Translates into Balinese', 'A person with this label says that knows how to translate into Balinese');
INSERT INTO label (id, "schema", name, title, description) VALUES (42, 5, 'eu', 'Translates into Basque', 'A person with this label says that knows how to translate into Basque');
INSERT INTO label (id, "schema", name, title, description) VALUES (43, 5, 'bas', 'Translates into Basa', 'A person with this label says that knows how to translate into Basa');
INSERT INTO label (id, "schema", name, title, description) VALUES (44, 5, 'bat', 'Translates into Baltic (Other)', 'A person with this label says that knows how to translate into Baltic (Other)');
INSERT INTO label (id, "schema", name, title, description) VALUES (45, 5, 'bej', 'Translates into Beja', 'A person with this label says that knows how to translate into Beja');
INSERT INTO label (id, "schema", name, title, description) VALUES (46, 5, 'be', 'Translates into Belarusian', 'A person with this label says that knows how to translate into Belarusian');
INSERT INTO label (id, "schema", name, title, description) VALUES (47, 5, 'bem', 'Translates into Bemba', 'A person with this label says that knows how to translate into Bemba');
INSERT INTO label (id, "schema", name, title, description) VALUES (48, 5, 'bn', 'Translates into Bengali', 'A person with this label says that knows how to translate into Bengali');
INSERT INTO label (id, "schema", name, title, description) VALUES (49, 5, 'ber', 'Translates into Berber (Other)', 'A person with this label says that knows how to translate into Berber (Other)');
INSERT INTO label (id, "schema", name, title, description) VALUES (50, 5, 'bho', 'Translates into Bhojpuri', 'A person with this label says that knows how to translate into Bhojpuri');
INSERT INTO label (id, "schema", name, title, description) VALUES (51, 5, 'bh', 'Translates into Bihari', 'A person with this label says that knows how to translate into Bihari');
INSERT INTO label (id, "schema", name, title, description) VALUES (52, 5, 'bik', 'Translates into Bikol', 'A person with this label says that knows how to translate into Bikol');
INSERT INTO label (id, "schema", name, title, description) VALUES (53, 5, 'bin', 'Translates into Bini', 'A person with this label says that knows how to translate into Bini');
INSERT INTO label (id, "schema", name, title, description) VALUES (54, 5, 'bi', 'Translates into Bislama', 'A person with this label says that knows how to translate into Bislama');
INSERT INTO label (id, "schema", name, title, description) VALUES (55, 5, 'bla', 'Translates into Siksika', 'A person with this label says that knows how to translate into Siksika');
INSERT INTO label (id, "schema", name, title, description) VALUES (56, 5, 'bnt', 'Translates into Bantu (Other)', 'A person with this label says that knows how to translate into Bantu (Other)');
INSERT INTO label (id, "schema", name, title, description) VALUES (57, 5, 'bs', 'Translates into Bosnian', 'A person with this label says that knows how to translate into Bosnian');
INSERT INTO label (id, "schema", name, title, description) VALUES (58, 5, 'bra', 'Translates into Braj', 'A person with this label says that knows how to translate into Braj');
INSERT INTO label (id, "schema", name, title, description) VALUES (59, 5, 'br', 'Translates into Breton', 'A person with this label says that knows how to translate into Breton');
INSERT INTO label (id, "schema", name, title, description) VALUES (60, 5, 'btk', 'Translates into Batak (Indonesia)', 'A person with this label says that knows how to translate into Batak (Indonesia)');
INSERT INTO label (id, "schema", name, title, description) VALUES (61, 5, 'bua', 'Translates into Buriat', 'A person with this label says that knows how to translate into Buriat');
INSERT INTO label (id, "schema", name, title, description) VALUES (62, 5, 'bug', 'Translates into Buginese', 'A person with this label says that knows how to translate into Buginese');
INSERT INTO label (id, "schema", name, title, description) VALUES (63, 5, 'bg', 'Translates into Bulgarian', 'A person with this label says that knows how to translate into Bulgarian');
INSERT INTO label (id, "schema", name, title, description) VALUES (64, 5, 'my', 'Translates into Burmese', 'A person with this label says that knows how to translate into Burmese');
INSERT INTO label (id, "schema", name, title, description) VALUES (65, 5, 'byn', 'Translates into Blin; Bilin', 'A person with this label says that knows how to translate into Blin; Bilin');
INSERT INTO label (id, "schema", name, title, description) VALUES (66, 5, 'cad', 'Translates into Caddo', 'A person with this label says that knows how to translate into Caddo');
INSERT INTO label (id, "schema", name, title, description) VALUES (67, 5, 'cai', 'Translates into Central American Indian (Other)', 'A person with this label says that knows how to translate into Central American Indian (Other)');
INSERT INTO label (id, "schema", name, title, description) VALUES (68, 5, 'car', 'Translates into Carib', 'A person with this label says that knows how to translate into Carib');
INSERT INTO label (id, "schema", name, title, description) VALUES (69, 5, 'ca', 'Translates into Catalan', 'A person with this label says that knows how to translate into Catalan');
INSERT INTO label (id, "schema", name, title, description) VALUES (70, 5, 'cau', 'Translates into Caucasian (Other)', 'A person with this label says that knows how to translate into Caucasian (Other)');
INSERT INTO label (id, "schema", name, title, description) VALUES (71, 5, 'ceb', 'Translates into Cebuano', 'A person with this label says that knows how to translate into Cebuano');
INSERT INTO label (id, "schema", name, title, description) VALUES (72, 5, 'cel', 'Translates into Celtic (Other)', 'A person with this label says that knows how to translate into Celtic (Other)');
INSERT INTO label (id, "schema", name, title, description) VALUES (73, 5, 'ch', 'Translates into Chamorro', 'A person with this label says that knows how to translate into Chamorro');
INSERT INTO label (id, "schema", name, title, description) VALUES (74, 5, 'chb', 'Translates into Chibcha', 'A person with this label says that knows how to translate into Chibcha');
INSERT INTO label (id, "schema", name, title, description) VALUES (75, 5, 'ce', 'Translates into Chechen', 'A person with this label says that knows how to translate into Chechen');
INSERT INTO label (id, "schema", name, title, description) VALUES (76, 5, 'chg', 'Translates into Chagatai', 'A person with this label says that knows how to translate into Chagatai');
INSERT INTO label (id, "schema", name, title, description) VALUES (77, 5, 'zh', 'Translates into Chinese', 'A person with this label says that knows how to translate into Chinese');
INSERT INTO label (id, "schema", name, title, description) VALUES (78, 5, 'chk', 'Translates into Chukese', 'A person with this label says that knows how to translate into Chukese');
INSERT INTO label (id, "schema", name, title, description) VALUES (79, 5, 'chm', 'Translates into Mari', 'A person with this label says that knows how to translate into Mari');
INSERT INTO label (id, "schema", name, title, description) VALUES (80, 5, 'chn', 'Translates into Chinook jargon', 'A person with this label says that knows how to translate into Chinook jargon');
INSERT INTO label (id, "schema", name, title, description) VALUES (81, 5, 'cho', 'Translates into Choctaw', 'A person with this label says that knows how to translate into Choctaw');
INSERT INTO label (id, "schema", name, title, description) VALUES (82, 5, 'chp', 'Translates into Chipewyan', 'A person with this label says that knows how to translate into Chipewyan');
INSERT INTO label (id, "schema", name, title, description) VALUES (83, 5, 'chr', 'Translates into Cherokee', 'A person with this label says that knows how to translate into Cherokee');
INSERT INTO label (id, "schema", name, title, description) VALUES (84, 5, 'chu', 'Translates into Church Slavic', 'A person with this label says that knows how to translate into Church Slavic');
INSERT INTO label (id, "schema", name, title, description) VALUES (85, 5, 'cv', 'Translates into Chuvash', 'A person with this label says that knows how to translate into Chuvash');
INSERT INTO label (id, "schema", name, title, description) VALUES (86, 5, 'chy', 'Translates into Cheyenne', 'A person with this label says that knows how to translate into Cheyenne');
INSERT INTO label (id, "schema", name, title, description) VALUES (87, 5, 'cmc', 'Translates into Chamic languages', 'A person with this label says that knows how to translate into Chamic languages');
INSERT INTO label (id, "schema", name, title, description) VALUES (88, 5, 'cop', 'Translates into Coptic', 'A person with this label says that knows how to translate into Coptic');
INSERT INTO label (id, "schema", name, title, description) VALUES (89, 5, 'kw', 'Translates into Cornish', 'A person with this label says that knows how to translate into Cornish');
INSERT INTO label (id, "schema", name, title, description) VALUES (90, 5, 'co', 'Translates into Corsican', 'A person with this label says that knows how to translate into Corsican');
INSERT INTO label (id, "schema", name, title, description) VALUES (91, 5, 'cpe', 'Translates into English-based (Other)', 'A person with this label says that knows how to translate into English-based (Other)');
INSERT INTO label (id, "schema", name, title, description) VALUES (92, 5, 'cpf', 'Translates into French-based (Other)', 'A person with this label says that knows how to translate into French-based (Other)');
INSERT INTO label (id, "schema", name, title, description) VALUES (93, 5, 'cpp', 'Translates into Portuguese-based (Other)', 'A person with this label says that knows how to translate into Portuguese-based (Other)');
INSERT INTO label (id, "schema", name, title, description) VALUES (94, 5, 'cr', 'Translates into Cree', 'A person with this label says that knows how to translate into Cree');
INSERT INTO label (id, "schema", name, title, description) VALUES (95, 5, 'crh', 'Translates into Crimean Turkish; Crimean Tatar', 'A person with this label says that knows how to translate into Crimean Turkish; Crimean Tatar');
INSERT INTO label (id, "schema", name, title, description) VALUES (96, 5, 'crp', 'Translates into Creoles and pidgins (Other)', 'A person with this label says that knows how to translate into Creoles and pidgins (Other)');
INSERT INTO label (id, "schema", name, title, description) VALUES (97, 5, 'csb', 'Translates into Kashubian', 'A person with this label says that knows how to translate into Kashubian');
INSERT INTO label (id, "schema", name, title, description) VALUES (98, 5, 'cus', 'Translates into Cushitic (Other)', 'A person with this label says that knows how to translate into Cushitic (Other)');
INSERT INTO label (id, "schema", name, title, description) VALUES (99, 5, 'cs', 'Translates into Czech', 'A person with this label says that knows how to translate into Czech');
INSERT INTO label (id, "schema", name, title, description) VALUES (100, 5, 'dak', 'Translates into Dakota', 'A person with this label says that knows how to translate into Dakota');
INSERT INTO label (id, "schema", name, title, description) VALUES (101, 5, 'da', 'Translates into Danish', 'A person with this label says that knows how to translate into Danish');
INSERT INTO label (id, "schema", name, title, description) VALUES (102, 5, 'dar', 'Translates into Dargwa', 'A person with this label says that knows how to translate into Dargwa');
INSERT INTO label (id, "schema", name, title, description) VALUES (103, 5, 'del', 'Translates into Delaware', 'A person with this label says that knows how to translate into Delaware');
INSERT INTO label (id, "schema", name, title, description) VALUES (104, 5, 'den', 'Translates into Slave (Athapascan)', 'A person with this label says that knows how to translate into Slave (Athapascan)');
INSERT INTO label (id, "schema", name, title, description) VALUES (105, 5, 'dgr', 'Translates into Dogrib', 'A person with this label says that knows how to translate into Dogrib');
INSERT INTO label (id, "schema", name, title, description) VALUES (106, 5, 'din', 'Translates into Dinka', 'A person with this label says that knows how to translate into Dinka');
INSERT INTO label (id, "schema", name, title, description) VALUES (107, 5, 'dv', 'Translates into Divehi', 'A person with this label says that knows how to translate into Divehi');
INSERT INTO label (id, "schema", name, title, description) VALUES (108, 5, 'doi', 'Translates into Dogri', 'A person with this label says that knows how to translate into Dogri');
INSERT INTO label (id, "schema", name, title, description) VALUES (109, 5, 'dra', 'Translates into Dravidian (Other)', 'A person with this label says that knows how to translate into Dravidian (Other)');
INSERT INTO label (id, "schema", name, title, description) VALUES (110, 5, 'dsb', 'Translates into Lower Sorbian', 'A person with this label says that knows how to translate into Lower Sorbian');
INSERT INTO label (id, "schema", name, title, description) VALUES (111, 5, 'dua', 'Translates into Duala', 'A person with this label says that knows how to translate into Duala');
INSERT INTO label (id, "schema", name, title, description) VALUES (112, 5, 'dum', 'Translates into Dutch, Middle (ca. 1050-1350)', 'A person with this label says that knows how to translate into Dutch, Middle (ca. 1050-1350)');
INSERT INTO label (id, "schema", name, title, description) VALUES (113, 5, 'nl', 'Translates into Dutch', 'A person with this label says that knows how to translate into Dutch');
INSERT INTO label (id, "schema", name, title, description) VALUES (114, 5, 'dyu', 'Translates into Dyula', 'A person with this label says that knows how to translate into Dyula');
INSERT INTO label (id, "schema", name, title, description) VALUES (115, 5, 'dz', 'Translates into Dzongkha', 'A person with this label says that knows how to translate into Dzongkha');
INSERT INTO label (id, "schema", name, title, description) VALUES (116, 5, 'efi', 'Translates into Efik', 'A person with this label says that knows how to translate into Efik');
INSERT INTO label (id, "schema", name, title, description) VALUES (117, 5, 'egy', 'Translates into Egyptian (Ancient)', 'A person with this label says that knows how to translate into Egyptian (Ancient)');
INSERT INTO label (id, "schema", name, title, description) VALUES (118, 5, 'eka', 'Translates into Ekajuk', 'A person with this label says that knows how to translate into Ekajuk');
INSERT INTO label (id, "schema", name, title, description) VALUES (119, 5, 'elx', 'Translates into Elamite', 'A person with this label says that knows how to translate into Elamite');
INSERT INTO label (id, "schema", name, title, description) VALUES (120, 5, 'en', 'Translates into English', 'A person with this label says that knows how to translate into English');
INSERT INTO label (id, "schema", name, title, description) VALUES (121, 5, 'enm', 'Translates into English, Middle (1100-1500)', 'A person with this label says that knows how to translate into English, Middle (1100-1500)');
INSERT INTO label (id, "schema", name, title, description) VALUES (122, 5, 'eo', 'Translates into Esperanto', 'A person with this label says that knows how to translate into Esperanto');
INSERT INTO label (id, "schema", name, title, description) VALUES (123, 5, 'et', 'Translates into Estonian', 'A person with this label says that knows how to translate into Estonian');
INSERT INTO label (id, "schema", name, title, description) VALUES (124, 5, 'ee', 'Translates into Ewe', 'A person with this label says that knows how to translate into Ewe');
INSERT INTO label (id, "schema", name, title, description) VALUES (125, 5, 'ewo', 'Translates into Ewondo', 'A person with this label says that knows how to translate into Ewondo');
INSERT INTO label (id, "schema", name, title, description) VALUES (126, 5, 'fan', 'Translates into Fang', 'A person with this label says that knows how to translate into Fang');
INSERT INTO label (id, "schema", name, title, description) VALUES (127, 5, 'fo', 'Translates into Faroese', 'A person with this label says that knows how to translate into Faroese');
INSERT INTO label (id, "schema", name, title, description) VALUES (128, 5, 'fat', 'Translates into Fanti', 'A person with this label says that knows how to translate into Fanti');
INSERT INTO label (id, "schema", name, title, description) VALUES (129, 5, 'fj', 'Translates into Fijian', 'A person with this label says that knows how to translate into Fijian');
INSERT INTO label (id, "schema", name, title, description) VALUES (130, 5, 'fi', 'Translates into Finnish', 'A person with this label says that knows how to translate into Finnish');
INSERT INTO label (id, "schema", name, title, description) VALUES (131, 5, 'fiu', 'Translates into Finno-Ugrian (Other)', 'A person with this label says that knows how to translate into Finno-Ugrian (Other)');
INSERT INTO label (id, "schema", name, title, description) VALUES (132, 5, 'fon', 'Translates into Fon', 'A person with this label says that knows how to translate into Fon');
INSERT INTO label (id, "schema", name, title, description) VALUES (133, 5, 'fr', 'Translates into French', 'A person with this label says that knows how to translate into French');
INSERT INTO label (id, "schema", name, title, description) VALUES (134, 5, 'frm', 'Translates into French, Middle (ca.1400-1600)', 'A person with this label says that knows how to translate into French, Middle (ca.1400-1600)');
INSERT INTO label (id, "schema", name, title, description) VALUES (135, 5, 'fro', 'Translates into French, Old (842-ca.1400)', 'A person with this label says that knows how to translate into French, Old (842-ca.1400)');
INSERT INTO label (id, "schema", name, title, description) VALUES (136, 5, 'fy', 'Translates into Frisian', 'A person with this label says that knows how to translate into Frisian');
INSERT INTO label (id, "schema", name, title, description) VALUES (137, 5, 'ff', 'Translates into Fulah', 'A person with this label says that knows how to translate into Fulah');
INSERT INTO label (id, "schema", name, title, description) VALUES (138, 5, 'fur', 'Translates into Friulian', 'A person with this label says that knows how to translate into Friulian');
INSERT INTO label (id, "schema", name, title, description) VALUES (139, 5, 'gaa', 'Translates into Ga', 'A person with this label says that knows how to translate into Ga');
INSERT INTO label (id, "schema", name, title, description) VALUES (140, 5, 'gay', 'Translates into Gayo', 'A person with this label says that knows how to translate into Gayo');
INSERT INTO label (id, "schema", name, title, description) VALUES (141, 5, 'gba', 'Translates into Gbaya', 'A person with this label says that knows how to translate into Gbaya');
INSERT INTO label (id, "schema", name, title, description) VALUES (142, 5, 'gem', 'Translates into Germanic (Other)', 'A person with this label says that knows how to translate into Germanic (Other)');
INSERT INTO label (id, "schema", name, title, description) VALUES (143, 5, 'ka', 'Translates into Georgian', 'A person with this label says that knows how to translate into Georgian');
INSERT INTO label (id, "schema", name, title, description) VALUES (144, 5, 'de', 'Translates into German', 'A person with this label says that knows how to translate into German');
INSERT INTO label (id, "schema", name, title, description) VALUES (145, 5, 'gez', 'Translates into Geez', 'A person with this label says that knows how to translate into Geez');
INSERT INTO label (id, "schema", name, title, description) VALUES (146, 5, 'gil', 'Translates into Gilbertese', 'A person with this label says that knows how to translate into Gilbertese');
INSERT INTO label (id, "schema", name, title, description) VALUES (147, 5, 'gd', 'Translates into Gaelic; Scottish', 'A person with this label says that knows how to translate into Gaelic; Scottish');
INSERT INTO label (id, "schema", name, title, description) VALUES (148, 5, 'ga', 'Translates into Irish', 'A person with this label says that knows how to translate into Irish');
INSERT INTO label (id, "schema", name, title, description) VALUES (149, 5, 'gl', 'Translates into Gallegan', 'A person with this label says that knows how to translate into Gallegan');
INSERT INTO label (id, "schema", name, title, description) VALUES (150, 5, 'gv', 'Translates into Manx', 'A person with this label says that knows how to translate into Manx');
INSERT INTO label (id, "schema", name, title, description) VALUES (151, 5, 'gmh', 'Translates into German, Middle High (ca.1050-1500)', 'A person with this label says that knows how to translate into German, Middle High (ca.1050-1500)');
INSERT INTO label (id, "schema", name, title, description) VALUES (152, 5, 'goh', 'Translates into German, Old High (ca.750-1050)', 'A person with this label says that knows how to translate into German, Old High (ca.750-1050)');
INSERT INTO label (id, "schema", name, title, description) VALUES (153, 5, 'gon', 'Translates into Gondi', 'A person with this label says that knows how to translate into Gondi');
INSERT INTO label (id, "schema", name, title, description) VALUES (154, 5, 'gor', 'Translates into Gorontalo', 'A person with this label says that knows how to translate into Gorontalo');
INSERT INTO label (id, "schema", name, title, description) VALUES (155, 5, 'got', 'Translates into Gothic', 'A person with this label says that knows how to translate into Gothic');
INSERT INTO label (id, "schema", name, title, description) VALUES (156, 5, 'grb', 'Translates into Grebo', 'A person with this label says that knows how to translate into Grebo');
INSERT INTO label (id, "schema", name, title, description) VALUES (157, 5, 'grc', 'Translates into Greek, Ancient (to 1453)', 'A person with this label says that knows how to translate into Greek, Ancient (to 1453)');
INSERT INTO label (id, "schema", name, title, description) VALUES (158, 5, 'el', 'Translates into Greek, Modern (1453-)', 'A person with this label says that knows how to translate into Greek, Modern (1453-)');
INSERT INTO label (id, "schema", name, title, description) VALUES (159, 5, 'gn', 'Translates into Guarani', 'A person with this label says that knows how to translate into Guarani');
INSERT INTO label (id, "schema", name, title, description) VALUES (160, 5, 'gu', 'Translates into Gujarati', 'A person with this label says that knows how to translate into Gujarati');
INSERT INTO label (id, "schema", name, title, description) VALUES (161, 5, 'gwi', 'Translates into Gwichin', 'A person with this label says that knows how to translate into Gwichin');
INSERT INTO label (id, "schema", name, title, description) VALUES (162, 5, 'hai', 'Translates into Haida', 'A person with this label says that knows how to translate into Haida');
INSERT INTO label (id, "schema", name, title, description) VALUES (163, 5, 'ht', 'Translates into Haitian; Haitian Creole', 'A person with this label says that knows how to translate into Haitian; Haitian Creole');
INSERT INTO label (id, "schema", name, title, description) VALUES (164, 5, 'ha', 'Translates into Hausa', 'A person with this label says that knows how to translate into Hausa');
INSERT INTO label (id, "schema", name, title, description) VALUES (165, 5, 'haw', 'Translates into Hawaiian', 'A person with this label says that knows how to translate into Hawaiian');
INSERT INTO label (id, "schema", name, title, description) VALUES (166, 5, 'he', 'Translates into Hebrew', 'A person with this label says that knows how to translate into Hebrew');
INSERT INTO label (id, "schema", name, title, description) VALUES (167, 5, 'hz', 'Translates into Herero', 'A person with this label says that knows how to translate into Herero');
INSERT INTO label (id, "schema", name, title, description) VALUES (168, 5, 'hil', 'Translates into Hiligaynon', 'A person with this label says that knows how to translate into Hiligaynon');
INSERT INTO label (id, "schema", name, title, description) VALUES (169, 5, 'him', 'Translates into Himachali', 'A person with this label says that knows how to translate into Himachali');
INSERT INTO label (id, "schema", name, title, description) VALUES (170, 5, 'hi', 'Translates into Hindi', 'A person with this label says that knows how to translate into Hindi');
INSERT INTO label (id, "schema", name, title, description) VALUES (171, 5, 'hit', 'Translates into Hittite', 'A person with this label says that knows how to translate into Hittite');
INSERT INTO label (id, "schema", name, title, description) VALUES (172, 5, 'hmn', 'Translates into Hmong', 'A person with this label says that knows how to translate into Hmong');
INSERT INTO label (id, "schema", name, title, description) VALUES (173, 5, 'ho', 'Translates into Hiri', 'A person with this label says that knows how to translate into Hiri');
INSERT INTO label (id, "schema", name, title, description) VALUES (174, 5, 'hsb', 'Translates into Upper Sorbian', 'A person with this label says that knows how to translate into Upper Sorbian');
INSERT INTO label (id, "schema", name, title, description) VALUES (175, 5, 'hu', 'Translates into Hungarian', 'A person with this label says that knows how to translate into Hungarian');
INSERT INTO label (id, "schema", name, title, description) VALUES (176, 5, 'hup', 'Translates into Hupa', 'A person with this label says that knows how to translate into Hupa');
INSERT INTO label (id, "schema", name, title, description) VALUES (177, 5, 'iba', 'Translates into Iban', 'A person with this label says that knows how to translate into Iban');
INSERT INTO label (id, "schema", name, title, description) VALUES (178, 5, 'ig', 'Translates into Igbo', 'A person with this label says that knows how to translate into Igbo');
INSERT INTO label (id, "schema", name, title, description) VALUES (179, 5, 'is', 'Translates into Icelandic', 'A person with this label says that knows how to translate into Icelandic');
INSERT INTO label (id, "schema", name, title, description) VALUES (180, 5, 'io', 'Translates into Ido', 'A person with this label says that knows how to translate into Ido');
INSERT INTO label (id, "schema", name, title, description) VALUES (181, 5, 'ii', 'Translates into Sichuan Yi', 'A person with this label says that knows how to translate into Sichuan Yi');
INSERT INTO label (id, "schema", name, title, description) VALUES (182, 5, 'ijo', 'Translates into Ijo', 'A person with this label says that knows how to translate into Ijo');
INSERT INTO label (id, "schema", name, title, description) VALUES (183, 5, 'iu', 'Translates into Inuktitut', 'A person with this label says that knows how to translate into Inuktitut');
INSERT INTO label (id, "schema", name, title, description) VALUES (184, 5, 'ie', 'Translates into Interlingue', 'A person with this label says that knows how to translate into Interlingue');
INSERT INTO label (id, "schema", name, title, description) VALUES (185, 5, 'ilo', 'Translates into Iloko', 'A person with this label says that knows how to translate into Iloko');
INSERT INTO label (id, "schema", name, title, description) VALUES (186, 5, 'ia', 'Translates into Interlingua', 'A person with this label says that knows how to translate into Interlingua');
INSERT INTO label (id, "schema", name, title, description) VALUES (187, 5, 'inc', 'Translates into Indic (Other)', 'A person with this label says that knows how to translate into Indic (Other)');
INSERT INTO label (id, "schema", name, title, description) VALUES (188, 5, 'id', 'Translates into Indonesian', 'A person with this label says that knows how to translate into Indonesian');
INSERT INTO label (id, "schema", name, title, description) VALUES (189, 5, 'ine', 'Translates into Indo-European (Other)', 'A person with this label says that knows how to translate into Indo-European (Other)');
INSERT INTO label (id, "schema", name, title, description) VALUES (190, 5, 'inh', 'Translates into Ingush', 'A person with this label says that knows how to translate into Ingush');
INSERT INTO label (id, "schema", name, title, description) VALUES (191, 5, 'ik', 'Translates into Inupiaq', 'A person with this label says that knows how to translate into Inupiaq');
INSERT INTO label (id, "schema", name, title, description) VALUES (192, 5, 'ira', 'Translates into Iranian (Other)', 'A person with this label says that knows how to translate into Iranian (Other)');
INSERT INTO label (id, "schema", name, title, description) VALUES (193, 5, 'iro', 'Translates into Iroquoian languages', 'A person with this label says that knows how to translate into Iroquoian languages');
INSERT INTO label (id, "schema", name, title, description) VALUES (194, 5, 'it', 'Translates into Italian', 'A person with this label says that knows how to translate into Italian');
INSERT INTO label (id, "schema", name, title, description) VALUES (195, 5, 'jv', 'Translates into Javanese', 'A person with this label says that knows how to translate into Javanese');
INSERT INTO label (id, "schema", name, title, description) VALUES (196, 5, 'jbo', 'Translates into Lojban', 'A person with this label says that knows how to translate into Lojban');
INSERT INTO label (id, "schema", name, title, description) VALUES (197, 5, 'ja', 'Translates into Japanese', 'A person with this label says that knows how to translate into Japanese');
INSERT INTO label (id, "schema", name, title, description) VALUES (198, 5, 'jpr', 'Translates into Judeo-Persian', 'A person with this label says that knows how to translate into Judeo-Persian');
INSERT INTO label (id, "schema", name, title, description) VALUES (199, 5, 'jrb', 'Translates into Judeo-Arabic', 'A person with this label says that knows how to translate into Judeo-Arabic');
INSERT INTO label (id, "schema", name, title, description) VALUES (200, 5, 'kaa', 'Translates into Kara-Kalpak', 'A person with this label says that knows how to translate into Kara-Kalpak');
INSERT INTO label (id, "schema", name, title, description) VALUES (201, 5, 'kab', 'Translates into Kabyle', 'A person with this label says that knows how to translate into Kabyle');
INSERT INTO label (id, "schema", name, title, description) VALUES (202, 5, 'kac', 'Translates into Kachin', 'A person with this label says that knows how to translate into Kachin');
INSERT INTO label (id, "schema", name, title, description) VALUES (203, 5, 'kl', 'Translates into Greenlandic (Kalaallisut)', 'A person with this label says that knows how to translate into Greenlandic (Kalaallisut)');
INSERT INTO label (id, "schema", name, title, description) VALUES (204, 5, 'kam', 'Translates into Kamba', 'A person with this label says that knows how to translate into Kamba');
INSERT INTO label (id, "schema", name, title, description) VALUES (205, 5, 'kn', 'Translates into Kannada', 'A person with this label says that knows how to translate into Kannada');
INSERT INTO label (id, "schema", name, title, description) VALUES (206, 5, 'kar', 'Translates into Karen', 'A person with this label says that knows how to translate into Karen');
INSERT INTO label (id, "schema", name, title, description) VALUES (207, 5, 'ks', 'Translates into Kashmiri', 'A person with this label says that knows how to translate into Kashmiri');
INSERT INTO label (id, "schema", name, title, description) VALUES (208, 5, 'kr', 'Translates into Kanuri', 'A person with this label says that knows how to translate into Kanuri');
INSERT INTO label (id, "schema", name, title, description) VALUES (209, 5, 'kaw', 'Translates into Kawi', 'A person with this label says that knows how to translate into Kawi');
INSERT INTO label (id, "schema", name, title, description) VALUES (210, 5, 'kk', 'Translates into Kazakh', 'A person with this label says that knows how to translate into Kazakh');
INSERT INTO label (id, "schema", name, title, description) VALUES (211, 5, 'kbd', 'Translates into Kabardian', 'A person with this label says that knows how to translate into Kabardian');
INSERT INTO label (id, "schema", name, title, description) VALUES (212, 5, 'kha', 'Translates into Khazi', 'A person with this label says that knows how to translate into Khazi');
INSERT INTO label (id, "schema", name, title, description) VALUES (213, 5, 'khi', 'Translates into Khoisan (Other)', 'A person with this label says that knows how to translate into Khoisan (Other)');
INSERT INTO label (id, "schema", name, title, description) VALUES (214, 5, 'km', 'Translates into Khmer', 'A person with this label says that knows how to translate into Khmer');
INSERT INTO label (id, "schema", name, title, description) VALUES (215, 5, 'kho', 'Translates into Khotanese', 'A person with this label says that knows how to translate into Khotanese');
INSERT INTO label (id, "schema", name, title, description) VALUES (216, 5, 'ki', 'Translates into Kikuyu', 'A person with this label says that knows how to translate into Kikuyu');
INSERT INTO label (id, "schema", name, title, description) VALUES (217, 5, 'rw', 'Translates into Kinyarwanda', 'A person with this label says that knows how to translate into Kinyarwanda');
INSERT INTO label (id, "schema", name, title, description) VALUES (218, 5, 'ky', 'Translates into Kirghiz', 'A person with this label says that knows how to translate into Kirghiz');
INSERT INTO label (id, "schema", name, title, description) VALUES (219, 5, 'kmb', 'Translates into Kimbundu', 'A person with this label says that knows how to translate into Kimbundu');
INSERT INTO label (id, "schema", name, title, description) VALUES (220, 5, 'kok', 'Translates into Konkani', 'A person with this label says that knows how to translate into Konkani');
INSERT INTO label (id, "schema", name, title, description) VALUES (221, 5, 'kv', 'Translates into Komi', 'A person with this label says that knows how to translate into Komi');
INSERT INTO label (id, "schema", name, title, description) VALUES (222, 5, 'kg', 'Translates into Kongo', 'A person with this label says that knows how to translate into Kongo');
INSERT INTO label (id, "schema", name, title, description) VALUES (223, 5, 'ko', 'Translates into Korean', 'A person with this label says that knows how to translate into Korean');
INSERT INTO label (id, "schema", name, title, description) VALUES (224, 5, 'kos', 'Translates into Kosraean', 'A person with this label says that knows how to translate into Kosraean');
INSERT INTO label (id, "schema", name, title, description) VALUES (225, 5, 'kpe', 'Translates into Kpelle', 'A person with this label says that knows how to translate into Kpelle');
INSERT INTO label (id, "schema", name, title, description) VALUES (226, 5, 'krc', 'Translates into Karachay-Balkar', 'A person with this label says that knows how to translate into Karachay-Balkar');
INSERT INTO label (id, "schema", name, title, description) VALUES (227, 5, 'kro', 'Translates into Kru', 'A person with this label says that knows how to translate into Kru');
INSERT INTO label (id, "schema", name, title, description) VALUES (228, 5, 'kru', 'Translates into Kurukh', 'A person with this label says that knows how to translate into Kurukh');
INSERT INTO label (id, "schema", name, title, description) VALUES (229, 5, 'kj', 'Translates into Kuanyama', 'A person with this label says that knows how to translate into Kuanyama');
INSERT INTO label (id, "schema", name, title, description) VALUES (230, 5, 'kum', 'Translates into Kumyk', 'A person with this label says that knows how to translate into Kumyk');
INSERT INTO label (id, "schema", name, title, description) VALUES (231, 5, 'ku', 'Translates into Kurdish', 'A person with this label says that knows how to translate into Kurdish');
INSERT INTO label (id, "schema", name, title, description) VALUES (232, 5, 'kut', 'Translates into Kutenai', 'A person with this label says that knows how to translate into Kutenai');
INSERT INTO label (id, "schema", name, title, description) VALUES (233, 5, 'lad', 'Translates into Ladino', 'A person with this label says that knows how to translate into Ladino');
INSERT INTO label (id, "schema", name, title, description) VALUES (234, 5, 'lah', 'Translates into Lahnda', 'A person with this label says that knows how to translate into Lahnda');
INSERT INTO label (id, "schema", name, title, description) VALUES (235, 5, 'lam', 'Translates into Lamba', 'A person with this label says that knows how to translate into Lamba');
INSERT INTO label (id, "schema", name, title, description) VALUES (236, 5, 'lo', 'Translates into Lao', 'A person with this label says that knows how to translate into Lao');
INSERT INTO label (id, "schema", name, title, description) VALUES (237, 5, 'la', 'Translates into Latin', 'A person with this label says that knows how to translate into Latin');
INSERT INTO label (id, "schema", name, title, description) VALUES (238, 5, 'lv', 'Translates into Latvian', 'A person with this label says that knows how to translate into Latvian');
INSERT INTO label (id, "schema", name, title, description) VALUES (239, 5, 'lez', 'Translates into Lezghian', 'A person with this label says that knows how to translate into Lezghian');
INSERT INTO label (id, "schema", name, title, description) VALUES (240, 5, 'li', 'Translates into Limburgian', 'A person with this label says that knows how to translate into Limburgian');
INSERT INTO label (id, "schema", name, title, description) VALUES (241, 5, 'ln', 'Translates into Lingala', 'A person with this label says that knows how to translate into Lingala');
INSERT INTO label (id, "schema", name, title, description) VALUES (242, 5, 'lt', 'Translates into Lithuanian', 'A person with this label says that knows how to translate into Lithuanian');
INSERT INTO label (id, "schema", name, title, description) VALUES (243, 5, 'lol', 'Translates into Mongo', 'A person with this label says that knows how to translate into Mongo');
INSERT INTO label (id, "schema", name, title, description) VALUES (244, 5, 'loz', 'Translates into Lozi', 'A person with this label says that knows how to translate into Lozi');
INSERT INTO label (id, "schema", name, title, description) VALUES (245, 5, 'lb', 'Translates into Luxembourgish', 'A person with this label says that knows how to translate into Luxembourgish');
INSERT INTO label (id, "schema", name, title, description) VALUES (246, 5, 'lua', 'Translates into Luba-Lulua', 'A person with this label says that knows how to translate into Luba-Lulua');
INSERT INTO label (id, "schema", name, title, description) VALUES (247, 5, 'lu', 'Translates into Luba-Katanga', 'A person with this label says that knows how to translate into Luba-Katanga');
INSERT INTO label (id, "schema", name, title, description) VALUES (248, 5, 'lg', 'Translates into Ganda', 'A person with this label says that knows how to translate into Ganda');
INSERT INTO label (id, "schema", name, title, description) VALUES (249, 5, 'lui', 'Translates into Luiseno', 'A person with this label says that knows how to translate into Luiseno');
INSERT INTO label (id, "schema", name, title, description) VALUES (250, 5, 'lun', 'Translates into Lunda', 'A person with this label says that knows how to translate into Lunda');
INSERT INTO label (id, "schema", name, title, description) VALUES (251, 5, 'luo', 'Translates into Luo (Kenya and Tanzania)', 'A person with this label says that knows how to translate into Luo (Kenya and Tanzania)');
INSERT INTO label (id, "schema", name, title, description) VALUES (252, 5, 'lus', 'Translates into Lushai', 'A person with this label says that knows how to translate into Lushai');
INSERT INTO label (id, "schema", name, title, description) VALUES (253, 5, 'mk', 'Translates into Macedonian', 'A person with this label says that knows how to translate into Macedonian');
INSERT INTO label (id, "schema", name, title, description) VALUES (254, 5, 'mad', 'Translates into Madurese', 'A person with this label says that knows how to translate into Madurese');
INSERT INTO label (id, "schema", name, title, description) VALUES (255, 5, 'mag', 'Translates into Magahi', 'A person with this label says that knows how to translate into Magahi');
INSERT INTO label (id, "schema", name, title, description) VALUES (256, 5, 'mh', 'Translates into Marshallese', 'A person with this label says that knows how to translate into Marshallese');
INSERT INTO label (id, "schema", name, title, description) VALUES (257, 5, 'mai', 'Translates into Maithili', 'A person with this label says that knows how to translate into Maithili');
INSERT INTO label (id, "schema", name, title, description) VALUES (258, 5, 'mak', 'Translates into Makasar', 'A person with this label says that knows how to translate into Makasar');
INSERT INTO label (id, "schema", name, title, description) VALUES (259, 5, 'ml', 'Translates into Malayalam', 'A person with this label says that knows how to translate into Malayalam');
INSERT INTO label (id, "schema", name, title, description) VALUES (260, 5, 'man', 'Translates into Mandingo', 'A person with this label says that knows how to translate into Mandingo');
INSERT INTO label (id, "schema", name, title, description) VALUES (261, 5, 'mi', 'Translates into Maori', 'A person with this label says that knows how to translate into Maori');
INSERT INTO label (id, "schema", name, title, description) VALUES (262, 5, 'map', 'Translates into Austronesian (Other)', 'A person with this label says that knows how to translate into Austronesian (Other)');
INSERT INTO label (id, "schema", name, title, description) VALUES (263, 5, 'mr', 'Translates into Marathi', 'A person with this label says that knows how to translate into Marathi');
INSERT INTO label (id, "schema", name, title, description) VALUES (264, 5, 'mas', 'Translates into Masai', 'A person with this label says that knows how to translate into Masai');
INSERT INTO label (id, "schema", name, title, description) VALUES (265, 5, 'ms', 'Translates into Malay', 'A person with this label says that knows how to translate into Malay');
INSERT INTO label (id, "schema", name, title, description) VALUES (266, 5, 'mdf', 'Translates into Moksha', 'A person with this label says that knows how to translate into Moksha');
INSERT INTO label (id, "schema", name, title, description) VALUES (267, 5, 'mdr', 'Translates into Mandar', 'A person with this label says that knows how to translate into Mandar');
INSERT INTO label (id, "schema", name, title, description) VALUES (268, 5, 'men', 'Translates into Mende', 'A person with this label says that knows how to translate into Mende');
INSERT INTO label (id, "schema", name, title, description) VALUES (269, 5, 'mga', 'Translates into Irish, Middle (900-1200)', 'A person with this label says that knows how to translate into Irish, Middle (900-1200)');
INSERT INTO label (id, "schema", name, title, description) VALUES (270, 5, 'mic', 'Translates into Micmac', 'A person with this label says that knows how to translate into Micmac');
INSERT INTO label (id, "schema", name, title, description) VALUES (271, 5, 'min', 'Translates into Minangkabau', 'A person with this label says that knows how to translate into Minangkabau');
INSERT INTO label (id, "schema", name, title, description) VALUES (272, 5, 'mis', 'Translates into Miscellaneous languages', 'A person with this label says that knows how to translate into Miscellaneous languages');
INSERT INTO label (id, "schema", name, title, description) VALUES (273, 5, 'mkh', 'Translates into Mon-Khmer (Other)', 'A person with this label says that knows how to translate into Mon-Khmer (Other)');
INSERT INTO label (id, "schema", name, title, description) VALUES (274, 5, 'mg', 'Translates into Malagasy', 'A person with this label says that knows how to translate into Malagasy');
INSERT INTO label (id, "schema", name, title, description) VALUES (275, 5, 'mt', 'Translates into Maltese', 'A person with this label says that knows how to translate into Maltese');
INSERT INTO label (id, "schema", name, title, description) VALUES (276, 5, 'mnc', 'Translates into Manchu', 'A person with this label says that knows how to translate into Manchu');
INSERT INTO label (id, "schema", name, title, description) VALUES (277, 5, 'mno', 'Translates into Manobo languages', 'A person with this label says that knows how to translate into Manobo languages');
INSERT INTO label (id, "schema", name, title, description) VALUES (278, 5, 'moh', 'Translates into Mohawk', 'A person with this label says that knows how to translate into Mohawk');
INSERT INTO label (id, "schema", name, title, description) VALUES (279, 5, 'mo', 'Translates into Moldavian', 'A person with this label says that knows how to translate into Moldavian');
INSERT INTO label (id, "schema", name, title, description) VALUES (280, 5, 'mn', 'Translates into Mongolian', 'A person with this label says that knows how to translate into Mongolian');
INSERT INTO label (id, "schema", name, title, description) VALUES (281, 5, 'mos', 'Translates into Mossi', 'A person with this label says that knows how to translate into Mossi');
INSERT INTO label (id, "schema", name, title, description) VALUES (282, 5, 'mul', 'Translates into Multiple languages', 'A person with this label says that knows how to translate into Multiple languages');
INSERT INTO label (id, "schema", name, title, description) VALUES (283, 5, 'mun', 'Translates into Munda languages', 'A person with this label says that knows how to translate into Munda languages');
INSERT INTO label (id, "schema", name, title, description) VALUES (284, 5, 'mus', 'Translates into Creek', 'A person with this label says that knows how to translate into Creek');
INSERT INTO label (id, "schema", name, title, description) VALUES (285, 5, 'mwr', 'Translates into Marwari', 'A person with this label says that knows how to translate into Marwari');
INSERT INTO label (id, "schema", name, title, description) VALUES (286, 5, 'myn', 'Translates into Mayan languages', 'A person with this label says that knows how to translate into Mayan languages');
INSERT INTO label (id, "schema", name, title, description) VALUES (287, 5, 'myv', 'Translates into Erzya', 'A person with this label says that knows how to translate into Erzya');
INSERT INTO label (id, "schema", name, title, description) VALUES (288, 5, 'nah', 'Translates into Nahuatl', 'A person with this label says that knows how to translate into Nahuatl');
INSERT INTO label (id, "schema", name, title, description) VALUES (289, 5, 'nai', 'Translates into North American Indian (Other)', 'A person with this label says that knows how to translate into North American Indian (Other)');
INSERT INTO label (id, "schema", name, title, description) VALUES (290, 5, 'nap', 'Translates into Neapolitan', 'A person with this label says that knows how to translate into Neapolitan');
INSERT INTO label (id, "schema", name, title, description) VALUES (291, 5, 'na', 'Translates into Nauru', 'A person with this label says that knows how to translate into Nauru');
INSERT INTO label (id, "schema", name, title, description) VALUES (292, 5, 'nv', 'Translates into Navaho', 'A person with this label says that knows how to translate into Navaho');
INSERT INTO label (id, "schema", name, title, description) VALUES (293, 5, 'nr', 'Translates into Ndebele, South', 'A person with this label says that knows how to translate into Ndebele, South');
INSERT INTO label (id, "schema", name, title, description) VALUES (294, 5, 'nd', 'Translates into Ndebele, North', 'A person with this label says that knows how to translate into Ndebele, North');
INSERT INTO label (id, "schema", name, title, description) VALUES (295, 5, 'ng', 'Translates into Ndonga', 'A person with this label says that knows how to translate into Ndonga');
INSERT INTO label (id, "schema", name, title, description) VALUES (296, 5, 'nds', 'Translates into German, Low', 'A person with this label says that knows how to translate into German, Low');
INSERT INTO label (id, "schema", name, title, description) VALUES (297, 5, 'ne', 'Translates into Nepali', 'A person with this label says that knows how to translate into Nepali');
INSERT INTO label (id, "schema", name, title, description) VALUES (298, 5, 'new', 'Translates into Newari', 'A person with this label says that knows how to translate into Newari');
INSERT INTO label (id, "schema", name, title, description) VALUES (299, 5, 'nia', 'Translates into Nias', 'A person with this label says that knows how to translate into Nias');
INSERT INTO label (id, "schema", name, title, description) VALUES (300, 5, 'nic', 'Translates into Niger-Kordofanian (Other)', 'A person with this label says that knows how to translate into Niger-Kordofanian (Other)');
INSERT INTO label (id, "schema", name, title, description) VALUES (301, 5, 'niu', 'Translates into Niuean', 'A person with this label says that knows how to translate into Niuean');
INSERT INTO label (id, "schema", name, title, description) VALUES (302, 5, 'nn', 'Translates into Norwegian Nynorsk', 'A person with this label says that knows how to translate into Norwegian Nynorsk');
INSERT INTO label (id, "schema", name, title, description) VALUES (303, 5, 'nb', 'Translates into Bokmål, Norwegian', 'A person with this label says that knows how to translate into Bokmål, Norwegian');
INSERT INTO label (id, "schema", name, title, description) VALUES (304, 5, 'nog', 'Translates into Nogai', 'A person with this label says that knows how to translate into Nogai');
INSERT INTO label (id, "schema", name, title, description) VALUES (305, 5, 'non', 'Translates into Norse, Old', 'A person with this label says that knows how to translate into Norse, Old');
INSERT INTO label (id, "schema", name, title, description) VALUES (306, 5, 'no', 'Translates into Norwegian', 'A person with this label says that knows how to translate into Norwegian');
INSERT INTO label (id, "schema", name, title, description) VALUES (307, 5, 'nso', 'Translates into Sotho, Northern', 'A person with this label says that knows how to translate into Sotho, Northern');
INSERT INTO label (id, "schema", name, title, description) VALUES (308, 5, 'nub', 'Translates into Nubian languages', 'A person with this label says that knows how to translate into Nubian languages');
INSERT INTO label (id, "schema", name, title, description) VALUES (309, 5, 'nwc', 'Translates into Classical Newari; Old Newari', 'A person with this label says that knows how to translate into Classical Newari; Old Newari');
INSERT INTO label (id, "schema", name, title, description) VALUES (310, 5, 'ny', 'Translates into Chewa; Chichewa; Nyanja', 'A person with this label says that knows how to translate into Chewa; Chichewa; Nyanja');
INSERT INTO label (id, "schema", name, title, description) VALUES (311, 5, 'nym', 'Translates into Nyankole', 'A person with this label says that knows how to translate into Nyankole');
INSERT INTO label (id, "schema", name, title, description) VALUES (312, 5, 'nyo', 'Translates into Nyoro', 'A person with this label says that knows how to translate into Nyoro');
INSERT INTO label (id, "schema", name, title, description) VALUES (313, 5, 'nzi', 'Translates into Nzima', 'A person with this label says that knows how to translate into Nzima');
INSERT INTO label (id, "schema", name, title, description) VALUES (314, 5, 'oc', 'Translates into Occitan (post 1500)', 'A person with this label says that knows how to translate into Occitan (post 1500)');
INSERT INTO label (id, "schema", name, title, description) VALUES (315, 5, 'oj', 'Translates into Ojibwa', 'A person with this label says that knows how to translate into Ojibwa');
INSERT INTO label (id, "schema", name, title, description) VALUES (316, 5, 'or', 'Translates into Oriya', 'A person with this label says that knows how to translate into Oriya');
INSERT INTO label (id, "schema", name, title, description) VALUES (317, 5, 'om', 'Translates into Oromo', 'A person with this label says that knows how to translate into Oromo');
INSERT INTO label (id, "schema", name, title, description) VALUES (318, 5, 'osa', 'Translates into Osage', 'A person with this label says that knows how to translate into Osage');
INSERT INTO label (id, "schema", name, title, description) VALUES (319, 5, 'os', 'Translates into Ossetian', 'A person with this label says that knows how to translate into Ossetian');
INSERT INTO label (id, "schema", name, title, description) VALUES (320, 5, 'ota', 'Translates into Turkish, Ottoman (1500-1928)', 'A person with this label says that knows how to translate into Turkish, Ottoman (1500-1928)');
INSERT INTO label (id, "schema", name, title, description) VALUES (321, 5, 'oto', 'Translates into Otomian languages', 'A person with this label says that knows how to translate into Otomian languages');
INSERT INTO label (id, "schema", name, title, description) VALUES (322, 5, 'paa', 'Translates into Papuan (Other)', 'A person with this label says that knows how to translate into Papuan (Other)');
INSERT INTO label (id, "schema", name, title, description) VALUES (323, 5, 'pag', 'Translates into Pangasinan', 'A person with this label says that knows how to translate into Pangasinan');
INSERT INTO label (id, "schema", name, title, description) VALUES (324, 5, 'pal', 'Translates into Pahlavi', 'A person with this label says that knows how to translate into Pahlavi');
INSERT INTO label (id, "schema", name, title, description) VALUES (325, 5, 'pam', 'Translates into Pampanga', 'A person with this label says that knows how to translate into Pampanga');
INSERT INTO label (id, "schema", name, title, description) VALUES (326, 5, 'pa', 'Translates into Panjabi', 'A person with this label says that knows how to translate into Panjabi');
INSERT INTO label (id, "schema", name, title, description) VALUES (327, 5, 'pap', 'Translates into Papiamento', 'A person with this label says that knows how to translate into Papiamento');
INSERT INTO label (id, "schema", name, title, description) VALUES (328, 5, 'pau', 'Translates into Palauan', 'A person with this label says that knows how to translate into Palauan');
INSERT INTO label (id, "schema", name, title, description) VALUES (329, 5, 'peo', 'Translates into Persian, Old (ca.600-400 B.C.)', 'A person with this label says that knows how to translate into Persian, Old (ca.600-400 B.C.)');
INSERT INTO label (id, "schema", name, title, description) VALUES (330, 5, 'fa', 'Translates into Persian', 'A person with this label says that knows how to translate into Persian');
INSERT INTO label (id, "schema", name, title, description) VALUES (331, 5, 'phi', 'Translates into Philippine (Other)', 'A person with this label says that knows how to translate into Philippine (Other)');
INSERT INTO label (id, "schema", name, title, description) VALUES (332, 5, 'phn', 'Translates into Phoenician', 'A person with this label says that knows how to translate into Phoenician');
INSERT INTO label (id, "schema", name, title, description) VALUES (333, 5, 'pi', 'Translates into Pali', 'A person with this label says that knows how to translate into Pali');
INSERT INTO label (id, "schema", name, title, description) VALUES (334, 5, 'pl', 'Translates into Polish', 'A person with this label says that knows how to translate into Polish');
INSERT INTO label (id, "schema", name, title, description) VALUES (335, 5, 'pt', 'Translates into Portuguese', 'A person with this label says that knows how to translate into Portuguese');
INSERT INTO label (id, "schema", name, title, description) VALUES (336, 5, 'pon', 'Translates into Pohnpeian', 'A person with this label says that knows how to translate into Pohnpeian');
INSERT INTO label (id, "schema", name, title, description) VALUES (337, 5, 'pra', 'Translates into Prakrit languages', 'A person with this label says that knows how to translate into Prakrit languages');
INSERT INTO label (id, "schema", name, title, description) VALUES (338, 5, 'pro', 'Translates into Provençal, Old (to 1500)', 'A person with this label says that knows how to translate into Provençal, Old (to 1500)');
INSERT INTO label (id, "schema", name, title, description) VALUES (339, 5, 'ps', 'Translates into Pushto', 'A person with this label says that knows how to translate into Pushto');
INSERT INTO label (id, "schema", name, title, description) VALUES (340, 5, 'qu', 'Translates into Quechua', 'A person with this label says that knows how to translate into Quechua');
INSERT INTO label (id, "schema", name, title, description) VALUES (341, 5, 'raj', 'Translates into Rajasthani', 'A person with this label says that knows how to translate into Rajasthani');
INSERT INTO label (id, "schema", name, title, description) VALUES (342, 5, 'rap', 'Translates into Rapanui', 'A person with this label says that knows how to translate into Rapanui');
INSERT INTO label (id, "schema", name, title, description) VALUES (343, 5, 'rar', 'Translates into Rarotongan', 'A person with this label says that knows how to translate into Rarotongan');
INSERT INTO label (id, "schema", name, title, description) VALUES (344, 5, 'roa', 'Translates into Romance (Other)', 'A person with this label says that knows how to translate into Romance (Other)');
INSERT INTO label (id, "schema", name, title, description) VALUES (345, 5, 'rm', 'Translates into Raeto-Romance', 'A person with this label says that knows how to translate into Raeto-Romance');
INSERT INTO label (id, "schema", name, title, description) VALUES (346, 5, 'rom', 'Translates into Romany', 'A person with this label says that knows how to translate into Romany');
INSERT INTO label (id, "schema", name, title, description) VALUES (347, 5, 'ro', 'Translates into Romanian', 'A person with this label says that knows how to translate into Romanian');
INSERT INTO label (id, "schema", name, title, description) VALUES (348, 5, 'rn', 'Translates into Rundi', 'A person with this label says that knows how to translate into Rundi');
INSERT INTO label (id, "schema", name, title, description) VALUES (349, 5, 'ru', 'Translates into Russian', 'A person with this label says that knows how to translate into Russian');
INSERT INTO label (id, "schema", name, title, description) VALUES (350, 5, 'sad', 'Translates into Sandawe', 'A person with this label says that knows how to translate into Sandawe');
INSERT INTO label (id, "schema", name, title, description) VALUES (351, 5, 'sg', 'Translates into Sango', 'A person with this label says that knows how to translate into Sango');
INSERT INTO label (id, "schema", name, title, description) VALUES (352, 5, 'sah', 'Translates into Yakut', 'A person with this label says that knows how to translate into Yakut');
INSERT INTO label (id, "schema", name, title, description) VALUES (353, 5, 'sai', 'Translates into South American Indian (Other)', 'A person with this label says that knows how to translate into South American Indian (Other)');
INSERT INTO label (id, "schema", name, title, description) VALUES (354, 5, 'sal', 'Translates into Salishan languages', 'A person with this label says that knows how to translate into Salishan languages');
INSERT INTO label (id, "schema", name, title, description) VALUES (355, 5, 'sam', 'Translates into Samaritan Aramaic', 'A person with this label says that knows how to translate into Samaritan Aramaic');
INSERT INTO label (id, "schema", name, title, description) VALUES (356, 5, 'sa', 'Translates into Sanskrit', 'A person with this label says that knows how to translate into Sanskrit');
INSERT INTO label (id, "schema", name, title, description) VALUES (357, 5, 'sas', 'Translates into Sasak', 'A person with this label says that knows how to translate into Sasak');
INSERT INTO label (id, "schema", name, title, description) VALUES (358, 5, 'sat', 'Translates into Santali', 'A person with this label says that knows how to translate into Santali');
INSERT INTO label (id, "schema", name, title, description) VALUES (359, 5, 'sr', 'Translates into Serbian', 'A person with this label says that knows how to translate into Serbian');
INSERT INTO label (id, "schema", name, title, description) VALUES (360, 5, 'sco', 'Translates into Scots', 'A person with this label says that knows how to translate into Scots');
INSERT INTO label (id, "schema", name, title, description) VALUES (361, 5, 'hr', 'Translates into Croatian', 'A person with this label says that knows how to translate into Croatian');
INSERT INTO label (id, "schema", name, title, description) VALUES (362, 5, 'sel', 'Translates into Selkup', 'A person with this label says that knows how to translate into Selkup');
INSERT INTO label (id, "schema", name, title, description) VALUES (363, 5, 'sem', 'Translates into Semitic (Other)', 'A person with this label says that knows how to translate into Semitic (Other)');
INSERT INTO label (id, "schema", name, title, description) VALUES (364, 5, 'sga', 'Translates into Irish, Old (to 900)', 'A person with this label says that knows how to translate into Irish, Old (to 900)');
INSERT INTO label (id, "schema", name, title, description) VALUES (365, 5, 'sgn', 'Translates into Sign languages', 'A person with this label says that knows how to translate into Sign languages');
INSERT INTO label (id, "schema", name, title, description) VALUES (366, 5, 'shn', 'Translates into Shan', 'A person with this label says that knows how to translate into Shan');
INSERT INTO label (id, "schema", name, title, description) VALUES (367, 5, 'sid', 'Translates into Sidamo', 'A person with this label says that knows how to translate into Sidamo');
INSERT INTO label (id, "schema", name, title, description) VALUES (368, 5, 'si', 'Translates into Sinhalese', 'A person with this label says that knows how to translate into Sinhalese');
INSERT INTO label (id, "schema", name, title, description) VALUES (369, 5, 'sio', 'Translates into Siouan languages', 'A person with this label says that knows how to translate into Siouan languages');
INSERT INTO label (id, "schema", name, title, description) VALUES (370, 5, 'sit', 'Translates into Sino-Tibetan (Other)', 'A person with this label says that knows how to translate into Sino-Tibetan (Other)');
INSERT INTO label (id, "schema", name, title, description) VALUES (371, 5, 'sla', 'Translates into Slavic (Other)', 'A person with this label says that knows how to translate into Slavic (Other)');
INSERT INTO label (id, "schema", name, title, description) VALUES (372, 5, 'sk', 'Translates into Slovak', 'A person with this label says that knows how to translate into Slovak');
INSERT INTO label (id, "schema", name, title, description) VALUES (373, 5, 'sl', 'Translates into Slovenian', 'A person with this label says that knows how to translate into Slovenian');
INSERT INTO label (id, "schema", name, title, description) VALUES (374, 5, 'sma', 'Translates into Southern Sami', 'A person with this label says that knows how to translate into Southern Sami');
INSERT INTO label (id, "schema", name, title, description) VALUES (375, 5, 'se', 'Translates into Northern Sami', 'A person with this label says that knows how to translate into Northern Sami');
INSERT INTO label (id, "schema", name, title, description) VALUES (376, 5, 'smi', 'Translates into Sami languages (Other)', 'A person with this label says that knows how to translate into Sami languages (Other)');
INSERT INTO label (id, "schema", name, title, description) VALUES (377, 5, 'smj', 'Translates into Lule Sami', 'A person with this label says that knows how to translate into Lule Sami');
INSERT INTO label (id, "schema", name, title, description) VALUES (378, 5, 'smn', 'Translates into Inari Sami', 'A person with this label says that knows how to translate into Inari Sami');
INSERT INTO label (id, "schema", name, title, description) VALUES (379, 5, 'sm', 'Translates into Samoan', 'A person with this label says that knows how to translate into Samoan');
INSERT INTO label (id, "schema", name, title, description) VALUES (380, 5, 'sms', 'Translates into Skolt Sami', 'A person with this label says that knows how to translate into Skolt Sami');
INSERT INTO label (id, "schema", name, title, description) VALUES (381, 5, 'sn', 'Translates into Shona', 'A person with this label says that knows how to translate into Shona');
INSERT INTO label (id, "schema", name, title, description) VALUES (382, 5, 'sd', 'Translates into Sindhi', 'A person with this label says that knows how to translate into Sindhi');
INSERT INTO label (id, "schema", name, title, description) VALUES (383, 5, 'snk', 'Translates into Soninke', 'A person with this label says that knows how to translate into Soninke');
INSERT INTO label (id, "schema", name, title, description) VALUES (384, 5, 'sog', 'Translates into Sogdian', 'A person with this label says that knows how to translate into Sogdian');
INSERT INTO label (id, "schema", name, title, description) VALUES (385, 5, 'so', 'Translates into Somali', 'A person with this label says that knows how to translate into Somali');
INSERT INTO label (id, "schema", name, title, description) VALUES (386, 5, 'son', 'Translates into Songhai', 'A person with this label says that knows how to translate into Songhai');
INSERT INTO label (id, "schema", name, title, description) VALUES (387, 5, 'st', 'Translates into Sotho, Southern', 'A person with this label says that knows how to translate into Sotho, Southern');
INSERT INTO label (id, "schema", name, title, description) VALUES (388, 5, 'es', 'Translates into Spanish (Castilian)', 'A person with this label says that knows how to translate into Spanish (Castilian)');
INSERT INTO label (id, "schema", name, title, description) VALUES (389, 5, 'sc', 'Translates into Sardinian', 'A person with this label says that knows how to translate into Sardinian');
INSERT INTO label (id, "schema", name, title, description) VALUES (390, 5, 'srr', 'Translates into Serer', 'A person with this label says that knows how to translate into Serer');
INSERT INTO label (id, "schema", name, title, description) VALUES (391, 5, 'ssa', 'Translates into Nilo-Saharan (Other)', 'A person with this label says that knows how to translate into Nilo-Saharan (Other)');
INSERT INTO label (id, "schema", name, title, description) VALUES (392, 5, 'ss', 'Translates into Swati', 'A person with this label says that knows how to translate into Swati');
INSERT INTO label (id, "schema", name, title, description) VALUES (393, 5, 'suk', 'Translates into Sukuma', 'A person with this label says that knows how to translate into Sukuma');
INSERT INTO label (id, "schema", name, title, description) VALUES (394, 5, 'su', 'Translates into Sundanese', 'A person with this label says that knows how to translate into Sundanese');
INSERT INTO label (id, "schema", name, title, description) VALUES (395, 5, 'sus', 'Translates into Susu', 'A person with this label says that knows how to translate into Susu');
INSERT INTO label (id, "schema", name, title, description) VALUES (396, 5, 'sux', 'Translates into Sumerian', 'A person with this label says that knows how to translate into Sumerian');
INSERT INTO label (id, "schema", name, title, description) VALUES (397, 5, 'sw', 'Translates into Swahili', 'A person with this label says that knows how to translate into Swahili');
INSERT INTO label (id, "schema", name, title, description) VALUES (398, 5, 'sv', 'Translates into Swedish', 'A person with this label says that knows how to translate into Swedish');
INSERT INTO label (id, "schema", name, title, description) VALUES (399, 5, 'syr', 'Translates into Syriac', 'A person with this label says that knows how to translate into Syriac');
INSERT INTO label (id, "schema", name, title, description) VALUES (400, 5, 'ty', 'Translates into Tahitian', 'A person with this label says that knows how to translate into Tahitian');
INSERT INTO label (id, "schema", name, title, description) VALUES (401, 5, 'tai', 'Translates into Tai (Other)', 'A person with this label says that knows how to translate into Tai (Other)');
INSERT INTO label (id, "schema", name, title, description) VALUES (402, 5, 'ta', 'Translates into Tamil', 'A person with this label says that knows how to translate into Tamil');
INSERT INTO label (id, "schema", name, title, description) VALUES (403, 5, 'ts', 'Translates into Tsonga', 'A person with this label says that knows how to translate into Tsonga');
INSERT INTO label (id, "schema", name, title, description) VALUES (404, 5, 'tt', 'Translates into Tatar', 'A person with this label says that knows how to translate into Tatar');
INSERT INTO label (id, "schema", name, title, description) VALUES (405, 5, 'te', 'Translates into Telugu', 'A person with this label says that knows how to translate into Telugu');
INSERT INTO label (id, "schema", name, title, description) VALUES (406, 5, 'tem', 'Translates into Timne', 'A person with this label says that knows how to translate into Timne');
INSERT INTO label (id, "schema", name, title, description) VALUES (407, 5, 'ter', 'Translates into Tereno', 'A person with this label says that knows how to translate into Tereno');
INSERT INTO label (id, "schema", name, title, description) VALUES (408, 5, 'tet', 'Translates into Tetum', 'A person with this label says that knows how to translate into Tetum');
INSERT INTO label (id, "schema", name, title, description) VALUES (409, 5, 'tg', 'Translates into Tajik', 'A person with this label says that knows how to translate into Tajik');
INSERT INTO label (id, "schema", name, title, description) VALUES (410, 5, 'tl', 'Translates into Tagalog', 'A person with this label says that knows how to translate into Tagalog');
INSERT INTO label (id, "schema", name, title, description) VALUES (411, 5, 'th', 'Translates into Thai', 'A person with this label says that knows how to translate into Thai');
INSERT INTO label (id, "schema", name, title, description) VALUES (412, 5, 'bo', 'Translates into Tibetan', 'A person with this label says that knows how to translate into Tibetan');
INSERT INTO label (id, "schema", name, title, description) VALUES (413, 5, 'tig', 'Translates into Tigre', 'A person with this label says that knows how to translate into Tigre');
INSERT INTO label (id, "schema", name, title, description) VALUES (414, 5, 'ti', 'Translates into Tigrinya', 'A person with this label says that knows how to translate into Tigrinya');
INSERT INTO label (id, "schema", name, title, description) VALUES (415, 5, 'tiv', 'Translates into Tiv', 'A person with this label says that knows how to translate into Tiv');
INSERT INTO label (id, "schema", name, title, description) VALUES (416, 5, 'tlh', 'Translates into Klingon; tlhIngan-Hol', 'A person with this label says that knows how to translate into Klingon; tlhIngan-Hol');
INSERT INTO label (id, "schema", name, title, description) VALUES (417, 5, 'tkl', 'Translates into Tokelau', 'A person with this label says that knows how to translate into Tokelau');
INSERT INTO label (id, "schema", name, title, description) VALUES (418, 5, 'tli', 'Translates into Tlinglit', 'A person with this label says that knows how to translate into Tlinglit');
INSERT INTO label (id, "schema", name, title, description) VALUES (419, 5, 'tmh', 'Translates into Tamashek', 'A person with this label says that knows how to translate into Tamashek');
INSERT INTO label (id, "schema", name, title, description) VALUES (420, 5, 'tog', 'Translates into Tonga (Nyasa)', 'A person with this label says that knows how to translate into Tonga (Nyasa)');
INSERT INTO label (id, "schema", name, title, description) VALUES (421, 5, 'to', 'Translates into Tonga (Tonga Islands)', 'A person with this label says that knows how to translate into Tonga (Tonga Islands)');
INSERT INTO label (id, "schema", name, title, description) VALUES (422, 5, 'tpi', 'Translates into Tok Pisin', 'A person with this label says that knows how to translate into Tok Pisin');
INSERT INTO label (id, "schema", name, title, description) VALUES (423, 5, 'tsi', 'Translates into Tsimshian', 'A person with this label says that knows how to translate into Tsimshian');
INSERT INTO label (id, "schema", name, title, description) VALUES (424, 5, 'tn', 'Translates into Tswana', 'A person with this label says that knows how to translate into Tswana');
INSERT INTO label (id, "schema", name, title, description) VALUES (425, 5, 'tk', 'Translates into Turkmen', 'A person with this label says that knows how to translate into Turkmen');
INSERT INTO label (id, "schema", name, title, description) VALUES (426, 5, 'tum', 'Translates into Tumbuka', 'A person with this label says that knows how to translate into Tumbuka');
INSERT INTO label (id, "schema", name, title, description) VALUES (427, 5, 'tup', 'Translates into Tupi languages', 'A person with this label says that knows how to translate into Tupi languages');
INSERT INTO label (id, "schema", name, title, description) VALUES (428, 5, 'tr', 'Translates into Turkish', 'A person with this label says that knows how to translate into Turkish');
INSERT INTO label (id, "schema", name, title, description) VALUES (429, 5, 'tut', 'Translates into Altaic (Other)', 'A person with this label says that knows how to translate into Altaic (Other)');
INSERT INTO label (id, "schema", name, title, description) VALUES (430, 5, 'tvl', 'Translates into Tuvalu', 'A person with this label says that knows how to translate into Tuvalu');
INSERT INTO label (id, "schema", name, title, description) VALUES (431, 5, 'tw', 'Translates into Twi', 'A person with this label says that knows how to translate into Twi');
INSERT INTO label (id, "schema", name, title, description) VALUES (432, 5, 'tyv', 'Translates into Tuvinian', 'A person with this label says that knows how to translate into Tuvinian');
INSERT INTO label (id, "schema", name, title, description) VALUES (433, 5, 'udm', 'Translates into Udmurt', 'A person with this label says that knows how to translate into Udmurt');
INSERT INTO label (id, "schema", name, title, description) VALUES (434, 5, 'uga', 'Translates into Ugaritic', 'A person with this label says that knows how to translate into Ugaritic');
INSERT INTO label (id, "schema", name, title, description) VALUES (435, 5, 'ug', 'Translates into Uighur', 'A person with this label says that knows how to translate into Uighur');
INSERT INTO label (id, "schema", name, title, description) VALUES (436, 5, 'uk', 'Translates into Ukrainian', 'A person with this label says that knows how to translate into Ukrainian');
INSERT INTO label (id, "schema", name, title, description) VALUES (437, 5, 'umb', 'Translates into Umbundu', 'A person with this label says that knows how to translate into Umbundu');
INSERT INTO label (id, "schema", name, title, description) VALUES (438, 5, 'und', 'Translates into Undetermined', 'A person with this label says that knows how to translate into Undetermined');
INSERT INTO label (id, "schema", name, title, description) VALUES (439, 5, 'urd', 'Translates into Urdu', 'A person with this label says that knows how to translate into Urdu');
INSERT INTO label (id, "schema", name, title, description) VALUES (440, 5, 'uz', 'Translates into Uzbek', 'A person with this label says that knows how to translate into Uzbek');
INSERT INTO label (id, "schema", name, title, description) VALUES (441, 5, 'vai', 'Translates into Vai', 'A person with this label says that knows how to translate into Vai');
INSERT INTO label (id, "schema", name, title, description) VALUES (442, 5, 've', 'Translates into Venda', 'A person with this label says that knows how to translate into Venda');
INSERT INTO label (id, "schema", name, title, description) VALUES (443, 5, 'vi', 'Translates into Vietnamese', 'A person with this label says that knows how to translate into Vietnamese');
INSERT INTO label (id, "schema", name, title, description) VALUES (444, 5, 'vo', 'Translates into Volapuk', 'A person with this label says that knows how to translate into Volapuk');
INSERT INTO label (id, "schema", name, title, description) VALUES (445, 5, 'vot', 'Translates into Votic', 'A person with this label says that knows how to translate into Votic');
INSERT INTO label (id, "schema", name, title, description) VALUES (446, 5, 'wak', 'Translates into Wakashan languages', 'A person with this label says that knows how to translate into Wakashan languages');
INSERT INTO label (id, "schema", name, title, description) VALUES (447, 5, 'wal', 'Translates into Walamo', 'A person with this label says that knows how to translate into Walamo');
INSERT INTO label (id, "schema", name, title, description) VALUES (448, 5, 'war', 'Translates into Waray', 'A person with this label says that knows how to translate into Waray');
INSERT INTO label (id, "schema", name, title, description) VALUES (449, 5, 'was', 'Translates into Washo', 'A person with this label says that knows how to translate into Washo');
INSERT INTO label (id, "schema", name, title, description) VALUES (450, 5, 'cy', 'Translates into Welsh', 'A person with this label says that knows how to translate into Welsh');
INSERT INTO label (id, "schema", name, title, description) VALUES (451, 5, 'wen', 'Translates into Sorbian languages', 'A person with this label says that knows how to translate into Sorbian languages');
INSERT INTO label (id, "schema", name, title, description) VALUES (452, 5, 'wa', 'Translates into Walloon', 'A person with this label says that knows how to translate into Walloon');
INSERT INTO label (id, "schema", name, title, description) VALUES (453, 5, 'wo', 'Translates into Wolof', 'A person with this label says that knows how to translate into Wolof');
INSERT INTO label (id, "schema", name, title, description) VALUES (454, 5, 'xal', 'Translates into Kalmyk', 'A person with this label says that knows how to translate into Kalmyk');
INSERT INTO label (id, "schema", name, title, description) VALUES (455, 5, 'xh', 'Translates into Xhosa', 'A person with this label says that knows how to translate into Xhosa');
INSERT INTO label (id, "schema", name, title, description) VALUES (456, 5, 'yao', 'Translates into Yao', 'A person with this label says that knows how to translate into Yao');
INSERT INTO label (id, "schema", name, title, description) VALUES (457, 5, 'yap', 'Translates into Yapese', 'A person with this label says that knows how to translate into Yapese');
INSERT INTO label (id, "schema", name, title, description) VALUES (458, 5, 'yi', 'Translates into Yiddish', 'A person with this label says that knows how to translate into Yiddish');
INSERT INTO label (id, "schema", name, title, description) VALUES (459, 5, 'yo', 'Translates into Yoruba', 'A person with this label says that knows how to translate into Yoruba');
INSERT INTO label (id, "schema", name, title, description) VALUES (460, 5, 'ypk', 'Translates into Yupik languages', 'A person with this label says that knows how to translate into Yupik languages');
INSERT INTO label (id, "schema", name, title, description) VALUES (461, 5, 'zap', 'Translates into Zapotec', 'A person with this label says that knows how to translate into Zapotec');
INSERT INTO label (id, "schema", name, title, description) VALUES (462, 5, 'zen', 'Translates into Zenaga', 'A person with this label says that knows how to translate into Zenaga');
INSERT INTO label (id, "schema", name, title, description) VALUES (463, 5, 'za', 'Translates into Chuang; Zhuang', 'A person with this label says that knows how to translate into Chuang; Zhuang');
INSERT INTO label (id, "schema", name, title, description) VALUES (464, 5, 'znd', 'Translates into Zande', 'A person with this label says that knows how to translate into Zande');
INSERT INTO label (id, "schema", name, title, description) VALUES (465, 5, 'zu', 'Translates into Zulu', 'A person with this label says that knows how to translate into Zulu');
INSERT INTO label (id, "schema", name, title, description) VALUES (466, 5, 'zun', 'Translates into Zuni', 'A person with this label says that knows how to translate into Zuni');


--
-- Name: personlabel; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO personlabel (person, label) VALUES (13, 388);
INSERT INTO personlabel (person, label) VALUES (13, 69);
INSERT INTO personlabel (person, label) VALUES (14, 450);
INSERT INTO personlabel (person, label) VALUES (14, 197);
INSERT INTO personlabel (person, label) VALUES (14, 120);
INSERT INTO personlabel (person, label) VALUES (15, 335);


--
-- Name: project; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO project (id, "owner", name, displayname, title, shortdesc, description, datecreated, homepageurl, wikiurl, lastdoap) VALUES (1, 1, 'ubuntu', 'Ubuntu', 'The Ubuntu Project', 'A community Linux distribution building building a slick desktop for the global market.', 'The Ubuntu Project aims to create a freely redistributable OS that is easy to customize and derive from. Ubuntu is released every six months with contributions from a large community. Ubuntu also includes work to unify the translation of common opens source desktop applications and the tracking of bugs across multiple distributions.', '2004-09-24 20:58:00.633513', 'http://www.no-name-yet.com/', NULL, NULL);
INSERT INTO project (id, "owner", name, displayname, title, shortdesc, description, datecreated, homepageurl, wikiurl, lastdoap) VALUES (2, 2, 'do-not-use-info-imports', 'DO NOT USE', 'DO NOT USE', 'DO NOT USE', 'TEMPORARY project till mirror jobs are assigned to correct project', '2004-09-24 20:58:00.637677', 'http://arch.ubuntu.com/', NULL, NULL);
INSERT INTO project (id, "owner", name, displayname, title, shortdesc, description, datecreated, homepageurl, wikiurl, lastdoap) VALUES (3, 2, 'launchpad-mirrors', 'Launchpad SCM Mirrors', 'The Launchpad Mirroring Project', 'launchpad mirrors various revision control archives, that mirroring is managed here', 'A project to mirror revision control archives into Arch.', '2004-09-24 20:58:00.65398', 'http://arch.ubuntu.com/', NULL, NULL);
INSERT INTO project (id, "owner", name, displayname, title, shortdesc, description, datecreated, homepageurl, wikiurl, lastdoap) VALUES (4, 12, 'mozilla', 'The Mozilla Project', 'The Mozilla Project', 'The Mozilla Project is the largest open source web browser collaborative project.', 'The Mozilla Project is the largest open source web browser collaborative project. The Mozilla Project produces several internet applications that are very widely used, and is also a center for collaboration on internet standards work by open source groups.', '2004-09-24 20:58:02.177698', 'http://www.mozilla.org/', NULL, NULL);
INSERT INTO project (id, "owner", name, displayname, title, shortdesc, description, datecreated, homepageurl, wikiurl, lastdoap) VALUES (5, 12, 'gnome', 'GNOME', 'The GNOME Project', 'foo', 'bar', '2004-09-24 20:58:02.222154', 'http://www.gnome.org/', NULL, NULL);
INSERT INTO project (id, "owner", name, displayname, title, shortdesc, description, datecreated, homepageurl, wikiurl, lastdoap) VALUES (6, 12, 'iso-codes', 'iso-codes', 'iso-codes', 'foo', 'bar', '2004-09-24 20:58:02.238443', 'http://www.gnome.org/', NULL, NULL);


--
-- Name: projectrelationship; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: projectrole; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: product; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO product (id, project, "owner", name, displayname, title, shortdesc, description, datecreated, homepageurl, screenshotsurl, wikiurl, listurl, programminglang, downloadurl, lastdoap) VALUES (1, 1, 1, 'ubuntu', 'Ubuntu', 'Ubuntu', 'An easy-to-install version of Linux that has a complete set of desktop applications ready to use immediately after installation.', 'Ubuntu is a desktop Linux that you can give your girlfriend to install. Works out of the box with recent Gnome desktop applications configured to make you productive immediately. Ubuntu is updated every six months, comes with security updates for peace of mind, and is avaialble everywhere absolutely free of charge.', '2004-09-24 20:58:00.655518', 'http://www.ubuntu.com/', NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO product (id, project, "owner", name, displayname, title, shortdesc, description, datecreated, homepageurl, screenshotsurl, wikiurl, listurl, programminglang, downloadurl, lastdoap) VALUES (2, 2, 2, 'unassigned', 'unassigned syncs', 'unassigned syncs', 'syncs still not assigned to a real product', 'unassigned syncs, will not be processed, to be moved to real proejcts ASAP.', '2004-09-24 20:58:00.674409', 'http://arch.ubuntu.com/', NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO product (id, project, "owner", name, displayname, title, shortdesc, description, datecreated, homepageurl, screenshotsurl, wikiurl, listurl, programminglang, downloadurl, lastdoap) VALUES (3, 3, 2, 'arch-mirrors', 'Arch mirrors', 'Arch archive mirrors', 'Arch Archive Mirroring project.', 'Arch archive full-archive mirror tasks', '2004-09-24 20:58:00.691047', 'http://arch.ubuntu.com/', NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO product (id, project, "owner", name, displayname, title, shortdesc, description, datecreated, homepageurl, screenshotsurl, wikiurl, listurl, programminglang, downloadurl, lastdoap) VALUES (4, 4, 12, 'firefox', 'Mozilla Firefox', 'Mozilla Firefox', 'The Mozilla Firefox web browser', 'The Mozilla Firefox web browser', '2004-09-24 20:58:02.185708', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO product (id, project, "owner", name, displayname, title, shortdesc, description, datecreated, homepageurl, screenshotsurl, wikiurl, listurl, programminglang, downloadurl, lastdoap) VALUES (5, 5, 12, 'evolution', 'Evolution', 'The Evolution Groupware', 'foo', 'bar', '2004-09-24 20:58:02.240163', 'http://www.novell.com/', NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO product (id, project, "owner", name, displayname, title, shortdesc, description, datecreated, homepageurl, screenshotsurl, wikiurl, listurl, programminglang, downloadurl, lastdoap) VALUES (6, 5, 12, 'gnome-terminal', 'GNOME Terminal', 'The GNOME terminal emulator', 'foo', 'bar', '2004-09-24 20:58:02.256678', 'http://www.gnome.org/', NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO product (id, project, "owner", name, displayname, title, shortdesc, description, datecreated, homepageurl, screenshotsurl, wikiurl, listurl, programminglang, downloadurl, lastdoap) VALUES (7, 6, 12, 'iso-codes', 'iso-codes', 'The iso-codes', 'foo', 'bar', '2004-09-24 20:58:02.258743', 'http://www.novell.com/', NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO product (id, project, "owner", name, displayname, title, shortdesc, description, datecreated, homepageurl, screenshotsurl, wikiurl, listurl, programminglang, downloadurl, lastdoap) VALUES (8, 4, 12, 'thunderbird', 'Mozilla Thunderbird', 'Mozilla Thunderbird', 'The Mozilla Thunderbird email client', 'The Mozilla Thunderbird email client', '2004-09-24 20:58:04.478988', NULL, NULL, NULL, NULL, NULL, NULL, NULL);


--
-- Name: productlabel; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: productrole; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: productseries; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: productrelease; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO productrelease (id, product, datereleased, "version", title, description, changelog, "owner") VALUES (1, 4, '2004-06-28 00:00:00', 'mozilla-firefox-0.9.1', NULL, NULL, NULL, 12);
INSERT INTO productrelease (id, product, datereleased, "version", title, description, changelog, "owner") VALUES (2, 8, '2004-06-28 00:00:00', 'mozilla-thunderbird-0.8.0', NULL, NULL, NULL, 12);


--
-- Name: productcvsmodule; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: productbkbranch; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: productsvnmodule; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: archarchive; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO archarchive (id, name, title, description, visible, "owner") VALUES (1, 'mozilla', 'Mozilla', 'text', false, NULL);
INSERT INTO archarchive (id, name, title, description, visible, "owner") VALUES (2, 'thunderbird', 'Thunderbid', 'text', false, NULL);
INSERT INTO archarchive (id, name, title, description, visible, "owner") VALUES (3, 'twisted', 'Twisted', 'text', false, NULL);
INSERT INTO archarchive (id, name, title, description, visible, "owner") VALUES (4, 'bugzila', 'Bugzila', 'text', false, NULL);
INSERT INTO archarchive (id, name, title, description, visible, "owner") VALUES (5, 'arch', 'Arch', 'text', false, NULL);
INSERT INTO archarchive (id, name, title, description, visible, "owner") VALUES (6, 'kiwi2', 'Kiwi2', 'text', false, NULL);
INSERT INTO archarchive (id, name, title, description, visible, "owner") VALUES (7, 'plone', 'Plone', 'text', false, NULL);
INSERT INTO archarchive (id, name, title, description, visible, "owner") VALUES (8, 'gnome', 'GNOME', 'The GNOME Project', false, NULL);
INSERT INTO archarchive (id, name, title, description, visible, "owner") VALUES (9, 'iso-codes', 'iso-codes', 'The iso-codes', false, NULL);


--
-- Name: archarchivelocation; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: archarchivelocationsigner; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: archnamespace; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO archnamespace (id, archarchive, category, branch, "version", visible) VALUES (1, 1, 'mozilla', NULL, NULL, true);
INSERT INTO archnamespace (id, archarchive, category, branch, "version", visible) VALUES (2, 2, 'tunderbird', NULL, NULL, true);
INSERT INTO archnamespace (id, archarchive, category, branch, "version", visible) VALUES (3, 3, 'twisted', NULL, NULL, true);
INSERT INTO archnamespace (id, archarchive, category, branch, "version", visible) VALUES (4, 4, 'bugzila', NULL, NULL, true);
INSERT INTO archnamespace (id, archarchive, category, branch, "version", visible) VALUES (5, 5, 'arch', NULL, NULL, true);
INSERT INTO archnamespace (id, archarchive, category, branch, "version", visible) VALUES (6, 6, 'kiwi2', NULL, NULL, true);
INSERT INTO archnamespace (id, archarchive, category, branch, "version", visible) VALUES (7, 7, 'plone', NULL, NULL, true);
INSERT INTO archnamespace (id, archarchive, category, branch, "version", visible) VALUES (8, 8, 'gnome', 'evolution', '2.0', false);
INSERT INTO archnamespace (id, archarchive, category, branch, "version", visible) VALUES (9, 9, 'iso-codes', 'iso-codes', '0.35', false);


--
-- Name: branch; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO branch (id, archnamespace, title, description, "owner", product) VALUES (1, 1, 'Mozilla Firefox 0.9.1', 'text', 1, NULL);
INSERT INTO branch (id, archnamespace, title, description, "owner", product) VALUES (2, 2, 'Mozilla Thunderbird 0.9.1', 'text', 11, NULL);
INSERT INTO branch (id, archnamespace, title, description, "owner", product) VALUES (3, 3, 'Python Twisted 0.9.1', 'text', 7, NULL);
INSERT INTO branch (id, archnamespace, title, description, "owner", product) VALUES (4, 4, 'Bugzila 0.9.1', 'text', 3, NULL);
INSERT INTO branch (id, archnamespace, title, description, "owner", product) VALUES (5, 5, 'Arch 0.9.1', 'text', 8, NULL);
INSERT INTO branch (id, archnamespace, title, description, "owner", product) VALUES (6, 6, 'Kiwi2 0.9.1', 'text', 9, NULL);
INSERT INTO branch (id, archnamespace, title, description, "owner", product) VALUES (7, 7, 'Plone 0.9.1', 'text', 10, NULL);
INSERT INTO branch (id, archnamespace, title, description, "owner", product) VALUES (8, 8, 'Evolution 2.0', 'text', 13, NULL);
INSERT INTO branch (id, archnamespace, title, description, "owner", product) VALUES (9, 9, 'Iso-codes 0.35', 'text', 13, NULL);


--
-- Name: changeset; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: changesetfilename; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: changesetfile; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: changesetfilehash; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: branchrelationship; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: branchlabel; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: productbranchrelationship; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: manifest; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO manifest (id, datecreated, "owner") VALUES (1, '2004-06-29 00:00:00', 1);
INSERT INTO manifest (id, datecreated, "owner") VALUES (2, '2004-06-30 00:00:00', 11);
INSERT INTO manifest (id, datecreated, "owner") VALUES (3, '2004-07-01 00:00:00', 7);
INSERT INTO manifest (id, datecreated, "owner") VALUES (4, '2004-07-02 00:00:00', 3);
INSERT INTO manifest (id, datecreated, "owner") VALUES (5, '2004-07-03 00:00:00', 8);
INSERT INTO manifest (id, datecreated, "owner") VALUES (6, '2004-07-04 00:00:00', 9);
INSERT INTO manifest (id, datecreated, "owner") VALUES (7, '2004-07-05 00:00:00', 10);
INSERT INTO manifest (id, datecreated, "owner") VALUES (8, '2004-06-29 00:00:00', 12);
INSERT INTO manifest (id, datecreated, "owner") VALUES (9, '2004-06-29 00:00:00', 12);


--
-- Name: manifestentry; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: archconfig; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: archconfigentry; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: processorfamily; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO processorfamily (id, name, title, description, "owner") VALUES (1, 'x86', 'Intel 386 compatible chips', 'Bring back the 8086!', 1);


--
-- Name: processor; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO processor (id, family, name, title, description, "owner") VALUES (1, 1, '386', 'Intel 386', 'Intel 386 and its many derivatives and clones, the basic 32-bit chip in the x86 family', 1);


--
-- Name: builder; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: component; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO component (id, name) VALUES (1, 'default_component');


--
-- Name: section; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO section (id, name) VALUES (1, 'default_section');


--
-- Name: distribution; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO distribution (id, name, title, description, domainname, "owner") VALUES (1, 'ubuntu', 'Ubuntu', 'Ubuntu is a new concept of GNU/Linux Distribution based on Debian GNU/Linux.', 'domain', 1);
INSERT INTO distribution (id, name, title, description, domainname, "owner") VALUES (2, 'redhat', 'Redhat Advanced Server', 'Red Hat is a commercial distribution of GNU/Linux Operating System.', 'domain', 1);
INSERT INTO distribution (id, name, title, description, domainname, "owner") VALUES (3, 'debian', 'Debian GNU/Linux', 'Debian GNU/Linux is a non commercial distribution of a GNU/Linux Operating System for many platforms.', 'domain', 1);
INSERT INTO distribution (id, name, title, description, domainname, "owner") VALUES (4, 'gentoo', 'The Gentoo Linux', 'Gentoo is a very customizeable GNU/Linux Distribution', 'domain', 1);
INSERT INTO distribution (id, name, title, description, domainname, "owner") VALUES (5, 'porkypigpolka', 'Porky Pig Polka Distribution', 'Should be near the Spork concept of GNU/Linux Distribution', 'domain', 1);


--
-- Name: distributionrole; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO distributionrole (person, distribution, role, id) VALUES (1, 1, 1, 1);
INSERT INTO distributionrole (person, distribution, role, id) VALUES (11, 1, 1, 2);
INSERT INTO distributionrole (person, distribution, role, id) VALUES (10, 1, 1, 3);
INSERT INTO distributionrole (person, distribution, role, id) VALUES (7, 1, 1, 4);
INSERT INTO distributionrole (person, distribution, role, id) VALUES (5, 1, 1, 5);
INSERT INTO distributionrole (person, distribution, role, id) VALUES (17, 1, 3, 6);
INSERT INTO distributionrole (person, distribution, role, id) VALUES (18, 1, 3, 7);


--
-- Name: distrorelease; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO distrorelease (id, distribution, name, title, description, "version", components, sections, releasestate, datereleased, parentrelease, "owner") VALUES (1, 1, 'warty', 'Warty', 'This is the first stable release of Ubuntu', '1.0.0', 1, 1, 3, '2004-08-20 00:00:00', NULL, 1);
INSERT INTO distrorelease (id, distribution, name, title, description, "version", components, sections, releasestate, datereleased, parentrelease, "owner") VALUES (2, 2, 'six', 'Six Six Six', 'some text to describe the whole 666 release of RH', '6.0.1', 1, 1, 4, '2004-03-21 00:00:00', NULL, 8);
INSERT INTO distrorelease (id, distribution, name, title, description, "version", components, sections, releasestate, datereleased, parentrelease, "owner") VALUES (3, 1, 'hoary', 'Hoary Crazy-Unstable', 'Hoary is the next release of Ubuntu', '0.0.1', 1, 1, 2, '2004-08-25 00:00:00', 1, 1);
INSERT INTO distrorelease (id, distribution, name, title, description, "version", components, sections, releasestate, datereleased, parentrelease, "owner") VALUES (4, 2, '7.0', 'Seven', 'The release that we would not expect', '7.0.1', 1, 1, 3, '2004-04-01 00:00:00', 2, 7);
INSERT INTO distrorelease (id, distribution, name, title, description, "version", components, sections, releasestate, datereleased, parentrelease, "owner") VALUES (5, 1, 'grumpy', 'G-R-U-M-P-Y', 'Grumpy is far far away, but should be the third release of Ubuntu', '-0.0.1', 1, 1, 1, '2004-08-29 00:00:00', 1, 1);
INSERT INTO distrorelease (id, distribution, name, title, description, "version", components, sections, releasestate, datereleased, parentrelease, "owner") VALUES (6, 3, 'woody', 'WOODY', 'WOODY is the current stable verison of Debian GNU/Linux', '3.0', 1, 1, 4, '2003-01-01 00:00:00', NULL, 2);
INSERT INTO distrorelease (id, distribution, name, title, description, "version", components, sections, releasestate, datereleased, parentrelease, "owner") VALUES (7, 3, 'sarge', 'Sarge', 'Sarge is the FROZEN unstable version of Debian GNU/Linux.', '3.1', 1, 1, 3, '2004-09-29 00:00:00', 6, 5);
INSERT INTO distrorelease (id, distribution, name, title, description, "version", components, sections, releasestate, datereleased, parentrelease, "owner") VALUES (8, 3, 'sid', 'Sid', 'Sid is the CRAZY unstable version of Debian GNU/Linux.', '3.2', 1, 1, 1, '2004-12-29 00:00:00', 6, 6);


--
-- Name: distroreleaserole; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO distroreleaserole (person, distrorelease, role, id) VALUES (1, 1, 1, 1);
INSERT INTO distroreleaserole (person, distrorelease, role, id) VALUES (1, 3, 1, 2);
INSERT INTO distroreleaserole (person, distrorelease, role, id) VALUES (1, 5, 1, 3);
INSERT INTO distroreleaserole (person, distrorelease, role, id) VALUES (11, 1, 2, 4);
INSERT INTO distroreleaserole (person, distrorelease, role, id) VALUES (11, 3, 2, 5);
INSERT INTO distroreleaserole (person, distrorelease, role, id) VALUES (11, 5, 3, 6);
INSERT INTO distroreleaserole (person, distrorelease, role, id) VALUES (20, 1, 4, 7);
INSERT INTO distroreleaserole (person, distrorelease, role, id) VALUES (19, 1, 4, 8);
INSERT INTO distroreleaserole (person, distrorelease, role, id) VALUES (21, 3, 4, 9);


--
-- Name: distroarchrelease; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO distroarchrelease (id, distrorelease, processorfamily, architecturetag, "owner") VALUES (1, 1, 1, 'warty--x86--devel--0', 1);


--
-- Name: libraryfilecontent; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: libraryfilealias; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: productreleasefile; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: sourcepackagename; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO sourcepackagename (id, name) VALUES (1, 'mozilla-firefox');
INSERT INTO sourcepackagename (id, name) VALUES (2, 'mozilla-thunderbird');
INSERT INTO sourcepackagename (id, name) VALUES (3, 'python-twisted');
INSERT INTO sourcepackagename (id, name) VALUES (4, 'bugzilla');
INSERT INTO sourcepackagename (id, name) VALUES (5, 'arch');
INSERT INTO sourcepackagename (id, name) VALUES (6, 'kiwi2');
INSERT INTO sourcepackagename (id, name) VALUES (7, 'plone');
INSERT INTO sourcepackagename (id, name) VALUES (8, 'evolution');


--
-- Name: sourcepackage; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO sourcepackage (id, maintainer, shortdesc, description, manifest, distro, sourcepackagename) VALUES (1, 1, 'Mozilla Firefox Web Browser', 'Firefox is a redesign of the Mozilla browser component, similar to Galeon, 
	K-Meleon and Camino, but written using the XUL user interface language and 
	designed to lightweight and cross-platform.', NULL, 3, 1);
INSERT INTO sourcepackage (id, maintainer, shortdesc, description, manifest, distro, sourcepackagename) VALUES (2, 11, 'Mozilla Thunderbird Mail Reader', 'Mozilla Thunderbird is a redesign of the Mozilla mail component. 
	The goal is to produce a cross platform stand alone mail application 
	using the XUL user interface language. Mozilla Thunderbird leaves a 
	somewhat smaller memory footprint than the Mozilla suite.', NULL, 3, 2);
INSERT INTO sourcepackage (id, maintainer, shortdesc, description, manifest, distro, sourcepackagename) VALUES (3, 7, 'Python Twisted', 'It includes a web server, a telnet server, a multiplayer RPG engine, 
	a generic client and server for remote object access, and APIs for 
	creating new protocols.', NULL, 3, 3);
INSERT INTO sourcepackage (id, maintainer, shortdesc, description, manifest, distro, sourcepackagename) VALUES (4, 3, 'Bugzilla', 'Bugzilla is a "Defect Tracking System" or "Bug-Tracking System". 
	Defect Tracking Systems allow individual or groups of developers 
	to keep track of outstanding bugs in their product effectively.', NULL, 1, 4);
INSERT INTO sourcepackage (id, maintainer, shortdesc, description, manifest, distro, sourcepackagename) VALUES (5, 8, 'Arch(TLA)', 'arch is a revision control system with features that are ideal for 
	projects characterised by widely distributed development, concurrent 
	support of multiple releases, and substantial amounts of development
	on branches. It can be a replacement for CVS and corrects many 
	mis-features of that system.', NULL, 1, 5);
INSERT INTO sourcepackage (id, maintainer, shortdesc, description, manifest, distro, sourcepackagename) VALUES (6, 9, 'Kiwi2', ' Kiwi2 consists of a set of classes and wrappers for PyGTK-2 that were 
	developed to provide a sort of framework for applications. Fully object-oriented, 
	and roughly modeled after Smalltalk''s MVC, Kiwi provides a simple, practical 
	way to build forms, windows and widgets that transparently access and display
	your object data. Kiwi was primarily designed to make implementing the UI for
	 Stoq easier, and it is released under the LGPL', NULL, 1, 6);
INSERT INTO sourcepackage (id, maintainer, shortdesc, description, manifest, distro, sourcepackagename) VALUES (7, 10, 'Plone', 'Plone is powerful and flexible. It is ideal as an intranet and extranet 
	server, as a document publishing system, a portal server and as a groupware
	 tool for collaboration between separately located entities.', NULL, 1, 7);
INSERT INTO sourcepackage (id, maintainer, shortdesc, description, manifest, distro, sourcepackagename) VALUES (8, 6, 'Evolution', 'Evolution is the integrated mail, calendar, task and address book 
	distributed suite from Ximian, Inc.', NULL, 1, 8);


--
-- Name: sourcepackagerelationship; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: sourcepackagelabel; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: packaging; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO packaging (sourcepackage, packaging, product) VALUES (1, 1, 4);


--
-- Name: sourcepackagerelease; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO sourcepackagerelease (id, sourcepackage, srcpackageformat, creator, "version", dateuploaded, urgency, dscsigningkey, component, changelog, builddepends, builddependsindep, architecturehintlist, dsc) VALUES (7, 3, 1, 7, '0.9.1-3', '2004-07-01 00:00:00', 1, NULL, NULL, NULL, 'mozilla-firefox (>= 0.9.0-9), mozilla-thunderbird, arch', 'kiwi (>= 2.0),python-twisted , bugzilla, plone', NULL, NULL);
INSERT INTO sourcepackagerelease (id, sourcepackage, srcpackageformat, creator, "version", dateuploaded, urgency, dscsigningkey, component, changelog, builddepends, builddependsindep, architecturehintlist, dsc) VALUES (8, 4, 1, 3, '0.9.1-4', '2004-07-02 00:00:00', 1, NULL, NULL, NULL, 'mozilla-firefox  (>= 0.9.0-9), mozilla-thunderbird, arch', 'kiwi (>= 2.0),python-twisted , bugzilla, plone', NULL, NULL);
INSERT INTO sourcepackagerelease (id, sourcepackage, srcpackageformat, creator, "version", dateuploaded, urgency, dscsigningkey, component, changelog, builddepends, builddependsindep, architecturehintlist, dsc) VALUES (9, 5, 1, 8, '0.9.1-5', '2004-07-03 00:00:00', 1, NULL, NULL, NULL, 'mozilla-firefox  (>= 0.9.0-9), mozilla-thunderbird, arch', 'kiwi (>= 2.0),python-twisted , bugzilla, plone', NULL, NULL);
INSERT INTO sourcepackagerelease (id, sourcepackage, srcpackageformat, creator, "version", dateuploaded, urgency, dscsigningkey, component, changelog, builddepends, builddependsindep, architecturehintlist, dsc) VALUES (10, 6, 1, 9, '0.9.1-6', '2004-07-04 00:00:00', 1, NULL, NULL, NULL, 'mozilla-firefox  (>= 0.9.0-9), mozilla-thunderbird, arch', 'kiwi (>= 2.0),python-twisted , bugzilla, plone', NULL, NULL);
INSERT INTO sourcepackagerelease (id, sourcepackage, srcpackageformat, creator, "version", dateuploaded, urgency, dscsigningkey, component, changelog, builddepends, builddependsindep, architecturehintlist, dsc) VALUES (11, 7, 1, 10, '0.9.1-7', '2004-07-05 00:00:00', 1, NULL, NULL, NULL, 'mozilla-firefox  (>= 0.9.0-9), mozilla-thunderbird, arch', 'kiwi (>= 2.0),python-twisted , bugzilla, plone', NULL, NULL);
INSERT INTO sourcepackagerelease (id, sourcepackage, srcpackageformat, creator, "version", dateuploaded, urgency, dscsigningkey, component, changelog, builddepends, builddependsindep, architecturehintlist, dsc) VALUES (6, 2, 1, 11, '0.9.1-2', '2004-06-30 00:00:00', 1, NULL, NULL, '
mozilla-thunderbird (0.5-4) unstable; urgency=low

  * reenabled hppa patch, which apparently led to FTBFS on hppa

 -- Alexander Sack <asac@jwsdot.com>  Thu, 04 Mar 2004 21:30:20 +0100

mozilla-thunderbird (0.5-3) unstable; urgency=medium

  * preinst added to allow clean upgrade path to this
      (Closes: 234118, Closes: 234267)
  * added prerm script to allow a clean remove of package

 -- Alexander Sack <asac@jwsdot.com>  Sun, 29 Feb 2004 10:30:20 +0100

mozilla-thunderbird (0.5-2) unstable; urgency=low

  * new source package layout!! Now using orig.tar.gz with diff.gz
    (Closes: 232055)
  * moved arch-indep chrome stuff to /usr/share/mozilla-thunderbird/chrome
  * moved images to /usr/share/mozilla-thunderbird/res
      /usr/share/mozilla-thunderbird/icons
      /usr/share/mozilla-thunderbird/chrome/icons

 -- Alexander Sack <asac@jwsdot.com>  Thu, 19 Feb 2004 19:30:20 +0100

mozilla-thunderbird (0.5-1.1) unstable; urgency=low

  * new source package layout!! Now using orig.tar.gz with diff.gz

 -- Alexander Sack <asac@jwsdot.com>  Mon, 11 Feb 2003 19:30:20 +0100

mozilla-thunderbird (0.5-1) unstable; urgency=low

 Aggregated changes since 0.4-1:
  * new upstream release 0.5 included
  * added xprt-xprintorg to Recommends (Closes: 226626)
  * upgraded enigmail to 0.83.2 (Closes: 228678)
      + includes a workaround for mozilla bug
          leading to a crash in rare situations
          (fixed in 0.82.6)
  * improved package structure. Sources now are included as original archives
        & are extracted to build-dir. (Closes: 225033)
  * Minor wording changes in package description, pointed out by
      Mark Stevenson.
  * New debianization of appearance (branding)
  * added switches for pref.js config entries for
        individual doubleclick timeout & drag threshold
        settings in gtk2 (Closes: 229146)

 -- Alexander Sack <asac@jwsdot.com>  Mon, 09 Feb 2003 19:30:20 +0100
', 'mozilla-firefox (>= 0.9.0-9), mozilla-thunderbird, arch', 'kiwi (>= 2.0),python-twisted , bugzilla, plone', NULL, NULL);
INSERT INTO sourcepackagerelease (id, sourcepackage, srcpackageformat, creator, "version", dateuploaded, urgency, dscsigningkey, component, changelog, builddepends, builddependsindep, architecturehintlist, dsc) VALUES (1, 1, 1, 1, '0.9.0-6', '2004-06-17 00:00:00', 1, NULL, NULL, '
mozilla-firefox (0.8-12) unstable; urgency=low

  * The "Last Chance Before 0.9" release.
  * debian/mozilla-firefox-runner: Fix unescaped 
, thanks Olly
    Betts. (Closes: #252436)
  * debian/update-mozilla-firefox-chrome: Watch out for empty
    LD_LIBRARY_PATH. Thanks George Cristian Birzan. (Closes: #254142)
  * debian/README.Debian: Restructure and update a bit.
  * debian/presubj: Add bug information from README.Debian for reportbug.
  * debian/mozilla-firefox.install: Install the presubj.

 -- Eric Dorland <eric@debian.org>  Mon, 14 Jun 2004 19:39:27 -0400

mozilla-firefox (0.8-11) unstable; urgency=low

  * Apply amd64 fix from #249211.
  * debian/README.Debian: Shamelessly stole the java plugin installation
    instructions from the mozilla package. (Closes: #243513)
  * nsCommonWidget.cpp, nsCommonWidget.h, nsWindow.cpp: Apply patch (with
    some hand massaging) from upstream bugzilla bug #209342 to fix initial
    window placement. (Closes: #235209, 241519)
  * nsprpub/pr/src/misc/prnetdb.c: Apply patch from Miquel van Smoorenburg
    to prevent unless reverse DNS lookups. (Closes: #251978)
  * debian/mozilla-firefox-runner: Apply patch from Jasper Spaans to fix
    remote xprint printing. (Closes: #252072)

 -- Eric Dorland <eric@debian.org>  Tue,  1 Jun 2004 23:12:36 -0400

mozilla-firefox (0.8-10) unstable; urgency=low

  * debian/mozilla-firefox.install: Don''t install uuencoded file. (Closes:
    #251441)
  * debian/mozilla-firefox-runner: unset AUDIODEV which can cause
    crashes. Thanks Christopher Armstrong. (Closes: #236231)
  * update-mozilla-firefox-chrome: Port security fix from #249613 to
    handle insecure tempfile creation.
  * debian/rules: Following the advice of #247585 I''m disabling postscript
    printing. Perhaps this will alleviate some of the other printing
    problems.

 -- Eric Dorland <eric@debian.org>  Sun, 30 May 2004 01:47:52 -0400

mozilla-firefox (0.8-9) unstable; urgency=low

  * debian/control:
    - Suggest latex-xft-fonts for MathML fonts. Thanks Michael
      JasonSmith. (Closes: #216925)
    - Build depend on libx11-dev & libxp-dev instead of xlibs-dev to
      reflect new X packages.
  * widget/src/gtk2/nsWindow.cpp: Apply patch from Peter Colberg to ignore
    unused mouse buttons. (Closes: #244305)
  * debian/README.Debian: Document the fact that the loopback interface
    has to be up and unfiltered for things to work right.

 -- Eric Dorland <eric@debian.org>  Wed,  5 May 2004 23:30:42 -0400

', 'mozilla-firefox (>= 0.9.0-9), mozilla-thunderbird, arch', 'kiwi (>= 2.0),python-twisted , bugzilla, plone', NULL, NULL);
INSERT INTO sourcepackagerelease (id, sourcepackage, srcpackageformat, creator, "version", dateuploaded, urgency, dscsigningkey, component, changelog, builddepends, builddependsindep, architecturehintlist, dsc) VALUES (2, 1, 1, 1, '0.9.0-7', '2004-06-18 00:00:00', 1, NULL, NULL, '
mozilla-firefox (0.8-12) unstable; urgency=low

  * The "Last Chance Before 0.9" release.
  * debian/mozilla-firefox-runner: Fix unescaped 
, thanks Olly
    Betts. (Closes: #252436)
  * debian/update-mozilla-firefox-chrome: Watch out for empty
    LD_LIBRARY_PATH. Thanks George Cristian Birzan. (Closes: #254142)
  * debian/README.Debian: Restructure and update a bit.
  * debian/presubj: Add bug information from README.Debian for reportbug.
  * debian/mozilla-firefox.install: Install the presubj.

 -- Eric Dorland <eric@debian.org>  Mon, 14 Jun 2004 19:39:27 -0400

mozilla-firefox (0.8-11) unstable; urgency=low

  * Apply amd64 fix from #249211.
  * debian/README.Debian: Shamelessly stole the java plugin installation
    instructions from the mozilla package. (Closes: #243513)
  * nsCommonWidget.cpp, nsCommonWidget.h, nsWindow.cpp: Apply patch (with
    some hand massaging) from upstream bugzilla bug #209342 to fix initial
    window placement. (Closes: #235209, 241519)
  * nsprpub/pr/src/misc/prnetdb.c: Apply patch from Miquel van Smoorenburg
    to prevent unless reverse DNS lookups. (Closes: #251978)
  * debian/mozilla-firefox-runner: Apply patch from Jasper Spaans to fix
    remote xprint printing. (Closes: #252072)

 -- Eric Dorland <eric@debian.org>  Tue,  1 Jun 2004 23:12:36 -0400

mozilla-firefox (0.8-10) unstable; urgency=low

  * debian/mozilla-firefox.install: Don''t install uuencoded file. (Closes:
    #251441)
  * debian/mozilla-firefox-runner: unset AUDIODEV which can cause
    crashes. Thanks Christopher Armstrong. (Closes: #236231)
  * update-mozilla-firefox-chrome: Port security fix from #249613 to
    handle insecure tempfile creation.
  * debian/rules: Following the advice of #247585 I''m disabling postscript
    printing. Perhaps this will alleviate some of the other printing
    problems.

 -- Eric Dorland <eric@debian.org>  Sun, 30 May 2004 01:47:52 -0400

mozilla-firefox (0.8-9) unstable; urgency=low

  * debian/control:
    - Suggest latex-xft-fonts for MathML fonts. Thanks Michael
      JasonSmith. (Closes: #216925)
    - Build depend on libx11-dev & libxp-dev instead of xlibs-dev to
      reflect new X packages.
  * widget/src/gtk2/nsWindow.cpp: Apply patch from Peter Colberg to ignore
    unused mouse buttons. (Closes: #244305)
  * debian/README.Debian: Document the fact that the loopback interface
    has to be up and unfiltered for things to work right.

 -- Eric Dorland <eric@debian.org>  Wed,  5 May 2004 23:30:42 -0400

', 'mozilla-firefox (>= 0.9.0-9), mozilla-thunderbird, arch', 'kiwi (>= 2.0),python-twisted , bugzilla, plone', NULL, NULL);
INSERT INTO sourcepackagerelease (id, sourcepackage, srcpackageformat, creator, "version", dateuploaded, urgency, dscsigningkey, component, changelog, builddepends, builddependsindep, architecturehintlist, dsc) VALUES (3, 1, 1, 1, '0.9.0-8', '2004-06-19 00:00:00', 1, NULL, NULL, '
mozilla-firefox (0.8-12) unstable; urgency=low

  * The "Last Chance Before 0.9" release.
  * debian/mozilla-firefox-runner: Fix unescaped 
, thanks Olly
    Betts. (Closes: #252436)
  * debian/update-mozilla-firefox-chrome: Watch out for empty
    LD_LIBRARY_PATH. Thanks George Cristian Birzan. (Closes: #254142)
  * debian/README.Debian: Restructure and update a bit.
  * debian/presubj: Add bug information from README.Debian for reportbug.
  * debian/mozilla-firefox.install: Install the presubj.

 -- Eric Dorland <eric@debian.org>  Mon, 14 Jun 2004 19:39:27 -0400

mozilla-firefox (0.8-11) unstable; urgency=low

  * Apply amd64 fix from #249211.
  * debian/README.Debian: Shamelessly stole the java plugin installation
    instructions from the mozilla package. (Closes: #243513)
  * nsCommonWidget.cpp, nsCommonWidget.h, nsWindow.cpp: Apply patch (with
    some hand massaging) from upstream bugzilla bug #209342 to fix initial
    window placement. (Closes: #235209, 241519)
  * nsprpub/pr/src/misc/prnetdb.c: Apply patch from Miquel van Smoorenburg
    to prevent unless reverse DNS lookups. (Closes: #251978)
  * debian/mozilla-firefox-runner: Apply patch from Jasper Spaans to fix
    remote xprint printing. (Closes: #252072)

 -- Eric Dorland <eric@debian.org>  Tue,  1 Jun 2004 23:12:36 -0400

mozilla-firefox (0.8-10) unstable; urgency=low

  * debian/mozilla-firefox.install: Don''t install uuencoded file. (Closes:
    #251441)
  * debian/mozilla-firefox-runner: unset AUDIODEV which can cause
    crashes. Thanks Christopher Armstrong. (Closes: #236231)
  * update-mozilla-firefox-chrome: Port security fix from #249613 to
    handle insecure tempfile creation.
  * debian/rules: Following the advice of #247585 I''m disabling postscript
    printing. Perhaps this will alleviate some of the other printing
    problems.

 -- Eric Dorland <eric@debian.org>  Sun, 30 May 2004 01:47:52 -0400

mozilla-firefox (0.8-9) unstable; urgency=low

  * debian/control:
    - Suggest latex-xft-fonts for MathML fonts. Thanks Michael
      JasonSmith. (Closes: #216925)
    - Build depend on libx11-dev & libxp-dev instead of xlibs-dev to
      reflect new X packages.
  * widget/src/gtk2/nsWindow.cpp: Apply patch from Peter Colberg to ignore
    unused mouse buttons. (Closes: #244305)
  * debian/README.Debian: Document the fact that the loopback interface
    has to be up and unfiltered for things to work right.

 -- Eric Dorland <eric@debian.org>  Wed,  5 May 2004 23:30:42 -0400

', 'mozilla-firefox (>= 0.9.0-9), mozilla-thunderbird, arch', 'kiwi (>= 2.0),python-twisted , bugzilla, plone', NULL, NULL);
INSERT INTO sourcepackagerelease (id, sourcepackage, srcpackageformat, creator, "version", dateuploaded, urgency, dscsigningkey, component, changelog, builddepends, builddependsindep, architecturehintlist, dsc) VALUES (4, 1, 1, 1, '0.9.0-9', '2004-06-20 00:00:00', 1, NULL, NULL, '
mozilla-firefox (0.8-12) unstable; urgency=low

  * The "Last Chance Before 0.9" release.
  * debian/mozilla-firefox-runner: Fix unescaped 
, thanks Olly
    Betts. (Closes: #252436)
  * debian/update-mozilla-firefox-chrome: Watch out for empty
    LD_LIBRARY_PATH. Thanks George Cristian Birzan. (Closes: #254142)
  * debian/README.Debian: Restructure and update a bit.
  * debian/presubj: Add bug information from README.Debian for reportbug.
  * debian/mozilla-firefox.install: Install the presubj.

 -- Eric Dorland <eric@debian.org>  Mon, 14 Jun 2004 19:39:27 -0400

mozilla-firefox (0.8-11) unstable; urgency=low

  * Apply amd64 fix from #249211.
  * debian/README.Debian: Shamelessly stole the java plugin installation
    instructions from the mozilla package. (Closes: #243513)
  * nsCommonWidget.cpp, nsCommonWidget.h, nsWindow.cpp: Apply patch (with
    some hand massaging) from upstream bugzilla bug #209342 to fix initial
    window placement. (Closes: #235209, 241519)
  * nsprpub/pr/src/misc/prnetdb.c: Apply patch from Miquel van Smoorenburg
    to prevent unless reverse DNS lookups. (Closes: #251978)
  * debian/mozilla-firefox-runner: Apply patch from Jasper Spaans to fix
    remote xprint printing. (Closes: #252072)

 -- Eric Dorland <eric@debian.org>  Tue,  1 Jun 2004 23:12:36 -0400

mozilla-firefox (0.8-10) unstable; urgency=low

  * debian/mozilla-firefox.install: Don''t install uuencoded file. (Closes:
    #251441)
  * debian/mozilla-firefox-runner: unset AUDIODEV which can cause
    crashes. Thanks Christopher Armstrong. (Closes: #236231)
  * update-mozilla-firefox-chrome: Port security fix from #249613 to
    handle insecure tempfile creation.
  * debian/rules: Following the advice of #247585 I''m disabling postscript
    printing. Perhaps this will alleviate some of the other printing
    problems.

 -- Eric Dorland <eric@debian.org>  Sun, 30 May 2004 01:47:52 -0400

mozilla-firefox (0.8-9) unstable; urgency=low

  * debian/control:
    - Suggest latex-xft-fonts for MathML fonts. Thanks Michael
      JasonSmith. (Closes: #216925)
    - Build depend on libx11-dev & libxp-dev instead of xlibs-dev to
      reflect new X packages.
  * widget/src/gtk2/nsWindow.cpp: Apply patch from Peter Colberg to ignore
    unused mouse buttons. (Closes: #244305)
  * debian/README.Debian: Document the fact that the loopback interface
    has to be up and unfiltered for things to work right.

 -- Eric Dorland <eric@debian.org>  Wed,  5 May 2004 23:30:42 -0400

', 'mozilla-firefox (>= 0.9.0-9), mozilla-thunderbird, arch', 'kiwi (>= 2.0),python-twisted , bugzilla, plone', NULL, NULL);
INSERT INTO sourcepackagerelease (id, sourcepackage, srcpackageformat, creator, "version", dateuploaded, urgency, dscsigningkey, component, changelog, builddepends, builddependsindep, architecturehintlist, dsc) VALUES (5, 1, 1, 1, '0.9.1-1', '2004-06-29 00:00:00', 1, NULL, NULL, '
mozilla-firefox (0.8-12) unstable; urgency=low

  * The "Last Chance Before 0.9" release.
  * debian/mozilla-firefox-runner: Fix unescaped 
, thanks Olly
    Betts. (Closes: #252436)
  * debian/update-mozilla-firefox-chrome: Watch out for empty
    LD_LIBRARY_PATH. Thanks George Cristian Birzan. (Closes: #254142)
  * debian/README.Debian: Restructure and update a bit.
  * debian/presubj: Add bug information from README.Debian for reportbug.
  * debian/mozilla-firefox.install: Install the presubj.

 -- Eric Dorland <eric@debian.org>  Mon, 14 Jun 2004 19:39:27 -0400

mozilla-firefox (0.8-11) unstable; urgency=low

  * Apply amd64 fix from #249211.
  * debian/README.Debian: Shamelessly stole the java plugin installation
    instructions from the mozilla package. (Closes: #243513)
  * nsCommonWidget.cpp, nsCommonWidget.h, nsWindow.cpp: Apply patch (with
    some hand massaging) from upstream bugzilla bug #209342 to fix initial
    window placement. (Closes: #235209, 241519)
  * nsprpub/pr/src/misc/prnetdb.c: Apply patch from Miquel van Smoorenburg
    to prevent unless reverse DNS lookups. (Closes: #251978)
  * debian/mozilla-firefox-runner: Apply patch from Jasper Spaans to fix
    remote xprint printing. (Closes: #252072)

 -- Eric Dorland <eric@debian.org>  Tue,  1 Jun 2004 23:12:36 -0400

mozilla-firefox (0.8-10) unstable; urgency=low

  * debian/mozilla-firefox.install: Don''t install uuencoded file. (Closes:
    #251441)
  * debian/mozilla-firefox-runner: unset AUDIODEV which can cause
    crashes. Thanks Christopher Armstrong. (Closes: #236231)
  * update-mozilla-firefox-chrome: Port security fix from #249613 to
    handle insecure tempfile creation.
  * debian/rules: Following the advice of #247585 I''m disabling postscript
    printing. Perhaps this will alleviate some of the other printing
    problems.

 -- Eric Dorland <eric@debian.org>  Sun, 30 May 2004 01:47:52 -0400

mozilla-firefox (0.8-9) unstable; urgency=low

  * debian/control:
    - Suggest latex-xft-fonts for MathML fonts. Thanks Michael
      JasonSmith. (Closes: #216925)
    - Build depend on libx11-dev & libxp-dev instead of xlibs-dev to
      reflect new X packages.
  * widget/src/gtk2/nsWindow.cpp: Apply patch from Peter Colberg to ignore
    unused mouse buttons. (Closes: #244305)
  * debian/README.Debian: Document the fact that the loopback interface
    has to be up and unfiltered for things to work right.

 -- Eric Dorland <eric@debian.org>  Wed,  5 May 2004 23:30:42 -0400

', 'mozilla-firefox (>= 0.9.0-9), mozilla-thunderbird, arch', 'kiwi (>= 2.0),python-twisted , bugzilla, plone', NULL, NULL);
INSERT INTO sourcepackagerelease (id, sourcepackage, srcpackageformat, creator, "version", dateuploaded, urgency, dscsigningkey, component, changelog, builddepends, builddependsindep, architecturehintlist, dsc) VALUES (12, 1, 1, 12, '0.9.1-1', '2004-06-29 00:00:00', 1, NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO sourcepackagerelease (id, sourcepackage, srcpackageformat, creator, "version", dateuploaded, urgency, dscsigningkey, component, changelog, builddepends, builddependsindep, architecturehintlist, dsc) VALUES (13, 2, 1, 12, '0.8.0-1', '2004-06-29 00:00:00', 1, NULL, NULL, NULL, NULL, NULL, NULL, NULL);


--
-- Name: sourcepackagereleasefile; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: sourcepackageupload; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO sourcepackageupload (distrorelease, sourcepackagerelease, uploadstatus) VALUES (1, 11, 1);
INSERT INTO sourcepackageupload (distrorelease, sourcepackagerelease, uploadstatus) VALUES (1, 10, 1);
INSERT INTO sourcepackageupload (distrorelease, sourcepackagerelease, uploadstatus) VALUES (1, 1, 6);
INSERT INTO sourcepackageupload (distrorelease, sourcepackagerelease, uploadstatus) VALUES (1, 2, 6);
INSERT INTO sourcepackageupload (distrorelease, sourcepackagerelease, uploadstatus) VALUES (1, 3, 6);
INSERT INTO sourcepackageupload (distrorelease, sourcepackagerelease, uploadstatus) VALUES (1, 4, 4);
INSERT INTO sourcepackageupload (distrorelease, sourcepackagerelease, uploadstatus) VALUES (1, 5, 1);
INSERT INTO sourcepackageupload (distrorelease, sourcepackagerelease, uploadstatus) VALUES (1, 6, 1);
INSERT INTO sourcepackageupload (distrorelease, sourcepackagerelease, uploadstatus) VALUES (3, 7, 1);
INSERT INTO sourcepackageupload (distrorelease, sourcepackagerelease, uploadstatus) VALUES (3, 10, 1);
INSERT INTO sourcepackageupload (distrorelease, sourcepackagerelease, uploadstatus) VALUES (3, 8, 1);
INSERT INTO sourcepackageupload (distrorelease, sourcepackagerelease, uploadstatus) VALUES (5, 8, 1);
INSERT INTO sourcepackageupload (distrorelease, sourcepackagerelease, uploadstatus) VALUES (5, 9, 1);


--
-- Name: build; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO build (id, datecreated, processor, distroarchrelease, buildstate, datebuilt, buildduration, buildlog, builder, gpgsigningkey, changes) VALUES (1, '2004-08-24 00:00:00', 1, 1, 1, NULL, NULL, NULL, NULL, NULL, NULL);


--
-- Name: binarypackagename; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO binarypackagename (id, name) VALUES (1, 'mozilla-firefox');
INSERT INTO binarypackagename (id, name) VALUES (2, 'mozilla-thunderbird');
INSERT INTO binarypackagename (id, name) VALUES (3, 'python-twisted');
INSERT INTO binarypackagename (id, name) VALUES (4, 'bugzilla');
INSERT INTO binarypackagename (id, name) VALUES (5, 'arch');
INSERT INTO binarypackagename (id, name) VALUES (6, 'kiwi');
INSERT INTO binarypackagename (id, name) VALUES (7, 'plone');


--
-- Name: binarypackage; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO binarypackage (id, sourcepackagerelease, binarypackagename, "version", shortdesc, description, build, binpackageformat, component, section, priority, shlibdeps, depends, recommends, suggests, conflicts, replaces, provides, essential, installedsize, copyright, licence) VALUES (1, 5, 1, '0.9.1-1', 'Mozilla Firefox Web Browser', 'Firefox is a redesign of the Mozilla browser component, similar to Galeon, 
	K-Meleon and Camino, but written using the XUL user interface language and 
	designed to lightweight and cross-platform.', 1, 1, 1, 1, 3, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO binarypackage (id, sourcepackagerelease, binarypackagename, "version", shortdesc, description, build, binpackageformat, component, section, priority, shlibdeps, depends, recommends, suggests, conflicts, replaces, provides, essential, installedsize, copyright, licence) VALUES (2, 4, 1, '0.9.0-9', 'Mozilla Firefox Web Browser', 'Firefox is a redesign of the Mozilla browser component, similar to Galeon, 
	K-Meleon and Camino, but written using the XUL user interface language and 
	designed to lightweight and cross-platform.', 1, 1, 1, 1, 3, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO binarypackage (id, sourcepackagerelease, binarypackagename, "version", shortdesc, description, build, binpackageformat, component, section, priority, shlibdeps, depends, recommends, suggests, conflicts, replaces, provides, essential, installedsize, copyright, licence) VALUES (3, 3, 1, '0.9.0-8', 'Mozilla Firefox Web Browser', 'Firefox is a redesign of the Mozilla browser component, similar to Galeon, 
	K-Meleon and Camino, but written using the XUL user interface language and 
	designed to lightweight and cross-platform.', 1, 1, 1, 1, 3, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO binarypackage (id, sourcepackagerelease, binarypackagename, "version", shortdesc, description, build, binpackageformat, component, section, priority, shlibdeps, depends, recommends, suggests, conflicts, replaces, provides, essential, installedsize, copyright, licence) VALUES (4, 2, 1, '0.9.0-7', 'Mozilla Firefox Web Browser', 'Firefox is a redesign of the Mozilla browser component, similar to Galeon, 
	K-Meleon and Camino, but written using the XUL user interface language and 
	designed to lightweight and cross-platform.', 1, 1, 1, 1, 3, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO binarypackage (id, sourcepackagerelease, binarypackagename, "version", shortdesc, description, build, binpackageformat, component, section, priority, shlibdeps, depends, recommends, suggests, conflicts, replaces, provides, essential, installedsize, copyright, licence) VALUES (5, 1, 1, '0.9.0-6', 'Mozilla Firefox Web Browser', 'Firefox is a redesign of the Mozilla browser component, similar to Galeon, 
	K-Meleon and Camino, but written using the XUL user interface language and 
	designed to lightweight and cross-platform.', 1, 1, 1, 1, 3, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO binarypackage (id, sourcepackagerelease, binarypackagename, "version", shortdesc, description, build, binpackageformat, component, section, priority, shlibdeps, depends, recommends, suggests, conflicts, replaces, provides, essential, installedsize, copyright, licence) VALUES (6, 6, 2, '0.9.1-2', 'Mozilla Thunderbird Mail Reader', 'Mozilla Thunderbird is a redesign of the Mozilla mail component. 
	The goal is to produce a cross platform stand alone mail application 
	using the XUL user interface language. Mozilla Thunderbird leaves a 
	somewhat smaller memory footprint than the Mozilla suite.', 1, 1, 1, 1, 3, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO binarypackage (id, sourcepackagerelease, binarypackagename, "version", shortdesc, description, build, binpackageformat, component, section, priority, shlibdeps, depends, recommends, suggests, conflicts, replaces, provides, essential, installedsize, copyright, licence) VALUES (7, 7, 3, '0.9.1-3', 'Python Twisted', 'It includes a web server, a telnet server, a multiplayer RPG engine, 
	a generic client and server for remote object access, and APIs for 
	creating new protocols.', 1, 1, 1, 1, 3, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO binarypackage (id, sourcepackagerelease, binarypackagename, "version", shortdesc, description, build, binpackageformat, component, section, priority, shlibdeps, depends, recommends, suggests, conflicts, replaces, provides, essential, installedsize, copyright, licence) VALUES (8, 8, 4, '0.9.1-4', 'Bugzilla', 'Bugzilla is a "Defect Tracking System" or "Bug-Tracking System". 
	Defect Tracking Systems allow individual or groups of developers 
	to keep track of outstanding bugs in their product effectively.', 1, 1, 1, 1, 3, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO binarypackage (id, sourcepackagerelease, binarypackagename, "version", shortdesc, description, build, binpackageformat, component, section, priority, shlibdeps, depends, recommends, suggests, conflicts, replaces, provides, essential, installedsize, copyright, licence) VALUES (9, 9, 5, '0.9.1-5', 'ARCH', 'arch is a revision control system with features that are ideal for 
	projects characterised by widely distributed development, concurrent 
	support of multiple releases, and substantial amounts of development
	on branches. It can be a replacement for CVS and corrects many 
	mis-features of that system.', 1, 1, 1, 1, 3, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO binarypackage (id, sourcepackagerelease, binarypackagename, "version", shortdesc, description, build, binpackageformat, component, section, priority, shlibdeps, depends, recommends, suggests, conflicts, replaces, provides, essential, installedsize, copyright, licence) VALUES (10, 10, 6, '0.9.1-6', 'Python Kiwi', ' Kiwi2 consists of a set of classes and wrappers for PyGTK-2 that were 
	developed to provide a sort of framework for applications. Fully object-oriented, 
	and roughly modeled after Smalltalk''s MVC, Kiwi provides a simple, practical 
	way to build forms, windows and widgets that transparently access and display
	your object data. Kiwi was primarily designed to make implementing the UI for
	 Stoq easier, and it is released under the LGPL', 1, 1, 1, 1, 3, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO binarypackage (id, sourcepackagerelease, binarypackagename, "version", shortdesc, description, build, binpackageformat, component, section, priority, shlibdeps, depends, recommends, suggests, conflicts, replaces, provides, essential, installedsize, copyright, licence) VALUES (11, 11, 7, '0.9.1-7', 'Plone', 'Plone is powerful and flexible. It is ideal as an intranet and extranet 
	server, as a document publishing system, a portal server and as a groupware
	 tool for collaboration between separately located entities.', 1, 1, 1, 1, 3, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL);


--
-- Name: binarypackagefile; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: packagepublishing; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO packagepublishing (id, binarypackage, distroarchrelease, component, section, priority) VALUES (1, 1, 1, 1, 1, 3);
INSERT INTO packagepublishing (id, binarypackage, distroarchrelease, component, section, priority) VALUES (2, 2, 1, 1, 1, 3);
INSERT INTO packagepublishing (id, binarypackage, distroarchrelease, component, section, priority) VALUES (3, 3, 1, 1, 1, 3);
INSERT INTO packagepublishing (id, binarypackage, distroarchrelease, component, section, priority) VALUES (4, 4, 1, 1, 1, 3);
INSERT INTO packagepublishing (id, binarypackage, distroarchrelease, component, section, priority) VALUES (5, 5, 1, 1, 1, 3);
INSERT INTO packagepublishing (id, binarypackage, distroarchrelease, component, section, priority) VALUES (6, 6, 1, 1, 1, 3);
INSERT INTO packagepublishing (id, binarypackage, distroarchrelease, component, section, priority) VALUES (7, 7, 1, 1, 1, 3);
INSERT INTO packagepublishing (id, binarypackage, distroarchrelease, component, section, priority) VALUES (8, 10, 1, 1, 1, 3);


--
-- Name: packageselection; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: coderelease; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO coderelease (id, productrelease, sourcepackagerelease, manifest) VALUES (1, NULL, 5, 1);
INSERT INTO coderelease (id, productrelease, sourcepackagerelease, manifest) VALUES (2, NULL, 6, 2);
INSERT INTO coderelease (id, productrelease, sourcepackagerelease, manifest) VALUES (3, NULL, 7, 3);
INSERT INTO coderelease (id, productrelease, sourcepackagerelease, manifest) VALUES (4, NULL, 8, 4);
INSERT INTO coderelease (id, productrelease, sourcepackagerelease, manifest) VALUES (5, NULL, 9, 5);
INSERT INTO coderelease (id, productrelease, sourcepackagerelease, manifest) VALUES (6, NULL, 10, 6);
INSERT INTO coderelease (id, productrelease, sourcepackagerelease, manifest) VALUES (7, NULL, 11, 1);
INSERT INTO coderelease (id, productrelease, sourcepackagerelease, manifest) VALUES (8, NULL, 1, 8);
INSERT INTO coderelease (id, productrelease, sourcepackagerelease, manifest) VALUES (9, NULL, 2, 9);


--
-- Name: codereleaserelationship; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: osfile; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: osfileinpackage; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: pomsgid; Type: TABLE DATA; Schema: public; Owner: mark
--

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


--
-- Name: potranslation; Type: TABLE DATA; Schema: public; Owner: mark
--

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


--
-- Name: language; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: country; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (1, 'AF', 'AFG', 'Afghanistan', 'The Transitional Islamic State of Afghanistan', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (2, 'AX', 'ALA', 'Åland Islands', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (3, 'AL', 'ALB', 'Albania', 'Republic of Albania', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (4, 'DZ', 'DZA', 'Algeria', 'People''s Democratic Republic of Algeria', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (5, 'AS', 'ASM', 'American Samoa', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (6, 'AD', 'AND', 'Andorra', 'Principality of Andorra', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (7, 'AO', 'AGO', 'Angola', 'Republic of Angola', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (8, 'AI', 'AIA', 'Anguilla', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (9, 'AQ', 'ATA', 'Antarctica', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (10, 'AG', 'ATG', 'Antigua and Barbuda', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (11, 'AR', 'ARG', 'Argentina', 'Argentine Republic', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (12, 'AM', 'ARM', 'Armenia', 'Republic of Armenia', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (13, 'AW', 'ABW', 'Aruba', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (14, 'AU', 'AUS', 'Australia', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (15, 'AT', 'AUT', 'Austria', 'Republic of Austria', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (16, 'AZ', 'AZE', 'Azerbaijan', 'Republic of Azerbaijan', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (17, 'BS', 'BHS', 'Bahamas', 'Commonwealth of the Bahamas', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (18, 'BH', 'BHR', 'Bahrain', 'State of Bahrain', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (19, 'BD', 'BGD', 'Bangladesh', 'People''s Republic of Bangladesh', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (20, 'BB', 'BRB', 'Barbados', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (21, 'BY', 'BLR', 'Belarus', 'Republic of Belarus', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (22, 'BE', 'BEL', 'Belgium', 'Kingdom of Belgium', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (23, 'BZ', 'BLZ', 'Belize', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (24, 'BJ', 'BEN', 'Benin', 'Republic of Benin', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (25, 'BM', 'BMU', 'Bermuda', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (26, 'BT', 'BTN', 'Bhutan', 'Kingdom of Bhutan', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (27, 'BO', 'BOL', 'Bolivia', 'Republic of Bolivia', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (28, 'BA', 'BIH', 'Bosnia and Herzegovina', 'Republic of Bosnia and Herzegovina', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (29, 'BW', 'BWA', 'Botswana', 'Republic of Botswana', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (30, 'BV', 'BVT', 'Bouvet Island', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (31, 'BR', 'BRA', 'Brazil', 'Federative Republic of Brazil', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (32, 'IO', 'IOT', 'British Indian Ocean Territory', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (33, 'BN', 'BRN', 'Brunei Darussalam', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (34, 'BG', 'BGR', 'Bulgaria', 'Republic of Bulgaria', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (35, 'BF', 'BFA', 'Burkina Faso', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (36, 'BI', 'BDI', 'Burundi', 'Republic of Burundi', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (37, 'KH', 'KHM', 'Cambodia', 'Kingdom of Cambodia', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (38, 'CM', 'CMR', 'Cameroon', 'Republic of Cameroon', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (39, 'CA', 'CAN', 'Canada', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (40, 'CV', 'CPV', 'Cape Verde', 'Republic of Cape Verde', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (41, 'KY', 'CYM', 'Cayman Islands', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (42, 'CF', 'CAF', 'Central African Republic', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (43, 'TD', 'TCD', 'Chad', 'Republic of Chad', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (44, 'CL', 'CHL', 'Chile', 'Republic of Chile', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (45, 'CN', 'CHN', 'China', 'People''s Republic of China', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (46, 'CX', 'CXR', 'Christmas Island', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (47, 'CC', 'CCK', 'Cocos (Keeling) Islands', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (48, 'CO', 'COL', 'Colombia', 'Republic of Colombia', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (49, 'KM', 'COM', 'Comoros', 'Union of the Comoros', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (50, 'CG', 'COG', 'Congo', 'Republic of the Congo', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (51, 'CD', 'ZAR', 'Congo, The Democratic Republic of the', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (52, 'CK', 'COK', 'Cook Islands', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (53, 'CR', 'CRI', 'Costa Rica', 'Republic of Costa Rica', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (54, 'CI', 'CIV', 'Côte d''Ivoire', 'Republic of Cote d''Ivoire', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (55, 'HR', 'HRV', 'Croatia', 'Republic of Croatia', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (56, 'CU', 'CUB', 'Cuba', 'Republic of Cuba', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (57, 'CY', 'CYP', 'Cyprus', 'Republic of Cyprus', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (58, 'CZ', 'CZE', 'Czech Republic', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (59, 'DK', 'DNK', 'Denmark', 'Kingdom of Denmark', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (60, 'DJ', 'DJI', 'Djibouti', 'Republic of Djibouti', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (61, 'DM', 'DMA', 'Dominica', 'Commonwealth of Dominica', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (62, 'DO', 'DOM', 'Dominican Republic', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (63, 'TL', 'TLS', 'Timor-Leste', 'Democratic Republic of Timor-Leste', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (64, 'EC', 'ECU', 'Ecuador', 'Republic of Ecuador', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (65, 'EG', 'EGY', 'Egypt', 'Arab Republic of Egypt', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (66, 'SV', 'SLV', 'El Salvador', 'Republic of El Salvador', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (67, 'GQ', 'GNQ', 'Equatorial Guinea', 'Republic of Equatorial Guinea', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (68, 'ER', 'ERI', 'Eritrea', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (69, 'EE', 'EST', 'Estonia', 'Republic of Estonia', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (70, 'ET', 'ETH', 'Ethiopia', 'Federal Democratic Republic of Ethiopia', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (71, 'FK', 'FLK', 'Falkland Islands (Malvinas)', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (72, 'FO', 'FRO', 'Faroe Islands', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (73, 'FJ', 'FJI', 'Fiji', 'Republic of the Fiji Islands', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (74, 'FI', 'FIN', 'Finland', 'Republic of Finland', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (75, 'FR', 'FRA', 'France', 'French Republic', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (76, 'GF', 'GUF', 'French Guiana', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (77, 'PF', 'PYF', 'French Polynesia', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (78, 'TF', 'ATF', 'French Southern Territories', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (79, 'GA', 'GAB', 'Gabon', 'Gabonese Republic', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (80, 'GM', 'GMB', 'Gambia', 'Republic of the Gambia', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (81, 'GE', 'GEO', 'Georgia', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (82, 'DE', 'DEU', 'Germany', 'Federal Republic of Germany', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (83, 'GH', 'GHA', 'Ghana', 'Republic of Ghana', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (84, 'GI', 'GIB', 'Gibraltar', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (85, 'GR', 'GRC', 'Greece', 'Hellenic Republic', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (86, 'GL', 'GRL', 'Greenland', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (87, 'GD', 'GRD', 'Grenada', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (88, 'GP', 'GLP', 'Guadeloupe', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (89, 'GU', 'GUM', 'Guam', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (90, 'GT', 'GTM', 'Guatemala', 'Republic of Guatemala', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (91, 'GN', 'GIN', 'Guinea', 'Republic of Guinea', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (92, 'GW', 'GNB', 'Guinea-Bissau', 'Republic of Guinea-Bissau', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (93, 'GY', 'GUY', 'Guyana', 'Republic of Guyana', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (94, 'HT', 'HTI', 'Haiti', 'Republic of Haiti', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (95, 'HM', 'HMD', 'Heard Island and McDonald Islands', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (96, 'VA', 'VAT', 'Holy See (Vatican City State)', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (97, 'HN', 'HND', 'Honduras', 'Republic of Honduras', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (98, 'HK', 'HKG', 'Hong Kong', 'Hong Kong Special Administrative Region of China', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (99, 'HU', 'HUN', 'Hungary', 'Republic of Hungary', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (100, 'IS', 'ISL', 'Iceland', 'Republic of Iceland', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (101, 'IN', 'IND', 'India', 'Republic of India', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (102, 'ID', 'IDN', 'Indonesia', 'Republic of Indonesia', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (103, 'IR', 'IRN', 'Iran, Islamic Republic of', 'Islamic Republic of Iran', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (104, 'IQ', 'IRQ', 'Iraq', 'Republic of Iraq', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (105, 'IE', 'IRL', 'Ireland', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (106, 'IL', 'ISR', 'Israel', 'State of Israel', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (107, 'IT', 'ITA', 'Italy', 'Italian Republic', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (108, 'JM', 'JAM', 'Jamaica', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (109, 'JP', 'JPN', 'Japan', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (110, 'JO', 'JOR', 'Jordan', 'Hashemite Kingdom of Jordan', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (111, 'KZ', 'KAZ', 'Kazakhstan', 'Republic of Kazakhstan', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (112, 'KE', 'KEN', 'Kenya', 'Republic of Kenya', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (113, 'KI', 'KIR', 'Kiribati', 'Republic of Kiribati', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (114, 'KP', 'PRK', 'Korea, Democratic People''s Republic of', 'Democratic People''s Republic of Korea', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (115, 'KR', 'KOR', 'Korea, Republic of', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (116, 'KW', 'KWT', 'Kuwait', 'State of Kuwait', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (117, 'KG', 'KGZ', 'Kyrgyzstan', 'Kyrgyz Republic', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (118, 'LA', 'LAO', 'Lao People''s Democratic Republic', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (119, 'LV', 'LVA', 'Latvia', 'Republic of Latvia', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (120, 'LB', 'LBN', 'Lebanon', 'Lebanese Republic', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (121, 'LS', 'LSO', 'Lesotho', 'Kingdom of Lesotho', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (122, 'LR', 'LBR', 'Liberia', 'Republic of Liberia', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (123, 'LY', 'LBY', 'Libyan Arab Jamahiriya', 'Socialist People''s Libyan Arab Jamahiriya', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (124, 'LI', 'LIE', 'Liechtenstein', 'Principality of Liechtenstein', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (125, 'LT', 'LTU', 'Lithuania', 'Republic of Lithuania', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (126, 'LU', 'LUX', 'Luxembourg', 'Grand Duchy of Luxembourg', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (127, 'MO', 'MAC', 'Macao', 'Macao Special Administrative Region of China', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (128, 'MK', 'MKD', 'Macedonia, the Former Yugoslav Republic of', 'The Former Yugoslav Republic of Macedonia', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (129, 'MG', 'MDG', 'Madagascar', 'Republic of Madagascar', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (130, 'MW', 'MWI', 'Malawi', 'Republic of Malawi', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (131, 'MY', 'MYS', 'Malaysia', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (132, 'MV', 'MDV', 'Maldives', 'Republic of Maldives', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (133, 'ML', 'MLI', 'Mali', 'Republic of Mali', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (134, 'MT', 'MLT', 'Malta', 'Republic of Malta', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (135, 'MH', 'MHL', 'Marshall Islands', 'Republic of the Marshall Islands', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (136, 'MQ', 'MTQ', 'Martinique', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (137, 'MR', 'MRT', 'Mauritania', 'Islamic Republic of Mauritania', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (138, 'MU', 'MUS', 'Mauritius', 'Republic of Mauritius', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (139, 'YT', 'MYT', 'Mayotte', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (140, 'MX', 'MEX', 'Mexico', 'United Mexican States', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (141, 'FM', 'FSM', 'Micronesia, Federated States of', 'Federated States of Micronesia', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (142, 'MD', 'MDA', 'Moldova, Republic of', 'Republic of Moldova', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (143, 'MC', 'MCO', 'Monaco', 'Principality of Monaco', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (144, 'MN', 'MNG', 'Mongolia', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (145, 'MS', 'MSR', 'Montserrat', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (146, 'MA', 'MAR', 'Morocco', 'Kingdom of Morocco', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (147, 'MZ', 'MOZ', 'Mozambique', 'Republic of Mozambique', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (148, 'MM', 'MMR', 'Myanmar', 'Union of Myanmar', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (149, 'NA', 'NAM', 'Namibia', 'Republic of Namibia', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (150, 'NR', 'NRU', 'Nauru', 'Republic of Nauru', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (151, 'NP', 'NPL', 'Nepal', 'Kingdom of Nepal', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (152, 'NL', 'NLD', 'Netherlands', 'Kingdom of the Netherlands', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (153, 'AN', 'ANT', 'Netherlands Antilles', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (154, 'NC', 'NCL', 'New Caledonia', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (155, 'NZ', 'NZL', 'New Zealand', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (156, 'NI', 'NIC', 'Nicaragua', 'Republic of Nicaragua', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (157, 'NE', 'NER', 'Niger', 'Republic of the Niger', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (158, 'NG', 'NGA', 'Nigeria', 'Federal Republic of Nigeria', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (159, 'NU', 'NIU', 'Niue', 'Republic of Niue', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (160, 'NF', 'NFK', 'Norfolk Island', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (161, 'MP', 'MNP', 'Northern Mariana Islands', 'Commonwealth of the Northern Mariana Islands', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (162, 'NO', 'NOR', 'Norway', 'Kingdom of Norway', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (163, 'OM', 'OMN', 'Oman', 'Sultanate of Oman', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (164, 'PK', 'PAK', 'Pakistan', 'Islamic Republic of Pakistan', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (165, 'PW', 'PLW', 'Palau', 'Republic of Palau', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (166, 'PS', 'PSE', 'Palestinian Territory, Occupied', 'Occupied Palestinian Territory', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (167, 'PA', 'PAN', 'Panama', 'Republic of Panama', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (168, 'PG', 'PNG', 'Papua New Guinea', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (169, 'PY', 'PRY', 'Paraguay', 'Republic of Paraguay', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (170, 'PE', 'PER', 'Peru', 'Republic of Peru', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (171, 'PH', 'PHL', 'Philippines', 'Republic of the Philippines', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (172, 'PN', 'PCN', 'Pitcairn', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (173, 'PL', 'POL', 'Poland', 'Republic of Poland', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (174, 'PT', 'PRT', 'Portugal', 'Portuguese Republic', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (175, 'PR', 'PRI', 'Puerto Rico', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (176, 'QA', 'QAT', 'Qatar', 'State of Qatar', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (177, 'RE', 'REU', 'Reunion', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (178, 'RO', 'ROU', 'Romania', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (179, 'RU', 'RUS', 'Russian Federation', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (180, 'RW', 'RWA', 'Rwanda', 'Rwandese Republic', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (181, 'SH', 'SHN', 'Saint Helena', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (182, 'KN', 'KNA', 'Saint Kitts and Nevis', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (183, 'LC', 'LCA', 'Saint Lucia', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (184, 'PM', 'SPM', 'Saint Pierre and Miquelon', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (185, 'VC', 'VCT', 'Saint Vincent and the Grenadines', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (186, 'WS', 'WSM', 'Samoa', 'Independent State of Samoa', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (187, 'SM', 'SMR', 'San Marino', 'Republic of San Marino', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (188, 'ST', 'STP', 'Sao Tome and Principe', 'Democratic Republic of Sao Tome and Principe', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (189, 'SA', 'SAU', 'Saudi Arabia', 'Kingdom of Saudi Arabia', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (190, 'SN', 'SEN', 'Senegal', 'Republic of Senegal', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (191, 'SC', 'SYC', 'Seychelles', 'Republic of Seychelles', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (192, 'SL', 'SLE', 'Sierra Leone', 'Republic of Sierra Leone', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (193, 'SG', 'SGP', 'Singapore', 'Republic of Singapore', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (194, 'SK', 'SVK', 'Slovakia', 'Slovak Republic', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (195, 'SI', 'SVN', 'Slovenia', 'Republic of Slovenia', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (196, 'SB', 'SLB', 'Solomon Islands', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (197, 'SO', 'SOM', 'Somalia', 'Somali Republic', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (198, 'ZA', 'ZAF', 'South Africa', 'Republic of South Africa', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (199, 'GS', 'SGS', 'South Georgia and the South Sandwich Islands', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (200, 'ES', 'ESP', 'Spain', 'Kingdom of Spain', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (201, 'LK', 'LKA', 'Sri Lanka', 'Democratic Socialist Republic of Sri Lanka', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (202, 'SD', 'SDN', 'Sudan', 'Republic of the Sudan', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (203, 'SR', 'SUR', 'Suriname', 'Republic of Suriname', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (204, 'SJ', 'SJM', 'Svalbard and Jan Mayen', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (205, 'SZ', 'SWZ', 'Swaziland', 'Kingdom of Swaziland', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (206, 'SE', 'SWE', 'Sweden', 'Kingdom of Sweden', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (207, 'CH', 'CHE', 'Switzerland', 'Swiss Confederation', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (208, 'SY', 'SYR', 'Syrian Arab Republic', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (209, 'TW', 'TWN', 'Taiwan, Province of China', 'Taiwan, Province of China', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (210, 'TJ', 'TJK', 'Tajikistan', 'Republic of Tajikistan', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (211, 'TZ', 'TZA', 'Tanzania, United Republic of', 'United Republic of Tanzania', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (212, 'TH', 'THA', 'Thailand', 'Kingdom of Thailand', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (213, 'TG', 'TGO', 'Togo', 'Togolese Republic', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (214, 'TK', 'TKL', 'Tokelau', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (215, 'TO', 'TON', 'Tonga', 'Kingdom of Tonga', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (216, 'TT', 'TTO', 'Trinidad and Tobago', 'Republic of Trinidad and Tobago', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (217, 'TN', 'TUN', 'Tunisia', 'Republic of Tunisia', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (218, 'TR', 'TUR', 'Turkey', 'Republic of Turkey', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (219, 'TM', 'TKM', 'Turkmenistan', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (220, 'TC', 'TCA', 'Turks and Caicos Islands', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (221, 'TV', 'TUV', 'Tuvalu', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (222, 'UG', 'UGA', 'Uganda', 'Republic of Uganda', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (223, 'UA', 'UKR', 'Ukraine', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (224, 'AE', 'ARE', 'United Arab Emirates', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (225, 'GB', 'GBR', 'United Kingdom', 'United Kingdom of Great Britain and Northern Ireland', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (226, 'US', 'USA', 'United States', 'United States of America', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (227, 'UM', 'UMI', 'United States Minor Outlying Islands', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (228, 'UY', 'URY', 'Uruguay', 'Eastern Republic of Uruguay', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (229, 'UZ', 'UZB', 'Uzbekistan', 'Republic of Uzbekistan', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (230, 'VU', 'VUT', 'Vanuatu', 'Republic of Vanuatu', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (231, 'VE', 'VEN', 'Venezuela', 'Bolivarian Republic of Venezuela', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (232, 'VN', 'VNM', 'Viet Nam', 'Socialist Republic of Viet Nam', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (233, 'VG', 'VGB', 'Virgin Islands, British', 'British Virgin Islands', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (234, 'VI', 'VIR', 'Virgin Islands, U.S.', 'Virgin Islands of the United States', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (235, 'WF', 'WLF', 'Wallis and Futuna', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (236, 'EH', 'ESH', 'Western Sahara', NULL, NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (237, 'YE', 'YEM', 'Yemen', 'Republic of Yemen', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (238, 'ZM', 'ZMB', 'Zambia', 'Republic of Zambia', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (239, 'ZW', 'ZWE', 'Zimbabwe', 'Republic of Zimbabwe', NULL);
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (240, 'CS', 'SCG', 'Serbia and Montenegro', NULL, NULL);


--
-- Name: spokenin; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: license; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO license (id, legalese) VALUES (1, 'GPL-2');


--
-- Name: potemplate; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO potemplate (id, product, priority, branch, changeset, name, title, description, copyright, license, datecreated, "path", iscurrent, messagecount, "owner") VALUES (1, 5, 2, 8, NULL, 'evolution-2.0', 'Main POT file for the Evolution 2.0 development branch', 'I suppose we should create a long description here....', 'Copyright (C) 2003  Ximian Inc.', 1, '2004-08-17 09:10:00', 'po/', true, 3, 13);
INSERT INTO potemplate (id, product, priority, branch, changeset, name, title, description, copyright, license, datecreated, "path", iscurrent, messagecount, "owner") VALUES (2, 7, 2, 9, NULL, 'languages', 'POT file for the iso_639 strings', 'I suppose we should create a long description here....', 'Copyright', 1, '2004-08-17 09:10:00', 'iso_639/', true, 3, 13);


--
-- Name: pofile; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO pofile (id, potemplate, "language", title, description, topcomment, header, fuzzyheader, lasttranslator, license, currentcount, updatescount, rosettacount, lastparsed, "owner", pluralforms, variant, filename) VALUES (1, 1, 387, NULL, NULL, ' traducción de es.po al Spanish
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
', false, 13, NULL, 2, 0, 1, NULL, NULL, 2, NULL, NULL);


--
-- Name: pomsgset; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO pomsgset (id, primemsgid, "sequence", potemplate, pofile, iscomplete, obsolete, fuzzy, commenttext, filereferences, sourcecomment, flagscomment) VALUES (1, 1, 1, 1, NULL, false, false, false, NULL, 'a11y/addressbook/ea-addressbook-view.c:94
a11y/addressbook/ea-addressbook-view.c:103
a11y/addressbook/ea-minicard-view.c:119', NULL, NULL);
INSERT INTO pomsgset (id, primemsgid, "sequence", potemplate, pofile, iscomplete, obsolete, fuzzy, commenttext, filereferences, sourcecomment, flagscomment) VALUES (2, 2, 2, 1, NULL, false, false, false, NULL, 'a11y/addressbook/ea-minicard-view.c:101', NULL, NULL);
INSERT INTO pomsgset (id, primemsgid, "sequence", potemplate, pofile, iscomplete, obsolete, fuzzy, commenttext, filereferences, sourcecomment, flagscomment) VALUES (3, 3, 3, 1, NULL, false, false, false, NULL, 'a11y/addressbook/ea-minicard-view.c:102', NULL, NULL);
INSERT INTO pomsgset (id, primemsgid, "sequence", potemplate, pofile, iscomplete, obsolete, fuzzy, commenttext, filereferences, sourcecomment, flagscomment) VALUES (4, 4, 4, 1, NULL, false, false, false, NULL, 'a11y/addressbook/ea-minicard-view.c:102', NULL, NULL);
INSERT INTO pomsgset (id, primemsgid, "sequence", potemplate, pofile, iscomplete, obsolete, fuzzy, commenttext, filereferences, sourcecomment, flagscomment) VALUES (5, 5, 5, 1, NULL, false, false, false, NULL, 'a11y/addressbook/ea-minicard-view.c:104', NULL, NULL);
INSERT INTO pomsgset (id, primemsgid, "sequence", potemplate, pofile, iscomplete, obsolete, fuzzy, commenttext, filereferences, sourcecomment, flagscomment) VALUES (6, 6, 6, 1, NULL, false, false, false, NULL, 'a11y/addressbook/ea-minicard-view.c:104', NULL, NULL);
INSERT INTO pomsgset (id, primemsgid, "sequence", potemplate, pofile, iscomplete, obsolete, fuzzy, commenttext, filereferences, sourcecomment, flagscomment) VALUES (7, 7, 7, 1, NULL, false, false, false, NULL, 'a11y/addressbook/ea-minicard-view.c:105', NULL, NULL);
INSERT INTO pomsgset (id, primemsgid, "sequence", potemplate, pofile, iscomplete, obsolete, fuzzy, commenttext, filereferences, sourcecomment, flagscomment) VALUES (8, 8, 8, 1, NULL, false, false, false, NULL, 'a11y/addressbook/ea-minicard.c:166', NULL, NULL);
INSERT INTO pomsgset (id, primemsgid, "sequence", potemplate, pofile, iscomplete, obsolete, fuzzy, commenttext, filereferences, sourcecomment, flagscomment) VALUES (9, 9, 9, 1, NULL, false, false, false, NULL, 'addressbook/addressbook-errors.xml.h:2', 'addressbook:ldap-init primary', NULL);
INSERT INTO pomsgset (id, primemsgid, "sequence", potemplate, pofile, iscomplete, obsolete, fuzzy, commenttext, filereferences, sourcecomment, flagscomment) VALUES (10, 10, 10, 1, NULL, false, false, false, NULL, 'addressbook/addressbook-errors.xml.h:4', 'addressbook:ldap-init secondary', NULL);
INSERT INTO pomsgset (id, primemsgid, "sequence", potemplate, pofile, iscomplete, obsolete, fuzzy, commenttext, filereferences, sourcecomment, flagscomment) VALUES (11, 11, 11, 1, NULL, false, false, false, NULL, 'addressbook/addressbook-errors.xml.h:6', 'addressbook:ldap-auth primary', NULL);
INSERT INTO pomsgset (id, primemsgid, "sequence", potemplate, pofile, iscomplete, obsolete, fuzzy, commenttext, filereferences, sourcecomment, flagscomment) VALUES (12, 12, 12, 1, NULL, false, false, false, NULL, 'addressbook/addressbook-errors.xml.h:8', 'addressbook:ldap-auth secondary', NULL);
INSERT INTO pomsgset (id, primemsgid, "sequence", potemplate, pofile, iscomplete, obsolete, fuzzy, commenttext, filereferences, sourcecomment, flagscomment) VALUES (13, 62, 13, 1, NULL, false, false, false, NULL, 'addressbook/gui/component/addressbook-migrate.c:124
calendar/gui/migration.c:188 mail/em-migrate.c:1201', NULL, 'c-format');
INSERT INTO pomsgset (id, primemsgid, "sequence", potemplate, pofile, iscomplete, obsolete, fuzzy, commenttext, filereferences, sourcecomment, flagscomment) VALUES (14, 68, 14, 1, NULL, false, false, false, NULL, 'addressbook/gui/component/addressbook-migrate.c:1123', NULL, NULL);
INSERT INTO pomsgset (id, primemsgid, "sequence", potemplate, pofile, iscomplete, obsolete, fuzzy, commenttext, filereferences, sourcecomment, flagscomment) VALUES (15, 93, 15, 1, NULL, false, false, false, NULL, 'addressbook/gui/widgets/e-addressbook-model.c:151', NULL, 'c-format');
INSERT INTO pomsgset (id, primemsgid, "sequence", potemplate, pofile, iscomplete, obsolete, fuzzy, commenttext, filereferences, sourcecomment, flagscomment) VALUES (16, 95, 16, 1, NULL, false, false, false, NULL, 'addressbook/gui/widgets/eab-gui-util.c:275', NULL, 'c-format');
INSERT INTO pomsgset (id, primemsgid, "sequence", potemplate, pofile, iscomplete, obsolete, fuzzy, commenttext, filereferences, sourcecomment, flagscomment) VALUES (17, 1, 1, 1, 1, true, false, false, NULL, NULL, NULL, NULL);
INSERT INTO pomsgset (id, primemsgid, "sequence", potemplate, pofile, iscomplete, obsolete, fuzzy, commenttext, filereferences, sourcecomment, flagscomment) VALUES (18, 2, 2, 1, 1, true, false, false, NULL, NULL, NULL, NULL);
INSERT INTO pomsgset (id, primemsgid, "sequence", potemplate, pofile, iscomplete, obsolete, fuzzy, commenttext, filereferences, sourcecomment, flagscomment) VALUES (19, 3, 3, 1, 1, false, false, true, NULL, NULL, NULL, NULL);
INSERT INTO pomsgset (id, primemsgid, "sequence", potemplate, pofile, iscomplete, obsolete, fuzzy, commenttext, filereferences, sourcecomment, flagscomment) VALUES (20, 93, 4, 1, 1, true, false, false, NULL, NULL, NULL, NULL);
INSERT INTO pomsgset (id, primemsgid, "sequence", potemplate, pofile, iscomplete, obsolete, fuzzy, commenttext, filereferences, sourcecomment, flagscomment) VALUES (21, 68, 5, 1, 1, true, false, false, ' This is an example of commenttext for a multiline msgset', NULL, NULL, NULL);
INSERT INTO pomsgset (id, primemsgid, "sequence", potemplate, pofile, iscomplete, obsolete, fuzzy, commenttext, filereferences, sourcecomment, flagscomment) VALUES (22, 95, 6, 1, 1, true, false, false, NULL, NULL, NULL, NULL);
INSERT INTO pomsgset (id, primemsgid, "sequence", potemplate, pofile, iscomplete, obsolete, fuzzy, commenttext, filereferences, sourcecomment, flagscomment) VALUES (23, 97, 7, 1, 1, true, true, false, NULL, NULL, NULL, NULL);


--
-- Name: pomsgidsighting; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO pomsgidsighting (id, pomsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (1, 1, 1, '2004-09-24 21:58:04.969875', '2004-09-24 21:58:04.969875', true, 0);
INSERT INTO pomsgidsighting (id, pomsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (2, 2, 2, '2004-09-24 21:58:05.005673', '2004-09-24 21:58:05.005673', true, 0);
INSERT INTO pomsgidsighting (id, pomsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (3, 3, 3, '2004-09-24 21:58:05.11396', '2004-09-24 21:58:05.11396', true, 0);
INSERT INTO pomsgidsighting (id, pomsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (4, 4, 4, '2004-09-24 21:58:05.148051', '2004-09-24 21:58:05.148051', true, 0);
INSERT INTO pomsgidsighting (id, pomsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (5, 5, 5, '2004-09-24 21:58:05.181877', '2004-09-24 21:58:05.181877', true, 0);
INSERT INTO pomsgidsighting (id, pomsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (6, 6, 6, '2004-09-24 21:58:05.216203', '2004-09-24 21:58:05.216203', true, 0);
INSERT INTO pomsgidsighting (id, pomsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (7, 7, 7, '2004-09-24 21:58:05.250458', '2004-09-24 21:58:05.250458', true, 0);
INSERT INTO pomsgidsighting (id, pomsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (8, 8, 8, '2004-09-24 21:58:05.283205', '2004-09-24 21:58:05.283205', true, 0);
INSERT INTO pomsgidsighting (id, pomsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (9, 9, 9, '2004-09-24 21:58:05.301434', '2004-09-24 21:58:05.301434', true, 0);
INSERT INTO pomsgidsighting (id, pomsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (10, 10, 10, '2004-09-24 21:58:05.319483', '2004-09-24 21:58:05.319483', true, 0);
INSERT INTO pomsgidsighting (id, pomsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (11, 11, 11, '2004-09-24 21:58:05.337554', '2004-09-24 21:58:05.337554', true, 0);
INSERT INTO pomsgidsighting (id, pomsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (12, 12, 12, '2004-09-24 21:58:05.355659', '2004-09-24 21:58:05.355659', true, 0);
INSERT INTO pomsgidsighting (id, pomsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (13, 13, 62, '2004-09-24 21:58:05.650973', '2004-09-24 21:58:05.650973', true, 0);
INSERT INTO pomsgidsighting (id, pomsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (14, 14, 68, '2004-09-24 21:58:05.701435', '2004-09-24 21:58:05.701435', true, 0);
INSERT INTO pomsgidsighting (id, pomsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (15, 15, 93, '2004-09-24 21:58:05.868655', '2004-09-24 21:58:05.868655', true, 0);
INSERT INTO pomsgidsighting (id, pomsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (16, 15, 94, '2004-09-24 21:58:05.870713', '2004-09-24 21:58:05.870713', true, 0);
INSERT INTO pomsgidsighting (id, pomsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (17, 16, 95, '2004-09-24 21:58:05.902536', '2004-09-24 21:58:05.902536', true, 0);
INSERT INTO pomsgidsighting (id, pomsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (18, 16, 96, '2004-09-24 21:58:05.904686', '2004-09-24 21:58:05.904686', true, 0);
INSERT INTO pomsgidsighting (id, pomsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (19, 17, 1, '2004-09-24 21:58:05.974138', '2004-09-24 21:58:05.974138', true, 0);
INSERT INTO pomsgidsighting (id, pomsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (20, 18, 2, '2004-09-24 21:58:06.024526', '2004-09-24 21:58:06.024526', true, 0);
INSERT INTO pomsgidsighting (id, pomsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (21, 19, 3, '2004-09-24 21:58:06.070179', '2004-09-24 21:58:06.070179', true, 0);
INSERT INTO pomsgidsighting (id, pomsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (22, 20, 93, '2004-09-24 21:58:06.137789', '2004-09-24 21:58:06.137789', true, 0);
INSERT INTO pomsgidsighting (id, pomsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (23, 20, 94, '2004-09-24 21:58:06.13923', '2004-09-24 21:58:06.13923', true, 1);
INSERT INTO pomsgidsighting (id, pomsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (24, 21, 68, '2004-09-24 21:58:06.204569', '2004-09-24 21:58:06.204569', true, 0);
INSERT INTO pomsgidsighting (id, pomsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (25, 22, 95, '2004-09-24 21:58:06.239604', '2004-09-24 21:58:06.239604', true, 0);
INSERT INTO pomsgidsighting (id, pomsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (26, 22, 96, '2004-09-24 21:58:06.255259', '2004-09-24 21:58:06.255259', true, 1);
INSERT INTO pomsgidsighting (id, pomsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (27, 23, 97, '2004-09-24 21:58:06.306292', '2004-09-24 21:58:06.306292', true, 0);


--
-- Name: potranslationsighting; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO potranslationsighting (id, pomsgset, potranslation, license, datefirstseen, datelastactive, inlastrevision, pluralform, active, origin, person) VALUES (1, 17, 1, 1, '2004-09-24 21:58:05.989829', '2004-09-24 21:58:05.989829', true, 0, true, 0, 13);
INSERT INTO potranslationsighting (id, pomsgset, potranslation, license, datefirstseen, datelastactive, inlastrevision, pluralform, active, origin, person) VALUES (2, 18, 2, 1, '2004-09-24 21:58:06.036589', '2004-09-24 21:58:06.036589', true, 0, true, 0, 13);
INSERT INTO potranslationsighting (id, pomsgset, potranslation, license, datefirstseen, datelastactive, inlastrevision, pluralform, active, origin, person) VALUES (3, 19, 3, 1, '2004-09-24 21:58:06.086645', '2004-09-24 21:58:06.086645', true, 0, true, 0, 13);
INSERT INTO potranslationsighting (id, pomsgset, potranslation, license, datefirstseen, datelastactive, inlastrevision, pluralform, active, origin, person) VALUES (4, 20, 4, 1, '2004-09-24 21:58:06.154994', '2004-09-24 21:58:06.154994', true, 0, true, 0, 13);
INSERT INTO potranslationsighting (id, pomsgset, potranslation, license, datefirstseen, datelastactive, inlastrevision, pluralform, active, origin, person) VALUES (5, 20, 5, 1, '2004-09-24 21:58:06.15703', '2004-09-24 21:58:06.15703', true, 1, true, 0, 13);
INSERT INTO potranslationsighting (id, pomsgset, potranslation, license, datefirstseen, datelastactive, inlastrevision, pluralform, active, origin, person) VALUES (6, 21, 6, 1, '2004-09-24 21:58:06.206034', '2004-09-24 21:58:06.206034', true, 0, true, 0, 13);
INSERT INTO potranslationsighting (id, pomsgset, potranslation, license, datefirstseen, datelastactive, inlastrevision, pluralform, active, origin, person) VALUES (7, 22, 7, 1, '2004-09-24 21:58:06.256662', '2004-09-24 21:58:06.256662', true, 0, true, 0, 13);
INSERT INTO potranslationsighting (id, pomsgset, potranslation, license, datefirstseen, datelastactive, inlastrevision, pluralform, active, origin, person) VALUES (8, 22, 8, 1, '2004-09-24 21:58:06.273004', '2004-09-24 21:58:06.273004', true, 1, true, 0, 13);
INSERT INTO potranslationsighting (id, pomsgset, potranslation, license, datefirstseen, datelastactive, inlastrevision, pluralform, active, origin, person) VALUES (9, 23, 9, 1, '2004-09-24 21:58:06.307785', '2004-09-24 21:58:06.307785', true, 0, true, 0, 13);


--
-- Name: pocomment; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: translationeffort; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: translationeffortpotemplate; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: posubscription; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: bug; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO bug (id, datecreated, name, title, description, "owner", duplicateof, communityscore, communitytimestamp, activityscore, activitytimestamp, hits, hitstimestamp, shortdesc) VALUES (2, '2004-09-24 20:58:04.572546', 'blackhole', 'Blackhole Trash folder', 'The Trash folder seems to have significant problems! At the moment, dragging an item to the trash results in immediate deletion. The item does not appear in the Trash, it is just deleted from my hard disk. There is no undo or ability to recover the deleted file. Help!', 12, NULL, 0, '2004-09-24 00:00:00', 0, '2004-09-24 00:00:00', 0, '2004-09-24 00:00:00', 'Everything put into the folder "Trash" disappears!');
INSERT INTO bug (id, datecreated, name, title, description, "owner", duplicateof, communityscore, communitytimestamp, activityscore, activitytimestamp, hits, hitstimestamp, shortdesc) VALUES (1, '2004-09-24 20:58:04.553583', NULL, 'Firefox does not support SVG', 'The SVG standard 1.0 is complete, and draft implementations for Firefox exist. One of these implementations needs to be integrated with the base install of Firefox. Ideally, the implementation needs to include support for the manipulation of SVG objects from JavaScript to enable interactive and dynamic SVG drawings.', 12, NULL, 0, '2004-09-24 00:00:00', 0, '2004-09-24 00:00:00', 0, '2004-09-24 00:00:00', 'Firefox needs to support embedded SVG images, now that the standard has been finalised.');


--
-- Name: bugsubscription; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: buginfestation; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: sourcepackagebugassignment; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO sourcepackagebugassignment (id, bug, sourcepackage, bugstatus, priority, severity, binarypackage, assignee) VALUES (1, 1, 1, 2, 4, 2, NULL, NULL);
INSERT INTO sourcepackagebugassignment (id, bug, sourcepackage, bugstatus, priority, severity, binarypackage, assignee) VALUES (2, 2, 8, 2, 4, 2, NULL, 12);


--
-- Name: productbugassignment; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO productbugassignment (id, bug, product, bugstatus, priority, severity, assignee) VALUES (1, 1, 4, 1, 2, 2, NULL);
INSERT INTO productbugassignment (id, bug, product, bugstatus, priority, severity, assignee) VALUES (2, 2, 8, 1, 2, 2, NULL);


--
-- Name: bugactivity; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO bugactivity (id, bug, datechanged, person, whatchanged, oldvalue, newvalue, message) VALUES (1, 1, '2004-09-24 00:00:00', 1, 'title', 'A silly problem', 'An odd problem', 'Decided problem wasn''t silly after all');


--
-- Name: bugexternalref; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO bugexternalref (id, bug, bugreftype, data, description, datecreated, "owner") VALUES (1, 2, 1, '45', 'Some junk has to go here because the field is NOT NULL', '2004-09-24 20:58:04.702498', 12);
INSERT INTO bugexternalref (id, bug, bugreftype, data, description, datecreated, "owner") VALUES (2, 2, 2, 'http://www.mozilla.org', 'The homepage of the project this bug is on, for no particular reason', '2004-09-24 20:58:04.720774', 12);


--
-- Name: bugsystemtype; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO bugsystemtype (id, name, title, description, homepage, "owner") VALUES (1, 'bugzilla', 'BugZilla', 'Dave Miller''s Labour of Love, the Godfather of Open Source project issue tracking.', 'http://www.bugzilla.org/', 12);


--
-- Name: bugsystem; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO bugsystem (id, bugsystemtype, name, title, shortdesc, baseurl, "owner", contactdetails) VALUES (1, 1, 'mozilla.org', 'The Mozilla.org Bug Tracker', 'The Mozilla.org bug tracker', 'http://www.example.com/bugtracker', 12, 'Carrier pidgeon only');


--
-- Name: bugwatch; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO bugwatch (id, bug, bugsystem, remotebug, remotestatus, lastchanged, lastchecked, datecreated, "owner") VALUES (1, 2, 1, '42', 'FUBAR', '2004-09-24 20:58:04.740841', '2004-09-24 20:58:04.740841', '2004-09-24 20:58:04.740841', 12);


--
-- Name: projectbugsystem; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: buglabel; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: bugrelationship; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: bugmessage; Type: TABLE DATA; Schema: public; Owner: mark
--

INSERT INTO bugmessage (id, bug, datecreated, title, contents, "owner", parent, distribution, rfc822msgid) VALUES (1, 2, '2004-09-24 20:58:04.684057', 'PEBCAK', 'Problem exists between chair and keyboard', NULL, NULL, NULL, 'foo@example.com-332342--1231');
INSERT INTO bugmessage (id, bug, datecreated, title, contents, "owner", parent, distribution, rfc822msgid) VALUES (3, 1, '2004-09-24 21:17:17.153792', 'Reproduced on AIX', 'We''ve seen something very similar on AIX with Gnome 2.6 when it is compiled with XFT support. It might be that the anti-aliasing is causing loopback devices to degrade, resulting in a loss of transparency at the system cache level and decoherence in the undelete function. This is only known to be a problem when the moon is gibbous.', 12, NULL, NULL, 'sdsdfsfd');
INSERT INTO bugmessage (id, bug, datecreated, title, contents, "owner", parent, distribution, rfc822msgid) VALUES (4, 1, '2004-09-24 21:24:03.922564', 'Re: Reproduced on AIX', 'Sorry, it was SCO unix which appears to have the same bug. For a brief moment I was confused there, since so much code is known to have been copied from SCO into AIX.', 12, NULL, NULL, 'sdfssfdfsd');
INSERT INTO bugmessage (id, bug, datecreated, title, contents, "owner", parent, distribution, rfc822msgid) VALUES (5, 2, '2004-09-24 21:29:27.407354', 'Fantastic idea, I''d really like to see this', 'This would be a real killer feature. If there is already code to make it possible, why aren''t there tons of press announcements about the secuirty possibilities. Imagine - no more embarrassing emails for Mr Gates... everything they delete would actually disappear! I''m sure Redmond will switch over as soon as they hear about this. It''s not a bug, it''s a feature!', 12, NULL, NULL, 'dxssdfsdgf');
INSERT INTO bugmessage (id, bug, datecreated, title, contents, "owner", parent, distribution, rfc822msgid) VALUES (6, 2, '2004-09-24 21:35:20.125564', 'Strange bug with duplicate messages.', 'Oddly enough the bug system seems only capable of displaying the first two comments that are made against a bug. I wonder why that is? Lets have a few more decent legth comments in here so we can see what the spacing is like. Also, at some stage, we''ll need a few comments that get displayed in a fixed-width font, so we have a clue about code-in-bug-comments etc.', 12, NULL, NULL, 'sdfsfwew');


--
-- Name: bugattachment; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: sourcesource; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: componentselection; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: sectionselection; Type: TABLE DATA; Schema: public; Owner: mark
--



--
-- Name: person_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('person_id_seq', 21, true);


--
-- Name: emailaddress_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('emailaddress_id_seq', 19, true);


--
-- Name: gpgkey_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('gpgkey_id_seq', 10, true);


--
-- Name: archuserid_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('archuserid_id_seq', 10, true);


--
-- Name: wikiname_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('wikiname_id_seq', 10, true);


--
-- Name: jabberid_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('jabberid_id_seq', 10, true);


--
-- Name: ircid_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('ircid_id_seq', 9, true);


--
-- Name: membership_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('membership_id_seq', 8, true);


--
-- Name: teamparticipation_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('teamparticipation_id_seq', 11, true);


--
-- Name: schema_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('schema_id_seq', 5, true);


--
-- Name: label_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('label_id_seq', 466, true);


--
-- Name: project_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('project_id_seq', 6, true);


--
-- Name: projectrelationship_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('projectrelationship_id_seq', 1, false);


--
-- Name: projectrole_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('projectrole_id_seq', 1, false);


--
-- Name: product_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('product_id_seq', 8, true);


--
-- Name: productlabel_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('productlabel_id_seq', 1, false);


--
-- Name: productrole_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('productrole_id_seq', 1, false);


--
-- Name: productseries_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('productseries_id_seq', 1, false);


--
-- Name: productrelease_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('productrelease_id_seq', 2, true);


--
-- Name: productcvsmodule_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('productcvsmodule_id_seq', 1, false);


--
-- Name: productbkbranch_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('productbkbranch_id_seq', 1, false);


--
-- Name: productsvnmodule_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('productsvnmodule_id_seq', 1, false);


--
-- Name: archarchive_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('archarchive_id_seq', 9, true);


--
-- Name: archarchivelocation_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('archarchivelocation_id_seq', 1, false);


--
-- Name: archnamespace_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('archnamespace_id_seq', 9, true);


--
-- Name: branch_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('branch_id_seq', 9, true);


--
-- Name: changeset_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('changeset_id_seq', 1, false);


--
-- Name: changesetfilename_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('changesetfilename_id_seq', 1, false);


--
-- Name: changesetfile_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('changesetfile_id_seq', 1, false);


--
-- Name: changesetfilehash_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('changesetfilehash_id_seq', 1, false);


--
-- Name: productbranchrelationship_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('productbranchrelationship_id_seq', 1, false);


--
-- Name: manifest_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('manifest_id_seq', 9, true);


--
-- Name: manifestentry_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('manifestentry_id_seq', 1, false);


--
-- Name: archconfig_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('archconfig_id_seq', 1, false);


--
-- Name: processorfamily_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('processorfamily_id_seq', 1, true);


--
-- Name: processor_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('processor_id_seq', 1, true);


--
-- Name: builder_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('builder_id_seq', 1, false);


--
-- Name: component_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('component_id_seq', 1, true);


--
-- Name: section_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('section_id_seq', 1, true);


--
-- Name: distribution_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('distribution_id_seq', 5, true);


--
-- Name: distrorelease_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('distrorelease_id_seq', 8, true);


--
-- Name: distroarchrelease_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('distroarchrelease_id_seq', 1, true);


--
-- Name: libraryfilecontent_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('libraryfilecontent_id_seq', 1, false);


--
-- Name: libraryfilealias_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('libraryfilealias_id_seq', 1, false);


--
-- Name: sourcepackagename_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('sourcepackagename_id_seq', 8, true);


--
-- Name: sourcepackage_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('sourcepackage_id_seq', 8, true);


--
-- Name: sourcepackagerelease_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('sourcepackagerelease_id_seq', 13, true);


--
-- Name: build_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('build_id_seq', 1, true);


--
-- Name: binarypackagename_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('binarypackagename_id_seq', 7, true);


--
-- Name: binarypackage_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('binarypackage_id_seq', 11, true);


--
-- Name: packagepublishing_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('packagepublishing_id_seq', 8, true);


--
-- Name: packageselection_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('packageselection_id_seq', 1, false);


--
-- Name: coderelease_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('coderelease_id_seq', 9, true);


--
-- Name: osfile_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('osfile_id_seq', 1, false);


--
-- Name: pomsgid_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('pomsgid_id_seq', 97, true);


--
-- Name: potranslation_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('potranslation_id_seq', 9, true);


--
-- Name: language_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('language_id_seq', 632, true);


--
-- Name: country_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('country_id_seq', 240, true);


--
-- Name: license_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('license_id_seq', 1, true);


--
-- Name: potemplate_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('potemplate_id_seq', 2, true);


--
-- Name: pofile_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('pofile_id_seq', 1, true);


--
-- Name: pomsgset_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('pomsgset_id_seq', 23, true);


--
-- Name: pomsgidsighting_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('pomsgidsighting_id_seq', 27, true);


--
-- Name: potranslationsighting_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('potranslationsighting_id_seq', 9, true);


--
-- Name: pocomment_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('pocomment_id_seq', 1, false);


--
-- Name: translationeffort_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('translationeffort_id_seq', 1, false);


--
-- Name: posubscription_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('posubscription_id_seq', 1, false);


--
-- Name: bug_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('bug_id_seq', 2, true);


--
-- Name: bugsubscription_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('bugsubscription_id_seq', 1, false);


--
-- Name: sourcepackagebugassignment_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('sourcepackagebugassignment_id_seq', 2, true);


--
-- Name: productbugassignment_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('productbugassignment_id_seq', 2, true);


--
-- Name: bugactivity_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('bugactivity_id_seq', 1, true);


--
-- Name: bugexternalref_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('bugexternalref_id_seq', 2, true);


--
-- Name: bugsystemtype_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('bugsystemtype_id_seq', 1, true);


--
-- Name: bugsystem_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('bugsystem_id_seq', 1, true);


--
-- Name: bugwatch_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('bugwatch_id_seq', 1, true);


--
-- Name: bugmessage_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('bugmessage_id_seq', 6, true);


--
-- Name: bugattachment_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('bugattachment_id_seq', 1, false);


--
-- Name: sourcesource_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('sourcesource_id_seq', 1, false);


--
-- Name: projectbugsystem_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('projectbugsystem_id_seq', 1, false);


--
-- Name: distributionrole_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('distributionrole_id_seq', 7, true);


--
-- Name: distroreleaserole_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('distroreleaserole_id_seq', 9, true);


--
-- Name: componentselection_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('componentselection_id_seq', 1, false);


--
-- Name: sectionselection_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mark
--

SELECT pg_catalog.setval('sectionselection_id_seq', 1, false);


