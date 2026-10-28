# -*- coding: utf-8 -*-
"""
RO Cooldown Overlay v3 — estilo WeakAuras para Ragnarok Online LATAM.

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
"""

import copy
import ctypes
import hashlib
import io
import json
import math
import os
import re
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import shutil
import zipfile
import sys
import time
import tkinter as tk
import traceback
from ctypes import wintypes
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

if sys.platform != "win32":
    sys.exit("Este overlay só funciona no Windows.")

import queue
import threading

import mss
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageStat, ImageTk

try:                        # para achar os ícones na tela sozinho
    import numpy as np
except ImportError:
    np = None
try:
    import cv2
except ImportError:
    cv2 = None
try:                        # tema visual moderno (Windows 11, claro/escuro)
    import sv_ttk
except ImportError:
    sv_ttk = None

LIMIAR_PERDIDO = 0.5        # semelhança abaixo disso: o ícone não está mais ali
LIMIAR_ACHADO = 0.85        # semelhança mínima para aceitar um ícone encontrado
LIMIAR_BUFF = 0.80          # semelhança mínima para considerar o buff na tela
BUFF_TOLERANCIA = 1.5       # s sem ver o ícone antes de dizer que o buff acabou (ícone pisca)
MOSTRAR_BUFF = {"Sempre": "sempre", "Só quando faltar": "faltando", "Só quando ativo": "ativo"}


VERSAO = "1.0.21"
NOME_APP = "RO Cooldown Overlay"
# Repositório no GitHub de onde vêm as atualizações (CHANGELOG.md e .zip da branch abaixo)
REPO_GITHUB = "tassiocarlini/RO-Cooldown-Overlay"
BRANCH_GITHUB = "main"

if getattr(sys, "frozen", False):
    # Versão .exe: seus dados ficam em %APPDATA%, assim atualizar o programa não apaga nada
    PASTA = Path(os.environ.get("APPDATA") or Path.home()) / NOME_APP
    PASTA_RECURSOS = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
else:
    PASTA = Path(__file__).resolve().parent
    PASTA_RECURSOS = PASTA
PASTA.mkdir(parents=True, exist_ok=True)

# Pastas onde o programa procura pacotes de buffs (buffs*.zip) para importar sozinho:
# a pasta do programa (.exe ou .py) e a pasta de dados
PASTAS_PACOTES = list(dict.fromkeys([
    Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent,
    PASTA]))

PASTA_PERFIS = PASTA / "perfis"
ARQ_APP = PASTA / "app.json"
ARQ_BANCO = (PASTA / "banco_skills.json" if (PASTA / "banco_skills.json").exists()
             else PASTA_RECURSOS / "banco_skills.json")   # nomes e recargas padrão
ARQ_MEUS = PASTA / "meus_tempos.json"            # recargas que você corrigiu
TODAS = "Todas as classes"
PASTA_DP = PASTA / "cache_divinepride"           # respostas e ícones da Divine Pride
DP_URL = "https://www.divine-pride.net/api/database/Skill/{id}"
DP_URL_EFST = "https://www.divine-pride.net/api/database/Efst/{id}"   # ícones de buff (status)
ESCALAS_BUFF = [round(0.9 + 0.05 * i, 2) for i in range(23)]          # 0,90x até 2,00x
LIMIAR_ACHADO_DP = 0.75     # ícone da Divine Pride x ícone na tela (podem diferir um pouco)
LIMIAR_BUFF_SITE = 0.80     # para aceitar um buff achado pelo ícone da Divine Pride
ESCALAS_DP = (1.0, 1.25, 1.5, 2.0)
ARQ_ANTIGO = PASTA / "ro_cd_config.json"          # config da versão anterior
PASTA_ICONES_ANTIGA = PASTA / "ro_cd_icones"

COR_TRANSPARENTE = "#010101"
COR_PAINEL = (20, 23, 31)              # fundo da caixa dos ícones
ESTILOS = {"Clássico": "classico", "Moderno": "moderno", "Minimalista": "minimalista"}
BARRA_H = 5

PERFIL_PADRAO = {
    "titulo_janela_jogo": "Ragnarok",
    "classe": TODAS,
    "origem_calibracao": None,         # posição do jogo quando os ícones foram marcados
    "skills": [],
    "buffs": [],                       # buffs vigiados (cada um com 1+ versões de ícone)
    "area_buffs": None,                # área da tela onde ficam os ícones de buff
    "area_ap": None,                   # onde aparece "AP 53 / 200" na janela Informações básicas
    "layout": {
        "x": None, "y": None,          # None = centralizado
        "tamanho": 52,
        "espaco": 8,
        "orientacao": "horizontal",
        "esconder_quando_pronto": False,
        "esconder_sem_foco": False,
        "estilo": "moderno",           # classico | moderno | minimalista
        "fundo_painel": False,         # caixa escura atrás de todos os ícones
        "mostrar_nomes": False,        # nome da skill/buff embaixo do ícone
        "mostrar_ap": False,           # barra de AP acima dos ícones
        "ap_altura": 0,                # altura da barra de AP em pixels (0 = automática)
        "ap_cor": "#3b82f6",           # cor do preenchimento da barra de AP
        "aviso_vermelho_s": 3.0,
        "origem": None,                # posição do jogo quando o overlay foi posicionado
    },
    "deteccao": {
        "limiar_delay": 0.10,
        "limiar_pronto": 0.03,
        "frames_entrar": 1,
        "frames_confirmar": 2,
        "min_mostrar": 0.6,
        "fps": 30,
    },
    "versao": 6,
}

JANELA_GRUPO = 0.15   # s: ícones que escurecem juntos dentro disso = delay global

user32 = ctypes.windll.user32
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
WDA_EXCLUDEFROMCAPTURE = 0x11


# =============================================================== utilidades

def dpi_aware():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass


def nova_captura():
    """mss.MSS nas versões novas, mss.mss nas antigas."""
    return (getattr(mss, "MSS", None) or mss.mss)()


GA_ROOT = 2
HWND = wintypes.HWND


def _sig(fn, res, *args):
    fn.restype = res
    fn.argtypes = list(args)


_sig(user32.GetParent, HWND, HWND)
_sig(user32.GetWindowLongW, ctypes.c_long, HWND, ctypes.c_int)
_sig(user32.SetWindowLongW, ctypes.c_long, HWND, ctypes.c_int, ctypes.c_long)
_sig(user32.GetForegroundWindow, HWND)
_sig(user32.GetWindowTextLengthW, ctypes.c_int, HWND)
_sig(user32.GetWindowTextW, ctypes.c_int, HWND, wintypes.LPWSTR, ctypes.c_int)
_sig(user32.GetClassNameW, ctypes.c_int, HWND, wintypes.LPWSTR, ctypes.c_int)
_sig(user32.IsWindow, wintypes.BOOL, HWND)
_sig(user32.IsWindowVisible, wintypes.BOOL, HWND)
_sig(user32.IsIconic, wintypes.BOOL, HWND)
_sig(user32.GetClientRect, wintypes.BOOL, HWND, ctypes.POINTER(wintypes.RECT))
_sig(user32.ClientToScreen, wintypes.BOOL, HWND, ctypes.POINTER(wintypes.POINT))
_sig(user32.WindowFromPoint, HWND, wintypes.POINT)
_sig(user32.GetAncestor, HWND, HWND, ctypes.c_uint)
_sig(user32.SetWindowDisplayAffinity, wintypes.BOOL, HWND, wintypes.DWORD)
EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, HWND, wintypes.LPARAM)
_sig(user32.EnumWindows, wintypes.BOOL, EnumWindowsProc, wintypes.LPARAM)

# Janelas que podem ter "Ragnarok" no título mas não são o jogo
# (navegadores, Discord, Explorer, terminal, este próprio programa)
CLASSES_IGNORADAS = ("Chrome_WidgetWin", "MozillaWindowClass", "TkTopLevel", "TkChild",
                     "CabinetWClass", "ConsoleWindowClass", "CASCADIA_HOSTING_WINDOW_CLASS",
                     "ApplicationFrameWindow")


def hwnd_de(janela):
    return user32.GetParent(janela.winfo_id())


def mudar_estilo(hwnd, ligar=0, desligar=0):
    estilo = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, (estilo | ligar) & ~desligar)


def texto_janela(h):
    n = user32.GetWindowTextLengthW(h)
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(h, buf, n + 1)
    return buf.value


def classe_janela(h):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(h, buf, 256)
    return buf.value


def eh_jogo(h, titulo):
    if not h or not user32.IsWindow(h) or not user32.IsWindowVisible(h):
        return False
    if titulo.lower() not in texto_janela(h).lower():
        return False
    cls = classe_janela(h)
    return not any(cls.startswith(c) for c in CLASSES_IGNORADAS)


class Jogo:
    """Acha e acompanha a janela do Ragnarok (só lê título/posição da janela)."""

    def __init__(self):
        self.hwnd = None
        self._ult_busca = -99.0

    def localizar(self, titulo, agora):
        fg = user32.GetForegroundWindow()
        if fg and fg != self.hwnd and eh_jogo(fg, titulo):
            self.hwnd = fg               # o jogo em foco tem prioridade (multi-client)
            return
        if self.hwnd and agora - self._ult_busca < 0.5:
            return
        self._ult_busca = agora
        if self.hwnd and eh_jogo(self.hwnd, titulo):
            return
        achados = []

        def cb(h, _lp):
            if eh_jogo(h, titulo):
                achados.append(h)
                return False
            return True

        user32.EnumWindows(EnumWindowsProc(cb), 0)
        self.hwnd = achados[0] if achados else None

    def geometria(self):
        """(x, y, largura, altura) da área do jogo na tela, ou None."""
        h = self.hwnd
        if not h or not user32.IsWindow(h) or user32.IsIconic(h):
            return None
        r = wintypes.RECT()
        p = wintypes.POINT(0, 0)
        if not user32.GetClientRect(h, ctypes.byref(r)) or not user32.ClientToScreen(h, ctypes.byref(p)):
            return None
        if r.right <= 0 or r.bottom <= 0:
            return None
        return (p.x, p.y, r.right, r.bottom)

    def em_foco(self):
        return bool(self.hwnd) and user32.GetForegroundWindow() == self.hwnd


def janela_no_ponto(x, y):
    h = user32.WindowFromPoint(wintypes.POINT(int(x), int(y)))
    return user32.GetAncestor(h, GA_ROOT) if h else None


def miolo(img):
    """Ignora 15% de cada borda (moldura do slot, número da tecla etc.)."""
    w, h = img.size
    mx, my = max(1, int(w * 0.15)), max(1, int(h * 0.15))
    if w - 2 * mx < 2 or h - 2 * my < 2:
        return img
    return img.crop((mx, my, w - mx, h - my))


def diferenca(a, b):
    st = ImageStat.Stat(ImageChops.difference(a, b))
    return sum(st.mean) / (len(st.mean) * 255.0)


ARQ_LOG = PASTA / "log.txt"
_ult_log = {}


def registrar(msg, chave_rep=None, intervalo=10.0):
    """Escreve em log.txt (com limite de repetição para erros que se repetem a cada frame)."""
    agora = time.monotonic()
    if chave_rep is not None:
        if agora - _ult_log.get(chave_rep, -1e9) < intervalo:
            return
        _ult_log[chave_rep] = agora
    try:
        if ARQ_LOG.exists() and ARQ_LOG.stat().st_size > 500_000:
            ARQ_LOG.unlink()
        with open(ARQ_LOG, "a", encoding="utf-8") as f:
            f.write(time.strftime("%H:%M:%S ") + msg.rstrip() + "\n")
    except Exception:
        pass


def cinza(img):
    return np.asarray(img.convert("L"), dtype=np.float32)


def mapa_simbolo(arr):
    """Realça os traços claros do desenho do ícone (ex.: o kanji branco da Brisa Leve).

    Os ícones de buff do RO são translúcidos: o cenário aparece por trás e muda o tempo todo,
    e uma "varredura" clara mostra o tempo restante. Os traços brancos do desenho não mudam,
    então comparar só eles reconhece o buff em qualquer fundo."""
    m = np.asarray(arr)[..., :3].min(axis=2).astype(np.int32)
    return (np.clip(m - 200, 0, 40) * 255 // 40).astype(np.uint8)


def mapa_simbolo_suave(arr):
    """Traços claros levemente desfocados: tolera 1 pixel de diferença e ícone ampliado."""
    m = mapa_simbolo(arr)
    return cv2.GaussianBlur(m, (3, 3), 0) if cv2 is not None else m


def tem_moldura(mx, x, y, w, h, folga=4, minimo=230):
    """Os ícones de buff do RO têm uma moldura clara em volta. Texto e cenário não.
    mx = brilho (maior canal) da imagem. Exige pelo menos 2 lados claros."""
    H, W = mx.shape

    def lin_h(yy):
        if not 0 <= yy < H:
            return 0.0
        seg = mx[yy, max(0, x + 3):min(W, x + w - 3)]
        return float(seg.mean()) if seg.size else 0.0

    def lin_v(xx):
        if not 0 <= xx < W:
            return 0.0
        seg = mx[max(0, y + 3):min(H, y + h - 3), xx]
        return float(seg.mean()) if seg.size else 0.0

    d = range(-folga, folga + 1)
    lados = [max(lin_h(y + k) for k in d), max(lin_h(y + h - 1 + k) for k in d),
             max(lin_v(x + k) for k in d), max(lin_v(x + w - 1 + k) for k in d)]
    return sum(v >= minimo for v in lados) >= 2


def picos(r, n=4, raio=6):
    """Até n melhores posições de um mapa de semelhança (apagando em volta de cada uma)."""
    r = r.copy()
    for _ in range(n):
        _, v, _, loc = cv2.minMaxLoc(r)
        if v != v or v <= -1:
            return
        yield v, loc
        x, y = loc
        r[max(0, y - raio):y + raio + 1, max(0, x - raio):x + raio + 1] = -1


def modelos_buff(im):
    """(modelo em tons de cinza, modelo só dos traços claros ou None) do miolo do ícone."""
    c = miolo(im)
    branco = mapa_simbolo(np.asarray(c))
    if branco.std() < 8:
        return np.asarray(c.convert("L")), None
    return np.asarray(c.convert("L")), mapa_simbolo_suave(np.asarray(c))


def _ncc(a, b):
    a = a - a.mean()
    b = b - b.mean()
    va, vb = float((a * a).sum()), float((b * b).sum())
    liso = 1e-3 * a.size
    if vb < liso:                       # pedaço liso no ícone original
        return 1.0 if va < liso else 0.0
    if va < liso:
        return 0.0
    return float((a * b).sum() / math.sqrt(va * vb))


def semelhanca(a, b, n=3):
    """0 a 1: o ícone continua sendo o mesmo? Não muda se ele escurecer, ficar cinza
    ou tiver a varredura do delay; cai para ~0 se for outro ícone ou slot vazio."""
    if a.shape != b.shape:
        return 0.0
    h, w = b.shape
    vals = [_ncc(a[i * h // n:(i + 1) * h // n, j * w // n:(j + 1) * w // n],
                 b[i * h // n:(i + 1) * h // n, j * w // n:(j + 1) * w // n])
            for i in range(n) for j in range(n)]
    return float(np.median(vals))


def sem_cor_chave(img):
    return img.point(lambda v: max(v, 2))


# ---------------------------------------------------------------- ícones e tema
# Ícones desenhados aqui mesmo (sem arquivos de imagem), em 4x e reduzidos para ficarem lisos.

ESC_ICONE = 4  # desenha 4x maior e reduz: bordas suaves


def _rgba(hexcor, a=255):
    h = hexcor.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (a,)


def desenhar_icone(nome, cor="#e6e6e6", tam=18):
    S = tam * ESC_ICONE
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = _rgba(cor)
    w = max(2, int(S * 0.085))          # espessura do traço
    m = S * 0.14                        # margem
    L, T, R, B = m, m, S - m, S - m
    cx, cy = S / 2, S / 2

    def linha(*pts, larg=w):
        d.line(pts, fill=c, width=larg, joint="curve")
        for p in (pts[0], pts[-1]):
            r = larg / 2
            d.ellipse((p[0] - r, p[1] - r, p[0] + r, p[1] + r), fill=c)

    def circulo(x, y, r, preench=False, larg=w):
        if preench:
            d.ellipse((x - r, y - r, x + r, y + r), fill=c)
        else:
            d.ellipse((x - r, y - r, x + r, y + r), outline=c, width=larg)

    def ret(x0, y0, x1, y1, raio=S * 0.08, preench=False, larg=w):
        if preench:
            d.rounded_rectangle((x0, y0, x1, y1), radius=raio, fill=c)
        else:
            d.rounded_rectangle((x0, y0, x1, y1), radius=raio, outline=c, width=larg)

    if nome == "play":
        d.polygon([(S * 0.30, S * 0.18), (S * 0.30, S * 0.82), (S * 0.84, S * 0.50)], fill=c)
    elif nome == "stop":
        ret(S * 0.22, S * 0.22, S * 0.78, S * 0.78, preench=True)
    elif nome == "camera":
        ret(L, S * 0.30, R, B, raio=S * 0.10)
        d.polygon([(S * 0.34, S * 0.30), (S * 0.42, S * 0.18), (S * 0.58, S * 0.18), (S * 0.66, S * 0.30)], fill=c)
        circulo(cx, S * 0.56, S * 0.15)
    elif nome == "pasta":
        d.polygon([(L, S * 0.24), (S * 0.42, S * 0.24), (S * 0.50, S * 0.34), (R, S * 0.34),
                   (R, B), (L, B)], outline=c, width=w)
        linha((L, S * 0.42), (R, S * 0.42))
    elif nome == "lupa":
        circulo(S * 0.42, S * 0.42, S * 0.25)
        linha((S * 0.60, S * 0.60), (S * 0.84, S * 0.84), larg=int(w * 1.2))
    elif nome == "mais":
        linha((cx, L), (cx, B), larg=int(w * 1.1))
        linha((L, cy), (R, cy), larg=int(w * 1.1))
    elif nome == "mais_circulo":
        circulo(cx, cy, S * 0.38)
        linha((cx, S * 0.32), (cx, S * 0.68))
        linha((S * 0.32, cy), (S * 0.68, cy))
    elif nome == "selecao":              # marcar ícones: cantos de recorte + quadrado
        k = S * 0.22
        for (x, y, dx, dy) in ((L, T, 1, 1), (R, T, -1, 1), (L, B, 1, -1), (R, B, -1, -1)):
            linha((x, y + dy * k), (x, y), (x + dx * k, y))
        ret(S * 0.38, S * 0.38, S * 0.62, S * 0.62, preench=True, raio=S * 0.04)
    elif nome == "radar":                # procurar na tela: cantos + lupa
        k = S * 0.18
        for (x, y, dx, dy) in ((L, T, 1, 1), (R, T, -1, 1), (L, B, 1, -1), (R, B, -1, -1)):
            linha((x, y + dy * k), (x, y), (x + dx * k, y))
        circulo(S * 0.47, S * 0.47, S * 0.14)
        linha((S * 0.57, S * 0.57), (S * 0.68, S * 0.68))
    elif nome == "mover":
        linha((cx, L), (cx, B))
        linha((L, cy), (R, cy))
        a = S * 0.12
        for (x, y, dx, dy) in ((cx, L, 0, 1), (cx, B, 0, -1), (L, cy, 1, 0), (R, cy, -1, 0)):
            if dx == 0:
                linha((x - a, y + dy * a), (x, y), (x + a, y + dy * a))
            else:
                linha((x + dx * a, y - a), (x, y), (x + dx * a, y + a))
    elif nome == "centro":
        circulo(cx, cy, S * 0.30)
        circulo(cx, cy, S * 0.07, preench=True)
        for (a, b) in (((cx, T), (cx, S * 0.26)), ((cx, S * 0.74), (cx, B)),
                       ((L, cy), (S * 0.26, cy)), ((S * 0.74, cy), (R, cy))):
            linha(a, b)
    elif nome == "chave":
        circulo(S * 0.34, S * 0.38, S * 0.17)
        linha((S * 0.46, S * 0.50), (S * 0.82, S * 0.86))
        linha((S * 0.66, S * 0.70), (S * 0.56, S * 0.80))
        linha((S * 0.76, S * 0.80), (S * 0.68, S * 0.88))
    elif nome == "ajuda":
        circulo(cx, cy, S * 0.38)
        d.arc((S * 0.36, S * 0.24, S * 0.64, S * 0.50), start=180, end=50, fill=c, width=w)
        linha((S * 0.59, S * 0.44), (cx, S * 0.54), (cx, S * 0.60))
        circulo(cx, S * 0.72, w * 0.7, preench=True)
    elif nome == "check":
        circulo(cx, cy, S * 0.38)
        linha((S * 0.33, S * 0.52), (S * 0.45, S * 0.64), (S * 0.68, S * 0.38))
    elif nome == "copiar":
        ret(S * 0.34, S * 0.34, R, B)
        linha((S * 0.24, S * 0.66), (L, S * 0.66), (L, L), (S * 0.66, L), (S * 0.66, S * 0.24))
    elif nome == "lapis":
        d.polygon([(S * 0.64, S * 0.18), (S * 0.82, S * 0.36), (S * 0.38, S * 0.80),
                   (S * 0.16, S * 0.84), (S * 0.20, S * 0.62)], outline=c, width=w)
        linha((S * 0.56, S * 0.26), (S * 0.74, S * 0.44))
    elif nome == "lixeira":
        linha((S * 0.20, S * 0.28), (S * 0.80, S * 0.28))
        linha((S * 0.40, S * 0.28), (S * 0.42, S * 0.18), (S * 0.58, S * 0.18), (S * 0.60, S * 0.28))
        d.polygon([(S * 0.27, S * 0.34), (S * 0.73, S * 0.34), (S * 0.69, B), (S * 0.31, B)],
                  outline=c, width=w)
        linha((S * 0.43, S * 0.46), (S * 0.43, S * 0.74))
        linha((S * 0.57, S * 0.46), (S * 0.57, S * 0.74))
    elif nome == "cima":
        linha((S * 0.24, S * 0.64), (cx, S * 0.36), (S * 0.76, S * 0.64), larg=int(w * 1.2))
    elif nome == "baixo":
        linha((S * 0.24, S * 0.36), (cx, S * 0.64), (S * 0.76, S * 0.36), larg=int(w * 1.2))
    elif nome == "fechar":
        linha((S * 0.28, S * 0.28), (S * 0.72, S * 0.72), larg=int(w * 1.1))
        linha((S * 0.72, S * 0.28), (S * 0.28, S * 0.72), larg=int(w * 1.1))
    elif nome in ("exportar", "importar"):
        linha((L, S * 0.62), (L, B), (R, B), (R, S * 0.62))
        if nome == "exportar":
            linha((cx, S * 0.66), (cx, T))
            linha((S * 0.32, S * 0.32), (cx, T), (S * 0.68, S * 0.32))
        else:
            linha((cx, T), (cx, S * 0.66))
            linha((S * 0.32, S * 0.46), (cx, S * 0.66), (S * 0.68, S * 0.46))
    elif nome == "escudo":
        d.polygon([(cx, S * 0.12), (S * 0.82, S * 0.26), (S * 0.78, S * 0.58), (cx, S * 0.88),
                   (S * 0.22, S * 0.58), (S * 0.18, S * 0.26)], outline=c, width=w)
        linha((S * 0.36, S * 0.50), (S * 0.46, S * 0.60), (S * 0.65, S * 0.40))
    elif nome == "relogio":              # logo do app: cronômetro com varredura
        circulo(cx, S * 0.56, S * 0.34)
        d.pieslice((cx - S * 0.26, S * 0.56 - S * 0.26, cx + S * 0.26, S * 0.56 + S * 0.26),
                   start=-90, end=120, fill=c)
        ret(S * 0.42, S * 0.08, S * 0.58, S * 0.16, preench=True, raio=S * 0.02)
        linha((cx, S * 0.16), (cx, S * 0.22))
    return im.resize((tam, tam), Image.LANCZOS)


NOMES_ICONES = ["play", "stop", "camera", "pasta", "lupa", "mais", "mais_circulo", "selecao", "radar",
         "mover", "centro", "chave", "ajuda", "check", "copiar", "lapis", "lixeira", "cima",
         "baixo", "fechar", "relogio", "escudo", "exportar", "importar"]



def windows_usa_tema_escuro():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as k:
            return winreg.QueryValueEx(k, "AppsUseLightTheme")[0] == 0
    except Exception:
        return False


def logo_app(tam):
    """Ícone do programa: cronômetro amarelo sobre fundo escuro arredondado."""
    S = tam * ESC_ICONE
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, S - 1, S - 1), radius=S * 0.22,
                                         fill=(32, 34, 40, 255))
    rel = desenhar_icone("relogio", "#f1c40f", tam).resize((S, S), Image.LANCZOS)
    m = int(S * 0.14)
    im.alpha_composite(rel.resize((S - 2 * m, S - 2 * m), Image.LANCZOS), (m, m))
    return im.resize((tam, tam), Image.LANCZOS)


def imagem_degrade(larg, alt, cor_topo, cor_base, raio=7, borda=None, faixa=None, so_topo=False):
    """Fundo arredondado com degradê vertical (usado nos botões e nas abas)."""
    E = 4
    W, H = larg * E, alt * E
    c1, c2 = _rgba(cor_topo), _rgba(cor_base)
    grad = Image.new("RGBA", (1, H))
    for y in range(H):
        t = y / max(1, H - 1)
        grad.putpixel((0, y), tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(4)))
    grad = grad.resize((W, H))
    mascara = Image.new("L", (W, H), 0)
    extra = raio * E if so_topo else 0          # aba: só os cantos de cima arredondados
    ImageDraw.Draw(mascara).rounded_rectangle((0, 0, W - 1, H - 1 + extra), radius=raio * E, fill=255)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    im.paste(grad, (0, 0), mascara)
    d = ImageDraw.Draw(im)
    if faixa:                                   # faixa clara no topo (aba selecionada)
        topo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(topo).rectangle((0, 0, W, 3 * E), fill=_rgba(faixa))
        im.paste(topo, (0, 0), Image.composite(mascara, Image.new("L", (W, H), 0),
                                               topo.split()[3]))
    if borda:
        d.rounded_rectangle((E // 2, E // 2, W - 1 - E // 2, H - 1 + extra), radius=raio * E,
                            outline=_rgba(borda), width=E)
    return im.resize((larg, alt), Image.LANCZOS)


# Paleta preto + azul
DEGRADES = {
    #            topo       base       borda      (normal, passar o mouse, apertado)
    "Grad":     (("#0b0f17", "#1e3a8a", "#2f5fd0"), ("#111a2e", "#2754c7", "#5b8cff"),
                 ("#1e3a8a", "#0b0f17", "#2f5fd0")),
    "Destaque": (("#3b82f6", "#1d4ed8", "#60a5fa"), ("#4f93ff", "#2563eb", "#93c5fd"),
                 ("#1d4ed8", "#1e3a8a", "#60a5fa")),
    "Perigo":   (("#ef4444", "#b91c1c", "#f87171"), ("#f75b5b", "#dc2626", "#fca5a5"),
                 ("#b91c1c", "#7f1d1d", "#f87171")),
    "Amarelo":  (("#fde047", "#ca8a04", "#fef08a"), ("#fef08a", "#eab308", "#fef9c3"),
                 ("#ca8a04", "#a16207", "#fde047")),
}
TEXTO_ESCURO = {"Amarelo"}          # estilos claros: texto e ícone escuros


def icone_arredondado(img, T, raio, fundo=None, brilho=None, cinza=False):
    """Ícone no tamanho T com cantos arredondados. Com fundo conhecido (caixa escura) a borda
    fica suave; sem fundo, os cantos viram a cor transparente da janela (sem serrilhado escuro)."""
    im = img.convert("RGB").resize((T, T), Image.NEAREST)
    if cinza:
        im = im.convert("L").convert("RGB")
    if brilho is not None:
        im = ImageEnhance.Brightness(im).enhance(brilho)
    im = sem_cor_chave(im)
    E = 4
    mascara = Image.new("L", (T * E, T * E), 0)
    ImageDraw.Draw(mascara).rounded_rectangle((0, 0, T * E - 1, T * E - 1), radius=raio * E, fill=255)
    mascara = mascara.resize((T, T), Image.LANCZOS)
    if fundo is None:
        mascara = mascara.point(lambda v: 255 if v >= 128 else 0)
        base = Image.new("RGB", (T, T), (1, 1, 1))
    else:
        base = Image.new("RGB", (T, T), fundo)
    base.paste(im, (0, 0), mascara)
    return base


def misturar_cor(a, b, t):
    """Mistura duas cores "#rrggbb" (t=0 -> a, t=1 -> b)."""
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(ca, cb))


def ret_arred(c, x0, y0, x1, y1, r, **kw):
    """Retângulo de cantos arredondados no canvas."""
    r = max(1, min(r, (x1 - x0) / 2, (y1 - y0) / 2))
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
           x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return c.create_polygon(pts, smooth=True, **kw)


# ---------------------------------------------------------------- leitura do AP
# Desenho de cada dígito na fonte da interface do jogo (texto em 1 bit, 8 pixels de altura).
# O programa recorta a área marcada, separa os caracteres e compara com estes modelos.
FONTE_DIGITOS = {
    "/": ['..#', '..#', '.#.', '.#.', '.#.', '.#.', '#..', '#..'],
    "0": ['.###.', '#...#', '#...#', '#...#', '#...#', '#...#', '#...#', '.###.'],
    "1": ['..#', '.##', '#.#', '..#', '..#', '..#', '..#', '..#'],
    "2": ['.###.', '#...#', '....#', '....#', '...#.', '..#..', '.#...', '#####'],
    "3": ['.###.', '#...#', '....#', '..##.', '....#', '....#', '#...#', '.###.'],
    "4": ['...#.', '..##.', '.#.#.', '.#.#.', '#..#.', '#####', '...#.', '...#.'],
    "5": ['.####', '.#...', '#....', '####.', '....#', '....#', '#...#', '.###.'],
    "6": ['.###.', '#...#', '#....', '####.', '#...#', '#...#', '#...#', '.###.'],
    "7": ['#####', '...#.', '...#.', '..#..', '..#..', '.#...', '.#...', '.#...'],
    "8": ['.###.', '#...#', '#...#', '.###.', '#...#', '#...#', '#...#', '.###.'],
    "9": ['.###.', '#...#', '#...#', '#...#', '.####', '....#', '#...#', '.###.']
}
# Mesma coisa para a fonte menor usada DENTRO das barras de HP/SP/AP (7 pixels de altura).
# Os desenhos de 4 e 8 não apareciam nos prints e foram deduzidos dos outros dígitos.
FONTE_DIGITOS_BARRA = {
    "/": ['..#', '..#', '.#.', '.#.', '.#.', '#..', '#..'],
    "0": ['.###.', '#...#', '#...#', '#...#', '#...#', '#...#', '.###.'],
    "1": ['..#', '.##', '#.#', '..#', '..#', '..#', '..#'],
    "2": ['.###.', '#...#', '....#', '...#.', '..#..', '.#...', '#####'],
    "3": ['.###.', '#...#', '....#', '..##.', '....#', '#...#', '.###.'],
    "4": ['...#.', '..##.', '.#.#.', '#..#.', '#####', '...#.', '...#.'],
    "5": ['.####', '.#...', '####.', '#...#', '....#', '#...#', '.###.'],
    "6": ['.###.', '#...#', '####.', '#...#', '#...#', '#...#', '.###.'],
    "7": ['#####', '...#.', '...#.', '..#..', '..#..', '.#...', '.#...'],
    "8": ['.###.', '#...#', '#...#', '.###.', '#...#', '#...#', '.###.'],
    "9": ['.###.', '#...#', '#...#', '#...#', '.####', '#...#', '.###.']
}
_MODELOS_DIGITOS = None


def _modelos_digitos():
    global _MODELOS_DIGITOS
    if _MODELOS_DIGITOS is None:
        _MODELOS_DIGITOS = [(k, np.array([[c == "#" for c in r] for r in v], dtype=bool))
                            for fonte in (FONTE_DIGITOS, FONTE_DIGITOS_BARRA)
                            for k, v in fonte.items()]
    return _MODELOS_DIGITOS


def _glifos(mascara):
    """Separa os caracteres por colunas vazias: [(x, largura, desenho recortado)]."""
    cols = mascara.any(axis=0)
    res, x, W = [], 0, mascara.shape[1]
    while x < W:
        if not cols[x]:
            x += 1
            continue
        ini = x
        while x < W and cols[x]:
            x += 1
        sub = mascara[:, ini:x]
        linhas = np.nonzero(sub.any(axis=1))[0]
        res.append((ini, x - ini, sub[linhas.min():linhas.max() + 1]))
    return res


def _sem_linhas(mascara, comprimento=10):
    """Apaga traços horizontais longos (bordas de barras e janelas), que não são texto."""
    m = mascara.copy()
    for y in range(m.shape[0]):
        linha = m[y]
        if linha.sum() < comprimento:
            continue
        x, W = 0, linha.shape[0]
        while x < W:
            if not linha[x]:
                x += 1
                continue
            ini = x
            while x < W and linha[x]:
                x += 1
            if x - ini >= comprimento:
                m[y, ini:x] = False
    return m


def _faixas(mascara):
    """Separa as linhas de texto (faixas de linhas com pixels, entre linhas vazias)."""
    linhas = mascara.any(axis=1)
    res, y, H = [], 0, mascara.shape[0]
    while y < H:
        if not linhas[y]:
            y += 1
            continue
        ini = y
        while y < H and linhas[y]:
            y += 1
        res.append(mascara[ini:y])
    return res


def _classificar(g):
    """Qual dígito (ou "/") é este desenho? None se não parecer nenhum."""
    h, w = g.shape
    if h < 5 or h > 40 or w > 12:
        return None
    melhor, qual = 1.0, None
    for ch, t in _modelos_digitos():
        th, tw = t.shape
        if (th, tw) == (h, w):                          # mesmo tamanho: compara pixel a pixel
            dif = float((g != t).mean())
        else:
            if abs(w * th / h - tw) > 1.2:             # proporção bem diferente
                continue
            r = np.asarray(Image.fromarray(g.astype(np.uint8) * 255).resize((tw, th),
                                                                          Image.NEAREST)) > 127
            dif = float((r != t).mean()) + 0.04        # tamanho diferente: confia um pouco menos
        if dif < melhor:
            melhor, qual = dif, ch
    return qual if melhor <= 0.18 else None


# Rótulo "AP" da janela Informações básicas (mesma fonte, texto preto): usado para achar a
# linha do AP sozinho, em qualquer lugar da tela, nos dois modos da janela.
ROTULO_AP = ['...#....####.', '..#.#...#...#', '..#.#...#...#', '..#.#...#...#', '.#...#..####.', '.#####..#....', '#.....#.#....', '#.....#.#....']


def achar_rotulos_ap(arr, maximo=12):
    """Todos os lugares onde aparece o rótulo "AP" (texto preto), do canto superior esquerdo
    para baixo/direita — a janela Informações básicas costuma ficar ali."""
    if cv2 is None:
        return []
    preto = (np.asarray(arr)[..., :3].max(axis=2) < 60).astype(np.uint8) * 255
    t = np.array([[c == "#" for c in r] for r in ROTULO_AP], dtype=np.uint8) * 255
    if preto.shape[0] < t.shape[0] or preto.shape[1] < t.shape[1]:
        return []
    r = cv2.matchTemplate(preto, t, cv2.TM_SQDIFF) / (255 * 255)
    ys, xs = np.nonzero(r <= 3)                         # até 3 pixels diferentes
    locais = sorted(zip(xs.tolist(), ys.tolist()), key=lambda p: (p[0] + p[1], p[1]))
    res = []
    for x, y in locais:                                 # junta acertos vizinhos
        if all(abs(x - a) > 3 or abs(y - b) > 3 for a, b in res):
            res.append((x, y))
        if len(res) >= maximo:
            break
    return res


def achar_rotulo_ap(arr):
    """O primeiro rótulo "AP" (mais perto do canto superior esquerdo), ou None."""
    locais = achar_rotulos_ap(arr, maximo=1)
    return locais[0] if locais else None


def localizar_ap(arr):
    """Acha a linha do AP que dá para ler: testa cada rótulo "AP" encontrado (o primeiro pode
    ser outro texto). Devolve ((x, y) do rótulo, (atual, máximo)) ou (None, None)."""
    for x, y in achar_rotulos_ap(arr):
        trecho = arr[max(0, y - 3):y + 12, x + 13:x + 13 + 190]
        lido = ler_fracao(trecho)
        if lido:
            return (x, y), lido
    return None, None


def ler_fracao(arr):
    """Lê "atual / máximo" (ex.: 53 / 200) de um recorte da tela. Devolve (atual, máximo) ou None."""
    a = np.asarray(arr)[..., :3]
    lum = a.mean(axis=2)
    # 1º: só pixels pretos (o texto do jogo é preto puro; a borda azul do preenchimento
    #     da barra, que às vezes passa por cima dos números, não entra)
    for mascara_toda in (a.max(axis=2) < 60, lum < 100, lum > 170):
        if mascara_toda.mean() > 0.5:
            continue
        for mascara in _faixas(_sem_linhas(mascara_toda)):   # cada linha de texto separada
            lido = _ler_linha(mascara)
            if lido:
                return lido
    return None


def _ler_linha(mascara):
    """Procura "número / número" numa linha de texto."""
    if True:
        gl = _glifos(mascara)
        if not gl:
            return None
        tipos = [_classificar(g) for _, _, g in gl]
        alturas = sorted(g.shape[0] for (_, _, g), t in zip(gl, tipos) if t not in (None, "/"))
        altura = alturas[len(alturas) // 2] if alturas else 8
        junto = max(3, int(altura * 0.6))            # espaço entre dígitos do mesmo número

        def numero(indices):
            if not indices or any(tipos[i] in (None, "/") for i in indices):
                return None
            return int("".join(tipos[i] for i in indices))

        for k, t in enumerate(tipos):
            if t != "/":
                continue
            esq, i = [], k - 1
            while i >= 0 and tipos[i] not in (None, "/"):
                fim_ant = gl[i][0] + gl[i][1]
                prox_ini = gl[esq[0]][0] if esq else None
                if prox_ini is not None and prox_ini - fim_ant > junto:
                    break
                esq.insert(0, i)
                i -= 1
            dir_, i = [], k + 1
            while i < len(gl) and tipos[i] not in (None, "/"):
                if dir_ and gl[i][0] - (gl[dir_[-1]][0] + gl[dir_[-1]][1]) > junto:
                    break
                dir_.append(i)
                i += 1
            atual, maximo = numero(esq), numero(dir_)
            if atual is not None and maximo and 0 <= atual <= maximo <= 10_000_000:
                return atual, maximo
        return None


def texto_contorno(canvas, x, y, texto, fonte, cor):
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)):
        canvas.create_text(x + dx, y + dy, text=texto, font=fonte, fill="#000000")
    canvas.create_text(x, y, text=texto, font=fonte, fill=cor)


def ler_tempo(txt):
    """'12' / '4,5' / '1:30' -> segundos. Vazio -> None (aprender). Retorna (valor, valido)."""
    t = txt.strip().replace(",", ".")
    if not t:
        return None, True
    try:
        if ":" in t:
            m, s = t.split(":", 1)
            v = int(m) * 60 + float(s)
        else:
            v = float(t)
    except ValueError:
        return None, False
    return (v, True) if v > 0 else (None, False)


def fmt_tempo(v):
    return "" if v is None else f"{v:g}"


def fmt_aprendido(sk):
    if sk.get("cd"):
        return "usa manual"
    v = sk.get("aprendido")
    return "—" if v is None else f"{v:.1f}s"


def mesclar(padrao, dados):
    out = {}
    for k, v in padrao.items():
        if isinstance(v, dict):
            sub = dados.get(k) if isinstance(dados.get(k), dict) else {}
            out[k] = mesclar(v, sub)
        else:
            out[k] = copy.deepcopy(dados.get(k, v))
    for k, v in dados.items():
        out.setdefault(k, v)
    return out


def ler_json(arq, padrao):
    try:
        return {**padrao, **json.loads(arq.read_text(encoding="utf-8"))}
    except Exception:
        return dict(padrao)


def gravar_json(arq, dados):
    arq.write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8")


# =============================================================== banco de skills

def chave(txt):
    """Normaliza para busca: sem acento, minúsculo."""
    t = unicodedata.normalize("NFKD", txt or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


class Banco:
    def __init__(self):
        self.itens = {}
        self.classes = []
        self.fonte = ""
        try:
            self.meus = json.loads(ARQ_MEUS.read_text(encoding="utf-8"))
        except Exception:
            self.meus = {}
        try:
            dados = json.loads(ARQ_BANCO.read_text(encoding="utf-8"))
        except Exception:
            dados = {}
        self.fonte = dados.get("fonte", "")
        self.por_id = {}
        for classe, lista in dados.get("classes", {}).items():
            self.classes.append(classe)
            for x in lista:
                it = self.por_id.get(x.get("id")) if x.get("id") else None
                if it is None:
                    nome = x.get("nome") or x.get("en")
                    k = chave(nome)
                    if not k:
                        continue
                    it = self.itens.get(k)
                    if it is None:
                        it = {"nome": nome, "pt": bool(x.get("nome")), "en": x.get("en") or "",
                              "cd": None, "classes": [], "id": x.get("id"),
                              "efst": x.get("efst") or []}
                        self.itens[k] = it
                        if x.get("en"):
                            self.itens.setdefault(chave(x["en"]), it)
                    if it["id"]:
                        self.por_id[it["id"]] = it
                if classe not in it["classes"]:
                    it["classes"].append(classe)
                if it["cd"] is None and x.get("cd"):
                    it["cd"] = x["cd"]
        self.ok = bool(self.itens)
        self.dp = None

    def definir_nome(self, sid, nome):
        """Nome em português (vindo da Divine Pride) para uma skill que só tinha nome em inglês."""
        it = self.por_id.get(sid)
        if not it or it["pt"] or not nome:
            return False
        it["nome"], it["pt"] = nome.strip(), True
        self.itens.setdefault(chave(it["nome"]), it)
        return True

    def aplicar_nomes(self, nomes):
        return sum(self.definir_nome(sid, n) for sid, n in nomes.items())

    def sem_nome_pt(self, classe):
        return [it["id"] for it in self.por_id.values()
                if not it["pt"] and (classe == TODAS or classe in it["classes"])]

    def efst_de(self, nome):
        """Ícones de status (buff) da skill: lista de [chave, id]."""
        it = self.itens.get(chave(nome))
        return it.get("efst") or [] if it else []

    def id_de(self, nome):
        it = self.itens.get(chave(nome))
        return it.get("id") if it else None

    def recarga_padrao(self, nome):
        it = self.itens.get(chave(nome))
        return it["cd"] if it else None

    def recarga(self, nome):
        """(segundos, origem): 'sua' (corrigida por você) > 'LATAM' (cliente, via ragassets)
        > 'LATAM' (Divine Pride) > 'padrão' (rAthena)."""
        k = chave(nome)
        m = self.meus.get(k)
        if m and m.get("cd"):
            return m["cd"], "sua"
        it = self.itens.get(k)
        rag = getattr(self, "rag", None)
        if it and rag and it.get("id") in rag.cds:
            return rag.cds[it["id"]], "LATAM"
        if it and self.dp and it.get("id") in self.dp.cds:
            return self.dp.cds[it["id"]], "LATAM"
        if it and it["cd"]:
            return it["cd"], "padrão"
        return None, None

    def existe(self, nome):
        k = chave(nome)
        return k in self.itens or k in self.meus

    def buscar(self, texto, classe=TODAS, limite=400, so_buffs=False):
        """Busca pelo nome em português ou em inglês, sem ligar para acentos."""
        q = chave(texto)
        unicos = {id(it): it for it in self.itens.values()}
        res = []
        for it in unicos.values():
            if so_buffs and not it.get("efst"):
                continue
            if classe and classe != TODAS and classe not in it["classes"]:
                continue
            kn, ke = chave(it["nome"]), chave(it.get("en"))
            if q and q not in kn and q not in ke:
                continue
            ordem = 0 if (kn.startswith(q) or ke.startswith(q)) else 1
            res.append((ordem, not it.get("pt", True), kn, it))
        if not so_buffs:
            for k, m in self.meus.items():
                if k not in self.itens and (not q or q in k):
                    res.append((0 if k.startswith(q) else 1, False, k,
                                {"nome": m["nome"], "cd": None, "classes": [], "pt": True}))
        res.sort(key=lambda r: (r[0], r[1], r[2]))
        return [r[3] for r in res[:limite]]

    def salvar_meu(self, nome, cd):
        k = chave(nome)
        if not k or re.fullmatch(r"skill \d+", k):
            return
        padrao = self.itens.get(k, {}).get("cd")
        if cd is None or cd == padrao:
            if self.meus.pop(k, None) is None:
                return
        else:
            self.meus[k] = {"nome": nome.strip(), "cd": cd}
        try:
            gravar_json(ARQ_MEUS, self.meus)
        except Exception:
            pass


def _segundos(v):
    """Converte o valor de recarga da API (número ou texto) para segundos."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        x = float(v)
        return x / 1000 if x > 300 else x
    if isinstance(v, str):
        nums = re.findall(r"\d+(?:[.,]\d+)?", v)
        if not nums:
            return None
        x = float(nums[-1].replace(",", "."))
        low = v.lower()
        if "ms" in low:
            x /= 1000
        elif x > 300 and not re.search(r"\d\s*(s|sec|seg)", low):
            x /= 1000
        return x
    if isinstance(v, list) and v:
        return _segundos(v[-1])
    if isinstance(v, dict):
        for k in ("value", "time", "seconds"):
            if k in v:
                return _segundos(v[k])
    return None


def extrair_recarga(d):
    """Recarga no nível máximo a partir da resposta da Divine Pride."""
    melhor = None
    lt = d.get("levelTable") if isinstance(d, dict) else None
    if isinstance(lt, list):
        def nivel(e):
            for k in ("level", "skillLevel", "lv", "Level"):
                if isinstance(e.get(k), (int, float)):
                    return e[k]
            return 0
        linhas = [e for e in lt if isinstance(e, dict)]
        if linhas:
            ult = max(linhas, key=nivel)
            for k, v in ult.items():
                if "cool" in k.lower():
                    melhor = _segundos(v)
                    break
    if melhor is None and isinstance(d, dict):
        melhor = _segundos(d.get("cooldown"))
    return round(melhor, 2) if melhor and melhor > 0 else None


class DivinePride:
    """Busca recarga e ícone de cada skill que você usa (servidor LATAM) e guarda no PC.
    Só pede à API as skills dos seus perfis, uma por vez e com cache, como a API pede."""

    def __init__(self, chave_api):
        self.chave = (chave_api or "").strip()
        self.fila = queue.Queue()
        self.pedidos = queue.Queue()
        self.cds = {}
        PASTA_DP.mkdir(exist_ok=True)
        self.nomes = {}
        for arq in PASTA_DP.glob("skill_*.json"):
            try:
                sid = int(arq.stem.split("_")[1])
                dados = json.loads(arq.read_text(encoding="utf-8"))
                cd = extrair_recarga(dados)
                if cd:
                    self.cds[sid] = cd
                if isinstance(dados, dict) and dados.get("name"):
                    self.nomes[sid] = dados["name"]
            except Exception:
                pass
        self._ultimo = 0.0
        threading.Thread(target=self._trabalhar, daemon=True).start()

    def ativo(self):
        return bool(self.chave)

    def icone(self, sid):
        p = PASTA_DP / f"icone_{sid}.png"
        return p if sid and p.exists() else None

    def pedir(self, sid, motivo):
        if sid and (self.ativo() or (PASTA_DP / f"skill_{sid}.json").exists()):
            self.pedidos.put((int(sid), motivo))

    def icone_efst(self, eid):
        p = PASTA_DP / f"efst_icone_{eid}.png"
        return p if p.exists() else None

    def pedir_efst(self, eid, chave_esperada, motivo):
        """Ícone de um buff (status). Confere se o id da Divine Pride é mesmo o esperado."""
        if self.ativo() or self.icone_efst(eid):
            self.pedidos.put((("efst", int(eid), chave_esperada), motivo))

    def _trabalhar_efst(self, eid, esperada, motivo):
        arq = PASTA_DP / f"efst_{eid}.json"
        ico = PASTA_DP / f"efst_icone_{eid}.png"
        try:
            if arq.exists():
                dados = json.loads(arq.read_text(encoding="utf-8"))
            else:
                if not self.ativo():
                    raise ValueError("sem chave da API")
                url = DP_URL_EFST.format(id=eid) + "?apiKey=" + urllib.parse.quote(self.chave)
                dados = self._abrir(url)
                registrar(f"Divine Pride: buff {eid} recebido: "
                          + json.dumps(dados, ensure_ascii=False)[:1000])
                chave_site = str(dados.get("key") or "") if isinstance(dados, dict) else ""
                if esperada and chave_site and chave_site.upper() != esperada.upper():
                    raise ValueError(f"o ícone {eid} na Divine Pride é {chave_site}, "
                                     f"não {esperada}")
                arq.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
            url_ico = dados.get("iconUrl") if isinstance(dados, dict) else None
            if url_ico and not ico.exists() and self.ativo():
                ico.write_bytes(self._abrir(url_ico, json_=False))
            if not ico.exists():
                raise ValueError("ícone não disponível")
            self.fila.put(("ok", ("efst", eid), None, motivo, dados.get("name")))
        except Exception as e:
            registrar(f"Divine Pride: erro no buff {eid}: {e}")
            self.fila.put(("erro", ("efst", eid), str(e), motivo, None))

    def _abrir(self, url, json_=True):
        req = urllib.request.Request(url, headers={
            "Accept-Language": "pt", "x-server": "LATAM",
            "User-Agent": "RO-Cooldown-Overlay/1.0 (ferramenta pessoal)"})
        for tentativa in range(3):
            espera = 1.2 - (time.monotonic() - self._ultimo)
            if espera > 0:
                time.sleep(espera)
            self._ultimo = time.monotonic()
            try:
                with urllib.request.urlopen(req, timeout=15) as r:
                    dados = r.read()
                return json.loads(dados.decode("utf-8")) if json_ else dados
            except urllib.error.HTTPError as e:
                if e.code == 429 and tentativa < 2:
                    time.sleep(min(60, int(e.headers.get("Retry-After") or 10)))
                    continue
                if e.code == 401:
                    raise ValueError("chave da API inválida (401)")
                if e.code == 404:
                    raise ValueError("skill não encontrada na Divine Pride (404)")
                raise ValueError(f"erro HTTP {e.code}")
        raise ValueError("limite de pedidos da API; tente mais tarde")

    def _trabalhar(self):
        while True:
            sid, motivo = self.pedidos.get()
            if isinstance(sid, tuple):                      # ícone de buff
                self._trabalhar_efst(sid[1], sid[2], motivo)
                continue
            arq = PASTA_DP / f"skill_{sid}.json"
            try:
                if arq.exists() and time.time() - arq.stat().st_mtime < 30 * 86400:
                    dados = json.loads(arq.read_text(encoding="utf-8"))
                else:
                    if not self.ativo():
                        raise ValueError("sem chave da API")
                    url = DP_URL.format(id=sid) + "?apiKey=" + urllib.parse.quote(self.chave)
                    dados = self._abrir(url)
                    arq.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
                    registrar(f"Divine Pride: skill {sid} recebida: "
                              + json.dumps(dados, ensure_ascii=False)[:2000])
                cd = extrair_recarga(dados)
                if cd:
                    self.cds[sid] = cd
                if isinstance(dados, dict) and dados.get("name"):
                    self.nomes[sid] = dados["name"]
                ico = PASTA_DP / f"icone_{sid}.png"
                url_ico = dados.get("iconUrl") if isinstance(dados, dict) else None
                if url_ico and not ico.exists() and self.ativo() and motivo == "buscar":
                    ico.write_bytes(self._abrir(url_ico, json_=False))
                self.fila.put(("ok", sid, cd, motivo, dados.get("name") if isinstance(dados, dict) else None))
            except Exception as e:
                registrar(f"Divine Pride: erro na skill {sid}: {e}")
                self.fila.put(("erro", sid, str(e), motivo, None))


PASTA_RAG = PASTA / "cache_ragassets"
RAG_URL = "https://assets.latam-tools.com.br"


class RagAssets:
    """Fonte principal de ícones e nomes: ragassets (latam-tools), que tira tudo do próprio
    cliente LATAM. Não precisa de chave. Cada arquivo é baixado uma vez e guardado no PC.
    Se o servidor falhar ou não responder, fica 10 minutos sem tentar e o programa usa as
    outras fontes (Divine Pride, banco local, captura da tela)."""

    def __init__(self, ligado=True):
        self.ligado = ligado
        self.fila = queue.Queue()
        self.pedidos = queue.Queue()
        self.nomes = {}
        self.cds = {}
        self.estado = "ainda não usado"
        self._fora_ate = 0.0
        PASTA_RAG.mkdir(exist_ok=True)
        try:
            dados = json.loads((PASTA_RAG / "skills.json").read_text(encoding="utf-8"))
            self._ler_tabela(dados)
        except Exception:
            pass
        threading.Thread(target=self._trabalhar, daemon=True).start()

    def _ler_tabela(self, dados):
        """skills.json do cliente: nomes em português e recarga oficial no nível máximo."""
        nomes, cds = {}, {}
        for x in dados:
            sid = x.get("id")
            if not sid:
                continue
            if x.get("name"):
                nomes[int(sid)] = x["name"]
            cd = (x.get("delay") or {}).get("cooldown") or []
            if isinstance(cd, list) and cd and isinstance(cd[-1], (int, float)) and cd[-1] > 0:
                cds[int(sid)] = round(cd[-1] / 1000, 2)
        self.nomes, self.cds = nomes, cds

    def disponivel(self):
        return self.ligado and time.monotonic() >= self._fora_ate

    def icone_status(self, eid):
        p = PASTA_RAG / f"status_{eid}.png"
        return p if p.exists() else None

    def icone_skill(self, sid):
        p = PASTA_RAG / f"skill_{sid}.png"
        return p if sid and p.exists() else None

    def pedir(self, tipo, ident, motivo):
        """tipo: "status" (ícone de buff pelo id EFST), "skill" (ícone) ou "nomes"."""
        self.pedidos.put((tipo, ident, motivo))

    def _baixar(self, caminho, timeout=8):
        if not self.disponivel():
            raise ConnectionError("ragassets indisponível no momento")
        req = urllib.request.Request(RAG_URL + caminho, headers={
            "User-Agent": f"RO-Cooldown-Overlay/{VERSAO} (ferramenta pessoal)"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                dados = r.read()
            self.estado = "funcionando"
            return dados
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise FileNotFoundError("não existe no ragassets")
            self._fora(f"erro HTTP {e.code}")
            raise
        except Exception as e:
            self._fora(str(e)[:80])
            raise

    def _fora(self, motivo):
        self._fora_ate = time.monotonic() + 600
        self.estado = "sem resposta agora; usando as outras fontes (detalhes no log)"
        registrar(f"ragassets: {motivo} — usando as outras fontes por 10 minutos.", chave_rep="rag")

    def _trabalhar(self):
        while True:
            tipo, ident, motivo = self.pedidos.get()
            try:
                if not self.ligado:
                    raise ConnectionError("ragassets desligado nas opções")
                if tipo == "nomes":
                    arq = PASTA_RAG / "skills.json"
                    if not arq.exists() or time.time() - arq.stat().st_mtime > 7 * 86400:
                        arq.write_bytes(self._baixar("/raw/skills.json", timeout=20))
                    dados = json.loads(arq.read_text(encoding="utf-8"))
                    self._ler_tabela(dados)
                else:
                    pasta_tipo = "status" if tipo == "status" else "skill"
                    arq = PASTA_RAG / f"{pasta_tipo}_{ident}.png"
                    if not arq.exists():
                        dados = self._baixar(f"/icons/{pasta_tipo}/{int(ident)}.png")
                        Image.open(io.BytesIO(dados)).load()          # confere que é imagem
                        arq.write_bytes(dados)
                self.fila.put(("ok", tipo, ident, motivo))
            except Exception as e:
                self.fila.put(("erro", tipo, ident, motivo, str(e)))


def icone_dp_rgb(caminho):
    """Ícone da Divine Pride (com transparência) sobre fundo escuro, em RGB."""
    im = Image.open(caminho).convert("RGBA")
    fundo = Image.new("RGBA", im.size, (40, 40, 48, 255))
    fundo.alpha_composite(im)
    return fundo.convert("RGB")


class CapturaAuto:
    """Salva sozinha cada versão nova do ícone de um buff (ex.: Brisa Leve de cada elemento).

    Como funciona: acha na tela uma versão já conhecida do buff e guarda a coluna de buffs.
    Quando ela some (você usou o buff com outro elemento), compara a coluna de antes com a de
    depois: o pedaço novo, parado e que não existia antes é o ícone novo."""

    def __init__(self, painel, bf):
        self.p, self.bf = painel, bf
        self.top = top = tk.Toplevel(painel.win)
        top.title(f"Captura automática — {bf.get('nome')}")
        top.configure(bg=painel.cor_fundo)
        top.attributes("-topmost", True)
        top.resizable(False, False)
        top.geometry("+40+40")
        f = ttk.Frame(top)
        f.pack(fill="both", expand=True, padx=14, pady=12)
        ttk.Label(f, text=f"Capturando versões de: {bf.get('nome')}",
                  style="Titulo.TLabel").pack(anchor="w")
        ttk.Label(f, style="Dica.TLabel", wraplength=360, justify="left",
                  text="1. No jogo, deixe o buff ativo com um elemento que já está salvo.\n"
                       "2. Use o buff de novo com OUTRO elemento. A versão nova é salva sozinha.\n"
                       "3. Repita com cada elemento e clique em Concluir.").pack(anchor="w", pady=(4, 8))
        self.lbl = ttk.Label(f, text="Procurando o buff na tela…", wraplength=360, justify="left")
        self.lbl.pack(anchor="w")
        self.lbl_n = ttk.Label(f, style="Titulo.TLabel")
        self.lbl_n.pack(anchor="w", pady=(6, 8))
        painel.bt(f, "Concluir", "check", self.concluir, destaque=True).pack(anchor="e")
        top.protocol("WM_DELETE_WINDOW", self.concluir)
        self.salvas = 0
        self.estado = "procurando"
        self.antes = None
        self.loc = None
        self.sumiu = None
        self.depois = []
        self.t_troca = 0.0
        self.sct = nova_captura()
        self._atualizar_contagem()
        top.after(100, self._esconder_da_captura)
        self.vivo = True
        self._tick()

    def _esconder_da_captura(self):
        try:
            user32.SetWindowDisplayAffinity(hwnd_de(self.top), WDA_EXCLUDEFROMCAPTURE)
        except Exception:
            pass

    def _atualizar_contagem(self):
        n = len(self.bf.get("variantes", []))
        self.lbl_n.config(text=f"Versões salvas: {n}" + (f"  (+{self.salvas} agora)" if self.salvas else ""))

    def _achar_conhecida(self, g, wm, brilho):
        """Melhor versão conhecida na área: (semelhança, x, y, w, h, qual).
        Versões vindas da Divine Pride só contam onde há moldura de ícone de buff."""
        melhor = (0.0, 0, 0, 0, 0, -1)
        imgs = self.bf.get("_imgs", [])
        t_c = self.bf.get("_tmpls", [])
        t_b = self.bf.get("_tmpls_b") or [None] * len(t_c)
        site = self.bf.get("_site") or [False] * len(t_c)
        for qual, (im, tc, tb, do_site) in enumerate(zip(imgs, t_c, t_b, site)):
            w, h = im.size
            tela, t = (wm, tb) if tb is not None else (g, tc)
            if t.shape[0] > tela.shape[0] or t.shape[1] > tela.shape[1]:
                continue
            mx, my = (w - t.shape[1]) // 2, (h - t.shape[0]) // 2
            r = cv2.matchTemplate(tela, t, cv2.TM_CCOEFF_NORMED)
            for v, loc in picos(r, n=4 if do_site else 1):
                if v <= melhor[0]:
                    break
                if not do_site or tem_moldura(brilho, loc[0] - mx, loc[1] - my, w, h):
                    melhor = (v, loc[0] - mx, loc[1] - my, w, h, qual)
                    break
        return melhor

    def _faixa(self, g, wm):
        x, _, w = self.loc[0], self.loc[1], self.loc[2]
        self.fx0 = max(0, x - 3)
        self.fx1 = min(g.shape[1], x + w + 3)
        return (g[:, self.fx0:self.fx1].copy(), wm[:, self.fx0:self.fx1].copy())

    def _tick(self):
        if not self.vivo:
            return
        try:
            self._passo()
        except Exception:
            registrar("Erro na captura automática:\n" + traceback.format_exc(), chave_rep="auto")
        self.top.after(250, self._tick)

    def _passo(self):
        regiao = self.p.overlay._area_buffs()
        if not regiao:
            self.lbl.config(text="Não encontrei a janela do jogo. Abra o Ragnarok.")
            return
        shot = self.sct.grab(regiao)
        rgb = Image.frombytes("RGB", shot.size, shot.rgb)
        arr = np.asarray(rgb)
        g = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        wm = mapa_simbolo(arr)
        agora = time.monotonic()
        v, x, y, w, h, qual = self._achar_conhecida(g, cv2.GaussianBlur(wm, (3, 3), 0),
                                                    arr.max(axis=2))
        visivel = v >= LIMIAR_BUFF
        vs = self.bf.get("variantes", [])
        if visivel and 0 <= qual < len(vs) and vs[qual].startswith("buff_site_"):
            self._confirmar(qual, rgb.crop((x, y, x + w, y + h)))
            self.lbl.config(text="✓ Ícone confirmado com a sua tela. Use o buff com o próximo elemento.")
        elif visivel and self.estado == "pronto" and getattr(self, "qual", qual) != qual:
            self.lbl.config(text="Esse elemento já estava salvo. Use outro elemento.")
        if visivel:
            self.qual = qual

        if self.estado == "procurando":
            if visivel:
                self.loc = (x, y, w, h)
                self.antes = self._faixa(g, wm)
                self.estado = "pronto"
                self.lbl.config(text="✓ Buff encontrado. Agora use-o com OUTRO elemento.")
            else:
                self.lbl.config(text="Deixe o buff ativo no jogo com um elemento já salvo…")
        elif self.estado == "pronto":
            if visivel:
                self.loc = (x, y, w, h)
                self.antes = self._faixa(g, wm)
                self.sumiu = None
            elif self.sumiu is None:
                self.sumiu = agora
            elif agora - self.sumiu > 0.4:
                self.estado, self.depois, self.t_troca = "trocou", [], agora
                self.lbl.config(text="Troca detectada, lendo o ícone novo…")
        elif self.estado == "trocou":
            if visivel:
                self.estado, self.sumiu = "pronto", None
                self.lbl.config(text="Esse elemento já estava salvo. Use outro elemento.")
                return
            if agora - self.t_troca >= 0.5:
                self.depois.append(((g[:, self.fx0:self.fx1].copy(),
                                     wm[:, self.fx0:self.fx1].copy()), rgb))
                self.depois = self.depois[-3:]
            if len(self.depois) == 3:
                # primeiro pelos traços claros (ignora o fundo), depois pelos tons de cinza
                novo = self._achar_novo(1) or self._achar_novo(0)
                if novo is not None:
                    recorte, topo = novo
                    self._salvar(recorte)                              # (atualiza self.qual)
                    # já fica pronto para a próxima troca, com o ícone novo como referência
                    self.loc = (self.loc[0], topo, self.loc[2], self.loc[3])
                    self.antes = self.depois[-1][0]
                    self.estado, self.sumiu = "pronto", None
                    return
            if agora - self.t_troca > 5:
                self.estado = "procurando"
                self.lbl.config(text="Não consegui ler o ícone novo. Tente de novo, "
                                     "ou use \"+ Ícone\" para marcar à mão.")

    def _achar_novo(self, canal):
        """Acha na coluna de buffs o ícone que não existia antes.

        canal 1 = só os traços claros do desenho (o fundo atrás do ícone não atrapalha);
        canal 0 = tons de cinza (para ícones sem traços claros).
        Os ícones de buff ficam numa grade (mesma coluna, distância fixa). Quando um buff sai,
        os de baixo sobem uma casa, o que revela o passo da grade; o ícone novo é a casa cujo
        conteúdo não existia na coluna de antes."""
        lx, ly, w, h = self.loc
        xo = lx - self.fx0
        A = [d[0][canal] for d in self.depois]
        B = self.antes[canal]
        if A[-1].shape[1] < xo + w or B.shape[1] < w:
            return None
        conv = (lambda im: mapa_simbolo(np.asarray(im))) if canal == 1 else (
            lambda im: np.asarray(im.convert("L")))
        conhecidos = [conv(im).astype(np.float32)
                      for im in self.bf.get("_imgs", []) if im.size == (w, h)]
        if B.std() < 2 and A[-1].std() < 2:
            return None                                     # nada desenhado nesta forma de ver
        # Filtros rápidos por janela (somas acumuladas por linha):
        # textura (desvio) e estabilidade entre os quadros (diferença média)
        col = A[-1][:, xo:xo + w].astype(np.float32)
        n_px = float(h * w)
        def janelas(v):
            c = np.concatenate([[0.0], np.cumsum(v)])
            return (c[h:] - c[:-h]) / n_px
        media = janelas(col.sum(axis=1))
        desvio = np.sqrt(np.maximum(janelas((col * col).sum(axis=1)) - media ** 2, 0))
        mexe = np.zeros_like(media)
        for a in A[:-1]:
            mexe = np.maximum(mexe, janelas(np.abs(col - a[:, xo:xo + w].astype(np.float32)).sum(axis=1)))
        if B.shape[0] == col.shape[0] and B.shape[1] >= xo + w:
            # igual a antes no mesmo lugar = nada mudou ali (não precisa analisar)
            mudou = janelas(np.abs(col - B[:, xo:xo + w].astype(np.float32)).sum(axis=1)) >= 6
        else:
            mudou = np.ones_like(media, dtype=bool)
        explic = {}                 # posição -> quanto o conteúdo já existia antes (0 a 1)
        for yy in np.nonzero((desvio >= 5) & (mexe < 6) & mudou)[0]:
            yy = int(yy)                                    # (liso = fundo; mexendo = cenário)
            jan = A[-1][yy:yy + h, xo:xo + w]
            jf = jan.astype(np.float32)
            if any(_ncc(jf, c) >= 0.8 for c in conhecidos):
                continue                                    # versão que já temos
            explic[yy] = float(cv2.matchTemplate(B, jan, cv2.TM_CCOEFF_NORMED).max())
        if not explic:
            return None

        # Quando um buff sai, os de baixo sobem uma "casa": isso revela o passo da grade
        passo = self._passo_coluna(A[-1], B, ly, h, xo, w)
        candidatos = []
        if passo:
            for k in range(0, 40):
                yy = ly + k * passo
                if yy in explic and explic[yy] < 0.85:
                    candidatos.append(yy)
        if not candidatos and ly in explic and explic[ly] < 0.85:
            candidatos = [ly]                               # trocou no mesmo lugar
        if not candidatos:
            candidatos = [y for y, r in explic.items() if r < 0.85]
        if not candidatos:
            return None
        topo = min(candidatos, key=lambda y: explic[y])
        rgb = self.depois[-1][1]
        return rgb.crop((self.fx0 + xo, topo, self.fx0 + xo + w, topo + h)), topo

    @staticmethod
    def _passo_coluna(A, B, ly, h, xo, w):
        """Distância entre ícones da coluna, medida pelos ícones que subiram uma casa.
        Vence a distância em que mais ícones de antes reaparecem idênticos uma casa acima."""
        H = min(A.shape[0], B.shape[0])
        melhor, passo = (0, 0.0), None
        for st in range(h, h + 13):
            iguais, soma = 0, 0.0
            for k in range(0, 8):
                ya, yb = ly + k * st, ly + (k + 1) * st
                if yb + h > H:
                    break
                bw = B[yb:yb + h, xo:xo + w]
                if bw.std() < 5:
                    continue                 # casa sem desenho claro: não dá para comparar
                v = _ncc(A[ya:ya + h, xo:xo + w].astype(np.float32), bw.astype(np.float32))
                if v >= 0.9:
                    iguais += 1
                    soma += v
            if (iguais, soma) > melhor:
                melhor, passo = (iguais, soma), st
        return passo if melhor[0] >= 1 else None

    def _limpar_site(self):
        """Com versões reais para todos os ícones do buff, as do site que sobraram saem."""
        vs = self.bf.get("variantes", [])
        reais = sum(not v.startswith("buff_site_") for v in vs)
        if not self.bf.get("efst") or reais < len(self.bf["efst"]):
            return
        pasta = Perfis.pasta(self.p.nome)
        listas = [self.bf.setdefault(k, []) for k in ("_imgs", "_tmpls", "_tmpls_b", "_site")]
        sobras = [i for i, v in enumerate(vs) if v.startswith("buff_site_")]
        for i in sobras[::-1]:
            (pasta / vs[i]).unlink(missing_ok=True)
            vs.pop(i)
            for lst in listas:
                if i < len(lst):
                    lst.pop(i)
        if sobras:
            self.qual = -1
            self.p.salvar_agora()

    def _confirmar(self, qual, recorte):
        """Troca a versão baixada do site pelo recorte real da tela (mesmo elemento)."""
        pasta = Perfis.pasta(self.p.nome)
        vs = self.bf["variantes"]
        arq = f"buff_{time.time_ns()}.png"
        recorte.save(pasta / arq)
        (pasta / vs[qual]).unlink(missing_ok=True)
        vs[qual] = arq
        cinza_m, branco_m = modelos_buff(recorte)
        for k, val in (("_imgs", recorte), ("_tmpls", cinza_m), ("_tmpls_b", branco_m),
                       ("_site", False)):
            self.bf[k][qual] = val
        self.salvas += 1
        self._limpar_site()
        self._atualizar_contagem()
        self.p.salvar_agora()

    def _salvar(self, recorte):
        pasta = Perfis.pasta(self.p.nome)
        arq = f"buff_{time.time_ns()}.png"
        recorte.save(pasta / arq)
        cinza_m, branco_m = modelos_buff(recorte)
        vs = self.bf.setdefault("variantes", [])
        listas = [self.bf.setdefault(k, []) for k in ("_imgs", "_tmpls", "_tmpls_b", "_site")]
        # Se for o mesmo elemento de uma versão baixada da Divine Pride, substitui ela
        alvo, melhor = None, 0.55
        nova = mapa_simbolo_suave(np.asarray(recorte))
        nova_c = np.ascontiguousarray(nova[3:-3, 3:-3])          # tolera 3 px de deslocamento
        for i, (v, im) in enumerate(zip(vs, listas[0])):
            if not v.startswith("buff_site_") or nova_c.size == 0:
                continue
            ref = mapa_simbolo_suave(np.asarray(im.resize(recorte.size, Image.BILINEAR)))
            if ref.std() < 2:
                continue
            s_ = float(cv2.matchTemplate(ref, nova_c, cv2.TM_CCOEFF_NORMED).max())
            if s_ > melhor:
                alvo, melhor = i, s_
        valores = (recorte, cinza_m, branco_m, False)
        if alvo is not None:
            (pasta / vs[alvo]).unlink(missing_ok=True)
            vs[alvo] = arq
            for lst, val in zip(listas, valores):
                lst[alvo] = val
            self.qual = alvo
        else:
            vs.append(arq)
            for lst, val in zip(listas, valores):
                lst.append(val)
            self.qual = len(vs) - 1
        self._limpar_site()
        self.salvas += 1
        self._atualizar_contagem()
        self.lbl.config(text="✓ Versão nova salva! Use o buff com o próximo elemento.")
        self.p.salvar_agora()

    def concluir(self):
        self.vivo = False
        try:
            self.sct.close()
        except Exception:
            pass
        self.top.destroy()
        self.p.salvar_agora()
        self.p.overlay.carregar_perfil(self.p.perfil, Perfis.pasta(self.p.nome))
        self.p.montar_buffs()
        self.p.status(f"{self.bf.get('nome')}: {len(self.bf.get('variantes', []))} versão(ões) "
                      f"de ícone ({self.salvas} nova(s)).")


class SeletorSkill:
    """Janela de busca: digite parte do nome, escolha e a recarga vem junto."""

    def __init__(self, painel, sk, nova=False, buff=False):
        self.painel = painel
        self.sk = sk or {}
        self.nova = nova
        self.buff = buff
        sk = self.sk
        b = painel.banco
        self.top = top = tk.Toplevel(painel.win)
        top.title("Escolher buff" if buff else "Escolher skill")
        top.geometry("600x480")
        top.configure(bg=painel.cor_fundo)
        top.transient(painel.win)
        top.grab_set()

        l1 = ttk.Frame(top)
        l1.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Label(l1, text="Buscar:").pack(side="left")
        self.var_q = tk.StringVar(value=sk.get("nome", "") if b.existe(sk.get("nome", "")) else "")
        ent = ttk.Entry(l1, textvariable=self.var_q, width=28)
        ent.pack(side="left", padx=6)
        ttk.Label(l1, text="Classe:").pack(side="left", padx=(8, 0))
        self.var_cl = tk.StringVar(value=painel.perfil.get("classe", TODAS))
        cb = ttk.Combobox(l1, textvariable=self.var_cl, state="readonly", width=20,
                          values=[TODAS] + b.classes)
        cb.pack(side="left", padx=6)

        cont = ttk.Frame(top)
        cont.pack(fill="both", expand=True, padx=8, pady=4)
        self.tv = ttk.Treeview(cont, columns=("nome", "cd", "classes"), show="headings",
                               selectmode="browse")
        for col, txt, larg in (("nome", "Skill", 200), ("cd", "Recarga", 90),
                               ("classes", "Classes", 220)):
            self.tv.heading(col, text=txt)
            self.tv.column(col, width=larg, anchor="w" if col != "cd" else "center")
        sb = ttk.Scrollbar(cont, orient="vertical", command=self.tv.yview)
        self.tv.configure(yscrollcommand=sb.set)
        self.tv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        rodape = ttk.Frame(top)
        rodape.pack(fill="x", padx=8, pady=(4, 8))
        aviso = ("Recarga padrão sem equipamentos. Se você corrigir o valor depois, "
                 "o programa lembra (aparece como \"sua\").") if b.ok else (
                 "Arquivo banco_skills.json não encontrado na pasta do programa.")
        ttk.Label(rodape, text=aviso, style="Dica.TLabel", wraplength=300).pack(side="left")
        painel.bt(rodape, "Usar", "check", self.usar, destaque=True).pack(side="right")
        painel.bt(rodape, "Cancelar", "fechar", top.destroy).pack(side="right", padx=6)

        self.mapa = {}
        self.var_q.trace_add("write", lambda *_: self.atualizar())
        cb.bind("<<ComboboxSelected>>", lambda _e: (painel.pedir_nomes(self.var_cl.get()),
                                                    self.atualizar()))
        self.tv.bind("<Double-1>", lambda _e: self.usar())
        top.bind("<Return>", lambda _e: self.usar())
        top.bind("<Escape>", lambda _e: top.destroy())
        top.bind("<Down>", self._descer)
        self.atualizar()
        ent.focus_set()
        self._nomes_vistos = painel._nomes_recebidos
        top.after(1500, self._vigiar_nomes)

    def _vigiar_nomes(self):
        """Atualiza a lista quando chegam nomes em português da Divine Pride."""
        if not self.top.winfo_exists():
            return
        if self.painel._nomes_recebidos != self._nomes_vistos:
            self._nomes_vistos = self.painel._nomes_recebidos
            self.atualizar()
        self.top.after(1500, self._vigiar_nomes)

    def atualizar(self):
        self.tv.delete(*self.tv.get_children())
        self.mapa.clear()
        for it in self.painel.banco.buscar(self.var_q.get(), self.var_cl.get(), so_buffs=self.buff):
            if self.buff:
                n = len(it.get("efst") or [])
                txt_cd = f"{n} ícones" if n > 1 else "1 ícone"
            else:
                cd, origem = self.painel.banco.recarga(it["nome"])
                txt_cd = "—" if cd is None else f"{cd:g} s" + (
                    f" ({origem})" if origem in ("sua", "LATAM") else "")
            classes = ", ".join(it["classes"][:3]) + ("…" if len(it["classes"]) > 3 else "")
            nome_vis = it["nome"] if it.get("pt", True) else f"{it['nome']} (inglês)"
            iid = self.tv.insert("", "end", values=(nome_vis, txt_cd, classes))
            self.mapa[iid] = it
        filhos = self.tv.get_children()
        if filhos:
            self.tv.selection_set(filhos[0])

    def _descer(self, _e):
        if self.tv.focus_get() is not self.tv and self.tv.get_children():
            self.tv.focus_set()
            self.tv.focus(self.tv.selection()[0] if self.tv.selection() else self.tv.get_children()[0])

    def usar(self):
        sel = self.tv.selection()
        if not sel:
            return
        it = self.mapa[sel[0]]
        self.top.destroy()
        if self.buff:
            self.painel.adicionar_buff_por_nome(it["nome"])
        elif self.nova:
            self.painel.adicionar_por_nome(it["nome"])
        else:
            self.painel.aplicar_skill(self.sk, it["nome"])


# =============================================================== perfis

def nome_seguro(nome):
    return re.sub(r'[<>:"/\\|?*]', "_", (nome or "")).strip().strip(".")


class Perfis:
    @staticmethod
    def listar():
        PASTA_PERFIS.mkdir(exist_ok=True)
        return sorted(p.name for p in PASTA_PERFIS.iterdir() if (p / "perfil.json").exists())

    @staticmethod
    def pasta(nome):
        return PASTA_PERFIS / nome

    @staticmethod
    def carregar(nome):
        try:
            dados = json.loads((PASTA_PERFIS / nome / "perfil.json").read_text(encoding="utf-8"))
        except Exception:
            dados = {}
        perfil = mesclar(PERFIL_PADRAO, dados)
        if dados and dados.get("versao", 3) < 4:
            D = perfil["deteccao"]
            D["fps"] = max(D["fps"], 30)
            D["limiar_pronto"] = round(D["limiar_delay"] * 0.3, 3)
            perfil["versao"] = 4
        if dados and dados.get("versao", 3) < 5:
            # visual padrão: estilo Moderno, sem caixa escura e sem nomes
            perfil["layout"].update(estilo="moderno", fundo_painel=False, mostrar_nomes=False)
            perfil["versao"] = 5
        if dados and dados.get("versao", 3) < 6:
            # na 1.0.8 marcar o AP era obrigatório; agora o programa acha sozinho
            perfil["area_ap"] = None
            perfil["versao"] = 6
        return perfil

    @staticmethod
    def salvar(nome, perfil):
        pasta = PASTA_PERFIS / nome
        pasta.mkdir(parents=True, exist_ok=True)
        limpo = {k: v for k, v in perfil.items() if k not in ("skills", "buffs")}
        for chave_lista in ("skills", "buffs"):
            limpo[chave_lista] = [{k: v for k, v in s.items() if not k.startswith("_")}
                                  for s in perfil.get(chave_lista, [])]
        gravar_json(pasta / "perfil.json", limpo)

    @staticmethod
    def criar(nome):
        Perfis.salvar(nome, copy.deepcopy(PERFIL_PADRAO))


def migrar_config_antiga():
    """Importa a configuração da versão anterior como perfil 'Padrão'."""
    if Perfis.listar() or not ARQ_ANTIGO.exists():
        return
    try:
        antigo = json.loads(ARQ_ANTIGO.read_text(encoding="utf-8"))
    except Exception:
        return
    nome = "Padrão"
    pasta = Perfis.pasta(nome)
    pasta.mkdir(parents=True, exist_ok=True)
    perfil = copy.deepcopy(PERFIL_PADRAO)
    for s in antigo.get("skills", []):
        src = PASTA_ICONES_ANTIGA / s.get("icone", "")
        if src.is_file():
            shutil.copy2(src, pasta / src.name)
        perfil["skills"].append({k: s.get(k) for k in
                                 ("nome", "x", "y", "w", "h", "icone", "cd", "aprendido")})
    perfil["titulo_janela_jogo"] = antigo.get("titulo_janela_jogo", "Ragnarok")
    L, D = perfil["layout"], perfil["deteccao"]
    L["tamanho"] = antigo.get("tamanho_icone", L["tamanho"])
    L["espaco"] = antigo.get("espaco", L["espaco"])
    L["esconder_quando_pronto"] = antigo.get("esconder_quando_pronto", False)
    for k in D:
        D[k] = antigo.get(k, D[k])
    Perfis.salvar(nome, perfil)


# =============================================================== overlay

class Overlay:
    def __init__(self, root, painel):
        self.root = root
        self.painel = painel
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.attributes("-transparentcolor", COR_TRANSPARENTE)
        root.configure(bg=COR_TRANSPARENTE)
        self.canvas = tk.Canvas(root, bg=COR_TRANSPARENTE, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        root.withdraw()

        self.perfil = None
        self.pasta = None
        self.ativo = False
        self.mover = False
        self.preview_ate = 0.0
        self.janela_visivel = False
        self.jogo = Jogo()
        self.geo = None                # (x, y, w, h) do jogo
        self.jogo_ok = False           # overlay pode aparecer?
        self.estado_jogo = "—"
        self.pos = (0, 0)
        self.meu_hwnd = None
        self.forcar_visivel = False
        self.fila_busca = queue.Queue()
        self.buscando = False
        self.busca_desde = 0.0
        self.busca_manual = False
        self._recarregar = False
        self._buff_job = None
        self._buff_res = {}
        self._fila_escala = queue.Queue()
        self._buscando_escala = False
        self._trocando = False
        threading.Thread(target=self._loop_buffs, daemon=True).start()
        self.pendentes = set()
        self.sct = None
        self.caixa = None
        self.frames = 0
        self.w = self.h = 10
        self._arrasto = None
        self._avisou_captura = False

        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.canvas.bind("<MouseWheel>", self._roda)
        self.loop()

    @property
    def skills(self):
        return self.perfil["skills"] if self.perfil else []

    @property
    def L(self):
        return self.perfil["layout"]

    @property
    def buffs(self):
        return self.perfil.get("buffs", []) if self.perfil else []

    def itens(self):
        """O que aparece no overlay, em ordem: skills e depois buffs com ícone."""
        return ([("sk", s) for s in self.skills] +
                [("bf", b) for b in self.buffs if b.get("_img")])

    # ---- perfil / layout

    def carregar_perfil(self, perfil, pasta):
        self.perfil = perfil
        self.pasta = pasta
        for sk in self.skills:
            sk["_do_site"] = False
            ref = None
            if sk.get("icone"):
                try:
                    ref = Image.open(pasta / sk["icone"]).convert("RGB")
                except Exception:
                    ref = None
            if ref is None and self.painel.icone_skill(sk.get("id")):
                try:
                    ref = icone_dp_rgb(self.painel.icone_skill(sk["id"]))
                    sk["_do_site"] = True        # ainda não achado na tela
                except Exception:
                    ref = None
            if ref is None:
                ref = Image.new("RGB", (max(4, sk.get("w") or 24), max(4, sk.get("h") or 24)),
                                (90, 90, 90))
            sk["_ref_full"] = ref
            sk["_ref"] = miolo(ref)
            if sk.get("x") is None and not sk["_do_site"]:
                pass                                  # sem ícone ainda: nada a procurar
            elif np is not None:
                sk["_ref_g"] = cinza(sk["_ref"])
                sk["_tmpl"] = sk["_ref_g"].astype(np.uint8)
                sk["_margem"] = ((ref.width - sk["_ref"].width) // 2,
                                 (ref.height - sk["_ref"].height) // 2)
            sk.update(_delay=False, _cont=0, _inicio=-99.0, _fim=0.0, _d=0.0,
                      _contando=False, _decidido=True, _ini_cd=0.0, _vis=True,
                      _ncc=1.0, _perdido_desde=None, _sumiu=False, _ult_busca=-99.0)
        for bf in self.buffs:
            bf["_imgs"], bf["_tmpls"], bf["_tmpls_b"], bf["_site"] = [], [], [], []
            for arq in bf.get("variantes", []):
                try:
                    im = Image.open(pasta / arq).convert("RGB")
                except Exception:
                    continue
                bf["_imgs"].append(im)
                bf["_site"].append(arq.startswith("buff_site_"))
                if np is not None:
                    cinza_m, branco_m = modelos_buff(im)
                    bf["_tmpls"].append(cinza_m)
                    bf.setdefault("_tmpls_b", []).append(branco_m)
            bf.update(_ativo=False, _visto=-99.0, _desde=0.0, _score=0.0)
        self.preparar_imagens()
        self.calcular_caixa()
        self.relayout()

    @property
    def estilo(self):
        return self.L.get("estilo", "moderno") if self.perfil else "moderno"

    def metricas(self):
        """Medidas da faixa de ícones conforme o estilo escolhido."""
        L = self.L
        T, esp = L["tamanho"], L["espaco"]
        classico = self.estilo == "classico"
        pad = 9 if L.get("fundo_painel") else 4
        barra = BARRA_H if classico else max(4, T // 12)
        fonte_nome = max(7, int(T * 0.2))
        nome_h = fonte_nome + 8 if L.get("mostrar_nomes") else 0
        ap_h = (int(L.get("ap_altura") or 0) or max(14, int(T * 0.3))) if self.mostrar_ap() else 0
        return {"T": T, "esp": esp, "pad": pad, "barra": barra, "nome_h": nome_h,
                "fonte_nome": fonte_nome, "raio": 0 if classico else max(3, int(T * 0.18)),
                "slot_h": T + 3 + barra + nome_h,
                "ap_h": ap_h, "ap_off": ap_h + 3 if ap_h else 0}

    def mostrar_ap(self):
        return bool(self.perfil and self.L.get("mostrar_ap"))

    def preparar_imagens(self):
        T = self.L["tamanho"]
        m = self.metricas()
        fundo = COR_PAINEL if self.L.get("fundo_painel") else None

        def img(pil, brilho=None, cinza=False):
            if self.estilo == "classico":
                g = sem_cor_chave(pil.convert("RGB").resize((T, T), Image.NEAREST))
                if cinza:
                    g = g.convert("L").convert("RGB")
                if brilho is not None:
                    g = sem_cor_chave(ImageEnhance.Brightness(g).enhance(brilho))
                return ImageTk.PhotoImage(g)
            return ImageTk.PhotoImage(icone_arredondado(pil, T, m["raio"], fundo, brilho, cinza))

        for sk in self.skills:
            sk["_img"] = img(sk["_ref_full"])
            sk["_img_cd"] = img(sk["_ref_full"], 0.35)
        for bf in self.buffs:
            if not bf.get("_imgs"):
                bf["_img"] = None
                continue
            bf["_img"] = img(bf["_imgs"][0])
            bf["_img_var"] = [img(im) for im in bf["_imgs"]]
            bf["_img_off"] = img(bf["_imgs"][0], 0.45, cinza=True)

    def calcular_caixa(self):
        com_pos = [s for s in self.skills if s.get("x") is not None]
        if not com_pos:
            self.caixa = None
            return
        x0 = min(s["x"] for s in com_pos)
        y0 = min(s["y"] for s in com_pos)
        x1 = max(s["x"] + s["w"] for s in com_pos)
        y1 = max(s["y"] + s["h"] for s in com_pos)
        self.caixa = {"left": x0, "top": y0, "width": x1 - x0, "height": y1 - y0}

    def passo(self):
        m = self.metricas()
        if self.L["orientacao"] == "vertical":
            return 0, m["slot_h"] + m["esp"]
        return m["T"] + m["esp"], 0

    def relayout(self):
        m = self.metricas()
        T, esp, pad = m["T"], m["esp"], m["pad"]
        n = max(1, len(self.itens()))
        if self.L["orientacao"] == "vertical":
            w, h = T + 2 * pad, n * m["slot_h"] + (n - 1) * esp + 2 * pad
        else:
            w, h = n * T + (n - 1) * esp + 2 * pad, m["slot_h"] + 2 * pad
        h += m["ap_off"]                       # barra de AP em cima, colada nos ícones
        if self.L["orientacao"] == "vertical" and m["ap_h"]:
            w = max(w, 2 * pad + max(T, 64))   # na vertical, espaço mínimo para "53 / 200"
        self.w, self.h = w, h
        if self.L["x"] is None or self.L["y"] is None:
            if self.geo:
                gx, gy, gw, gh = self.geo
                x = gx + (gw - w) // 2
                y = min(gy + gh // 2 + 140, gy + gh - h - 10)
            else:
                sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
                x, y = (sw - w) // 2, sh // 2 + 140
        else:
            dx, dy = self.delta(self.L.get("origem"))
            x, y = self.L["x"] + dx, self.L["y"] + dy
        self.pos = (x, y)
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.canvas.config(width=w, height=h)

    def mudar_tamanho(self, T):
        T = max(20, min(160, int(T)))
        if T == self.L["tamanho"]:
            return
        self.L["tamanho"] = T
        self.preparar_imagens()
        self.relayout()
        self.painel.salvar_depois()

    def delta(self, ref):
        """Quanto o jogo andou desde a posição de referência."""
        if ref is None or not self.geo:
            return 0, 0
        return self.geo[0] - ref[0], self.geo[1] - ref[1]

    def origem_agora(self):
        titulo = self.perfil["titulo_janela_jogo"].strip() if self.perfil else ""
        if titulo:
            self.jogo.localizar(titulo, time.monotonic())
            g = self.jogo.geometria()
            if g:
                return [g[0], g[1]]
        return None

    def _fixar_origens(self):
        """Perfis antigos: assume que o jogo não se moveu desde a configuração."""
        o = [self.geo[0], self.geo[1]]
        if self.skills and self.perfil.get("origem_calibracao") is None:
            self.perfil["origem_calibracao"] = o
            self.painel.salvar_depois()
        if self.L["x"] is not None and self.L.get("origem") is None:
            self.L["origem"] = o
            self.painel.salvar_depois()

    def centralizar(self):
        self.L["x"] = self.L["y"] = None
        self.L["origem"] = None
        self.relayout()
        self.preview()
        self.painel.salvar_depois()

    # ---- estados da janela

    def tem_algo(self):
        """Há algo para mostrar ou para procurar na tela (buff pelo nome aguardando)?"""
        return bool(self.itens()) or self.mostrar_ap() or any(
            b.get("efst") and not b.get("variantes") for b in self.buffs)

    def iniciar(self):
        if not self.tem_algo():
            return False
        if self.sct is None:
            self.sct = nova_captura()
        self.ativo = True
        self._atualizar_janela()
        self.procurar_todos()
        return True

    # ---- procurar os ícones na tela

    def busca_disponivel(self):
        return np is not None and cv2 is not None

    def procurar_todos(self):
        if self.busca_disponivel():
            for sk in self.skills:
                self.pendentes.add(id(sk))

    def _pedir_busca(self, sk, agora):
        if self.busca_disponivel() and agora - sk["_ult_busca"] > 3.0:
            sk["_ult_busca"] = agora
            self.pendentes.add(id(sk))

    def _disparar_busca(self):
        if self.buscando and time.monotonic() - self.busca_desde > 20:
            registrar("Busca passou de 20 s sem responder; liberando.")
            self.buscando = False
            if self.busca_manual:
                self.busca_manual = False
                self.painel.status("A busca demorou demais. Detalhes em log.txt.")
        if self.buscando or not self.pendentes:
            return
        alvos = []
        for sk in self.skills:
            if id(sk) not in self.pendentes or "_tmpl" not in sk:
                continue
            if sk["_do_site"]:
                full = np.asarray(sk["_ref_full"].convert("L"))
                alvos.append((id(sk), full, None, ESCALAS_DP))
            else:
                alvos.append((id(sk), sk["_tmpl"], sk["_margem"], (1.0,)))
        self.pendentes.clear()
        if not alvos:
            return
        if self.geo:
            gx, gy, gw, gh = self.geo
            regiao = {"left": gx, "top": gy, "width": gw, "height": gh}
        else:
            with nova_captura() as sct:
                regiao = dict(sct.monitors[1])
        self.buscando = True
        self.busca_desde = time.monotonic()
        registrar(f"Busca iniciada: {len(alvos)} ícone(s) na área {regiao}")
        threading.Thread(target=self._buscar, args=(alvos, regiao), daemon=True).start()

    def _buscar(self, alvos, regiao):
        """Roda em segundo plano: procura cada ícone na área do jogo."""
        res = {}
        t0 = time.monotonic()
        try:
            with nova_captura() as sct:
                shot = sct.grab(regiao)
            rgb = Image.frombytes("RGB", shot.size, shot.rgb)
            tela = np.asarray(rgb.convert("L"))
            for chave_sk, tmpl, margem, escalas in alvos:
                melhor = None
                for esc in escalas:
                    if margem is None:            # ícone do site: redimensiona e usa o miolo
                        fh, fw = tmpl.shape
                        fw, fh = max(4, round(fw * esc)), max(4, round(fh * esc))
                        cheio = cv2.resize(tmpl, (fw, fh), interpolation=cv2.INTER_NEAREST)
                        mx, my = max(1, int(fw * 0.15)), max(1, int(fh * 0.15))
                        t = np.ascontiguousarray(cheio[my:fh - my, mx:fw - mx])
                    else:
                        t, (mx, my) = tmpl, margem
                        fh, fw = t.shape[0] + 2 * my, t.shape[1] + 2 * mx
                    if t.shape[0] > tela.shape[0] or t.shape[1] > tela.shape[1]:
                        continue
                    r = cv2.matchTemplate(tela, t, cv2.TM_CCOEFF_NORMED)
                    _, v, _, loc = cv2.minMaxLoc(r)
                    if v == v and (melhor is None or v > melhor[2]):   # ignora NaN
                        melhor = (loc[0] + regiao["left"] - mx, loc[1] + regiao["top"] - my,
                                  v, fw, fh)
                if melhor:
                    if margem is None:            # guarda o recorte real da tela
                        x0, y0 = melhor[0] - regiao["left"], melhor[1] - regiao["top"]
                        melhor += (rgb.crop((x0, y0, x0 + melhor[3], y0 + melhor[4])),)
                    res[chave_sk] = melhor
        except Exception:
            res["_erro"] = traceback.format_exc()
        res["_tempo"] = time.monotonic() - t0
        self.fila_busca.put((res, [a[0] for a in alvos]))

    def _aplicar_buscas(self):
        while True:
            try:
                res, pedidos = self.fila_busca.get_nowait()
            except queue.Empty:
                return
            self.buscando = False
            manual, self.busca_manual = self.busca_manual, False
            if "_erro" in res:
                registrar("Erro na busca:\n" + res["_erro"])
                self.painel.status("Erro ao procurar na tela. Detalhes em log.txt.")
                continue
            ox, oy = self.pos
            dx, dy = self.delta(self.perfil.get("origem_calibracao"))
            achados, moveu, faltam, linhas, novos = 0, [], [], [], []
            for sk in self.skills:
                if id(sk) not in pedidos:
                    continue
                nome = sk.get("nome") or "?"
                r = res.get(id(sk))
                no_overlay = bool(r) and ox <= r[0] < ox + self.w and oy <= r[1] < oy + self.h
                linhas.append(f"  {nome}: " + (f"semelhança {r[2]:.2f} em ({r[0]}, {r[1]})"
                                                   + (" [em cima do overlay, ignorado]" if no_overlay else "")
                                                   if r else "sem resultado"))
                if r and sk["_do_site"]:
                    if r[2] >= LIMIAR_ACHADO_DP and not no_overlay:
                        if self._fixar_achado_do_site(sk, r):
                            achados += 1
                            novos.append(nome)
                        else:
                            faltam.append(nome + " (em delay; espero ela ficar pronta)")
                    else:
                        faltam.append(nome)
                    continue
                if r and r[2] >= LIMIAR_ACHADO and not no_overlay:
                    achados += 1
                    nx, ny = r[0] - dx, r[1] - dy
                    if abs(nx - sk["x"]) > 1 or abs(ny - sk["y"]) > 1:
                        sk["x"], sk["y"] = nx, ny
                        sk.update(_delay=False, _cont=0, _decidido=True)
                        moveu.append(nome)
                    sk["_sumiu"] = False
                    sk["_perdido_desde"] = None
                else:
                    sk["_sumiu"] = True
                    faltam.append(nome)
            registrar(f"Busca concluída em {res.get('_tempo', 0):.2f} s:\n" + "\n".join(linhas))
            if self._recarregar:
                self._recarregar = False
                self.painel.salvar_agora()
                self.carregar_perfil(self.perfil, self.pasta)
                self.painel.montar_lista()
            elif moveu:
                self.calcular_caixa()
                self.painel.salvar_depois()
            if manual or moveu or faltam or novos:
                txt = f"Busca concluída: {achados} de {len(linhas)} ícone(s) encontrados"
                if novos:
                    txt += f"; achei na tela pela primeira vez: {', '.join(novos)}"
                if moveu:
                    txt += f"; mudaram de lugar: {', '.join(moveu)}"
                if faltam:
                    txt += f"; não estão na tela: {', '.join(faltam)}"
                self.painel.status(txt + ".")

    def _fixar_achado_do_site(self, sk, r):
        """Ícone achado pela imagem da Divine Pride: passa a usar o recorte real da tela."""
        x, y, v, fw, fh, recorte = r
        ref_site = cinza(miolo(sk["_ref_full"].resize((fw, fh), Image.NEAREST)))
        if cinza(miolo(recorte)).mean() < 0.6 * ref_site.mean():
            return False                      # parece estar em delay: captura depois
        if self.perfil.get("origem_calibracao") is None and self.geo:
            self.perfil["origem_calibracao"] = [self.geo[0], self.geo[1]]
        dx, dy = self.delta(self.perfil.get("origem_calibracao"))
        arq = f"icone_site_{sk.get('id')}_{time.time_ns()}.png"
        recorte.save(self.pasta / arq)
        sk.update(x=x - dx, y=y - dy, w=fw, h=fh, icone=arq)
        self._recarregar = True
        return True

    def parar(self):
        self.ativo = False
        for sk in self.skills:
            sk.update(_delay=False, _cont=0, _fim=0.0, _contando=False, _decidido=True)
        for bf in self.buffs:
            bf.update(_ativo=False, _visto=-99.0)
        self._buff_job = None
        self._atualizar_janela()

    # ---- buffs: leitura em segundo plano (não trava o overlay)

    def _loop_buffs(self):
        sct = None
        while True:
            time.sleep(0.3)
            job = self._buff_job
            if not job or cv2 is None or np is None:
                continue
            regiao, alvos, ov = job
            try:
                if sct is None:
                    sct = nova_captura()
                shot = sct.grab(regiao)
                arr = np.asarray(Image.frombytes("RGB", shot.size, shot.rgb))
                tela_c = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
                tela_b = mapa_simbolo_suave(arr)
                ox, oy = ov[0] - regiao["left"], ov[1] - regiao["top"]
                agora = time.monotonic()
                res = {}
                brilho = None
                for chave_b, mods in alvos:
                    melhor, qual, recorte = 0.0, 0, None
                    for n_var, (t_c, t_b, do_site, (W, H)) in enumerate(mods):
                        # ícone translúcido: o cinza "vê" o cenário por trás e pode confundir;
                        # por isso o cinza só é usado quando o ícone não tem traços claros
                        tela, t = (tela_b, t_b) if t_b is not None else (tela_c, t_c)
                        th, tw = t.shape
                        if th > tela.shape[0] or tw > tela.shape[1]:
                            continue
                        r = cv2.matchTemplate(tela, t, cv2.TM_CCOEFF_NORMED)
                        # ignora o próprio overlay (caso ele apareça na captura)
                        x0, y0 = max(0, ox - tw), max(0, oy - th)
                        x1, y1 = min(r.shape[1], ox + ov[2]), min(r.shape[0], oy + ov[3])
                        if x1 > x0 and y1 > y0:
                            r[y0:y1, x0:x1] = -1
                        if not do_site:
                            v = float(r.max())
                            if v == v and v > melhor:
                                melhor, qual, recorte = v, n_var, None
                            continue
                        # versão vinda da Divine Pride: só vale se tiver a moldura de ícone de buff
                        if brilho is None:
                            brilho = arr.max(axis=2)
                        mx_, my_ = (W - tw) // 2, (H - th) // 2
                        for v, (lx, ly) in picos(r):
                            if v < LIMIAR_BUFF:
                                break
                            if tem_moldura(brilho, lx - mx_, ly - my_, W, H):
                                if v > melhor:
                                    fx, fy = lx - mx_, ly - my_
                                    recorte = Image.fromarray(arr).crop((fx, fy, fx + W, fy + H))
                                    melhor, qual = v, n_var
                                break
                    res[chave_b] = (melhor, agora, qual, recorte)
                self._buff_res = res
            except Exception:
                registrar("Erro ao ler buffs:\n" + traceback.format_exc(), chave_rep="buffs")
                sct = None

    def _area_buffs(self):
        a = self.perfil.get("area_buffs")
        if a:
            dx, dy = self.delta(a.get("origem"))
            return {"left": a["x"] + dx, "top": a["y"] + dy, "width": a["w"], "height": a["h"]}
        if self.geo:
            # Os ícones de buff do RO ficam sempre no lado direito da tela
            gx, gy, gw, gh = self.geo
            larg = max(120, int(gw * 0.25))
            return {"left": gx + gw - larg, "top": gy, "width": larg, "height": gh}
        return None

    # ---- buff escolhido pelo nome: ícones da Divine Pride -> acha o tamanho na tela

    def _buffs_do_site(self):
        """Buffs sem versão salva cujos ícones da Divine Pride já estão no PC."""
        dp = self.painel.dp
        res = []
        for b in self.buffs:
            if b.get("variantes") or not b.get("efst") or b.get("_rag_pend"):
                continue
            icones = [self.painel.icone_buff(eid) for _, eid in b["efst"]]
            if icones and all(icones):
                res.append((b, icones))
        return res

    def _verificar_buffs_do_site(self, agora):
        if self._buscando_escala or not self.ativo or np is None or cv2 is None:
            return
        pend = [(b, ic) for b, ic in self._buffs_do_site() if agora - b.get("_ult_escala", -99) > 3]
        regiao = self._area_buffs()
        if not pend or not regiao:
            return
        b, icones = pend[0]
        b["_ult_escala"] = agora
        self._buscando_escala = True
        ov = (self.pos[0], self.pos[1], self.w, self.h)
        threading.Thread(target=self._buscar_escala, args=(id(b), icones, regiao, ov),
                         daemon=True).start()

    def _buscar_escala(self, chave_b, icones, regiao, ov):
        """Procura qualquer versão do buff na tela em vários tamanhos (fora do overlay)."""
        res = None
        try:
            with nova_captura() as sct:
                shot = sct.grab(regiao)
            arr = np.asarray(Image.frombytes("RGB", shot.size, shot.rgb))
            tela_c = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
            tela_b = mapa_simbolo_suave(arr)
            ox, oy = ov[0] - regiao["left"], ov[1] - regiao["top"]
            bases = [icone_dp_rgb(p) for p in icones]
            brilho = arr.max(axis=2)
            melhor = (0.0,)
            for idx, base in enumerate(bases):
                for esc in ESCALAS_BUFF:
                    W, H = max(6, round(base.width * esc)), max(6, round(base.height * esc))
                    for interp in (Image.NEAREST, Image.BILINEAR):
                        im = base.resize((W, H), interp)
                        t_c, t_b = modelos_buff(im)
                        tela, t = (tela_b, t_b) if t_b is not None else (tela_c, t_c)
                        if t.shape[0] > tela.shape[0] or t.shape[1] > tela.shape[1]:
                            continue
                        r = cv2.matchTemplate(tela, t, cv2.TM_CCOEFF_NORMED)
                        x0, y0 = max(0, ox - t.shape[1]), max(0, oy - t.shape[0])
                        x1, y1 = min(r.shape[1], ox + ov[2]), min(r.shape[0], oy + ov[3])
                        if x1 > x0 and y1 > y0:
                            r[y0:y1, x0:x1] = -1             # ignora o próprio overlay
                        mx, my = (W - t.shape[1]) // 2, (H - t.shape[0]) // 2
                        for v, loc in picos(r):
                            if v <= melhor[0] or v < LIMIAR_BUFF_SITE:
                                break
                            # só vale onde existe a moldura de ícone de buff (texto e cenário não têm)
                            if tem_moldura(brilho, loc[0] - mx, loc[1] - my, W, H):
                                melhor = (v, idx, esc, interp, loc[0] - mx, loc[1] - my, W, H)
                                break
            if melhor[0] > 0:
                v, idx, esc, interp, x, y, W, H = melhor
                recorte = Image.fromarray(arr).crop((x, y, x + W, y + H))
                res = {"v": v, "idx": idx, "esc": esc, "interp": interp, "recorte": recorte,
                       "bases": bases}
            registrar(f"Tamanho do buff: melhor semelhança {melhor[0]:.2f}"
                      + (f" (versão {melhor[1] + 1}, escala {melhor[2]}x)" if res else ""))
        except Exception:
            registrar("Erro ao procurar o tamanho do buff:\n" + traceback.format_exc())
        self._fila_escala.put((chave_b, res))

    def _aplicar_escala(self):
        while True:
            try:
                chave_b, res = self._fila_escala.get_nowait()
            except queue.Empty:
                return
            self._buscando_escala = False
            b = next((x for x in self.buffs if id(x) == chave_b), None)
            if b is None or b.get("variantes"):
                continue
            if not res or res["v"] < LIMIAR_BUFF_SITE:
                b["_aguardando_tela"] = True
                continue
            # Salva todas as versões no tamanho da tela; a encontrada usa o recorte real
            nomes = []
            for i, base in enumerate(res["bases"]):
                im = res["recorte"] if i == res["idx"] else base.resize(
                    (res["recorte"].width, res["recorte"].height), res["interp"])
                arq = (f"buff_{time.time_ns()}_{i}.png" if i == res["idx"]      # recorte real
                       else f"buff_site_{time.time_ns()}_{i}.png")                # da Divine Pride
                im.save(self.pasta / arq)
                nomes.append(arq)
            b["variantes"] = nomes
            b["escala"] = res["esc"]
            b.pop("_aguardando_tela", None)
            self.painel.salvar_agora()
            self.carregar_perfil(self.perfil, self.pasta)
            self.painel.montar_buffs()
            self.painel.status(f"{b.get('nome')}: achei o buff na tela e salvei "
                               f"{len(nomes)} versão(ões) do ícone.")
            if len(nomes) > 1:
                # Os outros ícones vieram do site; o "Auto" confirma cada um com a sua tela
                self.painel.root.after(400, lambda bb=b: CapturaAuto(self.painel, bb))

    def _trocar_por_real(self, b, qual, recorte):
        """A versão do buff vinha da Divine Pride; agora que apareceu na tela, guarda o
        recorte real (mais preciso para reconhecer depois)."""
        vs = b.get("variantes", [])
        if not 0 <= qual < len(vs) or not vs[qual].startswith("buff_site_"):
            return
        self._trocando = True
        try:
            arq = f"buff_{time.time_ns()}.png"
            recorte.save(self.pasta / arq)
            (self.pasta / vs[qual]).unlink(missing_ok=True)
            vs[qual] = arq
            self.painel.salvar_agora()
            self.carregar_perfil(self.perfil, self.pasta)
            self.painel.montar_buffs()
        finally:
            self._trocando = False

    def _atualizar_buffs(self, agora, pode_ler):
        self._aplicar_escala()
        if pode_ler:
            self._verificar_buffs_do_site(agora)
        alvos = [(id(b), list(zip(b["_tmpls"], b.get("_tmpls_b") or [None] * len(b["_tmpls"]),
                                   b.get("_site") or [False] * len(b["_tmpls"]),
                                   [im.size for im in b["_imgs"]])))
                 for b in self.buffs if b.get("_tmpls")]
        regiao = self._area_buffs() if (self.ativo and pode_ler and alvos) else None
        self._buff_job = (regiao, alvos, (self.pos[0], self.pos[1], self.w, self.h)) if regiao else None
        res = self._buff_res
        for b in self.buffs:
            r = res.get(id(b))
            if r:
                b["_score"] = r[0]
                if r[0] >= LIMIAR_BUFF:
                    b["_visto"] = max(b["_visto"], r[1])
                    b["_var_atual"] = r[2]          # qual versão do ícone está na tela
                    if r[3] is not None and r[0] >= 0.85 and not self._trocando:
                        self._trocar_por_real(b, r[2], r[3])
            ativo = agora - b["_visto"] < BUFF_TOLERANCIA
            if ativo and not b["_ativo"]:
                b["_desde"] = b["_visto"]
            b["_ativo"] = ativo

    def set_mover(self, ligado):
        self.mover = ligado
        self._atualizar_janela()
        if self.janela_visivel:
            self.aplicar_estilos()

    def preview(self, seg=2.0):
        self.preview_ate = time.monotonic() + seg
        self._atualizar_janela()

    def _atualizar_janela(self):
        deve = (bool(self.itens()) or self.mostrar_ap()) and ((self.ativo and self.jogo_ok) or self.mover
                                      or time.monotonic() < self.preview_ate)
        if deve and not self.janela_visivel:
            self.root.deiconify()
            self.root.update_idletasks()
            self.janela_visivel = True
            self.aplicar_estilos()
        elif not deve and self.janela_visivel:
            self.root.withdraw()
            self.janela_visivel = False

    def aplicar_estilos(self):
        hwnd = hwnd_de(self.root)
        self.meu_hwnd = hwnd
        base = WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
        if self.mover:
            mudar_estilo(hwnd, base, WS_EX_TRANSPARENT)       # aceita mouse
        else:
            mudar_estilo(hwnd, base | WS_EX_TRANSPARENT)       # clique atravessa
        ok = self.atualizar_captura()
        if not ok and not self._avisou_captura:
            self._avisou_captura = True
            self.painel.status("Aviso: deixe o overlay longe da barra de atalhos.")

    def atualizar_captura(self):
        """Por padrão o overlay é invisível para prints/gravações (para não ler a si mesmo).
        Fica visível se a opção estiver ligada ou durante o 'Tirar print'."""
        if not self.meu_hwnd:
            return True
        visivel = self.forcar_visivel or self.painel.app_cfg.get("visivel_em_capturas", False)
        return bool(user32.SetWindowDisplayAffinity(self.meu_hwnd,
                                                    0 if visivel else WDA_EXCLUDEFROMCAPTURE))

    # ---- arrastar / roda do mouse (modo mover)

    def _press(self, e):
        if self.mover:
            self._arrasto = (e.x_root - self.root.winfo_x(), e.y_root - self.root.winfo_y())

    def _drag(self, e):
        if self._arrasto:
            ax, ay = self._arrasto
            self.root.geometry(f"+{e.x_root - ax}+{e.y_root - ay}")

    def _release(self, _e):
        if self._arrasto:
            self._arrasto = None
            self.L["x"], self.L["y"] = self.root.winfo_x(), self.root.winfo_y()
            self.L["origem"] = [self.geo[0], self.geo[1]] if self.geo else None
            self.painel.salvar_depois()

    def _roda(self, e):
        if self.mover and self.perfil:
            self.mudar_tamanho(self.L["tamanho"] + (4 if e.delta > 0 else -4))
            self.painel.sincronizar_aparencia()

    # ---- detecção

    def atualizar_estado(self, sk, d, agora):
        """Atualiza o estado bruto do ícone: escuro (delay) ou normal."""
        D = self.perfil["deteccao"]
        quer_delay = d > D["limiar_pronto"] if sk["_delay"] else d >= D["limiar_delay"]
        if quer_delay == sk["_delay"]:
            sk["_cont"] = 0
            return
        sk["_cont"] += 1
        precisa = D["frames_entrar"] if quer_delay else D["frames_confirmar"]
        if sk["_cont"] < precisa:
            return
        sk["_cont"] = 0
        sk["_delay"] = quer_delay
        if quer_delay:
            sk["_inicio"] = agora - (precisa - 1) / D["fps"]
            # se já está contando, esse escurecimento é do delay global de outra skill
            sk["_decidido"] = sk["_contando"]
        else:
            sk["_saida"] = agora - (precisa - 1) / D["fps"]

    def processar_cooldowns(self, agora):
        D = self.perfil["deteccao"]
        varias = len(self.skills) >= 2
        for sk in self.skills:
            # 1) Confirma o início de um cooldown
            if sk["_delay"] and not sk["_decidido"]:
                passou = agora - sk["_inicio"]
                sozinho = varias and passou >= JANELA_GRUPO and not any(
                    o is not sk and abs(o["_inicio"] - sk["_inicio"]) <= JANELA_GRUPO
                    for o in self.skills)
                if sozinho or passou >= D["min_mostrar"]:
                    sk["_decidido"] = True
                    sk["_contando"] = True
                    sk["_ini_cd"] = sk["_inicio"]
            # 2) Encerra o cooldown
            if not sk["_contando"]:
                continue
            manual = sk.get("cd")
            if manual:
                # Recarga manual: confia no tempo digitado
                if agora >= sk["_ini_cd"] + manual and not sk["_delay"]:
                    sk["_contando"] = False
                    sk["_fim"] = agora
            elif not sk["_delay"]:
                # Sem recarga manual: acaba quando o ícone volta, e aprende o tempo
                sk["_contando"] = False
                sk["_fim"] = agora
                dur = sk.get("_saida", agora) - sk["_ini_cd"]
                if dur >= 0.2:
                    sk["aprendido"] = round(dur, 2)
                    self.painel.salvar_depois()

    def loop(self):
        try:
            self._tick()
        except Exception:
            registrar("Erro no loop:\n" + traceback.format_exc(), chave_rep="loop")
        fps = self.perfil["deteccao"]["fps"] if self.perfil else 20
        self.root.after(max(10, 1000 // max(1, int(fps))), self.loop)

    def _tick(self):
        agora = time.monotonic()
        if not self.perfil:
            self._atualizar_janela()
            return
        L = self.L
        titulo = self.perfil["titulo_janela_jogo"].strip()

        # 1) Onde está o jogo?
        if titulo:
            self.jogo.localizar(titulo, agora)
            geo = self.jogo.geometria()
            if geo is None:
                self.estado_jogo = "jogo minimizado" if self.jogo.hwnd else "jogo não encontrado"
        else:
            geo = None
            self.estado_jogo = ""
        if geo != self.geo:
            self.geo = geo
            if geo:
                self._fixar_origens()
            self.relayout()

        # 2) O overlay pode aparecer? (jogo aberto e visível embaixo dele)
        if not titulo:
            self.jogo_ok = True
        elif geo is None:
            self.jogo_ok = False
        elif L["esconder_sem_foco"] and not self.jogo.em_foco():
            self.jogo_ok = False
            self.estado_jogo = "jogo sem foco"
        else:
            gx, gy, gw, gh = geo
            cx, cy = self.pos[0] + self.w // 2, self.pos[1] + self.h // 2
            dentro = gx <= cx < gx + gw and gy <= cy < gy + gh
            # Se o overlay está em cima do jogo, só aparece se nada estiver cobrindo o jogo ali
            self.jogo_ok = not dentro or janela_no_ponto(cx, cy) in (self.jogo.hwnd, self.meu_hwnd)
            self.estado_jogo = "" if self.jogo_ok else "jogo coberto"
        self._atualizar_janela()

        # 3) Leitura dos ícones
        if self.ativo and (geo or not titulo):
            for sk in self.skills:
                if sk.get("x") is None and "_tmpl" in sk:
                    self._pedir_busca(sk, agora)
        if self.ativo and self.caixa and (geo or not titulo):
            dx, dy = self.delta(self.perfil.get("origem_calibracao"))
            caixa = dict(self.caixa, left=self.caixa["left"] + dx, top=self.caixa["top"] + dy)
            shot = self.sct.grab(caixa)
            tela = Image.frombytes("RGB", shot.size, shot.rgb)
            for sk in self.skills:
                if sk.get("x") is None:
                    continue
                x, y = sk["x"] - self.caixa["left"], sk["y"] - self.caixa["top"]
                if titulo:
                    px, py = sk["x"] + dx + sk["w"] // 2, sk["y"] + dy + sk["h"] // 2
                    sk["_vis"] = janela_no_ponto(px, py) == self.jogo.hwnd
                    if not sk["_vis"]:
                        continue             # algo cobrindo a barra: congela o estado
                else:
                    sk["_vis"] = True
                atual = miolo(tela.crop((x, y, x + sk["w"], y + sk["h"])))
                sk["_d"] = diferenca(atual, sk["_ref"])
                if np is not None and "_ref_g" in sk:
                    # Escurecido ou cinza continua parecido; outro ícone no lugar não
                    sk["_ncc"] = semelhanca(cinza(atual), sk["_ref_g"])
                    if sk["_ncc"] < LIMIAR_PERDIDO:
                        if sk["_perdido_desde"] is None:
                            sk["_perdido_desde"] = agora
                        elif agora - sk["_perdido_desde"] > 1.2:
                            self._pedir_busca(sk, agora)
                        continue                 # não conta como delay
                    sk["_perdido_desde"] = None
                    sk["_sumiu"] = False
                self.atualizar_estado(sk, sk["_d"], agora)
            self.processar_cooldowns(agora)
        if geo or not titulo:
            self._disparar_busca()
        self._aplicar_buscas()
        self._atualizar_buffs(agora, bool(geo) or not titulo)
        if self.ativo and self.sct is not None and (geo or not titulo):
            self._ler_ap(agora)

        self.frames += 1
        if self.janela_visivel and self.frames % 40 == 0:
            self.root.attributes("-topmost", True)
        self.desenhar(agora, self.jogo_ok)

    # ---- desenho

    def desenhar(self, agora, foco):
        c = self.canvas
        c.delete("all")
        itens = self.itens()
        if not self.janela_visivel or not (itens or self.mostrar_ap()):
            return
        L = self.L
        m = self.metricas()
        T, pad = m["T"], m["pad"]
        dx, dy = self.passo()
        edicao = self.mover or agora < self.preview_ate
        if not edicao and not (self.ativo and foco):
            return
        if L.get("fundo_painel"):
            ret_arred(c, 1, 1, self.w - 2, self.h - 2, 10,
                      fill="#%02x%02x%02x" % COR_PAINEL, outline="#2a3142", width=1)
        elif edicao:
            c.create_rectangle(1, 1, self.w - 2, self.h - 2, fill="#202020", outline="")
        if edicao:
            ret_arred(c, 1, 1, self.w - 2, self.h - 2, 10, fill="", outline="#f1c40f", width=2)

        if m["ap_h"]:
            self._desenhar_ap(c, m, agora, edicao)
        fonte = ("Segoe UI", max(8, int(T * 0.34)), "bold")
        for i, (tipo, it) in enumerate(itens):
            x0, y0 = pad + i * dx, pad + m["ap_off"] + i * dy
            if edicao:
                c.create_image(x0, y0, anchor="nw", image=it["_img"])
                if tipo == "bf":
                    self._borda(c, x0, y0, T, m, "#22c55e", 2)
                desenhou = True
            elif tipo == "bf":
                desenhou = self._desenhar_buff(c, it, x0, y0, T, agora, fonte, m)
            else:
                desenhou = self._desenhar_skill(c, it, x0, y0, T, agora, fonte, m)
            if desenhou and L.get("mostrar_nomes"):
                self._nome(c, it.get("nome") or "", x0, y0, T, m)

    # ---- barra de AP

    def _desenhar_ap(self, c, m, agora, edicao):
        """Barra de AP do tamanho da faixa de ícones, com "atual / máximo" no meio."""
        pad, h = m["pad"], m["ap_h"]
        x0, y0, x1 = pad, pad, self.w - pad
        leitura = getattr(self, "ap", None)
        recente = leitura is not None and agora - getattr(self, "ap_t", -99) < 3
        if edicao and leitura is None:
            leitura, recente = (53, 200), True       # exemplo para posicionar
        frac = leitura[0] / leitura[1] if leitura and leitura[1] else 0.0
        raio = 0 if self.estilo == "classico" else h / 2
        borda = "#2a3142"

        def caixa(xa, xb, **kw):
            if raio:
                return ret_arred(c, xa, y0, xb, y0 + h, raio, **kw)
            return c.create_rectangle(xa, y0, xb, y0 + h, **kw)

        caixa(x0, x1, fill="#161b26", outline=borda, width=1)
        if frac > 0:
            cor = self.L.get("ap_cor") or "#3b82f6"
            preench = cor if recente else misturar_cor(cor, "#3a4050", 0.75)
            xb = x0 + max(h if raio else 2, (x1 - x0) * min(1.0, frac))
            caixa(x0, xb, fill=preench, outline="")
            if recente and h >= 10:                   # brilho no topo da barra
                c.create_line(x0 + raio, y0 + 2, max(x0 + raio, xb - raio), y0 + 2,
                              fill=misturar_cor(cor, "#ffffff", 0.45), width=1)
        txt = f"{leitura[0]} / {leitura[1]}" if leitura else "AP ?"
        if not recente and leitura:
            txt = "AP ?  (" + txt + ")"
        fonte = ("Segoe UI", max(6, min(int(h * 0.62), 22)), "bold")
        texto_contorno(c, (x0 + x1) / 2, y0 + h / 2, txt, fonte,
                       "#ffffff" if recente else "#9aa4b5")

    def _ler_ap(self, agora):
        """Lê o AP 4 vezes por segundo. Acha sozinho a janela Informações básicas pelo rótulo
        "AP" (na tela toda do jogo); se você marcou a área à mão, usa a área marcada."""
        if not self.mostrar_ap() or np is None or agora - getattr(self, "_ap_ult", -99) < 0.25:
            return
        self._ap_ult = agora
        self._receber_busca_ap()
        manual = self.perfil.get("area_ap")
        if manual and getattr(self, "_ap_manual_falhas", 0) >= 8:
            # a área marcada à mão não está mais lendo (janela mudou de lugar ou de modo):
            # usa a busca automática enquanto isso
            if not getattr(self, "_ap_avisou_manual", False):
                self._ap_avisou_manual = True
                registrar("AP: a área marcada à mão parou de ler; usando a busca automática.")
            manual = None
            if getattr(self, "_ap_rotulo", None) is None and agora - getattr(self, "_ap_tenta_manual", 0) > 10:
                self._ap_tenta_manual = agora           # de vez em quando testa a área de novo
                self._ap_manual_falhas = 4
                manual = self.perfil.get("area_ap")
        if manual:
            dx, dy = self.delta(manual.get("origem"))
            caixa = {"left": manual["x"] + dx, "top": manual["y"] + dy,
                     "width": manual["w"], "height": manual["h"]}
        elif getattr(self, "_ap_rotulo", None):
            x, y = self._ap_rotulo
            esq = max(0, x - 2) if not self.geo else max(self.geo[0], x - 2)
            topo = max(0, y - 3) if not self.geo else max(self.geo[1], y - 3)
            caixa = {"left": esq, "top": topo, "width": (x - esq) + 13 + 190,
                     "height": (y - topo) + 12}
        else:
            self._buscar_ap(agora)
            return
        try:
            shot = self.sct.grab(caixa)
            arr = np.asarray(Image.frombytes("RGB", shot.size, shot.rgb))
        except Exception:
            arr = None
        if arr is not None and not manual:
            # O rótulo "AP" ainda está no mesmo lugar? Se a janela mudou (compacta <-> expandida,
            # arrastada ou fechada), o lugar antigo pode cair em cima do HP/SP: procura de novo já.
            ox, oy = x - caixa["left"], y - caixa["top"]
            loc = achar_rotulo_ap(arr)
            self._ap_ultimo_trecho = arr
            if loc is None or abs(loc[0] - ox) > 2 or abs(loc[1] - oy) > 2:
                self._ap_rotulo, self._ap_ult_busca = None, -99.0
                self._buscar_ap(agora)
                return
            arr = arr[:, ox + 13:]
        lido = ler_fracao(arr) if arr is not None else None
        if lido is None:
            self._ap_falhas = getattr(self, "_ap_falhas", 0) + 1
            if manual:
                self._ap_manual_falhas = getattr(self, "_ap_manual_falhas", 0) + 1
            elif self._ap_falhas >= 4:                     # janela mudou de lugar ou fechou
                self._ap_rotulo = None
            return
        self._ap_falhas = 0
        if manual:
            self._ap_manual_falhas = 0
            self._ap_avisou_manual = False
        if lido == getattr(self, "_ap_cand", None) or lido == getattr(self, "ap", None):
            self.ap, self.ap_t = lido, agora           # confirmado em 2 leituras seguidas
        self._ap_cand = lido

    def _buscar_ap(self, agora):
        """Procura o rótulo "AP" na tela do jogo em segundo plano (a cada 1,5 s)."""
        if getattr(self, "_ap_buscando", False) or agora - getattr(self, "_ap_ult_busca", -99) < 1.5:
            return
        if self.geo:
            gx, gy, gw, gh = self.geo
            regiao = {"left": gx, "top": gy, "width": gw, "height": gh}
        else:
            with nova_captura() as sct:
                regiao = dict(sct.monitors[1])
        self._ap_buscando, self._ap_ult_busca = True, agora
        if not hasattr(self, "_fila_ap"):
            self._fila_ap = queue.Queue()

        def trabalho():
            achado = None
            try:
                with nova_captura() as sct:
                    shot = sct.grab(regiao)
                arr = np.asarray(Image.frombytes("RGB", shot.size, shot.rgb))
                # 1º o canto superior esquerdo (onde a janela costuma ficar), depois a tela toda
                h, w = arr.shape[:2]
                canto = arr[:max(200, h * 2 // 5), :max(320, w * 2 // 5)]
                loc, lido = localizar_ap(canto)
                if loc is None:
                    loc, lido = localizar_ap(arr)
                if loc:
                    achado = (regiao["left"] + loc[0], regiao["top"] + loc[1])
                    registrar(f"AP encontrado em {achado}: {lido[0]} / {lido[1]}", chave_rep="ap_ok",
                              intervalo=30)
                else:
                    n = len(achar_rotulos_ap(arr))
                    registrar(f"AP não encontrado na tela ({n} rótulo(s) \"AP\" sem números legíveis)",
                              chave_rep="ap_nao", intervalo=30)
                self._ap_ultimo_quadro = arr                 # para o diagnóstico
            except Exception:
                registrar("Erro ao procurar o AP:\n" + traceback.format_exc(), chave_rep="ap")
            self._fila_ap.put(achado)
        threading.Thread(target=trabalho, daemon=True).start()

    def _receber_busca_ap(self):
        fila = getattr(self, "_fila_ap", None)
        while fila is not None:
            try:
                achado = fila.get_nowait()
            except queue.Empty:
                return
            self._ap_buscando = False
            if achado:
                self._ap_rotulo, self._ap_falhas = achado, 0

    # ---- peças do desenho

    def _borda(self, c, x0, y0, T, m, cor, largura):
        if self.estilo == "classico":
            c.create_rectangle(x0 + 1, y0 + 1, x0 + T - 1, y0 + T - 1, outline=cor, width=largura)
        else:
            ret_arred(c, x0 + 1, y0 + 1, x0 + T - 1, y0 + T - 1, m["raio"],
                      fill="", outline=cor, width=largura)

    def _barra(self, c, x0, y0, T, m, frac, cor):
        yb = y0 + T + 3
        bh = m["barra"]
        if self.estilo == "classico":
            c.create_rectangle(x0, yb, x0 + T, yb + bh, fill="#222222", outline="")
            c.create_rectangle(x0, yb, x0 + T * frac, yb + bh, fill=cor, outline="")
            return
        r = bh / 2
        ret_arred(c, x0, yb, x0 + T, yb + bh, r, fill="#2a3040", outline="")
        if frac > 0:
            ret_arred(c, x0, yb, x0 + max(bh, T * frac), yb + bh, r, fill=cor, outline="")

    def _nome(self, c, nome, x0, y0, T, m):
        """Nome embaixo do ícone, cortado com "…" para não encostar no vizinho."""
        tam = m["fonte_nome"]
        fonte = ("Segoe UI", tam)
        if getattr(self, "_fonte_nome", (None,))[0] != tam:
            import tkinter.font as tkfont
            self._fonte_nome = (tam, tkfont.Font(root=self.root, family="Segoe UI", size=tam))
            self._cache_nomes = {}
        medida = self._fonte_nome[1]
        livre = T + max(0, m["esp"] - 4)
        chave_n = (nome, livre)
        if chave_n not in self._cache_nomes:
            txt = nome
            while txt and medida.measure(txt) > livre:
                txt = txt[:-1]
            if txt != nome:
                txt = txt[:-1].rstrip() + "…" if len(txt) > 1 else "…"
            self._cache_nomes[chave_n] = txt
        y = y0 + T + 3 + m["barra"] + 3 + tam / 2 + 1
        texto_contorno(c, x0 + T / 2, y, self._cache_nomes[chave_n], fonte, "#d7dce6")

    def _alerta_buff(self, c, x0, y0, T, m, agora):
        pisca = int(agora * 2.5) % 2 == 0
        borda = "#ff2d2d" if pisca else "#ffd23f"
        if self.estilo == "classico":
            c.create_rectangle(x0 + 2, y0 + 2, x0 + T - 2, y0 + T - 2, outline=borda, width=4)
        else:
            ret_arred(c, x0 + 2, y0 + 2, x0 + T - 2, y0 + T - 2, m["raio"],
                      fill="", outline=borda, width=4)
        grande = ("Segoe UI", max(12, int(T * 0.72)), "bold")
        cx, cy = x0 + T / 2, y0 + T / 2
        for ddx in (-3, -2, 0, 2, 3):
            for ddy in (-3, -2, 0, 2, 3):
                if ddx or ddy:
                    c.create_text(cx + ddx, cy + ddy, text="!", font=grande, fill="#000000")
        c.create_text(cx, cy, text="!", font=grande, fill=borda)

    def _desenhar_buff(self, c, bf, x0, y0, T, agora, fonte, m):
        ativo = bf["_ativo"]
        modo = bf.get("mostrar", "sempre")
        if (modo == "faltando" and ativo) or (modo == "ativo" and not ativo):
            return False
        vars_ = bf.get("_img_var") or [bf["_img"]]
        atual = vars_[min(bf.get("_var_atual", 0), len(vars_) - 1)]
        c.create_image(x0, y0, anchor="nw", image=atual if ativo else bf["_img_off"])
        if not ativo:
            self._alerta_buff(c, x0, y0, T, m, agora)
            return True
        if self.estilo == "minimalista":
            ret_arred(c, x0 + T * 0.3, y0 + T + 3, x0 + T * 0.7, y0 + T + 3 + m["barra"],
                      m["barra"] / 2, fill="#22c55e", outline="")     # tracinho verde = ativo
        else:
            self._borda(c, x0, y0, T, m, "#22c55e", 2)
        dur = bf.get("duracao")
        if dur:
            resta = dur - (agora - bf["_desde"])
            if resta > 0:
                txt = f"{int(resta // 60)}m" if resta >= 60 else f"{math.ceil(resta)}"
                cor = "#ff5555" if resta <= self.L["aviso_vermelho_s"] else "#ffffff"
                texto_contorno(c, x0 + T / 2, y0 + T / 2, txt, fonte, cor)
        return True

    def _desenhar_skill(self, c, sk, x0, y0, T, agora, fonte, m):
        L = self.L
        decorrido = agora - sk["_ini_cd"]
        em_cd = sk["_contando"]
        voltou = sk["_fim"] > 0 and agora - sk["_fim"] < 0.4
        if L["esconder_quando_pronto"] and not em_cd and not voltou:
            return False
        c.create_image(x0, y0, anchor="nw", image=sk["_img_cd"] if em_cd else sk["_img"])
        estilo = self.estilo
        if voltou:
            self._borda(c, x0, y0, T, m, "#ffffff", 3)
        elif estilo == "classico":
            c.create_rectangle(x0, y0, x0 + T, y0 + T, outline="#000000", width=1)
        elif estilo == "moderno":
            self._borda(c, x0, y0, T, m, "#f1c40f" if em_cd else "#3a4256", 2)
        if not em_cd:
            return True
        cd = sk.get("cd") or sk.get("aprendido")
        if cd:
            resta = cd - decorrido
            if resta <= 0:
                txt = "…"
            elif resta >= 60:
                txt = f"{int(resta // 60)}m"
            elif resta >= 10:
                txt = f"{math.ceil(resta)}"
            else:
                txt = f"{resta:.1f}"
            cor = "#ff5555" if 0 < resta <= L["aviso_vermelho_s"] else "#ffffff"
            texto_contorno(c, x0 + T / 2, y0 + T / 2, txt, fonte, cor)
            self._barra(c, x0, y0, T, m, max(0.0, min(1.0, resta / cd)), "#f1c40f")
        else:
            texto_contorno(c, x0 + T / 2, y0 + T / 2, f"{decorrido:.0f}s", fonte, "#bbbbbb")
        return True


# =============================================================== seleção de ícones

class Seletor:
    """Tela congelada onde o usuário arrasta retângulos sobre os ícones."""

    def __init__(self, root, tela, mon, ao_terminar,
                 texto="Arraste um retângulo sobre CADA ícone de skill na barra de atalhos"):
        self.ao_terminar = ao_terminar
        W, H = mon["width"], mon["height"]
        self.top = top = tk.Toplevel(root)
        top.overrideredirect(True)
        top.attributes("-topmost", True)
        top.geometry(f"{W}x{H}+{mon['left']}+{mon['top']}")
        self.cv = cv = tk.Canvas(top, width=W, height=H, highlightthickness=0, cursor="crosshair")
        cv.pack()
        self.foto = ImageTk.PhotoImage(tela)
        cv.create_image(0, 0, anchor="nw", image=self.foto)
        cv.create_rectangle(0, 0, W, 34, fill="#111111", outline="")
        cv.create_text(W // 2, 17, fill="#ffffff", font=("Segoe UI", 11, "bold"),
                       text=texto + "   |   Botão direito: desfaz   |   Enter: salvar   |   Esc: cancelar")
        for i, (txt, cor, cmd) in enumerate((("Cancelar", "#c0392b", lambda: self._fim(None)),
                                             ("Salvar", "#27ae60", lambda: self._fim(self.regioes)))):
            x1 = W - 10 - i * 100
            tag = f"bt{i}"
            cv.create_rectangle(x1 - 90, 4, x1, 30, fill=cor, outline="", tags=tag)
            cv.create_text(x1 - 45, 17, text=txt, fill="#ffffff",
                           font=("Segoe UI", 10, "bold"), tags=tag)
            cv.tag_bind(tag, "<ButtonRelease-1>", lambda _e, c=cmd: c())
        self.regioes, self.desenhos = [], []
        self.ini = None
        self.ret = None
        cv.bind("<ButtonPress-1>", self._press)
        cv.bind("<B1-Motion>", self._move)
        cv.bind("<ButtonRelease-1>", self._release)
        top.bind("<Button-3>", self._desfazer)
        top.bind("<Return>", lambda _e: self._fim(self.regioes))
        top.bind("<Escape>", lambda _e: self._fim(None))
        top.after(50, top.focus_force)

    def _press(self, e):
        if e.y < 34:                      # barra de instruções / botões
            return
        self.ini = (e.x, e.y)
        self.ret = self.cv.create_rectangle(e.x, e.y, e.x, e.y, outline="#00ff66", width=2)

    def _move(self, e):
        if self.ret:
            self.cv.coords(self.ret, *self.ini, e.x, e.y)

    def _release(self, e):
        if not self.ret:
            return
        x0, x1 = sorted((self.ini[0], e.x))
        y0, y1 = sorted((self.ini[1], e.y))
        if x1 - x0 < 6 or y1 - y0 < 6:
            self.cv.delete(self.ret)
            self.ret = None
            return
        txt = self.cv.create_text(x0, y0 - 10, text=str(len(self.regioes) + 1), anchor="w",
                                  fill="#00ff66", font=("Segoe UI", 10, "bold"))
        self.regioes.append((x0, y0, x1 - x0, y1 - y0))
        self.desenhos.append((self.ret, txt))
        self.ret = None

    def _desfazer(self, _e):
        if self.regioes:
            self.regioes.pop()
            for d in self.desenhos.pop():
                self.cv.delete(d)

    def _fim(self, regioes):
        self.top.destroy()
        self.ao_terminar(regioes)


# =============================================================== painel

class Painel:
    def __init__(self, root):
        self.root = root
        self.app_cfg = ler_json(ARQ_APP, {"ultimo_perfil": None, "iniciar_auto": False})
        migrar_config_antiga()
        if not Perfis.listar():
            Perfis.criar("Meu perfil")

        self.win = tk.Toplevel(root)
        self.win.title(f"{NOME_APP} v{VERSAO}")
        alt = min(680, self.win.winfo_screenheight() - 80)
        self.win.geometry(f"880x{alt}+40+20")
        self.win.minsize(760, 520)
        self.win.protocol("WM_DELETE_WINDOW", self.sair)
        self._aplicar_tema()

        self.nome = None
        self.perfil = None
        self._carregando = False
        self._salvar_agendado = False
        self._estava_ativo = False
        self._preenchendo = False
        self.banco = Banco()
        self.dp = DivinePride(self.app_cfg.get("dp_chave", ""))
        self.banco.dp = self.dp
        self.rag = RagAssets(self.app_cfg.get("usar_ragassets", True))
        self.banco.rag = self.rag
        self.banco.aplicar_nomes(self.rag.nomes)          # 1º ragassets (nomes do cliente LATAM)
        self.banco.aplicar_nomes(self.dp.nomes)           # depois o que veio da Divine Pride
        self._nomes_pedidos = set()
        self._nomes_recebidos = 0
        if self.rag.ligado:
            self.rag.pedir("nomes", None, "nomes")

        self.overlay = Overlay(root, self)
        self._montar_ui()
        self.atualizar_aba_avancado()

        ultimo = self.app_cfg.get("ultimo_perfil")
        lista = Perfis.listar()
        self.trocar_perfil(ultimo if ultimo in lista else lista[0])
        self.win.after(300, self._atualizar_status)
        if self.app_cfg.get("iniciar_auto") and self.perfil["skills"]:
            self.win.after(500, self.iniciar)
        # procura versão nova em segundo plano toda vez que o programa abre
        if self.app_cfg.get("verificar_atualizacoes", True):
            self.win.after(4000, lambda: self.verificar_atualizacao(False))

    # ---- tema e ícones

    def _aplicar_tema(self):
        self.escuro = True                       # visual preto + azul
        st = ttk.Style(self.root)
        self.tema_moderno = False
        if sv_ttk is not None:
            try:
                sv_ttk.set_theme("dark", self.root)
                try:
                    self.root.tk.call("configure_colors")   # aplica as cores já, sem esperar evento
                except tk.TclError:
                    pass
                self.tema_moderno = True
            except Exception:
                registrar("Tema moderno indisponível:\n" + traceback.format_exc())
        if not self.tema_moderno and "clam" in st.theme_names():
            st.theme_use("clam")
            st.configure(".", background="#1c1c1c", foreground="#fafafa",
                         fieldbackground="#2b2b2b")
        self.cor_fundo = str(st.lookup("TFrame", "background") or "") or "#1c1c1c"
        self.win.configure(bg=self.cor_fundo)
        st.configure("Dica.TLabel", foreground="#8b95a7")
        st.configure("Titulo.TLabel", font=("Segoe UI", 9, "bold"), foreground="#9cc3ff")
        # títulos das seções (caixas) mais visíveis
        st.configure("TLabelframe.Label", font=("Segoe UI", 10, "bold"), foreground="#9cc3ff")
        st.configure("Campo.TLabel", font=("Segoe UI", 10))

        branco = "#f4f7ff"
        self.ic = {n: ImageTk.PhotoImage(desenhar_icone(n, branco, 16)) for n in NOMES_ICONES}
        self.ic_dest = self.ic
        self.ic_escuro = {n: ImageTk.PhotoImage(desenhar_icone(n, "#1a1a1a", 16)) for n in NOMES_ICONES}
        self._logos = [ImageTk.PhotoImage(logo_app(t)) for t in (16, 32, 64)]
        try:
            self.win.iconphoto(True, *self._logos)
        except tk.TclError:
            pass
        self._criar_estilos(st)

    def _criar_estilos(self, st):
        """Botões com degradê preto→azul (vermelho no de ajuda) e abas bem marcadas."""
        self._imgs_estilo = []

        def foto(*args, **kw):
            img = ImageTk.PhotoImage(imagem_degrade(*args, **kw))
            self._imgs_estilo.append(img)
            return img

        for nome, (normal, hover, apertado) in DEGRADES.items():
            i_n = foto(40, 28, *normal[:2], borda=normal[2], raio=6)
            i_h = foto(40, 28, *hover[:2], borda=hover[2], raio=6)
            i_p = foto(40, 28, *apertado[:2], borda=apertado[2], raio=6)
            i_d = foto(40, 28, "#1b1f27", "#14171d", borda="#2a2f3a", raio=6)
            elem = f"{nome}.botao"
            try:
                st.element_create(elem, "image", i_n, ("disabled", i_d), ("pressed", i_p),
                                  ("active", i_h), border=(8, 7, 8, 7), sticky="nsew")
            except tk.TclError:
                pass                             # já existe
            estilo = f"{nome}.TButton"
            st.layout(estilo, [(elem, {"sticky": "nsew", "children": [
                ("Button.padding", {"sticky": "nsew", "children": [
                    ("Button.label", {"sticky": "nsew"})]})]})])
            st.configure(estilo, foreground="#1a1a1a" if nome in TEXTO_ESCURO else "#ffffff",
                         padding=(6, 1), anchor="center")
            st.map(estilo, foreground=[("disabled", "#6b7280")])
            st.configure(f"Icone.{estilo}", padding=(1, 1))   # botões só com ícone
        self.estilo_padrao = "Grad.TButton"
        self.estilo_destaque = "Destaque.TButton"

        # Abas: a selecionada fica azul, com faixa clara no topo e texto branco em negrito
        t_n = foto(40, 34, "#161b26", "#11151d", raio=7, so_topo=True)
        t_h = foto(40, 34, "#1f2a40", "#141b2a", raio=7, so_topo=True)
        t_s = foto(40, 34, "#2563eb", "#0f1d3d", raio=7, so_topo=True, faixa="#7cc0ff")
        try:
            st.element_create("Aba.tab", "image", t_n, ("selected", t_s), ("active", t_h),
                              border=(8, 8, 8, 2), sticky="nsew")
        except tk.TclError:
            pass
        st.layout("TNotebook.Tab", [("Aba.tab", {"sticky": "nsew", "children": [
            ("Notebook.padding", {"side": "top", "sticky": "nsew", "children": [
                ("Notebook.label", {"side": "top", "sticky": ""})]})]})])
        st.configure("TNotebook.Tab", padding=(18, 7), foreground="#8b95a7")
        st.configure("TNotebook", tabmargins=(2, 4, 2, 0))
        st.map("TNotebook.Tab",
               foreground=[("selected", "#ffffff"), ("active", "#dbe7ff")],
               expand=[("selected", (0, 0, 0, 0))],
               font=[("selected", ("Segoe UI", 10, "bold")), ("!selected", ("Segoe UI", 10))])

    def dica(self, widget, texto):
        """Explicação que aparece ao parar o mouse em cima de um botão ou opção."""
        estado = {"janela": None, "agendado": None}

        def mostrar():
            estado["agendado"] = None
            if estado["janela"] or not widget.winfo_exists():
                return
            j = tk.Toplevel(widget)
            j.overrideredirect(True)
            j.attributes("-topmost", True)
            tk.Label(j, text=texto, justify="left", wraplength=320, bg="#0f1420", fg="#e6ecf7",
                     font=("Segoe UI", 9), padx=10, pady=6, bd=1, relief="solid",
                     highlightthickness=0).pack()
            x = widget.winfo_rootx() + 8
            y = widget.winfo_rooty() + widget.winfo_height() + 6
            j.geometry(f"+{x}+{y}")
            estado["janela"] = j

        def entrar(_e):
            estado["agendado"] = widget.after(450, mostrar)

        def sair(_e):
            if estado["agendado"]:
                widget.after_cancel(estado["agendado"])
                estado["agendado"] = None
            if estado["janela"]:
                estado["janela"].destroy()
                estado["janela"] = None

        widget.bind("<Enter>", entrar, add="+")
        widget.bind("<Leave>", sair, add="+")
        widget.bind("<ButtonPress>", sair, add="+")
        return widget

    def bt(self, pai, texto, icone, cmd, destaque=False, perigo=False, amarelo=False, **kw):
        """Botão com ícone à esquerda do texto (ou só o ícone, se texto vazio)."""
        estilo = ("Amarelo.TButton" if amarelo else "Perigo.TButton" if perigo else
                  self.estilo_destaque if destaque else self.estilo_padrao)
        if not texto:
            estilo = "Icone." + estilo
        icones = self.ic_escuro if amarelo else self.ic
        return ttk.Button(pai, text=texto, image=icones.get(icone),
                          compound="left" if texto else "image",
                          command=cmd, style=estilo, **kw)

    # ---- interface

    def _montar_ui(self):
        w = self.win
        pad = {"padx": 8, "pady": 4}

        # Perfil
        fp = ttk.LabelFrame(w, text="Perfil")
        fp.pack(fill="x", **pad)
        self.var_perfil = tk.StringVar()
        self.cb_perfil = ttk.Combobox(fp, textvariable=self.var_perfil, state="readonly", width=30)
        self.cb_perfil.pack(side="left", padx=6, pady=6)
        self.cb_perfil.bind("<<ComboboxSelected>>",
                            lambda _e: self.trocar_perfil(self.var_perfil.get()))
        for txt, ic, cmd in (("Novo", "mais", self.novo_perfil),
                             ("Duplicar", "copiar", self.duplicar_perfil),
                             ("Renomear", "lapis", self.renomear_perfil),
                             ("Excluir", "lixeira", self.excluir_perfil)):
            self.bt(fp, txt, ic, cmd).pack(side="left", padx=2)

        # Skills
        # Abas: deixa a janela compacta (cabe em telas de notebook)
        self.abas = nb = ttk.Notebook(w)
        nb.pack(fill="both", expand=True, padx=8, pady=(4, 4))
        aba_sk, aba_ap, aba_av = ttk.Frame(nb), ttk.Frame(nb), ttk.Frame(nb)
        aba_bf = ttk.Frame(nb)
        nb.add(aba_sk, text=" Skills", image=self.ic["relogio"], compound="left")
        nb.add(aba_bf, text=" Buffs", image=self.ic["escudo"], compound="left")
        self._montar_aba_buffs(aba_bf)
        nb.add(aba_ap, text=" Aparência", image=self.ic["mover"], compound="left")
        nb.add(aba_av, text=" Avançado", image=self.ic["chave"], compound="left")
        self.aba_av = aba_av

        fs = ttk.Frame(aba_sk)
        fs.pack(fill="both", expand=True, padx=4, pady=4)
        barra = ttk.Frame(fs)
        barra.pack(fill="x", padx=6, pady=(6, 2))
        self.dica(self.bt(barra, "Skill pelo nome", "mais_circulo",
                          lambda: SeletorSkill(self, None, nova=True), amarelo=True),
                  "O jeito mais fácil: escolha a skill pelo nome e o programa baixa o ícone "
                  "e acha ela sozinho na sua barra de atalhos.").pack(side="left")
        self.dica(self.bt(barra, "Marcar ícones na tela", "selecao",
                          lambda: self.marcar_icones(True)),
                  "A tela congela e você arrasta um quadrado sobre cada skill da barra de "
                  "atalhos (com as skills prontas). Substitui os ícones deste perfil."
                  ).pack(side="left", padx=(4, 0))
        self.dica(self.bt(barra, "Adicionar mais", "mais", lambda: self.marcar_icones(False)),
                  "Igual a \"Marcar ícones na tela\", mas mantém as skills que você já tem."
                  ).pack(side="left", padx=4)
        self.dica(self.bt(barra, "Procurar na tela", "radar", self.procurar_icones),
                  "Mudou a barra de atalhos de lugar? O programa procura os ícones de novo."
                  ).pack(side="left")
        barra2 = ttk.Frame(fs)
        barra2.pack(fill="x", padx=6, pady=(2, 2))
        ttk.Label(barra2, text="Sua classe:").pack(side="left")
        self.var_classe = tk.StringVar(value=TODAS)
        cb_cl = ttk.Combobox(barra2, textvariable=self.var_classe, state="readonly", width=24,
                             values=[TODAS] + self.banco.classes)
        cb_cl.pack(side="left", padx=4)
        cb_cl.bind("<<ComboboxSelected>>", lambda _e: self._on_classe())
        ttk.Label(fs, style="Dica.TLabel",
                  wraplength=760, justify="left",
                  text="Clique em \"Buscar\" para escolher a skill do banco (a recarga vem junto), "
                       "ou digite a recarga (12, 4.5 ou 1:30). Vazio = aprender sozinho."
                  ).pack(anchor="w", padx=8)

        cont = ttk.Frame(fs)
        cont.pack(fill="both", expand=True, padx=6, pady=6)
        self.lista_cv = tk.Canvas(cont, highlightthickness=0, height=150, bg=self.cor_fundo)
        sb = ttk.Scrollbar(cont, orient="vertical", command=self.lista_cv.yview)
        self.lista = ttk.Frame(self.lista_cv)
        self.lista.bind("<Configure>", lambda _e: self.lista_cv.configure(
            scrollregion=self.lista_cv.bbox("all")))
        self.lista_cv.create_window((0, 0), window=self.lista, anchor="nw")
        self.lista_cv.configure(yscrollcommand=sb.set)
        self.lista_cv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        rolar = lambda e: self.lista_cv.yview_scroll(-1 if e.delta > 0 else 1, "units")
        self.lista_cv.bind("<Enter>", lambda _e: self.lista_cv.bind_all("<MouseWheel>", rolar))
        self.lista_cv.bind("<Leave>", lambda _e: self.lista_cv.unbind_all("<MouseWheel>"))

        # Aparência
        # Duas colunas de seções: à esquerda o visual dos ícones e a posição,
        # à direita quando o overlay aparece e a barra de AP.
        fa = ttk.Frame(aba_ap)
        fa.pack(fill="both", expand=True, padx=4, pady=6)
        fa.columnconfigure(0, weight=1, uniform="col")
        fa.columnconfigure(1, weight=1, uniform="col")
        esq, dir_ = ttk.Frame(fa), ttk.Frame(fa)
        esq.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        dir_.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        self.var_tam = tk.DoubleVar()
        self.var_esp = tk.DoubleVar()
        self.var_ori = tk.StringVar()
        self.var_esconder = tk.BooleanVar()
        self.var_sem_foco = tk.BooleanVar()
        self.var_capturas = tk.BooleanVar(value=bool(self.app_cfg.get("visivel_em_capturas")))
        self.var_estilo = tk.StringVar()
        self.var_painel = tk.BooleanVar()
        self.var_nomes = tk.BooleanVar()
        self.var_ap = tk.BooleanVar()
        self.var_ap_alt = tk.DoubleVar()

        def deslizante(pai, linha, rotulo, de, ate, var, cmd, ajuda):
            ttk.Label(pai, text=rotulo, style="Campo.TLabel").grid(
                row=linha, column=0, sticky="w", padx=(8, 6), pady=(6, 0))
            sc = ttk.Scale(pai, from_=de, to=ate, orient="horizontal", variable=var, command=cmd)
            sc.grid(row=linha, column=1, sticky="ew", pady=(6, 0))
            valor = ttk.Label(pai, width=7, anchor="e")
            valor.grid(row=linha, column=2, sticky="e", padx=(4, 8), pady=(6, 0))
            ttk.Label(pai, text=ajuda, style="Dica.TLabel", wraplength=360, justify="left").grid(
                row=linha + 1, column=0, columnspan=3, sticky="w", padx=8)
            self.dica(sc, ajuda)
            return valor

        # --- Ícones
        fi = ttk.LabelFrame(esq, text="Ícones")
        fi.pack(fill="x", pady=(0, 8))
        fi.columnconfigure(1, weight=1)
        self.lbl_tam = deslizante(fi, 0, "Tamanho do ícone", 20, 160, self.var_tam, self._on_tam,
                                  "Largura e altura de cada ícone no overlay.")
        self.lbl_esp = deslizante(fi, 2, "Espaço entre ícones", 0, 40, self.var_esp, self._on_esp,
                                  "Distância entre um ícone e o próximo.")
        ttk.Label(fi, text="Direção da fila", style="Campo.TLabel").grid(
            row=4, column=0, sticky="w", padx=(8, 6), pady=(8, 0))
        fdir = ttk.Frame(fi)
        fdir.grid(row=4, column=1, columnspan=2, sticky="w", pady=(8, 0))
        for txt, val in (("Lado a lado", "horizontal"), ("Em coluna", "vertical")):
            ttk.Radiobutton(fdir, text=txt, value=val, variable=self.var_ori,
                            command=self._on_ori).pack(side="left", padx=(0, 10))
        ttk.Label(fi, text="Estilo", style="Campo.TLabel").grid(
            row=5, column=0, sticky="w", padx=(8, 6), pady=(8, 0))
        cb_est = ttk.Combobox(fi, textvariable=self.var_estilo, state="readonly", width=14,
                              values=list(ESTILOS))
        cb_est.grid(row=5, column=1, sticky="w", pady=(8, 0))
        cb_est.bind("<<ComboboxSelected>>", lambda _e: self._on_estilo())
        self.dica(cb_est, "Moderno: cantos arredondados e borda colorida pelo estado.\n"
                          "Minimalista: só o ícone, sem borda.\nClássico: quadrado, como antes.")
        c = ttk.Checkbutton(fi, text="Caixa escura atrás dos ícones", variable=self.var_painel,
                            command=self._on_estilo)
        c.grid(row=6, column=0, columnspan=3, sticky="w", padx=8, pady=(8, 0))
        self.dica(c, "Um fundo escuro agrupando todos os ícones. Ajuda a ler sobre cenários claros.")
        c = ttk.Checkbutton(fi, text="Nome da skill/buff embaixo de cada ícone",
                            variable=self.var_nomes, command=self._on_estilo)
        c.grid(row=7, column=0, columnspan=3, sticky="w", padx=8, pady=(4, 8))

        # --- Posição na tela
        fpos = ttk.LabelFrame(esq, text="Posição na tela")
        fpos.pack(fill="x")
        lb = ttk.Frame(fpos)
        lb.pack(fill="x", padx=8, pady=(6, 2))
        self.bt_mover = self.bt(lb, "Mover / redimensionar", "mover", self.alternar_mover)
        self.bt_mover.pack(side="left")
        self.dica(self.bt_mover, "Mostra o overlay como uma caixa amarela: arraste para mudar de "
                                 "lugar e use a roda do mouse para aumentar ou diminuir. "
                                 "Clique de novo em \"Concluir posição\" para salvar.")
        b_cent = self.bt(lb, "Centralizar", "centro", lambda: self.overlay.centralizar())
        b_cent.pack(side="left", padx=6)
        self.dica(b_cent, "Volta o overlay para o meio da janela do jogo.")
        ttk.Label(fpos, style="Dica.TLabel", wraplength=360, justify="left",
                  text="No modo mover: arraste a caixa amarela; a roda do mouse muda o tamanho."
                  ).pack(anchor="w", padx=8, pady=(0, 8))

        # --- Quando mostrar
        fq = ttk.LabelFrame(dir_, text="Quando mostrar")
        fq.pack(fill="x", pady=(0, 8))
        for var, txt, cmd, ajuda in (
                (self.var_esconder, "Skills só aparecem em recarga",
                 self._on_esconder, "Esconde o ícone da skill enquanto ela está pronta para usar."),
                (self.var_sem_foco, "Esconder com o jogo fora de foco",
                 self._on_sem_foco, "Desmarcado: o overlay aparece sempre que o jogo estiver "
                                    "visível, mesmo usando outro programa."),
                (self.var_capturas, "Aparecer em prints e lives",
                 self._on_capturas, "Para OBS, Discord e prints. Com esta opção ligada, deixe o "
                                    "overlay longe da barra de atalhos do jogo.")):
            c = ttk.Checkbutton(fq, text=txt, variable=var, command=cmd)
            c.pack(anchor="w", padx=8, pady=(6, 0))
            self.dica(c, ajuda)
            ttk.Label(fq, text=ajuda, style="Dica.TLabel", wraplength=340, justify="left").pack(
                anchor="w", padx=34)
        ttk.Frame(fq, height=6).pack()

        # --- Barra de AP
        fap = ttk.LabelFrame(dir_, text="Barra de AP")
        fap.pack(fill="x")
        fap.columnconfigure(1, weight=1)
        ttk.Checkbutton(fap, text="Mostrar a barra de AP", variable=self.var_ap,
                        command=self._on_ap).grid(row=0, column=0, columnspan=3, sticky="w",
                                                  padx=8, pady=(6, 0))
        self.lbl_ap = ttk.Label(fap, style="Dica.TLabel", text="")
        self.lbl_ap.grid(row=1, column=0, columnspan=3, sticky="w", padx=34)
        self.lbl_ap_alt = deslizante(fap, 2, "Altura da barra", 8, 40, self.var_ap_alt,
                                     self._on_ap_altura, "Fica colada acima dos ícones. Deixe a "
                                     "janela Informações básicas aberta no jogo: o AP é lido dela.")
        lc = ttk.Frame(fap)
        lc.grid(row=4, column=0, columnspan=3, sticky="w", padx=8, pady=(8, 8))
        b_cor = self.bt(lc, "Cor da barra", "lapis", self._escolher_cor_ap)
        b_cor.pack(side="left")
        self.amostra_ap = tk.Label(lc, width=3, relief="flat", bd=0)
        self.amostra_ap.pack(side="left", padx=(6, 12), ipady=6)
        self.bt_ap_manual = self.bt(lc, "Marcar à mão", "selecao", self._ap_manual_ou_auto)
        self.bt_ap_manual.pack(side="left")
        self.dica(self.bt_ap_manual, "Normalmente o programa acha o AP sozinho. Use só se a "
                                     "busca automática não funcionar no seu jogo.")
        b_diag = self.bt(lc, "", "ajuda", self.diagnostico_ap)
        b_diag.pack(side="left", padx=6)
        self.dica(b_diag, "Diagnóstico: salva o que o programa está vendo do AP, para mandar "
                          "a quem dá suporte.")

        # Detecção
        fd = ttk.LabelFrame(aba_av, text="Detecção das skills (só mexa se algo não funcionar)")
        fd.pack(fill="x", padx=4, pady=(8, 4))
        self.var_min = tk.StringVar()
        self.var_lim = tk.StringVar()
        self.var_titulo = tk.StringVar()
        for linha, (rotulo, widget, ajuda) in enumerate((
                ("Delay global da sua build (segundos)",
                 ttk.Spinbox(fd, from_=0, to=5, increment=0.1, width=7, textvariable=self.var_min),
                 "Coloque um pouco acima do delay pós-conjuração da sua build. Se o contador "
                 "demora a aparecer, diminua; se aparecem contadores falsos, aumente."),
                ("Sensibilidade (menor = mais sensível)",
                 ttk.Spinbox(fd, from_=0.03, to=0.5, increment=0.01, width=7,
                             textvariable=self.var_lim),
                 "Quanto o ícone precisa escurecer para contar como recarga. Padrão: 0,1."),
                ("Nome da janela do jogo",
                 ttk.Entry(fd, textvariable=self.var_titulo, width=20),
                 "Parte do título da janela do jogo (padrão: Ragnarok)."))):
            ttk.Label(fd, text=rotulo, style="Campo.TLabel").grid(
                row=linha * 2, column=0, sticky="w", padx=8, pady=(6, 0))
            widget.grid(row=linha * 2, column=1, sticky="w", pady=(6, 0))
            ttk.Label(fd, text=ajuda, style="Dica.TLabel", wraplength=760, justify="left").grid(
                row=linha * 2 + 1, column=0, columnspan=3, sticky="w", padx=8)
            self.dica(widget, ajuda)
        ttk.Frame(fd, height=6).grid(row=6, column=0)
        self.var_min.trace_add("write", lambda *_: self._on_deteccao())
        self.var_lim.trace_add("write", lambda *_: self._on_deteccao())
        self.var_titulo.trace_add("write", lambda *_: self._on_deteccao())

        # Divine Pride
        fat = ttk.LabelFrame(aba_av, text="Atualizações")
        fat.pack(fill="x", padx=4, pady=4)
        lat = ttk.Frame(fat)
        lat.pack(fill="x", padx=8, pady=(6, 2))
        ttk.Label(lat, text=f"Versão instalada: v{VERSAO}", style="Campo.TLabel").pack(side="left")
        b_at = self.bt(lat, "Verificar atualizações", "radar", lambda: self.verificar_atualizacao(True))
        b_at.pack(side="left", padx=12)
        self.dica(b_at, "Procura uma versão nova no projeto do GitHub e, "
                        "se houver, baixa e instala sozinho. Seus perfis e configurações não "
                        "são apagados.")
        self.var_auto_at = tk.BooleanVar(value=self.app_cfg.get("verificar_atualizacoes", True))
        ttk.Checkbutton(lat, text="Verificar sozinho ao abrir",
                        variable=self.var_auto_at, command=self._on_auto_at).pack(side="left")
        self.lbl_at = ttk.Label(fat, style="Dica.TLabel", text="")
        self.lbl_at.pack(anchor="w", padx=8, pady=(0, 6))

        frag = ttk.LabelFrame(aba_av, text="Fonte principal: ragassets (latam-tools)")
        frag.pack(fill="x", padx=4, pady=4)
        self.var_rag = tk.BooleanVar(value=bool(self.app_cfg.get("usar_ragassets", True)))
        ttk.Checkbutton(frag, text="Baixar ícones e nomes do ragassets (do cliente LATAM, sem chave)",
                        variable=self.var_rag, command=self._on_rag).pack(anchor="w", padx=6, pady=(6, 0))
        self.lbl_rag = ttk.Label(frag, style="Dica.TLabel", text="")
        self.lbl_rag.pack(anchor="w", padx=34, pady=(0, 6))

        fdp = ttk.LabelFrame(aba_av, text="Divine Pride (opcional: recarga do LATAM e ícones)")
        fdp.pack(fill="x", padx=4, pady=4)
        ttk.Label(fdp, image=self.ic["chave"]).pack(side="left", padx=(6, 2), pady=6)
        ttk.Label(fdp, text="Chave da API:").pack(side="left", padx=(0, 4), pady=6)
        self.var_dp = tk.StringVar(value=self.app_cfg.get("dp_chave", ""))
        ttk.Entry(fdp, textvariable=self.var_dp, width=34, show="•").pack(side="left")
        self.bt(fdp, "Salvar e testar", "check", self.testar_dp).pack(side="left", padx=6)
        self.bt(fdp, "Como pegar a chave?", "ajuda", self.ajuda_dp, perigo=True).pack(side="left")
        self.lbl_dp = ttk.Label(fdp, style="Dica.TLabel",
                                text=""
                                if not self.dp.ativo() else "Chave salva.")
        self.lbl_dp.pack(side="left", padx=4)

        # Rodapé
        fr = ttk.Frame(w)
        self.bt_iniciar = self.bt(fr, "Iniciar overlay", "play", self.alternar_overlay, destaque=True)
        self.dica(self.bt_iniciar, "Liga ou desliga o overlay em cima do jogo.")
        self.bt_iniciar.pack(side="left")
        self.var_auto = tk.BooleanVar(value=bool(self.app_cfg.get("iniciar_auto")))
        self.dica(ttk.Checkbutton(fr, text="Iniciar automaticamente ao abrir",
                                  variable=self.var_auto, command=self._on_auto),
                  "Liga o overlay sozinho toda vez que o programa abrir.").pack(side="left", padx=12)
        self.dica(self.bt(fr, "Pasta de dados", "pasta", lambda: os.startfile(PASTA)),
                  "Abre a pasta com seus perfis e os arquivos de log (log.txt, erro.log)."
                  ).pack(side="right")
        self.dica(self.bt(fr, "Tirar print", "camera", self.tirar_print),
                  "Contagem de 5 s: volte ao jogo e use uma skill. O print sai com o overlay."
                  ).pack(side="right", padx=6)
        self.lbl_status = ttk.Label(w, text="", style="Dica.TLabel")
        self.lbl_status.pack(side="bottom", fill="x", padx=10, pady=(0, 8), before=fp)
        fr.pack(side="bottom", fill="x", padx=8, pady=(4, 2), before=fp)

    def status(self, txt):
        self.lbl_status.config(text=txt)

    # ---- buffs

    def _montar_aba_buffs(self, aba):
        f = ttk.Frame(aba)
        f.pack(fill="both", expand=True, padx=4, pady=4)
        barra = ttk.Frame(f)
        barra.pack(fill="x", padx=6, pady=(6, 2))
        self.dica(self.bt(barra, "Buff pelo nome", "mais_circulo",
                          lambda: SeletorSkill(self, None, buff=True), amarelo=True),
                  "O jeito mais fácil: escolha o buff pelo nome. O programa baixa todos os "
                  "ícones dele e o acha na tela quando estiver ativo.").pack(side="left")
        self.dica(self.bt(barra, "Marcar na tela", "mais", self.adicionar_buff),
                  "Com o buff ativo no jogo, marque o ícone dele na coluna de buffs "
                  "(à direita da tela).").pack(side="left", padx=4)
        self.dica(self.bt(barra, "Área dos buffs", "selecao", self.marcar_area_buffs),
                  "Opcional: marque a região onde os buffs aparecem para a leitura ficar "
                  "mais leve. Sem marcar, o programa olha o lado direito do jogo."
                  ).pack(side="left", padx=4)
        self.dica(self.bt(barra, "Importar", "importar", self.importar_buffs),
                  "Traz buffs de um arquivo .zip exportado por outra pessoa.").pack(side="right")
        self.dica(self.bt(barra, "Exportar", "exportar", self.exportar_buffs),
                  "Salva seus buffs num .zip para passar a um amigo (em particular)."
                  ).pack(side="right", padx=4)
        self.lbl_area = ttk.Label(barra, style="Dica.TLabel")
        self.lbl_area.pack(side="left", padx=8)
        ttk.Label(f, style="Dica.TLabel", wraplength=760, justify="left",
                  text="\"Buff pelo nome\": escolha o buff e o programa baixa os ícones (todas as "
                       "versões, ex.: os 7 elementos da Brisa Leve) pela Divine Pride e acha o buff na "
                       "tela quando ele estiver ativo. Sem a chave da API, use \"Marcar na tela\" com o "
                       "buff ativo e \"Auto\" para pegar as outras versões."
                  ).pack(anchor="w", padx=8, pady=(2, 4))
        cont = ttk.Frame(f)
        cont.pack(fill="both", expand=True, padx=6, pady=4)
        self.buffs_cv = tk.Canvas(cont, highlightthickness=0, height=150, bg=self.cor_fundo)
        sb = ttk.Scrollbar(cont, orient="vertical", command=self.buffs_cv.yview)
        self.lista_buffs = ttk.Frame(self.buffs_cv)
        self.lista_buffs.bind("<Configure>", lambda _e: self.buffs_cv.configure(
            scrollregion=self.buffs_cv.bbox("all")))
        self.buffs_cv.create_window((0, 0), window=self.lista_buffs, anchor="nw")
        self.buffs_cv.configure(yscrollcommand=sb.set)
        self.buffs_cv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    def montar_buffs(self):
        for wdg in self.lista_buffs.winfo_children():
            wdg.destroy()
        a = self.perfil.get("area_buffs")
        self.lbl_area.config(text="Área: marcada ✓" if a else "Área: lado direito")
        buffs = self.perfil.get("buffs", [])
        if not buffs:
            ttk.Label(self.lista_buffs, justify="left", text=(
                "Nenhum buff ainda.\n"
                "  1. No jogo, deixe o buff ativo (por exemplo, use a Brisa Leve).\n"
                "  2. Clique em \"Adicionar buff\", dê um nome e marque o ícone dele na tela.\n"
                "  3. Para outra versão do ícone (outro elemento), clique em \"+ Ícone\".")
                      ).grid(row=0, column=0, padx=6, pady=10, sticky="w")
            return
        for col, t in enumerate(("Ícones", "Nome", "", "Mostrar", "Duração",
                                 "Estado", "")):
            ttk.Label(self.lista_buffs, text=t, style="Titulo.TLabel").grid(
                row=0, column=col, padx=4, sticky="w")
        for i, bf in enumerate(buffs):
            r = i + 1
            fi = ttk.Frame(self.lista_buffs)
            fi.grid(row=r, column=0, padx=4, pady=3, sticky="w")
            imgs = bf.get("_imgs") or [icone_dp_rgb(p) for p in
                                       (self.icone_buff(e) for _, e in bf.get("efst", [])) if p]
            bf["_thumbs"] = [ImageTk.PhotoImage(im.resize((24, 24), Image.NEAREST))
                             for im in imgs[:1]]
            for th in bf["_thumbs"]:
                ttk.Label(fi, image=th).pack(side="left", padx=1)
            if not bf["_thumbs"]:
                ttk.Label(fi, text="—", style="Dica.TLabel").pack(side="left")
            elif len(imgs) > 1:               # buff com várias versões (ex.: Brisa Leve)
                ttk.Label(fi, text=f"×{len(imgs)}", style="Dica.TLabel").pack(side="left", padx=2)

            vn = tk.StringVar(value=bf.get("nome", ""))
            ttk.Entry(self.lista_buffs, textvariable=vn, width=11).grid(row=r, column=1, padx=2)
            vn.trace_add("write", lambda *_, b=bf, v=vn: (b.__setitem__("nome", v.get()),
                                                          self.salvar_depois()))
            fb = ttk.Frame(self.lista_buffs)
            fb.grid(row=r, column=2, padx=2)
            self.dica(self.bt(fb, "Ícone", "mais", lambda b=bf: self.capturar_variante(b)),
                      "Marcar à mão mais uma versão do ícone deste buff.").pack(side="left")
            self.dica(self.bt(fb, "Auto", "radar", lambda b=bf: self.captura_auto(b)),
                      "Use o buff no jogo com cada elemento/versão: cada ícone novo é salvo "
                      "sozinho.").pack(side="left", padx=(4, 0))

            inv = {v: k for k, v in MOSTRAR_BUFF.items()}
            vm = tk.StringVar(value=inv.get(bf.get("mostrar", "sempre"), "Sempre"))
            cb = ttk.Combobox(self.lista_buffs, textvariable=vm, state="readonly", width=10,
                              values=list(MOSTRAR_BUFF))
            cb.grid(row=r, column=3, padx=2)
            cb.bind("<<ComboboxSelected>>", lambda _e, b=bf, v=vm: (
                b.__setitem__("mostrar", MOSTRAR_BUFF[v.get()]), self.salvar_depois()))

            vd = tk.StringVar(value=fmt_tempo(bf.get("duracao")))
            ed = ttk.Entry(self.lista_buffs, textvariable=vd, width=5, justify="center")
            ed.grid(row=r, column=4, padx=2)
            vd.trace_add("write", lambda *_, b=bf, v=vd, e=ed: self._on_duracao(b, v, e))
            bf["_tk"] = (vn, vm, vd)

            bf["_lbl_est"] = ttk.Label(self.lista_buffs, text="—", width=10)
            bf["_lbl_est"].grid(row=r, column=5, padx=2)
            fo = ttk.Frame(self.lista_buffs)
            fo.grid(row=r, column=6, padx=(2, 0))
            self.bt(fo, "", "cima", lambda k=i: self.mover_buff(k, -1)).pack(side="left")
            self.bt(fo, "", "baixo", lambda k=i: self.mover_buff(k, 1)).pack(side="left", padx=2)
            self.bt(fo, "", "lixeira", lambda k=i: self.remover_buff(k)).pack(side="left", padx=(6, 0))

    def icone_buff(self, eid):
        """Ícone de um buff já baixado: ragassets primeiro, depois Divine Pride."""
        return self.rag.icone_status(eid) or self.dp.icone_efst(eid)

    def icone_skill(self, sid):
        return self.rag.icone_skill(sid) or self.dp.icone(sid)

    def adicionar_buff_por_nome(self, nome):
        """Buff escolhido no banco: baixa os ícones (Divine Pride) e acha o buff na tela."""
        efst = self.banco.efst_de(nome)
        if not efst:
            return
        tem_todos = all(self.icone_buff(e) for _, e in efst)
        if not tem_todos and not self.rag.disponivel() and not self.dp.ativo():
            if messagebox.askyesno(
                    "Buff pelo nome",
                    "Não consegui baixar os ícones agora (o ragassets não respondeu e não há "
                    "chave da Divine Pride na aba Avançado).\n\n"
                    "Quer marcar o ícone na tela agora, do jeito manual?",
                    parent=self.win):
                self._novo_buff(nome, capturar=True)
            return
        bf = self._novo_buff(nome, capturar=False)
        bf["efst"] = [list(e) for e in efst]
        self.salvar_agora()
        pend = set()
        for chave_e, eid in efst:
            if self.rag.icone_status(eid):
                continue
            if self.rag.disponivel():
                pend.add(eid)                         # espera o ragassets antes de procurar
                self.rag.pedir("status", eid, ("buff", id(bf), chave_e))
            elif not self.icone_buff(eid):
                self.dp.pedir_efst(eid, chave_e, ("buff", id(bf)))
        bf["_rag_pend"] = pend
        if not self.overlay.ativo:
            self.iniciar()
        self.status(f"{nome}: baixando {len(efst)} ícone(s). Deixe o buff ATIVO no jogo "
                    "para eu achar o tamanho do ícone na tela.")

    def _novo_buff(self, nome, capturar):
        bf = {"nome": nome, "variantes": [], "mostrar": "sempre", "duracao": None}
        self.perfil.setdefault("buffs", []).append(bf)
        self.salvar_agora()
        self.overlay.carregar_perfil(self.perfil, Perfis.pasta(self.nome))
        self.montar_buffs()
        if capturar:
            self.capturar_variante(bf)
        return bf

    def captura_auto(self, bf):
        if np is None or cv2 is None:
            messagebox.showinfo("Captura automática", "Instale os pacotes: pip install numpy "
                                "opencv-python (o iniciar.bat já faz isso).", parent=self.win)
            return
        if not bf.get("_tmpls"):
            messagebox.showinfo("Captura automática",
                                "Primeiro salve UMA versão do ícone com \"+ Ícone\".\n"
                                "Depois o modo automático pega as outras sozinho.", parent=self.win)
            return
        CapturaAuto(self, bf)

    def exportar_buffs(self):
        buffs = [b for b in self.perfil.get("buffs", []) if b.get("variantes")]
        if not buffs:
            self.status("Nenhum buff com ícone para exportar.")
            return
        arq = filedialog.asksaveasfilename(
            parent=self.win, title="Exportar buffs", defaultextension=".zip",
            initialfile=f"buffs_{nome_seguro(self.nome).replace(' ', '_')}.zip",
            filetypes=[("Pacote de buffs", "*.zip")])
        if not arq:
            return
        pasta = Perfis.pasta(self.nome)
        dados = {"tipo": "ro-cooldown-overlay/buffs", "versao": 1, "buffs": []}
        try:
            with zipfile.ZipFile(arq, "w", zipfile.ZIP_DEFLATED) as z:
                for i, b in enumerate(buffs):
                    nomes = []
                    for j, v in enumerate(b["variantes"]):
                        if (pasta / v).exists():
                            nomes.append(f"icones/{i}_{j}.png")
                            z.write(pasta / v, nomes[-1])
                    dados["buffs"].append({"nome": b.get("nome", ""), "mostrar": b.get("mostrar", "sempre"),
                                           "duracao": b.get("duracao"), "icones": nomes})
                z.writestr("buffs.json", json.dumps(dados, ensure_ascii=False, indent=1))
        except Exception as e:
            registrar("Erro ao exportar buffs:\n" + traceback.format_exc())
            messagebox.showerror("Exportar buffs", f"Não consegui exportar: {e}", parent=self.win)
            return
        self.status(f"{len(buffs)} buff(s) exportado(s) para {Path(arq).name}. Para um amigo: "
                    "é só ele colocar o arquivo na pasta do programa e abrir.")

    def importar_buffs(self):
        arq = filedialog.askopenfilename(parent=self.win, title="Importar buffs",
                                         filetypes=[("Pacote de buffs", "*.zip")])
        if not arq:
            return
        try:
            novos, versoes = self._importar_pacote(arq)
        except Exception as e:
            registrar("Erro ao importar buffs:\n" + traceback.format_exc())
            messagebox.showerror("Importar buffs", f"Não consegui importar: {e}", parent=self.win)
            return
        self._depois_de_importar()
        self.status(f"Importado: {novos} buff(s) novo(s), {versoes} ícone(s) novo(s).")

    def _depois_de_importar(self):
        self.salvar_agora()
        self.overlay.carregar_perfil(self.perfil, Perfis.pasta(self.nome))
        self.montar_buffs()

    def _importar_pacote(self, arq):
        """Junta os buffs de um pacote .zip ao perfil atual. Devolve (buffs novos, ícones novos).
        Versões que o perfil já tem são ignoradas, então importar de novo não duplica nada."""
        pasta = Perfis.pasta(self.nome)
        buffs = self.perfil.setdefault("buffs", [])
        novos = versoes = 0
        with zipfile.ZipFile(arq) as z:
            dados = json.loads(z.read("buffs.json").decode("utf-8"))
            if dados.get("tipo") != "ro-cooldown-overlay/buffs":
                raise ValueError("este arquivo não é um pacote de buffs do RO Cooldown Overlay")
            nomes_zip = set(z.namelist())
            for item in dados.get("buffs", [])[:50]:
                nome = str(item.get("nome", "")).strip()[:60] or "Buff"
                alvo = next((b for b in buffs if chave(b.get("nome", "")) == chave(nome)), None)
                if alvo is None:
                    dur = item.get("duracao")
                    alvo = {"nome": nome, "variantes": [],
                            "mostrar": item.get("mostrar") if item.get("mostrar") in
                            MOSTRAR_BUFF.values() else "sempre",
                            "duracao": float(dur) if isinstance(dur, (int, float)) and dur > 0 else None}
                    buffs.append(alvo)
                    novos += 1
                ja = set()
                for v in alvo.get("variantes", []):        # evita versões repetidas
                    try:
                        ja.add(hashlib.sha1(Image.open(pasta / v).convert("RGB").tobytes()).hexdigest())
                    except Exception:
                        pass
                for n in item.get("icones", [])[:20]:
                    if n not in nomes_zip or z.getinfo(n).file_size > 2_000_000:
                        continue
                    im = Image.open(io.BytesIO(z.read(n)))
                    im.load()
                    if max(im.size) > 256:
                        continue
                    im = im.convert("RGB")
                    hs = hashlib.sha1(im.tobytes()).hexdigest()
                    if hs in ja:
                        continue
                    fname = f"buff_{time.time_ns()}.png"
                    im.save(pasta / fname)          # salva de novo: só a imagem, nada mais
                    alvo["variantes"].append(fname)
                    ja.add(hs)
                    versoes += 1
        return novos, versoes

    def importar_pacotes_da_pasta(self):
        """Importa sozinho os pacotes buffs*.zip deixados na pasta do programa.
        Cada pacote entra uma vez em cada perfil (se o arquivo mudar, entra de novo)."""
        feitos = self.perfil.setdefault("pacotes_importados", [])
        n_antes = len(feitos)
        resumo = []
        for pasta in PASTAS_PACOTES:
            try:
                arquivos = sorted(pasta.glob("buffs*.zip"))
            except Exception:
                continue
            for arq in arquivos:
                try:
                    marca = hashlib.sha1(arq.read_bytes()).hexdigest()
                except Exception:
                    continue
                if marca in feitos:
                    continue
                try:
                    novos, versoes = self._importar_pacote(arq)
                except Exception:
                    registrar(f"Pacote {arq.name} ignorado:\n" + traceback.format_exc())
                    feitos.append(marca)          # não fica tentando um arquivo inválido
                    continue
                feitos.append(marca)
                registrar(f"Pacote {arq.name} importado no perfil {self.nome}: "
                          f"{novos} buff(s), {versoes} ícone(s).")
                resumo.append(f"{arq.name} ({novos} buff(s), {versoes} ícone(s))")
        if resumo:
            self._depois_de_importar()
            self.status("Pacote de buffs importado automaticamente: " + ", ".join(resumo) + ".")
        elif len(feitos) != n_antes:
            self.salvar_depois()                  # lembra dos pacotes inválidos já vistos
        return resumo

    def _on_duracao(self, bf, var, entry):
        v, ok = ler_tempo(var.get())
        try:
            entry.state(["!invalid"] if ok else ["invalid"])
        except tk.TclError:
            pass
        if ok:
            bf["duracao"] = v
            self.salvar_depois()

    def adicionar_buff(self):
        nome = simpledialog.askstring("Adicionar buff", "Nome do buff (ex.: Brisa Leve):",
                                      parent=self.win)
        if not nome or not nome.strip():
            return
        self._novo_buff(nome.strip(), capturar=True)

    def mover_buff(self, k, d):
        """Muda a posição do buff na lista (e no overlay)."""
        buffs = self.perfil.get("buffs", [])
        j = k + d
        if 0 <= j < len(buffs):
            buffs[k], buffs[j] = buffs[j], buffs[k]
            self.montar_buffs()
            self.overlay.preview()
            self.salvar_depois()

    def remover_buff(self, k):
        bf = self.perfil["buffs"][k]
        if not messagebox.askyesno("Remover", f"Remover o buff \"{bf.get('nome')}\"?",
                                   parent=self.win):
            return
        for arq in bf.get("variantes", []):
            (Perfis.pasta(self.nome) / arq).unlink(missing_ok=True)
        self.perfil["buffs"].pop(k)
        self.salvar_agora()
        self.overlay.carregar_perfil(self.perfil, Perfis.pasta(self.nome))
        self.montar_buffs()

    def _capturar_com_contagem(self, aviso_txt, texto_seletor, ao_terminar):
        """Contagem de 5 s, congela a tela e deixa marcar retângulos."""
        estava = self.overlay.ativo
        if self.overlay.mover:
            self.alternar_mover()
        self.win.withdraw()
        aviso = tk.Toplevel(self.root)
        aviso.overrideredirect(True)
        aviso.attributes("-topmost", True)
        lbl = tk.Label(aviso, font=("Segoe UI", 14, "bold"), bg="#111111", fg="#ffffff",
                       padx=24, pady=14, justify="center")
        lbl.pack()
        aviso.geometry(f"+{aviso.winfo_screenwidth() // 2 - 300}+40")

        def fim(regioes, tela, mon):
            try:
                ao_terminar(regioes, tela, mon)
            finally:
                self.win.deiconify()
                self.win.lift()
                if estava and not self.overlay.ativo:
                    self.iniciar()

        def contar(n):
            if n > 0:
                lbl.config(text=f"{aviso_txt}\nCapturando a tela em {n}...")
                aviso.after(1000, contar, n - 1)
                return
            aviso.destroy()

            def capturar():
                with nova_captura() as sct:
                    mon = dict(sct.monitors[1])
                    shot = sct.grab(mon)
                tela = Image.frombytes("RGB", shot.size, shot.rgb)
                Seletor(self.root, tela, mon, lambda regs: fim(regs, tela, mon), texto=texto_seletor)
            self.root.after(250, capturar)
        contar(5)

    def capturar_variante(self, bf):
        def pronto(regioes, tela, mon):
            if not regioes:
                return
            pasta = Perfis.pasta(self.nome)
            stamp = time.time_ns()   # nome único, mesmo com duas capturas no mesmo segundo
            for i, (x, y, w, h) in enumerate(regioes, 1):
                arq = f"buff_{stamp}_{i}.png"
                tela.crop((x, y, x + w, y + h)).save(pasta / arq)
                bf.setdefault("variantes", []).append(arq)
            self.salvar_agora()
            self.overlay.carregar_perfil(self.perfil, Perfis.pasta(self.nome))
            self.montar_buffs()
            self.status(f"{bf.get('nome')}: {len(bf['variantes'])} versão(ões) de ícone.")
        self._capturar_com_contagem(
            f"Deixe o buff \"{bf.get('nome')}\" ATIVO no jogo",
            "Arraste um quadrado sobre o ícone do buff (coluna de buffs, à direita)", pronto)

    def _on_ap(self):
        if self._carregando:
            return
        self.perfil["layout"]["mostrar_ap"] = bool(self.var_ap.get())
        self.salvar_depois()
        if self.var_ap.get() and not self.overlay.ativo and self.overlay.tem_algo():
            self.iniciar()
        self.overlay.preparar_imagens()
        self.overlay.relayout()
        self.overlay.preview(3)

    def _on_ap_altura(self, val):
        v = int(round(float(val)))
        self.lbl_ap_alt.config(text=f"{v} px")
        if self._carregando:
            return
        self.perfil["layout"]["ap_altura"] = v
        self.overlay.relayout()
        self.overlay.preview(2)
        self.salvar_depois()

    def _escolher_cor_ap(self):
        from tkinter import colorchooser
        atual = self.perfil["layout"].get("ap_cor") or "#3b82f6"
        _, cor = colorchooser.askcolor(color=atual, title="Cor da barra de AP", parent=self.win)
        if not cor:
            return
        self.perfil["layout"]["ap_cor"] = cor
        self.amostra_ap.config(bg=cor)
        self.overlay.preview(3)
        self.salvar_depois()

    def diagnostico_ap(self):
        """Salva o que o programa está vendo do AP, para mandar a quem dá suporte."""
        ov = self.overlay
        try:
            pasta = PASTA / "diagnostico_ap"
            pasta.mkdir(exist_ok=True)
            carimbo = time.strftime("%Y%m%d_%H%M%S")
            regiao = None
            if ov.geo:
                gx, gy, gw, gh = ov.geo
                regiao = {"left": gx, "top": gy, "width": gw, "height": gh}
            with nova_captura() as sct:
                shot = sct.grab(regiao or dict(sct.monitors[1]))
            arr = np.asarray(Image.frombytes("RGB", shot.size, shot.rgb))
            Image.fromarray(arr).save(pasta / f"tela_{carimbo}.png")
            trecho = getattr(ov, "_ap_ultimo_trecho", None)
            if trecho is not None:
                Image.fromarray(trecho).save(pasta / f"trecho_{carimbo}.png")
            rotulos = achar_rotulos_ap(arr)
            loc, lido = localizar_ap(arr)
            texto = (f"versão {VERSAO}\njogo (geo): {ov.geo}\nrótulo guardado: "
                     f"{getattr(ov, '_ap_rotulo', None)}\nárea manual: {self.perfil.get('area_ap')}\n"
                     f"rótulos 'AP' achados agora: {rotulos}\nleitura agora: {loc} -> {lido}\n"
                     f"última leitura aceita: {getattr(ov, 'ap', None)}\n")
            (pasta / f"info_{carimbo}.txt").write_text(texto, encoding="utf-8")
            registrar("Diagnóstico do AP:\n" + texto)
            self.status(f"Diagnóstico salvo em {pasta.name}. Leitura agora: "
                        f"{f'{lido[0]} / {lido[1]}' if lido else 'nenhuma'}.")
            os.startfile(pasta)
        except Exception as e:
            registrar("Erro no diagnóstico do AP:\n" + traceback.format_exc())
            self.status(f"Não consegui salvar o diagnóstico: {e}")

    def _ap_manual_ou_auto(self):
        if self.perfil.get("area_ap"):
            self.perfil["area_ap"] = None              # volta a procurar sozinho
            self.bt_ap_manual.config(text="Marcar à mão")
            self.salvar_depois()
            self.status("AP: voltei a procurar a janela Informações básicas sozinho.")
        else:
            self.marcar_ap()

    def marcar_ap(self):
        def pronto(regioes, tela, mon):
            if not regioes:
                return
            x0 = min(r[0] for r in regioes)
            y0 = min(r[1] for r in regioes)
            x1 = max(r[0] + r[2] for r in regioes)
            y1 = max(r[1] + r[3] for r in regioes)
            lido = ler_fracao(np.asarray(tela.crop((x0, y0, x1, y1)))) if np is not None else None
            self.perfil["area_ap"] = {"x": x0 + mon["left"], "y": y0 + mon["top"],
                                      "w": x1 - x0, "h": y1 - y0,
                                      "origem": self.overlay.origem_agora()}
            self.perfil["layout"]["mostrar_ap"] = True
            self.var_ap.set(True)
            self.bt_ap_manual.config(text="Voltar ao automático")
            self.salvar_agora()
            self.overlay.relayout()
            self.overlay.preview(3)
            if lido:
                self.overlay.ap, self.overlay.ap_t = lido, time.monotonic()
                self.status(f"AP marcado: li {lido[0]} / {lido[1]} ✓")
            else:
                self.status("Marquei a área, mas não consegui ler os números do AP. "
                            "Marque de novo, só em volta de \"53 / 200\".")
        self._capturar_com_contagem(
            "Deixe a janela Informações básicas aberta no jogo",
            "Arraste um retângulo em volta dos números do AP (ex.: 53 / 200)", pronto)

    def marcar_area_buffs(self):
        def pronto(regioes, tela, mon):
            if not regioes:
                return
            x0 = min(r[0] for r in regioes)
            y0 = min(r[1] for r in regioes)
            x1 = max(r[0] + r[2] for r in regioes)
            y1 = max(r[1] + r[3] for r in regioes)
            self.perfil["area_buffs"] = {"x": x0 + mon["left"], "y": y0 + mon["top"],
                                         "w": x1 - x0, "h": y1 - y0,
                                         "origem": self.overlay.origem_agora()}
            self.salvar_agora()
            self.montar_buffs()
            self.status("Área dos buffs marcada.")
        self._capturar_com_contagem(
            "Mostre o jogo com seus buffs na tela",
            "Arraste um retângulo cobrindo TODA a área onde os ícones de buff aparecem", pronto)

    # ---- lista de skills

    def montar_lista(self):
        for wdg in self.lista.winfo_children():
            wdg.destroy()
        for col, t in enumerate(("", "Nome", "", "Recarga (s)", "Aprendido", "Estado", "")):
            ttk.Label(self.lista, text=t, style="Titulo.TLabel").grid(
                row=0, column=col, padx=4, sticky="w")
        skills = self.perfil["skills"]
        if not skills:
            ttk.Label(self.lista, justify="left", text=(
                "Primeiros passos:\n"
                "  1. Abra o Ragnarok em modo janela (ou janela sem bordas).\n"
                "  2. Clique em \"Marcar ícones na tela\" e arraste um quadrado sobre cada skill\n"
                "      da sua barra de atalhos (com as skills prontas, sem delay).\n"
                "  3. Clique em \"Buscar\" em cada linha para escolher o nome da skill.\n"
                "  4. Clique em \"Iniciar overlay\" e jogue!")
                      ).grid(row=1, column=0, columnspan=7, pady=12, padx=6, sticky="w")
            return
        for i, sk in enumerate(skills):
            r = i + 1
            sk["_thumb"] = ImageTk.PhotoImage(sk["_ref_full"].resize((28, 28), Image.NEAREST))
            ttk.Label(self.lista, image=sk["_thumb"]).grid(row=r, column=0, padx=4, pady=2)

            vn = tk.StringVar(value=sk.get("nome") or "")
            ttk.Entry(self.lista, textvariable=vn, width=22).grid(row=r, column=1, padx=(4, 0))
            vn.trace_add("write", lambda *_, s=sk, v=vn: self._on_nome(s, v))
            self.dica(self.bt(self.lista, "Buscar", "lupa", lambda s=sk: SeletorSkill(self, s)),
                      "Escolher o nome desta skill no banco (a recarga vem junto)."
                      ).grid(row=r, column=2, padx=(4, 4))

            vc = tk.StringVar(value=fmt_tempo(sk.get("cd")))
            ec = ttk.Entry(self.lista, textvariable=vc, width=7, justify="center")
            ec.grid(row=r, column=3, padx=4)
            vc.trace_add("write", lambda *_, s=sk, v=vc, e=ec: self._on_cd(s, v, e))
            sk["_vars"] = (vn, vc)

            sk["_lbl_apr"] = ttk.Label(self.lista, text=fmt_aprendido(sk), width=10)
            sk["_lbl_apr"].grid(row=r, column=4, padx=4)
            sk["_lbl_est"] = ttk.Label(self.lista, text="—", width=14)
            sk["_lbl_est"].grid(row=r, column=5, padx=4)

            fb = ttk.Frame(self.lista)
            fb.grid(row=r, column=6, padx=4)
            self.bt(fb, "", "cima", lambda k=i: self.mover_skill(k, -1)).pack(side="left")
            self.bt(fb, "", "baixo", lambda k=i: self.mover_skill(k, 1)).pack(side="left", padx=2)
            self.bt(fb, "", "lixeira", lambda k=i: self.remover_skill(k)).pack(side="left", padx=(6, 0))

    def _on_nome(self, sk, var):
        sk["nome"] = var.get()
        # Nome digitado igual a uma skill do banco e recarga vazia: preenche sozinho
        if not self._preenchendo and sk.get("cd") is None:
            cd, _ = self.banco.recarga(sk["nome"])
            if cd:
                self._preencher_cd(sk, cd)
        self.salvar_depois()

    def _on_cd(self, sk, var, entry):
        v, ok = ler_tempo(var.get())
        try:
            entry.state(["!invalid"] if ok else ["invalid"])
        except tk.TclError:
            pass
        if ok:
            sk["cd"] = v
            if not self._preenchendo:
                self.banco.salvar_meu(sk.get("nome", ""), v)   # lembra para outros perfis
            self.salvar_depois()

    def _preencher_cd(self, sk, cd):
        self._preenchendo = True
        try:
            sk["_vars"][1].set(fmt_tempo(cd))
        finally:
            self._preenchendo = False

    def aplicar_skill(self, sk, nome):
        """Chamado pela janela de busca."""
        self._preenchendo = True
        try:
            sk["_vars"][0].set(nome)
        finally:
            self._preenchendo = False
        sk["id"] = self.banco.id_de(nome)
        cd, _ = self.banco.recarga(nome)
        if cd:
            self._preencher_cd(sk, cd)
        if sk["id"] and self.dp.ativo():
            self.dp.pedir(sk["id"], "cd")
        self.status(f"{nome}: recarga {fmt_tempo(cd) + ' s' if cd else 'não cadastrada (vai aprender sozinho)'}.")

    def adicionar_por_nome(self, nome):
        """Nova skill sem marcar: o ícone vem da Divine Pride e o programa acha na tela."""
        sid = self.banco.id_de(nome)
        cd, _ = self.banco.recarga(nome)
        self.perfil["skills"].append({"nome": nome, "id": sid, "x": None, "y": None,
                                      "w": 24, "h": 24, "icone": None, "cd": cd,
                                      "aprendido": None})
        self.salvar_agora()
        self.overlay.carregar_perfil(self.perfil, Perfis.pasta(self.nome))
        self.montar_lista()
        if not sid:
            self.status(f"{nome}: sem código da skill; use \"Marcar ícones na tela\" para ela.")
        elif self.icone_skill(sid):
            self._procurar_skill_nova()
            self.status(f"{nome} adicionada. Procurando na tela…")
        elif self.rag.disponivel():
            self.rag.pedir("skill", sid, "buscar")
            if self.dp.ativo():
                self.dp.pedir(sid, "cd")                     # recarga LATAM continua vindo da DP
            self.status(f"{nome} adicionada. Baixando ícone e procurando na tela…")
        elif self.dp.ativo():
            self.dp.pedir(sid, "buscar")
            self.status(f"{nome} adicionada. Baixando ícone e procurando na tela…")
        else:
            self.status(f"{nome} adicionada, mas não consegui baixar o ícone agora. "
                        "Use \"Adicionar mais\" para marcá-la na tela.")

    def atualizar_icones_buffs(self):
        """Buffs criados "pelo nome" antes do ragassets: as versões ainda não confirmadas na
        tela (vindas da Divine Pride) são trocadas pelos ícones do cliente LATAM."""
        if not self.rag.ligado:
            return
        for bf in self.perfil.get("buffs", []):
            if not bf.get("efst") or not any(v.startswith("buff_site_")
                                             for v in bf.get("variantes", [])):
                continue
            faltam = [(k, e) for k, e in bf["efst"] if not self.rag.icone_status(e)]
            if not faltam:
                self._trocar_icones_site(bf)
            elif self.rag.disponivel():
                for k, e in faltam:
                    self.rag.pedir("status", e, ("refresh", id(bf), k))

    def _trocar_icones_site(self, bf):
        pasta = Perfis.pasta(self.nome)
        trocou = 0
        for v in bf.get("variantes", []):
            if not v.startswith("buff_site_"):
                continue
            try:
                i = int(v.rsplit("_", 1)[1].split(".")[0])
                eid = bf["efst"][i][1]
            except (ValueError, IndexError, KeyError):
                continue
            p = self.rag.icone_status(eid)
            if not p or not (pasta / v).exists():
                continue
            antigo = Image.open(pasta / v).convert("RGB")
            novo = icone_dp_rgb(p).resize(antigo.size, Image.NEAREST)
            if novo.tobytes() == antigo.tobytes():
                continue                                   # já é o ícone do ragassets
            novo.save(pasta / v)
            trocou += 1
        if trocou:
            registrar(f"{bf.get('nome')}: {trocou} ícone(s) trocados pelos do ragassets.")
            self.overlay.carregar_perfil(self.perfil, pasta)
            self.montar_buffs()

    def _procurar_skill_nova(self):
        self.overlay.carregar_perfil(self.perfil, Perfis.pasta(self.nome))
        self.montar_lista()
        if not self.overlay.ativo:
            self.iniciar()
        self.overlay.procurar_todos()
        self.overlay.busca_manual = True

    def _processar_rag(self):
        """Respostas do ragassets. Se falhar, pede a mesma coisa à Divine Pride (fallback)."""
        while True:
            try:
                item = self.rag.fila.get_nowait()
            except queue.Empty:
                break
            tipo_r, tipo, ident, motivo = item[:4]
            if tipo == "nomes":
                if tipo_r == "ok":
                    self.atualizar_icones_buffs()
                    n = self.banco.aplicar_nomes(self.rag.nomes)
                    if n:
                        self._nomes_recebidos += n
                        self.status(f"Nomes em português do cliente LATAM: {n} skill(s) atualizadas.")
                else:
                    self.pedir_nomes(self.var_classe.get())   # fallback: Divine Pride
                continue
            if tipo == "status" and isinstance(motivo, tuple):
                bf = next((b for b in self.perfil.get("buffs", []) if id(b) == motivo[1]), None)
                if bf is not None:
                    bf.get("_rag_pend", set()).discard(ident)
                if tipo_r == "ok":
                    if not self.rag.nomes and not getattr(self, "_rag_nomes_pedidos", False):
                        self._rag_nomes_pedidos = True       # voltou a responder: pega nomes/recargas
                        self.rag.pedir("nomes", None, "nomes")
                    if bf is not None and motivo[0] == "refresh":
                        if all(self.rag.icone_status(e) for _, e in bf["efst"]):
                            self._trocar_icones_site(bf)
                    elif bf is not None:
                        self.montar_buffs()
                elif self.icone_buff(ident):
                    pass                                   # já tem o da Divine Pride guardado
                elif self.dp.ativo():
                    self.dp.pedir_efst(ident, motivo[2], ("buff", motivo[1]))
                else:
                    self.status("Não consegui baixar um ícone do buff (ragassets fora e sem chave "
                                "da Divine Pride). Use \"Marcar na tela\" para este buff.")
                continue
            if tipo == "skill":
                if tipo_r == "ok":
                    self._procurar_skill_nova()
                elif self.dp.ativo():
                    self.dp.pedir(ident, "buscar")
                else:
                    self.status("Não consegui baixar o ícone da skill agora. Use "
                                "\"Adicionar mais\" para marcá-la na tela.")
        if hasattr(self, "lbl_rag"):
            self.lbl_rag.config(text=("desligado" if not self.rag.ligado else self.rag.estado))

    def ajuda_dp(self):
        messagebox.showinfo(
            "Chave da API da Divine Pride",
            "1. Crie uma conta grátis em divine-pride.net (botão Register, no topo).\n"
            "2. Entre na conta (Login).\n"
            "3. Abra seu perfil: divine-pride.net/account/profile\n"
            "4. Copie o campo \"API Key\" (se houver um botão para gerar, clique nele antes).\n"
            "5. Cole aqui no campo \"Chave da API\" e clique em \"Salvar e testar\".\n\n"
            "A chave é pessoal: não compartilhe a sua.\n\n"
            "Ao clicar em OK, a página do seu perfil abre no navegador.",
            parent=self.win)
        import webbrowser
        webbrowser.open("https://www.divine-pride.net/account/profile")

    # ---- atualizações

    def _on_auto_at(self):
        self.app_cfg["verificar_atualizacoes"] = bool(self.var_auto_at.get())
        gravar_json(ARQ_APP, self.app_cfg)

    def verificar_atualizacao(self, manual):
        """Consulta o GitHub em segundo plano; se houver versão nova, pergunta se quer instalar."""
        if getattr(self, "_verificando", False):
            return
        self._verificando = True
        if manual:
            self.lbl_at.config(text="Procurando versão nova…")
        fila = queue.Queue()

        def trabalho():
            try:
                fila.put(("ok", buscar_versao_nova()))
            except Exception as e:
                fila.put(("erro", str(e)))
        threading.Thread(target=trabalho, daemon=True).start()

        def esperar():
            try:
                tipo, info = fila.get_nowait()
            except queue.Empty:
                self.win.after(200, esperar)
                return
            self._verificando = False
            self.app_cfg["ultima_verificacao"] = time.time()
            gravar_json(ARQ_APP, self.app_cfg)
            if tipo == "erro":
                registrar(f"Atualização: não consegui consultar ({info})")
                self.lbl_at.config(text=f"Não consegui verificar agora: {info}")
                return
            if info is None:
                self.lbl_at.config(text=f"Você já está na versão mais nova (v{VERSAO}).")
                return
            self.lbl_at.config(text=f"Versão nova disponível: {info['tag']}")
            if not manual and info["tag"] == self.app_cfg.get("pular_versao"):
                return
            self._oferecer_atualizacao(info)
        esperar()

    def _oferecer_atualizacao(self, info):
        top = tk.Toplevel(self.win)
        top.title("Atualização disponível")
        top.configure(bg=self.cor_fundo)
        top.transient(self.win)
        top.resizable(False, False)
        f = ttk.Frame(top)
        f.pack(fill="both", expand=True, padx=16, pady=14)
        ttk.Label(f, text=f"Versão nova: {info['tag']}   (você tem a v{VERSAO})",
                  style="Titulo.TLabel").pack(anchor="w")
        notas = info["notas"] or "Sem descrição."
        if len(notas) > 900:
            notas = notas[:900].rstrip() + "…"
        ttk.Label(f, text=notas, wraplength=460, justify="left").pack(anchor="w", pady=(8, 10))
        ttk.Label(f, style="Dica.TLabel", wraplength=460, justify="left",
                  text="O programa baixa a versão nova, fecha e abre de novo sozinho. "
                       "Seus perfis, buffs e configurações continuam como estão.").pack(anchor="w")
        lb = ttk.Frame(f)
        lb.pack(fill="x", pady=(12, 0))

        def pular():
            self.app_cfg["pular_versao"] = info["tag"]
            gravar_json(ARQ_APP, self.app_cfg)
            top.destroy()

        def atualizar():
            top.destroy()
            self._instalar_atualizacao(info)
        self.bt(lb, "Atualizar agora", "check", atualizar, amarelo=True).pack(side="left")
        self.bt(lb, "Depois", "fechar", top.destroy).pack(side="left", padx=6)
        self.bt(lb, "Pular esta versão", "lixeira", pular).pack(side="right")
        top.update_idletasks()
        x = self.win.winfo_rootx() + (self.win.winfo_width() - top.winfo_width()) // 2
        y = self.win.winfo_rooty() + 80
        top.geometry(f"+{max(0, x)}+{max(0, y)}")
        top.lift()

    def _instalar_atualizacao(self, info):
        fila = queue.Queue()
        self.lbl_at.config(text="Baixando a atualização… 0%")
        self.status(f"Baixando a versão {info['tag']}…")

        def trabalho():
            try:
                tmp, origem = preparar_atualizacao(
                    info, progresso=lambda f: fila.put(("prog", f)))
                fila.put(("pronto", (tmp, origem)))
            except Exception as e:
                fila.put(("erro", str(e)))
        threading.Thread(target=trabalho, daemon=True).start()

        def esperar():
            try:
                while True:
                    tipo, dado = fila.get_nowait()
                    if tipo == "prog":
                        self.lbl_at.config(text=f"Baixando a atualização… {int(dado * 100)}%")
                        continue
                    if tipo == "erro":
                        registrar(f"Atualização falhou: {dado}")
                        self.lbl_at.config(text=f"A atualização falhou: {dado}")
                        messagebox.showerror(
                            "Atualização", f"Não consegui atualizar: {dado}\n\nVocê pode baixar a "
                            f"versão nova à mão em:\n{info['pagina']}", parent=self.win)
                        return
                    tmp, origem = dado
                    self.lbl_at.config(text="Instalando e reiniciando…")
                    self.salvar_agora()
                    gravar_json(ARQ_APP, self.app_cfg)
                    registrar(f"Atualizando de v{VERSAO} para {info['tag']}.")
                    aplicar_atualizacao(tmp, origem)
                    self.root.after(300, self.sair)
                    return
            except queue.Empty:
                self.win.after(150, esperar)
        esperar()

    def _on_rag(self):
        self.rag.ligado = bool(self.var_rag.get())
        self.app_cfg["usar_ragassets"] = self.rag.ligado
        gravar_json(ARQ_APP, self.app_cfg)
        if self.rag.ligado:
            self.rag._fora_ate = 0.0
            self.rag.pedir("nomes", None, "nomes")

    def atualizar_aba_avancado(self):
        """Aba Avançado em vermelho enquanto a chave da Divine Pride não estiver configurada."""
        if not hasattr(self, "aba_av"):
            return
        if self.dp.ativo():
            self.abas.tab(self.aba_av, text=" Avançado", image=self.ic["chave"], compound="left")
            return
        if not hasattr(self, "_aba_av_vermelha"):
            self._aba_av_vermelha = ImageTk.PhotoImage(self._rotulo_aba(" Avançado", "chave",
                                                                         "#ff4d4d"))
        self.abas.tab(self.aba_av, text="", image=self._aba_av_vermelha, compound="image")

    def _rotulo_aba(self, texto, icone, cor):
        """Desenha ícone + texto de uma aba numa imagem (para poder mudar a cor de uma aba só)."""
        import tkinter.font as tkfont
        try:
            f = tkfont.Font(root=self.root, family="Segoe UI", size=10, weight="bold")
            px = max(10, int(f.metrics("linespace") * 0.8))
        except tk.TclError:
            px = 13
        from PIL import ImageFont
        fonte = None
        pasta_fontes = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
        for nome in ("segoeuib.ttf", "arialbd.ttf", str(pasta_fontes / "segoeuib.ttf"),
                     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
            try:
                fonte = ImageFont.truetype(nome, px)
                break
            except OSError:
                continue
        if fonte is None:
            try:
                fonte = ImageFont.load_default(size=px)
            except TypeError:
                fonte = ImageFont.load_default()
        ic = desenhar_icone(icone, cor, 16)
        caixa = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), texto, font=fonte)
        larg_t, alt_t = caixa[2] - caixa[0], caixa[3] - caixa[1]
        alt = max(ic.height, alt_t + 4)
        im = Image.new("RGBA", (ic.width + 2 + larg_t + 2, alt), (0, 0, 0, 0))
        im.alpha_composite(ic, (0, (alt - ic.height) // 2))
        ImageDraw.Draw(im).text((ic.width + 2 - caixa[0], (alt - alt_t) // 2 - caixa[1]), texto,
                                font=fonte, fill=cor)
        return im

    def testar_dp(self):
        self.dp.chave = self.var_dp.get().strip()
        self.app_cfg["dp_chave"] = self.dp.chave
        gravar_json(ARQ_APP, self.app_cfg)
        self.atualizar_aba_avancado()
        if not self.dp.ativo():
            self.lbl_dp.config(text="Sem chave: usando só o banco local.")
            return
        (PASTA_DP / "skill_28.json").unlink(missing_ok=True)      # força consulta real
        self.dp.pedir(28, "teste")
        self.lbl_dp.config(text="Testando…")

    def _sid(self, sk):
        if not sk.get("id"):
            sk["id"] = self.banco.id_de(sk.get("nome", ""))
        return sk.get("id")

    def _processar_dp(self):
        while True:
            try:
                tipo, sid, info, motivo, nome_site = self.dp.fila.get_nowait()
            except queue.Empty:
                return
            if motivo == "nome":
                if tipo == "ok" and self.banco.definir_nome(sid, nome_site):
                    self._nomes_recebidos += 1
                    if self.dp.pedidos.empty():
                        self.status(f"Nomes em português atualizados ({self._nomes_recebidos}).")
                continue
            if isinstance(motivo, tuple) and motivo[0] == "buff":
                bf = next((b for b in self.perfil.get("buffs", []) if id(b) == motivo[1]), None)
                if tipo == "erro":
                    self.status(f"Divine Pride: {info}. Use \"Marcar na tela\" para este buff.")
                elif bf is not None:
                    self.montar_buffs()
                continue
            if motivo == "teste":
                if tipo == "ok":
                    self.lbl_dp.config(text="Conectado ✓ Buscando recargas das suas skills…")
                    self.pedir_nomes(self.var_classe.get())
                    for sk in self.perfil["skills"]:
                        if self._sid(sk):
                            self.dp.pedir(sk["id"], "cd")
                else:
                    self.lbl_dp.config(text=f"Erro: {info}")
                continue
            if tipo == "erro":
                self.status(f"Divine Pride: {info}")
                continue
            alvo = [sk for sk in self.perfil["skills"] if self._sid(sk) == sid]
            for sk in alvo:
                # só troca se você não tiver posto um valor seu
                padrao = self.banco.recarga_padrao(sk.get("nome", ""))
                meu = self.banco.meus.get(chave(sk.get("nome", "")))
                if info and not meu and sk.get("cd") in (None, padrao) and "_vars" in sk:
                    self._preencher_cd(sk, info)
            if motivo == "buscar" and alvo:
                self.overlay.carregar_perfil(self.perfil, Perfis.pasta(self.nome))
                self.montar_lista()
                if not self.overlay.ativo:
                    self.iniciar()
                self.overlay.procurar_todos()
                self.overlay.busca_manual = True
            if info and alvo:
                self.status(f"{alvo[0].get('nome')}: recarga LATAM (Divine Pride) = {fmt_tempo(info)} s.")

    def _on_classe(self):
        self.perfil["classe"] = self.var_classe.get()
        self.salvar_depois()
        self.pedir_nomes(self.perfil["classe"])

    def pedir_nomes(self, classe):
        """Pede à Divine Pride o nome em português das skills da classe que ainda não têm."""
        if self.rag.nomes:
            self.banco.aplicar_nomes(self.rag.nomes)
        if not self.dp.ativo() or not classe or classe == TODAS:
            return
        faltam = [sid for sid in self.banco.sem_nome_pt(classe) if sid not in self._nomes_pedidos]
        for sid in faltam:
            self._nomes_pedidos.add(sid)
            self.dp.pedir(sid, "nome")
        if faltam:
            self.status(f"Baixando da Divine Pride o nome em português de {len(faltam)} "
                        f"skill(s) de {classe}…")

    def mover_skill(self, k, d):
        skills = self.perfil["skills"]
        j = k + d
        if 0 <= j < len(skills):
            skills[k], skills[j] = skills[j], skills[k]
            self.montar_lista()
            self.overlay.preview()
            self.salvar_depois()

    def remover_skill(self, k):
        sk = self.perfil["skills"][k]
        if not messagebox.askyesno("Remover", f"Remover \"{sk.get('nome')}\"?", parent=self.win):
            return
        if sk.get("icone"):
            (Perfis.pasta(self.nome) / sk["icone"]).unlink(missing_ok=True)
        self.perfil["skills"].pop(k)
        self.overlay.carregar_perfil(self.perfil, Perfis.pasta(self.nome))
        self.montar_lista()
        if not self.perfil["skills"]:
            self.parar()
        self.salvar_agora()

    # ---- marcar ícones

    def _on_capturas(self):
        self.app_cfg["visivel_em_capturas"] = bool(self.var_capturas.get())
        gravar_json(ARQ_APP, self.app_cfg)
        self.overlay.atualizar_captura()

    def tirar_print(self):
        """Contagem de 5 s para você voltar ao jogo e usar uma skill; depois salva um print
        da janela do jogo COM o overlay (para usar de exemplo)."""
        if not self.perfil["skills"]:
            self.status("Marque os ícones primeiro para o print mostrar o overlay.")
            return
        if not self.overlay.ativo:
            self.iniciar()
        if self.overlay.mover:
            self.alternar_mover()
        self.win.withdraw()
        aviso = tk.Toplevel(self.root)
        aviso.overrideredirect(True)
        aviso.attributes("-topmost", True)
        lbl = tk.Label(aviso, font=("Segoe UI", 13, "bold"), bg="#111111", fg="#ffffff",
                       padx=20, pady=10, justify="center")
        lbl.pack()
        aviso.geometry(f"+{aviso.winfo_screenwidth() // 2 - 260}+20")

        def contar(n):
            if n > 0:
                lbl.config(text=f"Volte para o jogo e use uma skill\nPrint em {n}...")
                aviso.after(1000, contar, n - 1)
            else:
                aviso.destroy()
                self.overlay.forcar_visivel = True
                self.overlay.atualizar_captura()
                self.root.after(250, self._capturar_print)
        contar(5)

    def _capturar_print(self):
        try:
            g = self.overlay.geo
            with nova_captura() as sct:
                regiao = ({"left": g[0], "top": g[1], "width": g[2], "height": g[3]} if g
                          else dict(sct.monitors[1]))
                shot = sct.grab(regiao)
            arq = PASTA / f"print_{time.strftime('%Y%m%d_%H%M%S')}.png"
            Image.frombytes("RGB", shot.size, shot.rgb).save(arq)
            self.status(f"Print salvo: {arq.name} (na pasta de dados).")
            registrar(f"Print salvo em {arq}")
            os.startfile(arq)
        except Exception as e:
            registrar("Erro ao tirar print:\n" + traceback.format_exc())
            self.status(f"Não consegui tirar o print: {e}")
        finally:
            self.overlay.forcar_visivel = False
            self.overlay.atualizar_captura()
            self.win.deiconify()

    def marcar_icones(self, substituir):
        if substituir and self.perfil["skills"] and not messagebox.askyesno(
                "Marcar ícones", "Isso substitui os ícones deste perfil. Continuar?",
                parent=self.win):
            return
        self._estava_ativo = self.overlay.ativo
        if self.overlay.mover:
            self.alternar_mover()
        self.overlay.parar()
        self.bt_iniciar.config(text="Iniciar overlay", image=self.ic_dest["play"])
        self.win.withdraw()

        aviso = tk.Toplevel(self.root)
        aviso.overrideredirect(True)
        aviso.attributes("-topmost", True)
        lbl = tk.Label(aviso, font=("Segoe UI", 14, "bold"), bg="#111111", fg="#ffffff",
                       padx=24, pady=14, justify="center")
        lbl.pack()
        aviso.geometry(f"+{aviso.winfo_screenwidth() // 2 - 300}+40")

        def contar(n):
            if n > 0:
                lbl.config(text="Clique no jogo e deixe as skills PRONTAS (sem delay)\n"
                                f"Capturando a tela em {n}...")
                aviso.after(1000, contar, n - 1)
            else:
                aviso.destroy()
                self.root.after(250, lambda: self._capturar(substituir))
        contar(5)

    def _capturar(self, substituir):
        with nova_captura() as sct:
            mon = dict(sct.monitors[1])
            shot = sct.grab(mon)
        tela = Image.frombytes("RGB", shot.size, shot.rgb)
        Seletor(self.root, tela, mon,
                lambda regs: self._fim_selecao(regs, tela, mon, substituir))

    def _fim_selecao(self, regioes, tela, mon, substituir):
        if regioes:
            pasta = Perfis.pasta(self.nome)
            pasta.mkdir(parents=True, exist_ok=True)
            skills = self.perfil["skills"]
            if substituir:
                for sk in skills:
                    if sk.get("icone"):
                        (pasta / sk["icone"]).unlink(missing_ok=True)
                skills.clear()
            origem = self.overlay.origem_agora()
            ref = self.perfil.get("origem_calibracao")
            if not skills or ref is None or origem is None:
                self.perfil["origem_calibracao"] = origem
                ox = oy = 0
            else:   # converte para o mesmo referencial dos ícones já marcados
                ox, oy = origem[0] - ref[0], origem[1] - ref[1]
            stamp = time.time_ns()   # nome único, mesmo com duas capturas no mesmo segundo
            for i, (x, y, w, h) in enumerate(regioes, 1):
                arq = f"icone_{stamp}_{i}.png"
                tela.crop((x, y, x + w, y + h)).save(pasta / arq)
                skills.append({"nome": f"Skill {len(skills) + 1}",
                               "x": x + mon["left"] - ox, "y": y + mon["top"] - oy, "w": w, "h": h,
                               "icone": arq, "cd": None, "aprendido": None})
            self.salvar_agora()
            self.overlay.carregar_perfil(self.perfil, pasta)
            self.montar_lista()
            self.status(f"{len(regioes)} ícone(s) marcado(s). Dê nomes e recargas na lista.")
        self.win.deiconify()
        self.win.lift()
        if self._estava_ativo:
            self.iniciar()

    # ---- perfis

    def trocar_perfil(self, nome):
        if self.perfil is not None and self.nome:
            Perfis.salvar(self.nome, self.perfil)
        self.nome = nome
        self.perfil = Perfis.carregar(nome)
        self.app_cfg["ultimo_perfil"] = nome
        gravar_json(ARQ_APP, self.app_cfg)
        self.cb_perfil["values"] = Perfis.listar()
        self.var_perfil.set(nome)
        self.overlay.carregar_perfil(self.perfil, Perfis.pasta(nome))
        self.sincronizar_aparencia()
        self.sincronizar_deteccao()
        classe = self.perfil.get("classe", TODAS)
        self.var_classe.set(classe if classe in self.banco.classes else TODAS)
        self.pedir_nomes(self.var_classe.get())
        self.atualizar_icones_buffs()
        self.montar_lista()
        self.montar_buffs()
        if self.overlay.ativo and not self.overlay.itens():
            self.parar()
        self.status(f"Perfil \"{nome}\" carregado.")
        try:
            self.importar_pacotes_da_pasta()
        except Exception:
            registrar("Erro ao procurar pacotes de buffs:\n" + traceback.format_exc())

    def _pedir_nome(self, titulo, inicial=""):
        nome = simpledialog.askstring(titulo, "Nome do perfil (ex.: nome do personagem):",
                                      initialvalue=inicial, parent=self.win)
        nome = nome_seguro(nome)
        if not nome:
            return None
        if nome in Perfis.listar():
            messagebox.showerror(titulo, "Já existe um perfil com esse nome.", parent=self.win)
            return None
        return nome

    def novo_perfil(self):
        nome = self._pedir_nome("Novo perfil")
        if nome:
            Perfis.criar(nome)
            self.trocar_perfil(nome)

    def duplicar_perfil(self):
        nome = self._pedir_nome("Duplicar perfil", f"{self.nome} (cópia)")
        if nome:
            self.salvar_agora()
            shutil.copytree(Perfis.pasta(self.nome), Perfis.pasta(nome))
            self.trocar_perfil(nome)

    def renomear_perfil(self):
        nome = self._pedir_nome("Renomear perfil", self.nome)
        if nome:
            self.salvar_agora()
            Perfis.pasta(self.nome).rename(Perfis.pasta(nome))
            self.perfil = None
            self.trocar_perfil(nome)

    def excluir_perfil(self):
        if not messagebox.askyesno("Excluir perfil",
                                   f"Excluir o perfil \"{self.nome}\" e seus ícones?",
                                   parent=self.win):
            return
        shutil.rmtree(Perfis.pasta(self.nome), ignore_errors=True)
        self.perfil = None
        self.nome = None
        if not Perfis.listar():
            Perfis.criar("Meu perfil")
        self.trocar_perfil(Perfis.listar()[0])

    # ---- aparência / detecção

    def sincronizar_aparencia(self):
        self._carregando = True
        L = self.perfil["layout"]
        self.var_tam.set(L["tamanho"])
        self.var_esp.set(L["espaco"])
        self.lbl_tam.config(text=f"{L['tamanho']} px")
        self.lbl_esp.config(text=f"{L['espaco']} px")
        self.var_ori.set(L["orientacao"])
        self.var_esconder.set(bool(L["esconder_quando_pronto"]))
        self.var_sem_foco.set(bool(L["esconder_sem_foco"]))
        inv = {v: k for k, v in ESTILOS.items()}
        self.var_estilo.set(inv.get(L.get("estilo", "moderno"), "Moderno"))
        self.var_painel.set(bool(L.get("fundo_painel")))
        self.var_nomes.set(bool(L.get("mostrar_nomes")))
        self.var_ap.set(bool(L.get("mostrar_ap")))
        alt = int(L.get("ap_altura") or 0)
        self.var_ap_alt.set(alt or max(14, int(L["tamanho"] * 0.3)))
        self.lbl_ap_alt.config(text=f"{alt} px" if alt else "auto")
        self.amostra_ap.config(bg=L.get("ap_cor") or "#3b82f6")
        self.bt_ap_manual.config(text="Voltar ao automático" if self.perfil.get("area_ap")
                                 else "Marcar à mão")
        self.root.after_idle(self._fim_carregando)

    def sincronizar_deteccao(self):
        self._carregando = True
        D = self.perfil["deteccao"]
        self.var_min.set(f"{D['min_mostrar']:g}")
        self.var_lim.set(f"{D['limiar_delay']:g}")
        self.var_titulo.set(self.perfil["titulo_janela_jogo"])
        self.root.after_idle(self._fim_carregando)

    def _fim_carregando(self):
        self._carregando = False

    def _on_tam(self, val):
        v = int(round(float(val) / 2) * 2)
        self.lbl_tam.config(text=f"{v} px")
        if self._carregando:
            return
        self.overlay.mudar_tamanho(v)
        self.overlay.preview()

    def _on_esp(self, val):
        v = int(round(float(val)))
        self.lbl_esp.config(text=f"{v} px")
        if self._carregando:
            return
        if v == self.perfil["layout"]["espaco"]:
            return
        self.perfil["layout"]["espaco"] = v
        self.overlay.relayout()
        self.overlay.preview()
        self.salvar_depois()

    def _on_ori(self):
        self.perfil["layout"]["orientacao"] = self.var_ori.get()
        self.overlay.relayout()
        self.overlay.preview()
        self.salvar_depois()

    def _on_estilo(self):
        if self._carregando:
            return
        L = self.perfil["layout"]
        L["estilo"] = ESTILOS.get(self.var_estilo.get(), "moderno")
        L["fundo_painel"] = bool(self.var_painel.get())
        L["mostrar_nomes"] = bool(self.var_nomes.get())
        self.overlay.preparar_imagens()
        self.overlay.relayout()
        self.overlay.preview(3)
        self.salvar_depois()

    def _on_sem_foco(self):
        self.perfil["layout"]["esconder_sem_foco"] = bool(self.var_sem_foco.get())
        self.salvar_depois()

    def _on_esconder(self):
        self.perfil["layout"]["esconder_quando_pronto"] = bool(self.var_esconder.get())
        self.salvar_depois()

    def _on_deteccao(self):
        if self._carregando or not self.perfil:
            return
        D = self.perfil["deteccao"]
        try:
            D["min_mostrar"] = max(0.0, float(self.var_min.get().replace(",", ".")))
        except ValueError:
            pass
        try:
            lim = float(self.var_lim.get().replace(",", "."))
            if 0.01 <= lim <= 1:
                D["limiar_delay"] = lim
                D["limiar_pronto"] = round(lim * 0.3, 3)
        except ValueError:
            pass
        self.perfil["titulo_janela_jogo"] = self.var_titulo.get()
        self.salvar_depois()

    def alternar_mover(self):
        ligar = not self.overlay.mover
        self.overlay.set_mover(ligar)
        self.bt_mover.config(text="Concluir posição" if ligar else "Mover / redimensionar",
                             image=self.ic_dest["check"] if ligar else self.ic["mover"],
                             style=self.estilo_destaque if ligar else self.estilo_padrao)
        if not ligar:
            self.salvar_depois()

    # ---- overlay

    def alternar_overlay(self):
        if self.overlay.ativo:
            self.parar()
        else:
            self.iniciar()

    def procurar_icones(self):
        if not self.overlay.busca_disponivel():
            messagebox.showinfo("Procurar na tela",
                                "Para procurar os ícones sozinho, instale os pacotes:\n\n"
                                "pip install numpy opencv-python\n\n"
                                "(o iniciar.bat já faz isso).", parent=self.win)
            return
        if not self.perfil["skills"]:
            self.status("Marque os ícones primeiro em \"Marcar ícones na tela\".")
            return
        titulo = self.perfil["titulo_janela_jogo"].strip()
        if titulo and self.overlay.origem_agora() is None:
            self.status(f"Não encontrei a janela do jogo (título contendo \"{titulo}\"). "
                        "Abra o jogo, não deixe minimizado e confira o título na aba Avançado.")
            registrar(f"Procurar: janela do jogo não encontrada (título '{titulo}').")
            return
        if not self.overlay.ativo:
            self.iniciar()
        self.overlay.procurar_todos()
        self.overlay.busca_manual = True
        self.status("Procurando os ícones na tela do jogo…")

    def iniciar(self):
        if not self.overlay.tem_algo():
            messagebox.showinfo("RO Cooldown Overlay",
                                'Marque os ícones primeiro em "Marcar ícones na tela" '
                                '(ou adicione um buff na aba Buffs).',
                                parent=self.win)
            return
        if self.overlay.iniciar():
            self.bt_iniciar.config(text="Parar overlay", image=self.ic_dest["stop"])
            self.status("Overlay rodando. Pode minimizar esta janela.")

    def parar(self):
        self.overlay.parar()
        self.bt_iniciar.config(text="Iniciar overlay", image=self.ic_dest["play"])
        self.status("Overlay parado.")

    def _on_auto(self):
        self.app_cfg["iniciar_auto"] = bool(self.var_auto.get())
        gravar_json(ARQ_APP, self.app_cfg)

    def _atualizar_status(self):
        try:
            if hasattr(self, "lbl_ap"):
                ov = self.overlay
                if not self.var_ap.get():
                    t = ""
                elif not ov.ativo:
                    t = "AP: overlay parado"
                elif getattr(ov, "ap", None) and time.monotonic() - getattr(ov, "ap_t", -99) < 3:
                    t = f"AP lido: {ov.ap[0]} / {ov.ap[1]}"
                elif not self.perfil.get("area_ap") and not getattr(ov, "_ap_rotulo", None):
                    t = "procurando a janela Informações básicas…"
                else:
                    t = "AP: não consigo ler"
                self.lbl_ap.config(text=t)
        except tk.TclError:
            pass
        try:
            for bf in self.overlay.buffs:
                le = bf.get("_lbl_est")
                if le is None or not le.winfo_exists():
                    continue
                if not bf.get("_tmpls") and bf.get("efst"):
                    t = ("ative no jogo" if bf.get("_aguardando_tela") else "procurando…") \
                        if all(self.icone_buff(e) for _, e in bf["efst"]) else "baixando…"
                elif not bf.get("_tmpls"):
                    t = "sem ícone"
                elif not self.overlay.ativo:
                    t = "parado"
                elif self.overlay.geo is None and self.overlay.estado_jogo:
                    t = self.overlay.estado_jogo
                else:
                    t = f"{'ATIVO' if bf['_ativo'] else 'inativo'} ({bf['_score']:.2f})"
                    vs = bf.get("variantes", [])
                    if any(v.startswith("buff_site_") for v in vs):
                        reais = sum(not v.startswith("buff_site_") for v in vs)
                        t += f" · {reais}/{len(vs)}"
                le.config(text=t)
        except tk.TclError:
            pass
        try:
            for sk in self.overlay.skills:
                le = sk.get("_lbl_est")
                if le is None or not le.winfo_exists():
                    continue
                if not self.overlay.ativo:
                    t = "parado"
                elif self.overlay.geo is None and self.overlay.estado_jogo:
                    t = self.overlay.estado_jogo
                elif not sk.get("_vis", True):
                    t = "barra coberta"
                elif sk.get("x") is None:
                    t = "procurando na tela…" if "_tmpl" in sk else "sem ícone"
                elif sk.get("_sumiu"):
                    t = "não está na tela"
                elif sk.get("_perdido_desde") is not None:
                    t = "procurando…"
                else:
                    t = f"{'DELAY' if sk['_delay'] else 'pronta'} ({sk['_d']:.2f})"
                    if sk.get("_contando"):
                        t += " ⏱"
                le.config(text=t)
                sk["_lbl_apr"].config(text=fmt_aprendido(sk))
        except tk.TclError:
            pass
        try:
            self._processar_rag()
        except Exception:
            registrar("Erro ao aplicar dados do ragassets:\n" + traceback.format_exc(),
                      chave_rep="rag2")
        try:
            self._processar_dp()
        except Exception:
            registrar("Erro ao aplicar dados da Divine Pride:\n" + traceback.format_exc(),
                      chave_rep="dp")
        self.win.after(250, self._atualizar_status)

    # ---- salvar / sair

    def salvar_depois(self):
        if not self._salvar_agendado:
            self._salvar_agendado = True
            self.win.after(800, self.salvar_agora)

    def salvar_agora(self):
        self._salvar_agendado = False
        if self.perfil is not None and self.nome:
            Perfis.salvar(self.nome, self.perfil)

    def sair(self):
        try:
            self.salvar_agora()
            gravar_json(ARQ_APP, self.app_cfg)
        finally:
            self.root.destroy()


# =============================================================== início

# =============================================================== atualizações

def versao_tupla(v):
    """"v1.0.16" -> (1, 0, 16). Partes não numéricas viram 0."""
    partes = re.findall(r"\d+", str(v or ""))
    return tuple(int(x) for x in partes[:4]) or (0,)


def _http(url, binario=False, timeout=20, progresso=None):
    req = urllib.request.Request(url, headers={
        "User-Agent": f"RO-Cooldown-Overlay/{VERSAO}",
        "Accept": "application/octet-stream" if binario else "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        if not binario:
            return json.loads(r.read().decode("utf-8"))
        total = int(r.headers.get("Content-Length") or 0)
        partes, lido = [], 0
        while True:
            bloco = r.read(256 * 1024)
            if not bloco:
                break
            partes.append(bloco)
            lido += len(bloco)
            if progresso and total:
                progresso(lido / total)
        return b"".join(partes)


def buscar_versao_nova():
    """Consulta o CHANGELOG.md da branch main no GitHub: o primeiro "## vX.Y.Z" é a versão
    mais nova e o texto até o próximo "## " são as novidades. Devolve dict com a versão nova
    ou None se já está na mais nova."""
    if not REPO_GITHUB or "SEU-USUARIO" in REPO_GITHUB:
        raise ValueError("o endereço do repositório ainda não foi configurado no programa")
    req = urllib.request.Request(
        f"https://raw.githubusercontent.com/{REPO_GITHUB}/{BRANCH_GITHUB}/CHANGELOG.md",
        headers={"User-Agent": f"RO-Cooldown-Overlay/{VERSAO}", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=20) as r:
        texto = r.read().decode("utf-8", errors="replace")
    m = re.search(r"^##[ \t]*(v?\d+(?:\.\d+)+)[ \t]*\r?$(.*?)(?=^##\s|\Z)", texto, re.M | re.S)
    if not m:
        raise ValueError("não achei a versão no CHANGELOG.md do GitHub")
    tag = m.group(1)
    if versao_tupla(tag) <= versao_tupla(VERSAO):
        return None
    return {"tag": tag, "notas": m.group(2).strip(),
            "pagina": f"https://github.com/{REPO_GITHUB}",
            "zip_exe": None, "digest": None,
            "zip_fonte": f"https://github.com/{REPO_GITHUB}/archive/refs/heads/{BRANCH_GITHUB}.zip"}


# Arquivos do programa trocados ao atualizar a versão em Python (os seus dados nunca são tocados)
ARQUIVOS_PROGRAMA = ("ro_cooldown_overlay.py", "banco_skills.json", "requirements.txt",
                     "iniciar.bat", "LEIA-ME.txt", "README.md", "CHANGELOG.md", "LICENSE",
                     "RO Cooldown Overlay.exe", "build_exe.bat")
PASTAS_PROGRAMA = ("assets", "lancador")


def _extrair_seguro(zf, destino):
    """Extrai um .zip sem deixar nenhum arquivo sair da pasta de destino."""
    destino = Path(destino).resolve()
    for nome in zf.namelist():
        alvo = (destino / nome).resolve()
        if destino not in alvo.parents and alvo != destino:
            raise ValueError(f"arquivo suspeito no pacote: {nome}")
    zf.extractall(destino)


def preparar_atualizacao(info, progresso=None):
    """Baixa e desempacota a versão nova numa pasta temporária. Devolve a pasta com os arquivos
    novos já no formato da instalação atual (.exe ou Python)."""
    import tempfile
    congelado = getattr(sys, "frozen", False)
    url = info["zip_exe"] if congelado else info["zip_fonte"]
    if not url:
        raise ValueError("a release não tem o arquivo para Windows")
    dados = _http(url, binario=True, timeout=120, progresso=progresso)
    if congelado and info.get("digest", "").startswith("sha256:"):
        if hashlib.sha256(dados).hexdigest() != info["digest"].split(":", 1)[1]:
            raise ValueError("o arquivo baixado não confere (download corrompido)")
    tmp = Path(tempfile.mkdtemp(prefix="ro_cd_atualiza_"))
    with zipfile.ZipFile(io.BytesIO(dados)) as zf:
        _extrair_seguro(zf, tmp / "pacote")
    if congelado:
        # o .zip da release tem a pasta "RO Cooldown Overlay" com o .exe dentro
        exe = next((p for p in (tmp / "pacote").rglob(f"{NOME_APP}.exe")), None)
        if exe is None:
            raise ValueError("não achei o programa dentro do pacote baixado")
        return tmp, exe.parent
    # código-fonte: a pasta de cima do .zip tem o nome do repositório e do commit
    raiz = next((p.parent for p in (tmp / "pacote").rglob("ro_cooldown_overlay.py")), None)
    if raiz is None:
        raise ValueError("não achei o ro_cooldown_overlay.py dentro do pacote baixado")
    return tmp, raiz


def aplicar_atualizacao(tmp, origem):
    """Instala a versão nova e reinicia o programa.
    .exe: um script do PowerShell espera este programa fechar, copia os arquivos e abre o novo.
    Python: troca só os arquivos do programa na pasta e reabre."""
    congelado = getattr(sys, "frozen", False)
    pasta_prog = Path(sys.executable).parent if congelado else Path(__file__).resolve().parent

    def q(caminho):                                   # texto entre aspas no PowerShell
        return "'" + str(caminho).replace("'", "''") + "'"

    if not congelado:
        for nome in ARQUIVOS_PROGRAMA:
            if (origem / nome).is_file():
                shutil.copy2(origem / nome, pasta_prog / nome)
        for nome in PASTAS_PROGRAMA:
            if (origem / nome).is_dir():
                shutil.copytree(origem / nome, pasta_prog / nome, dirs_exist_ok=True)
        lancador = pasta_prog / f"{NOME_APP}.exe"
        if lancador.exists():
            abrir = f"Start-Process -FilePath {q(lancador)}"
        else:
            pyw = Path(sys.executable).with_name("pythonw.exe")
            abrir = (f"Start-Process -FilePath {q(pyw if pyw.exists() else 'pythonw')} "
                     f"-ArgumentList {q(chr(34) + str(pasta_prog / 'ro_cooldown_overlay.py') + chr(34))} "
                     f"-WorkingDirectory {q(pasta_prog)}")
        copiar = ""
    else:
        abrir = f"Start-Process -FilePath {q(pasta_prog / (NOME_APP + '.exe'))}"
        copiar = f"Copy-Item -Path {q(str(origem) + chr(92) + '*')} -Destination {q(pasta_prog)} -Recurse -Force\r\n"
    script = ("$ErrorActionPreference = 'SilentlyContinue'\r\n"
              f"Wait-Process -Id {os.getpid()} -Timeout 60\r\n"
              "Start-Sleep -Milliseconds 500\r\n"
              + copiar + abrir + "\r\n"
              f"Remove-Item -Path {q(tmp)} -Recurse -Force\r\n")
    arq = tmp / "atualizar.ps1"
    arq.write_text(script, encoding="utf-8-sig")       # com BOM: acentos nos caminhos funcionam
    import subprocess
    subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                      "-WindowStyle", "Hidden", "-File", str(arq)],
                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), close_fds=True)


def ja_aberto():
    """Evita abrir dois overlays ao mesmo tempo (duplo clique repetido)."""
    try:
        k32 = ctypes.windll.kernel32
        k32.CreateMutexW.restype = wintypes.HANDLE
        ja_aberto._mutex = k32.CreateMutexW(None, False, "RO_Cooldown_Overlay_instancia")
        return k32.GetLastError() == 183          # ERROR_ALREADY_EXISTS
    except Exception:
        return False


def main():
    if ja_aberto():
        r = tk.Tk()
        r.withdraw()
        messagebox.showinfo(NOME_APP, "O programa já está aberto.\n"
                            "Procure a janela dele na barra de tarefas.")
        return
    dpi_aware()
    try:    # barra de tarefas com o ícone do programa (e não o do Python)
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ROCooldownOverlay.App")
    except Exception:
        pass
    root = tk.Tk()
    registrar(f"{NOME_APP} v{VERSAO} iniciado (dados em {PASTA})")

    def erro(exc, val, tb):
        texto = "".join(traceback.format_exception(exc, val, tb))
        (PASTA / "erro.log").write_text(texto, encoding="utf-8")
        messagebox.showerror(NOME_APP, f"Ocorreu um erro:\n{val}\n\n"
                             "Os detalhes foram salvos em erro.log "
                             "(botão \"Pasta de dados\").")

    root.report_callback_exception = erro
    try:
        Painel(root)
    except Exception:
        (PASTA / "erro.log").write_text(traceback.format_exc(), encoding="utf-8")
        raise
    root.mainloop()


if __name__ == "__main__":
    main()
