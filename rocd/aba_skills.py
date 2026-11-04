"""Painel, aba Skills ofensivas: lista, busca, Divine Pride e marcar ícones na tela."""

import os
import queue
import time
import tkinter as tk
import traceback
from tkinter import messagebox, ttk

from PIL import Image, ImageTk

from .config import ARQ_APP, PASTA, TODAS, registrar
from .janelas import nova_captura
from .dados import chave, fmt_aprendido, fmt_tempo, gravar_json, ler_tempo
from .sites import icone_dp_rgb
from .seletores import Seletor, SeletorSkill
from .perfis import Perfis


class AbaSkills:
    """Métodos do Painel (aba Skills ofensivas: lista, busca, Divine Pride e marcar ícones)."""

    # ---- lista de skills

    def montar_lista(self):
        for wdg in self.lista.winfo_children():
            wdg.destroy()
        for col, t in enumerate(("", "SKILL", "", "RECARGA (S)", "APRENDIDO", "ESTADO", "")):
            ttk.Label(self.lista, text=t, style="Titulo.TLabel").grid(
                row=0, column=col, padx=4, sticky="w")
        skills = self.perfil["skills"]
        if not skills:
            ttk.Label(self.lista, justify="left", text=(
                "Primeiros passos:\n"
                "  1. Abra o Ragnarok em modo janela (ou janela sem bordas).\n"
                "  2. Clique em \"Marcar ícones na tela\" e arraste um quadrado sobre cada skill\n"
                "      da sua barra de atalhos (com as skills prontas, sem delay).\n"
                "  3. Clique em \"Buscar\" em cada linha para escolher o nome da skill.\n"
                "  4. Clique em \"Iniciar overlay\" e jogue!")
                      ).grid(row=1, column=0, columnspan=7, pady=12, padx=6, sticky="w")
            return
        for i, sk in enumerate(skills):
            r = i + 1
            self.cartao(self.lista, r, 7)
            sk["_thumb"] = ImageTk.PhotoImage((sk.get("_visual") or sk["_ref_full"]).resize(
                (28, 28), Image.LANCZOS))
            ttk.Label(self.lista, image=sk["_thumb"], style="Cartao.TLabel").grid(
                row=r, column=0, padx=(10, 4), pady=9)

            vn = tk.StringVar(value=sk.get("nome") or "")
            en = ttk.Entry(self.lista, textvariable=vn, width=22, style="Cartao.TEntry")
            en.grid(row=r, column=1, padx=(4, 0))
            vn.trace_add("write", lambda *_, s=sk, v=vn: self._on_nome(s, v))
            if self.banco.eh_buff(sk.get("nome", "")):
                # buff colocado aqui antes da separação: avisa e oferece mudar de aba
                en.state(["invalid"])
                self.dica(self.bt(self.lista, "Para Buffs", "escudo",
                                  lambda k=i: self.mover_para_buffs(k), perigo=True,
                                  fundo="Cartao"),
                          f"{sk['nome']} é buff, não skill ofensiva: a recarga não é o tempo "
                          "do buff. Clique para mover para a aba Buffs."
                          ).grid(row=r, column=2, padx=(4, 4))
            else:
                self.dica(self.bt(self.lista, "Buscar", "lupa", lambda s=sk: SeletorSkill(self, s),
                                  fundo="Cartao"),
                          "Escolher o nome desta skill no banco (a recarga vem junto)."
                          ).grid(row=r, column=2, padx=(4, 4))

            vc = tk.StringVar(value=fmt_tempo(sk.get("cd")))
            ec = ttk.Entry(self.lista, textvariable=vc, width=7, justify="center",
                           style="Cartao.TEntry")
            ec.grid(row=r, column=3, padx=4)
            vc.trace_add("write", lambda *_, s=sk, v=vc, e=ec: self._on_cd(s, v, e))
            sk["_vars"] = (vn, vc)

            sk["_lbl_apr"] = ttk.Label(self.lista, text=fmt_aprendido(sk), width=10,
                                       style="Cartao.Dica.TLabel")
            sk["_lbl_apr"].grid(row=r, column=4, padx=4)
            sk["_lbl_est"] = ttk.Label(self.lista, text="—", width=14, style="Cartao.TLabel",
                                       font=("Segoe UI", 9, "bold"))
            sk["_lbl_est"].grid(row=r, column=5, padx=4)

            fb = ttk.Frame(self.lista, style="Cartao.TFrame")
            fb.grid(row=r, column=6, padx=(4, 10))
            self.bt(fb, "", "cima", lambda k=i: self.mover_skill(k, -1), fundo="Cartao").pack(side="left")
            self.bt(fb, "", "baixo", lambda k=i: self.mover_skill(k, 1), fundo="Cartao").pack(side="left")
            self.bt(fb, "", "lixeira", lambda k=i: self.remover_skill(k), fundo="Cartao").pack(
                side="left", padx=(4, 0))

    def _on_nome(self, sk, var):
        sk["nome"] = var.get()
        if self.banco.eh_buff(sk["nome"]):
            self.status(f"{sk['nome']} é buff: coloque na aba Buffs, não em Skills ofensivas.")
        # Nome digitado igual a uma skill do banco e recarga vazia: preenche sozinho
        elif not self._preenchendo and sk.get("cd") is None:
            cd, _ = self.banco.recarga(sk["nome"])
            if cd:
                self._preencher_cd(sk, cd)
        self.salvar_depois()

    def _on_cd(self, sk, var, entry):
        v, ok = ler_tempo(var.get())
        try:
            entry.state(["!invalid"] if ok else ["invalid"])
        except tk.TclError:
            pass
        if ok:
            sk["cd"] = v
            if not self._preenchendo:
                self.banco.salvar_meu(sk.get("nome", ""), v)   # lembra para outros perfis
            self.salvar_depois()

    def _preencher_cd(self, sk, cd):
        self._preenchendo = True
        try:
            sk["_vars"][1].set(fmt_tempo(cd))
        finally:
            self._preenchendo = False

    def aplicar_skill(self, sk, nome):
        """Chamado pela janela de busca."""
        self._preenchendo = True
        try:
            sk["_vars"][0].set(nome)
        finally:
            self._preenchendo = False
        sk["id"] = self.banco.id_de(nome)
        cd, _ = self.banco.recarga(nome)
        if cd:
            self._preencher_cd(sk, cd)
        if sk["id"] and self.dp.ativo():
            self.dp.pedir(sk["id"], "cd")
        self.status(f"{nome}: recarga {fmt_tempo(cd) + ' s' if cd else 'não cadastrada (vai aprender sozinho)'}.")

    def adicionar_por_nome(self, nome):
        """Nova skill sem marcar: o ícone vem da Divine Pride e o programa acha na tela."""
        sid = self.banco.id_de(nome)
        cd, _ = self.banco.recarga(nome)
        self.perfil["skills"].append({"nome": nome, "id": sid, "x": None, "y": None,
                                      "w": 24, "h": 24, "icone": None, "cd": cd,
                                      "aprendido": None})
        self.salvar_agora()
        self.overlay.carregar_perfil(self.perfil, Perfis.pasta(self.nome))
        self.montar_lista()
        if not sid:
            self.status(f"{nome}: sem código da skill; use \"Marcar ícones na tela\" para ela.")
        elif self.icone_skill(sid):
            self._procurar_skill_nova()
            self.status(f"{nome} adicionada. Procurando na tela…")
        elif self.rag.disponivel():
            self.rag.pedir("skill", sid, "buscar")
            if self.dp.ativo():
                self.dp.pedir(sid, "cd")                     # recarga LATAM continua vindo da DP
            self.status(f"{nome} adicionada. Baixando ícone e procurando na tela…")
        elif self.dp.ativo():
            self.dp.pedir(sid, "buscar")
            self.status(f"{nome} adicionada. Baixando ícone e procurando na tela…")
        else:
            self.status(f"{nome} adicionada, mas não consegui baixar o ícone agora. "
                        "Use \"Adicionar mais\" para marcá-la na tela.")

    def atualizar_icones_buffs(self):
        """Buffs criados "pelo nome" antes do ragassets: as versões ainda não confirmadas na
        tela (vindas da Divine Pride) são trocadas pelos ícones do cliente LATAM (os que vêm
        dentro do programa ou os do ragassets)."""
        for bf in self.perfil.get("buffs", []):
            if not bf.get("efst") or not any(v.startswith("buff_site_")
                                             for v in bf.get("variantes", [])):
                continue
            faltam = [(k, e) for k, e in bf["efst"] if not self.rag.icone_status(e)]
            if not faltam:
                self._trocar_icones_site(bf)
            elif self.rag.disponivel():
                for k, e in faltam:
                    self.rag.pedir("status", e, ("refresh", id(bf), k))

    def _trocar_icones_site(self, bf):
        pasta = Perfis.pasta(self.nome)
        trocou = 0
        for v in bf.get("variantes", []):
            if not v.startswith("buff_site_"):
                continue
            try:
                i = int(v.rsplit("_", 1)[1].split(".")[0])
                eid = bf["efst"][i][1]
            except (ValueError, IndexError, KeyError):
                continue
            p = self.rag.icone_status(eid)
            if not p or not (pasta / v).exists():
                continue
            antigo = Image.open(pasta / v).convert("RGB")
            novo = icone_dp_rgb(p).resize(antigo.size, Image.NEAREST)
            if novo.tobytes() == antigo.tobytes():
                continue                                   # já é o ícone do ragassets
            novo.save(pasta / v)
            trocou += 1
        if trocou:
            registrar(f"{bf.get('nome')}: {trocou} ícone(s) trocados pelos do ragassets.")
            self.overlay.carregar_perfil(self.perfil, pasta)
            self.montar_buffs()

    def _procurar_skill_nova(self):
        self.overlay.carregar_perfil(self.perfil, Perfis.pasta(self.nome))
        self.montar_lista()
        if not self.overlay.ativo:
            self.iniciar()
        self.overlay.procurar_todos()
        self.overlay.busca_manual = True

    def _processar_rag(self):
        """Respostas do ragassets. Se falhar, pede a mesma coisa à Divine Pride (fallback)."""
        while True:
            try:
                item = self.rag.fila.get_nowait()
            except queue.Empty:
                break
            tipo_r, tipo, ident, motivo = item[:4]
            if tipo == "nomes":
                if tipo_r == "ok":
                    self.atualizar_icones_buffs()
                    n = self.banco.aplicar_nomes(self.rag.nomes)
                    if n:
                        self._nomes_recebidos += n
                        self.status(f"Nomes em português do cliente LATAM: {n} skill(s) atualizadas.")
                else:
                    self.pedir_nomes(self.var_classe.get())   # fallback: Divine Pride
                continue
            if tipo in ("skill", "status") and isinstance(motivo, tuple) and motivo[0] == "visual":
                if tipo_r == "ok":                          # ícone oficial para mostrar
                    self._icone_oficial_chegou()
                else:                                       # o ragassets não tem: Divine Pride
                    self.pedir_icone_dp(tipo, ident, motivo)
                continue
            if tipo == "status" and isinstance(motivo, tuple):
                bf = next((b for b in self.perfil.get("buffs", []) if id(b) == motivo[1]), None)
                if bf is not None:
                    bf.get("_rag_pend", set()).discard(ident)
                if tipo_r == "ok":
                    if not self.rag.nomes and not getattr(self, "_rag_nomes_pedidos", False):
                        self._rag_nomes_pedidos = True       # voltou a responder: pega nomes/recargas
                        self.rag.pedir("nomes", None, "nomes")
                    if bf is not None and motivo[0] == "refresh":
                        if all(self.rag.icone_status(e) for _, e in bf["efst"]):
                            self._trocar_icones_site(bf)
                    elif bf is not None:
                        self.montar_buffs()
                elif self.icone_buff(ident):
                    pass                                   # já tem o da Divine Pride guardado
                elif self.dp.ativo():
                    self.dp.pedir_efst(ident, motivo[2], ("buff", motivo[1]))
                else:
                    self.status("Não consegui baixar um ícone do buff (ragassets fora e sem chave "
                                "da Divine Pride). Use \"Marcar na tela\" para este buff.")
                continue
            if tipo == "skill":
                if tipo_r == "ok":
                    self._procurar_skill_nova()
                elif self.dp.ativo():
                    self.dp.pedir(ident, "buscar")
                else:
                    self.status("Não consegui baixar o ícone da skill agora. Use "
                                "\"Adicionar mais\" para marcá-la na tela.")
        if hasattr(self, "lbl_rag"):
            self.lbl_rag.config(text=("desligado" if not self.rag.ligado else self.rag.estado))

    def ajuda_dp(self):
        messagebox.showinfo(
            "Chave da API da Divine Pride",
            "1. Crie uma conta grátis em divine-pride.net (botão Register, no topo).\n"
            "2. Entre na conta (Login).\n"
            "3. Abra seu perfil: divine-pride.net/account/profile\n"
            "4. Copie o campo \"API Key\" (se houver um botão para gerar, clique nele antes).\n"
            "5. Cole aqui no campo \"Chave da API\" e clique em \"Salvar e testar\".\n\n"
            "A chave é pessoal: não compartilhe a sua.\n\n"
            "Ao clicar em OK, a página do seu perfil abre no navegador.",
            parent=self.win)
        import webbrowser
        webbrowser.open("https://www.divine-pride.net/account/profile")

    def _sid(self, sk):
        if not sk.get("id"):
            sk["id"] = self.banco.id_de(sk.get("nome", ""))
        return sk.get("id")

    def pedir_icone_dp(self, tipo, ident, motivo):
        """Ícone oficial pela Divine Pride (só com a chave da API)."""
        if not self.dp.ativo():
            return
        if tipo == "status" and motivo[2]:
            self.dp.pedir_efst(ident, motivo[2], motivo)
        elif tipo == "skill":
            self.dp.pedir(ident, motivo)

    def _icone_oficial_chegou(self):
        self.overlay.preparar_imagens()
        self.montar_lista()
        self.montar_buffs()

    def _processar_dp(self):
        while True:
            try:
                tipo, sid, info, motivo, nome_site = self.dp.fila.get_nowait()
            except queue.Empty:
                return
            if isinstance(motivo, tuple) and motivo[0] == "visual":
                if tipo == "ok":
                    self._icone_oficial_chegou()
                continue
            if motivo == "nome":
                if tipo == "ok" and self.banco.definir_nome(sid, nome_site):
                    self._nomes_recebidos += 1
                    if self.dp.pedidos.empty():
                        self.status(f"Nomes em português atualizados ({self._nomes_recebidos}).")
                continue
            if isinstance(motivo, tuple) and motivo[0] == "buff":
                bf = next((b for b in self.perfil.get("buffs", []) if id(b) == motivo[1]), None)
                if tipo == "erro":
                    self.status(f"Divine Pride: {info}. Use \"Marcar na tela\" para este buff.")
                elif bf is not None:
                    self.montar_buffs()
                continue
            if motivo == "teste":
                if tipo == "ok":
                    self.lbl_dp.config(text="Conectado ✓ Buscando recargas das suas skills…")
                    self.pedir_nomes(self.var_classe.get())
                    for sk in self.perfil["skills"]:
                        if self._sid(sk):
                            self.dp.pedir(sk["id"], "cd")
                else:
                    self.lbl_dp.config(text=f"Erro: {info}")
                continue
            if tipo == "erro":
                self.status(f"Divine Pride: {info}")
                continue
            alvo = [sk for sk in self.perfil["skills"] if self._sid(sk) == sid]
            for sk in alvo:
                # só troca se você não tiver posto um valor seu
                padrao = self.banco.recarga_padrao(sk.get("nome", ""))
                meu = self.banco.meus.get(chave(sk.get("nome", "")))
                if info and not meu and sk.get("cd") in (None, padrao) and "_vars" in sk:
                    self._preencher_cd(sk, info)
            if motivo == "buscar" and alvo:
                self.overlay.carregar_perfil(self.perfil, Perfis.pasta(self.nome))
                self.montar_lista()
                if not self.overlay.ativo:
                    self.iniciar()
                self.overlay.procurar_todos()
                self.overlay.busca_manual = True
            if info and alvo:
                self.status(f"{alvo[0].get('nome')}: recarga LATAM (Divine Pride) = {fmt_tempo(info)} s.")

    def _on_classe(self):
        self.perfil["classe"] = self.var_classe.get()
        self.salvar_depois()
        self.pedir_nomes(self.perfil["classe"])

    def pedir_nomes(self, classe):
        """Pede à Divine Pride o nome em português das skills da classe que ainda não têm."""
        if self.rag.nomes:
            self.banco.aplicar_nomes(self.rag.nomes)
        if not self.dp.ativo() or not classe or classe == TODAS:
            return
        faltam = [sid for sid in self.banco.sem_nome_pt(classe) if sid not in self._nomes_pedidos]
        for sid in faltam:
            self._nomes_pedidos.add(sid)
            self.dp.pedir(sid, "nome")
        if faltam:
            self.status(f"Baixando da Divine Pride o nome em português de {len(faltam)} "
                        f"skill(s) de {classe}…")

    def mover_skill(self, k, d):
        skills = self.perfil["skills"]
        j = k + d
        if 0 <= j < len(skills):
            skills[k], skills[j] = skills[j], skills[k]
            self.montar_lista()
            self.overlay.preview()
            self.salvar_depois()

    def mover_para_buffs(self, k):
        """Tira o buff da aba Skills ofensivas e o adiciona na aba Buffs pelo nome."""
        nome = self.perfil["skills"][k].get("nome", "")
        if not messagebox.askyesno(
                "Mover para Buffs",
                f"{nome} é buff. Tirar de Skills ofensivas e colocar na aba Buffs?\n\n"
                "Na aba Buffs o programa avisa quando o buff acaba (e não a recarga).",
                parent=self.win):
            return
        self.perfil["skills"].pop(k)
        self.salvar_agora()
        self.overlay.carregar_perfil(self.perfil, Perfis.pasta(self.nome))
        self.montar_lista()
        if not any(b.get("nome") == nome for b in self.perfil.get("buffs", [])):
            self.adicionar_buff_por_nome(nome)
        else:
            self.status(f"{nome} já estava na aba Buffs.")

    def remover_skill(self, k):
        sk = self.perfil["skills"][k]
        if not messagebox.askyesno("Remover", f"Remover \"{sk.get('nome')}\"?", parent=self.win):
            return
        if sk.get("icone"):
            (Perfis.pasta(self.nome) / sk["icone"]).unlink(missing_ok=True)
        self.perfil["skills"].pop(k)
        self.overlay.carregar_perfil(self.perfil, Perfis.pasta(self.nome))
        self.montar_lista()
        if not self.perfil["skills"]:
            self.parar()
        self.salvar_agora()

    # ---- marcar ícones

    def _on_capturas(self):
        self.app_cfg["visivel_em_capturas"] = bool(self.var_capturas.get())
        gravar_json(ARQ_APP, self.app_cfg)
        self.overlay.atualizar_captura()
        self.cronometro.atualizar_captura()

    def tirar_print(self):
        """Contagem de 5 s para você voltar ao jogo e usar uma skill; depois salva um print
        da janela do jogo COM o overlay (para usar de exemplo)."""
        if not self.perfil["skills"]:
            self.status("Marque os ícones primeiro para o print mostrar o overlay.")
            return
        if not self.overlay.ativo:
            self.iniciar()
        if self.overlay.mover:
            self.alternar_mover()
        self.win.withdraw()
        aviso = tk.Toplevel(self.root)
        aviso.overrideredirect(True)
        aviso.attributes("-topmost", True)
        lbl = tk.Label(aviso, font=("Segoe UI", 13, "bold"), bg="#111111", fg="#ffffff",
                       padx=20, pady=10, justify="center")
        lbl.pack()
        aviso.geometry(f"+{aviso.winfo_screenwidth() // 2 - 260}+20")

        def contar(n):
            if n > 0:
                lbl.config(text=f"Volte para o jogo e use uma skill\nPrint em {n}...")
                aviso.after(1000, contar, n - 1)
            else:
                aviso.destroy()
                self.overlay.forcar_visivel = True
                self.overlay.atualizar_captura()
                self.root.after(250, self._capturar_print)
        contar(5)

    def _capturar_print(self):
        try:
            g = self.overlay.geo
            with nova_captura() as sct:
                regiao = ({"left": g[0], "top": g[1], "width": g[2], "height": g[3]} if g
                          else dict(sct.monitors[1]))
                shot = sct.grab(regiao)
            arq = PASTA / f"print_{time.strftime('%Y%m%d_%H%M%S')}.png"
            Image.frombytes("RGB", shot.size, shot.rgb).save(arq)
            self.status(f"Print salvo: {arq.name} (na pasta de dados).")
            registrar(f"Print salvo em {arq}")
            os.startfile(arq)
        except Exception as e:
            registrar("Erro ao tirar print:\n" + traceback.format_exc())
            self.status(f"Não consegui tirar o print: {e}")
        finally:
            self.overlay.forcar_visivel = False
            self.overlay.atualizar_captura()
            self.win.deiconify()

    def marcar_icones(self, substituir):
        if substituir and self.perfil["skills"] and not messagebox.askyesno(
                "Marcar ícones", "Isso substitui os ícones deste perfil. Continuar?",
                parent=self.win):
            return
        self._estava_ativo = self.overlay.ativo
        if self.overlay.mover:
            self.alternar_mover()
        self.overlay.parar()
        self.bt_iniciar.config(text="Iniciar overlay", image=self.ic_escuro["play"])
        self.win.withdraw()

        aviso = tk.Toplevel(self.root)
        aviso.overrideredirect(True)
        aviso.attributes("-topmost", True)
        lbl = tk.Label(aviso, font=("Segoe UI", 14, "bold"), bg="#111111", fg="#ffffff",
                       padx=24, pady=14, justify="center")
        lbl.pack()
        aviso.geometry(f"+{aviso.winfo_screenwidth() // 2 - 300}+40")

        def contar(n):
            if n > 0:
                lbl.config(text="Clique no jogo e deixe as skills PRONTAS (sem delay)\n"
                                f"Capturando a tela em {n}...")
                aviso.after(1000, contar, n - 1)
            else:
                aviso.destroy()
                self.root.after(250, lambda: self._capturar(substituir))
        contar(5)

    def _capturar(self, substituir):
        with nova_captura() as sct:
            mon = dict(sct.monitors[1])
            shot = sct.grab(mon)
        tela = Image.frombytes("RGB", shot.size, shot.rgb)
        Seletor(self.root, tela, mon,
                lambda regs: self._fim_selecao(regs, tela, mon, substituir))

    def _fim_selecao(self, regioes, tela, mon, substituir):
        if regioes:
            pasta = Perfis.pasta(self.nome)
            pasta.mkdir(parents=True, exist_ok=True)
            skills = self.perfil["skills"]
            if substituir:
                for sk in skills:
                    if sk.get("icone"):
                        (pasta / sk["icone"]).unlink(missing_ok=True)
                skills.clear()
            origem = self.overlay.origem_agora()
            ref = self.perfil.get("origem_calibracao")
            if not skills or ref is None or origem is None:
                self.perfil["origem_calibracao"] = origem
                ox = oy = 0
            else:   # converte para o mesmo referencial dos ícones já marcados
                ox, oy = origem[0] - ref[0], origem[1] - ref[1]
            stamp = time.time_ns()   # nome único, mesmo com duas capturas no mesmo segundo
            for i, (x, y, w, h) in enumerate(regioes, 1):
                arq = f"icone_{stamp}_{i}.png"
                tela.crop((x, y, x + w, y + h)).save(pasta / arq)
                skills.append({"nome": f"Skill {len(skills) + 1}",
                               "x": x + mon["left"] - ox, "y": y + mon["top"] - oy, "w": w, "h": h,
                               "icone": arq, "cd": None, "aprendido": None})
            self.salvar_agora()
            self.overlay.carregar_perfil(self.perfil, pasta)
            self.montar_lista()
            self.status(f"{len(regioes)} ícone(s) marcado(s). Dê nomes e recargas na lista.")
        self.win.deiconify()
        self.win.lift()
        if self._estava_ativo:
            self.iniciar()
