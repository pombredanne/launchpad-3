-- Copyright 2011 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).
SET client_min_messages=ERROR;

CREATE TABLE PillarObserverPolicy (
    id serial PRIMARY KEY,
    product integer REFERENCES Product,
    distribution integer REFERENCES Distribution,
    display_name text NOT NULL,
    CONSTRAINT pillarobserverpolicy__product__display_name__key
        UNIQUE (product, display_name),
    CONSTRAINT pillarobserverpolicy__distribution__display_name__key
        UNIQUE (distribution, display_name),
    CONSTRAINT has_target CHECK (product IS NULL != distribution IS NULL)
);

CREATE TABLE PillarObserverArtifact (
    id serial PRIMARY KEY,
    bug integer REFERENCES Bug,
    branch integer REFERENCES Branch,
    CONSTRAINT pillarobserverartifact__bug__key UNIQUE (bug),
    CONSTRAINT pillarobserverartifact__branch__key UNIQUE (branch),
    CONSTRAINT has_artifact CHECK (bug IS NULL != branch IS NULL)
);

CREATE TABLE PillarObserverPermission (
    id serial PRIMARY KEY,
    policy integer NOT NULL REFERENCES PillarObserverPolicy,
    person integer NOT NULL REFERENCES Person,
    artifact integer REFERENCES PillarObserverArtifact,
    CONSTRAINT pillarobserverpermission__policy__person__artifact__key
        UNIQUE (policy, person, artifact)
);

CREATE UNIQUE INDEX pillarobserverpermission__policy__person__key
    ON PillarObserverPermission(policy, person) WHERE artifact IS NULL;

ALTER TABLE bug
    ADD COLUMN observer_policy integer REFERENCES PillarObserverPolicy;
CREATE INDEX bug__observer_policy__idx ON bug(observer_policy);

ALTER TABLE branch
    ADD COLUMN observer_policy integer REFERENCES PillarObserverPolicy;
CREATE INDEX branch__observer_policy__idx ON branch(observer_policy);

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 99, 0);
