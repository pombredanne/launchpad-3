ALTER TABLE SourcepackageName ADD CONSTRAINT lowercasename 
    CHECK (lower(name) = name);
