# Arquitetura do pipeline de processamento

## Fluxo atual

1. API recebe o arquivo e valida extensão e limite de tamanho.
2. Arquivo recebe identificador aleatório e é armazenado fora da pasta pública.
3. Registro do job é persistido no banco SQL.
4. API envia o identificador para a fila Celery/Redis.
5. Worker assume o job e atualiza seu estado.
6. Enquanto os modelos não estiverem integrados, o worker marca o job como falha controlada com código explícito.

## Próxima integração de modelos

O worker será dividido em etapas independentes:
- inspeção técnica e normalização do áudio;
- separação de fontes (benchmark Demucs/MDX e alternativas);
- transcrição vocal em português;
- alinhamento temporal de palavras e, quando suportado, sílabas;
- reconhecimento harmônico no mix e nas fontes relevantes;
- consolidação de eventos numa timeline comum.

## Requisitos de qualidade

Cada etapa deverá registrar versão do modelo, parâmetros, timestamps, confiança e artefatos produzidos. Resultados não serão apresentados como concluídos sem saída real e validação.

## Ambiente de desenvolvimento

Execute `docker compose up --build`. API em `http://localhost:8000`; documentação OpenAPI em `/docs`; verificação em `/health`.

## Limitações atuais

A persistência e a fila foram estruturadas, mas o worker ainda não executa inferência musical. SQLite é apenas configuração de desenvolvimento; produção deverá usar banco gerenciado e armazenamento de objetos com autenticação e política de retenção.
