#!/bin/bash
#SBATCH --job-name=pcie-debug
#SBATCH --array=0-19
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=00:10:00
#SBATCH --output=slurm_logs/%x_%A_%a.out
# Submit:  sbatch scripts/run_regression.sbatch
# Merge:   python -m pcie_debug.cli summarize results/
# Local mock (no Slurm):  SLURM_ARRAY_TASK_ID=0 bash scripts/run_regression.sbatch
set -euo pipefail
mkdir -p results slurm_logs
FILES=(logs/*.log)
FILE="${FILES[${SLURM_ARRAY_TASK_ID:-0}]}"
python -m pcie_debug.cli analyze "$FILE" --workers 1 --out "results/task_${SLURM_ARRAY_TASK_ID:-0}.json"
