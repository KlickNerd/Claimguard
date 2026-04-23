# PROJ-1: User Authentication

## Status: Planned
**Created:** 2026-04-23
**Last Updated:** 2026-04-23
**Backlog-Referenz:** F-040

## Dependencies
- None (Basis-Feature)

## User Stories
- Als neuer Nutzer möchte ich mich per E-Mail + Passwort registrieren, damit ich ClaimGuard nutzen kann.
- Als neuer Nutzer möchte ich mich alternativ per Google OAuth registrieren, damit ich nicht erneut ein Passwort verwalten muss.
- Als registrierter Nutzer möchte ich eine Verifikations-E-Mail erhalten, damit Spam-/Fake-Accounts verhindert werden.
- Als eingeloggter Nutzer möchte ich meine Session für 30 Tage behalten, damit ich mich nicht täglich neu einloggen muss.
- Als Nutzer, der sein Passwort vergessen hat, möchte ich einen sicheren Reset-Flow, damit ich wieder Zugriff bekomme.

## Acceptance Criteria
- [ ] Registrierung per E-Mail + Passwort (min. 12 Zeichen, Zonxcvbn-Score ≥ 3) funktioniert über Supabase Auth
- [ ] Registrierung per Google OAuth funktioniert (OAuth-Consent auf Deutsch)
- [ ] Verifikations-E-Mail wird innerhalb 30 s versendet, Link gültig 24 h
- [ ] Account ist vor Verifikation gesperrt: Login möglich, Analyse nicht auslösbar
- [ ] Passwort-Reset per E-Mail-Link, Token gültig 1 h, einmalig verwendbar
- [ ] JWT-Token werden vom Next.js-Frontend an das FastAPI-Backend weitergereicht, Backend validiert gegen Supabase
- [ ] Session-TTL konfigurierbar, Default 30 Tage, Refresh-Token rotiert bei jedem Use
- [ ] Alle Auth-E-Mails in deutscher Sprache, ClaimGuard-Absender
- [ ] Logout invalidiert Session serverseitig (nicht nur Cookie löschen)

## Edge Cases
- **E-Mail bereits registriert:** Generische Fehlermeldung „E-Mail oder Passwort ungültig" auf Login-Seite, keine User-Enumeration
- **Verifikations-Link abgelaufen:** Button „Neuen Link anfordern" mit Rate-Limit (1 pro 5 Min)
- **Google-OAuth-Konto ohne verifizierte E-Mail:** Ablehnen mit klarer Meldung
- **Nutzer ändert E-Mail in Google:** Supabase-Identity bleibt, E-Mail-Änderung triggert neue Verifikation
- **Brute-Force auf Login:** Rate-Limit 5 Versuche pro 10 Min pro IP + E-Mail, danach 15-Min-Lockout
- **Passwort-Reset mit bereits verwendetem Token:** Generische Fehlermeldung, User muss neuen Link anfordern
- **User löscht sich selbst während aktiver Analyse:** Laufende Analyse wird abgebrochen, nicht abgerechnet

## Technical Requirements
- Supabase Auth (Email/Passwort, Google OAuth)
- JWT-Validierung im FastAPI-Backend via supabase-py
- Session-Cookie: HttpOnly, Secure, SameSite=Lax
- Passwort-Hashing übernimmt Supabase (bcrypt/scrypt)
- E-Mail-Templates in Supabase konfigurierbar (DE)
- Rate-Limiting per IP + E-Mail-Kombi

## Open Questions
- Magic-Link-Login als zusätzliche Option (statt Passwort)? → V1.1 evaluieren
- 2FA/MFA im MVP nötig? → **Entscheidung: nein, V1.1**

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
_To be added by /architecture_

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
