from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / 'uploads'
OUTPUT_DIR = BASE_DIR / 'outputs'

def ensure_directories():
    """Ensure all required directories exist and are writable"""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Create uploads directory
    try:
        UPLOAD_DIR.mkdir(exist_ok=True)
    except PermissionError:
        print(f"Error: No permission to create directory {UPLOAD_DIR}")
        raise
    except Exception as e:
        print(f"Error creating uploads directory: {e}")
        raise

    # Create Downloads directory if it doesn't exist
    try:
        downloads_dir = Path.home() / "Downloads"
        downloads_dir.mkdir(exist_ok=True)
    except PermissionError:
        print(f"Error: No permission to create directory {downloads_dir}")
        raise
    except Exception as e:
        print(f"Error creating downloads directory: {e}")
        raise

    # Create OTGU_Splitter directory
    try:
        OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
    except PermissionError:
        print(f"Error: No permission to create directory {OUTPUT_DIR}")
        raise
    except Exception as e:
        print(f"Error creating output directory: {e}")
        raise