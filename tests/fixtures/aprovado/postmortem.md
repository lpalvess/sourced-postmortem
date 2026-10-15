# Postmortem: lentidão no checkout

- Data: 2026-09-14
- Severidade: SEV2
- Status: Reviewed
- Dono do postmortem: Ana Souza

## Resumo

Entre 14:54 e 16:00 UTC o checkout-api respondeu com erro para parte dos pedidos. A duração do impacto foi de 66 min. TTD: 7 min. TTM: 42 min.

## Impacto

1.240 pedidos falharam, cerca de 18% do total do período. 3 clientes abriram chamado.

## Fatores contribuintes

- O deploy da versão 4.2 do checkout-api às 14:50 trocou o pool de conexões para 10 conexões.
- O alerta de erro só disparava acima de 15% de erros, por isso a detecção veio às 15:01.

## Linha do tempo (todos os horários em UTC)

- 14:50 Deploy da versão 4.2 do checkout-api concluído.
- 14:54 [inicio] Taxa de erro do checkout-api começa a subir.
- 15:01 [deteccao] Alerta CheckoutErrorRate disparou e acionou o plantão.
- 15:05 [reconhecimento] Plantão reconheceu o alerta.
- 15:36 [mitigacao] Rollback para a versão 4.1 concluído.
- 16:00 [fim] Taxa de erro volta ao normal.

## Ações

| Ação | Dono | Ticket | Prioridade | Tipo | Prazo | Componente |
|---|---|---|---|---|---|---|
| Adicionar teste de carga do pool de conexões no pipeline | ana.souza | PAY-101 | P1 | prevent | 2026-09-28 | checkout-api |
| Reduzir o limiar do alerta de erro para 5% | @joao | PAY-102 | P2 | detect | 2026-10-10 | checkout-api |
| Automatizar o rollback quando a taxa de erro passar de 10% | @maria | PLAT-55 | P1 | mitigate | 2026-09-28 | ingress |
