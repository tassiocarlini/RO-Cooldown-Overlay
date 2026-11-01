"""Constantes, pastas de dados, perfil padrão, bibliotecas opcionais e o log."""

import os
import sys
import time
from pathlib import Path


FALTANDO = {}               # biblioteca opcional que não carregou -> erro (vai para o log)
try:                        # para achar os ícones na tela sozinho
    import numpy as np
except ImportError as e:
    np, FALTANDO["numpy"] = None, e
try:
    import cv2
except ImportError as e:
    cv2, FALTANDO["cv2"] = None, e
try:                        # tema visual moderno (Windows 11, claro/escuro)
    import sv_ttk
except ImportError as e:
    sv_ttk, FALTANDO["sv_ttk"] = None, e

LIMIAR_PERDIDO = 0.5        # semelhança abaixo disso: o ícone não está mais ali
LIMIAR_ACHADO = 0.85        # semelhança mínima para aceitar um ícone encontrado
LIMIAR_BUFF = 0.80          # semelhança mínima para considerar o buff na tela
BUFF_TOLERANCIA = 1.5       # s sem ver o ícone antes de dizer que o buff acabou (ícone pisca)
BUFF_FOLGA_PAUSA = 1.5      # s a mais depois de tela preta / alt-tab para os ícones voltarem
MOSTRAR_BUFF = {"Sempre": "sempre", "Só quando faltar": "faltando", "Só quando ativo": "ativo"}


VERSAO = "1.0.31"
NOME_APP = "RO Cooldown Overlay"
# Repositório no GitHub de onde vêm as atualizações (CHANGELOG.md e .zip da branch abaixo)
REPO_GITHUB = "tassiocarlini/RO-Cooldown-Overlay"
BRANCH_GITHUB = "main"

if getattr(sys, "frozen", False):
    # Versão .exe: seus dados ficam em %APPDATA%, assim atualizar o programa não apaga nada
    PASTA = Path(os.environ.get("APPDATA") or Path.home()) / NOME_APP
    PASTA_RECURSOS = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
else:
    PASTA = Path(__file__).resolve().parent.parent
    PASTA_RECURSOS = PASTA
PASTA.mkdir(parents=True, exist_ok=True)

# Pastas onde o programa procura pacotes de buffs (buffs*.zip) para importar sozinho:
# a pasta do programa (.exe ou .py) e a pasta de dados
PASTAS_PACOTES = list(dict.fromkeys([
    Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent,
    PASTA]))

PASTA_PERFIS = PASTA / "perfis"
ARQ_APP = PASTA / "app.json"
ARQ_BANCO = (PASTA / "banco_skills.json" if (PASTA / "banco_skills.json").exists()
             else PASTA_RECURSOS / "banco_skills.json")   # nomes e recargas padrão
ARQ_MEUS = PASTA / "meus_tempos.json"            # recargas que você corrigiu
TODAS = "Todas as classes"
PASTA_DP = PASTA / "cache_divinepride"           # respostas e ícones da Divine Pride
DP_URL = "https://www.divine-pride.net/api/database/Skill/{id}"
DP_URL_EFST = "https://www.divine-pride.net/api/database/Efst/{id}"   # ícones de buff (status)
ESCALAS_BUFF = [round(0.9 + 0.05 * i, 2) for i in range(23)]          # 0,90x até 2,00x
LIMIAR_ACHADO_DP = 0.75     # ícone da Divine Pride x ícone na tela (podem diferir um pouco)
LIMIAR_BUFF_SITE = 0.80     # para aceitar um buff achado pelo ícone da Divine Pride
LIMIAR_OFICIAL = 0.70       # ícone oficial parecido o bastante com o do jogo para mostrar
ESCALAS_DP = (1.0, 1.25, 1.5, 2.0)
ARQ_ANTIGO = PASTA / "ro_cd_config.json"          # config da versão anterior
PASTA_ICONES_ANTIGA = PASTA / "ro_cd_icones"

COR_TRANSPARENTE = "#010101"
COR_PAINEL = (20, 23, 31)              # fundo da caixa dos ícones
ESTILOS = {"Clássico": "classico", "Moderno": "moderno", "Minimalista": "minimalista"}
BARRA_H = 5
PASTA_SONS = PASTA / "sons"                       # sons de aviso gerados pelo programa
PASTA_MEUS_SONS = PASTA / "meus_sons"             # sons que você adicionou (.mp3 ou .wav)
SEM_SOM, PADRAO = "Sem som", "Padrão"
# Sons gerados pelo programa: chave -> (nome, timbre, notas). Cada nota é
# (frequência inicial, frequência final, duração em s, decaimento); frequência 0 = pausa.
SONS_PRONTOS = {
    "sino": ("Sino", "sino", [(1320, 1320, 0.45, 7)]),
    "bip": ("Bip", "puro", [(880, 880, 0.07, 0), (0, 0, 0.05, 0), (880, 880, 0.07, 0)]),
    "suave": ("Suave", "puro", [(660, 660, 0.12, 3), (990, 990, 0.22, 6)]),
    "alerta": ("Alerta", "quadrado", [(988, 988, 0.12, 0), (0, 0, 0.03, 0), (659, 659, 0.18, 2)]),
    "moeda": ("Moeda", "quadrado", [(988, 988, 0.08, 0), (1319, 1319, 0.32, 6)]),
    "gota": ("Gota", "puro", [(1500, 450, 0.14, 9)]),
    "campainha": ("Campainha", "sino", [(784, 784, 0.32, 5), (622, 622, 0.55, 5)]),
    "subida": ("Subida", "puro", [(523, 523, 0.07, 0), (659, 659, 0.07, 0), (784, 784, 0.07, 0),
                                  (1047, 1047, 0.25, 6)]),
    "sonar": ("Sonar", "puro", [(1047, 1047, 0.9, 4)]),
    "sirene": ("Sirene", "quadrado", [(700, 1100, 0.25, 0), (1100, 700, 0.25, 0)]),
}
# Sugestões do MyInstants: o programa só guarda o link; o som é baixado no PC de quem quiser
SONS_SUGERIDOS = {"Jungle": "https://www.myinstants.com/pt/instant/gawr-gura-a-66933/"}

PERFIL_PADRAO = {
    "titulo_janela_jogo": "Ragnarok",
    "classe": TODAS,
    "origem_calibracao": None,         # posição do jogo quando os ícones foram marcados
    "skills": [],
    "buffs": [],                       # buffs vigiados (cada um com 1+ versões de ícone)
    "area_buffs": None,                # área da tela onde ficam os ícones de buff
    "area_ap": None,                   # onde aparece "AP 53 / 200" na janela Informações básicas
    "layout": {
        "x": None, "y": None,          # None = centralizado
        "tamanho": 50,
        "espaco": 1,
        "orientacao": "horizontal",
        "esconder_quando_pronto": False,
        "esconder_sem_foco": False,
        "estilo": "moderno",           # classico | moderno | minimalista
        "fundo_painel": False,         # caixa escura atrás de todos os ícones
        "mostrar_nomes": False,        # nome da skill/buff embaixo do ícone
        "icone_oficial": True,         # mostra o ícone oficial (não o print da sua barra)
        "mostrar_ap": True,            # barra de AP acima dos ícones
        "ap_altura": 0,                # altura da barra de AP em pixels (0 = automática)
        "ap_cor": "#3b82f6",           # cor do preenchimento da barra de AP
        "aviso_vermelho_s": 3.0,
        "som_skill": "sino",           # som quando a skill volta (None = sem som)
        "som_buff": "alerta",          # som quando o buff está acabando ou acabou
        "som_volume": 70,              # 0 a 100
        "origem": None,                # posição do jogo quando o overlay foi posicionado
    },
    "deteccao": {
        "limiar_delay": 0.10,
        "limiar_pronto": 0.03,
        "frames_entrar": 1,
        "frames_confirmar": 2,
        "min_mostrar": 0.6,
        "fps": 30,
    },
    "versao": 6,
}

JANELA_GRUPO = 0.15   # s: ícones que escurecem juntos dentro disso = delay global


ARQ_LOG = PASTA / "log.txt"
_ult_log = {}


def registrar(msg, chave_rep=None, intervalo=10.0):
    """Escreve em log.txt (com limite de repetição para erros que se repetem a cada frame)."""
    agora = time.monotonic()
    if chave_rep is not None:
        if agora - _ult_log.get(chave_rep, -1e9) < intervalo:
            return
        _ult_log[chave_rep] = agora
    try:
        if ARQ_LOG.exists() and ARQ_LOG.stat().st_size > 500_000:
            ARQ_LOG.unlink()
        with open(ARQ_LOG, "a", encoding="utf-8") as f:
            f.write(time.strftime("%H:%M:%S ") + msg.rstrip() + "\n")
    except Exception:
        pass
