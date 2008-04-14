SET client_min_messages=ERROR;


ALTER TABLE Product
  ADD COLUMN bug_supervisor integer REFERENCES person(id),
  DROP CONSTRAINT private_bugs_need_contact;

CREATE INDEX product_bug_supervisor_idx
  ON Product USING btree (bug_supervisor);

UPDATE Product
  SET bug_supervisor = bugcontact;

ALTER TABLE Product
  DROP COLUMN bugcontact,
  ADD CONSTRAINT private_bugs_need_contact CHECK (
    ((private_bugs IS FALSE) OR (bug_supervisor IS NOT NULL)));


ALTER TABLE Distribution
  ADD COLUMN bug_supervisor integer REFERENCES person(id);

CREATE INDEX distribution_bug_supervisor_idx
  ON Distribution USING btree (bug_supervisor);

UPDATE Distribution
  SET bug_supervisor = bugcontact;

ALTER TABLE Distribution
  DROP COLUMN bugcontact;


DROP TABLE PackageBugContact;

CREATE TABLE PackageBugSupervisor (
    id serial PRIMARY KEY,
    distribution integer NOT NULL,
    sourcepackagename integer NOT NULL,
    bug_supervisor integer NOT NULL,
    date_created timestamp without time zone
      DEFAULT timezone('UTC'::text, now()) NOT NULL,
    CONSTRAINT packagebugsupervisor_one_bug_supervisor UNIQUE (
      sourcepackagename, distribution)
);


INSERT INTO LaunchpadDatabaseRevision VALUES (121, 99, 0);
