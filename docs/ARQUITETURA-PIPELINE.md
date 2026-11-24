# Arquitetura do pipeline de processamento

## Fluxo implementado

1. API recebe o áudio, valida extensão e limite de 250 MB.
2. Arquivo é armazenado em volume privado com UUID; nome original é preservado apenas como metadado.
3. Job é persistido no banco SQL.
4. Celery/Redis agenda a tarefa.
5. Worker executa separação, transcrição, alinhamento opcional, harmonia e ritmo.
6. Resultados e metadados são persistidos em JSON e no banco.
7. API permite consultar o job, baixar o original/stems, reabrir projeto e salvar correções.

## Separação de fontes

- Modelo padrão: Demucs `htdemucs_ft`, quatro stems (vocals, drums, bass, other).
- Perfil alternativo: `htdemucs_6s`, seis stems (vocals, drums, bass, guitar, piano, other).
- O perfil de seis stems não é automaticamente considerado melhor; comparar SI-SDR e ouvir os stems no mesmo conjunto de referência.
- O modelo e os pesos são baixados no primeiro processamento e armazenados no volume de cache. Como a licença comercial dos pesos não está confirmada, o worker exige `ALLOW_UNCLEARED_MODEL_WEIGHTS=true`; o Compose define essa opção apenas para desenvolvimento/teste privado.

## Voz e alinhamento

- faster-whisper executa ASR no stem vocal, inicialmente configurado para português.
- WhisperX/Wav2Vec2 executa alinhamento forçado opcional usando o texto reconhecido.
- Quando o alinhador não carrega ou falha, o pipeline preserva os timestamps estimados pelo ASR e registra a razão.
- Alinhamento de caracteres não é equivalente a segmentação silábica musical. Canto, vibrato, melismas, coros e sobreposição vocal exigem validação.

## Harmonia e ritmo

- Chroma CQT e templates reconhecem acordes no stem harmônico; o mix completo é usado como corroborador.
- Eventos harmônicos são produzidos em intervalos não sobrepostos e carregam fonte e índice de similaridade.
- O reconhecedor inclui tríades, tétrades e alguns acordes com extensões/alterações. Inversões e tensões complexas ainda exigem revisão.
- Librosa estima BPM e pulsos. A fórmula de compasso não é inferida nesta versão.

## Timeline e edição

Palavras e acordes mantêm timestamps independentes, com o áudio original como relógio comum. A interface mostra uma prévia de cifra associada à palavra que contém ou sucede o onset do acorde, mas mantém o timestamp harmônico original. O usuário pode editar texto, início/fim das palavras e início/fim dos acordes. As revisões podem ser salvas no backend.

## Ambiente de desenvolvimento

Execute `docker compose up --build`. API em `http://localhost:8000`; OpenAPI em `/docs`; health check em `/health`. A primeira execução pode baixar vários gigabytes de dependências e pesos. O Compose está configurado para CPU e baixa concorrência; produção requer worker GPU e armazenamento adequado.

## Limitações e requisitos para produção

- A precisão real ainda precisa ser medida em músicas de referência anotadas e autorizadas.
- A análise de acordes é baseline por templates, não modelo ACR neural de produção.
- Não há separação individual de todos os instrumentos além dos stems oferecidos pelo modelo.
- SQLite e volume local são apenas para desenvolvimento.
- Não há autenticação, cotas, expiração automática, antivírus ou isolamento multiusuário. O perfil de pesos Demucs do Compose não está liberado para assumir uso comercial.
- Não exponha o backend publicamente até implementar segurança, banco gerenciado, storage privado, logs/monitoramento e políticas de retenção.
