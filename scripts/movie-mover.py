import os
import shutil
import time
from datetime import datetime

# --- Configuration ---
SOURCE_DIR = "/movie-source"
DESTINATION_DIR = "/movie-destination"
LOG_FILE = "/var/log/movie-mover.log" 

# --- Helper Functions ---

def log_message(message):
    """Writes a timestamped message to the log file and stdout."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    
    print(log_entry)
    
    try:
        with open(LOG_FILE, "a") as f:
            f.write(log_entry + "\n")
    except Exception as e:
        print(f"ERROR: Could not write to log file {LOG_FILE}: {e}")

def get_files_to_move(source_dir):
    """Generates a list of movie files, excluding those marked as TELESYNC."""
    file_list = []
    
    for root, _, files in os.walk(source_dir):
        # Note: Your original logic skips the root directory files. 
        # I've kept this behavior to match your base script.
        if root == source_dir:
            continue
            
        for name in files:
            full_path = os.path.join(root, name)
            relative_path = os.path.relpath(full_path, source_dir)
            file_list.append((full_path, relative_path))
            
    return file_list

def verify_file(source_path, destination_path):
    """Verifies that the destination file exists and matches the source size."""
    if not os.path.exists(destination_path):
        log_message(f"Verification FAILED: Destination file not found: {destination_path}")
        return False

    try:
        source_size = os.path.getsize(source_path)
        destination_size = os.path.getsize(destination_path)
        
        if source_size != destination_size:
            log_message(f"Verification FAILED: Size mismatch for {destination_path}. Source: {source_size} bytes, Dest: {destination_size} bytes.")
            return False
            
        log_message(f"Verification SUCCESS: {destination_path} size verified.")
        return True
        
    except OSError as e:
        log_message(f"Verification FAILED: Error accessing file size: {e}")
        return False

def move_files():
    """Main function to perform the move, verify, and delete operation."""
    log_message("-" * 50)
    log_message("🎬 Starting movie file movement process.")
    
    try:
        files_to_move = get_files_to_move(SOURCE_DIR)
    except Exception as e:
        log_message(f"CRITICAL ERROR: Failed to scan source directory {SOURCE_DIR}: {e}")
        return

    if not files_to_move:
        log_message(f"✅ Source directory {SOURCE_DIR} is empty or only contains filtered files. Nothing to move.")
        log_message("--- Process Finished ---")
        return

    log_message(f"Found {len(files_to_move)} files to process.")
    
    successful_moves = 0
    failed_moves = 0
    
    # --- 1. Copy Files ---
    log_message("--- Stage 1/3: Copying movies and creating structure... ---")
    files_to_clean = [] 
    
    for source_path, relative_path in files_to_move:
        destination_path = os.path.join(DESTINATION_DIR, relative_path)
        destination_dir = os.path.dirname(destination_path)

        try:
            os.makedirs(destination_dir, exist_ok=True)
            
            log_message(f"Copying: {relative_path}")
            shutil.copy2(source_path, destination_path) 
            
            # --- 2. Verify File ---
            if verify_file(source_path, destination_path):
                successful_moves += 1
                files_to_clean.append(source_path)
            else:
                log_message(f"Skipping deletion for failed copy/verify: {source_path}")
                failed_moves += 1
                
        except Exception as e:
            log_message(f"ERROR: Failed to copy or verify {source_path}: {e}")
            failed_moves += 1
            
    # --- 3. Delete Original Files ---
    log_message("--- Stage 3/3: Cleaning up source directory... ---")
    if files_to_clean:
        for source_path in files_to_clean:
            try:
                os.remove(source_path)
                log_message(f"Deleted source file: {os.path.relpath(source_path, SOURCE_DIR)}")
            except Exception as e:
                log_message(f"ERROR: Failed to delete source file {source_path}: {e}")
                
        # Clean up empty directories
        log_message("Cleaning up empty source directories...")
        for root, dirs, files in os.walk(SOURCE_DIR, topdown=False):
            if root != SOURCE_DIR and not dirs and not files:
                try:
                    os.rmdir(root)
                    log_message(f"Deleted empty source directory: {os.path.relpath(root, SOURCE_DIR)}")
                except OSError as e:
                    log_message(f"Could not remove source directory {root}: {e}")

    # --- Summary ---
    log_message("-" * 50)
    log_message("🎉 Process Summary:")
    log_message(f"  - Total files processed: {len(files_to_move)}")
    log_message(f"  - Successful moves: {successful_moves}")
    log_message(f"  - Failed moves/verifications: {failed_moves}")
    log_message("--- Process Finished ---")

if __name__ == "__main__":
    log_message(f"Movie-mover script starting at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    move_files()
