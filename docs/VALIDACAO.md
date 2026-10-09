# Validação funcional — Vivobook S5406SA

Data: 2026-10-09T18:30:53.768963-03:00

Modelo: ASUS Vivobook S 14 S5406SA_S5406SA

Testes executados pelo processo GTK, usando os callbacks reais dos controles,
sem simular as respostas de asusd/UPower. Perfis, limites e brilho foram
confirmados também nos arquivos do kernel.

| Verificação | Resultado | Evidência |
|---|---|---|
| Detecção e carregamento GTK | PASS | ["profile", "battery", "keyboard", "info"] |
| Perfil Quiet | PASS | {"daemon": "Quiet", "kernel": "quiet", "gui": "Silencioso"} |
| Perfil Balanced | PASS | {"daemon": "Balanced", "kernel": "balanced", "gui": "Equilibrado"} |
| Perfil Performance | PASS | {"daemon": "Performance", "kernel": "performance", "gui": "Desempenho"} |
| Perfil automático ac: True | PASS | {"profile": "Quiet", "enabled": true, "persisted": true} |
| Perfil automático ac: False | PASS | {"profile": "Balanced", "enabled": false, "persisted": true} |
| Perfil automático battery: True | PASS | {"profile": "Quiet", "enabled": true, "persisted": true} |
| Perfil automático battery: False | PASS | {"profile": "Balanced", "enabled": false, "persisted": true} |
| Limite de carga 20% | PASS | {"daemon": 20, "kernel": 20, "gui": "20%"} |
| Limite de carga 60% | PASS | {"daemon": 60, "kernel": 60, "gui": "60%"} |
| Limite de carga 80% | PASS | {"daemon": 80, "kernel": 80, "gui": "80%"} |
| Limite de carga 55% | PASS | {"daemon": 55, "kernel": 55, "gui": "55%"} |
| Limite de carga 100% | PASS | {"daemon": 100, "kernel": 100, "gui": "100%"} |
| Brilho do teclado 0 | PASS | {"upower": 0, "kernel": 0, "gui": "0 / 3"} |
| Brilho do teclado 1 | PASS | {"upower": 1, "kernel": 1, "gui": "1 / 3"} |
| Brilho do teclado 2 | PASS | {"upower": 2, "kernel": 2, "gui": "2 / 3"} |
| Brilho do teclado 3 | PASS | {"upower": 3, "kernel": 3, "gui": "3 / 3"} |
| Carga completa temporária: ativação | PASS | {"temporary_threshold": 100, "saved_base": "80"} |
| Atualização e navegação | PASS | Leitura atualizada, navegação e nova detecção concluídas |

## Correção encontrada

O asusd tinha perfis AC/bateria salvos, mas os flags de alternância automática
estavam desativados. A GUI não mostrava essa distinção. Ela agora consulta
`ChangePlatformProfileOnAc` e `ChangePlatformProfileOnBattery` por D-Bus,
mostra o estado e permite ativar/desativar a alternância junto com o perfil.
Salvar exige confirmação de leitura de ambas as configurações.

## Ocorrências durante o diagnóstico

Uma primeira sequência rápida não confirmou o perfil Performance; a GUI
mostrou erro e o teste restaurou o estado original. A consulta isolada confirmou
Performance no daemon e no kernel durante vários segundos. A sequência final
pela GUI confirmou os três perfis. Essa ocorrência não foi reproduzida na
sequência final; o teste não prova ausência de conflitos com outros serviços
de gerenciamento de energia.

O bloqueio observado na inicialização estava no script de teste: ele processava
poucos eventos GTK por intervalo, deixando os callbacks de menor prioridade
sem execução. O laço foi corrigido para drenar os eventos pendentes. A GUI
executada com o laço normal de aplicação passou pela verificação de inicialização.

## Restauração

Restauração integral confirmada: **True**.

- Perfil ativo: Balanced.
- Perfil na tomada: Performance; alternância desativada.
- Perfil na bateria: Balanced; alternância desativada.
- Limite de carga atual e base: 100%.
- Brilho do teclado: 0 de 3.
- EPP de todas as políticas de CPU: balance_performance, como antes do teste.

A comparação final incluiu valores do daemon, configuração persistida e EPP.

## Limites desta validação

- Sem desconexão física de AC: evento de troca da fonte de energia não testado.
- Carga temporária: ativação e limite verificados; ciclo completo de recarga não executado.
- Aura RGB e curvas de ventoinha não são expostos pelo asusd nesta instalação.
- A bateria estava em 100%: o teste confirma o limite aplicado, sem descarregá-la para medir uma recarga.
- O RPM é gerado e inspecionado; a instalação no sistema não faz parte deste teste.

O relatório bruto está em `build/validation-live.json`.
