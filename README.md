# Dashboard de gestão e rastreabilidade · Cadastro & Criativo (WeAxis)

Página única (`index.html`), em HTML, CSS e JavaScript puros, na identidade visual WeAxis (lime `#ECFC30`, ink `#212121`, Inter Tight como alternativa à fonte Greed, que não tem licença web).

Versão publicada no claude.ai: https://claude.ai/artifact/Rv7ZTCr3NUoHNUyVQhPYgQ

## Hospedagem e dados

A página fica no GitHub Pages. As tarefas do ClickUp vêm de `data/clickup.json`, que uma rotina do Claude Code atualiza todo dia às 7h (horário de Brasília) pelo conector do ClickUp, com commit no `main`. Procedimento e regras da coleta em [ROTINA.md](ROTINA.md).

O repositório é público, então nomes de tarefas, responsáveis, tags e links das quatro fontes ficam visíveis para qualquer pessoa.

Dois recursos ainda só existem dentro do claude.ai:

| Recurso | Para quê | No GitHub Pages |
|---|---|---|
| `db` | Guardar plano, lotes, fornecedores, Vonder e metas | Não funciona. Precisa de banco de dados. |
| `downloads` | Exportar CSV | Não funciona. Trocar por download via Blob. |

No GitHub Pages, os módulos que usam ClickUp funcionam. Expansão, Plano, Vonder, Lotes, metas e exportação abrem sem salvar.

## Planilha de banco de dados

`planilha/banco-de-dados.xlsx` é o modelo do banco de dados para importar no Google Sheets. Tem histórico do ClickUp (carga de 13/10/2026), plano de 90 dias, fornecedores com catálogo × cadastrados × disponíveis, Vonder 60, lotes, metas e relatório planejado × realizado. Instruções na aba LEIA-ME. Para regerar: `python3 scripts/gerar_planilha.py` (precisa de `openpyxl`) e recalcular as fórmulas com LibreOffice.

## Módulos

| Módulo | Estado | Fonte dos dados |
|---|---|---|
| Painel executivo | Pronto | ClickUp |
| Central de tarefas (lista e Kanban) | Pronto | ClickUp |
| Expansão e fornecedores | Pronto | Digitação (db) |
| Plano de 90 dias | Pronto | Digitação (db) |
| Vonder 360 | Pronto | Ficha da Vonder em Expansão + posições registradas (db) + ClickUp |
| Cadastro e pendências (lotes) | Pronto | Digitação (db) |
| Produtividade e qualidade | Pronto | ClickUp + lotes |
| Relatórios | Pronto | Todos os anteriores; exporta CSV |
| Processos e POPs | **Falta fazer** | — |

Itens do briefing original ainda sem módulo: treinamento do Tiny ERP, conteúdo e vídeos, permissões por perfil (diretoria × operação).

## ClickUp

Workspace `Domus Ecommerce` (`90131376764`). A rotina consulta com `clickup_filter_tasks`, incluindo concluídas, por ordem de atualização, e guarda até 1.000 tarefas por fonte (10 páginas de 100), as atualizadas mais recentemente. A página mostra o estado do horário da coleta, não em tempo real.

Fontes selecionáveis na página:

| Fonte | Lista ou pasta |
|---|---|
| Anúncios (Criativo) | lista `901312757364` |
| Compras | lista `901312319816` |
| Pasta Itajaí-SC | pasta `90137504399` |
| Pasta Londrina-PR | pasta `90137507791` |

Regras de leitura:
- **Filial** vem das tags `itajaí` e `londrina`. Sem tag, aparece "Sem filial".
- **Concluída**: tarefa com data de fechamento ou status contendo "conclu".
- **Atrasada**: em aberto com prazo anterior a hoje. Tarefas sem prazo não entram na conta, e a página informa quantas estão sem prazo.
- **Parada**: em aberto sem atualização há mais de 14 dias.
- **Aguardando informações**: tarefa em aberto com a tag `aguardando informações`.
- Status observados em Anúncios: solicitações, precificação, fotos, cadastrando, subindo anúncios, concluído.

## Dados guardados (db)

| Caminho | Conteúdo |
|---|---|
| `fornecedores` | Ficha: filial, modelo, informado, validado, elegível, priorizado, ERP, publicado |
| `plano` | Atividades do plano, com histórico que só cresce |
| `config/plano` | Data de início do plano |
| `vonder_hist` | Posições registradas da Vonder (documento por data) |
| `config/vonder` | Meta, pendências por motivo, critérios de priorização |
| `lotes` | Lotes de cadastro, checklist e histórico |
| `config/prod` | Metas e pesos de complexidade |

## Fórmulas

- **Tarefas concluídas (simples)**: concluídas ÷ total, sem peso.
- **Progresso ponderado do plano**: soma(% × peso) ÷ soma dos pesos. Atividades canceladas ficam fora.
- **Cobertura do catálogo**: publicados ÷ elegíveis validados. O catálogo bruto não entra.
- **Taxa de devolução**: lotes cuja 1ª conferência foi devolvida ÷ lotes analisados. O primeiro resultado nunca é sobrescrito, para não contar o mesmo evento duas vezes.
- **Aprovação na 1ª conferência**: complemento da taxa de devolução.
- **Retrabalho**: lotes concluídos devolvidos ao menos uma vez ÷ lotes concluídos.
- **Cumprimento de prazo**: concluídas dentro do prazo ÷ concluídas com prazo válido.
- **Ritmo da Vonder**: variação de publicados entre a primeira e a última posição registrada, por semana. Exige 7 dias ou mais de série.
- **Conclusão projetada**: restante ÷ ritmo real.
- **Sem dados suficientes**: aparece sempre que falta base. Nunca se exibe zero no lugar.

## Regras de negócio implementadas

- **Lote**: só aprova com os itens obrigatórios do tipo (simples, kit, variações) em Conforme ou Não aplicável, ou com exceção justificada, que fica no histórico.
- **Devolução** exige motivo e departamento que corrige. **Conclusão** exige lote aprovado.
- **Tempo do lote**: conta a partir da entrada na fila. O período em que o lote está devolvido é atribuído a quem corrige. O restante é do Cadastro & Criativo.
- **Plano**: atividade bloqueada exige motivo, quem age em seguida e data de acompanhamento.
- **Metas** (prazo, retrabalho, devolução, Vonder) ficam vazias até a gestão aprovar.
- Os 16.000 SKUs da Vonder e os 2.000 trabalhados são **referência inicial a validar**.

## Limites conhecidos

- Poucas tarefas de Anúncios têm prazo no ClickUp, então "atrasadas" tem pouca base.
- O ClickUp não traz produtos cadastrados ou não anunciados por plataforma, nem SKUs do portfólio do fornecedor. Esses indicadores do briefing precisam de exportação do Tiny ou das planilhas dos fornecedores.
- Não há histórico de mudança de status das tarefas do ClickUp; só o estado atual.
- Na coleta incremental, tarefa excluída ou movida para fora da fonte continua no arquivo até uma coleta completa (ver ROTINA.md).
- A série semanal da Vonder depende de alguém registrar a posição com regularidade.
- Sem permissão por perfil: quem tem acesso de edição ao link altera os dados.

## Para continuar em um novo chat

1. Abra um chat novo e cole o link da página publicada.
2. Diga que quer continuar o projeto e anexe este README.
3. Próximo passo planejado: módulo **Processos e POPs** (código, nome, categoria, responsável, revisor, status, versão, datas, link, observações; status: Não iniciado, Em elaboração, Em revisão, Aguardando aprovação, Aprovado, Publicado, Revisão necessária). Depois, treinamento do Tiny ERP e conteúdo e vídeos.
