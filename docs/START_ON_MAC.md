# Start on a Mac

This build was tested on Linux, not on a Mac. It uses Python's standard library and is designed to run on macOS with Python 3.10 or newer.

1. Download and unzip the review ZIP.
2. In Finder, open the `learning-path-lab` folder.
3. Double-click `START_MAC.command`. It starts the included full synthetic dataset and opens your browser. Keep the Terminal window open while using the app. Stop it with Control-C.

If macOS refuses to launch the file, use Terminal instead. Type `cd ` (with a space), drag the `learning-path-lab` folder into Terminal, press Return, then run:

```sh
python3 -m learninglab --db data/full.sqlite serve
```

Open http://127.0.0.1:8765/ in your browser. If the page opens before the server is ready, refresh it once. If `python3` is missing or older than 3.10, install a current Python from https://www.python.org/downloads/macos/ and reopen Terminal. No pip install is needed. Do not expose this local server to the internet.

What to inspect first: employee EMP-000001, current skill gaps, ordered course path, department budget, then the evidence/lifecycle section below. Read WALKTHROUGH.md before approving a public submission.
