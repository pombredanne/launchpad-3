-- Copyright 2011 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).
SET client_min_messages=ERROR;

CREATE TABLE AccessPolicy (
    id serial PRIMARY KEY,
    product integer REFERENCES Product,
    distribution integer REFERENCES Distribution,
    display_name text NOT NULL,
    CONSTRAINT accesspolicy__product__display_name__key
        UNIQUE (product, display_name),
    CONSTRAINT accesspolicy__distribution__display_name__key
        UNIQUE (distribution, display_name),
    CONSTRAINT has_target CHECK (product IS NULL != distribution IS NULL)
);

CREATE TABLE AccessPolicyArtifact (
    id serial PRIMARY KEY,
    bug integer REFERENCES Bug,
    branch integer REFERENCES Branch,
    CONSTRAINT accesspolicyartifact__bug__key UNIQUE (bug),
    CONSTRAINT accesspolicyartifact__branch__key UNIQUE (branch),
    CONSTRAINT has_artifact CHECK (bug IS NULL != branch IS NULL)
);

CREATE TABLE AccessPolicyPermission (
    id serial PRIMARY KEY,
    policy integer NOT NULL REFERENCES AccessPolicy,
    person integer NOT NULL REFERENCES Person,
    artifact integer REFERENCES AccessPolicyArtifact,
    CONSTRAINT accesspolicypermission__policy__person__artifact__key
        UNIQUE (policy, person, artifact)
);

CREATE UNIQUE INDEX accesspolicypermission__policy__person__key
    ON AccessPolicyPermission(policy, person) WHERE artifact IS NULL;

ALTER TABLE bug
    ADD COLUMN access_policy integer REFERENCES AccessPolicy;
CREATE INDEX bug__access_policy__idx ON bug(access_policy);

ALTER TABLE branch
    ADD COLUMN access_policy integer REFERENCES AccessPolicy;
CREATE INDEX branch__access_policy__idx ON branch(access_policy);

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 99, 0);
