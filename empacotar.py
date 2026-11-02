"""Gera a versão .exe do RO Cooldown Overlay com o PyInstaller.

Uso:  python empacotar.py            (precisa de: pip install -r requirements.txt pyinstaller)
Sai:  dist/RO Cooldown Overlay/                         pasta com o programa
      dist/RO-Cooldown-Overlay-Windows.zip              o que vai para a Release (nome fixo:
                                                        o link de download do README não muda)
      dist/notas.md                                     novidades desta versão (do CHANGELOG)

O mesmo script roda no GitHub (.github/workflows/release.yml) e no seu PC (build_exe.bat).
Chave padrão da Divine Pride: se a variável DP_CHAVE_PADRAO existir (no GitHub vem do segredo
de mesmo nome), ela entra embaralhada só dentro do .exe (rocd/_chave.py, apagado no fim).
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import PyInstaller.__main__

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rocd.chave import esconder  # noqa: E402

AQUI = Path(__file__).resolve().parent
NOME = "RO Cooldown Overlay"
DIST = AQUI / "dist"
BUILD = AQUI / "build"


def versao():
    m = re.search(r'^VERSAO = "([\d.]+)"', (AQUI / "rocd" / "config.py").read_text(encoding="utf-8"), re.M)
    if not m:
        sys.exit("Não achei VERSAO no rocd/config.py")
    return m.group(1)


def notas(v):
    """Texto do CHANGELOG.md entre "## vX.Y.Z" e a próxima versão."""
    texto = (AQUI / "CHANGELOG.md").read_text(encoding="utf-8")
    m = re.search(rf"^##[ \t]*v?{re.escape(v)}[ \t]*\r?$(.*?)(?=^##\s|\Z)", texto, re.M | re.S)
    if not m:
        sys.exit(f"O CHANGELOG.md não tem a seção ## v{v}")
    return m.group(1).strip()


def arquivo_versao(v):
    """Propriedades do .exe (botão direito > Propriedades > Detalhes)."""
    n = tuple(int(x) for x in v.split(".")) + (0,) * (4 - len(v.split(".")))
    campos = {"CompanyName": "Autores do RO Cooldown Overlay",
              "FileDescription": NOME,
              "FileVersion": v,
              "InternalName": NOME,
              "LegalCopyright": "Licença MIT",
              "OriginalFilename": f"{NOME}.exe",
              "ProductName": NOME,
              "ProductVersion": v}
    tabela = ",\n          ".join(f"StringStruct({k!r}, {val!r})" for k, val in campos.items())
    arq = BUILD / "versao.txt"
    arq.parent.mkdir(exist_ok=True)
    arq.write_text(f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={n}, prodvers={n}, mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('041604B0', [
          {tabela}])]),
    VarFileInfo([VarStruct('Translation', [0x0416, 1200])])
  ]
)
""", encoding="utf-8")
    return arq


def verificar_chave(exe):
    """O .exe tem mesmo a chave padrão? (sem mostrar a chave)"""
    (BUILD / "dados_verificacao").mkdir(parents=True, exist_ok=True)
    r = subprocess.run([str(exe), "--verificar-chave"], timeout=120,
                       env={**os.environ, "APPDATA": str(BUILD / "dados_verificacao")})
    if r.returncode != 0:
        sys.exit("O .exe gerado não ficou com a chave padrão da Divine Pride.")
    print("Verificação: chave padrão da Divine Pride embutida.")


def verificar(exe):
    """Abre o .exe com --verificar: falha se numpy, cv2 ou sv_ttk não carregarem dentro dele
    (já aconteceu: sem numpy, buffs e AP param e o programa não avisa)."""
    dados = BUILD / "dados_verificacao"              # o log do teste não vai para o seu %APPDATA%
    shutil.rmtree(dados, ignore_errors=True)
    dados.mkdir(parents=True)
    r = subprocess.run([str(exe), "--verificar"], env={**os.environ, "APPDATA": str(dados)},
                       timeout=120)
    if r.returncode != 0:
        log = dados / NOME / "log.txt"
        print(log.read_text(encoding="utf-8") if log.exists() else "(sem log)")
        sys.exit(f"O .exe gerado não carrega todas as bibliotecas (código {r.returncode}).")
    print("Verificação: numpy, cv2, sv_ttk e os ícones embutidos carregam dentro do .exe.")


def main():
    v = versao()
    texto_notas = notas(v)
    print(f"Gerando {NOME} v{v}…")
    chave = os.environ.get("DP_CHAVE_PADRAO", "").strip()
    arq_chave = AQUI / "rocd" / "_chave.py"
    if chave:
        arq_chave.write_text(esconder(chave), encoding="utf-8")
        print("Com a chave padrão da Divine Pride (embaralhada).")
    else:
        arq_chave.unlink(missing_ok=True)
        print("Sem DP_CHAVE_PADRAO: o .exe sai sem chave padrão (cada um usa a sua).")
    try:
        gerar_exe(v)
    finally:
        arq_chave.unlink(missing_ok=True)          # nunca fica no PC nem vai para o git
    pasta = DIST / NOME
    if chave:
        verificar_chave(pasta / f"{NOME}.exe")
    finalizar(pasta, texto_notas)


def gerar_exe(v):
    PyInstaller.__main__.run([
        "--noconfirm", "--clean", "--windowed",
        "--name", NOME,
        "--icon", str(AQUI / "assets" / "icone.ico"),
        "--version-file", str(arquivo_versao(v)),
        "--add-data", f"{AQUI / 'banco_skills.json'};.",
        "--add-data", f"{AQUI / 'rocd' / 'icones'};rocd/icones",      # ícones de status embutidos
        "--collect-data", "sv_ttk",
        "--hidden-import", "rocd._chave",
        "--distpath", str(DIST),
        "--workpath", str(BUILD),
        "--specpath", str(BUILD),
        str(AQUI / "ro_cooldown_overlay.py"),
    ])


def finalizar(pasta, texto_notas):
    for dll in pasta.glob("_internal/cv2/opencv_videoio_ffmpeg*.dll"):
        dll.unlink()                               # 30 MB só para vídeo: o programa não usa
    verificar(pasta / f"{NOME}.exe")
    for nome in ("LEIA-ME.txt", "LICENSE", "CHANGELOG.md"):
        shutil.copy2(AQUI / nome, pasta / nome)
    zip_base = DIST / "RO-Cooldown-Overlay-Windows"
    shutil.make_archive(str(zip_base), "zip", DIST, NOME)      # o .zip tem a pasta do programa
    (DIST / "notas.md").write_text(texto_notas + "\n", encoding="utf-8")
    print(f"\nPronto: {pasta}\n       {zip_base}.zip")


if __name__ == "__main__":
    main()
