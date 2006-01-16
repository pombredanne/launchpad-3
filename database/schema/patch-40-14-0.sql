SET client_min_messages=ERROR;

DROP TABLE Maintainership;

-- Redundant, given posubmission_can_be_selected
DROP INDEX posubmission_pomsgset_and_pluralform_idx;

-- Convert indexes to partial
DROP INDEX person_emblem_idx;
CREATE INDEX person_emblem_idx ON Person(emblem)
    WHERE emblem IS NOT NULL;

DROP INDEX person_hackergotchi_idx;
CREATE INDEX person_hackergotchi_idx ON Person(hackergotchi)
    WHERE hackergotchi IS NOT NULL;

DROP INDEX message_raw_idx;
CREATE INDEX message_raw_idx ON Message(raw) WHERE raw IS NOT NULL;

DROP INDEX messagechunk_blob_idx;
CREATE INDEX messagechunk_blob_idx ON MessageChunk(blob) WHERE blob IS NOT NULL;

DROP INDEX build_buildlog_idx;
CREATE INDEX build_buildlog_idx ON Build(buildlog) WHERE buildlog IS NOT NULL;

-- Foreign key updates
ALTER TABLE Person ADD CONSTRAINT person_teamowner_fk
    FOREIGN KEY (teamowner) REFERENCES Person;
ALTER TABLE Person DROP CONSTRAINT "$1";

ALTER TABLE Person ADD CONSTRAINT person_country_fk
    FOREIGN KEY (country) REFERENCES Country;
ALTER TABLE Person DROP CONSTRAINT "$2";

ALTER TABLE Language ADD CONSTRAINT valid_language
    CHECK (pluralforms IS NULL = pluralexpression IS NULL);
ALTER TABLE Language DROP CONSTRAINT "$1";

ALTER TABLE ManifestEntry ADD CONSTRAINT positive_sequence
    CHECK ("sequence" > 0);
ALTER TABLE ManifestEntry DROP CONSTRAINT "$1";

ALTER TABLE EmailAddress ADD CONSTRAINT emailaddress_person_fk
    FOREIGN KEY (person) REFERENCES Person;
ALTER TABLE EmailAddress DROP CONSTRAINT "$1";

ALTER TABLE WikiName ADD CONSTRAINT wikiname_person_fk
    FOREIGN KEY (person) REFERENCES Person;
ALTER TABLE WikiName DROP CONSTRAINT "$1";

ALTER TABLE JabberId ADD CONSTRAINT jabberid_person_fk
    FOREIGN KEY (person) REFERENCES Person;
ALTER TABLE JabberId DROP CONSTRAINT "$1";

ALTER TABLE IrcId ADD CONSTRAINT ircid_person_fk
    FOREIGN KEY (person) REFERENCES Person;
ALTER TABLE IrcId DROP CONSTRAINT "$1";

ALTER TABLE TeamMembership ADD CONSTRAINT teammembership_person_fk
    FOREIGN KEY (person) REFERENCES Person;
ALTER TABLE TeamMembership DROP CONSTRAINT "$1";

ALTER TABLE TeamMembership ADD CONSTRAINT teammembership_team_fk
    FOREIGN KEY (team) REFERENCES Person;
ALTER TABLE TeamMembership DROP CONSTRAINT "$2";

ALTER TABLE TeamParticipation ADD CONSTRAINT teamparticipation_team_fk
    FOREIGN KEY (team) REFERENCES Person;
ALTER TABLE TeamParticipation DROP CONSTRAINT "$1";

ALTER TABLE TeamParticipation ADD CONSTRAINT teamparticipation_person_fk
    FOREIGN KEY (person) REFERENCES Person;
ALTER TABLE TeamParticipation DROP CONSTRAINT "$2";

ALTER TABLE Schema ADD CONSTRAINT schema_owner_fk
    FOREIGN KEY (owner) REFERENCES Person;
ALTER TABLE Schema DROP CONSTRAINT "$1";

ALTER TABLE Label ADD CONSTRAINT label_schema_fk
    FOREIGN KEY (schema) REFERENCES "schema";
ALTER TABLE Label DROP CONSTRAINT "$1";

ALTER TABLE PersonLabel ADD CONSTRAINT personlabel_person_fk
    FOREIGN KEY (person) REFERENCES Person;
ALTER TABLE PersonLabel DROP CONSTRAINT "$1";

ALTER TABLE PersonLabel ADD CONSTRAINT personlabel_label_fk
    FOREIGN KEY (label) REFERENCES Label;
ALTER TABLE PersonLabel DROP CONSTRAINT "$2";

ALTER TABLE ProjectRelationship ADD CONSTRAINT projectrelationship_subject_fk
    FOREIGN KEY (subject) REFERENCES Project;
ALTER TABLE ProjectRelationship DROP CONSTRAINT "$1";

ALTER TABLE ProjectRelationship ADD CONSTRAINT projectrelationship_object_fk
    FOREIGN KEY (object) REFERENCES Project;
ALTER TABLE ProjectRelationship DROP CONSTRAINT "$2";

ALTER TABLE ProductLabel ADD CONSTRAINT productlabel_product_fk
    FOREIGN KEY (product) REFERENCES Product;
ALTER TABLE ProductLabel DROP CONSTRAINT "$1";

ALTER TABLE ProductLabel ADD CONSTRAINT productlabel_label_fk
    FOREIGN KEY (label) REFERENCES Label;
ALTER TABLE ProductLabel DROP CONSTRAINT "$2";

ALTER TABLE ProductRelease ADD CONSTRAINT productrelease_owner_fk
    FOREIGN KEY (owner) REFERENCES Person;
ALTER TABLE ProductRelease DROP CONSTRAINT "$2";

ALTER TABLE ProductCvsModule ADD CONSTRAINT productcvsmodule_product_fk
    FOREIGN KEY (product) REFERENCES Product;
ALTER TABLE ProductCvsModule DROP CONSTRAINT "$1";

ALTER TABLE ProductSvnModule ADD CONSTRAINT productsvnmodule_product_fk
    FOREIGN KEY (product) REFERENCES Product;
ALTER TABLE ProductSvnModule DROP CONSTRAINT "$1";


INSERT INTO LaunchpadDatabaseRevision VALUES (40, 14, 0);

