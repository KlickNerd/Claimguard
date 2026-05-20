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

### Großer Bogen

ClaimGuard nutzt **Supabase Auth** als User-Backbone. Im Frontend rendert Next.js die Login-/Register-/Reset-Seiten gegen den Supabase-JS-Client; nach erfolgreichem Auth liefert Supabase ein JWT, das in einem HttpOnly-Cookie liegt. Eine Next.js-Middleware schützt alle Workspace-Routen und leitet Unauthentifizierte zum Login um. Bei jedem API-Call schickt der Frontend das JWT mit, ein neues FastAPI-Dependency validiert es gegen Supabase, lädt das Profil und stellt es als „aktueller Nutzer" allen Endpoints zur Verfügung.

Parallel legen wir eine eigene `profiles`-Tabelle an, in der ClaimGuard-spezifische User-Daten (Anzeigename, später Plan-Status für PROJ-2) leben — getrennt von Supabase's verwalteter `auth.users`-Tabelle. Ein DB-Trigger sorgt dafür, dass beim Anlauf eines neuen Users automatisch eine Profil-Zeile mitkommt.

Rate-Limiting (5 Login-Versuche / 10 Min pro IP+E-Mail) läuft in einer schlanken FastAPI-Middleware mit Redis als Counter-Store. Redis steht im Stack schon bereit.

### Komponentenstruktur (Frontend)

```
apps/web/
├── src/app/
│   ├── login/page.tsx              (bestehend → bekommt echte Form-Logik)
│   ├── register/page.tsx           (neu)
│   ├── forgot-password/page.tsx    (neu — E-Mail-Eingabe für Reset-Link)
│   ├── reset-password/page.tsx     (neu — Landing nach E-Mail-Klick)
│   ├── verify-email/page.tsx       (neu — „bitte Postfach prüfen")
│   └── auth/callback/route.ts      (neu — OAuth-Callback für Google)
├── src/middleware.ts               (neu — Protected Routes)
├── src/lib/
│   ├── supabase.ts                 (existiert als Stub → wird aktiviert)
│   ├── supabase-server.ts          (neu — Variante für Server Components)
│   └── auth-context.tsx            (neu — `useUser`-Hook, AuthProvider)
└── src/components/
    └── auth/                       (neu)
        ├── auth-form.tsx           (gemeinsame Form für Login/Register)
        ├── google-button.tsx
        └── password-strength.tsx   (zxcvbn-Live-Indikator)
```

### Komponentenstruktur (Backend)

```
apps/api/app/
├── core/
│   └── auth.py                 (neu — JWT-Validierung, Dependency `get_current_user`)
├── middleware/
│   └── rate_limit.py           (neu — Redis-Counter pro IP+E-Mail)
├── api/
│   └── analyses.py             (bestehend → bekommt `Depends(get_current_user)`)
└── schemas/
    └── user.py                 (neu — Profile + CurrentUser Pydantic-Modelle)
```

### Datenmodell (in Worten)

**Supabase-managed (nicht selbst geschrieben):**
- `auth.users` — Supabase Standard: E-Mail, verschlüsseltes Passwort, OAuth-Identitäten, Verifikationsstatus, Created-Timestamp. Wir lesen nur, schreiben nie direkt rein.

**Neue Tabelle: `profiles`** (Public-Schema, 1:1 an `auth.users`)
- Verweist per Foreign Key auf `auth.users(id)`, löscht mit (Cascade).
- Felder: Anzeigename (optional), Avatar-URL (optional), Onboarding-Flag (boolean), Created/Updated-Timestamps.
- Spätere Erweiterung (PROJ-2): Plan, Abo-Status etc. werden additiv ergänzt — kein Schema-Bruch.
- **RLS:** Jeder User darf nur sein eigenes Profil lesen und ändern.

**Automatischer Profil-Anlauf:** Ein DB-Trigger reagiert auf jeden neuen Eintrag in `auth.users` und legt synchron eine `profiles`-Zeile in derselben Transaktion an. Damit gibt es nie User ohne zugehöriges Profil.

### Tech-Entscheidungen (das Warum)

1. **Supabase Auth statt selbstgebaut** — Steht in der Spec. Gehärtete Implementierung von Verifikation, OAuth, Password-Reset, Token-Rotation; E-Mail-Versand mit Vorlagen ist eingebaut. Stack-konform: Supabase-Postgres liegt schon in der EU.

2. **JWT im HttpOnly-Cookie + `Authorization: Bearer` für API-Calls** — Next.js sieht das Token via SSR-tauglichem Cookie, FastAPI bekommt es im Header. XSS-resistent (HttpOnly verhindert JS-Zugriff), CSRF-resistent über SameSite-Lax.

3. **Next.js Middleware für Protected Routes** — Statt jede Server-Komponente einzeln auf Auth zu prüfen, eine zentrale Datei. Less Code, weniger Edge-Cases, läuft sauber durch RSC-Streams.

4. **FastAPI-Dependency `get_current_user` statt globaler Middleware** — Geschützte Endpoints ziehen das Dependency rein (`Depends(get_current_user)`); öffentliche Routen wie `/health` bleiben ohne Auth, ohne Sonder-Logik in einer globalen Middleware.

5. **`profiles` separat von `auth.users`** — `auth.users` ist Supabase-managed; wir sollten dort nichts dazuhängen, weil ein Supabase-Schema-Update das überschreiben könnte. Eigene `profiles` im Public-Schema = volle Kontrolle, Standard-Supabase-Pattern.

6. **DB-Trigger statt App-Trigger für Profil-Anlauf** — Würde das Profil im App-Code nachgezogen, könnte ein Crash zwischen Sign-Up und Profil-Insert User ohne Profil hinterlassen. Der DB-Trigger arbeitet atomar in derselben Transaktion wie der User-Anlauf.

7. **Rate-Limiting in FastAPI + Redis statt nur Supabase-Defaults** — Supabase hat eingebaute Rate-Limits, aber generisch. Die Spec verlangt IP+E-Mail-Kombi-Lockout mit klarer Sperrdauer. Redis steht im Compose schon — Sliding-Window-Counter pro Schlüssel reicht.

8. **zxcvbn im Frontend** — Passwort-Strength-Score wird live beim Tippen berechnet, ohne Server-Roundtrip. Kleine Library, Industriestandard.

9. **Logout serverseitig** — Beim Logout-Klick wird Supabase `signOut` aufgerufen, das den Refresh-Token serverseitig invalidiert (nicht nur das Cookie löscht). Sonst könnte ein abgegriffenes Refresh-Token nach „Logout" weiter Sessions erzeugen.

### Dependencies

**Frontend (neu zu installieren):**
- `@supabase/ssr` — Server-Side-Helpers für Supabase Auth in Next.js (Middleware + Server Components)
- `zxcvbn` + `@types/zxcvbn` — Passwort-Strength-Score

**Backend (neu zu installieren):**
- `supabase` (supabase-py) — JWT-Validierung und User-Lookup

**Bereits vorhanden, neu genutzt:**
- `@supabase/supabase-js` (im Frontend bereits installiert, nur Stub muss aktiviert werden)
- Redis-Container (für Rate-Limit-Counter)

### Migration / Datenbank-Änderungen

Zwei neue Supabase-Migrationen:
1. **`profiles`-Tabelle** mit Foreign Key auf `auth.users(id)`, Indexen, RLS-Policies.
2. **Trigger-Funktion** + Trigger auf `auth.users` für automatischen Profil-Anlauf.

Bestehende Daten bleiben unberührt — reine Erweiterung. Die bisherigen API-Endpoints werden in einem zweiten Schritt (PROJ-1 Backend-Phase) auf Auth-protected umgestellt, mit klarer Deploy-Sequenz, damit Frontend und Backend nicht aus dem Tritt geraten.

### Risiken & Mitigationen

- **JWT läuft während langer Analyse ab** — Refresh-Token rotiert (Supabase-Default). Backend wirft bei abgelaufenem Token 401; Frontend macht im Hintergrund einen Silent-Refresh und wiederholt den Call.
- **Rollout-Reihenfolge** — Wenn Backend Auth verlangt, Frontend aber noch kein JWT mitschickt, würden alle Requests 401 sein. Deploy strikt: erst Frontend mit Auth-Flow, dann Backend mit `get_current_user`.
- **E-Mail-Versand zickt** — Supabase nutzt einen Default-SMTP, der manchmal in Spam landet. Mitigation: Custom-SMTP (Postmark / Resend) konfigurieren, ist eine reine Supabase-Setting-Änderung.
- **Schon registrierte E-Mail** — Spec verlangt generische Fehlermeldung. Supabase liefert von Haus aus „User already registered"; wir mappen das im Frontend zu der generischen Meldung, ohne User-Enumeration zu erlauben.

### Offene Fragen aus der Spec — beantwortet

- **Magic-Link statt Passwort?** Bewusst raus aus dem MVP. Supabase kann es per Config — kein Architektur-Wechsel später nötig.
- **2FA?** Bewusst raus aus dem MVP. Supabase unterstützt TOTP-2FA, dann nur Config + UI nötig.

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
