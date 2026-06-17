import os
import sys
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
import getpass
from dotenv import load_dotenv

# Fix encoding for Windows legacy console (cp1252) to avoid UnicodeEncodeError
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.progress import track

# Initialize Rich Console
console = Console()

def load_credentials():
    """Load credentials from .env or prompt the user."""
    # Try loading from the current directory .env file
    load_dotenv()
    
    email_addr = os.getenv("GMAIL_EMAIL")
    password = os.getenv("GMAIL_APP_PASSWORD")
    
    if not email_addr:
        console.print("[yellow]GMAIL_EMAIL not found in environment or .env file.[/yellow]")
        email_addr = Prompt.ask("Enter your Gmail address")
        
    if not password:
        console.print("[yellow]GMAIL_APP_PASSWORD not found in environment or .env file.[/yellow]")
        console.print("[dim]Note: If you have 2-Factor Authentication enabled, use an App Password.[/dim]")
        password = getpass.getpass("Enter your password/App Password: ")
        
    return email_addr, password

def decode_mime_words(s):
    """Safely decode email header fields."""
    if not s:
        return ""
    try:
        decoded = decode_header(s)
        parts = []
        for word, encoding in decoded:
            if isinstance(word, bytes):
                if encoding:
                    parts.append(word.decode(encoding, errors="replace"))
                else:
                    parts.append(word.decode("utf-8", errors="replace"))
            else:
                parts.append(str(word))
        return "".join(parts)
    except Exception:
        return str(s)

def connect_imap(email_addr, password):
    """Connect to Gmail IMAP server and login."""
    try:
        console.print("[cyan]Connecting to imap.gmail.com:993...[/cyan]")
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        console.print("[cyan]Logging in...[/cyan]")
        mail.login(email_addr, password)
        console.print("[green]Successfully logged in![/green]")
        return mail
    except imaplib.IMAP4.error as e:
        console.print(f"[bold red]Authentication failed: {e}[/bold red]")
        console.print("[yellow]Please check your email and App Password. Ensure IMAP is enabled in Gmail settings.[/yellow]")
        return None
    except Exception as e:
        console.print(f"[bold red]Connection error: {e}[/bold red]")
        return None

def find_trash_folder(mail):
    """Discover Gmail's Trash folder, which might vary by locale (e.g. [Gmail]/Trash or [Gmail]/Bin)."""
    try:
        status, folder_list = mail.list()
        if status != "OK":
            return "[Gmail]/Trash"  # Fallback
            
        for folder_info in folder_list:
            folder_name = folder_info.decode("utf-8")
            # Look for Gmail's system trash folder tags
            if "\\Trash" in folder_name or "Trash" in folder_name:
                # Extract folder name inside quotes or last part
                parts = folder_name.split(' "/" ')
                if len(parts) > 1:
                    return parts[1].strip('"')
            elif "\\Bin" in folder_name or "Bin" in folder_name:
                parts = folder_name.split(' "/" ')
                if len(parts) > 1:
                    return parts[1].strip('"')
        
        return "[Gmail]/Trash"  # Default fallback
    except Exception:
        return "[Gmail]/Trash"

def build_search_criterion():
    """Prompt user for clean-up rules and build IMAP search criteria."""
    console.print(Panel.fit(
        "[bold cyan]Select Email Cleanup Rule[/bold cyan]\n\n"
        "1. Emails older than X days/years\n"
        "2. Newsletters / Promo (containing the word 'unsubscribe')\n"
        "3. Emails from a specific sender or domain\n"
        "4. Combine: Older than X AND containing 'unsubscribe'\n"
        "5. Receipts / Order Confirmations (specific phrases like 'order confirmation', 'invoice', etc.)\n"
        "6. Combine: Older than X AND Receipts / Order Confirmations",
        title="Rules Config"
    ))
    
    choice = Prompt.ask("Choose a rule", choices=["1", "2", "3", "4", "5", "6"], default="1")
    
    criteria = []
    
    if choice in ["1", "4", "6"]:
        days = Prompt.ask("Enter number of days old (e.g. 365 for 1 year, 730 for 2 years)", default="365")
        try:
            days_int = int(days)
        except ValueError:
            console.print("[red]Invalid number of days. Defaulting to 365.[/red]")
            days_int = 365
        cutoff_date = datetime.now() - timedelta(days=days_int)
        # Format date for IMAP: DD-Mon-YYYY (e.g., 01-Jan-2023)
        imap_date_str = cutoff_date.strftime("%d-%b-%Y")
        criteria.append(f'BEFORE {imap_date_str}')
        console.print(f"[dim]Adding filter: Older than {days_int} days (Before {imap_date_str})[/dim]")
        
    if choice in ["2", "4"]:
        criteria.append('BODY "unsubscribe"')
        console.print("[dim]Adding filter: Body contains 'unsubscribe'[/dim]")
        
    if choice == "3":
        sender = Prompt.ask("Enter sender email or domain (e.g., spam@spam.com or linkedin.com)")
        criteria.append(f'FROM "{sender}"')
        console.print(f"[dim]Adding filter: From {sender}[/dim]")
        
    if choice in ["5", "6"]:
        # Use specific multi-word phrases to avoid matching promotional emails
        # e.g. "40% off your purchase!" would match "purchase" alone, but NOT "order confirmation"
        criteria.append(
            'OR SUBJECT "order confirmation" '
            'OR SUBJECT "order receipt" '
            'OR SUBJECT "your order" '
            'OR SUBJECT "your receipt" '
            'OR SUBJECT "payment receipt" '
            'OR SUBJECT "payment confirmation" '
            'OR SUBJECT "shipping confirmation" '
            'OR SUBJECT "purchase confirmation" '
            'OR SUBJECT "invoice" '
            'SUBJECT "receipt for"'
        )
        # Exclude emails that already have the target label (Gmail IMAP extension)
        skip_label = Prompt.ask("Exclude emails already labeled as", default="receipts")
        if skip_label:
            criteria.append(f'NOT X-GM-LABELS "{skip_label}"')
            console.print(f"[dim]Adding filter: Receipts & order confirmations, skipping emails already labeled '{skip_label}'[/dim]")
        else:
            console.print("[dim]Adding filter: Receipts & order confirmations (specific phrases only, excludes promos)[/dim]")
        
    # Combine list into space-separated string
    return " ".join(criteria)

def preview_emails(mail, email_uids):
    """Fetch and print metadata for a slice of the matching emails."""
    if not email_uids:
        return
        
    total = len(email_uids)
    preview_limit = min(total, 10)
    
    console.print(f"\n[bold cyan]Previewing {preview_limit} of {total} matching emails:[/bold cyan]")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("No.", style="dim", width=4)
    table.add_column("Date", width=12)
    table.add_column("From", width=25)
    table.add_column("Subject", width=45)
    
    # We slice to fetch the latest/newest first or oldest first. Let's do latest first (from end of list)
    preview_uids = email_uids[-preview_limit:]
    preview_uids.reverse()  # Show most recent first
    
    for idx, uid in enumerate(preview_uids, start=1):
        # Fetch only headers to make it fast
        status, data = mail.uid('FETCH', uid, '(BODY[HEADER.FIELDS (SUBJECT FROM DATE)])')
        if status != 'OK' or not data or not data[0]:
            continue
            
        raw_email = data[0][1]
        msg = email.message_from_bytes(raw_email)
        
        subj = decode_mime_words(msg.get("Subject", "(No Subject)"))
        from_ = decode_mime_words(msg.get("From", "(Unknown Sender)"))
        date_ = msg.get("Date", "(Unknown Date)")
        
        # Format date briefly
        try:
            parsed_date = email.utils.parsedate_to_datetime(date_)
            date_str = parsed_date.strftime("%Y-%m-%d")
        except Exception:
            date_str = date_[:11] if date_ else "N/A"
            
        # Truncate fields for neat table alignment
        from_truncated = (from_[:22] + "..") if len(from_) > 24 else from_
        subj_truncated = (subj[:42] + "..") if len(subj) > 44 else subj
        
        table.add_row(str(idx), date_str, from_truncated, subj_truncated)
        
    console.print(table)

def main():
    console.print(Panel("[bold green]Gmail Inbox IMAP Cleaner[/bold green]", subtitle="Clean old or unwanted emails securely"))
    
    email_addr, password = load_credentials()
    mail = connect_imap(email_addr, password)
    
    if not mail:
        return
        
    try:
        # Default to select INBOX
        console.print("[cyan]Selecting 'INBOX'...[/cyan]")
        mail.select("INBOX")
        
        # Build search filters
        search_query = build_search_criterion()
        console.print(f"[cyan]Searching inbox with query: [bold]{search_query}[/bold]...[/cyan]")
        
        status, data = mail.uid('search', None, search_query)
        if status != 'OK':
            console.print("[bold red]Failed to execute search query.[/bold red]")
            return
            
        email_uids = data[0].split()
        total_emails = len(email_uids)
        
        if total_emails == 0:
            console.print("[bold green]No emails matched your criteria. Your inbox is clean![/bold green]")
            return
            
        console.print(f"[bold green]Found {total_emails} matching emails.[/bold green]")
        
        # Preview matching emails
        preview_emails(mail, email_uids)
        
        # Ask for confirmation
        action = Prompt.ask(
            "\n[bold yellow]What action would you like to take?[/bold yellow]",
            choices=["dry-run", "label", "trash", "cancel"],
            default="dry-run"
        )
        
        if action == "dry-run":
            console.print("[yellow]Dry-run selected. No emails were modified or deleted.[/yellow]")
            return
        elif action == "cancel":
            console.print("[blue]Operation cancelled.[/blue]")
            return
        elif action == "label":
            label_name = Prompt.ask("Enter Gmail label to apply", default="receipts")
            
            # Double confirm
            double_confirm = Confirm.ask(
                f"[bold red]Are you absolutely sure you want to apply the label '{label_name}' to all {total_emails} emails?[/bold red]"
            )
            
            if not double_confirm:
                console.print("[blue]Operation cancelled.[/blue]")
                return
                
            console.print(f"[yellow]Applying label '{label_name}' to {total_emails} emails...[/yellow]")
            
            success_count = 0
            for uid in track(email_uids, description="Labeling emails..."):
                # Use Gmail's IMAP extension to add custom label (enclosed in quotes to support spaces)
                label_status, _ = mail.uid('STORE', uid, '+X-GM-LABELS', f'"{label_name}"')
                if label_status == 'OK':
                    success_count += 1
                    
            console.print(f"[bold green]Done! Successfully applied label '{label_name}' to {success_count} of {total_emails} emails.[/bold green]")
            return
            
        # Action is trash. Let's make double-sure.
        double_confirm = Confirm.ask(
            f"[bold red]Are you absolutely sure you want to move all {total_emails} emails to Gmail's Trash?[/bold red]"
        )
        
        if not double_confirm:
            console.print("[blue]Operation cancelled.[/blue]")
            return
            
        # Discover the Trash folder
        trash_folder = find_trash_folder(mail)
        console.print(f"[cyan]Discovered Gmail Trash folder: [bold]{trash_folder}[/bold][/cyan]")
        
        # Move emails to Trash
        console.print(f"[yellow]Moving {total_emails} emails to Trash...[/yellow]")
        
        success_count = 0
        # Process in batches or track progress
        for uid in track(email_uids, description="Trashing emails..."):
            # Copy to trash
            copy_status, _ = mail.uid('COPY', uid, trash_folder)
            if copy_status == 'OK':
                # Mark as deleted in current mailbox (INBOX)
                mail.uid('STORE', uid, '+FLAGS', '\\Deleted')
                success_count += 1
                
        # Expunge to apply deletion in INBOX
        mail.expunge()
        
        console.print(f"[bold green]Done! Successfully moved {success_count} of {total_emails} emails to Trash.[/bold green]")
        console.print("[dim]Note: Gmail automatically purges emails in the Trash after 30 days.[/dim]")
        
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred during execution: {e}[/bold red]")
    finally:
        # Close connection cleanly
        try:
            mail.logout()
            console.print("[cyan]Connection closed cleanly.[/cyan]")
        except Exception:
            pass

if __name__ == "__main__":
    main()
