#!/bin/bash
# 更新線上版：覆寫 index.html 與 "Huginn Dashboard.data.json" 後執行本檔
set -e; cd "$(dirname "$0")"
mkdir -p public; cp index.html public/index.html; cp "Huginn Dashboard.data.json" "public/Huginn Dashboard.data.json"
npx -y wrangler deploy          # → https://huginn.brzder.workers.dev
git add -A && git commit -qm "update $(date +%F)" && git push -q   # → GitHub Pages 鏡像
