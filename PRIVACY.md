# Privacy policy / Política de privacidade

Last updated / Última atualização: 2026-10-15

## English

sourced-postmortem runs on your machine. It has no server, no account and no telemetry.

- **What it reads:** only the files you pass to it: the postmortem, the evidence folder and, if you use one, the TOML config.
- **What it writes:** three files (`relatorio.json`, `relatorio.md` and `diagrama.excalidraw`), only in the output folder you choose (`sourced-postmortem-out/` by default).
- **Network:** the verifier runs in a Docker container started with `--network none`, so your documents never leave your machine. Only Docker downloads the base image, the first time you run it. No data of yours is sent in that step.
- **Personal data:** the project does not collect or send personal data. The evidence excerpts in the report can contain data from your logs, such as IPs and IDs, so treat the report with the same care as the logs. Credentials are hidden before the excerpts are written. A secret you paste into the chat is already in your conversation with Claude, and the plugin cannot undo that.

Claude Code and Docker have their own privacy policies, which this project does not control.

## Português

O sourced-postmortem roda na sua máquina. Não tem servidor, conta nem telemetria.

- **O que lê:** só os arquivos que você passa: o postmortem, a pasta de evidências e, se usar, o TOML de configuração.
- **O que grava:** três arquivos (`relatorio.json`, `relatorio.md` e `diagrama.excalidraw`), só na pasta de saída que você escolher (`sourced-postmortem-out/` por padrão).
- **Rede:** o verificador roda num contêiner Docker iniciado com `--network none`, então seus documentos nunca saem da sua máquina. Só o Docker baixa a imagem base, na primeira execução. Nenhum dado seu é enviado nesse passo.
- **Dados pessoais:** o projeto não coleta nem envia dados pessoais. Os trechos de evidência no relatório podem conter dados dos seus logs, como IPs e IDs, então trate o relatório com o mesmo cuidado dos logs. As credenciais são ocultadas antes de os trechos serem gravados. Um segredo colado no chat já está na sua conversa com o Claude, e o plugin não consegue desfazer isso.

O Claude Code e o Docker têm suas próprias políticas de privacidade, que este projeto não controla.
