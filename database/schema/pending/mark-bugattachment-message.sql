
/*
  This fixes the name of a field in the bugattachment table. Ages ago when
  we renamed bugmessage to message and then created a new bugmessage linking
  table between bug and message I should have spotted this fieldname and
  renamed it. Stub, this one is good to go.

  Note that the bugattachment system will be entirely reviewed once we have
  figured out emails-in-the-database properly, with the email-sig.
*/

ALTER TABLE bugattachment RENAME COLUMN bugmessage TO message;
