# Scratch Studio Adder

A Python script that adds a Scratch project to multiple studios from a list. Built with [scratchattach](https://github.com/TimMcCool/scratchattach).

> **Utility tool** — Created to automate adding projects to studios while respecting Scratch's rate limits.

## Features

- Adds one project to dozens of studios automatically
- Smart delay system respects Scratch's rate limits without unnecessary waits
- Detects and skips duplicate studios
- Stops immediately on rate limits or authentication errors
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

For each studio, the script connects and adds your project. A minimum 200ms spacing is maintained between requests (half of Scratch's 10/s limit), and if a request takes longer no extra wait is added. Results are saved to `report.txt`.

## License

This project is licensed under the **MIT License** — feel free to use, modify, and share it.
See [LICENSE](LICENSE) for details.

> **Note:** `scratchattach` is also MIT licensed. This project is not affiliated with Scratch or the scratchattach team.
