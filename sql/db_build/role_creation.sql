CREATE ROLE [software_user];

-- Grant INSERT, SELECT permission on specific SCHEMA
GRANT INSERT, SELECT ON SCHEMA::[metadata] TO [software_user];
GRANT INSERT, SELECT ON SCHEMA::[outputs] TO [software_user];

-- Grant UPDATE permission on specific fields in the run table
GRANT UPDATE ([end_date], [complete]) ON [metadata].[run] TO [software_user];