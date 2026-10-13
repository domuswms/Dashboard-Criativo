# Apps Script: gravação do ClickUp na planilha

Web App ligado à planilha `banco-de-dados`. A rotina diária envia `data/clickup.json` a ele. Por ID, o script atualiza as linhas de `clickup_tarefas`, acrescenta as tarefas novas e registra em `clickup_historico` cada mudança de status. Assim o histórico cresce sem reconsultar o que já se sabe.

## Instalação (uma vez)

1. Importe `planilha/banco-de-dados.xlsx` no Google Sheets (Arquivo > Importar > Substituir planilha). Abra a planilha criada.
2. Extensões > Apps Script. Apague o conteúdo de `Código.gs` e cole `apps-script/Code.gs`.
3. Configurações do projeto: marque "Mostrar arquivo de manifesto appsscript.json" e cole o conteúdo de `apps-script/appsscript.json`. Isso fixa o fuso America/Sao_Paulo e o acesso do Web App.
4. Configurações do projeto > Propriedades do script > Adicionar: nome `TOKEN`, valor uma senha longa e aleatória (gere uma e guarde: a rotina precisa dela).
5. Implantar > Nova implantação > tipo "App da Web". Executar como: **Eu**. Quem pode acessar: **Qualquer pessoa**. Autorize as permissões e copie a URL que termina em `/exec`.
   - "Qualquer pessoa" só deixa o endereço acessível. Sem o token, toda chamada é recusada.
6. No ambiente da rotina (Claude Code na nuvem), crie as variáveis `APPS_SCRIPT_URL` (a URL `/exec`) e `APPS_SCRIPT_TOKEN` (o mesmo valor de `TOKEN`).
7. Na política de rede do ambiente, libere `script.google.com` e `script.googleusercontent.com`.

Depois de mudar o `Code.gs`, faça Implantar > Gerenciar implantações > Editar > Nova versão. A URL continua a mesma.

## Teste manual

```
APPS_SCRIPT_URL='https://script.google.com/macros/s/.../exec' APPS_SCRIPT_TOKEN='...' node scripts/coleta.mjs enviar
```

Na primeira vez, `clickup_tarefas` já vem preenchida pela planilha-modelo (carga de 13/10/2026), então o envio mostra tudo como atualizado e nenhuma tarefa nova. Mudança de status só aparece quando uma tarefa muda de fato.

## Leitura

`GET <URL>?token=...` lista as abas. `GET <URL>?token=...&aba=plano_90_dias` devolve o cabeçalho e as linhas da aba, para análise ou para o dashboard.

## Limites

- Tarefa excluída ou movida do ClickUp continua na planilha: o script só acrescenta e atualiza, nunca apaga.
- O token fica nas variáveis do ambiente e na planilha. Não coloque o token no `index.html`: o repositório é público.
