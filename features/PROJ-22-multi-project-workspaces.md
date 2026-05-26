# PROJ-22: Multi-Projekt-Workspaces mit Team-Einladungen

## Status: Architected
**Created:** 2026-05-25
**Last Updated:** 2026-05-25

## Dependencies
- **Hard-Requires: PROJ-21 (Analyses-Persistierung)** — die `analyses`-Tabelle ist die Tabelle, an die `project_id` als FK hängt. Ohne persistierte Analysen gibt es nichts „in ein Projekt zu legen". PROJ-22 muss daher denselben Migrationsschritt mitnehmen oder direkt nach PROJ-21 deployen.
- **Hard-Requires: PROJ-1 (User Authentication)** — Owner, Member, Invites referenzieren `auth.users`; RLS-Policies basieren auf `auth.uid()`.
- Soft: PROJ-2 (Plan- & Nutzungs-Verwaltung) — pro-plan-abhängige Projekt-/Member-Limits werden dort definiert, im MVP harte Default-Limits.
- Soft: PROJ-16 (Dashboard / History) — Liste wird auf das aktive Projekt gefiltert.
- Soft: PROJ-20 (KI-Chat) — Chat-Verlauf folgt der Analyse, die zu einem Projekt gehört, kein eigener Mechanismus nötig.

## User Stories

### Account-Inhaber (z. B. Agentur)
- Als Agentur-Inhaber möchte ich pro Kunde ein eigenes Projekt anlegen können, damit Prüfungen sauber nach Kunden getrennt sind und ich nicht versehentlich Kunde-A-Analysen für Kunde-B verwende.
- Als Agentur-Inhaber möchte ich Mitarbeiter:innen per E-Mail in ein Kunden-Projekt einladen, damit das Team kollaborativ am selben Kunden arbeiten kann — ohne Logins zu teilen.
- Als Agentur-Inhaber möchte ich Rollen vergeben (Owner / Editor / Viewer), damit Junior-Texter Analysen anlegen, aber nicht versehentlich Mitglieder rausschmeißen oder das Projekt löschen können.
- Als Agentur-Inhaber möchte ich Projekte umbenennen und mit einer Farb-Markierung versehen, damit ich sie in der Sidebar visuell schnell unterscheide.

### Mitarbeiter:in / Eingeladener User
- Als eingeladene Person möchte ich nach Klick auf den Invite-Link automatisch in das Projekt aufgenommen werden (nach Login oder neuem Account), damit ich nicht in einer Sackgasse lande.
- Als Mitglied eines Projekts möchte ich beim Anlegen einer neuen Analyse sehen, in welchem Projekt sie gerade landet, damit ich nicht versehentlich Analysen ins falsche Projekt schiebe.

### Einzelnutzer:in (kein Team)
- Als Solo-User möchte ich nach dem Login direkt ein einsatzbereites Default-Projekt vorfinden („Mein Workspace"), ohne Setup-Schritte, damit ich sofort loslegen kann.
- Als Solo-User möchte ich Projekte ignorieren können — alle meine Analysen landen automatisch im Default-Projekt, ohne jede Auswahl.

## Acceptance Criteria

### Projekt-Anlegen & Verwalten
- [ ] Beim ersten Login eines Users wird automatisch ein Default-Projekt „Mein Workspace" angelegt, mit dem User als Owner.
- [ ] User können über den Switcher in der Sidebar (Workspace-Card oben) ein neues Projekt anlegen: Modal mit Name (Pflicht, 3–60 Zeichen) und Farbe (eine von 8 vorgegebenen Tailwind-Farben).
- [ ] Owner können Projekte umbenennen (gleicher Modal mit aktuellen Werten vorausgefüllt).
- [ ] Owner können Projekte löschen mit Bestätigungs-Dialog, der den Projektnamen zur Eingabe verlangt („Tippe »X« zum Bestätigen").
- [ ] Beim Löschen eines Projekts werden alle zugehörigen Analysen mit-soft-gelöscht (folgen dem Soft-Delete-Window aus PROJ-21, 30 Tage).
- [ ] Beim Löschen eines Projekts werden alle Memberships dieses Projekts hart entfernt; Mitglieder sehen das Projekt sofort nicht mehr.
- [ ] Default-Projekt („Mein Workspace") kann nicht gelöscht werden, solange es das einzige Projekt eines Users ist.

### Projekt-Switcher in der Sidebar
- [ ] Die Workspace-Card oben in der Sidebar zeigt das aktuell aktive Projekt mit Farbe + Name + Mitglieder-Anzahl.
- [ ] Klick öffnet ein Dropdown mit: Liste aller Projekte (mit Farb-Indikator, Owner-Badge bei Owner-Projekten), Trenner, „Neues Projekt anlegen", „Projekte verwalten".
- [ ] Auswahl eines Projekts wechselt das aktive Projekt; History- und Neue-Prüfung-Ansichten filtern entsprechend.
- [ ] Das aktive Projekt wird im LocalStorage persistiert; nach Reload ist es weiterhin aktiv. Wenn ein User das Recht verliert (Member-Entfernung) oder Projekt gelöscht wurde, fällt der Switcher automatisch auf das Default-Projekt zurück.

### Analyse-Zuordnung
- [ ] `POST /api/analyses` akzeptiert ein optionales Feld `project_id`. Wenn nicht angegeben, wird das aktive Projekt aus dem Header (`X-Active-Project-Id`) verwendet, sonst Default-Projekt.
- [ ] Backend validiert, dass der User Membership im angegebenen Projekt hat; sonst 403 mit Code `project_forbidden`.
- [ ] `GET /api/analyses?project_id=...` liefert nur Analysen aus dem angegebenen Projekt; ohne Filter werden alle Analysen aller Projekte zurückgegeben, in denen der User Member ist.
- [ ] History-Page filtert standardmäßig auf das aktive Projekt; ein Toggle „Alle Projekte" zeigt projektübergreifend.
- [ ] Anzeige in jeder Analyse-Zeile: Farb-Punkt + Projektname als kleines Badge, damit beim Toggle „Alle Projekte" die Zuordnung sichtbar ist.

### Mitglieder & Rollen
- [ ] Drei Rollen: **Owner** (alles), **Editor** (Analysen anlegen/lesen/löschen + Member sehen), **Viewer** (nur lesen).
- [ ] Owner können Mitglieder per E-Mail einladen, Rolle wählen (Editor oder Viewer), Member-Liste auf einer Projekt-Detail-Seite einsehen.
- [ ] Owner können bestehende Mitglieder umrollen oder entfernen.
- [ ] Ein Projekt hat immer mindestens einen Owner. Der einzige Owner kann sich nicht selbst entfernen oder umrollen — er muss vorher einen anderen Member zum Owner promoten.
- [ ] Editor/Viewer sehen den „Mitglieder verwalten"-Bereich, aber nur read-only.
- [ ] In der Member-Liste ist eingeladen-aber-noch-nicht-akzeptiert sichtbar als „Einladung versendet · pending".

### Invite-Flow
- [ ] Owner gibt E-Mail-Adresse + Rolle ein, klickt „Einladen". System erstellt einen Invite-Record (Tabelle `project_invites`) mit Token (UUID), Status `pending`, Verfallsdatum (7 Tage), und versendet eine E-Mail an die Adresse.
- [ ] E-Mail enthält den Projektnamen, den Namen des einladenden Users, die Rolle, und einen Link `https://claim-guard.de/invite/{token}`.
- [ ] Klick auf den Invite-Link führt:
  - **Bereits eingeloggter User mit derselben E-Mail:** Token wird eingelöst, User wird sofort Member, redirect nach `/app` mit Toast „Du bist jetzt Mitglied bei …".
  - **Eingeloggter User mit anderer E-Mail:** Fehlerseite „Diese Einladung ist nicht für dein Konto bestimmt".
  - **Nicht eingeloggter User, hat aber Account:** Login-Seite mit E-Mail vorbefüllt; nach Login wird Token eingelöst.
  - **Nicht eingeloggter User ohne Account:** Register-Seite mit E-Mail vorbefüllt; nach Bestätigung der E-Mail wird Token eingelöst und Membership angelegt.
- [ ] Mehrfach-Einladungen an dieselbe E-Mail werden zu einer Einladung zusammengefasst (Reuse des bestehenden pending-Tokens).
- [ ] Invites lassen sich vom Owner widerrufen, solange `pending` (Button „Einladung zurückziehen" in der Member-Liste).
- [ ] Abgelaufene Invites (älter als 7 Tage) werden beim Klick auf den Link mit „Einladung abgelaufen — bitte beim Projekt-Inhaber neue anfordern" abgelehnt; ein Background-Cleanup räumt solche Records nach 30 Tagen physisch weg.

### Backend
- [ ] Neue Endpoints unter `/api/projects`:
  - `GET /api/projects` — alle Projekte, in denen der User Member ist.
  - `POST /api/projects` — neues Projekt anlegen (User wird Owner).
  - `GET /api/projects/{id}` — Projekt-Detail inkl. Member-Liste; nur Member.
  - `PATCH /api/projects/{id}` — Name / Farbe ändern; nur Owner.
  - `DELETE /api/projects/{id}` — Projekt löschen; nur Owner; nicht erlaubt für Default-Projekt eines Users wenn es das einzige Projekt ist.
- [ ] Member-Endpoints:
  - `POST /api/projects/{id}/invites` — Mitglied per E-Mail einladen; nur Owner.
  - `DELETE /api/projects/{id}/invites/{invite_id}` — Einladung zurückziehen; nur Owner.
  - `POST /api/projects/{id}/members/{user_id}/role` — Rolle ändern; nur Owner.
  - `DELETE /api/projects/{id}/members/{user_id}` — Mitglied entfernen; nur Owner (Self-Removal nur für Nicht-Owner möglich).
- [ ] Invite-Token-Einlösung:
  - `POST /api/invites/{token}/accept` — Token einlösen (User muss eingeloggt sein und E-Mail muss matchen); legt Membership an, markiert Invite `accepted`.

### RLS + Sicherheit
- [ ] RLS auf `projects`: SELECT, wenn User Member ist; INSERT erlaubt für jeden eingeloggten User (er wird automatisch Owner); UPDATE/DELETE nur, wenn User Owner ist.
- [ ] RLS auf `project_members`: SELECT für Member desselben Projekts; INSERT/UPDATE/DELETE nur durch Owner desselben Projekts.
- [ ] RLS auf `project_invites`: SELECT durch Owner; INSERT durch Owner; UPDATE durch Owner (Widerruf) oder den eingeladenen User (Accept).
- [ ] RLS auf `analyses` wird erweitert: SELECT, wenn User Member des `project_id` ist (statt nur `auth.uid() = user_id`); INSERT, wenn User Editor oder Owner.
- [ ] Backend nutzt Service-Role-Key, prüft Membership zusätzlich im Code (Defense-in-Depth, gleiches Muster wie PROJ-21).

## Edge Cases

- **User wird aus Projekt entfernt, während er gerade aktiv darin arbeitet:** Beim nächsten API-Call kommt 403; Frontend wechselt das aktive Projekt automatisch auf Default und zeigt Toast „Du bist nicht mehr Mitglied von … — gewechselt zu Mein Workspace".
- **Owner versucht, sich selbst zum Editor zu degradieren, während er einziger Owner ist:** API antwortet 409 mit Code `last_owner`. UI verhindert den Button-Klick proaktiv.
- **Letzter Member (=Owner) löscht sein eigenes nicht-Default-Projekt:** Cascade soft-deletet alle Analysen (PROJ-21-Soft-Delete-Window greift), löscht das Projekt aus der Sidebar; User landet auf Default-Projekt.
- **Default-Projekt wurde irgendwie hart gelöscht (Daten-Inkonsistenz):** Beim nächsten Login legt der Auto-Onboarding-Trigger ein neues Default-Projekt an. Idempotent.
- **Invite an E-Mail-Adresse, die bereits Member ist:** API antwortet 409 mit Code `already_member`. UI zeigt das vor dem Absenden, indem die Member-Liste verglichen wird.
- **Invite-Token wird nach erstem Klick erneut angeklickt:** Status ist bereits `accepted` — Endpoint antwortet idempotent mit 200, redirect nach `/app`.
- **Invite-Token wird verändert / ungültig (Brute-Force-Versuche):** API antwortet 404 mit generischem „Einladung nicht gefunden oder abgelaufen". Rate-Limiting auf den Accept-Endpoint.
- **User akzeptiert Invite, hat aber seinen Account zwischendurch gelöscht:** Beim erneuten Register mit derselben E-Mail wird der Token automatisch einlösbar — Status bleibt `pending` bis zur ersten Akzeptanz oder dem 7-Tage-Ablauf.
- **Eingeladener User registriert sich mit einer anderen E-Mail:** Token bleibt pending an die ursprüngliche E-Mail gebunden; der neue Account hat keinen Zugriff. Er muss eine neue Einladung anfordern.
- **Projekt-Name-Kollision** innerhalb desselben Users: erlaubt. Differenzierung über UUID; UI zeigt beide getrennt.
- **Mehr als 50 Member-Invites in 24 h vom selben User:** Rate-Limit 50/24h pro User auf `POST /api/projects/{id}/invites`, sonst 429. Spam-Schutz.
- **Switcher-Anzeige bei sehr vielen Projekten (>20):** Dropdown bekommt eine Sucheingabe-Komponente (basiert auf `Command` aus shadcn/ui).
- **SMTP-Ausfall beim Invite-Versand:** Backend antwortet 502 `mail_send_failed`, der Invite-Record wird trotzdem angelegt (User kann manuell den Link kopieren); Frontend zeigt „Mail-Versand fehlgeschlagen — Link kopieren?" mit dem Token.

## Non-Goals (MVP)

- **Cross-Account-Workspace-Wechsel** (z. B. „Switch zu einer komplett anderen Organisation"): jeder User hat genau eine Identität; Projekte hängen an dieser Identität. Multi-Tenancy in dem Sinne kommt erst in V2.
- **Granulare Permissions pro Analyse** (z. B. „Editor X darf nur seine eigenen Analysen löschen"): Editor kann alle Analysen seines Projekts löschen. Feinere Permissions kommen in V1.2.
- **Audit-Log** für Member-Aktionen („Wer hat wen wann eingeladen?"): kommt in V1.2.
- **Externe Identity-Provider** auf Projekt-Ebene (SAML, SSO für Enterprise): V2.
- **Slack-/Discord-Notifications** bei Member-Aktionen: V2.
- **Plan-abhängige Limits** (z. B. Free = 1 Projekt, Pro = 10): wird in PROJ-2 modelliert; im MVP harter Default (10 Projekte / 10 Member pro Projekt für alle).
- **Project-Templates** („Klonen von Projekt X mit allen Einstellungen"): V1.2.
- **Project-Archiving** (zwischen aktiv/inaktiv): V1.2 — im MVP nur löschen oder behalten.

## Technical Requirements

- **Datenbank:** Drei neue Tabellen in Supabase Postgres (EU): `projects`, `project_members`, `project_invites`. Erweiterung von `analyses` um `project_id` (FK, NOT NULL nach Migration).
- **Auto-Onboarding:** DB-Trigger `on_auth_user_created` (kommt aus PROJ-1) wird erweitert, um beim neuen User ein Default-Projekt + Owner-Membership anzulegen — atomar in derselben Transaction.
- **Migration (Bestandsdaten):** Wenn PROJ-21 schon Analysen persistiert hat, müssen die in ein Default-Projekt migriert werden. Migration legt für jeden User mit existierenden Analysen das Default-Projekt an und setzt `analyses.project_id` auf dessen ID.
- **API:** FastAPI-Routen unter `/api/projects/...` + `/api/invites/...`; Pydantic-Schemas für Projects / Members / Invites.
- **E-Mail-Versand:** **Eigener Transactional-SMTP-Provider** (z. B. Resend oder Postmark), nicht der Supabase-Default-Mailer — der hat 3 Mails/h Limit. Architektur-Entscheidung gehört in PROJ-22-Architektur. EU-Region des Providers ist Pflicht (DSGVO).
- **Frontend:** Erweiterung der `AppSidebar` um Projekt-Switcher-Dropdown; neue Seite `/app/projects/[id]` für Member-Verwaltung; neue Page `/invite/[token]` für Invite-Acceptance.
- **State-Management:** Aktives Projekt im React-Context (`ProjectContext`), persistiert via LocalStorage, server-seitig validiert bei jedem API-Call.
- **Performance:** Projekt-Liste pro User muss < 100 ms zurückkommen. History-Filter pro Projekt < 300 ms bei 1.000 Analysen.
- **Sicherheit:** RLS auf allen vier Tabellen (`projects`, `project_members`, `project_invites`, `analyses`); zusätzlich Membership-Check im Backend-Code.
- **DSGVO:** Account-Löschung (PROJ-17) kaskadiert über `project_members` → entfernt User aus allen Projekten, ohne die Projekte zu löschen (Co-Owner bleibt; falls letzter Owner = der gelöschte User → Projekt wird ebenfalls hart gelöscht).

## Offene Fragen (für /architecture)

1. **E-Mail-Provider:** Resend vs. Postmark vs. Mailjet — alle bieten EU-Region. Welcher passt zum bestehenden Stack? Sollen wir den Supabase-Auth-Mailer (für Passwort-Reset/Confirm) und den Invite-Mailer auf denselben Provider legen, oder bleiben sie getrennt?
2. **Aktives Projekt: Server-seitig oder Client-seitig?** Aktuell vorgeschlagen: LocalStorage + Header `X-Active-Project-Id`. Alternative wäre eine Spalte `users.active_project_id` in Supabase. Pro Server-State: konsistent über Devices. Pro Client-State: einfacher, keine extra Tabelle. Empfehlung in Architecture-Phase.
3. **Default-Projekt-Anlage: Trigger oder Lazy?** Variante A: DB-Trigger erweitert. Variante B: Backend-Endpunkt `/api/me/bootstrap` wird beim ersten Login getriggert. Trigger ist robuster (atomar), Endpoint ist debugbarer.
4. **`analyses.project_id`-Constraint:** `NOT NULL` nach Migration oder bleibt `NULL` als gültiger Zustand möglich (für Demo-/Anonym-Analysen)? Empfehlung: NOT NULL für eingeloggte Analysen, Demo bleibt sowieso ungespeichert.
5. **Soft-Delete-Cascade-Verhalten:** Wenn Projekt soft-gelöscht wird (UI-Variante), bleiben Analysen soft-bezogen oder fallen sofort weg? Aktuell vorgeschlagen: Projekt-Löschung ist hart, Analysen folgen dem PROJ-21-Soft-Delete-Pattern. Architecture muss das schließen.
6. **Member-Limit pro Projekt im MVP:** 10? 20? Hängt an PROJ-2 (Pricing). Im MVP-Default: 10.

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)

### Großer Bogen

Drei neue Tabellen — `projects`, `project_members`, `project_invites` — bilden zusammen mit der bestehenden `analyses`-Tabelle (kommt aus PROJ-21) den Kern. Eine Analyse gehört über `analyses.project_id` zu genau einem Projekt; ein User wird über `project_members` mit einer Rolle (Owner / Editor / Viewer) an Projekte gebunden. Beim Anlegen eines neuen Accounts (PROJ-1-Trigger) wird in derselben Transaktion automatisch ein Default-Projekt „Mein Workspace" + Owner-Membership angelegt — User landen auf einer einsatzbereiten Oberfläche, ohne Setup-Schritt.

Das aktive Projekt wird **zwei-stufig** geführt: kanonisch auf `profiles.active_project_id` (synchronisiert über Devices), gespiegelt im Browser-LocalStorage für Instant-Paint nach Reload. Jeder API-Call schickt `X-Active-Project-Id` mit; das Backend validiert Mitgliedschaft und liefert den aktualisierten Wert via Response-Header zurück, falls der Client veraltet ist.

Einladungen laufen über E-Mail mit signiertem Token, versendet via **Resend** (EU-Region, AVV verfügbar). Token-Klick verzweigt in vier Pfade (eingeloggt-match / eingeloggt-andere-Mail / nicht-eingeloggt-mit-Account / nicht-eingeloggt-ohne-Account); pg_cron räumt abgelaufene Invites automatisch weg.

PROJ-21 und PROJ-22 werden als **gemeinsame Migration** ausgerollt — die `analyses`-Tabelle entsteht und bekommt direkt im selben Schritt ihren `project_id`-FK, statt zwei aufeinander folgende Schema-Versionen zu bauen.

### Komponentenstruktur (Backend)

```
apps/api/app/
├── api/
│   ├── analyses.py            (bestehend → akzeptiert/validiert project_id)
│   ├── projects.py            (NEU — CRUD + Members)
│   └── invites.py             (NEU — Invite-Lifecycle, getrennt weil pre-/post-Auth)
├── services/
│   ├── analysis_storage.py    (aus PROJ-21 → erweitert um project_id-Filter)
│   ├── project_repo.py        (NEU — Supabase-Wrapper für projects/members/invites)
│   └── mailer.py              (NEU — Resend-Client + Template-Loader)
├── schemas/
│   ├── analysis.py            (bestehend → StoredAnalysis bekommt project_id)
│   └── project.py             (NEU — Project, Member, Invite, RoleEnum)
├── core/
│   └── auth.py                (bestehend → neue Helper: require_member, require_role)
└── prompts/                   (unverändert)
```

### Komponentenstruktur (Frontend)

```
apps/web/src/
├── app/
│   ├── app/                       (Routegruppe, hinter Auth-Middleware)
│   │   ├── layout.tsx             (bestehend → wrappt jetzt ProjectProvider)
│   │   ├── page.tsx               (Neue Prüfung — zeigt aktives Projekt als Badge)
│   │   ├── history/page.tsx       (bestehend → Projekt-Filter-Toggle)
│   │   ├── projects/
│   │   │   ├── page.tsx           (NEU — Liste aller Projekte des Users)
│   │   │   └── [id]/page.tsx      (NEU — Detail: Einstellungen + Mitglieder + Pending-Invites)
│   │   └── ...
│   └── invite/
│       └── [token]/page.tsx       (NEU — außerhalb /app, weil un-eingeloggte User Zugang brauchen)
├── components/
│   ├── app/
│   │   ├── app-sidebar.tsx        (bestehend → WorkspaceSwitcher ersetzt Mock-Card)
│   │   ├── workspace-switcher.tsx (NEU — Dropdown mit Projekten + Aktionen)
│   │   ├── project-create-dialog.tsx (NEU — Modal für Anlegen/Umbenennen)
│   │   ├── project-delete-dialog.tsx (NEU — „Tippe Namen zum Bestätigen"-Modal)
│   │   └── member-list.tsx        (NEU — Tabelle Rolle / entfernen / Pending-Invites)
│   └── ui/                        (shadcn-Bausteine — alle bereits installiert)
└── lib/
    ├── project-context.tsx        (NEU — React-Context für aktives Projekt + Switch)
    ├── api-client.ts              (bestehend → neue Funktionen: listProjects, createProject, …)
    └── supabase.ts                (unverändert)
```

### Datenmodell (in Worten)

**Neue Tabelle: `projects`**
- **ID** (UUID, vom Server)
- **Name** (Text, 3-60 Zeichen, vom User)
- **Farbe** (Text, eine von 8 vorgegebenen Tailwind-Tokens — z. B. „indigo", „emerald", „rose")
- **Default-Marker** (Boolean — `true` für das auto-angelegte „Mein Workspace"; per User max. einmal `true`)
- **Erstellt am** + **Aktualisiert am**

**Neue Tabelle: `project_members`** (Junction zwischen `projects` und `auth.users`)
- **Projekt-ID** + **User-ID** (zusammen Primärschlüssel)
- **Rolle** (`owner` | `editor` | `viewer`)
- **Beigetreten am**

**Neue Tabelle: `project_invites`**
- **ID** + **Token** (UUID, indiziert für Lookup)
- **Projekt-ID** (FK)
- **E-Mail** (lowercase-normalisiert, Index)
- **Vorgesehene Rolle** (`editor` | `viewer` — Owner-Invites sind nicht erlaubt im MVP)
- **Status** (`pending` | `accepted` | `revoked` | `expired`)
- **Eingeladen von** (User-ID), **Eingeladen am**, **Läuft ab am** (= invited_at + 7 Tage), **Akzeptiert am** (optional)

**Erweiterung von `analyses` (kommt aus PROJ-21):**
- Neue Spalte **Projekt-ID** (FK auf `projects`, `NOT NULL` nach Migration der Bestandsdaten)
- Bestehende Spalte **user_id** bleibt — sie zeigt, **wer** die Analyse erstellt hat (für Audit-Zwecke), während `project_id` zeigt, **wo** sie liegt

**Erweiterung von `profiles` (kommt aus PROJ-1):**
- Neue Spalte **active_project_id** (FK auf `projects`, nullable — wird per Trigger initial auf das Default-Projekt gesetzt)

**Indexe:**
- `project_members(user_id)` — schnelle Liste „meine Projekte"
- `project_members(project_id)` — schnelle Liste „Mitglieder dieses Projekts"
- `project_invites(token)` — Lookup beim Accept-Klick
- `project_invites(email, status)` — Duplikat-Check vor neuer Einladung
- `analyses(project_id, created_at DESC) WHERE deleted_at IS NULL` — ersetzt den PROJ-21-Index, gleicher Use-Case, jetzt project-scoped

**Row-Level-Security (auf alle vier Tabellen aktiv):**
- `projects` — SELECT, wenn User Mitglied ist; INSERT für jeden Eingeloggten (er wird zum Owner); UPDATE/DELETE nur durch Owner
- `project_members` — SELECT durch jedes Mitglied desselben Projekts; INSERT/UPDATE/DELETE nur durch Owner
- `project_invites` — SELECT durch Owner desselben Projekts; INSERT/UPDATE durch Owner (Widerruf) oder eingeladenen User (Accept)
- `analyses` — bestehende Policy aus PROJ-21 erweitert: SELECT, wenn Mitglied im `project_id`; INSERT, wenn Editor oder Owner

**Defense-in-Depth:** Das Backend verwendet weiterhin den Service-Role-Key (umgeht RLS), prüft Membership + Rolle aber zusätzlich im Code. Identisch zum PROJ-21-Pattern.

### Endpoints im Überblick

| Methode | Pfad | Wozu |
|---|---|---|
| **GET** | `/api/projects` | Eigene Projekte (alle Projekte, in denen User Mitglied ist) |
| **POST** | `/api/projects` | Neues Projekt anlegen, User wird Owner |
| **GET** | `/api/projects/{id}` | Projekt-Detail inkl. Mitglieder + Pending-Invites |
| **PATCH** | `/api/projects/{id}` | Name / Farbe ändern (Owner) |
| **DELETE** | `/api/projects/{id}` | Projekt löschen (Owner, nicht wenn einziges Default) |
| **POST** | `/api/projects/{id}/invites` | Einladung erstellen + Mail versenden (Owner) |
| **DELETE** | `/api/projects/{id}/invites/{invite_id}` | Pending-Einladung zurückziehen (Owner) |
| **PUT** | `/api/projects/{id}/members/{user_id}/role` | Rolle ändern (Owner) |
| **DELETE** | `/api/projects/{id}/members/{user_id}` | Mitglied entfernen (Owner; Self-Removal nur Nicht-Owner) |
| **POST** | `/api/me/active-project` | Aktives Projekt setzen (schreibt `profiles.active_project_id`) |
| **POST** | `/api/invites/{token}/accept` | Token einlösen (pre-/post-Login, prüft Email-Match) |
| **GET** | `/api/invites/{token}` | Token-Info zum Anzeigen auf der `/invite/[token]`-Page (Projektname, Einladender) |
| **POST/GET/DELETE** | `/api/analyses(...)` | aus PROJ-21, erweitert um project_id-Validation |

### Aktive-Projekt-Synchronisation (das Drei-Schichten-Modell)

1. **Server-Quelle** (`profiles.active_project_id`) — kanonisch, gilt bei Konflikt
2. **Frontend-React-Context** (`ProjectContext`) — bekommt initialen Wert beim Server-Render des AppLayouts (zero-flicker)
3. **Browser-LocalStorage** — gecachte Last-Known-Active, sorgt für Instant-Paint nach Reload, bevor Server-Wert eintrifft

**Sync-Flow:**
- User klickt im Switcher auf Projekt B → Frontend ändert sofort Context + LocalStorage → ruft `POST /api/me/active-project` im Hintergrund → bei Fehler: rollback auf vorherigen Wert mit Toast
- Reload → LocalStorage liefert sofortigen Wert → Server-Wert wird aus dem `profiles`-Fetch geprüft → wenn abweichend, Server gewinnt + LocalStorage wird korrigiert (Cross-Device-Konsistenz)
- API-Call mit veraltetem `X-Active-Project-Id` → Server antwortet `X-Active-Project-Id`-Header mit aktuellem Wert → Client passt sich an

### Default-Projekt-Anlage

Erweiterung des bestehenden `on_auth_user_created`-Triggers (kommt aus PROJ-1):
1. User-Reihe in `auth.users` entsteht
2. Trigger feuert → erzeugt `profiles`-Eintrag (war bisher die einzige Aktion)
3. **NEU:** Erzeugt zusätzlich ein `projects`-Reihe mit Name „Mein Workspace", `is_default=true`
4. **NEU:** Erzeugt ein `project_members`-Reihe mit Rolle `owner`
5. **NEU:** Setzt `profiles.active_project_id` auf die ID des neuen Projekts

Alles in derselben Transaktion. Idempotent dank `ON CONFLICT DO NOTHING` — falls der Trigger versehentlich zweimal feuert, bleibt's bei einem Default-Projekt.

### Invite-Lifecycle (Kurzform)

```
Owner klickt "Einladen"
    │
    ▼
POST /api/projects/{id}/invites
    │
    ├─ Backend validiert: Owner-Rolle, kein Member-Match, kein Pending-Match
    ├─ Token generieren (UUID), Insert in project_invites mit status=pending, expires_at=now+7d
    ├─ Mailer.send (Resend) → React-Email-Template mit Token-URL
    │
    ▼
Empfänger klickt Mail-Link → /invite/{token}
    │
    ├─ Page-Load → GET /api/invites/{token} → Status- & Pfad-Entscheidung
    │
    ▼
4 Pfade je nach Session-Zustand:
  • Eingeloggt + Email-Match    → Auto-Accept → /app mit Toast
  • Eingeloggt + Email-Mismatch → Fehlermeldung, kein Accept
  • Nicht eingeloggt + Account  → Redirect /login?invite={token}&email=… → nach Login Auto-Accept
  • Nicht eingeloggt ohne Account → Redirect /register?invite={token}&email=… → nach Bestätigung Auto-Accept

Token-Cleanup via pg_cron (täglich):
  • Pending > 7d → status=expired
  • Nicht-pending > 30d → DELETE
```

### Migration / Datenbank-Änderungen (Coupled mit PROJ-21)

**Eine Supabase-Migration in neun Schritten** ersetzt die alleinige PROJ-21-Migration:

1. Tabelle `analyses` anlegen (aus PROJ-21)
2. Tabelle `projects` anlegen
3. Tabelle `project_members` anlegen
4. Tabelle `project_invites` anlegen
5. Spalte `analyses.project_id` (nullable) hinzufügen
6. **Bestandsdaten-Migration:** Für jeden bestehenden User (falls die DB nicht greenfield ist) Default-Projekt anlegen + bestehende Analysen darauf zeigen lassen
7. `analyses.project_id` auf **NOT NULL** setzen
8. Spalte `profiles.active_project_id` (nullable, FK auf `projects`)
9. Trigger `on_auth_user_created` erweitern; pg_cron-Jobs registrieren (PROJ-21-Purge + Invite-Cleanup); RLS-Policies aktivieren

**Erwartung:** Die DB ist beim ersten Deploy greenfield (kein User hat sich vor PROJ-1 registriert). Schritt 6 ist dann ein No-Op. Falls doch Bestandsdaten existieren, läuft die Migration trotzdem durch, weil die Default-Projekt-Erstellung idempotent ist.

### Tech-Entscheidungen (das Warum)

1. **Resend als Mailer (statt Postmark / Mailjet / Supabase-Default).** EU-Region (Frankfurt) verfügbar, AVV vorhanden — DSGVO-konform für Invite-Mails mit personenbezogenen Daten (Email der Empfänger). Free-Plan deckt MVP-Volumen (3.000 Mails/Monat ≫ erwartete Invite-Rate). React-Email als Template-Stack erlaubt versionierte, getypte Templates statt HTML-Strings im Code. Domain-Verification über DNS-Records einmalig nötig — `claim-guard.de` wird Sender. Postmark wäre robuster, aber teurer und kein nennenswerter Free-Tier; Mailjet hat schwächere DX; der Supabase-Default-Mailer ist mit 3 Mails/h für Team-Invites zu klein.

2. **Server-Source + Client-Cache für aktives Projekt.** Gewählt für Multi-Device-Konsistenz: Agentur-User wechseln zwischen Laptop / Tablet / Phone, das aktive Projekt soll mitwandern. Reine LocalStorage-Lösung wäre einfacher, aber pro Browser inkonsistent. Reine Server-Lösung wäre robust, aber jeder Reload würde einen API-Roundtrip vor dem ersten Render kosten (LocalStorage-Cache vermeidet den Flicker). Der zusätzliche Code für die Sync-Logik ist überschaubar — ein React-Context plus ein Hintergrund-PATCH bei jedem Switch.

3. **DB-Trigger für Default-Projekt (statt Lazy-Bootstrap-Endpoint).** Atomar mit der User-Anlage, vermeidet Race-Conditions („User existiert, aber kein Projekt"). Idempotent dank `ON CONFLICT`. Erweitert den bestehenden Auth-Trigger aus PROJ-1, kein zweiter Trigger nötig. Lazy-Endpoint hätte den Vorteil besserer Debuggbarkeit, aber Trigger sind in Supabase robust und kommen ohne Frontend-Coupling aus.

4. **Coupled Migration PROJ-21 + PROJ-22.** Statt die `analyses`-Tabelle erst ohne `project_id` zu deployen und dann nachträglich umzubauen, geht beides in einem Schritt. Keine zwei Migrations-Versionen, kein Zwischen-Zustand, in dem `project_id` `NULL` ist und Code aus Versehen ungescopt schreibt. Die PROJ-21-Spec wird in einem Anhang explizit auf diese Kopplung verwiesen — das ursprüngliche PROJ-21-Design (pg_cron, JSONB-Snapshot, Soft-Delete) bleibt unverändert in Kraft.

5. **Member-Limits als Backend-Konstanten (10/10), nicht in der DB.** Free-vs-Pro-Logik kommt erst in PROJ-2. Limits in einer Konfigurationsdatei sind ohne Schema-Änderung anpassbar; in der DB würden sie eine `plan`-Spalte erzwingen, die heute noch nicht existiert. 10 Projekte pro User + 10 Member pro Projekt deckt die Agentur-Persona im MVP solide (typischer Use-Case: 3–6 Kunden, 2–4 Mitarbeitende pro Projekt).

6. **Owner-Schutz im Code (statt DB-Constraint).** „Mindestens 1 Owner pro Projekt" als API-Validation, nicht als CHECK-Constraint. CHECKS, die Tupel-Anzahl in einer Junction-Tabelle messen, sind in Postgres awkward (Trigger nötig). Eine simple API-Validierung gibt zudem eine verständliche Fehlermeldung („Du bist der einzige Owner — promote jemanden bevor du rausgehst") statt eines kryptischen DB-Fehlers.

7. **`/invite/[token]` außerhalb von `/app`.** Die Auth-Middleware blockt `/app/*` für nicht-eingeloggte User. Invites müssen aber auch für Leute ohne Account funktionieren — daher der Token-Pfad als öffentliche Route. Die Page erkennt den Session-Zustand selbst und verzweigt in die vier Pfade.

8. **Token als UUID + Server-Side-Lookup (statt JWT).** UUID ist undurchsichtig (kein Information-Leak im Token selbst), brauchbar für einen einfachen DB-Lookup, und revoke-bar (`status=revoked`). JWT wäre stateless, aber nicht revoke-bar, was bei Invite-Widerruf zum Problem würde.

9. **`is_default`-Spalte auf `projects` (statt impliziter Heuristik).** Explizit markieren, welches Projekt das auto-angelegte ist — sonst müsste der Code raten („das älteste? das mit Namen ‚Mein Workspace'?"). Erleichtert auch die UI-Regel „Default-Projekt nicht löschbar, wenn einziges".

10. **Frontend-State via React-Context, nicht Zustand-Library.** Ein Provider-Scope reicht für ein einzelnes Konzept (aktives Projekt + Switch-Funktion). Externe State-Libraries wären Overkill und führen Boilerplate ein, den wir nicht brauchen.

11. **Invite-E-Mails im Backend (statt im Web-Hook).** Resend wird vom FastAPI-Service aus angesprochen, nicht vom Frontend oder einer Supabase-Edge-Function. Vorteil: Templates und Send-Logik liegen beim Code, der die Invite-Records erzeugt — ein Ort, ein Test. Nachteil: Backend muss den Resend-API-Key kennen, was Secret-Management bedeutet (kein Drama, der Service-Role-Key liegt eh dort).

12. **`X-Active-Project-Id`-Header statt URL-Query.** Header bleibt durchgängig für alle API-Calls, ohne dass jede Route den Parameter im Schema haben müsste. Backend liest den Header im Middleware und stellt ihn als Pydantic-Dependency bereit.

### Dependencies

**Backend (Python):**
- `resend` — offizielles Resend-SDK
- `pyjwt` — bereits durch Supabase eingebracht, hier ungenutzt aber erwähnt für Vollständigkeit
- _(keine weiteren neuen Packages)_

**Frontend (Node):**
- _keine neuen Packages_ — DropdownMenu, Dialog, Form, Sonner-Toast, Command-Search sind alle bereits in `components/ui/` installiert; react-hook-form + zod stehen bereit

**Email-Templates:**
- Templates liegen unter `apps/api/app/services/mailer_templates/` als einfache Jinja2-HTML-Dateien (Jinja2 ist Standard-Dependency von FastAPI-Verwandtem). React-Email wäre nett, würde aber ein eigenes Bundling-Setup einführen — für 1-2 Templates Overkill. Wenn die Template-Menge wächst, ist React-Email die V1.1-Migration.

**Externe Services:**
- Resend-Account (Free-Plan reicht), Domain-Verification über DNS-TXT- und CNAME-Records für `claim-guard.de` im Hostinger-DNS-Panel

### Risiken & Mitigationen

- **Resend-Domain-Verification scheitert oder dauert.** Während Verification läuft, kann von der Resend-Sandbox-Adresse versendet werden (kein Branding, aber funktional). Für Production muss DNS gepflegt sein, sonst landen Mails in Spam.
- **Cross-Device-Konflikt: User wechselt Projekt auf Laptop, Phone schickt API-Call mit altem Header.** Backend nimmt den Header, validiert Membership, und schickt im Response-Header den aktuellen Server-Wert mit. Client passt sich automatisch an. Kein User-Confirm nötig.
- **Member-Limit erreicht (10), User will mehr einladen.** UI zeigt Limit-Warnung, blockiert weitere Invites mit Hinweis auf Plan-Upgrade (Plan-Upgrade ist in PROJ-2; im MVP nur Anzeige).
- **Trigger schlägt fehl, User entsteht ohne Default-Projekt.** Dann scheitert die User-Anlage selbst (Trigger ist atomar mit dem User-Insert). User bekommt Register-Fehler, Auth-Cookie wird nicht gesetzt. Sehr unwahrscheinlich — DB-Trigger sind stabil — aber Postgres-Constraints fangen den Edge-Case.
- **Invite-Spam:** Rate-Limit 50 Invites / 24 h pro User auf den POST-Endpoint. Resend selbst hat Anti-Spam auf Account-Ebene.
- **Token-Brute-Force:** UUID-Tokens sind 128 Bit; Bruteforce nicht wirtschaftlich. Zusätzlich Rate-Limit auf `GET /api/invites/{token}` und `POST /api/invites/{token}/accept`.
- **PROJ-21 wird ohne PROJ-22 deployed:** Nicht vorgesehen, weil Migration coupled ist. Falls aus Versehen: `analyses.project_id` wäre nullable → Backend würde versehentlich ungescopte Inserts schreiben. Mitigation: Migration und beide Feature-Branches gemeinsam ausrollen.
- **`profiles.active_project_id` zeigt auf gelöschtes Projekt.** Cascade `ON DELETE SET NULL` auf der FK; Frontend erkennt `null` und fällt auf Default-Projekt zurück.
- **Bestehender Sidebar-Mock (`WORKSPACE` aus `mock-analyses.ts`):** wird beim Frontend-Bau durch echten ProjectContext ersetzt. Mock-Datei kann bei dieser Gelegenheit weiter abgespeckt werden.

### Offene Fragen aus der Spec — beantwortet

- **SMTP-Provider?** → **Resend**, EU-Region, AVV, niedrige Reibung.
- **Aktives Projekt: Server oder Client?** → **Beides** — Server kanonisch, Client gecacht.
- **Default-Projekt-Anlage: Trigger oder Lazy?** → **Trigger**, erweitert den bestehenden PROJ-1-Trigger.
- **`analyses.project_id` NOT NULL?** → **NOT NULL** nach der einmaligen Migration (Bestandsdaten füllen, dann Constraint).
- **Soft-Delete-Cascade Projekt → Analysen?** → Projekt-Löschung ist **hart**; abhängige Analysen folgen dem PROJ-21-Soft-Delete-Pattern via `ON DELETE` auf der FK (deren Soft-Delete-Window von 30 Tagen gilt weiter — wenn User es bereut, kann er sie über die Single-Analyse-Wiederherstellung zurückholen, aber das gelöschte Projekt kommt nicht wieder).
- **Member-Limit MVP?** → **10 Mitglieder pro Projekt + 10 Projekte pro User** als Backend-Konstante.

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
