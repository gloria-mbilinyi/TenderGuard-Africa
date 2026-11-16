# Temporary laptop-hosted HTTPS demonstration

Use this when AWS launch authorization is unavailable. Cloudflare Quick Tunnels
provide a free temporary HTTPS hostname without an account, purchased domain, or
AWS provisioning. This is a laptop-hosted demonstration: keep Windows awake, connected
to power and the internet, and keep Ollama running. There is no uptime guarantee.
The existing local demo, Docker configuration, and recording remain independent.

Official service documentation: <https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/>.
Quick Tunnels do not support server-sent events; this application uses ordinary HTTP.

## Start

1. Use the existing `.venv`, built frontend, and installed `qwen3:1.7b` Ollama model.
2. Download `cloudflared` only from the official Cloudflare GitHub release and verify
   its SHA-256 against the release asset digest. Do not commit downloaded executables.
3. Start the supervisor from the repository root, using the verified binary path:

```powershell
.\.venv\Scripts\python.exe -m deploy.temporary_demo --cloudflared C:\PATH\cloudflared.exe --hours 8
```

For a background process, use PowerShell `Start-Process -WindowStyle Hidden`, the
same Python module/arguments, and private local logs. The supervisor starts a separate
loopback-only server on port 8768, creates a temporary HTTPS tunnel, and stops its own
two child processes after eight hours. It never opens an inbound firewall rule.

An explicit extension can update the live supervisor without restarting the tunnel,
backend, sessions, or data. Supply an exact timezone-aware cutoff within the next
24 hours; the default initial duration remains eight hours:

```powershell
.\.venv\Scripts\python.exe -m deploy.temporary_demo --extend-until "2026-11-17T20:47:00+03:00"
```

The command succeeds only after the running supervisor acknowledges the new cutoff.
Status exposes that effective expiry in UTC. Extensions cannot shorten the current
window. A legacy supervisor started before live control was supported needs the
one-time Windows watchdog takeover:

```powershell
.\.venv\Scripts\python.exe -m deploy.temporary_demo_watchdog --until "2026-11-17T20:47:00+03:00" --expected-supervisor RECORDED_WATCHDOG_PID
```

Run a takeover as a hidden background process. It checks the recorded watchdog,
its exact loopback tunnel/backend command lines, executable paths, creation times,
and stable Windows process handles before retiring only the old watchdog. It adopts
the existing workers, including Windows venv delegates, and preserves their runtime
files and password. The status heartbeat and `previous_supervisor_pid` confirm the
actual transfer. Do not stop the old watchdog separately or use process-tree kills.

```powershell
.\.venv\Scripts\python.exe -m deploy.temporary_demo --status
.\.venv\Scripts\python.exe -m deploy.temporary_demo --stop
```

Status gives the HTTPS URL, expiry in UTC, and the local credential-file path.
EAT is UTC+3. Open that file privately to obtain the dashboard password; do not paste
it into chat, recordings, Git, screenshots, or command-line arguments. Windows ACLs
restrict the per-run folder to the current user and SYSTEM. No API key is returned
to the browser. Runtime files and credentials live under Git-ignored storage.

## Security and validation

The server binds only to `127.0.0.1`. Browser traffic uses publicly trusted HTTPS to
Cloudflare and an encrypted outbound tunnel to this machine. The local hop is
loopback HTTP. The server uses an exact tunnel origin, Secure/HttpOnly/SameSite=Strict
cookies, existing authentication, CSRF checks, session expiry, audit, and human-review
protections. Workspaces are stored in an isolated private per-run folder. MCP and
Ollama have no tunnel routes of their own. Use only synthetic demonstration PDFs.

Verify the issued HTTPS URL with `python -m deploy.aws.verify_cloud --url https://ISSUED_HOST`.
The verifier prompts for the private password and uses real PDF extraction, Ollama,
LangGraph, MCP, and certificate validation. Report generation remains a separate
named administrator CLI action; a recorded authorizer name is not verified identity.

Cloudflare's ordinary proxy timeout can affect a slow evaluation. Warm the local model
and run the synthetic three-PDF check before presenting. If the laptop, tunnel, or
network becomes unavailable, use the existing Windows demo and recording.
After the eight-hour stop there are no AWS compute, disk, or IP resources from this
temporary path. The local runtime files remain for review and can be removed later
by their owner. A new run receives a new hostname and password.

## Container verification

The public-repository `Deployment verification` GitHub workflow builds the actual
production image and starts an isolated Caddy/Ollama/application stack. It tests TLS,
three PDFs, real AI/MCP evaluation, denied report authorization, named synthetic
draft authorization, protected downloads, and persistence after container replacement.
It uses a test-only local CA and loopback ports; production TLS settings stay intact.
The standard public runner is free and test volumes are removed after each run.
