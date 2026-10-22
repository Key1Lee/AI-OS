#!/usr/bin/env bash
set -uo pipefail
lab_root="$(cd "$(dirname "$0")/.." && pwd)"
label="$1"
shift
run_dir="$lab_root/evidence/$(date -u +%Y%m%dT%H%M%SZ)-$label-$$"
mkdir -p "$run_dir"
printf '%q ' "$@" > "$run_dir/command.txt"
printf '\n' >> "$run_dir/command.txt"
date -u +%Y-%m-%dT%H:%M:%SZ > "$run_dir/started.txt"
"$@" 2>&1 | tee "$run_dir/output.log"
run_status=${PIPESTATUS[0]}
printf '%s\n' "$run_status" > "$run_dir/exit-code.txt"
date -u +%Y-%m-%dT%H:%M:%SZ > "$run_dir/finished.txt"
case "$label" in
  unit|smoke|challenge)
    for report_kind in surefire-reports failsafe-reports; do
      report_source="$lab_root/source/debezium/debezium-connector-mysql/target/$report_kind"
      if [ -d "$report_source" ]; then
        mkdir -p "$run_dir/reports/$report_kind"
        while IFS= read -r -d '' report_file; do
          cp "$report_file" "$run_dir/reports/$report_kind/"
        done < <(find "$report_source" -maxdepth 1 -type f -newer "$run_dir/started.txt" -print0)
      fi
    done
    docker compose -f "$lab_root/compose.yaml" logs --no-color mysql > "$run_dir/mysql.log" 2>&1 || true
    ;;
esac
printf '\nEvidence: %s (exit %s)\n' "$run_dir" "$run_status"
exit "$run_status"
