#!/usr/bin/env bash
set -euo pipefail

SPEED=1.0   # <1 变慢 >1 变快
OUT="out.mp4"

print_help() {
  cat <<EOF
用法: $0 [选项] -i 输入文件

选项:
  -i, --input FILE     输入视频
  -o, --out FILE       输出文件 (默认: out.mp4)
  -s, --speed X        倍速因子 (默认: 1.0)
  -h, --help           显示帮助
EOF
}

INPUT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -i|--input) INPUT="$2"; shift 2 ;;
    -o|--out)   OUT="$2"; shift 2 ;;
    -s|--speed) SPEED="$2"; shift 2 ;;
    -h|--help)  print_help; exit 0 ;;
    *) echo "未知参数: $1"; print_help; exit 1 ;;
  esac
done

[[ -z "$INPUT" ]] && { echo "缺少输入文件，请用 -i 指定"; exit 1; }

build_atempo_chain() {
  local s="$1"
  awk -v s="$s" '
    function abs(x){return x<0?-x:x}
    BEGIN {
      if (s <= 0) { print "ERR"; exit 0 }
      parts=""
      while (s < 0.5) { parts = parts ((parts!="")?",":"") "atempo=0.5"; s/=0.5 }
      while (s > 2.0) { parts = parts ((parts!="")?",":"") "atempo=2.0"; s/=2.0 }
      if (abs(s-1.0) > 1e-6) {
        sf = sprintf("%.3f", s)+0
        parts = parts ((parts!="")?",":"") "atempo=" sf
      }
      print parts
    }'
}

ATEMPO=$(build_atempo_chain "$SPEED")
[[ "$ATEMPO" == "ERR" ]] && { echo "无效 speed=$SPEED"; exit 1; }

# 视频倍速：setpts=PTS/SPEED
VF="setpts=PTS/${SPEED}"

echo ">>> 输入: $INPUT"
echo ">>> 输出: $OUT"
echo ">>> 倍速: $SPEED"

if [[ -n "$ATEMPO" ]]; then
  ffmpeg -hide_banner -y -i "$INPUT" \
    -vf "$VF" -af "$ATEMPO" \
    -c:v libx264 -preset fast -crf 18 \
    -c:a aac -b:a 160k \
    "$OUT"
else
  ffmpeg -hide_banner -y -i "$INPUT" \
    -vf "$VF" \
    -c:v libx264 -preset fast -crf 18 \
    -c:a aac -b:a 160k \
    "$OUT"
fi

echo "✅ 完成: $OUT"
