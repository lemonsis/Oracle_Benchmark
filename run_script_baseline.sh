#!/bin/bash

EVA_MODEL_FAMILY="gpt"
EVA_MODEL_NAME="gpt-4.1"
BASELINE_TEST="True"
MAX_TURNS=12
K=0

python main.py \
    --eva_model_family $EVA_MODEL_FAMILY \
    --eva_model_name $EVA_MODEL_NAME \
    --baseline_test $BASELINE_TEST \
    --max_turns $MAX_TURNS \
    --k $K \