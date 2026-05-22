import os
import sys
import time
import re
import random
import signal
import warnings
from datetime import datetime, timezone
import scratchattach as scratch3
from dotenv import load_dotenv
from scratchattach.utils.exceptions import (
    FetchError, RateLimitedError, Response429,
    Unauthenticated, Unauthorized, LoginFailure, XTokenError
)

warnings.filterwarnings("ignore", category=scratch3.LoginDataWarning)

load_dotenv()

SESSION_ID = os.environ.get("SCRATCH_SESSION_ID")
USERNAME = os.environ.get("SCRATCH_USERNAME")
PROJECT_ID = int(os.environ.get("SCRATCH_PROJECT_ID", 0))
STUDIOS_FILE = os.environ.get("STUDIOS_FILE", "studios_to_add.txt")
REPORT_FILE = "report.txt"
MIN_INTERVAL = 1.0
BATCH_SIZE = 10
BATCH_DELAY = 10.0

aborted = False
success_list = []
fail_list = []
pending_ids = []
start_time = None

def save_report():
    actual_time = time.time() - start_time if start_time else 0
    success_count = len(success_list)
    fail_count = len(fail_list)
    pending_count = len(pending_ids)
    
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("=== Studio Addition Report ===\n")
        f.write(f"Project ID: {PROJECT_ID}\n")
        f.write(f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        f.write(f"Status: {'ABORTED' if aborted else 'COMPLETED'}\n")
        f.write(f"Estimated time: {estimated_time:.1f}s | Actual time: {actual_time:.1f}s\n\n")
        
        f.write(f"--- Successfully added to ({success_count}/{total}) ---\n")
        if success_list:
            for sid in success_list:
                f.write(f"{studio_urls_by_id[sid]}\n")
        else:
            f.write("None\n")
        
        f.write(f"\n--- Failed to add to ({fail_count}/{total}) ---\n")
        if fail_list:
            for sid, reason in fail_list:
                f.write(f"{studio_urls_by_id[sid]} - {reason}\n")
        else:
            f.write("None\n")
        
        if pending_ids:
            f.write(f"\n--- Pending (not processed, {pending_count}/{total}) ---\n")
            for sid in pending_ids:
                f.write(f"{studio_urls_by_id[sid]}\n")
        
        f.write(f"\n=== End of Report ===\n")
    
    print(f"\nReport saved to {REPORT_FILE}")

def signal_handler(sig, frame):
    global aborted, pending_ids
    print(f"\n\nInterrupted by user. Saving progress...")
    aborted = True
    pending_ids = studio_ids[studio_ids.index(studio_id):] if 'studio_id' in dir() else []
    save_report()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def load_previous_progress():
    if not os.path.exists(REPORT_FILE):
        return set()
    
    processed = set()
    found_project = False
    in_section = False
    
    with open(REPORT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            
            if line.startswith("Project ID:"):
                try:
                    report_project_id = int(line.split(":")[1].strip())
                    if report_project_id == PROJECT_ID:
                        found_project = True
                except:
                    pass
                continue
            
            if not found_project:
                continue
            
            if line.startswith("--- Successfully added to") or line.startswith("--- Failed to add to"):
                in_section = True
                continue
            
            if line.startswith("---") or line.startswith("==="):
                in_section = False
                continue
            
            if in_section and "studios/" in line:
                match = re.search(r"studios/(\d+)", line)
                if match:
                    processed.add(int(match.group(1)))
    
    return processed

def rate_limit_protected_request(last_request_time):
    base_delay = 1 + 3 * (random.random() ** 2)
    elapsed = time.time() - last_request_time
    if elapsed < base_delay:
        time.sleep(base_delay - elapsed)
    return time.time()

if not all([SESSION_ID, USERNAME, PROJECT_ID]):
    raise ValueError(
        "Environment variables are missing. Make sure the .env file exists "
        "and contains SCRATCH_SESSION_ID, SCRATCH_USERNAME and SCRATCH_PROJECT_ID"
    )

if not os.path.exists(STUDIOS_FILE):
    raise FileNotFoundError(f"Studios file '{STUDIOS_FILE}' not found.")

studio_urls_by_id = {}
duplicates = set()
with open(STUDIOS_FILE, "r", encoding="utf-8") as f:
    for line_num, line in enumerate(f, 1):
        line = line.strip()
        if line:
            match = re.search(r"studios/(\d+)", line)
            if match:
                sid = int(match.group(1))
                if sid in studio_urls_by_id:
                    duplicates.add(sid)
                studio_urls_by_id[sid] = line
            else:
                print(f"Skipping invalid line {line_num}: {line}")

if duplicates:
    print(f"Warning: Duplicate studio IDs found and will be processed once: {', '.join(str(d) for d in duplicates)}")

if not studio_urls_by_id:
    print("No valid studio URLs found in the file.")
    sys.exit(0)

studio_ids = list(studio_urls_by_id.keys())
total = len(studio_ids)

previously_processed = load_previous_progress()
if previously_processed:
    remaining_ids = [sid for sid in studio_ids if sid not in previously_processed]
    skipped = len(studio_ids) - len(remaining_ids)
    print(f"Found previous report. {skipped} studios already processed. Resuming...")
    studio_ids = remaining_ids
    success_list = list(previously_processed)
    total = len(studio_ids)

estimated_time = len(studio_ids) * 2.5
start_time = time.time()

print(f"Connecting to Scratch as {USERNAME}...")
try:
    session = scratch3.login_by_id(SESSION_ID, username=USERNAME)
    project = session.connect_project(PROJECT_ID)
    print(f"Connected successfully. Project: {project.title}")
except (Unauthenticated, LoginFailure, XTokenError) as e:
    print(f"FATAL: Authentication failed: {e}")
    sys.exit(1)

print(f"\nAdding project {PROJECT_ID} to {len(studio_ids)} studios...")
print(f"Estimated time: {estimated_time:.1f}s ({estimated_time/60:.1f} min)")
print(f"Batch size: {BATCH_SIZE}, Batch delay: {BATCH_DELAY}s\n")

last_request_time = time.time()

for i, studio_id in enumerate(studio_ids, 1):
    bar_length = 30
    filled = int(bar_length * i / len(studio_ids))
    bar = "=" * filled + ">" + " " * (bar_length - filled - 1)
    elapsed = time.time() - start_time
    progress = f"\r[{bar}] {i}/{len(studio_ids)} ({i * 100 // len(studio_ids)}%) | Elapsed: {elapsed:.1f}s | Failed: {len(fail_list)}"
    print(progress, end="", flush=True)

    try:
        last_request_time = rate_limit_protected_request(last_request_time)
        studio = session.connect_studio(studio_id)
        
        last_request_time = rate_limit_protected_request(last_request_time)
        studio.add_project(PROJECT_ID)
        
        success_list.append(studio_id)
    except (RateLimitedError, Response429) as e:
        fail_list.append((studio_id, f"Rate limited: {e}"))
        pending_ids = studio_ids[i:]
        aborted = True
        print(f"\nFATAL: Rate limited by Scratch. Stop adding and try again later.")
        break
    except (Unauthenticated, LoginFailure, XTokenError) as e:
        fail_list.append((studio_id, f"Auth error: {e}"))
        pending_ids = studio_ids[i:]
        aborted = True
        print(f"\nFATAL: Session expired or invalid: {e}")
        break
    except Unauthorized as e:
        fail_list.append((studio_id, f"Unauthorized: {e}"))
    except FetchError as e:
        fail_list.append((studio_id, f"API error: {e}"))
    except Exception as e:
        fail_list.append((studio_id, f"Unexpected error: {e}"))

    if len(success_list) % BATCH_SIZE == 0 and i < len(studio_ids):
        print(f"\r{' ' * 80}", end="", flush=True)
        print(f"\r[Batch] Processed {len(success_list)} studios. Waiting {BATCH_DELAY}s...", end="", flush=True)
        time.sleep(BATCH_DELAY)
        last_request_time = time.time()
        print(f"\r{' ' * 80}", end="", flush=True)

print()
actual_time = time.time() - start_time
success_count = len(success_list)
fail_count = len(fail_list)
pending_count = len(pending_ids)

print(f"Done! {success_count} added, {fail_count} failed", end="")
if pending_count > 0:
    print(f", {pending_count} pending (aborted)")
else:
    print(f", {total} total")
print(f"Estimated: {estimated_time:.1f}s | Actual: {actual_time:.1f}s")

save_report()