#!/usr/bin/env python3
import hashlib
import threading
import queue
import tkinter as tk
from tkinter import filedialog, messagebox, StringVar, IntVar, scrolledtext
from tkinter.ttk import Progressbar, Style
import os

class HashCracker:
    def __init__(self, target_hash, algorithm, dictionary_file, progress_callback, current_guess_callback, completion_callback):
        self.target_hash = target_hash
        self.algorithm = algorithm
        self.dictionary_file = dictionary_file
        self.progress_callback = progress_callback
        self.current_guess_callback = current_guess_callback
        self.completion_callback = completion_callback
        self.found = None
        self.lock = threading.Lock()
        self.total_guesses = 0
        self.guess_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()

    def hash_function(self, guess):
        hash_functions = {
            'md5': hashlib.md5,
            'sha1': hashlib.sha1,
            'sha256': hashlib.sha256,
            'sha512': hashlib.sha512,
            'sha224': hashlib.sha224,
            'sha384': hashlib.sha384,
            'sha512/224': lambda x: hashlib.sha512(x).hexdigest()[:56],
            'sha512/256': lambda x: hashlib.sha512(x).hexdigest()[:64],
            'blake2b': hashlib.blake2b,
            'blake2s': hashlib.blake2s,
            'ripemd160': lambda x: hashlib.new('ripemd160', x).hexdigest(),
            'whirlpool': lambda x: hashlib.new('whirlpool', x).hexdigest(),
        }
        if self.algorithm not in hash_functions:
            raise ValueError("Unsupported hash algorithm")
        return hash_functions[self.algorithm](guess.encode()).hexdigest()

    def brute_force_worker(self):
        while not self.stop_event.is_set():
            self.pause_event.wait()  # Wait if paused
            try:
                guess = self.guess_queue.get(timeout=1)
                self.total_guesses += 1
                self.current_guess_callback(guess)  # Update the current guess display
                if self.hash_function(guess) == self.target_hash:
                    with self.lock:
                        self.found = guess
                    self.stop_event.set()  # Stop all threads
                    return
                self.progress_callback(self.total_guesses)
            except queue.Empty:
                continue

    def generate_guesses(self):
        if self.dictionary_file:
            try:
                with open(self.dictionary_file, 'r') as file:
                    for line in file:
                        guess = line.strip()  # Remove any surrounding whitespace/newline
                        if guess:  # Ensure the guess is not empty
                            self.guess_queue.put(guess)
                            if self.stop_event.is_set():  # Stop if cracking is canceled
                                break
            except FileNotFoundError:
                messagebox.showerror("Error", "Dictionary file not found. Please select a valid file.")
            except IOError as e:
                messagebox.showerror("Error", f"Failed to read dictionary file: {e}")
            except Exception as e:
                messagebox.showerror("Error", f"An unexpected error occurred: {e}")

    def start_cracking(self):
        # Set the pause_event to allow threads to run
        self.pause_event.set()

        # Start worker threads
        workers = []
        num_threads = os.cpu_count() or 1  # Use the number of CPU cores
        for _ in range(num_threads):
            thread = threading.Thread(target=self.brute_force_worker)
            thread.start()
            workers.append(thread)

        # Generate guesses from the dictionary file
        self.generate_guesses()

        # Wait for all workers to finish
        for worker in workers:
            worker.join()

        # Notify completion
        self.completion_callback(self.found)

class HashCrackerGUI:
    def __init__(self, master):
        self.master = master
        master.title(">>--ADVANCE-HASH-CRACKER---<<")
        master.geometry("600x700")
        master.configure(bg="#2E2E2E")

        self.target_hash_var = StringVar()
        self.algorithm_var = StringVar(value='md5')
        self.dictionary_file = None
        self.canceled = False  # Flag to indicate if the cracking was canceled

        self.create_widgets()

    def create_widgets(self):
        style = Style()
        style.configure("TButton", padding=6, relief="flat", background="#4CAF50", foreground="white")
        style.map("TButton", background=[("active", "#45a049")])

        title_label = tk.Label(self.master, text="ADVANCE-HASH-CRACKER", font=("Helvetica", 24), bg="#2E2E2E", fg="white")
        title_label.pack(pady=20)

        # Frame for hash input and algorithm selection
        hash_frame = tk.Frame(self.master, bg="#2E2E2E")
        hash_frame.pack(pady=10)

        # Entry for hash input with binding to detect changes
        hash_entry = tk.Entry(hash_frame, textvariable=self.target_hash_var, width=40)
        hash_entry.pack(side=tk.LEFT, padx=5)
        hash_entry.bind("<KeyRelease>", self.detect_hash_type)  # Bind key release event

        tk.Label(hash_frame, text=">> SELECT TYPE:", bg="#2E2E2E", fg="white").pack(side=tk.LEFT, padx=5)
        tk.OptionMenu(hash_frame, self.algorithm_var, 
                       'md5', 'sha1', 'sha256', 'sha512', 
                       'sha224', 'sha384', 'sha512/224', 
                       'sha512/256', 'blake2b', 'blake2s', 
                       'ripemd160', 'whirlpool').pack(side=tk.LEFT, padx=5)

        tk.Button(self.master, text="-> BROWSE FILE", command=self.select_dictionary_file).pack(pady=10)

        self.progress_var = IntVar()
        self.progress_bar = Progressbar(self.master, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=20, pady=10)

        self.status_label = tk.Label(self.master, text="", bg="#2E2E2E", fg="white")
        self.status_label.pack(pady=5)

        # Label to show the current guess
        self.current_guess_label = tk.Label(self.master, text="TESTING: ", bg="#2E2E2E", fg="white")
        self.current_guess_label.pack(pady=5)

        # Text box to show the guesses
        self.guess_box = scrolledtext.ScrolledText(self.master, width=50, height=10, bg="#2E2E2E", fg="white", insertbackground='white')
        self.guess_box.pack(pady=10)

        # Result label to show the outcome of the cracking attempt
        self.result_label = tk.Label(self.master, text="", bg="#2E2E2E", fg="white")
        self.result_label.pack(pady=5)

        # Control buttons
        control_frame = tk.Frame(self.master, bg="#2E2E2E")
        control_frame.pack(pady=10)

        self.start_button = tk.Button(control_frame, text="START CRACKING", command=self.start_cracking)
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.pause_button = tk.Button(control_frame, text="PAUSE", command=self.pause_cracking, state=tk.DISABLED)
        self.pause_button.pack(side=tk.LEFT, padx=5)

        self.resume_button = tk.Button(control_frame, text="RESUME", command=self.resume_cracking, state=tk.DISABLED)
        self.resume_button.pack(side=tk.LEFT, padx=5)

        self.cancel_button = tk.Button(control_frame, text="CANCEL", command=self.cancel_cracking, state=tk.DISABLED)
        self.cancel_button.pack(side=tk.LEFT, padx=5)

        self.help_button = tk.Button(control_frame, text="HELP", command=self.show_help)
        self.help_button.pack(side=tk.LEFT, padx=5)

        self.close_button = tk.Button(control_frame, text="CLOSE TOOL", command=self.close_application)
        self.close_button.pack(side=tk.LEFT, padx=5)

        self.is_cracking = False

    def detect_hash_type(self, event):
        # Get the current hash input
        hash_string = self.target_hash_var.get().strip()
        # Identify the hash type
        identified_algorithm = self.identify_hash(hash_string)
        if identified_algorithm:
            self.algorithm_var.set(identified_algorithm)  # Set the identified algorithm

    def identify_hash(self, hash_string):
        hash_length = len(hash_string)

        if hash_length == 32:
            return "md5"
        elif hash_length == 40:
            return "sha1"  # Default to SHA-1 for 40 characters
        elif hash_length == 56:
            return "sha224"
        elif hash_length == 64:
            return "sha256"  # Default to SHA-256 for 64 characters
        elif hash_length == 96:
            return "sha384"
        elif hash_length == 128:
            return "sha512"  # Default to SHA-512 for 128 characters
        else:
            return None  # Unknown hash type

    def select_dictionary_file(self):
        self.dictionary_file = filedialog.askopenfilename(title="Select Dictionary File", filetypes=[("Textfiles", "*.txt"), ("All files", "*.*")])
        if self.dictionary_file:
            self.status_label.config(text=f"Selected dictionary file: {self.dictionary_file}")
        else:
            self.status_label.config(text="No dictionary file selected.")

    def is_valid_hash(self, hash_string, algorithm):
        hash_lengths = {
            'md5': 32,
            'sha1': 40,
            'sha256': 64,
            'sha512': 128,
            'sha224': 56,
            'sha384': 96,
            'sha512/224': 56,
            'sha512/256': 64,
            'blake2b': 64,
            'blake2s': 32,
            'ripemd160': 40,
            'whirlpool': 128,
        }
        return len(hash_string) == hash_lengths.get(algorithm, 0)

    def start_cracking(self):
        if self.is_cracking:
            messagebox.showwarning("Warning", "Cracking is already in progress.")
            return

        target_hash = self.target_hash_var.get().strip()
        algorithm = self.algorithm_var.get()

        if not algorithm:
            messagebox.showerror("Error", "Please enter a valid hash or select an algorithm.")
            return

        if not self.is_valid_hash(target_hash, algorithm):
            messagebox.showerror("Error", "Invalid hash length for the selected algorithm.")
            return

        self.is_cracking = True
        self.canceled = False  # Reset the canceled flag
        self.status_label.config(text="Cracking in progress...")
        self.progress_var.set(0)
        self.guess_box.delete(1.0, tk.END)  # Clear previous guesses
        self.result_label.config(text="")  # Clear previous results

        self.start_button.config(state=tk.DISABLED)
        self.pause_button.config(state=tk.NORMAL)
        self.resume_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.NORMAL)

        self.hash_cracker = HashCracker(
            target_hash,
            algorithm,
            self.dictionary_file,
            self.update_progress,
            self.update_current_guess,
            self.display_result
        )

        threading.Thread(target=self.hash_cracker.start_cracking).start()

    def update_progress(self, total_guesses):
        # Update the progress bar smoothly
        self.progress_var.set(min(total_guesses, 100))  # Cap at 100 for the progress bar

    def update_current_guess(self, guess):
        self.current_guess_label.config(text=f"Current Guess: {guess}")
        self.guess_box.insert(tk.END, f"{guess}\n")  # Show the current guess in the guess box
        self.guess_box.see(tk.END)  # Scroll to the end

    def display_result(self, found):
        self.is_cracking = False
        self.start_button.config(state=tk.NORMAL)
        self.pause_button.config(state=tk.DISABLED)
        self.resume_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.DISABLED)

        if self.canceled:
            self.result_label.config(text="Cracking was canceled.")
        elif found:
            self.result_label.config(text=f"Password found: {found}")
        else:
            self.result_label.config(text="Password not found.")
        
        self.status_label.config(text="Cracking completed.")
        self.progress_var.set(100)  # Set progress bar to 100% when done

    def pause_cracking(self):
        if not self.is_cracking:
            messagebox.showwarning("Warning", "No cracking in progress.")
            return
        self.hash_cracker.pause_event.clear()  # Clear the pause event to pause
        self.status_label.config(text="Cracking paused.")
        self.pause_button.config(state=tk.DISABLED)
        self.resume_button.config(state=tk.NORMAL)

    def resume_cracking(self):
        if not self.is_cracking:
            messagebox.showwarning("Warning", "No cracking in progress.")
            return
        self.hash_cracker.pause_event.set()  # Set the pause event to resume
        self.status_label.config(text="Resuming cracking...")
        self.pause_button.config(state=tk.NORMAL)
        self.resume_button.config(state=tk.DISABLED)

    def cancel_cracking(self):
        if not self.is_cracking:
            messagebox.showwarning("Warning", "No cracking in progress.")
            return
        self.is_cracking = False
        self.canceled = True  # Set the canceled flag
        self.hash_cracker.stop_event.set()  # Stop the cracking process
        self.status_label.config(text="Cracking canceled.")
        self.result_label.config(text="")  # Clear the result label
        self.start_button.config(state=tk.NORMAL)
        self.pause_button.config(state=tk.DISABLED)
        self.resume_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.DISABLED)

    def close_application(self):
        if self.is_cracking:
            if messagebox.askokcancel("Quit", "Cracking is in progress. Do you really want to quit?"):
                self.cancel_cracking()
                self.master.quit()
        else:
            self.master.quit()

    def show_help(self):
        help_text = (
            "Hash Cracker Help\n"
            "1. Enter the hash you want to crack.\n"
            "2. Select the hashing algorithm from the dropdown.\n"
            "3. Choose a dictionary file containing potential passwords.\n"
            "4. Click 'START CRACKING' to begin.\n"
            "5. You can pause, resume, or cancel the cracking process at any time.\n"
            "6. The current guess and progress will be displayed."
        )
        messagebox.showinfo("Help", help_text)

if __name__ == "__main__":
    root = tk.Tk()
    app = HashCrackerGUI(root)
    root.mainloop()