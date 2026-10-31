# -*- coding: utf-8 -*-
"""
RO Cooldown Overlay — estilo WeakAuras para Ragnarok Online LATAM.

Abre um painel onde você:
  - cria PERFIS (ex.: um por personagem), que ficam salvos;
  - marca os ícones das skills na barra de atalhos;
  - digita a recarga de cada skill (ou deixa vazio para o programa aprender);
  - move e redimensiona os ícones do overlay.

Como detecta o delay:
  Olha a tela como um print/OBS faria e compara cada ícone da barra de
  atalhos com a imagem dele "pronto". Não lê memória, não injeta nada no
  client, não escuta nem envia teclas.

Requisitos: Windows 10/11 e Python 3.10+
    pip install mss pillow numpy opencv-python

Uso: dê dois cliques em iniciar.bat (ou rode: python ro_cooldown_overlay.py)

O código fica na pasta rocd/ (o que tem em cada arquivo: rocd/__init__.py).
"""
import sys
from pathlib import Path

if sys.platform != "win32":
    sys.exit("Este overlay só funciona no Windows.")

AQUI = Path(__file__).resolve().parent
ZIP_MAIN = "https://github.com/tassiocarlini/RO-Cooldown-Overlay/archive/refs/heads/main.zip"


def completar_atualizacao(url=ZIP_MAIN):
    """Até a v1.0.28 o programa era um arquivo só, e o atualizador dessas versões copia este
    arquivo mas não a pasta rocd/. Na primeira vez que abre, baixa do GitHub a pasta que falta."""
    import io
    import urllib.request
    import zipfile
    req = urllib.request.Request(url, headers={"User-Agent": "RO-Cooldown-Overlay"})
    with urllib.request.urlopen(req, timeout=120) as r:
        dados = r.read()
    with zipfile.ZipFile(io.BytesIO(dados)) as zf:
        for nome in zf.namelist():
            partes = nome.split("/")       # "RO-Cooldown-Overlay-main/rocd/app.py"
            if len(partes) > 2 and partes[1] == "rocd" and partes[-1] and ".." not in partes:
                alvo = AQUI.joinpath(*partes[1:])
                alvo.parent.mkdir(parents=True, exist_ok=True)
                alvo.write_bytes(zf.read(nome))


if not getattr(sys, "frozen", False) and not (AQUI / "rocd" / "app.py").exists():
    try:
        completar_atualizacao()
    except Exception as e:
        import tkinter as tk
        from tkinter import messagebox
        tk.Tk().withdraw()
        messagebox.showerror("RO Cooldown Overlay",
                             f"Falta a pasta rocd do programa e não deu para baixar ({e}).\n\n"
                             "Baixe o programa de novo em:\n"
                             "github.com/tassiocarlini/RO-Cooldown-Overlay")
        sys.exit(1)

from rocd.app import main  # noqa: E402

if __name__ == "__main__":
    main()
