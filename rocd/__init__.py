"""Código do RO Cooldown Overlay. Quem abre é o ro_cooldown_overlay.py (pasta de cima).

Módulos (cada um importa só dos que estão acima dele na lista):
  config        constantes, pastas de dados, PERFIL_PADRAO, VERSAO, numpy/cv2/sv_ttk, registrar()
  janelas       Windows: achar a janela do jogo (Jogo), estilos de janela, captura de tela
  visao         comparar imagens: semelhanca(), mapa_simbolo(), molduras
  desenho       paleta COR (mude aqui o visual), logo, ícones dos botões, abas
  ap            leitura do número de AP (dígitos da fonte do jogo)
  dados         Banco de skills, JSON, ler_tempo() / fmt_tempo()
  sites         DivinePride (API) e RagAssets (latam-tools)
  perfis        Perfis e importação de dados de versões antigas
  captura       CapturaAuto: acha um ícone de skill ou buff na tela
  seletores     SeletorSkill (busca pelo nome) e Seletor (marcar área na tela)
  sons          Sons (MCI do Windows) e download do MyInstants
  overlay       Overlay: lê a tela, recargas, buffs, AP e desenha os ícones
  atualizacao   atualização pelo GitHub
  aba_skills    métodos do Painel da aba Skills ofensivas (+ marcar ícones, Divine Pride)
  aba_buffs     métodos do Painel da aba Buffs (+ barra de AP)
  aba_sons      métodos do Painel da aba Sons
  aba_avancado  métodos do Painel da aba Avançado (+ atualizações)
  painel        Painel (janela principal): base, tema, perfis, aparência, status
  app           main()
"""
