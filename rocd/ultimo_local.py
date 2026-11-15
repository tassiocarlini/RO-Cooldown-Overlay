"""Último local (Last Spot): um X no mini mapa marcando onde você estava antes de teleportar.

Só olha a tela: acha a sua seta no mini mapa (branca, com um ponto vermelho no meio). Se ela
pula de um lugar para outro de uma vez (Asa de Mosca, teleporte) ou some numa tela preta e volta
em outro mapa, o lugar de antes fica guardado. X verde = você está no mesmo mapa; X vermelho =
você está em outro mapa (o X continua guardado até você voltar ou apagar)."""

import math
import threading
import time
import tkinter as tk
import traceback

from .config import ARQ_APP, COR_TRANSPARENTE, ULTIMO_LOCAL_PADRAO, cv2, np, registrar
from .dados import gravar_json
from .desenho import COR
from .janelas import (WS_EX_LAYERED, WS_EX_NOACTIVATE, WS_EX_TOOLWINDOW, WS_EX_TRANSPARENT, Jogo,
                      hwnd_de, mudar_estilo, nova_captura)
from .visao import tela_escura

SALTO = 4.0             # px no mini mapa de uma leitura para a outra = teleporte (andar é bem menos)
SUMIU_MAX = 4.0         # s sem ver a seta: depois disso, sem tela preta, não conta como teleporte
LIMIAR_MAPA = 0.5       # semelhança mínima do desenho do mini mapa para ser o mesmo mapa
INTERVALO = 0.15        # s entre leituras
SEGURA = 1.5            # s que o X continua na tela depois de a seta sumir (print, piscada)
PERTO = 8               # px: com a seta a essa distância do X (mais meio X), o X some


# =============================================================== leitura do mini mapa

def achar_seta(arr):
    """(x, y) do centro da sua seta no mini mapa, ou None. arr = RGB do numpy.

    A seta é uma manchinha branca (uns 10x10 px) com um ponto vermelho no meio. Ícones e
    textos brancos não têm o ponto vermelho; o ponto vermelho parado (NPC, grupo) não tem
    branco em volta."""
    if cv2 is None or arr is None or arr.size == 0:
        return None
    a = arr[..., :3].astype(np.int16)
    mx, mn = a.max(axis=2), a.min(axis=2)
    branco = ((mn > 170) & (mx - mn < 60)).astype(np.uint8)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    vermelho = (r > 140) & (r - g > 70) & (r - b > 30)
    n, _lab, st, cen = cv2.connectedComponentsWithStats(branco, connectivity=8)
    melhor = None
    for k in range(1, n):
        x, y, w, h, area = (int(v) for v in st[k])
        if not (12 <= area <= 90 and 5 <= w <= 18 and 5 <= h <= 18):
            continue
        y0, y1, x0, x1 = max(0, y - 1), y + h + 1, max(0, x - 1), x + w + 1
        ys, xs = np.nonzero(vermelho[y0:y1, x0:x1])
        if not len(ys):
            continue
        # o ponto vermelho é o centro exato (o meio da mancha branca muda quando a seta gira)
        pos = (float(xs.mean() + x0), float(ys.mean() + y0))
        if melhor is None or area > melhor[0]:
            melhor = (area, pos)
    return melhor[1] if melhor else None


def assinatura(arr):
    """Detalhes do desenho do mini mapa (sem o fundo do jogo que aparece por trás)."""
    g = arr[..., :3].max(axis=2).astype(np.float32)
    return cv2.GaussianBlur(g, (0, 0), 1.2) - cv2.GaussianBlur(g, (0, 0), 5)


def mesmo_mapa(a, b, folga=8):
    """0 a 1: os dois mini mapas são do mesmo mapa? Aceita alguns px de deslocamento."""
    if a is None or b is None or a.shape != b.shape:
        return 0.0
    h, w = b.shape
    if h <= 2 * folga + 8 or w <= 2 * folga + 8:
        return 0.0
    t = b[folga:h - folga, folga:w - folga]
    if float(t.std()) < 1e-3 or float(a.std()) < 1e-3:
        return 0.0
    return float(cv2.matchTemplate(a, t, cv2.TM_CCOEFF_NORMED).max())


class Rastreio:
    """Segue a seta leitura a leitura e guarda o último lugar antes de cada teleporte.
    Sem janela nem tela: dá para testar sozinho."""

    def __init__(self):
        self.ant = None          # (pos, assinatura, quando) da última vez que viu a seta
        self.salvo = None        # (pos, assinatura) do lugar de antes do último teleporte
        self.escuro = False      # teve tela preta desde a última vez que viu a seta

    def ler(self, seta, sig, escuro, agora):
        """Uma leitura. Devolve True se acabou de guardar um lugar novo."""
        if seta is None:
            self.escuro = self.escuro or escuro
            return False
        guardou = False
        if self.ant is not None:
            pos, sig_ant, quando = self.ant
            dist = math.hypot(seta[0] - pos[0], seta[1] - pos[1])
            sumido = agora - quando
            if self.escuro:      # carregou um mapa: pulou de lugar ou trocou de mapa
                pulou = dist >= SALTO or mesmo_mapa(sig, sig_ant) < LIMIAR_MAPA
            else:
                pulou = dist >= SALTO and sumido <= SUMIU_MAX
            if pulou:
                self.salvo = (pos, sig_ant)
                guardou = True
        self.ant = (seta, sig, agora)
        self.escuro = False
        return guardou

    def apagar(self):
        self.salvo = None


# =============================================================== janela do X

class UltimoLocal:
    """Janela transparente por cima do mini mapa, que só desenha o X (o clique atravessa).

    A leitura da tela roda numa linha própria (capturar espera a tela, uns 20 ms): assim ela não
    atrasa o overlay. O X aparece em prints e lives; por isso ele some quando você chega perto
    dele, senão taparia a sua seta e o programa a perderia de vista."""
    CHECAR_MAPA = 0.5    # s entre comparações do desenho do mini mapa (verde/vermelho)
    TAM_MIN, TAM_MAX = 6, 40   # largura do X em pixels

    def __init__(self, root, painel):
        self.painel = painel
        cfg = painel.app_cfg.get("ultimo_local")
        painel.app_cfg["ultimo_local"] = dict(ULTIMO_LOCAL_PADRAO, **(cfg if isinstance(cfg, dict) else {}))
        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.attributes("-transparentcolor", COR_TRANSPARENTE)
        self.win.configure(bg=COR_TRANSPARENTE)
        self.canvas = tk.Canvas(self.win, bg=COR_TRANSPARENTE, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.win.withdraw()
        self.visivel = False
        self.hwnd = None
        self.jogo = Jogo()
        self.rastreio = Rastreio()
        self._pedido = None      # área do mini mapa para a linha de leitura (None = não ler)
        self._leitura = None     # (número, quando, área, seta, assinatura, tela preta)
        self._lida = 0           # número da última leitura já usada
        self._vista = (-99.0, None, None)   # (quando, seta, assinatura) da última vez com seta
        self._desenho = None     # (geometria, x, y, cor) já desenhado
        self._verde = True
        self._ult_mapa = -99.0
        self._ult_topo = 0.0
        threading.Thread(target=self._ler_tela, daemon=True).start()
        self._loop()

    @property
    def cfg(self):
        return self.painel.app_cfg["ultimo_local"]

    def salvar(self):
        gravar_json(ARQ_APP, self.painel.app_cfg)

    def apagar(self):
        self.rastreio.apagar()
        self._esconder()

    def regiao(self, geo):
        """Área do mini mapa na tela (dict do mss), seguindo a janela do jogo se ela andou."""
        a = self.cfg.get("area")
        gx, gy, gw, _gh = geo
        if a:
            o = a.get("origem")
            dx, dy = (gx - o[0], gy - o[1]) if o else (0, 0)
            return {"left": a["x"] + dx, "top": a["y"] + dy, "width": a["w"], "height": a["h"]}
        # sem área marcada: o mini mapa do RO fica no canto de cima, à direita
        return {"left": gx + gw - 152, "top": gy + 4, "width": 148, "height": 148}

    # ---- leitura (linha própria)

    def _ler_tela(self):
        sct, n = None, 0
        while True:
            time.sleep(INTERVALO)
            reg = self._pedido
            if reg is None:
                continue
            try:
                if sct is None:
                    sct = nova_captura()
                shot = sct.grab(reg)
                arr = np.frombuffer(shot.rgb, np.uint8).reshape(shot.height, shot.width, 3)
                seta = achar_seta(arr)
                n += 1
                self._leitura = (n, time.monotonic(), reg, seta,
                                 assinatura(arr) if seta is not None else None, tela_escura(arr))
            except Exception:
                registrar("Erro ao ler o mini mapa:\n" + traceback.format_exc(), chave_rep="ultimo_ler")
                sct = None

    # ---- acompanhar (linha da janela)

    def _loop(self):
        try:
            self._tick()
        except Exception:
            registrar("Erro no último local:\n" + traceback.format_exc(), chave_rep="ultimo_local")
        self.win.after(100, self._loop)

    def _parar(self):
        self._pedido = None
        self._esconder()

    def _tick(self):
        if not self.cfg.get("ligado") or np is None or cv2 is None:
            return self._parar()
        agora = time.monotonic()
        perfil = self.painel.perfil or {}
        titulo = (perfil.get("titulo_janela_jogo") or "").strip()
        if not titulo:
            return self._parar()
        self.jogo.localizar(titulo, agora)
        geo = self.jogo.geometria()
        if not geo:
            return self._parar()
        reg = self.regiao(geo)
        self._pedido = reg
        lei = self._leitura
        if lei is None or lei[2] != reg or agora - lei[1] > 1.0:
            return self._esconder()                 # sem leitura desta área (ou velha demais)
        n, quando, _reg, seta, sig, escuro = lei
        if n != self._lida:
            self._lida = n
            if self.rastreio.ler(seta, sig, escuro, quando):
                p = self.rastreio.salvo[0]
                registrar(f"Último local guardado: ({p[0]:.0f}, {p[1]:.0f}) no mini mapa")
                self._ult_mapa = -99.0
        salvo = self.rastreio.salvo
        # Mostra com o mini mapa à vista (a seta foi achada na tela). Não exige o jogo em foco:
        # a ferramenta de print e o próprio painel tiram o foco, e o X sumia bem na hora do print.
        # Se outra janela cobrir o mini mapa, a seta deixa de ser vista e o X some sozinho.
        if seta is not None:
            self._vista = (agora, seta, sig)
        elif agora - self._vista[0] <= SEGURA:
            seta, sig = self._vista[1], self._vista[2]    # sumiu um instante: segura o X
        if salvo is None or seta is None:
            return self._esconder()
        T = self.tamanho()
        if math.hypot(seta[0] - salvo[0][0], seta[1] - salvo[0][1]) <= T / 2 + PERTO:
            return self._esconder()                 # você está em cima do X: ele taparia a seta
        if agora - self._ult_mapa >= self.CHECAR_MAPA:
            self._ult_mapa = agora
            self._verde = mesmo_mapa(sig, salvo[1]) >= LIMIAR_MAPA
        self._desenhar(reg, salvo[0], COR["verde"] if self._verde else COR["vermelho"], T)
        if agora - self._ult_topo > 2:
            self._ult_topo = agora
            self.win.attributes("-topmost", True)

    def tamanho(self):
        return min(self.TAM_MAX, max(self.TAM_MIN, int(self.cfg.get("tamanho") or 14)))

    # ---- janela

    def _desenhar(self, reg, pos, cor, T):
        geo = (reg["width"], reg["height"], reg["left"], reg["top"])
        chave = (geo, round(pos[0]), round(pos[1]), cor, T)
        if chave != self._desenho:
            self._desenho = chave
            # a janela cobre o mini mapa com folga: X grande perto da borda não é cortado
            folga = T
            self.win.geometry("%dx%d+%d+%d" % (geo[0] + 2 * folga, geo[1] + 2 * folga,
                                               geo[2] - folga, geo[3] - folga))
            c = self.canvas
            c.delete("all")
            x, y = pos[0] + folga, pos[1] + folga
            r = T / 2
            traco = max(2, round(T / 6))
            for larg, tinta in ((traco + 2, "#000000"), (traco, cor)):   # contorno preto: aparece em qualquer fundo
                c.create_line(x - r, y - r, x + r + 1, y + r + 1, fill=tinta, width=larg)
                c.create_line(x - r, y + r, x + r + 1, y - r - 1, fill=tinta, width=larg)
        if not self.visivel:
            self._mostrar()

    def _mostrar(self):
        self.win.deiconify()
        self.win.update_idletasks()
        self.visivel = True
        self.hwnd = hwnd_de(self.win)
        # o clique atravessa e não rouba o foco do jogo
        mudar_estilo(self.hwnd, WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_TRANSPARENT)

    def _esconder(self):
        if self.visivel:
            self.win.withdraw()
            self.visivel = False
            self._desenho = None
