#!/bin/bash

EVA_MODEL_FAMILY="human"
EVA_MODEL_NAME="human"
TASK="physics"
TASK_ID="cycloid.json"
EVA_MODE="normal"
MAX_TURNS=5
K=0

python main.py \
    --eva_model_family $EVA_MODEL_FAMILY \
    --eva_model_name $EVA_MODEL_NAME \
    --task $TASK \
    --task_id $TASK_ID \
    --eva_mode $EVA_MODE \
    --max_turns $MAX_TURNS \
    --k $K \