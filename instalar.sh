#!/usr/bin/env bash
# Instalador del sistema de contenido (Mac Intel o Apple, y Linux). Uso:
#   curl -fsSL https://raw.githubusercontent.com/freneticotrouw/sistema-contenido-gemini/main/instalar.sh | bash
# No necesita Homebrew: en Mac baja cada programa de su página oficial.
set -e
REPO="freneticotrouw/sistema-contenido-gemini"
DESTINO="$HOME/mi-contenido"
LOCAL="$HOME/.local"
NODE_V="v22.11.0"
PY_V="3.12.10"
mkdir -p "$LOCAL/bin"
export PATH="$LOCAL/bin:$LOCAL/node/bin:/Library/Frameworks/Python.framework/Versions/3.12/bin:$PATH"
falta() { ! command -v "$1" >/dev/null 2>&1; }
py_ok() { command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; sys.exit(sys.version_info < (3,10))' 2>/dev/null; }

echo "1/4 Programas necesarios..."
if [ "$(uname)" = "Darwin" ]; then
  ARCH="$(uname -m)"; [ "$ARCH" = "arm64" ] || ARCH="x64"
  MACOS="$(sw_vers -productVersion | cut -d. -f1)"
  [ "$MACOS" -lt 11 ] && NODE_V="v20.18.0"   # macOS 10.15 o anterior
  if ! xcode-select -p >/dev/null 2>&1; then
    echo "   Se abrirá una ventana para instalar las herramientas de Apple (incluye git)."
    echo ""
    echo "   >>> IMPORTANTE: cuando termine esa ventana, VUELVE A PEGAR el comando de instalación. <<<"
    echo "   (Esta primera vuelta solo instala las herramientas de Apple; el resto va en la segunda.)"
    xcode-select --install || true
    exit 0
  fi
  if ! py_ok; then
    echo "   Instalando Python $PY_V (te pedirá la contraseña del Mac)..."
    curl -fsSL "https://www.python.org/ftp/python/$PY_V/python-$PY_V-macos11.pkg" -o /tmp/python.pkg
    sudo installer -pkg /tmp/python.pkg -target / < /dev/tty
  fi
  if falta node; then
    echo "   Instalando Node..."
    curl -fsSL "https://nodejs.org/dist/$NODE_V/node-$NODE_V-darwin-$ARCH.tar.gz" -o /tmp/node.tgz
    rm -rf "$LOCAL/node" && mkdir -p "$LOCAL/node"
    tar -xzf /tmp/node.tgz -C "$LOCAL/node" --strip-components 1
  fi
  if falta ffmpeg || falta ffprobe; then
    echo "   Instalando ffmpeg..."
    [ "$ARCH" = "arm64" ] && MR="arm64" || MR="amd64"
    for p in ffmpeg ffprobe; do
      ok=""
      for url in "https://ffmpeg.martin-riedl.de/redirect/latest/macos/$MR/release/$p.zip" \
                 "https://evermeet.cx/ffmpeg/getrelease/$p/zip"; do
        if curl -fsSL "$url" -o "/tmp/$p.zip" 2>/dev/null && unzip -o -q "/tmp/$p.zip" -d "$LOCAL/bin" 2>/dev/null; then
          chmod +x "$LOCAL/bin/$p"; xattr -d com.apple.quarantine "$LOCAL/bin/$p" 2>/dev/null || true
          "$LOCAL/bin/$p" -version >/dev/null 2>&1 && ok=1 && break
        fi
      done
      [ -n "$ok" ] || echo "   (no se pudo bajar $p directo; se intenta por pip más abajo)"
    done
  fi
else
  sudo apt-get update -y && sudo apt-get install -y python3 python3-pip python3-venv ffmpeg nodejs npm git unzip
fi

echo "2/4 Herramientas de video y transcripción (gratis, locales)..."
python3 -m pip install --user --upgrade --quiet yt-dlp faster-whisper \
  || python3 -m pip install --user --break-system-packages --upgrade --quiet yt-dlp faster-whisper

if falta ffmpeg || falta ffprobe; then
  python3 -m pip install --user --upgrade --quiet static-ffmpeg && python3 - <<'PY'
import os, shutil, static_ffmpeg.run as r
ff, fp = r.get_or_fetch_platform_executables_else_raise()
dst = os.path.expanduser("~/.local/bin")
for f in (ff, fp):
    shutil.copy(f, os.path.join(dst, os.path.basename(f))); os.chmod(os.path.join(dst, os.path.basename(f)), 0o755)
print("   ffmpeg listo (vía pip)")
PY
fi

echo "3/4 Gemini CLI..."
if falta gemini; then
  if [ -d "$LOCAL/node" ]; then npm install -g --prefix "$LOCAL/node" @google/gemini-cli
  else npm install -g @google/gemini-cli || sudo npm install -g @google/gemini-cli; fi
fi

echo "4/4 Carpeta del sistema..."
if [ ! -d "$DESTINO" ]; then
  tmp="$(mktemp -d)"
  curl -fsSL "https://github.com/$REPO/archive/refs/heads/main.zip" -o "$tmp/s.zip"
  unzip -q "$tmp/s.zip" -d "$tmp" && mv "$tmp/sistema-contenido-gemini-main" "$DESTINO"
else
  echo "   Ya existe $DESTINO (no se toca)."
fi

# Rutas y atajo 'mi-contenido' para las próximas veces
PYBIN="$(python3 -c 'import site,os; print(os.path.join(site.getuserbase(),"bin"))')"
for rc in "$HOME/.zshrc" "$HOME/.bashrc"; do
  [ "$rc" = "$HOME/.bashrc" ] && [ ! -f "$rc" ] && continue
  touch "$rc"
  grep -q "# sistema-contenido" "$rc" || cat >> "$rc" <<EOF

# sistema-contenido
export PATH="$LOCAL/bin:$LOCAL/node/bin:$PYBIN:/Library/Frameworks/Python.framework/Versions/3.12/bin:\$PATH"
alias mi-contenido='cd "$DESTINO" && gemini'
EOF
done
export PATH="$PYBIN:$PATH"

echo
echo "Listo. Inicia sesión con tu cuenta de Google (la de tu suscripción), no con API key."
echo "Luego escribe /empezar. La próxima vez abre la Terminal y escribe: mi-contenido"
cd "$DESTINO" && exec gemini < /dev/tty
