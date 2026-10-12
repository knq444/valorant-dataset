# Pesquisa tática de VALORANT para revisão das duas equipes

Pesquisa realizada em **12/10/2026**. Fontes primárias: publicações da Riot,
resposta direta de jogador em espaço oficial de sua organização, artigos dos
próprios pesquisadores e repositório do autor. Os textos abaixo distinguem
**regra/documentação consultada**, **resultado publicado** e **inferência de
engenharia**. As inferências são propostas de avaliação; sua presença neste
documento não comprova implementação, acerto de rótulos ou ganho competitivo.

## 1. O que muda ao avaliar duas equipes

A unidade de análise deve ser `(partida, mapa, round, instante, equipe,
perspectiva)`. `team_id` é identidade persistente; `side` é ataque/defesa naquele
round; cor e posição do overlay são propriedades da transmissão. A Riot mudou
as cores de observer para permanecerem ligadas à equipe ao longo da partida,
em vez de sempre indicar o lado. Portanto **cor não basta para inferir lado**.
A mesma atualização documenta renda reduzida para atacantes que sobrevivem a
uma derrota sem plant e defensores que sobrevivem à detonação. Esses valores
são registro histórico, a conferir no perfil do patch analisado.
[Riot, patch 1.11, 27/10/2020](https://playvalorant.com/en-us/news/game-updates/valorant-patch-notes-1-11/).

**Inferência de engenharia:** manter duas avaliações próprias, nunca produzir
a segunda como `100 − nota_da_primeira`. Uma nota compara ações disponíveis
para a mesma equipe; equipes distintas têm informações e alternativas
diferentes. Mesmo uma probabilidade complementar só seria legítima em um
modelo binário calibrado do **mesmo** resultado de round, sob o mesmo estado e
denominador. A pontuação atual do projeto não é tal probabilidade.

Para cada equipe, guardar: identidade, lado, jogadores vivos, recursos que
pertencem àquela equipe, controle do objetivo e ações efetivamente observadas.
Uma redução de munição no POV da equipe A não revela munição de B. A ausência
do jogador B na câmera é ausência de observação, não prova de inatividade.
Registrar uma janela temporal para ambas as equipes é possível; reconhecer
todas as decisões dos dez jogadores depende de evidência que o observer pode
não ter filmado.

## 2. Patch, mapa e modalidade fazem parte do estado

O índice oficial consultado mostra o patch **13.06, de 22/09/2026**, como a
publicação mais recente disponível. Isso é uma fotografia da pesquisa, não
prova de qual patch rodou em qualquer torneio.
[Índice Riot](https://playvalorant.com/en-us/news/tags/patch-notes/),
[patch 13.06](https://playvalorant.com/en-us/news/game-updates/valorant-patch-notes-13-06/).

O patch 11.08, publicado **14/10/2025**, alterou habilidades, armas e geometria
de Pearl/Abyss: entre outros exemplos, Recon Bolt de Sova passou de 40 s para
60 s de cooldown; Dark Cover de Omen de 30 s para 40 s; visão sob Nearsight de
5 m para 7 m. A Riot relacionou essas mudanças a coordenação e contrajogo.
[Riot, patch 11.08](https://playvalorant.com/en-us/news/game-updates/valorant-patch-notes-11-08/).

Em 13.00, de **23/06/2026**, cooldowns de assinaturas de Sova, Fade, Skye,
Breach e KAY/O foram reduzidos de 60 s para 50 s, e recuperação de habilidades
de Gekko de 20 s para 15 s. O modo Retake descrito ali é 3v3, com spike
pré-plantada e sem economia, diferente de uma partida profissional 5v5.
[Riot, patch 13.00](https://playvalorant.com/en-us/news/game-updates/valorant-patch-notes-13-00/).

**Inferência de engenharia:** o perfil de regras deve ter versão, patch,
modalidade, geometria e intervalos de validade. Nunca atualizar retroativamente
o cálculo de uma VOD de 2025 com cooldowns de 2026. A documentação oficial de
Champions Paris situa o evento entre setembro e 05/10/2025, antes do patch
11.08. Não foi localizada nesta pesquisa uma declaração primária que confirme
o número exato do patch do torneio; deixar `patch=unknown` até obter evidência
direta. O patch 11.05 existe e foi consultado, mas sua existência não comprova
uso no evento.
[Champions Paris, Riot](https://playvalorant.com/en-us/news/esports/everything-you-need-to-know-champions-paris/),
[patch 11.05](https://playvalorant.com/en-us/news/game-updates/valorant-patch-notes-11-05/).

## 3. Objetivo, tempo e economia: avaliar o round

A introdução oficial explica equipes de cinco, troca de lado após doze rounds,
compras de armas/habilidades e objetivos de plantar/detonar ou desarmar. Também
apresenta smokes como meios de bloquear linhas de visão, atenção a mapas e
ângulos, comunicação, escolha entre caminhar/correr e a importância de parar
antes de atirar para melhorar precisão. Os números de agentes/mapas dessa
página de 2024 são históricos e não foram tratados como catálogo atual.
[Riot, Beginner’s Guide, 02/08/2024](https://playvalorant.com/en-us/news/announcements/beginners-guide/).

**Regras operacionalizáveis propostas — inferências deste projeto:**

| Situação | Avaliação condicional | Alternativa a comparar | Contraexemplo / dado necessário |
| --- | --- | --- | --- |
| Ataque, spike não plantada | Calcular margem `tempo_do_round − deslocamento − limpeza − plant − margem_de_execução` | Acelerar, trocar rota ou disputar eliminação se o plant ficou inviável | Tempo de chegada e limpeza desconhecidos não podem virar zero; portador/rota podem estar inacessíveis |
| Defesa antes do plant | Conter acesso e gastar tempo pode valer mais que buscar kill | Recuar para cobertura com visão de entrada e suporte | Esperar fora do site não impede plant; ataque pode trocar de site |
| Ataque após plant | Comprar tempo e preservar capacidade de impedir desarme | Crossfire, contato coordenado, utilitário de atraso ou reposição com visão do objetivo | Esconder-se sem linha de tiro/utilitário permite desarme; lineup distante pode chegar tarde |
| Defesa após plant | Reservar deslocamento, limpeza e duração restante do desarme | Retake sincronizado, tap para informação ou continuidade protegida | Um tap desperdiça tempo se já não houver janela para concluir; metade já desarmada muda a duração restante |
| Vantagem numérica | Comparar preservação da vantagem com execução do objetivo | Contatos com trade, manutenção de controle ou recuo | 5v3 não garante posse do site, munição, tempo ou ausência de ultimate decisiva |
| Desvantagem numérica | Buscar confrontos separáveis pode reduzir dificuldade local | Dividir defesa, informação barata, efeito de utilitário ou save | Estar atrás não obriga duelo solo quando ainda existe proteção ou desarme disponível |
| Save | Avaliar equipamento preservado, renda prevista e próximo round | Tentar objetivo, buscar dano econômico ou preservar arma | Último round da metade, match point e renda de sobrevivente mudam o valor de guardar equipamento |

Não fixar durações de plant/desarme/detonação sem perfil verificado para a
modalidade e patch. Separar cronômetro de round e cronômetro de spike: o
cronômetro normal pode desaparecer após plant. Uma observação ausente não é
"zero segundos" nem "spike não plantada".

Um preprint de David Wang, publicado em 16/05/2025, estudou economia e
ultimates em **1.301 rounds** de VCT Pacific/EMEA 2024 usando regressão
logística. Relata **60,61%** de acurácia e maior influência de loadout que das
outras variáveis consideradas. É resultado preliminar, não replicado aqui, sem
transferência de parâmetros para o motor. Sustenta investigar economia como
variável contextual; não permite inferir que comprar mais ou salvar sempre
causa vitória.
[Artigo original, TechRxiv](https://doi.org/10.36227/techrxiv.174742078.82022650/v1).

## 4. Trade, spacing, crossfire e abertura de ângulos

**Definições operacionais propostas, não limiares oficiais:**

- **Trade possível:** um aliado consegue obter linha de tiro sobre a mesma
  ameaça dentro de uma janela útil, com arma pronta e capacidade de confronto.
  Proximidade visual ou distância euclidiana sozinha não comprova trade.
- **Spacing útil:** relação entre tempo de chegada ao contato, linha de visão e
  vulnerabilidade compartilhada. Muito perto pode permitir spray/flash/área
  contra ambos; muito longe pode permitir que o inimigo mate e recue.
- **Crossfire funcional:** posições distintas pressionam o mesmo acesso e não
  são isoladas por cobertura, smoke ou ausência de sincronia. Duas posições
  apenas diferentes no minimapa não são prova de crossfire.
- **Peek coordenado:** comparar contatos simultâneos ou escalonados, arma
  adversária, cobertura e efeito de utilitário. Um único `peek` abstrato não
  representa jiggle, wide swing, jump peek e abertura para trade.
- **Repetição de ângulo:** informação revelada pelo contato anterior pode
  alterar o risco de reabrir; manter memória com expiração e alcance do que
  cada equipe realmente viu/ouviu.

O estudo de DeMars DeRover, publicado no espaço do MIT Sloan Sports Analytics
Conference, modela dificuldades de duelos a partir de dados posicionais.
O repositório original explica que suas heatmaps de coordenadas, isoladas,
não incluem armas/armadura e que o modelo acrescenta esse contexto. O autor
relata colaboração com o coach JoshRT/NRG. Este resultado orienta medir
geometria e equipamento, sem importar probabilidades antigas para VODs novas
nem confundir ganhar um duelo com escolher a melhor tática de round.
[Publicação original](https://www.sloansportsconference.com/research-papers/winning-duels-in-valorant-a-visualization-of-optimal-positioning),
[código e descrição do autor](https://github.com/jlirms/valorant-analytics).

A Riot explica que animação/movimento vistos por outro cliente podem estar
dessincronizados em relação ao disparo e que peeker’s advantage depende de
latência, renderização e processamento. Os valores apresentados são de 2020,
não medidas das VODs atuais. Portanto um frame de transmissão não prova erro
de tiro em movimento nem autoriza uma estimativa milimétrica de reação.
[Riot, 04: On Peeker’s Advantage & Ranked, 13/05/2020](https://playvalorant.com/en-us/news/game-updates/04-on-peeker-s-advantage-ranked/).

**Implementação sugerida:** trocar `teammate_support: bool` por evidências
separadas de linha de tiro, tempo até contato, arma pronta e ameaça compartilhada
quando essas observações existirem. Não considerar automaticamente qualquer
aliado próximo como bônus +20. Preservar a compatibilidade do fato atual, mas
exibir que ele não resolve essas condições.

## 5. Utilitário: finalidade, janela e contrajogo

**Inferências propostas:** uma habilidade deve ser avaliada por alvo, espaço
obtido/negado, duração, coordenação com entrada/retake, custo de equipar e
possibilidade de recuperação/recharge. Compare guardar, usar agora e usar em
outro alvo. `utility_ready=True` apenas torna uma classe de ação disponível;
não comprova que lançar qualquer utilitário é melhor.

Para uma combinação, registrar a cadeia temporal: informação ou supressão →
remoção de ângulo ou deslocamento → contato de jogadores → proteção do
objetivo. Não atribuir sucesso a um combo só porque os efeitos aparecem no
mesmo trecho: medir sobreposição útil e contato antes de acabar o efeito.
Contraexemplos: flash que atinge aliados, smoke que remove a visão do próprio
crossfire, stun sem aliado que possa explorar, usar uma carga insubstituível
sem alvo e gastar tempo em lineup quando o desarme já está ocorrendo.

Também comparar resposta adversária: destruir utilitário, recuar, esperar
expiração, avançar antes da execução, contestar outro acesso. Esses são ramos
condicionais; probabilidades exigem dados e calibração.

No AMA oficial da FNATIC de **18/06/2026**, Boaster respondeu diretamente que
liderar ranked exige adaptar-se aos parceiros, mencionou apoio com utilitário
e relacionou paredes/orbs de Viper a facilitar ações da equipe. Contrapôs
comportamento agrupado de ranked a defaults e discutiu uso reativo de ultimate
na defesa. É orientação contextual de um jogador, não lei universal nem
declaração de que determinada composição é obrigatória.
[Resposta original de Boaster na FNATIC](https://fnatic.com/community/6610-ama-valorant-team-ama-presented-by-blacklyte).

**Consequência proposta:** os regimes `professional_organized`, `ranked` e
`unknown` devem permanecer separados; sincronia e calls ausentes não podem ser
presumidas com base no nome do time. Não diagnosticar intenção, confiança ou
estado mental a partir de um atraso observado.

## 6. Informação, observer e dados dos dez jogadores

A documentação de Replays da Riot, de **16/09/2025**, descreve dez perspectivas
em primeira pessoa, câmera livre e controles temporais. Seus problemas
conhecidos incluem: desligar outlines de inimigos **não** remove posições
inimigas do minimapa; mapas de habilidade e previews de placement não aparecem
como na execução original. Logo um vídeo de replay com outlines desligados
ainda pode conter conhecimento privilegiado. As respostas de alguns FAQs
colapsados não foram recuperadas pelo leitor web; não foram usadas para
afirmar disponibilidade de arquivos profissionais ou gravação de calls.
[Riot, Replays: Everything You Need to Know](https://playvalorant.com/en-us/news/dev/replays-everything-you-need-to-know/).

**Proposta para o projeto:** importar gravações autorizadas sincronizadas das
perspectivas quando disponíveis. Modo observer avalia cenário da transmissão;
modo jogador recebe somente evidências comprovadamente acessíveis àquele
jogador/equipe. Reconstruir ou mascarar o minimapa privilegiado antes de usar
replay como observação do jogador. O pipeline não precisa nem deve controlar
o cliente para esta análise offline.

Manter crença separada para cada equipe. Uma call só entra no instante em que
ficou audível; narração e conhecimento dos casters não são calls do time.
Marcar escopo de áudio: som do jogo daquele POV, caster ou comunicação real.
Persistir última observação, incerteza, possíveis rotas e expiração; inimigo
sumido não significa inimigo morto nem posição conhecida para sempre.

Um artigo de Hayakawa et al. usa TimeSformer e eventos do minimapa de
transmissões oficiais de 2024, cujo minimapa mostra **ambas as equipes**.
Relata **80,55%** de acurácia média por segundo versus 72,28% sem rótulos
táticos adicionais; o início do round foi pior com a versão enriquecida.
O texto descreve 100 rounds amostrados para avaliação e exclui rounds acima
de 100 s da seleção inicial. Não demonstra julgamento causal de cada ação,
calibração de probabilidade ou generalização do nosso detector. Sua descrição
não estabelece separação por partida/patch nem explicitamente causalidade do
contexto temporal do modelo; estes pontos exigem reprodução antes de adoção.
[Artigo original, arXiv:2510.17199](https://arxiv.org/pdf/2510.17199).

## 7. Inferir uma alternativa melhor sem conhecer o futuro

Para cada lance, emitir quatro campos distintos:

1. **Observado:** fatos e referências de frame/áudio disponíveis no instante.
2. **Inferido:** hipótese de ação, intenção ou estado oculto e sua incerteza.
3. **Alternativa:** ação viável encontrada com o mesmo conjunto de informação.
4. **Risco:** contrajogada e fatos faltantes que podem inverter a preferência.

Exemplo **sintético**, não análise de profissional: defensor com arma pronta,
spike plantada e acesso protegido pode comparar completar desarme com abrir
ângulo. Sem tempo de spike, progresso do desarme e cobertura efetiva, não há
base para dizer que um deles é "Blunder". Outro exemplo sintético: atacante
sem plant e sem tempo suficiente para rota+plant pode preferir disputar a
eliminação; um ranking que recomenda ficar parado porque aumenta sobrevivência
estaria otimizando o objetivo errado.

O artigo de Xenopoulos et al. sobre CS:GO propõe valorizar ações pela mudança
na chance estimada de vitória, com contexto e medidas de incerteza, em vez de
contagens isoladas. É inspiração metodológica, em outro jogo, com dados que
este projeto ainda não tem. Variação entre estados antes/depois de uma ação
também não é automaticamente efeito causal de escolher essa ação.
[Artigo original, arXiv:2011.01324](https://arxiv.org/abs/2011.01324).

Pesquisa de avaliação off-policy em ambientes parcialmente observáveis mostra
que variáveis ocultas podem produzir estimativas enviesadas e erros grandes.
Outro trabalho formula trajetórias contrafactuais com modelos causais e
hipóteses específicas. Ambos impedem tratar correlação observacional como
garantia de que "a alternativa venceria"; não são benchmarks de VALORANT.
[Tennenholtz, Shalit e Mannor, AAAI 2020](https://ojs.aaai.org/index.php/AAAI/article/view/6590),
[Oberst e Sontag, ICML 2019](https://proceedings.mlr.press/v97/oberst19a.html).

## 8. Mudanças recomendadas na rubrica existente

Inspeção da rubrica inicial feita em `src/cortexarena/analysis/tactical_vod.py`.
A tabela registra os achados daquela inspeção. Após a pesquisa, a rubrica v2
corrigiu a separação de relógios, deslocamento desconhecido, propagação do
countdown e urgência por lado/fase; `save` saiu das sugestões automáticas e
passou a exigir abstenção por falta de economia. Essas correções não resolvem
geometria, utilitário específico nem as demais propostas da tabela.

| Problema observado no cálculo atual | Mudança proposta | Verificação que deve acompanhar |
| --- | --- | --- |
| Base de survival alta para `save`, sem fatos econômicos | Exigir justificativa econômica e horizonte restante; separar valor de round e de próximo round | Mesmo estado, último round vs começo da metade deve admitir preferência distinta |
| Peso fixo de sobrevivência pode dominar obrigação de objetivo | Viabilidade temporal e objetivo como restrições antes de bônus; condicionamento por lado/fase | Esperar na defesa antes do plant vs esperar na defesa após plant |
| Tempo de deslocamento ausente usado como zero ao testar duração | Marcar tempo necessário desconhecido, sem declaração de viabilidade | `plant_duration` conhecido, rota desconhecida não comprova que há tempo |
| Um booleano de suporte dá grande bônus a múltiplas ações | Evidência de trade/cobertura por ameaça e prontidão | Aliado próximo atrás de parede ou sem arma pronta não equivale a cobertura |
| `use_utility` usa base genérica sem habilidade/alvo | Só propor combo/lineup específico com habilidade, patch, carga, alvo e duração | Utilitário que corta crossfire próprio pode ser pior que guardar |
| Ações abstratas não representam coordenação de time | Separar decisão individual e plano de equipe, com sincronização e dependências | Cinco decisões individuais razoáveis podem ser incompatíveis em conjunto |
| Duas equipes poderiam compartilhar fatos indevidamente | Identidade estável e contextos separados; escopo observer explícito | Troca de lado, POV, replay e rounds repetidos não devem mesclar recursos |

Não trocar pesos fixos por outros números anunciados como "científicos". Para
esta fase, publicar as regras e contribuições, comparar cenários/contraexemplos
e admitir intervalo de sensibilidade e indeterminação. Citar o ID da regra e
sua evidência na explicação. `human_verified` continua distinto de
`ai_inspected`; uma inferência desta IA não vira revisão humana independente.

## 9. Validação e dados que tornam o motor melhor

**Protocolo proposto:** analistas revisam o contexto até *t*, sem assistir ao
resultado antes de rotular alternativas; registram informação faltante e
mais de uma ação aceitável. Um segundo analista revisa amostra independente.
Guardar divergências em vez de forçar um único rótulo. Após avaliação cega,
resultado posterior pode medir associação, nunca mudar o que o jogador sabia.

- Separar treino, validação e teste por séries inteiras; incluir equipes,
  mapas, patches e transmissões inéditos.
- Medir detecção por equipe e classe, cobertura/abstenção e continuidade de
  identidade. Reportar replay, transições e overlays fora do perfil.
- Para alternativas, medir concordância entre avaliadores, top-k aceitável,
  violações de viabilidade e sensibilidade a fatos desconhecidos.
- Para um futuro modelo de resultado: especificar alvo de round, instante,
  amostragem, baseline e Brier/log-loss/ECE por lado e fase, sem chamar uma
  softmax de cenas de probabilidade de vitória.
- Para contrafactuais: simulador validado ou hipóteses causais explícitas,
  ablações e avaliação independente. Um bom predictor de desfecho não basta
  para identificar intervenção melhor.

**Validado nesta pesquisa:** leitura das fontes linkadas, inspeção do cálculo
existente e entrega deste documento. **Não validado:** eficácia competitiva
das regras propostas, acurácia de detecção dos dez jogadores, avaliações
humanas, permissões de redistribuição de VODs ou transferência dos resultados
publicados. Não foram assistidos vídeos completos nem atribuídas recomendações
a treinadores com base apenas em título/miniatura de vídeo.
