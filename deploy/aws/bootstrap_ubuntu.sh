#!/usr/bin/env bash
# Run ONLY on the newly approved, dedicated TenderGuard EC2 instance.
set -euo pipefail
set +x

if [[ "${1:-}" != "--expected-instance-id" || ! "${2:-}" =~ ^i-[a-f0-9]{8,17}$ || "${3:-}" != "--confirm-dedicated-host" ]]; then
  printf '%s\n' 'Usage: sudo bash bootstrap_ubuntu.sh --expected-instance-id i-NEW_INSTANCE --confirm-dedicated-host' >&2
  exit 2
fi
expected_instance="$2"
[[ "$expected_instance" != i-0b8d60a2621893ac1 ]] || {
  printf '%s\n' 'Protected host mwalimulens-demo must never be modified.' >&2; exit 2;
}
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
[[ "$EUID" -eq 0 ]] || { printf '%s\n' 'Run with sudo on the approved EC2 instance.' >&2; exit 2; }
source /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 24.04 && "$(uname -m)" == x86_64 ]] || {
  printf '%s\n' 'This installer requires Ubuntu 24.04 x86_64.' >&2; exit 2;
}
token="$(curl --fail --silent --show-error --max-time 5 --noproxy '*' -X PUT \
  -H 'X-aws-ec2-metadata-token-ttl-seconds: 60' http://169.254.169.254/latest/api/token)"
actual_instance="$(curl --fail --silent --show-error --max-time 5 --noproxy '*' \
  -H "X-aws-ec2-metadata-token: $token" http://169.254.169.254/latest/meta-data/instance-id)"
[[ "$actual_instance" == "$expected_instance" ]] || {
  printf '%s\n' 'EC2 identity mismatch. No packages were installed.' >&2; exit 2;
}
command -v python3 >/dev/null || { printf '%s\n' 'Ubuntu Python 3 is required.' >&2; exit 2; }
identity_document="$(curl --fail --silent --show-error --max-time 5 --noproxy '*' \
  -H "X-aws-ec2-metadata-token: $token" http://169.254.169.254/latest/dynamic/instance-identity/document)"
unset token
stop_at="$(python3 "$script_dir/shutdown_deadline.py" --instance-id "$expected_instance" <<< "$identity_document")"
unset identity_document

# The approved eight-hour limit starts at EC2 launch, not at installation completion.
# Persistent calendar timers also fire after a reboot if the cutoff was missed.
install -m 0644 /dev/stdin /etc/systemd/system/tenderguard-demo-stop.service <<'SERVICE'
[Unit]
Description=Stop the approved TenderGuard demo host at its spending cutoff

[Service]
Type=oneshot
ExecStart=/usr/sbin/shutdown -h now
SERVICE
install -m 0644 /dev/stdin /etc/systemd/system/tenderguard-demo-stop.timer <<TIMER
[Unit]
Description=Eight-hour TenderGuard demonstration shutdown

[Timer]
OnCalendar=${stop_at}
Persistent=true
AccuracySec=1s
Unit=tenderguard-demo-stop.service

[Install]
WantedBy=timers.target
TIMER
systemctl daemon-reload
systemctl enable --now tenderguard-demo-stop.timer
systemctl list-timers tenderguard-demo-stop.timer --no-pager
if [[ "$(date -u -d "$stop_at" +%s)" -le "$(date -u +%s)" ]]; then
  printf '%s\n' 'The approved eight-hour launch window has expired. Installation is blocked.' >&2
  exit 2
fi

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y ca-certificates curl git python3
install -m 0755 -d /etc/apt/keyrings
if ! command -v docker >/dev/null 2>&1; then
  curl --fail --silent --show-error https://download.docker.com/linux/ubuntu/gpg \
    -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  printf '%s\n' \
    'Types: deb' \
    'URIs: https://download.docker.com/linux/ubuntu' \
    'Suites: noble' \
    'Components: stable' \
    'Architectures: amd64' \
    'Signed-By: /etc/apt/keyrings/docker.asc' > /etc/apt/sources.list.d/docker.sources
  apt-get update
  DEBIAN_FRONTEND=noninteractive apt-get install -y \
    docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
systemctl enable --now docker
docker version --format '{{.Server.Version}}'
docker compose version
printf '%s\n' 'Docker is ready. Continue with the approved repository checkout and private .env setup.'
