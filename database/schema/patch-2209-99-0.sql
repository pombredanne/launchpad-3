SET client_min_messages=ERROR;

CREATE OR REPLACE FUNCTION check_email_address_person_account(
    person integer, account integer)
    RETURNS boolean
    LANGUAGE plpythonu IMMUTABLE RETURNS NULL ON NULL INPUT AS
$$
    # It's possible for an EmailAddress to be created without an
    # account. If that happens, and this function is called, we return
    # True so as to avoid breakages.
    if account is None:
        return True
    results = plpy.execute("""
        SELECT account FROM Person WHERE id = %s""" % person)
    # If there are no accounts with that Person in the DB, or the Person
    # is new and hasn't yet been linked to an account, return success
    # anyway. This helps avoid the PGRestore breaking (and referential
    # integrity will prevent this from causing bugs later.
    if results.nrows() == 0 or results[0]['account'] is None:
        return True
    return results[0]['account'] == account
$$;

COMMENT ON FUNCTION check_email_address_person_account(integer, integer) IS
'Check that the person to which an email address is linked has the same account as that email address.';

CREATE OR REPLACE FUNCTION check_person_email_address_account(
    person integer, account integer)
    RETURNS boolean
    LANGUAGE plpythonu IMMUTABLE RETURNS NULL ON NULL INPUT AS
$$
    # It's possible for a Person to be created without an account. If
    # that happens, return True so that things don't break.
    if account is None:
        return True
    email_address_accounts = plpy.execute("""
        SELECT account FROM EmailAddress WHERE
            person = %s AND account IS NOT NULL""" % person)
    # If there are no email address accounts to check, we're done.
    if email_address_accounts.nrows() == 0:
        return True
    for email_account_row in email_address_accounts:
        email_account = email_account_row['account']
        if email_account is not None and email_account != account:
            return False
    return True
$$;

COMMENT ON FUNCTION check_person_email_address_account(integer, integer) IS
'Check that the email addresses linked to a person have the same account ID as that person.';

ALTER TABLE EmailAddress ADD CONSTRAINT valid_account_for_person
    CHECK (check_email_address_person_account(person, account));
ALTER TABLE Person ADD CONSTRAINT valid_account_for_emailaddresses
    CHECK (check_person_email_address_account(id, account));

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 99, 0);
