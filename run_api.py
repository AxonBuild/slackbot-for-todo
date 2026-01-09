"""Script to run the FastAPI server."""

import uvicorn
from utils.logger import setup_logging

if __name__ == "__main__":
    # Set up logging
    setup_logging()
    
    # Use import string for reload to work properly
    uvicorn.run(
        "api.app:app",  # Import string format: "module:variable"
        host="0.0.0.0",
        port=8000,
        reload=True  # Auto-reload on code changes
    )

