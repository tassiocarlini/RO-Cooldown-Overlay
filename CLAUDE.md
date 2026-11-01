# RO Cooldown Overlay

Overlay de recargas para Ragnarok Online LATAM (Python + tkinter, Windows). Só olha a tela:
nunca ler memória do jogo nem enviar teclas.

## Onde fica cada coisa
- `ro_cooldown_overlay.py`: só a porta de entrada (e baixa `rocd/` se faltar). Não pôr código aqui.
- `rocd/`: o programa. Mapa dos módulos no docstring de `rocd/__init__.py`.
- O Painel é dividido por aba: `class Painel(AbaSkills, AbaBuffs, AbaSons, AbaAvancado)` em
  `rocd/painel.py`; os métodos de cada aba ficam em `rocd/aba_*.py`.
- `VERSAO` fica em `rocd/config.py` (lida também por `empacotar.py` e pelo CI).

## Versão nova
1. Subir `VERSAO` em `rocd/config.py`, nova seção `## vX.Y.Z` no topo do `CHANGELOG.md`
   e a linha de versão do `LEIA-ME.txt`.
2. Envio para a `main` = release para todos (o CI gera o .exe e a Release). Perguntar antes de enviar.

## Checagens
- `python -m pytest` (testes em `tests/`, rodam sem internet e sem abrir janela) e
  `python -m pyflakes rocd ro_cooldown_overlay.py tests empacotar.py`. O CI roda os dois em todo
  envio; se falharem, a Release não sai.
- `python ro_cooldown_overlay.py --verificar` (sai 1 se numpy/cv2/sv_ttk não carregarem).
- `python empacotar.py` gera o .exe em `dist/` (precisa de pyinstaller==6.22.3).

## Não enviar ao GitHub
Dados de quem usa: `app.json` (tem a chave da Divine Pride), `perfis/`, caches, `sons/`, `meus_sons/`.
Áudio de terceiros (ex.: Jungle) não entra no repositório: o programa baixa no PC da pessoa.
