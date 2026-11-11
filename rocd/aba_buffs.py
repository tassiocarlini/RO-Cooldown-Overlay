"""Painel, aba Buffs (inclui a barra de AP)."""

import os
import time
import tkinter as tk
import traceback
from tkinter import messagebox, simpledialog, ttk

from PIL import Image, ImageTk

from .config import MOSTRAR_BUFF, PASTA, VERSAO, cv2, np, registrar
from .janelas import nova_captura
from .ap import achar_rotulos_ap, ler_fracao, localizar_ap
from .dados import fmt_tempo, ler_tempo
from .sites import icone_dp_rgb
from .captura import CapturaAuto
from .seletores import Seletor, SeletorSkill
from .perfis import Perfis


class AbaBuffs:
    """Métodos do Painel (aba Buffs (inclui a barra de AP))."""

    # ---- buffs

    def _montar_aba_buffs(self, aba):
        f = ttk.Frame(aba)
        f.pack(fill="both", expand=True, padx=4, pady=4)
        barra = ttk.Frame(f)
        barra.pack(fill="x", padx=6, pady=(6, 2))
        self.dica(self.bt(barra, "Buff pelo nome", "mais_circulo",
                          lambda: SeletorSkill(self, None, buff=True), amarelo=True),
                  "Escolha o buff pelo nome e pronto: o programa já tem os ícones do jogo "
                  "e acha o buff na tela quando ele estiver ativo. Consumíveis (Estimulante, "
                  "poções, comidas) também estão na busca.").pack(side="left")
        self.dica(self.bt(barra, "Marcar na tela", "mais", self.adicionar_buff),
                  "Só se o buff não estiver na busca: com ele ativo no jogo, marque o ícone "
                  "na coluna de buffs (à direita da tela).").pack(side="left", padx=4)
        self.dica(self.bt(barra, "Área dos buffs", "selecao", self.marcar_area_buffs),
                  "Opcional: marque a região onde os buffs aparecem para a leitura ficar "
                  "mais leve. Sem marcar, o programa olha o lado direito do jogo."
                  ).pack(side="left", padx=4)
        self.lbl_area = ttk.Label(barra, style="Dica.TLabel")
        self.lbl_area.pack(side="left", padx=8)
        ttk.Label(f, style="Dica.TLabel", wraplength=760, justify="left",
                  text="O programa usa os ícones oficiais do jogo (todas as versões, ex.: os 7 "
                       "elementos da Brisa Leve) e acha o buff na tela quando ele estiver ativo. "
                       "Consumíveis (Estimulante, poções, comidas) entram do mesmo jeito."
                  ).pack(anchor="w", padx=8, pady=(2, 4))
        self.lista_buffs = self.lista_rolavel(f, padx=6, pady=4)
        self.lista_buffs.columnconfigure(1, weight=1)    # o nome do buff estica

    def montar_buffs(self):
        for wdg in self.lista_buffs.winfo_children():
            wdg.destroy()
        a = self.perfil.get("area_buffs")
        self.lbl_area.config(text="Área: marcada ✓" if a else "Área: lado direito")
        buffs = self.perfil.get("buffs", [])
        if not buffs:
            self.lista_vazia(self.lista_buffs, "Nenhum buff ainda", (
                "1. Escolha o buff ou consumível pelo nome (ex.: Brisa Leve, Estimulante).\n"
                "2. No jogo, deixe o buff ativo: o programa acha o ícone sozinho."),
                "Buff pelo nome", lambda: SeletorSkill(self, None, buff=True))
            return
        for col, t in enumerate(("ÍCONE", "NOME", "", "MOSTRAR", "DURAÇÃO",
                                 "ESTADO", "")):
            ttk.Label(self.lista_buffs, text=t, style="Titulo.TLabel").grid(
                row=0, column=col, padx=4, sticky="w")
        for i, bf in enumerate(buffs):
            r = i + 1
            self.cartao(self.lista_buffs, r, 7)
            fi = ttk.Frame(self.lista_buffs, style="Cartao.TFrame")
            fi.grid(row=r, column=0, padx=(10, 4), pady=9, sticky="w")
            imgs = bf.get("_visuais") or bf.get("_imgs") or [icone_dp_rgb(p) for p in
                                       (self.icone_buff(e) for _, e in bf.get("efst", [])) if p]
            bf["_thumbs"] = [ImageTk.PhotoImage(im.resize((24, 24), Image.LANCZOS))
                             for im in imgs[:1]]
            for th in bf["_thumbs"]:
                ttk.Label(fi, image=th, style="Cartao.TLabel").pack(side="left", padx=1)
            if not bf["_thumbs"]:
                ttk.Label(fi, text="—", style="Cartao.Dica.TLabel").pack(side="left")
            elif len(imgs) > 1:               # buff com várias versões (ex.: Brisa Leve)
                ttk.Label(fi, text=f"×{len(imgs)}", style="Cartao.Dica.TLabel").pack(side="left", padx=2)

            vn = tk.StringVar(value=bf.get("nome", ""))
            ttk.Entry(self.lista_buffs, textvariable=vn, width=11, style="Cartao.TEntry").grid(
                row=r, column=1, padx=2, sticky="ew")
            vn.trace_add("write", lambda *_, b=bf, v=vn: (b.__setitem__("nome", v.get()),
                                                          self.salvar_depois()))
            fb = ttk.Frame(self.lista_buffs, style="Cartao.TFrame")
            fb.grid(row=r, column=2, padx=2)
            efst = bf.get("efst") or self.banco.efst_de(bf.get("nome", ""))
            if efst and all(self.rag.icone_status(e) for _, e in efst):
                # todas as versões têm o ícone oficial do jogo: nada para marcar à mão
                ttk.Label(fb, text="✓ ícones do jogo", style="Cartao.Dica.TLabel").pack(
                    side="left", padx=6)
            else:
                self.dica(self.bt(fb, "Ícone", "mais", lambda b=bf: self.capturar_variante(b),
                                  fundo="Cartao"),
                          "Marcar à mão mais uma versão do ícone deste buff.").pack(side="left")
                self.dica(self.bt(fb, "Auto", "radar", lambda b=bf: self.captura_auto(b),
                                  fundo="Cartao"),
                          "Use o buff no jogo com cada elemento/versão: cada ícone novo é salvo "
                          "sozinho.").pack(side="left", padx=(4, 0))

            inv = {v: k for k, v in MOSTRAR_BUFF.items()}
            vm = tk.StringVar(value=inv.get(bf.get("mostrar", "sempre"), "Sempre"))
            cb = ttk.Combobox(self.lista_buffs, textvariable=vm, state="readonly", width=10,
                              values=list(MOSTRAR_BUFF), style="Cartao.TCombobox")
            cb.grid(row=r, column=3, padx=2)
            cb.bind("<<ComboboxSelected>>", lambda _e, b=bf, v=vm: (
                b.__setitem__("mostrar", MOSTRAR_BUFF[v.get()]), self.salvar_depois()))

            vd = tk.StringVar(value=fmt_tempo(bf.get("duracao")))
            ed = ttk.Entry(self.lista_buffs, textvariable=vd, width=5, justify="center",
                           style="Cartao.TEntry")
            ed.grid(row=r, column=4, padx=2)
            vd.trace_add("write", lambda *_, b=bf, v=vd, e=ed: self._on_duracao(b, v, e))
            bf["_tk"] = (vn, vm, vd)

            bf["_lbl_est"] = self.etiqueta_estado(self.lista_buffs)
            bf["_lbl_est"].grid(row=r, column=5, padx=2)
            fo = ttk.Frame(self.lista_buffs, style="Cartao.TFrame")
            fo.grid(row=r, column=6, padx=(2, 10))
            self.bt(fo, "", "cima", lambda k=i: self.mover_buff(k, -1), fundo="Cartao").pack(side="left")
            self.bt(fo, "", "baixo", lambda k=i: self.mover_buff(k, 1), fundo="Cartao").pack(side="left")
            self.bt(fo, "", "lixeira", lambda k=i: self.remover_buff(k), fundo="Cartao").pack(
                side="left", padx=(4, 0))

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
        # consumível com duração conhecida (ex.: Estimulante, 30 min): o aviso de "acabando"
        # já funciona sem a pessoa digitar nada
        bf = {"nome": nome, "variantes": [], "mostrar": "sempre",
              "duracao": self.banco.duracao_de(nome)}
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
