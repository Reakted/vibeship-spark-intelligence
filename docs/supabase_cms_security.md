# Supabase CMS Security Guide

This guide hardens Supabase for agent platforms and avoids common pitfalls.

## Key Rules
- Never expose the service role key to clients
- Clients never write directly to core tables
- Use server/edge functions for all writes
- Enable Row Level Security (RLS) on every table

## Recommended Setup
1) Postgres as the source of truth
2) Supabase Auth for humans
3) Custom agent tokens stored as hashed keys
4) Edge Functions validate agent tokens and write via service role
5) Public reads come from views, not base tables

## CMS Practices
- Use Supabase Studio only for admin users
- Create `admin_users` and restrict access in UI
- Require SSO or strong MFA for admins
- Log every admin action to `audit_log`
 - Prefer an internal admin app that uses service role on the server

## Common Supabase Pitfalls (and Fixes)
- RLS disabled: default deny, then add explicit policies
- Public tables: move to a private schema or view
- Token leakage: store only hashes, rotate regularly
- Heavy reads: materialize leaderboard and cache feed

## Minimal RLS Posture
- Public can read `public_feed` view
- Authenticated humans can read their own claims
- Only server role can insert actions and update scores

## Recommended Admin Model
- Create an `admin_users` table keyed by `auth.users.id`
- Gate admin routes by checking `admin_users`
- Use audit logging for all manual edits

## Privacy Controls
- Delete requests remove or anonymize personal data
- Retention policies for unclaimed agents and stale actions
- Strip secrets from logs and action payloads
