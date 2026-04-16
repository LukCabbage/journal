#!/bin/bash
# 刪除日誌文章 — 用法: ./scripts/delete.sh a001 a003 a006
# 會同時刪除 articles.json 中的條目和對應的 HTML 檔案，然後 commit + push

cd "$(dirname "$0")/.."

if [ $# -eq 0 ]; then
  echo "📋 用法: ./scripts/delete.sh <id1> [id2] [id3] ..."
  echo "   範例: ./scripts/delete.sh a003 a006"
  echo ""
  echo "目前所有文章："
  python3 -c "
import json
with open('articles.json') as f:
    arts = json.load(f)
for a in arts:
    print(f\"  {a['id']:6s}  {a['date']}  [{a['category']}]  {a['title'][:50]}\")
print(f\"\n  共 {len(arts)} 篇\")
"
  exit 0
fi

IDS="$@"

python3 -c "
import json, sys, os

ids_to_delete = set('$IDS'.split())

with open('articles.json') as f:
    arts = json.load(f)

deleted = [a for a in arts if a.get('id') in ids_to_delete]
remaining = [a for a in arts if a.get('id') not in ids_to_delete]

if not deleted:
    print('❌ 找不到指定的 ID，沒有任何變更')
    sys.exit(1)

# Remove HTML files
for a in deleted:
    fpath = a['filename']
    if os.path.exists(fpath):
        os.remove(fpath)
        print(f'  🗑  刪除檔案: {fpath}')
    else:
        print(f'  ⚠️  檔案不存在（已跳過）: {fpath}')

# Update articles.json
with open('articles.json', 'w') as f:
    json.dump(remaining, f, ensure_ascii=False, indent=2)
    f.write('\n')

print(f'\n✅ 已從 articles.json 移除 {len(deleted)} 筆：')
for a in deleted:
    print(f'   {a[\"id\"]}  {a[\"title\"]}')
print(f'📝 剩餘 {len(remaining)} 篇')
"

if [ $? -eq 0 ]; then
  git add -A
  git commit -m "chore: delete articles $IDS"
  git push origin main
  echo ""
  echo "✅ 已推上 GitHub！GitHub Pages 將在幾分鐘內更新。"
fi
