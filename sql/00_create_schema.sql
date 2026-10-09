-- Synthetic facts only. PostgreSQL is the single source of truth.
CREATE SCHEMA IF NOT EXISTS horizon;
SET search_path TO horizon;
CREATE TABLE IF NOT EXISTS run_metadata (key text PRIMARY KEY, value text NOT NULL);
CREATE TABLE IF NOT EXISTS users (
 user_id bigint PRIMARY KEY, register_date date NOT NULL, market text NOT NULL,
 acquisition_channel text NOT NULL, campaign text NOT NULL, device text NOT NULL,
 platform text NOT NULL, age_bucket text NOT NULL, latent_player_archetype text NOT NULL,
 acquisition_quality double precision NOT NULL);
CREATE TABLE IF NOT EXISTS sessions (
 session_id bigint PRIMARY KEY, user_id bigint NOT NULL REFERENCES users,
 session_date date NOT NULL, session_number integer NOT NULL,
 session_minutes double precision NOT NULL CHECK(session_minutes>0), device text NOT NULL,
 fps_quality_bucket integer NOT NULL CHECK(fps_quality_bucket BETWEEN 1 AND 3), crash_flag integer NOT NULL CHECK(crash_flag IN(0,1)));
CREATE TABLE IF NOT EXISTS progression (
 user_id bigint NOT NULL REFERENCES users, event_date date NOT NULL,
 chapter integer NOT NULL, level integer NOT NULL, tutorial_completed integer NOT NULL,
 core_loop_unlocked integer NOT NULL, boss_attempts integer NOT NULL,
 boss_failures integer NOT NULL, PRIMARY KEY(user_id,event_date));
CREATE TABLE IF NOT EXISTS gameplay_events (
 event_id bigint PRIMARY KEY, user_id bigint NOT NULL REFERENCES users,
 event_time timestamp NOT NULL, event_type text NOT NULL, event_value double precision NOT NULL);
CREATE TABLE IF NOT EXISTS monetization (
 transaction_id bigint PRIMARY KEY, user_id bigint NOT NULL REFERENCES users,
 transaction_date date NOT NULL, product_type text NOT NULL,
 amount_usd numeric(12,2) NOT NULL CHECK(amount_usd>=0));
CREATE TABLE IF NOT EXISTS acquisition (
 user_id bigint PRIMARY KEY REFERENCES users, market text NOT NULL, channel text NOT NULL,
 campaign text NOT NULL, creative text NOT NULL, acquisition_date date NOT NULL);
CREATE TABLE IF NOT EXISTS content_exposure (
 user_id bigint NOT NULL REFERENCES users, date date NOT NULL, content_type text NOT NULL,
 content_id text NOT NULL, exposed integer NOT NULL, clicked integer NOT NULL,
 PRIMARY KEY(user_id,date,content_id));
CREATE INDEX IF NOT EXISTS sessions_user_date ON sessions(user_id,session_date);
CREATE INDEX IF NOT EXISTS sessions_date ON sessions(session_date);
CREATE INDEX IF NOT EXISTS events_user_time ON gameplay_events(user_id,event_time);
CREATE INDEX IF NOT EXISTS events_type ON gameplay_events(event_type,user_id);
CREATE INDEX IF NOT EXISTS progression_user_date ON progression(user_id,event_date);
CREATE INDEX IF NOT EXISTS payment_user_date ON monetization(user_id,transaction_date);
CREATE INDEX IF NOT EXISTS users_cohort ON users(register_date,market,acquisition_channel);
CREATE INDEX IF NOT EXISTS exposure_user_date ON content_exposure(user_id,date);
