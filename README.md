# RO Cooldown Overlay

Mostra a **recarga (cooldown) das suas skills no meio da tela** do Ragnarok Online LATAM, no estilo do WeakAuras do World of Warcraft.

- Os ícones aparecem perto do centro da tela, com contagem regressiva e barrinha de tempo.
- Os ícones **não são clicáveis**: o clique passa direto para o jogo.
- O overlay fica "preso" à janela do Ragnarok e acompanha a janela se você movê-la.
- Banco com as skills das classes de 4ª (e herdadas da 3ª) **em português**, já com a recarga padrão.

> **Como ele funciona:** o programa só *olha a tela*, como um print ou o OBS fariam. Ele **não lê a memória do jogo, não mexe nos arquivos do jogo e não aperta teclas por você**. Mesmo assim, é um programa de terceiros: use por sua conta e risco. Não tem ligação com a Gravity.

---

## ⬇️ Como baixar e instalar (sem precisar de Python)

1. Clique em **[Releases](../../releases/latest)** (à direita, nesta página do GitHub).
2. Em **Assets**, baixe o arquivo **`RO-Cooldown-Overlay-v1.0.0-Windows.zip`**.
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
4. Clique em **▶ Iniciar overlay** e jogue. Pode minimizar o programa.

### Dicas
- **Sua classe:** escolha no campo "Sua classe" para a busca mostrar primeiro as suas skills.
- **Recarga diferente por causa de equipamento?** Digite o valor certo no campo "Recarga". O programa lembra para os próximos personagens.
- **Mover ou mudar o tamanho:** clique em **Mover / redimensionar**, arraste a caixa amarela e use a roda do mouse. Clique em **Concluir posição** no fim.
- **Contador demora a aparecer?** Em *Detecção*, ajuste "Delay global da sua build" para um valor um pouco acima do seu delay pós-conjuração.
- **Perfis:** crie um perfil por personagem. Marque "Iniciar automaticamente ao abrir" para não precisar configurar de novo.
- **Mudou a barra de lugar?** O programa procura os ícones sozinho. Se quiser forçar, clique em **Procurar na tela**.

### Opcional: Divine Pride (recarga do servidor LATAM e skill "pelo nome")
1. Crie uma conta em [divine-pride.net](https://www.divine-pride.net), entre e copie a **chave da API** no seu perfil.
2. Cole no campo **Divine Pride** do programa e clique em **Salvar e testar**.
3. Agora o botão **+ Skill pelo nome** adiciona uma skill sem precisar marcar: o programa baixa o ícone e acha na sua barra sozinho.

Cada pessoa usa a **própria chave** (não compartilhe a sua).

---

## ❓ Perguntas frequentes

**Aparece "jogo não encontrado".**
Confira em *Detecção* o campo "Título da janela do jogo contém". Ele precisa ter uma parte do nome que aparece na barra de título da janela do jogo (padrão: `Ragnarok`).

**O overlay some quando clico em outro programa.**
Desmarque "Esconder quando o jogo não estiver em foco", em *Aparência*.

**Onde ficam minhas configurações? Como mando um erro para vocês?**
Clique em **Abrir pasta de dados (logs)**. Lá ficam os perfis, o `log.txt` e o `erro.log`. Mande esses dois arquivos de log junto com a descrição do problema numa [Issue](../../issues).

**Como atualizo para uma versão nova?**
Baixe o novo `.zip`, extraia e use. Suas configurações ficam guardadas em `%APPDATA%\RO Cooldown Overlay` e não se perdem.

**Como desinstalo?**
Apague a pasta do programa. Para apagar também as configurações, apague a pasta `%APPDATA%\RO Cooldown Overlay`.

---

## 🐍 Rodar pelo Python (opcional, para quem entende)

Requer Windows 10/11 e Python 3.10 ou mais novo.

```
pip install -r requirements.txt
python ro_cooldown_overlay.py
```

Ou dê dois cliques em `iniciar.bat`. Rodando assim, os dados ficam na mesma pasta do script.

## 🛠️ Como publicar uma versão nova (para quem mantém o projeto)

1. Atualize `VERSAO` no topo do `ro_cooldown_overlay.py` e o `CHANGELOG.md`.
2. No GitHub: **Releases** → **Draft a new release** → crie a tag (ex.: `v1.0.1`) → **Publish release**.
3. A aba **Actions** gera o `.exe` sozinha (uns 5 minutos) e anexa o `.zip` na Release.

Para gerar o `.exe` no seu PC, use `build_exe.bat`.

---

## Créditos e avisos
- Nomes das skills em português: simulador [latam-tools](https://simulador.latam-tools.com.br).
- Recargas padrão: base de dados do projeto [rAthena](https://github.com/rathena/rathena) (podem diferir do servidor oficial).
- Recargas LATAM e ícones opcionais: API da [Divine Pride](https://www.divine-pride.net), com a chave de cada usuário.
- Ragnarok Online é marca da Gravity Co., Ltd. Este projeto não é oficial nem afiliado à Gravity.
- Licença: MIT (veja `LICENSE`).
