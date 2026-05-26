import asyncio
import os
from src.monitor import start_monitor
from src.job_crawler import crawler_loop
from src.orchestrator import process_job

ENABLE_CRAWLER = os.getenv("ENABLE_CRAWLER", "true").lower() == "true"

async def main():
    tasks = [start_monitor()]
    if ENABLE_CRAWLER:
        tasks.append(crawler_loop(process_job))
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
