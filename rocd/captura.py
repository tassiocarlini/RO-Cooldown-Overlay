"""CapturaAuto: acha na tela o ícone de uma skill ou buff sozinho."""

import time
import tkinter as tk
import traceback
from tkinter import ttk

from PIL import Image

from .config import LIMIAR_BUFF, cv2, np, registrar
from .janelas import WDA_EXCLUDEFROMCAPTURE, hwnd_de, nova_captura, user32
from .visao import _ncc, mapa_simbolo, mapa_simbolo_suave, modelos_buff, picos, tem_moldura
from .perfis import Perfis


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
