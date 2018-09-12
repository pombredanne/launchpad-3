-- Copyright 2018 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE TABLE GitRule (
    id serial PRIMARY KEY,
    repository integer NOT NULL REFERENCES gitrepository ON DELETE CASCADE,
    ref_pattern text NOT NULL,
    creator integer NOT NULL REFERENCES person,
    date_created timestamp without time zone DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    date_last_modified timestamp without time zone DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL
);

CREATE UNIQUE INDEX gitrule__repository__ref_pattern__key
    ON GitRule(repository, ref_pattern);

COMMENT ON TABLE GitRule IS 'An access rule for a Git repository.';
COMMENT ON COLUMN GitRule.repository IS 'The repository that this rule is for.';
COMMENT ON COLUMN GitRule.ref_pattern IS 'The pattern of references matched by this rule.';
COMMENT ON COLUMN GitRule.creator IS 'The user who created this rule.';
COMMENT ON COLUMN GitRule.date_created IS 'The time when this rule was created.';
COMMENT ON COLUMN GitRule.date_last_modified IS 'The time when this rule was last modified.';

ALTER TABLE GitRepository ADD COLUMN rule_order integer[];

COMMENT ON COLUMN GitRepository.rule_order IS 'An ordered array of access rule IDs in this repository.';

CREATE TABLE GitRuleGrant (
    id serial PRIMARY KEY,
    repository integer NOT NULL REFERENCES gitrepository ON DELETE CASCADE,
    rule integer NOT NULL REFERENCES gitrule ON DELETE CASCADE,
    grantee_type integer NOT NULL,
    grantee integer REFERENCES person,
    can_create boolean DEFAULT false NOT NULL,
    can_push boolean DEFAULT false NOT NULL,
    can_force_push boolean DEFAULT false NOT NULL,
    grantor integer NOT NULL REFERENCES person,
    date_created timestamp without time zone DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    date_last_modified timestamp without time zone DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    -- 2 == PERSON
    CONSTRAINT has_grantee CHECK ((grantee_type = 2) = (grantee IS NOT NULL))
);

CREATE INDEX gitrulegrant__repository__idx
    ON GitRuleGrant(repository);
CREATE UNIQUE INDEX gitrulegrant__rule__grantee_type__grantee_key
    ON GitRuleGrant(rule, grantee_type, grantee);

COMMENT ON TABLE GitRuleGrant IS 'An access grant for a Git repository rule.';
COMMENT ON COLUMN GitRuleGrant.repository IS 'The repository that this grant is for.';
COMMENT ON COLUMN GitRuleGrant.rule IS 'The rule that this grant is for.';
COMMENT ON COLUMN GitRuleGrant.grantee_type IS 'The type of entity being granted access.';
COMMENT ON COLUMN GitRuleGrant.grantee IS 'The person or team being granted access.';
COMMENT ON COLUMN GitRuleGrant.can_create IS 'Whether creating references is allowed.';
COMMENT ON COLUMN GitRuleGrant.can_push IS 'Whether pushing references is allowed.';
COMMENT ON COLUMN GitRuleGrant.can_force_push IS 'Whether force-pushing references is allowed.';
COMMENT ON COLUMN GitRuleGrant.grantor IS 'The user who created this grant.';
COMMENT ON COLUMN GitRuleGrant.date_created IS 'The time when this grant was created.';
COMMENT ON COLUMN GitRuleGrant.date_last_modified IS 'The time when this grant was last modified.';

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 85, 0);
