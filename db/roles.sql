-- Read-only role used by the agent. Dev password only: change it outside local use.
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'qp_readonly') THEN
    CREATE ROLE qp_readonly LOGIN PASSWORD 'readonly';
  END IF;
  EXECUTE format('GRANT CONNECT ON DATABASE %I TO qp_readonly', current_database());
END
$$;
GRANT USAGE ON SCHEMA public TO qp_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO qp_readonly;
ALTER ROLE qp_readonly SET default_transaction_read_only = on;
ALTER ROLE qp_readonly SET statement_timeout = '5s';
