-- Step 2.1: アプリ用ユーザー olivo を NOSUPERUSER NOBYPASSRLS で作成
--
-- 設計意図:
--   - DB の SUPERUSER は postgres ユーザーのみ
--   - アプリは olivo ユーザーで接続。olivo は最初から NOSUPERUSER で作成され、
--     RLS をバイパスできない通常ユーザーとして振る舞う
--   - Postgres 15+ の public スキーマ権限制約に対応するため、
--     public スキーマのオーナーも olivo に移譲

CREATE ROLE olivo WITH LOGIN PASSWORD 'olivo_dev_password'
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION
    NOBYPASSRLS;

CREATE DATABASE olivo_chat OWNER olivo;

\connect olivo_chat

-- Postgres 15+ では public スキーマのオーナーが postgres のまま残る。
-- olivo がテーブル/関数/トリガーを作れるよう、スキーマ自体のオーナーも移譲。
ALTER SCHEMA public OWNER TO olivo;
