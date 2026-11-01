"""Janela principal (Painel): base, tema, perfis, aparência e status."""

import os
import re
import shutil
import sys
import time
import tkinter as tk
import traceback
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

from PIL import Image, ImageDraw, ImageTk

from .config import ARQ_APP, ESTILOS, NOME_APP, PASTA, TODAS, VERSAO, registrar, sv_ttk
from .desenho import (BOTOES, COR, NOMES_ICONES, TEXTO_ESCURO, desenhar_icone, dourar,
                      imagem_aba, imagem_degrade, logo_app)
from .dados import Banco, fmt_aprendido, gravar_json, ler_json
from .sites import DivinePride, RagAssets
from .seletores import SeletorSkill
from .perfis import importar_dados_antigos_sozinho, migrar_config_antiga, nome_seguro, Perfis
from .janelas import Jogo, barra_escura
from .overlay import Overlay
from .aba_buffs import AbaBuffs
from .aba_skills import AbaSkills
from .aba_avancado import AbaAvancado
from .aba_sons import AbaSons


# =============================================================== painel

class Painel(AbaSkills, AbaBuffs, AbaSons, AbaAvancado):
    def __init__(self, root):
        self.root = root
        importar_dados_antigos_sozinho()
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
        barra_escura(self.win)

    # ---- tema e ícones

    def _aplicar_tema(self):
        self.escuro = True
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
            if self.tema_moderno:
                try:
                    self._sv_dourado()
                except Exception:
                    registrar("Não deu para dourar o tema:\n" + traceback.format_exc())
        if not self.tema_moderno and "clam" in st.theme_names():
            st.theme_use("clam")
            st.configure(".", background=COR["fundo"], foreground="#fafafa",
                         fieldbackground="#2b2b2b")
        self.cor_fundo = str(st.lookup("TFrame", "background") or "") or COR["fundo"]
        self.win.configure(bg=self.cor_fundo)
        st.configure("Dica.TLabel", foreground=COR["mudo"])
        st.configure("Titulo.TLabel", font=("Segoe UI", 8, "bold"), foreground=COR["mudo"])
        st.configure("TLabelframe.Label", font=("Segoe UI", 10, "bold"), foreground=COR["ouro"])
        st.configure("Campo.TLabel", font=("Segoe UI", 10))
        st.map("TCombobox", selectbackground=[("readonly", "hover", "#3a3a3a"),
                                              ("readonly", "focus", "#3a3a3a")])
        st.map("Treeview", background=[("selected", "#3a3220")],
               foreground=[("selected", COR["ouro_claro"])])
        self.root.option_add("*TCombobox*Listbox.selectBackground", COR["ouro_escuro"])
        self.root.option_add("*TCombobox*Listbox.selectForeground", COR["texto_ouro"])

        def icones(cor):
            return {n: ImageTk.PhotoImage(desenhar_icone(n, cor, 16)) for n in NOMES_ICONES}
        self.ic = icones(COR["texto"])
        self.ic_escuro = icones(COR["texto_ouro"])
        self.ic_mudo = icones(COR["mudo"])
        self.ic_ouro = icones(COR["ouro"])
        self.ic_verm = icones(COR["vermelho"])
        self._logos = [ImageTk.PhotoImage(logo_app(t)) for t in (16, 32, 64)]
        self.logo_topo = ImageTk.PhotoImage(logo_app(30))
        try:
            self.win.iconphoto(True, *self._logos)
        except tk.TclError:
            pass
        self._criar_estilos(st)

    def _sv_dourado(self):
        """O tema sv_ttk vem em azul (caixas de marcar, deslizantes, foco): troca por dourado.
        Recolore a folha de imagens do tema e copia cada pedaço por cima do original."""
        pasta = Path(sv_ttk.__file__).parent / "theme"
        info = re.findall(r"^\s*([\w-]+) (\d+) (\d+) (\d+) (\d+)",
                          (pasta / "sprites_dark.tcl").read_text(encoding="utf-8"), re.M)
        folha = dourar(Image.open(pasta / "spritesheet_dark.png"))
        tk_ = self.root.tk
        for nome, x, y, w, h in info:
            x, y, w, h = int(x), int(y), int(w), int(h)
            try:
                alvo = tk_.eval(f"set ttk::theme::sv_dark::I({nome})")
            except tk.TclError:
                continue
            pedaco = ImageTk.PhotoImage(folha.crop((x, y, x + w, y + h)), master=self.root)
            tk_.call(alvo, "copy", pedaco, "-compositingrule", "set")

    def _criar_estilos(self, st):
        """Botões lisos (dourado só no principal), botões só com ícone e abas com traço."""
        self._imgs_estilo = []

        def foto(im):
            img = ImageTk.PhotoImage(im)
            self._imgs_estilo.append(img)
            return img

        def botao(fundo, borda):
            return foto(imagem_degrade(40, 28, fundo, fundo, borda=borda, raio=6))

        i_d = botao("#202020", COR["borda"])
        for nome, (normal, hover, apertado) in BOTOES.items():
            elem = f"{nome}.botao"
            try:
                st.element_create(elem, "image", botao(*normal), ("disabled", i_d),
                                  ("pressed", botao(*apertado)), ("active", botao(*hover)),
                                  border=(8, 7, 8, 7), sticky="nsew")
            except tk.TclError:
                pass                             # já existe
            estilo = f"{nome}.TButton"
            st.layout(estilo, [(elem, {"sticky": "nsew", "children": [
                ("Button.padding", {"sticky": "nsew", "children": [
                    ("Button.label", {"sticky": "nsew"})]})]})])
            escuro = nome in TEXTO_ESCURO
            st.configure(estilo, padding=(8, 2), anchor="center",
                         foreground=COR["texto_ouro"] if escuro else COR["texto"],
                         font=("Segoe UI", 10, "bold") if escuro else ("Segoe UI", 10))
            st.map(estilo, foreground=[("disabled", "#6b6b6b")])
        st.configure("Perigo.TButton", foreground=COR["vermelho"])
        self.estilo_padrao = "Grad.TButton"
        self.estilo_destaque = "Destaque.TButton"

        # Botão só com ícone: sem caixa; a caixa aparece ao passar o mouse
        vazio = foto(Image.new("RGBA", (28, 28), (0, 0, 0, 0)))
        try:
            st.element_create("Icone.botao", "image", vazio,
                              ("pressed", botao(COR["cartao"], COR["borda2"])),
                              ("active", botao(COR["campo"], COR["borda2"])),
                              border=(8, 7, 8, 7), sticky="nsew")
        except tk.TclError:
            pass
        st.layout("Icone.TButton", [("Icone.botao", {"sticky": "nsew", "children": [
            ("Button.padding", {"sticky": "nsew", "children": [
                ("Button.label", {"sticky": "nsew"})]})]})])
        st.configure("Icone.TButton", padding=(4, 3))

        # Abas lisas: a selecionada ganha um traço dourado embaixo
        t_n = foto(imagem_aba(40, 34, self.cor_fundo))
        t_s = foto(imagem_aba(40, 34, self.cor_fundo, COR["ouro"]))
        try:
            st.element_create("Aba.tab", "image", t_n, ("selected", t_s),
                              border=(8, 8, 8, 4), sticky="nsew")
        except tk.TclError:
            pass
        st.layout("TNotebook.Tab", [("Aba.tab", {"sticky": "nsew", "children": [
            ("Notebook.padding", {"side": "top", "sticky": "nsew", "children": [
                ("Notebook.label", {"side": "top", "sticky": ""})]})]})])
        st.configure("TNotebook.Tab", padding=(16, 7), foreground=COR["mudo"])
        # sem a moldura clara do sv_ttk atrás das abas; só uma borda fina em volta do conteúdo
        st.layout("TNotebook", [("Notebook.client", {"sticky": "nsew"})])
        st.configure("TNotebook", tabmargins=(2, 4, 2, 0), background=self.cor_fundo,
                     bordercolor=COR["borda"], lightcolor=COR["borda"], darkcolor=COR["borda"])
        st.map("TNotebook.Tab",
               foreground=[("selected", COR["texto"]), ("active", COR["texto"])],
               expand=[("selected", (0, 0, 0, 0))],
               font=[("selected", ("Segoe UI", 10, "bold")), ("!selected", ("Segoe UI", 10))])

        # Cópias dos estilos com outro fundo (cantos dos botões e campos pegam essa cor)
        for prefixo, cor in (("Cartao", COR["cartao"]), ("Rodape", COR["cabecalho"])):
            for base in ("TFrame", "TLabel", "Dica.TLabel", "Titulo.TLabel", "Campo.TLabel",
                         "TCheckbutton", "TRadiobutton", "TEntry", "TCombobox", "TSpinbox",
                         "Icone.TButton", *(f"{n}.TButton" for n in BOTOES)):
                st.configure(f"{prefixo}.{base}", background=cor)

    def cartao(self, grade, linha, colunas):
        """Fundo de cartão atrás de uma linha da grade. Criar antes dos widgets da linha
        (assim fica por baixo deles) e usar os estilos "Cartao." nos widgets."""
        f = tk.Frame(grade, bg=COR["cartao"], highlightthickness=1,
                     highlightbackground=COR["borda"], bd=0)
        f.grid(row=linha, column=0, columnspan=colunas, sticky="nsew", pady=3)
        return f

    def aba(self, texto, icone):
        """Texto e ícone de uma aba (ícone dourado na aba aberta)."""
        return {"text": " " + texto, "compound": "left",
                "image": (self.ic_mudo[icone], "selected", self.ic_ouro[icone])}

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
            tk.Label(j, text=texto, justify="left", wraplength=320, bg=COR["campo"],
                     fg=COR["texto"], font=("Segoe UI", 9), padx=10, pady=6, bd=0,
                     highlightthickness=1, highlightbackground=COR["borda2"]).pack()
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

    def bt(self, pai, texto, icone, cmd, destaque=False, perigo=False, amarelo=False, fundo="",
           **kw):
        """Botão com ícone à esquerda do texto, ou só o ícone (texto vazio: cinza, dourado com o
        mouse em cima). fundo: "Cartao" ou "Rodape" para botões nessas faixas."""
        pre = fundo + "." if fundo else ""
        if not texto:
            return ttk.Button(pai, image=(self.ic_mudo[icone], "active", self.ic_ouro[icone]),
                              command=cmd, style=pre + "Icone.TButton", **kw)
        estilo = ("Amarelo.TButton" if amarelo else "Perigo.TButton" if perigo else
                  self.estilo_destaque if destaque else self.estilo_padrao)
        icones = self.ic_escuro if amarelo or destaque else self.ic_verm if perigo else self.ic
        return ttk.Button(pai, text=texto, image=icones.get(icone), compound="left",
                          command=cmd, style=pre + estilo, **kw)

    # ---- interface

    def _montar_ui(self):
        w = self.win

        # Topo: logo, nome e se o jogo e o overlay estão funcionando
        topo = tk.Frame(w, bg=COR["cabecalho"])
        topo.pack(fill="x")
        tk.Label(topo, image=self.logo_topo, bg=COR["cabecalho"]).pack(side="left", padx=(14, 10),
                                                                       pady=10)
        tk.Label(topo, text=NOME_APP, bg=COR["cabecalho"], fg=COR["texto"],
                 font=("Segoe UI", 13, "bold")).pack(side="left")
        tk.Label(topo, text=f"v{VERSAO}", bg=COR["cabecalho"], fg=COR["mudo"],
                 font=("Segoe UI", 9)).pack(side="left", padx=8, pady=(4, 0))
        self.pilulas = {}
        for chave in ("overlay", "jogo"):
            f = tk.Frame(topo, bg=COR["campo"], highlightthickness=1,
                         highlightbackground=COR["borda"])
            f.pack(side="right", padx=(0, 14 if chave == "overlay" else 6))
            c = tk.Canvas(f, width=9, height=9, bg=COR["campo"], highlightthickness=0)
            bola = c.create_oval(1, 1, 8, 8, fill=COR["mudo"], outline="")
            c.pack(side="left", padx=(9, 5))
            lb = tk.Label(f, text="", bg=COR["campo"], fg=COR["texto"], font=("Segoe UI", 9))
            lb.pack(side="left", padx=(0, 9), pady=3)
            self.pilulas[chave] = (c, bola, lb)
        self._jogo_topo = Jogo()                      # só para a bolinha "jogo encontrado"
        self._jogo_topo_t = -99.0

        # Perfil
        fp = ttk.Frame(w)
        fp.pack(fill="x", padx=12, pady=(12, 4))
        ttk.Label(fp, text="PERFIL", style="Titulo.TLabel").pack(side="left", padx=(0, 8))
        self.var_perfil = tk.StringVar()
        self.cb_perfil = ttk.Combobox(fp, textvariable=self.var_perfil, state="readonly", width=30)
        self.cb_perfil.pack(side="left")
        self.cb_perfil.bind("<<ComboboxSelected>>",
                            lambda _e: self.trocar_perfil(self.var_perfil.get()))
        for txt, ic, cmd in (("Excluir", "lixeira", self.excluir_perfil),
                             ("Renomear", "lapis", self.renomear_perfil),
                             ("Duplicar", "copiar", self.duplicar_perfil),
                             ("Novo", "mais", self.novo_perfil)):
            self.bt(fp, txt, ic, cmd, perigo=txt == "Excluir").pack(side="right", padx=(6, 0))

        # Skills
        # Abas: deixa a janela compacta (cabe em telas de notebook)
        self.abas = nb = ttk.Notebook(w)
        nb.pack(fill="both", expand=True, padx=8, pady=(6, 4))
        aba_sk, aba_ap, aba_av = ttk.Frame(nb), ttk.Frame(nb), ttk.Frame(nb)
        aba_bf = ttk.Frame(nb)
        nb.add(aba_sk, **self.aba("Skills", "relogio"))
        nb.add(aba_bf, **self.aba("Buffs", "escudo"))
        self._montar_aba_buffs(aba_bf)
        aba_som = ttk.Frame(nb)
        nb.add(aba_som, **self.aba("Sons", "som"))
        self._montar_aba_sons(aba_som)
        nb.add(aba_ap, **self.aba("Aparência", "mover"))
        nb.add(aba_av, **self.aba("Avançado", "chave"))
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
        self.var_oficial = tk.BooleanVar()
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
        c.grid(row=7, column=0, columnspan=3, sticky="w", padx=8, pady=(4, 0))
        c = ttk.Checkbutton(fi, text="Ícone oficial do jogo (não o print da sua barra)",
                            variable=self.var_oficial, command=self._on_estilo)
        c.grid(row=8, column=0, columnspan=3, sticky="w", padx=8, pady=(4, 8))
        self.dica(c, "O print da sua barra de atalhos pode vir com o número da recarga ou a "
                     "sombra do delay. Com isto ligado, o overlay mostra o ícone oficial "
                     "(ragassets ou Divine Pride); o print continua servindo para detectar.")

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
        if getattr(sys, "frozen", False):
            b_imp = self.bt(lat, "Trazer perfis da versão antiga", "importar", self.importar_versao_antiga)
            b_imp.pack(side="right")
            self.dica(b_imp, "Usava a versão em Python (com o ro_cooldown_overlay.py)? Escolha a "
                             "pasta dela para copiar seus perfis e a chave da Divine Pride.")
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
        rod = tk.Frame(w, bg=COR["cabecalho"])
        fr = ttk.Frame(rod, style="Rodape.TFrame")
        fr.pack(fill="x", padx=12, pady=(10, 4))
        self.bt_iniciar = self.bt(fr, "Iniciar overlay", "play", self.alternar_overlay,
                                  destaque=True, fundo="Rodape")
        self.dica(self.bt_iniciar, "Liga ou desliga o overlay em cima do jogo.")
        self.bt_iniciar.pack(side="left")
        self.var_auto = tk.BooleanVar(value=bool(self.app_cfg.get("iniciar_auto")))
        self.dica(ttk.Checkbutton(fr, text="Iniciar automaticamente ao abrir",
                                  variable=self.var_auto, command=self._on_auto,
                                  style="Rodape.TCheckbutton"),
                  "Liga o overlay sozinho toda vez que o programa abrir.").pack(side="left", padx=12)
        self.dica(self.bt(fr, "Pasta de dados", "pasta", lambda: os.startfile(PASTA), fundo="Rodape"),
                  "Abre a pasta com seus perfis e os arquivos de log (log.txt, erro.log)."
                  ).pack(side="right")
        self.dica(self.bt(fr, "Tirar print", "camera", self.tirar_print, fundo="Rodape"),
                  "Contagem de 5 s: volte ao jogo e use uma skill. O print sai com o overlay."
                  ).pack(side="right", padx=6)
        fst = tk.Frame(rod, bg=COR["cabecalho"])
        fst.pack(fill="x", padx=12, pady=(0, 8))
        self.bola_status = tk.Canvas(fst, width=8, height=8, bg=COR["cabecalho"],
                                     highlightthickness=0)
        self._bola_status = self.bola_status.create_oval(0, 0, 8, 8, fill=COR["mudo"], outline="")
        self.bola_status.pack(side="left", padx=(0, 6))
        self.lbl_status = ttk.Label(fst, text="", style="Rodape.Dica.TLabel")
        self.lbl_status.pack(side="left", fill="x")
        rod.pack(side="bottom", fill="x", before=fp)
        tk.Frame(w, bg=COR["borda"], height=1).pack(side="bottom", fill="x", before=fp)

    def status(self, txt):
        self.lbl_status.config(text=txt)

    @staticmethod
    def cor_estado(t):
        """Cor do texto de estado de uma skill ou buff."""
        if t.startswith(("pronta", "ATIVO")):
            return COR["verde"]
        if t.startswith(("DELAY", "ative")):
            return COR["ouro"]
        if t.startswith(("não", "sem", "jogo não", "barra")):
            return COR["vermelho"]
        return COR["mudo"]

    def _atualizar_topo(self):
        """Bolinhas do topo: o jogo foi achado? o overlay está ligado?"""
        ov = self.overlay
        agora = time.monotonic()
        if ov.ativo:
            achou = ov.geo is not None or ov.jogo.hwnd is not None
        else:
            if agora - self._jogo_topo_t > 1.5:
                self._jogo_topo_t = agora
                titulo = (self.perfil or {}).get("titulo_janela_jogo", "").strip()
                self._jogo_topo.hwnd = None
                if titulo:
                    self._jogo_topo.localizar(titulo, agora)
            achou = self._jogo_topo.hwnd is not None
        for chave, (texto, cor) in (
                ("jogo", ("Jogo encontrado", COR["verde"]) if achou else
                 ("Jogo não encontrado", COR["vermelho"])),
                ("overlay", ("Overlay ativo", COR["ouro"]) if ov.ativo else
                 ("Overlay parado", COR["mudo"]))):
            c, bola, lb = self.pilulas[chave]
            if lb.cget("text") != texto:
                lb.config(text=texto)
                c.itemconfig(bola, fill=cor)
        self.bola_status.itemconfig(self._bola_status,
                                    fill=COR["ouro"] if ov.ativo else COR["mudo"])

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
        self.montar_sons()
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
        self.var_oficial.set(bool(L.get("icone_oficial", True)))
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
        L["icone_oficial"] = bool(self.var_oficial.get())
        self.overlay.preparar_imagens()
        self.montar_lista()
        self.montar_buffs()
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
                             image=self.ic["check"] if ligar else self.ic["mover"],
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
            self.bt_iniciar.config(text="Parar overlay", image=self.ic_escuro["stop"])
            self.status("Overlay rodando. Pode minimizar esta janela.")

    def parar(self):
        self.overlay.parar()
        self.bt_iniciar.config(text="Iniciar overlay", image=self.ic_escuro["play"])
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
                le.config(text=t, foreground=self.cor_estado(t))
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
                le.config(text=t, foreground=self.cor_estado(t))
                sk["_lbl_apr"].config(text=fmt_aprendido(sk))
        except tk.TclError:
            pass
        try:
            self._atualizar_topo()
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
