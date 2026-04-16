#!/bin/bash
cd "$(dirname "$0")/.."
git add -A
git commit -m "chore: update journal"
git push origin main
echo ""
echo "✅ 已推上 GitHub！"
