# Rotina diária de coleta do ClickUp

Roda todo dia às 7h (horário de Brasília) como rotina do Claude Code na nuvem, com o conector do ClickUp. Atualiza `data/clickup.json` no branch `main`, que é o arquivo lido pela página.

## Procedimento (para o agente da rotina)

1. Na raiz do repositório, rode:

   ```
   node scripts/coleta.mjs plano
   ```

   O script lista, para cada fonte (anuncios, compras, itajai, londrina), os parâmetros de `clickup_filter_tasks` e o arquivo onde gravar a resposta.

2. Para cada fonte, chame `clickup_filter_tasks` do conector do ClickUp **com exatamente os parâmetros impressos** e grave a resposta da ferramenta **sem alterar nada** no arquivo indicado (`.coleta/<fonte>-<página>.json`):
   - não reformate, não resuma, não traduza, não corrija nomes, não reordene, não omita tarefas;
   - o arquivo é o objeto JSON inteiro da resposta (`tasks`, `count`, `page`, `has_more`, `next_page`).

3. Rode:

   ```
   node scripts/coleta.mjs verificar
   ```

   - `BUSCAR página N`: chame a ferramenta com os parâmetros impressos e grave no arquivo indicado.
   - `ERRO`: a página gravada não confere (JSON inválido, contagem, ordem, IDs). Refaça a chamada dessa página e grave de novo.
   - Repita até aparecer `Tudo certo`.

4. Rode:

   ```
   node scripts/coleta.mjs mesclar
   ```

5. Faça commit **somente** de `data/clickup.json` no `main` e dê push:

   ```
   git add data/clickup.json
   git commit -m "Coleta ClickUp AAAA-MM-DD"
   git push origin main
   ```

   Use a data de hoje no fuso de Brasília. Se o push for recusado porque o remoto avançou, rode `git pull --rebase origin main` e tente de novo.

6. Não altere nenhum outro arquivo. Se algo falhar (conector indisponível, erro persistente na mesma página após 3 tentativas), **não faça commit**: termine relatando a fonte, a página e a mensagem de erro.

## Como funciona

- **Incremental**: as fontes já presentes no arquivo são buscadas por ordem de atualização, só até alcançar tarefas anteriores à última coleta (com 1 h de folga). Num dia comum, é uma página por fonte.
- **Completa**: quando a fonte ainda não está no arquivo, ou com `node scripts/coleta.mjs plano --completa`, a fonte é buscada inteira e substituída.
- **Limite**: 1.000 tarefas por fonte (10 páginas de 100), as atualizadas mais recentemente. É o mesmo teto que a página usava ao consultar o ClickUp direto.
- **Workspace**: `90131376764` (Domus Ecommerce). O conector enxerga dois workspaces, então o ID vai em toda chamada.

## Limites

- Na coleta incremental, uma tarefa **excluída** ou **movida** para fora da fonte continua no arquivo. Uma coleta completa (`plano --completa`) limpa esses casos.
- A página mostra o estado do ClickUp no horário da coleta, não em tempo real. O horário aparece ao lado do botão "Recarregar dados".
