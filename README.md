<p align="center">
  <img src="[https://imgur.com/a/jz1HX2s](https://imgur.com/se86yT7)" alt="RO Cooldown Overlay Banner" width="100%">
</p>

# RO Cooldown Overlay

Mostra a **recarga (cooldown) das suas skills no meio da tela** do Ragnarok Online LATAM, no estilo do WeakAuras do World of Warcraft.


- Os ícones aparecem perto do centro da tela, com contagem regressiva e barrinha de tempo.
- Os ícones **não são clicáveis**: o clique passa direto para o jogo.
- O overlay fica "preso" à janela do Ragnarok e acompanha a janela se você movê-la.
- Banco com as skills das classes de 4ª (e herdadas da 3ª) **em português**, já com a recarga padrão.

> **Como ele funciona:** o programa só *olha a tela*, como um print ou o OBS fariam. Ele **não lê a memória do jogo, não mexe nos arquivos do jogo e não aperta teclas por você**. Mesmo assim, é um programa de terceiros: use por sua conta e risco. Não tem ligação com a Gravity.

---

## ⬇️ Como baixar e instalar (sem precisar de Python)

> ⚠️ **Não use o botão verde "Code → Download ZIP".** Ele baixa o código-fonte, que precisa de Python.
> A versão pronta para usar fica em **Releases**.

1. Clique em **[Releases](../../releases/latest)** (à direita, nesta página do GitHub).
​2. Em **Assets**, baixe o arquivo **`RO-Cooldown-Overlay-v1.0.0-Windows.zip`**.
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
​2. No programa, clique em **Marcar ícones na tela**. Volte para o jogo com as skills **prontas** (sem delay).
   A tela congela: arraste um quadrado sobre **cada skill** da sua barra de atalhos e aperte **Enter**.
3. Na lista, clique em **Buscar** em cada linha e escolha o nome da skill. A recarga já vem preenchida.
4. Clique em **▶ Iniciar overlay** e jogue. Pode minimizar o programa.

### Dicas
- **Sua classe:** escolha no campo "Sua classe" para a busca mostrar primeiro as suas skills.
- **Recarga diferente por causa de equipamento?** Digite o valor certo no campo "Recarga". O programa lembra para os próximos personagens.
- **Mover ou mudar o tamanho:** clique em **Mover / redimensionar**, arraste a caixa amarela e use a roda do mouse. Clique em **Concluir posição** no fim.
- **Contador demora a aparecer?** Em *Detecção*, ajuste "Delay global da sua build" para um valor um pouco acima do seu delay pós-conjuração.
- **Perfis:** crie um perfil por personagem. Marque "Iniciar automaticamente ao abrir" para não precisar configurar de novo.
- **Mudou a barra de lugar?** O programa procura os ícones sozinho. Se quiser forçar, clique em **Procurar na tela**.

### Opcional: Divine Pride (recarga do servidor LATAM e skill "pelo nome")

Sem isso o programa já funciona normalmente. Com a chave da Divine Pride você ganha:
- a **recarga oficial do servidor LATAM** de cada skill (em vez do valor padrão);
- o botão **+ Skill pelo nome**: escolhe a skill pela busca e o programa baixa o ícone e acha na sua barra de atalhos sozinho, sem precisar marcar na tela.

#### Como pegar sua chave da API (grátis, uns 3 minutos)

1. **Crie uma conta** na Divine Pride: abra [divine-pride.net](https://www.divine-pride.net) e clique em **Register**, no canto de cima.
   O cadastro é feito pelo fórum do site. Preencha usuário, e-mail e senha e, se pedirem, confirme pelo link que chega no seu e-mail.
2. **Entre na conta**: volte ao site e clique em **Login** (ou acesse [divine-pride.net/account/login](https://www.divine-pride.net/account/login)).
3. **Abra seu perfil**: com a conta logada, acesse [divine-pride.net/profile](https://www.divine-pride.net/profile).
4. **Copie a chave**: procure o campo **API Key** (uma sequência longa de letras e números). Se aparecer um botão para gerar a chave, clique nele primeiro. Selecione a chave e copie (**Ctrl+C**).
5. **Cole no programa**: no RO Cooldown Overlay, na parte **Divine Pride**, cole a chave no campo **Chave da API** (**Ctrl+V**) e clique em **Salvar e testar**.
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
| Outro erro / sem internet | Confira a conexão. Os detalhes ficam no `log.txt` (botão **Abrir pasta de dados**). |

---

## ❓ Perguntas frequentes

**Aparece "jogo não encontrado".**
Confira em *Detecção* o campo "Título da janela do jogo contém". Ele precisa ter uma parte do nome que aparece na barra de título da janela do jogo (padrão: `Ragnarok`).

**O overlay some quando clico em outro programa.**
Desmarque "Esconder quando o jogo não estiver em foco", em *Aparência*.

**Onde ficam minhas configurações? Como mando um erro para vocês?**
Clique em **Abrir pasta de dados (logs)**. Lá ficam os perfis, o `log.txt` e o `erro.log`. Mande esses dois arquivos de log junto com a descrição do problema numa [Issue](../../issues).

**O overlay não aparece nos meus prints, no OBS ou no Discord.**
Isso é de propósito: assim o programa não confunde o próprio overlay com os ícones do jogo. Para mostrar, marque "Aparecer em prints, gravações e lives" em *Aparência* (e deixe o overlay longe da barra de atalhos). Para um print rápido, use o botão **📷 Tirar print**.

**Como atualizo para uma versão nova?**
Baixe o novo `.zip`, extraia e use. Suas configurações ficam guardadas em `%APPDATA%\RO Cooldown Overlay` e não se perdem.

**Como desinstalo?**
Apague a pasta do programa. Para apagar também as configurações, apague a pasta `%APPDATA%\RO Cooldown Overlay`.

---

## 🐍 Rodar pelo código-fonte (opcional)

Baixou pelo botão "Code → Download ZIP"? Também funciona: extraia e dê dois cliques em **`iniciar.bat`**.
Se o computador não tiver Python, o `iniciar.bat` **instala sozinho** o Python e todas as bibliotecas na primeira vez (pelo instalador do Windows ou pelo site oficial python.org). Nas próximas vezes ele só abre o programa.
Se algo der errado, ele mostra o que fazer e salva os detalhes em `instalacao.log`.

Para quem prefere fazer à mão (Windows 10/11, Python 3.10 ou mais novo):
