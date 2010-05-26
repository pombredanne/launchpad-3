-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE TABLE AffiliationDescription (
    id serial PRIMARY KEY,
    pillar_name integer NOT NULL REFERENCES PillarName,
    sort_order integer NOT NULL DEFAULT 0,
    description TEXT NOT NULL,
    date_created timestamp WITHOUT TIME ZONE
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),

    -- UNIQUE constraint for Affiliation -> Description foreign key
    CONSTRAINT affiliationdescription__pillar_name__id__key
        UNIQUE (pillar_name, id)
    );

CREATE TABLE PersonAffiliation (
    id serial PRIMARY KEY,
    person integer NOT NULL REFERENCES Person,
    pillar_name integer NOT NULL,
    description integer NOT NULL,
    date_created timestamp WITHOUT TIME ZONE
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    status integer NOT NULL,
    date_status_set timestamp WITHOUT TIME ZONE
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    registrant integer NOT NULL References Person,

    CONSTRAINT personaffiliation__pillar_name__description__fk
        FOREIGN KEY(pillar_name, description)
        REFERENCES AffiliationDescription(pillar_name, id)
    );

-- Trigger to maintain date_status_set
CREATE TRIGGER set_date_set_t BEFORE UPDATE ON PersonAffiliation
FOR EACH ROW EXECUTE PROCEDURE set_date_status_set();

-- Indexes required for person merge and looking up affiliations for a person
CREATE INDEX personaffiliation__person__idx ON PersonAffiliation(person);
CREATE INDEX personaffiliation__registrant__idx
    ON PersonAffiliation(registrant);

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 27, 0);

