SET client_min_messages TO error;

/*
  - Give each ProductRelease a shortdesc as well.
*/

ALTER TABLE ProductRelease ADD COLUMN shortdesc TEXT;

COMMENT ON COLUMN ProductRelease.shortdesc IS 'A short description of this ProductRelease. This should be a very brief overview of changes and highlights, just a short paragraph of text.';

