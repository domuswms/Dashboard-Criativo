# Rotina diária de coleta do ClickUp

Roda todo dia às 7h (horário de Brasília) como rotina do Claude Code na nuvem. Atualiza `data/clickup.json` no branch `main`, que é o arquivo lido pela página.

Há dois modos de coleta:

- **Automático (preferido)**: o próprio script busca na API do ClickUp com um token pessoal (`CLICKUP_TOKEN`). O agente só roda comandos, sem copiar dados.
- **Manual (reserva)**: o agente chama o conector do ClickUp e grava cada resposta em arquivo. Vale só enquanto o `CLICKUP_TOKEN` não estiver configurado. É frágil: o agente precisa reescrever dezenas de KB de JSON por dia, e em 16/10/2026 essa cópia foi interrompida no meio e o dia ficou sem coleta.

## Prompt da rotina

Texto para colar na rotina "Dash Criativo". O procedimento fica todo neste arquivo, para não haver duas versões.

```
Você executa a coleta diária do ClickUp do repositório domuswms/Dashboard-Criativo.
Trabalhe sem pedir confirmação. Na raiz do repositório, leia ROTINA.md e siga exatamente
a seção "Procedimento". Termine com um resumo de 3 linhas: modo usado (automático ou manual),
tarefas novas e alteradas por fonte, e qualquer falha (inclusive do envio à planilha).
```

## Procedimento (para o agente da rotina)

1. Na raiz do repositório, rode:

   ```
   NODE_USE_ENV_PROXY=1 node scripts/coleta.mjs auto
   ```

   - Terminou com `data/clickup.json gravado`: siga para o passo 2.
   - `Coleta automática indisponível: CLICKUP_TOKEN não definido`: faça o **modo manual** (abaixo) e depois siga para o passo 2.
   - `ERRO ...`: **não faça commit**. Termine relatando a mensagem (ela traz a fonte e a página).

2. Envie os dados à planilha (Apps Script):

   ```
   NODE_USE_ENV_PROXY=1 node scripts/coleta.mjs enviar
   ```

   - `Planilha atualizada: ...`: está certo.
   - `Envio à planilha pulado`: as variáveis `APPS_SCRIPT_URL` e `APPS_SCRIPT_TOKEN` não estão definidas. Siga em frente.
   - `ERRO ...`: a falha é só da planilha. Não refaça a coleta. Siga para o commit e **mencione o erro** no resumo final.

   Instalação do Apps Script em [apps-script/README.md](apps-script/README.md).

3. Faça commit **somente** de `data/clickup.json` e envie ao `main`. A sessão da rotina pode começar num branch `claude/...`, por isso o push usa `HEAD:main`:

   ```
   git add data/clickup.json
   git commit -m "Coleta ClickUp AAAA-MM-DD"
   git push origin HEAD:main
   ```

   Use a data de hoje no fuso de Brasília. Se o push for recusado porque o remoto avançou, rode `git pull --rebase origin main` e repita `git push origin HEAD:main`. Nunca use `--force`.

4. Não altere nenhum outro arquivo. A pasta `.coleta/` é de trabalho e fica fora do git (`.gitignore`).

### Modo manual (só sem `CLICKUP_TOKEN`)

1. Rode `node scripts/coleta.mjs plano`. O script lista, para cada fonte (anuncios, compras, itajai, londrina), os parâmetros de `clickup_filter_tasks` e o arquivo onde gravar a resposta.
2. Para cada fonte, chame `clickup_filter_tasks` do conector do ClickUp **com exatamente os parâmetros impressos** e grave a resposta da ferramenta **sem alterar nada** no arquivo indicado (`.coleta/<fonte>-<página>.json`):
   - não reformate, não resuma, não traduza, não corrija nomes, não reordene, não omita tarefas;
   - o arquivo é o objeto JSON inteiro da resposta (`tasks`, `count`, `page`, `has_more`, `next_page`).
3. Rode `node scripts/coleta.mjs verificar`.
   - `BUSCAR página N`: chame a ferramenta com os parâmetros impressos e grave no arquivo indicado.
   - `ERRO`: a página gravada não confere (JSON inválido, contagem, ordem, IDs). Refaça a chamada dessa página e grave de novo.
   - Repita até aparecer `Tudo certo`. Erro persistente na mesma página após 3 tentativas, ou conector indisponível: **não faça commit** e termine relatando a fonte, a página e a mensagem de erro.
4. Rode `node scripts/coleta.mjs mesclar`.

## Configuração do modo automático (uma vez)

1. **Token do ClickUp**: no ClickUp, avatar > Settings > Apps > API Token > Generate. O token tem o acesso da pessoa que o gera, então use uma conta que enxergue as quatro fontes. Ele começa com `pk_`.
2. **Ambiente da rotina** (Claude Code na nuvem, ambiente usado pela rotina "Dash Criativo"): crie a variável `CLICKUP_TOKEN` com o token. Não grave o token em nenhum arquivo do repositório: ele é público.
3. **Rede do ambiente**: libere `api.clickup.com`. Para o envio à planilha, libere também `script.google.com` e `script.googleusercontent.com`.
4. Teste numa sessão do mesmo ambiente: `NODE_USE_ENV_PROXY=1 node scripts/coleta.mjs auto --completa`. As quatro fontes devem terminar em `OK`.

Na primeira execução com o token, rode `auto --completa`. Isso refaz o arquivo inteiro pela API e limpa tarefas excluídas ou movidas que tenham ficado da coleta incremental.

Para trocar o token (ex.: a pessoa saiu da empresa), gere outro e substitua a variável no ambiente.

## Como funciona

- **Incremental**: as fontes já presentes no arquivo são buscadas por ordem de atualização, só até alcançar tarefas anteriores à última coleta (com 1 h de folga). Num dia comum, é uma página por fonte.
- **Completa**: quando a fonte ainda não está no arquivo, ou com `auto --completa` (ou `plano --completa` no modo manual), a fonte é buscada inteira e substituída.
- **Limite**: 1.000 tarefas por fonte (10 páginas de 100), as atualizadas mais recentemente. É o mesmo teto que a página usava ao consultar o ClickUp direto.
- **Mesmo formato nos dois modos**: o modo automático chama a mesma consulta do conector (`/team/{workspace}/task`, com concluídas e subtarefas, por ordem de atualização) e grava cada página no formato da resposta do conector. A validação (`verificar`) e a mescla são as mesmas.
- **Novas tentativas**: no modo automático, cada página é tentada até 3 vezes (falha de rede, erro do ClickUp ou página que não confere). Com token inválido (HTTP 401), para na hora.
- **Workspace**: `90131376764` (Domus Ecommerce). O ID vai em toda chamada.

## Limites

- Na coleta incremental, uma tarefa **excluída** ou **movida** para fora da fonte continua no arquivo. Uma coleta completa (`--completa`) limpa esses casos.
- A página mostra o estado do ClickUp no horário da coleta, não em tempo real. O horário aparece ao lado do botão "Recarregar dados".
- Se a coleta falhar, a página continua com os dados do último dia que deu certo.
