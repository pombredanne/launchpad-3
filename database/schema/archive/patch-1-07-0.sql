/* Place to store unvalidated gpg keys for importing archives */
ALTER TABLE SourceSource ADD COLUMN currentgpgkey text;

