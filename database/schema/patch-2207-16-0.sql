SET client_min_messages=ERROR;

CREATE TABLE lp_TeamParticipation AS SELECT * FROM TeamParticipation;
ALTER TABLE lp_TeamParticipation
    ADD CONSTRAINT lp_TeamParticipation_pkey PRIMARY KEY (id),
    ADD CONSTRAINT lp_TeamPerticipation__team__person__key
        UNIQUE (team, person);
CREATE INDEX lp_TeamParticipation__person__idx ON lp_TeamParticipation(person);


CREATE TABLE lp_PersonLocation AS SELECT * FROM PersonLocation;
ALTER TABLE lp_PersonLocation
    ADD CONSTRAINT lp_PersonLocation_pkey PRIMARY KEY (id),
    ADD CONSTRAINT lp_PersonLocation__person__key UNIQUE (person);


CREATE TABLE lp_Person AS SELECT * FROM Person;
ALTER TABLE lp_Person
    ADD CONSTRAINT lp_Person_pkey PRIMARY KEY (id),
    ADD CONSTRAINT lp_Person__name__key UNIQUE (name),
    ADD CONSTRAINT lp_Person__account__key UNIQUE (account);


-- Insert triggers
CREATE TRIGGER lp_mirror_teamparticipation_ins_t
AFTER INSERT ON TeamParticipation
FOR EACH ROW EXECUTE PROCEDURE lp_mirror_teamparticipation_ins();

CREATE TRIGGER lp_mirror_personlocation_ins_t
AFTER INSERT ON PersonLocation
FOR EACH ROW EXECUTE PROCEDURE lp_mirror_personlocation_ins();

CREATE TRIGGER lp_mirror_person_ins_t
AFTER INSERT ON Person
FOR EACH ROW EXECUTE PROCEDURE lp_mirror_person_ins();


-- UPDATE triggers
CREATE TRIGGER lp_mirror_teamparticipation_upd_t
AFTER UPDATE ON TeamParticipation
FOR EACH ROW EXECUTE PROCEDURE lp_mirror_teamparticipation_upd();

CREATE TRIGGER lp_mirror_personlocation_upd_t
AFTER UPDATE ON PersonLocation
FOR EACH ROW EXECUTE PROCEDURE lp_mirror_personlocation_upd();

CREATE TRIGGER lp_mirror_person_upd_t
AFTER UPDATE ON Person
FOR EACH ROW EXECUTE PROCEDURE lp_mirror_person_upd();

-- Delete triggers
CREATE TRIGGER lp_mirror_teamparticipation_del_t
AFTER DELETE ON TeamParticipation
FOR EACH ROW EXECUTE PROCEDURE lp_mirror_del();

CREATE TRIGGER lp_mirror_personlocation_del_t
AFTER DELETE ON TeamParticipation
FOR EACH ROW EXECUTE PROCEDURE lp_mirror_del();

CREATE TRIGGER lp_mirror_person_del_t
AFTER DELETE ON Person
FOR EACH ROW EXECUTE PROCEDURE lp_mirror_del();

INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 16, 0);

