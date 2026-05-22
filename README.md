# Scratch Studio Adder

A Python script that adds a Scratch project to multiple studios from a list. Built with [scratchattach](https://github.com/TimMcCool/scratchattach).

> **Utility tool** — Created to automate adding projects to studios while respecting Scratch's rate limits.

## Features

- Adds one project to dozens of studios automatically
- Randomized delays prevent rate limiting
- Detects and skips duplicate studios
- Graceful shutdown on Ctrl+C — saves progress before exiting
- Automatically resumes from where it left off using the previous report
- Stops immediately on authentication errors
- Generates a detailed report of successes and failures
- Progress bar with real-time elapsed time

## Requirements

- Python 3.9+
- A Scratch account
- [scratchattach](https://github.com/TimMcCool/scratchattach)
- [python-dotenv](https://pypi.org/project/python-dotenv/)

## Installation

1. Clone the repository:

       git clone https://github.com/KrisbelGV/scratch-studio-adder.git
       cd scratch-studio-adder

2. Install dependencies:

       pip install -r requirements.txt

3. Set up environment variables:

       cp .env.example .env

   Edit `.env` with your data:
   - `SCRATCH_SESSION_ID` — See [Getting your session ID](https://github.com/TimMcCool/scratchattach/wiki/Getting-your-session-id)
   - `SCRATCH_USERNAME` — Your Scratch username (case sensitive)
   - `SCRATCH_PROJECT_ID` — The project ID to add to studios
   - `STUDIOS_FILE` — Path to the studio list file (default: `open_studios.txt`)

4. Prepare your studio list in `open_studios.txt` (one URL per line):

       https://scratch.mit.edu/studios/11111111/
       https://scratch.mit.edu/studios/22222222/

   You can use the included `open_studios.txt` as a starting point. For the most up-to-date list, download it from the studios featured in [this project](https://scratch.mit.edu/projects/1318691000/).

5. Run the script:

       python main.py

## How it works

For each studio, the script connects and adds your project with randomized 1-4 second delays between requests. Every 10 studios, a 10-second batch pause gives the API extra breathing room. If interrupted, press Ctrl+C to save progress and resume later — the script reads `report.txt` and continues from where it stopped. Results are saved to `report.txt`.

## ⚠️ Known issue: Undocumented rate limit around 300 requests

Testing has revealed a consistent pattern: **429 Rate Limit errors appear around studio #301**, regardless of request spacing. This strongly suggests Scratch applies an **undocumented limit of approximately 300 write operations per session** to the studio add endpoint — far stricter than the official 10 requests/second REST API cap.

> **This limit is not documented anywhere by Scratch.** It was discovered through repeated testing with this tool.

**Workarounds:**
- The script now auto-resumes — when rate limited, wait 15-30 minutes and run again
- Process studios in smaller sessions (200-250 at a time)
- If investigating further, check for `X-RateLimit-*` headers in responses

**Contributions and insights on this issue are highly welcome.**

## Known issue: Rate limiting on large studio lists

When adding a project to a large number of studios (100+), you may encounter `429 Rate Limit` errors even though the tool stays within 5 requests/second. This suggests Scratch applies additional limits — possibly per-minute or per-endpoint — beyond the documented 10 req/s REST API cap.

A more robust solution is under development. In the meantime:

- Try processing studios in smaller batches (e.g., 40–50 at a time)
- Wait a few minutes between batches
- If you hit a rate limit, stop and wait before resuming

Contributions and insights on this issue are welcome.

## License

This project is licensed under the **MIT License** — feel free to use, modify, and share it.
See [LICENSE](LICENSE) for details.

> **Note:** `scratchattach` is also MIT licensed. This project is not affiliated with Scratch or the scratchattach team.