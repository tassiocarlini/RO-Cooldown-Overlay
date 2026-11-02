"""Painel, aba Sons."""

import os
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from PIL import Image, ImageTk

from .config import PADRAO, PASTA_MEUS_SONS, SEM_SOM, SONS_PRONTOS, SONS_SUGERIDOS, registrar
from .perfis import nome_seguro
from .sons import baixar_myinstants


class AbaSons:
    """Métodos do Painel (aba Sons)."""

    # ---- sons

    def _montar_aba_sons(self, aba):
        f = ttk.Frame(aba)
        f.pack(fill="both", expand=True, padx=4, pady=6)
        f.columnconfigure(0, weight=2, uniform="col")
        f.columnconfigure(1, weight=3, uniform="col")
        f.rowconfigure(0, weight=1)
        esq, dir_ = ttk.Frame(f), ttk.Frame(f)
        esq.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        dir_.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        # --- Som padrão
        fp = ttk.LabelFrame(esq, text="Som padrão")
        fp.pack(fill="x", pady=(0, 8))
        fp.columnconfigure(1, weight=1)
        self.var_som_skill = tk.StringVar()
        self.var_som_buff = tk.StringVar()
        self.var_vol = tk.DoubleVar()
        self.cbs_som = []
        for linha, (rotulo, var, chave, ajuda) in enumerate((
                ("Skill pronta", self.var_som_skill, "som_skill",
                 "Toca quando a recarga de uma skill termina."),
                ("Buff acabando", self.var_som_buff, "som_buff",
                 "Toca quando faltam poucos segundos para o buff acabar (se ele tiver "
                 "duração) ou quando ele some da tela."))):
            ttk.Label(fp, text=rotulo, style="Campo.TLabel").grid(
                row=linha, column=0, sticky="w", padx=(8, 6), pady=(6, 0))
            cb = ttk.Combobox(fp, textvariable=var, state="readonly", width=14)
            cb.grid(row=linha, column=1, sticky="w", pady=(6, 0))
            cb.bind("<<ComboboxSelected>>", lambda _e, c=chave: self._on_som(c, True))
            self.dica(cb, ajuda)
            self.cbs_som.append(cb)
            b = self.bt(fp, "", "play", lambda c=chave: self._on_som(c, True))
            b.grid(row=linha, column=2, sticky="e", padx=(4, 8), pady=(6, 0))
            self.dica(b, "Testar: toca o som escolhido.")
        ttk.Label(fp, text="Volume", style="Campo.TLabel").grid(
            row=2, column=0, sticky="w", padx=(8, 6), pady=(6, 8))
        fv = ttk.Frame(fp)
        fv.grid(row=2, column=1, columnspan=2, sticky="ew", padx=(0, 8), pady=(6, 8))
        sc = ttk.Scale(fv, from_=0, to=100, orient="horizontal", variable=self.var_vol,
                       command=self._on_volume)
        sc.pack(side="left", fill="x", expand=True)
        self.lbl_vol = ttk.Label(fv, width=5, anchor="e")
        self.lbl_vol.pack(side="left", padx=(4, 0))
        self.dica(sc, "Volume dos sons de aviso (0% = mudo).")

        # --- Meus sons
        fm = ttk.LabelFrame(esq, text="Meus sons")
        fm.pack(fill="both", expand=True)
        lb = ttk.Frame(fm)
        lb.pack(fill="x", padx=8, pady=(6, 2))
        self.dica(self.bt(lb, "Adicionar som", "mais", self.adicionar_som, amarelo=True),
                  "Escolha um arquivo .mp3 ou .wav do seu PC e dê um nome para ele.").pack(side="left")
        self.dica(self.bt(lb, "MyInstants", "importar", lambda: self.baixar_do_myinstants()),
                  "Cole o link de um som do myinstants.com: o programa baixa e adiciona ele."
                  ).pack(side="left", padx=(6, 0))
        self.dica(self.bt(lb, "", "pasta", lambda: os.startfile(self._pasta_meus_sons())),
                  "Abre a pasta com os seus sons.").pack(side="left", padx=6)
        ttk.Label(fm, style="Dica.TLabel", wraplength=300, justify="left",
                  text="Um MP3 ou WAV do seu PC, ou o link de um som do MyInstants. De "
                       "preferência curtinho (1 a 3 s). Ficam só no seu PC."
                  ).pack(anchor="w", padx=8, pady=(0, 4))
        self.lista_meus = ttk.Frame(fm)
        self.lista_meus.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # --- Som de cada skill e buff
        fi = ttk.LabelFrame(dir_, text="Som de cada skill e buff")
        fi.pack(fill="both", expand=True)
        ttk.Label(fi, style="Dica.TLabel", wraplength=440, justify="left",
                  text=f"\"{PADRAO}\" usa o som padrão ao lado. \"{SEM_SOM}\" deixa a skill ou o "
                       "buff mudo.").pack(anchor="w", padx=8, pady=(6, 4))
        cont = ttk.Frame(fi)
        cont.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self.sons_cv = tk.Canvas(cont, highlightthickness=0, height=150, bg=self.cor_fundo)
        sb = ttk.Scrollbar(cont, orient="vertical", command=self.sons_cv.yview)
        self.lista_sons = ttk.Frame(self.sons_cv)
        self.lista_sons.bind("<Configure>", lambda _e: self.sons_cv.configure(
            scrollregion=self.sons_cv.bbox("all")))
        self.sons_cv.create_window((0, 0), window=self.lista_sons, anchor="nw")
        self.sons_cv.configure(yscrollcommand=sb.set)
        self.sons_cv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        rolar = lambda e: self.sons_cv.yview_scroll(-1 if e.delta > 0 else 1, "units")
        self.sons_cv.bind("<Enter>", lambda _e: self.sons_cv.bind_all("<MouseWheel>", rolar))
        self.sons_cv.bind("<Leave>", lambda _e: self.sons_cv.unbind_all("<MouseWheel>"))
        self.abas.bind("<<NotebookTabChanged>>", lambda _e: self.montar_sons()
                       if self.abas.select() == str(aba) else None)

    @staticmethod
    def _pasta_meus_sons():
        PASTA_MEUS_SONS.mkdir(parents=True, exist_ok=True)
        return PASTA_MEUS_SONS

    def montar_sons(self):
        """Atualiza a aba Sons (listas de som, som de cada skill/buff e os seus sons)."""
        if not self.perfil:
            return
        sons = self.overlay.sons
        opcoes = list(sons.opcoes())
        L = self.perfil["layout"]
        self._carregando = True
        for cb in self.cbs_som:
            cb["values"] = opcoes
        self.var_som_skill.set(sons.nome(L.get("som_skill")))
        self.var_som_buff.set(sons.nome(L.get("som_buff")))
        self.var_vol.set(L.get("som_volume", 70))
        self.lbl_vol.config(text=f"{int(L.get('som_volume', 70))}%")
        self.root.after_idle(self._fim_carregando)

        for wdg in self.lista_sons.winfo_children():
            wdg.destroy()
        itens = ([("skill", s) for s in self.perfil["skills"]] +
                 [("buff", b) for b in self.perfil.get("buffs", [])])
        if not itens:
            ttk.Label(self.lista_sons, style="Dica.TLabel",
                      text="Adicione skills e buffs nas abas Skills ofensivas e Buffs.").grid(
                row=0, column=0, padx=6, pady=10, sticky="w")
        for r, (tipo, item) in enumerate(itens):
            self.cartao(self.lista_sons, r, 5)
            img = (item.get("_visual") or item.get("_ref_full") if tipo == "skill" else
                   (item.get("_visuais") or item.get("_imgs") or [None])[0])
            if img is not None:
                item["_thumb_som"] = ImageTk.PhotoImage(img.resize((22, 22), Image.LANCZOS))
                ttk.Label(self.lista_sons, image=item["_thumb_som"], style="Cartao.TLabel").grid(
                    row=r, column=0, padx=(8, 2), pady=7)
            nome = item.get("nome") or "(sem nome)"
            ttk.Label(self.lista_sons, text=nome if len(nome) <= 22 else nome[:21] + "…",
                      width=22, style="Cartao.TLabel").grid(row=r, column=1, padx=4, sticky="w")
            ttk.Label(self.lista_sons, text="Skill" if tipo == "skill" else "Buff",
                      style="Cartao.Dica.TLabel", width=5).grid(row=r, column=2, padx=2)
            som = item.get("som", True)
            atual = (SEM_SOM if som is False else
                     sons.nome(som) if isinstance(som, str) and sons.existe(som) else PADRAO)
            var = tk.StringVar(value=atual)
            item["_var_som"] = var
            cb = ttk.Combobox(self.lista_sons, textvariable=var, state="readonly", width=13,
                              values=[PADRAO] + opcoes, style="Cartao.TCombobox")
            cb.grid(row=r, column=3, padx=4, pady=6)
            cb.bind("<<ComboboxSelected>>",
                    lambda _e, i=item, t=tipo, v=var: self._on_som_item(i, t, v))
            self.dica(self.bt(self.lista_sons, "", "play", lambda i=item, t=tipo: self._testar_item(i, t),
                              fundo="Cartao"),
                      "Testar o som desta skill/buff.").grid(row=r, column=4, padx=(2, 8), pady=6)

        for wdg in self.lista_meus.winfo_children():
            wdg.destroy()
        meus = sons.meus()
        faltam = [n for n in SONS_SUGERIDOS if n.lower() not in {m.lower() for m in meus}]
        if faltam:
            sug = ttk.Frame(self.lista_meus)
            sug.pack(fill="x", pady=(0, 4))
            ttk.Label(sug, text="Sugestão:", style="Dica.TLabel").pack(side="left")
            for n in faltam:
                self.dica(self.bt(sug, n, "importar", lambda n=n: self.baixar_do_myinstants(
                    SONS_SUGERIDOS[n], n)), f"Baixa o som \"{n}\" do MyInstants.").pack(side="left", padx=4)
        if not meus:
            ttk.Label(self.lista_meus, style="Dica.TLabel", text="Nenhum som seu ainda.").pack(anchor="w")
        for nome in meus:
            linha = ttk.Frame(self.lista_meus)
            linha.pack(fill="x", pady=1)
            ttk.Label(linha, text=nome).pack(side="left")
            self.dica(self.bt(linha, "", "lixeira", lambda n=nome: self.remover_som(n)),
                      "Remover este som.").pack(side="right")
            self.bt(linha, "", "play", lambda n=nome: sons.tocar(
                "meu:" + n, self.perfil["layout"].get("som_volume", 70), forcar=True)
                    ).pack(side="right", padx=4)

    def _on_som(self, chave, testar=False):
        if self._carregando:
            return
        L = self.perfil["layout"]
        var = self.var_som_skill if chave == "som_skill" else self.var_som_buff
        L[chave] = self.overlay.sons.opcoes().get(var.get())
        self.salvar_depois()
        if testar:
            self.overlay.sons.tocar(L[chave], L.get("som_volume", 70), forcar=True)

    def _on_som_item(self, item, tipo, var):
        escolha = var.get()
        if escolha == PADRAO:
            item.pop("som", None)
        elif escolha == SEM_SOM:
            item["som"] = False
        else:
            item["som"] = self.overlay.sons.opcoes().get(escolha)
        self.salvar_depois()
        self._testar_item(item, tipo)

    def _testar_item(self, item, tipo):
        L = self.perfil["layout"]
        som, vol = item.get("som", True), L.get("som_volume", 70)
        if som is False:
            return
        sons = self.overlay.sons
        if not (isinstance(som, str) and sons.tocar(som, vol, forcar=True)):
            sons.tocar(L.get("som_skill" if tipo == "skill" else "som_buff"), vol, forcar=True)

    def _on_volume(self, val):
        v = int(round(float(val) / 10) * 10)
        self.lbl_vol.config(text=f"{v}%")
        if self._carregando or v == self.perfil["layout"].get("som_volume"):
            return
        self.perfil["layout"]["som_volume"] = v
        self.salvar_depois()
        som = self.perfil["layout"].get("som_skill") or self.perfil["layout"].get("som_buff")
        self.overlay.sons.tocar(som, v)          # amostra (no máximo 1 a cada 0,35 s)

    def adicionar_som(self):
        arq = filedialog.askopenfilename(parent=self.win, title="Escolha um som (MP3 ou WAV)",
                                         filetypes=[("Som (MP3 ou WAV)", "*.mp3 *.wav")])
        if not arq:
            return
        arq = Path(arq)
        if arq.suffix.lower() not in (".mp3", ".wav"):
            messagebox.showerror("Adicionar som", "Use um arquivo .mp3 ou .wav.", parent=self.win)
            return
        nome = nome_seguro(simpledialog.askstring("Adicionar som", "Nome do som:",
                                                  initialvalue=arq.stem, parent=self.win))
        if not nome:
            return
        try:
            dados = arq.read_bytes()
        except Exception as e:
            messagebox.showerror("Adicionar som", f"Não consegui ler o arquivo: {e}", parent=self.win)
            return
        self._instalar_som(nome, dados, arq.suffix.lower(), "Adicionar som")

    def baixar_do_myinstants(self, link=None, nome=None):
        """Baixa um som do MyInstants (em segundo plano) e adiciona aos seus sons."""
        if link is None:
            link = simpledialog.askstring(
                "Som do MyInstants", "Cole o link do som no MyInstants\n"
                "(ex.: https://www.myinstants.com/pt/instant/...):", parent=self.win)
            if not link:
                return
        self.status("Baixando o som do MyInstants…")
        fila = queue.Queue()

        def trabalho():
            try:
                fila.put(("ok", baixar_myinstants(link)))
            except Exception as e:
                fila.put(("erro", e))
        threading.Thread(target=trabalho, daemon=True).start()

        def esperar():
            try:
                tipo, res = fila.get_nowait()
            except queue.Empty:
                self.win.after(150, esperar)
                return
            if tipo == "erro":
                registrar(f"MyInstants: não consegui baixar {link} ({res})")
                self.status("")
                messagebox.showerror("Som do MyInstants", f"Não consegui baixar o som: {res}",
                                     parent=self.win)
                return
            sugerido, dados = res
            final = nome or nome_seguro(simpledialog.askstring(
                "Som do MyInstants", "Nome do som:", initialvalue=nome_seguro(sugerido)[:40],
                parent=self.win))
            if final:
                self._instalar_som(final, dados, ".mp3", "Som do MyInstants")
            else:
                self.status("")
        esperar()

    def _instalar_som(self, nome, dados, ext, titulo):
        """Grava um som novo em meus_sons, confere se ele toca e atualiza a aba Sons."""
        reservados = {SEM_SOM, PADRAO} | {n for n, _, _ in SONS_PRONTOS.values()}
        if nome.lower() in {r.lower() for r in reservados}:
            messagebox.showerror(titulo, f"\"{nome}\" já é o nome de um som do programa. "
                                 "Escolha outro nome.", parent=self.win)
            return
        sons = self.overlay.sons
        igual = next((n for n in sons.meus() if n.lower() == nome.lower()), None)
        if igual:
            if not messagebox.askyesno(titulo, f"Já existe o som \"{igual}\". "
                                       "Trocar pelo novo?", parent=self.win):
                return
            sons.esquecer("meu:" + igual)
            sons.meus()[igual].unlink()
        destino = self._pasta_meus_sons() / (nome + ext)
        try:
            destino.write_bytes(dados)
        except Exception as e:
            messagebox.showerror(titulo, f"Não consegui salvar o som: {e}", parent=self.win)
            return
        if not sons.preparar(["meu:" + nome]):
            destino.unlink(missing_ok=True)
            messagebox.showerror(titulo, "Não consegui tocar esse som. Tente outro "
                                 ".mp3 ou .wav.", parent=self.win)
            return
        sons.tocar("meu:" + nome, self.perfil["layout"].get("som_volume", 70), forcar=True)
        self.montar_sons()
        self.status(f"Som \"{nome}\" adicionado: escolha ele nas listas da aba Sons.")

    def remover_som(self, nome):
        if not messagebox.askyesno("Remover som", f"Remover o som \"{nome}\"? Quem usava ele "
                                   "volta para o som padrão.", parent=self.win):
            return
        sons = self.overlay.sons
        sons.esquecer("meu:" + nome)
        arq = sons.meus().get(nome)
        if arq:
            arq.unlink(missing_ok=True)
        self.montar_sons()
