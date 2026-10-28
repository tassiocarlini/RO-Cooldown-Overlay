<p align="center">
  <img src="https://i.imgur.com/se86yT7.png" alt="RO Cooldown Overlay Banner" width="100%">
</p>

# RO Cooldown Overlay

Mostra a **recarga (cooldown) das suas skills no meio da tela** do Ragnarok Online LATAM, no estilo do WeakAuras do World of Warcraft.


- Os ícones aparecem perto do centro da tela, com contagem regressiva e barrinha de tempo.
- Os ícones **não são clicáveis**: o clique passa direto para o jogo.
- O overlay fica "preso" à janela do Ragnarok e acompanha a janela se você movê-la.
- Banco com as skills das classes de 4ª (e herdadas da 3ª) **em português**, já com a recarga padrão.

> **Como ele funciona:** o programa só *olha a tela*, como um print ou o OBS fariam. Ele **não lê a memória do jogo, não mexe nos arquivos do jogo e não aperta teclas por você**. Mesmo assim, é um programa de terceiros: use por sua conta e risco. Não tem ligação com a Gravity.

---

## ⬇️ Como baixar e instalar

1. Nesta página do GitHub, clique no botão verde **Code** e depois em **Download ZIP**.
2. Clique com o botão direito no `.zip` → **Extrair tudo…** → escolha a **Área de Trabalho** ou **Documentos**.
   *(Não extraia dentro de "Arquivos de Programas".)*
3. Abra a pasta extraída e dê dois cliques em **`RO Cooldown Overlay.exe`**.

Na primeira vez, se o computador não tiver Python, o programa **instala sozinho** o Python e as bibliotecas (leva alguns minutos e mostra o progresso numa janela preta). Nas próximas vezes ele só abre.
Se algo der errado, ele mostra o que fazer e salva os detalhes em `instalacao.log`, na pasta do programa.

### "O Windows protegeu o computador"
Isso aparece porque o programa é novo e não tem assinatura paga. Clique em **Mais informações** → **Executar assim mesmo**. Só precisa fazer isso na primeira vez.

### O antivírus reclamou
O `RO Cooldown Overlay.exe` é só um atalho que abre o `ro_cooldown_overlay.py` pelo Python, e às vezes é marcado por engano. O código está todo aqui no GitHub para quem quiser conferir. Se preferir, abra pelo **`iniciar.bat`**, que faz a mesma coisa.

---
#### 🚨 MUITO IMPORTANTE: Como pegar sua chave da API (grátis, uns 3 minutos)

> ⚠️ **ATENÇÃO:** A sua chave da API é **pessoal e confidencial** (funciona como uma senha). Siga os passos abaixo para gerar a sua e **nunca a compartilhe** com ninguém.

1. **Crie uma conta** na Divine Pride: abra [divine-pride.net](https://www.divine-pride.net) e clique em **Register**, no canto de cima.
   O cadastro é feito pelo fórum do site. Preencha usuário, e-mail e senha e, se pedirem, confirme pelo link que chega no seu e-mail.
2. **Entre na conta**: volte ao site e clique em **Login** (ou acesse [divine-pride.net/account/login](https://www.divine-pride.net/account/login)).
3. **Abra seu perfil**: com a conta logada, acesse [divine-pride.net/profile](https://www.divine-pride.net/profile).
4. **Copie a chave**: procure o campo **API Key** (uma sequência longa de letras e números). Se aparecer um botão para gerar a chave, clique nele primeiro. Selecione a chave e copie (**Ctrl+C**).
5. **Cole no programa**: no RO Cooldown Overlay, na parte **Divine Pride**, cole a chave no campo **Chave da API** (**Ctrl+V**) e clique em **Salvar e testar**.
6. Se aparecer **Conectado ✓**, pronto! O programa já busca a recarga LATAM das skills dos seus perfis.

> 💡 No programa, o botão **Como pegar a chave?** abre a página do seu perfil na Divine Pride direto no navegador.

## 🎮 Como usar

1. Abra o Ragnarok em **modo janela** ou **janela sem bordas** (em tela cheia exclusiva nenhum overlay aparece).
2. No programa, clique em **Marcar ícones na tela**. Volte para o jogo com as skills **prontas** (sem delay).
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
Na própria pasta do programa. Clique em **Abrir pasta de dados (logs)**: lá ficam os perfis, o `log.txt` e o `erro.log`. Mande esses dois arquivos de log junto com a descrição do problema numa [Issue](../../issues).

**O overlay não aparece nos meus prints, no OBS ou no Discord.**
Isso é de propósito: assim o programa não confunde o próprio overlay com os ícones do jogo. Para mostrar, marque "Aparecer em prints, gravações e lives" em *Aparência* (e deixe o overlay longe da barra de atalhos). Para um print rápido, use o botão **📷 Tirar print**.

**Como atualizo para uma versão nova?**
O programa avisa sozinho quando sai uma versão nova e atualiza com um clique. Seus perfis e configurações não são apagados.
Para atualizar à mão, baixe de novo pelo **Code → Download ZIP** e copie os arquivos novos por cima da pasta antiga.

**Como desinstalo?**
Apague a pasta do programa. Suas configurações ficam dentro dela, na pasta `perfis` e no `app.json`.

---

## 🐍 Instalar o Python à mão (opcional)

Para quem prefere não usar a instalação automática (Windows 10/11, Python 3.10 ou mais novo):

*(... instruções de instalação manual ...)*

---

## 🤝 Agradecimentos

Um agradecimento especial a **Adson Leal** do [latam-tools.com.br](https://latam-tools.com.br/#/) por disponibilizar o repositório de ragassets, que foi fundamental para este projeto.
