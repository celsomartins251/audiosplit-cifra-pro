# Protocolo de validação de qualidade

## Separação de fontes

Use músicas de referência para as quais existam stems originais alinhados e direitos de uso. Cada modelo deve receber exatamente o mesmo mix, sem normalização ou corte diferente entre execuções.

Compare ao menos:
- `htdemucs_ft`: quatro stems, referência inicial de qualidade geral;
- `htdemucs_6s`: seis stems, com guitarra e piano separados, quando a qualidade dessas categorias for suficiente.

O benchmark local calcula SI-SDR por stem:

```bash
PYTHONPATH=backend python backend/scripts/benchmark_stems.py \
  --reference-dir /caminho/stems-originais \
  --estimated-dir /caminho/stems-gerados
```

Maior SI-SDR indica maior semelhança de sinal, mas não substitui audição crítica. Registre vazamento entre fontes, artefatos, transientes, sustentação de notas e inteligibilidade. Não compare números obtidos com protocolos ou conjuntos de músicas diferentes como se fossem equivalentes.

## Transcrição e alinhamento

Prepare a letra correta e timestamps anotados manualmente. Avalie:
- WER/CER para o texto;
- erro absoluto de início e fim por palavra;
- percentual de palavras dentro de tolerâncias temporais predefinidas;
- taxa de falha do alinhador em trechos cantados, falados, coros e sobreposições.

A pontuação do alinhador não deve ser interpretada como garantia de precisão em canto.

## Reconhecimento harmônico

Prepare anotações com símbolo completo e onset real de cada acorde. Avalie:
- precisão e recall de símbolos;
- F-score de fronteiras harmônicas com tolerância temporal definida;
- acerto de qualidade, extensão, alteração e baixo/inversão;
- desempenho separado por gênero, densidade do arranjo e velocidade de mudança.

A avaliação deve incluir contratempos, antecipações, acordes de passagem, dominantes secundárias, substituições por trítono, inversões e tensões.

## Sincronização letra/cifra

Meça o erro entre o onset harmônico anotado e o onset apresentado. Atribuir uma cifra à palavra mais próxima é apenas uma visualização: o onset original deve permanecer preservado, inclusive quando a mudança ocorre no meio de uma palavra ou sílaba.

## Reprodutibilidade

Para cada execução, registre:
- hash do áudio de entrada;
- modelo, versão, pesos e parâmetros;
- hardware, dispositivo e duração do processamento;
- métricas e observações auditivas;
- correções manuais realizadas.

Não publique amostras protegidas por direitos autorais sem autorização. Use materiais próprios ou licenciados.
