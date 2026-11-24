# AudioSplit & Cifra Pro

Aplicativo web para separação de fontes de áudio, transcrição vocal, reconhecimento harmônico e sincronização temporal de letra e cifras.

## Estrutura

- `frontend/`: interface responsiva, player da música original, players dos stems, timeline clicável, editor e exportação.
- `backend/app/`: API FastAPI, banco SQLAlchemy, fila Celery, pipeline de áudio, ASR, alinhamento opcional e reconhecimento harmônico.
- `docker-compose.yml`: API, worker e Redis.
- `docs/`: contratos de dados e arquitetura.

## Inicialização local

Requer Docker e Docker Compose:

```bash
docker compose up --build
```

A API estará em `http://localhost:8000`; documentação em `http://localhost:8000/docs`; health check em `/health`.

Abra a interface em `frontend/index.html` por um servidor estático (por exemplo, `python -m http.server 8080 -d frontend`) ou habilite GitHub Pages na raiz do repositório. O arquivo `index.html` da raiz redireciona para `frontend/`. No campo “Endereço da API”, informe o endereço do backend acessível pelo navegador. `localhost` só funciona quando o navegador e o Docker estão na mesma máquina. O backend ainda precisa ser hospedado em um servidor separado para acesso externo.

## Pipeline implementado

1. Upload com validação de extensão e limite de 250 MB.
2. Persistência do job e arquivo em volume privado.
3. Fila assíncrona Celery/Redis.
4. Separação de quatro stems com Demucs `htdemucs_ft`: vocals, drums, bass e other.
5. Transcrição da voz com faster-whisper, configurada inicialmente para português.
6. Alinhamento forçado opcional com WhisperX/Wav2Vec2. Se o alinhador não carregar ou falhar, o pipeline mantém os timestamps estimados do ASR e registra a limitação.
7. Estimativa de acordes por chroma CQT/templates no stem harmônico, com conferência do mix e eventos não sobrepostos.
8. Estimativa de BPM e pulsos.
9. Resultado JSON, consulta de estado e download individual dos stems.

O primeiro download dos pesos dos modelos pode ser grande e o processamento é pesado. O Compose atual é uma configuração de desenvolvimento em CPU; para produção, recomenda-se worker com GPU, fila/banco gerenciados e armazenamento de objetos.

## Interface

A interface permite:
- selecionar/enviar áudio e acompanhar o processamento;
- ouvir o áudio original e cada stem;
- editar o texto reconhecido, os tempos por palavra e os símbolos/tempos dos acordes;
- clicar em eventos temporais para posicionar a reprodução, reabrir projetos e salvar revisões no servidor;
- exportar JSON com os timestamps e TXT com eventos em ordem cronológica.

## Limitações que ainda exigem validação

- Demucs `htdemucs_ft` gera quatro grupos; guitarra e piano permanecem dentro de “other”.
- Whisper/Wav2Vec2 foram treinados principalmente para fala. Em canto, transcrição e alinhamento podem errar, mesmo quando o modelo retorna confiança.
- O alinhamento de caracteres não equivale automaticamente a divisão silábica musical.
- O reconhecedor de acordes é um baseline por chroma/template; o índice de similaridade não é probabilidade calibrada. Tensões, inversões, acordes rápidos e arranjos densos exigem revisão.
- BPM e pulsos são estimativas; o compasso não é inferido nesta versão.
- Não há autenticação, cotas, política de retenção, antivírus ou proteção contra abuso. Não exponha o backend publicamente antes de adicionar esses controles.

## Configuração de modelos

Por padrão, o Compose usa `htdemucs_ft`, `small` do faster-whisper e alinhamento WhisperX em CPU. Para experimentar seis stems (guitarra e piano separados), altere `DEMUCS_MODEL=htdemucs_6s` no serviço `worker`. Esse modelo deve ser comparado em gravações reais antes de ser considerado superior. Para um servidor com GPU, configure PyTorch/CUDA e `WHISPER_DEVICE=cuda`, `WHISPER_COMPUTE_TYPE=float16` e `ALIGNMENT_DEVICE=cuda`, usando uma imagem Docker compatível com o driver NVIDIA.

## Validação

A suíte automatizada verifica sintaxe do frontend/backend, padrões sintéticos de acordes, estimativa de BPM e métrica SI-SDR. A validação de separação e ASR com gravações musicais reais ainda depende de conjunto de referência e execução em servidor com os modelos baixados.

Métricas previstas:
- separação: SI-SDR/SDR e avaliação auditiva por stem;
- letra: WER/CER em repertório cantado em português brasileiro;
- alinhamento: erro temporal de início/fim;
- acordes: precisão/recall de símbolos e F-score de fronteiras;
- sincronização: diferença temporal entre mudança harmônica anotada e evento exibido.
