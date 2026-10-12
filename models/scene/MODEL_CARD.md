# Detector semântico visual

Status: trained_exploratory. Supervisão: ai_assisted_exploratory.

Amostras elegíveis: 535; aprendidas: 358. Split: match_holdout_fixed.

Teste: {"n": 177, "accuracy": 0.9265536723163842, "log_loss": 0.3264011325638658, "brier": 0.1275969144792751, "macro_f1": 0.7744957983193277, "class_order": ["gameplay_pov", "tactical_map", "replay", "broadcast_break", "unknown"], "confusion_matrix": [[114, 0, 2, 3, 0], [0, 0, 0, 0, 0], [2, 0, 15, 2, 0], [1, 0, 0, 34, 0], [2, 0, 0, 1, 1]], "abstention_rate": 0.011299435028248588, "accepted_n": 175, "accepted_accuracy": 0.9314285714285714}.

Reconhece classes visuais de transmissão. Não estabelece decisão tática, qualidade de lance nem probabilidade de vitória. Rótulos inspecionados por IA não equivalem a revisão humana independente. Holdout de blocos de uma VOD não mede generalização entre partidas. Mídias permanecem locais.
