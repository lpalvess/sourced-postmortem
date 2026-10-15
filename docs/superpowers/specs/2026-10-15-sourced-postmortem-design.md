# sourced-postmortem: spec de design (v1)

Data: 2026-10-15. Status: aguardando revisão do autor.

## 1. Objetivo

Plugin do Claude Code que **verifica** postmortems de incidente, não os gera. Ele reprova o documento quando um horário ou número não tem respaldo nas evidências, recalcula as métricas de tempo e confere timeline e ações contra os padrões de mercado (Google SRE, PagerDuty, Atlassian, incident.io, FireHydrant, Etsy). Cada regra cita a fonte.

Princípio: o Claude escreve e opina, o código confere. Tudo o que pode ser checado de forma determinística fica no script.

### Sucesso

- Um postmortem com horário ou número inventado é reprovado, com o local exato do problema.
- As durações citadas no texto batem com as recalculadas, ou o documento é reprovado.
- O relatório deixa separado o que foi **conferido pelo script** e o que é **opinião do modelo**.
- Publicação aprovada no diretório da Anthropic, seguindo o modelo da nota 07 do vault.

### Fora da v1

CI, entradas .docx/PDF, geração de postmortem, perfis prontos por fonte, os critérios de script que ficaram de fora do núcleo (glossário, siglas, lições em 3 partes, recorrência, prazo de publicação, dados de cliente).

## 2. Entradas e saídas

Entradas:

- `postmortem.md`: o documento, em Markdown.
- `evidencias/`: pasta com qualquer mistura de logs em texto (syslog, nginx, journalctl, kubectl logs), timeline exportada (incident.io, FireHydrant, Slack), alertas (JSON do Alertmanager) e métricas (CSV), ou texto colado salvo em `.txt`.
- `sourced-postmortem.toml` (opcional): ajustes do perfil e mapa de times.

Saídas (na pasta indicada, padrão `./sourced-postmortem-out/`):

- `relatorio.json`: achados estruturados.
- `relatorio.md`: o mesmo relatório para leitura.
- `diagrama.excalidraw`: cadeia "onde e por quê".

Execução: `${CLAUDE_SKILL_DIR}/scripts/verify.sh <postmortem.md> <evidencias/> [--config arquivo.toml] [--out pasta]`.

## 3. Arquitetura

Python 3.12, **só biblioteca padrão**: sem dependências e sem lockfile. Assim não aparece a retenção `LOCKFILE_AUTO_INSTALL` que o sourced-carousel teve.

`scripts/verify.sh` roda `docker run --rm --network none` com a imagem `python:3.12-slim` pinada por digest. A entrada é montada só leitura, a pasta de saída é a única gravável e o processo roda como usuário não root.

Módulos (`verifier/`), cada um testável sozinho:

| Módulo | Responsabilidade | Depende de |
|---|---|---|
| `redact.py` | Oculta credenciais em qualquer texto antes do resto do pipeline | nada |
| `timestamps.py` | Acha e normaliza horários em texto livre para UTC | nada |
| `parse_doc.py` | Markdown para modelo: metadados, seções, timeline, marcos, ações, fatores, números e durações citados | `timestamps` |
| `evidence.py` | Indexa evidências em registros (horário UTC, arquivo, linha, trecho, números) | `redact`, `timestamps` |
| `config.py` | Perfil padrão embutido + TOML do usuário + mapa de times; valida tudo | nada |
| `metrics.py` | Calcula TTD, TTA, TTM, TTR e duração do impacto a partir dos marcos | nada |
| `rules/` | `evidencias.py`, `metricas.py`, `timeline.py`, `acoes.py`, `linguagem.py`, `donos.py`; cada regra recebe o modelo e devolve achados | modelos acima |
| `excalidraw.py` | Gera o diagrama a partir do modelo já verificado | modelo + achados |
| `report.py` | Escreve `relatorio.json` e `relatorio.md` | achados |
| `cli.py` | Orquestra e define o código de saída | todos |

Formato de um achado:

```json
{"id": "E1", "nivel": "reprova", "local": "postmortem.md:42",
 "mensagem": "Horário 14:54 UTC sem correspondência nas evidências",
 "fonte": ["P4"], "evidencia": null}
```

## 4. Reconhecimento do documento

### Seções

O script reconhece cabeçalhos por sinônimos PT/EN, sem diferenciar maiúsculas, e a lista pode ser ampliada no TOML:

- resumo: Resumo, Summary, Executive Summary, Overview
- impacto: Impacto, Impact
- causa: Causa, Causa raiz, Fatores contribuintes, Root cause(s), Contributing factors, Contributors, Trigger
- timeline: Linha do tempo, Timeline
- acoes: Ações, Action items, Follow-ups, Corrective actions

### Fuso declarado

O fuso é aceito em duas formas: no cabeçalho da timeline ou do documento ("todos os horários em UTC", "all times UTC", "(UTC-3)", "America/Sao_Paulo"), ou como sufixo em cada entrada.

### Entradas da timeline

Cada item de lista ou linha de tabela que começa com horário vira uma entrada. A data vem da própria entrada ou, se faltar, da data do cabeçalho ou dos metadados.

### Marcos

Os marcos são reconhecidos por palavras-chave na entrada, e a lista pode ser ajustada no TOML:

| Marco | Palavras padrão |
|---|---|
| inicio | início do impacto, impacto começa, impact started, outage begins, started |
| deteccao | detectado, detecção, alerta disparou, detected, alert fired, reported |
| reconhecimento | reconhecido, ack, acknowledged, on-call assumiu |
| mitigacao | mitigado, mitigação, mitigated, outage mitigated |
| fim | fim do impacto, impacto encerrado, resolvido, outage ends, resolved, impact ended |

Também vale uma tag explícita, que tem prioridade sobre as palavras: `[inicio]`, `[deteccao]`, `[reconhecimento]`, `[mitigacao]`, `[fim]`.

### Ações

As ações vêm de uma tabela na seção de ações. As colunas são reconhecidas por sinônimos:

- ação/action
- dono/owner
- ticket/bug/link
- prioridade/priority
- tipo/type
- prazo/due
- componente/component (opcional)

Uma ação em lista, fora de tabela, é reprovada por falta de campos (A1 a A5 se aplicam).

### Fatores

Cada item de lista da seção de causa vira um fator. Se o texto do fator cita um horário presente na timeline, o fator fica ligado àquele evento.

### Números citados

O script extrai números com unidade das seções resumo e impacto: %, usuários, requisições, erros, pedidos, R$, ms, s, min, h. Ignora números colados em letras (SEV1, P0, v2.3), datas e horários.

### Durações citadas

O script extrai durações como "66 min", "1h06", "durou 47 minutos" e "for 66 minutes", e associa cada uma à métrica do rótulo próximo (TTD, TTA, TTM, TTR, duração, impacto).

## 5. Extração de horários (`timestamps.py`)

Formatos da v1:

- ISO 8601 e RFC 3339, com ou sem fração e offset
- syslog: `Oct 15 14:54:01`, com o ano vindo da data do incidente
- nginx/Apache: `[15/Oct/2026:14:54:01 +0000]`
- epoch em segundos e milissegundos em campos JSON conhecidos (`startsAt`, `endsAt`, `timestamp`, `ts`)
- `HH:MM` e `HH:MM:SS`, com a data vinda do contexto
- datas `DD/MM/AAAA` e `AAAA-MM-DD`

Regras:

- Uma data ambígua (`03/04/2026`) só é interpretada se `formato_data` estiver no TOML (`"DMY"` ou `"MDY"`). Sem isso, não é interpretada e gera o aviso T5.
- Uma evidência sem fuso usa o fuso declarado no documento e gera o aviso T6.
- Cada horário guarda sua **precisão**: minuto ou segundo.

## 6. Ocultação de credenciais (`redact.py`)

Roda sobre o documento e sobre cada evidência **antes** de qualquer extração. O que é detectado vira `[OCULTO:<tipo>]`:

| Tipo | Padrão |
|---|---|
| aws-key | `AKIA[0-9A-Z]{16}`, `ASIA[0-9A-Z]{16}` |
| aws-secret | valor de 40 caracteres após `aws_secret_access_key` |
| github-token | `gh[pousr]_[A-Za-z0-9]{36,}`, `github_pat_...` |
| slack-token | `xox[baprs]-...` |
| jwt | três blocos base64url separados por ponto, começando em `eyJ` |
| bearer | `Bearer <token>` |
| private-key | bloco `-----BEGIN ... PRIVATE KEY-----` até `END` |
| senha-chave | valor após `password`, `passwd`, `senha`, `secret`, `token`, `api_key`, `apikey` seguidos de `=` ou `:` |
| url-credencial | `scheme://usuario:senha@host` |

- O relatório informa a contagem e, para cada ocultação, o tipo, o arquivo e a linha. **Nunca o valor.**
- Ocultar não reprova o documento.
- A skill não lê as evidências diretamente, só o relatório.
- Limite: um segredo colado no chat já está na conversa. O plugin só garante que ele não vá parar nos arquivos gerados. O PRIVACY.md diz isso.

## 7. Métricas (`metrics.py`)

As definições do perfil padrão seguem a FireHydrant (F1), com a duração do impacto como no exemplo do Google (G2):

| Métrica | Cálculo |
|---|---|
| TTD | deteccao menos inicio |
| TTA | reconhecimento menos inicio |
| TTM | mitigacao menos inicio |
| TTR | fim menos inicio |
| duração do impacto | fim menos inicio |

O relatório declara essas definições no topo, porque as fontes divergem (seção 13).

Comparação com o texto:

- Uma duração citada com rótulo é comparada à métrica do rótulo.
- Uma duração sem rótulo precisa ser igual a alguma métrica calculada.
- A tolerância é a precisão dos marcos: 1 min se a timeline usa minutos.

## 8. Regras da v1

"Reprova" faz o script sair com código 1. "Aviso" aparece no relatório sem reprovar. Todos os níveis podem ser ajustados no TOML (`[niveis] A5 = "reprova"`), e uma regra pode ser desligada com `"desligada"`.

| ID | Regra | Nível padrão | Fonte |
|---|---|---|---|
| E1 | Horário de entrada da timeline sem registro de evidência dentro da janela de precisão (minuto: hh:mm:00 a hh:mm:59 UTC; tolerância extra configurável em `tolerancia_segundos`, padrão 0) | reprova | P4 |
| E2 | Número do resumo ou do impacto que não aparece nas evidências (normalizando 1.234, 1,234 e 1234) nem é uma métrica calculada | reprova | G3 |
| M1 | Faltam os marcos inicio, deteccao, mitigacao ou fim | reprova | G2, A2, P6, F1 |
| M2 | Marcos fora da ordem inicio ≤ deteccao ≤ reconhecimento ≤ mitigacao ≤ fim | reprova | F1 |
| M3 | Duração citada diferente da recalculada | reprova | F1, G2 |
| T1 | Fuso horário não declarado | reprova | G2, A2, I2 |
| T2 | Entradas da timeline fora de ordem cronológica | reprova | A2 |
| T3 | Horário vago ("cerca de", "aprox", "~", "around", "approx") | aviso | A1 |
| T4 | Primeira entrada não é anterior ao inicio (sem lead-up) | aviso | P4, G2 |
| T5 | Data ambígua não interpretada | aviso | interno |
| T6 | Evidência sem fuso, assumido o do documento | aviso | interno |
| A1 | Ação sem dono (reprova); dono com cara de time: "time", "team", "squad", "@grupo", e-mail de lista (aviso) | reprova / aviso | G3, I4 |
| A2 | Ação sem ticket ou link | reprova | G3, P4, A2, I4 |
| A3 | Prioridade fora de P0 a P3 (reprova); impacto ao usuário sem nenhuma ação P0 ou P1 (reprova); todas as prioridades iguais (aviso) | misto | G3, G4 |
| A4 | Tipo fora de investigate, mitigate, repair, detect, prevent, ou equivalentes em PT (reprova); falta mitigate ou prevent (aviso) | misto | G4, A2 |
| A5 | Sem prazo interpretável (reprova); prazo além da política contada da data do incidente, padrão SEV1 15 dias e SEV2 30 dias (aviso) | misto | P3, A3, I4 |
| A6 | Ação começa com verbo vago: Improve, Make better, Investigate, Review, Explore, Look into, Consider, Evaluate, Discuss, Melhorar, Investigar, Revisar, Verificar, Avaliar, Analisar, Considerar, Discutir | reprova | G4, I4 |
| O1 | Dono não é membro do time que o mapa indica para o componente (aviso); componente sem time no mapa (aviso) | aviso | config |
| L1 | Termos de culpa, lista PT/EN: "erro humano", "human error", "descuido", "careless", "negligên", "negligen", "should have", "deveria ter", "falhou em", "failed to", "culpa", "fault", "ridículo", "ridiculous", "needs to learn", "precisa aprender", "obviamente", "obviously", "!!!" | aviso, o modelo revisa | G3, G4, P5, E1 |
| L2 | Nomes próprios (lista de membros do mapa) ou @handles nas seções causa e timeline | aviso, pode ser desligado | A2 (I8 permite) |

"Impacto ao usuário" (A3) é verdadeiro quando a seção de impacto cita usuários, clientes, requisições ou erros, ou quando a severidade é SEV1/SEV2.

## 9. Configuração (`sourced-postmortem.toml`)

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

Chave desconhecida, nível inválido ou ID de regra inexistente dão código 3, com a linha do erro.

## 10. Diagrama (`excalidraw.py`)

Arquivo `.excalidraw` (JSON v2):

- traço à mão: `roughness: 1`, `fontFamily` Excalifont;
- não embute arquivos de fonte, o que evita a retenção `UNREAD_ASSET_REFERENCED`.

**Faixa de cima, linha do tempo:**
- os marcos e as entradas da timeline, da esquerda para a direita;
- espaçamento proporcional ao tempo, com mínimo legível;
- cada caixa mostra o horário UTC e o texto encurtado (60 caracteres).

**Faixa de baixo, por quê:**
- um fator por caixa;
- seta até o evento da timeline cujo horário o fator cita;
- fator sem horário fica sem seta.

**Onde:** cada caixa traz o componente (coluna "Componente" ou nome do mapa encontrado no texto), e caixas do mesmo componente ganham um retângulo de agrupamento com o nome.

**Cores por papel:**

| Papel | Cor |
|---|---|
| inicio do impacto | vermelho |
| deteccao e reconhecimento | azul |
| mitigacao e fim | verde |
| fatores | cinza |
| demais entradas | branco |

**Trava:** uma entrada reprovada em E1, ou um fator sem horário verificado, sai com traço **tracejado** e o rótulo "sem evidência".

**Determinismo:**
- o ID de cada elemento é o hash SHA-256 truncado do seu conteúdo;
- `seed` fixo derivado do ID;
- sem timestamps de geração.

Com isso, a mesma entrada gera o mesmo arquivo byte a byte.

## 11. Skill (`SKILL.md`)

Fluxo que a skill segue:

1. Pedir o caminho do postmortem e da pasta de evidências. Se o usuário colar texto, salvar em arquivos dentro de uma pasta de trabalho e avisar que um segredo colado já está na conversa.
2. Rodar `${CLAUDE_SKILL_DIR}/scripts/verify.sh`. Não abrir os arquivos de evidência com Read.
3. Ler `relatorio.json` e apresentar:
   - **Conferido pelo script:** reprovações e avisos, com local e fonte. Esta parte é copiada do relatório, sem reescrever o resultado.
   - **Opinião do modelo:** profundidade da causa (não parar em erro humano nem em sintoma), tom além da lista de termos, se cada ação ataca a causa e é específica e delimitada, cobertura das lições por ações. Esta seção é sempre rotulada como opinião.
   - **Melhorias sugeridas:** cada uma direcionada ao time que o mapa indica para o componente; se o componente não está no mapa, "sem dono no mapa".
4. Informar o caminho do `diagrama.excalidraw`.

Frontmatter: `allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/verify.sh *)`.

## 12. Erros e códigos de saída

| Código | Quando |
|---|---|
| 0 | aprovado (pode ter avisos) |
| 1 | reprovado |
| 2 | entrada inválida: arquivo ausente, documento sem timeline, evidências acima de `limite_evidencias_mb` |
| 3 | configuração inválida |
| 4 | Docker ausente ou parado (detectado pelo `verify.sh` antes de rodar) |

Uma linha que não dá para interpretar não interrompe a execução: ela vai para `relatorio.json` em `nao_interpretado` com arquivo e linha. Nenhuma exceção é engolida: um erro inesperado sai com código 2 e a mensagem.

## 13. Divergências entre fontes e escolhas do perfil padrão

| Ponto | Divergência | Escolha padrão |
|---|---|---|
| Início do TTA | impacto (F1) vs alerta (A4, I7) vs page (I6) | impacto (F1), declarado no relatório |
| MTTR | desde o reporte (A1), quatro sentidos (A4), desde o impacto (I5, F1) | inicio até fim (F1) |
| Fim do impacto | mitigado (F1) vs outage ends (G2) | marco fim (G2) |
| Nomes no documento | proibido (A2) vs aceito (I8) | aviso L2 ligado, desligável |
| Prazo nas ações | não exigido (Google) vs exigido (A3, I4, E1) | exigido (A5) |
| Action items obrigatórios | sim (maioria) vs não (E1) | sim |
| "Investigate" | tipo válido (G4, A2) vs verbo proibido (G4, I4) | aceito como tipo, reprovado como verbo inicial |
| Root cause vs fatores | G e A usam root cause; P4, I1 e E1 preferem fatores | aceita os dois cabeçalhos |

## 14. Privacidade e segurança

- O processo roda em contêiner com `--network none`, montagens só leitura e usuário não root.
- Não há telemetria.
- O relatório cita trechos de evidência cortados em 200 caracteres e já sem credenciais. O PRIVACY.md avisa que esses trechos podem conter outros dados dos logs (IPs, IDs).
- SECURITY.md traz a versão suportada e o canal de reporte.

## 15. Testes

- `unittest` da biblioteca padrão. O comando `python -m unittest` roda tudo dentro do mesmo contêiner.
- Fixtures **sintéticas** escritas para o projeto. O exemplo do Google não é copiado, porque é CC BY-NC-ND.
- `fixtures/aprovado/`: incidente com a estrutura de marcos do exemplo do Google, que precisa dar 66 min de duração, mais evidências que sustentam tudo.
- `fixtures/falhas/<regra>/`: um caso mínimo por regra e por nível.
- Evidências em todos os formatos da seção 5, inclusive texto colado.
- `redact`: um caso positivo e um negativo por tipo. Um teste garante que nenhum valor original aparece em `relatorio.*` nem no `.excalidraw`.
- `excalidraw`: comparação byte a byte com um arquivo de referência, e um teste de que caixas sem evidência saem tracejadas.
- Códigos de saída de 0 a 4 cobertos, o 4 com Docker simulado ausente no teste do `verify.sh`.
- Os 3 exemplos de pedido do README testados de ponta a ponta antes do envio.

## 16. Empacotamento

Segue a nota 07 do vault:

- `.claude-plugin/plugin.json` com `"skills": ["."]`, `marketplace.json` com `"source": "./"`, `version: 1.0.0`, licença MIT;
- ícone 1024 px, PRIVACY.md, SECURITY.md, README PT/EN com as 9 seções obrigatórias;
- diagramas de arquitetura em `docs/diagrams/`.

Commits com a identidade noreply `lpalvess`.

## 17. Riscos

- **Formatos de horário fora da lista:** a linha cai em `nao_interpretado` e pode gerar E1 falso. Mitigação: relatório lista as linhas não lidas; formatos novos entram com fixture.
- **E2 rígido para números vindos de dashboards fora das evidências:** o caminho é anexar a exportação do dashboard (CSV) como evidência. O nível pode ser trocado para aviso.
- **Marcos sem linha de log própria** (fim do impacto costuma ser ausência de erro): a evidência esperada é o ponto da métrica em CSV ou o evento de resolução do alerta.
- **Detecção de nomes depende do mapa de membros:** sem mapa, L2 só pega @handles.
- **Adoção baixa:** o valor maior é de portfólio, como já registrado na nota 05.

## 18. Fontes

| Código | URL |
|---|---|
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

Não foram lidos:

- template e checklist do Google em g.co/SiteReliabilityWorkbookMaterials (são Google Docs);
- PDF do handbook da Atlassian (foi usada a versão web);
- página "Examples" do PagerDuty;
- "Intro to Retrospectives" da FireHydrant.
