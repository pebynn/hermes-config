# Data Freshness Check Pattern for Cron Scripts (2026-05-13)

When a cron job depends on data that is loaded by a separate upstream process, add a freshness check before the main logic.

## Pattern

```bash
#!/bin/bash
# Check that today's data is loaded before generating signals

COUNT=$(python3 -c "
from data_common import _get_db_engine
from datetime import datetime
e = _get_db_engine()
today = datetime.now().strftime('%Y-%m-%d')
r = e.execute('SELECT COUNT(*) FROM kline WHERE trade_date = %s', (today,)).fetchone()
print(r[0] if r else 0)
" 2>/dev/null)

if [ "$COUNT" -lt 3000 ]; then
    for i in $(seq 1 5); do
        echo "Waiting for data... attempt $i: $COUNT stocks"
        sleep 120
        # Re-check
        COUNT=$(python3 -c "..." 2>/dev/null)
        if [ "$COUNT" -gt 3000 ]; then
            echo "Data ready: $COUNT stocks"
            break
        fi
    done
fi

if [ "$COUNT" -le 3000 ]; then
    echo "Data insufficient, aborting"
    exit 1
fi
```

## Timing Rules

- Data pull cron: 15:30
- Signal generation cron: 16:10 (40-minute buffer)
- Exchanges close at 15:00, data takes 10-30 minutes to propagate through API → DB pipeline
- Never schedule dependent cron at the same minute as its upstream

## Threshold Selection

- A-share market: ~5300 listed stocks, expect 4900+ on normal days
- Set threshold at 3000 to allow for suspensions, STs, etc.
- If <3000 rows for today's date, the upstream data pull likely failed
