
SET check_function_bodies = false;
SET client_encoding = 'UNICODE';

SET search_path = public, pg_catalog;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'person'::pg_catalog.regclass;

INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (1, 'Mark Shuttleworth', 'Mark', 'Shuttleworth', 'K7Qmeansl6RbuPfulfcmyDQOzp70OxVh5Fcf', NULL, NULL, 'sabdfl', NULL, '''mark'':2B,4C ''sabdfl'':1A ''shuttleworth'':3B,5C', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.591618', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (2, 'Robert Collins', 'Robert', 'Collins', 'ID1adsprLaTBox18F6dpSdtSdqCiOdpgUXBo4oG17qhg73jSDTVe3g==', NULL, NULL, 'lifeless', NULL, '''collin'':3B,5C ''robert'':2B,4C ''lifeless'':1A', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.598107', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (3, 'Dave Miller', 'Dave', 'Miller', NULL, NULL, NULL, 'justdave', NULL, '''dave'':2B,4C ''miller'':3B,5C ''justdav'':1A', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.610048', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (4, 'Colin Watson', 'Colin', 'Watson', NULL, NULL, NULL, 'kamion', NULL, '''colin'':2B,4C ''kamion'':1A ''watson'':3B,5C', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.611185', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (5, 'Scott James Remnant', 'Scott James', 'Remnant', NULL, NULL, NULL, 'keybuk', NULL, '''jame'':3B,6C ''scott'':2B,5C ''keybuk'':1A ''remnant'':4B,7C', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.608802', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (6, 'Jeff Waugh', 'Jeff', 'Waugh', NULL, NULL, NULL, 'jdub', NULL, '''jdub'':1A ''jeff'':2B,4C ''waugh'':3B,5C', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.600523', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (7, 'Andrew Bennetts', 'Andrew', 'Bennetts', NULL, NULL, NULL, 'spiv', NULL, '''spiv'':1A ''andrew'':2B,4C ''bennett'':3B,5C', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.551196', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (8, 'James Blackwell', 'James', 'Blackwell', NULL, NULL, NULL, 'jblack', NULL, '''jame'':2B,4C ''jblack'':1A ''blackwel'':3B,5C', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.601584', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (9, 'Christian Reis', 'Christian', 'Reis', NULL, NULL, NULL, 'kiko', NULL, '''rei'':3B,5C ''kiko'':1A ''christian'':2B,4C', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.594941', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (10, 'Alexander Limi', 'Alexander', 'Limi', NULL, NULL, NULL, 'limi', NULL, '''limi'':1A,3B,5C ''alexand'':2B,4C', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.619713', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (11, 'Steve Alexander', 'Steve', 'Alexander', NULL, NULL, NULL, 'stevea', NULL, '''steve'':2B,4C ''stevea'':1A ''alexand'':3B,5C', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.599234', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (12, 'Sample Person', 'Sample', 'Person', 'K7Qmeansl6RbuPfulfcmyDQOzp70OxVh5Fcf', NULL, NULL, 'name12', NULL, '''sampl'':2B,4C ''name12'':1A ''person'':3B,5C', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.612277', 1, 'Australia/Perth');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (13, 'Carlos Perelló Marín', 'Carlos', 'Perelló Marín', 'MdB+BoAdbza3BA6mIkMm6bFo1kv9hR2PKZ3U', NULL, NULL, 'carlos', NULL, '''carlo'':1A,2B,5C ''marín'':4B,7C ''perelló'':3B,6C', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.615543', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (14, 'Dafydd Harries', 'Dafydd', 'Harries', 'EvSuSe4k4tkRHSp6p+g91vyQIwL5VJ3iTbRZ', NULL, NULL, 'daf', NULL, '''daf'':1A ''harri'':3B,5C ''dafydd'':2B,4C', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.616666', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (16, 'Foo Bar', 'Foo', 'Bar', 'K7Qmeansl6RbuPfulfcmyDQOzp70OxVh5Fcf', NULL, NULL, 'name16', NULL, '''bar'':3B,5C ''foo'':2B,4C ''name16'':1A', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.593849', 2, 'Africa/Johannesburg');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (17, 'Ubuntu Team', NULL, NULL, NULL, 1, 'This Team is responsible for the Ubuntu Distribution', 'name17', NULL, '''team'':3B ''name17'':1A ''ubuntu'':2B', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.60576', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (18, 'Ubuntu Gnome Team', NULL, NULL, NULL, 1, 'This Team is responsible for the GNOME releases Issues on whole Ubuntu Distribution', 'name18', NULL, '''team'':4B ''gnome'':3B ''name18'':1A ''ubuntu'':2B', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.607744', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (19, 'Warty Gnome Team', NULL, NULL, NULL, 1, 'This Team is responsible for GNOME release Issues on Warty Distribution Release', 'name19', NULL, '''team'':4B ''gnome'':3B ''warti'':2B ''name19'':1A', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.602661', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (20, 'Warty Security Team', NULL, NULL, NULL, 1, 'This Team is responsible for Security Issues on Warty Distribution Release', 'name20', NULL, '''team'':4B ''secur'':3B ''warti'':2B ''name20'':1A', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.614468', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (21, 'Hoary Gnome Team', NULL, NULL, NULL, 1, 'This team is responsible for Security Issues on Hoary Distribution Release', 'name21', NULL, '''team'':4B ''gnome'':3B ''hoari'':2B ''name21'':1A', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.603691', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (22, 'Stuart Bishop', 'Stuart', 'Bishop', 'I+lQozEFEr+uBuxQZuKGpL4jkiy6lE1dQsZx', NULL, NULL, 'stub', NULL, '''stub'':1A ''bishop'':3B,5C ''stuart'':2B,4C', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.59276', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (23, 'David Allouche', 'David', 'Allouche', NULL, NULL, NULL, 'ddaa', NULL, '''ddaa'':1A ''david'':2B,4C ''allouch'':3B,5C', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.620823', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (24, 'Buttress Source Administrators', NULL, NULL, NULL, 2, 'Ultimate control of the Buttress systems', 'buttsource', NULL, '''sourc'':3B ''buttress'':2B ''administr'':4B ''buttsourc'':1A', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.604746', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (25, 'Launchpad Administrators', NULL, NULL, NULL, 1, 'Launchpad Administrators', 'admins', NULL, '''admin'':1A ''administr'':3B ''launchpad'':2B', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.571899', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (26, 'Daniel Silverstone', 'Daniel', 'Silverstone', NULL, NULL, NULL, 'kinnison', NULL, '''daniel'':2B,4C ''kinnison'':1A ''silverston'':3B,5C', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.618722', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (27, 'Daniel Henrique Debonzi', 'Daniel', 'Henrique', 'DAJs/l1RrrYFPPd2mBY4b/aFjnTfodXOyg+L+U6uPxUy8rCp/IFC/w==', NULL, NULL, 'debonzi', NULL, '''daniel'':2B,5C ''debonzi'':1A,4B ''henriqu'':3B,6C', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.557224', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (28, 'Celso Providelo', 'Celso', 'Providelo', 'DAJs/l1RrrYFPPd2mBY4b/aFjnTfodXOyg+L+U6uPxUy8rCp/IFC/w==', NULL, NULL, 'cprov', NULL, '''celso'':2B,4C ''cprov'':1A ''providelo'':3B,5C', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.59705', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (29, 'Guilherme Salgado', 'Guilherme', 'Salgado', 'DAJs/l1RrrYFPPd2mBY4b/aFjnTfodXOyg+L+U6uPxUy8rCp/IFC/w==', NULL, NULL, 'salgado', NULL, '''salgado'':1A,3B,5C ''guilherm'':2B,4C', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.596025', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (30, 'Rosetta Administrators', NULL, NULL, NULL, 25, 'Rosetta Administrators', 'rosetta-admins', NULL, '''admin'':3A ''rosetta'':2A,4B ''administr'':5B ''rosetta-admin'':1A', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.613368', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (31, 'Ubuntu Translators', NULL, NULL, NULL, 30, 'Ubuntu Translators', 'ubuntu-translators', NULL, '''ubuntu'':2A,4B ''translat'':3A,5B ''ubuntu-transl'':1A', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.617651', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (32, 'GuadaMen', NULL, NULL, NULL, 16, 'The guadalinex maintainers team', 'guadamen', NULL, '''guadamen'':1A,2B', 700, 300, 1, NULL, '2005-06-06 08:59:51.606755', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (33, 'Edgar Bursic', 'Edgar', 'Bursic', '3JiiJZWCSnGbu71a+Qw1Dik7QAsrS4soxQTy1qzErmIA4F7zfmca8Q==', NULL, NULL, 'edgar', NULL, '''edgar'':1A,2B,4C ''bursic'':3B,5C', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.621892', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (34, 'Jordi Vilalta', 'Jordi', 'Vilalta', 'gsTz0TyTUL7xrkoAH4Yz2WE6/w6WoYG5LjaO8p/xA1FDdSM6qkWiYA==', NULL, NULL, 'jvprat', NULL, '''jordi'':2B,4C ''jvprat'':1A ''vilalta'':3B,5C', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.622908', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (35, 'Sigurd Gartmann', 'Sigurd', 'Gartmann', 'FvPq9d4L5onnmcRA9wCzQ5lnPPYIzvW5rJA7GGnnsJuQqz8M8naZkQ==', NULL, NULL, 'sigurd-ubuntu', NULL, '''sigurd'':2A,4B,6C ''ubuntu'':3A ''gartmann'':5B,7C ''sigurd-ubuntu'':1A', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.623962', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (36, 'Vlastimil Skacel', 'Vlastimil', 'Skacel', 'lyA9CgUH9lHmTiaiWGP2vzkmytufiHBAnc9c8WCX1g5pYyBd6QgL3A==', NULL, NULL, 'skacel', NULL, '''skacel'':1A,3B,5C ''vlastimil'':2B,4C', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.5244', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (37, 'Daniel Aguayo', 'Daniel', 'Aguayo', 'bpLapC1tQHUedQBP447krtcmaRPd3hrncPusTlNUKXh5ymfO5yVhhQ==', NULL, NULL, 'danner', NULL, '''aguayo'':3B,5C ''daniel'':2B,4C ''danner'':1A', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.549651', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (38, 'Martin Pitt', 'Martin', 'Pitt', 'iNbxn63pi1VFuZ0byz76vhFtdMXQAj2L+Cn/1UpsbmOhjUZs+Z6Naw==', NULL, NULL, 'martin-pitt', NULL, '''pitt'':3A,5B,7C ''martin'':2A,4B,6C ''martin-pitt'':1A', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.555051', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (39, 'Nicolas Velin', 'Nicolas', 'Velin', 'U2QzusrIFlQZKb3hWzcLpfhFcB3WZ0fa0E+OwcV8q/WOtsQCjarzzA==', NULL, NULL, 'nsv', NULL, '''nsv'':1A ''velin'':3B,5C ''nicola'':2B,4C', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.556132', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (40, 'Francesco Accattapà', 'Francesco', 'Accattapà', 'mSKDc1EKoi8a5L0zd+oueU33nuSEuFWy+JHIHxOukBVJt9LPW47RVg==', NULL, NULL, 'callipeo', NULL, '''callipeo'':1A ''francesco'':2B,4C ''accattapà'':3B,5C', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.558429', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (41, 'Aloriel', 'Aloriel', '', '94y1dy33Evut2/bLsGG8Pzguyuip9wHeRtFWp0cSItzHdD1tK3gmcQ==', NULL, NULL, 'jorge-gonzalez-gonzalez', NULL, '''jorg'':2A ''aloriel'':5B,6C ''gonzalez'':3A,4A ''jorge-gonzalez-gonzalez'':1A', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.559519', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (42, 'Denis Barbier', 'Denis', 'Barbier', 'vI/vIVB2qsx1NvuaMy+q4l8rWUNMFINWzCSLOK1D5qi97/VmXvIrEw==', NULL, NULL, 'barbier', NULL, '''deni'':2B,4C ''barbier'':1A,3B,5C', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.560604', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (43, 'André Luís Lopes', 'André', 'Luís Lopes', 'HG6qWB8PwzfIr3z+Tu+m3lQv7r1dsaWY6rxCxRuNypGomTPTzBh9iA==', NULL, NULL, 'andrelop', NULL, '''lope'':4B,7C ''luís'':3B,6C ''andré'':2B,5C ''andrelop'':1A', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.561685', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (44, 'Carlos Valdivia Yagüe', 'Carlos', 'Valdivia Yagüe', 'xrXafuC+VBaIz3m2+0UMjxms+2KhGhj6qnQdoo2V/f4iNFHJgSDzzw==', NULL, NULL, 'valyag', NULL, '''carlo'':2B,5C ''valyag'':1A ''yagüe'':4B,7C ''valdivia'':3B,6C', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.562857', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (45, 'Luk Claes', 'Luk', 'Claes', 'w+f2krWWyQIIm76PIUEIsMCNQLhWLjObLcDONJNjjXcRaiKzKXeMAw==', NULL, NULL, 'luk-claes', NULL, '''luk'':2A,4B,6C ''clae'':3A,5B,7C ''luk-cla'':1A', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.563952', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (46, 'Miroslav Kure', 'Miroslav', 'Kure', '1u05okOZJIa069F8COZ2vmxRq11c+4rolNUVRp539TI5ihnHwk9+Sw==', NULL, NULL, 'kurem', NULL, '''kure'':3B,5C ''kurem'':1A ''miroslav'':2B,4C', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.565033', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (47, 'Morten Brix Pedersen', 'Morten', 'Brix Pedersen', 'n+KIa3PoihBN8ljj9Hjg9H3Im2LWnrn2yprgY4u/MnxOQx3dOh3bDw==', NULL, NULL, 'morten', NULL, '''brix'':3B,6C ''morten'':1A,2B,5C ''pedersen'':4B,7C', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.56614', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (48, 'Matti Pöllä', 'Matti', 'Pöllä', 'U4KMnp73AYdriB7QH2NpEYhlH+fBWJKziDPcDAt25OxItZMYh0QV4Q==', NULL, NULL, 'mpo', NULL, '''mpo'':1A ''matti'':2B,4C ''pöllä'':3B,5C', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.567224', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (49, 'Kęstutis Biliūnas', 'Kęstutis', 'Biliūnas', 'YbUJ4nzlxjYtaLLFMqUFL3LplUpS3FxcYwiCAS0WaAcnXS8Sst9BgA==', NULL, NULL, 'kebil', NULL, '''kebil'':1A ''biliūnas'':3B,5C ''kęstutis'':2B,4C', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.568323', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (50, 'Valentina Commissari', 'Valentina', 'Commissari', 'fgwbt51c6ajsTet6DTbQBqAzQ7Q9S1G7S0APNvMX7YN2qpdbNbEn3Q==', NULL, NULL, 'tsukimi', NULL, '''tsukimi'':1A ''valentina'':2B,4C ''commissari'':3B,5C', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.569518', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (51, 'Helge Kreutzmann', 'Helge', 'Kreutzmann', 'sYVFKi2dWAfkFkWekcW296s2dZ0ihYcxAXtwumI1FQJes4PWD8xvqQ==', NULL, NULL, 'kreutzm', NULL, '''helg'':2B,4C ''kreutzm'':1A ''kreutzmann'':3B,5C', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.570701', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (52, 'No Privileges Person', 'No', 'Privileges', 'K7Qmeansl6RbuPfulfcmyDQOzp70OxVh5Fcf', NULL, NULL, 'no-priv', NULL, '''priv'':3A ''person'':6B ''no-priv'':1A ''privileg'':5B,7C', NULL, NULL, 1, NULL, '2005-06-06 08:59:51.593849', NULL, 'UTC');
INSERT INTO person (id, displayname, givenname, familyname, "password", teamowner, teamdescription, name, "language", fti, defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, datecreated, calendar, timezone) VALUES (53, 'testing Spanish team', NULL, NULL, NULL, 13, NULL, 'testing-spanish-team', NULL, '''team'':4A,7B ''test'':2A,5B ''spanish'':3A,6B ''testing-spanish-team'':1A', NULL, NULL, 1, NULL, '2005-07-12 14:32:01.84779', NULL, 'UTC');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'person'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'emailaddress'::pg_catalog.regclass;

INSERT INTO emailaddress (id, email, person, status) VALUES (1, 'mark@hbd.com', 1, 4);
INSERT INTO emailaddress (id, email, person, status) VALUES (2, 'robertc@robertcollins.net', 2, 4);
INSERT INTO emailaddress (id, email, person, status) VALUES (3, 'carlos@canonical.com', 13, 4);
INSERT INTO emailaddress (id, email, person, status) VALUES (4, 'daf@canonical.com', 14, 4);
INSERT INTO emailaddress (id, email, person, status) VALUES (6, 'foo.bar@canonical.com', 16, 4);
INSERT INTO emailaddress (id, email, person, status) VALUES (7, 'steve.alexander@ubuntulinux.com', 11, 1);
INSERT INTO emailaddress (id, email, person, status) VALUES (8, 'colin.watson@ubuntulinux.com', 4, 1);
INSERT INTO emailaddress (id, email, person, status) VALUES (9, 'scott.james.remnant@ubuntulinux.com', 5, 1);
INSERT INTO emailaddress (id, email, person, status) VALUES (10, 'andrew.bennetts@ubuntulinux.com', 7, 1);
INSERT INTO emailaddress (id, email, person, status) VALUES (11, 'james.blackwell@ubuntulinux.com', 8, 1);
INSERT INTO emailaddress (id, email, person, status) VALUES (12, 'christian.reis@ubuntulinux.com', 9, 1);
INSERT INTO emailaddress (id, email, person, status) VALUES (13, 'jeff.waugh@ubuntulinux.com', 6, 1);
INSERT INTO emailaddress (id, email, person, status) VALUES (14, 'dave.miller@ubuntulinux.com', 3, 1);
INSERT INTO emailaddress (id, email, person, status) VALUES (15, 'justdave@bugzilla.org', 3, 1);
INSERT INTO emailaddress (id, email, person, status) VALUES (16, 'test@canonical.com', 12, 4);
INSERT INTO emailaddress (id, email, person, status) VALUES (17, 'testtest@canonical.com', 12, 1);
INSERT INTO emailaddress (id, email, person, status) VALUES (18, 'testtesttest@canonical.com', 12, 3);
INSERT INTO emailaddress (id, email, person, status) VALUES (19, 'testing@canonical.com', 12, 2);
INSERT INTO emailaddress (id, email, person, status) VALUES (20, 'stuart.bishop@canonical.com', 22, 4);
INSERT INTO emailaddress (id, email, person, status) VALUES (21, 'david.allouche@canonical.com', 23, 4);
INSERT INTO emailaddress (id, email, person, status) VALUES (22, 'david@canonical.com', 23, 2);
INSERT INTO emailaddress (id, email, person, status) VALUES (23, 'daniel.debonzi@canonical.com', 27, 4);
INSERT INTO emailaddress (id, email, person, status) VALUES (24, 'celso.providelo@canonical.com', 28, 4);
INSERT INTO emailaddress (id, email, person, status) VALUES (25, 'guilherme.salgado@canonical.com', 29, 1);
INSERT INTO emailaddress (id, email, person, status) VALUES (26, 'edgar@monteparadiso.hr', 33, 1);
INSERT INTO emailaddress (id, email, person, status) VALUES (27, 'jvprat@wanadoo.es', 34, 1);
INSERT INTO emailaddress (id, email, person, status) VALUES (28, 'sigurd-ubuntu@brogar.org', 35, 1);
INSERT INTO emailaddress (id, email, person, status) VALUES (29, 'skacel@svtech.cz', 36, 1);
INSERT INTO emailaddress (id, email, person, status) VALUES (30, 'danner@mixmail.com', 37, 1);
INSERT INTO emailaddress (id, email, person, status) VALUES (31, 'martin.pitt@canonical.com', 38, 1);
INSERT INTO emailaddress (id, email, person, status) VALUES (32, 'nsv@fr.st', 39, 1);
INSERT INTO emailaddress (id, email, person, status) VALUES (33, 'callipeo@libero.it', 40, 1);
INSERT INTO emailaddress (id, email, person, status) VALUES (34, 'jorge.gonzalez.gonzalez@hispalinux.es', 41, 1);
INSERT INTO emailaddress (id, email, person, status) VALUES (35, 'barbier@linuxfr.org', 42, 1);
INSERT INTO emailaddress (id, email, person, status) VALUES (36, 'andrelop@debian.org', 43, 1);
INSERT INTO emailaddress (id, email, person, status) VALUES (37, 'valyag@dat.etsit.upm.es', 44, 1);
INSERT INTO emailaddress (id, email, person, status) VALUES (38, 'luk.claes@ugent.be', 45, 1);
INSERT INTO emailaddress (id, email, person, status) VALUES (39, 'kurem@debian.cz', 46, 4);
INSERT INTO emailaddress (id, email, person, status) VALUES (40, 'morten@wtf.dk', 47, 1);
INSERT INTO emailaddress (id, email, person, status) VALUES (41, 'mpo@iki.fi', 48, 1);
INSERT INTO emailaddress (id, email, person, status) VALUES (42, 'kebil@kaunas.init.lt', 49, 1);
INSERT INTO emailaddress (id, email, person, status) VALUES (43, 'tsukimi@quaqua.net', 50, 4);
INSERT INTO emailaddress (id, email, person, status) VALUES (44, 'kreutzm@itp.uni-hannover.de', 51, 1);
INSERT INTO emailaddress (id, email, person, status) VALUES (45, 'support@ubuntu.com', 17, 4);
INSERT INTO emailaddress (id, email, person, status) VALUES (46, 'no-priv@canonical.com', 52, 4);
INSERT INTO emailaddress (id, email, person, status) VALUES (47, 'stuart@stuartbishop.net', 22, 2);
INSERT INTO emailaddress (id, email, person, status) VALUES (48, 'zen@shangri-la.dropbear.id.au', 22, 3);
INSERT INTO emailaddress (id, email, person, status) VALUES (49, 'stub@fastmail.fm', 22, 1);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'emailaddress'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'gpgkey'::pg_catalog.regclass;



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
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (11, 2, 'http://www.ubuntulinux.com/wiki/', 'RobertCollins');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (12, 12, 'http://www.ubuntulinux.com/wiki/', 'SamplePerson');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (13, 13, 'http://www.ubuntulinux.com/wiki/', 'CarlosPerellóMarín');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (14, 14, 'http://www.ubuntulinux.com/wiki/', 'DafyddHarries');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (15, 16, 'http://www.ubuntulinux.com/wiki/', 'FooBar');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (16, 17, 'http://www.ubuntulinux.com/wiki/', 'UbuntuTeam');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (17, 18, 'http://www.ubuntulinux.com/wiki/', 'UbuntuGnomeTeam');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (18, 19, 'http://www.ubuntulinux.com/wiki/', 'WartyGnomeTeam');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (19, 20, 'http://www.ubuntulinux.com/wiki/', 'WartySecurityTeam');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (20, 21, 'http://www.ubuntulinux.com/wiki/', 'HoaryGnomeTeam');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (21, 22, 'http://www.ubuntulinux.com/wiki/', 'StuartBishop');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (22, 23, 'http://www.ubuntulinux.com/wiki/', 'DavidAllouche');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (23, 24, 'http://www.ubuntulinux.com/wiki/', 'ButtressSourceAdministrators');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (24, 25, 'http://www.ubuntulinux.com/wiki/', 'LaunchpadAdministrators');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (25, 26, 'http://www.ubuntulinux.com/wiki/', 'DanielSilverstone');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (26, 27, 'http://www.ubuntulinux.com/wiki/', 'DanielHenriqueDebonzi');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (27, 28, 'http://www.ubuntulinux.com/wiki/', 'CelsoProvidelo');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (28, 29, 'http://www.ubuntulinux.com/wiki/', 'GuilhermeSalgado');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (29, 30, 'http://www.ubuntulinux.com/wiki/', 'RosettaAdministrators');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (30, 31, 'http://www.ubuntulinux.com/wiki/', 'UbuntuTranslators');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (31, 32, 'http://www.ubuntulinux.com/wiki/', 'Guadamen');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (32, 33, 'http://www.ubuntulinux.com/wiki/', 'EdgarBursic');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (33, 34, 'http://www.ubuntulinux.com/wiki/', 'JordiVilalta');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (34, 35, 'http://www.ubuntulinux.com/wiki/', 'SigurdGartmann');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (35, 36, 'http://www.ubuntulinux.com/wiki/', 'VlastimilSkacel');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (36, 37, 'http://www.ubuntulinux.com/wiki/', 'DanielAguayo');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (37, 38, 'http://www.ubuntulinux.com/wiki/', 'MartinPitt');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (38, 39, 'http://www.ubuntulinux.com/wiki/', 'NicolasVelin');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (39, 40, 'http://www.ubuntulinux.com/wiki/', 'FrancescoAccattapà');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (40, 41, 'http://www.ubuntulinux.com/wiki/', 'Aloriel');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (41, 42, 'http://www.ubuntulinux.com/wiki/', 'DenisBarbier');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (42, 43, 'http://www.ubuntulinux.com/wiki/', 'AndréLuísLopes');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (43, 44, 'http://www.ubuntulinux.com/wiki/', 'CarlosValdiviaYagüe');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (44, 45, 'http://www.ubuntulinux.com/wiki/', 'LukClaes');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (45, 46, 'http://www.ubuntulinux.com/wiki/', 'MiroslavKure');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (46, 47, 'http://www.ubuntulinux.com/wiki/', 'MortenBrixPedersen');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (47, 48, 'http://www.ubuntulinux.com/wiki/', 'MattiPöllä');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (48, 49, 'http://www.ubuntulinux.com/wiki/', 'KęstutisBiliūnas');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (49, 50, 'http://www.ubuntulinux.com/wiki/', 'ValentinaCommissari');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (50, 51, 'http://www.ubuntulinux.com/wiki/', 'HelgeKreutzmann');
INSERT INTO wikiname (id, person, wiki, wikiname) VALUES (51, 52, 'http://www.ubuntulinux.com/wiki/', 'NoPrivilegesPerson');


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


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'teammembership'::pg_catalog.regclass;

INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (1, 1, 17, 3, '2005-03-03 10:02:53.830191', NULL, NULL, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (2, 11, 17, 2, '2005-03-03 10:02:53.831231', NULL, NULL, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (3, 10, 17, 3, '2005-03-03 10:02:53.831725', NULL, NULL, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (4, 4, 17, 3, '2005-03-03 10:02:53.832216', NULL, NULL, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (5, 7, 17, 1, '2005-03-03 10:02:53.832809', NULL, NULL, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (6, 3, 17, 6, '2005-03-03 10:02:53.833299', NULL, NULL, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (7, 1, 18, 5, '2005-03-03 10:02:53.833759', '2005-03-13 10:02:53.833759', NULL, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (8, 6, 18, 5, '2005-03-03 10:02:53.834248', '2005-03-13 10:02:53.833759', NULL, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (9, 20, 17, 1, '2005-03-03 10:02:53.834789', NULL, NULL, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (10, 11, 18, 3, '2005-03-03 10:02:53.835303', NULL, NULL, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (11, 10, 18, 2, '2005-03-03 10:02:53.835792', NULL, NULL, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (12, 4, 18, 5, '2005-03-03 10:02:53.836299', '2005-03-13 10:02:53.833759', NULL, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (13, 7, 18, 2, '2005-03-03 10:02:53.8368', NULL, NULL, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (14, 3, 18, 1, '2005-03-03 10:02:53.837284', NULL, NULL, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (15, 20, 18, 4, '2005-03-03 10:02:53.837789', NULL, NULL, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (16, 6, 17, 3, '2005-03-03 10:02:53.838301', NULL, NULL, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (17, 16, 17, 3, '2005-03-03 10:02:53.838806', NULL, NULL, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (18, 16, 18, 3, '2005-03-03 10:02:53.839322', NULL, NULL, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (19, 23, 24, 3, '2005-03-03 10:02:53.839822', NULL, NULL, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (20, 2, 24, 3, '2005-03-03 10:02:53.840339', NULL, NULL, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (21, 28, 25, 2, '2005-03-03 10:02:53.840813', NULL, NULL, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (22, 22, 25, 2, '2005-03-03 10:02:53.841292', NULL, NULL, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (23, 2, 25, 2, '2005-03-03 10:02:53.841836', NULL, NULL, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (24, 11, 25, 2, '2005-03-03 10:02:53.842335', NULL, NULL, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (25, 23, 25, 2, '2005-03-03 10:02:53.842821', NULL, NULL, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (26, 7, 25, 2, '2005-03-03 10:02:53.843319', NULL, NULL, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (27, 8, 25, 2, '2005-03-03 10:02:53.843811', NULL, NULL, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (28, 14, 25, 2, '2005-03-03 10:02:53.844315', NULL, NULL, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (29, 13, 25, 2, '2005-03-03 10:02:53.844834', NULL, NULL, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (30, 26, 25, 2, '2005-03-03 10:02:53.84533', NULL, NULL, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (31, 27, 25, 2, '2005-03-03 10:02:53.845844', NULL, NULL, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (32, 16, 25, 3, '2005-03-03 10:02:53.846352', NULL, NULL, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (33, 29, 25, 3, '2005-03-03 10:02:53.846864', NULL, NULL, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (34, 14, 30, 3, '2005-03-07 13:05:57.590333', NULL, NULL, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (35, 13, 30, 3, '2005-03-07 13:05:57.610314', NULL, NULL, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (36, 16, 24, 2, '2005-04-14 00:00:00', NULL, 16, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (37, 13, 31, 2, '2005-05-07 00:00:00', NULL, 13, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (38, 1, 25, 3, '2005-03-03 10:02:53.830191', NULL, NULL, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (39, 17, 32, 3, '2005-03-03 10:02:53.830191', NULL, NULL, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (40, 13, 53, 3, '2005-07-12 14:32:01.84779', NULL, NULL, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (41, 1, 53, 2, '2005-07-12 14:32:14.20688', NULL, 13, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (42, 50, 53, 2, '2005-07-12 14:34:36.906758', NULL, 13, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (43, 46, 53, 2, '2005-07-12 14:35:44.635842', NULL, 13, NULL);
INSERT INTO teammembership (id, person, team, status, datejoined, dateexpires, reviewer, reviewercomment) VALUES (44, 16, 53, 2, '2005-07-12 14:36:09.587753', NULL, 13, NULL);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'teammembership'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'teamparticipation'::pg_catalog.regclass;

INSERT INTO teamparticipation (id, team, person) VALUES (1, 17, 1);
INSERT INTO teamparticipation (id, team, person) VALUES (2, 17, 11);
INSERT INTO teamparticipation (id, team, person) VALUES (3, 17, 10);
INSERT INTO teamparticipation (id, team, person) VALUES (4, 17, 4);
INSERT INTO teamparticipation (id, team, person) VALUES (5, 18, 11);
INSERT INTO teamparticipation (id, team, person) VALUES (6, 18, 10);
INSERT INTO teamparticipation (id, team, person) VALUES (7, 18, 7);
INSERT INTO teamparticipation (id, team, person) VALUES (8, 17, 6);
INSERT INTO teamparticipation (id, team, person) VALUES (9, 17, 16);
INSERT INTO teamparticipation (id, team, person) VALUES (10, 18, 16);
INSERT INTO teamparticipation (id, team, person) VALUES (11, 24, 23);
INSERT INTO teamparticipation (id, team, person) VALUES (12, 24, 2);
INSERT INTO teamparticipation (id, team, person) VALUES (13, 25, 28);
INSERT INTO teamparticipation (id, team, person) VALUES (14, 25, 22);
INSERT INTO teamparticipation (id, team, person) VALUES (15, 25, 2);
INSERT INTO teamparticipation (id, team, person) VALUES (16, 25, 11);
INSERT INTO teamparticipation (id, team, person) VALUES (17, 25, 23);
INSERT INTO teamparticipation (id, team, person) VALUES (18, 25, 7);
INSERT INTO teamparticipation (id, team, person) VALUES (19, 25, 8);
INSERT INTO teamparticipation (id, team, person) VALUES (20, 25, 14);
INSERT INTO teamparticipation (id, team, person) VALUES (21, 25, 13);
INSERT INTO teamparticipation (id, team, person) VALUES (22, 25, 26);
INSERT INTO teamparticipation (id, team, person) VALUES (23, 25, 27);
INSERT INTO teamparticipation (id, team, person) VALUES (24, 25, 16);
INSERT INTO teamparticipation (id, team, person) VALUES (25, 25, 29);
INSERT INTO teamparticipation (id, team, person) VALUES (26, 30, 14);
INSERT INTO teamparticipation (id, team, person) VALUES (27, 30, 13);
INSERT INTO teamparticipation (id, team, person) VALUES (28, 2, 2);
INSERT INTO teamparticipation (id, team, person) VALUES (29, 5, 5);
INSERT INTO teamparticipation (id, team, person) VALUES (30, 26, 26);
INSERT INTO teamparticipation (id, team, person) VALUES (31, 27, 27);
INSERT INTO teamparticipation (id, team, person) VALUES (32, 29, 29);
INSERT INTO teamparticipation (id, team, person) VALUES (33, 3, 3);
INSERT INTO teamparticipation (id, team, person) VALUES (34, 8, 8);
INSERT INTO teamparticipation (id, team, person) VALUES (35, 10, 10);
INSERT INTO teamparticipation (id, team, person) VALUES (36, 13, 13);
INSERT INTO teamparticipation (id, team, person) VALUES (37, 14, 14);
INSERT INTO teamparticipation (id, team, person) VALUES (38, 23, 23);
INSERT INTO teamparticipation (id, team, person) VALUES (39, 9, 9);
INSERT INTO teamparticipation (id, team, person) VALUES (40, 1, 1);
INSERT INTO teamparticipation (id, team, person) VALUES (42, 22, 22);
INSERT INTO teamparticipation (id, team, person) VALUES (43, 16, 16);
INSERT INTO teamparticipation (id, team, person) VALUES (44, 28, 28);
INSERT INTO teamparticipation (id, team, person) VALUES (45, 7, 7);
INSERT INTO teamparticipation (id, team, person) VALUES (46, 6, 6);
INSERT INTO teamparticipation (id, team, person) VALUES (47, 11, 11);
INSERT INTO teamparticipation (id, team, person) VALUES (48, 4, 4);
INSERT INTO teamparticipation (id, team, person) VALUES (49, 12, 12);
INSERT INTO teamparticipation (id, team, person) VALUES (58, 24, 16);
INSERT INTO teamparticipation (id, team, person) VALUES (59, 32, 16);
INSERT INTO teamparticipation (id, team, person) VALUES (60, 33, 33);
INSERT INTO teamparticipation (id, team, person) VALUES (61, 34, 34);
INSERT INTO teamparticipation (id, team, person) VALUES (62, 35, 35);
INSERT INTO teamparticipation (id, team, person) VALUES (63, 36, 36);
INSERT INTO teamparticipation (id, team, person) VALUES (64, 37, 37);
INSERT INTO teamparticipation (id, team, person) VALUES (65, 38, 38);
INSERT INTO teamparticipation (id, team, person) VALUES (66, 39, 39);
INSERT INTO teamparticipation (id, team, person) VALUES (67, 40, 40);
INSERT INTO teamparticipation (id, team, person) VALUES (68, 41, 41);
INSERT INTO teamparticipation (id, team, person) VALUES (69, 42, 42);
INSERT INTO teamparticipation (id, team, person) VALUES (70, 43, 43);
INSERT INTO teamparticipation (id, team, person) VALUES (71, 44, 44);
INSERT INTO teamparticipation (id, team, person) VALUES (72, 45, 45);
INSERT INTO teamparticipation (id, team, person) VALUES (73, 46, 46);
INSERT INTO teamparticipation (id, team, person) VALUES (74, 47, 47);
INSERT INTO teamparticipation (id, team, person) VALUES (75, 48, 48);
INSERT INTO teamparticipation (id, team, person) VALUES (76, 49, 49);
INSERT INTO teamparticipation (id, team, person) VALUES (77, 50, 50);
INSERT INTO teamparticipation (id, team, person) VALUES (78, 51, 51);
INSERT INTO teamparticipation (id, team, person) VALUES (79, 31, 13);
INSERT INTO teamparticipation (id, team, person) VALUES (80, 25, 1);
INSERT INTO teamparticipation (id, team, person) VALUES (81, 32, 17);
INSERT INTO teamparticipation (id, team, person) VALUES (82, 53, 13);
INSERT INTO teamparticipation (id, team, person) VALUES (83, 53, 1);
INSERT INTO teamparticipation (id, team, person) VALUES (84, 53, 50);
INSERT INTO teamparticipation (id, team, person) VALUES (85, 53, 46);
INSERT INTO teamparticipation (id, team, person) VALUES (86, 53, 16);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'teamparticipation'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = '"schema"'::pg_catalog.regclass;

INSERT INTO "schema" (id, name, title, description, "owner", extensible) VALUES (1, 'mark', 'TITLE', 'description', 1, true);
INSERT INTO "schema" (id, name, title, description, "owner", extensible) VALUES (2, 'schema', 'SCHEMA', 'description', 1, true);
INSERT INTO "schema" (id, name, title, description, "owner", extensible) VALUES (3, 'trema', 'XCHEMA', 'description', 1, true);
INSERT INTO "schema" (id, name, title, description, "owner", extensible) VALUES (4, 'enema', 'ENHEMA', 'description', 1, true);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = '"schema"'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'label'::pg_catalog.regclass;

INSERT INTO label (id, "schema", name, title, description) VALUES (1, 1, 'blah', 'blah', 'blah');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'label'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'personlabel'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'personlabel'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'project'::pg_catalog.regclass;

INSERT INTO project (id, "owner", name, displayname, title, summary, description, datecreated, homepageurl, wikiurl, lastdoap, sourceforgeproject, freshmeatproject, reviewed, active, fti, translationgroup, translationpermission, calendar) VALUES (1, 1, 'ubuntu', 'the Ubuntu Project', 'The Ubuntu Project', 'A community Linux distribution building a slick desktop for the global market. Ubuntu is absolutely free and will stay that way, contains no proprietary application software, always ships with the latest Gnome desktop software and Python integration.', 'The Ubuntu Project aims to create a freely redistributable OS that is easy to customize and derive from. Ubuntu is released every six months with contributions from a large community, especially the Gnome Project. While the full range of KDE and other desktop environments are available, Ubuntu''s Gnome desktop receives most of the polish and support work done for each release.

Ubuntu also includes work to unify the translation of common open source desktop applications and the tracking of bugs across multiple distributions.', '2004-09-24 20:58:00.633513', 'http://www.ubuntulinux.org/', NULL, NULL, NULL, NULL, false, true, '''os'':54 ''aim'':48 ''bug'':125 ''kde'':84 ''six'':67 ''way'':28C ''also'':108 ''done'':103 ''easi'':57 ''free'':23C ''full'':81 ''larg'':73 ''open'':117 ''rang'':82 ''ship'':35C ''stay'':26C ''work'':102,110 ''alway'':34C ''avail'':90 ''build'':12C ''creat'':50 ''deriv'':61 ''everi'':66 ''gnome'':39C,77,93 ''linux'':10C ''month'':68 ''slick'':14C ''sourc'':118 ''track'':123 ''unifi'':112 ''across'':126 ''applic'':32C,120 ''common'':116 ''commun'':9C,74 ''custom'':59 ''especi'':75 ''freeli'':52 ''global'':18C ''includ'':109 ''integr'':44C ''latest'':38C ''market'':19C ''polish'':99 ''python'':43C ''receiv'':95 ''releas'':65,106 ''ubuntu'':1A,3A,6B,20C,46,63,91,107 ''absolut'':22C ''contain'':29C ''desktop'':15C,40C,87,94,119 ''environ'':88 ''multipl'':127 ''project'':4A,7B,47,78 ''softwar'':33C,41C ''support'':101 ''translat'':114 ''contribut'':70 ''distribut'':11C,128 ''proprietari'':31C ''redistribut'':53', NULL, 1, 3);
INSERT INTO project (id, "owner", name, displayname, title, summary, description, datecreated, homepageurl, wikiurl, lastdoap, sourceforgeproject, freshmeatproject, reviewed, active, fti, translationgroup, translationpermission, calendar) VALUES (2, 2, 'do-not-use-info-imports', 'DO NOT USE', 'DO NOT USE', 'DO NOT USE', 'TEMPORARY project till mirror jobs are assigned to correct project', '2004-09-24 20:58:00.637677', 'http://arch.ubuntu.com/', NULL, NULL, NULL, NULL, true, false, '''job'':20 ''use'':4A,9A,12B,15C ''info'':5A ''till'':18 ''assign'':22 ''import'':6A ''mirror'':19 ''correct'':24 ''project'':17,25 ''temporari'':16 ''do-not-use-info-import'':1A', NULL, 1, NULL);
INSERT INTO project (id, "owner", name, displayname, title, summary, description, datecreated, homepageurl, wikiurl, lastdoap, sourceforgeproject, freshmeatproject, reviewed, active, fti, translationgroup, translationpermission, calendar) VALUES (3, 2, 'launchpad-mirrors', 'Launchpad SCM Mirrors', 'The Launchpad Mirroring Project', 'launchpad mirrors various revision control archives, that mirroring is managed here', 'A project to mirror revision control archives into Arch.', '2004-09-24 20:58:00.65398', 'http://arch.ubuntu.com/', NULL, NULL, NULL, NULL, false, true, '''scm'':5A ''arch'':29 ''manag'':20C ''revis'':14C,25 ''archiv'':16C,27 ''mirror'':3A,6A,9B,12C,18C,24 ''control'':15C,26 ''project'':10B,22 ''various'':13C ''launchpad'':2A,4A,8B,11C ''launchpad-mirror'':1A', NULL, 1, NULL);
INSERT INTO project (id, "owner", name, displayname, title, summary, description, datecreated, homepageurl, wikiurl, lastdoap, sourceforgeproject, freshmeatproject, reviewed, active, fti, translationgroup, translationpermission, calendar) VALUES (4, 12, 'mozilla', 'the Mozilla Project', 'The Mozilla Project', 'The Mozilla Project is the largest open source web browser collaborative project. Founded when Netscape released the source code to its pioneering browser in 1999, the Mozilla Project continues to set the standard for web browser technology.', 'The Mozilla Project produces several internet applications that are very widely used, and is also a center for collaboration on internet standards work by open source groups.

The Project now has several popular products, including the Firefox web browser, the Thunderbird mail client and the libraries that enable them to run on many platforms.

Organisationally, the Mozilla Project is hosted by the Mozilla Foundation, a not-for-profit company incorporated in the US.', '2004-09-24 20:58:02.177698', 'http://www.mozilla.org/', NULL, NULL, NULL, NULL, false, true, '''us'':118 ''run'':95 ''set'':38C ''use'':56 ''web'':16C,42C,82 ''1999'':32C ''also'':59 ''code'':26C ''host'':104 ''mail'':86 ''mani'':97 ''open'':14C,69 ''wide'':55 ''work'':67 ''enabl'':92 ''found'':20C ''group'':71 ''sever'':49,76 ''sourc'':15C,25C,70 ''applic'':51 ''center'':61 ''client'':87 ''includ'':79 ''produc'':48 ''profit'':113 ''releas'':23C ''browser'':17C,30C,43C,83 ''compani'':114 ''continu'':36C ''firefox'':81 ''foundat'':108 ''largest'':13C ''librari'':90 ''mozilla'':1A,3A,6B,9C,34C,46,101,107 ''netscap'':22C ''organis'':99 ''pioneer'':29C ''popular'':77 ''product'':78 ''project'':4A,7B,10C,19C,35C,47,73,102 ''collabor'':18C,63 ''incorpor'':115 ''internet'':50,65 ''platform'':98 ''standard'':40C,66 ''technolog'':44C ''thunderbird'':85 ''not-for-profit'':110', NULL, 1, NULL);
INSERT INTO project (id, "owner", name, displayname, title, summary, description, datecreated, homepageurl, wikiurl, lastdoap, sourceforgeproject, freshmeatproject, reviewed, active, fti, translationgroup, translationpermission, calendar) VALUES (5, 12, 'gnome', 'GNOME', 'The GNOME Project', 'The GNOME Project is an initiative to prduce a free desktop software framework. GNOME is more than a set of applications, it is a user interface standard (the Gnome HIG) and a set of libraries that allow applications to work together in a harmonious desktop-ish way.', 'The Gnome Project was founded (when?) to build on the success of early applications using the Gtk GUI toolkit. Many of those applications are still part of Gnome, and the Gtk toolkit remains an essential part of Gnome.

Gnome applications cover the full spectrum from office productivity applications to games, digital camera applications, and of course the Gnome Panel which acts as a launcher and general access point for apps on the desktop.', '2004-09-24 20:58:02.222154', 'http://www.gnome.org/', NULL, NULL, NULL, NULL, false, true, '''act'':114 ''app'':123 ''gtk'':70,84 ''gui'':71 ''hig'':35C ''ish'':52C ''set'':24C,38C ''use'':68 ''way'':53C ''free'':15C ''full'':96 ''game'':103 ''mani'':73 ''part'':79,89 ''user'':30C ''work'':45C ''allow'':42C ''build'':61 ''cours'':109 ''cover'':94 ''digit'':104 ''earli'':66 ''found'':58 ''gnome'':1A,2A,4B,7C,19C,34C,55,81,91,92,111 ''initi'':11C ''offic'':99 ''panel'':112 ''point'':121 ''still'':78 ''access'':120 ''applic'':26C,43C,67,76,93,101,106 ''camera'':105 ''prduce'':13C ''remain'':86 ''togeth'':46C ''desktop'':16C,51C,126 ''essenti'':88 ''general'':119 ''harmoni'':49C ''librari'':40C ''product'':100 ''project'':5B,8C,56 ''softwar'':17C ''success'':64 ''toolkit'':72,85 ''interfac'':31C ''launcher'':117 ''spectrum'':97 ''standard'':32C ''framework'':18C ''desktop-ish'':50C', NULL, 1, NULL);
INSERT INTO project (id, "owner", name, displayname, title, summary, description, datecreated, homepageurl, wikiurl, lastdoap, sourceforgeproject, freshmeatproject, reviewed, active, fti, translationgroup, translationpermission, calendar) VALUES (6, 12, 'iso-codes', 'iso-codes', 'iso-codes', 'foo', 'bar', '2004-09-24 20:58:02.238443', 'http://www.gnome.org/', NULL, NULL, NULL, NULL, false, true, '''bar'':11 ''foo'':10C ''iso'':2A,5A,8B ''code'':3A,6A,9B ''iso-cod'':1A,4A,7B', NULL, 1, NULL);
INSERT INTO project (id, "owner", name, displayname, title, summary, description, datecreated, homepageurl, wikiurl, lastdoap, sourceforgeproject, freshmeatproject, reviewed, active, fti, translationgroup, translationpermission, calendar) VALUES (7, 16, 'aaa', 'the Test Project', 'The Test Project', 'This is a small project that has no purpose by to serve as a test data point. The only thing this project has ever produced is products, most of which are largely unheard of. This short description is long enough.', 'Of course, one can''t say enough about the Test Project. Not only is it always there, it''s often exactly in the same state that you saw it last. And it has an amazing ability to pop up in places where you just didn''t think you''d expect to find it. Very noticeable when you least want it noticed, that sort of thing.

It would be very interesting to know whether this second paragraph of text about the test project is in fact rendered as a second paragraph, or if it all blurs together in a haze of testing. Only time will tell.', '2004-10-03 22:27:25.02843', 'http://www.testmenow.com', NULL, NULL, NULL, NULL, false, true, '''d'':96 ''aaa'':1A ''one'':50 ''pop'':85 ''saw'':75 ''say'':53 ''abil'':83 ''amaz'':82 ''blur'':142 ''data'':23C ''didn'':92 ''ever'':31C ''fact'':132 ''find'':99 ''haze'':146 ''know'':119 ''larg'':39C ''last'':77 ''long'':46C ''serv'':19C ''sort'':110 ''tell'':152 ''test'':3A,6B,22C,57,128,148 ''text'':125 ''time'':150 ''want'':106 ''alway'':63 ''cours'':49 ''exact'':68 ''least'':105 ''notic'':102,108 ''often'':67 ''place'':88 ''point'':24C ''short'':43C ''small'':11C ''state'':72 ''thing'':27C,112 ''think'':94 ''would'':114 ''enough'':47C,54 ''expect'':97 ''produc'':32C ''purpos'':16C ''render'':133 ''second'':122,136 ''togeth'':143 ''product'':34C ''project'':4A,7B,12C,29C,58,129 ''unheard'':40C ''whether'':120 ''descript'':44C ''interest'':117 ''paragraph'':123,137', NULL, 1, NULL);
INSERT INTO project (id, "owner", name, displayname, title, summary, description, datecreated, homepageurl, wikiurl, lastdoap, sourceforgeproject, freshmeatproject, reviewed, active, fti, translationgroup, translationpermission, calendar) VALUES (8, 16, 'gimp', 'the GiMP Project', 'The GIMP Project', 'The GIMP Project works in the field of image manipulation and reproduction. The Project is responsible for several pieces of software, such as The GiMP and GiMP-Print.', 'Founded by Spencer Kimball in 1996 with the simple aim of producing a "paint" program, the GIMP project has become one of the defining projects of the open source world. The GIMP itself is an image manipulation program that is beginning to rival even Adobe Photoshop in features and functionality.

The project is loosely organised, with about 15 people making regular contributions. There is no fixed release schedule other than "when it is done".', '2004-10-03 22:27:45.283741', 'http://www.gimp.org/', NULL, NULL, NULL, NULL, false, true, '''15'':94 ''aim'':46 ''fix'':102 ''one'':57 ''1996'':42 ''adob'':81 ''done'':110 ''even'':80 ''gimp'':1A,3A,6B,9C,32C,35C,53,68 ''imag'':16C,72 ''loos'':90 ''make'':96 ''open'':64 ''piec'':26C ''work'':11C ''becom'':56 ''begin'':77 ''defin'':60 ''field'':14C ''found'':37 ''paint'':50 ''peopl'':95 ''print'':36C ''rival'':79 ''sever'':25C ''simpl'':45 ''sourc'':65 ''world'':66 ''featur'':84 ''kimbal'':40 ''produc'':48 ''releas'':103 ''manipul'':17C,73 ''organis'':91 ''program'':51,74 ''project'':4A,7B,10C,21C,54,61,88 ''regular'':97 ''respons'':23C ''schedul'':104 ''softwar'':28C ''spencer'':39 ''function'':86 ''contribut'':98 ''photoshop'':82 ''reproduct'':19C ''gimp-print'':34C', NULL, 1, NULL);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'project'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'projectrelationship'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'projectrelationship'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'product'::pg_catalog.regclass;

INSERT INTO product (id, project, "owner", name, displayname, title, summary, description, datecreated, homepageurl, screenshotsurl, wikiurl, listurl, programminglang, downloadurl, lastdoap, sourceforgeproject, freshmeatproject, reviewed, active, fti, autoupdate, translationgroup, translationpermission, releaseroot, calendar) VALUES (1, 1, 17, 'ubuntu', 'Ubuntu', 'Ubuntu', 'An easy-to-install version of Linux that has a complete set of desktop applications ready to use immediately after installation.', 'Ubuntu is a desktop Linux that you can give your girlfriend to install. Works out of the box with recent Gnome desktop applications configured to make you productive immediately. Ubuntu is updated every six months, comes with security updates for peace of mind, and is available everywhere absolutely free of charge.', '2004-09-24 20:58:00.655518', 'http://www.ubuntu.com/', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, false, true, '''box'':43 ''set'':16C ''six'':59 ''use'':22C ''come'':61 ''easi'':6C ''free'':74 ''give'':34 ''make'':51 ''mind'':68 ''peac'':66 ''work'':39 ''avail'':71 ''charg'':76 ''everi'':58 ''gnome'':46 ''linux'':11C,30 ''month'':60 ''readi'':20C ''secur'':63 ''updat'':57,64 ''applic'':19C,48 ''immedi'':23C,54 ''instal'':8C,25C,38 ''recent'':45 ''ubuntu'':1A,2A,3B,26,55 ''absolut'':73 ''complet'':15C ''desktop'':18C,29,47 ''product'':53 ''version'':9C ''configur'':49 ''everywher'':72 ''girlfriend'':36 ''easy-to-instal'':5C', false, NULL, 1, NULL, NULL);
INSERT INTO product (id, project, "owner", name, displayname, title, summary, description, datecreated, homepageurl, screenshotsurl, wikiurl, listurl, programminglang, downloadurl, lastdoap, sourceforgeproject, freshmeatproject, reviewed, active, fti, autoupdate, translationgroup, translationpermission, releaseroot, calendar) VALUES (2, 2, 2, 'unassigned', 'unassigned syncs', 'unassigned syncs', 'syncs still not assigned to a real product', 'unassigned syncs, will not be processed, to be moved to real projects ASAP.', '2004-09-24 20:58:00.674409', 'http://arch.ubuntu.com/', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, true, false, '''asap'':26 ''move'':22 ''real'':12C,24 ''sync'':3A,5B,6C,15 ''still'':7C ''assign'':9C ''process'':19 ''product'':13C ''project'':25 ''unassign'':1A,2A,4B,14', false, NULL, 1, NULL, NULL);
INSERT INTO product (id, project, "owner", name, displayname, title, summary, description, datecreated, homepageurl, screenshotsurl, wikiurl, listurl, programminglang, downloadurl, lastdoap, sourceforgeproject, freshmeatproject, reviewed, active, fti, autoupdate, translationgroup, translationpermission, releaseroot, calendar) VALUES (3, 3, 2, 'arch-mirrors', 'Arch mirrors', 'Arch archive mirrors', 'Arch Archive Mirroring project.', 'Arch archive full-archive mirror tasks', '2004-09-24 20:58:00.691047', 'http://arch.ubuntu.com/', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, false, true, '''arch'':2A,4A,6B,9C,13 ''full'':16 ''task'':19 ''archiv'':7B,10C,14,17 ''mirror'':3A,5A,8B,11C,18 ''project'':12C ''full-arch'':15 ''arch-mirror'':1A', false, NULL, 1, NULL, NULL);
INSERT INTO product (id, project, "owner", name, displayname, title, summary, description, datecreated, homepageurl, screenshotsurl, wikiurl, listurl, programminglang, downloadurl, lastdoap, sourceforgeproject, freshmeatproject, reviewed, active, fti, autoupdate, translationgroup, translationpermission, releaseroot, calendar) VALUES (4, 4, 12, 'firefox', 'Mozilla Firefox', 'Mozilla Firefox', 'The Mozilla Firefox web browser', 'The Mozilla Firefox web browser', '2004-09-24 20:58:02.185708', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, false, true, '''web'':9C,14 ''browser'':10C,15 ''firefox'':1A,3A,5B,8C,13 ''mozilla'':2A,4B,7C,12', false, 1, 100, NULL, NULL);
INSERT INTO product (id, project, "owner", name, displayname, title, summary, description, datecreated, homepageurl, screenshotsurl, wikiurl, listurl, programminglang, downloadurl, lastdoap, sourceforgeproject, freshmeatproject, reviewed, active, fti, autoupdate, translationgroup, translationpermission, releaseroot, calendar) VALUES (5, 5, 12, 'evolution', 'Evolution', 'The Evolution Groupware Application', 'Evolution is an email client, addressbook and calendar application that is very well integrated with the Gnome desktop. Evolution is the standard mail client in the Ubuntu distribution, and supports all current mail system standards.', 'Recently, Evolution has seen significant work to make it interoperable with the proprietary Microsoft Exchange Server protocols and formats, allowing organisations to replace Outlook on Windows with Evolution and Linux.

The current stable release series of Evolution is 2.0.', '2004-09-24 20:58:02.240163', 'http://www.gnome.org/evolution/', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, false, true, '''2.0'':80 ''mail'':29C,39C ''make'':49 ''seen'':45 ''seri'':76 ''well'':19C ''work'':47 ''allow'':61 ''email'':10C ''gnome'':23C ''linux'':71 ''stabl'':74 ''applic'':6B,15C ''client'':11C,30C ''evolut'':1A,2A,4B,7C,25C,43,69,78 ''format'':60 ''integr'':20C ''recent'':42 ''releas'':75 ''replac'':64 ''server'':57 ''system'':40C ''ubuntu'':33C ''window'':67 ''current'':38C,73 ''desktop'':24C ''exchang'':56 ''organis'':62 ''outlook'':65 ''support'':36C ''calendar'':14C ''groupwar'':5B ''protocol'':58 ''signific'':46 ''standard'':28C,41C ''distribut'':34C ''interoper'':51 ''microsoft'':55 ''addressbook'':12C ''proprietari'':54', false, 1, 100, NULL, NULL);
INSERT INTO product (id, project, "owner", name, displayname, title, summary, description, datecreated, homepageurl, screenshotsurl, wikiurl, listurl, programminglang, downloadurl, lastdoap, sourceforgeproject, freshmeatproject, reviewed, active, fti, autoupdate, translationgroup, translationpermission, releaseroot, calendar) VALUES (6, 5, 12, 'gnome-terminal', 'GNOME Terminal', 'The GNOME Terminal Emulator', 'Gnome Terminal is a simple terminal application for your Gnome desktop. It allows quick access to console applications, supports all console types, and has many useful features such as tabbed consoles (many consoles in a single window with quick switching between them).', 'The Gnome Terminal application fully supports Gnome 2 and is a standard part of the Gnome Desktop.', '2004-09-24 20:58:02.256678', 'http://www.gnome.org/', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, false, true, '''2'':57 ''tab'':39C ''use'':35C ''emul'':9B ''mani'':34C,41C ''part'':62 ''type'':31C ''allow'':22C ''fulli'':54 ''gnome'':2A,4A,7B,10C,19C,51,56,65 ''quick'':23C,48C ''simpl'':14C ''singl'':45C ''access'':24C ''applic'':16C,27C,53 ''consol'':26C,30C,40C,42C ''featur'':36C ''switch'':49C ''termin'':3A,5A,8B,11C,15C,52 ''window'':46C ''desktop'':20C,66 ''support'':28C,55 ''standard'':61 ''gnome-termin'':1A', false, NULL, 1, NULL, NULL);
INSERT INTO product (id, project, "owner", name, displayname, title, summary, description, datecreated, homepageurl, screenshotsurl, wikiurl, listurl, programminglang, downloadurl, lastdoap, sourceforgeproject, freshmeatproject, reviewed, active, fti, autoupdate, translationgroup, translationpermission, releaseroot, calendar) VALUES (7, 6, 12, 'iso-codes', 'iso-codes', 'The iso-codes', 'foo', 'bar', '2004-09-24 20:58:02.258743', 'http://www.novell.com/', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, false, true, '''bar'':12 ''foo'':11C ''iso'':2A,5A,9B ''code'':3A,6A,10B ''iso-cod'':1A,4A,8B', false, NULL, 1, NULL, NULL);
INSERT INTO product (id, project, "owner", name, displayname, title, summary, description, datecreated, homepageurl, screenshotsurl, wikiurl, listurl, programminglang, downloadurl, lastdoap, sourceforgeproject, freshmeatproject, reviewed, active, fti, autoupdate, translationgroup, translationpermission, releaseroot, calendar) VALUES (8, 4, 12, 'thunderbird', 'Mozilla Thunderbird', 'Mozilla Thunderbird', 'The Mozilla Thunderbird email client', 'The Mozilla Thunderbird email client', '2004-09-24 20:58:04.478988', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, false, true, '''email'':9C,14 ''client'':10C,15 ''mozilla'':2A,4B,7C,12 ''thunderbird'':1A,3A,5B,8C,13', false, NULL, 1, NULL, NULL);
INSERT INTO product (id, project, "owner", name, displayname, title, summary, description, datecreated, homepageurl, screenshotsurl, wikiurl, listurl, programminglang, downloadurl, lastdoap, sourceforgeproject, freshmeatproject, reviewed, active, fti, autoupdate, translationgroup, translationpermission, releaseroot, calendar) VALUES (9, 5, 16, 'applets', 'Gnome Applets', 'The Gnome Panel Applets', 'The Gnome Panel Applets are a collection of standard widgets that can be installed on your desktop Panel. These icons act as launchers for applications, or indicators of the status of your machine. For example, panel applets exist to show you your battery status or wifi network signal strength.', 'This is the collection of Panel Applets that is part of the default Gnome release. Additional Panel Applets are available from third parties. A complete set of Panel Applets is included in the Ubuntu OS, for example.

The Gnome Panel team includes Abel Kascinsky, Frederick Wurst and Andreas Andropovitch Axelsson.', '2004-10-03 16:46:09.113721', 'http://www.gnome.org/panel/', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, false, true, '''os'':91 ''act'':28C ''set'':82 ''abel'':99 ''icon'':27C ''part'':66 ''show'':47C ''team'':97 ''wifi'':53C ''addit'':72 ''avail'':76 ''exist'':45C ''gnome'':2A,5B,9C,70,95 ''indic'':34C ''panel'':6B,10C,25C,43C,62,73,84,96 ''parti'':79 ''third'':78 ''wurst'':102 ''andrea'':104 ''applet'':1A,3A,7B,11C,44C,63,74,85 ''applic'':32C ''exampl'':42C,93 ''includ'':87,98 ''instal'':21C ''machin'':40C ''releas'':71 ''signal'':55C ''status'':37C,51C ''ubuntu'':90 ''widget'':17C ''batteri'':50C ''collect'':14C,60 ''complet'':81 ''default'':69 ''desktop'':24C ''network'':54C ''axelsson'':106 ''launcher'':30C ''standard'':16C ''strength'':56C ''frederick'':101 ''kascinski'':100 ''andropovitch'':105', false, NULL, 1, NULL, NULL);
INSERT INTO product (id, project, "owner", name, displayname, title, summary, description, datecreated, homepageurl, screenshotsurl, wikiurl, listurl, programminglang, downloadurl, lastdoap, sourceforgeproject, freshmeatproject, reviewed, active, fti, autoupdate, translationgroup, translationpermission, releaseroot, calendar) VALUES (10, NULL, 2, 'python-gnome2-dev', 'python gnome2 dev', 'python gnome2 dev', 'Python bindings for the GNOME desktop environment', 'Python bindings for the GNOME desktop environment', '2004-09-24 20:58:00.674409', 'http://www.daa.com.au/~james/software/pygtk/', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, true, false, '''dev'':4A,7A,10B ''bind'':12C,19 ''gnome'':15C,22 ''gnome2'':3A,6A,9B ''python'':2A,5A,8B,11C,18 ''desktop'':16C,23 ''environ'':17C,24 ''python-gnome2-dev'':1A', false, NULL, 1, NULL, NULL);
INSERT INTO product (id, project, "owner", name, displayname, title, summary, description, datecreated, homepageurl, screenshotsurl, wikiurl, listurl, programminglang, downloadurl, lastdoap, sourceforgeproject, freshmeatproject, reviewed, active, fti, autoupdate, translationgroup, translationpermission, releaseroot, calendar) VALUES (11, 5, 12, 'netapplet', 'NetApplet', 'Network Applet', 'The Novell Network Applet', 'Displays current network status and allows network switching', '2005-03-10 16:00:00', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, false, true, '''allow'':14 ''novel'':6C ''applet'':4B,8C ''status'':12 ''switch'':16 ''current'':10 ''display'':9 ''network'':3B,7C,11,15 ''netapplet'':1A,2A', false, NULL, 1, NULL, NULL);
INSERT INTO product (id, project, "owner", name, displayname, title, summary, description, datecreated, homepageurl, screenshotsurl, wikiurl, listurl, programminglang, downloadurl, lastdoap, sourceforgeproject, freshmeatproject, reviewed, active, fti, autoupdate, translationgroup, translationpermission, releaseroot, calendar) VALUES (12, NULL, 16, 'a52dec', 'a52dec', 'Liba52 Test Decoder', 'a52dec is a test program for liba52.', 'This tool decodes ATSC A/52 streams, and also includes a demultiplexer for mpeg-1 and mpeg-2 program streams. The liba52 source code is always distributed in the a52dec package, to make sure it easier for people to test it.', '2005-04-14 00:00:00', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, false, true, '''1'':27 ''2'':31 ''a/52'':17 ''also'':20 ''atsc'':16 ''code'':37 ''make'':46 ''mpeg'':26,30 ''sure'':47 ''test'':4B,9C,53 ''tool'':14 ''alway'':39 ''decod'':5B,15 ''peopl'':51 ''sourc'':36 ''a52dec'':1A,2A,6C,43 ''easier'':49 ''includ'':21 ''liba52'':3B,12C,35 ''mpeg-1'':25 ''mpeg-2'':29 ''packag'':44 ''stream'':18,33 ''program'':10C,32 ''distribut'':40 ''demultiplex'':23', false, NULL, 1, NULL, NULL);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'product'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'productlabel'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'productlabel'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'productseries'::pg_catalog.regclass;

INSERT INTO productseries (id, product, name, displayname, summary, branch, importstatus, datelastsynced, syncinterval, rcstype, cvsroot, cvsmodule, cvsbranch, cvstarfileurl, svnrepository, bkrepository, releaseroot, releasefileglob, releaseverstyle, targetarcharchive, targetarchcategory, targetarchbranch, targetarchversion, dateautotested, dateprocessapproved, datesyncapproved, datestarted, datefinished, datecreated) VALUES (1, 4, 'milestones', 'Milestone Releases', 'The Firefox milestone releases are development releases aimed at testing new features in the developer community. They are not intended for widespread end-user adoption, except among the very brave.', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2005-06-06 08:59:51.895136');
INSERT INTO productseries (id, product, name, displayname, summary, branch, importstatus, datelastsynced, syncinterval, rcstype, cvsroot, cvsmodule, cvsbranch, cvstarfileurl, svnrepository, bkrepository, releaseroot, releasefileglob, releaseverstyle, targetarcharchive, targetarchcategory, targetarchbranch, targetarchversion, dateautotested, dateprocessapproved, datesyncapproved, datestarted, datefinished, datecreated) VALUES (2, 4, '1.0', 'Mozilla Firefox', 'The 1.0 branch of the Mozilla web browser. Currently, this is the stable branch of Mozilla, and all stable releases are made off this branch.', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2005-06-06 08:59:51.898385');
INSERT INTO productseries (id, product, name, displayname, summary, branch, importstatus, datelastsynced, syncinterval, rcstype, cvsroot, cvsmodule, cvsbranch, cvstarfileurl, svnrepository, bkrepository, releaseroot, releasefileglob, releaseverstyle, targetarcharchive, targetarchcategory, targetarchbranch, targetarchversion, dateautotested, dateprocessapproved, datesyncapproved, datestarted, datefinished, datecreated) VALUES (3, 5, 'main', 'MAIN', 'The primary "trunk" of development for this product. This series
was automatically created and represents the idea of a primary trunk
of software development without "stable branches". For most
products, releases in this series will be "milestone" or "test"
releases, and there should be other series for the stable releases
of the product.', 14, 5, NULL, NULL, 1, ':pserver:anonymous@anoncvs.gnome.org:/cvs/gnome', 'evolution', 'MAIN', '', NULL, NULL, '', '', NULL, 'gnome@arch.ubuntu.com', 'evolution', 'MAIN', '0', NULL, NULL, NULL, NULL, NULL, '2005-06-06 08:59:51.914873');
INSERT INTO productseries (id, product, name, displayname, summary, branch, importstatus, datelastsynced, syncinterval, rcstype, cvsroot, cvsmodule, cvsbranch, cvstarfileurl, svnrepository, bkrepository, releaseroot, releasefileglob, releaseverstyle, targetarcharchive, targetarchcategory, targetarchbranch, targetarchversion, dateautotested, dateprocessapproved, datesyncapproved, datestarted, datefinished, datecreated) VALUES (4, 8, 'main', 'MAIN', 'The primary "trunk" of development for this product. This series
was automatically created and represents the idea of a primary trunk
of software development without "stable branches". For most
products, releases in this series will be "milestone" or "test"
releases, and there should be other series for the stable releases
of the product.', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2005-06-06 08:59:51.91214');
INSERT INTO productseries (id, product, name, displayname, summary, branch, importstatus, datelastsynced, syncinterval, rcstype, cvsroot, cvsmodule, cvsbranch, cvstarfileurl, svnrepository, bkrepository, releaseroot, releasefileglob, releaseverstyle, targetarcharchive, targetarchcategory, targetarchbranch, targetarchversion, dateautotested, dateprocessapproved, datesyncapproved, datestarted, datefinished, datecreated) VALUES (5, 11, 'releases', 'NetApplet Releases', 'Releases of Network Applet', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2005-06-06 08:59:51.899819');
INSERT INTO productseries (id, product, name, displayname, summary, branch, importstatus, datelastsynced, syncinterval, rcstype, cvsroot, cvsmodule, cvsbranch, cvstarfileurl, svnrepository, bkrepository, releaseroot, releasefileglob, releaseverstyle, targetarcharchive, targetarchcategory, targetarchbranch, targetarchversion, dateautotested, dateprocessapproved, datesyncapproved, datestarted, datefinished, datecreated) VALUES (6, 12, 'main', 'MAIN', 'The primary upstream development branch, from which all releases are made.', NULL, 2, NULL, NULL, 1, ':pserver:anonymous@cvs.sourceforge.net:/cvsroot/liba52', 'a52dec', 'MAIN', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2005-06-06 08:59:51.913564');
INSERT INTO productseries (id, product, name, displayname, summary, branch, importstatus, datelastsynced, syncinterval, rcstype, cvsroot, cvsmodule, cvsbranch, cvstarfileurl, svnrepository, bkrepository, releaseroot, releasefileglob, releaseverstyle, targetarcharchive, targetarchcategory, targetarchbranch, targetarchversion, dateautotested, dateprocessapproved, datesyncapproved, datestarted, datefinished, datecreated) VALUES (7, 12, 'failedbranch', 'FAILEDBRANCH', 'A branch where auto test has failed.', NULL, 3, NULL, NULL, 1, ':pserver:anonymous@cvs.sourceforge.net:/cvsroot/liba52', 'a52dec', 'AUTOTESTFAILED', NULL, NULL, NULL, NULL, NULL, NULL, 'a52dec@bazaar.ubuntu.com', 'a52dec', 'AUTOTESTFAILED', '0', NULL, NULL, NULL, NULL, NULL, '2005-06-06 08:59:51.913564');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'productseries'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'productrelease'::pg_catalog.regclass;

INSERT INTO productrelease (id, datereleased, "version", title, description, changelog, "owner", summary, productseries, manifest, datecreated) VALUES (1, '2004-06-28 00:00:00', '1.0.0', 'First Stable Release', '', '', 12, 'After four years of work the Mozilla project makes its first public stable release. Mozilla 1.0.0 is a major milestone in open source history.', 2, 4, '2005-06-06 08:59:51.930201');
INSERT INTO productrelease (id, datereleased, "version", title, description, changelog, "owner", summary, productseries, manifest, datecreated) VALUES (2, '2004-06-28 00:00:00', '0.8', NULL, NULL, NULL, 12, NULL, 4, NULL, '2005-06-06 08:59:51.924844');
INSERT INTO productrelease (id, datereleased, "version", title, description, changelog, "owner", summary, productseries, manifest, datecreated) VALUES (3, '2004-10-15 18:27:09.878302', '0.9', 'One Tree Hill', 'What''s New

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

', NULL, 16, 'Release 0.9 of Firefox introduced a new theme as well as improved migration tools for people switching to Firefox.', 1, 3, '2005-06-06 08:59:51.929023');
INSERT INTO productrelease (id, datereleased, "version", title, description, changelog, "owner", summary, productseries, manifest, datecreated) VALUES (4, '2004-10-15 18:31:19.164989', '0.9.1', 'One Tree Hill (v2)', '', NULL, 16, 'This was a bugfix release to patch up problems with the new extension system.', 1, 2, '2005-06-06 08:59:51.927785');
INSERT INTO productrelease (id, datereleased, "version", title, description, changelog, "owner", summary, productseries, manifest, datecreated) VALUES (5, '2004-10-15 18:32:35.717695', '0.9.2', 'One (secure) Tree Hill', 'Security fixes

    * 250180 - [Windows] Disallow access to insecure shell: protocol.
', NULL, 16, 'This was a security fix release for 0.9.', 1, 1, '2005-06-06 08:59:51.926792');
INSERT INTO productrelease (id, datereleased, "version", title, description, changelog, "owner", summary, productseries, manifest, datecreated) VALUES (6, '2005-02-28 00:00:00', '2.1.6', NULL, NULL, 'Bugzilla bugs fixed (see http://bugzilla.ximian.com/show_bug.cgi):

 * Addressbook
   #73005 - Cannot cancel ''Contact List Editor'' (Siva)
   #73005 - offline - setting/unsetting folder offline property is not working (Sushma)
   #70371 - Evolution crashes when adding contact list (Siva)
   #67724 - When unix user name, callendar points to old username (Siva)
   #54825 - Freeze on .vcf import from MacOS X AddressBook (Christophe Fergeau)
   #73013 - ''Right'' click on a ''Contact'' cannot select ''Cut'' (Siva)

 * Calendar
   #72958 - Unable to send delayed meeting (Chen)
   #72006 - Opened existing appointments with attachment - press cancel - popup info with save / discard / cancel changes (Chen)
   #63866 - Same name can be entered twice in invitations tab (JP)
   #67714 - Invitations Tab Allows Entry Of Empty Line (JP)
   #62089 - adding contact lists to meetings impossible (JP)
   #47747 - Changes to attendee not updated until click on different row (JP)
   #61495 - Existing text is placed off screen when editing attendee field (JP)
   #28947 - adding contact list to attendee list should expand it (JP)
   #67724 - When unix user name, callendar points to old username (Siva)
   #72038 - Changes meeting to appoinment after throwing warning invalid mail id (Rodrigo)
   #69556 - Crash attaching mime parts to calendar events (Harish)

 * Mail
   #66126 - attach File Chooser is modal (Michael)
   #68549 - Answering to Usenet article doesn''t consider the "Followup-To:" field (Michael)
   #71003 - threads still running at exit (Michael)
   #62109 - Inconsistent ways of determining 8-bit Subject: and From: header charsets (Jeff)
   #34153 - Confusing Outbox semantics for deleted outgoing messages (Michael)
   #71528 - Search Selection Widget Has Repeated Items (Michael)
   #71967 - Evolution delete mail from POP3 server even is checked the option "leave the mail on server (Michael)
   #40515 - Signature scripts do not allow switches (Michael)
   #68866 - Forward button doesn''t put newline between headers and body (Michael)
   #35219 - flag-for-followup crufting (Michael)
   #64987 - Go to next unread message doesn''t work when multiple messages are selected (Michael)
   #72337 - Evolution crashes if I click OK/Cancel on the password dialog after disabling the IMAP account (Michael)
   #70718 - Next and previous buttons don''t realize there''s new mail (Michael)
   #61363 - Setup wizard, IMAP for receiving server, sending default GW (Michael)
   #70795 - Next/Previous Message Should Only Display Listed Emails (Michael)
   #23822 - no copy text option when right-clicking on marked mail text (Rodney)
   #72266 - You shouldn''t be able to open more than one ''Select Folder'' dialog in the mail filters (Michael)
   #71429 - on NLD, menus in wrong order (Michae)l
   #72228 - cannot store into groupwise sent folder (Michael)
   #72209 - Evolution is crashing when you move a VFolder to a folder ''on this computer'' (Michael)
   #72275 - Can''t use Shift+F10 to popup context menu for link in message (Harry Lu)
   #54503 - "New" dropdown menu on toolbar has wrong widget style (Rodney)
   #72676 - Saved filter rule can''t be modified if it is selected with GOK. (Harry Lu)

 * SMIME
   #68592 - "Backup" buttons in certificate settings does nothing - work around (Michael)

 * Shell
   #33287 - "send/receive" button not greyed out when starting offline (JP)
   #48868 - Status bar changes its height when fonts are large (William Jon McCann)

 * Plugins
   #71527 - Save Calendar widget mixup between directory and file (Rodrigo)

Other bugs

 * Addressbook
   - Use new categories dialog in contact editor (Rodrigo)
   - HIG spacing fixes (Rodney)
   - Display warning dialog when GW server is old (Vivek)

 * Calendar
   - Always ensure default sources are available (Siva)
   - Don''t look up free/busy unless we need to (Harish)
   - Make sure new events don''t display twice (Chen)
   - Make sure double click opens attachments (Chen)

 * Mail
   - a11y fixes for composer (Harry Lu)
   - Use gnome-vfs API to launch external applications (Marco Pesenti Gritti)
   - New mailer context menus for messages (Rodney)

 * Shell
   - Fix leak (JP)
   - Use gnome-vfs API to open quick reference (Marco Pesenti Gritti)

 * Plugins
   - Make e-popup more robust (Michael)
   - Cleanup authors/descriptions (Björn Torkelsson)
   - out of office exchange fixes (Sushma)
   - retry send options if invalid session string (Chen)
   - set proper default port for shared folders (Vivek)

 * Miscellaneous
   - BSD runtime linking fixes (Hans)
   - distclean fixes (Björn Torkelsson)

Updated translations:
   - et (Priit Laes)
   - el (Kostas Papadimas, Nikos Charonitakis)
   - sv (Christian Rose)
   - es (Francisco Javier F. Serrador)
   - it (Luca Ferretti, Marco Ciampa)
   - da (Martin Willemoes Hansen)
   - ca (Josep Puigdemont, Xavi Conde)
   - nb (Kjartan Maraas)
   - no (Kjartan Maraas)
   - ru (Leonid Kanter)
   - gu (Ankit Patel)
   - cs (Miloslav Trmac)
   - nl (Vincent van Adrighem)
   - fi (Ilkka Tuohela)
   - pt (Duarte Loreto)
   - uk (Maxim Dziumanenko)
   - ko (Changwoo Ryu)
   - de (Frank Arnold)
   - fr (Vincent Carriere)
   - en_CA (Adam Weinberger)
   - cs (Miloslav Trmac)
   - pl (Artur Flinta)
   - bg (Vladimir Petkov)
   - ja (Takeshi AIHANA)
   - en_GB (David Lodge)
   - en_CA (Adam Weinberger)
   - lt (Zygimantas Berucka)', 12, NULL, 3, NULL, '2005-06-06 08:59:51.919766');
INSERT INTO productrelease (id, datereleased, "version", title, description, changelog, "owner", summary, productseries, manifest, datecreated) VALUES (7, '2005-03-10 16:20:00', '1.0', NULL, NULL, NULL, 12, NULL, 5, NULL, '2005-06-06 08:59:51.925908');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'productrelease'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'productcvsmodule'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'productcvsmodule'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'productbkbranch'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'productbkbranch'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'productsvnmodule'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'productsvnmodule'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'archarchive'::pg_catalog.regclass;

INSERT INTO archarchive (id, name, title, description, visible, "owner") VALUES (1, 'mozilla@arch.ubuntu.com', 'Mozilla', 'text', false, NULL);
INSERT INTO archarchive (id, name, title, description, visible, "owner") VALUES (2, 'thunderbird@arch.ubuntu.com', 'Thunderbid', 'text', false, NULL);
INSERT INTO archarchive (id, name, title, description, visible, "owner") VALUES (3, 'twisted@arch.ubuntu.com', 'Twisted', 'text', false, NULL);
INSERT INTO archarchive (id, name, title, description, visible, "owner") VALUES (4, 'bugzilla@arch.ubuntu.com', 'Bugzilla', 'text', false, NULL);
INSERT INTO archarchive (id, name, title, description, visible, "owner") VALUES (5, 'arch@arch.ubuntu.com', 'Arch', 'text', false, NULL);
INSERT INTO archarchive (id, name, title, description, visible, "owner") VALUES (6, 'kiwi2@arch.ubuntu.com', 'Kiwi2', 'text', false, NULL);
INSERT INTO archarchive (id, name, title, description, visible, "owner") VALUES (7, 'plone@arch.ubuntu.com', 'Plone', 'text', false, NULL);
INSERT INTO archarchive (id, name, title, description, visible, "owner") VALUES (8, 'gnome@arch.ubuntu.com', 'GNOME', 'The GNOME Project', false, NULL);
INSERT INTO archarchive (id, name, title, description, visible, "owner") VALUES (9, 'iso-codes@arch.ubuntu.com', 'iso-codes', 'The iso-codes', false, NULL);


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
INSERT INTO archnamespace (id, archarchive, category, branch, "version", visible) VALUES (10, 1, 'mozilla', 'release', '0.9.2', true);
INSERT INTO archnamespace (id, archarchive, category, branch, "version", visible) VALUES (11, 1, 'mozilla', 'release', '0.9.1', true);
INSERT INTO archnamespace (id, archarchive, category, branch, "version", visible) VALUES (12, 1, 'mozilla', 'release', '0.9', true);
INSERT INTO archnamespace (id, archarchive, category, branch, "version", visible) VALUES (13, 1, 'mozilla', 'release', '0.8', true);
INSERT INTO archnamespace (id, archarchive, category, branch, "version", visible) VALUES (14, 8, 'evolution', 'MAIN', '0', true);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'archnamespace'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'branch'::pg_catalog.regclass;

INSERT INTO branch (id, archnamespace, title, description, "owner", product) VALUES (1, 1, 'Mozilla Firefox 0.9.1', 'text', 1, 4);
INSERT INTO branch (id, archnamespace, title, description, "owner", product) VALUES (2, 2, 'Mozilla Thunderbird 0.9.1', 'text', 11, 8);
INSERT INTO branch (id, archnamespace, title, description, "owner", product) VALUES (3, 3, 'Python Twisted 0.9.1', 'text', 7, NULL);
INSERT INTO branch (id, archnamespace, title, description, "owner", product) VALUES (4, 4, 'Bugzila 0.9.1', 'text', 3, NULL);
INSERT INTO branch (id, archnamespace, title, description, "owner", product) VALUES (5, 5, 'Arch 0.9.1', 'text', 8, NULL);
INSERT INTO branch (id, archnamespace, title, description, "owner", product) VALUES (6, 6, 'Kiwi2 0.9.1', 'text', 9, NULL);
INSERT INTO branch (id, archnamespace, title, description, "owner", product) VALUES (7, 7, 'Plone 0.9.1', 'text', 10, NULL);
INSERT INTO branch (id, archnamespace, title, description, "owner", product) VALUES (8, 8, 'Evolution 2.0', 'text', 13, 5);
INSERT INTO branch (id, archnamespace, title, description, "owner", product) VALUES (9, 9, 'Iso-codes 0.35', 'text', 13, 7);
INSERT INTO branch (id, archnamespace, title, description, "owner", product) VALUES (10, 10, 'Mozilla Firefox 0.9.2', 'text', 1, 4);
INSERT INTO branch (id, archnamespace, title, description, "owner", product) VALUES (11, 11, 'Mozilla Firefox 0.9.1', 'text', 1, 4);
INSERT INTO branch (id, archnamespace, title, description, "owner", product) VALUES (12, 12, 'Mozilla Firefox 0.9', 'text', 1, 4);
INSERT INTO branch (id, archnamespace, title, description, "owner", product) VALUES (13, 13, 'Mozilla Firefox 0.8', 'text', 1, 4);
INSERT INTO branch (id, archnamespace, title, description, "owner", product) VALUES (14, 14, 'Evolution HEAD', 'text', 1, 5);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'branch'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'changeset'::pg_catalog.regclass;

INSERT INTO changeset (id, branch, datecreated, name, logmessage, archid, gpgkey) VALUES (1, 10, '2005-03-09 15:45:00', 'base-0', 'Import of Mozilla Firefox 0.9.2', NULL, NULL);
INSERT INTO changeset (id, branch, datecreated, name, logmessage, archid, gpgkey) VALUES (2, 11, '2005-03-09 15:50:00', 'base-0', 'Import of Mozilla Firefox 0.9.1', NULL, NULL);
INSERT INTO changeset (id, branch, datecreated, name, logmessage, archid, gpgkey) VALUES (3, 12, '2005-03-09 15:55:00', 'base-0', 'Import of Mozilla Firefox 0.9', NULL, NULL);


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

INSERT INTO manifest (id, datecreated, uuid) VALUES (1, '2005-03-09 15:50:00', '24fce331-655a-4e17-be55-c718c7faebd0');
INSERT INTO manifest (id, datecreated, uuid) VALUES (2, '2005-03-09 15:55:00', 'bf819b15-10b3-4d1e-9963-b787753e8fb2');
INSERT INTO manifest (id, datecreated, uuid) VALUES (3, '2005-03-09 16:00:00', '2a18a3f1-eec5-4b72-b23c-fb46c8c12a88');
INSERT INTO manifest (id, datecreated, uuid) VALUES (4, '2005-03-09 16:05:00', '97b4ece8-b3c5-4e07-b529-6c76b59a5455');
INSERT INTO manifest (id, datecreated, uuid) VALUES (14, '2005-03-24 00:00:00', 'e0451064-b405-4f52-b387-ebfc1a7ee297');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'manifest'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'manifestentry'::pg_catalog.regclass;

INSERT INTO manifestentry (id, manifest, "sequence", branch, changeset, entrytype, "path", patchon, dirname) VALUES (1, 1, 1, 10, 1, 4, 'firefox-0.9.2.tar.gz', NULL, 'firefox-0.9.2/');
INSERT INTO manifestentry (id, manifest, "sequence", branch, changeset, entrytype, "path", patchon, dirname) VALUES (2, 2, 1, 11, 2, 4, 'firefox-0.9.1.tar.gz', NULL, 'firefox-0.9.1/');
INSERT INTO manifestentry (id, manifest, "sequence", branch, changeset, entrytype, "path", patchon, dirname) VALUES (3, 2, 2, NULL, NULL, 1, 'firefox-0.9.1.tar.gz/random/', NULL, NULL);
INSERT INTO manifestentry (id, manifest, "sequence", branch, changeset, entrytype, "path", patchon, dirname) VALUES (4, 3, 1, 12, 3, 5, 'firefox-0.9.zip', NULL, 'firefox-0.9/');
INSERT INTO manifestentry (id, manifest, "sequence", branch, changeset, entrytype, "path", patchon, dirname) VALUES (5, 3, 2, 12, NULL, 6, 'firefox-0.9_unix.patch', 1, 'firefox-0.9_unix/');
INSERT INTO manifestentry (id, manifest, "sequence", branch, changeset, entrytype, "path", patchon, dirname) VALUES (6, 4, 1, 13, NULL, 3, 'firefox-0.8.ar', NULL, NULL);


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

INSERT INTO distribution (id, name, title, description, domainname, "owner", lucilleconfig, displayname, summary, members, translationgroup, translationpermission) VALUES (1, 'ubuntu', 'Ubuntu Linux', 'Ubuntu is a new
approach to Linux Distribution that includes regular releases, and a
simplified single-CD installation system.', 'ubuntulinux.org', 17, NULL, 'ubuntu', 'Ubuntu is a new
approach to Linux Distribution that includes regular releases, and a
simplified single-CD installation system.', 1, NULL, 1);
INSERT INTO distribution (id, name, title, description, domainname, "owner", lucilleconfig, displayname, summary, members, translationgroup, translationpermission) VALUES (2, 'redhat', 'Redhat Advanced Server', 'Red Hat is a
commercial distribution of the GNU/Linux Operating System.', 'redhat.com', 1, NULL, 'redhat', 'Red Hat is a
commercial distribution of the GNU/Linux Operating System.', 1, NULL, 1);
INSERT INTO distribution (id, name, title, description, domainname, "owner", lucilleconfig, displayname, summary, members, translationgroup, translationpermission) VALUES (3, 'debian', 'Debian GNU/Linux', 'Debian GNU/Linux is
a non commercial distribution of a GNU/Linux Operating System for many
platforms.', 'debian.org', 1, NULL, 'debian', 'Debian GNU/Linux is
a non commercial distribution of a GNU/Linux Operating System for many
platforms.', 1, NULL, 1);
INSERT INTO distribution (id, name, title, description, domainname, "owner", lucilleconfig, displayname, summary, members, translationgroup, translationpermission) VALUES (4, 'gentoo', 'The Gentoo Linux', 'Gentoo is a very
customizeable GNU/Linux Distribution that is designed to let you build every
single package yourself, with your own preferences.', 'gentoo.org', 1, NULL, 'gentoo', 'Gentoo is a very
customizeable GNU/Linux Distribution that is designed to let you build every
single package yourself, with your own preferences.', 1, NULL, 1);
INSERT INTO distribution (id, name, title, description, domainname, "owner", lucilleconfig, displayname, summary, members, translationgroup, translationpermission) VALUES (5, 'kubuntu', 'Kubuntu - Free KDE-based Linux', 'Kubuntu is an entirely free Linux distribution that uses the K Desktop
Environment as its default desktop after install.', 'kubuntu.org', 1, NULL, 'kubuntu', 'Kubuntu is an entirely free Linux distribution that uses the K Desktop
Environment as its default desktop after install.', 1, NULL, 1);
INSERT INTO distribution (id, name, title, description, domainname, "owner", lucilleconfig, displayname, summary, members, translationgroup, translationpermission) VALUES (7, 'guadalinex', 'GuadaLinex: Linux for Andalucia', 'GuadaLinex is based on Ubuntu and adds full support for applications specific to the local environment in Andalucia.', 'guadalinex.es', 4, NULL, 'GuadaLinex', 'The GuadaLinex team produces a high quality linux for the Andalucian marketplace.', 32, NULL, 1);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'distribution'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'distrorelease'::pg_catalog.regclass;

INSERT INTO distrorelease (id, distribution, name, title, description, "version", components, sections, releasestatus, datereleased, parentrelease, "owner", lucilleconfig, summary, displayname, datelastlangpack, messagecount) VALUES (1, 1, 'warty', 'The Warty Warthog
Release', 'Warty was the first stable release of Ubuntu. Key feature goals
included releasing on time, with the latest version of the Gnome Desktop
Environment, and the creation of all the infrastructure required to manage
Ubuntu itself. Warty includes excellent support for Python, with most of the
widely used Python libraries installed by default.', '4.10', 1, 1, 4, '2004-08-20 00:00:00', NULL, 17, NULL, 'Warty is the first release of Ubuntu,
with a planned release date of October 2004.', 'warty', NULL, 0);
INSERT INTO distrorelease (id, distribution, name, title, description, "version", components, sections, releasestatus, datereleased, parentrelease, "owner", lucilleconfig, summary, displayname, datelastlangpack, messagecount) VALUES (2, 2, 'six', 'Six Six Six', 'some text to describe the whole 666 release of RH', '6.0.1', 1, 1, 4, '2004-03-21 00:00:00', NULL, 8, NULL, 'some text to describe the whole 666 release of RH', 'six', NULL, 0);
INSERT INTO distrorelease (id, distribution, name, title, description, "version", components, sections, releasestatus, datereleased, parentrelease, "owner", lucilleconfig, summary, displayname, datelastlangpack, messagecount) VALUES (3, 1, 'hoary', 'The Hoary Hedgehog Release', 'Hoary is the second release of Ubuntu. Key feature goals include the integration of Hoary with the Launchpad for bugs and translation information, as well as Gnome 2.10 and the X.org window system.', '5.04', 1, 1, 2, '2004-08-25 00:00:00', 1, 1, NULL, 'Hoary is the second released of Ubuntu, with release planned for April 2005.', 'hoary', NULL, 94);
INSERT INTO distrorelease (id, distribution, name, title, description, "version", components, sections, releasestatus, datereleased, parentrelease, "owner", lucilleconfig, summary, displayname, datelastlangpack, messagecount) VALUES (4, 2, '7.0', 'Seven', 'The release that we would not expect', '7.0.1', 1, 1, 3, '2004-04-01 00:00:00', 2, 7, NULL, 'The release that we would not expect', '7.0', NULL, 0);
INSERT INTO distrorelease (id, distribution, name, title, description, "version", components, sections, releasestatus, datereleased, parentrelease, "owner", lucilleconfig, summary, displayname, datelastlangpack, messagecount) VALUES (5, 1, 'grumpy', 'The Grumpy
Groundhog Release', 'Grumpy, the third release of Ubuntu Linux, is not yet
in active development. This information is purely a placeholder.', '5.10', 1, 1, 1, '2004-08-29 00:00:00', 1, 1, NULL, 'Grumpy is the third release of
Ubuntu, planned for October 2005.', 'grumpy', NULL, 0);
INSERT INTO distrorelease (id, distribution, name, title, description, "version", components, sections, releasestatus, datereleased, parentrelease, "owner", lucilleconfig, summary, displayname, datelastlangpack, messagecount) VALUES (6, 3, 'woody', 'WOODY', 'WOODY is the current stable verison of Debian GNU/Linux', '3.0', 1, 1, 4, '2003-01-01 00:00:00', NULL, 2, NULL, 'WOODY is the current stable verison of Debian GNU/Linux', 'woody', NULL, 0);
INSERT INTO distrorelease (id, distribution, name, title, description, "version", components, sections, releasestatus, datereleased, parentrelease, "owner", lucilleconfig, summary, displayname, datelastlangpack, messagecount) VALUES (7, 3, 'sarge', 'Sarge', 'Sarge is the FROZEN unstable version of Debian GNU/Linux.', '3.1', 1, 1, 3, '2004-09-29 00:00:00', 6, 5, NULL, 'Sarge is the FROZEN unstable version of Debian GNU/Linux.', 'sarge', NULL, 0);
INSERT INTO distrorelease (id, distribution, name, title, description, "version", components, sections, releasestatus, datereleased, parentrelease, "owner", lucilleconfig, summary, displayname, datelastlangpack, messagecount) VALUES (8, 3, 'sid', 'Sid', 'Sid is the CRAZY unstable version of Debian GNU/Linux.', '3.2', 1, 1, 1, '2004-12-29 00:00:00', 6, 6, NULL, 'Sid is the CRAZY unstable version of Debian GNU/Linux.', 'sid', NULL, 0);
INSERT INTO distrorelease (id, distribution, name, title, description, "version", components, sections, releasestatus, datereleased, parentrelease, "owner", lucilleconfig, summary, displayname, datelastlangpack, messagecount) VALUES (9, 7, '2k5', 'Guada 2005', 'This release places extra emphasis on usability and installability. The installer is adapted from Ubuntu to assume your country, language, keyboard and time zone preference, thus ensuring that installs ask the minimum number of questions possible.', '2005', 1, 1, 2, NULL, 3, 4, NULL, 'Guada 2005 is a rapid-install version of
Ubuntu Hoary for the Andalucian marketplace.', 'Guada2005', NULL, 0);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'distrorelease'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'distroarchrelease'::pg_catalog.regclass;

INSERT INTO distroarchrelease (id, distrorelease, processorfamily, architecturetag, "owner") VALUES (1, 1, 1, 'i386', 1);
INSERT INTO distroarchrelease (id, distrorelease, processorfamily, architecturetag, "owner") VALUES (6, 3, 1, 'i386', 1);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'distroarchrelease'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'libraryfilecontent'::pg_catalog.regclass;

INSERT INTO libraryfilecontent (id, datecreated, datemirrored, filesize, sha1) VALUES (1, '2005-04-07 16:46:05.265391', NULL, 178859, '378b3498ead213d35a82033a6e9196014a5ef25c');
INSERT INTO libraryfilecontent (id, datecreated, datemirrored, filesize, sha1) VALUES (2, '2005-04-07 16:46:05.266763', NULL, 9922560, 'a57faa6287aee2c58e115673a119c6083d31d1b9');
INSERT INTO libraryfilecontent (id, datecreated, datemirrored, filesize, sha1) VALUES (3, '2005-04-07 16:46:05.26727', NULL, 309386, 'b218ca7b52fa813550e3f14cdcf3ba68606e4446');
INSERT INTO libraryfilecontent (id, datecreated, datemirrored, filesize, sha1) VALUES (4, '2005-04-07 16:46:05.267803', NULL, 162927750, 'cfbd3ee1f510c66d49be465b900a3334e8488184');
INSERT INTO libraryfilecontent (id, datecreated, datemirrored, filesize, sha1) VALUES (5, '2005-05-18 08:03:28.021862', NULL, 4381, '9b1f78faa39fb09a9fd955d744002c2d8f32d88d');
INSERT INTO libraryfilecontent (id, datecreated, datemirrored, filesize, sha1) VALUES (6, '2005-05-18 08:03:28.021862', NULL, 7910, 'afdf21d698587a6601e2ffed0f44292b7ad5dd07');
INSERT INTO libraryfilecontent (id, datecreated, datemirrored, filesize, sha1) VALUES (7, '2005-05-18 08:03:28.021862', NULL, 10826, '502828e7591277535abe9015ffbc6918dbba8ef4');
INSERT INTO libraryfilecontent (id, datecreated, datemirrored, filesize, sha1) VALUES (8, '2005-05-18 08:03:28.021862', NULL, 10826, '502828e7591277535abe9015ffbc6918dbba8ef4');
INSERT INTO libraryfilecontent (id, datecreated, datemirrored, filesize, sha1) VALUES (9, '2005-05-18 08:03:28.021862', NULL, 2655, 'ca3b107af84c05eaf98ba073376153986566ec28');
INSERT INTO libraryfilecontent (id, datecreated, datemirrored, filesize, sha1) VALUES (10, '2005-05-18 08:03:28.021862', NULL, 13110, 'bc7bebca1e3c5c166838b19f0eeb7f171e51805d');
INSERT INTO libraryfilecontent (id, datecreated, datemirrored, filesize, sha1) VALUES (11, '2005-05-18 08:03:28.021862', NULL, 13499, '78a26efee75a54f113063b78783b2d4612fee409');
INSERT INTO libraryfilecontent (id, datecreated, datemirrored, filesize, sha1) VALUES (12, '2005-05-18 08:03:28.021862', NULL, 12695, '8812d04c170ca90bb1423e188ce9706869aa03d7');
INSERT INTO libraryfilecontent (id, datecreated, datemirrored, filesize, sha1) VALUES (13, '2005-05-18 08:03:28.021862', NULL, 13133, 'db1b50cbde7142d344bd8ef9b2e1fe3b3116f77c');
INSERT INTO libraryfilecontent (id, datecreated, datemirrored, filesize, sha1) VALUES (14, '2005-05-18 08:03:28.021862', NULL, 13641, 'e19cc1446e3004f10475c37b2cd363f75b8ae89a');
INSERT INTO libraryfilecontent (id, datecreated, datemirrored, filesize, sha1) VALUES (15, '2005-05-18 08:03:28.021862', NULL, 13269, 'fc8cab1cb1e5fb1efa3c3c475b8f7c8dc5038d50');
INSERT INTO libraryfilecontent (id, datecreated, datemirrored, filesize, sha1) VALUES (16, '2005-05-18 08:03:28.021862', NULL, 13983, 'e17ee3031bd29dcd1e5905c0fd17945600a91ccf');
INSERT INTO libraryfilecontent (id, datecreated, datemirrored, filesize, sha1) VALUES (17, '2005-05-18 08:03:28.021862', NULL, 12652, '07b01d1e6fe9a729f911e72dfe674a5e0abdc4ee');
INSERT INTO libraryfilecontent (id, datecreated, datemirrored, filesize, sha1) VALUES (18, '2005-05-18 08:03:28.021862', NULL, 13240, '801dc911c2bd67e17eff087516fdc63a2ac322ce');
INSERT INTO libraryfilecontent (id, datecreated, datemirrored, filesize, sha1) VALUES (19, '2005-05-18 08:03:28.021862', NULL, 4165, 'fca78a2292e4034b8dfbb2de6f69e17ebeecaaa1');
INSERT INTO libraryfilecontent (id, datecreated, datemirrored, filesize, sha1) VALUES (20, '2005-05-18 08:03:28.021862', NULL, 4093, 'fc67a1770f78c45c396b4724195aeb10683aa2fd');
INSERT INTO libraryfilecontent (id, datecreated, datemirrored, filesize, sha1) VALUES (21, '2005-05-18 08:03:28.021862', NULL, 3635, '4ab2ca308dafe152789640942488e23a33e4f46c');
INSERT INTO libraryfilecontent (id, datecreated, datemirrored, filesize, sha1) VALUES (22, '2005-05-18 08:03:28.021862', NULL, 3553, '20815563ee33368d51e3213354f97c05b4685968');
INSERT INTO libraryfilecontent (id, datecreated, datemirrored, filesize, sha1) VALUES (23, '2005-05-18 08:03:28.021862', NULL, 3778, '965968d3e6668f39ebc64bc11a3f1a5cd07c213b');
INSERT INTO libraryfilecontent (id, datecreated, datemirrored, filesize, sha1) VALUES (24, '2005-05-18 08:03:28.021862', NULL, 3666, 'cca8fb78e05a34481e07683cea8c3a47f01c609e');
INSERT INTO libraryfilecontent (id, datecreated, datemirrored, filesize, sha1) VALUES (25, '2005-05-18 08:03:28.021862', NULL, 3793, '28a7accfb491a2b4895b49b810ca7cda0badc787');
INSERT INTO libraryfilecontent (id, datecreated, datemirrored, filesize, sha1) VALUES (26, '2005-05-18 08:03:28.021862', NULL, 4773, '03efb176f04f3897de7d5e6484864b0559fd6cd6');
INSERT INTO libraryfilecontent (id, datecreated, datemirrored, filesize, sha1) VALUES (27, '2005-05-18 08:03:28.021862', NULL, 2961, '4468039e1d2cbdfc78d2e53477e5fe0537bae302');
INSERT INTO libraryfilecontent (id, datecreated, datemirrored, filesize, sha1) VALUES (28, '2005-05-18 08:03:28.021862', NULL, 3558, 'd6c2ddacdab7618ce2a555c20a4a730fcdb42600');
INSERT INTO libraryfilecontent (id, datecreated, datemirrored, filesize, sha1) VALUES (29, '2005-05-18 08:03:28.021862', NULL, 3561, '9eb09455e6a568605c1bbab4cdf1936eee92222d');
INSERT INTO libraryfilecontent (id, datecreated, datemirrored, filesize, sha1) VALUES (30, '2005-05-18 08:03:28.021862', NULL, 3305, 'b45b170da29f9b22650315657505124766c93720');
INSERT INTO libraryfilecontent (id, datecreated, datemirrored, filesize, sha1) VALUES (31, '2005-05-18 08:03:28.021862', NULL, 3987, '9668ba9f0a59f9e6e6bc73fc5dc9f116b202bceb');
INSERT INTO libraryfilecontent (id, datecreated, datemirrored, filesize, sha1) VALUES (32, '2005-05-18 08:03:28.021862', NULL, 4908, '874a6ef9cd1aaef17653c6c12f4b83ef9487c1c3');
INSERT INTO libraryfilecontent (id, datecreated, datemirrored, filesize, sha1) VALUES (33, '2005-05-18 08:03:28.021862', NULL, 4908, '874a6ef9cd1aaef17653c6c12f4b83ef9487c1c3');
INSERT INTO libraryfilecontent (id, datecreated, datemirrored, filesize, sha1) VALUES (34, '2005-08-10 09:31:29.606407', NULL, 2, '71853c6197a6a7f222db0f1978c7cb232b87c5ee');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'libraryfilecontent'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'libraryfilealias'::pg_catalog.regclass;

INSERT INTO libraryfilealias (id, content, filename, mimetype, expires) VALUES (1, 1, 'netapplet-1.0.0.tar.gz', 'application/x-gtar', NULL);
INSERT INTO libraryfilealias (id, content, filename, mimetype, expires) VALUES (2, 1, 'netapplet_1.0.0.orig.tar.gz', 'application/x-gtar', NULL);
INSERT INTO libraryfilealias (id, content, filename, mimetype, expires) VALUES (3, 2, 'firefox-0.9.2.tar.gz', 'application/x-gtar', NULL);
INSERT INTO libraryfilealias (id, content, filename, mimetype, expires) VALUES (4, 3, 'evolution-1.0.tar.gz', 'application/x-gtar', NULL);
INSERT INTO libraryfilealias (id, content, filename, mimetype, expires) VALUES (5, 5, 'netapplet.pot', 'application/x-po', NULL);
INSERT INTO libraryfilealias (id, content, filename, mimetype, expires) VALUES (6, 6, 'pmount.pot', 'application/x-po', NULL);
INSERT INTO libraryfilealias (id, content, filename, mimetype, expires) VALUES (7, 7, 'evolution-2.2.pot', 'application/x-po', NULL);
INSERT INTO libraryfilealias (id, content, filename, mimetype, expires) VALUES (8, 8, 'evolution-2.2.pot', 'application/x-po', NULL);
INSERT INTO libraryfilealias (id, content, filename, mimetype, expires) VALUES (9, 9, 'pkgconf-mozilla.pot', 'application/x-po', NULL);
INSERT INTO libraryfilealias (id, content, filename, mimetype, expires) VALUES (10, 10, 'hr.po', 'application/x-po', NULL);
INSERT INTO libraryfilealias (id, content, filename, mimetype, expires) VALUES (11, 11, 'ca.po', 'application/x-po', NULL);
INSERT INTO libraryfilealias (id, content, filename, mimetype, expires) VALUES (12, 12, 'nb.po', 'application/x-po', NULL);
INSERT INTO libraryfilealias (id, content, filename, mimetype, expires) VALUES (13, 13, 'cs.po', 'application/x-po', NULL);
INSERT INTO libraryfilealias (id, content, filename, mimetype, expires) VALUES (14, 14, 'es_ES.po', 'application/x-po', NULL);
INSERT INTO libraryfilealias (id, content, filename, mimetype, expires) VALUES (15, 15, 'de.po', 'application/x-po', NULL);
INSERT INTO libraryfilealias (id, content, filename, mimetype, expires) VALUES (16, 16, 'fr.po', 'application/x-po', NULL);
INSERT INTO libraryfilealias (id, content, filename, mimetype, expires) VALUES (17, 17, 'it_IT.po', 'application/x-po', NULL);
INSERT INTO libraryfilealias (id, content, filename, mimetype, expires) VALUES (18, 18, 'es.po', 'application/x-po', NULL);
INSERT INTO libraryfilealias (id, content, filename, mimetype, expires) VALUES (19, 19, 'fr.po', 'application/x-po', NULL);
INSERT INTO libraryfilealias (id, content, filename, mimetype, expires) VALUES (20, 20, 'pt_BR.po', 'application/x-po', NULL);
INSERT INTO libraryfilealias (id, content, filename, mimetype, expires) VALUES (21, 21, 'ja.po', 'application/x-po', NULL);
INSERT INTO libraryfilealias (id, content, filename, mimetype, expires) VALUES (22, 22, 'es.po', 'application/x-po', NULL);
INSERT INTO libraryfilealias (id, content, filename, mimetype, expires) VALUES (23, 23, 'nl.po', 'application/x-po', NULL);
INSERT INTO libraryfilealias (id, content, filename, mimetype, expires) VALUES (24, 24, 'cs.po', 'application/x-po', NULL);
INSERT INTO libraryfilealias (id, content, filename, mimetype, expires) VALUES (25, 25, 'da.po', 'application/x-po', NULL);
INSERT INTO libraryfilealias (id, content, filename, mimetype, expires) VALUES (26, 26, 'fi.po', 'application/x-po', NULL);
INSERT INTO libraryfilealias (id, content, filename, mimetype, expires) VALUES (27, 27, 'gl.po', 'application/x-po', NULL);
INSERT INTO libraryfilealias (id, content, filename, mimetype, expires) VALUES (28, 28, 'lt.po', 'application/x-po', NULL);
INSERT INTO libraryfilealias (id, content, filename, mimetype, expires) VALUES (29, 29, 'it.po', 'application/x-po', NULL);
INSERT INTO libraryfilealias (id, content, filename, mimetype, expires) VALUES (30, 30, 'tr.po', 'application/x-po', NULL);
INSERT INTO libraryfilealias (id, content, filename, mimetype, expires) VALUES (31, 31, 'de.po', 'application/x-po', NULL);
INSERT INTO libraryfilealias (id, content, filename, mimetype, expires) VALUES (32, 32, 'es.po', 'application/x-po', NULL);
INSERT INTO libraryfilealias (id, content, filename, mimetype, expires) VALUES (33, 33, 'es.po', 'application/x-po', NULL);
INSERT INTO libraryfilealias (id, content, filename, mimetype, expires) VALUES (34, 34, 'evolution-2.2-test.pot', 'application/x-po', NULL);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'libraryfilealias'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'productreleasefile'::pg_catalog.regclass;

INSERT INTO productreleasefile (productrelease, libraryfile, filetype, id) VALUES (5, 3, 1, 2);
INSERT INTO productreleasefile (productrelease, libraryfile, filetype, id) VALUES (7, 1, 1, 1);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'productreleasefile'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'sourcepackagename'::pg_catalog.regclass;

INSERT INTO sourcepackagename (id, name) VALUES (1, 'mozilla-firefox');
INSERT INTO sourcepackagename (id, name) VALUES (9, 'evolution');
INSERT INTO sourcepackagename (id, name) VALUES (10, 'netapplet');
INSERT INTO sourcepackagename (id, name) VALUES (14, 'pmount');
INSERT INTO sourcepackagename (id, name) VALUES (15, 'a52dec');
INSERT INTO sourcepackagename (id, name) VALUES (16, 'mozilla');
INSERT INTO sourcepackagename (id, name) VALUES (17, 'uberfrob');
INSERT INTO sourcepackagename (id, name) VALUES (18, 'thunderbird');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'sourcepackagename'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'packaging'::pg_catalog.regclass;

INSERT INTO packaging (packaging, id, sourcepackagename, distrorelease, productseries, datecreated, "owner") VALUES (1, 1, 1, 3, 2, '2005-07-05 14:20:26.577312', NULL);
INSERT INTO packaging (packaging, id, sourcepackagename, distrorelease, productseries, datecreated, "owner") VALUES (1, 2, 9, 3, 3, '2005-07-05 14:20:26.577312', NULL);
INSERT INTO packaging (packaging, id, sourcepackagename, distrorelease, productseries, datecreated, "owner") VALUES (1, 3, 10, 1, 5, '2005-07-05 14:20:26.577312', NULL);
INSERT INTO packaging (packaging, id, sourcepackagename, distrorelease, productseries, datecreated, "owner") VALUES (1, 4, 9, 1, 3, '2005-07-05 14:20:26.577312', NULL);
INSERT INTO packaging (packaging, id, sourcepackagename, distrorelease, productseries, datecreated, "owner") VALUES (1, 6, 10, 3, 5, '2005-07-05 14:20:26.577312', NULL);
INSERT INTO packaging (packaging, id, sourcepackagename, distrorelease, productseries, datecreated, "owner") VALUES (1, 7, 15, 1, 6, '2005-07-05 14:20:26.577312', NULL);
INSERT INTO packaging (packaging, id, sourcepackagename, distrorelease, productseries, datecreated, "owner") VALUES (1, 9, 1, 1, 1, '2005-07-05 14:20:26.577312', NULL);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'packaging'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'sourcepackagerelease'::pg_catalog.regclass;

INSERT INTO sourcepackagerelease (id, creator, "version", dateuploaded, urgency, dscsigningkey, component, changelog, builddepends, builddependsindep, architecturehintlist, dsc, section, manifest, maintainer, sourcepackagename, uploaddistrorelease, format) VALUES (14, 1, '0.9', '2004-09-27 11:57:13', 1, NULL, 1, 'Mozilla dummy Changelog......', 'gcc-3.4-base, libc6 (>= 2.3.2.ds1-4), gcc-3.4 (>= 3.4.1-4sarge1), gcc-3.4 (<< 3.4.2), libstdc++6-dev (>= 3.4.1-4sarge1)', 'bacula-common (= 1.34.6-2), bacula-director-common (= 1.34.6-2), postgresql-client (>= 7.4)', NULL, NULL, 1, NULL, 1, 1, 3, 1);
INSERT INTO sourcepackagerelease (id, creator, "version", dateuploaded, urgency, dscsigningkey, component, changelog, builddepends, builddependsindep, architecturehintlist, dsc, section, manifest, maintainer, sourcepackagename, uploaddistrorelease, format) VALUES (15, 1, '1.0', '2004-09-27 11:57:13', 1, NULL, 1, NULL, NULL, NULL, NULL, NULL, 1, NULL, 1, 9, 3, 1);
INSERT INTO sourcepackagerelease (id, creator, "version", dateuploaded, urgency, dscsigningkey, component, changelog, builddepends, builddependsindep, architecturehintlist, dsc, section, manifest, maintainer, sourcepackagename, uploaddistrorelease, format) VALUES (16, 1, '1.0-1', '2005-03-10 16:30:00', 1, NULL, 1, NULL, NULL, NULL, NULL, NULL, 1, NULL, 1, 10, 3, 1);
INSERT INTO sourcepackagerelease (id, creator, "version", dateuploaded, urgency, dscsigningkey, component, changelog, builddepends, builddependsindep, architecturehintlist, dsc, section, manifest, maintainer, sourcepackagename, uploaddistrorelease, format) VALUES (17, 1, '0.99.6-1', '2005-03-14 18:00:00', 1, NULL, 1, NULL, NULL, NULL, NULL, NULL, 1, NULL, 1, 10, 1, 1);
INSERT INTO sourcepackagerelease (id, creator, "version", dateuploaded, urgency, dscsigningkey, component, changelog, builddepends, builddependsindep, architecturehintlist, dsc, section, manifest, maintainer, sourcepackagename, uploaddistrorelease, format) VALUES (20, 1, '0.1-1', '2005-03-24 20:59:31.439579', 1, NULL, 1, NULL, NULL, NULL, NULL, NULL, 1, 14, 1, 14, 3, 1);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'sourcepackagerelease'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'sourcepackagereleasefile'::pg_catalog.regclass;

INSERT INTO sourcepackagereleasefile (sourcepackagerelease, libraryfile, filetype, id) VALUES (15, 4, 1, 2);
INSERT INTO sourcepackagereleasefile (sourcepackagerelease, libraryfile, filetype, id) VALUES (16, 2, 1, 1);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'sourcepackagereleasefile'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'build'::pg_catalog.regclass;

INSERT INTO build (id, datecreated, processor, distroarchrelease, buildstate, datebuilt, buildduration, buildlog, builder, gpgsigningkey, changes, sourcepackagerelease) VALUES (2, '2004-09-27 11:57:13', 1, 1, 1, '2004-09-27 11:57:13', NULL, NULL, NULL, NULL, 'Sample changes :)....', 14);
INSERT INTO build (id, datecreated, processor, distroarchrelease, buildstate, datebuilt, buildduration, buildlog, builder, gpgsigningkey, changes, sourcepackagerelease) VALUES (7, '2005-03-24 00:00:00', 1, 6, 1, NULL, NULL, NULL, NULL, NULL, 'changes', 20);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'build'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'binarypackagename'::pg_catalog.regclass;

INSERT INTO binarypackagename (id, name) VALUES (8, 'mozilla-firefox');
INSERT INTO binarypackagename (id, name) VALUES (13, 'pmount');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'binarypackagename'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'binarypackage'::pg_catalog.regclass;

INSERT INTO binarypackage (id, binarypackagename, "version", summary, description, build, binpackageformat, component, section, priority, shlibdeps, depends, recommends, suggests, conflicts, replaces, provides, essential, installedsize, copyright, licence, architecturespecific, fti) VALUES (12, 8, '0.9', 'Mozilla Firefox Web Browser', 'Mozilla Firefox Web Browser is .....', 2, 1, 1, 1, 10, NULL, 'gcc-3.4-base, libc6 (>= 2.3.2.ds1-4), gcc-3.4 (>= 3.4.1-4sarge1), gcc-3.4 (<< 3.4.2), libstdc++6-dev (>= 3.4.1-4sarge1)', 'gcc-3.4-base, libc6 (>= 2.3.2.ds1-4), gcc-3.4 (>= 3.4.1-4sarge1), gcc-3.4 (<< 3.4.2), libstdc++6-dev (>= 3.4.1-4sarge1)', NULL, NULL, NULL, 'mozilla-firefox', NULL, NULL, NULL, NULL, true, '''web'':3,7 ''browser'':4,8 ''firefox'':2,6 ''mozilla'':1,5');
INSERT INTO binarypackage (id, binarypackagename, "version", summary, description, build, binpackageformat, component, section, priority, shlibdeps, depends, recommends, suggests, conflicts, replaces, provides, essential, installedsize, copyright, licence, architecturespecific, fti) VALUES (15, 13, '0.1-1', 'pmount shortdesc', 'pmount description', 7, 1, 1, 1, 40, NULL, NULL, NULL, NULL, NULL, NULL, NULL, false, NULL, NULL, NULL, false, '''pmount'':1,3 ''descript'':4 ''shortdesc'':2');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'binarypackage'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'binarypackagefile'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'binarypackagefile'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'packageselection'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'packageselection'::pg_catalog.regclass;


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
INSERT INTO pomsgid (id, msgid) VALUES (13, 'Migrating `%s'':');
INSERT INTO pomsgid (id, msgid) VALUES (14, 'The location and hierarchy of the Evolution contact folders has changed since Evolution 1.x.

Please be patient while Evolution migrates your folders...');
INSERT INTO pomsgid (id, msgid) VALUES (15, '%d contact');
INSERT INTO pomsgid (id, msgid) VALUES (16, '%d contacts');
INSERT INTO pomsgid (id, msgid) VALUES (17, 'Opening %d contact will open %d new window as well.
Do you really want to display this contact?');
INSERT INTO pomsgid (id, msgid) VALUES (18, 'Opening %d contacts will open %d new windows as well.
Do you really want to display all of these contacts?');
INSERT INTO pomsgid (id, msgid) VALUES (19, '%d foo');
INSERT INTO pomsgid (id, msgid) VALUES (20, '%d bars');
INSERT INTO pomsgid (id, msgid) VALUES (21, 'EncFS Password: ');
INSERT INTO pomsgid (id, msgid) VALUES (22, 'When specifying daemon mode, you must use absolute paths (beginning with ''/'')');
INSERT INTO pomsgid (id, msgid) VALUES (23, 'Please select a key size in bits.  The cipher you have chosen
supports sizes from %i to %i bits in increments of %i bits.
For example: ');
INSERT INTO pomsgid (id, msgid) VALUES (24, 'Found %i invalid file.');
INSERT INTO pomsgid (id, msgid) VALUES (25, 'Found %i invalid files.');
INSERT INTO pomsgid (id, msgid) VALUES (26, '
      <p>Thousands of sites (particularly news sites and weblogs) publish their latest headlines and/or stories in a machine-readable format so that other sites can easily link to them. This content is usually in the form of an <a href="http://blogs.law.harvard.edu/tech/rss">RSS</a> feed (which is an XML-based syndication standard).</p>
      <p>You can read aggregated content from many sites using RSS feed readers, such as <a href="http://www.disobey.com/amphetadesk/">Amphetadesk</a>.</p>
      <p>Drupal provides the means to aggregate feeds from many sites and display these aggregated feeds to your site''s visitors. To do this, enable the aggregator module in site administration and then go to the aggregator configuration page, where you can subscribe to feeds and set up other options.</p>
      <h3>How do I find RSS feeds to aggregate?</h3>
      <p>Many web sites (especially weblogs) display small XML icons or other obvious links on their home page. You can follow these to obtain the web address for the RSS feed. Common extensions for RSS feeds are .rss, .xml and .rdf. For example: <a href="http://slashdot.org/slashdot.rdf">Slashdot RSS</a>.</p>
      <p>If you can''t find a feed for a site, or you want to find several feeds on a given topic, try an RSS syndication directory such as <a href="http://www.syndic8.com/">Syndic8</a>.</p>
      <p>To learn more about RSS, read Mark Pilgrim''s <a href="http://www.xml.com/pub/a/2002/12/18/dive-into-xml.html">What is RSS</a> and WebReference.com''s <a href="http://www.webreference.com/authoring/languages/xml/rss/1/">The Evolution of RSS</a> articles.</p>
      <p>NOTE: Enable your site''s XML syndication button by turning on the Syndicate block in block management.</p>
      <h3>How do I add a news feed?</h3>
      <p>To subscribe to an RSS feed on another site, use the <a href="% admin-news">aggregation page</a>.</p>
      <p>Once there, click the <a href="%new-feed">new feed</a> tab. Drupal will then ask for the following:</p>
      <ul>
       <li><strong>Title</strong> -- The text entered here will be used in your news aggregator, within the administration configuration section, and as a title for the news feed block. As a general rule, use the web site name from which the feed originates.</li>
       <li><strong>URL</strong> -- Here you''ll enter the fully-qualified web address for the feed you wish to subscribe to.</li>
       <li><strong>Update interval</strong> -- This is how often Drupal will scan the feed for new content. This defaults to every hour. Checking a feed more frequently that this is typically a waste of bandwidth and is considered somewhat impolite. For automatic updates to work, cron.php must be called regularly. If it is not, you''ll have to manually update the feeds one at a time within the news aggregation administration page by using <a href="%update-items">update items</a>.</li>
       <li><strong>Latest items block</strong> -- The number of items selected here will determine how many of the latest items from the feed will appear in a block which may be enabled and placed in the <a href="%block">blocks</a> administration page.</li>
       <li><strong>Automatically file items</strong> -- As items are received from a feed they will be put in any categories you have selected here.</li>
      </ul>
      <p>Once you have submitted the new feed, check to make sure it is working properly by selecting <a href="%update-items">update items</a> on the <a href="%admin-news">aggregation page</a>. If you do not see any items listed for that feed, edit the feed and make sure that the URL was entered correctly.</p>
      <h3>Adding categories</h3>
      <p>News items can be filed into categories. To create a category, start at the <a href="%admin-news">aggregation page</a>.</p>
      <p>Once there, select <a href="%new-category">new category</a> from the menu. Drupal will then ask for the following:</p>
      <ul>
       <li><strong>Title</strong> -- The title will be used in the <em>news by topics</em> listing in your news aggregator and for the block created for the bundle.</li>
       <li><strong>Description</strong> -- A short description of the category to tell users more details about what news items they might find in the category.</li>
       <li><strong>Latest items block</strong> -- The number of items selected here will determine how many of the latest items from the category will appear in a block which may be enabled and placed in the <a href="%block">blocks</a> administration page.</li>
      </ul>
      <h3>Using the news aggregator</h3>
      <p>The news aggregator has a number of ways that it displays your subscribed content:</p>
      <ul>
       <li><strong><a href="%news-aggregator">News aggregator</a></strong> (latest news) -- Displays all incoming items in the order in which they were received.</li>
       <li><strong><a href="%sources">Sources</a></strong> -- Organizes incoming content by feed, displaying feed titles (each of which links to a page with the latest items from that feed) and item titles (which link to that item''s actual story/article).</li>
       <li><strong><a href="%categories">Categories</a></strong> -- Organizes incoming content by category, displaying category titles (each of which links to a page with the latest items from that category) and item titles (which link to that item''s actual story/article).</li>
      </ul>
      <p>Pages that display items (for sources, categories, etc.) display the following for each item:
      <ul>
       <li>The title of the item (its headline).</li>
       <li>The categories that the item belongs to, each of which links to that particular category page as detailed above.</li>
       <li>A description containing the first few paragraphs or a summary of the item (if available).</li>
       <li>The name of the feed, which links to the individual feed''s page, listing information about that feed and items for that feed only. This is not shown on feed pages (they would link to the page you''re currently on).</li>
      </ul>
      <p>Additionally, users with the <em>administer news feeds permission</em> will see a link to categorize the news items. Clicking this will allow them to select which category(s) each news item is in.</p>
      <h3>Technical details</h3>
      <p>Drupal automatically generates an OPML feed file that is available by selecting the XML icon on the News Sources page.</p>
      <p>When fetching feeds Drupal supports conditional GETs, this reduces the bandwidth usage for feeds that have not been updated since the last check.</p>
      <p>If a feed is permanently moved to a new location Drupal will automatically update the feed URL to the new address.</p>');
INSERT INTO pomsgid (id, msgid) VALUES (27, '_Add Group');
INSERT INTO pomsgid (id, msgid) VALUES (28, 'Disconnected');
INSERT INTO pomsgid (id, msgid) VALUES (29, 'Ethernet connection');
INSERT INTO pomsgid (id, msgid) VALUES (30, 'Dial-up connection');
INSERT INTO pomsgid (id, msgid) VALUES (31, 'Wireless connection');
INSERT INTO pomsgid (id, msgid) VALUES (32, 'Wireless connection (secure)');
INSERT INTO pomsgid (id, msgid) VALUES (33, '<span weight="bold" size="larger">Network switching is currently unavailable</span>

The "netdaemon" service is not running');
INSERT INTO pomsgid (id, msgid) VALUES (34, '<span weight="bold" size="larger">Do you want to disconnect all network connections?</span>

Applications which use the network, such as web browsers and email programs, will likely stop working while you are disconnected.');
INSERT INTO pomsgid (id, msgid) VALUES (35, 'Error trying to set default keyring: %d');
INSERT INTO pomsgid (id, msgid) VALUES (36, 'Error trying to create keyring: %d');
INSERT INTO pomsgid (id, msgid) VALUES (37, 'Error trying to get default keyring: %d');
INSERT INTO pomsgid (id, msgid) VALUES (38, 'Unable to save to keyring!  Err: %d');
INSERT INTO pomsgid (id, msgid) VALUES (39, 'Password for network "%s"');
INSERT INTO pomsgid (id, msgid) VALUES (40, '<span weight="bold" size="larger">Error displaying connection information: </span>

No active connection!');
INSERT INTO pomsgid (id, msgid) VALUES (41, '<span weight="bold" size="larger">Error displaying connection information: </span>

Unable to open socket!');
INSERT INTO pomsgid (id, msgid) VALUES (42, '<span weight="bold" size="larger">Error displaying information: </span>

SIOCGIFFLAGS failed on socket!');
INSERT INTO pomsgid (id, msgid) VALUES (43, '<span weight="bold" size="larger">Network configuration could not be run</span>

%s');
INSERT INTO pomsgid (id, msgid) VALUES (44, 'Network Connections');
INSERT INTO pomsgid (id, msgid) VALUES (45, 'No network connections available');
INSERT INTO pomsgid (id, msgid) VALUES (46, '%s: %s (active)');
INSERT INTO pomsgid (id, msgid) VALUES (47, 'Wireless Networks');
INSERT INTO pomsgid (id, msgid) VALUES (48, 'Wireless disabled');
INSERT INTO pomsgid (id, msgid) VALUES (49, 'No wireless networks available');
INSERT INTO pomsgid (id, msgid) VALUES (50, '%s (active)');
INSERT INTO pomsgid (id, msgid) VALUES (51, 'Connection _Information');
INSERT INTO pomsgid (id, msgid) VALUES (52, '_Configure Network Settings');
INSERT INTO pomsgid (id, msgid) VALUES (53, '_Remove from Panel');
INSERT INTO pomsgid (id, msgid) VALUES (54, '<span weight="bold" size="larger">Network switching is currently unavailable</span>

You do not have the permissions to change network settings');
INSERT INTO pomsgid (id, msgid) VALUES (55, '*');
INSERT INTO pomsgid (id, msgid) VALUES (56, '<span weight="bold" size="larger">Active Connection Information</span>');
INSERT INTO pomsgid (id, msgid) VALUES (57, 'Add to Keyring');
INSERT INTO pomsgid (id, msgid) VALUES (58, 'Broadcast Address:');
INSERT INTO pomsgid (id, msgid) VALUES (59, 'Connection Information');
INSERT INTO pomsgid (id, msgid) VALUES (60, 'Destination Address:');
INSERT INTO pomsgid (id, msgid) VALUES (61, 'ESSID:');
INSERT INTO pomsgid (id, msgid) VALUES (62, 'Encryption Key:');
INSERT INTO pomsgid (id, msgid) VALUES (63, 'Hardware Address:');
INSERT INTO pomsgid (id, msgid) VALUES (64, 'IP Address:');
INSERT INTO pomsgid (id, msgid) VALUES (65, 'Interface:');
INSERT INTO pomsgid (id, msgid) VALUES (66, 'Show Encryption Key');
INSERT INTO pomsgid (id, msgid) VALUES (67, 'Specify an ESSID');
INSERT INTO pomsgid (id, msgid) VALUES (68, 'Specify the key');
INSERT INTO pomsgid (id, msgid) VALUES (69, 'Subnet Mask:');
INSERT INTO pomsgid (id, msgid) VALUES (70, 'Type:');
INSERT INTO pomsgid (id, msgid) VALUES (71, 'Usage:

%s [options] <device> [<label>]

  Mount <device> to a directory below %s if policy requirements
  are met (see pmount(1) for details). If <label> is given, the mount point
  will be %s/<label>, otherwise it will be %s<device>.
  If the mount point does not exist, it will be created.

');
INSERT INTO pomsgid (id, msgid) VALUES (72, '%s --lock <device> <pid>
  Prevent further pmounts of <device> until it is unlocked again. <pid>
  specifies the process id the lock holds for. This allows to lock a device
  by several independent processes and avoids indefinite locks of crashed
  processes (nonexistant pids are cleaned before attempting a mount).

');
INSERT INTO pomsgid (id, msgid) VALUES (73, '%s --unlock <device> <pid>
  Remove the lock on <device> for process <pid> again.

');
INSERT INTO pomsgid (id, msgid) VALUES (74, 'Options:
  -a, --async : mount <device> with the ''async'' option (default: ''sync'')
  --noatime   : mount <device> with the ''noatime'' option (default: ''atime'')
  -e, --exec  : mount <device> with the ''exec'' option (default: ''noexec'')
  -t <fs>     : mount as file system type <fs> (default: autodetected)
  -c <charset>: use given I/O character set (default: ''utf8'' if called
                in an UTF-8 locale, otherwise mount default)
  -d, --debug : enable debug output (very verbose)
  -h, --help  : print help message and exit successfuly');
INSERT INTO pomsgid (id, msgid) VALUES (75, 'Error: make_mountpoint_name: invalid device %s (must be in /dev/)
');
INSERT INTO pomsgid (id, msgid) VALUES (76, 'Error: label must not be empty
');
INSERT INTO pomsgid (id, msgid) VALUES (77, 'Error: label too long
');
INSERT INTO pomsgid (id, msgid) VALUES (78, 'Error: ''/'' must not occur in label name
');
INSERT INTO pomsgid (id, msgid) VALUES (79, 'Error: device name too long
');
INSERT INTO pomsgid (id, msgid) VALUES (80, 'Error: could not drop all uid privileges');
INSERT INTO pomsgid (id, msgid) VALUES (81, 'Error: could not execute mount');
INSERT INTO pomsgid (id, msgid) VALUES (82, 'Internal error: mount_attempt: given file system name is NULL
');
INSERT INTO pomsgid (id, msgid) VALUES (83, 'Error: invalid file system name ''%s''
');
INSERT INTO pomsgid (id, msgid) VALUES (84, 'Error: invalid charset name ''%s''
');
INSERT INTO pomsgid (id, msgid) VALUES (85, 'Error: could not raise to full root uid privileges');
INSERT INTO pomsgid (id, msgid) VALUES (86, 'Error: could not wait for executed mount process');
INSERT INTO pomsgid (id, msgid) VALUES (87, 'Error: cannot lock for pid %u, this process does not exist
');
INSERT INTO pomsgid (id, msgid) VALUES (88, 'Error: could not create pid lock file %s: %s
');
INSERT INTO pomsgid (id, msgid) VALUES (89, 'Error: could not remove pid lock file %s: %s
');
INSERT INTO pomsgid (id, msgid) VALUES (90, 'Error: do_unlock: could not remove lock directory');
INSERT INTO pomsgid (id, msgid) VALUES (91, 'Error: this program needs to be installed suid root
');
INSERT INTO pomsgid (id, msgid) VALUES (92, 'Internal error: getopt_long() returned unknown value
');
INSERT INTO pomsgid (id, msgid) VALUES (93, 'Warning: device %s is already handled by /etc/fstab, supplied label is ignored
');
INSERT INTO pomsgid (id, msgid) VALUES (94, 'Error: could not determine real path of the device');
INSERT INTO pomsgid (id, msgid) VALUES (95, 'Error: invalid device %s (must be in /dev/)
');
INSERT INTO pomsgid (id, msgid) VALUES (96, 'Error: could not delete mount point');
INSERT INTO pomsgid (id, msgid) VALUES (97, 'Internal error: mode %i not handled.
');
INSERT INTO pomsgid (id, msgid) VALUES (98, 'pmount-hal - execute pmount with additional information from hal

Usage: pmount-hal <hal UDI> [pmount options]

This command mounts the device described by the given UDI using pmount. The
file system type, the volume storage policy and the desired label will be
read out from hal and passed to pmount.');
INSERT INTO pomsgid (id, msgid) VALUES (99, 'Error: could not execute pmount
');
INSERT INTO pomsgid (id, msgid) VALUES (100, 'Error: could not connect to hal
');
INSERT INTO pomsgid (id, msgid) VALUES (101, 'Error: given UDI does not exist
');
INSERT INTO pomsgid (id, msgid) VALUES (102, 'Error: given UDI is not a mountable volume
');
INSERT INTO pomsgid (id, msgid) VALUES (103, 'Error: could not get status of device');
INSERT INTO pomsgid (id, msgid) VALUES (104, 'Error: could not get sysfs directory
');
INSERT INTO pomsgid (id, msgid) VALUES (105, 'Error: could not open <sysfs dir>/block/');
INSERT INTO pomsgid (id, msgid) VALUES (106, 'Error: could not open <sysfs dir>/block/<device>/');
INSERT INTO pomsgid (id, msgid) VALUES (107, 'Error: device %s does not exist
');
INSERT INTO pomsgid (id, msgid) VALUES (108, 'Error: %s is not a block device
');
INSERT INTO pomsgid (id, msgid) VALUES (109, 'Error: could not open fstab-type file');
INSERT INTO pomsgid (id, msgid) VALUES (110, 'Error: device %s is already mounted to %s
');
INSERT INTO pomsgid (id, msgid) VALUES (111, 'Error: device %s is not mounted
');
INSERT INTO pomsgid (id, msgid) VALUES (112, 'Error: device %s was not mounted by you
');
INSERT INTO pomsgid (id, msgid) VALUES (113, 'Error: device %s is not removable
');
INSERT INTO pomsgid (id, msgid) VALUES (114, 'Error: device %s is locked
');
INSERT INTO pomsgid (id, msgid) VALUES (115, 'Error: directory %s already contains a mounted file system
');
INSERT INTO pomsgid (id, msgid) VALUES (116, 'Error: directory %s does not contain a mounted file system
');
INSERT INTO pomsgid (id, msgid) VALUES (117, 'Usage:

%s [options] <device>
  Umount <device> from a directory below %s if policy requirements
  are met (see pumount(1) for details). The mount point directory is removed
  afterwards.

Options:
  -l, --lazy : umount lazily, see umount(8)
  -d, --debug : enable debug output (very verbose)
  -h, --help  : print help message and exit successfuly
');
INSERT INTO pomsgid (id, msgid) VALUES (118, 'Internal error: could not determine mount point
');
INSERT INTO pomsgid (id, msgid) VALUES (119, 'Error: mount point %s is not below %s
');
INSERT INTO pomsgid (id, msgid) VALUES (120, 'Error: could not execute umount');
INSERT INTO pomsgid (id, msgid) VALUES (121, 'Error: could not wait for executed umount process');
INSERT INTO pomsgid (id, msgid) VALUES (122, 'Error: umount failed
');
INSERT INTO pomsgid (id, msgid) VALUES (123, 'Error: out of memory
');
INSERT INTO pomsgid (id, msgid) VALUES (124, 'Error: could not create directory');
INSERT INTO pomsgid (id, msgid) VALUES (125, 'Error: could not create stamp file in directory');
INSERT INTO pomsgid (id, msgid) VALUES (126, 'Error: %s is not a directory
');
INSERT INTO pomsgid (id, msgid) VALUES (127, 'Error: could not open directory');
INSERT INTO pomsgid (id, msgid) VALUES (128, 'Error: directory %s is not empty
');
INSERT INTO pomsgid (id, msgid) VALUES (129, 'Error: ''%s'' is not a valid number
');
INSERT INTO pomsgid (id, msgid) VALUES (130, 'Internal error: could not change to effective uid root');
INSERT INTO pomsgid (id, msgid) VALUES (131, 'Internal error: could not change effective user uid to real user id');
INSERT INTO pomsgid (id, msgid) VALUES (132, 'Internal error: could not change to effective gid root');
INSERT INTO pomsgid (id, msgid) VALUES (133, 'Internal error: could not change effective group id to real group id');
INSERT INTO pomsgid (id, msgid) VALUES (134, '/etc/mozilla/prefs.js is available for customizing preferences.');
INSERT INTO pomsgid (id, msgid) VALUES (135, 'Debian mozilla will load /etc/mozilla/prefs.js after loading some default preference scripts.');
INSERT INTO pomsgid (id, msgid) VALUES (136, 'You can edit this file for system-wide settings. (i.e.: font settings)');
INSERT INTO pomsgid (id, msgid) VALUES (137, 'auto, esddsp, artsdsp, none');
INSERT INTO pomsgid (id, msgid) VALUES (138, 'Please choose your sound daemon''s dsp wrapper.');
INSERT INTO pomsgid (id, msgid) VALUES (139, 'Sometimes mozilla hangs since plugins (e.g. flashplugin) lock /dev/dsp. You can use dsp wrapper to resolve it. ''auto'' will decide which dsp wrappers should be used according to the sound daemon running. When no sound daemon is detected, mozilla won''t use any wrapper. This setting will be saved into /etc/mozilla/mozillarc and can be overriden with your ~/.mozillarc.');
INSERT INTO pomsgid (id, msgid) VALUES (140, 'Enable automatic Language/Region selection?');
INSERT INTO pomsgid (id, msgid) VALUES (141, 'This setting provides an automatic language/region pack selection in Mozilla using the locale settings. It may help a sysadmin faced with hundreds of non-english-speaking novices.');
INSERT INTO pomsgid (id, msgid) VALUES (142, 'Please set your LC_MESSAGE or LC_ALL variable in order this setting works correctly.');
INSERT INTO pomsgid (id, msgid) VALUES (143, 'xprint seems not to be installed');
INSERT INTO pomsgid (id, msgid) VALUES (144, 'Mozilla has dropped postscript support. This means that Xprint is required for printing. Please install xprt-xprintorg package.');
INSERT INTO pomsgid (id, msgid) VALUES (145, 'This is not a bug, Don''t submit bug reports for this. (wishlist to reenable postscript has been submitted already, Bug#256072)');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'pomsgid'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'potranslation'::pg_catalog.regclass;

INSERT INTO potranslation (id, translation) VALUES (1, 'libreta de direcciones de Evolution');
INSERT INTO potranslation (id, translation) VALUES (2, 'carpeta de libretas de direcciones actual');
INSERT INTO potranslation (id, translation) VALUES (3, 'tiene');
INSERT INTO potranslation (id, translation) VALUES (4, ' tarjetas');
INSERT INTO potranslation (id, translation) VALUES (5, 'La ubicación y jerarquía de las carpetas de contactos de Evolution ha cambiado desde Evolution 1.x.

Tenga paciencia mientras Evolution migra sus carpetas...');
INSERT INTO potranslation (id, translation) VALUES (6, '%d contacto');
INSERT INTO potranslation (id, translation) VALUES (7, '%d contactos');
INSERT INTO potranslation (id, translation) VALUES (8, 'Abrir %d contacto abrirá %d ventanas nuevas también.
¿Quiere realmente mostrar este contacto?');
INSERT INTO potranslation (id, translation) VALUES (9, 'Abrir %d contactos abrirá %d ventanas nuevas también.
¿Quiere realmente mostrar todos estos contactos?');
INSERT INTO potranslation (id, translation) VALUES (10, '%d foo');
INSERT INTO potranslation (id, translation) VALUES (11, 'Contraseña de EncFS: ');
INSERT INTO potranslation (id, translation) VALUES (12, '_Añadir grupo');
INSERT INTO potranslation (id, translation) VALUES (13, 'Upotreba:

%s [opcije] <uređaj> [<etiketa>]

  Montiraj <device> u direktorij ispod %s ako su policy zahtjevi
  zadovoljeni (vidi pmount(1) za detalje). Ako <label> je zadan, točka montiranja
  će biti %s/<label>, inače će biti %s<device>.
  Ako ne postoji točka montiranja, biti će kreirana.

');
INSERT INTO potranslation (id, translation) VALUES (14, '%s --lock <device> <pid>
  Spriječi daljnje pmounts <device> sve dok nije ponovno otključan. <pid>
  specificira id procesa za koji drži brava. To dozvoljava da se zaključa uređaj
  sa strane nekoliko nezavisnih procesa i izbjegava neodređena zaključavanja srušenih
  procesa (nepostojeći pid-ovi su očišćeni prije pokušaja montiranja).

');
INSERT INTO potranslation (id, translation) VALUES (15, '%s --unlock <device> <pid>
  Odstrani bravu na <device> za ponovno procesiranje <pid>.

');
INSERT INTO potranslation (id, translation) VALUES (16, 'Opcije:
  -a, --async : montiraj <device> sa ''async'' opcijom (predodređeno: ''sync'')
  --noatime : montiraj <device> sa ''noatime'' opcijom (predodređeno: ''atime'')
  -e, --exec : montiraj <device> sa ''exec'' opcijom (predodređeno: ''noexec'')
  -t <fs> : montiraj kao datotečni sustav <fs> vrste (predodređeno: samodetektirano)
  -c <charset>: upotrebi dani I/O skup znakova (predodređeno: ''utf8'' ako je pozvano
                u jednoj UTF-8 lokali, inače montiraj predodređeno)
  -d, --debug : aktiviraj debug izlaz (jako riječito)
  -h, --help : ispiši pomoćnu poruku i uspješno izađi');
INSERT INTO potranslation (id, translation) VALUES (17, 'Greška: make_mountpoint_name: nevažeči uređaj %s (mora biti u /dev/)
');
INSERT INTO potranslation (id, translation) VALUES (18, 'Greška: etiketa ne smije biti prazna
');
INSERT INTO potranslation (id, translation) VALUES (19, 'Greška: etiketa je preduga
');
INSERT INTO potranslation (id, translation) VALUES (20, 'Greška: ''/'' ne smije se nalaziti u imenu etikete
');
INSERT INTO potranslation (id, translation) VALUES (21, 'Greška: ime uređaja je predugo
');
INSERT INTO potranslation (id, translation) VALUES (22, 'Greška: ne mogu otpustiti sve uid privilegije');
INSERT INTO potranslation (id, translation) VALUES (23, 'Greška: ne mogu izvršiti mount');
INSERT INTO potranslation (id, translation) VALUES (24, 'Unutarnja greška: mount_attempt: dato ime datotečnog sustava je NULL
');
INSERT INTO potranslation (id, translation) VALUES (25, 'Greška: nevažeće ime datotečnog sustava ''%s''
');
INSERT INTO potranslation (id, translation) VALUES (26, 'Greška: nevažeće ime charseta ''%s''
');
INSERT INTO potranslation (id, translation) VALUES (27, 'Greška: ne mogu se dignuti na pune root uid privilegije');
INSERT INTO potranslation (id, translation) VALUES (28, 'Greška: ne mogu čekati za izvršeni proces montiranja');
INSERT INTO potranslation (id, translation) VALUES (29, 'Greška: ne mogu zaključati za pid %u, taj proces ne postoji
');
INSERT INTO potranslation (id, translation) VALUES (30, 'Greška: ne mogu kreirati pid zaključanu datoteku %s: %s
');
INSERT INTO potranslation (id, translation) VALUES (31, 'Greška: ne mogu maknuti pid zaključanu datoteku %s: %s
');
INSERT INTO potranslation (id, translation) VALUES (32, 'Greška: do_unlock: ne mogu maknuti zaključani direktorij');
INSERT INTO potranslation (id, translation) VALUES (33, 'Greška: ovaj program mora biti instaliran kao suid root
');
INSERT INTO potranslation (id, translation) VALUES (34, 'Unutarnja greška: getopt_long() vratio nepoznatu vrijednost
');
INSERT INTO potranslation (id, translation) VALUES (35, 'Upozorenje: uređaj %s je već zbrinut sa strane /etc/fstab, dana etiketa je zanemarena
');
INSERT INTO potranslation (id, translation) VALUES (36, 'Greška: ne mogu ustanoviti pravi put uređaja');
INSERT INTO potranslation (id, translation) VALUES (37, 'Greška: nevažeći uređaj %s (mora biti u /dev/)
');
INSERT INTO potranslation (id, translation) VALUES (38, 'Greška: ne mogu izbrisati točku montiranja');
INSERT INTO potranslation (id, translation) VALUES (39, 'Unutarnja greška: mod %i nije obrađen.
');
INSERT INTO potranslation (id, translation) VALUES (40, 'pmount-hal - izvrši pmount sa dodatnim informacijama iz hal-a

Upotreba: pmount-hal <hal UDI> [pmount opcije]

Ova naredba montira uređaj opisan sa datim UDI-jem koristeči pmount.
Tip datotečnog sustava, volumen policyja spremanja i željena etiketa biti će
čitani iz hal-a i proslijeđeni pmountu.');
INSERT INTO potranslation (id, translation) VALUES (41, 'Greška: ne mogu izvršiti pmount
');
INSERT INTO potranslation (id, translation) VALUES (42, 'Greška: ne mogu se spojiti na hal
');
INSERT INTO potranslation (id, translation) VALUES (43, 'Greška: dani UDI ne postoji
');
INSERT INTO potranslation (id, translation) VALUES (44, 'Greška: dani UDI nije montabilni volumen
');
INSERT INTO potranslation (id, translation) VALUES (45, 'Greška: ne mogu dobiti stanje uređaja');
INSERT INTO potranslation (id, translation) VALUES (46, 'Greška: ne mogu dobiti sysfs direktorij
');
INSERT INTO potranslation (id, translation) VALUES (47, 'Greška: ne mogu otvoriti <sysfs dir>/block/');
INSERT INTO potranslation (id, translation) VALUES (48, 'Greška: ne mogu otvoriti <sysfs dir>/block/<device>/');
INSERT INTO potranslation (id, translation) VALUES (49, 'Greška: uređaj %s ne postoji
');
INSERT INTO potranslation (id, translation) VALUES (50, 'Greška: %s nije blok uređaj
');
INSERT INTO potranslation (id, translation) VALUES (51, 'Greška: ne mogu otvoriti fstab-type datoteku');
INSERT INTO potranslation (id, translation) VALUES (52, 'Greška: uređaj %s je već montiran na %s
');
INSERT INTO potranslation (id, translation) VALUES (53, 'Greška: uređaj %s nije montiran
');
INSERT INTO potranslation (id, translation) VALUES (54, 'Greška: uređaj %s nije montiran za vas
');
INSERT INTO potranslation (id, translation) VALUES (55, 'Greška: uređaj %s nije odstranjiv
');
INSERT INTO potranslation (id, translation) VALUES (56, 'Greška: uređaj %s je zaključan
');
INSERT INTO potranslation (id, translation) VALUES (57, 'Greška: direktorij %s već sadrži montirani datotečni sustav
');
INSERT INTO potranslation (id, translation) VALUES (58, 'Greška: direktorij %s ne sadrži montirani datotečni sustav
');
INSERT INTO potranslation (id, translation) VALUES (59, 'Upotreba:

%s [options] <device>
  Umount <device> iz direktorija ispod %s ako su zahtjevi policyja
  zadovoljeni (vidi pumount(1) za detalje). Točka montiranja direktorija je odstranjena 
  kasnije.

Opcije:
  -l, --lazy : umount lijeno, vidi umount (8)
  -d, --debug : aktiviraj debug izlaz (jako opširno)
  -h, --help : ispiši poruku pomoći i uspješno izađi
');
INSERT INTO potranslation (id, translation) VALUES (60, 'Unutarnja greška: ne mogu ustanoviti točku montiranja
');
INSERT INTO potranslation (id, translation) VALUES (61, 'Greška: točka montiranja %s nije ispod %s
');
INSERT INTO potranslation (id, translation) VALUES (62, 'Greška: ne mogu izvršiti umount');
INSERT INTO potranslation (id, translation) VALUES (63, 'Greška: nisam mogla pričekati za izvršeni umount proces');
INSERT INTO potranslation (id, translation) VALUES (64, 'Greška: neuspjelo umount
');
INSERT INTO potranslation (id, translation) VALUES (65, 'Greška: izvan memorije
');
INSERT INTO potranslation (id, translation) VALUES (66, 'Greška: Nisam mogla kreirati direktorij');
INSERT INTO potranslation (id, translation) VALUES (67, 'Greška: nisam mogla kreirati žig datoteku u direktoriju');
INSERT INTO potranslation (id, translation) VALUES (68, 'Greška: %s nije direktorij
');
INSERT INTO potranslation (id, translation) VALUES (69, 'Greška: nisam mogla otvoriti direktorij');
INSERT INTO potranslation (id, translation) VALUES (70, 'Greška: direktorij %s nije prazan
');
INSERT INTO potranslation (id, translation) VALUES (71, 'Greška: ''%s'' nije ispravan broj
');
INSERT INTO potranslation (id, translation) VALUES (72, 'Unutarnja greška: nisam mogla promjeniti u efektivni uid root');
INSERT INTO potranslation (id, translation) VALUES (73, 'Unutarnja greška: nisam mogla promjeniti efektivni korisnički uid u realni korisnićki id');
INSERT INTO potranslation (id, translation) VALUES (74, 'Unutarnja greška: nisam mogla promjeniti u efektivni gid root');
INSERT INTO potranslation (id, translation) VALUES (75, 'Unutarnja greška: nisam mogla promjeniti efektivnu grupu u realni id grupe');
INSERT INTO potranslation (id, translation) VALUES (76, 'Ús:

%s [opcions] <dispositiu> [<etiqueta>]

  Monta <dispositiu> al directori sota %s si es compleixen
  els requeriments (vegeu pmount(1) per més detalls). Si es dóna <etiqueta>, el punt de muntatge
  serà %s/<etiqueta>, en cas contrari, serà %s<dispositiu>.
  Si el punt de muntatge no existeix, es crearà.

');
INSERT INTO potranslation (id, translation) VALUES (77, '%s --lock <dispositiu> <pid>
  Prevén més pmounts del <dispositiu> fins que no es desbloqui altra vegada. <pid>
  especifica l''identificador del procés al qual actua el blocatge. Això permet bloquejar un dispositiu
  per diversos processos independents i evita bloquejos indefinits de processos
  fallits (pids no existents es netegen abans d''intentar montar-los).

');
INSERT INTO potranslation (id, translation) VALUES (78, '%s --unlock <dispositiu> <pid>
  Remou el blocatge al <dispositiu> per processar <pid> altra vegada.

');
INSERT INTO potranslation (id, translation) VALUES (79, 'Opcions:
  -a, --async : monta <dispositiu> amb l''opció ''async'' (per defecte: ''sync'')
  --noatime   : monta <dispositiu> amb l''opció ''noatime'' (per defecte: ''atime'')
  -e, --exec  : monta <dispositiu> amb l''opció ''exec'' (per defecte: ''noexec'')
  -t <fs>     : monta com a tipus de sistema de fitxers <fs> (per defecte: autodetectat)
  -c <charset>: usa el joc de caràcters I/O donat (per defecte: ''utf8'' si es crida
                des d''una locale UTF-8, si no es monta per defecte)
  -d, --debug : habilita la sortida en mode depuració (molt detalladament)
  -h, --help  : imprimeix el missatge d''ajuda i surt exitosament');
INSERT INTO potranslation (id, translation) VALUES (80, 'Error: make_mountpoint_name: dispositiu %s invàlid (ha d''estar a /dev/)
');
INSERT INTO potranslation (id, translation) VALUES (81, 'Error: l''etiqueta no pot estar buida
');
INSERT INTO potranslation (id, translation) VALUES (82, 'Error: etiqueta massa llarga
');
INSERT INTO potranslation (id, translation) VALUES (83, 'Error: ''/'' no ha d''estar al nom de l''etiqueta
');
INSERT INTO potranslation (id, translation) VALUES (84, 'Error: nom de dispositiu massa llarg
');
INSERT INTO potranslation (id, translation) VALUES (85, 'Error: no es poden eliminar tots els privilegis uid');
INSERT INTO potranslation (id, translation) VALUES (86, 'Error: no es pot executar mount');
INSERT INTO potranslation (id, translation) VALUES (87, 'error intern: mount_attempt: el sistema de fitxers donat és NULL
');
INSERT INTO potranslation (id, translation) VALUES (88, 'Error: el nom %s de sistema de fitxers és invàlid
');
INSERT INTO potranslation (id, translation) VALUES (89, 'Error: el nom %s del joc de caràcters és invàlid
');
INSERT INTO potranslation (id, translation) VALUES (90, 'Error: no s''han pogut donar tots els privilegis uid de super-usuari');
INSERT INTO potranslation (id, translation) VALUES (91, 'Error: no s''ha pogut esperar per processos de muntatge executats');
INSERT INTO potranslation (id, translation) VALUES (92, 'Error: no s''ha pogut blocar el pid  %u. Aquest procés no existeix
');
INSERT INTO potranslation (id, translation) VALUES (93, 'Error: no s''ha pogut crear un blocatge del pid del fitxer %s: %s
');
INSERT INTO potranslation (id, translation) VALUES (94, 'Error: no s''ha pogut remoure el blocatge del pid del fitxer %s: %s
');
INSERT INTO potranslation (id, translation) VALUES (95, 'Error: do_unlock: no s''ha pogut remoure el blocatge del directori');
INSERT INTO potranslation (id, translation) VALUES (96, 'Error: aquest programa necessita ser instal·lar amb suid de super-usuari
');
INSERT INTO potranslation (id, translation) VALUES (97, 'error intern: getopt_long() ha retornat un valor desconegut
');
INSERT INTO potranslation (id, translation) VALUES (98, 'Avís: el dispositiu %s ja és gestionat per /etc/fstab, s''ignorarà l''etiqueta donada
');
INSERT INTO potranslation (id, translation) VALUES (99, 'Error: no s''ha pogut determinar el camí real del dispositiu');
INSERT INTO potranslation (id, translation) VALUES (100, 'Error: dispositiu %s invàlid (ha d''estar a /dev/)
');
INSERT INTO potranslation (id, translation) VALUES (101, 'Error: no s''ha pogut eliminar el punt de muntatge');
INSERT INTO potranslation (id, translation) VALUES (102, 'error intern: el mode %i no s''ha gestionat.
');
INSERT INTO potranslation (id, translation) VALUES (103, 'pmount-hal - executa pmount amb informació addicional de hal

Ús: pmount-hal <UDI de hal> [opcions de pmount]

Aquesta comanda monta el dispositiu descrit per l''UDI donat utilitzant
pmount. El tipus de sistema de fitxers, la política d''emmagatzematge del
volum i l''etiqueta desitjada es llegiran de hal i es passaran a pmount.');
INSERT INTO potranslation (id, translation) VALUES (104, 'Error: no s''ha pogut executar pmount
');
INSERT INTO potranslation (id, translation) VALUES (105, 'Error, no es pot obrir el directori');
INSERT INTO potranslation (id, translation) VALUES (106, 'Error: l''UDI donat no existeix
');
INSERT INTO potranslation (id, translation) VALUES (107, 'Error: l''UDI donat no és un volum montable
');
INSERT INTO potranslation (id, translation) VALUES (108, 'Error: no s''ha pogut aconseguir l''estat del dispositiu');
INSERT INTO potranslation (id, translation) VALUES (109, 'Error: no s''ha pogut aconseguir el directori sysfs
');
INSERT INTO potranslation (id, translation) VALUES (110, 'Error: no s''ha pogut obrir <sysfs dir>/block/');
INSERT INTO potranslation (id, translation) VALUES (111, 'Error: no s''ha pogut obrir <sysfs dir>/block/<dispsitiu>/');
INSERT INTO potranslation (id, translation) VALUES (112, 'Error: el dispositiu %s no existeix
');
INSERT INTO potranslation (id, translation) VALUES (113, 'Error: %s no és un dispositiu de blocs
');
INSERT INTO potranslation (id, translation) VALUES (114, 'Error: no s''ha pogut obrir el fitxer de tipus fstab');
INSERT INTO potranslation (id, translation) VALUES (115, 'Error: el dispositiu %s ja està montat a %s
');
INSERT INTO potranslation (id, translation) VALUES (116, 'Error: el dispositiu %s no està montat
');
INSERT INTO potranslation (id, translation) VALUES (117, 'Error: el dispositiu %s no ha estat montat per tu
');
INSERT INTO potranslation (id, translation) VALUES (118, 'Error: el dispositiu %s no es pot remoure
');
INSERT INTO potranslation (id, translation) VALUES (119, 'Error: el dispositiu %s està blocat
');
INSERT INTO potranslation (id, translation) VALUES (120, 'Error: el directori %s ja conté un sistema de fitxers montat
');
INSERT INTO potranslation (id, translation) VALUES (121, 'Error: el directori %s no conté un sistema de fitxers montat
');
INSERT INTO potranslation (id, translation) VALUES (122, 'Ús:

%s [opcions] <dispositiu>
  Umount <dispositiu> des d''un directori sota %s si es compleixen els
  requeriments (vegeu pumount(1) per més detalls). El directori del punt de montatge
  s''elimina després

Opcions:
  -l, --lazy : umount mandrosament, vegeu umount(8)
  -d, --debug : habilita la sortida de depuració (molt detalladament)
  -h, --help : imprimeix el missatge d''ajuda i surt exitosament
');
INSERT INTO potranslation (id, translation) VALUES (123, 'Error intern: no s''ha pogut determinar el punt de montatge
');
INSERT INTO potranslation (id, translation) VALUES (124, 'Error: el punt de montatge %s no és a sota %s
');
INSERT INTO potranslation (id, translation) VALUES (125, 'Error: no s''ha pogut executar umount');
INSERT INTO potranslation (id, translation) VALUES (126, 'Error no s''ha pogut esperar els processos d''umount executats');
INSERT INTO potranslation (id, translation) VALUES (127, 'Error: ha fallat umount
');
INSERT INTO potranslation (id, translation) VALUES (128, 'Error: fora de memòria
');
INSERT INTO potranslation (id, translation) VALUES (129, 'Error: no es pot crear el directori');
INSERT INTO potranslation (id, translation) VALUES (130, 'Error: no es pot crear fitxer de marca al directori');
INSERT INTO potranslation (id, translation) VALUES (131, 'Error: %s no és un directori
');
INSERT INTO potranslation (id, translation) VALUES (132, 'Error: el directori %s no és buit
');
INSERT INTO potranslation (id, translation) VALUES (133, 'Error: ''%s'' no és un número vàlid
');
INSERT INTO potranslation (id, translation) VALUES (134, 'Error intern: no s''ha pogut canviar a uid de superusuari efectiva');
INSERT INTO potranslation (id, translation) VALUES (135, 'Error intern: no s''ha pogut canviar uid d''usuari efectiva a identificació d''usuari real');
INSERT INTO potranslation (id, translation) VALUES (136, 'Error intern: no s''ha pogut canviar a gid superusuari efectiu');
INSERT INTO potranslation (id, translation) VALUES (137, 'Error intern: no s''ha pogut canviar l''identificació de grup efectiva a una identificació real de grup');
INSERT INTO potranslation (id, translation) VALUES (138, 'Bruk:

%s [valg] <enhet> [<etikett>]

  Monter <enhet> til en katalog under %s hvis krav er tilfredsstilt
  (se pmount(1) for mer). Hvis <etikett> er oppgitt, vil
  monteringspunktet bli %s/<etikett>, ellers vil det bli
  %s/<enhet>. Hvis monteringspunktet ikke finnes, vil det 
  bli opprettet.

');
INSERT INTO potranslation (id, translation) VALUES (139, '%s --lock <enhet> <pid>
  Forhindrer videre pmount-monteringer av <enhet> helt til den
  blir låst opp igjen. <pid> er hvilken prosess id låsen holdes
  for. Dette gjør det mulig å låse en enhet av flere uavhengige
  prosesser, og unngår uendelig låsing av krasjede prosesser
  (pids som ikke finnes blir ryddet før forsøk på en montering).
');
INSERT INTO potranslation (id, translation) VALUES (140, '%s --unlock <enhet> <pid>
  Fjerner låsen på <enhet> for prosess <pid>.

');
INSERT INTO potranslation (id, translation) VALUES (141, 'Valg:
  -a, --async : monterer <enhet> med «async»-valget (standard: «sync»)
  --noatime : monterer <enhet> med «noatime»-valget (standard: «atime»)
  -e, --exec : monterer <enhet> med «exec»-valget (standard: «noexec»)
  -t <fs> : monterer som filsystemtype <fs> (standard: velger automatisk)
  -c <tegnsett> : bruk gitt I/O-tegnsett (standard: utf8 i
                 UTF-8-locale, ellers monteringsstandard)
  -d, --debug : skriv debuginformasjon (veldig mye)
  -h, --help : skriv hjelpemelding og avslutt med suksess');
INSERT INTO potranslation (id, translation) VALUES (142, 'Feil: make_mountpoint_name: ugyldig enhet %s (må finnes i /dev/)
');
INSERT INTO potranslation (id, translation) VALUES (143, 'Feil: etiketten kan ikke være blank
');
INSERT INTO potranslation (id, translation) VALUES (144, 'Feil: Etiketten er for lang
');
INSERT INTO potranslation (id, translation) VALUES (145, 'Feil: Etiketter kan ikke inneholde «/»
');
INSERT INTO potranslation (id, translation) VALUES (146, 'Feil: Navnet på enheten er for langt
');
INSERT INTO potranslation (id, translation) VALUES (147, 'Feil: Kunne ikke fjerne alle uid-rettigheter');
INSERT INTO potranslation (id, translation) VALUES (148, 'Feil: Kunne ikke kjøre mount');
INSERT INTO potranslation (id, translation) VALUES (149, 'Intern feil: mount_attempt: Filsystemnavnet er NULL
');
INSERT INTO potranslation (id, translation) VALUES (150, 'Feil: Ugyldig filsystemnavn «%s»
');
INSERT INTO potranslation (id, translation) VALUES (151, 'Feil: Ugyldig tegnsettnavn «%s»
');
INSERT INTO potranslation (id, translation) VALUES (152, 'Feil: Kunne ikke øke til fullstendige root-uid-rettigheter');
INSERT INTO potranslation (id, translation) VALUES (153, 'Feil: Kunne ikke vente på startet mounting');
INSERT INTO potranslation (id, translation) VALUES (154, 'Feil: Kan ikke låse for %u, siden denne prosessen ikke finnes
');
INSERT INTO potranslation (id, translation) VALUES (155, 'Feil: Kunne ikke opprette pid-låsfil %s: %s
');
INSERT INTO potranslation (id, translation) VALUES (156, 'Feil: Kunne ikke fjerne pid-låsfil %s: %s
');
INSERT INTO potranslation (id, translation) VALUES (157, 'Feil: du_unlock: Kunne ikke fjerne låskatalog');
INSERT INTO potranslation (id, translation) VALUES (158, 'Feil: Dette programmet må være installert suid root
');
INSERT INTO potranslation (id, translation) VALUES (159, 'Intern feil: getopt_long() returnerte ukjent verdi
');
INSERT INTO potranslation (id, translation) VALUES (160, 'Advarsel: Enheten «%s» håndteres allerede i /etc/fstab, ny etikett blir ignorert
');
INSERT INTO potranslation (id, translation) VALUES (161, 'Feil: Kunne ikke bestemme den ordentlige stien for denne enheten');
INSERT INTO potranslation (id, translation) VALUES (162, 'Feil: Ugyldig enhet %s (må være i /dev/)
');
INSERT INTO potranslation (id, translation) VALUES (163, 'Feil: Kunne ikke slette monteringspunkt');
INSERT INTO potranslation (id, translation) VALUES (164, 'Intern feil: modus %i er blir ikke håndtert.
');
INSERT INTO potranslation (id, translation) VALUES (165, 'pmount-hal - kjør pmount med tilleggsinformasjon fra hal

Bruk: pmount-hal <hal UDI> [pmount-valg]

Denne kommandoen monterer enheten beskrevet av den oppgitte UDI-en ved bruk av «pmount». Filsystemtypen, volumlagringspolitikk og ønsket etikett vil bli lest ut fra «hal» og gitt til «pmount».');
INSERT INTO potranslation (id, translation) VALUES (166, 'Feil: Kunne ikke kjøre pmount
');
INSERT INTO potranslation (id, translation) VALUES (167, 'Feil: Kunne ikke koble til hal
');
INSERT INTO potranslation (id, translation) VALUES (168, 'Feil: Oppgitt UDI finnes ikke
');
INSERT INTO potranslation (id, translation) VALUES (169, 'Feil: Oppgitt UDI er ikke en monterbar enhet
');
INSERT INTO potranslation (id, translation) VALUES (170, 'Feil: Kunne ikke få status fra enhet');
INSERT INTO potranslation (id, translation) VALUES (171, 'Feil: Kunne ikke hente sysfs-katalog
');
INSERT INTO potranslation (id, translation) VALUES (172, 'Feil: Kunne ikke åpne <sysfs-katalog>/block/');
INSERT INTO potranslation (id, translation) VALUES (173, 'Feil: Kunne ikke åpne <sysfs-kat>/block/<enhet>/');
INSERT INTO potranslation (id, translation) VALUES (174, 'Feil: Enhet %s finnes ikke
');
INSERT INTO potranslation (id, translation) VALUES (175, 'Feil: %s er ikke en blokkenhet
');
INSERT INTO potranslation (id, translation) VALUES (176, 'Feil: Kunne ikke åpne fstab-fil');
INSERT INTO potranslation (id, translation) VALUES (177, 'Feil: Enheten «%s» er allerede montert på «%s»
');
INSERT INTO potranslation (id, translation) VALUES (178, 'Feil: Enheten «%s» er ikke montert
');
INSERT INTO potranslation (id, translation) VALUES (179, 'Feil: Enheten %s ble ikke montert av deg
');
INSERT INTO potranslation (id, translation) VALUES (180, 'Feil: Enheten «%s» kan ikke fjernes
');
INSERT INTO potranslation (id, translation) VALUES (181, 'Feil: Enheten «%s» er låst
');
INSERT INTO potranslation (id, translation) VALUES (182, 'Feil: Katalogen «%s» inneholder allerede et montert filsystem
');
INSERT INTO potranslation (id, translation) VALUES (183, 'Feil: Katalogen «%s» inneholder ikke et montert filsystem
');
INSERT INTO potranslation (id, translation) VALUES (184, 'Bruk

%s [valg] <enhet>
  Avmonter <enhet> fra en katalog under %s hvis krav er
  tilfredsstilt (se pumount(1) for mer). Monteringspunktkatalogen
  blir fjernet etterpå.

Valg:
  -l, --lazy : lat umount, se umount(8)
  -d, --debug :  skriv debuginformasjon (veldig mye)
  -h, --help : skriv hjelpemelding og avslutt med suksess
');
INSERT INTO potranslation (id, translation) VALUES (185, 'Intern feil: Kunne ikke bestemme monteringspunkt
');
INSERT INTO potranslation (id, translation) VALUES (186, 'Feil: Monteringspunktet «%s» er ikke under «%s»
');
INSERT INTO potranslation (id, translation) VALUES (187, 'Feil: Kunne ikke kjøre umount');
INSERT INTO potranslation (id, translation) VALUES (188, 'Feil: Kunne ikke vente på startet avmonteringsprosess');
INSERT INTO potranslation (id, translation) VALUES (189, 'Feil: Avmontering feilet
');
INSERT INTO potranslation (id, translation) VALUES (190, 'Feil: Ikke mer minne
');
INSERT INTO potranslation (id, translation) VALUES (191, 'Feil: Kunne ikke opprette katalog');
INSERT INTO potranslation (id, translation) VALUES (192, 'Feil: Kunne ikke opprette stempelfil i katalog');
INSERT INTO potranslation (id, translation) VALUES (193, 'Feil. «%s» er ikke en katalog
');
INSERT INTO potranslation (id, translation) VALUES (194, 'Feil: Kunne ikke åpne katalog');
INSERT INTO potranslation (id, translation) VALUES (195, 'Feil: Katalogen «%s» er ikke tom
');
INSERT INTO potranslation (id, translation) VALUES (196, 'Feil: «%s» er ikke et gyldig tall
');
INSERT INTO potranslation (id, translation) VALUES (197, 'Intern feil: Kunne ikke endre til effektiv uid root');
INSERT INTO potranslation (id, translation) VALUES (198, 'Intern feil: kunne ikke endre effektiv bruker-uid til ekte bruker-id');
INSERT INTO potranslation (id, translation) VALUES (199, 'Intern feil: Kunne ikke endre til effektiv gid root');
INSERT INTO potranslation (id, translation) VALUES (200, 'Intern feil: Kunne ikke endre effektiv gruppe-id til ekte grouppe-id');
INSERT INTO potranslation (id, translation) VALUES (201, 'Použití:

%s [volby]<zařízení>[<jméno>]

  Připojí <zařízení> do adresáře na %s jestliže má oprávnění
  (podívej do pmount(1) na podrobnosti). Jestliže je <jméno>
  zadáno,   připojovací bod bude %s/<jméno>, jinak to bude%s
  <zařízení>. Jestliže připojovací bod neexistuje, 
  bude vytvořen.
');
INSERT INTO potranslation (id, translation) VALUES (202, '%s --lock <zařízení><pid>
  Zabrání příštím pmounts <zařízení> dokud není znovu odemčeno.
  <pid> specifikuje id uzamykajícího procesu. To umožňuje zamknout
  zařízení několika nezávislými procesy a zabrání nekonečnému
  uzamčení havarovanými procesy (neexistující pid jsou smazány
  před mount)
');
INSERT INTO potranslation (id, translation) VALUES (203, '%s --unlock <device> <pid>
  Odstranit znovu zámek na <device> pro proces <pid>.

');
INSERT INTO potranslation (id, translation) VALUES (204, 'Volby:
  -a, --async : připojit <zařízení> s volbou ''async'' (výchozí je:''sync'')
  --noatime : připojit <zařízení> s volbou ''noatime'' (výchozí je:''atime'')
  -e, --exec : připojit <zařízení> s volbou ''exec'' (výchozí je: ''noexec'')
  -t <fs> : připojit jako souborový systém <fs> (výchozí: autodetected)
  -c <charset>: použít danou znakovou sadu (výchozí: ''utf8'' jestliže je
                v nějakém lokálním UTF-8 , jinak výchozí pro mount)
  -d, --debug : povolit ladící výstupy (mnoho hlášek)
  -h, --help : vypíše nápovědu a ukončí se ');
INSERT INTO potranslation (id, translation) VALUES (205, 'Chyba: make_mount_name: neplatné zařízení %s (musí být v /dev/)
');
INSERT INTO potranslation (id, translation) VALUES (206, 'Chyba: jméno nesmí být prázdné
');
INSERT INTO potranslation (id, translation) VALUES (207, 'Chyba: Příliš dlouhé jméno
');
INSERT INTO potranslation (id, translation) VALUES (208, 'Chyba:''/'' se nesmí vyskytovat ve jméně
');
INSERT INTO potranslation (id, translation) VALUES (209, 'Chyba: příliš dlouhé jméno zařízení
');
INSERT INTO potranslation (id, translation) VALUES (210, 'Chyba: nelze zapsat všechna uid oprávnění');
INSERT INTO potranslation (id, translation) VALUES (211, 'Chyba: nelze spustit mount');
INSERT INTO potranslation (id, translation) VALUES (212, 'Vnitřní chyba: mount_attempmt: předané jméno souboru je NULL
');
INSERT INTO potranslation (id, translation) VALUES (213, 'Chyba: špatné jméno souborového systému ''%s''
');
INSERT INTO potranslation (id, translation) VALUES (214, 'Chyba: špatné jméno znakové sady ''%s''
');
INSERT INTO potranslation (id, translation) VALUES (215, 'Chyba: nelze získat plná práva superuživatele');
INSERT INTO potranslation (id, translation) VALUES (216, 'Chyba: nelze čekat na spuštěný proces připojení');
INSERT INTO potranslation (id, translation) VALUES (217, 'Chyba: nelze zamknout pro pid %u, tento proces neexistuje
');
INSERT INTO potranslation (id, translation) VALUES (218, 'Chyba: nelze vytvořit pid zamykací soubor %s:%s
');
INSERT INTO potranslation (id, translation) VALUES (219, 'Chyba: nelze odstranit pid zamykací soubor %s: %s
');
INSERT INTO potranslation (id, translation) VALUES (220, 'Chyba: do_unlock: nelze odstranit uzamčení adresáře');
INSERT INTO potranslation (id, translation) VALUES (221, 'Chyba: tento program je potřeba instalovat jako root
');
INSERT INTO potranslation (id, translation) VALUES (222, 'Vnitřní chyba: getopt_long() vrátil neznámou hodnotu
');
INSERT INTO potranslation (id, translation) VALUES (223, 'Varování: zařízení %s je již řízeno s /etc/fstab, dodané jméno bude ignorováno
');
INSERT INTO potranslation (id, translation) VALUES (224, 'Chyba: nelze určit opravdovou cestu k zařízení');
INSERT INTO potranslation (id, translation) VALUES (225, 'Chyba: neplatné zařízení %s (musí být v /dev/)
');
INSERT INTO potranslation (id, translation) VALUES (226, 'Chyba: nelze smazat bod připojení');
INSERT INTO potranslation (id, translation) VALUES (227, 'Vnitřní chyba: mód %i není obsluhován.
');
INSERT INTO potranslation (id, translation) VALUES (228, 'pmount-hal - spusit pmount s přídavnými informacemi z halu

Užití: pmount-hal <hal UDI> [pmount volby]

Tento příkaz připojí zařízení popsané daným UDI používající pmount. Systém souborů, chování diskové jednotky and požadovaný název budou
přečteny z halu a zaslány pmountu.');
INSERT INTO potranslation (id, translation) VALUES (229, 'Chyba: nelze spusit pmount
');
INSERT INTO potranslation (id, translation) VALUES (230, 'Chyba: nelze se připojit na hal
');
INSERT INTO potranslation (id, translation) VALUES (231, 'Chyba: dané UDI neexistuje
');
INSERT INTO potranslation (id, translation) VALUES (232, 'Chyba: dané UDI neni připojitelné zařízení
');
INSERT INTO potranslation (id, translation) VALUES (233, 'Chyba: nelze zjistit stav zařízení');
INSERT INTO potranslation (id, translation) VALUES (234, 'Chyba: nelze získat sysfs adresář
');
INSERT INTO potranslation (id, translation) VALUES (235, 'Chyba: nelze otevřít <sysfs adresář>/block/');
INSERT INTO potranslation (id, translation) VALUES (236, 'Chyba: nelze otevřít <sysfs adresář>/block/<device>/');
INSERT INTO potranslation (id, translation) VALUES (237, 'Chyba: zařízení %s neexistuje
');
INSERT INTO potranslation (id, translation) VALUES (238, 'Chyba: %s není blokové zařízení
');
INSERT INTO potranslation (id, translation) VALUES (239, 'Chyba: nelze otevřít soubor fstab-type');
INSERT INTO potranslation (id, translation) VALUES (240, 'Chyba: zařízení %s je jíž připojeno na %s
');
INSERT INTO potranslation (id, translation) VALUES (241, 'Chyba: zařízení %s není připojeno
');
INSERT INTO potranslation (id, translation) VALUES (242, 'Chyba: zařízení %s nepřipojils ty
');
INSERT INTO potranslation (id, translation) VALUES (243, 'Chyba: zařízení %s není vyjímatelné
');
INSERT INTO potranslation (id, translation) VALUES (244, 'Chyba: zařízení %s je zamčeno
');
INSERT INTO potranslation (id, translation) VALUES (245, 'Chyba: adresář %s již obsahuje připojený souborový systém
');
INSERT INTO potranslation (id, translation) VALUES (246, 'Chyba: adresář %s neobsahuje připojený souborový systém
');
INSERT INTO potranslation (id, translation) VALUES (247, 'Použití:

%s [parametry] <zařízení>
  Odpojenit <zařízení> z adresáře pod %s jestliže 
  jsou nastavená požadovná práva (podrobnosti viz pumount(1)). 
  Adresář připojovacího bodu je poté odstraněn.

Parametry:
  -l, --lazy : odpojit líně, viz umount(8)
  -d, --debug : povolit ladící výstupy (velmi ukecané)
  -h, --help : vytiskne nápovědu a ukončí se
');
INSERT INTO potranslation (id, translation) VALUES (248, 'Vnitřní chyba: nelze určit bod připojení
');
INSERT INTO potranslation (id, translation) VALUES (249, 'Chyba: připojovací bod %s není pod %s
');
INSERT INTO potranslation (id, translation) VALUES (250, 'Chyba: nelze spustit umount');
INSERT INTO potranslation (id, translation) VALUES (251, 'Chyba: nelze čekat na spuštěný proces umount ');
INSERT INTO potranslation (id, translation) VALUES (252, 'Chyba: umount selhal
');
INSERT INTO potranslation (id, translation) VALUES (253, 'Chyba: nedostatek paměti
');
INSERT INTO potranslation (id, translation) VALUES (254, 'Chyba: nelze vytvořit adresář');
INSERT INTO potranslation (id, translation) VALUES (255, 'Chyba: nelze vytvořit soubor razítka v adresáři');
INSERT INTO potranslation (id, translation) VALUES (256, 'Chyba: %s není adresář
');
INSERT INTO potranslation (id, translation) VALUES (257, 'Chyba: nelze otevřít adresář');
INSERT INTO potranslation (id, translation) VALUES (258, 'Chyba: adresář %s není prázdný
');
INSERT INTO potranslation (id, translation) VALUES (259, 'Chyba: ''%s'' není platné číslo
');
INSERT INTO potranslation (id, translation) VALUES (260, 'Vnitřní chyba: nelze změnit úspěšně na uid roota');
INSERT INTO potranslation (id, translation) VALUES (261, 'Vnitřní chyba: nelze změnit skutečné uživatelské id na pravé uživatelské id');
INSERT INTO potranslation (id, translation) VALUES (262, 'Vnitřní chyba: nelze změnit na skutečné gid roota');
INSERT INTO potranslation (id, translation) VALUES (263, 'Vnitřní chyba: nelze změnit id skutečné skupiny na id pravé skupiny');
INSERT INTO potranslation (id, translation) VALUES (264, 'Uso:

%s [opciones] <dispositivo> [<etiqueta>]

  Monta el <dispositivo> en un directorio bajo %s si se cumplen los
  requisitos de seguridad (ver detalles en pmount(1)). Si se pone
  <etiqueta>, el punto de montaje será %s/<etiqueta>, si no, será
  %s<dispositivo>. Si el punto de montaje no existe, se creará.
');
INSERT INTO potranslation (id, translation) VALUES (265, '%s --lock <dispositivo> <pid>↵
  Previene posteriores montajes del <dispositivo> hasta que se desbloquee.
  <pid> especifica el id del proceso que pone el bloqueo. Esto permite
  bloquear un dispositivo a varios procesos independendientes evitando
  bloqueos indefinidos por procesos caídos (los pids inexistentes se
  limpian antes de intentar un montaje).
');
INSERT INTO potranslation (id, translation) VALUES (266, '%s --unlock <dispositivo> <pid>
  Quita el bloqueo del proceso <pid> al <dispositivo>.
');
INSERT INTO potranslation (id, translation) VALUES (267, 'Opciones:
  -a, --async : montar <dispositivo> con la opción ''async'' (por defecto: ''sync'')
  --noatime   : montar <dispositivo> con la opción ''noatime'' (por defecto: ''atime'')
  -e, --exec  : montar <dispositivo> con la opción ''exec'' (por defecto: ''noexec'')
  -t <fs>     : montar como sistema de ficheros tipo <fs> (por defecto: autodetectado)
  -c <charset>: usar el juego de caracteres E/S dado (por defecto: ''utf8'' si se llama
                en un local UTF-8, si no, el defecto de montaje)
  -d, --debug : habilita salida de depuración (muy verbosa)
  -h, --help  : escribir mensaje de ayuda y salir');
INSERT INTO potranslation (id, translation) VALUES (268, 'Error: make_mountpoint_name: el dispositivo %s no es válido (ha de estar en /dev/)
');
INSERT INTO potranslation (id, translation) VALUES (269, 'Error: la etiqueta no puede estar vacia
');
INSERT INTO potranslation (id, translation) VALUES (270, 'Error: etiqueta es demasiado larga
');
INSERT INTO potranslation (id, translation) VALUES (271, 'Error: no se puede poner ''/'' en el nombre de la etiqueta
');
INSERT INTO potranslation (id, translation) VALUES (272, 'Error: el nombre de dispositivo es demasiado largo
');
INSERT INTO potranslation (id, translation) VALUES (273, 'Error: no se han podido soltar todos los privilegios de uid');
INSERT INTO potranslation (id, translation) VALUES (274, 'Error: no se ha podido ejecutar el montaje');
INSERT INTO potranslation (id, translation) VALUES (275, 'Error interno: mount_attempt: el nombre del sistema de archivos dado es NULO
');
INSERT INTO potranslation (id, translation) VALUES (276, 'Error: el nombre del sistema de ficheros ''%s'' no es válido
');
INSERT INTO potranslation (id, translation) VALUES (277, 'Error: el nombre del juego de caracteres ''%s'' no es válido
');
INSERT INTO potranslation (id, translation) VALUES (278, 'Error: no se han podido alcanzar privilegios de uid root completos');
INSERT INTO potranslation (id, translation) VALUES (279, 'Error: no se ha podido esperar a que se ejecutara el proceso de montaje');
INSERT INTO potranslation (id, translation) VALUES (280, 'Error: no se puede bloquear para el pid %u, este proceso no existe
');
INSERT INTO potranslation (id, translation) VALUES (281, 'Error: no se ha podido crear el fichero de bloqueo del pid %s: %s
');
INSERT INTO potranslation (id, translation) VALUES (282, 'Error: no se ha podido eliminar el fichero de bloqueo del pid %s: %s
');
INSERT INTO potranslation (id, translation) VALUES (283, 'Error: do_unlock: no se ha podido eliminar el directorio de bloqueo');
INSERT INTO potranslation (id, translation) VALUES (284, 'Error este programa necesita ser instalado como super usuario (root)
');
INSERT INTO potranslation (id, translation) VALUES (285, 'Error interno: getopt_long() ha devuelto un valor desconocido
');
INSERT INTO potranslation (id, translation) VALUES (286, 'Aviso: el dispositivo %s ya se gestiona en /etc/fstab, la etiqueta proporcionada será ignorada
');
INSERT INTO potranslation (id, translation) VALUES (287, 'Error: no se ha podido determinar la ruta real del dispositivo');
INSERT INTO potranslation (id, translation) VALUES (288, 'Error: el dispositivo %s no vale (ha de estar en /dev/)
');
INSERT INTO potranslation (id, translation) VALUES (289, 'Error: no se ha podido borrar el punto de montaje');
INSERT INTO potranslation (id, translation) VALUES (290, 'Error interno: %i es un modo no gestionado.
');
INSERT INTO potranslation (id, translation) VALUES (291, 'pmount-hal - ejecutar pmount con información adicional de hal

Uso: pmount-hal <UDI hal> [opciones de pmount]

Esta orden monta el dispositivo descrito por el UDI dado usando pmount. El
tipo de sistema de ficheros, la política de almacenamiento del volumen y la etiqueta deseada se 
leerán de hal y se pasarán a pmount.');
INSERT INTO potranslation (id, translation) VALUES (292, 'Error: no se pudo ejecutar pmount
');
INSERT INTO potranslation (id, translation) VALUES (293, 'Error: no se ha podido abrir el directorio
');
INSERT INTO potranslation (id, translation) VALUES (294, 'Error: el UDI introducido no existe
');
INSERT INTO potranslation (id, translation) VALUES (295, 'Error: el UDI introducido no es un volúmen montable
');
INSERT INTO potranslation (id, translation) VALUES (296, 'Error: no se ha podido hallar el estado del dispositivo');
INSERT INTO potranslation (id, translation) VALUES (297, 'Error: no se ha podido hallar el directorio sysfs
');
INSERT INTO potranslation (id, translation) VALUES (298, 'Error: no se ha podido abrir <sysfs dir>/bloque/');
INSERT INTO potranslation (id, translation) VALUES (299, 'Error: no se ha podido abrir <sysfs dir>/bloque/<dispositivo>/');
INSERT INTO potranslation (id, translation) VALUES (300, 'Error: el dispositivo %s no existe
');
INSERT INTO potranslation (id, translation) VALUES (301, 'Error: %s no es dispositivo de bloques
');
INSERT INTO potranslation (id, translation) VALUES (302, 'Error: un fichero de tipo fstab no se ha podido abrir');
INSERT INTO potranslation (id, translation) VALUES (303, 'Error: el dispositivo %s ya está montado en %s
');
INSERT INTO potranslation (id, translation) VALUES (304, 'Error: el dispositivo %s no está montado
');
INSERT INTO potranslation (id, translation) VALUES (305, 'Error: el dispositivo %s no lo ha montado usted
');
INSERT INTO potranslation (id, translation) VALUES (306, 'Error: el dispositivo %s no es enchufable
');
INSERT INTO potranslation (id, translation) VALUES (307, 'Error: el dispositivo %s está bloqueado
');
INSERT INTO potranslation (id, translation) VALUES (308, 'Error: el directorio %s ya tiene montado un sistema de ficheros
');
INSERT INTO potranslation (id, translation) VALUES (309, 'Error: el directorio %s no tiene montado ningún sistema de ficheros
');
INSERT INTO potranslation (id, translation) VALUES (310, 'Uso:

%s [opciones] <dispositivo>
  Desmontar <dispositivo> de directorio bajo %s si se cumplen los requisitos
  de seguridad (ver detalles en pumount(1)). Después se elimina el directorio
  del punto de montaje.

Opciones:
  -l, --lazy : desmontaje laxo, ver umount(8)
  -d, --debug : permitir salida de depuración (muy verbosa)
  -h, --help : escribir mensaje de ayuda y salir bien
');
INSERT INTO potranslation (id, translation) VALUES (311, 'Error interno: no se ha podido determinar el punto de montaje
');
INSERT INTO potranslation (id, translation) VALUES (312, 'Error: el punto de montaje %s no está bajo %s
');
INSERT INTO potranslation (id, translation) VALUES (313, 'Error: no se ha podido ejecutar el desmontaje');
INSERT INTO potranslation (id, translation) VALUES (314, 'Error: no se ha podido esperar a que se ejecutara el proceso de desmontaje');
INSERT INTO potranslation (id, translation) VALUES (315, 'Error: desmontaje fallido
');
INSERT INTO potranslation (id, translation) VALUES (316, 'Error: memoria agotada
');
INSERT INTO potranslation (id, translation) VALUES (317, 'Error: no se ha podido crear el directorio');
INSERT INTO potranslation (id, translation) VALUES (318, 'Error: no se ha podido crear el fichero de fecha en el directorio');
INSERT INTO potranslation (id, translation) VALUES (319, 'Error: %s no es un directorio
');
INSERT INTO potranslation (id, translation) VALUES (320, 'Error: no se ha podido abrir el directorio');
INSERT INTO potranslation (id, translation) VALUES (321, 'Error: el directorio %s no está vacío
');
INSERT INTO potranslation (id, translation) VALUES (322, 'Error: ''%s'' no es un número válido
');
INSERT INTO potranslation (id, translation) VALUES (323, 'Error interno: no se ha podido cambiar a un uid efectivo de root');
INSERT INTO potranslation (id, translation) VALUES (324, 'Error interno: no se ha podido cambiar del uid del usuario efectivo al id del usuario real');
INSERT INTO potranslation (id, translation) VALUES (325, 'Error interno: no se ha podido cambiar a un gid efectivo de root');
INSERT INTO potranslation (id, translation) VALUES (326, 'Error interno: no se ha podido cambiar del id de grupo efectivo al id de grupo real');
INSERT INTO potranslation (id, translation) VALUES (327, 'Aufruf:

%s [Optionen] <Gerät> [<Label>]

  Bindet <Gerät> unter ein Verzeichnis in %s ein wenn die 
  Richtlinien dies erlauben (siehe pmount(1) für Details).
  Wenn <Label> gegeben ist, wird als Bindungsverzeichnis
  %s<Label> verwendet, ansonsten %s<Gerät>.
  Wenn dieses Verzeichnis nicht existiert, wird es erstellt.

');
INSERT INTO potranslation (id, translation) VALUES (328, '%s --lock <Gerät> <pid>
  Sperrt weitere pmount-Aufrufe für <Gerät> bis es wieder entsperrt
  wird. <pid> gibt die ID des Prozesses an, der die Sperre hält.  Dies
  ermöglicht das Sperren eines Gerätes von mehreren unabhängigen
  Prozessen und vermeidet unendliche Sperren von abgestürzten
  Prozessen (Sperren von nichtexistierenden Prozessen werden gelöscht
  bevor eine Einbindung versucht wird).

');
INSERT INTO potranslation (id, translation) VALUES (329, '%s --unlock <Gerät> <pid>
  Hebt die Sperre auf <Gerät> durch den Prozess <pid> wieder auf.

');
INSERT INTO potranslation (id, translation) VALUES (330, 'Optionen:
  -a, --async : Binde <Gerät> mit der Option ''async'' ein (Default: ''sync'')
  --noatime   : Binde <Gerät> mit der Option ''noatime'' ein (Default: ''atime'')
  -e, --exec  : Binde <Gerät> mit der Option ''exec'' ein (Default: ''noexec'')
  -t <fs>     : Verwende Dateisystem <fs> (Default: automatisch)
  -c <charset>: Verwende angegebenen Zeichensatz (Default: ''utf8'' in
                einer UTF-8 Umgebung, ansonsten mount-Default)
  -d, --debug : Debug-Ausgaben aktivieren (gibt sehr viel aus)
  -h, --help  : Hilfetext anzeigen und erfolgreich beenden');
INSERT INTO potranslation (id, translation) VALUES (331, 'Fehler: make_mountpoint_name: Ungültiges Gerät %s (muss in /dev/ sein)
');
INSERT INTO potranslation (id, translation) VALUES (332, 'Fehler: Label darf nicht leer sein
');
INSERT INTO potranslation (id, translation) VALUES (333, 'Fehler: Label ist zu lang
');
INSERT INTO potranslation (id, translation) VALUES (334, 'Fehler: Label darf nicht das Zeichen ''/'' enthalten
');
INSERT INTO potranslation (id, translation) VALUES (335, 'Fehler: Gerätname zu lang
');
INSERT INTO potranslation (id, translation) VALUES (336, 'Fehler: konnte nicht alle User-ID Privilegien aufgeben');
INSERT INTO potranslation (id, translation) VALUES (337, 'Fehler: konnte mount nicht ausführen');
INSERT INTO potranslation (id, translation) VALUES (338, 'Interner Fehler: mount_attempt: gegebener Dateisystem-Name ist NULL
');
INSERT INTO potranslation (id, translation) VALUES (339, 'Fehler: Ungültiges Dateisystem ''%s''
');
INSERT INTO potranslation (id, translation) VALUES (340, 'Fehler: ungültiger Zeichensatzname ''%s''
');
INSERT INTO potranslation (id, translation) VALUES (341, 'Fehler: konnte nicht zu vollen root-UID-Privilegien wechseln');
INSERT INTO potranslation (id, translation) VALUES (342, 'Fehler: konnte nicht auf ausgeführten mount-Prozess warten');
INSERT INTO potranslation (id, translation) VALUES (343, 'Fehler: kann nicht für PID %u sperren, dieser Prozess existiert nicht
');
INSERT INTO potranslation (id, translation) VALUES (344, 'Fehler: konnte PID-Lock-Datei %s nicht anlegen: %s
');
INSERT INTO potranslation (id, translation) VALUES (345, 'Fehler: konnte PID-Lock-Datei %s nicht löschen: %s
');
INSERT INTO potranslation (id, translation) VALUES (346, 'Fehler: do_unlock: konnte Lock-Verzeichnis nicht entfernen');
INSERT INTO potranslation (id, translation) VALUES (347, 'Fehler: Dieses programm muss als setuid root installiert sein
');
INSERT INTO potranslation (id, translation) VALUES (348, 'Interner Fehler: getopt_long() lieferte unbekannten Wert zurück
');
INSERT INTO potranslation (id, translation) VALUES (349, 'Warnung: Gerät %s wird schon in /etc/fstab verwaltet, angegebenes Label wird ignoriert
');
INSERT INTO potranslation (id, translation) VALUES (350, 'Error: konnte echten Pfad des Gerätes nicht bestimmen');
INSERT INTO potranslation (id, translation) VALUES (351, 'Fehler: ungültiges Gerät %s (muss in /dev/ sein)
');
INSERT INTO potranslation (id, translation) VALUES (352, 'Fehler: konnte Mount-Verzeichnis nicht löschen');
INSERT INTO potranslation (id, translation) VALUES (353, 'Interner Fehler: Modus %i nicht behandelt.
');
INSERT INTO potranslation (id, translation) VALUES (354, 'pmount-hal - führt pmount mit zusätzlichen Informationen von HAL aus

Aufruf: pmount-hal <hal UDI> [zusätzliche pmount-Optionen]

Dieser Befehl bindet das durch den hal-UDI spezifierte Gerät mit 
pmount ein. Der Dateisystem-Typ, verschiedene Mount-Optionen und 
der bevorzugte Name werden von hal gelesen und pmount als Optionen 
überreicht.');
INSERT INTO potranslation (id, translation) VALUES (355, 'Fehler: konnte pmount nicht ausführen
');
INSERT INTO potranslation (id, translation) VALUES (356, 'Fehler: konnte nicht zu hal verbinden
');
INSERT INTO potranslation (id, translation) VALUES (357, 'Fehler: angegebene UDI existiert nicht
');
INSERT INTO potranslation (id, translation) VALUES (358, 'Fehler: angegebene UDI ist kein einbindbares Gerät
');
INSERT INTO potranslation (id, translation) VALUES (359, 'Fehler: Konnte Status des Gerätes nicht bestimmen');
INSERT INTO potranslation (id, translation) VALUES (360, 'Fehler: konnte sysfs-Verzeichnis nicht erfragen
');
INSERT INTO potranslation (id, translation) VALUES (361, 'Fehler: konnte Verzeichnis <sysfs>/block/ nicht öffnen');
INSERT INTO potranslation (id, translation) VALUES (362, 'Fehler: konnte Verzeichnis <sysfs>/block/<Gerät> nicht öffnen');
INSERT INTO potranslation (id, translation) VALUES (363, 'Fehler: Verzeichnis %s existiert nicht
');
INSERT INTO potranslation (id, translation) VALUES (364, 'Fehler: %s ist kein Block-Gerät
');
INSERT INTO potranslation (id, translation) VALUES (365, 'Fehler: konnte fstab-artige Datei nicht öffnen');
INSERT INTO potranslation (id, translation) VALUES (366, 'Fehler: Gerät %s ist schon in %s eingebunden
');
INSERT INTO potranslation (id, translation) VALUES (367, 'Fehler: Gerät %s ist nicht eingebunden
');
INSERT INTO potranslation (id, translation) VALUES (368, 'Fehler: Gerät %s wurde nicht von Ihnen eingebunden
');
INSERT INTO potranslation (id, translation) VALUES (369, 'Fehler: Gerät %s ist kein Wechseldatenträger
');
INSERT INTO potranslation (id, translation) VALUES (370, 'Fehler: Gerät %s ist gesperrt
');
INSERT INTO potranslation (id, translation) VALUES (371, 'Fehler: Verzeichnis %s enthält schon ein eingebundenes Dateisystem
');
INSERT INTO potranslation (id, translation) VALUES (372, 'Fehler: Verzeichnis %s enthält kein eingebundenes Dateisystem
');
INSERT INTO potranslation (id, translation) VALUES (373, 'Aufruf:

%s [Optionen] <Gerät>
  Löse Bindung von <Gerät> von einem Verzeichnis unter %s wenn die
  Richtlinien dies erlauben (siehe pumount(1) für Details). Das
  Bindungsverzeichnis wird danach gelöscht.

Optionen:
  -l, --lazy : "lazy" unmount, siehe umount(8)
  -d, --debug : Debug-Ausgaben aktivieren (gibt sehr viel aus)
  -h, --help  : Hilfetext anzeigen und erfolgreich beenden
');
INSERT INTO potranslation (id, translation) VALUES (374, 'Interner Fehler: Konnte Bindungsverzeichnis nicht bestimmen
');
INSERT INTO potranslation (id, translation) VALUES (375, 'Fehler: Bindungsverzeichnis %s ist nicht unter %s
');
INSERT INTO potranslation (id, translation) VALUES (376, 'Fehler: Konnte unmount nicht ausführen');
INSERT INTO potranslation (id, translation) VALUES (377, 'Fehler: Konnte nicht auf ausgeführten umount-Prozess warten');
INSERT INTO potranslation (id, translation) VALUES (378, 'Fehler: umount fehlgeschlagen
');
INSERT INTO potranslation (id, translation) VALUES (379, 'Fehler: Speicher voll
');
INSERT INTO potranslation (id, translation) VALUES (380, 'Fehler: konnte Verzeichnis nicht anlegen');
INSERT INTO potranslation (id, translation) VALUES (381, 'Fehler: konnte Markierungs-Datei in Verzeichnis nicht anlegen');
INSERT INTO potranslation (id, translation) VALUES (382, 'Fehler: %s ist kein Verzeichnis
');
INSERT INTO potranslation (id, translation) VALUES (383, 'Fehler: konnte Verzeichnis nicht öffnen');
INSERT INTO potranslation (id, translation) VALUES (384, 'Fehler: Verzeichnis %s ist nicht leer
');
INSERT INTO potranslation (id, translation) VALUES (385, 'Fehler: ''%s'' ist keine gültige Zahl
');
INSERT INTO potranslation (id, translation) VALUES (386, 'Interner Fehler: konnte nicht zur effektiven UID von root wechseln');
INSERT INTO potranslation (id, translation) VALUES (387, 'Interner Fehler: konnte effektive Benutzer-UID nicht zu realer Benutzer-UID wechseln');
INSERT INTO potranslation (id, translation) VALUES (388, 'Interner Fehler: konnte nicht zur effektiven GID von root wechseln');
INSERT INTO potranslation (id, translation) VALUES (389, 'Interner Fehler: konnte effektive Benutzer-GID nicht zu realer Benutzer-GID wechseln');
INSERT INTO potranslation (id, translation) VALUES (390, 'Usage:

%s [options] <périphérique> [<label>]

  Monte le <périphérique> sur un répertoire sous %s si les contraintes
  sont satisfaites (voir pmount(1)). Si <label> est précisé, le point
  de montage sera %s/<label>, autrement ce sera %s<périphérique>.
  Si le point de montage n''existe pas, il sera créé.

');
INSERT INTO potranslation (id, translation) VALUES (391, '%s --lock <périphérique> <pid>
  Empèche tout p-montage du <périphérique> jusqu''à ce qu''il
  soit déverrouillé. <pid> indique le numéro de processus pour
  lequel le verrou est pris. Ceci permet de verrouiller un
  périphérique pour plusieurs processus indépendants et évite
  de créer des verrouillage indéfinis pour des processus qui
  ont échoué (les pids inexistants sont nettoyés avant de
  tenter un montage).

');
INSERT INTO potranslation (id, translation) VALUES (392, '%s --unlock <périphérique> <pid>
  Retire le verrou sur le <périphérique> pour le processus <pid>.
');
INSERT INTO potranslation (id, translation) VALUES (393, 'Options:
  -a, --async : monte le <périphérique> avec l''option ''async'' (par défaut: ''sync'')
  -noatime : monte le <périphérique> avec l''option ''noatime'' (par défaut: ''atime'')
  -e, --exec : monte le <périphérique> avec l''option ''exec'' (par défaut: ''noexec'')
  -t <fs> : monte le système de fichier de type <fs> (par défaut: autodétecté)
  -c <charset>: utilise le jeu de caractères <charset> pour les Entrées/Sorties
                (par défaut: ''utf8'' si la locale est une locale UTF-8, autrement celui par défaut de mount)
  -d, --debug : active l''affichage de débogage (très verbeux)
  -h, --help : affiche ce message d''aide et terminer avec succès');
INSERT INTO potranslation (id, translation) VALUES (394, 'Erreur : make_mountpoint_name: périphérique invalide %s (il doit être dans /dev/)
');
INSERT INTO potranslation (id, translation) VALUES (395, 'Erreur : l''étiquette ne peut pas être vide
');
INSERT INTO potranslation (id, translation) VALUES (396, 'Erreur : label trop long
');
INSERT INTO potranslation (id, translation) VALUES (397, 'Erreur : ''/'' ne doit pas apparaitre dans un nom de label
');
INSERT INTO potranslation (id, translation) VALUES (398, 'Erreur : nom du périphérique trop long
');
INSERT INTO potranslation (id, translation) VALUES (399, 'Erreur : impossible de révoquer tous les privilèges');
INSERT INTO potranslation (id, translation) VALUES (400, 'Erreur : impossible d''exécuter mount');
INSERT INTO potranslation (id, translation) VALUES (401, 'Erreur interne : mount_attempt : le nom du système de fichiers est NULL
');
INSERT INTO potranslation (id, translation) VALUES (402, 'Erreur : nom de système de fichiers invalide ''%s''
');
INSERT INTO potranslation (id, translation) VALUES (403, 'Erreur : nom de jeu de caractères invalide ''%s''
');
INSERT INTO potranslation (id, translation) VALUES (404, 'Erreur : impossible d''obtenir les privilèges complets de l''uid root');
INSERT INTO potranslation (id, translation) VALUES (405, 'Erreur : impossible d''attendre pour exécuter les processus de montage');
INSERT INTO potranslation (id, translation) VALUES (406, 'Erreur : ne peut pas verrouiller pour le pid %u, ce processus n''existe pas
');
INSERT INTO potranslation (id, translation) VALUES (407, 'Erreur : ne peut créer le fichier de verrou de pid  %s: %s
');
INSERT INTO potranslation (id, translation) VALUES (408, 'Erreur : ne peut ôter le fichier de verrou pid %s:%s
');
INSERT INTO potranslation (id, translation) VALUES (409, 'Erreur : do_unlock: ne peut ôter le verrou du répertoire');
INSERT INTO potranslation (id, translation) VALUES (410, 'Erreur : ce programme a besoin d''être installé en suid root
');
INSERT INTO potranslation (id, translation) VALUES (411, 'Erreur interne : getopt_long() a retourné une valeur inconnue
');
INSERT INTO potranslation (id, translation) VALUES (412, 'Avertissement : le périphérique %s est déjà pris en charge par /etc/fstab, l''étiquette fournie est ignorée
');
INSERT INTO potranslation (id, translation) VALUES (413, 'Erreur : n''a pas pu déterminer le véritable chemin d''accès à ce périphérique');
INSERT INTO potranslation (id, translation) VALUES (414, 'Erreur : périphérique invalide %s (doit être dans /dev/)
');
INSERT INTO potranslation (id, translation) VALUES (415, 'Erreur : n''a pas pu détruire le point de montage');
INSERT INTO potranslation (id, translation) VALUES (416, 'Erreur interne : le mode %i n''est pas pris en charge.
');
INSERT INTO potranslation (id, translation) VALUES (417, 'pmount-hal - execute pmount avec les informations supplémentaires provenant du hal

Usage: pmount-hal <hal UDI> [options pmount]

Cette commande monte le périphérique décrit par l''UDI fourni en utilisant pmount. Le
type du système de fichiers, les contraintes de stockage du volume et l''étiquette désirée
seront extraites du hal et passés à pmount.');
INSERT INTO potranslation (id, translation) VALUES (418, 'Erreur: impossible d''exécuter pmount
');
INSERT INTO potranslation (id, translation) VALUES (419, 'Erreur : impossible de se connecter à hal
');
INSERT INTO potranslation (id, translation) VALUES (420, 'Erreur : l''UDI fourni n''existe pas
');
INSERT INTO potranslation (id, translation) VALUES (421, 'Erreur : L''UDI fourni n''est pas un volume montable
');
INSERT INTO potranslation (id, translation) VALUES (422, 'Erreur : n''a pas pu obtenir l''état du périphérique');
INSERT INTO potranslation (id, translation) VALUES (423, 'Erreur : n''a pas trouver le répertoire sysfs
');
INSERT INTO potranslation (id, translation) VALUES (424, 'Erreur : n''a pas pu ouvrir <sysfs dir>/block/');
INSERT INTO potranslation (id, translation) VALUES (425, 'Erreur : n''a pas pu ouvrir <sysfs dir>/block/<device>/');
INSERT INTO potranslation (id, translation) VALUES (426, 'Erreur : le périphérique %s n''existe pas
');
INSERT INTO potranslation (id, translation) VALUES (427, 'Erreur : %s n''est pas un périphérique de bloc
');
INSERT INTO potranslation (id, translation) VALUES (428, 'Erreur : n''a pas  pu ouvrir le fichier fstab-type');
INSERT INTO potranslation (id, translation) VALUES (429, 'Erreur : le périphérique %s est déja monté sur %s
');
INSERT INTO potranslation (id, translation) VALUES (430, 'Erreur : le périphérique %s n''est pas monté
');
INSERT INTO potranslation (id, translation) VALUES (431, 'Erreur : le périphérique %s n''a pas été monté par vous
');
INSERT INTO potranslation (id, translation) VALUES (432, 'Erreur : le périphérique %s n''est pas amovible');
INSERT INTO potranslation (id, translation) VALUES (433, 'Erreur : le périphérique %s est vérrouillé
');
INSERT INTO potranslation (id, translation) VALUES (434, 'Erreur : le répertoire %s contient déja un système de fichiers
');
INSERT INTO potranslation (id, translation) VALUES (435, 'Erreur : le répertoire %s ne contient pas de systême de fichiers monté
');
INSERT INTO potranslation (id, translation) VALUES (436, 'Utilisation :

%s [options] <périphérique>
  Démonte le <périphérique> du répertoire suivant %s si les droits sont
  satisfaient ( voir pumount(1) pour les détails). Le répertoire du
  point de montage est supprimé après l''opération.

Options:↵
  -l, --lazy : démontage paresseux, voir umount(8)
  -d, --debug : autorise l''affichage des messages de debug (très verbeux)
  -h, --help : affiche ce message d''aide et termine avec succès
');
INSERT INTO potranslation (id, translation) VALUES (437, 'Erreur interne : n''a pas pu déterminer le point de montage
');
INSERT INTO potranslation (id, translation) VALUES (438, 'Erreur : le point de montage %s n''est pas sous %s
');
INSERT INTO potranslation (id, translation) VALUES (439, 'Erreur : n''a pas pu exécuter umount');
INSERT INTO potranslation (id, translation) VALUES (440, 'Erreur : n''a pas pu attendre pour exécuter le processus de démontage');
INSERT INTO potranslation (id, translation) VALUES (441, 'Erreur : échec de umount
');
INSERT INTO potranslation (id, translation) VALUES (442, 'Erreur : plus de mémoire disponible
');
INSERT INTO potranslation (id, translation) VALUES (443, 'Erreur : n''a pas pu créer de répertoire');
INSERT INTO potranslation (id, translation) VALUES (444, 'Erreur : n''a pas pu créer un fichier estampillé dans le répertoire');
INSERT INTO potranslation (id, translation) VALUES (445, 'Erreur : %s n''est pas un répertoire
');
INSERT INTO potranslation (id, translation) VALUES (446, 'Erreur : ne peut pas ouvrir le répertoire');
INSERT INTO potranslation (id, translation) VALUES (447, 'Erreur : le répertoire %s n''est pas vide
');
INSERT INTO potranslation (id, translation) VALUES (448, 'Erreur : ''%s'' n''est pas un nombre valide
');
INSERT INTO potranslation (id, translation) VALUES (449, 'Erreur interne : n''a pas pu changer pour l''uid effectif de root ');
INSERT INTO potranslation (id, translation) VALUES (450, 'Erreur interne : n''a pas pu changer de l''uid effectif pour le véritable id de l''utilisateur');
INSERT INTO potranslation (id, translation) VALUES (451, 'Erreur interne : n''a pas pu changer pour le gid effectif de root');
INSERT INTO potranslation (id, translation) VALUES (452, 'Erreur interne : n''a pas pu changer de l''id effectif de groupe pour le véritable id du groupe');
INSERT INTO potranslation (id, translation) VALUES (453, 'Utilizzo:

%s [opzioni] <dispositivo> [<etichetta>]

  Monta il <dispositivo> in una directory sotto %s se i requisiti 
  sono rispettati (vedere pmount(1) per dettagli). Se è data <etichetta>,
  il punto di mount sarà %s/<etichetta>, altrimenti %s<dispositivo>.
  Se il punto di mount non esiste verrà creato.



  

');
INSERT INTO potranslation (id, translation) VALUES (454, '%s --lock <dispositivo> <pid>
  Impedisce ulteriori pmount di <dispositivo> finché questo non è sbloccato
  di nuovo. <pid> specifica l''id del processo che detiene il lock. Questo
  permette a diversi processi indipendenti di fare il lock ad un dispositivo
  ed evita lock illimitati da parte di processi andati in crash (id di processi
  non esistenti sono ripuliti prima di tentare un mount).
');
INSERT INTO potranslation (id, translation) VALUES (455, '%s --unlock <dispsitivo> <pid>
  Rimuove il lock sul <dispositivo> per il processo <pid>.

');
INSERT INTO potranslation (id, translation) VALUES (456, 'Opzioni:
  --a, --async: monta <dispositivo> con l''opzione ''async'' (predefinito: ''sync)
  --noatime: monta <dispositivo> con l''opzione ''noatime'' (predefinito: ''atime'')
  -e, --exec: monta <dispositivo> con l''opzione ''exec'' (predefinito: ''noexec'')
  -t <fs>: monta come un file system di tipo <fs> (predefinito: rilevato
           automaticamente)
  -c <charset>: usa il set di caratteri di I/O fornito (predefinito: ''utf8'' se
                invocato in una locale UTF-8, altrimenti il predefinito di mount)
  -d, --debug: abilita l''output di debug (molto prolisso)
  -h, --help: stampa il messaggio di aiuto ed esce con successo');
INSERT INTO potranslation (id, translation) VALUES (457, 'Errore: make_mountpoint_name: dispositivo %s non valido (deve essere in /dev/)
');
INSERT INTO potranslation (id, translation) VALUES (458, 'Errore: l''etichetta non deve essere vuota
');
INSERT INTO potranslation (id, translation) VALUES (459, 'Errore: etichetta troppo lunga
');
INSERT INTO potranslation (id, translation) VALUES (460, 'Errore: ''/'' non deve comparire nell''etichetta
');
INSERT INTO potranslation (id, translation) VALUES (461, 'Errore: nome del dispositivo troppo lungo
');
INSERT INTO potranslation (id, translation) VALUES (462, 'Errore: impossibile eseguire mount');
INSERT INTO potranslation (id, translation) VALUES (463, 'Errore interno: mount_attempt: il tipo di file system dato è NULL
');
INSERT INTO potranslation (id, translation) VALUES (464, 'Errore: file system ''%s'' non valido
');
INSERT INTO potranslation (id, translation) VALUES (465, 'Errore: set di caratteri ''%s'' non valido
');
INSERT INTO potranslation (id, translation) VALUES (466, 'Errore: impossibile fare il lock per il pid %u, il processo non esiste
');
INSERT INTO potranslation (id, translation) VALUES (467, 'Errore: questo programma deve essere installato con i permessi di root
');
INSERT INTO potranslation (id, translation) VALUES (468, 'Errore interno: getopt_long() ha restituito un valore sconosciuto
');
INSERT INTO potranslation (id, translation) VALUES (469, 'Attenzione: il dispositivo %s è già gestito da /etc/fstab,
l''etichetta fornita verrà ignorata
');
INSERT INTO potranslation (id, translation) VALUES (470, 'Errore: impossibile determinare il percorso effettivo del dispositivo');
INSERT INTO potranslation (id, translation) VALUES (471, 'Errore: dispositivo %s non valido (deve trovarsi in /dev)
');
INSERT INTO potranslation (id, translation) VALUES (472, 'Errore: impossibile cancellare il punto di mount');
INSERT INTO potranslation (id, translation) VALUES (473, 'pmount-hal - esegue pmount con informazioni aggiuntive provenienti da hal

Utilizzo: pmount-hal <hal UDI> [opzioni di pmount]

Questo comando monta il dispositivo descritto dallo UDI fornito utilizzando
pmount. Il tipo di file system, la politica di memorizzazione del volume e
l''etichetta richiesta saranno estratti da hal e passati a pmount.');
INSERT INTO potranslation (id, translation) VALUES (474, 'Errore: impossibile eseguire pmount
');
INSERT INTO potranslation (id, translation) VALUES (475, 'Errore: impossibile eseguire la connessione ad hal
');
INSERT INTO potranslation (id, translation) VALUES (476, 'Errore: lo UDI fornito non esiste
');
INSERT INTO potranslation (id, translation) VALUES (477, 'Errore: lo UDI fornito non è un volume montabile
');
INSERT INTO potranslation (id, translation) VALUES (478, 'Errore: impossibile ottenere lo stato del dispositivo');
INSERT INTO potranslation (id, translation) VALUES (479, 'Errore: impossibile ottenere la directory sysfs
');
INSERT INTO potranslation (id, translation) VALUES (480, 'Errore: impossibile aprire <sysfs dir>/blobk/');
INSERT INTO potranslation (id, translation) VALUES (481, 'Errore: impossibile aprire <sysfs dir>/block/<dispositivo>/');
INSERT INTO potranslation (id, translation) VALUES (482, 'Errore: il dispositivo %s non esiste
');
INSERT INTO potranslation (id, translation) VALUES (483, 'Errore: %s non è un dispositivo a blocchi
');
INSERT INTO potranslation (id, translation) VALUES (484, 'Errore: il dispositivo %s è già montato in %s
');
INSERT INTO potranslation (id, translation) VALUES (485, 'Errore: il dispositivo %s non è montato
');
INSERT INTO potranslation (id, translation) VALUES (486, 'Errore: il dispositivo %s è stato montato da un altro utente
');
INSERT INTO potranslation (id, translation) VALUES (487, 'Errore: il dispositivo %s non è rimovibile
');
INSERT INTO potranslation (id, translation) VALUES (488, 'Errore: il dispositivo %s è in stato di lock
');
INSERT INTO potranslation (id, translation) VALUES (489, 'Errore: la directory %s contiene già un file system montato
');
INSERT INTO potranslation (id, translation) VALUES (490, 'Errore: la directory %s non contiene un file system montato
');
INSERT INTO potranslation (id, translation) VALUES (491, 'Utilizzo:

%s [opzioni] <dispositivo>
  Smonta il <dispositivo> da una directory sotto %s se i requisiti
  sono rispettati (vedere pumount(1) per i dettagli). La directory del
  punto di mount è rimossa successivamente.

Opzioni:
  -l, --lazy: smonta "pigramente", vedere umount(8)
  -d, --debug: abilita l''output di debug (molto prolisso)
  -h, --help: stampa il messaggio di aiuto ed esce con successo
');
INSERT INTO potranslation (id, translation) VALUES (492, 'Errore interno: impossibile determinare il punto di mount
');
INSERT INTO potranslation (id, translation) VALUES (493, 'Errore: il punto di mount %s non si trova sotto %s
');
INSERT INTO potranslation (id, translation) VALUES (494, 'Errore: impossibile eseguire umount');
INSERT INTO potranslation (id, translation) VALUES (495, 'Errore: umount fallito
');
INSERT INTO potranslation (id, translation) VALUES (496, 'Errore: memoria esaurita
');
INSERT INTO potranslation (id, translation) VALUES (497, 'Errore: impossibile creare la directory');
INSERT INTO potranslation (id, translation) VALUES (498, 'Errore: %s non è una directory
');
INSERT INTO potranslation (id, translation) VALUES (499, 'Errore: impossibile aprire la directory');
INSERT INTO potranslation (id, translation) VALUES (500, 'Errore: la directory %s non è vuota
');
INSERT INTO potranslation (id, translation) VALUES (501, 'Errore: ''%s'' non è un numero valido
');
INSERT INTO potranslation (id, translation) VALUES (502, 'Error: el nombre del juego de caracteres ''%s'' no es válido

');
INSERT INTO potranslation (id, translation) VALUES (503, 'Error interno: getopt_long() retornó un valor desconocido
');
INSERT INTO potranslation (id, translation) VALUES (504, 'ADVERTENCIA: el dispositivo %s está actualmente manejado por /etc/fstab, la etiqueta proporcionada se ha ignorado
');
INSERT INTO potranslation (id, translation) VALUES (505, 'Error: no es posible determinar la ubicación real del dispositivo');
INSERT INTO potranslation (id, translation) VALUES (506, 'Error: el dispositivo %s es invalido (debe estar en /dev/)
');
INSERT INTO potranslation (id, translation) VALUES (507, 'Error: no es posible borrar el punto de montaje');
INSERT INTO potranslation (id, translation) VALUES (508, 'Error interno: %i del modo, no manejado.
');
INSERT INTO potranslation (id, translation) VALUES (509, 'Error: no se pudo concectar con hal
');
INSERT INTO potranslation (id, translation) VALUES (510, 'Error: no es posible alcanzar el estado del dispositivo');
INSERT INTO potranslation (id, translation) VALUES (511, 'Error: no es posible alcanzar el directorio sysfs
');
INSERT INTO potranslation (id, translation) VALUES (512, 'Error: no se puede abrir <sysfs dir>/block/');
INSERT INTO potranslation (id, translation) VALUES (513, 'Error no se puede abrir <sysfs dir>/block/<device>/');
INSERT INTO potranslation (id, translation) VALUES (514, 'Error: no existe el dispositivo %s
');
INSERT INTO potranslation (id, translation) VALUES (515, 'Error: %s noes un dispositivo bloqueado
');
INSERT INTO potranslation (id, translation) VALUES (516, 'Error: no es posible abrir el archivo fstab-type');
INSERT INTO potranslation (id, translation) VALUES (517, 'Error: el dispositivo %s ya está montado como %s
');
INSERT INTO potranslation (id, translation) VALUES (518, 'Error: el dispositivo %s no fue montado por usted
');
INSERT INTO potranslation (id, translation) VALUES (519, 'Error: el dispositivo %s no es removible
');
INSERT INTO potranslation (id, translation) VALUES (520, 'Error: el directorio %s todavía tiene montado un sistema de archivos
');
INSERT INTO potranslation (id, translation) VALUES (521, 'Error: el directorio %s no tiene sistemas de archivos montados
');
INSERT INTO potranslation (id, translation) VALUES (522, 'Uso:

%s [opciones] <dispositivo>
  Desmonta <dispositivo> desde un directorio inferior a %s si se ajusta
  a los requerimientos de las politicas (ver pumount(1) para detalles).
  Luego, se remueve el directorio del punto de montaje.

Opciones:
  -l, --lazy: desmonta lentamente, ver umount(8)
  -d, --debug: activa la depuración (MUY PROLIJA)
  -h, --help: muestra esta pantalla y sale
');
INSERT INTO potranslation (id, translation) VALUES (523, 'Error interno: no esposible determinar el punto de montaje
');
INSERT INTO potranslation (id, translation) VALUES (524, 'Error: el punto de montaje %s no está debajo de %s
');
INSERT INTO potranslation (id, translation) VALUES (525, 'Error: no es posible ejecutar umount');
INSERT INTO potranslation (id, translation) VALUES (526, 'Error: no es posible esperar por el proceso umount ejecutado');
INSERT INTO potranslation (id, translation) VALUES (527, 'Error: umount fallido
');
INSERT INTO potranslation (id, translation) VALUES (528, 'Error: sin memoria
');
INSERT INTO potranslation (id, translation) VALUES (529, 'Error: no es posible crear el directorio');
INSERT INTO potranslation (id, translation) VALUES (530, 'Error:  no es posible crear el ''archivo stamp'' en el directorio');
INSERT INTO potranslation (id, translation) VALUES (531, 'Error: no es posible abrir el directorio');
INSERT INTO potranslation (id, translation) VALUES (532, 'Error interno: no es posible cambiar a root uid');
INSERT INTO potranslation (id, translation) VALUES (533, 'Error interno: no es posible cambiar desde el uid de usuario a id real de usuario');
INSERT INTO potranslation (id, translation) VALUES (534, 'Error interno: no es posible cambiar a root gid');
INSERT INTO potranslation (id, translation) VALUES (535, 'Error interno: no es posible cambiar desde gid al gid real');
INSERT INTO potranslation (id, translation) VALUES (536, 'Les paramètres globaux peuvent être modifiés dans /etc/mozilla/prefs.js');
INSERT INTO potranslation (id, translation) VALUES (537, 'La version de Mozilla dans Debian charge le fichier /etc/mozilla/prefs.js après d''autres scripts de configuration.');
INSERT INTO potranslation (id, translation) VALUES (538, 'Vous pouvez modifier dans ce fichier les paramètres globaux (p. ex. les paramètres concernant les polices).');
INSERT INTO potranslation (id, translation) VALUES (539, 'Automatique, esddsp (pour GNOME), artsdsp (pour KDE), Aucun');
INSERT INTO potranslation (id, translation) VALUES (540, 'Module d''encapsulation du serveur de son :');
INSERT INTO potranslation (id, translation) VALUES (541, 'Il arrive que Mozilla soit bloqué parce que certains greffons (« plugins ») -- p. ex. Flash -- verrouillent le périphérique audio /dev/dsp. Il est possible d''encapsuler l''accès au périphérique /dev/dsp pour résoudre ce problème.  « Automatique » sélectionne un module d''encapsulation du dsp en fonction du serveur de son en cours d''exécution. Si aucun gestionnaire de son n''est détecté, Mozilla n''utilisera aucun module d''encapsulation. Ce choix sera sauvegardé dans /etc/mozilla/mozillarc et pourra être modifié dans votre fichier ~/.mozillarc.');
INSERT INTO potranslation (id, translation) VALUES (542, 'Faut-il activer la sélection automatique de la langue/région ?');
INSERT INTO potranslation (id, translation) VALUES (543, 'Ce réglage permet de choisir automatiquement les extensions de langue et de région en fonction des paramètres régionaux de l''utilisateur. Il facilitera la tâche d''un administrateur système qui travaille pour de nombreux utilisateurs peu expérimentés qui ne parlent pas l''anglais.');
INSERT INTO potranslation (id, translation) VALUES (544, 'Pour que la configuration automatique fonctionne, il faut que les variables d''environnement LC_MESSAGES ou LC_ALL soient correctement définies.');
INSERT INTO potranslation (id, translation) VALUES (545, 'Arquivo /etc/mozilla/prefs.ja disponível para preferências personalizadas.');
INSERT INTO potranslation (id, translation) VALUES (546, 'O pacote Debian do Mozilla irá carregar o arquivo /etc/mozilla/prefs.js após carregar alguns scripts de prefrências padrão.');
INSERT INTO potranslation (id, translation) VALUES (547, 'Você pode editar esse arquivo para definir configurações válidas para todos os usuários do sistema. (por exemplo, configurações de fontes)');
INSERT INTO potranslation (id, translation) VALUES (548, 'auto, esddsp, artsdsp, nenhum');
INSERT INTO potranslation (id, translation) VALUES (549, 'Por favor, escolha o wrapper de seu servidor de som.');
INSERT INTO potranslation (id, translation) VALUES (550, 'Algumas vezes o Mozilla pode travar devido a alguns plugins (por exemplo, o plugin de Flash) tentarem travar o acesso ao dispositivo de som /dev/dsp. Você pode usar um wrapper dsp para resolver esse problema. A opção ''auto'' irá decidir qual wrapper dsp deverá ser usado de acordo com o daemon de som em execução. Quando nenhum daemon de som for detectado, o Mozilla não utilizará nenhum wrapper. Esta configuração será gravada no arquivo /etc/mozilla/mozillarc e poderá ser sobreescrita caso esteja definida em seu arquivo ~/.mozillarc.');
INSERT INTO potranslation (id, translation) VALUES (551, 'Habilitar seleção automática de Idioma/Região ?');
INSERT INTO potranslation (id, translation) VALUES (552, 'Esta configuração fornece uma seleção automática de idioma/região no Mozilla utilizando as configurações de locale. A mesma pode auxiliar um administrador de sistema que precisar lidar com centenas de novatos que não falam inglês.');
INSERT INTO potranslation (id, translation) VALUES (553, 'Por favor, defina suas variáveis de ambiente LC_MESSAGE e LC_ALL para que esta configuração funcione corretamente.');
INSERT INTO potranslation (id, translation) VALUES (554, '設定のカスタマイズに /etc/mozilla/prefs.js が利用できます。');
INSERT INTO potranslation (id, translation) VALUES (555, 'Debian の mozilla は デフォルトの設定スクリプトのあとに /etc/mozilla/prefs.js を読み込みます。');
INSERT INTO potranslation (id, translation) VALUES (556, 'このファイルにより、システムワイドの設定ができます。(例えばフォントなど)');
INSERT INTO potranslation (id, translation) VALUES (557, '自動, esddsp, artsdsp, 無し');
INSERT INTO potranslation (id, translation) VALUES (558, 'サウンドデーモンラッパーを選択してください:');
INSERT INTO potranslation (id, translation) VALUES (559, 'ときどき、mozilla はプラグイン(例えば flashplugin)のせいで /dev/dsp を開けずハングアップしてしまいます。dsp ラッパーを使うことでこの問題を回避できます。 ''auto'' は、使用しているサウンドデーモンを検出し、自動的に dsp ラッパーを選択します。 もしサウンドデーモンが動いていなければ、mozilla はどのラッパーも使いません。 この設定は /etc/mozilla/mozillarc に保存され、これはユーザの ~/.mozillarc によりオーバーライドできます。');
INSERT INTO potranslation (id, translation) VALUES (560, '言語/地域 自動選択機能を利用しますか?');
INSERT INTO potranslation (id, translation) VALUES (561, 'この設定により、Mozillaの言語/地域パックを自動的に選択することができます。これは、非英語圏の初心者に有用な設定です。');
INSERT INTO potranslation (id, translation) VALUES (562, 'この機能が正しく動作するために。LC_MESSAGE か LC_ALL 環境変数を設定しておいてください。');
INSERT INTO potranslation (id, translation) VALUES (563, 'Dispone de /etc/mozilla/prefs.js para personalizaciones.');
INSERT INTO potranslation (id, translation) VALUES (564, 'Mozilla en Debian carga el fichero /etc/mozilla/prefs.js después de ciertos scripts de configuración.');
INSERT INTO potranslation (id, translation) VALUES (565, 'Puede editar este fichero para realizar configuraciones generales, tales como la elección de fuentes.');
INSERT INTO potranslation (id, translation) VALUES (566, 'automático, esddsp, artsdsp, ninguno');
INSERT INTO potranslation (id, translation) VALUES (567, 'Por favor, elija el demonio de sonido para acceder al dsp.');
INSERT INTO potranslation (id, translation) VALUES (568, 'En ocasiones mozilla se cuelga cuando los plugins (por ejemplo el de Flash) bloquean /dev/dsp. Puede utilizar un demonio que haga de wrapper para acceder al dsp. «automático» decidirá cuál utilizar de acuerdo al demonio de sonido que se esté ejecutando. Si no se detecta ninguno, mozilla no usará ninguno. Este valor se guardará en /etc/mozilla/mozillarc y se puede sobreescribir con ~/.mozillarc.');
INSERT INTO potranslation (id, translation) VALUES (569, '/etc/mozilla/prefs.js is beschikbaar om instellingen te wijzigen.');
INSERT INTO potranslation (id, translation) VALUES (570, 'Debian mozilla zal /etc/mozilla/prefs.js inladen na enkele standaard voorkeurscripts te hebben ingeladen.');
INSERT INTO potranslation (id, translation) VALUES (571, 'U kunt dit bestand wijzigen voor systeemwijde instellingen (vb: fontinstellingen)');
INSERT INTO potranslation (id, translation) VALUES (572, 'automatisch, esddsp, artsdsp, geen');
INSERT INTO potranslation (id, translation) VALUES (573, 'Kies uw dsp-inwikkelaar van de geluidsachtergronddienst.');
INSERT INTO potranslation (id, translation) VALUES (574, 'Soms hangt mozilla omdat plugins (vb flashplugin) /dev/dsp vergrendelen. U kunt dsp-inwikkelaars gebruiken om dit op te lossen. ''automatisch'' zal beslissen welke dsp-inwikkelaars gebruikt moeten worden afhankelijk van de uitvoerende geluidsachtergronddienst. Wanneer er geen geluidsachtergronddienst wordt gedetecteerd, zal mozilla geen inwikkelaar gebruiken. Deze instelling zal worden bewaard in /etc/mozilla/mozillarc en kan overschreven worden door uw ~/.mozillarc.');
INSERT INTO potranslation (id, translation) VALUES (575, 'Automatische taal/regio-selectie inschakelen?');
INSERT INTO potranslation (id, translation) VALUES (576, 'Deze optie zorgt voor een automatische taal/regio-selectie in Mozilla gebruikmakend van de locale-instellingen. Het kan een systeembeheerder helpen die geconfronteerd wordt met honderden niet-Engels sprekende beginnelingen.');
INSERT INTO potranslation (id, translation) VALUES (577, 'Zet uw LC_MESSAGE- of LC_ALL-variabele om dit correct te laten werken.');
INSERT INTO potranslation (id, translation) VALUES (578, 'Pro přizpůsobení nastavení můžete použít /etc/mozilla/prefs.js.');
INSERT INTO potranslation (id, translation) VALUES (579, 'Mozilla v Debianu používá kromě dalších skriptů i soubor /etc/mozilla/prefs.js.');
INSERT INTO potranslation (id, translation) VALUES (580, 'V tomto souboru můžete nastavit vlastnosti pro všechny uživatele v systému (např. vhodná písma).');
INSERT INTO potranslation (id, translation) VALUES (581, 'auto, esddsp, artsdsp, žádný');
INSERT INTO potranslation (id, translation) VALUES (582, 'Vyberte program spravující zvukové zařízení dsp.');
INSERT INTO potranslation (id, translation) VALUES (583, 'Občas se může mozilla zaseknout, protože některé moduly (např. flash) zamknou /dev/dsp. Předejít tomu můžete použitím speciálního programu pro správu dsp. Volba ''auto'' se rozhodne podle toho, který správce dsp právě běží. Pokud žádný program nerozpozná, žádný se nepoužije. Toto nastavení se uloží do /etc/mozilla/mozillarc a můžete jej přepsat ve svém ~/.mozillarc.');
INSERT INTO potranslation (id, translation) VALUES (584, 'Povolit automatický výběr Jazyka/Země?');
INSERT INTO potranslation (id, translation) VALUES (585, 'Pokud odpovíte kladně, v Mozille se bude automaticky vybírat vhodný jazyk/země. To může velmi pomoci administrátorovi se spoustou neanglicky mluvících nováčků.');
INSERT INTO potranslation (id, translation) VALUES (586, 'Aby toto nastavení pracovalo správně, musíte mít správně nastavené proměnné LC_MESSAGE nebo LC_ALL.');
INSERT INTO potranslation (id, translation) VALUES (587, '/etc/mozilla/prefs.js kan bruges til at opsætte præferencer.');
INSERT INTO potranslation (id, translation) VALUES (588, 'Debians Mozilla vil læse /etc/mozilla/prefs.js efter standard præference-skriptsne er blevet læst.');
INSERT INTO potranslation (id, translation) VALUES (589, 'Du kan redigere i denne fil for system-globale indstillinger (f.eks. skrifttype indstillinger).');
INSERT INTO potranslation (id, translation) VALUES (590, 'auto, esddsp, artsdsp, ingen');
INSERT INTO potranslation (id, translation) VALUES (591, 'Vælg den lyd dæmon som skal bruges med mozilla.');
INSERT INTO potranslation (id, translation) VALUES (592, 'Nogle gange hænger mozilla fordi plugins (f.eks. flash) låser /dev/dsp.  Du kan bruge en lyd dæmon til at løse det. ''auto'' vil automatisk bestemme hvilken der skal bruges udfra en allerede kørende lyd dæmon Når ingen lyd dæmon er fundet, vil mozilla ikke bruge nogen. Denne indstilling vil blive gemt i /etc/mozilla/mozillarc og kan blive overskrevet af din ~/.mozillarc.');
INSERT INTO potranslation (id, translation) VALUES (593, 'Aktivér automatisk sprog/regionsvalg?');
INSERT INTO potranslation (id, translation) VALUES (594, 'Denne indstilling giver mulighed for automatisk sprog/regions valg i Mozilla ved hjælp af locale-indstillinger. Det kan være en stor hjælp for system administratorer der har hundredvis af ikke-engelsktalende nybegyndere.');
INSERT INTO potranslation (id, translation) VALUES (595, 'For at dette skal virke, skal LC_MESSAGE eller LC_ALL miljøvariablerne være sat korrekt.');
INSERT INTO potranslation (id, translation) VALUES (596, 'Tiedosto /etc/mozilla/prefs.js on asetuksien mukauttamista varten.');
INSERT INTO potranslation (id, translation) VALUES (597, 'Debianin mozilla lataa tiedoston /etc/mozilla/prefs.js oletusasetukset 
sisältävän skriptin jälkeen.');
INSERT INTO potranslation (id, translation) VALUES (598, 'Voit muokata tätä tiedostoa muuttaaksesi koko järjestelmää koskevia asetuksia. 
(esim. kirjasinasetukset)');
INSERT INTO potranslation (id, translation) VALUES (599, 'auto, esddsp, artsdsp, ei mikään');
INSERT INTO potranslation (id, translation) VALUES (600, 'Valitse äänenhallinnan taustaprosessin dsp-kääre.');
INSERT INTO potranslation (id, translation) VALUES (601, 'Joskus mozilla voi jumiutua, jos liitännäiset (esim. flashplugin) lukitsevat 
/dev/dsp:n. Ongelman voi välttää käyttämällä dsp-käärettä. "auto" valitsee 
käynnissä olevan äänenhallinnan taustaohjelman mukaisesti oikeat kääreet. Jos 
äänenhallinnan tataustaohjelmaa ei havaita, mozilla ei käytä mitään käärettä. 
Tämä asetus tallennetaan tiedostoon /etc/mozilla/mozillarc ja sen voi tarvittaessa
syrjäyttää käyttäjän omassa asetustiedostossa (~/.mozillarc).');
INSERT INTO potranslation (id, translation) VALUES (602, 'Salli automaattinen kielen/alueen valinta?');
INSERT INTO potranslation (id, translation) VALUES (603, 'Tämä asetus mahdollistaa automaattisen kielen/alueen valinnan
lokaaliasetuksiin perustuen. Asetus voi olla hyödyllinen
ylläpitäjille, joiden piirissä on satoja muuta kuin englannin kieltä
puhuvia käyttäjiä.');
INSERT INTO potranslation (id, translation) VALUES (604, 'Aseta muuttujat LC_MESSAGE ja LC_ALL, jotta automaattinen tunnistus toimisi.');
INSERT INTO potranslation (id, translation) VALUES (605, 'xprint ei näy olevan asennettu');
INSERT INTO potranslation (id, translation) VALUES (606, 'Mozillasta on poistettu tuki postscriptille. Tästä johtuen Xprint täytyy 
olla asennettuna, jotta tulostaminen toimisi. Ole hyvä ja asenna xprt-xptintorg 
-paketti.');
INSERT INTO potranslation (id, translation) VALUES (607, 'Tämä ei ole ohjelmavirhe. Älä lähetä vikailmoitusta tästä. (Toivomuslista 
postscriptin uudelleentukemiseksi on jo lähetetty, Vika#256072.)');
INSERT INTO potranslation (id, translation) VALUES (608, '/etc/mozilla/prefs.js está dispoñible para actualiza-las preferencias.');
INSERT INTO potranslation (id, translation) VALUES (609, 'O mozilla de Debian ha cargar /etc/mozilla/prefs.js despois de cargar algúns scripts de preferencia por defecto.');
INSERT INTO potranslation (id, translation) VALUES (610, 'Pode editar este ficheiro para configuracións globais do sistema (é dicir, configuración dos tipos de letra)');
INSERT INTO potranslation (id, translation) VALUES (611, 'Failas /etc/mozilla/prefs.js skirtas parinkčių individualizavimui.');
INSERT INTO potranslation (id, translation) VALUES (612, 'Debiano mozilla įkels /etc/mozilla/prefs.js parinktis po to, kai bus įkeltos kai kurios pagal nutylėjimą numatytos parinktys.');
INSERT INTO potranslation (id, translation) VALUES (613, 'Jūs galite keisti šį failą, nustatymams sistemos mastu (pvz. šriftų nustatymams)');
INSERT INTO potranslation (id, translation) VALUES (614, 'auto, esddsp, artsdsp, joks');
INSERT INTO potranslation (id, translation) VALUES (615, 'Pasirinkite Jūsų garso įrenginio demono dsp aplanką (wrapper).');
INSERT INTO potranslation (id, translation) VALUES (616, 'Kartais mozilla stringa, kuomet jos priedas (pvz. flashplugin) blokuoja /dev/dsp. Šiai problemai spręsti galite naudoti dsp aplanką (wrapper). ''auto'' nuspręs, kurį dsp aplanką naudoti, priklausomai nuo veikiančio garso demono. Jei nebus aptiktas joks garso demonas, mozilla nenaudos jokio aplanko. Šie nustatymai bus išsaugoti faile etc/mozilla/mozillarc, bet Jūsų ~/.mozillarc gali būti viršesnis.');
INSERT INTO potranslation (id, translation) VALUES (617, 'Ar leisti automatinį kalbos/regiono parinkimą?');
INSERT INTO potranslation (id, translation) VALUES (618, 'Šis nustatymas leidžia automatiškai pasirinkti Mozill''os kalbos/regiono paketą, panaudojant locale nustatymus. Tai gali padėti sistemos administratoriui, susiduriančiam su šimtais ne anglų kalba kalbančių naujokų.');
INSERT INTO potranslation (id, translation) VALUES (619, 'Tam kad šis nustatymas veiktų, teisingai nustatykite savo LC_MESSAGE arba LC_ALL kintamuosius.');
INSERT INTO potranslation (id, translation) VALUES (620, 'Il file /etc/mozilla/prefs.js è disponibile per la personalizzazione delle preferenze.');
INSERT INTO potranslation (id, translation) VALUES (621, 'Debian Mozilla caricherà il file /etc/mozilla/prefs.js dopo aver caricato alcuni script di configurazione predefiniti.');
INSERT INTO potranslation (id, translation) VALUES (622, 'Si può editare questo file per impostazioni globali di sistema. (Ad esempio le impostazioni per i caratteri)');
INSERT INTO potranslation (id, translation) VALUES (623, 'auto, esddsp, artsdsp, nessuno');
INSERT INTO potranslation (id, translation) VALUES (624, 'Scegliere il modulo di incapsulazione dsp del demone di gestione del suono.');
INSERT INTO potranslation (id, translation) VALUES (625, 'Qualche volta Mozilla si blocca quando alcuni plugin (ad esempio il plugin Flash) mettono un lock alla periferica /dev/dsp. Si può incapsulare l''accesso alla periferica /dev/dsp per risolvere il problema. Scegliendo ''auto'' verrà selezionato un modulo di incapsulazione dsp in funzione del demone di gestione del suono in esecuzione. Quando nessun gestore di suoni viene trovato, Mozilla non userà alcun modulo di incapsulazione. Questa scelta sarà salvata nel file /etc/mozilla/mozillarc e potrà essere sovrascritta dal file ~/.mozillarc.');
INSERT INTO potranslation (id, translation) VALUES (626, 'Abilitare la selezione automatica Lingua/Regione?');
INSERT INTO potranslation (id, translation) VALUES (627, 'Questa impostazione consente una selezione automatica di lingua/regione utilizzando le preferenze locali. Puo` aiutare un sistemista che abbia a che fare con centinaia di nuovi utenti non a conoscenza della lingua inglese.');
INSERT INTO potranslation (id, translation) VALUES (628, 'Settare la variabile LC_MESSAGE o LC_ALL per consentire a questa impostazione di funzionare correttamente.');
INSERT INTO potranslation (id, translation) VALUES (629, 'Yapılandırma tercihlerini kişiselleştirmek için /etc/mozilla/prefs.js mevcuttur.');
INSERT INTO potranslation (id, translation) VALUES (630, 'Debian mozilla ön tanımlı tercih betiklerini yükledikten sonra /etc/mozilla/prefs.js dosyasını yükleyecektir.');
INSERT INTO potranslation (id, translation) VALUES (631, 'Sistem genelinde ayarlar için bu dosyayı düzenleyebilirsiniz. (ör. yazıtipi tanımları)');
INSERT INTO potranslation (id, translation) VALUES (632, 'otomatik, esddsp, artsdsp, yok');
INSERT INTO potranslation (id, translation) VALUES (633, 'Lütfen ses servisinin kullanacağı ses sistemini (dsp wrapper) seçin.');
INSERT INTO potranslation (id, translation) VALUES (634, 'Bazen mozilla, eklentilerin (ör. flashplugin) /dev/dsp''yi kilitlemesi yüzünden askıda kalır. Bu sorunu çözmek için ses sistemini (dsp wrapper) kullanabilirsiniz. ''otomatik'' seçeneği, çalışan ses servisine göre hangi ses sistemlerinin (dsp wrapper) kullanılması gerektiğine karar verecekir. Hiç bir ses servisi bulunamaz ise, mozilla herhangi bir sistem kullanmayacaktır. Bu ayar /etc/mozilla/mozillarc dosyasına kaydedilecektir. Fakat size ait ~/.mozillarc dosyasındaki ayarlar daha önceliklidir.');
INSERT INTO potranslation (id, translation) VALUES (635, '/etc/mozilla/prefs.js ist für die Anpassungen von Einstellungen verfügbar.');
INSERT INTO potranslation (id, translation) VALUES (636, 'Debians Mozilla wird die Datei /etc/mozilla/prefs.js nach dem Laden von einigen Standard-Einstellungsskripten laden.');
INSERT INTO potranslation (id, translation) VALUES (637, 'Sie können diese Datei bearbeiten, um systemweite Einstellungen vorzunehmen (z.B. Schriften-Einstellungen).');
INSERT INTO potranslation (id, translation) VALUES (638, 'automatisch, esddsp, artsdsp, kein');
INSERT INTO potranslation (id, translation) VALUES (639, 'Bitte wählen Sie die DSP-Hülle Ihres Sound-Daemons aus.');
INSERT INTO potranslation (id, translation) VALUES (640, 'Manchmal hängt Mozilla, da Erweiterungen (bspw. flashplugin) einen /dev/dsp sperren. Sie können das durch die Benutzung einer DSP-Hülle beheben. ''automatisch'' wird anhand des laufenden Sound-Daemons entscheiden, welche DSP-Hülle verwendet werden sollte. Falls kein Sound-Daemon erkannt wird, verwendet Mozilla keine Hülle. Diese Einstellung wird in /etc/mozilla/mozillarc abgespeichert und kann in Ihrer ~/.mozillarc überschrieben werden.');
INSERT INTO potranslation (id, translation) VALUES (641, 'Automatische Sprach-/Regionenauswahl aktivieren?');
INSERT INTO potranslation (id, translation) VALUES (642, 'Diese Einstellung ermöglicht eine automatische Auswahl der Sprach-/Regionenpakete in Mozilla mittels der »locale«-Einstellungen. Dies mag Systemadministratoren helfen, die sich Hunderten von nicht Englisch sprechenden Neulingen gegenüber sehen.');
INSERT INTO potranslation (id, translation) VALUES (643, 'Bitte setzen Sie Ihre »LC_MESSAGE«- oder »LC_ALL«-Variable entsprechend, so dass diese Einstellung korrekt funktioniert.');
INSERT INTO potranslation (id, translation) VALUES (644, 'caratas');
INSERT INTO potranslation (id, translation) VALUES (645, '                        ');
INSERT INTO potranslation (id, translation) VALUES (648, 'Srprise! (non-editor)');
INSERT INTO potranslation (id, translation) VALUES (649, ' bang bang in evo hoary');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'potranslation'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = '"language"'::pg_catalog.regclass;

INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (1, 'aa', 'Afar', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (2, 'ab', 'Abkhazian', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (3, 'ace', 'Achinese', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (4, 'ach', 'Acoli', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (5, 'ada', 'Adangme', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (6, 'ady', 'Adyghe; Adygei', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (7, 'afa', 'Afro-Asiatic (Other)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (8, 'afh', 'Afrihili', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (9, 'af', 'Afrikaans', NULL, 2, 'n != 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (10, 'aka', 'Akan', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (11, 'ak', 'Akkadian', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (12, 'sq', 'Albanian', NULL, 2, 'n != 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (13, 'ale', 'Aleut', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (14, 'alg', 'Algonquian languages', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (15, 'am', 'Amharic', NULL, 2, 'n > 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (16, 'ang', 'English, Old (ca.450-1100)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (17, 'apa', 'Apache languages', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (18, 'ar', 'Arabic', NULL, 3, 'n==1 ? 0 : n==2 ? 1 : 2', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (19, 'arc', 'Aramaic', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (20, 'an', 'Aragonese', NULL, 2, 'n != 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (21, 'hy', 'Armenian', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (22, 'arn', 'Araucanian', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (23, 'arp', 'Arapaho', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (24, 'art', 'Artificial (Other)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (25, 'arw', 'Arawak', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (26, 'as', 'Assamese', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (27, 'ast', 'Asturian; Bable', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (28, 'ath', 'Athapascan language', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (29, 'aus', 'Australian languages', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (30, 'av', 'Avaric', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (31, 'ae', 'Avestan', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (32, 'awa', 'Awadhi', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (33, 'ay', 'Aymara', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (34, 'az', 'Azerbaijani', NULL, 2, 'n != 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (35, 'bad', 'Banda', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (36, 'bai', 'Bamileke languages', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (37, 'ba', 'Bashkir', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (38, 'bal', 'Baluchi', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (39, 'bm', 'Bambara', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (40, 'ban', 'Balinese', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (41, 'eu', 'Basque', NULL, 2, 'n != 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (42, 'bas', 'Basa', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (43, 'bat', 'Baltic (Other)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (44, 'bej', 'Beja', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (45, 'be', 'Belarusian', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (46, 'bem', 'Bemba', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (47, 'bn', 'Bengali', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (48, 'ber', 'Berber (Other)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (49, 'bho', 'Bhojpuri', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (50, 'bh', 'Bihari', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (51, 'bik', 'Bikol', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (52, 'bin', 'Bini', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (53, 'bi', 'Bislama', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (54, 'bla', 'Siksika', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (55, 'bnt', 'Bantu (Other)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (56, 'bs', 'Bosnian', NULL, 3, 'n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (57, 'bra', 'Braj', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (58, 'br', 'Breton', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (59, 'btk', 'Batak (Indonesia)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (60, 'bua', 'Buriat', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (61, 'bug', 'Buginese', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (62, 'bg', 'Bulgarian', NULL, 2, 'n != 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (63, 'my', 'Burmese', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (64, 'byn', 'Blin; Bilin', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (65, 'cad', 'Caddo', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (66, 'cai', 'Central American Indian (Other)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (67, 'car', 'Carib', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (68, 'ca', 'Catalan', NULL, 2, 'n != 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (69, 'cau', 'Caucasian (Other)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (70, 'ceb', 'Cebuano', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (71, 'cel', 'Celtic (Other)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (72, 'ch', 'Chamorro', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (73, 'chb', 'Chibcha', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (74, 'ce', 'Chechen', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (75, 'chg', 'Chagatai', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (76, 'zh', 'Chinese', NULL, 1, '0', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (77, 'chk', 'Chukese', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (78, 'chm', 'Mari', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (79, 'chn', 'Chinook jargon', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (80, 'cho', 'Choctaw', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (81, 'chp', 'Chipewyan', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (82, 'chr', 'Cherokee', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (83, 'chu', 'Church Slavic', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (84, 'cv', 'Chuvash', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (85, 'chy', 'Cheyenne', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (86, 'cmc', 'Chamic languages', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (87, 'cop', 'Coptic', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (88, 'kw', 'Cornish', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (89, 'co', 'Corsican', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (90, 'cpe', 'English-based (Other)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (91, 'cpf', 'French-based (Other)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (92, 'cpp', 'Portuguese-based (Other)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (93, 'cr', 'Cree', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (94, 'crh', 'Crimean Turkish; Crimean Tatar', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (95, 'crp', 'Creoles and pidgins (Other)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (96, 'csb', 'Kashubian', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (97, 'cus', 'Cushitic (Other)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (98, 'cs', 'Czech', NULL, 3, 'n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (99, 'dak', 'Dakota', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (100, 'da', 'Danish', NULL, 2, 'n != 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (101, 'dar', 'Dargwa', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (102, 'del', 'Delaware', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (103, 'den', 'Slave (Athapascan)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (104, 'dgr', 'Dogrib', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (105, 'din', 'Dinka', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (106, 'dv', 'Divehi', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (107, 'doi', 'Dogri', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (108, 'dra', 'Dravidian (Other)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (109, 'dsb', 'Lower Sorbian', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (110, 'dua', 'Duala', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (111, 'dum', 'Dutch, Middle (ca. 1050-1350)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (112, 'nl', 'Dutch', NULL, 2, 'n != 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (113, 'dyu', 'Dyula', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (114, 'dz', 'Dzongkha', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (115, 'efi', 'Efik', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (116, 'egy', 'Egyptian (Ancient)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (117, 'eka', 'Ekajuk', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (118, 'elx', 'Elamite', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (119, 'en', 'English', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (120, 'enm', 'English, Middle (1100-1500)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (121, 'eo', 'Esperanto', NULL, 2, 'n != 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (122, 'et', 'Estonian', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (123, 'ee', 'Ewe', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (124, 'ewo', 'Ewondo', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (125, 'fan', 'Fang', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (126, 'fo', 'Faroese', NULL, 2, 'n != 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (127, 'fat', 'Fanti', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (128, 'fj', 'Fijian', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (129, 'fi', 'Finnish', NULL, 2, 'n != 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (130, 'fiu', 'Finno-Ugrian (Other)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (131, 'fon', 'Fon', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (132, 'fr', 'French', NULL, 2, 'n > 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (133, 'frm', 'French, Middle (ca.1400-1600)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (134, 'fro', 'French, Old (842-ca.1400)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (135, 'fy', 'Frisian', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (136, 'ff', 'Fulah', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (137, 'fur', 'Friulian', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (138, 'gaa', 'Ga', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (139, 'gay', 'Gayo', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (140, 'gba', 'Gbaya', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (141, 'gem', 'Germanic (Other)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (142, 'ka', 'Georgian', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (143, 'de', 'German', NULL, 2, 'n != 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (144, 'gez', 'Geez', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (145, 'gil', 'Gilbertese', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (146, 'gd', 'Gaelic; Scottish', NULL, 3, 'n < 2 ? 0 : n == 2 ? 1 : 2', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (147, 'ga', 'Irish', NULL, 3, 'n==1 ? 0 : n==2 ? 1 : 2', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (148, 'gl', 'Galician', NULL, 2, 'n != 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (149, 'gv', 'Manx', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (150, 'gmh', 'German, Middle High (ca.1050-1500)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (151, 'goh', 'German, Old High (ca.750-1050)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (152, 'gon', 'Gondi', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (153, 'gor', 'Gorontalo', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (154, 'got', 'Gothic', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (155, 'grb', 'Grebo', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (156, 'grc', 'Greek, Ancient (to 1453)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (157, 'el', 'Greek, Modern (1453-)', NULL, 2, 'n != 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (158, 'gn', 'Guarani', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (159, 'gu', 'Gujarati', NULL, 2, 'n != 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (160, 'gwi', 'Gwichin', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (161, 'hai', 'Haida', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (162, 'ht', 'Haitian; Haitian Creole', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (163, 'ha', 'Hausa', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (164, 'haw', 'Hawaiian', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (165, 'he', 'Hebrew', NULL, 2, 'n != 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (166, 'hz', 'Herero', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (167, 'hil', 'Hiligaynon', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (168, 'him', 'Himachali', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (169, 'hi', 'Hindi', NULL, 2, 'n != 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (170, 'hit', 'Hittite', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (171, 'hmn', 'Hmong', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (172, 'ho', 'Hiri', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (173, 'hsb', 'Upper Sorbian', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (174, 'hu', 'Hungarian', NULL, 1, '0', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (175, 'hup', 'Hupa', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (176, 'iba', 'Iban', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (177, 'ig', 'Igbo', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (178, 'is', 'Icelandic', NULL, 2, 'n != 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (179, 'io', 'Ido', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (180, 'ii', 'Sichuan Yi', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (181, 'ijo', 'Ijo', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (182, 'iu', 'Inuktitut', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (183, 'ie', 'Interlingue', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (184, 'ilo', 'Iloko', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (185, 'ia', 'Interlingua', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (186, 'inc', 'Indic (Other)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (187, 'id', 'Indonesian', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (188, 'ine', 'Indo-European (Other)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (189, 'inh', 'Ingush', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (190, 'ik', 'Inupiaq', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (191, 'ira', 'Iranian (Other)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (192, 'iro', 'Iroquoian languages', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (193, 'it', 'Italian', NULL, 2, 'n != 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (194, 'jv', 'Javanese', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (195, 'jbo', 'Lojban', NULL, 1, '0', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (196, 'ja', 'Japanese', NULL, 1, '0', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (197, 'jpr', 'Judeo-Persian', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (198, 'jrb', 'Judeo-Arabic', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (199, 'kaa', 'Kara-Kalpak', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (200, 'kab', 'Kabyle', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (201, 'kac', 'Kachin', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (202, 'kl', 'Greenlandic (Kalaallisut)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (203, 'kam', 'Kamba', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (204, 'kn', 'Kannada', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (205, 'kar', 'Karen', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (206, 'ks', 'Kashmiri', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (207, 'kr', 'Kanuri', NULL, 1, '0', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (208, 'kaw', 'Kawi', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (209, 'kk', 'Kazakh', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (210, 'kbd', 'Kabardian', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (211, 'kha', 'Khazi', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (212, 'khi', 'Khoisan (Other)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (213, 'km', 'Khmer', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (214, 'kho', 'Khotanese', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (215, 'ki', 'Kikuyu', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (216, 'rw', 'Kinyarwanda', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (217, 'ky', 'Kirghiz', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (218, 'kmb', 'Kimbundu', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (219, 'kok', 'Konkani', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (220, 'kv', 'Komi', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (221, 'kg', 'Kongo', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (222, 'ko', 'Korean', NULL, 1, '0', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (223, 'kos', 'Kosraean', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (224, 'kpe', 'Kpelle', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (225, 'krc', 'Karachay-Balkar', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (226, 'kro', 'Kru', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (227, 'kru', 'Kurukh', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (228, 'kj', 'Kuanyama', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (229, 'kum', 'Kumyk', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (230, 'ku', 'Kurdish', NULL, 2, 'n != 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (231, 'kut', 'Kutenai', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (232, 'lad', 'Ladino', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (233, 'lah', 'Lahnda', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (234, 'lam', 'Lamba', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (235, 'lo', 'Lao', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (236, 'la', 'Latin', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (237, 'lv', 'Latvian', NULL, 3, 'n%10==1 && n%100!=11 ? 0 : n != 0 ? 1 : 2', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (238, 'lez', 'Lezghian', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (239, 'li', 'Limburgian', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (240, 'ln', 'Lingala', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (241, 'lt', 'Lithuanian', NULL, 3, 'n%10==1 && n%100!=11 ? 0 : n%10>=2 && (n%100<10 || n%100>=20) ? 1 : 2', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (242, 'lol', 'Mongo', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (243, 'loz', 'Lozi', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (244, 'lb', 'Luxembourgish', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (245, 'lua', 'Luba-Lulua', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (246, 'lu', 'Luba-Katanga', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (247, 'lg', 'Ganda', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (248, 'lui', 'Luiseno', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (249, 'lun', 'Lunda', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (250, 'luo', 'Luo (Kenya and Tanzania)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (251, 'lus', 'Lushai', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (252, 'mk', 'Macedonian', NULL, 2, '(n % 10 == 1 && n % 100 != 11) ? 0 : 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (253, 'mad', 'Madurese', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (254, 'mag', 'Magahi', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (255, 'mh', 'Marshallese', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (256, 'mai', 'Maithili', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (257, 'mak', 'Makasar', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (258, 'ml', 'Malayalam', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (259, 'man', 'Mandingo', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (260, 'mi', 'Maori', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (261, 'map', 'Austronesian (Other)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (262, 'mr', 'Marathi', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (263, 'mas', 'Masai', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (264, 'ms', 'Malay', NULL, 2, 'n != 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (265, 'mdf', 'Moksha', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (266, 'mdr', 'Mandar', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (267, 'men', 'Mende', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (268, 'mga', 'Irish, Middle (900-1200)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (269, 'mic', 'Micmac', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (270, 'min', 'Minangkabau', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (271, 'mis', 'Miscellaneous languages', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (272, 'mkh', 'Mon-Khmer (Other)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (273, 'mg', 'Malagasy', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (274, 'mt', 'Maltese', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (275, 'mnc', 'Manchu', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (276, 'mno', 'Manobo languages', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (277, 'moh', 'Mohawk', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (278, 'mo', 'Moldavian', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (279, 'mn', 'Mongolian', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (280, 'mos', 'Mossi', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (281, 'mul', 'Multiple languages', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (282, 'mun', 'Munda languages', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (283, 'mus', 'Creek', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (284, 'mwr', 'Marwari', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (285, 'myn', 'Mayan languages', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (286, 'myv', 'Erzya', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (287, 'nah', 'Nahuatl', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (288, 'nai', 'North American Indian (Other)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (289, 'nap', 'Neapolitan', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (290, 'na', 'Nauru', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (291, 'nv', 'Navaho', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (292, 'nr', 'Ndebele, South', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (293, 'nd', 'Ndebele, North', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (294, 'ng', 'Ndonga', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (295, 'nds', 'German, Low', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (296, 'ne', 'Nepali', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (297, 'new', 'Newari', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (298, 'nia', 'Nias', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (299, 'nic', 'Niger-Kordofanian (Other)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (300, 'niu', 'Niuean', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (301, 'nn', 'Norwegian Nynorsk', NULL, 2, 'n != 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (302, 'nb', 'Norwegian Bokmål', NULL, 2, 'n != 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (303, 'nog', 'Nogai', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (304, 'non', 'Norse, Old', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (305, 'no', 'Norwegian', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (306, 'nso', 'Sotho, Northern', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (307, 'nub', 'Nubian languages', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (308, 'nwc', 'Classical Newari; Old Newari', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (309, 'ny', 'Chewa; Chichewa; Nyanja', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (310, 'nym', 'Nyankole', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (311, 'nyo', 'Nyoro', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (312, 'nzi', 'Nzima', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (313, 'oc', 'Occitan (post 1500)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (314, 'oj', 'Ojibwa', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (315, 'or', 'Oriya', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (316, 'om', 'Oromo', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (317, 'osa', 'Osage', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (318, 'os', 'Ossetian', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (319, 'ota', 'Turkish, Ottoman (1500-1928)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (320, 'oto', 'Otomian languages', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (321, 'paa', 'Papuan (Other)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (322, 'pag', 'Pangasinan', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (323, 'pal', 'Pahlavi', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (324, 'pam', 'Pampanga', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (325, 'pa', 'Panjabi', NULL, 2, 'n != 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (326, 'pap', 'Papiamento', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (327, 'pau', 'Palauan', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (328, 'peo', 'Persian, Old (ca.600-400 B.C.)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (329, 'fa', 'Persian', NULL, 1, '0', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (330, 'phi', 'Philippine (Other)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (331, 'phn', 'Phoenician', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (332, 'pi', 'Pali', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (333, 'pl', 'Polish', NULL, 3, 'n==1 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (334, 'pt', 'Portuguese', NULL, 2, 'n != 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (335, 'pon', 'Pohnpeian', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (336, 'pra', 'Prakrit languages', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (337, 'pro', 'Provençal, Old (to 1500)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (338, 'ps', 'Pushto', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (339, 'qu', 'Quechua', NULL, 2, '(n % 10 == 1 && n % 100 != 11) ? 0 : 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (340, 'raj', 'Rajasthani', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (341, 'rap', 'Rapanui', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (342, 'rar', 'Rarotongan', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (343, 'roa', 'Romance (Other)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (344, 'rm', 'Raeto-Romance', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (345, 'rom', 'Romany', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (346, 'ro', 'Romanian', NULL, 2, 'n != 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (347, 'rn', 'Rundi', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (348, 'ru', 'Russian', NULL, 3, 'n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (349, 'sad', 'Sandawe', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (350, 'sg', 'Sango', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (351, 'sah', 'Yakut', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (352, 'sai', 'South American Indian (Other)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (353, 'sal', 'Salishan languages', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (354, 'sam', 'Samaritan Aramaic', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (355, 'sa', 'Sanskrit', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (356, 'sas', 'Sasak', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (357, 'sat', 'Santali', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (358, 'sr', 'Serbian', NULL, 3, 'n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (359, 'sco', 'Scots', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (360, 'hr', 'Croatian', NULL, 3, 'n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (361, 'sel', 'Selkup', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (362, 'sem', 'Semitic (Other)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (363, 'sga', 'Irish, Old (to 900)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (364, 'sgn', 'Sign languages', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (365, 'shn', 'Shan', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (366, 'sid', 'Sidamo', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (367, 'si', 'Sinhalese', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (368, 'sio', 'Siouan languages', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (369, 'sit', 'Sino-Tibetan (Other)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (370, 'sla', 'Slavic (Other)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (371, 'sk', 'Slovak', NULL, 3, 'n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (372, 'sl', 'Slovenian', NULL, 4, 'n%100==1 ? 0 : n%100==2 ? 1 : n%100==3 || n%100==4 ? 2 : 3', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (373, 'sma', 'Southern Sami', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (374, 'se', 'Northern Sami', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (375, 'smi', 'Sami languages (Other)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (376, 'smj', 'Lule Sami', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (377, 'smn', 'Inari Sami', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (378, 'sm', 'Samoan', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (379, 'sms', 'Skolt Sami', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (380, 'sn', 'Shona', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (381, 'sd', 'Sindhi', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (382, 'snk', 'Soninke', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (383, 'sog', 'Sogdian', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (384, 'so', 'Somali', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (385, 'son', 'Songhai', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (386, 'st', 'Sotho, Southern', NULL, 1, '0', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (387, 'es', 'Spanish', NULL, 2, 'n != 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (388, 'sc', 'Sardinian', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (389, 'srr', 'Serer', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (390, 'ssa', 'Nilo-Saharan (Other)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (391, 'ss', 'Swati', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (392, 'suk', 'Sukuma', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (393, 'su', 'Sundanese', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (394, 'sus', 'Susu', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (395, 'sux', 'Sumerian', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (396, 'sw', 'Swahili', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (397, 'sv', 'Swedish', NULL, 2, 'n != 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (398, 'syr', 'Syriac', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (399, 'ty', 'Tahitian', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (400, 'tai', 'Tai (Other)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (401, 'ta', 'Tamil', NULL, 2, 'n != 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (402, 'ts', 'Tsonga', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (403, 'tt', 'Tatar', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (404, 'te', 'Telugu', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (405, 'tem', 'Timne', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (406, 'ter', 'Tereno', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (407, 'tet', 'Tetum', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (408, 'tg', 'Tajik', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (409, 'tl', 'Tagalog', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (410, 'th', 'Thai', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (411, 'bo', 'Tibetan', NULL, 1, '0', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (412, 'tig', 'Tigre', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (413, 'ti', 'Tigrinya', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (414, 'tiv', 'Tiv', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (415, 'tlh', 'Klingon; tlhIngan-Hol', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (416, 'tkl', 'Tokelau', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (417, 'tli', 'Tlinglit', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (418, 'tmh', 'Tamashek', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (419, 'tog', 'Tonga (Nyasa)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (420, 'to', 'Tonga (Tonga Islands)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (421, 'tpi', 'Tok Pisin', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (422, 'tsi', 'Tsimshian', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (423, 'tn', 'Tswana', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (424, 'tk', 'Turkmen', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (425, 'tum', 'Tumbuka', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (426, 'tup', 'Tupi languages', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (427, 'tr', 'Turkish', NULL, 1, '0', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (428, 'tut', 'Altaic (Other)', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (429, 'tvl', 'Tuvalu', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (430, 'tw', 'Twi', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (431, 'tyv', 'Tuvinian', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (432, 'udm', 'Udmurt', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (433, 'uga', 'Ugaritic', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (434, 'ug', 'Uighur', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (435, 'uk', 'Ukrainian', NULL, 3, 'n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (436, 'umb', 'Umbundu', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (437, 'und', 'Undetermined', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (438, 'urd', 'Urdu', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (439, 'uz', 'Uzbek', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (440, 'vai', 'Vai', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (441, 've', 'Venda', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (442, 'vi', 'Vietnamese', NULL, 1, '0', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (443, 'vo', 'Volapuk', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (444, 'vot', 'Votic', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (445, 'wak', 'Wakashan languages', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (446, 'wal', 'Walamo', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (447, 'war', 'Waray', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (448, 'was', 'Washo', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (449, 'cy', 'Welsh', NULL, 4, 'n==1 ? 0 : n==2 ? 1 : (n != 8 || n != 11) ? 2 : 3', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (450, 'wen', 'Sorbian languages', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (451, 'wa', 'Walloon', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (452, 'wo', 'Wolof', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (453, 'xal', 'Kalmyk', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (454, 'xh', 'Xhosa', NULL, 2, 'n != 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (455, 'yao', 'Yao', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (456, 'yap', 'Yapese', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (457, 'yi', 'Yiddish', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (458, 'yo', 'Yoruba', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (459, 'ypk', 'Yupik languages', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (460, 'zap', 'Zapotec', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (461, 'zen', 'Zenaga', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (462, 'za', 'Chuang; Zhuang', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (463, 'znd', 'Zande', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (464, 'zu', 'Zulu', NULL, 2, 'n != 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (465, 'zun', 'Zuni', NULL, NULL, NULL, true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (466, 'ti_ER', 'Tigrinya (Eritrea)', NULL, NULL, NULL, false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (467, 'ti_ET', 'Tigrinya (Ethiopia)', NULL, NULL, NULL, false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (468, 'gez_ER', 'Geez (Eritrea)', NULL, NULL, NULL, false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (469, 'gez_ET', 'Geez (Ethiopia)', NULL, NULL, NULL, false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (470, 'de_AT', 'German (Austria)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (471, 'de_BE', 'German (Belgium)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (472, 'de_CH', 'German (Switzerland)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (473, 'de_DE', 'German (Germany)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (474, 'de_LU', 'German (Luxembourg)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (475, 'en_AU', 'English (Australia)', NULL, 2, 'n != 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (476, 'en_BW', 'English (Botswana)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (477, 'en_CA', 'English (Canada)', NULL, 2, 'n != 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (478, 'en_DK', 'English (Denmark)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (479, 'en_GB', 'English (United Kingdom)', NULL, 2, 'n != 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (480, 'en_HK', 'English (Hong Kong)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (481, 'en_IE', 'English (Ireland)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (482, 'en_IN', 'English (India)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (483, 'en_NZ', 'English (New Zealand)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (484, 'en_PH', 'English (Philippines)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (485, 'en_SG', 'English (Singapore)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (486, 'en_US', 'English (United States)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (487, 'en_ZA', 'English (South Africa)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (488, 'en_ZW', 'English (Zimbabwe)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (489, 'zh_CN', 'Chinese (China)', NULL, 1, '0', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (490, 'zh_HK', 'Chinese (Hong Kong)', NULL, 1, '0', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (491, 'zh_SG', 'Chinese (Singapore)', NULL, 1, '0', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (492, 'zh_TW', 'Chinese (Taiwan)', NULL, 1, '0', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (493, 'eu_ES', 'Basque (Spain)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (494, 'eu_FR', 'Basque (France)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (495, 'es_AR', 'Spanish (Argentina)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (496, 'es_BO', 'Spanish (Bolivia)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (497, 'es_CL', 'Spanish (Chile)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (498, 'es_CO', 'Spanish (Colombia)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (499, 'es_CR', 'Spanish (Costa Rica)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (500, 'es_DO', 'Spanish (Dominican Republic)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (501, 'es_EC', 'Spanish (Ecuador)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (502, 'es_ES', 'Spanish (Spain)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (503, 'es_GT', 'Spanish (Guatemala)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (504, 'es_HN', 'Spanish (Honduras)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (505, 'es_MX', 'Spanish (Mexico)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (506, 'es_NI', 'Spanish (Nicaragua)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (507, 'es_PA', 'Spanish (Panama)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (508, 'es_PE', 'Spanish (Peru)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (509, 'es_PR', 'Spanish (Puerto Rico)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (510, 'es_PY', 'Spanish (Paraguay)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (511, 'es_SV', 'Spanish (El Salvador)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (512, 'es_US', 'Spanish (United States)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (513, 'es_UY', 'Spanish (Uruguay)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (514, 'es_VE', 'Spanish (Venezuela)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (515, 'ru_RU', 'Russian (Russian Federation)', NULL, 3, 'n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (516, 'ru_UA', 'Russian (Ukraine)', NULL, 3, 'n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (517, 'bn_BD', 'Bengali (Bangladesh)', NULL, NULL, NULL, false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (518, 'bn_IN', 'Bengali (India)', NULL, NULL, NULL, false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (519, 'om_ET', 'Oromo (Ethiopia)', NULL, NULL, NULL, false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (520, 'om_KE', 'Oromo (Kenya)', NULL, NULL, NULL, false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (521, 'pt_BR', 'Portuguese (Brazil)', NULL, 2, 'n > 1', true);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (522, 'pt_PT', 'Portuguese (Portugal)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (523, 'aa_DJ', 'Afar (Djibouti)', NULL, NULL, NULL, false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (524, 'aa_ER', 'Afar (Eritrea)', NULL, NULL, NULL, false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (525, 'aa_ET', 'Afar (Ethiopia)', NULL, NULL, NULL, false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (526, 'it_CH', 'Italian (Switzerland)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (527, 'it_IT', 'Italian (Italy)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (528, 'ar_AE', 'Arabic (United Arab Emirates)', NULL, 3, 'n==1 ? 0 : n==2 ? 1 : 2', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (529, 'ar_BH', 'Arabic (Bahrain)', NULL, 3, 'n==1 ? 0 : n==2 ? 1 : 2', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (530, 'ar_DZ', 'Arabic (Algeria)', NULL, 3, 'n==1 ? 0 : n==2 ? 1 : 2', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (531, 'ar_EG', 'Arabic (Egypt)', NULL, 3, 'n==1 ? 0 : n==2 ? 1 : 2', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (532, 'ar_IN', 'Arabic (India)', NULL, 3, 'n==1 ? 0 : n==2 ? 1 : 2', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (533, 'ar_IQ', 'Arabic (Iraq)', NULL, 3, 'n==1 ? 0 : n==2 ? 1 : 2', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (534, 'ar_JO', 'Arabic (Jordan)', NULL, 3, 'n==1 ? 0 : n==2 ? 1 : 2', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (535, 'ar_KW', 'Arabic (Kuwait)', NULL, 3, 'n==1 ? 0 : n==2 ? 1 : 2', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (536, 'ar_LB', 'Arabic (Lebanon)', NULL, 3, 'n==1 ? 0 : n==2 ? 1 : 2', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (537, 'ar_LY', 'Arabic (Libyan Arab Jamahiriya)', NULL, 3, 'n==1 ? 0 : n==2 ? 1 : 2', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (538, 'ar_MA', 'Arabic (Morocco)', NULL, 3, 'n==1 ? 0 : n==2 ? 1 : 2', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (539, 'ar_OM', 'Arabic (Oman)', NULL, 3, 'n==1 ? 0 : n==2 ? 1 : 2', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (540, 'ar_QA', 'Arabic (Qatar)', NULL, 3, 'n==1 ? 0 : n==2 ? 1 : 2', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (541, 'ar_SA', 'Arabic (Saudi Arabia)', NULL, 3, 'n==1 ? 0 : n==2 ? 1 : 2', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (542, 'ar_SD', 'Arabic (Sudan)', NULL, 3, 'n==1 ? 0 : n==2 ? 1 : 2', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (543, 'ar_SY', 'Arabic (Syrian Arab Republic)', NULL, 3, 'n==1 ? 0 : n==2 ? 1 : 2', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (544, 'ar_TN', 'Arabic (Tunisia)', NULL, 3, 'n==1 ? 0 : n==2 ? 1 : 2', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (545, 'ar_YE', 'Arabic (Yemen)', NULL, 3, 'n==1 ? 0 : n==2 ? 1 : 2', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (546, 'nl_BE', 'Dutch (Belgium)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (547, 'nl_NL', 'Dutch (Netherlands)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (548, 'fr_BE', 'French (Belgium)', NULL, 2, 'n > 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (549, 'fr_CA', 'French (Canada)', NULL, 2, 'n > 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (550, 'fr_CH', 'French (Switzerland)', NULL, 2, 'n > 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (551, 'fr_FR', 'French (France)', NULL, 2, 'n > 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (552, 'fr_LU', 'French (Luxembourg)', NULL, 2, 'n > 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (553, 'sv_FI', 'Swedish (Finland)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (554, 'sv_SE', 'Swedish (Sweden)', NULL, 2, 'n != 1', false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (555, 'so_DJ', 'Somali (Djibouti)', NULL, NULL, NULL, false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (556, 'so_ET', 'Somali (Ethiopia)', NULL, NULL, NULL, false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (557, 'so_KE', 'Somali (Kenya)', NULL, NULL, NULL, false);
INSERT INTO "language" (id, code, englishname, nativename, pluralforms, pluralexpression, visible) VALUES (558, 'so_SO', 'Somali (Somalia)', NULL, NULL, NULL, false);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = '"language"'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'country'::pg_catalog.regclass;

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
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (128, 'MK', 'MKD', 'Macedonia, Republic of', 'The Former Yugoslav Republic of Macedonia', NULL);
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
INSERT INTO country (id, iso3166code2, iso3166code3, name, title, description) VALUES (209, 'TW', 'TWN', 'Taiwan', 'Taiwan', NULL);
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


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'country'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'spokenin'::pg_catalog.regclass;

INSERT INTO spokenin ("language", country, id) VALUES (1, 60, 165);
INSERT INTO spokenin ("language", country, id) VALUES (1, 68, 167);
INSERT INTO spokenin ("language", country, id) VALUES (1, 70, 169);
INSERT INTO spokenin ("language", country, id) VALUES (9, 198, 171);
INSERT INTO spokenin ("language", country, id) VALUES (12, 3, 244);
INSERT INTO spokenin ("language", country, id) VALUES (15, 70, 174);
INSERT INTO spokenin ("language", country, id) VALUES (18, 101, 188);
INSERT INTO spokenin ("language", country, id) VALUES (18, 104, 190);
INSERT INTO spokenin ("language", country, id) VALUES (18, 110, 192);
INSERT INTO spokenin ("language", country, id) VALUES (18, 116, 194);
INSERT INTO spokenin ("language", country, id) VALUES (18, 120, 196);
INSERT INTO spokenin ("language", country, id) VALUES (18, 123, 198);
INSERT INTO spokenin ("language", country, id) VALUES (18, 146, 200);
INSERT INTO spokenin ("language", country, id) VALUES (18, 163, 202);
INSERT INTO spokenin ("language", country, id) VALUES (18, 176, 204);
INSERT INTO spokenin ("language", country, id) VALUES (18, 18, 182);
INSERT INTO spokenin ("language", country, id) VALUES (18, 189, 206);
INSERT INTO spokenin ("language", country, id) VALUES (18, 202, 208);
INSERT INTO spokenin ("language", country, id) VALUES (18, 208, 210);
INSERT INTO spokenin ("language", country, id) VALUES (18, 217, 212);
INSERT INTO spokenin ("language", country, id) VALUES (18, 224, 180);
INSERT INTO spokenin ("language", country, id) VALUES (18, 237, 214);
INSERT INTO spokenin ("language", country, id) VALUES (18, 4, 184);
INSERT INTO spokenin ("language", country, id) VALUES (18, 65, 186);
INSERT INTO spokenin ("language", country, id) VALUES (20, 200, 179);
INSERT INTO spokenin ("language", country, id) VALUES (34, 16, 217);
INSERT INTO spokenin ("language", country, id) VALUES (41, 200, 74);
INSERT INTO spokenin ("language", country, id) VALUES (41, 75, 76);
INSERT INTO spokenin ("language", country, id) VALUES (45, 21, 125);
INSERT INTO spokenin ("language", country, id) VALUES (47, 101, 131);
INSERT INTO spokenin ("language", country, id) VALUES (47, 19, 129);
INSERT INTO spokenin ("language", country, id) VALUES (56, 28, 134);
INSERT INTO spokenin ("language", country, id) VALUES (58, 75, 133);
INSERT INTO spokenin ("language", country, id) VALUES (62, 34, 126);
INSERT INTO spokenin ("language", country, id) VALUES (64, 68, 10);
INSERT INTO spokenin ("language", country, id) VALUES (68, 200, 142);
INSERT INTO spokenin ("language", country, id) VALUES (76, 193, 70);
INSERT INTO spokenin ("language", country, id) VALUES (76, 209, 72);
INSERT INTO spokenin ("language", country, id) VALUES (76, 45, 66);
INSERT INTO spokenin ("language", country, id) VALUES (76, 98, 68);
INSERT INTO spokenin ("language", country, id) VALUES (88, 225, 228);
INSERT INTO spokenin ("language", country, id) VALUES (98, 58, 144);
INSERT INTO spokenin ("language", country, id) VALUES (100, 59, 35);
INSERT INTO spokenin ("language", country, id) VALUES (112, 152, 221);
INSERT INTO spokenin ("language", country, id) VALUES (112, 22, 219);
INSERT INTO spokenin ("language", country, id) VALUES (119, 101, 52);
INSERT INTO spokenin ("language", country, id) VALUES (119, 105, 50);
INSERT INTO spokenin ("language", country, id) VALUES (119, 14, 38);
INSERT INTO spokenin ("language", country, id) VALUES (119, 155, 54);
INSERT INTO spokenin ("language", country, id) VALUES (119, 171, 56);
INSERT INTO spokenin ("language", country, id) VALUES (119, 193, 58);
INSERT INTO spokenin ("language", country, id) VALUES (119, 198, 62);
INSERT INTO spokenin ("language", country, id) VALUES (119, 225, 46);
INSERT INTO spokenin ("language", country, id) VALUES (119, 226, 60);
INSERT INTO spokenin ("language", country, id) VALUES (119, 239, 64);
INSERT INTO spokenin ("language", country, id) VALUES (119, 29, 40);
INSERT INTO spokenin ("language", country, id) VALUES (119, 39, 42);
INSERT INTO spokenin ("language", country, id) VALUES (119, 59, 44);
INSERT INTO spokenin ("language", country, id) VALUES (119, 98, 48);
INSERT INTO spokenin ("language", country, id) VALUES (122, 69, 78);
INSERT INTO spokenin ("language", country, id) VALUES (126, 72, 242);
INSERT INTO spokenin ("language", country, id) VALUES (129, 74, 241);
INSERT INTO spokenin ("language", country, id) VALUES (132, 126, 238);
INSERT INTO spokenin ("language", country, id) VALUES (132, 207, 234);
INSERT INTO spokenin ("language", country, id) VALUES (132, 22, 230);
INSERT INTO spokenin ("language", country, id) VALUES (132, 39, 232);
INSERT INTO spokenin ("language", country, id) VALUES (132, 75, 236);
INSERT INTO spokenin ("language", country, id) VALUES (135, 152, 335);
INSERT INTO spokenin ("language", country, id) VALUES (142, 81, 243);
INSERT INTO spokenin ("language", country, id) VALUES (143, 126, 33);
INSERT INTO spokenin ("language", country, id) VALUES (143, 15, 25);
INSERT INTO spokenin ("language", country, id) VALUES (143, 207, 29);
INSERT INTO spokenin ("language", country, id) VALUES (143, 22, 27);
INSERT INTO spokenin ("language", country, id) VALUES (143, 82, 31);
INSERT INTO spokenin ("language", country, id) VALUES (144, 68, 21);
INSERT INTO spokenin ("language", country, id) VALUES (144, 70, 23);
INSERT INTO spokenin ("language", country, id) VALUES (146, 225, 3);
INSERT INTO spokenin ("language", country, id) VALUES (147, 105, 4);
INSERT INTO spokenin ("language", country, id) VALUES (148, 200, 5);
INSERT INTO spokenin ("language", country, id) VALUES (149, 225, 1);
INSERT INTO spokenin ("language", country, id) VALUES (157, 85, 37);
INSERT INTO spokenin ("language", country, id) VALUES (159, 101, 2);
INSERT INTO spokenin ("language", country, id) VALUES (165, 106, 156);
INSERT INTO spokenin ("language", country, id) VALUES (169, 101, 155);
INSERT INTO spokenin ("language", country, id) VALUES (174, 99, 154);
INSERT INTO spokenin ("language", country, id) VALUES (178, 100, 173);
INSERT INTO spokenin ("language", country, id) VALUES (187, 102, 218);
INSERT INTO spokenin ("language", country, id) VALUES (193, 107, 177);
INSERT INTO spokenin ("language", country, id) VALUES (193, 207, 175);
INSERT INTO spokenin ("language", country, id) VALUES (196, 109, 135);
INSERT INTO spokenin ("language", country, id) VALUES (202, 86, 123);
INSERT INTO spokenin ("language", country, id) VALUES (204, 101, 36);
INSERT INTO spokenin ("language", country, id) VALUES (222, 115, 245);
INSERT INTO spokenin ("language", country, id) VALUES (235, 118, 7);
INSERT INTO spokenin ("language", country, id) VALUES (237, 119, 145);
INSERT INTO spokenin ("language", country, id) VALUES (241, 125, 11);
INSERT INTO spokenin ("language", country, id) VALUES (247, 222, 6);
INSERT INTO spokenin ("language", country, id) VALUES (252, 128, 161);
INSERT INTO spokenin ("language", country, id) VALUES (258, 101, 158);
INSERT INTO spokenin ("language", country, id) VALUES (260, 155, 160);
INSERT INTO spokenin ("language", country, id) VALUES (262, 101, 164);
INSERT INTO spokenin ("language", country, id) VALUES (264, 131, 163);
INSERT INTO spokenin ("language", country, id) VALUES (274, 134, 162);
INSERT INTO spokenin ("language", country, id) VALUES (279, 144, 159);
INSERT INTO spokenin ("language", country, id) VALUES (296, 151, 226);
INSERT INTO spokenin ("language", country, id) VALUES (301, 162, 223);
INSERT INTO spokenin ("language", country, id) VALUES (302, 162, 225);
INSERT INTO spokenin ("language", country, id) VALUES (305, 162, 224);
INSERT INTO spokenin ("language", country, id) VALUES (313, 75, 140);
INSERT INTO spokenin ("language", country, id) VALUES (316, 112, 138);
INSERT INTO spokenin ("language", country, id) VALUES (316, 70, 136);
INSERT INTO spokenin ("language", country, id) VALUES (325, 101, 151);
INSERT INTO spokenin ("language", country, id) VALUES (329, 103, 240);
INSERT INTO spokenin ("language", country, id) VALUES (333, 173, 152);
INSERT INTO spokenin ("language", country, id) VALUES (334, 174, 148);
INSERT INTO spokenin ("language", country, id) VALUES (346, 178, 124);
INSERT INTO spokenin ("language", country, id) VALUES (348, 179, 119);
INSERT INTO spokenin ("language", country, id) VALUES (348, 223, 121);
INSERT INTO spokenin ("language", country, id) VALUES (360, 55, 153);
INSERT INTO spokenin ("language", country, id) VALUES (366, 70, 227);
INSERT INTO spokenin ("language", country, id) VALUES (371, 194, 251);
INSERT INTO spokenin ("language", country, id) VALUES (372, 195, 260);
INSERT INTO spokenin ("language", country, id) VALUES (374, 162, 261);
INSERT INTO spokenin ("language", country, id) VALUES (384, 112, 256);
INSERT INTO spokenin ("language", country, id) VALUES (384, 197, 258);
INSERT INTO spokenin ("language", country, id) VALUES (384, 60, 252);
INSERT INTO spokenin ("language", country, id) VALUES (384, 70, 254);
INSERT INTO spokenin ("language", country, id) VALUES (386, 198, 250);
INSERT INTO spokenin ("language", country, id) VALUES (387, 11, 79);
INSERT INTO spokenin ("language", country, id) VALUES (387, 140, 99);
INSERT INTO spokenin ("language", country, id) VALUES (387, 156, 101);
INSERT INTO spokenin ("language", country, id) VALUES (387, 167, 103);
INSERT INTO spokenin ("language", country, id) VALUES (387, 169, 109);
INSERT INTO spokenin ("language", country, id) VALUES (387, 170, 105);
INSERT INTO spokenin ("language", country, id) VALUES (387, 175, 107);
INSERT INTO spokenin ("language", country, id) VALUES (387, 200, 93);
INSERT INTO spokenin ("language", country, id) VALUES (387, 226, 113);
INSERT INTO spokenin ("language", country, id) VALUES (387, 228, 115);
INSERT INTO spokenin ("language", country, id) VALUES (387, 231, 117);
INSERT INTO spokenin ("language", country, id) VALUES (387, 27, 81);
INSERT INTO spokenin ("language", country, id) VALUES (387, 44, 83);
INSERT INTO spokenin ("language", country, id) VALUES (387, 48, 85);
INSERT INTO spokenin ("language", country, id) VALUES (387, 53, 87);
INSERT INTO spokenin ("language", country, id) VALUES (387, 62, 89);
INSERT INTO spokenin ("language", country, id) VALUES (387, 64, 91);
INSERT INTO spokenin ("language", country, id) VALUES (387, 66, 111);
INSERT INTO spokenin ("language", country, id) VALUES (387, 90, 95);
INSERT INTO spokenin ("language", country, id) VALUES (387, 97, 97);
INSERT INTO spokenin ("language", country, id) VALUES (397, 206, 248);
INSERT INTO spokenin ("language", country, id) VALUES (397, 74, 246);
INSERT INTO spokenin ("language", country, id) VALUES (401, 101, 19);
INSERT INTO spokenin ("language", country, id) VALUES (403, 179, 8);
INSERT INTO spokenin ("language", country, id) VALUES (404, 101, 18);
INSERT INTO spokenin ("language", country, id) VALUES (408, 210, 17);
INSERT INTO spokenin ("language", country, id) VALUES (409, 171, 150);
INSERT INTO spokenin ("language", country, id) VALUES (410, 212, 12);
INSERT INTO spokenin ("language", country, id) VALUES (412, 68, 229);
INSERT INTO spokenin ("language", country, id) VALUES (413, 68, 13);
INSERT INTO spokenin ("language", country, id) VALUES (413, 70, 15);
INSERT INTO spokenin ("language", country, id) VALUES (427, 218, 9);
INSERT INTO spokenin ("language", country, id) VALUES (435, 223, 127);
INSERT INTO spokenin ("language", country, id) VALUES (439, 229, 157);
INSERT INTO spokenin ("language", country, id) VALUES (442, 232, 172);
INSERT INTO spokenin ("language", country, id) VALUES (449, 225, 143);
INSERT INTO spokenin ("language", country, id) VALUES (451, 22, 128);
INSERT INTO spokenin ("language", country, id) VALUES (454, 198, 141);
INSERT INTO spokenin ("language", country, id) VALUES (457, 226, 20);
INSERT INTO spokenin ("language", country, id) VALUES (464, 198, 216);
INSERT INTO spokenin ("language", country, id) VALUES (466, 68, 14);
INSERT INTO spokenin ("language", country, id) VALUES (467, 70, 16);
INSERT INTO spokenin ("language", country, id) VALUES (468, 68, 22);
INSERT INTO spokenin ("language", country, id) VALUES (469, 70, 24);
INSERT INTO spokenin ("language", country, id) VALUES (470, 15, 26);
INSERT INTO spokenin ("language", country, id) VALUES (471, 22, 28);
INSERT INTO spokenin ("language", country, id) VALUES (472, 207, 30);
INSERT INTO spokenin ("language", country, id) VALUES (473, 82, 32);
INSERT INTO spokenin ("language", country, id) VALUES (474, 126, 34);
INSERT INTO spokenin ("language", country, id) VALUES (475, 14, 39);
INSERT INTO spokenin ("language", country, id) VALUES (476, 29, 41);
INSERT INTO spokenin ("language", country, id) VALUES (477, 39, 43);
INSERT INTO spokenin ("language", country, id) VALUES (478, 59, 45);
INSERT INTO spokenin ("language", country, id) VALUES (479, 225, 47);
INSERT INTO spokenin ("language", country, id) VALUES (480, 98, 49);
INSERT INTO spokenin ("language", country, id) VALUES (481, 105, 51);
INSERT INTO spokenin ("language", country, id) VALUES (482, 101, 53);
INSERT INTO spokenin ("language", country, id) VALUES (483, 155, 55);
INSERT INTO spokenin ("language", country, id) VALUES (484, 171, 57);
INSERT INTO spokenin ("language", country, id) VALUES (485, 193, 59);
INSERT INTO spokenin ("language", country, id) VALUES (486, 226, 61);
INSERT INTO spokenin ("language", country, id) VALUES (487, 198, 63);
INSERT INTO spokenin ("language", country, id) VALUES (488, 239, 65);
INSERT INTO spokenin ("language", country, id) VALUES (489, 45, 67);
INSERT INTO spokenin ("language", country, id) VALUES (490, 98, 69);
INSERT INTO spokenin ("language", country, id) VALUES (491, 193, 71);
INSERT INTO spokenin ("language", country, id) VALUES (492, 209, 73);
INSERT INTO spokenin ("language", country, id) VALUES (493, 200, 75);
INSERT INTO spokenin ("language", country, id) VALUES (494, 75, 77);
INSERT INTO spokenin ("language", country, id) VALUES (495, 11, 80);
INSERT INTO spokenin ("language", country, id) VALUES (496, 27, 82);
INSERT INTO spokenin ("language", country, id) VALUES (497, 44, 84);
INSERT INTO spokenin ("language", country, id) VALUES (498, 48, 86);
INSERT INTO spokenin ("language", country, id) VALUES (499, 53, 88);
INSERT INTO spokenin ("language", country, id) VALUES (500, 62, 90);
INSERT INTO spokenin ("language", country, id) VALUES (501, 64, 92);
INSERT INTO spokenin ("language", country, id) VALUES (502, 200, 94);
INSERT INTO spokenin ("language", country, id) VALUES (503, 90, 96);
INSERT INTO spokenin ("language", country, id) VALUES (504, 97, 98);
INSERT INTO spokenin ("language", country, id) VALUES (505, 140, 100);
INSERT INTO spokenin ("language", country, id) VALUES (506, 156, 102);
INSERT INTO spokenin ("language", country, id) VALUES (507, 167, 104);
INSERT INTO spokenin ("language", country, id) VALUES (508, 170, 106);
INSERT INTO spokenin ("language", country, id) VALUES (509, 175, 108);
INSERT INTO spokenin ("language", country, id) VALUES (510, 169, 110);
INSERT INTO spokenin ("language", country, id) VALUES (511, 66, 112);
INSERT INTO spokenin ("language", country, id) VALUES (512, 226, 114);
INSERT INTO spokenin ("language", country, id) VALUES (513, 228, 116);
INSERT INTO spokenin ("language", country, id) VALUES (514, 231, 118);
INSERT INTO spokenin ("language", country, id) VALUES (515, 179, 120);
INSERT INTO spokenin ("language", country, id) VALUES (516, 223, 122);
INSERT INTO spokenin ("language", country, id) VALUES (517, 19, 130);
INSERT INTO spokenin ("language", country, id) VALUES (518, 101, 132);
INSERT INTO spokenin ("language", country, id) VALUES (519, 70, 137);
INSERT INTO spokenin ("language", country, id) VALUES (520, 112, 139);
INSERT INTO spokenin ("language", country, id) VALUES (521, 31, 147);
INSERT INTO spokenin ("language", country, id) VALUES (522, 174, 149);
INSERT INTO spokenin ("language", country, id) VALUES (523, 60, 166);
INSERT INTO spokenin ("language", country, id) VALUES (524, 68, 168);
INSERT INTO spokenin ("language", country, id) VALUES (525, 70, 170);
INSERT INTO spokenin ("language", country, id) VALUES (526, 207, 176);
INSERT INTO spokenin ("language", country, id) VALUES (527, 107, 178);
INSERT INTO spokenin ("language", country, id) VALUES (528, 224, 181);
INSERT INTO spokenin ("language", country, id) VALUES (529, 18, 183);
INSERT INTO spokenin ("language", country, id) VALUES (530, 4, 185);
INSERT INTO spokenin ("language", country, id) VALUES (531, 65, 187);
INSERT INTO spokenin ("language", country, id) VALUES (532, 101, 189);
INSERT INTO spokenin ("language", country, id) VALUES (533, 104, 191);
INSERT INTO spokenin ("language", country, id) VALUES (534, 110, 193);
INSERT INTO spokenin ("language", country, id) VALUES (535, 116, 195);
INSERT INTO spokenin ("language", country, id) VALUES (536, 120, 197);
INSERT INTO spokenin ("language", country, id) VALUES (537, 123, 199);
INSERT INTO spokenin ("language", country, id) VALUES (538, 146, 201);
INSERT INTO spokenin ("language", country, id) VALUES (539, 163, 203);
INSERT INTO spokenin ("language", country, id) VALUES (540, 176, 205);
INSERT INTO spokenin ("language", country, id) VALUES (541, 189, 207);
INSERT INTO spokenin ("language", country, id) VALUES (542, 202, 209);
INSERT INTO spokenin ("language", country, id) VALUES (543, 208, 211);
INSERT INTO spokenin ("language", country, id) VALUES (544, 217, 213);
INSERT INTO spokenin ("language", country, id) VALUES (545, 237, 215);
INSERT INTO spokenin ("language", country, id) VALUES (546, 22, 220);
INSERT INTO spokenin ("language", country, id) VALUES (547, 152, 222);
INSERT INTO spokenin ("language", country, id) VALUES (548, 22, 231);
INSERT INTO spokenin ("language", country, id) VALUES (549, 39, 233);
INSERT INTO spokenin ("language", country, id) VALUES (550, 207, 235);
INSERT INTO spokenin ("language", country, id) VALUES (551, 75, 237);
INSERT INTO spokenin ("language", country, id) VALUES (552, 126, 239);
INSERT INTO spokenin ("language", country, id) VALUES (553, 74, 247);
INSERT INTO spokenin ("language", country, id) VALUES (554, 206, 249);
INSERT INTO spokenin ("language", country, id) VALUES (555, 60, 253);
INSERT INTO spokenin ("language", country, id) VALUES (556, 70, 255);
INSERT INTO spokenin ("language", country, id) VALUES (557, 112, 257);
INSERT INTO spokenin ("language", country, id) VALUES (558, 197, 259);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'spokenin'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'license'::pg_catalog.regclass;

INSERT INTO license (id, legalese) VALUES (1, 'GPL-2');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'license'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'potemplate'::pg_catalog.regclass;

INSERT INTO potemplate (id, priority, description, copyright, license, datecreated, "path", iscurrent, messagecount, "owner", rawimporter, daterawimport, rawimportstatus, sourcepackagename, distrorelease, sourcepackageversion, header, potemplatename, binarypackagename, languagepack, filename, rawfile, productseries) VALUES (1, NULL, 'Template for evolution in hoary', NULL, NULL, '2005-03-18 18:20:12.273149', 'po', true, 22, 30, 13, '2005-04-07 13:12:39.892924', 3, NULL, NULL, NULL, 'Project-Id-Version: PACKAGE VERSION
Report-Msgid-Bugs-To: 
POT-Creation-Date: 2005-04-07 14:10+0200
PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE
Last-Translator: FULL NAME <EMAIL@ADDRESS>
Language-Team: LANGUAGE <LL@li.org>
MIME-Version: 1.0
Content-Type: text/plain; charset=ASCII
Content-Transfer-Encoding: 8bit
', 1, NULL, false, NULL, 7, 3);
INSERT INTO potemplate (id, priority, description, copyright, license, datecreated, "path", iscurrent, messagecount, "owner", rawimporter, daterawimport, rawimportstatus, sourcepackagename, distrorelease, sourcepackageversion, header, potemplatename, binarypackagename, languagepack, filename, rawfile, productseries) VALUES (2, NULL, NULL, NULL, NULL, '2005-03-24 19:59:31.439579', 'po', true, 63, 30, 30, '2005-05-06 20:07:24.255804', 3, 14, 3, '0.7.2-0ubuntu1', 'Project-Id-Version: PACKAGE VERSION
Report-Msgid-Bugs-To: martin.pitt@canonical.com
POT-Creation-Date: 2005-04-04 17:43+0200
PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE
Last-Translator: FULL NAME <EMAIL@ADDRESS>
Language-Team: LANGUAGE <LL@li.org>
MIME-Version: 1.0
Content-Type: text/plain; charset=CHARSET
Content-Transfer-Encoding: 8bit
', 2, 13, true, 'template.pot', 6, NULL);
INSERT INTO potemplate (id, priority, description, copyright, license, datecreated, "path", iscurrent, messagecount, "owner", rawimporter, daterawimport, rawimportstatus, sourcepackagename, distrorelease, sourcepackageversion, header, potemplatename, binarypackagename, languagepack, filename, rawfile, productseries) VALUES (3, NULL, NULL, NULL, NULL, '2005-05-06 20:06:59.867977', 'po', true, 43, 12, 30, '2005-05-06 20:06:59.867977', 3, NULL, NULL, NULL, 'Project-Id-Version: PACKAGE VERSION
Report-Msgid-Bugs-To: 
POT-Creation-Date: 2004-08-24 16:09-0400
PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE
Last-Translator: FULL NAME <EMAIL@ADDRESS>
Language-Team: LANGUAGE <LL@li.org>
MIME-Version: 1.0
Content-Type: text/plain; charset=CHARSET
Content-Transfer-Encoding: 8bit
', 3, NULL, false, 'netapplet.pot', 5, 5);
INSERT INTO potemplate (id, priority, description, copyright, license, datecreated, "path", iscurrent, messagecount, "owner", rawimporter, daterawimport, rawimportstatus, sourcepackagename, distrorelease, sourcepackageversion, header, potemplatename, binarypackagename, languagepack, filename, rawfile, productseries) VALUES (4, NULL, NULL, NULL, NULL, '2005-05-06 20:39:27.778946', 'po', true, 22, 30, 13, '2005-05-06 20:40:52.942183', 3, 9, 3, NULL, 'Project-Id-Version: PACKAGE VERSION
Report-Msgid-Bugs-To: 
POT-Creation-Date: 2005-04-07 14:10+0200
PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE
Last-Translator: FULL NAME <EMAIL@ADDRESS>
Language-Team: LANGUAGE <LL@li.org>
MIME-Version: 1.0
Content-Type: text/plain; charset=ASCII
Content-Transfer-Encoding: 8bit
', 1, NULL, true, 'evolution-2.2.pot', 8, NULL);
INSERT INTO potemplate (id, priority, description, copyright, license, datecreated, "path", iscurrent, messagecount, "owner", rawimporter, daterawimport, rawimportstatus, sourcepackagename, distrorelease, sourcepackageversion, header, potemplatename, binarypackagename, languagepack, filename, rawfile, productseries) VALUES (5, NULL, NULL, NULL, NULL, '2005-05-06 21:10:17.367605', 'debian/po', true, 9, 30, 30, '2005-05-06 21:10:39.821363', 3, 16, 3, '2:1.7.6-1ubuntu2', 'Project-Id-Version: PACKAGE VERSION
Report-Msgid-Bugs-To: 
POT-Creation-Date: 2004-07-11 16:16+0900
PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE
Last-Translator: FULL NAME <EMAIL@ADDRESS>
Language-Team: LANGUAGE <LL@li.org>
MIME-Version: 1.0
Content-Type: text/plain; charset=CHARSET
Content-Transfer-Encoding: 8bit
', 4, NULL, false, 'templates.pot', 9, NULL);
INSERT INTO potemplate (id, priority, description, copyright, license, datecreated, "path", iscurrent, messagecount, "owner", rawimporter, daterawimport, rawimportstatus, sourcepackagename, distrorelease, sourcepackageversion, header, potemplatename, binarypackagename, languagepack, filename, rawfile, productseries) VALUES (6, NULL, NULL, NULL, NULL, '2005-08-10 09:31:29.606407', NULL, true, 0, 12, 12, '2005-08-10 09:31:29.606407', 3, NULL, NULL, NULL, NULL, 5, NULL, false, NULL, 34, 3);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'potemplate'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'pofile'::pg_catalog.regclass;

INSERT INTO pofile (id, potemplate, "language", description, topcomment, header, fuzzyheader, lasttranslator, license, currentcount, updatescount, rosettacount, lastparsed, "owner", pluralforms, variant, filename, rawimporter, daterawimport, rawimportstatus, rawfile, exportfile, exporttime, rawfilepublished, datecreated, latestsubmission) VALUES (1, 1, 387, 'Spanish translation for evolution in hoary', ' traducción de es.po al Spanish
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
PO-Revision-Date: 2005-04-07 13:22+0000
Last-Translator: Carlos Perelló Marín <carlos@canonical.com>
Language-Team: Spanish <traductores@es.gnome.org>
MIME-Version: 1.0
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: 8bit
Report-Msgid-Bugs-To: serrador@hispalinux.es
X-Generator: Rosetta (http://launchpad.ubuntu.com/rosetta/)
Plural-Forms: nplurals=2; plural=(n != 1);
', true, NULL, NULL, 7, 0, 0, NULL, 12, 2, NULL, NULL, 13, '2005-04-07 13:18:57.59704', 1, 33, NULL, NULL, NULL, '2005-06-06 08:59:54.24073', 690);
INSERT INTO pofile (id, potemplate, "language", description, topcomment, header, fuzzyheader, lasttranslator, license, currentcount, updatescount, rosettacount, lastparsed, "owner", pluralforms, variant, filename, rawimporter, daterawimport, rawimportstatus, rawfile, exportfile, exporttime, rawfilepublished, datecreated, latestsubmission) VALUES (3, 2, 502, NULL, ' Spanish (Spain) translation for mount removable devices as normal user
 Copyright (c) (c) 2005 Canonical Ltd, and Rosetta Contributors 2005
 This file is distributed under the same license as the mount removable devices as normal user package.
 FIRST AUTHOR <EMAIL@ADDRESS>, 2005.
', 'Project-Id-Version: mount removable devices as normal user
Report-Msgid-Bugs-To: martin.pitt@canonical.com
POT-Creation-Date: 2005-04-04 17:31+0200
PO-Revision-Date: 2005-03-15 21:19+0000
Last-Translator: Daniel Aguayo <danner@mixmail.com>
Language-Team: Spanish (Spain) <es_ES@li.org>
MIME-Version: 1.0
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: 8bit
X-Rosetta-Version: 0.1
Plural-Forms: nplurals=2; plural=n != 1
X-Generator: Rosetta (http://launchpad.ubuntu.com/rosetta/)
', true, NULL, NULL, 63, 0, 0, NULL, 31, 2, NULL, NULL, 30, '2005-05-06 20:07:24.255804', 3, 14, NULL, NULL, NULL, '2005-06-06 08:59:54.236824', 265);
INSERT INTO pofile (id, potemplate, "language", description, topcomment, header, fuzzyheader, lasttranslator, license, currentcount, updatescount, rosettacount, lastparsed, "owner", pluralforms, variant, filename, rawimporter, daterawimport, rawimportstatus, rawfile, exportfile, exporttime, rawfilepublished, datecreated, latestsubmission) VALUES (4, 2, 143, NULL, ' German translations for PACKAGE package
 German messages for PACKAGE.
 Copyright (C) 2004 Martin Pitt
 This file is distributed under the same license as the PACKAGE package.
 Martin Pitt <martin.pitt@canonical.com>, 2004.

', 'Project-Id-Version: pmount 0.5
Report-Msgid-Bugs-To: martin.pitt@canonical.com
POT-Creation-Date: 2005-04-04 17:31+0200
PO-Revision-Date: 2004-12-29 17:56+0100
Last-Translator: Martin Pitt <martin.pitt@canonical.com>
Language-Team: German <de@li.org>
MIME-Version: 1.0
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: 8bit
Plural-Forms: nplurals=2; plural=(n != 1);
', true, NULL, NULL, 63, 0, 0, NULL, 31, 2, NULL, NULL, 30, '2005-05-06 20:07:24.255804', 3, 15, NULL, NULL, NULL, '2005-06-06 08:59:54.238198', 328);
INSERT INTO pofile (id, potemplate, "language", description, topcomment, header, fuzzyheader, lasttranslator, license, currentcount, updatescount, rosettacount, lastparsed, "owner", pluralforms, variant, filename, rawimporter, daterawimport, rawimportstatus, rawfile, exportfile, exporttime, rawfilepublished, datecreated, latestsubmission) VALUES (5, 2, 68, NULL, ' Catalan translation for mount removable devices as normal user
 Copyright (c) (c) 2005 Canonical Ltd, and Rosetta Contributors 2005
 This file is distributed under the same license as the mount removable devices as normal user package.
 FIRST AUTHOR <EMAIL@ADDRESS>, 2005.
', 'Project-Id-Version: mount removable devices as normal user
Report-Msgid-Bugs-To: martin.pitt@canonical.com
POT-Creation-Date: 2005-04-04 17:31+0200
PO-Revision-Date: 2005-02-12 01:18+0000
Last-Translator: Jordi Vilalta <jvprat@wanadoo.es>
Language-Team: Catalan <ca@li.org>
MIME-Version: 1.0
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: 8bit
X-Rosetta-Version: 0.1
Plural-Forms: nplurals=2; plural=n != 1
X-Generator: Rosetta (http://launchpad.ubuntu.com/rosetta/)
', true, NULL, NULL, 62, 0, 0, NULL, 31, 2, NULL, NULL, 30, '2005-05-06 20:07:24.255804', 3, 11, NULL, NULL, NULL, '2005-06-06 08:59:54.254523', 76);
INSERT INTO pofile (id, potemplate, "language", description, topcomment, header, fuzzyheader, lasttranslator, license, currentcount, updatescount, rosettacount, lastparsed, "owner", pluralforms, variant, filename, rawimporter, daterawimport, rawimportstatus, rawfile, exportfile, exporttime, rawfilepublished, datecreated, latestsubmission) VALUES (6, 2, 132, NULL, ' French translation for mount removable devices as normal user
 Copyright (c) (c) 2005 Canonical Ltd, and Rosetta Contributors 2005
 This file is distributed under the same license as the mount removable devices as normal user package.
 FIRST AUTHOR <EMAIL@ADDRESS>, 2005.

', 'Project-Id-Version: mount removable devices as normal user
Report-Msgid-Bugs-To: martin.pitt@canonical.com
POT-Creation-Date: 2005-04-04 17:31+0200
PO-Revision-Date: 2005-04-02 22:34+0000
Last-Translator: Nicolas Velin <nsv@fr.st>
Language-Team: French <fr@li.org>
MIME-Version: 1.0
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: 8bit
X-Rosetta-Version: 0.1
Plural-Forms: nplurals=2; plural=n > 1
X-Generator: Rosetta (http://launchpad.ubuntu.com/rosetta/)
', true, NULL, NULL, 57, 0, 0, NULL, 31, 2, NULL, NULL, 30, '2005-05-06 20:07:24.255804', 3, 16, NULL, NULL, NULL, '2005-06-06 08:59:54.256914', 391);
INSERT INTO pofile (id, potemplate, "language", description, topcomment, header, fuzzyheader, lasttranslator, license, currentcount, updatescount, rosettacount, lastparsed, "owner", pluralforms, variant, filename, rawimporter, daterawimport, rawimportstatus, rawfile, exportfile, exporttime, rawfilepublished, datecreated, latestsubmission) VALUES (7, 2, 360, NULL, ' Croatian translation for pmount
 Copyright (c) (c) 2005 Canonical Ltd, and Rosetta Contributors 2005
 This file is distributed under the same license as the pmount package.
 FIRST AUTHOR <EMAIL@ADDRESS>, 2005.

', 'Project-Id-Version: pmount
Report-Msgid-Bugs-To: martin.pitt@canonical.com
POT-Creation-Date: 2005-04-04 17:31+0200
PO-Revision-Date: 2005-03-16 14:51+0000
Last-Translator: Edgar Bursic <edgar@monteparadiso.hr>
Language-Team: Croatian <hr@li.org>
MIME-Version: 1.0
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: 8bit
X-Rosetta-Version: 0.1
Plural-Forms: nplurals=3; plural=n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2
X-Generator: Rosetta (http://launchpad.ubuntu.com/rosetta/)
', true, NULL, NULL, 63, 0, 0, NULL, 31, 3, NULL, NULL, 30, '2005-05-06 20:07:24.255804', 3, 10, NULL, NULL, NULL, '2005-06-06 08:59:54.255734', 13);
INSERT INTO pofile (id, potemplate, "language", description, topcomment, header, fuzzyheader, lasttranslator, license, currentcount, updatescount, rosettacount, lastparsed, "owner", pluralforms, variant, filename, rawimporter, daterawimport, rawimportstatus, rawfile, exportfile, exporttime, rawfilepublished, datecreated, latestsubmission) VALUES (8, 2, 527, NULL, ' Italian (Italy) translation for pmount
 Copyright (c) (c) 2005 Canonical Ltd, and Rosetta Contributors 2005
 This file is distributed under the same license as the pmount package.
 FIRST AUTHOR <EMAIL@ADDRESS>, 2005.

', 'Project-Id-Version: pmount
Report-Msgid-Bugs-To: martin.pitt@canonical.com
POT-Creation-Date: 2005-04-04 17:31+0200
PO-Revision-Date: 2005-03-16 23:54+0000
Last-Translator: Francesco Accattapà <callipeo@libero.it>
Language-Team: Italian (Italy) <it_IT@li.org>
MIME-Version: 1.0
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: 8bit
X-Rosetta-Version: 0.1
Plural-Forms: nplurals=2; plural=n != 1
X-Generator: Rosetta (http://launchpad.ubuntu.com/rosetta/)
', true, NULL, NULL, 49, 0, 0, NULL, 31, 2, NULL, NULL, 30, '2005-05-06 20:07:24.255804', 3, 17, NULL, NULL, NULL, '2005-06-06 08:59:54.259358', 454);
INSERT INTO pofile (id, potemplate, "language", description, topcomment, header, fuzzyheader, lasttranslator, license, currentcount, updatescount, rosettacount, lastparsed, "owner", pluralforms, variant, filename, rawimporter, daterawimport, rawimportstatus, rawfile, exportfile, exporttime, rawfilepublished, datecreated, latestsubmission) VALUES (9, 2, 98, NULL, ' Czech translation for mount removable devices as normal user
 Copyright (c) (c) 2005 Canonical Ltd, and Rosetta Contributors 2005
 This file is distributed under the same license as the mount removable devices as normal user package.
 FIRST AUTHOR <EMAIL@ADDRESS>, 2005.

', 'Project-Id-Version: mount removable devices as normal user
Report-Msgid-Bugs-To: martin.pitt@canonical.com
POT-Creation-Date: 2005-04-04 17:31+0200
PO-Revision-Date: 2005-02-10 15:15+0000
Last-Translator: Vlastimil Skacel <skacel@svtech.cz>
Language-Team: Czech <cs@li.org>
MIME-Version: 1.0
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: 8bit
X-Rosetta-Version: 0.1
Plural-Forms: nplurals=3; plural=n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2
X-Generator: Rosetta (http://launchpad.ubuntu.com/rosetta/)
', true, NULL, NULL, 56, 0, 0, NULL, 31, 3, NULL, NULL, 30, '2005-05-06 20:07:24.255804', 3, 13, NULL, NULL, NULL, '2005-06-06 08:59:54.249601', 202);
INSERT INTO pofile (id, potemplate, "language", description, topcomment, header, fuzzyheader, lasttranslator, license, currentcount, updatescount, rosettacount, lastparsed, "owner", pluralforms, variant, filename, rawimporter, daterawimport, rawimportstatus, rawfile, exportfile, exporttime, rawfilepublished, datecreated, latestsubmission) VALUES (10, 2, 302, NULL, ' Bokmål, Norwegian translation for pmount
 Copyright (c) (c) 2005 Canonical Ltd, and Rosetta Contributors 2005
 This file is distributed under the same license as the pmount package.
 FIRST AUTHOR <EMAIL@ADDRESS>, 2005.

', 'Project-Id-Version: pmount
Report-Msgid-Bugs-To: martin.pitt@canonical.com
POT-Creation-Date: 2005-04-04 17:31+0200
PO-Revision-Date: 2005-03-31 10:35+0000
Last-Translator: Sigurd Gartmann <sigurd-ubuntu@brogar.org>
Language-Team: Bokmål, Norwegian <nb@li.org>
MIME-Version: 1.0
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: 8bit
X-Rosetta-Version: 0.1
Plural-Forms: nplurals=2; plural=n != 1
X-Generator: Rosetta (http://launchpad.ubuntu.com/rosetta/)
', true, NULL, NULL, 63, 0, 0, NULL, 31, 2, NULL, NULL, 30, '2005-05-06 20:07:24.255804', 3, 12, NULL, NULL, NULL, '2005-06-06 08:59:54.248418', 139);
INSERT INTO pofile (id, potemplate, "language", description, topcomment, header, fuzzyheader, lasttranslator, license, currentcount, updatescount, rosettacount, lastparsed, "owner", pluralforms, variant, filename, rawimporter, daterawimport, rawimportstatus, rawfile, exportfile, exporttime, rawfilepublished, datecreated, latestsubmission) VALUES (11, 2, 387, NULL, ' Spanish translation for mount removable devices as normal user
 Copyright (c) (c) 2005 Canonical Ltd, and Rosetta Contributors 2005
 This file is distributed under the same license as the mount removable devices as normal user package.
 FIRST AUTHOR <EMAIL@ADDRESS>, 2005.

', 'Project-Id-Version: mount removable devices as normal user
Report-Msgid-Bugs-To: martin.pitt@canonical.com
POT-Creation-Date: 2005-04-04 17:31+0200
PO-Revision-Date: 2005-02-21 17:57+0000
Last-Translator: Aloriel <jorge.gonzalez.gonzalez@hispalinux.es>
Language-Team: Spanish <es@li.org>
MIME-Version: 1.0
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: 8bit
X-Rosetta-Version: 0.1
Plural-Forms: nplurals=2; plural=n != 1
X-Generator: Rosetta (http://launchpad.ubuntu.com/rosetta/)
', true, NULL, NULL, 54, 0, 0, NULL, 31, 2, NULL, NULL, 30, '2005-05-06 20:07:24.255804', 3, 18, NULL, NULL, NULL, '2005-06-06 08:59:54.229882', 503);
INSERT INTO pofile (id, potemplate, "language", description, topcomment, header, fuzzyheader, lasttranslator, license, currentcount, updatescount, rosettacount, lastparsed, "owner", pluralforms, variant, filename, rawimporter, daterawimport, rawimportstatus, rawfile, exportfile, exporttime, rawfilepublished, datecreated, latestsubmission) VALUES (12, 4, 387, NULL, ' traducción de es.po al Spanish
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
PO-Revision-Date: 2005-04-07 13:22+0000
Last-Translator: Carlos Perelló Marín <carlos@canonical.com>
Language-Team: Spanish <traductores@es.gnome.org>
MIME-Version: 1.0
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: 8bit
Report-Msgid-Bugs-To: serrador@hispalinux.es
X-Generator: Rosetta (http://launchpad.ubuntu.com/rosetta/)
Plural-Forms: nplurals=2; plural=(n != 1);
', true, NULL, NULL, 7, 1, 1, NULL, 31, 2, NULL, NULL, 13, '2005-05-06 21:05:21.272603', 3, 32, NULL, NULL, NULL, '2005-06-06 08:59:54.235169', 689);
INSERT INTO pofile (id, potemplate, "language", description, topcomment, header, fuzzyheader, lasttranslator, license, currentcount, updatescount, rosettacount, lastparsed, "owner", pluralforms, variant, filename, rawimporter, daterawimport, rawimportstatus, rawfile, exportfile, exporttime, rawfilepublished, datecreated, latestsubmission) VALUES (13, 5, 132, NULL, '
    Translators, if you are not familiar with the PO format, gettext
    documentation is worth reading, especially sections dedicated to
    this format, e.g. by running:
         info -n ''(gettext)PO Files''
         info -n ''(gettext)Header Entry''

    Some information specific to po-debconf are available at
            /usr/share/doc/po-debconf/README-trans
         or http://www.debian.org/intl/l10n/po-debconf/README-trans

    Developers do not need to manually edit POT or PO files.

', 'Project-Id-Version: mozilla 2:1.7.4-1
Report-Msgid-Bugs-To: 
POT-Creation-Date: 2004-07-11 16:16+0900
PO-Revision-Date: 2004-08-02 00:08+0200
Last-Translator: Denis Barbier <barbier@linuxfr.org>
Language-Team: French <debian-l10n-french@lists.debian.org>
MIME-Version: 1.0
Content-Type: text/plain; charset=ISO-8859-15
Content-Transfer-Encoding: 8bit
plural-forms: nplurals=2; plural=n > 1
', true, NULL, NULL, 9, 0, 0, NULL, 31, 2, NULL, NULL, 30, '2005-05-06 21:10:39.821363', 3, 19, NULL, NULL, NULL, '2005-06-06 08:59:54.243358', 577);
INSERT INTO pofile (id, potemplate, "language", description, topcomment, header, fuzzyheader, lasttranslator, license, currentcount, updatescount, rosettacount, lastparsed, "owner", pluralforms, variant, filename, rawimporter, daterawimport, rawimportstatus, rawfile, exportfile, exporttime, rawfilepublished, datecreated, latestsubmission) VALUES (14, 5, 112, NULL, '
    Translators, if you are not familiar with the PO format, gettext
    documentation is worth reading, especially sections dedicated to
    this format, e.g. by running:
         info -n ''(gettext)PO Files''
         info -n ''(gettext)Header Entry''

    Some information specific to po-debconf are available at
            /usr/share/doc/po-debconf/README-trans
         or http://www.debian.org/intl/l10n/po-debconf/README-trans

    Developers do not need to manually edit POT or PO files.

', 'Project-Id-Version: mozilla 2:1.6-3
POT-Creation-Date: 2004-07-11 16:16+0900
PO-Revision-Date: 2004-09-09 11:37+0100
Last-Translator: Luk Claes <luk.claes@ugent.be>
Language-Team: Debian l10n Dutch <debian-l10n-dutch@lists.debian.org>
MIME-Version: 1.0
Content-Type: text/plain; charset=iso-8859-1
Content-Transfer-Encoding: 8bit
plural-forms: nplurals=2; plural=n != 1
', true, NULL, NULL, 9, 0, 0, NULL, 31, 2, NULL, NULL, 30, '2005-05-06 21:10:39.821363', 3, 23, NULL, NULL, NULL, '2005-06-06 08:59:54.260522', 610);
INSERT INTO pofile (id, potemplate, "language", description, topcomment, header, fuzzyheader, lasttranslator, license, currentcount, updatescount, rosettacount, lastparsed, "owner", pluralforms, variant, filename, rawimporter, daterawimport, rawimportstatus, rawfile, exportfile, exporttime, rawfilepublished, datecreated, latestsubmission) VALUES (15, 5, 521, NULL, '
    Translators, if you are not familiar with the PO format, gettext
    documentation is worth reading, especially sections dedicated to
    this format, e.g. by running:
         info -n ''(gettext)PO Files''
         info -n ''(gettext)Header Entry''

    Some information specific to po-debconf are available at
            /usr/share/doc/po-debconf/README-trans
         or http://www.debian.org/intl/l10n/po-debconf/README-trans

    Developers do not need to manually edit POT or PO files.

', 'Project-Id-Version: mozilla
Report-Msgid-Bugs-To: 
POT-Creation-Date: 2004-07-11 16:16+0900
PO-Revision-Date: 2004-07-25 16:17-0300
Last-Translator: André Luís Lopes <andrelop@debian.org>
Language-Team: Debian-BR Porject <debian-l10n-portuguese@lists.debian.org>
MIME-Version: 1.0
Content-Type: text/plain; charset=ISO-8859-1
Content-Transfer-Encoding: 8bit
plural-forms: nplurals=2; plural=n > 1
', true, NULL, NULL, 9, 0, 0, NULL, 31, 2, NULL, NULL, 30, '2005-05-06 21:10:39.821363', 3, 20, NULL, NULL, NULL, '2005-06-06 08:59:54.24721', 586);
INSERT INTO pofile (id, potemplate, "language", description, topcomment, header, fuzzyheader, lasttranslator, license, currentcount, updatescount, rosettacount, lastparsed, "owner", pluralforms, variant, filename, rawimporter, daterawimport, rawimportstatus, rawfile, exportfile, exporttime, rawfilepublished, datecreated, latestsubmission) VALUES (16, 5, 143, NULL, '
    Translators, if you are not familiar with the PO format, gettext
    documentation is worth reading, especially sections dedicated to
    this format, e.g. by running:
         info -n ''(gettext)PO Files''
         info -n ''(gettext)Header Entry''

    Some information specific to po-debconf are available at
            /usr/share/doc/po-debconf/README-trans
         or http://www.debian.org/intl/l10n/po-debconf/README-trans

    Developers do not need to manually edit POT or PO files.

', 'Project-Id-Version: PACKAGE VERSION
Report-Msgid-Bugs-To: 
POT-Creation-Date: 2004-07-11 16:16+0900
PO-Revision-Date: 2004-07-24 15:24+0200
Last-Translator: Helge Kreutzmann <kreutzm@itp.uni-hannover.de>
Language-Team: de <debian-l10n-german@lists.debian.org>
MIME-Version: 1.0
Content-Type: text/plain; charset=ISO-8859-15
Content-Transfer-Encoding: 8bit
plural-forms: nplurals=2; plural=n != 1
', true, NULL, NULL, 9, 0, 0, NULL, 31, 2, NULL, NULL, 30, '2005-05-06 21:10:39.821363', 3, 31, NULL, NULL, NULL, '2005-06-06 08:59:54.253299', 676);
INSERT INTO pofile (id, potemplate, "language", description, topcomment, header, fuzzyheader, lasttranslator, license, currentcount, updatescount, rosettacount, lastparsed, "owner", pluralforms, variant, filename, rawimporter, daterawimport, rawimportstatus, rawfile, exportfile, exporttime, rawfilepublished, datecreated, latestsubmission) VALUES (17, 5, 427, NULL, ' Turkish translation of mozilla.
 This file is distributed under the same license as the mozilla package.
 Mehmet Türker <mturker@innova.com.tr>, 2004.

', 'Project-Id-Version: mozilla
Report-Msgid-Bugs-To: 
POT-Creation-Date: 2004-07-11 16:16+0900
PO-Revision-Date: 2004-04-25 14:47+0300
Last-Translator: Mehmet Türker <EMAIL>
Language-Team: Turkish <debian-l10n-turkish@lists.debian.org>
MIME-Version: 1.0
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: 8bit
Plural-Forms:  nplurals=1; plural=0;
', true, NULL, NULL, 6, 0, 0, NULL, 31, 1, NULL, NULL, 30, '2005-05-06 21:10:39.821363', 3, 30, NULL, NULL, NULL, '2005-06-06 08:59:54.250735', 670);
INSERT INTO pofile (id, potemplate, "language", description, topcomment, header, fuzzyheader, lasttranslator, license, currentcount, updatescount, rosettacount, lastparsed, "owner", pluralforms, variant, filename, rawimporter, daterawimport, rawimportstatus, rawfile, exportfile, exporttime, rawfilepublished, datecreated, latestsubmission) VALUES (18, 5, 193, NULL, ' Italian translation of debconf for mozilla.
 This file is distributed under the same license as the mozilla package.
 Copyright 2004 by Valentina Commissari <ayor@quaqua.net>.
', 'Project-Id-Version: mozilla 1.7.3-5
POT-Creation-Date: 2004-07-11 16:16+0900
PO-Revision-Date: 2004-11-01 13:30+0100
Last-Translator: Valentina Commissari <tsukimi@quaqua.net>
Language-Team: Italian <debian-l10n-italian@lists.debian.org>
MIME-Version: 1.0
Content-Type: text/plain; charset=iso-8859-1
Content-Transfer-Encoding: 8bit
X-Poedit-Language: Italian
X-Poedit-Country: ITALY
plural-forms: nplurals=2; plural=n != 1
', true, NULL, NULL, 9, 0, 0, NULL, 31, 2, NULL, NULL, 30, '2005-05-06 21:10:39.821363', 3, 29, NULL, NULL, NULL, '2005-06-06 08:59:54.246003', 661);
INSERT INTO pofile (id, potemplate, "language", description, topcomment, header, fuzzyheader, lasttranslator, license, currentcount, updatescount, rosettacount, lastparsed, "owner", pluralforms, variant, filename, rawimporter, daterawimport, rawimportstatus, rawfile, exportfile, exporttime, rawfilepublished, datecreated, latestsubmission) VALUES (19, 5, 100, NULL, '
    Translators, if you are not familiar with the PO format, gettext
    documentation is worth reading, especially sections dedicated to
    this format, e.g. by running:
         info -n ''(gettext)PO Files''
         info -n ''(gettext)Header Entry''

    Some information specific to po-debconf are available at
            /usr/share/doc/po-debconf/README-trans
         or http://www.debian.org/intl/l10n/po-debconf/README-trans

    Developers do not need to manually edit POT or PO files.

', 'Project-Id-Version: mozilla 2:1.7.1-4
Report-Msgid-Bugs-To: 
POT-Creation-Date: 2004-07-11 16:16+0900
PO-Revision-Date: 2004-07-31 22:49+0200
Last-Translator: Morten Brix Pedersen <morten@wtf.dk>
Language-Team: debian-l10n-danish <debian-l10n-danish@lists.debian.org>
MIME-Version: 1.0
Content-Type: text/plain; charset=ISO-8859-1
Content-Transfer-Encoding: 8bit
X-Poedit-Language: Italian
X-Poedit-Country: ITALY
plural-forms: nplurals=2; plural=n != 1
', true, NULL, NULL, 9, 0, 0, NULL, 31, 2, NULL, NULL, 30, '2005-05-06 21:10:39.821363', 3, 25, NULL, NULL, NULL, '2005-06-06 08:59:54.24466', 628);
INSERT INTO pofile (id, potemplate, "language", description, topcomment, header, fuzzyheader, lasttranslator, license, currentcount, updatescount, rosettacount, lastparsed, "owner", pluralforms, variant, filename, rawimporter, daterawimport, rawimportstatus, rawfile, exportfile, exporttime, rawfilepublished, datecreated, latestsubmission) VALUES (20, 5, 241, NULL, ' Lithuanian translation of mozilla.
 This file is distributed under the same license as the mozilla package.
 Kęstutis Biliūnas <kebil@kaunas.init.lt>, 2004.

', 'Project-Id-Version: mozilla
Report-Msgid-Bugs-To: 
POT-Creation-Date: 2004-07-11 16:16+0900
PO-Revision-Date: 2004-10-24 14:14+0300
Last-Translator: Kęstutis Biliūnas <kebil@kaunas.init.lt>
Language-Team: Lithuanian <komp_lt@konferencijos.lt>
MIME-Version: 1.0
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: 8bit
X-Generator: KBabel 1.3.1
plural-forms: nplurals=3; plural=n%10==1 && n%100!=11 ? 0 : n%10>=2 && (n%100<10 || n%100>=20) ? 1 : 2
', true, NULL, NULL, 9, 0, 0, NULL, 31, 3, NULL, NULL, 30, '2005-05-06 21:10:39.821363', 3, 28, NULL, NULL, NULL, '2005-06-06 08:59:54.232379', 652);
INSERT INTO pofile (id, potemplate, "language", description, topcomment, header, fuzzyheader, lasttranslator, license, currentcount, updatescount, rosettacount, lastparsed, "owner", pluralforms, variant, filename, rawimporter, daterawimport, rawimportstatus, rawfile, exportfile, exporttime, rawfilepublished, datecreated, latestsubmission) VALUES (21, 5, 98, NULL, '
    Translators, if you are not familiar with the PO format, gettext
    documentation is worth reading, especially sections dedicated to
    this format, e.g. by running:
         info -n ''(gettext)PO Files''
         info -n ''(gettext)Header Entry''

    Some information specific to po-debconf are available at
            /usr/share/doc/po-debconf/README-trans
         or http://www.debian.org/intl/l10n/po-debconf/README-trans

    Developers do not need to manually edit POT or PO files.

', 'Project-Id-Version: mozilla
Report-Msgid-Bugs-To: 
POT-Creation-Date: 2004-07-11 16:16+0900
PO-Revision-Date: 2004-07-22 17:49+0200
Last-Translator: Miroslav Kure <kurem@debian.cz>
Language-Team: Czech <provoz@debian.cz>
MIME-Version: 1.0
Content-Type: text/plain; charset=ISO-8859-2
Content-Transfer-Encoding: 8bit
plural-forms: nplurals=3; plural=n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2
', true, NULL, NULL, 9, 0, 0, NULL, 31, 3, NULL, NULL, 30, '2005-05-06 21:10:39.821363', 3, 24, NULL, NULL, NULL, '2005-06-06 08:59:54.2394', 619);
INSERT INTO pofile (id, potemplate, "language", description, topcomment, header, fuzzyheader, lasttranslator, license, currentcount, updatescount, rosettacount, lastparsed, "owner", pluralforms, variant, filename, rawimporter, daterawimport, rawimportstatus, rawfile, exportfile, exporttime, rawfilepublished, datecreated, latestsubmission) VALUES (22, 5, 129, NULL, '  translation of fi.po to Finnish
  mozilla translation

    Translators, if you are not familiar with the PO format, gettext
    documentation is worth reading, especially sections dedicated to
    this format, e.g. by running:
         info -n ''(gettext)PO Files''
         info -n ''(gettext)Header Entry''

    Some information specific to po-debconf are available at
            /usr/share/doc/po-debconf/README-trans
         or http://www.debian.org/intl/l10n/po-debconf/README-trans

    Developers do not need to manually edit POT or PO files.

 Matti Pöllä <mpo@iki.fi>, 2004.
', 'Project-Id-Version: mozilla
Report-Msgid-Bugs-To: 
POT-Creation-Date: 2004-07-11 16:16+0900
PO-Revision-Date: 2004-08-15 22:41+0300
Last-Translator: Matti Pöllä <mpo@iki.fi>
Language-Team: Finnish <debian-l10n-finnish@lists.debian.org>
MIME-Version: 1.0
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: 8bit
plural-forms: nplurals=2; plural=n != 1
', true, NULL, NULL, 9, 0, 0, NULL, 31, 2, NULL, NULL, 30, '2005-05-06 21:10:39.821363', 3, 26, NULL, NULL, NULL, '2005-06-06 08:59:54.242018', 637);
INSERT INTO pofile (id, potemplate, "language", description, topcomment, header, fuzzyheader, lasttranslator, license, currentcount, updatescount, rosettacount, lastparsed, "owner", pluralforms, variant, filename, rawimporter, daterawimport, rawimportstatus, rawfile, exportfile, exporttime, rawfilepublished, datecreated, latestsubmission) VALUES (23, 5, 148, NULL, '
    Translators, if you are not familiar with the PO format, gettext
    documentation is worth reading, especially sections dedicated to
    this format, e.g. by running:
         info -n ''(gettext)PO Files''
         info -n ''(gettext)Header Entry''

    Some information specific to po-debconf are available at
            /usr/share/doc/po-debconf/README-trans
         or http://www.debian.org/intl/l10n/po-debconf/README-trans

    Developers do not need to manually edit POT or PO files.

', 'Project-Id-Version: PACKAGE VERSION
Report-Msgid-Bugs-To: 
POT-Creation-Date: 2004-07-11 16:16+0900
PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE
Last-Translator: FULL NAME <EMAIL@ADDRESS>
Language-Team: LANGUAGE <LL@li.org>
MIME-Version: 1.0
Content-Type: text/plain; charset=ISO-8859-15
Content-Transfer-Encoding: 8bit
plural-forms: nplurals=1; plural=0
', true, NULL, NULL, 3, 0, 0, NULL, 31, 1, NULL, NULL, 30, '2005-05-06 21:10:39.821363', 3, 27, NULL, NULL, NULL, '2005-06-06 08:59:54.258136', 649);
INSERT INTO pofile (id, potemplate, "language", description, topcomment, header, fuzzyheader, lasttranslator, license, currentcount, updatescount, rosettacount, lastparsed, "owner", pluralforms, variant, filename, rawimporter, daterawimport, rawimportstatus, rawfile, exportfile, exporttime, rawfilepublished, datecreated, latestsubmission) VALUES (24, 5, 196, NULL, '
    Translators, if you are not familiar with the PO format, gettext
    documentation is worth reading, especially sections dedicated to
    this format, e.g. by running:
         info -n ''(gettext)PO Files''
         info -n ''(gettext)Header Entry''

    Some information specific to po-debconf are available at
            /usr/share/doc/po-debconf/README-trans
         or http://www.debian.org/intl/l10n/po-debconf/README-trans

    Developers do not need to manually edit POT or PO files.

', 'Project-Id-Version: PACKAGE VERSION
Report-Msgid-Bugs-To: 
POT-Creation-Date: 2004-07-11 16:16+0900
PO-Revision-Date: 2004-07-20 02:46+0900
Last-Translator: FULL NAME <EMAIL@ADDRESS>
Language-Team: LANGUAGE <LL@li.org>
MIME-Version: 1.0
Content-Type: text/plain; charset=EUC-JP
Content-Transfer-Encoding: 8bit
plural-forms: nplurals=1; plural=0
', true, NULL, NULL, 9, 0, 0, NULL, 31, 1, NULL, NULL, 30, '2005-05-06 21:10:39.821363', 3, 21, NULL, NULL, NULL, '2005-06-06 08:59:54.233769', 595);
INSERT INTO pofile (id, potemplate, "language", description, topcomment, header, fuzzyheader, lasttranslator, license, currentcount, updatescount, rosettacount, lastparsed, "owner", pluralforms, variant, filename, rawimporter, daterawimport, rawimportstatus, rawfile, exportfile, exporttime, rawfilepublished, datecreated, latestsubmission) VALUES (25, 5, 387, NULL, '
    Translators, if you are not familiar with the PO format, gettext
    documentation is worth reading, especially sections dedicated to
    this format, e.g. by running:
         info -n ''(gettext)PO Files''
         info -n ''(gettext)Header Entry''

    Some information specific to po-debconf are available at
            /usr/share/doc/po-debconf/README-trans
         or http://www.debian.org/intl/l10n/po-debconf/README-trans

    Developers do not need to manually edit POT or PO files.

 Carlos Valdivia Yagüe <valyag@dat.etsit.upm.es>, 2003

', 'Project-Id-Version: mozilla-browser 1.4-4
Report-Msgid-Bugs-To: 
POT-Creation-Date: 2004-07-11 16:16+0900
PO-Revision-Date: 2003-09-20 20:00+0200
Last-Translator: Carlos Valdivia Yagüe <valyag@dat.etsit.upm.es>
Language-Team: Debian L10n Spanish <debian-l10n-spanish@lists.debian.org>
MIME-Version: 1.0
Content-Type: text/plain; charset=ISO-8859-15
Content-Transfer-Encoding: 8bit
plural-forms: nplurals=2; plural=n != 1
', true, NULL, NULL, 6, 0, 0, NULL, 31, 2, NULL, NULL, 30, '2005-05-06 21:10:39.821363', 3, 22, NULL, NULL, NULL, '2005-06-06 08:59:54.251898', 604);
INSERT INTO pofile (id, potemplate, "language", description, topcomment, header, fuzzyheader, lasttranslator, license, currentcount, updatescount, rosettacount, lastparsed, "owner", pluralforms, variant, filename, rawimporter, daterawimport, rawimportstatus, rawfile, exportfile, exporttime, rawfilepublished, datecreated, latestsubmission) VALUES (28, 4, 454, NULL, ' Xhosa translation for evolution
 Copyright (c) (c) 2005 Canonical Ltd, and Rosetta Contributors 2005
 This file is distributed under the same license as the evolution package.
 FIRST AUTHOR <EMAIL@ADDRESS>, 2005.

', 'Project-Id-Version: evolution
Report-Msgid-Bugs-To: FULL NAME <EMAIL@ADDRESS>
POT-Creation-Date: 2005-05-06 20:39:27+00:00
PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE
Last-Translator: FULL NAME <EMAIL@ADDRESS>
Language-Team: Xhosa <xh@li.org>
MIME-Version: 1.0
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: 8bit
X-Rosetta-Version: 0.1
Plural-Forms: nplurals=2; plural=n != 1
', true, NULL, NULL, 0, 0, 0, NULL, 31, 2, NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, false, '2005-06-15 19:26:21.919196', NULL);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'pofile'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'pomsgset'::pg_catalog.regclass;

INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (1, 1, 1, true, false, false, '', 1, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (2, 2, 1, true, false, false, '', 2, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (3, 3, 1, true, false, true, '', 3, true, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (4, 4, 1, false, false, false, '', 4, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (5, 5, 1, true, false, false, '', 5, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (6, 6, 1, false, false, false, '', 6, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (7, 7, 1, false, false, false, '', 7, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (8, 8, 1, false, false, false, '', 8, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (9, 9, 1, false, false, false, '', 9, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (10, 10, 1, false, false, false, '', 10, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (11, 11, 1, false, false, false, '', 11, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (12, 12, 1, false, false, false, '', 12, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (13, 13, 1, false, false, false, '', 13, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (14, 14, 1, true, false, false, ' This is an example of commenttext for a multiline msgset', 14, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (15, 15, 1, true, false, false, '', 15, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (16, 16, 1, true, false, false, '', 16, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (17, 17, 1, false, false, true, '', 17, true, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (18, 18, 1, true, false, false, ' start po-group: common
 start po-group: common', 18, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (19, 19, 1, false, false, false, '', 19, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (20, 20, 1, false, false, false, '', 20, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (21, 21, 1, false, false, false, '', 21, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (22, 22, 1, true, true, false, '', 23, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (23, 1, 7, true, false, false, '', 67, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (24, 2, 7, true, false, false, '', 68, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (25, 3, 7, true, false, false, '', 69, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (26, 4, 7, true, false, false, '', 70, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (27, 5, 7, true, false, false, '', 71, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (28, 6, 7, true, false, false, '', 72, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (29, 7, 7, true, false, false, '', 73, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (30, 8, 7, true, false, false, '', 74, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (31, 9, 7, true, false, false, '', 75, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (32, 10, 7, true, false, false, '', 76, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (33, 11, 7, true, false, false, '', 77, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (34, 12, 7, true, false, false, '', 78, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (35, 13, 7, true, false, false, '', 79, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (36, 14, 7, true, false, false, '', 80, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (37, 15, 7, true, false, false, '', 81, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (38, 16, 7, true, false, false, '', 82, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (39, 17, 7, true, false, false, '', 83, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (40, 18, 7, true, false, false, '', 84, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (41, 19, 7, true, false, false, '', 85, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (42, 20, 7, true, false, false, '', 86, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (43, 21, 7, true, false, false, '', 87, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (44, 22, 7, true, false, false, '', 88, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (45, 23, 7, true, false, false, '', 89, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (46, 24, 7, true, false, false, '', 90, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (47, 25, 7, true, false, false, '', 91, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (48, 26, 7, true, false, false, '', 92, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (49, 27, 7, true, false, false, '', 93, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (50, 28, 7, true, false, false, '', 94, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (51, 29, 7, true, false, false, '', 95, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (52, 30, 7, true, false, false, '', 96, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (53, 31, 7, true, false, false, '', 97, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (54, 32, 7, true, false, false, '', 98, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (55, 33, 7, true, false, false, '', 99, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (56, 34, 7, true, false, false, '', 100, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (57, 35, 7, true, false, false, '', 101, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (58, 36, 7, true, false, false, '', 102, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (59, 37, 7, true, false, false, '', 103, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (60, 38, 7, true, false, false, '', 104, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (61, 39, 7, true, false, false, '', 105, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (62, 40, 7, true, false, false, '', 106, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (63, 41, 7, true, false, false, '', 107, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (64, 42, 7, true, false, false, '', 108, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (65, 43, 7, true, false, false, '', 109, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (66, 44, 7, true, false, false, '', 110, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (67, 45, 7, true, false, false, '', 111, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (68, 46, 7, true, false, false, '', 112, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (69, 47, 7, true, false, false, '', 113, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (70, 48, 7, true, false, false, '', 114, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (71, 49, 7, true, false, false, '', 115, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (72, 50, 7, true, false, false, '', 116, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (73, 51, 7, true, false, false, '', 117, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (74, 52, 7, true, false, false, '', 118, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (75, 53, 7, true, false, false, '', 119, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (76, 54, 7, true, false, false, '', 120, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (77, 55, 7, true, false, false, '', 121, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (78, 56, 7, true, false, false, '', 122, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (79, 57, 7, true, false, false, '', 123, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (80, 58, 7, true, false, false, '', 124, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (81, 59, 7, true, false, false, '', 125, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (82, 60, 7, true, false, false, '', 126, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (83, 61, 7, true, false, false, '', 127, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (84, 62, 7, true, false, false, '', 128, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (85, 63, 7, true, false, false, '', 129, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (86, 1, 5, true, false, false, '', 67, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (87, 2, 5, true, false, false, '', 68, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (88, 3, 5, true, false, false, '', 69, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (89, 4, 5, true, false, false, '', 70, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (90, 5, 5, true, false, false, '', 71, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (91, 6, 5, true, false, false, '', 72, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (92, 7, 5, true, false, false, '', 73, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (93, 8, 5, true, false, false, '', 74, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (94, 9, 5, true, false, false, '', 75, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (95, 10, 5, true, false, false, '', 76, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (96, 11, 5, true, false, false, '', 77, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (97, 12, 5, true, false, false, '', 78, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (98, 13, 5, true, false, false, '', 79, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (99, 14, 5, true, false, false, '', 80, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (100, 15, 5, true, false, false, '', 81, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (101, 16, 5, true, false, false, '', 82, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (102, 17, 5, true, false, false, '', 83, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (103, 18, 5, true, false, false, '', 84, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (104, 19, 5, true, false, false, '', 85, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (105, 20, 5, true, false, false, '', 86, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (106, 21, 5, true, false, false, '', 87, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (107, 22, 5, true, false, false, '', 88, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (108, 23, 5, true, false, false, '', 89, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (109, 24, 5, true, false, false, '', 90, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (110, 25, 5, true, false, false, '', 91, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (111, 26, 5, true, false, false, '', 92, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (112, 27, 5, true, false, false, '', 93, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (113, 28, 5, true, false, false, '', 94, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (114, 29, 5, true, false, false, '', 95, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (115, 30, 5, true, false, true, '', 96, true, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (116, 31, 5, true, false, false, '', 97, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (117, 32, 5, true, false, false, '', 98, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (118, 33, 5, true, false, false, '', 99, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (119, 34, 5, true, false, false, '', 100, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (120, 35, 5, true, false, false, '', 101, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (121, 36, 5, true, false, false, '', 102, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (122, 37, 5, true, false, false, '', 103, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (123, 38, 5, true, false, false, '', 104, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (124, 39, 5, true, false, false, '', 105, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (125, 40, 5, true, false, false, '', 106, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (126, 41, 5, true, false, false, '', 107, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (127, 42, 5, true, false, false, '', 108, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (128, 43, 5, true, false, false, '', 109, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (129, 44, 5, true, false, false, '', 110, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (130, 45, 5, true, false, false, '', 111, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (131, 46, 5, true, false, false, '', 112, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (132, 47, 5, true, false, false, '', 113, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (133, 48, 5, true, false, false, '', 114, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (134, 49, 5, true, false, false, '', 115, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (135, 50, 5, true, false, false, '', 116, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (136, 51, 5, true, false, false, '', 117, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (137, 52, 5, true, false, false, '', 118, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (138, 53, 5, true, false, false, '', 119, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (139, 54, 5, true, false, false, '', 120, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (140, 55, 5, true, false, false, '', 121, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (141, 56, 5, true, false, false, '', 122, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (142, 57, 5, true, false, false, '', 123, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (143, 58, 5, true, false, false, '', 124, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (144, 59, 5, true, false, false, '', 125, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (145, 60, 5, true, false, false, '', 126, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (146, 61, 5, true, false, false, '', 127, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (147, 62, 5, true, false, false, '', 128, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (148, 63, 5, true, false, false, '', 129, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (149, 1, 10, true, false, false, '', 67, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (150, 2, 10, true, false, false, '', 68, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (151, 3, 10, true, false, false, '', 69, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (152, 4, 10, true, false, false, '', 70, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (153, 5, 10, true, false, false, '', 71, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (154, 6, 10, true, false, false, '', 72, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (155, 7, 10, true, false, false, '', 73, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (156, 8, 10, true, false, false, '', 74, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (157, 9, 10, true, false, false, '', 75, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (158, 10, 10, true, false, false, '', 76, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (159, 11, 10, true, false, false, '', 77, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (160, 12, 10, true, false, false, '', 78, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (161, 13, 10, true, false, false, '', 79, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (162, 14, 10, true, false, false, '', 80, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (163, 15, 10, true, false, false, '', 81, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (164, 16, 10, true, false, false, '', 82, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (165, 17, 10, true, false, false, '', 83, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (166, 18, 10, true, false, false, '', 84, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (167, 19, 10, true, false, false, '', 85, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (168, 20, 10, true, false, false, '', 86, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (169, 21, 10, true, false, false, '', 87, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (170, 22, 10, true, false, false, '', 88, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (171, 23, 10, true, false, false, '', 89, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (172, 24, 10, true, false, false, '', 90, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (173, 25, 10, true, false, false, '', 91, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (174, 26, 10, true, false, false, '', 92, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (175, 27, 10, true, false, false, '', 93, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (176, 28, 10, true, false, false, '', 94, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (177, 29, 10, true, false, false, '', 95, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (178, 30, 10, true, false, false, '', 96, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (179, 31, 10, true, false, false, '', 97, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (180, 32, 10, true, false, false, '', 98, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (181, 33, 10, true, false, false, '', 99, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (182, 34, 10, true, false, false, '', 100, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (183, 35, 10, true, false, false, '', 101, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (184, 36, 10, true, false, false, '', 102, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (185, 37, 10, true, false, false, '', 103, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (186, 38, 10, true, false, false, '', 104, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (187, 39, 10, true, false, false, '', 105, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (188, 40, 10, true, false, false, '', 106, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (189, 41, 10, true, false, false, '', 107, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (190, 42, 10, true, false, false, '', 108, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (191, 43, 10, true, false, false, '', 109, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (192, 44, 10, true, false, false, '', 110, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (193, 45, 10, true, false, false, '', 111, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (194, 46, 10, true, false, false, '', 112, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (195, 47, 10, true, false, false, '', 113, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (196, 48, 10, true, false, false, '', 114, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (197, 49, 10, true, false, false, '', 115, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (198, 50, 10, true, false, false, '', 116, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (199, 51, 10, true, false, false, '', 117, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (200, 52, 10, true, false, false, '', 118, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (201, 53, 10, true, false, false, '', 119, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (202, 54, 10, true, false, false, '', 120, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (203, 55, 10, true, false, false, '', 121, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (204, 56, 10, true, false, false, '', 122, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (205, 57, 10, true, false, false, '', 123, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (206, 58, 10, true, false, false, '', 124, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (207, 59, 10, true, false, false, '', 125, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (208, 60, 10, true, false, false, '', 126, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (209, 61, 10, true, false, false, '', 127, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (210, 62, 10, true, false, false, '', 128, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (211, 63, 10, true, false, false, '', 129, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (212, 1, 9, true, false, false, '', 67, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (213, 2, 9, true, false, false, '', 68, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (214, 3, 9, true, false, false, '', 69, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (215, 4, 9, true, false, true, '', 70, true, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (216, 5, 9, true, false, false, '', 71, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (217, 6, 9, true, false, false, '', 72, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (218, 7, 9, true, false, false, '', 73, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (219, 8, 9, true, false, false, '', 74, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (220, 9, 9, true, false, false, '', 75, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (221, 10, 9, true, false, false, '', 76, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (222, 11, 9, true, false, true, '', 77, true, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (223, 12, 9, true, false, false, '', 78, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (224, 13, 9, true, false, false, '', 79, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (225, 14, 9, true, false, false, '', 80, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (226, 15, 9, true, false, false, '', 81, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (227, 16, 9, true, false, false, '', 82, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (228, 17, 9, true, false, false, '', 83, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (229, 18, 9, true, false, false, '', 84, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (230, 19, 9, true, false, false, '', 85, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (231, 20, 9, true, false, false, '', 86, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (232, 21, 9, true, false, false, '', 87, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (233, 22, 9, true, false, false, '', 88, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (234, 23, 9, true, false, false, '', 89, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (235, 24, 9, true, false, false, '', 90, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (236, 25, 9, true, false, false, '', 91, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (237, 26, 9, true, false, false, '', 92, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (238, 27, 9, true, false, false, '', 93, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (239, 28, 9, true, false, true, '', 94, true, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (240, 29, 9, true, false, false, '', 95, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (241, 30, 9, true, false, false, '', 96, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (242, 31, 9, true, false, false, '', 97, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (243, 32, 9, true, false, false, '', 98, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (244, 33, 9, true, false, false, '', 99, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (245, 34, 9, true, false, false, '', 100, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (246, 35, 9, true, false, false, '', 101, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (247, 36, 9, true, false, false, '', 102, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (248, 37, 9, true, false, false, '', 103, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (249, 38, 9, true, false, false, '', 104, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (250, 39, 9, true, false, false, '', 105, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (251, 40, 9, true, false, false, '', 106, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (252, 41, 9, true, false, false, '', 107, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (253, 42, 9, true, false, false, '', 108, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (254, 43, 9, true, false, false, '', 109, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (255, 44, 9, true, false, false, '', 110, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (256, 45, 9, true, false, false, '', 111, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (257, 46, 9, true, false, false, '', 112, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (258, 47, 9, true, false, false, '', 113, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (259, 48, 9, true, false, false, '', 114, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (260, 49, 9, true, false, false, '', 115, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (261, 50, 9, true, false, false, '', 116, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (262, 51, 9, true, false, false, '', 117, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (263, 52, 9, true, false, false, '', 118, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (264, 53, 9, true, false, false, '', 119, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (265, 54, 9, true, false, false, '', 120, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (266, 55, 9, true, false, false, '', 121, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (267, 56, 9, true, false, false, '', 122, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (268, 57, 9, true, false, false, '', 123, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (269, 58, 9, true, false, false, '', 124, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (270, 59, 9, true, false, false, '', 125, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (271, 60, 9, true, false, true, '', 126, true, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (272, 61, 9, true, false, true, '', 127, true, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (273, 62, 9, true, false, true, '', 128, true, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (274, 63, 9, true, false, true, '', 129, true, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (275, 1, 3, true, false, false, '', 67, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (276, 2, 3, true, false, false, '', 68, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (277, 3, 3, true, false, false, '', 69, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (278, 4, 3, true, false, false, '', 70, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (279, 5, 3, true, false, false, '', 71, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (280, 6, 3, true, false, false, '', 72, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (281, 7, 3, true, false, false, '', 73, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (282, 8, 3, true, false, false, '', 74, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (283, 9, 3, true, false, false, '', 75, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (284, 10, 3, true, false, false, '', 76, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (285, 11, 3, true, false, false, '', 77, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (286, 12, 3, true, false, false, '', 78, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (287, 13, 3, true, false, false, '', 79, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (288, 14, 3, true, false, false, '', 80, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (289, 15, 3, true, false, false, '', 81, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (290, 16, 3, true, false, false, '', 82, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (291, 17, 3, true, false, false, '', 83, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (292, 18, 3, true, false, false, '', 84, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (293, 19, 3, true, false, false, '', 85, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (294, 20, 3, true, false, false, '', 86, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (295, 21, 3, true, false, false, '', 87, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (296, 22, 3, true, false, false, '', 88, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (297, 23, 3, true, false, false, '', 89, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (298, 24, 3, true, false, false, '', 90, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (299, 25, 3, true, false, false, '', 91, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (300, 26, 3, true, false, false, '', 92, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (301, 27, 3, true, false, false, '', 93, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (302, 28, 3, true, false, false, '', 94, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (303, 29, 3, true, false, false, '', 95, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (304, 30, 3, true, false, false, '', 96, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (305, 31, 3, true, false, false, '', 97, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (306, 32, 3, true, false, false, '', 98, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (307, 33, 3, true, false, false, '', 99, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (308, 34, 3, true, false, false, '', 100, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (309, 35, 3, true, false, false, '', 101, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (310, 36, 3, true, false, false, '', 102, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (311, 37, 3, true, false, false, '', 103, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (312, 38, 3, true, false, false, '', 104, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (313, 39, 3, true, false, false, '', 105, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (314, 40, 3, true, false, false, '', 106, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (315, 41, 3, true, false, false, '', 107, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (316, 42, 3, true, false, false, '', 108, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (317, 43, 3, true, false, false, '', 109, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (318, 44, 3, true, false, false, '', 110, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (319, 45, 3, true, false, false, '', 111, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (320, 46, 3, true, false, false, '', 112, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (321, 47, 3, true, false, false, '', 113, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (322, 48, 3, true, false, false, '', 114, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (323, 49, 3, true, false, false, '', 115, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (324, 50, 3, true, false, false, '', 116, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (325, 51, 3, true, false, false, '', 117, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (326, 52, 3, true, false, false, '', 118, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (327, 53, 3, true, false, false, '', 119, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (328, 54, 3, true, false, false, '', 120, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (329, 55, 3, true, false, false, '', 121, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (330, 56, 3, true, false, false, '', 122, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (331, 57, 3, true, false, false, '', 123, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (332, 58, 3, true, false, false, '', 124, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (333, 59, 3, true, false, false, '', 125, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (334, 60, 3, true, false, false, '', 126, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (335, 61, 3, true, false, false, '', 127, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (336, 62, 3, true, false, false, '', 128, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (337, 63, 3, true, false, false, '', 129, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (338, 1, 4, true, false, false, '', 67, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (339, 2, 4, true, false, false, '', 68, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (340, 3, 4, true, false, false, '', 69, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (341, 4, 4, true, false, false, '', 70, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (342, 5, 4, true, false, false, '', 71, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (343, 6, 4, true, false, false, '', 72, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (344, 7, 4, true, false, false, '', 73, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (345, 8, 4, true, false, false, '', 74, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (346, 9, 4, true, false, false, '', 75, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (347, 10, 4, true, false, false, '', 76, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (348, 11, 4, true, false, false, '', 77, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (349, 12, 4, true, false, false, '', 78, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (350, 13, 4, true, false, false, '', 79, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (351, 14, 4, true, false, false, '', 80, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (352, 15, 4, true, false, false, '', 81, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (353, 16, 4, true, false, false, '', 82, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (354, 17, 4, true, false, false, '', 83, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (355, 18, 4, true, false, false, '', 84, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (356, 19, 4, true, false, false, '', 85, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (357, 20, 4, true, false, false, '', 86, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (358, 21, 4, true, false, false, '', 87, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (359, 22, 4, true, false, false, '', 88, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (360, 23, 4, true, false, false, '', 89, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (361, 24, 4, true, false, false, '', 90, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (362, 25, 4, true, false, false, '', 91, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (363, 26, 4, true, false, false, '', 92, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (364, 27, 4, true, false, false, '', 93, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (365, 28, 4, true, false, false, '', 94, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (366, 29, 4, true, false, false, '', 95, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (367, 30, 4, true, false, false, '', 96, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (368, 31, 4, true, false, false, '', 97, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (369, 32, 4, true, false, false, '', 98, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (370, 33, 4, true, false, false, '', 99, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (371, 34, 4, true, false, false, '', 100, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (372, 35, 4, true, false, false, '', 101, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (373, 36, 4, true, false, false, '', 102, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (374, 37, 4, true, false, false, '', 103, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (375, 38, 4, true, false, false, '', 104, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (376, 39, 4, true, false, false, '', 105, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (377, 40, 4, true, false, false, '', 106, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (378, 41, 4, true, false, false, '', 107, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (379, 42, 4, true, false, false, '', 108, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (380, 43, 4, true, false, false, '', 109, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (381, 44, 4, true, false, false, '', 110, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (382, 45, 4, true, false, false, '', 111, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (383, 46, 4, true, false, false, '', 112, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (384, 47, 4, true, false, false, '', 113, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (385, 48, 4, true, false, false, '', 114, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (386, 49, 4, true, false, false, '', 115, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (387, 50, 4, true, false, false, '', 116, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (388, 51, 4, true, false, false, '', 117, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (389, 52, 4, true, false, false, '', 118, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (390, 53, 4, true, false, false, '', 119, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (391, 54, 4, true, false, false, '', 120, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (392, 55, 4, true, false, false, '', 121, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (393, 56, 4, true, false, false, '', 122, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (394, 57, 4, true, false, false, '', 123, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (395, 58, 4, true, false, false, '', 124, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (396, 59, 4, true, false, false, '', 125, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (397, 60, 4, true, false, false, '', 126, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (398, 61, 4, true, false, false, '', 127, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (399, 62, 4, true, false, false, '', 128, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (400, 63, 4, true, false, false, '', 129, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (401, 1, 6, true, false, false, '', 67, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (402, 2, 6, true, false, false, '', 68, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (403, 3, 6, true, false, false, '', 69, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (404, 4, 6, true, false, false, '', 70, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (405, 5, 6, true, false, false, '', 71, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (406, 6, 6, true, false, false, '', 72, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (407, 7, 6, true, false, false, '', 73, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (408, 8, 6, true, false, false, '', 74, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (409, 9, 6, true, false, false, '', 75, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (410, 10, 6, true, false, false, '', 76, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (411, 11, 6, true, false, false, '', 77, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (412, 12, 6, true, false, false, '', 78, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (413, 13, 6, true, false, false, '', 79, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (414, 14, 6, true, false, false, '', 80, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (415, 15, 6, true, false, false, '', 81, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (416, 16, 6, true, false, false, '', 82, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (417, 17, 6, true, false, false, '', 83, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (418, 18, 6, true, false, false, '', 84, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (419, 19, 6, true, false, false, '', 85, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (420, 20, 6, true, false, false, '', 86, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (421, 21, 6, true, false, false, '', 87, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (422, 22, 6, true, false, false, '', 88, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (423, 23, 6, true, false, false, '', 89, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (424, 24, 6, true, false, false, '', 90, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (425, 25, 6, true, false, false, '', 91, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (426, 26, 6, true, false, false, '', 92, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (427, 27, 6, true, false, false, '', 93, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (428, 28, 6, true, false, false, '', 94, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (429, 29, 6, true, false, false, '', 95, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (430, 30, 6, true, false, false, '', 96, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (431, 31, 6, true, false, false, '', 97, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (432, 32, 6, true, false, false, '', 98, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (433, 33, 6, true, false, false, '', 99, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (434, 34, 6, true, false, false, '', 100, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (435, 35, 6, true, false, false, '', 101, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (436, 36, 6, true, false, false, '', 102, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (437, 37, 6, true, false, false, '', 103, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (438, 38, 6, true, false, false, '', 104, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (439, 39, 6, true, false, false, '', 105, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (440, 40, 6, true, false, false, '', 106, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (441, 41, 6, true, false, false, '', 107, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (442, 42, 6, true, false, false, '', 108, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (443, 43, 6, true, false, true, '', 109, true, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (444, 44, 6, true, false, false, '', 110, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (445, 45, 6, true, false, false, '', 111, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (446, 46, 6, true, false, false, '', 112, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (447, 47, 6, true, false, false, '', 113, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (448, 48, 6, true, false, false, '', 114, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (449, 49, 6, true, false, false, '', 115, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (450, 50, 6, true, false, false, '', 116, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (451, 51, 6, true, false, false, '', 117, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (452, 52, 6, true, false, false, '', 118, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (453, 53, 6, true, false, false, '', 119, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (454, 54, 6, true, false, false, '', 120, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (455, 55, 6, true, false, true, '', 121, true, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (456, 56, 6, true, false, false, '', 122, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (457, 57, 6, true, false, false, '', 123, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (458, 58, 6, true, false, false, '', 124, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (459, 59, 6, true, false, false, '', 125, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (460, 60, 6, true, false, true, '', 126, true, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (461, 61, 6, true, false, true, '', 127, true, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (462, 62, 6, true, false, true, '', 128, true, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (463, 63, 6, true, false, true, '', 129, true, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (464, 1, 8, true, false, false, '', 67, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (465, 2, 8, true, false, false, '', 68, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (466, 3, 8, true, false, false, '', 69, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (467, 4, 8, true, false, false, '', 70, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (468, 5, 8, true, false, false, '', 71, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (469, 6, 8, true, false, false, '', 72, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (470, 7, 8, true, false, false, '', 73, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (471, 8, 8, true, false, false, '', 74, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (472, 9, 8, true, false, false, '', 75, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (473, 10, 8, false, false, false, '', 76, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (474, 11, 8, true, false, false, '', 77, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (475, 12, 8, true, false, false, '', 78, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (476, 13, 8, true, false, false, '', 79, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (477, 14, 8, true, false, false, '', 80, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (478, 15, 8, false, false, false, '', 81, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (479, 16, 8, false, false, false, '', 82, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (480, 17, 8, true, false, false, '', 83, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (481, 18, 8, false, false, false, '', 84, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (482, 19, 8, false, false, false, '', 85, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (483, 20, 8, false, false, false, '', 86, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (484, 21, 8, true, false, false, '', 87, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (485, 22, 8, true, false, false, '', 88, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (486, 23, 8, true, false, false, '', 89, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (487, 24, 8, true, false, false, '', 90, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (488, 25, 8, true, false, false, '', 91, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (489, 26, 8, true, false, false, '', 92, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (490, 27, 8, false, false, false, '', 93, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (491, 28, 8, true, false, false, '', 94, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (492, 29, 8, true, false, false, '', 95, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (493, 30, 8, true, false, false, '', 96, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (494, 31, 8, true, false, false, '', 97, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (495, 32, 8, true, false, false, '', 98, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (496, 33, 8, true, false, false, '', 99, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (497, 34, 8, true, false, false, '', 100, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (498, 35, 8, true, false, false, '', 101, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (499, 36, 8, true, false, false, '', 102, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (500, 37, 8, true, false, false, '', 103, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (501, 38, 8, true, false, false, '', 104, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (502, 39, 8, false, false, false, '', 105, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (503, 40, 8, true, false, false, '', 106, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (504, 41, 8, true, false, false, '', 107, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (505, 42, 8, true, false, false, '', 108, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (506, 43, 8, true, false, false, '', 109, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (507, 44, 8, true, false, false, '', 110, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (508, 45, 8, true, false, false, '', 111, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (509, 46, 8, true, false, false, '', 112, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (510, 47, 8, true, false, false, '', 113, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (511, 48, 8, true, false, false, '', 114, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (512, 49, 8, true, false, false, '', 115, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (513, 50, 8, true, false, false, '', 116, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (514, 51, 8, false, false, false, '', 117, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (515, 52, 8, true, false, false, '', 118, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (516, 53, 8, true, false, false, '', 119, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (517, 54, 8, true, false, false, '', 120, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (518, 55, 8, false, false, false, '', 121, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (519, 56, 8, true, false, false, '', 122, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (520, 57, 8, true, false, false, '', 123, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (521, 58, 8, true, false, false, '', 124, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (522, 59, 8, true, false, false, '', 125, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (523, 60, 8, false, false, false, '', 126, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (524, 61, 8, false, false, false, '', 127, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (525, 62, 8, false, false, false, '', 128, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (526, 63, 8, false, false, false, '', 129, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (527, 1, 11, true, false, false, '', 67, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (528, 2, 11, true, false, false, '', 68, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (529, 3, 11, true, false, false, '', 69, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (530, 4, 11, true, false, false, '', 70, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (531, 5, 11, true, false, false, '', 71, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (532, 6, 11, true, false, false, '', 72, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (533, 7, 11, true, false, false, '', 73, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (534, 8, 11, true, false, false, '', 74, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (535, 9, 11, true, false, false, '', 75, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (536, 10, 11, true, false, true, '', 76, true, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (537, 11, 11, true, false, false, '', 77, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (538, 12, 11, true, false, false, '', 78, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (539, 13, 11, true, false, false, '', 79, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (540, 14, 11, true, false, false, '', 80, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (541, 15, 11, true, false, true, '', 81, true, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (542, 16, 11, true, false, false, '', 82, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (543, 17, 11, true, false, false, '', 83, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (544, 18, 11, true, false, false, '', 84, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (545, 19, 11, true, false, false, '', 85, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (546, 20, 11, true, false, false, '', 86, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (547, 21, 11, true, false, false, '', 87, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (548, 22, 11, true, false, false, '', 88, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (549, 23, 11, true, false, false, '', 89, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (550, 24, 11, true, false, false, '', 90, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (551, 25, 11, true, false, false, '', 91, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (552, 26, 11, true, false, false, '', 92, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (553, 27, 11, true, false, true, '', 93, true, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (554, 28, 11, false, false, false, '', 94, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (555, 29, 11, true, false, false, '', 95, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (556, 30, 11, true, false, false, '', 96, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (557, 31, 11, true, false, false, '', 97, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (558, 32, 11, true, false, false, '', 98, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (559, 33, 11, true, false, false, '', 99, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (560, 34, 11, true, false, false, '', 100, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (561, 35, 11, true, false, false, '', 101, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (562, 36, 11, true, false, false, '', 102, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (563, 37, 11, true, false, false, '', 103, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (564, 38, 11, true, false, false, '', 104, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (565, 39, 11, true, false, false, '', 105, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (566, 40, 11, true, false, false, '', 106, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (567, 41, 11, true, false, false, '', 107, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (568, 42, 11, true, false, false, '', 108, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (569, 43, 11, true, false, false, '', 109, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (570, 44, 11, true, false, false, '', 110, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (571, 45, 11, true, false, false, '', 111, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (572, 46, 11, true, false, false, '', 112, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (573, 47, 11, true, false, false, '', 113, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (574, 48, 11, true, false, false, '', 114, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (575, 49, 11, true, false, false, '', 115, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (576, 50, 11, true, false, false, '', 116, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (577, 51, 11, true, false, false, '', 117, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (578, 52, 11, true, false, false, '', 118, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (579, 53, 11, true, false, false, '', 119, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (580, 54, 11, true, false, false, '', 120, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (581, 55, 11, true, false, true, '', 121, true, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (582, 56, 11, true, false, false, '', 122, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (583, 57, 11, true, false, false, '', 123, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (584, 58, 11, true, false, false, '', 124, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (585, 59, 11, true, false, false, '', 125, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (586, 60, 11, true, false, true, '', 126, true, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (587, 61, 11, true, false, true, '', 127, true, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (588, 62, 11, true, false, true, '', 128, true, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (589, 63, 11, true, false, true, '', 129, true, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (590, 1, 12, true, false, false, '', 130, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (591, 2, 12, true, false, false, '', 131, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (592, 3, 12, true, false, true, '', 132, true, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (593, 4, 12, false, false, false, '', 133, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (594, 5, 12, true, false, false, '', 134, false, true, true);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (595, 6, 12, false, false, false, '', 135, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (596, 7, 12, false, false, false, '', 136, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (597, 8, 12, false, false, false, '', 137, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (598, 9, 12, false, false, false, '', 138, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (599, 10, 12, true, false, false, '', 139, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (600, 11, 12, false, false, false, '', 140, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (601, 12, 12, false, false, false, '', 141, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (602, 13, 12, false, false, false, '', 142, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (603, 14, 12, true, false, false, ' This is an example of commenttext for a multiline msgset', 143, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (604, 15, 12, true, false, false, '', 144, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (605, 16, 12, true, false, false, '', 145, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (606, 17, 12, false, false, true, '', 146, true, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (607, 18, 12, true, false, false, ' start po-group: common
 start po-group: common', 147, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (608, 19, 12, false, false, false, '', 148, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (609, 20, 12, false, false, false, '', 149, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (610, 21, 12, false, false, false, '', 150, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (611, 22, 12, true, true, false, '', 161, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (612, 1, 13, true, false, false, '', 152, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (613, 2, 13, true, false, false, '', 153, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (614, 3, 13, true, false, false, '', 154, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (615, 4, 13, true, false, false, '', 155, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (616, 5, 13, true, false, false, '', 156, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (617, 6, 13, true, false, false, '', 157, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (618, 7, 13, true, false, false, '', 158, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (619, 8, 13, true, false, false, '', 159, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (620, 9, 13, true, false, false, '', 160, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (621, 1, 15, true, false, false, '', 152, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (622, 2, 15, true, false, false, '', 153, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (623, 3, 15, true, false, false, '', 154, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (624, 4, 15, true, false, false, '', 155, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (625, 5, 15, true, false, false, '', 156, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (626, 6, 15, true, false, false, '', 157, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (627, 7, 15, true, false, false, '', 158, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (628, 8, 15, true, false, false, '', 159, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (629, 9, 15, true, false, false, '', 160, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (630, 1, 24, true, false, false, '', 152, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (631, 2, 24, true, false, false, '', 153, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (632, 3, 24, true, false, false, '', 154, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (633, 4, 24, true, false, false, '', 155, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (634, 5, 24, true, false, false, '', 156, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (635, 6, 24, true, false, false, '', 157, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (636, 7, 24, true, false, false, '', 158, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (637, 8, 24, true, false, false, '', 159, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (638, 9, 24, true, false, false, '', 160, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (639, 1, 25, true, false, false, '', 152, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (640, 2, 25, true, false, false, '', 153, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (641, 3, 25, true, false, false, '', 154, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (642, 4, 25, true, false, false, '', 155, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (643, 5, 25, true, false, false, '', 156, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (644, 6, 25, true, false, false, '', 157, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (645, 7, 25, false, false, false, '', 158, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (646, 8, 25, false, false, false, '', 159, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (647, 9, 25, false, false, false, '', 160, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (648, 1, 14, true, false, false, '', 152, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (649, 2, 14, true, false, false, '', 153, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (650, 3, 14, true, false, false, '', 154, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (651, 4, 14, true, false, false, '', 155, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (652, 5, 14, true, false, false, '', 156, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (653, 6, 14, true, false, false, '', 157, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (654, 7, 14, true, false, false, '', 158, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (655, 8, 14, true, false, false, '', 159, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (656, 9, 14, true, false, false, '', 160, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (657, 1, 21, true, false, false, '', 152, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (658, 2, 21, true, false, false, '', 153, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (659, 3, 21, true, false, false, '', 154, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (660, 4, 21, true, false, false, '', 155, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (661, 5, 21, true, false, false, '', 156, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (662, 6, 21, true, false, false, '', 157, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (663, 7, 21, true, false, false, '', 158, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (664, 8, 21, true, false, false, '', 159, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (665, 9, 21, true, false, false, '', 160, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (666, 1, 19, true, false, false, '', 152, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (667, 2, 19, true, false, false, '', 153, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (668, 3, 19, true, false, false, '', 154, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (669, 4, 19, true, false, false, '', 155, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (670, 5, 19, true, false, false, '', 156, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (671, 6, 19, true, false, false, '', 157, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (672, 7, 19, true, false, false, '', 158, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (673, 8, 19, true, false, false, '', 159, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (674, 9, 19, true, false, false, '', 160, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (675, 1, 22, true, false, false, '', 152, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (676, 2, 22, true, false, false, '', 153, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (677, 3, 22, true, false, false, '', 154, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (678, 4, 22, true, false, false, '', 155, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (679, 5, 22, true, false, false, '', 156, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (680, 6, 22, true, false, false, '', 157, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (681, 7, 22, true, false, false, '', 158, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (682, 8, 22, true, false, false, '', 159, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (683, 9, 22, true, false, false, '', 160, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (684, 10, 22, true, true, false, '', 162, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (685, 11, 22, true, true, false, '', 163, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (686, 12, 22, true, true, false, '', 164, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (687, 1, 23, true, false, false, '', 152, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (688, 2, 23, true, false, false, '', 153, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (689, 3, 23, true, false, false, '', 154, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (690, 4, 23, false, false, false, '', 155, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (691, 5, 23, false, false, false, '', 156, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (692, 6, 23, false, false, false, '', 157, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (693, 7, 23, false, false, false, '', 158, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (694, 8, 23, false, false, false, '', 159, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (695, 9, 23, false, false, false, '', 160, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (696, 1, 20, true, false, false, '', 152, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (697, 2, 20, true, false, false, '', 153, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (698, 3, 20, true, false, false, '', 154, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (699, 4, 20, true, false, false, '', 155, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (700, 5, 20, true, false, false, '', 156, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (701, 6, 20, true, false, false, '', 157, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (702, 7, 20, true, false, false, '', 158, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (703, 8, 20, true, false, false, '', 159, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (704, 9, 20, true, false, false, '', 160, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (705, 1, 18, true, false, false, '', 152, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (706, 2, 18, true, false, false, '', 153, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (707, 3, 18, true, false, false, '', 154, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (708, 4, 18, true, false, false, '', 155, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (709, 5, 18, true, false, false, '', 156, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (710, 6, 18, true, false, false, '', 157, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (711, 7, 18, true, false, false, '', 158, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (712, 8, 18, true, false, false, '', 159, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (713, 9, 18, true, false, false, '', 160, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (714, 1, 17, true, false, false, '', 152, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (715, 2, 17, true, false, false, '', 153, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (716, 3, 17, true, false, false, '', 154, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (717, 4, 17, true, false, false, '', 155, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (718, 5, 17, true, false, false, '', 156, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (719, 6, 17, true, false, false, '', 157, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (720, 7, 17, false, false, false, '', 158, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (721, 8, 17, false, false, false, '', 159, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (722, 9, 17, false, false, false, '', 160, false, false, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (723, 1, 16, true, false, false, '', 152, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (724, 2, 16, true, false, false, '', 153, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (725, 3, 16, true, false, false, '', 154, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (726, 4, 16, true, false, false, '', 155, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (727, 5, 16, true, false, false, '', 156, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (728, 6, 16, true, false, false, '', 157, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (729, 7, 16, true, false, false, '', 158, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (730, 8, 16, true, false, false, '', 159, false, true, false);
INSERT INTO pomsgset (id, "sequence", pofile, iscomplete, obsolete, isfuzzy, commenttext, potmsgset, publishedfuzzy, publishedcomplete, isupdated) VALUES (731, 9, 16, true, false, false, '', 160, false, true, false);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'pomsgset'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'pomsgidsighting'::pg_catalog.regclass;

INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (1, 1, 1, '2005-03-18 18:31:17.54732', '2005-03-18 18:31:17.54732', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (2, 2, 2, '2005-03-18 18:31:17.54732', '2005-03-18 18:31:17.54732', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (3, 3, 3, '2005-03-18 18:31:17.54732', '2005-03-18 18:31:17.54732', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (4, 4, 4, '2005-03-18 18:31:17.54732', '2005-03-18 18:31:17.54732', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (5, 5, 5, '2005-03-18 18:31:17.54732', '2005-03-18 18:31:17.54732', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (6, 6, 6, '2005-03-18 18:31:17.54732', '2005-03-18 18:31:17.54732', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (7, 7, 7, '2005-03-18 18:31:17.54732', '2005-03-18 18:31:17.54732', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (8, 8, 8, '2005-03-18 18:31:17.54732', '2005-03-18 18:31:17.54732', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (9, 9, 9, '2005-03-18 18:31:17.54732', '2005-03-18 18:31:17.54732', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (10, 10, 10, '2005-03-18 18:31:17.54732', '2005-03-18 18:31:17.54732', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (11, 11, 11, '2005-03-18 18:31:17.54732', '2005-03-18 18:31:17.54732', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (12, 12, 12, '2005-03-18 18:31:17.54732', '2005-03-18 18:31:17.54732', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (13, 13, 13, '2005-03-18 18:31:17.54732', '2005-03-18 18:31:17.54732', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (14, 14, 14, '2005-03-18 18:31:17.54732', '2005-03-18 18:31:17.54732', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (15, 15, 15, '2005-03-18 18:31:17.54732', '2005-03-18 18:31:17.54732', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (16, 15, 16, '2005-03-18 18:31:17.54732', '2005-04-07 13:19:17.601068', true, 1);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (17, 16, 17, '2005-03-18 18:31:17.54732', '2005-03-18 18:31:17.54732', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (18, 16, 18, '2005-03-18 18:31:17.54732', '2005-04-07 13:19:17.601068', true, 1);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (19, 17, 19, '2005-03-18 18:31:17.54732', '2005-03-18 18:31:17.54732', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (20, 17, 20, '2005-03-18 18:31:17.54732', '2005-04-07 13:19:17.601068', true, 1);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (21, 18, 21, '2005-03-18 18:31:17.54732', '2005-03-18 18:31:17.54732', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (22, 19, 22, '2005-03-18 18:31:17.54732', '2005-03-18 18:31:17.54732', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (23, 20, 23, '2005-03-18 18:31:17.54732', '2005-03-18 18:31:17.54732', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (24, 21, 24, '2005-03-18 18:31:17.54732', '2005-03-18 18:31:17.54732', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (25, 21, 25, '2005-03-18 18:31:17.54732', '2005-04-07 13:19:17.601068', true, 1);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (26, 22, 26, '2005-04-07 13:16:19.484578', '2005-04-07 13:16:19.484578', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (27, 23, 27, '2005-04-07 13:19:17.601068', '2005-04-07 13:19:17.601068', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (28, 24, 28, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (29, 25, 29, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (30, 26, 30, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (31, 27, 31, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (32, 28, 32, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (33, 29, 33, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (34, 30, 34, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (35, 31, 35, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (36, 32, 36, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (37, 33, 37, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (38, 34, 38, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (39, 35, 39, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (40, 36, 40, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (41, 37, 41, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (42, 38, 42, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (43, 39, 43, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (44, 40, 44, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (45, 41, 45, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (46, 42, 46, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (47, 43, 47, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (48, 44, 48, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (49, 45, 49, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (50, 46, 50, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (51, 47, 51, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (52, 48, 52, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (53, 49, 53, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (54, 50, 54, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (55, 51, 55, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (56, 52, 56, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (57, 53, 57, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (58, 54, 58, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (59, 55, 59, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (60, 56, 60, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (61, 57, 61, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (62, 58, 62, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (63, 59, 63, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (64, 60, 64, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (65, 61, 65, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (66, 62, 66, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (67, 63, 67, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (68, 64, 68, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (69, 65, 69, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (70, 66, 70, '2005-05-06 20:09:20.041475', '2005-05-06 20:09:20.041475', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (71, 67, 71, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (72, 68, 72, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (73, 69, 73, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (74, 70, 74, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (75, 71, 75, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (76, 72, 76, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (77, 73, 77, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (78, 74, 78, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (79, 75, 79, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (80, 76, 80, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (81, 77, 81, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (82, 78, 82, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (83, 79, 83, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (84, 80, 84, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (85, 81, 85, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (86, 82, 86, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (87, 83, 87, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (88, 84, 88, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (89, 85, 89, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (90, 86, 90, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (91, 87, 91, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (92, 88, 92, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (93, 89, 93, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (94, 90, 94, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (95, 91, 95, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (96, 92, 96, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (97, 93, 97, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (98, 94, 98, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (99, 95, 99, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (100, 96, 100, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (101, 97, 101, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (102, 98, 102, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (103, 99, 103, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (104, 100, 104, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (105, 101, 105, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (106, 102, 106, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (107, 103, 107, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (108, 104, 108, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (109, 105, 109, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (110, 106, 110, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (111, 107, 111, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (112, 108, 112, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (113, 109, 113, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (114, 110, 114, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (115, 111, 115, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (116, 112, 116, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (117, 113, 117, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (118, 114, 118, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (119, 115, 119, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (120, 116, 120, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (121, 117, 121, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (122, 118, 122, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (123, 119, 123, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (124, 120, 124, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (125, 121, 125, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (126, 122, 126, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (127, 123, 127, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (128, 124, 128, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (129, 125, 129, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (130, 126, 130, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (131, 127, 131, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (132, 128, 132, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (133, 129, 133, '2005-05-06 20:09:23.775993', '2005-05-06 20:09:23.775993', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (134, 130, 1, '2005-05-06 20:50:49.06624', '2005-05-06 20:50:49.06624', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (135, 131, 2, '2005-05-06 20:50:49.06624', '2005-05-06 20:50:49.06624', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (136, 132, 3, '2005-05-06 20:50:49.06624', '2005-05-06 20:50:49.06624', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (137, 133, 4, '2005-05-06 20:50:49.06624', '2005-05-06 20:50:49.06624', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (138, 134, 5, '2005-05-06 20:50:49.06624', '2005-05-06 20:50:49.06624', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (139, 135, 6, '2005-05-06 20:50:49.06624', '2005-05-06 20:50:49.06624', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (140, 136, 7, '2005-05-06 20:50:49.06624', '2005-05-06 20:50:49.06624', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (141, 137, 8, '2005-05-06 20:50:49.06624', '2005-05-06 20:50:49.06624', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (142, 138, 9, '2005-05-06 20:50:49.06624', '2005-05-06 20:50:49.06624', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (143, 139, 10, '2005-05-06 20:50:49.06624', '2005-05-06 20:50:49.06624', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (144, 140, 11, '2005-05-06 20:50:49.06624', '2005-05-06 20:50:49.06624', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (145, 141, 12, '2005-05-06 20:50:49.06624', '2005-05-06 20:50:49.06624', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (146, 142, 13, '2005-05-06 20:50:49.06624', '2005-05-06 20:50:49.06624', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (147, 143, 14, '2005-05-06 20:50:49.06624', '2005-05-06 20:50:49.06624', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (148, 144, 15, '2005-05-06 20:50:49.06624', '2005-05-06 20:50:49.06624', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (149, 144, 16, '2005-05-06 20:50:49.06624', '2005-05-06 21:12:13.908028', true, 1);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (150, 145, 17, '2005-05-06 20:50:49.06624', '2005-05-06 20:50:49.06624', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (151, 145, 18, '2005-05-06 20:50:49.06624', '2005-05-06 21:12:13.908028', true, 1);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (152, 146, 19, '2005-05-06 20:50:49.06624', '2005-05-06 20:50:49.06624', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (153, 146, 20, '2005-05-06 20:50:49.06624', '2005-05-06 21:12:13.908028', true, 1);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (154, 147, 21, '2005-05-06 20:50:49.06624', '2005-05-06 20:50:49.06624', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (155, 148, 22, '2005-05-06 20:50:49.06624', '2005-05-06 20:50:49.06624', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (156, 149, 23, '2005-05-06 20:50:49.06624', '2005-05-06 20:50:49.06624', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (157, 150, 24, '2005-05-06 20:50:49.06624', '2005-05-06 20:50:49.06624', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (158, 150, 25, '2005-05-06 20:50:49.06624', '2005-05-06 21:12:13.908028', true, 1);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (159, 151, 26, '2005-05-06 20:50:49.06624', '2005-05-06 20:50:49.06624', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (160, 152, 134, '2005-05-06 21:12:12.222741', '2005-05-06 21:12:12.222741', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (161, 153, 135, '2005-05-06 21:12:12.222741', '2005-05-06 21:12:12.222741', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (162, 154, 136, '2005-05-06 21:12:12.222741', '2005-05-06 21:12:12.222741', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (163, 155, 137, '2005-05-06 21:12:12.222741', '2005-05-06 21:12:12.222741', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (164, 156, 138, '2005-05-06 21:12:12.222741', '2005-05-06 21:12:12.222741', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (165, 157, 139, '2005-05-06 21:12:12.222741', '2005-05-06 21:12:12.222741', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (166, 158, 140, '2005-05-06 21:12:12.222741', '2005-05-06 21:12:12.222741', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (167, 159, 141, '2005-05-06 21:12:12.222741', '2005-05-06 21:12:12.222741', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (168, 160, 142, '2005-05-06 21:12:12.222741', '2005-05-06 21:12:12.222741', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (169, 161, 27, '2005-05-06 21:12:13.908028', '2005-05-06 21:12:13.908028', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (170, 162, 143, '2005-05-06 21:12:33.238579', '2005-05-06 21:12:33.238579', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (171, 163, 144, '2005-05-06 21:12:33.238579', '2005-05-06 21:12:33.238579', true, 0);
INSERT INTO pomsgidsighting (id, potmsgset, pomsgid, datefirstseen, datelastseen, inlastrevision, pluralform) VALUES (172, 164, 145, '2005-05-06 21:12:33.238579', '2005-05-06 21:12:33.238579', true, 0);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'pomsgidsighting'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'pocomment'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'pocomment'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'translationeffort'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'translationeffort'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'translationeffortpotemplate'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'translationeffortpotemplate'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'posubscription'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'posubscription'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'bug'::pg_catalog.regclass;

INSERT INTO bug (id, datecreated, name, title, description, "owner", duplicateof, communityscore, communitytimestamp, activityscore, activitytimestamp, hits, hitstimestamp, summary, fti, private) VALUES (1, '2004-09-24 20:58:04.553583', NULL, 'Firefox does not support SVG', 'The SVG standard 1.0 is complete, and draft implementations for Firefox exist. One of these implementations needs to be integrated with the base install of Firefox. Ideally, the implementation needs to include support for the manipulation of SVG objects from JavaScript to enable interactive and dynamic SVG drawings.', 12, NULL, 0, '2004-09-24 00:00:00', 0, '2004-09-24 00:00:00', 0, '2004-09-24 00:00:00', 'Firefox needs to support embedded SVG images, now that the standard has been finalised.', '''1.0'':23 ''one'':32 ''svg'':5B,11C,21,57,66 ''base'':42 ''draw'':67 ''imag'':12C ''need'':7C,36,49 ''draft'':27 ''dynam'':65 ''embed'':10C ''enabl'':62 ''exist'':31 ''ideal'':46 ''includ'':51 ''instal'':43 ''integr'':39 ''object'':58 ''complet'':25 ''finalis'':19C ''firefox'':1B,6C,30,45 ''manipul'':55 ''support'':4B,9C,52 ''interact'':63 ''standard'':16C,22 ''implement'':28,35,48 ''javascript'':60', false);
INSERT INTO bug (id, datecreated, name, title, description, "owner", duplicateof, communityscore, communitytimestamp, activityscore, activitytimestamp, hits, hitstimestamp, summary, fti, private) VALUES (2, '2004-09-24 20:58:04.572546', 'blackhole', 'Blackhole Trash folder', 'The Trash folder seems to have significant problems! At the moment, dragging an item to the trash results in immediate deletion. The item does not appear in the Trash, it is just deleted from my hard disk. There is no undo or ability to recover the deleted file. Help!', 12, NULL, 0, '2004-09-24 00:00:00', 0, '2004-09-24 00:00:00', 0, '2004-09-24 00:00:00', 'Everything put into the folder "Trash" disappears!', '''put'':6C ''abil'':54 ''disk'':48 ''drag'':23 ''file'':59 ''hard'':47 ''help'':60 ''item'':25,34 ''seem'':15 ''undo'':52 ''delet'':32,44,58 ''recov'':56 ''trash'':3B,10C,13,28,40 ''appear'':37 ''folder'':4B,9C,14 ''immedi'':31 ''moment'':22 ''result'':29 ''everyth'':5C ''problem'':19 ''blackhol'':1A,2B ''signific'':18 ''disappear'':11C', false);
INSERT INTO bug (id, datecreated, name, title, description, "owner", duplicateof, communityscore, communitytimestamp, activityscore, activitytimestamp, hits, hitstimestamp, summary, fti, private) VALUES (3, '2004-10-05 00:00:00', NULL, 'Bug Title Test', 'y idu yifdxhfgffxShirtpkdf jlkdsj;lkd lkjd hlkjfds gkfdsg kfd glkfd gifdsytoxdiytxoiufdytoidxf yxoigfyoigfxuyfxoiug yxoiuy oiugf hyoifxugyoixgfuy xoiuyxoiyxoifuy xoShirtpkdf jlkdsj;lkd lkjd hlkjfds gkfdsg kfd glkfd gifdsytoxdiytxoiufdytoidxf yxoigfyoigfxuyfxoiug yxoiuy oiugf hyoifxugyoixgfuy xoiuyxoiyxoifuy xo
Shirtpkdf jlkdsj;lkd lkjd hlkjfds gkfdsg kfd glkfd gifdsytoxdiytxoiufdytoidxf yxoigfyoigfxuyfxoiug yxoiuy oiugf hyoifxugyoixgfuy xoiuyxoiyxoifuy xoShirtpkdf jlkdsj;lkd lkjd hlkjfds gkfdsg kfd glkfd gifdsytoxdiytxoiufdytoidxf yxoigfyoigfxuyfxoiug yxoiuy oiugf hyoifxugyoixgfuy xoiuyxoiyxoifuy xo

Shirtpkdf jlkdsj;lkd lkjd hlkjfds gkfdsg kfd glkfd gifdsytoxdiytxoiufdytoidxf yxoigfyoigfxuyfxoiug yxoiuy oiugf hyoifxugyoixgfuy xoiuyxoiyxoifuy xoShirtpkdf jlkdsj;lkd lkjd hlkjfds gkfdsg kfd glkfd gifdsytoxdiytxoiufdytoidxf yxoigfyoigfxuyfxoiug yxoiuy oiugf hyoifxugyoixgfuy xoiuyxoiyxoifuy xo', 16, NULL, 0, '2004-10-05 00:00:00', 0, '2004-10-05 00:00:00', 0, '2004-10-05 00:00:00', 'Shirtpkdf jlkdsj;lkd lkjd hlkjfds gkfdsg kfd glkfd gifdsytoxdiytxoiufdytoidxf yxoigfyoigfxuyfxoiug yxoiuy oiugf hyoifxugyoixgfuy xoiuyxoiyxoifuy xo', '''y'':19 ''xo'':18C,49,78,107 ''bug'':1B ''idu'':20 ''kfd'':10C,27,41,56,70,85,99 ''lkd'':6C,23,37,52,66,81,95 ''lkjd'':7C,24,38,53,67,82,96 ''test'':3B ''titl'':2B ''glkfd'':11C,28,42,57,71,86,100 ''oiugf'':15C,32,46,61,75,90,104 ''gkfdsg'':9C,26,40,55,69,84,98 ''jlkdsj'':5C,22,36,51,65,80,94 ''yxoiuy'':14C,31,45,60,74,89,103 ''hlkjfds'':8C,25,39,54,68,83,97 ''shirtpkdf'':4C,50,79 ''xoshirtpkdf'':35,64,93 ''xoiuyxoiyxoifuy'':17C,34,48,63,77,92,106 ''hyoifxugyoixgfuy'':16C,33,47,62,76,91,105 ''yifdxhfgffxshirtpkdf'':21 ''yxoigfyoigfxuyfxoiug'':13C,30,44,59,73,88,102 ''gifdsytoxdiytxoiufdytoidxf'':12C,29,43,58,72,87,101', false);
INSERT INTO bug (id, datecreated, name, title, description, "owner", duplicateof, communityscore, communitytimestamp, activityscore, activitytimestamp, hits, hitstimestamp, summary, fti, private) VALUES (4, '2005-01-14 00:00:00', NULL, 'Reflow problems with complex page layouts', NULL, 12, NULL, 0, '2005-01-14 17:20:12.820778', 0, '2005-01-14 17:20:12.820778', 0, '2005-01-14 17:20:12.820778', NULL, '''page'':5B ''layout'':6B ''reflow'':1B ''complex'':4B ''problem'':2B', false);
INSERT INTO bug (id, datecreated, name, title, description, "owner", duplicateof, communityscore, communitytimestamp, activityscore, activitytimestamp, hits, hitstimestamp, summary, fti, private) VALUES (5, '2005-01-14 00:00:00', NULL, 'Firefox install instructions should be complete', NULL, 12, NULL, 0, '2005-01-14 17:27:03.702622', 0, '2005-01-14 17:27:03.702622', 0, '2005-01-14 17:27:03.702622', NULL, '''instal'':2B ''complet'':6B ''firefox'':1B ''instruct'':3B', false);
INSERT INTO bug (id, datecreated, name, title, description, "owner", duplicateof, communityscore, communitytimestamp, activityscore, activitytimestamp, hits, hitstimestamp, summary, fti, private) VALUES (6, '2005-01-14 00:00:00', NULL, 'Firefox crashes when Save As dialog for a nonexistent window is closed', NULL, 12, 5, 0, '2005-01-14 17:35:39.548665', 0, '2005-01-14 17:35:39.548665', 0, '2005-01-14 17:35:39.548665', NULL, '''save'':4B ''close'':12B ''crash'':2B ''dialog'':6B ''window'':10B ''firefox'':1B ''nonexist'':9B', false);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'bug'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'bugsubscription'::pg_catalog.regclass;

INSERT INTO bugsubscription (id, person, bug, subscription) VALUES (1, 11, 1, 2);
INSERT INTO bugsubscription (id, person, bug, subscription) VALUES (2, 2, 1, 3);
INSERT INTO bugsubscription (id, person, bug, subscription) VALUES (3, 10, 1, 3);
INSERT INTO bugsubscription (id, person, bug, subscription) VALUES (4, 12, 1, 1);
INSERT INTO bugsubscription (id, person, bug, subscription) VALUES (5, 11, 2, 2);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'bugsubscription'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'bugactivity'::pg_catalog.regclass;

INSERT INTO bugactivity (id, bug, datechanged, person, whatchanged, oldvalue, newvalue, message) VALUES (1, 1, '2004-09-24 00:00:00', 1, 'title', 'A silly problem', 'An odd problem', 'Decided problem wasn''t silly after all');
INSERT INTO bugactivity (id, bug, datechanged, person, whatchanged, oldvalue, newvalue, message) VALUES (2, 4, '2005-01-14 00:00:00', 12, 'bug', NULL, NULL, 'added bug');
INSERT INTO bugactivity (id, bug, datechanged, person, whatchanged, oldvalue, newvalue, message) VALUES (3, 5, '2005-01-14 00:00:00', 12, 'bug', NULL, NULL, 'added bug');
INSERT INTO bugactivity (id, bug, datechanged, person, whatchanged, oldvalue, newvalue, message) VALUES (4, 5, '2005-01-14 00:00:00', 12, 'firefox: assignee', NULL, 'name12', 'XXX: not yet implemented');
INSERT INTO bugactivity (id, bug, datechanged, person, whatchanged, oldvalue, newvalue, message) VALUES (5, 6, '2005-01-14 00:00:00', 12, 'bug', NULL, NULL, 'added bug');
INSERT INTO bugactivity (id, bug, datechanged, person, whatchanged, oldvalue, newvalue, message) VALUES (6, 6, '2005-01-14 00:00:00', 12, 'firefox: severity', 'Normal', 'Critical', 'XXX: not yet implemented');
INSERT INTO bugactivity (id, bug, datechanged, person, whatchanged, oldvalue, newvalue, message) VALUES (7, 6, '2005-07-13 14:43:02.452716', 12, 'bug', NULL, NULL, 'assigned to source package mozilla-firefox');
INSERT INTO bugactivity (id, bug, datechanged, person, whatchanged, oldvalue, newvalue, message) VALUES (8, 1, '2005-08-03 12:04:50.669962', 16, 'bug', NULL, NULL, 'assigned to source package mozilla-firefox');
INSERT INTO bugactivity (id, bug, datechanged, person, whatchanged, oldvalue, newvalue, message) VALUES (9, 1, '2005-08-04 01:15:48.241836', 16, 'bug', NULL, NULL, 'assigned to source package mozilla-firefox');
INSERT INTO bugactivity (id, bug, datechanged, person, whatchanged, oldvalue, newvalue, message) VALUES (10, 3, '2005-08-10 16:30:32.295049', 12, 'bug', NULL, NULL, 'assigned to source package mozilla-firefox');
INSERT INTO bugactivity (id, bug, datechanged, person, whatchanged, oldvalue, newvalue, message) VALUES (11, 3, '2005-08-10 16:30:47.448639', 12, 'bug', NULL, NULL, 'assigned to source package mozilla-firefox');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'bugactivity'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'bugexternalref'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'bugexternalref'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'bugtracker'::pg_catalog.regclass;

INSERT INTO bugtracker (id, bugtrackertype, name, title, summary, baseurl, "owner", contactdetails) VALUES (1, 1, 'mozilla.org', 'The Mozilla.org Bug Tracker', 'The Mozilla.org bug tracker is the grand-daddy of bugzillas. This is where Bugzilla was conceived, born and raised. This bugzilla instance covers all Mozilla products such as Firefox, Thunderbird and Bugzilla itself.', 'http://bugzilla.mozilla.org/', 12, 'Carrier pigeon only');
INSERT INTO bugtracker (id, bugtrackertype, name, title, summary, baseurl, "owner", contactdetails) VALUES (2, 1, 'gnome-bugzilla', 'GnomeGBug GTracker', 'This is the Gnome Bugzilla bug tracking system. It covers all the applications in the Gnome Desktop and Gnome Fifth Toe.', 'http://bugzilla.gnome.org/', 16, 'Jeff Waugh, in his pants.');
INSERT INTO bugtracker (id, bugtrackertype, name, title, summary, baseurl, "owner", contactdetails) VALUES (3, 2, 'debbugs', 'Debian Bug tracker', 'Bug tracker for debian project.', 'http://bugs.debian.org', 1, NULL);


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

INSERT INTO message (id, datecreated, subject, "owner", parent, distribution, rfc822msgid, fti, raw) VALUES (1, '2004-09-24 20:58:04.684057', 'PEBCAK', NULL, NULL, NULL, 'foo@example.com-332342--1231', '''pebcak'':1B', NULL);
INSERT INTO message (id, datecreated, subject, "owner", parent, distribution, rfc822msgid, fti, raw) VALUES (3, '2004-09-24 21:17:17.153792', 'Reproduced on AIX', 12, NULL, NULL, 'sdsdfsfd', '''aix'':3B ''reproduc'':1B', NULL);
INSERT INTO message (id, datecreated, subject, "owner", parent, distribution, rfc822msgid, fti, raw) VALUES (4, '2004-09-24 21:24:03.922564', 'Re: Reproduced on AIX', 12, NULL, NULL, 'sdfssfdfsd', '''re'':1B ''aix'':4B ''reproduc'':2B', NULL);
INSERT INTO message (id, datecreated, subject, "owner", parent, distribution, rfc822msgid, fti, raw) VALUES (5, '2004-09-24 21:29:27.407354', 'Fantastic idea, I''d really like to see this', 12, NULL, NULL, 'dxssdfsdgf', '''d'':4B ''see'':8B ''idea'':2B ''like'':6B ''realli'':5B ''fantast'':1B', NULL);
INSERT INTO message (id, datecreated, subject, "owner", parent, distribution, rfc822msgid, fti, raw) VALUES (6, '2004-09-24 21:35:20.125564', 'Strange bug with duplicate messages.', 12, NULL, NULL, 'sdfsfwew', '''bug'':2B ''duplic'':4B ''messag'':5B ''strang'':1B', NULL);
INSERT INTO message (id, datecreated, subject, "owner", parent, distribution, rfc822msgid, fti, raw) VALUES (7, '2005-01-14 17:20:12.820778', 'Reflow problems with complex page layouts', 12, NULL, NULL, '<20050114172012.6687.51124.malonedeb@localhost.localdomain>', '''page'':5B ''layout'':6B ''reflow'':1B ''complex'':4B ''problem'':2B', NULL);
INSERT INTO message (id, datecreated, subject, "owner", parent, distribution, rfc822msgid, fti, raw) VALUES (8, '2005-01-14 17:27:03.702622', 'Firefox install instructions should be complete', 12, NULL, NULL, '<20050114172703.6687.71983.malonedeb@localhost.localdomain>', '''instal'':2B ''complet'':6B ''firefox'':1B ''instruct'':3B', NULL);
INSERT INTO message (id, datecreated, subject, "owner", parent, distribution, rfc822msgid, fti, raw) VALUES (9, '2005-01-14 17:35:39.548665', 'Firefox crashes when Save As dialog for a nonexistent window is closed', 12, NULL, NULL, '<20050114173539.6687.81610.malonedeb@localhost.localdomain>', '''save'':4B ''close'':12B ''crash'':2B ''dialog'':6B ''window'':10B ''firefox'':1B ''nonexist'':9B', NULL);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'message'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'bugattachment'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'bugattachment'::pg_catalog.regclass;


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
INSERT INTO personlanguage (id, person, "language") VALUES (2, 13, 68);
INSERT INTO personlanguage (id, person, "language") VALUES (3, 14, 196);
INSERT INTO personlanguage (id, person, "language") VALUES (4, 14, 449);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'personlanguage'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'potmsgset'::pg_catalog.regclass;

INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (1, 1, 1, 1, '', 'a11y/addressbook/ea-addressbook-view.c:94
a11y/addressbook/ea-addressbook-view.c:103
a11y/addressbook/ea-minicard-view.c:119', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (2, 2, 2, 1, '', 'a11y/addressbook/ea-minicard-view.c:101', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (3, 3, 3, 1, '', 'a11y/addressbook/ea-minicard-view.c:102', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (4, 4, 4, 1, '', 'a11y/addressbook/ea-minicard-view.c:102', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (5, 5, 5, 1, '', 'a11y/addressbook/ea-minicard-view.c:104', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (6, 6, 6, 1, '', 'a11y/addressbook/ea-minicard-view.c:104', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (7, 7, 7, 1, '', 'a11y/addressbook/ea-minicard-view.c:105', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (8, 8, 8, 1, '', 'a11y/addressbook/ea-minicard.c:166', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (9, 9, 9, 1, '', 'addressbook/addressbook-errors.xml.h:2', 'addressbook:ldap-init primary', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (10, 10, 10, 1, '', 'addressbook/addressbook-errors.xml.h:4', 'addressbook:ldap-init secondary', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (11, 11, 11, 1, '', 'addressbook/addressbook-errors.xml.h:6', 'addressbook:ldap-auth primary', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (12, 12, 12, 1, '', 'addressbook/addressbook-errors.xml.h:8', 'addressbook:ldap-auth secondary', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (13, 13, 13, 1, '', 'addressbook/gui/component/addressbook-migrate.c:124
calendar/gui/migration.c:188 mail/em-migrate.c:1201', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (14, 14, 14, 1, '', 'addressbook/gui/component/addressbook-migrate.c:1123', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (15, 15, 15, 1, '', 'addressbook/gui/widgets/e-addressbook-model.c:151', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (16, 17, 16, 1, '', 'addressbook/gui/widgets/eab-gui-util.c:275', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (17, 19, 17, 1, '', 'addressbook/gui/widgets/foo.c:345', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (18, 21, 18, 1, ' start po-group: common', 'encfs/FileUtils.cpp:1044', 'xgroup(common)', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (19, 22, 19, 1, '', 'encfs/main.cpp:340', 'xgroup(usage)', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (20, 23, 20, 1, '', 'encfs/FileUtils.cpp:535', 'xgroup(setup)', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (21, 24, 21, 1, '', 'encfs/encfsctl.cpp:346', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (22, 26, 22, 1, '', 'modules/aggregator.module:15', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (23, 27, 0, 1, NULL, '', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (24, 28, 1, 3, '', 'src/netapplet.c:131', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (25, 29, 2, 3, '', 'src/netapplet.c:133', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (26, 30, 3, 3, '', 'src/netapplet.c:135', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (27, 31, 4, 3, '', 'src/netapplet.c:139', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (28, 32, 5, 3, '', 'src/netapplet.c:141', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (29, 33, 6, 3, '', 'src/netapplet.c:291 src/netapplet.c:312', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (30, 34, 7, 3, '', 'src/netapplet.c:359', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (31, 35, 8, 3, '', 'src/netapplet.c:391', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (32, 36, 9, 3, '', 'src/netapplet.c:410', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (33, 37, 10, 3, '', 'src/netapplet.c:427', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (34, 38, 11, 3, '', 'src/netapplet.c:479', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (35, 39, 12, 3, '', 'src/netapplet.c:496', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (36, 40, 13, 3, '', 'src/netapplet.c:732', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (37, 41, 14, 3, '', 'src/netapplet.c:747', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (38, 42, 15, 3, '', 'src/netapplet.c:768', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (39, 43, 16, 3, '', 'src/netapplet.c:870', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (40, 44, 17, 3, '', 'src/netapplet.c:955', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (41, 45, 18, 3, '', 'src/netapplet.c:958', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (42, 46, 19, 3, '', 'src/netapplet.c:970', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (43, 47, 20, 3, '', 'src/netapplet.c:1015', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (44, 48, 21, 3, '', 'src/netapplet.c:1018', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (45, 49, 22, 3, '', 'src/netapplet.c:1021', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (46, 50, 23, 3, '', 'src/netapplet.c:1032', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (47, 51, 24, 3, '', 'src/netapplet.c:1072', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (48, 52, 25, 3, '', 'src/netapplet.c:1082', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (49, 53, 26, 3, '', 'src/netapplet.c:1093', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (50, 54, 27, 3, '', 'src/netapplet.c:1526', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (51, 55, 28, 3, '', 'src/netapplet.glade.h:1', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (52, 56, 29, 3, '', 'src/netapplet.glade.h:2', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (53, 57, 30, 3, '', 'src/netapplet.glade.h:3', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (54, 58, 31, 3, '', 'src/netapplet.glade.h:4', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (55, 59, 32, 3, '', 'src/netapplet.glade.h:5', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (56, 60, 33, 3, '', 'src/netapplet.glade.h:6', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (57, 61, 34, 3, '', 'src/netapplet.glade.h:7', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (58, 62, 35, 3, '', 'src/netapplet.glade.h:8', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (59, 63, 36, 3, '', 'src/netapplet.glade.h:9', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (60, 64, 37, 3, '', 'src/netapplet.glade.h:10', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (61, 65, 38, 3, '', 'src/netapplet.glade.h:11', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (62, 66, 39, 3, '', 'src/netapplet.glade.h:12', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (63, 67, 40, 3, '', 'src/netapplet.glade.h:13', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (64, 68, 41, 3, '', 'src/netapplet.glade.h:14', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (65, 69, 42, 3, '', 'src/netapplet.glade.h:15', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (66, 70, 43, 3, '', 'src/netapplet.glade.h:16', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (67, 71, 1, 2, '', 'pmount.c:50', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (68, 72, 2, 2, '', 'pmount.c:57', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (69, 73, 3, 2, '', 'pmount.c:64', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (70, 74, 4, 2, '', 'pmount.c:67', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (71, 75, 5, 2, '', 'pmount.c:120', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (72, 76, 6, 2, '', 'pmount.c:126', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (73, 77, 7, 2, '', 'pmount.c:130', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (74, 78, 8, 2, '', 'pmount.c:134', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (75, 79, 9, 2, '', 'pmount.c:141', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (76, 80, 10, 2, '', 'pmount.c:171 pumount.c:98', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (77, 81, 11, 2, '', 'pmount.c:176 pmount.c:270', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (78, 82, 12, 2, '', 'pmount.c:212', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (79, 83, 13, 2, '', 'pmount.c:218', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (80, 84, 14, 2, '', 'pmount.c:242', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (81, 85, 15, 2, '', 'pmount.c:258 pumount.c:124', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (82, 86, 16, 2, '', 'pmount.c:274', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (83, 87, 17, 2, '', 'pmount.c:347', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (84, 88, 18, 2, '', 'pmount.c:361', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (85, 89, 19, 2, '', 'pmount.c:401', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (86, 90, 20, 2, '', 'pmount.c:417', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (87, 91, 21, 2, '', 'pmount.c:509 pumount.c:181', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (88, 92, 22, 2, '', 'pmount.c:542 pumount.c:201', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (89, 93, 23, 2, '', 'pmount.c:580', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (90, 94, 24, 2, '', 'pmount.c:589 pumount.c:237', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (91, 95, 25, 2, '', 'pmount.c:595 pumount.c:243', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (92, 96, 26, 2, '', 'pmount.c:635', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (93, 97, 27, 2, '', 'pmount.c:656', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (94, 98, 28, 2, '', 'pmount-hal.c:29', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (95, 99, 29, 2, '', 'pmount-hal.c:140', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (96, 100, 30, 2, '', 'pmount-hal.c:169', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (97, 101, 31, 2, '', 'pmount-hal.c:175', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (98, 102, 32, 2, '', 'pmount-hal.c:182', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (99, 103, 33, 2, '', 'policy.c:79', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (100, 104, 34, 2, '', 'policy.c:90', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (101, 105, 35, 2, '', 'policy.c:97', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (102, 106, 36, 2, '', 'policy.c:128', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (103, 107, 37, 2, '', 'policy.c:228', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (104, 108, 38, 2, '', 'policy.c:233', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (105, 109, 39, 2, '', 'policy.c:251 policy.c:307', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (106, 110, 40, 2, '', 'policy.c:338', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (107, 111, 41, 2, '', 'policy.c:340', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (108, 112, 42, 2, '', 'policy.c:342', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (109, 113, 43, 2, '', 'policy.c:378', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (110, 114, 44, 2, '', 'policy.c:393', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (111, 115, 45, 2, '', 'policy.c:411', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (112, 116, 46, 2, '', 'policy.c:413', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (113, 117, 47, 2, '', 'pumount.c:42', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (114, 118, 48, 2, '', 'pumount.c:72', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (115, 119, 49, 2, '', 'pumount.c:78', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (116, 120, 50, 2, '', 'pumount.c:108 pumount.c:136', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (117, 121, 51, 2, '', 'pumount.c:140', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (118, 122, 52, 2, '', 'pumount.c:148', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (119, 123, 53, 2, '', 'utils.c:51', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (120, 124, 54, 2, '', 'utils.c:107', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (121, 125, 55, 2, '', 'utils.c:122', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (122, 126, 56, 2, '', 'utils.c:129', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (123, 127, 57, 2, '', 'utils.c:149', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (124, 128, 58, 2, '', 'utils.c:158', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (125, 129, 59, 2, '', 'utils.c:210', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (126, 130, 60, 2, '', 'utils.c:252', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (127, 131, 61, 2, '', 'utils.c:261', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (128, 132, 62, 2, '', 'utils.c:270', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (129, 133, 63, 2, '', 'utils.c:279', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (130, 1, 1, 4, '', 'a11y/addressbook/ea-addressbook-view.c:94
a11y/addressbook/ea-addressbook-view.c:103
a11y/addressbook/ea-minicard-view.c:119', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (131, 2, 2, 4, '', 'a11y/addressbook/ea-minicard-view.c:101', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (132, 3, 3, 4, '', 'a11y/addressbook/ea-minicard-view.c:102', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (133, 4, 4, 4, '', 'a11y/addressbook/ea-minicard-view.c:102', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (134, 5, 5, 4, '', 'a11y/addressbook/ea-minicard-view.c:104', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (135, 6, 6, 4, '', 'a11y/addressbook/ea-minicard-view.c:104', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (136, 7, 7, 4, '', 'a11y/addressbook/ea-minicard-view.c:105', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (137, 8, 8, 4, '', 'a11y/addressbook/ea-minicard.c:166', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (138, 9, 9, 4, '', 'addressbook/addressbook-errors.xml.h:2', 'addressbook:ldap-init primary', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (139, 10, 10, 4, '', 'addressbook/addressbook-errors.xml.h:4', 'addressbook:ldap-init secondary', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (140, 11, 11, 4, '', 'addressbook/addressbook-errors.xml.h:6', 'addressbook:ldap-auth primary', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (141, 12, 12, 4, '', 'addressbook/addressbook-errors.xml.h:8', 'addressbook:ldap-auth secondary', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (142, 13, 13, 4, '', 'addressbook/gui/component/addressbook-migrate.c:124
calendar/gui/migration.c:188 mail/em-migrate.c:1201', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (143, 14, 14, 4, '', 'addressbook/gui/component/addressbook-migrate.c:1123', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (144, 15, 15, 4, '', 'addressbook/gui/widgets/e-addressbook-model.c:151', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (145, 17, 16, 4, '', 'addressbook/gui/widgets/eab-gui-util.c:275', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (146, 19, 17, 4, '', 'addressbook/gui/widgets/foo.c:345', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (147, 21, 18, 4, ' start po-group: common', 'encfs/FileUtils.cpp:1044', 'xgroup(common)', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (148, 22, 19, 4, '', 'encfs/main.cpp:340', 'xgroup(usage)', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (149, 23, 20, 4, '', 'encfs/FileUtils.cpp:535', 'xgroup(setup)', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (150, 24, 21, 4, '', 'encfs/encfsctl.cpp:346', '', 'c-format');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (151, 26, 22, 4, '', 'modules/aggregator.module:15', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (152, 134, 1, 5, '', '../mozilla-browser.templates:3', 'Type: note
Description', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (153, 135, 2, 5, '', '../mozilla-browser.templates:3', 'Type: note
Description', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (154, 136, 3, 5, '', '../mozilla-browser.templates:3', 'Type: note
Description', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (155, 137, 4, 5, '', '../mozilla-browser.templates:11', 'Type: select
Choices', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (156, 138, 5, 5, '', '../mozilla-browser.templates:13', 'Type: select
Description', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (157, 139, 6, 5, '', '../mozilla-browser.templates:13', 'Type: select
Description', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (158, 140, 7, 5, '', '../mozilla-browser.templates:24', 'Type: boolean
Description', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (159, 141, 8, 5, '', '../mozilla-browser.templates:24', 'Type: boolean
Description', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (160, 142, 9, 5, '', '../mozilla-browser.templates:24', 'Type: boolean
Description', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (161, 27, 0, 4, NULL, '', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (162, 143, 0, 5, NULL, '', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (163, 144, 0, 5, NULL, '', '', '');
INSERT INTO potmsgset (id, primemsgid, "sequence", potemplate, commenttext, filereferences, sourcecomment, flagscomment) VALUES (164, 145, 0, 5, NULL, '', '', '');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'potmsgset'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'launchpaddatabaserevision'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'launchpaddatabaserevision'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'bounty'::pg_catalog.regclass;

INSERT INTO bounty (id, name, title, summary, description, usdvalue, difficulty, duration, reviewer, datecreated, "owner", deadline, claimant, dateclaimed) VALUES (1, 'foomatic-widgets', 'Make foomatic have better widgets.', 'Foomatic needs to have way better widgets. The current ones are SO WinXP. Eeewww. Maybe we can get some of that K-Bling that I saw in Kubuntu?', 'The widgets need to be particularly polished, since foomatic is going to be the default foomaster on the desktop for the planet.', 453.44, 65, '7 days', 16, '2005-03-11 09:17:40.585397', 16, NULL, NULL, NULL);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'bounty'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'bugmessage'::pg_catalog.regclass;

INSERT INTO bugmessage (id, bug, message) VALUES (1, 2, 1);
INSERT INTO bugmessage (id, bug, message) VALUES (2, 1, 3);
INSERT INTO bugmessage (id, bug, message) VALUES (3, 1, 4);
INSERT INTO bugmessage (id, bug, message) VALUES (4, 2, 5);
INSERT INTO bugmessage (id, bug, message) VALUES (5, 2, 6);
INSERT INTO bugmessage (id, bug, message) VALUES (6, 4, 7);
INSERT INTO bugmessage (id, bug, message) VALUES (7, 5, 8);
INSERT INTO bugmessage (id, bug, message) VALUES (8, 6, 9);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'bugmessage'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'cveref'::pg_catalog.regclass;

INSERT INTO cveref (id, bug, cveref, title, datecreated, "owner", cvestate) VALUES (1, 1, '1999-8979', 'Firefox crashes all the time', '2005-08-03 12:05:41.746447', 16, 2);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'cveref'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'karma'::pg_catalog.regclass;

INSERT INTO karma (id, datecreated, person, "action") VALUES (1, '2005-07-05 05:24:07.409248', 12, 1);
INSERT INTO karma (id, datecreated, person, "action") VALUES (2, '2005-07-05 05:24:07.414864', 12, 2);
INSERT INTO karma (id, datecreated, person, "action") VALUES (3, '2005-07-05 05:24:07.415443', 12, 3);
INSERT INTO karma (id, datecreated, person, "action") VALUES (4, '2005-07-05 05:24:07.415915', 12, 4);
INSERT INTO karma (id, datecreated, person, "action") VALUES (5, '2005-07-05 05:24:07.416384', 12, 5);
INSERT INTO karma (id, datecreated, person, "action") VALUES (6, '2005-07-05 05:24:07.416837', 12, 6);
INSERT INTO karma (id, datecreated, person, "action") VALUES (7, '2005-07-05 05:24:07.41729', 12, 7);
INSERT INTO karma (id, datecreated, person, "action") VALUES (8, '2005-07-05 05:24:07.417756', 12, 8);
INSERT INTO karma (id, datecreated, person, "action") VALUES (9, '2005-07-05 05:24:07.418209', 12, 9);
INSERT INTO karma (id, datecreated, person, "action") VALUES (10, '2005-07-13 14:43:02.452716', 12, 9);
INSERT INTO karma (id, datecreated, person, "action") VALUES (11, '2005-08-03 12:04:50.669962', 16, 9);
INSERT INTO karma (id, datecreated, person, "action") VALUES (12, '2005-08-04 01:15:48.241836', 16, 9);
INSERT INTO karma (id, datecreated, person, "action") VALUES (13, '2005-08-10 16:30:32.295049', 12, 9);
INSERT INTO karma (id, datecreated, person, "action") VALUES (14, '2005-08-10 16:30:47.448639', 12, 9);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'karma'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'sshkey'::pg_catalog.regclass;

INSERT INTO sshkey (id, person, keytype, keytext, "comment") VALUES (1, 12, 2, 'AAAAB3NzaC1kc3MAAAEBAPfhCA15ZaT08brwVXwpJjcZT6QFIipzF1sGy57HY7QPi/W+uljr1VcCHzWdlSmda7YpTCTx0NFYYQIccQRGX6zYL8v1w9FSRCAnxxUJmqEhsUDFYFdVTa9uLCrs3MSbmh7wwFPdRrGrO6X5x7T4dMZQwykSZrOVdpLcCHRgrMZslLomIAjERn6OAQNiGFz7B2tEi/3Soqd52bGJwOtGymRiAXkPSLbH7KfzSCe34ytdh6BD+4SrgSoa+TL3VDV70QAdlOFXD42ZHl3Sc0Tde4LbZeYq2Uf84DOATLZBbOYpRSqTLkM9XngpnvCRVb6dxEQfgODDw783tEuPpySLj2EAAAAVANpUVgivDjt9gFibN/AXfYy1meeBAAABAB6FtnMywmWZg2lr2I3nDfE5U5QbGUQB/ZEP98ZkSkhOcF29VlnGOxyb2/VZbVTLa/btlPF82L4An/c8VKtKZnel7LnAlMoArdgzQNXGVQQVtnaWwM26ydgDzkSSIes3elNZgsfnPRBvaF0ol9Tqju0rNGKjnr3ZOX/NX+42bxpjRnxYj1h56yP2jKKeGfjorI6JK1YfqBAiTxzaDMzSpknnrbztaKJoh7IFqMMOp9ANSFh7H106pEaCv3ebCTJZprtWqNKjb2zum7OQPRz3upA0qx22ocTokjv4itXJ6yj/BvGu9qdOIQFXuB2rsFtLZtS8ATueOly0GzyeiZBx/AEAAAEBAO8jRYjL7tAYnVlO1p6UzPOicAuGCFWfNbBEDRAXoSgLNdj451jStw+eUc9ZVz7tG/XRVZsiavtFHb2cbrcfX1YOd69xi0m+IY6mo3yKt3irQRokDtt376sHoUdHgj2ozySZJgG8IJndtoS+VQQy6NdClA3fNFb96bF865eNaRYoHJO9ZI84lkWQL++MLzIuyFfCs1hSlapyyuHC8kFmF7AQdrVZvbohSbnWs+w53nIW8nAA7z21wAukvE1Pl6AQyG0e7U1sYS8Pc8dtmzJvdtVZWBl02/gqQJ7f06mFvnsN45rR1Uyxnrwl6rbFwqabZDlyD5Ac6Icbvz9SG1gBOiI=', 'andrew@trogdor');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'sshkey'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'bugtask'::pg_catalog.regclass;

INSERT INTO bugtask (id, bug, product, distribution, distrorelease, sourcepackagename, binarypackagename, status, priority, severity, assignee, dateassigned, datecreated, "owner", milestone, bugwatch, statusexplanation, fti) VALUES (1, 1, 1, NULL, NULL, NULL, NULL, 10, 30, 20, 5, '2004-10-11 11:07:20.330975', '2004-11-13 03:49:22.910183', 12, NULL, NULL, NULL, '');
INSERT INTO bugtask (id, bug, product, distribution, distrorelease, sourcepackagename, binarypackagename, status, priority, severity, assignee, dateassigned, datecreated, "owner", milestone, bugwatch, statusexplanation, fti) VALUES (2, 1, 4, NULL, NULL, NULL, NULL, 10, 10, 20, 1, '2004-10-11 11:07:20.330975', '2004-11-13 03:49:22.910878', 12, NULL, NULL, NULL, '');
INSERT INTO bugtask (id, bug, product, distribution, distrorelease, sourcepackagename, binarypackagename, status, priority, severity, assignee, dateassigned, datecreated, "owner", milestone, bugwatch, statusexplanation, fti) VALUES (3, 2, 1, NULL, NULL, NULL, NULL, 10, 20, 20, NULL, '2004-10-11 11:07:20.330975', '2004-11-13 03:49:22.908491', 12, NULL, NULL, NULL, '');
INSERT INTO bugtask (id, bug, product, distribution, distrorelease, sourcepackagename, binarypackagename, status, priority, severity, assignee, dateassigned, datecreated, "owner", milestone, bugwatch, statusexplanation, fti) VALUES (4, 1, NULL, 3, NULL, 1, NULL, 20, 40, 20, NULL, '2004-10-11 11:07:20.584746', '2004-11-13 03:49:22.79024', 12, NULL, NULL, NULL, '');
INSERT INTO bugtask (id, bug, product, distribution, distrorelease, sourcepackagename, binarypackagename, status, priority, severity, assignee, dateassigned, datecreated, "owner", milestone, bugwatch, statusexplanation, fti) VALUES (5, 2, NULL, 3, NULL, 1, NULL, 20, 40, 20, 12, '2004-10-11 11:07:20.584746', '2004-11-13 03:49:22.824591', 12, NULL, NULL, 'Upstream said that they won''t bother fixing it.', '''fix'':8C ''won'':5C ''said'':2C ''bother'':7C ''upstream'':1C');
INSERT INTO bugtask (id, bug, product, distribution, distrorelease, sourcepackagename, binarypackagename, status, priority, severity, assignee, dateassigned, datecreated, "owner", milestone, bugwatch, statusexplanation, fti) VALUES (6, 3, NULL, 3, NULL, 1, NULL, 10, 20, 30, NULL, '2004-10-11 11:07:20.584746', '2004-11-13 03:49:22.825533', 16, NULL, NULL, NULL, '');
INSERT INTO bugtask (id, bug, product, distribution, distrorelease, sourcepackagename, binarypackagename, status, priority, severity, assignee, dateassigned, datecreated, "owner", milestone, bugwatch, statusexplanation, fti) VALUES (13, 4, 4, NULL, NULL, NULL, NULL, 10, 30, 30, NULL, '2005-01-14 17:20:12.820778', '2005-01-14 17:20:12.820778', 12, NULL, NULL, NULL, '');
INSERT INTO bugtask (id, bug, product, distribution, distrorelease, sourcepackagename, binarypackagename, status, priority, severity, assignee, dateassigned, datecreated, "owner", milestone, bugwatch, statusexplanation, fti) VALUES (14, 5, 4, NULL, NULL, NULL, NULL, 10, 30, 50, 12, '2005-01-14 17:27:03.702622', '2005-01-14 17:27:03.702622', 12, NULL, NULL, 'The status explanation is useful to provide task specific information.', '''use'':5C ''task'':8C ''explan'':3C ''inform'':10C ''provid'':7C ''specif'':9C ''status'':2C');
INSERT INTO bugtask (id, bug, product, distribution, distrorelease, sourcepackagename, binarypackagename, status, priority, severity, assignee, dateassigned, datecreated, "owner", milestone, bugwatch, statusexplanation, fti) VALUES (15, 6, 4, NULL, NULL, NULL, NULL, 10, 30, 40, NULL, '2005-01-14 17:35:39.548665', '2005-01-14 17:35:39.548665', 12, NULL, NULL, NULL, '');
INSERT INTO bugtask (id, bug, product, distribution, distrorelease, sourcepackagename, binarypackagename, status, priority, severity, assignee, dateassigned, datecreated, "owner", milestone, bugwatch, statusexplanation, fti) VALUES (16, 5, NULL, NULL, 1, 1, NULL, 10, 30, 30, NULL, '2005-07-13 14:43:02.452716', '2005-07-13 14:43:02.452716', 12, NULL, NULL, NULL, '');
INSERT INTO bugtask (id, bug, product, distribution, distrorelease, sourcepackagename, binarypackagename, status, priority, severity, assignee, dateassigned, datecreated, "owner", milestone, bugwatch, statusexplanation, fti) VALUES (17, 1, NULL, 1, NULL, 1, NULL, 10, 30, 30, NULL, '2005-08-04 01:15:48.241836', '2005-08-04 01:15:48.241836', 16, NULL, NULL, NULL, '');
INSERT INTO bugtask (id, bug, product, distribution, distrorelease, sourcepackagename, binarypackagename, status, priority, severity, assignee, dateassigned, datecreated, "owner", milestone, bugwatch, statusexplanation, fti) VALUES (18, 3, NULL, NULL, 6, 1, NULL, 10, 30, 30, NULL, '2005-08-10 16:30:32.295049', '2005-08-10 16:30:32.295049', 12, NULL, NULL, NULL, '');
INSERT INTO bugtask (id, bug, product, distribution, distrorelease, sourcepackagename, binarypackagename, status, priority, severity, assignee, dateassigned, datecreated, "owner", milestone, bugwatch, statusexplanation, fti) VALUES (19, 3, NULL, NULL, 7, 1, NULL, 10, 30, 30, NULL, '2005-08-10 16:30:47.448639', '2005-08-10 16:30:47.448639', 12, NULL, NULL, NULL, '');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'bugtask'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'logintoken'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'logintoken'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'milestone'::pg_catalog.regclass;

INSERT INTO milestone (id, product, name, distribution, dateexpected, visible) VALUES (1, 4, '1.0', NULL, NULL, true);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'milestone'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'pushmirroraccess'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'pushmirroraccess'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'buildqueue'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'buildqueue'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'signedcodeofconduct'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'signedcodeofconduct'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'bountysubscription'::pg_catalog.regclass;

INSERT INTO bountysubscription (id, bounty, person, subscription) VALUES (1, 1, 9, 1);
INSERT INTO bountysubscription (id, bounty, person, subscription) VALUES (2, 1, 6, 3);
INSERT INTO bountysubscription (id, bounty, person, subscription) VALUES (3, 1, 1, 2);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'bountysubscription'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'productbounty'::pg_catalog.regclass;

INSERT INTO productbounty (id, bounty, product) VALUES (1, 1, 4);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'productbounty'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'distrobounty'::pg_catalog.regclass;

INSERT INTO distrobounty (id, bounty, distribution) VALUES (1, 1, 1);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'distrobounty'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'projectbounty'::pg_catalog.regclass;

INSERT INTO projectbounty (id, bounty, project) VALUES (1, 1, 4);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'projectbounty'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'mirror'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'mirror'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'mirrorcontent'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'mirrorcontent'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'mirrorsourcecontent'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'mirrorsourcecontent'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'potemplatename'::pg_catalog.regclass;

INSERT INTO potemplatename (id, name, title, description, translationdomain) VALUES (1, 'evolution-2.2', 'Main translation domain for the Evolution 2.2', 'This is a description about Evolution 2.2 POTemplateName', 'evolution-2.2');
INSERT INTO potemplatename (id, name, title, description, translationdomain) VALUES (2, 'pmount', 'Main translation domain for pmount', 'This is the description about pmount''s POTemplateName', 'pmount');
INSERT INTO potemplatename (id, name, title, description, translationdomain) VALUES (3, 'netapplet', 'Main translation domain for netapplet', 'This is the description about netapplet''s POTemplateName', 'netapplet');
INSERT INTO potemplatename (id, name, title, description, translationdomain) VALUES (4, 'pkgconf-mozilla', 'pkgconf-mozilla', NULL, 'pkgconf-mozilla');
INSERT INTO potemplatename (id, name, title, description, translationdomain) VALUES (5, 'evolution-2.2-test', 'Another template for Evolution', NULL, 'evolution-2.2-test');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'potemplatename'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'maintainership'::pg_catalog.regclass;

INSERT INTO maintainership (id, distribution, sourcepackagename, maintainer) VALUES (1, 3, 1, 1);
INSERT INTO maintainership (id, distribution, sourcepackagename, maintainer) VALUES (2, 1, 9, 1);
INSERT INTO maintainership (id, distribution, sourcepackagename, maintainer) VALUES (3, 1, 14, 1);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'maintainership'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'messagechunk'::pg_catalog.regclass;

INSERT INTO messagechunk (id, message, "sequence", content, blob, fti) VALUES (1, 7, 1, 'Malone pages that use more complex layouts with portlets and fancy CSS are sometimes not getting properly reflowed after rendering.', NULL, '''css'':12C ''get'':16C ''use'':4C ''page'':2C ''fanci'':11C ''malon'':1C ''layout'':7C ''proper'':17C ''reflow'':18C ''render'':20C ''complex'':6C ''portlet'':9C ''sometim'':14C');
INSERT INTO messagechunk (id, message, "sequence", content, blob, fti) VALUES (2, 8, 1, 'All ways of downloading firefox should provide complete install instructions. At present, they are only visible on the Release Notes page.', NULL, '''way'':2C ''note'':20C ''page'':21C ''instal'':9C ''provid'':7C ''releas'':19C ''visibl'':16C ''complet'':8C ''firefox'':5C ''present'':12C ''download'':4C ''instruct'':10C');
INSERT INTO messagechunk (id, message, "sequence", content, blob, fti) VALUES (3, 9, 1, 'User-Agent:       
Build Identifier: Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.6) Gecko/20040207 Firefox/0.8

If a Save As dialog for a nonexistent window exists, when the dialog is closed Firefox will crash.  It''s possible to cause this to happen using the "Open With/Save As" dialog.

Reproducible: Always
Steps to Reproduce:
1. Visit http://www.mozilla.org/products/firefox/
2. Click on "Download Now!"  An "Open With/Save" dialog will appear.
4. Press OK.
5. Switch back to the "Open With/Save" dialog, and press OK again.  There are now two Save As dialogs.  This is bug 58777.
6. Close the second dialog with "Cancel"
7. Close the browser window that started all of this.
8. Close the first dialog with "Cancel".

Actual Results:  
Crash!

Expected Results:  
Not crashed.', NULL, '''1'':55C ''2'':60C ''4'':71C ''5'':74C ''6'':97C ''7'':104C ''8'':114C ''u'':8C ''en'':12C ''ok'':73C,84C ''rv'':14C ''us'':13C ''1.6'':15C ''bug'':95C ''two'':89C ''use'':44C ''x11'':7C ''back'':76C ''caus'':40C ''i686'':10C ''open'':46C,66C,79C ''save'':20C,90C ''step'':52C ''user'':2C ''58777'':96C ''agent'':3C ''alway'':51C ''build'':4C ''click'':61C ''close'':32C,98C,105C,115C ''crash'':35C,123C,127C ''en-us'':11C ''exist'':27C ''first'':117C ''linux'':9C ''press'':72C,83C ''start'':110C ''visit'':56C ''actual'':121C ''appear'':70C ''cancel'':103C,120C ''dialog'':22C,30C,49C,68C,81C,92C,101C,118C ''expect'':124C ''happen'':43C ''result'':122C,125C ''second'':100C ''switch'':75C ''window'':26C,108C ''browser'':107C ''firefox'':33C ''possibl'':38C ''user-ag'':1C ''download'':63C ''identifi'':5C ''nonexist'':25C ''reproduc'':50C,54C ''with/save'':47C,67C,80C ''firefox/0.8'':17C ''mozilla/5.0'':6C ''gecko/20040207'':16C ''www.mozilla.org'':58C ''/products/firefox/'':59C ''www.mozilla.org/products/firefox/'':57C');
INSERT INTO messagechunk (id, message, "sequence", content, blob, fti) VALUES (4, 1, 1, 'Problem exists between chair and keyboard', NULL, '''chair'':4C ''exist'':2C ''problem'':1C ''keyboard'':6C');
INSERT INTO messagechunk (id, message, "sequence", content, blob, fti) VALUES (5, 3, 1, 'We''ve seen something very similar on AIX with Gnome 2.6 when it is compiled with XFT support. It might be that the anti-aliasing is causing loopback devices to degrade, resulting in a loss of transparency at the system cache level and decoherence in the undelete function. This is only known to be a problem when the moon is gibbous.', NULL, '''ve'':2C ''2.6'':11C ''aix'':8C ''xft'':17C ''anti'':25C ''cach'':42C ''caus'':28C ''loss'':36C ''moon'':60C ''seen'':3C ''alias'':26C ''devic'':30C ''gnome'':10C ''known'':53C ''level'':43C ''might'':20C ''compil'':15C ''degrad'':32C ''result'':33C ''someth'':4C ''system'':41C ''decoher'':45C ''gibbous'':62C ''problem'':57C ''similar'':6C ''support'':18C ''undelet'':48C ''function'':49C ''loopback'':29C ''transpar'':38C ''anti-alias'':24C');
INSERT INTO messagechunk (id, message, "sequence", content, blob, fti) VALUES (6, 4, 1, 'Sorry, it was SCO unix which appears to have the same bug. For a brief moment I was confused there, since so much code is known to have been copied from SCO into AIX.', NULL, '''aix'':34C ''bug'':12C ''sco'':4C,32C ''code'':24C ''copi'':30C ''much'':23C ''sinc'':21C ''unix'':5C ''brief'':15C ''known'':26C ''sorri'':1C ''appear'':7C ''confus'':19C ''moment'':16C');
INSERT INTO messagechunk (id, message, "sequence", content, blob, fti) VALUES (7, 5, 1, 'This would be a real killer feature. If there is already code to make it possible, why aren''t there tons of press announcements about the secuirty possibilities. Imagine - no more embarrassing emails for Mr Gates... everything they delete would actually disappear! I''m sure Redmond will switch over as soon as they hear about this. It''s not a bug, it''s a feature!', NULL, '''m'':44C ''mr'':35C ''bug'':61C ''ton'':21C ''aren'':18C ''code'':12C ''gate'':36C ''hear'':54C ''make'':14C ''real'':5C ''soon'':51C ''sure'':45C ''delet'':39C ''email'':33C ''press'':23C ''would'':2C,40C ''actual'':41C ''featur'':7C,65C ''imagin'':29C ''killer'':6C ''switch'':48C ''alreadi'':11C ''announc'':24C ''everyth'':37C ''possibl'':16C,28C ''redmond'':46C ''secuirti'':27C ''disappear'':42C ''embarrass'':32C');
INSERT INTO messagechunk (id, message, "sequence", content, blob, fti) VALUES (8, 6, 1, 'Oddly enough the bug system seems only capable of displaying the first two comments that are made against a bug. I wonder why that is? Lets have a few more decent legth comments in here so we can see what the spacing is like. Also, at some stage, we''ll need a few comments that get displayed in a fixed-width font, so we have a clue about code-in-bug-comments etc.', NULL, '''ll'':50C ''bug'':4C,20C,73C ''etc'':75C ''fix'':61C ''get'':56C ''let'':26C ''odd'':1C ''see'':39C ''two'':13C ''also'':45C ''clue'':68C ''code'':71C ''font'':63C ''like'':44C ''made'':17C ''need'':51C ''seem'':6C ''first'':12C ''legth'':32C ''space'':42C ''stage'':48C ''width'':62C ''capabl'':8C ''decent'':31C ''enough'':2C ''system'':5C ''wonder'':22C ''comment'':14C,33C,54C,74C ''display'':10C,57C ''fixed-width'':60C ''code-in-bug-com'':70C');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'messagechunk'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'sourcepackagepublishinghistory'::pg_catalog.regclass;

INSERT INTO sourcepackagepublishinghistory (id, sourcepackagerelease, distrorelease, status, component, section, datecreated, datepublished, datesuperseded, supersededby, datemadepending, scheduleddeletiondate, dateremoved, pocket, embargo, embargolifted) VALUES (1, 14, 1, 2, 1, 1, '2004-09-27 11:57:13', '2004-09-27 11:57:13', NULL, NULL, NULL, NULL, NULL, 0, false, NULL);
INSERT INTO sourcepackagepublishinghistory (id, sourcepackagerelease, distrorelease, status, component, section, datecreated, datepublished, datesuperseded, supersededby, datemadepending, scheduleddeletiondate, dateremoved, pocket, embargo, embargolifted) VALUES (2, 15, 3, 2, 1, 1, '2004-09-27 11:57:13', '2004-09-27 11:57:13', NULL, NULL, NULL, NULL, NULL, 0, false, NULL);
INSERT INTO sourcepackagepublishinghistory (id, sourcepackagerelease, distrorelease, status, component, section, datecreated, datepublished, datesuperseded, supersededby, datemadepending, scheduleddeletiondate, dateremoved, pocket, embargo, embargolifted) VALUES (4, 17, 1, 2, 1, 1, '2004-03-14 18:00:00', '2004-03-14 18:00:00', NULL, NULL, NULL, NULL, NULL, 0, false, NULL);
INSERT INTO sourcepackagepublishinghistory (id, sourcepackagerelease, distrorelease, status, component, section, datecreated, datepublished, datesuperseded, supersededby, datemadepending, scheduleddeletiondate, dateremoved, pocket, embargo, embargolifted) VALUES (5, 16, 3, 2, 1, 1, '2004-03-10 16:30:00', '2004-03-10 16:30:00', NULL, NULL, NULL, NULL, NULL, 0, false, NULL);
INSERT INTO sourcepackagepublishinghistory (id, sourcepackagerelease, distrorelease, status, component, section, datecreated, datepublished, datesuperseded, supersededby, datemadepending, scheduleddeletiondate, dateremoved, pocket, embargo, embargolifted) VALUES (8, 20, 3, 2, 1, 1, '2005-04-18 17:34:15.308434', '2005-04-18 17:34:15.308434', NULL, NULL, NULL, NULL, NULL, 0, false, NULL);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'sourcepackagepublishinghistory'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'packagepublishinghistory'::pg_catalog.regclass;

INSERT INTO packagepublishinghistory (id, binarypackage, distroarchrelease, status, component, section, priority, datecreated, datepublished, datesuperseded, supersededby, datemadepending, scheduleddeletiondate, dateremoved, pocket, embargo, embargolifted) VALUES (9, 12, 1, 2, 1, 1, 10, '2005-05-05 00:00:00', NULL, NULL, NULL, NULL, NULL, NULL, 0, false, NULL);
INSERT INTO packagepublishinghistory (id, binarypackage, distroarchrelease, status, component, section, priority, datecreated, datepublished, datesuperseded, supersededby, datemadepending, scheduleddeletiondate, dateremoved, pocket, embargo, embargolifted) VALUES (11, 15, 6, 2, 1, 1, 40, '2005-05-05 00:00:00', NULL, NULL, NULL, NULL, NULL, NULL, 0, false, NULL);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'packagepublishinghistory'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'translationgroup'::pg_catalog.regclass;

INSERT INTO translationgroup (id, name, title, summary, datecreated, "owner") VALUES (1, 'testing-translation-team', 'Just a testing team', 'This team is to test the translation restrictions', '2005-07-12 14:30:24.162667', 13);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'translationgroup'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'translator'::pg_catalog.regclass;

INSERT INTO translator (id, translationgroup, "language", translator, datecreated) VALUES (1, 1, 387, 53, '2005-07-13 13:14:19.748396');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'translator'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'pocketchroot'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'pocketchroot'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'posubmission'::pg_catalog.regclass;

INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (1, 1, 0, 1, 1, '2005-04-07 13:19:17.601068', 13, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (2, 2, 0, 2, 1, '2005-04-07 13:19:17.601068', 13, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (3, 3, 0, 3, 1, '2005-04-07 13:19:17.601068', 13, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (4, 5, 0, 4, 1, '2005-04-07 13:19:17.601068', 13, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (5, 14, 0, 5, 1, '2005-04-07 13:19:17.601068', 13, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (6, 15, 0, 6, 1, '2005-04-07 13:19:17.601068', 13, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (7, 15, 1, 7, 1, '2005-04-07 13:19:17.601068', 13, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (8, 16, 0, 8, 1, '2005-04-07 13:19:17.601068', 13, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (9, 16, 1, 9, 1, '2005-04-07 13:19:17.601068', 13, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (10, 17, 0, 10, 1, '2005-04-07 13:19:17.601068', 13, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (11, 18, 0, 11, 1, '2005-04-07 13:19:17.601068', 13, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (12, 22, 0, 12, 1, '2005-04-07 13:19:17.601068', 13, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (13, 23, 0, 13, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (14, 24, 0, 14, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (15, 25, 0, 15, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (16, 26, 0, 16, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (17, 27, 0, 17, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (18, 28, 0, 18, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (19, 29, 0, 19, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (20, 30, 0, 20, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (21, 31, 0, 21, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (22, 32, 0, 22, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (23, 33, 0, 23, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (24, 34, 0, 24, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (25, 35, 0, 25, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (26, 36, 0, 26, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (27, 37, 0, 27, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (28, 38, 0, 28, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (29, 39, 0, 29, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (30, 40, 0, 30, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (31, 41, 0, 31, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (32, 42, 0, 32, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (33, 43, 0, 33, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (34, 44, 0, 34, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (35, 45, 0, 35, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (36, 46, 0, 36, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (37, 47, 0, 37, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (38, 48, 0, 38, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (39, 49, 0, 39, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (40, 50, 0, 40, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (41, 51, 0, 41, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (42, 52, 0, 42, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (43, 53, 0, 43, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (44, 54, 0, 44, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (45, 55, 0, 45, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (46, 56, 0, 46, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (47, 57, 0, 47, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (48, 58, 0, 48, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (49, 59, 0, 49, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (50, 60, 0, 50, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (51, 61, 0, 51, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (52, 62, 0, 52, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (53, 63, 0, 53, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (54, 64, 0, 54, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (55, 65, 0, 55, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (56, 66, 0, 56, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (57, 67, 0, 57, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (58, 68, 0, 58, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (59, 69, 0, 59, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (60, 70, 0, 60, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (61, 71, 0, 61, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (62, 72, 0, 62, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (63, 73, 0, 63, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (64, 74, 0, 64, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (65, 75, 0, 65, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (66, 76, 0, 66, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (67, 77, 0, 67, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (68, 78, 0, 68, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (69, 79, 0, 69, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (70, 80, 0, 70, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (71, 81, 0, 71, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (72, 82, 0, 72, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (73, 83, 0, 73, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (74, 84, 0, 74, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (75, 85, 0, 75, 1, '2005-05-06 20:09:31.825695', 33, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (76, 86, 0, 76, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (77, 87, 0, 77, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (78, 88, 0, 78, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (79, 89, 0, 79, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (80, 90, 0, 80, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (81, 91, 0, 81, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (82, 92, 0, 82, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (83, 93, 0, 83, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (84, 94, 0, 84, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (85, 95, 0, 85, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (86, 96, 0, 86, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (87, 97, 0, 87, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (88, 98, 0, 88, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (89, 99, 0, 89, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (90, 100, 0, 90, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (91, 101, 0, 91, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (92, 102, 0, 92, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (93, 103, 0, 93, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (94, 104, 0, 94, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (95, 105, 0, 95, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (96, 106, 0, 96, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (97, 107, 0, 97, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (98, 108, 0, 98, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (99, 109, 0, 99, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (100, 110, 0, 100, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (101, 111, 0, 101, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (102, 112, 0, 102, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (103, 113, 0, 103, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (104, 114, 0, 104, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (105, 115, 0, 105, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (106, 116, 0, 106, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (107, 117, 0, 107, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (108, 118, 0, 108, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (109, 119, 0, 109, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (110, 120, 0, 110, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (111, 121, 0, 111, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (112, 122, 0, 112, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (113, 123, 0, 113, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (114, 124, 0, 114, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (115, 125, 0, 115, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (116, 126, 0, 116, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (117, 127, 0, 117, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (118, 128, 0, 118, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (119, 129, 0, 119, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (120, 130, 0, 120, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (121, 131, 0, 121, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (122, 132, 0, 122, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (123, 133, 0, 123, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (124, 134, 0, 124, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (125, 135, 0, 125, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (126, 136, 0, 126, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (127, 137, 0, 127, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (128, 138, 0, 128, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (129, 139, 0, 129, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (130, 140, 0, 130, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (131, 141, 0, 131, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (132, 142, 0, 105, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (133, 143, 0, 132, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (134, 144, 0, 133, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (135, 145, 0, 134, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (136, 146, 0, 135, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (137, 147, 0, 136, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (138, 148, 0, 137, 1, '2005-05-06 20:09:51.386766', 34, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (139, 149, 0, 138, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (140, 150, 0, 139, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (141, 151, 0, 140, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (142, 152, 0, 141, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (143, 153, 0, 142, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (144, 154, 0, 143, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (145, 155, 0, 144, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (146, 156, 0, 145, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (147, 157, 0, 146, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (148, 158, 0, 147, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (149, 159, 0, 148, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (150, 160, 0, 149, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (151, 161, 0, 150, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (152, 162, 0, 151, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (153, 163, 0, 152, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (154, 164, 0, 153, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (155, 165, 0, 154, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (156, 166, 0, 155, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (157, 167, 0, 156, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (158, 168, 0, 157, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (159, 169, 0, 158, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (160, 170, 0, 159, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (161, 171, 0, 160, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (162, 172, 0, 161, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (163, 173, 0, 162, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (164, 174, 0, 163, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (165, 175, 0, 164, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (166, 176, 0, 165, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (167, 177, 0, 166, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (168, 178, 0, 167, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (169, 179, 0, 168, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (170, 180, 0, 169, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (171, 181, 0, 170, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (172, 182, 0, 171, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (173, 183, 0, 172, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (174, 184, 0, 173, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (175, 185, 0, 174, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (176, 186, 0, 175, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (177, 187, 0, 176, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (178, 188, 0, 177, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (179, 189, 0, 178, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (180, 190, 0, 179, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (181, 191, 0, 180, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (182, 192, 0, 181, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (183, 193, 0, 182, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (184, 194, 0, 183, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (185, 195, 0, 184, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (186, 196, 0, 185, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (187, 197, 0, 186, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (188, 198, 0, 187, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (189, 199, 0, 188, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (190, 200, 0, 189, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (191, 201, 0, 190, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (192, 202, 0, 191, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (193, 203, 0, 192, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (194, 204, 0, 193, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (195, 205, 0, 194, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (196, 206, 0, 195, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (197, 207, 0, 196, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (198, 208, 0, 197, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (199, 209, 0, 198, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (200, 210, 0, 199, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (201, 211, 0, 200, 1, '2005-05-06 20:10:18.431259', 35, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (202, 212, 0, 201, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (203, 213, 0, 202, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (204, 214, 0, 203, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (205, 215, 0, 204, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (206, 216, 0, 205, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (207, 217, 0, 206, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (208, 218, 0, 207, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (209, 219, 0, 208, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (210, 220, 0, 209, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (211, 221, 0, 210, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (212, 222, 0, 211, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (213, 223, 0, 212, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (214, 224, 0, 213, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (215, 225, 0, 214, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (216, 226, 0, 215, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (217, 227, 0, 216, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (218, 228, 0, 217, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (219, 229, 0, 218, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (220, 230, 0, 219, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (221, 231, 0, 220, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (222, 232, 0, 221, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (223, 233, 0, 222, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (224, 234, 0, 223, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (225, 235, 0, 224, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (226, 236, 0, 225, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (227, 237, 0, 226, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (228, 238, 0, 227, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (229, 239, 0, 228, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (230, 240, 0, 229, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (231, 241, 0, 230, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (232, 242, 0, 231, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (233, 243, 0, 232, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (234, 244, 0, 233, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (235, 245, 0, 234, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (236, 246, 0, 235, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (237, 247, 0, 236, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (238, 248, 0, 237, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (239, 249, 0, 238, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (240, 250, 0, 239, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (241, 251, 0, 240, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (242, 252, 0, 241, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (243, 253, 0, 242, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (244, 254, 0, 243, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (245, 255, 0, 244, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (246, 256, 0, 245, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (247, 257, 0, 246, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (248, 258, 0, 247, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (249, 259, 0, 248, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (250, 260, 0, 249, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (251, 261, 0, 250, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (252, 262, 0, 251, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (253, 263, 0, 252, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (254, 264, 0, 253, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (255, 265, 0, 254, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (256, 266, 0, 255, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (257, 267, 0, 256, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (258, 268, 0, 257, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (259, 269, 0, 258, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (260, 270, 0, 259, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (261, 271, 0, 260, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (262, 272, 0, 261, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (263, 273, 0, 262, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (264, 274, 0, 263, 1, '2005-05-06 20:10:41.732277', 36, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (265, 275, 0, 264, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (266, 276, 0, 265, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (267, 277, 0, 266, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (268, 278, 0, 267, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (269, 279, 0, 268, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (270, 280, 0, 269, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (271, 281, 0, 270, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (272, 282, 0, 271, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (273, 283, 0, 272, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (274, 284, 0, 273, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (275, 285, 0, 274, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (276, 286, 0, 275, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (277, 287, 0, 276, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (278, 288, 0, 277, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (279, 289, 0, 278, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (280, 290, 0, 279, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (281, 291, 0, 280, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (282, 292, 0, 281, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (283, 293, 0, 282, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (284, 294, 0, 283, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (285, 295, 0, 284, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (286, 296, 0, 285, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (287, 297, 0, 286, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (288, 298, 0, 287, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (289, 299, 0, 288, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (290, 300, 0, 289, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (291, 301, 0, 290, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (292, 302, 0, 291, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (293, 303, 0, 292, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (294, 304, 0, 293, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (295, 305, 0, 294, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (296, 306, 0, 295, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (297, 307, 0, 296, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (298, 308, 0, 297, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (299, 309, 0, 298, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (300, 310, 0, 299, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (301, 311, 0, 300, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (302, 312, 0, 301, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (303, 313, 0, 302, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (304, 314, 0, 303, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (305, 315, 0, 304, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (306, 316, 0, 305, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (307, 317, 0, 306, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (308, 318, 0, 307, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (309, 319, 0, 308, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (310, 320, 0, 309, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (311, 321, 0, 310, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (312, 322, 0, 311, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (313, 323, 0, 312, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (314, 324, 0, 313, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (315, 325, 0, 314, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (316, 326, 0, 315, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (317, 327, 0, 316, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (318, 328, 0, 317, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (319, 329, 0, 318, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (320, 330, 0, 319, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (321, 331, 0, 320, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (322, 332, 0, 321, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (323, 333, 0, 322, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (324, 334, 0, 323, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (325, 335, 0, 324, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (326, 336, 0, 325, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (327, 337, 0, 326, 1, '2005-05-06 20:11:16.591589', 37, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (328, 338, 0, 327, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (329, 339, 0, 328, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (330, 340, 0, 329, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (331, 341, 0, 330, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (332, 342, 0, 331, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (333, 343, 0, 332, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (334, 344, 0, 333, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (335, 345, 0, 334, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (336, 346, 0, 335, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (337, 347, 0, 336, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (338, 348, 0, 337, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (339, 349, 0, 338, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (340, 350, 0, 339, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (341, 351, 0, 340, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (342, 352, 0, 341, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (343, 353, 0, 342, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (344, 354, 0, 343, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (345, 355, 0, 344, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (346, 356, 0, 345, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (347, 357, 0, 346, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (348, 358, 0, 347, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (349, 359, 0, 348, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (350, 360, 0, 349, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (351, 361, 0, 350, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (352, 362, 0, 351, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (353, 363, 0, 352, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (354, 364, 0, 353, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (355, 365, 0, 354, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (356, 366, 0, 355, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (357, 367, 0, 356, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (358, 368, 0, 357, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (359, 369, 0, 358, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (360, 370, 0, 359, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (361, 371, 0, 360, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (362, 372, 0, 361, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (363, 373, 0, 362, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (364, 374, 0, 363, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (365, 375, 0, 364, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (366, 376, 0, 365, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (367, 377, 0, 366, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (368, 378, 0, 367, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (369, 379, 0, 368, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (370, 380, 0, 369, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (371, 381, 0, 370, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (372, 382, 0, 371, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (373, 383, 0, 372, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (374, 384, 0, 373, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (375, 385, 0, 374, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (376, 386, 0, 375, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (377, 387, 0, 376, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (378, 388, 0, 377, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (379, 389, 0, 378, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (380, 390, 0, 379, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (381, 391, 0, 380, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (382, 392, 0, 381, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (383, 393, 0, 382, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (384, 394, 0, 383, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (385, 395, 0, 384, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (386, 396, 0, 385, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (387, 397, 0, 386, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (388, 398, 0, 387, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (389, 399, 0, 388, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (390, 400, 0, 389, 1, '2005-05-06 20:11:41.773683', 38, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (391, 401, 0, 390, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (392, 402, 0, 391, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (393, 403, 0, 392, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (394, 404, 0, 393, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (395, 405, 0, 394, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (396, 406, 0, 395, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (397, 407, 0, 396, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (398, 408, 0, 397, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (399, 409, 0, 398, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (400, 410, 0, 399, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (401, 411, 0, 400, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (402, 412, 0, 401, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (403, 413, 0, 402, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (404, 414, 0, 403, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (405, 415, 0, 404, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (406, 416, 0, 405, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (407, 417, 0, 406, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (408, 418, 0, 407, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (409, 419, 0, 408, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (410, 420, 0, 409, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (411, 421, 0, 410, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (412, 422, 0, 411, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (413, 423, 0, 412, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (414, 424, 0, 413, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (415, 425, 0, 414, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (416, 426, 0, 415, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (417, 427, 0, 416, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (418, 428, 0, 417, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (419, 429, 0, 418, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (420, 430, 0, 419, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (421, 431, 0, 420, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (422, 432, 0, 421, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (423, 433, 0, 422, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (424, 434, 0, 423, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (425, 435, 0, 424, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (426, 436, 0, 425, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (427, 437, 0, 426, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (428, 438, 0, 427, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (429, 439, 0, 428, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (430, 440, 0, 429, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (431, 441, 0, 430, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (432, 442, 0, 431, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (433, 443, 0, 432, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (434, 444, 0, 433, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (435, 445, 0, 434, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (436, 446, 0, 435, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (437, 447, 0, 436, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (438, 448, 0, 437, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (439, 449, 0, 438, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (440, 450, 0, 439, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (441, 451, 0, 440, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (442, 452, 0, 441, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (443, 453, 0, 442, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (444, 454, 0, 443, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (445, 455, 0, 444, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (446, 456, 0, 445, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (447, 457, 0, 446, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (448, 458, 0, 447, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (449, 459, 0, 448, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (450, 460, 0, 449, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (451, 461, 0, 450, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (452, 462, 0, 451, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (453, 463, 0, 452, 1, '2005-05-06 20:12:08.283113', 39, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (454, 464, 0, 453, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (455, 465, 0, 454, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (456, 466, 0, 455, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (457, 467, 0, 456, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (458, 468, 0, 457, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (459, 469, 0, 458, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (460, 470, 0, 459, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (461, 471, 0, 460, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (462, 472, 0, 461, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (463, 474, 0, 462, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (464, 475, 0, 463, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (465, 476, 0, 464, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (466, 477, 0, 465, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (467, 480, 0, 466, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (468, 484, 0, 467, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (469, 485, 0, 468, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (470, 486, 0, 469, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (471, 487, 0, 470, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (472, 488, 0, 471, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (473, 489, 0, 472, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (474, 491, 0, 473, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (475, 492, 0, 474, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (476, 493, 0, 475, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (477, 494, 0, 476, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (478, 495, 0, 477, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (479, 496, 0, 478, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (480, 497, 0, 479, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (481, 498, 0, 480, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (482, 499, 0, 481, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (483, 500, 0, 482, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (484, 501, 0, 483, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (485, 503, 0, 484, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (486, 504, 0, 485, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (487, 505, 0, 486, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (488, 506, 0, 487, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (489, 507, 0, 488, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (490, 508, 0, 489, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (491, 509, 0, 490, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (492, 510, 0, 491, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (493, 511, 0, 492, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (494, 512, 0, 493, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (495, 513, 0, 494, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (496, 515, 0, 495, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (497, 516, 0, 496, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (498, 517, 0, 497, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (499, 519, 0, 498, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (500, 520, 0, 499, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (501, 521, 0, 500, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (502, 522, 0, 501, 1, '2005-05-06 20:12:35.976807', 40, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (503, 527, 0, 264, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (504, 528, 0, 265, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (505, 529, 0, 266, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (506, 530, 0, 267, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (507, 531, 0, 268, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (508, 532, 0, 269, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (509, 533, 0, 270, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (510, 534, 0, 271, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (511, 535, 0, 272, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (512, 536, 0, 273, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (513, 537, 0, 274, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (514, 538, 0, 275, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (515, 539, 0, 276, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (516, 540, 0, 502, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (517, 541, 0, 278, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (518, 542, 0, 279, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (519, 543, 0, 280, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (520, 544, 0, 281, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (521, 545, 0, 282, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (522, 546, 0, 283, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (523, 547, 0, 284, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (524, 548, 0, 503, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (525, 549, 0, 504, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (526, 550, 0, 505, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (527, 551, 0, 506, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (528, 552, 0, 507, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (529, 553, 0, 508, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (530, 555, 0, 292, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (531, 556, 0, 509, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (532, 557, 0, 294, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (533, 558, 0, 295, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (534, 559, 0, 510, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (535, 560, 0, 511, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (536, 561, 0, 512, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (537, 562, 0, 513, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (538, 563, 0, 514, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (539, 564, 0, 515, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (540, 565, 0, 516, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (541, 566, 0, 517, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (542, 567, 0, 304, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (543, 568, 0, 518, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (544, 569, 0, 519, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (545, 570, 0, 307, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (546, 571, 0, 520, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (547, 572, 0, 521, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (548, 573, 0, 522, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (549, 574, 0, 523, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (550, 575, 0, 524, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (551, 576, 0, 525, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (552, 577, 0, 526, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (553, 578, 0, 527, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (554, 579, 0, 528, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (555, 580, 0, 529, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (556, 581, 0, 530, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (557, 582, 0, 319, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (558, 583, 0, 531, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (559, 584, 0, 321, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (560, 585, 0, 322, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (561, 586, 0, 532, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (562, 587, 0, 533, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (563, 588, 0, 534, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (564, 589, 0, 535, 1, '2005-05-06 20:13:10.405056', 41, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (565, 590, 0, 1, 1, '2005-05-06 21:12:13.908028', 13, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (566, 591, 0, 2, 1, '2005-05-06 21:12:13.908028', 13, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (567, 592, 0, 3, 1, '2005-05-06 21:12:13.908028', 13, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (568, 594, 0, 4, 1, '2005-05-06 21:12:13.908028', 13, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (569, 603, 0, 5, 1, '2005-05-06 21:12:13.908028', 13, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (570, 604, 0, 6, 1, '2005-05-06 21:12:13.908028', 13, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (571, 604, 1, 7, 1, '2005-05-06 21:12:13.908028', 13, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (572, 605, 0, 8, 1, '2005-05-06 21:12:13.908028', 13, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (573, 605, 1, 9, 1, '2005-05-06 21:12:13.908028', 13, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (574, 606, 0, 10, 1, '2005-05-06 21:12:13.908028', 13, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (575, 607, 0, 11, 1, '2005-05-06 21:12:13.908028', 13, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (576, 611, 0, 12, 1, '2005-05-06 21:12:13.908028', 13, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (577, 612, 0, 536, 1, '2005-05-06 21:12:18.833057', 42, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (578, 613, 0, 537, 1, '2005-05-06 21:12:18.833057', 42, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (579, 614, 0, 538, 1, '2005-05-06 21:12:18.833057', 42, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (580, 615, 0, 539, 1, '2005-05-06 21:12:18.833057', 42, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (581, 616, 0, 540, 1, '2005-05-06 21:12:18.833057', 42, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (582, 617, 0, 541, 1, '2005-05-06 21:12:18.833057', 42, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (583, 618, 0, 542, 1, '2005-05-06 21:12:18.833057', 42, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (584, 619, 0, 543, 1, '2005-05-06 21:12:18.833057', 42, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (585, 620, 0, 544, 1, '2005-05-06 21:12:18.833057', 42, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (586, 621, 0, 545, 1, '2005-05-06 21:12:20.874654', 43, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (587, 622, 0, 546, 1, '2005-05-06 21:12:20.874654', 43, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (588, 623, 0, 547, 1, '2005-05-06 21:12:20.874654', 43, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (589, 624, 0, 548, 1, '2005-05-06 21:12:20.874654', 43, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (590, 625, 0, 549, 1, '2005-05-06 21:12:20.874654', 43, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (591, 626, 0, 550, 1, '2005-05-06 21:12:20.874654', 43, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (592, 627, 0, 551, 1, '2005-05-06 21:12:20.874654', 43, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (593, 628, 0, 552, 1, '2005-05-06 21:12:20.874654', 43, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (594, 629, 0, 553, 1, '2005-05-06 21:12:20.874654', 43, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (595, 630, 0, 554, 1, '2005-05-06 21:12:23.441015', 30, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (596, 631, 0, 555, 1, '2005-05-06 21:12:23.441015', 30, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (597, 632, 0, 556, 1, '2005-05-06 21:12:23.441015', 30, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (598, 633, 0, 557, 1, '2005-05-06 21:12:23.441015', 30, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (599, 634, 0, 558, 1, '2005-05-06 21:12:23.441015', 30, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (600, 635, 0, 559, 1, '2005-05-06 21:12:23.441015', 30, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (601, 636, 0, 560, 1, '2005-05-06 21:12:23.441015', 30, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (602, 637, 0, 561, 1, '2005-05-06 21:12:23.441015', 30, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (603, 638, 0, 562, 1, '2005-05-06 21:12:23.441015', 30, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (604, 639, 0, 563, 1, '2005-05-06 21:12:25.930403', 44, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (605, 640, 0, 564, 1, '2005-05-06 21:12:25.930403', 44, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (606, 641, 0, 565, 1, '2005-05-06 21:12:25.930403', 44, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (607, 642, 0, 566, 1, '2005-05-06 21:12:25.930403', 44, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (608, 643, 0, 567, 1, '2005-05-06 21:12:25.930403', 44, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (609, 644, 0, 568, 1, '2005-05-06 21:12:25.930403', 44, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (610, 648, 0, 569, 1, '2005-05-06 21:12:27.602384', 45, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (611, 649, 0, 570, 1, '2005-05-06 21:12:27.602384', 45, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (612, 650, 0, 571, 1, '2005-05-06 21:12:27.602384', 45, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (613, 651, 0, 572, 1, '2005-05-06 21:12:27.602384', 45, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (614, 652, 0, 573, 1, '2005-05-06 21:12:27.602384', 45, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (615, 653, 0, 574, 1, '2005-05-06 21:12:27.602384', 45, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (616, 654, 0, 575, 1, '2005-05-06 21:12:27.602384', 45, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (617, 655, 0, 576, 1, '2005-05-06 21:12:27.602384', 45, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (618, 656, 0, 577, 1, '2005-05-06 21:12:27.602384', 45, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (619, 657, 0, 578, 1, '2005-05-06 21:12:29.45271', 46, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (620, 658, 0, 579, 1, '2005-05-06 21:12:29.45271', 46, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (621, 659, 0, 580, 1, '2005-05-06 21:12:29.45271', 46, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (622, 660, 0, 581, 1, '2005-05-06 21:12:29.45271', 46, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (623, 661, 0, 582, 1, '2005-05-06 21:12:29.45271', 46, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (624, 662, 0, 583, 1, '2005-05-06 21:12:29.45271', 46, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (625, 663, 0, 584, 1, '2005-05-06 21:12:29.45271', 46, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (626, 664, 0, 585, 1, '2005-05-06 21:12:29.45271', 46, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (627, 665, 0, 586, 1, '2005-05-06 21:12:29.45271', 46, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (628, 666, 0, 587, 1, '2005-05-06 21:12:31.382429', 47, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (629, 667, 0, 588, 1, '2005-05-06 21:12:31.382429', 47, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (630, 668, 0, 589, 1, '2005-05-06 21:12:31.382429', 47, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (631, 669, 0, 590, 1, '2005-05-06 21:12:31.382429', 47, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (632, 670, 0, 591, 1, '2005-05-06 21:12:31.382429', 47, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (633, 671, 0, 592, 1, '2005-05-06 21:12:31.382429', 47, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (634, 672, 0, 593, 1, '2005-05-06 21:12:31.382429', 47, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (635, 673, 0, 594, 1, '2005-05-06 21:12:31.382429', 47, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (636, 674, 0, 595, 1, '2005-05-06 21:12:31.382429', 47, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (637, 675, 0, 596, 1, '2005-05-06 21:12:33.238579', 48, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (638, 676, 0, 597, 1, '2005-05-06 21:12:33.238579', 48, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (639, 677, 0, 598, 1, '2005-05-06 21:12:33.238579', 48, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (640, 678, 0, 599, 1, '2005-05-06 21:12:33.238579', 48, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (641, 679, 0, 600, 1, '2005-05-06 21:12:33.238579', 48, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (642, 680, 0, 601, 1, '2005-05-06 21:12:33.238579', 48, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (643, 681, 0, 602, 1, '2005-05-06 21:12:33.238579', 48, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (644, 682, 0, 603, 1, '2005-05-06 21:12:33.238579', 48, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (645, 683, 0, 604, 1, '2005-05-06 21:12:33.238579', 48, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (646, 684, 0, 605, 1, '2005-05-06 21:12:33.238579', 48, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (647, 685, 0, 606, 1, '2005-05-06 21:12:33.238579', 48, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (648, 686, 0, 607, 1, '2005-05-06 21:12:33.238579', 48, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (649, 687, 0, 608, 1, '2005-05-06 21:12:35.766036', 30, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (650, 688, 0, 609, 1, '2005-05-06 21:12:35.766036', 30, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (651, 689, 0, 610, 1, '2005-05-06 21:12:35.766036', 30, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (652, 696, 0, 611, 1, '2005-05-06 21:12:37.221421', 49, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (653, 697, 0, 612, 1, '2005-05-06 21:12:37.221421', 49, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (654, 698, 0, 613, 1, '2005-05-06 21:12:37.221421', 49, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (655, 699, 0, 614, 1, '2005-05-06 21:12:37.221421', 49, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (656, 700, 0, 615, 1, '2005-05-06 21:12:37.221421', 49, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (657, 701, 0, 616, 1, '2005-05-06 21:12:37.221421', 49, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (658, 702, 0, 617, 1, '2005-05-06 21:12:37.221421', 49, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (659, 703, 0, 618, 1, '2005-05-06 21:12:37.221421', 49, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (660, 704, 0, 619, 1, '2005-05-06 21:12:37.221421', 49, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (661, 705, 0, 620, 1, '2005-05-06 21:12:39.082421', 50, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (662, 706, 0, 621, 1, '2005-05-06 21:12:39.082421', 50, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (663, 707, 0, 622, 1, '2005-05-06 21:12:39.082421', 50, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (664, 708, 0, 623, 1, '2005-05-06 21:12:39.082421', 50, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (665, 709, 0, 624, 1, '2005-05-06 21:12:39.082421', 50, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (666, 710, 0, 625, 1, '2005-05-06 21:12:39.082421', 50, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (667, 711, 0, 626, 1, '2005-05-06 21:12:39.082421', 50, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (668, 712, 0, 627, 1, '2005-05-06 21:12:39.082421', 50, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (669, 713, 0, 628, 1, '2005-05-06 21:12:39.082421', 50, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (670, 714, 0, 629, 1, '2005-05-06 21:12:40.937835', 30, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (671, 715, 0, 630, 1, '2005-05-06 21:12:40.937835', 30, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (672, 716, 0, 631, 1, '2005-05-06 21:12:40.937835', 30, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (673, 717, 0, 632, 1, '2005-05-06 21:12:40.937835', 30, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (674, 718, 0, 633, 1, '2005-05-06 21:12:40.937835', 30, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (675, 719, 0, 634, 1, '2005-05-06 21:12:40.937835', 30, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (676, 723, 0, 635, 1, '2005-05-06 21:12:42.747648', 51, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (677, 724, 0, 636, 1, '2005-05-06 21:12:42.747648', 51, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (678, 725, 0, 637, 1, '2005-05-06 21:12:42.747648', 51, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (679, 726, 0, 638, 1, '2005-05-06 21:12:42.747648', 51, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (680, 727, 0, 639, 1, '2005-05-06 21:12:42.747648', 51, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (681, 728, 0, 640, 1, '2005-05-06 21:12:42.747648', 51, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (682, 729, 0, 641, 1, '2005-05-06 21:12:42.747648', 51, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (683, 730, 0, 642, 1, '2005-05-06 21:12:42.747648', 51, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (684, 731, 0, 643, 1, '2005-05-06 21:12:42.747648', 51, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (685, 594, 0, 644, 2, '2005-06-06 19:42:48.236409', 16, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (686, 599, 0, 645, 2, '2005-06-06 19:42:48.236409', 16, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (689, 594, 0, 648, 2, '2005-06-06 20:05:03.244905', 50, 0);
INSERT INTO posubmission (id, pomsgset, pluralform, potranslation, origin, datecreated, person, validationstatus) VALUES (690, 5, 0, 649, 2, '2005-06-06 20:08:02.521892', 1, 0);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'posubmission'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'poselection'::pg_catalog.regclass;

INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (1, 1, 0, 1, 1);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (2, 2, 0, 2, 2);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (3, 3, 0, 3, 3);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (4, 5, 0, 4, 4);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (5, 14, 0, 5, 5);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (6, 15, 0, 6, 6);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (7, 15, 1, 7, 7);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (8, 16, 0, 8, 8);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (9, 16, 1, 9, 9);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (10, 17, 0, 10, 10);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (11, 18, 0, 11, 11);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (12, 22, 0, 12, 12);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (13, 23, 0, 13, 13);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (14, 24, 0, 14, 14);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (15, 25, 0, 15, 15);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (16, 26, 0, 16, 16);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (17, 27, 0, 17, 17);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (18, 28, 0, 18, 18);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (19, 29, 0, 19, 19);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (20, 30, 0, 20, 20);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (21, 31, 0, 21, 21);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (22, 32, 0, 22, 22);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (23, 33, 0, 23, 23);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (24, 34, 0, 24, 24);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (25, 35, 0, 25, 25);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (26, 36, 0, 26, 26);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (27, 37, 0, 27, 27);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (28, 38, 0, 28, 28);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (29, 39, 0, 29, 29);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (30, 40, 0, 30, 30);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (31, 41, 0, 31, 31);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (32, 42, 0, 32, 32);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (33, 43, 0, 33, 33);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (34, 44, 0, 34, 34);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (35, 45, 0, 35, 35);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (36, 46, 0, 36, 36);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (37, 47, 0, 37, 37);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (38, 48, 0, 38, 38);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (39, 49, 0, 39, 39);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (40, 50, 0, 40, 40);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (41, 51, 0, 41, 41);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (42, 52, 0, 42, 42);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (43, 53, 0, 43, 43);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (44, 54, 0, 44, 44);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (45, 55, 0, 45, 45);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (46, 56, 0, 46, 46);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (47, 57, 0, 47, 47);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (48, 58, 0, 48, 48);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (49, 59, 0, 49, 49);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (50, 60, 0, 50, 50);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (51, 61, 0, 51, 51);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (52, 62, 0, 52, 52);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (53, 63, 0, 53, 53);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (54, 64, 0, 54, 54);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (55, 65, 0, 55, 55);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (56, 66, 0, 56, 56);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (57, 67, 0, 57, 57);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (58, 68, 0, 58, 58);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (59, 69, 0, 59, 59);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (60, 70, 0, 60, 60);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (61, 71, 0, 61, 61);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (62, 72, 0, 62, 62);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (63, 73, 0, 63, 63);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (64, 74, 0, 64, 64);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (65, 75, 0, 65, 65);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (66, 76, 0, 66, 66);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (67, 77, 0, 67, 67);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (68, 78, 0, 68, 68);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (69, 79, 0, 69, 69);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (70, 80, 0, 70, 70);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (71, 81, 0, 71, 71);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (72, 82, 0, 72, 72);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (73, 83, 0, 73, 73);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (74, 84, 0, 74, 74);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (75, 85, 0, 75, 75);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (76, 86, 0, 76, 76);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (77, 87, 0, 77, 77);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (78, 88, 0, 78, 78);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (79, 89, 0, 79, 79);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (80, 90, 0, 80, 80);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (81, 91, 0, 81, 81);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (82, 92, 0, 82, 82);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (83, 93, 0, 83, 83);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (84, 94, 0, 84, 84);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (85, 95, 0, 85, 85);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (86, 96, 0, 86, 86);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (87, 97, 0, 87, 87);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (88, 98, 0, 88, 88);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (89, 99, 0, 89, 89);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (90, 100, 0, 90, 90);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (91, 101, 0, 91, 91);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (92, 102, 0, 92, 92);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (93, 103, 0, 93, 93);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (94, 104, 0, 94, 94);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (95, 105, 0, 95, 95);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (96, 106, 0, 96, 96);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (97, 107, 0, 97, 97);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (98, 108, 0, 98, 98);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (99, 109, 0, 99, 99);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (100, 110, 0, 100, 100);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (101, 111, 0, 101, 101);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (102, 112, 0, 102, 102);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (103, 113, 0, 103, 103);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (104, 114, 0, 104, 104);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (105, 115, 0, 105, 105);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (106, 116, 0, 106, 106);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (107, 117, 0, 107, 107);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (108, 118, 0, 108, 108);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (109, 119, 0, 109, 109);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (110, 120, 0, 110, 110);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (111, 121, 0, 111, 111);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (112, 122, 0, 112, 112);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (113, 123, 0, 113, 113);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (114, 124, 0, 114, 114);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (115, 125, 0, 115, 115);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (116, 126, 0, 116, 116);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (117, 127, 0, 117, 117);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (118, 128, 0, 118, 118);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (119, 129, 0, 119, 119);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (120, 130, 0, 120, 120);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (121, 131, 0, 121, 121);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (122, 132, 0, 122, 122);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (123, 133, 0, 123, 123);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (124, 134, 0, 124, 124);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (125, 135, 0, 125, 125);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (126, 136, 0, 126, 126);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (127, 137, 0, 127, 127);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (128, 138, 0, 128, 128);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (129, 139, 0, 129, 129);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (130, 140, 0, 130, 130);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (131, 141, 0, 131, 131);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (132, 142, 0, 132, 132);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (133, 143, 0, 133, 133);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (134, 144, 0, 134, 134);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (135, 145, 0, 135, 135);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (136, 146, 0, 136, 136);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (137, 147, 0, 137, 137);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (138, 148, 0, 138, 138);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (139, 149, 0, 139, 139);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (140, 150, 0, 140, 140);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (141, 151, 0, 141, 141);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (142, 152, 0, 142, 142);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (143, 153, 0, 143, 143);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (144, 154, 0, 144, 144);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (145, 155, 0, 145, 145);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (146, 156, 0, 146, 146);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (147, 157, 0, 147, 147);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (148, 158, 0, 148, 148);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (149, 159, 0, 149, 149);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (150, 160, 0, 150, 150);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (151, 161, 0, 151, 151);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (152, 162, 0, 152, 152);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (153, 163, 0, 153, 153);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (154, 164, 0, 154, 154);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (155, 165, 0, 155, 155);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (156, 166, 0, 156, 156);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (157, 167, 0, 157, 157);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (158, 168, 0, 158, 158);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (159, 169, 0, 159, 159);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (160, 170, 0, 160, 160);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (161, 171, 0, 161, 161);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (162, 172, 0, 162, 162);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (163, 173, 0, 163, 163);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (164, 174, 0, 164, 164);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (165, 175, 0, 165, 165);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (166, 176, 0, 166, 166);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (167, 177, 0, 167, 167);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (168, 178, 0, 168, 168);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (169, 179, 0, 169, 169);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (170, 180, 0, 170, 170);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (171, 181, 0, 171, 171);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (172, 182, 0, 172, 172);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (173, 183, 0, 173, 173);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (174, 184, 0, 174, 174);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (175, 185, 0, 175, 175);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (176, 186, 0, 176, 176);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (177, 187, 0, 177, 177);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (178, 188, 0, 178, 178);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (179, 189, 0, 179, 179);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (180, 190, 0, 180, 180);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (181, 191, 0, 181, 181);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (182, 192, 0, 182, 182);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (183, 193, 0, 183, 183);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (184, 194, 0, 184, 184);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (185, 195, 0, 185, 185);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (186, 196, 0, 186, 186);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (187, 197, 0, 187, 187);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (188, 198, 0, 188, 188);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (189, 199, 0, 189, 189);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (190, 200, 0, 190, 190);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (191, 201, 0, 191, 191);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (192, 202, 0, 192, 192);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (193, 203, 0, 193, 193);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (194, 204, 0, 194, 194);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (195, 205, 0, 195, 195);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (196, 206, 0, 196, 196);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (197, 207, 0, 197, 197);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (198, 208, 0, 198, 198);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (199, 209, 0, 199, 199);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (200, 210, 0, 200, 200);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (201, 211, 0, 201, 201);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (202, 212, 0, 202, 202);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (203, 213, 0, 203, 203);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (204, 214, 0, 204, 204);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (205, 215, 0, 205, 205);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (206, 216, 0, 206, 206);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (207, 217, 0, 207, 207);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (208, 218, 0, 208, 208);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (209, 219, 0, 209, 209);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (210, 220, 0, 210, 210);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (211, 221, 0, 211, 211);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (212, 222, 0, 212, 212);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (213, 223, 0, 213, 213);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (214, 224, 0, 214, 214);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (215, 225, 0, 215, 215);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (216, 226, 0, 216, 216);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (217, 227, 0, 217, 217);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (218, 228, 0, 218, 218);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (219, 229, 0, 219, 219);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (220, 230, 0, 220, 220);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (221, 231, 0, 221, 221);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (222, 232, 0, 222, 222);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (223, 233, 0, 223, 223);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (224, 234, 0, 224, 224);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (225, 235, 0, 225, 225);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (226, 236, 0, 226, 226);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (227, 237, 0, 227, 227);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (228, 238, 0, 228, 228);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (229, 239, 0, 229, 229);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (230, 240, 0, 230, 230);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (231, 241, 0, 231, 231);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (232, 242, 0, 232, 232);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (233, 243, 0, 233, 233);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (234, 244, 0, 234, 234);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (235, 245, 0, 235, 235);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (236, 246, 0, 236, 236);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (237, 247, 0, 237, 237);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (238, 248, 0, 238, 238);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (239, 249, 0, 239, 239);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (240, 250, 0, 240, 240);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (241, 251, 0, 241, 241);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (242, 252, 0, 242, 242);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (243, 253, 0, 243, 243);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (244, 254, 0, 244, 244);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (245, 255, 0, 245, 245);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (246, 256, 0, 246, 246);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (247, 257, 0, 247, 247);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (248, 258, 0, 248, 248);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (249, 259, 0, 249, 249);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (250, 260, 0, 250, 250);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (251, 261, 0, 251, 251);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (252, 262, 0, 252, 252);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (253, 263, 0, 253, 253);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (254, 264, 0, 254, 254);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (255, 265, 0, 255, 255);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (256, 266, 0, 256, 256);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (257, 267, 0, 257, 257);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (258, 268, 0, 258, 258);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (259, 269, 0, 259, 259);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (260, 270, 0, 260, 260);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (261, 271, 0, 261, 261);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (262, 272, 0, 262, 262);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (263, 273, 0, 263, 263);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (264, 274, 0, 264, 264);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (265, 275, 0, 265, 265);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (266, 276, 0, 266, 266);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (267, 277, 0, 267, 267);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (268, 278, 0, 268, 268);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (269, 279, 0, 269, 269);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (270, 280, 0, 270, 270);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (271, 281, 0, 271, 271);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (272, 282, 0, 272, 272);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (273, 283, 0, 273, 273);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (274, 284, 0, 274, 274);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (275, 285, 0, 275, 275);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (276, 286, 0, 276, 276);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (277, 287, 0, 277, 277);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (278, 288, 0, 278, 278);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (279, 289, 0, 279, 279);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (280, 290, 0, 280, 280);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (281, 291, 0, 281, 281);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (282, 292, 0, 282, 282);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (283, 293, 0, 283, 283);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (284, 294, 0, 284, 284);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (285, 295, 0, 285, 285);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (286, 296, 0, 286, 286);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (287, 297, 0, 287, 287);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (288, 298, 0, 288, 288);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (289, 299, 0, 289, 289);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (290, 300, 0, 290, 290);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (291, 301, 0, 291, 291);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (292, 302, 0, 292, 292);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (293, 303, 0, 293, 293);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (294, 304, 0, 294, 294);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (295, 305, 0, 295, 295);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (296, 306, 0, 296, 296);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (297, 307, 0, 297, 297);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (298, 308, 0, 298, 298);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (299, 309, 0, 299, 299);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (300, 310, 0, 300, 300);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (301, 311, 0, 301, 301);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (302, 312, 0, 302, 302);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (303, 313, 0, 303, 303);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (304, 314, 0, 304, 304);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (305, 315, 0, 305, 305);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (306, 316, 0, 306, 306);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (307, 317, 0, 307, 307);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (308, 318, 0, 308, 308);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (309, 319, 0, 309, 309);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (310, 320, 0, 310, 310);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (311, 321, 0, 311, 311);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (312, 322, 0, 312, 312);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (313, 323, 0, 313, 313);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (314, 324, 0, 314, 314);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (315, 325, 0, 315, 315);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (316, 326, 0, 316, 316);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (317, 327, 0, 317, 317);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (318, 328, 0, 318, 318);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (319, 329, 0, 319, 319);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (320, 330, 0, 320, 320);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (321, 331, 0, 321, 321);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (322, 332, 0, 322, 322);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (323, 333, 0, 323, 323);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (324, 334, 0, 324, 324);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (325, 335, 0, 325, 325);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (326, 336, 0, 326, 326);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (327, 337, 0, 327, 327);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (328, 338, 0, 328, 328);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (329, 339, 0, 329, 329);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (330, 340, 0, 330, 330);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (331, 341, 0, 331, 331);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (332, 342, 0, 332, 332);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (333, 343, 0, 333, 333);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (334, 344, 0, 334, 334);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (335, 345, 0, 335, 335);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (336, 346, 0, 336, 336);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (337, 347, 0, 337, 337);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (338, 348, 0, 338, 338);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (339, 349, 0, 339, 339);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (340, 350, 0, 340, 340);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (341, 351, 0, 341, 341);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (342, 352, 0, 342, 342);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (343, 353, 0, 343, 343);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (344, 354, 0, 344, 344);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (345, 355, 0, 345, 345);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (346, 356, 0, 346, 346);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (347, 357, 0, 347, 347);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (348, 358, 0, 348, 348);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (349, 359, 0, 349, 349);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (350, 360, 0, 350, 350);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (351, 361, 0, 351, 351);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (352, 362, 0, 352, 352);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (353, 363, 0, 353, 353);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (354, 364, 0, 354, 354);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (355, 365, 0, 355, 355);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (356, 366, 0, 356, 356);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (357, 367, 0, 357, 357);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (358, 368, 0, 358, 358);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (359, 369, 0, 359, 359);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (360, 370, 0, 360, 360);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (361, 371, 0, 361, 361);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (362, 372, 0, 362, 362);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (363, 373, 0, 363, 363);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (364, 374, 0, 364, 364);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (365, 375, 0, 365, 365);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (366, 376, 0, 366, 366);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (367, 377, 0, 367, 367);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (368, 378, 0, 368, 368);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (369, 379, 0, 369, 369);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (370, 380, 0, 370, 370);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (371, 381, 0, 371, 371);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (372, 382, 0, 372, 372);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (373, 383, 0, 373, 373);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (374, 384, 0, 374, 374);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (375, 385, 0, 375, 375);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (376, 386, 0, 376, 376);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (377, 387, 0, 377, 377);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (378, 388, 0, 378, 378);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (379, 389, 0, 379, 379);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (380, 390, 0, 380, 380);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (381, 391, 0, 381, 381);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (382, 392, 0, 382, 382);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (383, 393, 0, 383, 383);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (384, 394, 0, 384, 384);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (385, 395, 0, 385, 385);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (386, 396, 0, 386, 386);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (387, 397, 0, 387, 387);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (388, 398, 0, 388, 388);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (389, 399, 0, 389, 389);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (390, 400, 0, 390, 390);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (391, 401, 0, 391, 391);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (392, 402, 0, 392, 392);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (393, 403, 0, 393, 393);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (394, 404, 0, 394, 394);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (395, 405, 0, 395, 395);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (396, 406, 0, 396, 396);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (397, 407, 0, 397, 397);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (398, 408, 0, 398, 398);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (399, 409, 0, 399, 399);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (400, 410, 0, 400, 400);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (401, 411, 0, 401, 401);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (402, 412, 0, 402, 402);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (403, 413, 0, 403, 403);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (404, 414, 0, 404, 404);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (405, 415, 0, 405, 405);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (406, 416, 0, 406, 406);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (407, 417, 0, 407, 407);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (408, 418, 0, 408, 408);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (409, 419, 0, 409, 409);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (410, 420, 0, 410, 410);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (411, 421, 0, 411, 411);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (412, 422, 0, 412, 412);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (413, 423, 0, 413, 413);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (414, 424, 0, 414, 414);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (415, 425, 0, 415, 415);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (416, 426, 0, 416, 416);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (417, 427, 0, 417, 417);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (418, 428, 0, 418, 418);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (419, 429, 0, 419, 419);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (420, 430, 0, 420, 420);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (421, 431, 0, 421, 421);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (422, 432, 0, 422, 422);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (423, 433, 0, 423, 423);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (424, 434, 0, 424, 424);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (425, 435, 0, 425, 425);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (426, 436, 0, 426, 426);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (427, 437, 0, 427, 427);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (428, 438, 0, 428, 428);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (429, 439, 0, 429, 429);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (430, 440, 0, 430, 430);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (431, 441, 0, 431, 431);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (432, 442, 0, 432, 432);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (433, 443, 0, 433, 433);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (434, 444, 0, 434, 434);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (435, 445, 0, 435, 435);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (436, 446, 0, 436, 436);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (437, 447, 0, 437, 437);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (438, 448, 0, 438, 438);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (439, 449, 0, 439, 439);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (440, 450, 0, 440, 440);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (441, 451, 0, 441, 441);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (442, 452, 0, 442, 442);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (443, 453, 0, 443, 443);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (444, 454, 0, 444, 444);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (445, 455, 0, 445, 445);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (446, 456, 0, 446, 446);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (447, 457, 0, 447, 447);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (448, 458, 0, 448, 448);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (449, 459, 0, 449, 449);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (450, 460, 0, 450, 450);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (451, 461, 0, 451, 451);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (452, 462, 0, 452, 452);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (453, 463, 0, 453, 453);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (454, 464, 0, 454, 454);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (455, 465, 0, 455, 455);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (456, 466, 0, 456, 456);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (457, 467, 0, 457, 457);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (458, 468, 0, 458, 458);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (459, 469, 0, 459, 459);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (460, 470, 0, 460, 460);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (461, 471, 0, 461, 461);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (462, 472, 0, 462, 462);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (463, 474, 0, 463, 463);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (464, 475, 0, 464, 464);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (465, 476, 0, 465, 465);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (466, 477, 0, 466, 466);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (467, 480, 0, 467, 467);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (468, 484, 0, 468, 468);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (469, 485, 0, 469, 469);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (470, 486, 0, 470, 470);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (471, 487, 0, 471, 471);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (472, 488, 0, 472, 472);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (473, 489, 0, 473, 473);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (474, 491, 0, 474, 474);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (475, 492, 0, 475, 475);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (476, 493, 0, 476, 476);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (477, 494, 0, 477, 477);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (478, 495, 0, 478, 478);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (479, 496, 0, 479, 479);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (480, 497, 0, 480, 480);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (481, 498, 0, 481, 481);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (482, 499, 0, 482, 482);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (483, 500, 0, 483, 483);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (484, 501, 0, 484, 484);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (485, 503, 0, 485, 485);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (486, 504, 0, 486, 486);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (487, 505, 0, 487, 487);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (488, 506, 0, 488, 488);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (489, 507, 0, 489, 489);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (490, 508, 0, 490, 490);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (491, 509, 0, 491, 491);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (492, 510, 0, 492, 492);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (493, 511, 0, 493, 493);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (494, 512, 0, 494, 494);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (495, 513, 0, 495, 495);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (496, 515, 0, 496, 496);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (497, 516, 0, 497, 497);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (498, 517, 0, 498, 498);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (499, 519, 0, 499, 499);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (500, 520, 0, 500, 500);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (501, 521, 0, 501, 501);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (502, 522, 0, 502, 502);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (503, 527, 0, 503, 503);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (504, 528, 0, 504, 504);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (505, 529, 0, 505, 505);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (506, 530, 0, 506, 506);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (507, 531, 0, 507, 507);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (508, 532, 0, 508, 508);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (509, 533, 0, 509, 509);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (510, 534, 0, 510, 510);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (511, 535, 0, 511, 511);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (512, 536, 0, 512, 512);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (513, 537, 0, 513, 513);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (514, 538, 0, 514, 514);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (515, 539, 0, 515, 515);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (516, 540, 0, 516, 516);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (517, 541, 0, 517, 517);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (518, 542, 0, 518, 518);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (519, 543, 0, 519, 519);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (520, 544, 0, 520, 520);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (521, 545, 0, 521, 521);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (522, 546, 0, 522, 522);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (523, 547, 0, 523, 523);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (524, 548, 0, 524, 524);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (525, 549, 0, 525, 525);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (526, 550, 0, 526, 526);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (527, 551, 0, 527, 527);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (528, 552, 0, 528, 528);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (529, 553, 0, 529, 529);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (530, 555, 0, 530, 530);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (531, 556, 0, 531, 531);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (532, 557, 0, 532, 532);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (533, 558, 0, 533, 533);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (534, 559, 0, 534, 534);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (535, 560, 0, 535, 535);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (536, 561, 0, 536, 536);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (537, 562, 0, 537, 537);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (538, 563, 0, 538, 538);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (539, 564, 0, 539, 539);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (540, 565, 0, 540, 540);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (541, 566, 0, 541, 541);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (542, 567, 0, 542, 542);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (543, 568, 0, 543, 543);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (544, 569, 0, 544, 544);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (545, 570, 0, 545, 545);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (546, 571, 0, 546, 546);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (547, 572, 0, 547, 547);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (548, 573, 0, 548, 548);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (549, 574, 0, 549, 549);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (550, 575, 0, 550, 550);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (551, 576, 0, 551, 551);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (552, 577, 0, 552, 552);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (553, 578, 0, 553, 553);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (554, 579, 0, 554, 554);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (555, 580, 0, 555, 555);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (556, 581, 0, 556, 556);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (557, 582, 0, 557, 557);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (558, 583, 0, 558, 558);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (559, 584, 0, 559, 559);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (560, 585, 0, 560, 560);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (561, 586, 0, 561, 561);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (562, 587, 0, 562, 562);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (563, 588, 0, 563, 563);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (564, 589, 0, 564, 564);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (565, 590, 0, 565, 565);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (566, 591, 0, 566, 566);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (567, 592, 0, 567, 567);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (568, 594, 0, 685, 568);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (569, 603, 0, 569, 569);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (570, 604, 0, 570, 570);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (571, 604, 1, 571, 571);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (572, 605, 0, 572, 572);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (573, 605, 1, 573, 573);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (574, 606, 0, 574, 574);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (575, 607, 0, 575, 575);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (576, 611, 0, 576, 576);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (577, 612, 0, 577, 577);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (578, 613, 0, 578, 578);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (579, 614, 0, 579, 579);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (580, 615, 0, 580, 580);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (581, 616, 0, 581, 581);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (582, 617, 0, 582, 582);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (583, 618, 0, 583, 583);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (584, 619, 0, 584, 584);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (585, 620, 0, 585, 585);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (586, 621, 0, 586, 586);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (587, 622, 0, 587, 587);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (588, 623, 0, 588, 588);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (589, 624, 0, 589, 589);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (590, 625, 0, 590, 590);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (591, 626, 0, 591, 591);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (592, 627, 0, 592, 592);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (593, 628, 0, 593, 593);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (594, 629, 0, 594, 594);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (595, 630, 0, 595, 595);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (596, 631, 0, 596, 596);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (597, 632, 0, 597, 597);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (598, 633, 0, 598, 598);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (599, 634, 0, 599, 599);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (600, 635, 0, 600, 600);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (601, 636, 0, 601, 601);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (602, 637, 0, 602, 602);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (603, 638, 0, 603, 603);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (604, 639, 0, 604, 604);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (605, 640, 0, 605, 605);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (606, 641, 0, 606, 606);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (607, 642, 0, 607, 607);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (608, 643, 0, 608, 608);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (609, 644, 0, 609, 609);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (610, 648, 0, 610, 610);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (611, 649, 0, 611, 611);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (612, 650, 0, 612, 612);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (613, 651, 0, 613, 613);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (614, 652, 0, 614, 614);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (615, 653, 0, 615, 615);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (616, 654, 0, 616, 616);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (617, 655, 0, 617, 617);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (618, 656, 0, 618, 618);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (619, 657, 0, 619, 619);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (620, 658, 0, 620, 620);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (621, 659, 0, 621, 621);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (622, 660, 0, 622, 622);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (623, 661, 0, 623, 623);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (624, 662, 0, 624, 624);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (625, 663, 0, 625, 625);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (626, 664, 0, 626, 626);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (627, 665, 0, 627, 627);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (628, 666, 0, 628, 628);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (629, 667, 0, 629, 629);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (630, 668, 0, 630, 630);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (631, 669, 0, 631, 631);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (632, 670, 0, 632, 632);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (633, 671, 0, 633, 633);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (634, 672, 0, 634, 634);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (635, 673, 0, 635, 635);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (636, 674, 0, 636, 636);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (637, 675, 0, 637, 637);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (638, 676, 0, 638, 638);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (639, 677, 0, 639, 639);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (640, 678, 0, 640, 640);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (641, 679, 0, 641, 641);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (642, 680, 0, 642, 642);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (643, 681, 0, 643, 643);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (644, 682, 0, 644, 644);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (645, 683, 0, 645, 645);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (646, 684, 0, 646, 646);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (647, 685, 0, 647, 647);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (648, 686, 0, 648, 648);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (649, 687, 0, 649, 649);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (650, 688, 0, 650, 650);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (651, 689, 0, 651, 651);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (652, 696, 0, 652, 652);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (653, 697, 0, 653, 653);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (654, 698, 0, 654, 654);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (655, 699, 0, 655, 655);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (656, 700, 0, 656, 656);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (657, 701, 0, 657, 657);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (658, 702, 0, 658, 658);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (659, 703, 0, 659, 659);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (660, 704, 0, 660, 660);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (661, 705, 0, 661, 661);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (662, 706, 0, 662, 662);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (663, 707, 0, 663, 663);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (664, 708, 0, 664, 664);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (665, 709, 0, 665, 665);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (666, 710, 0, 666, 666);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (667, 711, 0, 667, 667);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (668, 712, 0, 668, 668);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (669, 713, 0, 669, 669);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (670, 714, 0, 670, 670);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (671, 715, 0, 671, 671);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (672, 716, 0, 672, 672);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (673, 717, 0, 673, 673);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (674, 718, 0, 674, 674);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (675, 719, 0, 675, 675);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (676, 723, 0, 676, 676);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (677, 724, 0, 677, 677);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (678, 725, 0, 678, 678);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (679, 726, 0, 679, 679);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (680, 727, 0, 680, 680);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (681, 728, 0, 681, 681);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (682, 729, 0, 682, 682);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (683, 730, 0, 683, 683);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (684, 731, 0, 684, 684);
INSERT INTO poselection (id, pomsgset, pluralform, activesubmission, publishedsubmission) VALUES (685, 599, 0, 686, NULL);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'poselection'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'poexportrequest'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'poexportrequest'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'karmaaction'::pg_catalog.regclass;

INSERT INTO karmaaction (id, name, category, points) VALUES (1, 1, 2, 10);
INSERT INTO karmaaction (id, name, category, points) VALUES (2, 2, 2, 1);
INSERT INTO karmaaction (id, name, category, points) VALUES (3, 3, 2, 1);
INSERT INTO karmaaction (id, name, category, points) VALUES (4, 4, 2, 2);
INSERT INTO karmaaction (id, name, category, points) VALUES (5, 5, 2, 3);
INSERT INTO karmaaction (id, name, category, points) VALUES (6, 6, 2, 10);
INSERT INTO karmaaction (id, name, category, points) VALUES (7, 7, 2, 15);
INSERT INTO karmaaction (id, name, category, points) VALUES (8, 8, 2, 10);
INSERT INTO karmaaction (id, name, category, points) VALUES (9, 9, 2, 10);
INSERT INTO karmaaction (id, name, category, points) VALUES (10, 10, 3, 10);
INSERT INTO karmaaction (id, name, category, points) VALUES (11, 11, 3, 30);
INSERT INTO karmaaction (id, name, category, points) VALUES (12, 12, 3, 5);
INSERT INTO karmaaction (id, name, category, points) VALUES (13, 13, 3, 1);
INSERT INTO karmaaction (id, name, category, points) VALUES (14, 14, 3, 1);
INSERT INTO karmaaction (id, name, category, points) VALUES (15, 15, 3, 1);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'karmaaction'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'karmacache'::pg_catalog.regclass;

INSERT INTO karmacache (id, person, category, karmavalue) VALUES (1, 1, 2, 33);
INSERT INTO karmacache (id, person, category, karmavalue) VALUES (2, 1, 3, 33);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'karmacache'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'calendar'::pg_catalog.regclass;

INSERT INTO calendar (id, title, revision) VALUES (1, 'Sample Person''s Calendar', 0);
INSERT INTO calendar (id, title, revision) VALUES (2, 'Foo Bar''s Calendar', 0);
INSERT INTO calendar (id, title, revision) VALUES (3, 'Ubuntu Project Calendar', 0);


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'calendar'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'calendarsubscription'::pg_catalog.regclass;

INSERT INTO calendarsubscription (id, subject, object, colour) VALUES (1, 1, 1, '#c0d0ff');
INSERT INTO calendarsubscription (id, subject, object, colour) VALUES (2, 1, 2, '#c0ffc8');
INSERT INTO calendarsubscription (id, subject, object, colour) VALUES (3, 1, 3, '#faffd2');
INSERT INTO calendarsubscription (id, subject, object, colour) VALUES (4, 2, 2, '#c0ffc8');
INSERT INTO calendarsubscription (id, subject, object, colour) VALUES (5, 2, 1, '#c0d0ff');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'calendarsubscription'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'calendarevent'::pg_catalog.regclass;

INSERT INTO calendarevent (id, uid, calendar, dtstart, duration, title, description, "location") VALUES (1, 'sample-id-1@launchpad.example.org', 1, '2005-01-03 08:00:00', '01:00:00', 'Event 1', 'Desc 1', 'Location');
INSERT INTO calendarevent (id, uid, calendar, dtstart, duration, title, description, "location") VALUES (2, 'sample-id-2@launchpad.example.org', 1, '2005-01-03 10:00:00', '01:00:00', 'Event 2', 'Desc 2', 'Location');
INSERT INTO calendarevent (id, uid, calendar, dtstart, duration, title, description, "location") VALUES (3, 'sample-id-3@launchpad.example.org', 1, '2005-01-04 08:00:00', '01:00:00', 'Event 1', 'Desc 1', 'Location');
INSERT INTO calendarevent (id, uid, calendar, dtstart, duration, title, description, "location") VALUES (4, 'sample-id-4@launchpad.example.org', 2, '2005-01-04 08:00:00', '01:00:00', 'Foo Bar 1', 'Desc 1', 'Location');
INSERT INTO calendarevent (id, uid, calendar, dtstart, duration, title, description, "location") VALUES (5, 'sample-id-5@launchpad.example.org', 3, '2004-12-06 08:00:00', '11 days 08:30:00', 'The Mataro Sessions', 'The Ubuntu conference in Mataro', 'Mataro, Spain');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'calendarevent'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'distroreleaselanguage'::pg_catalog.regclass;

INSERT INTO distroreleaselanguage (id, distrorelease, "language", currentcount, updatescount, rosettacount, contributorcount, dateupdated) VALUES (1, 3, 68, 62, 0, 0, 1, '2005-07-22 22:51:42.32511');
INSERT INTO distroreleaselanguage (id, distrorelease, "language", currentcount, updatescount, rosettacount, contributorcount, dateupdated) VALUES (2, 3, 196, 9, 0, 0, 1, '2005-07-22 22:51:42.32511');
INSERT INTO distroreleaselanguage (id, distrorelease, "language", currentcount, updatescount, rosettacount, contributorcount, dateupdated) VALUES (3, 3, 360, 63, 0, 0, 1, '2005-07-22 22:51:42.32511');
INSERT INTO distroreleaselanguage (id, distrorelease, "language", currentcount, updatescount, rosettacount, contributorcount, dateupdated) VALUES (4, 3, 193, 9, 0, 0, 1, '2005-07-22 22:51:42.32511');
INSERT INTO distroreleaselanguage (id, distrorelease, "language", currentcount, updatescount, rosettacount, contributorcount, dateupdated) VALUES (5, 3, 98, 65, 0, 0, 2, '2005-07-22 22:51:42.32511');
INSERT INTO distroreleaselanguage (id, distrorelease, "language", currentcount, updatescount, rosettacount, contributorcount, dateupdated) VALUES (6, 3, 241, 9, 0, 0, 1, '2005-07-22 22:51:42.32511');
INSERT INTO distroreleaselanguage (id, distrorelease, "language", currentcount, updatescount, rosettacount, contributorcount, dateupdated) VALUES (7, 3, 112, 9, 0, 0, 1, '2005-07-22 22:51:42.32511');
INSERT INTO distroreleaselanguage (id, distrorelease, "language", currentcount, updatescount, rosettacount, contributorcount, dateupdated) VALUES (8, 3, 143, 72, 0, 0, 2, '2005-07-22 22:51:42.32511');
INSERT INTO distroreleaselanguage (id, distrorelease, "language", currentcount, updatescount, rosettacount, contributorcount, dateupdated) VALUES (9, 3, 527, 49, 0, 0, 1, '2005-07-22 22:51:42.32511');
INSERT INTO distroreleaselanguage (id, distrorelease, "language", currentcount, updatescount, rosettacount, contributorcount, dateupdated) VALUES (10, 3, 454, 0, 0, 0, 0, '2005-07-22 22:51:42.32511');
INSERT INTO distroreleaselanguage (id, distrorelease, "language", currentcount, updatescount, rosettacount, contributorcount, dateupdated) VALUES (11, 3, 148, 3, 0, 0, 1, '2005-07-22 22:51:42.32511');
INSERT INTO distroreleaselanguage (id, distrorelease, "language", currentcount, updatescount, rosettacount, contributorcount, dateupdated) VALUES (12, 3, 302, 63, 0, 0, 1, '2005-07-22 22:51:42.32511');
INSERT INTO distroreleaselanguage (id, distrorelease, "language", currentcount, updatescount, rosettacount, contributorcount, dateupdated) VALUES (13, 3, 387, 67, 1, 1, 5, '2005-07-22 22:51:42.32511');
INSERT INTO distroreleaselanguage (id, distrorelease, "language", currentcount, updatescount, rosettacount, contributorcount, dateupdated) VALUES (14, 3, 427, 6, 0, 0, 1, '2005-07-22 22:51:42.32511');
INSERT INTO distroreleaselanguage (id, distrorelease, "language", currentcount, updatescount, rosettacount, contributorcount, dateupdated) VALUES (15, 3, 129, 9, 0, 0, 1, '2005-07-22 22:51:42.32511');
INSERT INTO distroreleaselanguage (id, distrorelease, "language", currentcount, updatescount, rosettacount, contributorcount, dateupdated) VALUES (16, 3, 502, 63, 0, 0, 1, '2005-07-22 22:51:42.32511');
INSERT INTO distroreleaselanguage (id, distrorelease, "language", currentcount, updatescount, rosettacount, contributorcount, dateupdated) VALUES (17, 3, 132, 66, 0, 0, 2, '2005-07-22 22:51:42.32511');
INSERT INTO distroreleaselanguage (id, distrorelease, "language", currentcount, updatescount, rosettacount, contributorcount, dateupdated) VALUES (18, 3, 521, 9, 0, 0, 1, '2005-07-22 22:51:42.32511');
INSERT INTO distroreleaselanguage (id, distrorelease, "language", currentcount, updatescount, rosettacount, contributorcount, dateupdated) VALUES (19, 3, 100, 9, 0, 0, 1, '2005-07-22 22:51:42.32511');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'distroreleaselanguage'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'poll'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'poll'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'polloption'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'polloption'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'votecast'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'votecast'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'vote'::pg_catalog.regclass;



UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'vote'::pg_catalog.regclass;


UPDATE pg_catalog.pg_class SET reltriggers = 0 WHERE oid = 'launchpadstatistic'::pg_catalog.regclass;

INSERT INTO launchpadstatistic (id, name, value, dateupdated) VALUES (1, 'potemplate_count', 5, '2005-07-22 22:51:42.32511');
INSERT INTO launchpadstatistic (id, name, value, dateupdated) VALUES (2, 'pofile_count', 25, '2005-07-22 22:51:42.32511');
INSERT INTO launchpadstatistic (id, name, value, dateupdated) VALUES (3, 'pomsgid_count', 145, '2005-07-22 22:51:42.32511');
INSERT INTO launchpadstatistic (id, name, value, dateupdated) VALUES (4, 'translator_count', 23, '2005-07-22 22:51:42.32511');
INSERT INTO launchpadstatistic (id, name, value, dateupdated) VALUES (5, 'language_count', 19, '2005-07-22 22:51:42.32511');


UPDATE pg_catalog.pg_class SET reltriggers = (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger where pg_class.oid = tgrelid) WHERE oid = 'launchpadstatistic'::pg_catalog.regclass;




































































































































































































































































































































































































