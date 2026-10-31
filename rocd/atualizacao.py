"""Atualização sozinha pelo GitHub (CHANGELOG.md e Release)."""

import hashlib
import io
import json
import os
import re
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

from .config import BRANCH_GITHUB, NOME_APP, REPO_GITHUB, VERSAO


# =============================================================== início

# =============================================================== atualizações

def versao_tupla(v):
    """"v1.0.16" -> (1, 0, 16). Partes não numéricas viram 0."""
    partes = re.findall(r"\d+", str(v or ""))
    return tuple(int(x) for x in partes[:4]) or (0,)


def _http(url, binario=False, timeout=20, progresso=None):
    req = urllib.request.Request(url, headers={
        "User-Agent": f"RO-Cooldown-Overlay/{VERSAO}",
        "Accept": "application/octet-stream" if binario else "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        if not binario:
            return json.loads(r.read().decode("utf-8"))
        total = int(r.headers.get("Content-Length") or 0)
        partes, lido = [], 0
        while True:
            bloco = r.read(256 * 1024)
            if not bloco:
                break
            partes.append(bloco)
            lido += len(bloco)
            if progresso and total:
                progresso(lido / total)
        return b"".join(partes)


def buscar_versao_nova():
    """Consulta o CHANGELOG.md da branch main no GitHub: o primeiro "## vX.Y.Z" é a versão
    mais nova e o texto até o próximo "## " são as novidades. Devolve dict com a versão nova
    ou None se já está na mais nova."""
    if not REPO_GITHUB or "SEU-USUARIO" in REPO_GITHUB:
        raise ValueError("o endereço do repositório ainda não foi configurado no programa")
    req = urllib.request.Request(
        f"https://raw.githubusercontent.com/{REPO_GITHUB}/{BRANCH_GITHUB}/CHANGELOG.md",
        headers={"User-Agent": f"RO-Cooldown-Overlay/{VERSAO}", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=20) as r:
        texto = r.read().decode("utf-8", errors="replace")
    m = re.search(r"^##[ \t]*(v?\d+(?:\.\d+)+)[ \t]*\r?$(.*?)(?=^##\s|\Z)", texto, re.M | re.S)
    if not m:
        raise ValueError("não achei a versão no CHANGELOG.md do GitHub")
    tag = m.group(1)
    if versao_tupla(tag) <= versao_tupla(VERSAO):
        return None
    info = {"tag": tag, "notas": m.group(2).strip(),
            "pagina": f"https://github.com/{REPO_GITHUB}/releases/latest",
            "zip_exe": None, "digest": None, "pendente": False,
            "zip_fonte": f"https://github.com/{REPO_GITHUB}/archive/refs/heads/{BRANCH_GITHUB}.zip"}
    if getattr(sys, "frozen", False):
        # o .exe vem da Release que o GitHub gera sozinho a cada versão nova na main;
        # logo depois do envio ela ainda está sendo montada (alguns minutos)
        try:
            rel = _http(f"https://api.github.com/repos/{REPO_GITHUB}/releases/tags/{tag}")
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
            rel = {}
        zips = [a for a in rel.get("assets", []) if a.get("name", "").endswith("-Windows.zip")]
        if zips:
            info["zip_exe"] = zips[0]["browser_download_url"]
            info["digest"] = zips[0].get("digest") or ""
        else:
            info["pendente"] = True
    return info


# Arquivos do programa trocados ao atualizar a versão em Python (os seus dados nunca são tocados)
ARQUIVOS_PROGRAMA = ("ro_cooldown_overlay.py", "banco_skills.json", "requirements.txt",
                     "iniciar.bat", "LEIA-ME.txt", "README.md", "CHANGELOG.md", "LICENSE",
                     "RO Cooldown Overlay.exe", "build_exe.bat")
PASTAS_PROGRAMA = ("rocd", "assets", "lancador")


def _extrair_seguro(zf, destino):
    """Extrai um .zip sem deixar nenhum arquivo sair da pasta de destino."""
    destino = Path(destino).resolve()
    for nome in zf.namelist():
        alvo = (destino / nome).resolve()
        if destino not in alvo.parents and alvo != destino:
            raise ValueError(f"arquivo suspeito no pacote: {nome}")
    zf.extractall(destino)


def preparar_atualizacao(info, progresso=None):
    """Baixa e desempacota a versão nova numa pasta temporária. Devolve a pasta com os arquivos
    novos já no formato da instalação atual (.exe ou Python)."""
    import tempfile
    congelado = getattr(sys, "frozen", False)
    url = info["zip_exe"] if congelado else info["zip_fonte"]
    if not url:
        raise ValueError("a release não tem o arquivo para Windows")
    dados = _http(url, binario=True, timeout=120, progresso=progresso)
    if congelado and (info.get("digest") or "").startswith("sha256:"):
        if hashlib.sha256(dados).hexdigest() != info["digest"].split(":", 1)[1]:
            raise ValueError("o arquivo baixado não confere (download corrompido)")
    tmp = Path(tempfile.mkdtemp(prefix="ro_cd_atualiza_"))
    with zipfile.ZipFile(io.BytesIO(dados)) as zf:
        _extrair_seguro(zf, tmp / "pacote")
    if congelado:
        # o .zip da release tem a pasta "RO Cooldown Overlay" com o .exe dentro
        exe = next((p for p in (tmp / "pacote").rglob(f"{NOME_APP}.exe")), None)
        if exe is None:
            raise ValueError("não achei o programa dentro do pacote baixado")
        return tmp, exe.parent
    # código-fonte: a pasta de cima do .zip tem o nome do repositório e do commit
    raiz = next((p.parent for p in (tmp / "pacote").rglob("ro_cooldown_overlay.py")), None)
    if raiz is None:
        raise ValueError("não achei o ro_cooldown_overlay.py dentro do pacote baixado")
    return tmp, raiz


def aplicar_atualizacao(tmp, origem):
    """Instala a versão nova e reinicia o programa.
    .exe: um script do PowerShell espera este programa fechar, copia os arquivos e abre o novo.
    Python: troca só os arquivos do programa na pasta e reabre."""
    congelado = getattr(sys, "frozen", False)
    pasta_prog = Path(sys.executable).parent if congelado else Path(__file__).resolve().parent.parent

    def q(caminho):                                   # texto entre aspas no PowerShell
        return "'" + str(caminho).replace("'", "''") + "'"

    if not congelado:
        for nome in ARQUIVOS_PROGRAMA:
            if (origem / nome).is_file():
                shutil.copy2(origem / nome, pasta_prog / nome)
        for nome in PASTAS_PROGRAMA:
            if (origem / nome).is_dir():
                shutil.copytree(origem / nome, pasta_prog / nome, dirs_exist_ok=True)
        lancador = pasta_prog / f"{NOME_APP}.exe"
        if lancador.exists():
            abrir = f"Start-Process -FilePath {q(lancador)}"
        else:
            pyw = Path(sys.executable).with_name("pythonw.exe")
            abrir = (f"Start-Process -FilePath {q(pyw if pyw.exists() else 'pythonw')} "
                     f"-ArgumentList {q(chr(34) + str(pasta_prog / 'ro_cooldown_overlay.py') + chr(34))} "
                     f"-WorkingDirectory {q(pasta_prog)}")
        copiar = ""
    else:
        abrir = f"Start-Process -FilePath {q(pasta_prog / (NOME_APP + '.exe'))}"
        copiar = f"Copy-Item -Path {q(str(origem) + chr(92) + '*')} -Destination {q(pasta_prog)} -Recurse -Force\r\n"
    script = ("$ErrorActionPreference = 'SilentlyContinue'\r\n"
              f"Wait-Process -Id {os.getpid()} -Timeout 60\r\n"
              "Start-Sleep -Milliseconds 500\r\n"
              + copiar + abrir + "\r\n"
              f"Remove-Item -Path {q(tmp)} -Recurse -Force\r\n")
    arq = tmp / "atualizar.ps1"
    arq.write_text(script, encoding="utf-8-sig")       # com BOM: acentos nos caminhos funcionam
    import subprocess
    subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                      "-WindowStyle", "Hidden", "-File", str(arq)],
                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), close_fds=True)
