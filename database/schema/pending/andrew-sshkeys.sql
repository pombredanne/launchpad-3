
CREATE TABLE SSHKey (
    id          serial PRIMARY KEY,
    person      integer REFERENCES Person,
    keytype     integer NOT NULL,
    keytext     text NOT NULL, 
    comment     text NOT NULL
);

COMMENT ON COLUMN SSHKey.keytype IS 'See canonical.lp.dbschema.SSHKeyType.';
COMMENT ON COLUMN SSHKey.keytext IS 'includes keysize, exponent and modulus, in
the same format as openssh''s config files (such as authorized_keys and
id_dsa.pub)';
COMMENT ON COLUMN SSHKey.comment IS 'a human-readable comment describing the
key.  By default, this tends to be something like andrew@trogdor';


