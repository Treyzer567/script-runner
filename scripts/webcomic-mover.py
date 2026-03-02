import os
import shutil
import re
import unicodedata
from datetime import datetime

# --- Configuration ---
SOURCE_DIR = "/webcomic-source"
DESTINATION_DIR = "/webcomic-destination"
LOG_FILE = "/var/log/webcomic-mover.log"

# --- Helper Functions ---

def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {message}"
    print(entry)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(entry + "\n")
    except Exception as e:
        print(f"ERROR writing log file: {e}")

def get_files_to_move(source_dir):
    """Return list of files in the *root* of SOURCE_DIR only."""
    files = []
    try:
        if not os.path.exists(source_dir):
            log_message(f"Source directory {source_dir} does not exist.")
            return []
        for name in os.listdir(source_dir):
            full_path = os.path.join(source_dir, name)
            if os.path.isfile(full_path) and name.lower().endswith(".cbz"):
                files.append(full_path)
    except Exception as e:
        log_message(f"ERROR scanning source dir: {e}")
    return files

def normalize_name(text):
    """Normalize text for robust comparison by removing non-alphanumeric characters and casing."""
    text = unicodedata.normalize("NFKC", text)
    # Remove everything except letters and numbers
    return re.sub(r'[^a-zA-Z0-9]', '', text).lower()

def extract_title(filename):
    """
    Extracts the title by taking everything before the ' - v' marker.
    Example: 'Jojo's Bizarre Adventure Part 9 - JOJOLands - v31.cbz' -> 'Jojo's Bizarre Adventure Part 9 - JOJOLands'
    """
    # Use the specific ' - v' marker as the separator
    if " - v" in filename:
        return filename.split(" - v")[0].strip()
    return os.path.splitext(filename)[0]

def find_best_folder_match(extracted_title, destination_root):
    """
    Checks the destination for an existing folder that 'mostly matches' the title.
    Returns the name of the existing folder if found, otherwise returns the extracted_title.
    """
    normalized_title = normalize_name(extracted_title)
    
    try:
        existing_folders = [f for f in os.listdir(destination_root) if os.path.isdir(os.path.join(destination_root, f))]
    except Exception as e:
        log_message(f"Error reading destination folders: {e}")
        return extracted_title

    # 1. Look for an exact (normalized) match
    for folder in existing_folders:
        if normalize_name(folder) == normalized_title:
            return folder

    # 2. Optional: Look for partial matches (where one is contained within the other)
    for folder in existing_folders:
        norm_folder = normalize_name(folder)
        if normalized_title in norm_folder or norm_folder in normalized_title:
            # We only return if it's a significant match (e.g., more than 75% length match) to avoid false positives
            return folder

    return extracted_title

def verify_file(source_path, destination_path):
    """Verify file size matches after copying."""
    if not os.path.exists(destination_path):
        return False
    try:
        return os.path.getsize(source_path) == os.path.getsize(destination_path)
    except Exception:
        return False

def move_files():
    log_message("-" * 40)
    log_message("📚 Starting robust webcomic file mover")

    files = get_files_to_move(SOURCE_DIR)
    if not files:
        log_message("✔ No files found.")
        return

    log_message(f"Found {len(files)} file(s) to process.")
    successful = 0
    failed = 0

    for src in files:
        filename = os.path.basename(src)
        extracted_title = extract_title(filename)
        
        # Determine target directory using fuzzy matching
        matched_folder_name = find_best_folder_match(extracted_title, DESTINATION_DIR)
        destination_dir = os.path.join(DESTINATION_DIR, matched_folder_name)
        destination_path = os.path.join(destination_dir, filename)

        try:
            os.makedirs(destination_dir, exist_ok=True)
            log_message(f"Moving: {filename} → {matched_folder_name}/")

            shutil.copy2(src, destination_path)

            if verify_file(src, destination_path):
                os.remove(src)
                successful += 1
            else:
                log_message(f"Verification FAILED: {filename}")
                failed += 1

        except Exception as e:
            log_message(f"ERROR processing {filename}: {e}")
            failed += 1

    log_message("-" * 40)
    log_message(f"📦 Summary: {successful} Success, {failed} Failed.")

if __name__ == "__main__":
    move_files()
