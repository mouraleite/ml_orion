"""Entry point do Cron Job Render (09:00 e 14:00 em Brasília = 12:00 e 17:00 UTC)."""
from app.core.scheduler import daily_sienge_sync

if __name__ == "__main__":
    daily_sienge_sync()
