#!/usr/bin/env bash
# Instalează TITAN Mobile (control casă + consum) pe Raspberry Pi OS.
# Rulează pe Pi:   bash deploy/install-pi.sh
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

echo "==> Pachete de sistem"
sudo apt-get update -y
sudo apt-get install -y python3 python3-venv python3-pip git curl

echo "==> Mediu Python"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements-pi.txt

mkdir -p data

if [ ! -f .env ]; then
  echo "==> Creez .env cu un cod de acces generat"
  cp .env.example .env
  TOKEN="$(python3 -c 'import secrets;print(secrets.token_urlsafe(32))')"
  sed -i "s|^TITAN_MOBILE_ACCESS_TOKEN=.*|TITAN_MOBILE_ACCESS_TOKEN=${TOKEN}|" .env
  chmod 600 .env
fi

if [ ! -f smart_home.json ]; then
  cp smart_home.plugs.example.json smart_home.json
  chmod 600 smart_home.json
  echo "!! Editează smart_home.json: device_id, ip, local_key pentru fiecare bec/priză."
fi

echo "==> Serviciu systemd"
sed -e "s|__USER__|$(id -un)|g" -e "s|__DIR__|${DIR}|g" deploy/titan-mobile.service \
  | sudo tee /etc/systemd/system/titan-mobile.service >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable --now titan-mobile.service

echo "==> Tailscale (acces privat de pe telefon, fără port forwarding)"
if ! command -v tailscale >/dev/null; then
  curl -fsSL https://tailscale.com/install.sh | sh
fi
sudo tailscale up || true
sudo tailscale serve --bg 8787 || true

echo
echo "Gata. Starea serviciului:  systemctl status titan-mobile"
echo "Adresa (de pe telefon, cu Tailscale pornit):  tailscale serve status"
echo "Codul de conectare al telefonului:"
grep '^TITAN_MOBILE_ACCESS_TOKEN=' .env | cut -d= -f2
