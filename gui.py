import tkinter as tk
from tkinter import messagebox, ttk
import main
import config
import requests
import re

class BlockListApp:
    def __init__(self, master):
        self.master = master
        self.master.title("BlueSky Block List Automator")

        # Create a notebook to hold tabs
        self.notebook = ttk.Notebook(self.master)
        self.notebook.pack(expand=True, fill=tk.BOTH)

        # Create frames for each tab
        self.blocklist_tab = ttk.Frame(self.notebook)
        self.settings_tab = ttk.Frame(self.notebook)

        # Add tabs to notebook
        self.notebook.add(self.blocklist_tab, text="Blocklist")
        self.notebook.add(self.settings_tab, text="Settings")

        self.keywords = config.TARGET_KEYWORDS

        # Variables for settings
        self.username_var = tk.StringVar(value=config.USERNAME)
        self.password_var = tk.StringVar(value=config.APP_PASSWORD)
        # Instead of storing the direct BLOCKLIST_URI, we store the blocklist link (from bsky.app)
        self.blocklist_link_var = tk.StringVar()

        # Initialize the blocklist link var with a derived link, if known
        self.blocklist_link_var.set(self.construct_blocklist_link(config.BLOCKLIST_URI))

        # Set up the UI in each tab
        self.setup_blocklist_tab()
        self.setup_settings_tab()

    def setup_blocklist_tab(self):
        # Frame for listbox
        self.list_frame = tk.Frame(self.blocklist_tab)
        self.list_frame.pack(pady=10)

        # Listbox to display keywords
        self.keyword_listbox = tk.Listbox(self.list_frame, height=10, width=50, selectmode=tk.SINGLE)
        self.keyword_listbox.pack(side=tk.LEFT, padx=10)
        self.update_listbox()

        # Scrollbar for listbox
        self.scrollbar = tk.Scrollbar(self.list_frame)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.keyword_listbox.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.keyword_listbox.yview)

        # Frame for controls
        self.control_frame = tk.Frame(self.blocklist_tab)
        self.control_frame.pack(pady=10)

        # Entry to add keywords
        self.entry = tk.Entry(self.control_frame, width=30)
        self.entry.grid(row=0, column=0, padx=5)

        # Add button
        self.add_button = tk.Button(self.control_frame, text="Add Keyword", command=self.add_keyword)
        self.add_button.grid(row=0, column=1, padx=5)

        # Remove button
        self.remove_button = tk.Button(self.control_frame, text="Remove Selected", command=self.remove_keyword)
        self.remove_button.grid(row=0, column=2, padx=5)

        # Scan button
        self.scan_button = tk.Button(
            self.blocklist_tab,
            text="Run Scan",
            command=self.run_scan,
            bg="green",
            fg="white"
        )
        self.scan_button.pack(pady=10)

        # Unblock All Users button
        self.unblock_button = tk.Button(
            self.blocklist_tab,
            text="Unblock All Users",
            command=self.unblock_all_users,
            bg="red",
            fg="white"
        )
        self.unblock_button.pack(pady=10)

    def setup_settings_tab(self):
        # Labels and entries for each setting
        tk.Label(self.settings_tab, text="Username:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.E)
        self.username_entry = tk.Entry(self.settings_tab, textvariable=self.username_var, width=30)
        self.username_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(self.settings_tab, text="App Password:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.E)
        self.password_entry = tk.Entry(self.settings_tab, textvariable=self.password_var, width=30, show='*')
        self.password_entry.grid(row=1, column=1, padx=5, pady=5)

        tk.Label(self.settings_tab, text="Blocklist Link:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.E)
        self.blocklist_link_entry = tk.Entry(self.settings_tab, textvariable=self.blocklist_link_var, width=50)
        self.blocklist_link_entry.grid(row=2, column=1, padx=5, pady=5)

        # Save button
        self.save_button = tk.Button(
            self.settings_tab,
            text="Save Settings",
            command=self.save_settings
        )
        self.save_button.grid(row=3, column=0, columnspan=2, pady=10)

    def construct_blocklist_link(self, blocklist_uri):
        """Try to parse the at:// style blocklist URI into a link like bsky.app/profile/<handle>/lists/<id>."""
        if not blocklist_uri.startswith("at://"):
            return ""
        pattern = r"^at://(did:plc:[^/]+)/app.bsky.graph.list/(.+)$"
        match = re.match(pattern, blocklist_uri)
        if not match:
            return ""
        # We'll store them for reference
        did_part = match.group(1)
        blocklist_id = match.group(2)
        # We can't easily convert the DID back to a handle here.
        return ""  # We'll let the user supply the link themselves.

    def update_listbox(self):
        """Update the listbox to reflect the current keywords."""
        self.keyword_listbox.delete(0, tk.END)
        for keyword in self.keywords:
            self.keyword_listbox.insert(tk.END, keyword)

    def add_keyword(self):
        """Add a keyword to the block list."""
        keyword = self.entry.get().strip()
        if keyword and keyword not in config.TARGET_KEYWORDS:
            config.TARGET_KEYWORDS.append(keyword)
            self.update_config_file()
            self.update_listbox()
            self.entry.delete(0, tk.END)
            messagebox.showinfo("Success", f"'{keyword}' has been added to the block list.")
        elif keyword in config.TARGET_KEYWORDS:
            messagebox.showwarning("Duplicate Keyword", f"'{keyword}' is already in the block list.")
        else:
            messagebox.showwarning("Input Error", "Please enter a valid keyword.")

    def remove_keyword(self):
        """Remove the selected keyword from the block list."""
        selected = self.keyword_listbox.curselection()
        if selected:
            keyword = self.keyword_listbox.get(selected)
            if keyword in config.TARGET_KEYWORDS:
                config.TARGET_KEYWORDS.remove(keyword)
                self.update_config_file()
                self.update_listbox()
                messagebox.showinfo("Success", f"'{keyword}' has been removed from the block list.")
            else:
                messagebox.showwarning("Error", f"'{keyword}' not found in the block list.")
        else:
            messagebox.showwarning("Selection Error", "Please select a keyword to remove.")

    def run_scan(self):
        """Run the scan, display found users, and optionally block them."""
        try:
            access_token, session_did = main.get_session()
            main.SESSION_DID = session_did
            found_users = main.monitor_and_block(access_token)

            if not found_users:
                messagebox.showinfo("Scan Complete", "No users matching the keywords were found.")
                return

            confirm = messagebox.askyesno("Confirm Blocking", f"Found {len(found_users)} users. Block them?")
            if confirm:
                blocked_count = main.block_users(access_token, found_users)
                messagebox.showinfo("Scan Complete", f"Blocked {blocked_count} users from the block list.")
            else:
                messagebox.showinfo("Scan Canceled", "No users were blocked.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during the scan: {e}")

    def unblock_all_users(self):
        """Unblock all users in the block list."""
        confirm = messagebox.askyesno(
            "Confirm Unblock", "Are you sure you want to unblock all users from the block list?"
        )
        if not confirm:
            return

        try:
            access_token, session_did = main.get_session()
            main.SESSION_DID = session_did

            removed_count = main.remove_all_users_from_blocklist(access_token)
            messagebox.showinfo("Unblock Complete", f"{removed_count} users have been removed from the block list.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during the unblock process: {e}")

    def save_settings(self):
        """Save the updated settings to config.py, ensuring the DID portion is updated when the username changes.
        If the user also provides a blocklist link, parse out the blocklist ID from that link, otherwise reuse the old one."""
        new_username = self.username_var.get().strip()
        new_password = self.password_var.get().strip()
        new_link = self.blocklist_link_var.get().strip()

        # 1) Always resolve new_username to a DID
        resolved_did = self.resolve_handle_to_did(new_username)

        # 2) Extract the old blocklist DID + ID from the current config
        old_uri_pattern = r'^at://(did:plc:[^/]+)/app.bsky.graph.list/(.+)$'
        old_match = re.match(old_uri_pattern, config.BLOCKLIST_URI)
        old_did = ""
        old_blocklist_id = ""
        if old_match:
            old_did = old_match.group(1)
            old_blocklist_id = old_match.group(2)

        # 3) Attempt to parse a new blocklist ID from the link (if provided)
        new_blocklist_id = old_blocklist_id  # fallback to old blocklist ID
        if new_link:
            try:
                link_pattern = r"profile/[^/]+/lists/([^/]+)"
                link_match = re.search(link_pattern, new_link)
                if link_match:
                    new_blocklist_id = link_match.group(1)
                else:
                    messagebox.showwarning(
                        "Invalid Blocklist Link",
                        "Could not parse the provided blocklist link.\n"
                        "Ensure it's in the form:\n"
                        "https://bsky.app/profile/<handle>/lists/<blocklist_id>\n"
                        "(Using old blocklist ID.)"
                    )
            except Exception as e:
                messagebox.showwarning(
                    "Error Parsing Link",
                    f"An error occurred parsing the blocklist link: {e}\nUsing old blocklist ID."
                )

        # 4) Final DID: if we resolved a new DID from new_username, use it, else fallback
        final_did = resolved_did if resolved_did else old_did

        # 5) Construct the new blocklist URI
        if final_did and new_blocklist_id:
            final_blocklist_uri = f"at://{final_did}/app.bsky.graph.list/{new_blocklist_id}"
        else:
            final_blocklist_uri = config.BLOCKLIST_URI

        # 6) Update config in memory
        config.USERNAME = new_username
        config.APP_PASSWORD = new_password
        config.BLOCKLIST_URI = final_blocklist_uri

        # 7) Rewrite config file
        self.update_config_file()
        messagebox.showinfo("Settings Saved", "Your changes have been saved.")

    def resolve_handle_to_did(self, handle: str) -> str:
        """Resolve a Bluesky handle to its DID by calling the identity.resolveHandle endpoint."""
        url = f"{config.BASE_URL}/com.atproto.identity.resolveHandle?handle={handle}"
        try:
            resp = requests.get(url)
            resp.raise_for_status()
            data = resp.json()
            if "did" in data:
                return data["did"]
        except Exception:
            pass
        return ""

    def update_config_file(self):
        """Write the updated keywords and credentials back to the config.py file."""
        with open("config.py", "r") as file:
            lines = file.readlines()

        in_target_keywords = False
        updated_lines = []

        for line in lines:
            stripped = line.strip()

            # Update APP_PASSWORD
            if stripped.startswith("APP_PASSWORD"):
                updated_lines.append(f'APP_PASSWORD = "{config.APP_PASSWORD}"  # Your app password\n')
            elif stripped.startswith("USERNAME"):
                updated_lines.append(f'USERNAME = "{config.USERNAME}"  # Your Bluesky username\n')
            elif stripped.startswith("BLOCKLIST_URI"):
                updated_lines.append(f'BLOCKLIST_URI = "{config.BLOCKLIST_URI}"  # Your blocklist URI\n')
            elif stripped.startswith("TARGET_KEYWORDS"):
                updated_lines.append("TARGET_KEYWORDS = [\n")
                for keyword in config.TARGET_KEYWORDS:
                    updated_lines.append(f'    "{keyword}",\n')
                updated_lines.append("]\n")
                in_target_keywords = True
            elif in_target_keywords:
                if stripped == "]":
                    in_target_keywords = False
                # skip
            else:
                updated_lines.append(line)

        with open("config.py", "w") as file:
            file.writelines(updated_lines)


if __name__ == "__main__":
    root = tk.Tk()
    app = BlockListApp(root)
    root.mainloop()
