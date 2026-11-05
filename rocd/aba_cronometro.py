"""Painel, aba Cronômetro (contagem do recall)."""

import tkinter as tk
from tkinter import ttk

from .dados import fmt_contagem, ler_tempo


class AbaCronometro:
    """Métodos do Painel (aba Cronômetro)."""

    def _montar_aba_cronometro(self, aba):
        cr = self.cronometro
        cfg = cr.cfg
        f = ttk.Frame(aba)
        f.pack(fill="both", expand=True, padx=4, pady=6)
        fc = ttk.LabelFrame(f, text="Cronômetro do recall")
        fc.pack(fill="x")
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
        self.dica(self.bt(lb, "Reiniciar agora", "reiniciar", cr.reiniciar, amarelo=True),
                  "Começa a contagem do zero (o mesmo que o botão redondo do cronômetro)."
                  ).pack(side="left")
        self.dica(self.bt(lb, "Voltar para o alto da tela", "centro", cr.centralizar),
                  "Põe o cronômetro de novo no alto, no meio da tela.").pack(side="left", padx=6)
        ttk.Label(fc, style="Dica.TLabel", wraplength=760, justify="left",
                  text="Na tela: clique no botão redondo para reiniciar, arraste o resto da caixa "
                       "para mudar de lugar e use a roda do mouse para aumentar ou diminuir. "
                       "Clicar nele não tira o foco do jogo."
                  ).grid(row=7, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 8))

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
