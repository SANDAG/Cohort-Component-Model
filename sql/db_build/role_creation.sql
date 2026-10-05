CREATE ROLE ccm_user;

-- Grant INSERT, SELECT permission on a specific SCHEMA
GRANT INSERT, SELECT ON SCHEMA::[metadata] TO ccm_user;
GRANT INSERT, SELECT ON SCHEMA::[inputs] TO ccm_user;
GRANT INSERT, SELECT ON SCHEMA::[outputs] TO ccm_user;

-- Grant UPDATE permission on specific fields in the run table
GRANT UPDATE ([end_date], [complete]) ON [metadata].[run] TO ccm_user;