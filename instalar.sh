#!/usr/bin/env bash
# Instalador del sistema de contenido (Mac/Linux). Uso:
#   curl -fsSL https://raw.githubusercontent.com/freneticotrouw/sistema-contenido-gemini/main/instalar.sh | bash
set -e
REPO="freneticotrouw/sistema-contenido-gemini"
DESTINO="$HOME/mi-contenido"
falta() { ! command -v "$1" >/dev/null 2>&1; }

echo "1/4 Programas necesarios..."
if [ "$(uname)" = "Darwin" ]; then
  falta brew && /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  for p in python ffmpeg node git; do falta "$p" && brew install "$p"; done
  falta python3 && brew install python
else
  sudo apt-get update -y && sudo apt-get install -y python3 python3-pip ffmpeg nodejs npm git unzip
fi

echo "2/4 Herramientas de video y transcripción (gratis, locales)..."
python3 -m pip install --user --upgrade --quiet yt-dlp faster-whisper || python3 -m pip install --user --break-system-packages --upgrade yt-dlp faster-whisper

echo "3/4 Gemini CLI..."
falta gemini && npm install -g @google/gemini-cli

echo "4/4 Carpeta del sistema..."
if [ ! -d "$DESTINO" ]; then
  tmp="$(mktemp -d)"
  curl -fsSL "https://github.com/$REPO/archive/refs/heads/main.zip" -o "$tmp/s.zip"
  unzip -q "$tmp/s.zip" -d "$tmp" && mv "$tmp/sistema-contenido-gemini-main" "$DESTINO"
else
  echo "   Ya existe $DESTINO (no se toca)."
fi

for rc in "$HOME/.zshrc" "$HOME/.bashrc"; do
  [ -f "$rc" ] && ! grep -q "alias mi-contenido" "$rc" && echo "alias mi-contenido='cd \"$DESTINO\" && gemini'" >> "$rc"
done

echo
echo "Listo. Inicia sesión con tu cuenta de Google (la de tu suscripción), no con API key."
echo "Luego escribe /empezar. La próxima vez basta con escribir: mi-contenido"
cd "$DESTINO" && exec gemini < /dev/tty
