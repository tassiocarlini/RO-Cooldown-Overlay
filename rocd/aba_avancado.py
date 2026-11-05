"""Painel, aba Avançado: atualizações, versão antiga e Divine Pride."""

import queue
import threading
import time
import tkinter as tk
import traceback
from tkinter import filedialog, messagebox, ttk

from PIL import ImageTk

from .config import ARQ_APP, PASTA_DP, VERSAO, registrar
from .dados import gravar_json
from .desenho import COR, com_aviso, desenhar_icone
from .perfis import importar_dados_antigos, Perfis, tem_dados_antigos
from .atualizacao import aplicar_atualizacao, buscar_versao_nova, preparar_atualizacao


class AbaAvancado:
    """Métodos do Painel (aba Avançado: atualizações, versão antiga e Divine Pride)."""

    # ---- atualizações

    def _on_auto_at(self):
        self.app_cfg["verificar_atualizacoes"] = bool(self.var_auto_at.get())
        gravar_json(ARQ_APP, self.app_cfg)

    def aviso_atualizacao(self, texto):
        """Texto embaixo do botão de atualizar (a linha só ocupa espaço quando tem algo)."""
        self.lbl_at.config(text=texto)
        if texto and not self.lbl_at.winfo_manager():
            self.lbl_at.pack(anchor="w", padx=8, pady=(0, 6))

    def verificar_atualizacao(self, manual):
        """Consulta o GitHub em segundo plano; se houver versão nova, pergunta se quer instalar."""
        if getattr(self, "_verificando", False):
            return
        self._verificando = True
        if manual:
            self.aviso_atualizacao("Procurando versão nova…")
        fila = queue.Queue()

        def trabalho():
            try:
                fila.put(("ok", buscar_versao_nova()))
            except Exception as e:
                fila.put(("erro", str(e)))
        threading.Thread(target=trabalho, daemon=True).start()

        def esperar():
            try:
                tipo, info = fila.get_nowait()
            except queue.Empty:
                self.win.after(200, esperar)
                return
            self._verificando = False
            self.app_cfg["ultima_verificacao"] = time.time()
            gravar_json(ARQ_APP, self.app_cfg)
            if tipo == "erro":
                registrar(f"Atualização: não consegui consultar ({info})")
                self.aviso_atualizacao(f"Não consegui verificar agora: {info}")
                return
            if info is None:
                self.aviso_atualizacao(f"Você já está na versão mais nova (v{VERSAO}).")
                return
            if info["pendente"]:
                self.aviso_atualizacao(f"A versão {info['tag']} ainda está sendo preparada no "
                                       "GitHub. Tente de novo em alguns minutos.")
                return
            self.aviso_atualizacao(f"Versão nova disponível: {info['tag']}")
            if not manual and info["tag"] == self.app_cfg.get("pular_versao"):
                return
            self._oferecer_atualizacao(info)
        esperar()

    def _oferecer_atualizacao(self, info):
        top = tk.Toplevel(self.win)
        top.title("Atualização disponível")
        top.configure(bg=self.cor_fundo)
        top.transient(self.win)
        top.resizable(False, False)
        f = ttk.Frame(top)
        f.pack(fill="both", expand=True, padx=16, pady=14)
        ttk.Label(f, text=f"Versão nova: {info['tag']}   (você tem a v{VERSAO})",
                  style="Titulo.TLabel").pack(anchor="w")
        notas = info["notas"] or "Sem descrição."
        if len(notas) > 900:
            notas = notas[:900].rstrip() + "…"
        ttk.Label(f, text=notas, wraplength=460, justify="left").pack(anchor="w", pady=(8, 10))
        ttk.Label(f, style="Dica.TLabel", wraplength=460, justify="left",
                  text="O programa baixa a versão nova, fecha e abre de novo sozinho. "
                       "Seus perfis, buffs e configurações continuam como estão.").pack(anchor="w")
        lb = ttk.Frame(f)
        lb.pack(fill="x", pady=(12, 0))

        def pular():
            self.app_cfg["pular_versao"] = info["tag"]
            gravar_json(ARQ_APP, self.app_cfg)
            top.destroy()

        def atualizar():
            top.destroy()
            self._instalar_atualizacao(info)
        self.bt(lb, "Atualizar agora", "check", atualizar, amarelo=True).pack(side="left")
        self.bt(lb, "Depois", "fechar", top.destroy).pack(side="left", padx=6)
        self.bt(lb, "Pular esta versão", "lixeira", pular).pack(side="right")
        top.update_idletasks()
        x = self.win.winfo_rootx() + (self.win.winfo_width() - top.winfo_width()) // 2
        y = self.win.winfo_rooty() + 80
        top.geometry(f"+{max(0, x)}+{max(0, y)}")
        top.lift()

    def _instalar_atualizacao(self, info):
        fila = queue.Queue()
        self.aviso_atualizacao("Baixando a atualização… 0%")
        self.status(f"Baixando a versão {info['tag']}…")

        def trabalho():
            try:
                tmp, origem = preparar_atualizacao(
                    info, progresso=lambda f: fila.put(("prog", f)))
                fila.put(("pronto", (tmp, origem)))
            except Exception as e:
                fila.put(("erro", str(e)))
        threading.Thread(target=trabalho, daemon=True).start()

        def esperar():
            try:
                while True:
                    tipo, dado = fila.get_nowait()
                    if tipo == "prog":
                        self.aviso_atualizacao(f"Baixando a atualização… {int(dado * 100)}%")
                        continue
                    if tipo == "erro":
                        registrar(f"Atualização falhou: {dado}")
                        self.aviso_atualizacao(f"A atualização falhou: {dado}")
                        messagebox.showerror(
                            "Atualização", f"Não consegui atualizar: {dado}\n\nVocê pode baixar a "
                            f"versão nova à mão em:\n{info['pagina']}", parent=self.win)
                        return
                    tmp, origem = dado
                    self.aviso_atualizacao("Instalando e reiniciando…")
                    self.salvar_agora()
                    gravar_json(ARQ_APP, self.app_cfg)
                    registrar(f"Atualizando de v{VERSAO} para {info['tag']}.")
                    aplicar_atualizacao(tmp, origem)
                    self.root.after(300, self.sair)
                    return
            except queue.Empty:
                self.win.after(150, esperar)
        esperar()

    def importar_versao_antiga(self):
        pasta = filedialog.askdirectory(parent=self.win, title="Pasta da versão antiga "
                                        "(onde fica o ro_cooldown_overlay.py)")
        if not pasta:
            return
        if not tem_dados_antigos(pasta):
            messagebox.showwarning("Versão antiga", "Não achei perfis nessa pasta.\nEscolha a "
                                   "pasta onde fica o ro_cooldown_overlay.py.", parent=self.win)
            return
        try:
            tinha_chave = self.app_cfg.get("dp_chave")
            copiados = importar_dados_antigos(pasta, self.app_cfg)
            self.app_cfg["importou_versao_python"] = pasta
            gravar_json(ARQ_APP, self.app_cfg)
            if self.app_cfg.get("dp_chave") and not tinha_chave:
                self.var_dp.set(self.app_cfg["dp_chave"])
                self.testar_dp()                          # liga e testa a chave
        except Exception as e:
            registrar("Erro ao importar a versão antiga:\n" + traceback.format_exc())
            messagebox.showerror("Versão antiga", f"Não consegui copiar: {e}", parent=self.win)
            return
        self.cb_perfil["values"] = Perfis.listar()
        if copiados:
            self.nome = None                              # não salvar por cima do copiado
            self.trocar_perfil(copiados[0])
            self.status(f"{len(copiados)} perfil(is) copiado(s): {', '.join(copiados)}. "
                        "Perfis mais velhos com o mesmo nome ficaram como \"(antigo)\".")
        else:
            self.status("Nada novo para copiar: os perfis daqui são iguais ou mais novos.")

    def _on_rag(self):
        self.rag.ligado = bool(self.var_rag.get())
        self.app_cfg["usar_ragassets"] = self.rag.ligado
        gravar_json(ARQ_APP, self.app_cfg)
        if self.rag.ligado:
            self.rag._fora_ate = 0.0
            self.rag.pedir("nomes", None, "nomes")

    def atualizar_aba_avancado(self):
        """Bolinha vermelha no ícone da aba Avançado enquanto a chave da Divine Pride não estiver
        configurada."""
        if not hasattr(self, "aba_av"):
            return
        if self.dp.ativo():
            self.abas.tab(self.aba_av, **self.aba("Avançado", "chave"))
            return
        if not hasattr(self, "_ic_av_aviso"):
            self._ic_av_aviso = [ImageTk.PhotoImage(com_aviso(desenhar_icone("chave", cor, 16),
                                                              COR["vermelho"]))
                                 for cor in (COR["mudo"], COR["ouro"])]
        normal, aberta = self._ic_av_aviso
        self.abas.tab(self.aba_av, text=" Avançado", compound="left",
                      image=(normal, "selected", aberta))

    def texto_chave_dp(self):
        if self.dp.usando_padrao():
            return "Usando a chave do aplicativo ✓ (pode pôr a sua, se quiser)"
        return "Chave salva (a sua)." if self.dp.chave else ""

    def testar_dp(self):
        self.dp.chave = self.var_dp.get().strip()
        self.app_cfg["dp_chave"] = self.dp.chave
        gravar_json(ARQ_APP, self.app_cfg)
        self.atualizar_aba_avancado()
        if not self.dp.ativo():
            self.lbl_dp.config(text="Sem chave: usando só o banco local.")
            return
        if self.dp.usando_padrao():
            self.status("Campo vazio: usando a chave do aplicativo.")
        (PASTA_DP / "skill_28.json").unlink(missing_ok=True)      # força consulta real
        self.dp.pedir(28, "teste")
        self.lbl_dp.config(text="Testando…")
