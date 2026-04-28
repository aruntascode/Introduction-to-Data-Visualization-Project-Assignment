#!/bin/zsh

cd "$(dirname "$0")" || exit 1

echo "[1/4] Python sanal ortamı kontrol ediliyor..."
if [ ! -x ".venv/bin/python" ]; then
    python3 -m venv .venv || exit 1
fi

echo "[2/4] Sanal ortam açılıyor..."
source .venv/bin/activate || exit 1

echo "[3/4] Paketler kontrol ediliyor..."
python -m pip install --upgrade pip
pip install -r requirements.txt || exit 1

echo "[4/4] Akıllı Öğretmen Asistanı başlatılıyor..."
python main.pyw
