"""Perfis salvos e importação de dados de versões antigas."""

import copy
import json
import re
import shutil
import sys
import traceback
from pathlib import Path

from .config import (ARQ_ANTIGO, ARQ_APP, ARQ_MEUS, PASTA, PASTA_ICONES_ANTIGA, PASTA_PERFIS,
    PERFIL_PADRAO, registrar)
from .dados import gravar_json, ler_json, mesclar


# =============================================================== perfis

def nome_seguro(nome):
    return re.sub(r'[<>:"/\\|?*]', "_", (nome or "")).strip().strip(".")


class Perfis:
    @staticmethod
    def listar():
        PASTA_PERFIS.mkdir(exist_ok=True)
        return sorted(p.name for p in PASTA_PERFIS.iterdir() if (p / "perfil.json").exists())

    @staticmethod
    def pasta(nome):
        return PASTA_PERFIS / nome

    @staticmethod
    def carregar(nome):
        try:
            dados = json.loads((PASTA_PERFIS / nome / "perfil.json").read_text(encoding="utf-8"))
        except Exception:
            dados = {}
        perfil = mesclar(PERFIL_PADRAO, dados)
        if dados:
            # na 1.0.22 o padrão mudou só para perfis novos; os já salvos mantêm o antigo
            antigo = dados.get("layout") if isinstance(dados.get("layout"), dict) else {}
            for k, v in (("tamanho", 52), ("espaco", 8), ("mostrar_ap", False)):
                if k not in antigo:
                    perfil["layout"][k] = v
        if dados and dados.get("versao", 3) < 4:
            D = perfil["deteccao"]
            D["fps"] = max(D["fps"], 30)
            D["limiar_pronto"] = round(D["limiar_delay"] * 0.3, 3)
            perfil["versao"] = 4
        if dados and dados.get("versao", 3) < 5:
            # visual padrão: estilo Moderno, sem caixa escura e sem nomes
            perfil["layout"].update(estilo="moderno", fundo_painel=False, mostrar_nomes=False)
            perfil["versao"] = 5
        if dados and dados.get("versao", 3) < 6:
            # na 1.0.8 marcar o AP era obrigatório; agora o programa acha sozinho
            perfil["area_ap"] = None
            perfil["versao"] = 6
        return perfil

    @staticmethod
    def salvar(nome, perfil):
        pasta = PASTA_PERFIS / nome
        pasta.mkdir(parents=True, exist_ok=True)
        limpo = {k: v for k, v in perfil.items() if k not in ("skills", "buffs")}
        for chave_lista in ("skills", "buffs"):
            limpo[chave_lista] = [{k: v for k, v in s.items() if not k.startswith("_")}
                                  for s in perfil.get(chave_lista, [])]
        gravar_json(pasta / "perfil.json", limpo)

    @staticmethod
    def criar(nome):
        Perfis.salvar(nome, copy.deepcopy(PERFIL_PADRAO))


def migrar_config_antiga():
    """Importa a configuração da versão anterior como perfil 'Padrão'."""
    if Perfis.listar() or not ARQ_ANTIGO.exists():
        return
    try:
        antigo = json.loads(ARQ_ANTIGO.read_text(encoding="utf-8"))
    except Exception:
        return
    nome = "Padrão"
    pasta = Perfis.pasta(nome)
    pasta.mkdir(parents=True, exist_ok=True)
    perfil = copy.deepcopy(PERFIL_PADRAO)
    for s in antigo.get("skills", []):
        src = PASTA_ICONES_ANTIGA / s.get("icone", "")
        if src.is_file():
            shutil.copy2(src, pasta / src.name)
        perfil["skills"].append({k: s.get(k) for k in
                                 ("nome", "x", "y", "w", "h", "icone", "cd", "aprendido")})
    perfil["titulo_janela_jogo"] = antigo.get("titulo_janela_jogo", "Ragnarok")
    L, D = perfil["layout"], perfil["deteccao"]
    L["tamanho"] = antigo.get("tamanho_icone", L["tamanho"])
    L["espaco"] = antigo.get("espaco", L["espaco"])
    L["esconder_quando_pronto"] = antigo.get("esconder_quando_pronto", False)
    for k in D:
        D[k] = antigo.get(k, D[k])
    Perfis.salvar(nome, perfil)


def tem_dados_antigos(pasta):
    pasta = Path(pasta)
    return pasta.resolve() != PASTA.resolve() and (pasta / "perfis").is_dir() and any(
        (p / "perfil.json").exists() for p in (pasta / "perfis").iterdir())


def importar_dados_antigos(pasta, cfg):
    """Copia perfis e configurações da versão em Python (dados na pasta do programa) para a
    pasta de dados desta versão. Perfil com o mesmo nome: fica o mais novo, e o outro é
    guardado como "Nome (antigo)". Opções que faltam em `cfg` (app.json) vêm de lá.
    Devolve os nomes dos perfis copiados."""
    pasta = Path(pasta)
    copiados = []
    PASTA_PERFIS.mkdir(parents=True, exist_ok=True)
    for p in sorted((pasta / "perfis").iterdir()):
        if not (p / "perfil.json").exists():
            continue
        destino = PASTA_PERFIS / p.name
        if (destino / "perfil.json").exists():
            if (p / "perfil.json").stat().st_mtime <= (destino / "perfil.json").stat().st_mtime:
                continue                                  # o daqui é mais novo
            n, guarda = 1, PASTA_PERFIS / f"{p.name} (antigo)"
            while guarda.exists():
                n += 1
                guarda = PASTA_PERFIS / f"{p.name} (antigo {n})"
            destino.rename(guarda)
        elif destino.exists():
            shutil.rmtree(destino)                        # pasta sem perfil.json: sobra
        shutil.copytree(p, destino)
        copiados.append(p.name)
    for k, v in ler_json(pasta / "app.json", {}).items():
        if not cfg.get(k) and k not in ("ultimo_perfil", "pular_versao"):
            cfg[k] = v
    if copiados:
        cfg["ultimo_perfil"] = copiados[0]
    meus = ler_json(pasta / "meus_tempos.json", {})
    if meus:
        gravar_json(ARQ_MEUS, {**meus, **ler_json(ARQ_MEUS, {})})
    for nome in ("cache_divinepride", "cache_ragassets", "meus_sons"):
        if (pasta / nome).is_dir():
            shutil.copytree(pasta / nome, PASTA / nome, dirs_exist_ok=True)
    registrar(f"Importados da versão antiga ({pasta}): {', '.join(copiados) or 'nenhum perfil'}")
    return copiados


def importar_dados_antigos_sozinho():
    """Primeira vez do .exe: se ele foi extraído dentro (ou do lado) da versão em Python,
    traz os perfis de lá sem perguntar (uma vez só)."""
    if not getattr(sys, "frozen", False):
        return
    cfg = ler_json(ARQ_APP, {})
    if cfg.get("importou_versao_python"):
        return
    exe = Path(sys.executable).parent
    for pasta in (exe, exe.parent):
        try:
            if tem_dados_antigos(pasta):
                importar_dados_antigos(pasta, cfg)
                cfg["importou_versao_python"] = str(pasta)
                gravar_json(ARQ_APP, cfg)
                return
        except Exception:
            registrar("Erro ao importar a versão antiga:\n" + traceback.format_exc())
