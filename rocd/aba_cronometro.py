"""Painel, aba Utilidades (cronômetro do recall e último local)."""

import tkinter as tk
from tkinter import ttk

from .dados import fmt_contagem, ler_tempo
from .desenho import COR


class AbaCronometro:
    """Métodos do Painel (aba Utilidades)."""

    def _montar_aba_cronometro(self, aba):
        cr = self.cronometro
        cfg = cr.cfg
        # cada recurso numa caixa; a aba rola quando não cabe tudo na janela
        f = self.lista_rolavel(aba, padx=4, pady=6)
        f.columnconfigure(0, weight=1)
        fc = self._caixa(f, 0, "Cronômetro do recall")
        fc.columnconfigure(1, weight=1)          # sobra de largura vai para os campos, não rótulos

        self.var_crono = tk.BooleanVar(value=bool(cfg["ligado"]))
        c = ttk.Checkbutton(fc, text="Mostrar o cronômetro na tela", variable=self.var_crono,
                            command=self._on_crono)
        c.grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(6, 0))
        self.dica(c, "Uma caixinha só dele, por cima do jogo e separada das skills e buffs. "
                     "Aparece mesmo com o overlay parado.")

        self.var_crono_tempo = tk.StringVar(value=fmt_contagem(cfg["tempo"]))
        self.var_crono_aviso = tk.StringVar(value=f"{cfg['aviso']:g}")
        self.var_crono_tam = tk.DoubleVar(value=cfg["tamanho"])

        def lista_som(pai, chave):
            var = tk.StringVar(value=self.overlay.sons.nome(cfg.get(chave)))
            cb = ttk.Combobox(pai, textvariable=var, state="readonly", width=22,
                              postcommand=lambda: cb.configure(
                                  values=list(self.overlay.sons.opcoes())))
            cb.bind("<<ComboboxSelected>>", lambda _e: self._on_crono_som(chave, var))
            return cb

        # rótulo à esquerda; o campo e o que vem depois dele (unidade, botão) juntos à direita
        for linha, (rotulo, criar, depois, ajuda) in enumerate((
                ("Tempo", lambda p: ttk.Entry(p, textvariable=self.var_crono_tempo, width=8), "",
                 "Quanto tempo contar a cada reinício. Ex.: 300, 3:00 ou 4:30."),
                ("Avisar quando faltar",
                 lambda p: ttk.Spinbox(p, from_=1, to=600, increment=1, width=6,
                                       textvariable=self.var_crono_aviso), "segundos",
                 "Nos últimos segundos os números piscam em vermelho e amarelo."),
                ("Som faltando pouco", lambda p: lista_som(p, "som_aviso"), "som_aviso",
                 "Toca quando faltam os segundos acima. \"Sem som\" = não toca."),
                ("Som ao zerar", lambda p: lista_som(p, "som_fim"), "som_fim",
                 "Toca quando a contagem chega a zero. \"Sem som\" = não toca."),
                ("Tamanho da caixa",
                 lambda p: ttk.Scale(p, from_=cr.TAM_MIN, to=cr.TAM_MAX, orient="horizontal",
                                     length=220, variable=self.var_crono_tam,
                                     command=self._on_crono_tam), "tamanho",
                 "Altura dos números; a caixa cresce junto. A roda do mouse em cima do "
                 "cronômetro faz o mesmo.")), start=1):
            ttk.Label(fc, text=rotulo, style="Campo.TLabel").grid(
                row=linha, column=0, sticky="w", padx=(8, 16), pady=(8, 0))
            cel = ttk.Frame(fc)
            cel.grid(row=linha, column=1, sticky="w", pady=(8, 0))
            widget = criar(cel)
            widget.pack(side="left")
            if depois.startswith("som_"):
                self.dica(self.bt(cel, "", "play", lambda q=depois: cr.tocar(q)),
                          "Testar: toca o som escolhido (volume da aba Sons).").pack(
                    side="left", padx=4)
            elif depois == "tamanho":
                self.lbl_crono_tam = ttk.Label(cel, text=f"{cfg['tamanho']} px")
                self.lbl_crono_tam.pack(side="left", padx=8)
            elif depois:
                ttk.Label(cel, text=depois).pack(side="left", padx=8)
            self.dica(widget, ajuda)
        self.var_crono_tempo.trace_add("write", lambda *_: self._on_crono_tempo())
        self.var_crono_aviso.trace_add("write", lambda *_: self._on_crono_aviso())

        lb = ttk.Frame(fc)
        lb.grid(row=6, column=0, columnspan=2, sticky="w", padx=8, pady=(12, 4))
        self.dica(self.bt(lb, "Play / Pausar", "play", cr.play_pausa),
                  "Pausa a contagem ou continua de onde parou; parado ou zerado, começa do "
                  "tempo cheio (o mesmo que o botão verde do cronômetro)."
                  ).pack(side="left")
        self.dica(self.bt(lb, "Reiniciar agora", "reiniciar", cr.reiniciar, amarelo=True),
                  "Começa a contagem do zero (o mesmo que o botão dourado do cronômetro)."
                  ).pack(side="left", padx=(6, 0))
        self.dica(self.bt(lb, "Voltar para o alto da tela", "centro", cr.centralizar),
                  "Põe o cronômetro de novo no alto, no meio da tela.").pack(side="left", padx=6)
        ttk.Label(fc, style="Dica.TLabel", wraplength=760, justify="left",
                  text="Na tela: o botão verde inicia e pausa, o dourado reinicia; arraste o resto da caixa "
                       "para mudar de lugar e use a roda do mouse para aumentar ou diminuir. "
                       "Clicar nele não tira o foco do jogo."
                  ).grid(row=7, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 8))
        self._montar_ultimo_local(f)

    def _caixa(self, pai, linha, titulo):
        """Seção com borda em volta (uma por recurso da aba)."""
        borda = tk.Frame(pai, bg=self.cor_fundo, highlightthickness=1,
                         highlightbackground=COR["borda2"], bd=0)
        borda.grid(row=linha, column=0, sticky="ew", padx=(0, 6), pady=(0, 10))
        sec = ttk.LabelFrame(borda, text=titulo)
        sec.pack(fill="x", padx=8, pady=6)
        return sec

    # ---- Último local (Last Spot)

    def _montar_ultimo_local(self, f):
        ul = self.ultimo_local
        fu = self._caixa(f, 1, "Último local (Last Spot)")
        self.var_ultimo = tk.BooleanVar(value=bool(ul.cfg["ligado"]))
        c = ttk.Checkbutton(fu, text="Marcar no mini mapa com um X onde eu estava antes de teleportar",
                            variable=self.var_ultimo, command=self._on_ultimo)
        c.pack(anchor="w", padx=8, pady=(6, 0))
        self.dica(c, "Funciona mesmo com o overlay parado. Precisa do mini mapa aberto no jogo.")
        lt = ttk.Frame(fu)
        lt.pack(anchor="w", padx=8, pady=(8, 0))
        ttk.Label(lt, text="Tamanho do X", style="Campo.TLabel").pack(side="left", padx=(0, 16))
        self.var_ultimo_tam = tk.DoubleVar(value=ul.cfg["tamanho"])
        esc = ttk.Scale(lt, from_=ul.TAM_MIN, to=ul.TAM_MAX, orient="horizontal", length=220,
                        variable=self.var_ultimo_tam, command=self._on_ultimo_tam)
        esc.pack(side="left")
        self.dica(esc, "Largura do X no mini mapa, em pixels.")
        self.lbl_ultimo_tam = ttk.Label(lt, text=f"{ul.cfg['tamanho']} px")
        self.lbl_ultimo_tam.pack(side="left", padx=8)
        lb = ttk.Frame(fu)
        lb.pack(anchor="w", padx=8, pady=(10, 4))
        self.dica(self.bt(lb, "Marcar mini mapa", "selecao", self.marcar_minimapa),
                  "Arraste um retângulo bem em cima do mini mapa (só o quadrado do mapa). "
                  "Sem marcar, o programa usa o canto de cima, à direita, do jogo.").pack(side="left")
        self.dica(self.bt(lb, "Apagar o X", "lixeira", self.apagar_ultimo_local, perigo=True),
                  "Tira o X do mini mapa até o próximo teleporte.").pack(side="left", padx=6)
        self.lbl_ultimo_area = ttk.Label(lb)
        self.lbl_ultimo_area.pack(side="left", padx=8)
        self._atualizar_ultimo_area()
        ttk.Label(fu, style="Dica.TLabel", wraplength=760, justify="left",
                  text="X verde: você está no mesmo mapa (ex.: depois da Asa de Mosca). X vermelho: você "
                       "está em outro mapa; o X fica guardado até você voltar. O programa acha você pela "
                       "seta branca do mini mapa: só olha a tela."
                  ).pack(anchor="w", padx=8, pady=(0, 8))

    def _atualizar_ultimo_area(self):
        marcada = bool(self.ultimo_local.cfg.get("area"))
        self.lbl_ultimo_area.config(text="Mini mapa marcado ✓" if marcada else "Mini mapa: canto do jogo")

    def _on_ultimo(self):
        self.ultimo_local.cfg["ligado"] = bool(self.var_ultimo.get())
        self.ultimo_local.salvar()

    def _on_ultimo_tam(self, val):
        T = int(round(float(val)))
        self.lbl_ultimo_tam.config(text=f"{T} px")
        if T != self.ultimo_local.cfg["tamanho"]:
            self.ultimo_local.cfg["tamanho"] = T
            self.ultimo_local.salvar()

    def apagar_ultimo_local(self):
        self.ultimo_local.apagar()
        self.status("X do último local apagado.")

    def marcar_minimapa(self):
        def pronto(regioes, tela, mon):
            if not regioes:
                return
            x0, y0, w, h = regioes[-1]
            self.ultimo_local.cfg["area"] = {"x": x0 + mon["left"], "y": y0 + mon["top"], "w": w, "h": h,
                                             "origem": self.overlay.origem_agora()}
            self.ultimo_local.salvar()
            self.ultimo_local.apagar()          # o X antigo era de outra área
            self._atualizar_ultimo_area()
            self.status("Mini mapa marcado.")
        self._capturar_com_contagem(
            "Mostre o jogo com o mini mapa aberto",
            "Arraste um retângulo bem em cima do mini mapa (só o quadrado do mapa)", pronto)

    def sincronizar_cronometro(self):
        """O tamanho mudou pela roda do mouse no cronômetro: acompanha na aba."""
        T = self.cronometro.cfg["tamanho"]
        self.var_crono_tam.set(T)
        self.lbl_crono_tam.config(text=f"{T} px")

    def _on_crono_tam(self, val):
        T = int(round(float(val) / 2) * 2)
        self.lbl_crono_tam.config(text=f"{T} px")
        if T != self.cronometro.cfg["tamanho"]:
            self.cronometro.mudar_tamanho(T)

    def _on_crono(self):
        self.cronometro.cfg["ligado"] = bool(self.var_crono.get())
        self.cronometro.salvar()

    def _on_crono_tempo(self):
        v, ok = ler_tempo(self.var_crono_tempo.get())
        if ok and v:
            self.cronometro.cfg["tempo"] = v
            self.cronometro.salvar()

    def _on_crono_aviso(self):
        try:
            v = float(self.var_crono_aviso.get().replace(",", "."))
        except ValueError:
            return
        if v >= 0:
            self.cronometro.cfg["aviso"] = v
            self.cronometro.salvar()

    def _on_crono_som(self, chave, var):
        self.cronometro.cfg[chave] = self.overlay.sons.opcoes().get(var.get())
        self.cronometro.salvar()
        self.cronometro.tocar(chave)
