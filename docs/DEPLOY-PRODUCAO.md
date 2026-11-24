# Implantação de produção — AudioSplit & Cifra Pro

## Estado atual

O repositório contém uma interface estática e uma API/worker preparados para execução em Docker. O GitHub Pages publica somente os arquivos de `frontend/`; ele não executa FastAPI, Celery, Redis, FFmpeg, Demucs ou Whisper.

**Não existe, neste repositório, uma API pública de produção provisionada.** Não configure o endereço do GitHub Pages como endereço da API. O processamento real depende dos serviços descritos abaixo.

## Ativação do GitHub Pages

A automação tentou criar o site Pages, mas o token do GitHub Actions recebeu `Resource not accessible by integration` ao chamar a API de criação do site. Essa configuração administrativa precisa ser ativada pelo proprietário do repositório:

1. Abra **Settings → Pages** no repositório.
2. Em **Build and deployment → Source**, selecione **GitHub Actions**.
3. Salve a configuração. O workflow fará o upload de `frontend/` e publicará a interface no próximo push ou execução manual.

A permissão `pages: write` do workflow não substitui a ativação inicial do recurso quando a integração não tem permissão para criar o site.

## Arquitetura necessária

- **Frontend:** GitHub Pages ou hospedagem estática HTTPS.
- **API:** serviço FastAPI em HTTPS, com domínio próprio.
- **Worker:** processo Celery separado, com CPU/GPU e memória suficientes.
- **Fila:** Redis privado, sem porta pública.
- **Banco:** PostgreSQL recomendado para produção; SQLite fica restrito ao desenvolvimento/instância única.
- **Armazenamento:** volume ou object storage privado e persistente para originais, stems e resultados.
- **Proxy TLS:** termina HTTPS e encaminha à API; não expor diretamente a porta interna 8000.

API e worker precisam compartilhar o mesmo banco e armazenamento. O worker também precisa acessar o broker Redis.

## Bloqueios obrigatórios antes de abrir ao público

1. Implementar autenticação e autorização por usuário/projeto. Atualmente, conhecer um `job_id` permite consultar o job, resultado, áudio original e stems; UUID não substitui autorização.
2. Adicionar cotas por usuário/IP, limite de jobs simultâneos, proteção contra abuso e rate limiting.
3. Configurar `CORS_ORIGINS` com a origem exata do frontend. Nunca usar `*` em produção.
4. Manter Redis, banco, volumes e endpoints administrativos privados.
5. Definir retenção e exclusão automática dos áudios originais, stems e projetos; informar claramente ao usuário.
6. Aplicar TLS, logs sem conteúdo sensível, monitoramento, backups e limites de CPU/memória/disco.
7. Validar arquivos pelo conteúdo com FFmpeg/ffprobe, além da extensão, e manter limites de tamanho e duração.
8. Fazer revisão de segurança e teste de carga antes de liberar uploads públicos.

O Compose da raiz é de desenvolvimento local: a API fica vinculada a `127.0.0.1:8000` e o CORS aceita somente as origens locais configuradas. Não o use como configuração pública.

## Modelos e direitos de uso

O pipeline bloqueia por padrão pesos de separação cuja licença não foi confirmada. A variável `ALLOW_UNCLEARED_MODEL_WEIGHTS` deve permanecer desativada em produção até a seleção de um checkpoint com direitos compatíveis e documentados. A ativação explícita existente no worker do Compose destina-se somente a testes privados locais; não copie essa configuração para um servidor público.

Antes de publicar, registrar para cada checkpoint: nome exato, origem, versão, SHA-256, licença e autorização de uso comercial. Conferir também os pesos de ASR e alinhamento separadamente do código das bibliotecas.

## Configuração mínima do serviço

Definir por secret manager ou variáveis protegidas, nunca em commits:

- `DATABASE_URL`: PostgreSQL gerenciado/privado.
- `CELERY_BROKER_URL` e `CELERY_RESULT_BACKEND`: Redis privado.
- `DATA_DIR`, `UPLOAD_DIR`, `MODEL_DIR`: caminhos persistentes e com permissões mínimas.
- `CORS_ORIGINS`: domínio HTTPS exato do frontend.
- `DEMUCS_MODEL`, `WHISPER_MODEL`, dispositivos e limites operacionais aprovados.
- `ALLOW_UNCLEARED_MODEL_WEIGHTS=false` até a aprovação formal dos pesos.

Executar API e worker como usuário sem privilégios. Fixar versões de imagens e dependências, e reconstruir/testar antes de atualizar produção.

## Sequência de validação para liberar o link

- [ ] GitHub Pages habilitado com fonte GitHub Actions e deploy concluído.
- [ ] Endpoint `/health` acessível em HTTPS.
- [ ] API autenticada e autorização testada entre contas/projetos diferentes.
- [ ] Upload de arquivo válido e rejeição de arquivo inválido/maior que o limite.
- [ ] Job passa por queued → processing → completed.
- [ ] Stems gerados e reproduzidos pelo navegador.
- [ ] Transcrição, acordes e BPM retornados e revisáveis.
- [ ] Edições persistem após reabrir o projeto.
- [ ] JSON, TXT e ChordPro exportados e conferidos.
- [ ] Teste de exclusão/retensão, falhas de worker, reinício e carga concluído.
- [ ] Licenças dos pesos e custos de infraestrutura aprovados.

Até todos os bloqueios de segurança e os testes de ponta a ponta estarem concluídos, o link da interface deve ser tratado como prévia visual, não como serviço pronto para enviar áudios.
