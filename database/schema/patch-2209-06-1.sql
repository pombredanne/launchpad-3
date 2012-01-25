-- Copyright 2012 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE TABLE specificationworkitem (
    id SERIAL PRIMARY KEY,
    title text NOT NULL,
    specification integer NOT NULL REFERENCES specification,
    assignee integer REFERENCES person,
    milestone integer REFERENCES milestone,
    date_created timestamp without time zone DEFAULT 
        timezone('UTC'::text, now()) NOT NULL,
    status integer NOT NULL,
    deleted boolean NOT NULL DEFAULT FALSE);

CREATE TABLE specificationworkitemchange (
    id SERIAL PRIMARY KEY,
    work_item integer NOT NULL REFERENCES specificationworkitem,
    new_status integer NOT NULL,
    new_milestone integer REFERENCES milestone,
    new_assignee integer REFERENCES person,
    time timestamp NOT NULL);

CREATE TABLE specificationworkitemstats (
    id SERIAL PRIMARY KEY,
    specification integer REFERENCES specification,
    time timestamp NOT NULL,
    status integer NOT NULL,
    assignee integer REFERENCES person,
    milestone integer REFERENCES milestone,
    count integer NOT NULL);

-- TODO: Add security.cfg entries for the new tables
-- TODO: Add comments.sql entries for the new tables

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 13, 0);
