import uvicorn
import signal
import sys

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully on Windows."""
    print("\n🛑 Shutting down gracefully...")
    sys.exit(0)

# Register signal handlers for Windows compatibility
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    try:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=False,  # Disabled for better Ctrl+C handling on Windows
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped.")
        sys.exit(0)
