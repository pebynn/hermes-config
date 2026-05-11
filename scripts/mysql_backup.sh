#!/bin/bash
# MySQL weekly backup — mysqldump stock database
BACKUP_DIR="$HOME/backups/mysql"
mkdir -p "$BACKUP_DIR"
DATE=$(date +%Y%m%d)
FILE="$BACKUP_DIR/stock_backup_$DATE.sql.gz"

mysqldump -u pebynn stock stock_kline 2>/dev/null | gzip > "$FILE"

# Keep only last 4 backups
ls -t "$BACKUP_DIR"/stock_backup_*.sql.gz 2>/dev/null | tail -n +5 | xargs rm -f 2>/dev/null

if [ -s "$FILE" ]; then
    echo "✅ MySQL backup: $FILE ($(du -h "$FILE" | cut -f1))"
else
    echo "❌ MySQL backup failed"
    rm -f "$FILE"
fi
