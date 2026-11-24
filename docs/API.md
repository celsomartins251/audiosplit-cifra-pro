# API HTTP — AudioSplit & Cifra Pro

Base local: `http://localhost:8000`

## Endpoints

| Método | Rota | Uso |
|---|---|---|
| GET | `/health` | Verificar se a API responde |
| POST | `/v1/jobs` | Enviar áudio como multipart/form-data no campo `audio` |
| GET | `/v1/jobs/{job_id}` | Consultar estado e progresso |
| GET | `/v1/jobs/{job_id}/result` | Obter resultado JSON concluído |
| PUT | `/v1/jobs/{job_id}/result` | Persistir correções de letra e acordes |
| GET | `/v1/jobs/{job_id}/source` | Reproduzir/baixar o áudio original |
| GET | `/v1/jobs/{job_id}/stems/{stem_name}` | Baixar `vocals`, `drums`, `bass`, `guitar`, `piano` ou `other` |

## Estados do job

- `queued`: aguardando worker.
- `processing`: pipeline em execução.
- `completed`: resultado salvo e disponível.
- `failed`: falha técnica; consultar `error_code` e `error_message`.

## Evento temporal

Palavras e acordes usam a mesma referência de tempo em segundos:
```json
{
  "start": 12.34,
  "end": 12.91,
  "label": "Am7",
  "confidence": 0.73,
  "source": "librosa-chroma-template-baseline"
}
```

O campo `confidence` é específico da etapa. Para o reconhecedor de acordes atual, é um índice de similaridade de template, não uma probabilidade calibrada.

## Exemplo de envio

```bash
curl -X POST http://localhost:8000/v1/jobs \
  -F "audio=@musica.wav"
```

A resposta contém `job_id`. Consulte o estado até `completed` e então solicite `/result`.

## Revisões

O `PUT /v1/jobs/{job_id}/result` recebe o projeto JSON completo, incluindo o mesmo `job_id`. A API valida os intervalos temporais e grava o JSON no banco e no volume de dados.

## Segurança

Esta versão não possui autenticação. O endpoint de upload e os arquivos não devem ser expostos publicamente até que autenticação, autorização por usuário, limites de uso, expiração de arquivos, proteção contra abuso e armazenamento privado sejam implementados. Configure `CORS_ORIGINS` com os domínios exatos antes de qualquer implantação pública.
