# AWS deployment package (not provisioned)

This package is ready for an approved EC2 deployment, but it deliberately creates no
AWS resources. The account's displayed USD 44.61 is usage, not verified credit. Do
not launch the stack until the AWS Billing **Credits** page shows an unexpired amount
remaining, the target region and existing resources are reviewed, and the account
owner explicitly approves the estimated incremental cost.

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

AWS documents credit inspection in the Billing console and notes that credits have
eligibility and expiration rules:
<https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/useconsolidatedbilling-credits.html>.

## Sizing and cost guardrail

Use one `t3.large` (2 vCPU, 8 GiB) with 40 GiB gp3 for the CPU-only Qwen3 1.7B demo.
The locally verified loaded model used about 1.9 GB before the application, Docker,
and PDF workflow overhead. A `t3.medium` has only 4 GiB and leaves too little demo
headroom. Keep T3 CPU credits in `standard` mode so sustained inference cannot create
Unlimited-mode surplus-credit charges.

For us-east-1 list prices used only as a planning example: t3.large is USD 0.0835/hour,
public IPv4 is USD 0.005/hour, and 40 GiB gp3 is about USD 3.20/month. A 730-hour month
is therefore roughly USD 67.81 before data transfer, tax, snapshots, support, or price
changes. An eight-hour event is roughly USD 0.71 for compute and IPv4, while EBS keeps
accruing until deleted. Confirm the chosen region's live prices in the AWS Pricing
Calculator before approval:

- <https://aws.amazon.com/ec2/instance-types/t3/>
- <https://aws.amazon.com/vpc/pricing/>
- <https://aws.amazon.com/ebs/pricing/>
- <https://calculator.aws/>

## Approved deployment sequence

These commands are instructions only; they have not been run against an AWS account.

1. Launch Ubuntu LTS on an approved `t3.large` with 40 GiB gp3, IMDSv2 required,
   encrypted EBS, detailed monitoring off, and T3 credit specification `standard`.
2. Attach a security group allowing TCP 80/443 from the internet and TCP 22 only from
   the operator's current `/32` IP. Do not expose 8000 or 11434.
3. Point the approved DNS name at the instance's public address. A public IPv4 incurs
   charges; an Elastic IP can continue charging when detached or the instance stops.
4. Install Docker Engine and the Compose plugin from Docker's official Ubuntu
   repository, then clone the repository and check out `nairobi-demo-prep`.
5. In `deploy/aws`, prepare secrets without echoing them:

```bash
cp .env.aws.example .env
api_key="$(openssl rand -hex 32)"
read -rsp 'Dashboard password (12+ characters): ' dashboard_password; echo
sed -i "s/^TENDERGUARD_API_KEY=.*/TENDERGUARD_API_KEY=${api_key}/" .env
sed -i "s/^TENDERGUARD_DASHBOARD_PASSWORD=.*/TENDERGUARD_DASHBOARD_PASSWORD=${dashboard_password}/" .env
unset api_key dashboard_password
chmod 600 .env
```

6. Replace the example domain/email in `.env`, then validate and start:

```bash
docker compose --env-file .env -f compose.aws.yaml config --quiet
docker compose --env-file .env -f compose.aws.yaml build
docker compose --env-file .env -f compose.aws.yaml up -d ollama
docker compose --env-file .env -f compose.aws.yaml exec ollama ollama pull qwen3:1.7b
docker compose --env-file .env -f compose.aws.yaml up -d
docker compose --env-file .env -f compose.aws.yaml ps
```

7. Verify the HTTPS URL, authentication failure and success, uploads, real evaluation,
   citations, `AWAITING_HUMAN_REVIEW`, null award, authorized CLI report, and download.
   Do not call the deployment successful until this live checklist passes.

## Stop, backup, and teardown

Before the event, make an encrypted EBS snapshot or export the named volumes to an
encrypted, access-controlled backup. Uploaded bids and reports may be sensitive; do
not put backup archives in public S3 or Git.

To stop only the application while retaining data:

```bash
docker compose --env-file .env -f compose.aws.yaml down
```

Stopping an EC2 instance ends instance compute charges, but EBS and some public IPv4
resources can continue to accrue. The account owner must inspect and explicitly
terminate/delete the approved demo resources after backup. Never automate deletion of
unrelated account resources.
