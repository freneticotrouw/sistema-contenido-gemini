"""cs: la única puerta a los datos del sistema de contenido.

Uso: python -m cs <comando> [opciones]   (python -m cs -h para la lista)
"""
import argparse
import csv
import datetime as dt
import glob
import http.server
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import urllib.request
import zipfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(RAIZ, "datos")
CUENTAS = os.path.join(RAIZ, "cuentas")
WORK = os.path.join(RAIZ, "workspace")
PLANT = os.path.join(RAIZ, "plantillas")
DB = os.path.join(DATOS, "contenidos.json")
BANDEJA = os.path.join(DATOS, "acciones.json")
REPO_PLANTILLA = "freneticotrouw/sistema-contenido-gemini"  # se ajusta al publicar

PASOS = ["idea", "guion", "grabado", "en_carpeta", "cortes", "imagenes", "video", "publicacion"]
APROBABLES = {"idea", "guion", "cortes", "imagenes", "video", "publicacion"}
EDICION = ["cortes", "imagenes", "video"]
VIDEO_EXT = (".mp4", ".mov", ".m4v", ".webm")
IMG_EXT = (".png", ".jpg", ".jpeg", ".webp")


# ---------- utilidades ----------
def leer(ruta, defecto):
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return defecto


def escribir(ruta, datos):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    os.replace(tmp, ruta)


def ahora():
    return dt.datetime.now().isoformat(timespec="seconds")


def slug(texto):
    t = re.sub(r"[^a-z0-9]+", "-", texto.lower()).strip("-")
    return t[:40] or "contenido"


def contenidos():
    return leer(DB, [])


def buscar(cid):
    for c in contenidos():
        if c["id"] == cid:
            return c
    sys.exit(f"No existe el contenido '{cid}'. Mira: python -m cs lista")


def guardar(c):
    todos = [x for x in contenidos() if x["id"] != c["id"]] + [c]
    escribir(DB, sorted(todos, key=lambda x: x["creado"]))


def siguiente(c):
    for p in PASOS:
        if p not in c["hecho"]:
            return p
    return None


def cuenta_dir(cuenta):
    d = os.path.join(CUENTAS, cuenta)
    if not os.path.isdir(d):
        sys.exit(f"No existe la cuenta '{cuenta}'. Crea una con /empezar")
    return d


def lista_cuentas():
    if not os.path.isdir(CUENTAS):
        return []
    return sorted(n for n in os.listdir(CUENTAS) if os.path.isdir(os.path.join(CUENTAS, n)))


def tiene(prog):
    return shutil.which(prog) is not None


# ---------- cuentas ----------
def cmd_cuenta_nueva(a):
    d = os.path.join(CUENTAS, a.cuenta)
    os.makedirs(os.path.join(d, "informes"), exist_ok=True)
    redes = {}
    if a.instagram:
        redes["instagram"] = a.instagram.lstrip("@")
    if a.tiktok:
        redes["tiktok"] = a.tiktok.lstrip("@")
    for nombre in os.listdir(PLANT):
        dest = os.path.join(d, nombre)
        if not os.path.exists(dest):
            shutil.copy(os.path.join(PLANT, nombre), dest)
    perfil = os.path.join(d, "perfil.md")
    with open(perfil, encoding="utf-8") as f:
        txt = f.read()
    txt = txt.replace("{nombre}", a.nombre or a.cuenta).replace(
        "{redes}", ", ".join(f"{k}: @{v}" for k, v in redes.items()) or "-")
    with open(perfil, "w", encoding="utf-8") as f:
        f.write(txt)
    cfg = leer(os.path.join(d, "cuenta.json"), {})
    cfg.update({"nombre": a.nombre or a.cuenta, "redes": redes, "referentes": cfg.get("referentes", [])})
    escribir(os.path.join(d, "cuenta.json"), cfg)
    print(f"Cuenta '{a.cuenta}' lista en cuentas/{a.cuenta}/")


def cmd_referente(a):
    d = cuenta_dir(a.cuenta)
    cfg = leer(os.path.join(d, "cuenta.json"), {})
    ref = {"red": a.red, "usuario": a.usuario.lstrip("@")}
    if ref not in cfg.setdefault("referentes", []):
        cfg["referentes"].append(ref)
    escribir(os.path.join(d, "cuenta.json"), cfg)
    print(f"Referente @{ref['usuario']} ({a.red}) agregado.")


def cmd_cuentas(a):
    for n in lista_cuentas():
        cfg = leer(os.path.join(CUENTAS, n, "cuenta.json"), None)
        if cfg is not None:
            redes = ", ".join(f"{k} @{v}" for k, v in cfg.get("redes", {}).items())
            print(f"{n}: {cfg.get('nombre', n)} ({redes})")


# ---------- descarga y análisis ----------
def url_perfil(red, usuario):
    return {"instagram": f"https://www.instagram.com/{usuario}/reels/",
            "tiktok": f"https://www.tiktok.com/@{usuario}"}[red]


def ytdlp(red, usuario, carpeta, n, solo_datos, cookies):
    os.makedirs(carpeta, exist_ok=True)
    cmd = [sys.executable, "-m", "yt_dlp"] if not tiene("yt-dlp") else ["yt-dlp"]
    cmd += ["--playlist-end", str(n), "--write-info-json", "--no-overwrites", "--ignore-errors",
            "-o", os.path.join(carpeta, "%(upload_date)s_%(id)s.%(ext)s"),
            "-f", "mp4/best[height<=1080]/best"]
    if solo_datos:
        cmd.append("--skip-download")
    if cookies:
        cmd += ["--cookies-from-browser", cookies]
    cmd.append(url_perfil(red, usuario))
    print("→", red, "@" + usuario, "(con sesión de " + cookies + ")" if cookies else "")
    subprocess.run(cmd)
    return len(glob.glob(os.path.join(carpeta, "*.info.json")))


def cmd_descargar(a):
    d = cuenta_dir(a.cuenta)
    cfg = leer(os.path.join(d, "cuenta.json"), {})
    objetivos = [{"red": r, "usuario": u} for r, u in cfg.get("redes", {}).items()]
    if a.referentes:
        objetivos = cfg.get("referentes", [])
    if not objetivos:
        sys.exit("No hay cuentas para descargar. Agrega redes con cuenta-nueva o referentes con referente.")
    for o in objetivos:
        tipo = "referentes" if a.referentes else "propia"
        carpeta = os.path.join(d, "muestras", tipo, f"{o['red']}_{o['usuario']}")
        antes = len(glob.glob(os.path.join(carpeta, "*.info.json")))
        total = ytdlp(o["red"], o["usuario"], carpeta, a.n, a.solo_datos, None)
        if total == antes and total == 0:
            total = ytdlp(o["red"], o["usuario"], carpeta, a.n, a.solo_datos, a.navegador)
        print(f"   {total} videos con datos en {os.path.relpath(carpeta, RAIZ)}")
        if total == 0:
            print("   ⚠ No se pudo leer. Abre el perfil en tu navegador con la sesión iniciada y vuelve a intentar,"
                  " o pide a Gemini que lo lea con Gemini en Chrome (solo lectura).")
    resumen(a.cuenta)


def resumen(cuenta):
    d = cuenta_dir(cuenta)
    filas = []
    for info in glob.glob(os.path.join(d, "muestras", "*", "*", "*.info.json")):
        j = leer(info, {})
        base = info[: -len(".info.json")]
        video = next((base + e for e in VIDEO_EXT if os.path.exists(base + e)), "")
        txt = base + ".txt"
        filas.append({
            "origen": os.path.relpath(os.path.dirname(info), os.path.join(d, "muestras")),
            "fecha": j.get("upload_date", ""), "id": j.get("id", ""),
            "vistas": j.get("view_count") or "", "likes": j.get("like_count") or "",
            "comentarios": j.get("comment_count") or "", "duracion": j.get("duration") or "",
            "copy": (j.get("description") or j.get("title") or "").replace("\n", " ")[:300],
            "url": j.get("webpage_url", ""),
            "video": os.path.relpath(video, RAIZ) if video else "",
            "transcripcion": os.path.relpath(txt, RAIZ) if os.path.exists(txt) else "",
        })
    filas.sort(key=lambda f: (f["origen"], f["fecha"]), reverse=True)
    ruta = os.path.join(d, "muestras", "resumen.csv")
    if filas:
        with open(ruta, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(filas[0]))
            w.writeheader()
            w.writerows(filas)
    return filas


def cmd_transcribir(a):
    d = cuenta_dir(a.cuenta)
    videos = [v for v in glob.glob(os.path.join(d, "muestras", "*", "*", "*"))
              if v.lower().endswith(VIDEO_EXT) and not os.path.exists(os.path.splitext(v)[0] + ".txt")]
    if not videos:
        print("No hay videos nuevos para transcribir.")
        return
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("Falta Whisper: pip install faster-whisper")
    modelo = WhisperModel(a.modelo, device="auto", compute_type="int8")
    for i, v in enumerate(videos, 1):
        segs, _ = modelo.transcribe(v, language=a.idioma or None, vad_filter=True)
        texto = " ".join(s.text.strip() for s in segs)
        with open(os.path.splitext(v)[0] + ".txt", "w", encoding="utf-8") as f:
            f.write(texto)
        print(f"[{i}/{len(videos)}] {os.path.basename(v)}")
    resumen(a.cuenta)


def cmd_muestras(a):
    filas = resumen(a.cuenta)
    if not filas:
        print("Sin muestras. Corre: python -m cs descargar", a.cuenta)
        return
    for f in filas:
        print(f"{f['origen']} | {f['fecha']} | vistas {f['vistas']} | likes {f['likes']} | "
              f"{f['duracion']}s | {f['copy'][:90]}\n   video: {f['video'] or '-'} | texto: {f['transcripcion'] or '-'}")
    print(f"\nTotal: {len(filas)}. Tabla completa: cuentas/{a.cuenta}/muestras/resumen.csv")


# ---------- contenidos ----------
def cmd_nuevo(a):
    cuenta_dir(a.cuenta)
    cid = f"{dt.date.today():%Y%m%d}-{slug(a.titulo)}"
    n, base = 2, cid
    while any(c["id"] == cid for c in contenidos()):
        cid, n = f"{base}-{n}", n + 1
    carpeta = os.path.join(WORK, a.cuenta, cid)
    for sub in ("investigacion", "guion", "assets", "edicion", "publicacion"):
        os.makedirs(os.path.join(carpeta, sub), exist_ok=True)
    c = {"id": cid, "cuenta": a.cuenta, "titulo": a.titulo, "formato": a.formato,
         "carpeta": os.path.relpath(carpeta, RAIZ), "hecho": {}, "notas": [], "creado": ahora()}
    guardar(c)
    print(f"Creado {cid} en {c['carpeta']}")


def cmd_lista(a):
    for c in contenidos():
        if a.cuenta and c["cuenta"] != a.cuenta:
            continue
        print(f"{c['id']} [{c['cuenta']}] {c['titulo']} → falta: {siguiente(c) or 'terminado'}")


def cmd_ver(a):
    c = buscar(a.id)
    print(json.dumps(c, ensure_ascii=False, indent=2))
    print("Siguiente paso:", siguiente(c) or "terminado")


def marcar(c, paso, extra=None):
    c["hecho"][paso] = {"fecha": ahora(), **(extra or {})}
    guardar(c)


def cmd_aprobar(a):
    if a.paso not in APROBABLES:
        sys.exit(f"Pasos que se aprueban: {', '.join(sorted(APROBABLES))}")
    c = buscar(a.id)
    marcar(c, a.paso)
    print(f"Aprobado {a.paso} de {c['id']}. Sigue: {siguiente(c) or 'terminado'}")


def cmd_ajustes(a):
    c = buscar(a.id)
    c["notas"].append({"fecha": ahora(), "paso": a.paso, "nota": a.nota})
    c["hecho"].pop(a.paso, None)
    guardar(c)
    print(f"Ajustes anotados para {a.paso}.")


def cmd_grabado(a):
    marcar(buscar(a.id), "grabado")
    print("Marcado como grabado. Cuando dejes el video en assets/, marca en-carpeta.")


def cmd_en_carpeta(a):
    c = buscar(a.id)
    vids = [f for f in os.listdir(os.path.join(RAIZ, c["carpeta"], "assets")) if f.lower().endswith(VIDEO_EXT)]
    if not vids:
        sys.exit(f"No hay video en {c['carpeta']}/assets/. Déjalo ahí primero.")
    marcar(c, "en_carpeta")
    print("Listo para editar.")


def cmd_publicado(a):
    marcar(buscar(a.id), "publicacion", {"url": a.url})
    print("Publicación registrada.")


def cmd_pendiente(a):
    pend = [(c, siguiente(c)) for c in contenidos() if siguiente(c)]
    if not pend:
        print("Nada pendiente. Siguiente: /ideas")
        return
    quien = {"idea": "aprobar la idea", "guion": "escribir o aprobar el guion", "grabado": "grabar",
             "en_carpeta": "dejar el video en assets", "cortes": "editar paso 1 (cortes)",
             "imagenes": "editar paso 2 (imágenes)", "video": "editar paso 3 (subtítulos)",
             "publicacion": "publicar"}
    for c, p in pend:
        print(f"{c['id']} [{c['cuenta']}]: {quien[p]}")


def cmd_preparar(a):
    c = buscar(a.id)
    if "en_carpeta" not in c["hecho"]:
        sys.exit("Aún no está el video en la carpeta (marca en-carpeta).")
    paso = next((p for p in EDICION if p not in c["hecho"]), None)
    if not paso:
        sys.exit("La edición ya está aprobada completa.")
    carpeta = os.path.join(RAIZ, c["carpeta"])
    assets = sorted(os.listdir(os.path.join(carpeta, "assets")))
    videos = [f for f in assets if f.lower().endswith(VIDEO_EXT)]
    imagenes = [f for f in assets if f.lower().endswith(IMG_EXT)]
    if paso == "imagenes" and not imagenes:
        sys.exit("Paso 2 bloqueado: no hay fotos ni imágenes en assets/. Pídeselas a la persona.")
    previo = {"imagenes": "cortes", "video": "imagenes"}.get(paso)
    base = None
    if previo:
        hechos = sorted(glob.glob(os.path.join(carpeta, "edicion", previo, "*.mp4")), key=os.path.getmtime)
        base = os.path.relpath(hechos[-1], RAIZ) if hechos else None
    cd = os.path.join(CUENTAS, c["cuenta"])
    man = {
        "contenido": c["id"], "paso": paso, "carpeta": c["carpeta"],
        "video_entrada": base or [os.path.join(c["carpeta"], "assets", v) for v in videos],
        "imagenes": [os.path.join(c["carpeta"], "assets", i) for i in imagenes],
        "guion": os.path.join(c["carpeta"], "guion", "guion.md"),
        "marca": leer(os.path.join(cd, "marca.json"), {}),
        "preferencias": os.path.relpath(os.path.join(cd, "edicion.md"), RAIZ),
        "reglas": "reglas/edicion-tecnica.md",
        "salida": os.path.join(c["carpeta"], "edicion", paso),
        "ajustes_pedidos": [n for n in c["notas"] if n["paso"] == paso],
    }
    os.makedirs(os.path.join(RAIZ, man["salida"]), exist_ok=True)
    ruta = os.path.join(carpeta, "edicion", f"manifiesto_{paso}.json")
    escribir(ruta, man)
    print(f"Paso {EDICION.index(paso) + 1} ({paso}). Manifiesto: {os.path.relpath(ruta, RAIZ)}")


# ---------- Centro de contenido ----------
def estado_centro():
    out = []
    for c in contenidos():
        guion = os.path.join(RAIZ, c["carpeta"], "guion", "guion.md")
        videos = {p: sorted(os.path.relpath(v, RAIZ) for v in glob.glob(os.path.join(RAIZ, c["carpeta"], "edicion", p, "*.mp4")))
                  for p in EDICION}
        out.append({**c, "siguiente": siguiente(c),
                    "guion": open(guion, encoding="utf-8").read() if os.path.exists(guion) else "",
                    "videos": videos})
    return {"contenidos": out, "cuentas": lista_cuentas()}


ACCIONES = {
    "aprobar": lambda c, d: marcar(c, d["paso"]) if d["paso"] in APROBABLES else None,
    "grabado": lambda c, d: marcar(c, "grabado"),
    "en_carpeta": lambda c, d: marcar(c, "en_carpeta"),
    "publicado": lambda c, d: marcar(c, "publicacion", {"url": d.get("url", "")}),
}


class Centro(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kw):
        super().__init__(*args, directory=RAIZ, **kw)

    def log_message(self, *a):
        pass

    def responder(self, datos, codigo=200):
        cuerpo = json.dumps(datos, ensure_ascii=False).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.path = "/centro/index.html"
        if self.path == "/api/estado":
            return self.responder(estado_centro())
        if not (self.path.startswith("/centro/") or self.path.startswith("/workspace/")):
            return self.send_error(404)
        return super().do_GET()

    def do_POST(self):
        if self.path != "/api/accion":
            return self.send_error(404)
        d = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        c = next((x for x in contenidos() if x["id"] == d.get("id")), None)
        if not c or d.get("tipo") not in (*ACCIONES, "ajustes"):
            return self.responder({"error": "acción no válida"}, 400)
        if d["tipo"] == "ajustes":
            c["notas"].append({"fecha": ahora(), "paso": d.get("paso", ""), "nota": d.get("nota", "")})
            c["hecho"].pop(d.get("paso", ""), None)
            guardar(c)
        else:
            ACCIONES[d["tipo"]](c, d)
        bandeja = leer(BANDEJA, [])
        bandeja.append({**d, "fecha": ahora(), "visto": False})
        escribir(BANDEJA, bandeja)
        self.responder({"ok": True})


def ip_local():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def cmd_centro(a):
    srv = http.server.ThreadingHTTPServer(("0.0.0.0", a.puerto), Centro)
    print(f"Centro de contenido:\n  En este computador: http://localhost:{a.puerto}\n"
          f"  En el celular (misma wifi): http://{ip_local()}:{a.puerto}\nCtrl+C para cerrar.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


def cmd_bandeja(a):
    bandeja = leer(BANDEJA, [])
    nuevas = [b for b in bandeja if not b.get("visto")]
    if not nuevas:
        print("Sin acciones nuevas del Centro.")
        return
    for b in nuevas:
        extra = b.get("nota") or b.get("url") or ""
        print(f"{b['fecha']} {b['id']}: {b['tipo']} {b.get('paso', '')} {extra}".strip())
        b["visto"] = True
    escribir(BANDEJA, bandeja)


# ---------- sincronizar y actualizar ----------
def git(*args):
    return subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True)


def cmd_sync(a):
    if not os.path.isdir(os.path.join(RAIZ, ".git")) or not git("remote").stdout.strip():
        print("Sin GitHub conectado: todo queda en este computador.")
        return
    git("pull", "--rebase", "--autostash")
    git("add", "-A")
    if git("diff", "--cached", "--quiet").returncode:
        git("commit", "-m", a.m or "actualización")
    r = git("push")
    print("Sincronizado." if r.returncode == 0 else "No se pudo subir: " + r.stderr.strip())


def cmd_actualizar(a):
    url = f"https://github.com/{REPO_PLANTILLA}/archive/refs/heads/main.zip"
    print("Descargando", url)
    with urllib.request.urlopen(url) as r:
        z = zipfile.ZipFile(io.BytesIO(r.read()))
    raiz_zip = z.namelist()[0].split("/")[0]
    protegido = ("cuentas/", "workspace/", "datos/")
    for n in z.namelist():
        rel = n[len(raiz_zip) + 1:]
        if not rel or rel.endswith("/") or rel.startswith(protegido):
            continue
        dest = os.path.join(RAIZ, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(z.read(n))
    print("Actualizado. Tus cuentas y contenidos no se tocaron.")


def main():
    p = argparse.ArgumentParser(prog="cs", description="Sistema de contenido")
    sp = p.add_subparsers(dest="cmd", required=True)

    def sub(nombre, fn, ayuda):
        s = sp.add_parser(nombre, help=ayuda)
        s.set_defaults(fn=fn)
        return s

    s = sub("cuenta-nueva", cmd_cuenta_nueva, "crea una cuenta")
    s.add_argument("cuenta"); s.add_argument("--nombre"); s.add_argument("--instagram"); s.add_argument("--tiktok")
    s = sub("referente", cmd_referente, "agrega un referente a una cuenta")
    s.add_argument("cuenta"); s.add_argument("red", choices=["instagram", "tiktok"]); s.add_argument("usuario")
    sub("cuentas", cmd_cuentas, "lista las cuentas")
    s = sub("descargar", cmd_descargar, "baja videos y datos públicos de las redes de la cuenta")
    s.add_argument("cuenta"); s.add_argument("--n", type=int, default=25)
    s.add_argument("--referentes", action="store_true"); s.add_argument("--solo-datos", action="store_true")
    s.add_argument("--navegador", default="chrome", help="navegador con la sesión iniciada (para Instagram)")
    s = sub("transcribir", cmd_transcribir, "transcribe las muestras con Whisper local")
    s.add_argument("cuenta"); s.add_argument("--modelo", default="small"); s.add_argument("--idioma")
    s = sub("muestras", cmd_muestras, "lista videos descargados con métricas y transcripción")
    s.add_argument("cuenta")
    s = sub("nuevo", cmd_nuevo, "crea un contenido")
    s.add_argument("cuenta"); s.add_argument("titulo"); s.add_argument("--formato", default="video")
    s = sub("lista", cmd_lista, "lista contenidos"); s.add_argument("--cuenta")
    s = sub("ver", cmd_ver, "muestra un contenido"); s.add_argument("id")
    s = sub("aprobar", cmd_aprobar, "aprobación humana de un paso"); s.add_argument("id"); s.add_argument("paso")
    s = sub("ajustes", cmd_ajustes, "anota cambios pedidos")
    s.add_argument("id"); s.add_argument("paso"); s.add_argument("nota")
    s = sub("grabado", cmd_grabado, "marca que ya se grabó"); s.add_argument("id")
    s = sub("en-carpeta", cmd_en_carpeta, "el video ya está en assets"); s.add_argument("id")
    s = sub("publicado", cmd_publicado, "registra la publicación"); s.add_argument("id"); s.add_argument("url")
    sub("pendiente", cmd_pendiente, "qué sigue")
    s = sub("preparar", cmd_preparar, "manifiesto del siguiente paso de edición"); s.add_argument("id")
    s = sub("centro", cmd_centro, "abre el Centro de contenido"); s.add_argument("--puerto", type=int, default=8000)
    sub("bandeja", cmd_bandeja, "acciones nuevas marcadas en el Centro")
    s = sub("sync", cmd_sync, "sincroniza con GitHub si está conectado"); s.add_argument("-m")
    sub("actualizar", cmd_actualizar, "trae la última versión del sistema")
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
