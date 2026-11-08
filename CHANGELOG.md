# Mudanças

## v1.0.37
- Consumíveis já vêm com a duração do jogo ao escolher pelo nome (ex.: Estimulante 30 min, Churrasco de Selvagem 5 min): o aviso de "buff acabando" funciona sem digitar nada. Na busca, a coluna mostra os ícones e a duração.
- Relógio do ícone: o programa lê o véu claro que o jogo desenha no ícone do buff (o tempo que já passou). Buff que já estava ativo quando o programa viu fica com o tempo certo, e buff renovado volta a contar do começo (e a avisar). Vale para todo buff com duração.
- Barra de AP mais estável: um instante sem o rótulo "AP" (ex.: mouse em cima da janela) não faz mais o programa perder a janela Informações básicas e procurar na tela toda.

## v1.0.36
- Aba Buffs: consumíveis entram na busca "Buff pelo nome" (Estimulante, Poção de Velocidade, poções de ASPD, comidas de atributo, Manuk, pergaminhos, sais de banho, bônus de EXP/DROP e outros). Valem para qualquer classe e aparecem depois dos buffs da classe. No filtro de classe, "Consumível" mostra só eles.
- Comidas de atributo têm duas versões (comum e da loja); o programa acha as duas.
- Alguns consumíveis antigos não têm ícone no ragassets: o ícone vem da Divine Pride (com a chave) ou é marcado na tela com "Ícone" / "Auto".

## v1.0.35
- Visual novo na janela do programa: tons de azul-escuro (como o logo e o overlay) no lugar do cinza, e o dourado só nos botões principais e no que está selecionado.
- Uma fonte só em toda a janela. No Windows 10 cada campo saía com uma fonte diferente (as listas da aba Sons, por exemplo).
- Perfil: os botões Novo, Duplicar, Renomear e Excluir foram para o botão ⋯ ao lado do perfil.
- O estado de cada skill e buff virou uma etiqueta colorida: "Pronta"/"Ativo" em verde, "Em recarga"/"Delay"/"Ative no jogo" em dourado, "Sem ícone"/"Jogo não encontrado" em vermelho. Os números da detecção (ex.: 0.33) aparecem ao parar o mouse em cima.
- As listas de skills, buffs e sons ocupam a largura toda e não cortam mais os nomes (ex.: "Postura do Universo"). A barra de rolagem só aparece quando não cabe tudo, e a roda do mouse rola a lista mesmo com o mouse em cima de um campo.
- Seções sem moldura (nada de caixa dentro de caixa). Na aba Aparência, as explicações óbvias saíram da tela e ficam ao parar o mouse em cima ou no ícone (?).
- A aba Avançado não fica mais vermelha sem a chave da Divine Pride: aparece só uma bolinha no ícone. Ela também rola em telas baixas (antes a parte da Divine Pride podia ficar cortada). O botão "Como pegar a chave?" deixou de ser vermelho.
- Aba Cronômetro: "segundos", os botões ▶ e o tamanho ficam colados ao campo.
- Lista de skills ou de buffs vazia: mostra os passos e o botão "Skill pelo nome" / "Buff pelo nome".

## v1.0.34
- Nova aba "Cronômetro": contagem regressiva para o recall (padrão 3:00), numa caixinha só dela por cima do jogo, separada das skills e buffs. Aparece mesmo com o overlay parado.
- O botão redondo da caixinha reinicia a contagem. Clicar nele não tira o foco do jogo. Arraste a caixinha para mudar de lugar; a roda do mouse (ou "Tamanho da caixa" na aba) muda o tamanho.
- Nos últimos segundos (padrão 10, você escolhe) os números piscam em vermelho e amarelo. Dá para escolher um som para esse momento e outro para quando zerar, ou deixar só um deles (ou nenhum) com "Sem som".
- Sons novos: "Recall (voz feminina)" e "Recall (voz masculina)", falados pelas vozes do Windows no seu PC. São o padrão do cronômetro e também aparecem nas listas de som das skills e buffs.

## v1.0.33
- Barra de AP: em skins em que o preenchimento da barra tem borda preta (ex.: barra verde), a ponta do preenchimento passava por cima dos números e o AP saía errado (67 lido como 7) ou não era lido. Agora o programa ignora a borda e completa o dígito coberto.
- Maestria Arcana: o ícone do buff agora vem dentro do programa (o ragassets não tem e o da Divine Pride vem estragado).

## v1.0.32
- Aba "Skills" virou "Skills ofensivas". Buffs (ex.: Elo Celestial) só aparecem na busca da aba Buffs, e skills de ataque só na busca de Skills ofensivas, para não confundir recarga com tempo de buff. Skills de ataque que também dão status (ex.: Eclipse Lunar) ficam em Skills ofensivas.
- Buff que já estava na aba Skills fica com o nome em vermelho e o botão "Para Buffs", que move ele para a aba certa.
- Brisa Leve: os 7 ícones dos elementos (地 風 水 火 念 暗 聖) agora vêm dentro do programa, com o desenho do jogo. Antes vinham da Divine Pride com outro desenho e o buff não era achado. É só "Buff pelo nome" → Brisa Leve e pronto: sem baixar, sem marcar na tela e sem a janela "Auto".
- Buffs da Brisa Leve criados antes com os ícones errados são corrigidos sozinhos ao abrir o perfil.
- Saíram os botões Importar/Exportar da aba Buffs (e a importação automática de pacotes .zip): não são mais necessários.
- O programa já vem com a chave do aplicativo da Divine Pride, só para a configuração inicial. Depois, cada um precisa pôr a própria chave na aba Avançado (ela tem prioridade).

## v1.0.31
- Som de buff acabando não toca mais à toa no teleporte (tela preta), no alt-tab, com o jogo minimizado ou ao trocar para outro cliente (ex.: o mercador): o buff fica "segurado" no personagem onde foi visto e só conta como acabado se não voltar à tela dele.

## v1.0.30
- Visual novo: ícone novo do programa, topo com o logo e as bolinhas "Jogo encontrado" e "Overlay ativo", e barra de status embaixo.
- Uma cor de destaque só (dourado): botões lisos, caixas de marcar, deslizantes e a aba aberta em dourado.
- Skills, buffs e sons em cartões, com o estado colorido (verde = pronta, dourado = em recarga).
- Setas, lixeira e ▶ viram só o ícone (acendem com o mouse). Barra de título escura.
- O overlay mostra o ícone oficial da skill (do cliente LATAM), e não mais o print da sua barra, que às vezes vinha com o número da recarga ou a sombra do delay. Buffs também, quando o ícone oficial é igual ao do jogo. Dá para desligar na aba Aparência ("Ícone oficial do jogo").
- Barra de AP nova: degradê com brilho, marcas a cada 25%, rótulo "AP" e borda que acende quando o AP está cheio.

## v1.0.29
- Janela de busca de skill e buff: a lista de classes e a lista de skills ficam em ordem alfabética.
- Por dentro: o código foi dividido em partes menores (pasta "rocd"), o que deixa as próximas correções mais rápidas. Nada muda no uso.
- Versão em Python: na primeira vez que abrir depois de atualizar, o programa baixa sozinho a pasta "rocd" (precisa de internet).

## v1.0.28
- Sons do MyInstants: na aba Sons, em "Meus sons", clique em "MyInstants" e cole o link de qualquer som do site. O programa baixa e adiciona ele.
- Sugestão pronta: o botão "Jungle" baixa o som da Gawr Gura com um clique.

## v1.0.27
- Aba nova "Sons": som padrão de skill pronta e de buff acabando, volume, e um som diferente para cada skill e buff (ou "Sem som" para deixar mudo).
- Seis sons novos: Moeda, Gota, Campainha, Subida, Sonar e Sirene.
- "Meus sons": adicione seus próprios sons (.mp3 ou .wav) com o nome que quiser. Eles ficam só no seu PC.
- A coluna "Som" das abas Skills e Buffs foi para a aba Sons.

## v1.0.26
- Versão .exe de volta: baixe o .zip na página de versões do GitHub, extraia e abra. Não precisa mais instalar Python.
- O .exe se atualiza sozinho, igual à versão em Python. Seus dados ficam em %APPDATA%\RO Cooldown Overlay.
- Quem vem da versão em Python: extraia o .exe dentro da pasta antiga e os perfis vêm sozinhos, ou use "Trazer perfis da versão antiga" na aba Avançado.
- Corrigido o problema do .exe antigo (v1.0.17 a v1.0.20) que não lia buffs nem o AP.

## v1.0.25
- Sons de aviso: um som quando a skill fica pronta e outro quando o buff está acabando (se ele tiver duração) ou some da tela. Escolha o som (Sino, Bip, Suave, Alerta ou Sem som) e o volume na aba Aparência, em "Sons de aviso".
- Coluna "Som" nas abas Skills e Buffs para deixar mudas as skills e buffs que você não quer ouvir.

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
