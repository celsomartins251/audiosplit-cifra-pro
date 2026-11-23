# AudioSplit & Cifra Pro

Aplicativo web para separação de fontes de áudio e sincronização temporal de cifras com a letra.

## Objetivos do produto

- Separar voz, bateria, baixo, guitarra, piano/teclado e outros instrumentos.
- Transcrever a letra e manter timestamps por palavra; alinhamento por sílaba será refinado quando tecnicamente possível.
- Reconhecer acordes, inversões, extensões e mudanças harmônicas com timestamps independentes.
- Sincronizar cifras com a ocorrência real da mudança harmônica, inclusive antecipações e contratempos.
- Permitir revisão manual de stems, letra, acordes e marcações temporais.
- Exportar resultados em formatos úteis para músicos.

## Arquitetura inicial

O frontend será HTML, CSS e JavaScript, responsivo e adequado a dispositivos móveis. O processamento de áudio e inferência de modelos ficará em serviços Python na nuvem, executados por tarefas assíncronas. O navegador não tentará executar modelos pesados localmente.

### Componentes previstos

- `frontend/`: interface do usuário e editor de timeline.
- `backend/`: API e orquestração de jobs.
- `worker/`: pipeline de processamento de áudio e modelos.
- `docs/`: decisões de arquitetura, métricas e documentação.

## Princípios de qualidade

- Não apresentar resultados simulados como inferência real.
- Preservar timestamps, confiança e proveniência dos resultados.
- Avaliar separação, transcrição, alinhamento e acordes com conjuntos de referência e métricas próprias.
- Não posicionar cifras simplesmente no início de cada compasso: usar eventos harmônicos detectados e revisão humana.
- Manter separação, transcrição e reconhecimento harmônico como módulos independentes, combinados numa timeline comum.

## Estado atual

Estrutura inicial do repositório. Modelos de separação, ASR, alinhamento e reconhecimento de acordes ainda precisam ser selecionados por benchmark e integrados. Nenhuma precisão de produção é reivindicada nesta fase.

## Próximas etapas

1. Criar o esqueleto executável da interface e da API.
2. Definir contratos de dados e formato de timestamps.
3. Implementar importação e validação de áudio.
4. Construir pipeline de benchmark para separação, transcrição e reconhecimento harmônico.
5. Integrar os melhores modelos e validar com músicas anotadas.
