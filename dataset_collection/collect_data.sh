#!/usr/bin/env bash
set -euo pipefail

DATA_DIR="${DATA_DIR:-/isaac-sim/shared/data}"
OUTPUT_DIR="${OUTPUT_DIR:-/isaac-sim/shared/annotated_data}"
NUM_IMAGES="${NUM_IMAGES:-250}"
SEED_BASE="${SEED_BASE:-42}"

objects_nums=(1 3 5)
obstacles_nums=(0 1)

mkdir -p "$OUTPUT_DIR"

if [[ ! -f "$DATA_DIR/usd/room.usd" ]]; then
    echo "Skipping generation because $DATA_DIR/usd/room.usd does not exist"
    exit 1
fi

for objects_num in "${objects_nums[@]}"; do
    for obstacles_num in "${obstacles_nums[@]}"; do
    run_output="$OUTPUT_DIR/custom_room/objects_${objects_num}/obstacles_${obstacles_num}"
    mkdir -p "$run_output"

    SEED=$((SEED_BASE + objects_num * 100 + obstacles_num * 10))

    echo "Running objects_num=$objects_num obstacles_num=$obstacles_num"

    bash python.sh collect_data.py \
        --data_dir "$DATA_DIR" \
        --output_dir "$run_output" \
        --num_images "$NUM_IMAGES" \
        --objects_num "$objects_num" \
        --obstacles_num "$obstacles_num" \
        --seed "$SEED" \
        --headless
    done
done