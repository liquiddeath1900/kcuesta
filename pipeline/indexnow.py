#!/usr/bin/env python3
"""
Avisarle a los buscadores que una página cambió, el mismo día.

QUE ES Y QUE NO ES
    IndexNow lo usan Bing, Yandex, Seznam, Naver y Yep. **Google NO
    participa** —lo probó en 2021 y nunca lo adoptó— así que esto no
    acelera nada en Google. Para Google el camino sigue siendo el sitemap
    y Search Console.

POR QUE VALE LA PENA IGUAL
    El parte del gremio cambia todas las mañanas y envejece en horas. Que
    Bing lo recoja el mismo día en vez de la semana que viene es la
    diferencia entre publicar un precio y publicar un archivo histórico.

REGLA QUE HAY QUE RESPETAR
    Solo se avisan las páginas que DE VERDAD cambiaron. La documentación
    pide expresamente no reenviar URLs sin cambios, y cada buscador corta
    con 429 cuando se pasa. Avisar el sitemap entero todos los días es la
    forma rápida de que dejen de hacer caso.

USO
    python3 pipeline/indexnow.py gremio.html precios.html
    python3 pipeline/indexnow.py --si-cambiaron     (mira git)
"""
import json, os, subprocess, sys, urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://kcuesta.com/"


def clave():
    """La clave es el archivo .txt que vive en la raíz del sitio. Se busca
    en vez de escribirla aquí: así rotarla es borrar un archivo y poner
    otro, sin tocar código."""
    for f in os.listdir(RAIZ):
        if f.endswith(".txt") and len(f) == 36:      # 32 hex + '.txt'
            return f[:-4]
    raise SystemExit("no encuentro el archivo de clave de IndexNow en la raíz")


def cambiadas():
    """Las páginas tocadas en el último commit. Es la fuente honesta de
    'qué cambió': si el pipeline no modificó el HTML, no hay nada que
    avisar."""
    out = subprocess.run(["git", "-C", RAIZ, "diff", "--name-only", "HEAD~1", "HEAD"],
                         capture_output=True, text=True).stdout
    return [l for l in out.split("\n") if l.endswith(".html")]


def avisar(paginas):
    k = clave()
    urls = [BASE + ("" if p == "index.html" else p) for p in paginas]
    if not urls:
        print("nada cambió; no se avisa")
        return 0
    cuerpo = json.dumps({
        "host": "kcuesta.com", "key": k,
        "keyLocation": BASE + k + ".txt",
        "urlList": urls}).encode()
    req = urllib.request.Request("https://api.indexnow.org/indexnow", data=cuerpo,
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            # 200 = aceptado. 202 = aceptado, clave todavía validándose.
            # 403 = clave mala. 429 = demasiados avisos, hay que espaciar.
            print("IndexNow %s para %d URL(s):" % (r.status, len(urls)))
            for u in urls:
                print("   ", u)
            return 0
    except urllib.error.HTTPError as e:
        print("IndexNow rechazó (%s): %s" % (e.code, e.read().decode()[:200]))
        return 1


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "--si-cambiaron":
        sys.exit(avisar(cambiadas()))
    sys.exit(avisar(args))
