# AudioSplit & Cifra Pro

Aplicativo para separação de fontes de áudio e sincronização temporal de cifras com a letra.

## Objetivos

- Separar voz, bateria, baixo e instrumentos harmônicos.
- Transcrever a letra e manter timestamps por palavra; alinhamento silábico será avaliado.
- Reconhecer acordes, inversões, extensões e mudanças harmônicas.
- Sincronizar cifras pela ocorrência real da mudança, inclusive antecipações e contratempos.
- Permitir revisão manual e exportação.

## Estrutura atual

- `frontend/`: interface responsiva HTML, CSS e JavaScript.
- `backend/app/`: API FastAPI, persistência SQLAlchemy e tarefas Celery.
- `docker-compose.yml`: ambiente local com API, worker e Redis.
- `docs/`: contratos de dados e arquitetura do pipeline.

## Executar infraestrutura local

Requer Docker e Docker Compose:

```bash
docker compose up --build
```

- API: `http://localhost:8000`
- OpenAPI: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

A API recebe arquivos de áudio em `POST /v1/jobs` e consulta o estado em `GET /v1/jobs/{job_id}`. O limite inicial de upload é 250 MB. Os arquivos e o banco SQLite ficam no volume Docker `audiosplit_data`.

## Estado técnico

A recepção, persistência e fila assíncrona estão estruturadas. O worker ainda não executa separação, ASR, alinhamento ou reconhecimento de acordes: ele registra uma falha controlada e explícita até que os modelos sejam selecionados, integrados e testados. Portanto, não há ainda resultado musical real nem precisão de produção reivindicada.

SQLite é apenas para desenvolvimento. Antes de disponibilizar o serviço publicamente, será necessário migrar para banco gerenciado, armazenamento de objetos privado, autenticação, limites por usuário, política de retenção e observabilidade.

## Critérios de validação

- Separação: SI-SDR/SDR e avaliação auditiva por stem.
- Letra: WER/CER, incluindo testes específicos de canto em português brasileiro.
- Alinhamento: erro temporal de início/fim.
- Acordes: precisão/recall de símbolos e F-score de fronteiras harmônicas.
- Sincronização: erro temporal entre a mudança anotada e a cifra exibida.

Consulte `docs/CONTRATOS-DE-DADOS.md` e `docs/ARQUITETURA-PIPELINE.md`.
