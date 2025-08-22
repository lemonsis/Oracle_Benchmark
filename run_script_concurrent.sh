#!/bin/bash

EVA_MODEL_FAMILY="all"
TASK="encryption"
EVA_MODE="concurrent"
MAX_TURNS=10
K=0

python main.py \
    --eva_model_family $EVA_MODEL_FAMILY \
    --task $TASK \
    --eva_mode $EVA_MODE \
    --max_turns $MAX_TURNS \
    --k $K \