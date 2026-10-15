# sourced-postmortem

English | [Português](README.md)

Checks an incident postmortem against the evidence (logs, exported timeline, alerts, CSV metrics) and rejects the document if any time or number is not backed by it. It recomputes durations, checks the timeline and action items against industry standards, and cites the source of every rule. It runs in a container with no network. It is also a Claude Code skill (see [SKILL.md](SKILL.md), written in Portuguese).

## What it does and why it exists

A postmortem often has times and numbers that become "true" just because they sit in a well-written document. Zalando discusses, in an article about AI-powered postmortem analysis, the problem of postmortems that stop being a source of data: [Dead Ends or Data Goldmines? AI-Powered Postmortem Analysis](https://engineering.zalando.com/posts/2025/09/dead-ends-or-data-goldmines-ai-powered-postmortem-analysis.html). This project adds a simple gate: every timeline time must have a record in the evidence, every number in the summary and impact must appear there (or be a computed metric), and every quoted duration must match the one recomputed from the milestones.

The plugin **does not generate postmortems**. It verifies one that already exists. The principle is: Claude writes and gives opinions, the code checks. Whatever can be checked deterministically stays in the script, and the report keeps what was **checked by the script** apart from the **model's opinion**.

The gates:

- a timeline entry time with no record in the evidence (E1);
- a number in the summary or impact that is not in the evidence (E2);
- milestones (start, detection, mitigation, end) missing, out of order, or a quoted duration that differs from the recomputed one (M1 to M3);
- undeclared time zone and out-of-order timeline (T1 and T2);
- an action item without owner, ticket, priority, type or due date, and one that starts with a vague verb (A1 to A6);
- warnings for vague times, blame terms and personal names (T3, L1, L2).

## Architecture

![Architecture: the postmortem, the evidence and the TOML enter the no-network container; redact hides credentials, parse reads everything in UTC, the rules check with a cited source, and relatorio.json, relatorio.md and the diagram come out; the skill keeps what the script checked apart from the model's opinion](docs/diagrams/arquitetura.en.svg)

`scripts/verify.sh` runs the verifier in a container with no network and read-only inputs. Inside it, `redact` hides credentials before any other step, `parse_doc`, `evidence` and `timestamps` read the document and the evidence and normalize everything to UTC, and rules E, M, T, A, O and L produce the findings, each with its cited source. The output is `relatorio.json`, `relatorio.md` and `diagrama.excalidraw` (the "where and why" chain). The skill presents the result with what the script checked kept apart from the model's opinion.

The editable diagram files are in [docs/diagrams/](docs/diagrams/): `arquitetura.en.excalidraw` (opens at excalidraw.com) and the generator `build_architecture.py`, which also produces the Portuguese versions.

## Installation

Docker is required. The verifier only runs in a container.

### Use as a Claude Code skill

Install it as a plugin, straight from this repository. In the terminal:

```
claude plugin marketplace add lpalvess/sourced-postmortem
claude plugin install sourced-postmortem@sourced-postmortem
```

Or, inside a Claude Code session:

```
/plugin install sourced-postmortem --marketplace lpalvess/sourced-postmortem
```

Then ask, from any folder, for example: "check the postmortem in postmortem.md with the evidence in evidencias/".

### Direct use, without Claude Code

```
git clone https://github.com/lpalvess/sourced-postmortem.git
cd sourced-postmortem
scripts/verify.sh <postmortem.md> <evidencias/> [--config <file.toml>] [--out <folder>]
```

The default output folder is `./sourced-postmortem-out/`. It cannot be inside the evidence folder (the script refuses with exit code 2).

## Notices

- There is no lockfile and there are no dependencies: the verifier uses only the Python standard library.
- On the first run Docker downloads the image pinned by digest. This is the only moment with network access, and it is done by Docker, not by the verifier.
- The skill only works in Claude Code, because it needs Docker and a bash script. It does not run in the claude.ai chat.

## Example requests

The `examples/checkout/` folder holds a FICTIONAL example (invented company and numbers). It is a copy of a passing case with two changes in the text: `3 clientes` became `5 clientes` and `TTD: 7 min` became `TTD: 9 min`. That is why it fails, which shows the value of the plugin.

- "Verifique o postmortem em examples/checkout/postmortem.md com as evidências de examples/checkout/evidencias." (Check the postmortem in examples/checkout/postmortem.md with the evidence in examples/checkout/evidencias.) Expected: rejected (exit code 1), with E2 on "5 clientes" (that number is in no evidence) and M3 on the TTD.
- "As durações do resumo deste postmortem batem com a timeline?" (Do the durations in this postmortem's summary match the timeline?) Expected: M3, with the quoted TTD of 9 min and the recomputed one of 7 min from the milestones.
- "Para qual time vai cada ação deste postmortem? Use o mapa examples/checkout/sourced-postmortem.toml." (Which team gets each action item of this postmortem? Use the map examples/checkout/sourced-postmortem.toml.) Expected: the 3 action items, each with the team pagamentos or plataforma.

The skill is written in Portuguese, so the requests above are in Portuguese. To run the first one straight from the terminal:

```
scripts/verify.sh examples/checkout/postmortem.md examples/checkout/evidencias \
  --config examples/checkout/sourced-postmortem.toml --out sourced-postmortem-out
```

The output is `reprovado: 2 reprovações, 0 avisos.` (the verifier's messages are in Portuguese) and the exit code is 1.

## Expected postmortem format

Markdown with headings recognized by Portuguese and English synonyms, case-insensitive. The list can be extended in the TOML.

| Section | Headings recognized by default |
| ------- | ------------------------------ |
| resumo (summary) | Resumo, Summary, Executive Summary, Overview, Visão geral |
| impacto (impact) | Impacto, Impact |
| causa (cause) | Causa, Causa raiz, Causas, Fatores contribuintes, Root cause, Root causes, Contributing factors, Contributors, Trigger, Gatilho |
| timeline | Linha do tempo, Timeline, Cronologia |
| acoes (actions) | Ações, Acoes, Action items, Follow-ups, Follow ups, Corrective actions, Ações corretivas, Itens de ação |

- **Timeline:** each list item or table row that starts with a time becomes an entry. The time zone must be declared in the heading ("todos os horários em UTC", "all times UTC", "(UTC-3)", "America/Sao_Paulo") or in each entry.
- **Milestones:** recognized by keyword or by an explicit tag, which takes priority: `[inicio]`, `[deteccao]`, `[reconhecimento]`, `[mitigacao]`, `[fim]`.
- **Actions:** a table with the columns action, owner, ticket, priority, type, due and, optionally, component. An action in a list, outside a table, is rejected for missing fields.
- **Cause:** each list item becomes a factor. If it quotes a timeline time, it is linked to that event.

### Verifier rules

Level `reprova` (fail) makes the script exit with code 1. Level `aviso` (warning) shows in the report without failing.

| ID | Default level | What it rejects | Source |
| -- | ------------- | --------------- | ------ |
| E1 | reprova | Timeline entry time with no evidence record in the precision window (minute) | P4 |
| E2 | reprova | Number in the summary or impact that is not in the evidence and is not a computed metric | G3 |
| M1 | reprova | Missing milestones (inicio, deteccao, mitigacao or fim) | G2, A2, P6, F1 |
| M2 | reprova | Milestones out of order | F1 |
| M3 | reprova | Quoted duration differs from the recomputed one (a gap under 1 minute is allowed; 1 minute or more fails) | F1, G2 |
| T1 | reprova | Time zone not declared | G2, A2, I2 |
| T2 | reprova | Timeline entries out of chronological order | A2 |
| T3 | aviso | Vague time ("cerca de", "aprox", "~", "around", "approx") | A1 |
| T4 | aviso | First entry is not earlier than the start | P4, G2 |
| T5 | aviso | Ambiguous date not interpreted (`formato_data` missing) | interno |
| T6 | aviso | Evidence without time zone: the document's was assumed | interno |
| A1 | reprova | Action without owner (an owner that looks like a team is a warning) | G3, I4 |
| A2 | reprova | Action without ticket or link | G3, P4, A2, I4 |
| A3 | reprova | Priority outside P0 to P3, or user impact with no P0 or P1 action | G3, G4 |
| A4 | reprova | Type outside investigate, mitigate, repair, detect, prevent (or Portuguese equivalents) | G4, A2 |
| A5 | reprova | No interpretable due date (a due date beyond the policy is a warning) | P3, A3, I4 |
| A6 | reprova | Action that starts with a vague verb (Improve, Review, Melhorar, Revisar and similar) | G4, I4 |
| O1 | aviso | Owner is not a member of the team the map gives for the component, or component with no team | config |
| L1 | aviso | Blame term (for example "erro humano", "human error") | G3, G4, P5, E1 |
| L2 | aviso | Personal name (from the member list) or @handle in the cause and timeline sections | A2 |

### Configuration

The `sourced-postmortem.toml` is optional. It adjusts the profile, the levels, the milestones and the team map. An unknown key, an invalid level or a nonexistent rule ID gives exit code 3. The message carries the file name and the key name; only TOML syntax errors also carry line and column. A `prazo_dias` you supply replaces the whole default table (it does not merge): severities you do not list get no deadline.

```toml
[perfil]
tolerancia_segundos = 0
prazo_dias = { SEV1 = 15, SEV2 = 30 }
limite_evidencias_mb = 50
formato_data = "DMY"     # optional; without it, ambiguous dates raise T5

[niveis]
L2 = "desligada"        # the team accepts names, like incident.io

[marcos]
deteccao = ["pagerduty acionou"]   # adds to the default words

[times.pagamentos]
componentes = ["checkout-api", "payment-worker"]
membros = ["ana.souza", "@joao"]

[times.plataforma]
componentes = ["ingress", "kafka"]
membros = ["@maria"]
```

### Exit codes

| Code | Meaning |
| ---- | ------- |
| 0 | Passed (may have warnings). |
| 1 | Failed: at least one rule at level `reprova`. |
| 2 | Invalid input: missing file, document without a timeline, evidence above the limit, output folder inside the evidence folder. |
| 3 | Invalid configuration (TOML). |
| 4 | Docker missing or stopped, or the container could not start (`docker run` returned 125 or more). |

## Common problems

| Symptom | Code | What to do |
| ------- | ---- | ---------- |
| Docker missing or stopped | 4 | Install Docker and check that it is running (`docker info`). |
| Timeline section not found | 2 | Use a recognized heading (see the sections table), such as "Linha do tempo" or "Timeline", or add yours in the TOML. |
| Evidence above the limit | 2 | Shrink the evidence folder or raise `limite_evidencias_mb` in the TOML. |
| Invalid config | 3 | Read the message, which has the file name and the key name (a TOML syntax error also has line and column), and fix the key, level or rule ID in the TOML. |
| E1 on a time that exists in the log | 1 | See "Linhas não interpretadas" (lines not interpreted) in `relatorio.md`: most likely the time format is not supported or the evidence's time zone differs from the declared one. |
| E2 on a dashboard number | 1 | Numbers that only appear in an image or screenshot are not checked. Export the series as CSV and put it in the evidence folder. |
| M1 | 1 | Milestones are missing. Use the tags `[inicio]`, `[deteccao]`, `[mitigacao]` and `[fim]` on the timeline entries. |
| T5 | 0 | Ambiguous date (`03/04/2026`). Write YYYY-MM-DD or set `formato_data` in the TOML. |

## Support

- Questions and problems: open an issue at https://github.com/lpalvess/sourced-postmortem/issues.
- Security flaws: use private vulnerability reporting, as explained in [SECURITY.md](SECURITY.md).

## Security by construction

What the project guarantees, by construction:

- The verifier runs in a container with `--network none`: no network at runtime, no telemetry.
- The code and the inputs are mounted read-only, and only the output folder is writable. The process runs as the calling user (not as root unless the caller is root).
- Credentials are hidden before any other step, and the report carries only excerpts already free of credentials.
- The postmortem and the evidence are read as data, never executed.
- No dependencies beyond the Python standard library.
- The container base image is pinned by digest.

What the project does NOT guarantee:

- That the described cause is right. The script checks that times and numbers exist in the evidence, not the technical content. That is the model's opinion and your judgment.
- That every credential is recognized. Redaction follows known patterns.
- That the evidence excerpts in the report contain no data from your logs, such as IPs and IDs (see [PRIVACY.md](PRIVACY.md)).
- Docker's own security. Isolation depends on Docker and your system.

## Known limitations

- Supported time formats: ISO 8601 and RFC 3339, syslog, nginx and Apache, epoch in JSON fields (`startsAt`, `endsAt`, `timestamp`, `ts`), `HH:MM` and `HH:MM:SS` with the context date, and `DD/MM/YYYY` and `YYYY-MM-DD` dates. A line in another format goes to "Linhas não interpretadas" and can cause a false E1.
- An ambiguous date (`03/04/2026`) is only interpreted with `formato_data` in the TOML. Without it, warning T5 is raised.
- `15h30` without a label is read as a time. Write durations with a label ("1h06 de duração", "TTM 66 min").
- Numbers that only appear in dashboards (images) are not checked. Export as CSV.
- A timeline that crosses midnight needs a date subheading inside it (`### 2026-09-15`). Without it, the entry after the turn looks out of order (T2).
- Names of people are only detected from the team map's member list. Without a map, rule L2 only catches @handles.
- Only Markdown is accepted as the postmortem. There is no .docx or PDF support.
- The diagram was checked at excalidraw.com with the approved case, a case with E1 and the architecture diagrams. Text width is estimated (about 20 characters per line in 200 px boxes), so a label with very long words may touch the box edge.

## What this project does not do

- It does not generate postmortems and does not write the document's text.
- It does not run a live incident.
- It does not publish or send the postmortem anywhere.

## Similar projects

- [dastergon/postmortem-templates](https://github.com/dastergon/postmortem-templates): a collection of postmortem templates, useful if you want a starting point to write from.
- Postmortem generators: an alternative for those who want to generate the document, which is exactly what this project does not do. They and this plugin can be used in sequence: generate with one of them and check here.

## License, credits and privacy

- Code under the MIT license, see [LICENSE](LICENSE).
- Privacy policy: [PRIVACY.md](PRIVACY.md).
- Architecture diagrams generated by `docs/diagrams/build_architecture.py`, in a format compatible with [Excalidraw](https://excalidraw.com).

Rule sources:

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
