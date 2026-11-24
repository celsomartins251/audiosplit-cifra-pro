# Licenciamento e proveniência de modelos

Este documento separa licença do código e licença dos pesos. Uma licença MIT do repositório de código não concede automaticamente direitos comerciais sobre checkpoints treinados com conjuntos de dados de terceiros.

## Decisões atuais

| Componente | Código | Pesos/modelo | Decisão do projeto |
|---|---|---|---|
| Demucs HTDemucs/HTDemucs FT/6s | MIT no código | Situação dos pesos não está suficientemente clara para assumir uso comercial irrestrito; o treinamento inclui MUSDB18-HQ e dados adicionais | Usar apenas em desenvolvimento/testes privados até esclarecer direitos ou obter licença |
| BS-RoFormer/MelBand-RoFormer | Código de referência pode ser MIT | Checkpoints comunitários podem ter licença não comercial | Não incorporar pesos sem licença comercial expressa |
| BTC/ChordMini | Código-fonte MIT | Checkpoints dependem de proveniência e dados de treinamento; há checkpoints BTC conhecidos com restrição não comercial | Não distribuir nem usar comercialmente sem licença específica |
| Chroma/template próprio | Código desenvolvido neste projeto | Não utiliza checkpoint de terceiros | Baseline atual, sujeito a avaliação de qualidade |
| faster-whisper/Whisper | Verificar avisos e licenças da versão instalada | Pesos oficiais Whisper têm licença própria; preservar avisos e proveniência | Manter inventário de versões e avisos |
| WhisperX/Wav2Vec2 português | Licença do código e do checkpoint são itens separados | Verificar a licença do modelo de alinhamento baixado | Não assumir liberação comercial sem verificar o checkpoint exato |

## Referências para diligência

- Demucs: https://github.com/facebookresearch/demucs
- Demucs licensing discussion: https://github.com/facebookresearch/demucs/issues/327
- Spleeter: https://github.com/deezer/spleeter
- Spleeter question about pretrained weights: https://github.com/deezer/spleeter/issues/959
- BTC: https://github.com/jayg996/BTC-ISMIR19
- ChordMini: https://github.com/ptnghia-j/ChordMini
- WhisperX: https://github.com/m-bain/whisperX

## Regra de publicação

1. Não empacotar pesos com licença não comercial ou incerta em uma versão comercial.
2. Registrar URL, versão, SHA-256, licença, autor e origem de cada checkpoint.
3. Preferir pesos com concessão comercial explícita ou modelos treinados pelo projeto em dados próprios/licenciados.
4. Manter o motor de separação substituível por configuração, sem acoplar a interface a um fornecedor.
5. Não presumir que o direito de processar um áudio implica direito de redistribuir o áudio ou os stems.

Esta documentação é uma triagem técnica de licenças, não aconselhamento jurídico. A publicação comercial deve passar por revisão jurídica.
