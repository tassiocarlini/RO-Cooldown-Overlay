"""Cronômetro do recall: janela própria, sempre por cima do jogo, com botão de reiniciar."""

import re
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
import traceback

from PIL import ImageTk

from .config import ARQ_APP, COR_PAINEL, COR_TRANSPARENTE, CRONOMETRO_PADRAO, registrar
from .janelas import (WDA_EXCLUDEFROMCAPTURE, WS_EX_LAYERED, WS_EX_NOACTIVATE, WS_EX_TOOLWINDOW,
                      hwnd_de, mudar_estilo, user32)
from .desenho import COR, desenhar_icone, ret_arred
from .dados import fmt_contagem, gravar_json


class Cronometro:
    """Contagem regressiva do recall. Fica numa janela só dela (separada das skills e buffs),
    aparece com ou sem o overlay ligado e aceita clique sem tirar o foco do jogo: o botão
    redondo reinicia a contagem, o resto da caixa arrasta e a roda do mouse muda o tamanho."""
    PISCA = 0.5               # s: troca de cor nos últimos segundos
    TAM_MIN, TAM_MAX = 14, 96

    def __init__(self, root, painel):
        self.painel = painel
        cfg = painel.app_cfg.get("cronometro")
        painel.app_cfg["cronometro"] = dict(CRONOMETRO_PADRAO, **(cfg if isinstance(cfg, dict) else {}))
        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.attributes("-transparentcolor", COR_TRANSPARENTE)
        self.win.configure(bg=COR_TRANSPARENTE)
        self.canvas = tk.Canvas(self.win, bg=COR_TRANSPARENTE, highlightthickness=0, bd=0,
                                cursor="fleur")
        self.canvas.pack(fill="both", expand=True)
        self.win.withdraw()

        self.visivel = False
        self.hwnd = None
        self.inicio = None        # time.monotonic() do último reinício (None = nunca iniciado)
        self._avisou = False
        self._acabou = False
        self._arrasto = None
        self._apertou = False
        self._sobre_botao = False
        self._botao = (0, 0, 0, 0)
        self._fontes = None
        self._icones = {}
        self._tam = None
        self._ult_topo = 0.0

        c = self.canvas
        c.bind("<ButtonPress-1>", self._press)
        c.bind("<B1-Motion>", self._drag)
        c.bind("<ButtonRelease-1>", self._release)
        c.bind("<Motion>", self._mouse)
        c.bind("<Leave>", lambda _e: self._mouse(None))
        c.bind("<MouseWheel>", self._roda)
        # sons de voz ("Recall") gravados de antemão: o 1º aviso não atrasa
        threading.Thread(target=painel.overlay.sons.gerar_vozes, daemon=True).start()
        self._loop()

    @property
    def cfg(self):
        return self.painel.app_cfg["cronometro"]

    def salvar(self):
        gravar_json(ARQ_APP, self.painel.app_cfg)

    # ---- contagem

    def restante(self, agora=None):
        total = self.cfg["tempo"]
        if self.inicio is None:
            return total
        return max(0.0, total - ((agora or time.monotonic()) - self.inicio))

    def reiniciar(self):
        self.inicio = time.monotonic()
        self._avisou = self._acabou = False
        self.painel.overlay.sons.preparar([self.cfg.get("som_aviso"), self.cfg.get("som_fim")])

    def tocar(self, qual):
        """qual: "som_aviso" (faltando pouco) ou "som_fim" (chegou a zero)."""
        L = (self.painel.perfil or {}).get("layout", {})
        self.painel.overlay.sons.tocar(self.cfg.get(qual), L.get("som_volume", 70), forcar=True)

    def _loop(self):
        try:
            self._tick()
        except Exception:
            registrar("Erro no cronômetro:\n" + traceback.format_exc(), chave_rep="crono")
        self.win.after(100, self._loop)

    def _tick(self):
        cfg = self.cfg
        if not cfg["ligado"]:
            if self.visivel:
                self.win.withdraw()
                self.visivel = False
            return
        agora = time.monotonic()
        r = self.restante(agora)
        if self.inicio is not None:
            if not self._avisou and 0 < r <= cfg["aviso"] < cfg["tempo"]:
                self._avisou = True
                self.tocar("som_aviso")
            if not self._acabou and r <= 0:
                self._acabou = self._avisou = True
                self.tocar("som_fim")
        self.desenhar(agora, r)
        if not self.visivel:
            self._mostrar()
        elif agora - self._ult_topo > 2:
            self._ult_topo = agora
            self.win.attributes("-topmost", True)

    # ---- janela

    def _mostrar(self):
        self.win.deiconify()
        self.win.update_idletasks()
        self.visivel = True
        self.hwnd = hwnd_de(self.win)
        # aceita clique (sem WS_EX_TRANSPARENT), mas não rouba o foco do jogo
        mudar_estilo(self.hwnd, WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE)
        self.atualizar_captura()

    def atualizar_captura(self):
        """Igual ao overlay: fica fora dos prints (para não atrapalhar a leitura dos ícones),
        a não ser que "Aparecer em prints e lives" esteja ligado."""
        if self.hwnd:
            visivel = self.painel.app_cfg.get("visivel_em_capturas", False)
            user32.SetWindowDisplayAffinity(self.hwnd, 0 if visivel else WDA_EXCLUDEFROMCAPTURE)

    def centralizar(self):
        self.cfg["x"] = self.cfg["y"] = None
        self._tam = None
        self.salvar()

    def _medidas(self):
        T = int(self.cfg["tamanho"])
        if self._fontes is None or self._fontes[0] != T:
            grande = tkfont.Font(root=self.win, family="Segoe UI", size=-T, weight="bold")
            peq = tkfont.Font(root=self.win, family="Segoe UI", size=-max(9, int(T * 0.36)),
                              weight="bold")
            self._fontes = (T, grande, peq)
        return self._fontes

    def _icone(self, tam, cor):
        if (tam, cor) not in self._icones:
            self._icones[(tam, cor)] = ImageTk.PhotoImage(desenhar_icone("reiniciar", cor, tam),
                                                          master=self.win)
        return self._icones[(tam, cor)]

    def desenhar(self, agora, r):
        cfg = self.cfg
        T, grande, peq = self._medidas()
        modelo = re.sub(r"\d", "0", fmt_contagem(cfg["tempo"]))    # largura fixa
        pad = max(6, T // 3)
        alt_num, alt_rot = grande.metrics("linespace"), peq.metrics("linespace")
        bd = int(alt_num * 0.8)                                    # diâmetro do botão
        w = pad + grande.measure(modelo) + pad + bd + pad
        h = pad // 2 + alt_rot + alt_num + pad // 2
        if self._tam != (w, h):
            self._tam = (w, h)
            x, y = cfg["x"], cfg["y"]
            if x is None or y is None:
                x, y = (self.win.winfo_screenwidth() - w) // 2, 60
            self.canvas.config(width=w, height=h)
            self.win.geometry(f"{w}x{h}+{int(x)}+{int(y)}")

        if self.inicio is None:
            cor, rotulo, borda = COR["mudo"], "RECALL", COR["borda2"]
        elif r <= 0:
            cor, rotulo, borda = COR["verde"], "RECALL!", COR["verde"]
        elif r <= cfg["aviso"]:
            cor = COR["vermelho"] if int(agora / self.PISCA) % 2 == 0 else COR["ouro"]
            rotulo, borda = "RECALL", cor
        else:
            cor, rotulo, borda = COR["texto"], "RECALL", COR["borda2"]

        c = self.canvas
        c.delete("all")
        ret_arred(c, 0, 0, w - 1, h - 1, pad, fill="#%02x%02x%02x" % COR_PAINEL, outline=borda)
        c.create_text(pad, pad // 2, text=rotulo, font=peq, fill=COR["mudo"], anchor="nw")
        c.create_text(pad, pad // 2 + alt_rot, text=fmt_contagem(r), font=grande, fill=cor,
                      anchor="nw")
        bx, by = w - pad - bd, (h - bd) // 2
        self._botao = (bx, by, bx + bd, by + bd)
        sobre = self._sobre_botao
        c.create_oval(*self._botao, fill="#343434" if sobre else COR["campo"],
                      outline=COR["ouro"] if sobre else COR["borda2"])
        c.create_image(bx + bd / 2, by + bd / 2,
                       image=self._icone(max(10, int(bd * 0.62)), COR["ouro"] if sobre else COR["texto"]))

    # ---- mouse: botão reinicia, o resto arrasta, roda muda o tamanho

    def _no_botao(self, e):
        x0, y0, x1, y1 = self._botao
        return e is not None and x0 <= e.x <= x1 and y0 <= e.y <= y1

    def _mouse(self, e):
        sobre = self._no_botao(e)
        if sobre != self._sobre_botao:
            self._sobre_botao = sobre
            self.canvas.config(cursor="hand2" if sobre else "fleur")

    def _press(self, e):
        self._apertou = self._no_botao(e)
        self._arrasto = None if self._apertou else (e.x_root - self.win.winfo_x(),
                                                    e.y_root - self.win.winfo_y())

    def _drag(self, e):
        if self._arrasto:
            ax, ay = self._arrasto
            self.win.geometry(f"+{e.x_root - ax}+{e.y_root - ay}")

    def _release(self, e):
        if self._arrasto:
            self._arrasto = None
            self.cfg["x"], self.cfg["y"] = self.win.winfo_x(), self.win.winfo_y()
            self.salvar()
        elif self._apertou and self._no_botao(e):
            self.reiniciar()
        self._apertou = False

    def mudar_tamanho(self, T):
        self.cfg["tamanho"] = max(self.TAM_MIN, min(self.TAM_MAX, int(T)))
        self.salvar()

    def _roda(self, e):
        self.mudar_tamanho(self.cfg["tamanho"] + (2 if e.delta > 0 else -2))
        self.painel.sincronizar_cronometro()
