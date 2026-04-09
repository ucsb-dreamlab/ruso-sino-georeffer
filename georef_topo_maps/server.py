import sys
from pathlib import Path

# Add src to path just in case
sys.path.append(str(Path(__file__).parent / "src"))

from src.web_server import app

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Start the review web server")
    parser.add_argument(
        "--port", type=int, default=5000, help="Port to run the server on"
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host to run the server on")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    args = parser.parse_args()

    app.run(host=args.host, port=args.port, debug=args.debug)
