-- Copyright 2011 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).
SET client_min_messages=ERROR;

CREATE TABLE AccessPolicy (
    id serial PRIMARY KEY,
    product integer REFERENCES Product,
    distribution integer REFERENCES Distribution,
    name text NOT NULL,
    display_name text NOT NULL,
    CONSTRAINT has_target CHECK (product IS NULL != distribution IS NULL),
    CONSTRAINT valid_name CHECK (valid_name(name))
);

CREATE UNIQUE INDEX accesspolicy__product__name__key
    ON AccessPolicy(product, name) WHERE product IS NOT NULL;
CREATE UNIQUE INDEX accesspolicy__product__display_name__key
    ON AccessPolicy(product, display_name) WHERE product IS NOT NULL;
CREATE UNIQUE INDEX accesspolicy__distribution__name__key
    ON AccessPolicy(distribution, name) WHERE distribution IS NOT NULL;
CREATE UNIQUE INDEX accesspolicy__distribution__display_name__key
    ON AccessPolicy(distribution, display_name) WHERE distribution IS NOT NULL;

CREATE TABLE AccessPolicyArtifact (
    id serial PRIMARY KEY,
    bug integer REFERENCES Bug,
    branch integer REFERENCES Branch,
    CONSTRAINT has_artifact CHECK (bug IS NULL != branch IS NULL)
);

CREATE UNIQUE INDEX accesspolicyartifact__bug__key
    ON AccessPolicyArtifact(bug) WHERE branch IS NULL;
CREATE UNIQUE INDEX accesspolicyartifact__branch__key
    ON AccessPolicyArtifact(branch) WHERE bug IS NULL;

CREATE TABLE AccessPolicyGrant (
    id serial PRIMARY KEY,
    policy integer NOT NULL REFERENCES AccessPolicy,
    person integer NOT NULL REFERENCES Person,
    artifact integer REFERENCES AccessPolicyArtifact
);

CREATE UNIQUE INDEX accesspolicygrant__policy__person__artifact__key
    ON AccessPolicyGrant(policy, person, artifact) WHERE artifact IS NOT NULL;
CREATE UNIQUE INDEX accesspolicygrant__policy__person__key
    ON AccessPolicyGrant(policy, person) WHERE artifact IS NULL;
CREATE INDEX accesspolicygrant__person__idx ON AccessPolicyGrant(person);

ALTER TABLE bug
    ADD COLUMN access_policy integer REFERENCES AccessPolicy;
CREATE INDEX bug__access_policy__idx ON bug(access_policy);

ALTER TABLE branch
    ADD COLUMN access_policy integer REFERENCES AccessPolicy;
CREATE INDEX branch__access_policy__idx ON branch(access_policy);

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 93, 1);
