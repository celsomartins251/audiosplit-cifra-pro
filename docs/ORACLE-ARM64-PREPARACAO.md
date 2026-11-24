# Preparação Oracle Cloud Always Free (ARM64)

Este perfil prepara a execução em uma VM Oracle Ampere A1 ARM64, com CPU e sem GPU. Ele **não significa que o backend já esteja hospedado**.

## Estado e limites

- O frontend continua no GitHub Pages.
- API, worker Celery e Redis são executados na mesma VM.
- SQLite e arquivos de áudio ficam em volumes persistentes locais.
- O perfil mantém a API vinculada a `127.0.0.1:8000`; não a exponha por Caddy, Nginx, túnel ou regra de firewall enquanto não houver autenticação e autorização por proprietário.
- WhisperX/alinhamento forçado fica desativado inicialmente para reduzir dependências e validar primeiro o caminho ARM64 básico.
- O worker usa concorrência 1 e CPU. O processamento poderá ser demorado.
- Os limites de memória/CPU são limites de contêiner e devem ser conferidos na VM escolhida.

## Bloqueio de licença

O pipeline atual interrompe a análise quando `ALLOW_UNCLEARED_MODEL_WEIGHTS=false`. O perfil Oracle preserva essa proteção. A licença dos pesos/modelos Demucs ainda precisa ser verificada para o uso pretendido. Não altere para `true` em produção antes dessa revisão.

## Preparação na VM

Depois de criar uma instância Ampere A1 elegível ao Always Free, instalar Docker Engine e o plugin Docker Compose, clonar este repositório e executar:

```bash
docker compose -f docker-compose.oracle-arm64.yml build
docker compose -f docker-compose.oracle-arm64.yml up -d
docker compose -f docker-compose.oracle-arm64.yml ps
docker compose -f docker-compose.oracle-arm64.yml logs --tail=100 api worker
```

Verifique a arquitetura:

```bash
uname -m
docker image inspect audiosplit-cifra-pro-api --format '{{.Architecture}}'
```

O nome da imagem pode variar conforme o diretório/projeto Compose. Confirme também `docker compose ... ps` e os logs.

Teste local na própria VM:

```bash
curl -fsS http://127.0.0.1:8000/health
```

## Critérios antes de liberar o acesso externo

1. Validar instalação ARM64 de PyTorch, Demucs, CTranslate2/faster-whisper e FFmpeg.
2. Resolver a licença dos pesos de separação e selecionar somente modelos autorizados.
3. Implementar autenticação (por exemplo, validar tokens Firebase no backend) e autorização por usuário em **todos** os endpoints de jobs, origem, stems, resultados e exportações.
4. Implementar limites de uso, retenção e exclusão de arquivos, além de TLS.
5. Executar teste real de áudio e conferir stems, transcrição, acordes, PDF e ZIP.
6. Só então configurar o endereço HTTPS no frontend GitHub Pages.

Não coloque chaves privadas, tokens Firebase de serviço, senhas ou arquivos de credenciais no repositório.
