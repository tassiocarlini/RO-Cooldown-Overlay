"""Overlay: lê a tela, controla recargas, buffs e AP, e desenha os ícones."""

import math
import queue
import threading
import time
import tkinter as tk
import traceback

from PIL import Image, ImageEnhance, ImageTk

from .config import (BARRA_H, BUFF_FOLGA_PAUSA, BUFF_TOLERANCIA, COR_PAINEL, COR_TRANSPARENTE, ESCALAS_BUFF,
    ESCALAS_DP, JANELA_GRUPO, LIMIAR_ACHADO, LIMIAR_ACHADO_DP, LIMIAR_BUFF, LIMIAR_BUFF_SITE,
    LIMIAR_OFICIAL, LIMIAR_PERDIDO, cv2, np, registrar)
from .janelas import (WDA_EXCLUDEFROMCAPTURE, WS_EX_LAYERED, WS_EX_NOACTIVATE, WS_EX_TOOLWINDOW,
    WS_EX_TRANSPARENT, hwnd_de, janela_no_ponto, Jogo, mudar_estilo, nova_captura, user32)
from .visao import (cinza, diferenca, mapa_simbolo_suave, miolo, modelos_buff, picos, sem_cor_chave,
    semelhanca, tela_escura, tem_moldura)
from .desenho import contorno_arred, faixa_degrade, icone_arredondado, misturar_cor, ret_arred, texto_contorno
from .ap import achar_rotulo_ap, achar_rotulos_ap, ler_fracao, localizar_ap
from .relogio import arte_do_icone, fracao_passada, inicio_estimado
from .sites import icone_dp_rgb
from .captura import CapturaAuto
from .sons import Sons


# =============================================================== overlay

# Relógio do ícone de buff: as últimas leituras precisam concordar até max(10 s, 3% da duração)
RELOGIO_TOL, RELOGIO_TOL_MIN = 0.03, 10.0

# Quadros seguidos sem o rótulo "AP" no lugar guardado antes de procurar na tela toda (0,25 s cada)
AP_FALHAS_ROTULO = 3


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
        self.sons = Sons()

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
            bf["_arte"] = []
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
                    bf["_arte"].append(arte_do_icone(im))
            bf.update(_ativo=False, _visto=-99.0, _desde=0.0, _score=0.0, _cliente=None,
                      _relogio=[])
        self.preparar_imagens()
        self.calcular_caixa()
        self.relayout()
        self.root.after(300, self.preparar_sons)

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
            sk["_visual"] = self._visual_skill(sk)
            sk["_img"] = img(sk["_visual"])
            sk["_img_cd"] = img(sk["_visual"], 0.35)
        for bf in self.buffs:
            if not bf.get("_imgs"):
                bf["_img"] = None
                continue
            bf["_visuais"] = self._visual_buff(bf)
            bf["_img"] = img(bf["_visuais"][0])
            bf["_img_var"] = [img(im) for im in bf["_visuais"]]
            bf["_img_off"] = img(bf["_visuais"][0], 0.45, cinza=True)

    # ---- imagem mostrada no overlay
    # O print da sua barra de atalhos serve para detectar a recarga, mas pode vir com o número
    # da recarga ou a sombra do delay junto. Para mostrar, o padrão é o ícone oficial do jogo.

    def _visual_skill(self, sk):
        if self.L.get("icone_oficial", True):
            sid = self.painel._sid(sk)
            p = self.painel.icone_skill(sid) if sid else None
            if p:
                try:
                    return icone_dp_rgb(p)
                except Exception:
                    pass
            elif sid:
                self._pedir_icone(sid)
        return sk["_ref_full"]

    def _visual_buff(self, bf):
        """Para cada versão capturada, o ícone oficial mais parecido com ela (ex.: os 7
        elementos da Brisa Leve). A Divine Pride às vezes tem um desenho diferente do cliente
        LATAM: se nenhum oficial for parecido o bastante, fica a própria captura."""
        imgs = bf["_imgs"]
        # buff marcado na tela não guarda o id do ícone: procura pelo nome no banco
        efst = bf.get("efst") or self.painel.banco.efst_de(bf.get("nome", ""))
        if not self.L.get("icone_oficial", True) or not efst:
            return imgs
        oficiais = []
        for chave_efst, eid in efst:
            p = self.painel.icone_buff(eid)
            if p is None:
                self._pedir_icone(eid, "status", id(bf), chave_efst)
            try:
                oficiais.append(icone_dp_rgb(p) if p else None)
            except Exception:
                oficiais.append(None)
        if not any(oficiais):
            return imgs
        if np is None:
            return imgs
        cand = [o for o in oficiais if o is not None]
        res = []
        for im in imgs:
            g = cinza(im)
            nota, melhor = max(((semelhanca(cinza(o.resize(im.size, Image.LANCZOS)), g), k)
                                for k, o in enumerate(cand)), key=lambda x: x[0])
            res.append(cand[melhor] if nota >= LIMIAR_OFICIAL else im)
        return res

    def _pedir_icone(self, ident, tipo="skill", buff=None, chave_efst=None):
        """Baixa (uma vez) o ícone oficial que falta: ragassets e, se ele não tiver, a Divine
        Pride (com chave). Quando chega, o painel redesenha."""
        pedidos = self.__dict__.setdefault("_icones_pedidos", set())
        if (tipo, ident) in pedidos:
            return
        pedidos.add((tipo, ident))
        motivo = ("visual", buff, chave_efst)
        if self.painel.rag.ligado:
            self.painel.rag.pedir(tipo, ident, motivo)
        else:
            self.painel.pedir_icone_dp(tipo, ident, motivo)

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
            bf.update(_ativo=False, _visto=-99.0, _cliente=None)
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
            regiao, alvos, ov, geo, hwnd = job
            try:
                if sct is None:
                    sct = nova_captura()
                if geo:                         # tela preta = teleporte / troca de mapa
                    g = sct.grab({"left": geo[0], "top": geo[1], "width": geo[2], "height": geo[3]})
                    escura = tela_escura(np.frombuffer(g.rgb, np.uint8).reshape(g.height, g.width, 3))
                    self._tela_escura = (time.monotonic(), escura)
                shot = sct.grab(regiao)
                arr = np.asarray(Image.frombytes("RGB", shot.size, shot.rgb))
                tela_c = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
                tela_b = mapa_simbolo_suave(arr)
                ox, oy = ov[0] - regiao["left"], ov[1] - regiao["top"]
                agora = time.monotonic()
                res = {"hwnd": hwnd}              # de qual cliente do jogo é esta leitura
                brilho = None
                for chave_b, mods, artes in alvos:
                    melhor, qual, recorte, onde = 0.0, 0, None, None
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
                            _, v, _, (lx, ly) = cv2.minMaxLoc(r)
                            if v == v and v > melhor:
                                melhor, qual, recorte = v, n_var, None
                                onde = (lx - (W - tw) // 2, ly - (H - th) // 2, W, H)
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
                                    onde = (fx, fy, W, H)
                                break
                    relogio = None
                    if artes is not None and onde and melhor >= LIMIAR_BUFF:
                        fx, fy, W, H = onde
                        if fx >= 0 and fy >= 0 and fx + W <= arr.shape[1] and fy + H <= arr.shape[0]:
                            relogio = fracao_passada(arr[fy:fy + H, fx:fx + W],
                                                     artes[qual] if qual < len(artes) else None)
                    res[chave_b] = (melhor, agora, qual, recorte, relogio)
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
            if len(nomes) > 1 and not all(self.painel.rag.icone_status(e) for _, e in b["efst"]):
                # Os outros ícones vieram da Divine Pride (desenho pode ser outro): o "Auto"
                # confirma cada um com a sua tela
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
                                   [im.size for im in b["_imgs"]])),
                  # buff com duração: lê também o relógio do ícone (quanto já passou)
                  b.get("_arte") if b.get("duracao") else None)
                 for b in self.buffs if b.get("_tmpls")]
        regiao = self._area_buffs() if (self.ativo and pode_ler and alvos) else None
        hwnd = self.jogo.hwnd if self.perfil["titulo_janela_jogo"].strip() else None
        self._buff_job = ((regiao, alvos, (self.pos[0], self.pos[1], self.w, self.h), self.geo, hwnd)
                          if regiao else None)
        res = self._buff_res
        pausa = self._buffs_em_pausa(agora, pode_ler)
        for b in self.buffs:
            r = res.get(id(b))
            if r:
                b["_score"] = r[0]
                if r[0] >= LIMIAR_BUFF:
                    b["_visto"] = max(b["_visto"], r[1])
                    b["_cliente"] = res.get("hwnd")
                    b["_var_atual"] = r[2]          # qual versão do ícone está na tela
                    if r[3] is not None and r[0] >= 0.85 and not self._trocando:
                        self._trocar_por_real(b, r[2], r[3])
            # outro cliente em foco (ex.: o mercador): o buff é do personagem onde foi visto
            outro = b.get("_cliente") not in (None, hwnd) and user32.IsWindow(b["_cliente"])
            if (pausa or outro) and b["_ativo"]:
                # não dá para ver a tela: segura o buff (e dá um tempo para os ícones voltarem)
                b["_visto"] = max(b["_visto"], agora + BUFF_FOLGA_PAUSA)
            ativo = agora - b["_visto"] < BUFF_TOLERANCIA
            if ativo and not b["_ativo"]:
                b["_desde"] = b["_visto"]
                b["_avisou"] = False
                b["_relogio"] = []
            elif b["_ativo"] and not ativo and pode_ler:
                # acabou: só avisa se não avisou há pouco que estava acabando
                if agora - b.get("_avisou_em", -99.0) > 5:
                    self.avisar("buff", b)
            b["_ativo"] = ativo
            dur = b.get("duracao")
            if ativo and dur and r and r[0] >= LIMIAR_BUFF and len(r) > 4:
                self._acertar_pelo_relogio(b, r[1], r[4], dur)
            if ativo and dur and not b.get("_avisou"):
                resta = dur - (agora - b["_desde"])
                if 0 < resta <= self.L["aviso_vermelho_s"]:
                    b["_avisou"], b["_avisou_em"] = True, agora
                    self.avisar("buff", b)

    def _acertar_pelo_relogio(self, b, quando, relogio, dur):
        """Acerta o começo do buff pelo relógio do ícone: buff que já estava ativo quando o
        programa viu (ex.: abriu o programa no meio) e buff renovado (o véu volta ao começo)."""
        leit = b.setdefault("_relogio", [])
        if relogio is None or (leit and leit[-1][0] == quando):
            return                                     # sem leitura nova
        leit.append((quando, relogio[0]))
        del leit[:-5]
        tol = max(RELOGIO_TOL_MIN, dur * RELOGIO_TOL)
        ini = inicio_estimado(leit, dur, tol)
        if ini is None or abs(ini - b["_desde"]) <= tol:
            return
        if ini > b["_desde"]:                          # renovado: conta de novo e volta a avisar
            b["_avisou"] = False
        b["_desde"] = ini

    def _buffs_em_pausa(self, agora, pode_ler):
        """Hora em que não dá para ver os buffs: jogo minimizado ou coberto (alt-tab) ou tela
        preta (teleporte, troca de mapa). Nessa hora nenhum buff pode "acabar"."""
        if not self.ativo:
            return False
        if not pode_ler:
            return True
        quando, escura = getattr(self, "_tela_escura", (-99.0, False))
        if escura and agora - quando < 1.0:
            return True
        area = self._area_buffs()
        if area and self.perfil["titulo_janela_jogo"].strip() and self.jogo.hwnd:
            cx = area["left"] + area["width"] // 2
            for fy in (0.2, 0.5, 0.8):
                if janela_no_ponto(cx, area["top"] + int(area["height"] * fy)) not in (
                        self.jogo.hwnd, self.meu_hwnd):
                    return True
        return False

    def avisar(self, tipo, item):
        """Toca o som de aviso da skill/buff, se ele estiver ligado."""
        som = item.get("som", True)          # True/ausente = padrão, False = mudo, texto = som
        if not self.ativo or not self.jogo_ok or som is False:
            return
        L = self.L
        vol = L.get("som_volume", 70)
        if isinstance(som, str) and self.sons.tocar(som, vol):
            return                            # som próprio (se foi apagado, toca o padrão)
        self.sons.tocar(L.get("som_skill" if tipo == "skill" else "som_buff"), vol)

    def preparar_sons(self):
        """Abre de antemão os sons que este perfil usa."""
        if not self.perfil:
            return
        L = self.L
        self.sons.preparar([L.get("som_skill"), L.get("som_buff")] +
                           [i.get("som") for i in self.skills + self.buffs
                            if isinstance(i.get("som"), str)])

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
                    self.avisar("skill", sk)
            elif not sk["_delay"]:
                # Sem recarga manual: acaba quando o ícone volta, e aprende o tempo
                sk["_contando"] = False
                sk["_fim"] = agora
                self.avisar("skill", sk)
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
            self.jogo_ok = not dentro or janela_no_ponto(cx, cy) in (
                self.jogo.hwnd, self.meu_hwnd, self.painel.cronometro.hwnd)
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
            x1 = self.w - pad
            if L["orientacao"] != "vertical" and not edicao:
                # buffs escondidos ("Só quando ...") deixam o fim da faixa vazio: a barra
                # acompanha só até o último ícone que pode aparecer
                vis = [i for i, (tipo, it) in enumerate(itens)
                       if not (tipo == "bf" and self._buff_escondido(it))]
                ult = vis[-1] if vis else 0
                x1 = min(x1, max(pad + ult * dx + T, pad + max(T, 64)))
            self._desenhar_ap(c, m, agora, edicao, x1)
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

    def _desenhar_ap(self, c, m, agora, edicao, x1):
        """Barra de AP do tamanho da faixa de ícones: trilho escuro, preenchimento com brilho em
        cima e sombra embaixo, marcas a cada 25% e "AP  atual / máximo"."""
        pad, h = m["pad"], m["ap_h"]
        x0, y0 = pad, pad
        leitura = getattr(self, "ap", None)
        recente = leitura is not None and agora - getattr(self, "ap_t", -99) < 3
        if edicao and leitura is None:
            leitura, recente = (53, 200), True       # exemplo para posicionar
        frac = min(1.0, leitura[0] / leitura[1]) if leitura and leitura[1] else 0.0
        raio = 0 if self.estilo == "classico" else h / 2
        cor = self.L.get("ap_cor") or "#3b82f6"
        base = cor if recente else misturar_cor(cor, "#3a4050", 0.75)

        faixa_degrade(c, x0, y0, x1, y0 + h, raio,
                      lambda t: misturar_cor("#0b0e14", "#1c2230", t))          # trilho
        if frac > 0:
            xb = x0 + max(h if raio else 2, (x1 - x0) * frac)
            faixa_degrade(c, x0, y0, xb, y0 + h, raio, lambda t: (
                misturar_cor(base, "#ffffff", 0.45 * (1 - t / 0.4)) if t < 0.4 else
                misturar_cor(base, "#000000", 0.4 * (t - 0.4) / 0.6)))
            for q in (0.25, 0.5, 0.75):                                         # marcas
                xq = x0 + (x1 - x0) * q
                if xq < xb - 2 and h >= 10:
                    c.create_line(xq, y0 + 3, xq, y0 + h - 3,
                                  fill=misturar_cor(base, "#000000", 0.35))
        borda = misturar_cor(cor, "#ffffff", 0.35) if frac >= 1 and recente else "#3a4256"
        if raio:
            contorno_arred(c, x0, y0, x1, y0 + h, raio, borda)
        else:
            c.create_rectangle(x0, y0, x1, y0 + h, outline=borda, width=1)
        tam = max(6, min(int(h * 0.6), 22))
        fonte = ("Segoe UI", tam, "bold")
        cor_txt = "#ffffff" if recente else "#9aa4b5"
        if leitura is None:
            texto_contorno(c, (x0 + x1) / 2, y0 + h / 2, "AP ?", fonte, cor_txt)
            return
        txt = f"{leitura[0]} / {leitura[1]}" + ("" if recente else "  ?")
        if x1 - x0 >= 130 and h >= 12:                  # rótulo "AP" à esquerda
            texto_contorno(c, x0 + max(raio, 4) + tam * 0.9, y0 + h / 2, "AP",
                           ("Segoe UI", max(6, tam - 2), "bold"), "#e8ecf4")
        texto_contorno(c, (x0 + x1) / 2, y0 + h / 2, txt, fonte, cor_txt)

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
                # Um quadro sem o rótulo (mouse em cima, algo passando por cima) não quer dizer
                # que a janela mudou: pula a leitura e só procura de novo depois de 3 seguidos.
                self._ap_rotulo_falhas = getattr(self, "_ap_rotulo_falhas", 0) + 1
                if self._ap_rotulo_falhas >= AP_FALHAS_ROTULO:
                    self._perder_rotulo_ap()
                    self._buscar_ap(agora)
                return
            self._ap_rotulo_falhas = 0
            arr = arr[:, ox + 13:]
        lido = ler_fracao(arr) if arr is not None else None
        if lido is None:
            self._ap_falhas = getattr(self, "_ap_falhas", 0) + 1
            if manual:
                self._ap_manual_falhas = getattr(self, "_ap_manual_falhas", 0) + 1
            elif self._ap_falhas >= 4:                     # janela mudou de lugar ou fechou
                self._perder_rotulo_ap()
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

    def _perder_rotulo_ap(self):
        """Larga o lugar do rótulo "AP", mas lembra dele: se a busca na tela toda falhar
        (ex.: o quadro pego bem quando algo cobria a janela), volta a testar o lugar antigo."""
        if getattr(self, "_ap_rotulo", None):
            self._ap_rotulo_antigo = self._ap_rotulo
        self._ap_rotulo, self._ap_ult_busca = None, -99.0
        self._ap_falhas = self._ap_rotulo_falhas = 0

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
                self._ap_rotulo_antigo = achado
            elif getattr(self, "_ap_rotulo", None) is None:
                # não achou em lugar nenhum: testa de novo onde estava (a leitura confere se o
                # rótulo está lá antes de ler; se não estiver, larga e procura de novo)
                self._ap_rotulo = getattr(self, "_ap_rotulo_antigo", None)

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

    def _buff_escondido(self, bf):
        modo = bf.get("mostrar", "sempre")
        return (modo == "faltando" and bf["_ativo"]) or (modo == "ativo" and not bf["_ativo"])

    def _desenhar_buff(self, c, bf, x0, y0, T, agora, fonte, m):
        ativo = bf["_ativo"]
        if self._buff_escondido(bf):
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
