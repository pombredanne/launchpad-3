-- Copyright 2011 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).
SET client_min_messages=ERROR;

CREATE TABLE AccessPolicyUse (
    id serial PRIMARY KEY,
    product integer REFERENCES Product,
    distribution integer REFERENCES Distribution,
    policy integer,
    CONSTRAINT has_target CHECK (product IS NULL != distribution IS NULL)
);

CREATE UNIQUE INDEX accesspolicyuse__product__policy__key
    ON AccessPolicyUse(product, policy) WHERE product IS NOT NULL;
CREATE UNIQUE INDEX accesspolicyuse__distribution__policy__key
    ON AccessPolicyUse(distribution, policy) WHERE distribution IS NOT NULL;

CREATE TABLE AccessPolicyArtifact (
    id serial PRIMARY KEY,
    bug integer REFERENCES Bug,
    branch integer REFERENCES Branch,
    policy_use integer NOT NULL REFERENCES AccessPolicyUse,
    CONSTRAINT has_artifact CHECK (bug IS NULL != branch IS NULL)
);

CREATE UNIQUE INDEX accesspolicyartifact__bug__key
    ON AccessPolicyArtifact(bug) WHERE branch IS NULL;
CREATE UNIQUE INDEX accesspolicyartifact__branch__key
    ON AccessPolicyArtifact(branch) WHERE bug IS NULL;
CREATE INDEX accesspolicyartifact__policy_use__key
    ON AccessPolicyArtifact(policy_use);

CREATE TABLE AccessPolicyGrant (
    id serial PRIMARY KEY,
    person integer NOT NULL REFERENCES Person,
    policy_use integer REFERENCES AccessPolicyUse,
    artifact integer REFERENCES AccessPolicyArtifact,
    creator integer NOT NULL REFERENCES Person,
    date_created timestamp without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    CONSTRAINT has_target CHECK (policy_use IS NULL != artifact IS NULL)
);

CREATE UNIQUE INDEX accesspolicygrant__policy_use__person__key
    ON AccessPolicyGrant(policy_use, person) WHERE policy_use IS NOT NULL;
CREATE UNIQUE INDEX accessartifactgrant__artifact__person__key
    ON AccessPolicyGrant(artifact, person) WHERE artifact IS NOT NULL;
CREATE INDEX accesspolicygrant__person__idx ON AccessPolicyGrant(person);

ALTER TABLE bug
    ADD COLUMN access_policy_use integer REFERENCES AccessPolicyUse;
CREATE INDEX bug__access_policy_use__idx ON bug(access_policy_use);

ALTER TABLE branch
    ADD COLUMN access_policy_use integer REFERENCES AccessPolicyUse;
CREATE INDEX branch__access_policy_use__idx ON branch(access_policy_use);

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 93, 1);
