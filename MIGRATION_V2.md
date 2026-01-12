# Migration to v2.0 - API-Driven Configuration

## What Changed?

### Before (v1.x)
- ❌ Built-in APScheduler
- ❌ Configuration in `.env` file
- ❌ Single channel processing
- ❌ Many environment variables

### After (v2.0)
- ✅ External scheduler (cron, Airflow, etc.)
- ✅ Configuration in API request body
- ✅ Multi-channel processing per request
- ✅ Minimal environment variables (only secrets)

## Why This Change?

1. **Flexibility**: Use any scheduler (cron, Airflow, Lambda, Kubernetes CronJob, etc.)
2. **Simplicity**: No complex environment configuration
3. **Testability**: Easy to test with different parameters
4. **Scalability**: Run multiple instances without coordination
5. **Observability**: External schedulers provide better monitoring

## Migration Steps

### Step 1: Update `.env` File

**Old `.env`:**
```bash
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_NAME=general
SLACK_MINUTES_AGO=30
SLACK_MESSAGE_LIMIT=100
SCHEDULER_ENABLED=true
SCHEDULER_INTERVAL_MINUTES=30
POST_TODOS_TO_SLACK=true
OPENAI_API_KEY=sk-...
LLM_PROVIDER=openai
LOG_LEVEL=INFO
```

**New `.env`:**
```bash
# Only secrets and tokens!
SLACK_BOT_TOKEN=xoxb-...
OPENAI_API_KEY=sk-...
LLM_PROVIDER=openai
LOG_LEVEL=INFO
```

### Step 2: Set Up External Scheduler

Choose your scheduler and configure it to call the API:

#### Option A: Cron (Simplest)

Add to crontab:
```bash
*/30 * * * * curl -X POST http://localhost:8000/extract-todos \
  -H "Content-Type: application/json" \
  -d '{"minutes_ago": 30, "message_limit": 100, "post_to_slack": true}'
```

#### Option B: Python Script with schedule

```python
import requests
import schedule
import time

def extract_todos():
    requests.post(
        "http://localhost:8000/extract-todos",
        json={
            "minutes_ago": 30,
            "message_limit": 100,
            "post_to_slack": True
        }
    )

schedule.every(30).minutes.do(extract_todos)

while True:
    schedule.run_pending()
    time.sleep(60)
```

Run it: `python scheduler.py &`

#### Option C: systemd Timer (Linux)

Create `/etc/systemd/system/slack-todo-bot.service`:
```ini
[Unit]
Description=Slack Todo Bot Extraction

[Service]
Type=oneshot
ExecStart=/usr/bin/curl -X POST http://localhost:8000/extract-todos \
  -H "Content-Type: application/json" \
  -d '{"minutes_ago": 30, "message_limit": 100, "post_to_slack": true}'
```

Create `/etc/systemd/system/slack-todo-bot.timer`:
```ini
[Unit]
Description=Run Slack Todo Bot every 30 minutes

[Timer]
OnCalendar=*:0/30
Persistent=true

[Install]
WantedBy=timers.target
```

Enable: `systemctl enable --now slack-todo-bot.timer`

### Step 3: Update API Calls

**Old endpoint (removed):**
```bash
GET /extract-todos  # Used env vars
```

**New endpoint:**
```bash
POST /extract-todos  # Config in body
{
  "minutes_ago": 30,
  "message_limit": 100,
  "post_to_slack": true,
  "channel_ids": null
}
```

### Step 4: Restart API

```bash
# Stop old version
# Start new version
python run_api.py
```

## Configuration Mapping

| Old (v1.x Env Var) | New (v2.0 Request Body) | Notes |
|-------------------|-------------------------|-------|
| `SLACK_CHANNEL_NAME` | `channel_ids` | Now supports multiple; null = all |
| `SLACK_MINUTES_AGO` | `minutes_ago` | Per request, not global |
| `SLACK_MESSAGE_LIMIT` | `message_limit` | Per request, not global |
| `SCHEDULER_INTERVAL_MINUTES` | External scheduler | Use cron, etc. |
| `SCHEDULER_ENABLED` | External scheduler | Start/stop scheduler |
| `POST_TODOS_TO_SLACK` | `post_to_slack` | Per request |
| `SLACK_BOT_TOKEN` | `SLACK_BOT_TOKEN` (env) | Unchanged ✅ |
| `OPENAI_API_KEY` | `OPENAI_API_KEY` (env) | Unchanged ✅ |
| `LLM_PROVIDER` | `LLM_PROVIDER` (env) | Unchanged ✅ |

## Benefits of v2.0

### 1. Dynamic Configuration

**Before**: Change config → restart API
```bash
# Edit .env
nano .env
# Restart
systemctl restart slack-todo-api
```

**After**: Change config → just change request
```bash
# Different configs for different times
# Morning: Last 12 hours
curl ... -d '{"minutes_ago": 720}'

# Afternoon: Last 4 hours  
curl ... -d '{"minutes_ago": 240}'
```

### 2. Multiple Schedules

Run different extractions at different intervals:

```bash
# Quick check every 5 minutes
*/5 * * * * curl ... -d '{"minutes_ago": 5, "message_limit": 50}'

# Deep scan every 4 hours
0 */4 * * * curl ... -d '{"minutes_ago": 240, "message_limit": 500}'

# Daily summary at 9 AM
0 9 * * * curl ... -d '{"minutes_ago": 1440, "message_limit": 1000}'
```

### 3. Channel-Specific Processing

```bash
# Support channel - every 5 min
*/5 * * * * curl ... -d '{"channel_ids": ["C_SUPPORT"], "minutes_ago": 5}'

# Project channels - every 30 min
*/30 * * * * curl ... -d '{"channel_ids": ["C_PROJ_A", "C_PROJ_B"], "minutes_ago": 30}'

# All channels - every 2 hours
0 */2 * * * curl ... -d '{"channel_ids": null, "minutes_ago": 120}'
```

### 4. Better Monitoring

With external schedulers, you get:
- Built-in monitoring (Airflow UI, cron logs, etc.)
- Retry logic
- Alerting on failures
- Execution history
- Better observability

### 5. Easier Testing

```bash
# Test without affecting production schedule
curl -X POST http://localhost:8000/extract-todos \
  -d '{"minutes_ago": 5, "post_to_slack": false}'
```

## Troubleshooting

### Issue: API not responding

**Solution**: Check if API is running
```bash
curl http://localhost:8000/health
```

### Issue: No todos extracted

**Possible causes**:
1. Time window too short → increase `minutes_ago`
2. No messages in channels → check Slack
3. Bot not in channels → invite bot

### Issue: Scheduler not running

**Cron**:
```bash
# Check cron is running
systemctl status cron

# Check cron logs
grep CRON /var/log/syslog
```

**Python scheduler**:
```bash
# Check process
ps aux | grep scheduler.py

# Check logs
tail -f scheduler.log
```

### Issue: Todos not posting to Slack

**Solution**: Set `post_to_slack: true` in request body
```bash
curl ... -d '{"post_to_slack": true}'
```

## Rollback (if needed)

If you need to rollback to v1.x:

1. Checkout v1.x code
2. Restore old `.env` file
3. Restart API (built-in scheduler will start automatically)

## FAQ

**Q: Can I still use environment variables for config?**
A: No, operational config is now request-body only. Only secrets in env.

**Q: Why remove the built-in scheduler?**
A: External schedulers are more robust, flexible, and provide better monitoring.

**Q: What if I want to process just one channel?**
A: Use `"channel_ids": ["C1234567890"]` in the request.

**Q: Can I run multiple API instances?**
A: Yes! They're now stateless. Use a load balancer if needed.

**Q: How do I change the interval?**
A: Update your external scheduler (cron, Airflow, etc.)

**Q: Is the old GET endpoint still available?**
A: No, it's been removed. Use POST /extract-todos with request body.

## Next Steps

1. ✅ Update `.env` to only include secrets
2. ✅ Set up external scheduler
3. ✅ Test with `curl` or `test_api.py`
4. ✅ Monitor logs
5. ✅ Enjoy better flexibility!

## Support

- See `README.md` for full documentation
- See `API_EXAMPLES.md` for curl examples
- See `ARCHITECTURE.md` for technical details
