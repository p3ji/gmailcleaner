# Gmail Inbox IMAP Cleaner

A command-line tool to clean, organize, and label emails in your Gmail inbox using IMAP. Built with Python and [Rich](https://github.com/Textualize/rich) for a polished terminal experience.

## Features

- **6 cleanup rules** to filter emails:
  1. Emails older than X days
  2. Newsletters / Promos (body contains "unsubscribe")
  3. Emails from a specific sender or domain
  4. Combined: Older than X + newsletters
  5. Receipts / Order Confirmations (matches specific phrases like "order confirmation", "invoice", etc.)
  6. Combined: Older than X + receipts
- **Label emails** — apply Gmail labels (e.g. `receipts`) to matched emails without deleting them
- **Trash emails** — move matched emails to Gmail's Trash (auto-purged after 30 days)
- **Dry-run mode** — preview matched emails in a table before taking action
- **Skip already-labeled** — receipt rules automatically exclude emails you've already labeled
- **Auto-detects Trash folder** — works across Gmail locales (Trash, Bin, etc.)

## Prerequisites

- **Python 3.10+**
- A Gmail account with **IMAP enabled** ([how to enable](https://support.google.com/mail/answer/7126229))
- A **Gmail App Password** ([generate one here](https://myaccount.google.com/apppasswords)) — required if you have 2FA enabled

## Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/p3ji/gmailcleaner.git
cd gmailcleaner
```

### 2. Set up credentials

Copy the example environment file and fill in your details:

```bash
cp .env.example .env
```

Edit `.env` with your Gmail address and App Password:

```
GMAIL_EMAIL=you@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

### 3. Install & run

**Windows (double-click):**

- Run `install.bat` to create a virtual environment and install dependencies
- Run `run.bat` to launch the cleaner

**Manual setup (any OS):**

```bash
python -m venv .venv

# Activate the virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
python cleaner.py
```

## Usage

Once launched, the tool will:

1. Connect to Gmail via IMAP
2. Present a menu of cleanup rules
3. Search your inbox based on the selected rule
4. Show a preview table of the top 10 matching emails
5. Ask what action to take:
   - `dry-run` — preview only, no changes
   - `label` — apply a Gmail label (default: `receipts`)
   - `trash` — move to Gmail's Trash
   - `cancel` — abort

## Project Structure

```
gmailcleaner/
├── .env.example      # Credential template
├── .gitignore
├── cleaner.py         # Main script
├── install.bat        # Windows setup script
├── requirements.txt   # Python dependencies
├── run.bat            # Windows launcher
└── README.md
```

## Security

- Credentials are stored locally in `.env` and **never committed** to git
- Uses Gmail's IMAP over SSL (port 993)
- Uses App Passwords, not your main Google password

## License

MIT
