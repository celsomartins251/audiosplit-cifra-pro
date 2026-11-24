# Contratos de dados — timeline musical

## Referência temporal

O áudio original é o relógio único do projeto. Todos os eventos usam segundos desde o início do arquivo original, mesmo quando o modelo analisa um stem separado.

## Evento de letra

Cada token contém:
- `start`: início estimado em segundos.
- `end`: fim estimado em segundos.
- `label`: palavra reconhecida.
- `confidence`: score do ASR/alinhador, quando disponível.
- `source`: modelo/etapa que produziu o evento.

Quando WhisperX está disponível, o resultado também pode conter alinhamentos de caracteres. Caracteres não equivalem automaticamente a sílabas ou fonemas musicais. `edited_text` representa uma reescrita manual que não pôde ser mapeada token a token; nesse caso, os timestamps originais permanecem preservados.

## Evento harmônico

Cada acorde contém:
- `start` e `end`: intervalo temporal estimado.
- `label`: símbolo estimado.
- `confidence`: score específico da etapa.
- `source`: modelo ou processo responsável.
- `alternatives`: candidatos de outra fonte, quando mix e stem harmônico discordam.

No reconhecedor atual, `confidence` é um índice de similaridade de template, não uma probabilidade calibrada. Os eventos são intervalos não sobrepostos; gaps representam trechos em que o algoritmo não encontrou uma estimativa suficientemente confiável.

## Metadados

O projeto pode incluir:
- nome original, duração, sample rate, canais e hash SHA-256 do áudio;
- nome e versão dos pacotes/modelos;
- fonte de cada evento e observações sobre licenciamento;
- BPM e tempos estimados dos pulsos.

## Sincronização e edição

1. Manter timestamps de letra e harmonia independentes.
2. Não quantizar mudanças harmônicas automaticamente ao primeiro tempo do compasso.
3. A prévia visual associa a cifra à palavra que contém ou sucede o onset, mas o onset original permanece disponível.
4. O usuário pode corrigir início/fim das palavras e acordes.
5. A exportação ChordPro associa cifras à palavra temporalmente mais próxima; o JSON preserva os timestamps exatos, inclusive quando a mudança ocorre dentro de uma palavra.
6. Não declarar precisão silábica quando só há timestamps de palavra/caractere.

## Avaliação

- Separação: SI-SDR/SDR e avaliação auditiva por stem.
- Letra: WER/CER em canto brasileiro.
- Alinhamento: erro absoluto de início/fim por palavra.
- Acordes: precisão/recall de símbolos e F-score de fronteiras.
- Sincronização: erro temporal entre mudança harmônica anotada e evento exibido.

## Estado

A API, a fila, a separação base, a transcrição, o alinhamento opcional, o reconhecimento harmônico baseline, o ritmo e o editor estão implementados no código. A qualidade de produção ainda depende de execução em servidor, validação em gravações reais e substituição/regularização de pesos com licenças adequadas.
