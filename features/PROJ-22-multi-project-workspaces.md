# PROJ-22: Multi-Projekt-Workspaces mit Team-Einladungen

## Status: Planned
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
_To be added by /architecture_

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
