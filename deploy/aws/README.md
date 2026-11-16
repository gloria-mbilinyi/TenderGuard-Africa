# AWS deployment package (not provisioned)

This package targets a separately approved Ubuntu 24.04 EC2 instance in `eu-north-1`
(Stockholm). It does not create AWS resources automatically. Verify the current
Billing **Credits** details, service coverage, account plan, organizer rules, incremental
cost, alert recipient, and shutdown deadline before launching anything. Credit balances
are estimates and other account usage can consume them while the demo is running.

**Protected resource:** do not connect to or modify `mwalimulens-demo`. All installation,
deployment, and shutdown operations must target only the new `TenderGuard-Africa`
instance explicitly approved for this project.

## Architecture

```text
Internet -> EC2 security group (80/443 only) -> Caddy automatic HTTPS
                                             -> TenderGuard :8000 (private network)
                                             -> Ollama :11434 (private network)

Persistent named volumes: TLS state, uploaded PDFs, reports/audit, Ollama model
SSH: restricted to the operator's current /32 address; never open to 0.0.0.0/0
```

Only Caddy publishes ports. FastAPI, Ollama, and both stdio MCP servers have no public
host ports. TenderGuard runs as UID 10001 with a read-only root filesystem, dropped
capabilities, secure cookies, exact-origin CSRF checks, and persistent private data
volumes. The current password/session design is appropriate for a controlled demo,
not a multi-user institutional production deployment.

## Preflight approval gate

Record all of these before launching anything:

- AWS account and target region;
- Billing > Credits: amount remaining and expiration date;
- Cost Explorer current month total and existing charge sources;
- existing EC2, EBS, public IPv4, Elastic IP, S3, Bedrock, and support-plan resources;
- a monthly AWS Budget with email alerts (budgets alert but do not cap spend);
- a named owner and a specific stop/terminate time after the demonstration;
- explicit approval for the estimate and any residual EBS/public IPv4 cost.

For this demonstration, use one USD 15 deployment budget with actual-cost alerts at
USD 5, USD 10, and USD 15. Filter by an activated `Project=TenderGuard-Africa` cost
allocation tag and tag every new EC2/EBS/network resource consistently. Tags and cost
data can take time to become visible; verify the filter before relying on it. If a
project-specific filter is unavailable, disclose that limitation instead of presenting
an account-wide alert as exact incremental project spend. The recipient enters their
notification address privately in AWS. Do not commit the email, budget output, or
billing details. No budget is created by these local preparation scripts.

AWS documents credit inspection in the Billing console and notes that credits have
eligibility and expiration rules:
<https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/useconsolidatedbilling-credits.html>.

## Sizing and cost guardrail

Compare these candidates using the authenticated regional preflight:

| Candidate | CPU/RAM | Sustained CPU consideration |
| --- | --- | --- |
| `m7i-flex.large` | 2 vCPU / 8 GiB | 40% baseline per vCPU; sustained high utilization can reduce burst throughput |
| `t3.large` | 2 vCPU / 8 GiB | 30% baseline per vCPU; use `standard` credits to avoid Unlimited surplus charges |

Neither an eligible instance label nor promotional credits guarantee zero charges.
The loaded local model used about 1.9 GB before application and PDF overhead. Use
40 GiB encrypted gp3 and test actual CPU inference latency on the approved instance.

Run in an authenticated AWS CloudShell or configured temporary AWS CLI session:

```bash
python3 deploy/aws/preflight.py
```

The script reads identity, region offerings, instance specifications/Free Tier labels,
existing instance inventory, and AWS Pricing API Linux On-Demand quotes. It never
creates resources, exports credentials, queries paid Cost Explorer APIs, or treats
discovered IAM access as organizer authorization. Billing credits and current charges
must still be inspected in the console. Do not commit the output.

Compute estimate = approved runtime hours × Stockholm hourly instance rate. Add the
public IPv4 charge (currently USD 0.005/hour), 40 × the regional gp3 GB-month price
prorated over retention, transfer, tax, and any snapshots. Credit coverage must be
verified separately for each charge category. Budget alerts do not cap spending.

Public AWS Pricing API quotes inspected on 16 November 2026 were USD 0.10175/hour
for `m7i-flex.large`, USD 0.08640/hour for `t3.large`, and USD 0.0836/GB-month for
Stockholm gp3. With one public IPv4 and 40 GiB gp3 prorated for eight hours, the
planning totals are about USD 0.89 and USD 0.77 respectively, before transfer, tax,
snapshots, other usage, and any T3 Unlimited surplus charges. Retained 40 GiB gp3
costs about USD 3.34/month after compute stops. Requery live prices before launch.

- <https://aws.amazon.com/ec2/instance-types/t3/>
- <https://aws.amazon.com/vpc/pricing/>
- <https://aws.amazon.com/ebs/pricing/>
- <https://calculator.aws/>
- <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/burstable-credits-baseline-concepts.html>
- <https://aws.amazon.com/ec2/instance-types/m7i/>

## No-purchase DNS option

An operator-controlled domain is preferred. If none is available, `sslip.io`/`nip.io`
can provide a hostname encoding the instance's public IPv4, such as
`tenderguard.PUBLIC-IP.sslip.io` with the actual numeric address substituted. This
introduces an external DNS dependency, shared-domain certificate rate limits, and a
hostname change if the public IP changes. The service does not reserve ownership of
the label for you. Verify DNS resolution and Caddy's publicly trusted certificate
before publishing the URL. See <https://sslip.io/> and
<https://caddyserver.com/docs/automatic-https>.

Never serve dashboard login over public HTTP. If DNS/TLS cannot be verified, retain a
private SSH/SSM access path and keep the local Windows deployment as the fallback.

## Approved deployment sequence

These commands are instructions only; they have not been run against an AWS account.

1. Launch only the separately approved `TenderGuard-Africa` instance: Ubuntu 24.04
   x86_64, approved 2-vCPU/8-GiB type, 40 GiB encrypted gp3, IMDSv2 required, detailed
   monitoring off, instance-initiated shutdown behavior `stop`, and appropriate
   termination protection. Set T3 credit specification `standard` if using T3.
2. Attach a security group allowing TCP 80/443 from the internet and TCP 22 only from
   the operator's current `/32` IP. Do not expose 8000 or 11434.
3. Point the approved DNS name at the instance's public address. A public IPv4 incurs
   charges; an Elastic IP can continue charging when detached or the instance stops.
4. On that **new instance only**, obtain the repository and check out `nairobi-demo-prep`.
   Run the guarded installer with the actual newly approved instance ID. It verifies
   IMDSv2 identity and Ubuntu/architecture before installing Docker from Docker's
   official Ubuntu repository. It does not modify local Windows configuration:

```bash
sudo bash deploy/aws/bootstrap_ubuntu.sh --expected-instance-id i-NEW_APPROVED_ID --confirm-dedicated-host
```

5. Prepare private credentials with an interactive password prompt. Do not put the
   password in shell arguments, shell history, Git, screenshots, or logs. Existing
   `.env` files are never overwritten:

```bash
python3 deploy/aws/configure_env.py --domain ACTUAL_DNS_HOSTNAME --email YOUR_TLS_NOTIFICATION_EMAIL
```

6. Validate without printing interpolated secrets, then build/pull/start:

```bash
cd deploy/aws
sudo docker compose --env-file .env -f compose.aws.yaml config --quiet
sudo docker compose --env-file .env -f compose.aws.yaml build
sudo docker compose --env-file .env -f compose.aws.yaml up -d --wait --wait-timeout 120 ollama
sudo docker compose --env-file .env -f compose.aws.yaml exec ollama ollama pull qwen3:1.7b
sudo docker compose --env-file .env -f compose.aws.yaml up -d
sudo docker compose --env-file .env -f compose.aws.yaml ps
```

7. Verify the HTTPS URL, authentication failure and success, uploads, real evaluation,
   citations, `AWAITING_HUMAN_REVIEW`, null award, authorized CLI report, and download.
   Do not call the deployment successful until this live checklist passes.

From the prepared Windows Python environment, run the HTTPS verification command:

```powershell
.\.venv\Scripts\python.exe -m deploy.aws.verify_cloud --url https://ACTUAL_DNS_HOSTNAME
```

It checks certificate validation, login success/failure, cookie flags, three PDF
uploads, real evaluation, expected MCP tools, tax-clearance evidence, citations,
absence of deadline scoring, and human-review invariants. It prints the new workspace
ID without printing report content or credentials. In a separate administrative SSH
or SSM session on the new instance, authorize the draft only after reviewing findings:

```bash
sudo docker compose --env-file .env -f compose.aws.yaml exec tenderguard \
  python -m app.agent.approve_documents --workspace EVL-WORKSPACE_ID --approved-by 'Named Reviewer'
```

Then verify authenticated report download using the same workspace:

```powershell
.\.venv\Scripts\python.exe -m deploy.aws.verify_cloud --url https://ACTUAL_DNS_HOSTNAME --workspace EVL-WORKSPACE_ID --report-only
```

These are separate administrator actions; the name remains a recorded authorization
field, not independently verified identity. The browser has no approval capability.

## CPU, logs, and diagnostics

The cloud-only Compose file keeps one Qwen model loaded, serializes model inference,
bounds the Ollama queue, configures an 8192-token context, and rotates local container
logs at 10 MB × 3 per service. These settings do not change Windows/local Compose.
Larger context increases RAM use; verify `sudo docker stats --no-stream` and
`sudo docker compose --env-file .env -f compose.aws.yaml exec ollama ollama ps` after
the real evaluation. FastAPI/Pydantic validation and the existing model timeouts stay
enabled. Diagnose any invalid structured response rather than accepting invalid data.

## Stop, backup, and teardown

Before the event, make an encrypted EBS snapshot or export the named volumes to an
encrypted, access-controlled backup. Uploaded bids and reports may be sensitive; do
not put backup archives in public S3 or Git.

To stop only the application while retaining data:

```bash
sudo docker compose --env-file .env -f compose.aws.yaml down
```

Restart with the same `.env`, project name, and volumes using `up -d`. Never use
`down --volumes` for ordinary shutdown. For disaster recovery, stop writers, preserve
encrypted EBS or separately export the document/report volumes into an encrypted
private backup, restore them on another approved host under the same volume names,
then rerun health, authentication, and report checks. Keep `.env` outside Git and
transfer it only over a protected administrative connection.

The guarded installer creates a persistent `tenderguard-demo-stop.timer`, calculated
as EC2's IMDSv2 `pendingTime` plus exactly eight hours. The cutoff is expressed in UTC
(EAT is UTC+3), starts at launch rather than installation completion, and survives
ordinary reboots. Verify it on the **new instance only**:

```bash
sudo systemctl list-timers tenderguard-demo-stop.timer --no-pager
sudo systemctl cat tenderguard-demo-stop.timer
```

Configure EC2's instance-initiated shutdown behavior as `stop`. This timer stops the
host; it does not delete retained EBS data or guarantee that account credits cover the
run. Do not restart the host after the approved deadline without an explicitly approved
new operating window and corresponding timer update.

Stopping an EC2 instance ends instance compute charges, but EBS and some public IPv4
resources can continue to accrue. The account owner must inspect and explicitly
terminate/delete the approved demo resources after backup. Never automate deletion of
unrelated account resources.
