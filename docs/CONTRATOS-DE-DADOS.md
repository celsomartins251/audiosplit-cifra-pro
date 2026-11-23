# Contratos de dados — timeline musical

## Objetivo

Letra e acordes são eventos temporais independentes. A interface não deve presumir que uma mudança de acorde ocorre no primeiro tempo do compasso ou no início de uma palavra.

## Evento de letra

Cada token contém:
- `start`: início em segundos, relativo ao áudio original.
- `end`: fim em segundos, relativo ao áudio original.
- `label`: palavra reconhecida; futuramente poderá ser subdividida em sílabas.
- `confidence`: confiança do modelo, quando disponível.
- `source`: modelo/etapa que produziu o evento.

## Evento harmônico

Cada acorde contém:
- `start` e `end`: intervalo temporal estimado do acorde.
- `label`: símbolo completo, incluindo qualidade, extensões, alterações e baixo/inversão quando reconhecidos.
- `confidence`: confiança do reconhecimento.
- `source`: modelo ou processo responsável.

## Sincronização

1. Manter o relógio de áudio como referência única.
2. Não deslocar timestamps de letra para fazê-los coincidir artificialmente com acordes.
3. Exibir o acorde a partir do onset harmônico estimado.
4. Permitir revisão manual do onset e do símbolo do acorde.
5. Preservar o timestamp original do modelo e o timestamp corrigido pelo usuário como valores distintos.
6. Representar incerteza; não inventar precisão em nível de sílaba quando o alinhador só oferece precisão por palavra.

## Avaliação

- Separação: SI-SDR/SDR e avaliação auditiva por stem.
- Letra: WER/CER, com avaliação específica para canto em português brasileiro.
- Alinhamento: erro absoluto de início/fim e proporção dentro de tolerâncias temporais.
- Acordes: precisão/recall de símbolos e F-score de fronteiras harmônicas.
- Sincronização: erro temporal entre mudança harmônica anotada e evento exibido.

## Estado

Este documento define o contrato pretendido. Os modelos e serviços de inferência ainda não foram integrados.
