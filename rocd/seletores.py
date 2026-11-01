"""Janelas de escolha: busca de skill pelo nome e seleção de área na tela."""

import tkinter as tk
from tkinter import ttk

from PIL import ImageTk

from .config import TODAS
from .janelas import barra_escura


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
        barra_escura(top)

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
