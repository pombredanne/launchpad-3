SET client_min_messages TO error;

/* Mark's Bounty table */

CREATE TABLE Bounty (
    id serial PRIMARY KEY,
    name text NOT NULL UNIQUE,
    title text NOT NULL,
    summary text NOT NULL,
    description text NOT NULL,
    usdvalue decimal (10,2) NOT NULL,
    difficulty integer NOT NULL,
    duration interval NOT NULL,
    reviewer integer NOT NULL REFERENCES Person,
    datecreated timestamp without time zone
        DEFAULT (current_timestamp AT TIME ZONE 'UTC'),
    owner integer NOT NULL REFERENCES Person,
    deadline timestamp without time zone,
    claimant integer REFERENCES Person,
    dateclaimed timestamp without time zone
    );

ALTER TABLE person ADD column language int;
ALTER TABLE person ADD CONSTRAINT person_language_fk
    FOREIGN KEY(language) REFERENCES Language(id);

UPDATE LaunchpadDatabaseRevision SET major=4, minor=5, patch=0;

