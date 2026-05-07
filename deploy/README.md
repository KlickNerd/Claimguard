# ClaimGuard Deployment

Inhouse-Deployment auf einem Hostinger VPS Frankfurt mit docker-compose
und Caddy als Auto-TLS-Reverse-Proxy.

## Voraussetzungen auf der VPS

- Ubuntu 22.04+ (oder Debian 12+)
- mind. **8 GB RAM** (E5 + BGE-Reranker laden zusammen ~ 1,5 GB; Qdrant
  + Postgres + Redis + Caddy + Frontend brauchen den Rest)
- mind. **4 CPU-Kerne**, 50 GB SSD
- Domain (oder Subdomain) mit **DNS-A-Record auf die VPS-IP**.
  Erst danach kann Caddy ein TLS-Zertifikat ziehen.
- SSH-Zugang als root oder ein User mit sudo

## 1. Server vorbereiten

```bash
# Als root oder mit sudo:
apt update && apt upgrade -y
apt install -y docker.io docker-compose-plugin git

# Firewall: nur 22/80/443 reinlassen
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# Optional: deinen User in die docker-Gruppe, damit du ohne sudo
# arbeiten kannst.
usermod -aG docker $USER
# danach einmal neu einloggen
```

## 2. Repo + .env

```bash
# Repo nach /opt/claimguard ziehen
cd /opt
git clone https://github.com/<dein-org>/ClaimGuard claimguard
cd claimguard

# Production-Env anlegen
cp .env.production.example .env.production
nano .env.production
```

In `.env.production` musst du anpassen:

| Variable | Wert |
|---|---|
| `DOMAIN` | z. B. `claimguard.deinedomain.de` (DNS-A-Record muss schon zeigen) |
| `ANTHROPIC_API_KEY` | dein Anthropic-Key |
| `POSTGRES_PASSWORD` | starkes Passwort, frisch generiert (`openssl rand -hex 24`) |

## 3. Stack bauen + starten

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

Das bricht beim ersten Start in mehreren Schritten herunter:

1. **Bilder bauen** — API ~ 5 Min, Web ~ 3 Min
2. **Caddy lädt Let's-Encrypt-Cert** — ~ 30 Sek, sichtbar in den Logs
3. **API-Container startet** — pullt beim ersten Request E5 (~ 440 MB)
   und BGE-Reranker (~ 568 MB) auf das `models`-Volume.

Nach erfolgreichem Start:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production ps
```

Alle 6 Services sollten `healthy` oder `running` sein.

## 4. Knowledge Base indexieren (einmalig)

```bash
# In den API-Container reingehen und das Index-Skript laufen lassen
docker compose -f docker-compose.prod.yml --env-file .env.production exec api \
    python -m scripts.index_knowledge_base
```

Der Indexer läuft 1-3 Min, schreibt 1.961 Chunks nach Qdrant +
Postgres-FTS. Kommt am Ende `Done. eu_claims=221 hcvo_chunks=179
extra_reg=9 case_law=12 botanicals=1540` raus.

## 5. Live-Test

Im Browser:

```
https://<DEINE_DOMAIN>/app
```

Eingabetext einfügen, „Claims prüfen" klicken — sollte innerhalb von
~ 15-25 s ein Result liefern. Beim allerersten Request lädt der
API-Container die ML-Modelle, da kann es einmalig 60-90 s dauern.

## Updates ausrollen

```bash
cd /opt/claimguard
git pull
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

Caddy/Postgres/Qdrant/Redis-Volumes bleiben erhalten, nur API + Web
werden neu gebaut. Models-Cache bleibt auch erhalten — kein
Re-Download nötig.

Wenn nur die Frontend-Codebase geändert wurde:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production \
    up -d --no-deps --build web
```

Backend analog mit `--build api`.

## Logs

```bash
# Alle Services
docker compose -f docker-compose.prod.yml --env-file .env.production logs -f

# Nur Backend
docker compose -f docker-compose.prod.yml --env-file .env.production logs -f api

# Nur Caddy (TLS-Probleme, 4xx/5xx)
docker compose -f docker-compose.prod.yml --env-file .env.production logs -f caddy
```

## Backup

Drei Volumes lohnen sich zu sichern:

- `claimguard_postgres-data` — kb_chunks-Tabelle (FTS-Index)
- `claimguard_qdrant-data` — Vektor-Embeddings
- `claimguard_caddy-data` — Let's-Encrypt-Zertifikate (auch
  reproduzierbar via Re-Issue, aber spart eine Minute beim Restore)

Beispiel mit `tar`:

```bash
docker run --rm \
    -v claimguard_postgres-data:/data \
    -v $(pwd):/backup \
    alpine tar czf /backup/postgres-$(date +%F).tgz -C /data .
```

Das Models-Volume (`claimguard_models`) muss **nicht** gesichert
werden - es wird beim ersten Cold-Start automatisch von Huggingface
neu gezogen.

## Stoppen / Neustart

```bash
# Stoppen
docker compose -f docker-compose.prod.yml --env-file .env.production stop

# Hochfahren
docker compose -f docker-compose.prod.yml --env-file .env.production start

# Komplett runterfahren (Container löschen, Volumes bleiben)
docker compose -f docker-compose.prod.yml --env-file .env.production down

# Volumes auch löschen (KB-Verlust!)
docker compose -f docker-compose.prod.yml --env-file .env.production down -v
```

## Häufige Probleme

**Caddy bekommt kein Cert** → DNS-Record stimmt nicht. Test mit
`dig +short A claimguard.deinedomain.de` — muss die VPS-IP
zurückgeben.

**API zeigt `anthropic_unavailable: credit balance is too low`** →
Anthropic-Konto auf https://console.anthropic.com/settings/billing
aufladen.

**Backend braucht ewig beim ersten Request** → das Modellladen ist
nur einmal pro Container-Lifecycle. Wenn das Models-Volume korrekt
mountet, sind Folgerequests schnell. Check:
`docker volume inspect claimguard_models`.

**Out-of-memory beim API** → VPS hat zu wenig RAM. E5 (~ 500 MB) +
BGE (~ 1 GB) müssen rein, plus FastAPI selbst. Mindestens 4 GB für
die API allein, gesamtes System mind. 8 GB.

## Schutz / Auth (später)

Aktuell ist die Domain ungeschützt — wer die URL kennt, kann das Tool
nutzen. Sobald das problematisch wird, eine der drei Optionen:

1. **Caddy Basic-Auth** im Caddyfile - 5 Min Setup
2. **Cloudflare Access** vor Caddy - Login mit Google/Microsoft
3. **Tailscale-VPN** - Tool nur intern erreichbar

Sag Bescheid welche und wir bauen's.
