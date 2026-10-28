# RO Cooldown Overlay

Mostra a **recarga (cooldown) das suas skills no meio da tela** do Ragnarok Online LATAM, no estilo do WeakAuras do World of Warcraft.

![Exemplo do overlay no jogo](docs/exemplo.png)

- Os ícones aparecem perto do centro da tela, com contagem regressiva e barrinha de tempo.
- Os ícones **não são clicáveis**: o clique passa direto para o jogo.
- O overlay fica "preso" à janela do Ragnarok e acompanha a janela se você movê-la.
- Banco com **todas** as skills das classes de 4ª (e herdadas), já com a recarga padrão e os ícones de buff. Com a chave da Divine Pride, os nomes aparecem em português do LATAM; a busca também aceita o nome em inglês.

> **Como ele funciona:** o programa só *olha a tela*, como um print ou o OBS fariam. Ele **não lê a memória do jogo, não mexe nos arquivos do jogo e não aperta teclas por você**. Mesmo assim, é um programa de terceiros: use por sua conta e risco. Não tem ligação com a Gravity.

---

## ⬇️ Como baixar e instalar (sem precisar de Python)

> ⚠️ **Não use o botão verde "Code → Download ZIP".** Ele baixa o código-fonte, que precisa de Python.
> A versão pronta para usar fica em **Releases**.

1. Clique em **[Releases](../../releases/latest)** (à direita, nesta página do GitHub).
2. Em **Assets**, baixe o arquivo **`RO-Cooldown-Overlay-v…-Windows.zip`** (o da versão mais nova).
3. Clique com o botão direito no `.zip` → **Extrair tudo…** → escolha a **Área de Trabalho** ou **Documentos**.
   *(Não extraia dentro de "Arquivos de Programas".)*
4. Abra a pasta extraída e dê dois cliques em **`RO Cooldown Overlay.exe`**.

### "O Windows protegeu o computador"
Isso aparece porque o programa é novo e não tem assinatura paga. Clique em **Mais informações** → **Executar assim mesmo**. Só precisa fazer isso na primeira vez.

### O antivírus reclamou
Programas feitos em Python e empacotados em `.exe` às vezes são marcados por engano. O código está todo aqui no GitHub para quem quiser conferir. Se preferir, rode pelo Python (veja mais abaixo).

---

## 🎮 Como usar

1. Abra o Ragnarok em **modo janela** ou **janela sem bordas** (em tela cheia exclusiva nenhum overlay aparece).
2. No programa, clique em **Marcar ícones na tela**. Volte para o jogo com as skills **prontas** (sem delay).
   A tela congela: arraste um quadrado sobre **cada skill** da sua barra de atalhos e aperte **Enter**.
3. Na lista, clique em **Buscar** em cada linha e escolha o nome da skill. A recarga já vem preenchida.
4. Clique em **Iniciar overlay** e jogue. Pode minimizar o programa.

### Dicas
- **Sua classe:** escolha no campo "Sua classe" para a busca mostrar primeiro as suas skills.
- **Recarga diferente por causa de equipamento?** Digite o valor certo no campo "Recarga". O programa lembra para os próximos personagens.
- **Barra de AP:** na aba *Aparência*, seção *Barra de AP*, marque **Mostrar a barra de AP** e deixe a janela *Informações básicas* aberta no jogo (compacta ou expandida). O programa acha o AP sozinho, mesmo se você mover a janela. A barra aparece colada acima dos ícones, do mesmo tamanho da faixa, e dá para ajustar a **altura** e a **cor**. Se a busca automática não funcionar no seu jogo, use **Marcar à mão**.
- **Visual dos ícones:** na aba *Aparência*, seção *Ícones*, ajuste o **Tamanho do ícone** e o **Espaço entre ícones**, escolha o **Estilo** (Moderno, Minimalista ou Clássico), ligue a **caixa escura atrás dos ícones** e, se quiser, o **nome embaixo de cada ícone**. Parando o mouse em cima de qualquer opção aparece uma explicação.
- **Mover ou mudar o tamanho:** clique em **Mover / redimensionar**, arraste a caixa amarela e use a roda do mouse. Clique em **Concluir posição** no fim.
- **Contador demora a aparecer?** Na aba *Avançado*, ajuste "Delay global da sua build (segundos)" para um valor um pouco acima do seu delay pós-conjuração.
- **Perfis:** crie um perfil por personagem. Marque "Iniciar automaticamente ao abrir" para não precisar configurar de novo.
- **Mudou a barra de lugar?** O programa procura os ícones sozinho. Se quiser forçar, clique em **Procurar na tela**.

### Buffs: saber se o buff está ativo
Na aba **Buffs** você escolhe quais buffs quer vigiar. O overlay mostra o ícone do buff com **borda verde** quando ele está ativo e, quando ele cai, **apagado, com um "!" grande e borda piscando em vermelho e amarelo**.

1. **Com a chave da Divine Pride** (aba Avançado): clique em **Buff pelo nome** e escolha o buff (ex.: Brisa Leve). O programa baixa todas as versões do ícone (os 7 elementos) e, quando o buff estiver ativo no jogo, acha o ícone na tela e ajusta o tamanho sozinho. Pronto: pule para o passo 4.
2. **Sem a chave:** no jogo, deixe o buff **ativo**, clique em **Marcar na tela**, dê um nome e marque o ícone dele na coluna de buffs (à direita da tela).
3. **Buff que muda de ícone** (como a Brisa Leve de cada elemento): depois do "Buff pelo nome", a janela **Auto** abre sozinha para confirmar cada versão com a sua tela (alguns ícones do site podem ser diferentes dos do LATAM). Sem a chave, clique em **Auto** na linha do buff e, no jogo, use o buff com cada elemento, um depois do outro. Cada versão nova é reconhecida e salva sozinha; no fim, clique em **Concluir**. (Também dá para marcar uma versão à mão com **+ Ícone**.) O buff conta como ativo se **qualquer** versão aparecer, e o overlay mostra a versão que está ativa no momento.
4. Use as setas **▲▼** de cada linha para mudar a ordem dos buffs no overlay (como nas skills).
5. Opcional: em **Mostrar no overlay**, escolha *Só quando faltar* para o ícone aparecer só como alerta. Em **Duração (s)**, coloque a duração do buff para ver a contagem regressiva.
6. Opcional: **Área dos buffs** (um retângulo cobrindo a coluna de buffs). Sem marcar, o programa procura no lado direito da janela do jogo, onde o RO mostra os buffs.

**Compartilhar buffs com amigos:** depois de configurar, clique em **Exportar** (aba Buffs) para gerar um arquivo `buffs_....zip`. Quem receber só precisa **colocar o arquivo na pasta do programa** (junto do `.exe`) e abrir o programa: os buffs e todas as versões dos ícones entram sozinhos em cada perfil, uma vez só (versões repetidas são ignoradas). Também dá para usar o botão **Importar**. Os ícones são imagens do jogo capturadas da sua tela, então compartilhe o arquivo só em particular (Discord, por exemplo) e **não suba no GitHub**.

> A contagem da duração começa quando o ícone aparece. Se você renovar o buff antes de ele acabar, o ícone não some e a contagem não reinicia.

### De onde vêm os ícones e nomes
O programa baixa os ícones dos buffs e das skills e os nomes em português primeiro do **ragassets** (latam-tools), que tira tudo do próprio cliente LATAM e **não precisa de chave**. Cada arquivo é baixado uma vez e fica no seu PC. Se o ragassets estiver fora do ar, o programa usa a Divine Pride (se você tiver a chave), o banco local e a captura da tela. Dá para desligar o ragassets na aba *Avançado*.

### Opcional: Divine Pride (recarga do servidor LATAM e skill "pelo nome")

Sem isso o programa já funciona normalmente. Com a chave da Divine Pride você ganha:
- a **recarga oficial do servidor LATAM** de cada skill (em vez do valor padrão);
- o botão **Skill pelo nome**: escolhe a skill pela busca e o programa baixa o ícone e acha na sua barra de atalhos sozinho, sem precisar marcar na tela.

#### Como pegar sua chave da API (grátis, uns 3 minutos)

1. **Crie uma conta** na Divine Pride: abra [divine-pride.net](https://www.divine-pride.net) e clique em **Register**, no canto de cima.
   O cadastro é feito pelo fórum do site. Preencha usuário, e-mail e senha e, se pedirem, confirme pelo link que chega no seu e-mail.
2. **Entre na conta**: volte ao site e clique em **Login** (ou acesse [divine-pride.net/account/login](https://www.divine-pride.net/account/login)).
3. **Abra seu perfil**: com a conta logada, acesse [divine-pride.net/account/profile](https://www.divine-pride.net/account/profile).
4. **Copie a chave**: procure o campo **API Key** (uma sequência longa de letras e números). Se aparecer um botão para gerar a chave, clique nele primeiro. Selecione a chave e copie (**Ctrl+C**).
5. **Cole no programa**: no RO Cooldown Overlay, na aba **Avançado**, parte **Divine Pride**, cole a chave no campo **Chave da API** (**Ctrl+V**) e clique em **Salvar e testar**.
6. Se aparecer **Conectado ✓**, pronto! O programa já busca a recarga LATAM das skills dos seus perfis.

> No programa, o botão **Como pegar a chave?** abre a página do seu perfil na Divine Pride direto no navegador.

#### Cuidados com a chave
- A chave é **pessoal**: cada pessoa usa a sua. **Não poste nem envie a sua para ninguém**.
- Ela fica guardada só no seu computador (`app.json`, na pasta de dados do programa).
- O programa consulta **somente as skills que você usa**, uma de cada vez, e guarda as respostas no seu PC por 30 dias, seguindo as regras de uso da API da Divine Pride. Ele não baixa o banco de dados inteiro.

#### Deu erro?
| Mensagem | O que fazer |
|---|---|
| `Erro: chave da API inválida (401)` | A chave foi copiada errada ou incompleta. Copie de novo do seu perfil, sem espaços, e clique em **Salvar e testar**. |
| `Erro: limite de pedidos da API` ou `429` | Muitos pedidos em pouco tempo. Espere alguns minutos e tente de novo. |
| `Erro: skill não encontrada (404)` | Essa skill não existe na base do LATAM da Divine Pride. Use **Marcar ícones na tela** para ela. |
| Outro erro / sem internet | Confira a conexão. Os detalhes ficam no `log.txt` (botão **Pasta de dados**). |

---

## ❓ Perguntas frequentes

**Aparece "jogo não encontrado".**
Confira na aba *Avançado* o campo "Nome da janela do jogo". Ele precisa ter uma parte do nome que aparece na barra de título da janela do jogo (padrão: `Ragnarok`).

**O overlay some quando clico em outro programa.**
Desmarque "Esconder com o jogo fora de foco", na aba *Aparência* (seção *Quando mostrar*).

**Onde ficam minhas configurações? Como mando um erro para vocês?**
Clique em **Pasta de dados**, no rodapé do programa. Lá ficam os perfis, o `log.txt` e o `erro.log`. Mande esses dois arquivos de log junto com a descrição do problema numa [Issue](../../issues).

**O overlay não aparece nos meus prints, no OBS ou no Discord.**
Isso é de propósito: assim o programa não confunde o próprio overlay com os ícones do jogo. Para mostrar, marque "Aparecer em prints e lives" na aba *Aparência* (e deixe o overlay longe da barra de atalhos). Para um print rápido, use o botão **Tirar print**.

**Como atualizo para uma versão nova?**
O programa avisa sozinho: ao abrir (no máximo 1 vez por dia) ele confere a página de Releases e, se houver versão nova, mostra as novidades e oferece **Atualizar agora** — ele baixa, instala e abre de novo sozinho. Também dá para clicar em **Verificar atualizações** na aba *Avançado*. Suas configurações ficam guardadas e não se perdem. (Para quem está numa versão anterior à 1.0.17, a primeira atualização ainda é à mão: baixe o novo `.zip` e extraia por cima.)

**Como desinstalo?**
Apague a pasta do programa. Para apagar também as configurações, apague a pasta `%APPDATA%\RO Cooldown Overlay`.

---

## 🐍 Rodar pelo código-fonte (opcional)

Baixou pelo botão "Code → Download ZIP"? Também funciona: extraia e dê dois cliques em **`RO Cooldown Overlay.exe`** (o lançador, com o ícone do programa). Ele abre o `ro_cooldown_overlay.py` sem janela preta. Se preferir, o **`iniciar.bat`** faz o mesmo.
Se o computador não tiver Python, o lançador chama o `iniciar.bat`, que **instala sozinho** o Python e todas as bibliotecas na primeira vez (pelo instalador do Windows ou pelo site oficial python.org). Nas próximas vezes ele só abre o programa.
Se algo der errado, ele mostra o que fazer e salva os detalhes em `instalacao.log`.

Para quem prefere fazer à mão (Windows 10/11, Python 3.10 ou mais novo):

```
pip install -r requirements.txt
python ro_cooldown_overlay.py
```

Rodando assim, os dados ficam na mesma pasta do script.

## 🛠️ Como publicar uma versão nova (para quem mantém o projeto)

1. Atualize `VERSAO` no topo do `ro_cooldown_overlay.py` e o `CHANGELOG.md`.
2. No GitHub: **Releases** → **Draft a new release** → crie a tag (ex.: `v1.0.1`) → **Publish release**.
3. A aba **Actions** gera o `.exe` sozinha (uns 5 minutos) e anexa o `.zip` na Release.

Para gerar o `.exe` completo no seu PC, use `build_exe.bat`. O código do lançador (`RO Cooldown Overlay.exe`) está em `lancador/`, com o comando para compilar.

---

## Créditos e avisos
- Nomes das skills em português: simulador [latam-tools](https://simulador.latam-tools.com.br).
- Recargas padrão: base de dados do projeto [rAthena](https://github.com/rathena/rathena) (podem diferir do servidor oficial).
- Ícones de skills e de buffs e nomes em português (fonte principal, baixados por cada usuário enquanto usa): [ragassets](https://github.com/adsonpleal/ragassets), de Adson Leal, que extrai os dados do próprio cliente LATAM. Nada disso fica guardado neste repositório.
- Recargas LATAM e ícones de reserva: API da [Divine Pride](https://www.divine-pride.net), com a chave de cada usuário.
- Ragnarok Online é marca da Gravity Co., Ltd. Este projeto não é oficial nem afiliado à Gravity.
- Licença: MIT (veja `LICENSE`).
