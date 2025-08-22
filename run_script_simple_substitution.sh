#!/bin/bash

EVA_MODEL_FAMILY="gpt"
EVA_MODEL_NAME="gpt-4.1"
TASK="encryption"
TASK_ID="simple_substitution.json"
EVA_MODE="normal"
MAX_TURNS=20
K=1

python main.py \
    --eva_model_family $EVA_MODEL_FAMILY \
    --eva_model_name $EVA_MODEL_NAME \
    --task $TASK \
    --task_id $TASK_ID \
    --eva_mode $EVA_MODE \
    --max_turns $MAX_TURNS \
    --k $K \