/* Create the admins team */

INSERT INTO Person (name, teamowner, teamdescription) VALUES (
    'admins', (SELECT id FROM Person WHERE name='sabdfl'),
    'Launchpad Administrators'
    );

INSERT INTO TeamParticipation (team, person) VALUES (
    (SELECT id FROM Person WHERE name='admins'),
    (SELECT id FROM Person WHERE name='stub')
    );

INSERT INTO TeamParticipation (team, person) VALUES (
    (SELECT id FROM Person WHERE name='admins'),
    (SELECT id FROM Person WHERE name='lifeless')
    );

INSERT INTO TeamParticipation (team, person) VALUES (
    (SELECT id FROM Person WHERE name='admins'),
    (SELECT id FROM Person WHERE name='stevea')
    );

INSERT INTO TeamParticipation (team, person) VALUES (
    (SELECT id FROM Person WHERE name='admins'),
    (SELECT id FROM Person WHERE name='ddaa')
    );

INSERT INTO TeamParticipation (team, person) VALUES (
    (SELECT id FROM Person WHERE name='admins'),
    (SELECT id FROM Person WHERE name='kinnison')
    );

INSERT INTO TeamParticipation (team, person) VALUES (
    (SELECT id FROM Person WHERE name='admins'),
    (SELECT id FROM Person WHERE name='spiv')
    );

INSERT INTO TeamParticipation (team, person) VALUES (
    (SELECT id FROM Person WHERE name='admins'),
    (SELECT id FROM Person WHERE name='jblack')
    );

INSERT INTO TeamParticipation (team, person) VALUES (
    (SELECT id FROM Person WHERE name='admins'),
    (SELECT id FROM Person WHERE name='daf')
    );

INSERT INTO TeamParticipation (team, person) VALUES (
    (SELECT id FROM Person WHERE name='admins'),
    (SELECT id FROM Person WHERE name='carlos')
    );

