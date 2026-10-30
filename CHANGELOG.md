# Mudanças

## v1.0.24
- Barra de AP volta a ler valores com o dígito 4 (ex.: 140, 146, 44): o 4 da fonte do jogo encosta no dígito seguinte e o programa não reconhecia o número.

## v1.0.23
- Barra de AP acompanha os buffs: quando um buff com "Só quando faltar" ou "Só quando ativo" está escondido, a barra encolhe até o último ícone visível.

## v1.0.22
- Perfis novos começam com ícones de 50 px, 1 px de espaço entre eles e a barra de AP ligada. Perfis que você já tem continuam como estão.

## v1.0.21
- Atualização automática agora vem direto do código do GitHub (botão Code → Download ZIP), sem depender da página de Releases.
- A versão .exe separada foi retirada por enquanto: use o ZIP do código e abra o "RO Cooldown Overlay.exe" da pasta.

## v1.0.20
- O programa procura versão nova toda vez que abre (antes era no máximo 1 vez por dia). Se houver, pergunta se você quer baixar e instalar.

## v1.0.19
- Código do programa agora fica direto no repositório do GitHub. A atualização automática passa a funcionar na versão em Python e na versão .exe.

## v1.0.17
- Atualização automática: ao abrir (no máximo 1 vez por dia) ou pelo botão "Verificar atualizações" (aba Avançado), o programa consulta a página de Releases do GitHub. Se houver versão nova, mostra as novidades e, com um clique, baixa, instala e reabre sozinho — na versão .exe e na versão em Python. Perfis e configurações não são tocados.
- Opções "Depois" e "Pular esta versão".

## v1.0.16
- Aba Aparência reorganizada em seções (Ícones, Posição na tela, Quando mostrar, Barra de AP), com nomes mais claros ("Tamanho do ícone", "Espaço entre ícones", "Direção da fila"…), valores em pixels e uma explicação curta embaixo de cada opção.
- Aba Avançado com nomes e explicações mais claras ("Sensibilidade", "Nome da janela do jogo"…).
- Explicações que aparecem ao parar o mouse em cima dos botões e opções.
- Títulos das seções em destaque.

## v1.0.15
- Ícones de buff do ragassets passam na frente mesmo quando já existe um ícone antigo da Divine Pride guardado no PC.
- Buffs adicionados "pelo nome" antes do ragassets (ex.: Brisa Leve) têm as versões ainda não confirmadas trocadas sozinhas pelos ícones do cliente LATAM ao abrir o programa.
- Recargas oficiais do cliente LATAM (tabela de skills do ragassets) passam a ter prioridade sobre a Divine Pride e o banco local.

## v1.0.14
- ragassets (latam-tools) como fonte principal de ícones de buff, ícones de skill e nomes em português, tirados do próprio cliente LATAM e sem precisar de chave. Se ele falhar ou não responder, o programa usa as fontes de antes (Divine Pride, banco local e captura da tela) e só tenta o ragassets de novo depois de 10 minutos.
- Opção na aba Avançado para ligar/desligar o ragassets, com o estado da conexão.

## v1.0.13
- Aba Avançado fica vermelha enquanto a chave da API da Divine Pride não estiver configurada.
- Botões "Skill pelo nome" e "Buff pelo nome" em amarelo e como primeiro botão das abas Skills e Buffs.

## v1.0.12
- AP: a área marcada à mão na versão 1.0.8 (quando marcar era obrigatório) é descartada uma vez, e o programa passa a achar o AP sozinho.
- AP: se uma área marcada à mão parar de ler (janela arrastada ou trocada entre reduzida e expandida), o programa usa a busca automática no lugar e, de tempos em tempos, testa a área marcada de novo.

## v1.0.11
- AP: a busca começa pelo canto superior esquerdo da tela e testa todos os rótulos "AP" encontrados (se o primeiro não tiver números ao lado, tenta o próximo); tolera pequenas variações de cor.
- Botão "Diagnóstico" na barra de AP: salva o que o programa está vendo, para facilitar o suporte.

## v1.0.10
- AP: ao reduzir/expandir a janela Informações básicas (ou arrastá-la), o programa percebe na hora que o rótulo "AP" mudou de lugar e procura de novo, em vez de continuar lendo o lugar antigo (que caía em cima do HP/SP).

## v1.0.9
- AP encontrado sozinho: o programa acha a janela Informações básicas pelo rótulo "AP" em qualquer lugar da tela (compacta ou expandida) e volta a procurar se você mover ou fechar a janela. Marcar à mão virou opcional.
- Leitura mais firme na janela expandida: o preenchimento azul da barra passando por cima dos números não atrapalha mais.
- Barra de AP com altura e cor ajustáveis (aba Aparência).

## v1.0.8
- Barra de AP acima dos ícones (opcional, na aba Aparência): lê o "AP 53 / 200" da janela Informações básicas do jogo — compacta ou expandida — e mostra a barra com o número, sempre do tamanho da faixa de ícones.

## v1.0.7
- Versão base atual do projeto (inclui todas as mudanças abaixo).

## v1.0.0 — primeira versão pública
- Overlay de recarga das skills perto do centro da tela, sem receber cliques.
- Detecção pela tela: o programa compara cada ícone da barra de atalhos com a imagem dele "pronto".
- Recarga manual, aprendida sozinha ou vinda do banco de skills (classes de 4ª, em português).
- Busca automática dos ícones quando a barra muda de lugar; não conta delay falso quando o ícone some.
- Overlay preso à janela do Ragnarok (acompanha a janela e some quando o jogo é minimizado).
- Aba Buffs: vigia se um buff está ativo (borda verde) ou caiu (alerta vermelho), aceita várias versões de ícone por buff (ex.: Brisa Leve de cada elemento) e duração opcional.
- Captura automática das versões de um buff (botão "Auto"): basta usar o buff com cada elemento.
- Reconhecimento de buffs pelos traços do desenho do ícone: funciona com os ícones translúcidos do RO (cenário aparecendo por trás e varredura do tempo restante).
- Exportar e importar buffs em um arquivo `.zip`, para compartilhar a configuração.
- Pacotes `buffs*.zip` deixados na pasta do programa são importados sozinhos em cada perfil (uma vez por perfil).
- Botões para subir e descer cada buff na lista (muda a ordem no overlay).
- Estilos para as caixas dos ícones (Moderno, Minimalista, Clássico), caixa escura atrás dos ícones e opção de mostrar o nome embaixo de cada ícone.
- "Buff pelo nome": com a chave da Divine Pride, baixa todas as versões do ícone do buff (ex.: os 7 elementos da Brisa Leve) e acha o buff na tela sozinho, em qualquer tamanho de interface.
- Ícones de buff baixados do site são confirmados com a tela: o "Auto" troca cada um pelo recorte real e substitui os que forem diferentes no LATAM.
- Banco de skills completo das 20 classes de 4ª, com as skills herdadas (959 skills, 390 buffs com ícone). Nomes em português que faltam são baixados da Divine Pride ao escolher a classe; a busca aceita português ou inglês.
- Lançador `RO Cooldown Overlay.exe` (com ícone próprio) para abrir a versão em Python sem janela preta.
- Alerta de buff caído mais visível ("!" grande e borda piscando); sem barra embaixo do ícone do buff.
- Perfis por personagem, mover e redimensionar, direção horizontal/vertical.
- Integração opcional com a API da Divine Pride (recarga LATAM, ícones e "Skill pelo nome"), com botão "Como pegar a chave?" e passo a passo no README.
- Botão "Tirar print" e opção para o overlay aparecer em prints, gravações e lives.
- `iniciar.bat` instala o Python e as bibliotecas sozinho quando não estão no computador.
- Visual escuro com botões em degradê preto e azul, ícones em todos os botões e abas destacadas (Skills, Aparência, Avançado), que cabem em telas de notebook.
- Versão `.exe` para Windows: não precisa instalar Python. Configurações ficam em `%APPDATA%\RO Cooldown Overlay`.
