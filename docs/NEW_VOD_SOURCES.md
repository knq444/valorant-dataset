# Novas VODs oficiais para o corpus v0.9

Consulta realizada em **12 de outubro de 2026**. Este documento e
`data/vod_sources_v09.json` registram fontes e seleção de dados; não comprovam
qualidade dos lances nem aprovação humana dos futuros rótulos.

## Fontes confirmadas

As quatro páginas foram consultadas diretamente pelo extrator local
**yt-dlp 2026.08.19**, com `extract_info(download=False)`. Todas retornaram
`availability=public`, `live_status=not_live`, `is_live=false`,
`was_live=false`, o uploader **VALORANT Champions Tour** e o canal
`UCA1d3HFGFUmkKr2JIUA5Vlw` / `@ValorantEsports`.
O [anúncio oficial do Masters London](https://valorantesports.com/en-AU/news/masters-london-everything-you-need-to-know)
identifica esse handle como canal oficial e confirma as equipes e a realização
dos playoffs de 12 a 21 de junho. O
[panorama oficial do Champions Shanghai](https://valorantesports.com/en-US/tournament/115576361459045501/overview)
confirma o evento de setembro–outubro de 2026 e seus participantes.

| Seleção | Série oficial | Publicação informada pelo YouTube | Duração extraída | Evento / fase |
| --- | --- | --- | --- | --- |
| Treino | [Paper Rex × Leviatán](https://www.youtube.com/watch?v=BAH3zpoOYXQ) | 2026-06-12 | 4.789 s · 1:19:49 | Masters London 2026 / playoffs |
| Validação | [LOUD × EDward Gaming](https://www.youtube.com/watch?v=ZphbktbT26k) | 2026-09-26 | 4.658 s · 1:17:38 | Champions Shanghai 2026 / grupos |
| Teste reservado | [G2 × T1](https://www.youtube.com/watch?v=2EzWX2VemjM) | 2026-10-11 | 9.061 s · 2:31:01 | Champions Shanghai 2026 / playoffs |
| Reserva | [NRG × 100 Thieves](https://www.youtube.com/watch?v=UMIkxgmsOTA) | 2026-10-11 | 5.584 s · 1:33:04 | Champions Shanghai 2026 / playoffs |

As duas primeiras constituem a seleção inicial de menor custo, com duas
competições e quatro equipes, abrangendo Americas, Pacific e CN. A terceira
foi adicionada à seleção proposta para um teste inteiro independente; a quarta
é alternativa se uma fonte ficar indisponível. Todas diferem das fontes já
encontradas nas anotações locais: `HkJuEcNu_8E`, `_Mqh048pk9A` e
`58fhQgXv3iY`.

Os títulos das quatro fontes declaram **FULL MATCH**, portanto o catálogo usa
`scope=full_match`, em vez de highlights ou mapa isolado. Essa classificação
é declaração do publicador, **não auditoria visual de continuidade**: não foram
assistidos todos os frames nem verificados os limites dos mapas. Transmissões
podem incluir replays, pausas e cortes de câmera. Os offsets de round e mapa
devem ser extraídos posteriormente; não foram inventados neste catálogo.

`upload_date` é a data de publicação indicada pelo provedor, não prova da data
exata da partida. `match_date` e patch competitivo permanecem `null` / `unknown`
quando não confirmados por fonte primária específica. O patch público vigente
na publicação não deve preencher automaticamente o patch do torneio. As
durações são metadados aproximados; após adquirir mídia, vale a duração
decodificada do manifesto com SHA-256. A listagem simplificada e a consulta
individual divergiram em aproximadamente um segundo para algumas fontes.

## Separação proposta para treino e avaliação

Manter cada vídeo completo em uma única partição: PRX–LEV no treino,
LOUD–EDG na validação e G2–T1 no teste. Frames próximos, replays e recortes da
mesma partida não podem cruzar partições. O teste reservado não participa da
escolha de hiperparâmetros, rótulos ajustados após resultados ou treinamento.

A proposta do trabalho principal é amostrar frames a cada 60 segundos para
expandir o corpus visual. Isso fornece triagem de estados da transmissão;
**não identifica cada movimento nem oferece recall de todas as decisões**.
Eventos curtos exigem pares temporais mais densos e revisão. Usar
`observer_truth`, preservar timestamp global e `available_at`, e manter
`ai_inspected` separado de `human_verified`. A classificação tática de um lance
precisa de contexto e comparação de alternativas sob informação disponível no
instante; placar posterior e resultado da série não validam a decisão anterior.

## Redistribuição e licenças

**Vídeos, frames, áudio e assets de terceiros:** o extrator retornou
`license=null` para as quatro fontes. Isso não comprova CC BY nem permissão de
redistribuição. O [YouTube explica as licenças disponíveis](https://support.google.com/youtube/answer/2797468?hl=en)
e informa que a licença padrão é o default. Seus
[termos, de 15/12/2023](https://www.youtube.com/static?template=terms),
limitam download, distribuição e outros usos às funcionalidades autorizadas
ou à permissão escrita aplicável; o acesso público e o embed não concedem uso
independente do serviço. A consulta não estabelece uma exceção para extrair
treino de IA. O catálogo não concede autorização para download ou treino.

A [política oficial da Riot](https://www.riotgames.com/en/legal), apresentada
como atualizada em agosto de 2018, prevê licença limitada e revogável para
certos projetos comunitários, restringe reutilização de IP em apps e exige
contribuição original, em vez de republicar partidas com comentários leves.
Não equivale a CC BY nem permite sublicenciar indiscriminadamente o material
da Riot. Não foi encontrada autorização específica para este motor ou para
redistribuir suas VODs. A existência de um projeto privado não altera isso.

**Nossas anotações e parâmetros próprios:** a seleção de CC BY 4.0 deve
abranger somente o material original cujos direitos controlamos, com atribuição
e registro de alterações. A
[licença CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
permite compartilhar e adaptar esse material, inclusive comercialmente; não
concede direitos sobre conteúdo externo que o licenciante não possui. Licenciar
pesos próprios não regulariza automaticamente a obtenção dos dados de treino
nem autoriza redistribuir recursos de terceiros embutidos no artefato.

O pacote público proposto pode preservar URLs, IDs, timestamps, hashes,
anotações originais, proveniência, estado de revisão e parâmetros próprios,
sem incluir VODs, imagens, clipes, áudio, transcrições copiadas ou logos. A
licença do pacote precisa declarar expressamente esse escopo. É uma proposta
de publicação do nosso material, **não alegação de aprovação da Riot ou de
licença CC das fontes**.

## Reproduzir a verificação

```powershell
python -m yt_dlp --skip-download --no-playlist --print "%(id)s | %(title)s | %(channel)s | %(channel_id)s | %(upload_date)s | %(duration)s | %(live_status)s | %(license)s" https://www.youtube.com/watch?v=BAH3zpoOYXQ https://www.youtube.com/watch?v=ZphbktbT26k https://www.youtube.com/watch?v=2EzWX2VemjM https://www.youtube.com/watch?v=UMIkxgmsOTA
```

O extrator avisou que não encontrou runtime JavaScript compatível, podendo
omitir formatos; os campos de identidade e duração acima foram retornados.
Não foram usadas fontes agregadoras para confirmar as fontes finais. Esta
auditoria não baixou mídia, não publicou artefatos e não alterou código.
