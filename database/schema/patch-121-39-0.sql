SET client_min_messages=ERROR;

ALTER TABLE Product RENAME COLUMN bugcontact TO bug_supervisor;

DROP INDEX product__bugcontact__idx;
CREATE INDEX product__bug_supervisor__idx ON Product(bug_supervisor)
    WHERE bug_supervisor IS NOT NULL;


ALTER TABLE Distribution RENAME COLUMN bugcontact TO bug_supervisor;

DROP INDEX distribution_bugcontact_idx;
CREATE INDEX distribution__bug_supervisor__idx
    ON Distribution(bug_supervisor) WHERE bug_supervisor IS NOT NULL;


DROP TABLE PackageBugContact; -- Empty - no need for data migration

CREATE TABLE PackageBugSupervisor (
    id serial PRIMARY KEY,
    distribution integer NOT NULL,
    sourcepackagename integer NOT NULL,
    bug_supervisor integer NOT NULL,
    date_created timestamp without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    CONSTRAINT packagebugsupervisor__sourcepackagename__distribution__key
        UNIQUE (sourcepackagename, distribution)
);

CREATE INDEX packagebugsupervisor__bug_supervisor__idx
    ON PackageBugSupervisor(bug_supervisor);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 39, 0);
