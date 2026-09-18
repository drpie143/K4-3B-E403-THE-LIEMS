#!/usr/bin/env bash
# Chặn commit dữ liệu được cấp, key và file cục bộ. Chạy trước mỗi commit:
#   bash codebase/scripts/check_no_data.sh
# Hoặc cài làm hook:  ln -s ../../codebase/scripts/check_no_data.sh .git/hooks/pre-commit
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
fail=0
files=$(git diff --cached --name-only --diff-filter=ACM)
[ -z "$files" ] && files=$(git ls-files)

for f in $files; do
  case "$f" in
    *.local.*|*/data/*|*.db|*.jsonl|*.pdf|.env|*/.env|*/traces/*|*/.cache/*|*/.venv/*)
      echo "✗ Không được commit: $f"; fail=1 ;;
    *.csv)
      [ "$f" != "codebase/eval/golden_set.csv" ] && { echo "✗ CSV lạ (có thể là data pack): $f"; fail=1; } ;;
  esac
  [ -f "$f" ] || continue
  if grep -Eq '(sk-[A-Za-z0-9_-]{20,}|sk-ant-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{30,})' "$f"; then
    echo "✗ Có vẻ chứa API key: $f"; fail=1
  fi
  # Đoạn nguyên văn transcript thường bắt đầu bằng **[T0x-NNN]**
  if grep -Eq '^\*\*\[T0[0-9]-[0-9]{3}\]\*\*' "$f"; then
    echo "✗ Có vẻ chứa nguyên văn transcript: $f"; fail=1
  fi
done

if [ $fail -ne 0 ]; then
  echo "Dừng lại: gỡ các file trên khỏi commit (git restore --staged <file>)."
  exit 1
fi
echo "✓ Không thấy dữ liệu cấm trong các file sẽ commit."
