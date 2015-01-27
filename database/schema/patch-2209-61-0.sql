-- Copyright 2015 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE OR REPLACE FUNCTION valid_git_repository_name(text) RETURNS boolean
    LANGUAGE plpythonu IMMUTABLE STRICT
    AS $_$
    import re
    name = args[0]
    pat = r"^(?i)[a-z0-9][a-z0-9+\.\-@_]*\Z"
    if not name.endswith(".git") and re.match(pat, name):
        return 1
    return 0
$_$;

COMMENT ON FUNCTION valid_git_repository_name(text) IS 'validate a Git repository name.

    As per valid_branch_name, except we disallow names ending in ".git".';

CREATE TABLE GitRepository (
    id serial PRIMARY KEY,
    date_created timestamp without time zone DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    date_last_modified timestamp without time zone DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    registrant integer NOT NULL REFERENCES person,
    owner integer NOT NULL REFERENCES person,
    product integer REFERENCES product,
    distribution integer REFERENCES distribution,
    sourcepackagename integer REFERENCES sourcepackagename,
    name text,
    information_type integer NOT NULL,
    access_policy integer,
    access_grants integer[],
    CONSTRAINT one_container CHECK (((product IS NULL) OR (distribution IS NULL)) AND ((distribution IS NULL) = (sourcepackagename IS NULL))),
    CONSTRAINT valid_name CHECK (valid_git_repository_name(name))
);

CREATE UNIQUE INDEX gitrepository__owner__product__name__key
    ON GitRepository(owner, product, name) WHERE product IS NOT NULL AND distribution IS NULL;
CREATE UNIQUE INDEX gitrepository__owner__distribution__sourcepackagename__name__key
    ON GitRepository(owner, distribution, sourcepackagename, name) WHERE product IS NULL AND distribution IS NOT NULL;
CREATE UNIQUE INDEX gitrepository__owner__name__key
    ON GitRepository(owner, name) WHERE product IS NULL AND distribution IS NULL;

COMMENT ON TABLE GitRepository IS 'Git repository';
COMMENT ON COLUMN GitRepository.registrant IS 'The user who registered the repository.';
COMMENT ON COLUMN GitRepository.owner IS 'The owner of the repository.';
COMMENT ON COLUMN GitRepository.product IS 'The product that this repository belongs to.';
COMMENT ON COLUMN GitRepository.distribution IS 'The distribution that this repository belongs to.';
COMMENT ON COLUMN GitRepository.sourcepackagename IS 'The source package that this repository belongs to.';
COMMENT ON COLUMN GitRepository.name IS 'The name of this repository, if it is not the default one for its owner.';
COMMENT ON COLUMN GitRepository.information_type IS 'Enum describing what type of information is stored, such as type of private or security related data, and used to determine how to apply an access policy.';

ALTER TABLE AccessArtifact
    ADD COLUMN gitrepository integer REFERENCES gitrepository DEFAULT NULL;

CREATE UNIQUE INDEX accessartifact__gitrepository__key
    ON AccessArtifact(gitrepository) WHERE gitrepository IS NOT NULL;

ALTER TABLE AccessArtifact DROP CONSTRAINT has_artifact;

ALTER TABLE AccessArtifact
    ADD CONSTRAINT has_artifact CHECK ((null_count(ARRAY[bug, branch, gitrepository, specification]) = 3));

CREATE OR REPLACE FUNCTION gitrepository_denorm_access(branch_id integer)
    RETURNS void LANGUAGE sql SECURITY DEFINER SET search_path = public AS $$
    UPDATE GitRepository
        SET access_policy = policies[1], access_grants = grants
        FROM
            build_access_cache(
                (SELECT id FROM accessartifact WHERE branch = $1),
                (SELECT information_type FROM branch WHERE id = $1))
            AS (policies integer[], grants integer[])
        WHERE id = $1;
$$;

CREATE OR REPLACE FUNCTION accessartifact_denorm_to_artifacts(artifact_id integer)
    RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    artifact_row accessartifact%ROWTYPE;
BEGIN
    SELECT * INTO artifact_row FROM accessartifact WHERE id = artifact_id;
    IF artifact_row.bug IS NOT NULL THEN
        PERFORM bug_flatten_access(artifact_row.bug);
    END IF;
    IF artifact_row.branch IS NOT NULL THEN
        PERFORM branch_denorm_access(artifact_row.branch);
    END IF;
    IF artifact_row.gitrepository IS NOT NULL THEN
        PERFORM gitrepository_denorm_access(artifact_row.gitrepository);
    END IF;
    IF artifact_row.specification IS NOT NULL THEN
        PERFORM specification_denorm_access(artifact_row.specification);
    END IF;
    RETURN;
END;
$$;

COMMENT ON FUNCTION accessartifact_denorm_to_artifacts(artifact_id integer) IS
    'Denormalize the policy access and artifact grants to bugs, branches, Git repositories, and specifications.';

-- A trigger to handle gitrepository.information_type changes.
CREATE OR REPLACE FUNCTION gitrepository_maintain_access_cache_trig() RETURNS trigger
    LANGUAGE plpgsql AS $$
BEGIN
    PERFORM gitrepository_denorm_access(NEW.id);
    RETURN NULL;
END;
$$;

CREATE TRIGGER gitrepository_maintain_access_cache
    AFTER INSERT OR UPDATE OF information_type ON GitRepository
    FOR EACH ROW EXECUTE PROCEDURE gitrepository_maintain_access_cache_trig();

CREATE TABLE GitRef (
    id serial PRIMARY KEY,
    repository integer NOT NULL REFERENCES gitrepository,
    path text NOT NULL,
    commit_sha1 character(40) NOT NULL 
);

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 61, 0);
