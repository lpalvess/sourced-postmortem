# sourced-postmortem

[English](README.en.md) | Português

Confere um postmortem de incidente contra as evidências (logs, timeline exportada, alertas, métricas em CSV) e reprova o documento se algum horário ou número não tiver respaldo nelas. Recalcula as durações, confere timeline e ações contra os padrões de mercado e cita a fonte de cada regra. Roda em um contêiner sem rede. Também é uma skill do Claude Code (veja [SKILL.md](SKILL.md)).

## O que faz e por que existe

Um postmortem costuma ter horários e números que viram "verdade" só porque estão num documento bem escrito. A Zalando discute, em um artigo sobre análise de postmortems com IA, o problema de postmortems que deixam de servir como fonte de dados: [Dead Ends or Data Goldmines? AI-Powered Postmortem Analysis](https://engineering.zalando.com/posts/2025/09/dead-ends-or-data-goldmines-ai-powered-postmortem-analysis.html). Este projeto cria uma trava simples: todo horário da timeline precisa ter um registro nas evidências, todo número do resumo e do impacto precisa aparecer nelas (ou ser uma métrica calculada) e toda duração citada precisa bater com a recalculada a partir dos marcos.

O plugin **não gera postmortem**. Ele verifica um que já existe. O princípio é: o Claude escreve e opina, o código confere. O que dá para checar de forma determinística fica no script, e o relatório separa o que foi **conferido pelo script** do que é **opinião do modelo**.

As travas:

- horário de entrada da timeline sem registro nas evidências (E1);
- número do resumo ou do impacto que não está nas evidências (E2);
- marcos (início, detecção, mitigação, fim) faltando, fora de ordem ou com duração citada diferente da recalculada (M1 a M3);
- fuso não declarado e timeline fora de ordem (T1 e T2);
- ação sem dono, ticket, prioridade, tipo ou prazo, e ação que começa com verbo vago (A1 a A6);
- avisos para horário vago, termos de culpa e nomes próprios (T3, L1, L2).

## Arquitetura

![Arquitetura: o postmortem, as evidências e o TOML entram no contêiner sem rede; redact oculta credenciais, parse lê tudo em UTC, as regras conferem com fonte citada, e saem relatorio.json, relatorio.md e o diagrama; a skill separa o que o script conferiu da opinião do modelo](docs/diagrams/arquitetura.pt.svg)

O `scripts/verify.sh` roda o verificador em um contêiner sem rede, com as entradas somente leitura. Dentro dele, `redact` oculta credenciais antes de qualquer outra etapa, `parse_doc`, `evidence` e `timestamps` leem o documento e as evidências e normalizam tudo para UTC, e as regras E, M, T, A, O e L produzem os achados, cada um com a fonte citada. Saem `relatorio.json`, `relatorio.md` e `diagrama.excalidraw` (a cadeia "onde e por quê"). A skill apresenta o resultado com o que o script conferiu separado da opinião do modelo.

Os arquivos editáveis do diagrama ficam em [docs/diagrams/](docs/diagrams/): `arquitetura.pt.excalidraw` (abre em excalidraw.com) e o gerador `build_architecture.py`, que também produz as versões em inglês.

## Instalação

Precisa de Docker. O verificador só roda em contêiner.

### Usar como skill do Claude Code

Instale como plugin, direto deste repositório. No terminal:

```
claude plugin marketplace add lpalvess/sourced-postmortem
claude plugin install sourced-postmortem@sourced-postmortem
```

Ou, dentro de uma sessão do Claude Code:

```
/plugin install sourced-postmortem --marketplace lpalvess/sourced-postmortem
```

Depois peça, de qualquer pasta, por exemplo: "verifique o postmortem em postmortem.md com as evidências de evidencias/".

### Uso direto, sem o Claude Code

```
git clone https://github.com/lpalvess/sourced-postmortem.git
cd sourced-postmortem
scripts/verify.sh <postmortem.md> <evidencias/> [--config <arquivo.toml>] [--out <pasta>]
```

A pasta de saída padrão é `./sourced-postmortem-out/`. Ela não pode ficar dentro da pasta de evidências (o script recusa com código 2).

## Avisos

- Não há lockfile nem dependências: o verificador usa só a biblioteca padrão do Python.
- Na primeira execução o Docker baixa a imagem pinada por digest. É o único momento com rede, e quem faz isso é o Docker, não o verificador.
- A skill só funciona no Claude Code, porque precisa de Docker e de um script bash. No chat do claude.ai ela não roda.

## Exemplos de pedidos

A pasta `examples/checkout/` tem um exemplo FICTÍCIO (empresa e números inventados). É uma cópia de um caso aprovado com duas trocas no texto: `3 clientes` virou `5 clientes` e `TTD: 7 min` virou `TTD: 9 min`. Por isso ele é reprovado, o que mostra o valor do plugin.

- "Verifique o postmortem em examples/checkout/postmortem.md com as evidências de examples/checkout/evidencias." Esperado: reprovado (código 1), com E2 em "5 clientes" (esse número não está em nenhuma evidência) e M3 no TTD.
- "As durações do resumo deste postmortem batem com a timeline?" Esperado: M3, com TTD citado de 9 min e recalculado de 7 min a partir dos marcos.
- "Para qual time vai cada ação deste postmortem? Use o mapa examples/checkout/sourced-postmortem.toml." Esperado: as 3 ações, cada uma com o time pagamentos ou plataforma.

Para rodar o primeiro direto no terminal:

```
scripts/verify.sh examples/checkout/postmortem.md examples/checkout/evidencias \
  --config examples/checkout/sourced-postmortem.toml --out sourced-postmortem-out
```

A saída é `reprovado: 2 reprovações, 0 avisos.` e o código de saída é 1.

## Formato esperado do postmortem

Markdown com cabeçalhos reconhecidos por sinônimos em português e inglês, sem diferenciar maiúsculas. A lista pode ser ampliada no TOML.

| Seção | Cabeçalhos reconhecidos por padrão |
| ----- | ---------------------------------- |
| resumo | Resumo, Summary, Executive Summary, Overview, Visão geral |
| impacto | Impacto, Impact |
| causa | Causa, Causa raiz, Causas, Fatores contribuintes, Root cause, Root causes, Contributing factors, Contributors, Trigger, Gatilho |
| timeline | Linha do tempo, Timeline, Cronologia |
| acoes | Ações, Acoes, Action items, Follow-ups, Follow ups, Corrective actions, Ações corretivas, Itens de ação |

- **Timeline:** cada item de lista ou linha de tabela que começa com horário vira uma entrada. O fuso precisa estar declarado no cabeçalho ("todos os horários em UTC", "(UTC-3)", "America/Sao_Paulo") ou em cada entrada.
- **Marcos:** reconhecidos por palavra-chave ou por tag explícita, que tem prioridade: `[inicio]`, `[deteccao]`, `[reconhecimento]`, `[mitigacao]`, `[fim]`.
- **Ações:** tabela com as colunas ação, dono, ticket, prioridade, tipo, prazo e, opcionalmente, componente. Ação em lista, fora de tabela, reprova por falta de campos.
- **Causa:** cada item de lista vira um fator. Se cita um horário da timeline, fica ligado àquele evento.

### Regras do verificador

Nível `reprova` faz o script sair com código 1. Nível `aviso` aparece no relatório sem reprovar.

| ID | Nível padrão | O que reprova | Fonte |
| -- | ------------ | ------------- | ----- |
| E1 | reprova | Horário de entrada da timeline sem registro de evidência na janela de precisão (minuto) | P4 |
| E2 | reprova | Número do resumo ou do impacto que não está nas evidências nem é métrica calculada | G3 |
| M1 | reprova | Faltam marcos (inicio, deteccao, mitigacao ou fim) | G2, A2, P6, F1 |
| M2 | reprova | Marcos fora da ordem | F1 |
| M3 | reprova | Duração citada diferente da recalculada | F1, G2 |
| T1 | reprova | Fuso horário não declarado | G2, A2, I2 |
| T2 | reprova | Entradas da timeline fora de ordem cronológica | A2 |
| T3 | aviso | Horário vago ("cerca de", "aprox", "~") | A1 |
| T4 | aviso | Primeira entrada não é anterior ao início | P4, G2 |
| T5 | aviso | Data ambígua não interpretada (falta `formato_data`) | interno |
| T6 | aviso | Evidência sem fuso: foi assumido o do documento | interno |
| A1 | reprova | Ação sem dono (dono com cara de time é aviso) | G3, I4 |
| A2 | reprova | Ação sem ticket ou link | G3, P4, A2, I4 |
| A3 | reprova | Prioridade fora de P0 a P3, ou impacto ao usuário sem ação P0 ou P1 | G3, G4 |
| A4 | reprova | Tipo fora de investigate, mitigate, repair, detect, prevent (ou equivalentes em português) | G4, A2 |
| A5 | reprova | Sem prazo interpretável (prazo além da política é aviso) | P3, A3, I4 |
| A6 | reprova | Ação que começa com verbo vago (Improve, Review, Melhorar, Revisar e similares) | G4, I4 |
| O1 | aviso | Dono não é membro do time do componente no mapa, ou componente sem time | config |
| L1 | aviso | Termo de culpa (por exemplo "erro humano", "human error") | G3, G4, P5, E1 |
| L2 | aviso | Nome próprio (da lista de membros) ou @handle nas seções causa e timeline | A2 |

### Configuração

O `sourced-postmortem.toml` é opcional. Ele ajusta o perfil, os níveis, os marcos e o mapa de times. Chave desconhecida, nível inválido ou ID de regra inexistente dão código 3, com a linha do erro.

```toml
[perfil]
tolerancia_segundos = 0
prazo_dias = { SEV1 = 15, SEV2 = 30 }
limite_evidencias_mb = 50
formato_data = "DMY"     # opcional; sem ele, datas ambíguas geram T5

[niveis]
L2 = "desligada"        # time aceita nomes, como a incident.io

[marcos]
deteccao = ["pagerduty acionou"]   # soma às palavras padrão

[times.pagamentos]
componentes = ["checkout-api", "payment-worker"]
membros = ["ana.souza", "@joao"]

[times.plataforma]
componentes = ["ingress", "kafka"]
membros = ["@maria"]
```

### Códigos de saída

| Código | Significado |
| ------ | ----------- |
| 0 | Aprovado (pode ter avisos). |
| 1 | Reprovado: pelo menos uma regra de nível `reprova`. |
| 2 | Entrada inválida: arquivo ausente, documento sem timeline, evidências acima do limite, pasta de saída dentro da de evidências. |
| 3 | Configuração inválida (TOML). |
| 4 | Docker ausente ou parado. |

## Problemas comuns

| Sintoma | Código | O que fazer |
| ------- | ------ | ----------- |
| Docker ausente ou parado | 4 | Instale o Docker e confira se ele está rodando (`docker info`). |
| Seção de timeline não encontrada | 2 | Use um cabeçalho reconhecido (veja a tabela de seções), como "Linha do tempo" ou "Timeline", ou acrescente o seu no TOML. |
| Evidências acima do limite | 2 | Reduza a pasta de evidências ou aumente `limite_evidencias_mb` no TOML. |
| Config inválida | 3 | Leia a mensagem, que traz a linha do erro, e corrija a chave, o nível ou o ID de regra no TOML. |
| E1 num horário que existe no log | 1 | Veja "Linhas não interpretadas" em `relatorio.md`: provavelmente o formato do horário não é suportado ou o fuso da evidência difere do declarado. |
| E2 num número de dashboard | 1 | Números que só aparecem em imagem ou captura de tela não são conferidos. Exporte a série em CSV e coloque na pasta de evidências. |
| M1 | 1 | Faltam marcos. Use as tags `[inicio]`, `[deteccao]`, `[mitigacao]` e `[fim]` nas entradas da timeline. |
| T5 | 0 | Data ambígua (`03/04/2026`). Escreva AAAA-MM-DD ou defina `formato_data` no TOML. |

## Suporte

- Dúvidas e problemas: abra uma issue em https://github.com/lpalvess/sourced-postmortem/issues.
- Falhas de segurança: use o relato privado de vulnerabilidades, como explica o [SECURITY.md](SECURITY.md).

## Segurança por construção

O que o projeto garante, por construção:

- O verificador roda em contêiner com `--network none`: sem rede em tempo de execução, sem telemetria.
- O código e as entradas são montados somente leitura, e só a pasta de saída é gravável. O processo roda como usuário não root.
- Credenciais são ocultadas antes de qualquer outra etapa, e o relatório traz só trechos já sem credenciais.
- O postmortem e as evidências são lidos como dado, nunca executados.
- Não há dependências além da biblioteca padrão do Python.
- A imagem base do contêiner é fixada por digest.

O que o projeto NÃO garante:

- Que a causa descrita esteja certa. O script confere que horários e números existem nas evidências, não o conteúdo técnico. Isso é opinião do modelo e julgamento seu.
- Que toda credencial seja reconhecida. A ocultação segue padrões conhecidos.
- Que os trechos de evidência do relatório não tenham dados dos seus logs, como IPs e IDs (veja [PRIVACY.md](PRIVACY.md)).
- A segurança do Docker em si. O isolamento depende do Docker e do seu sistema.

## Limitações conhecidas

- Formatos de horário suportados: ISO 8601 e RFC 3339, syslog, nginx e Apache, epoch em campos JSON (`startsAt`, `endsAt`, `timestamp`, `ts`), `HH:MM` e `HH:MM:SS` com a data do contexto, e datas `DD/MM/AAAA` e `AAAA-MM-DD`. Uma linha em outro formato vai para "Linhas não interpretadas" e pode gerar um E1 falso.
- Data ambígua (`03/04/2026`) só é interpretada com `formato_data` no TOML. Sem isso, sai o aviso T5.
- `15h30` sem rótulo é lido como horário. Escreva durações com rótulo ("1h06 de duração", "TTM 66 min").
- Números que só aparecem em dashboards (imagem) não são conferidos. Exporte em CSV.
- Timeline que passa da meia-noite exige um subtítulo de data dentro dela (`### 2026-09-15`). Sem ele, a entrada depois da virada parece fora de ordem (T2).
- Nomes de pessoas só são detectados pela lista de membros do mapa de times. Sem mapa, a regra L2 só pega @handles.
- Só entra Markdown como postmortem. Não há suporte a .docx nem PDF.
- O desenho do diagrama foi gerado pelo script e não foi conferido visualmente no excalidraw.com por quem gerou. A conferência visual fica com o autor.

## O que este projeto não faz

- Não gera postmortem e não escreve o texto do documento.
- Não conduz um incidente em andamento.
- Não publica nem envia o postmortem para lugar nenhum.

## Projetos parecidos

- [dastergon/postmortem-templates](https://github.com/dastergon/postmortem-templates): coleção de modelos de postmortem, útil para quem quer um ponto de partida para escrever.
- Geradores de postmortem: são uma alternativa para quem quer gerar o documento, que é justamente o que este projeto não faz. Eles e este plugin podem ser usados em sequência: gere com um deles e confira aqui.

## Licença, créditos e privacidade

- Código sob licença MIT, veja [LICENSE](LICENSE).
- Política de privacidade: [PRIVACY.md](PRIVACY.md).
- Diagramas de arquitetura gerados por `docs/diagrams/build_architecture.py`, com formato compatível com o [Excalidraw](https://excalidraw.com).

Fontes das regras:

| Código | URL |
| ------ | --- |
| G1 | https://sre.google/sre-book/postmortem-culture/ |
| G2 | https://sre.google/sre-book/example-postmortem/ |
| G3 | https://sre.google/workbook/postmortem-culture/ |
| G4 | https://www.usenix.org/system/files/login/articles/login_spring17_09_lunney.pdf |
| P1 | https://postmortems.pagerduty.com/what_is/ |
| P2 | https://postmortems.pagerduty.com/culture/blameless/ |
| P3 | https://postmortems.pagerduty.com/culture/accountability/ |
| P4 | https://postmortems.pagerduty.com/how_to_write/writing/ |
| P5 | https://postmortems.pagerduty.com/how_to_write/effective_postmortems/ |
| P6 | https://postmortems.pagerduty.com/assets/pdf/PostmortemTemplate.pdf |
| A1 | https://www.atlassian.com/incident-management/postmortem |
| A2 | https://www.atlassian.com/incident-management/handbook/postmortems |
| A3 | https://www.atlassian.com/incident-management/postmortem/templates |
| A4 | https://www.atlassian.com/incident-management/kpis/common-metrics |
| A5 | https://www.atlassian.com/incident-management/postmortem/blameless |
| I1 | https://incident.io/guide/learn-and-improve/post-mortem-documents |
| I2 | https://incident.io/hubs/post-mortem/incident-post-mortem-template |
| I3 | https://docs.incident.io/post-incident/postmortem-templates |
| I4 | https://incident.io/blog/why-do-post-mortem-action-items-fail-how-to-make-incident-follow-ups-actually-get-done |
| I5 | https://docs.incident.io/incidents/lifecycle |
| I6 | https://docs.incident.io/insights/supported-measures |
| I7 | https://incident.io/blog/how-to-measure-mtta |
| I8 | https://incident.io/blog/blameless-post-mortems |
| F1 | https://firehydrant.com/docs/managing-incidents/incident-milestones |
| F2 | https://firehydrant.com/blog/incident-retrospective-postmortem-template/ |
| E1 | https://extfiles.etsy.com/DebriefingFacilitationGuide.pdf |
| D1 | https://github.com/dastergon/postmortem-templates |
