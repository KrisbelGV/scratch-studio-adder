import os
import sys
import time
import re
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
MIN_INTERVAL = 0.2

def rate_limit_protected_request(last_request_time):
    elapsed = time.time() - last_request_time
    if elapsed < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - elapsed)
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
with open(STUDIOS_FILE, "r") as f:
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
estimated_time = total * MIN_INTERVAL * 2
start_time = time.time()
aborted = False

print(f"Connecting to Scratch as {USERNAME}...")
try:
    session = scratch3.login_by_id(SESSION_ID, username=USERNAME)
    project = session.connect_project(PROJECT_ID)
    print(f"Connected successfully. Project: {project.title}")
except (Unauthenticated, LoginFailure, XTokenError) as e:
    print(f"FATAL: Authentication failed: {e}")
    sys.exit(1)

print(f"\nAdding project {PROJECT_ID} to {total} studios...")
print(f"Minimum estimated time: {estimated_time:.1f}s ({estimated_time/60:.1f} min)\n")

success_list = []
fail_list = []
pending_ids = []
last_request_time = time.time()

for i, studio_id in enumerate(studio_ids, 1):
    bar_length = 30
    filled = int(bar_length * i / total)
    bar = "=" * filled + ">" + " " * (bar_length - filled - 1)
    elapsed = time.time() - start_time
    progress = f"\r[{bar}] {i}/{total} ({i * 100 // total}%) | Elapsed: {elapsed:.1f}s | Failed: {len(fail_list)}"
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
print(f"Minimum estimated: {estimated_time:.1f}s | Actual: {actual_time:.1f}s")

with open(REPORT_FILE, "w") as f:
    f.write("=== Studio Addition Report ===\n")
    f.write(f"Project ID: {PROJECT_ID}\n")
    f.write(f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
    f.write(f"Status: {'ABORTED' if aborted else 'COMPLETED'}\n")
    f.write(f"Minimum estimated time: {estimated_time:.1f}s | Actual time: {actual_time:.1f}s\n\n")
    
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

print(f"Report saved to {REPORT_FILE}")