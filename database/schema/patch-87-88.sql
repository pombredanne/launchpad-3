SET client_min_messages=ERROR;

CREATE TABLE CodeImport (
    id SERIAL PRIMARY KEY,
    date_created TIMESTAMP WITHOUT TIME ZONE DEFAULT timezone('UTC', now()) NOT NULL,
    name text NOT NULL UNIQUE,
    rcs_type integer NOT NULL,
    svn_branch_url text UNIQUE,
    cvs_root text,
    cvs_module text,
    branch integer REFERENCES Branch,
    product integer REFERENCES Product NOT NULL,

    UNIQUE (cvs_root, cvs_module),

    CONSTRAINT valid_name CHECK (valid_name(name)),
    CONSTRAINT valid_cvs CHECK ((rcs_type <> 1) OR (
        (cvs_root IS NOT NULL) AND (cvs_root <> ''::text) AND
        (cvs_module IS NOT NULL) AND (cvs_module <> '':text))),
    CONSTRAINT null_cvs CHECK ((rcs_type == 1) OR (
        (cvs_root IS NULL) AND (cvs_module IS NULL))),
    CONSTRAINT valid_svn CHECK ((rcs_type <> 2) OR (
        (svn_branch_url IS NOT NULL) AND (svn_branch_url <> '':text))),
    CONSTRAINT null_svn CHECK ((rcs_type == 2) OR (svn_branch_url IS NULL)),

    FOREIGN KEY (branch, product) REFERENCES Branch (id, product)
);

-- XXX: This should be fixed once we get a real patch number:
-- MichaelHudson, 2007-05-15
INSERT INTO LaunchpadDatabaseRevision VALUES (87, 88, 1);
