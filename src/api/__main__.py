import os
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src.api.server:app",
        host="127.0.0.1",  # local only: the API has no auth
        port=int(os.getenv("API_PORT", "8765")),
    )
