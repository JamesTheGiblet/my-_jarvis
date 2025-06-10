# gui.py
import time
import tkinter as tk
from tkinter import scrolledtext, font, simpledialog
from typing import Optional, Dict, Callable 
import threading # For thread-safe GUI updates

# Attempt to import PraxisCore from main.py
try:
    from main import PraxisCore, set_gui_output_callback, INACTIVITY_THRESHOLD_SECONDS, SPEECH_RECOGNITION_AVAILABLE, PRAXIS_VERSION_INFO
except ImportError as e:
    print(f"Error importing from main.py: {e}. Praxis GUI will run in standalone mode.")
    PraxisCore = None 
    set_gui_output_callback = None
    INACTIVITY_THRESHOLD_SECONDS = 300 
    SPEECH_RECOGNITION_AVAILABLE = False
    PRAXIS_VERSION_INFO = "Praxis (Standalone GUI)"
 
class PraxisGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"Praxis Command Interface - {PRAXIS_VERSION_INFO}")
        self.root.geometry("800x600") # Initial size

        self.praxis_core_initialized_event = threading.Event()
        self.is_shutting_down = False

        # Define fonts
        self.default_font = font.nametofont("TkDefaultFont")
        self.default_font.configure(size=10)
        self.status_font = font.Font(family="Helvetica", size=10)
        self.response_font = font.Font(family="Consolas", size=10) # Monospaced for logs/responses
        self.button_font = font.Font(family="Helvetica", size=10, weight="bold")

        # Initialize praxis_core to None before setting up UI widgets
        self.praxis_core = None
        # Call _setup_ui_widgets() early to ensure all UI elements are created
        self._setup_ui_widgets()

        # --- Initialize Praxis Core ---
        if PraxisCore and set_gui_output_callback:
            try:
                # Pass the method to update GUI status labels
                self.praxis_core = PraxisCore(gui_update_status_callback=self.update_status_labels_thread_safe)
                # Set the global callback for 'speak' to update the response area
                set_gui_output_callback(self.add_message_to_response_area_thread_safe)
            except Exception as e:
                self._add_message_to_response_area(f"Error initializing PraxisCore: {e}", "SystemError")
                self.praxis_core = None 
        else:
            self._add_message_to_response_area("PraxisCore could not be loaded. GUI is standalone.", "SystemError")

        if self.praxis_core:
            # Schedule the dialog and core initialization to run in the main GUI thread
            self.root.after(10, self._show_user_dialog_and_initialize_core) # Small delay for window to be ready
            self.root.after(100, self._start_inactivity_timer_if_ready) # Check shortly if core is ready
        
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _setup_ui_widgets(self):
        # --- Status Bar Frame ---
        status_frame = tk.Frame(self.root, bd=1, relief=tk.SUNKEN)
        status_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=(5,0))

        self.user_status_label = tk.Label(status_frame, text="User: [Not Set]", font=self.status_font, anchor=tk.W)
        self.user_status_label.pack(side=tk.LEFT, padx=5)

        self.mode_status_label = tk.Label(status_frame, text="Mode: [N/A]", font=self.status_font, anchor=tk.W)
        self.mode_status_label.pack(side=tk.LEFT, padx=5)

        self.praxis_status_label = tk.Label(status_frame, text="Praxis: Idle", font=self.status_font, anchor=tk.E)
        self.praxis_status_label.pack(side=tk.RIGHT, padx=5)

        # Rate Limit Status Labels (add them before Praxis status to keep it on the right)
        self.rpd_status_label = tk.Label(status_frame, text="RPD: 0/0", font=self.status_font, anchor=tk.W)
        self.rpd_status_label.pack(side=tk.LEFT, padx=5)
        self.tpm_status_label = tk.Label(status_frame, text="TPM: 0/0", font=self.status_font, anchor=tk.W)
        self.tpm_status_label.pack(side=tk.LEFT, padx=5)
        self.rpm_status_label = tk.Label(status_frame, text="RPM: 0/0", font=self.status_font, anchor=tk.W)
        self.rpm_status_label.pack(side=tk.LEFT, padx=5)


        # --- Response Display Area ---
        response_frame = tk.Frame(self.root)
        response_frame.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)

        self.response_area = scrolledtext.ScrolledText(response_frame, wrap=tk.WORD, state=tk.DISABLED, font=self.response_font, bg="#f0f0f0", relief=tk.SUNKEN, bd=1)
        self.response_area.pack(fill=tk.BOTH, expand=True)
        self._add_message_to_response_area("Praxis GUI Initialized. Welcome!", "System")

        # --- Command Input Area ---
        input_frame = tk.Frame(self.root)
        input_frame.pack(fill=tk.X, padx=5, pady=(0,5))

        self.command_label = tk.Label(input_frame, text="Command:", font=self.default_font)
        self.command_label.pack(side=tk.LEFT, padx=(0,5))

        self.command_entry = tk.Entry(input_frame, font=self.default_font, relief=tk.SUNKEN, bd=1)
        self.command_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.command_entry.bind("<Return>", self.send_command_event) # Bind Enter key

        self.send_button = tk.Button(input_frame, text="Send", command=self.send_command, font=self.button_font, relief=tk.RAISED, bd=2)
        self.send_button.pack(side=tk.RIGHT, padx=(5,0))

        # --- Control Buttons Area ---
        controls_frame = tk.Frame(self.root)
        controls_frame.pack(fill=tk.X, padx=5, pady=(0,5))

        self.toggle_input_mode_button = tk.Button(controls_frame, text="Toggle Input Mode", command=self.toggle_input_mode, font=self.button_font, relief=tk.RAISED, bd=2)
        self.toggle_input_mode_button.pack(side=tk.LEFT, padx=(0,2))
        if not (SPEECH_RECOGNITION_AVAILABLE and self.praxis_core and self.praxis_core.recognizer and self.praxis_core.microphone):
            self.toggle_input_mode_button.config(state=tk.DISABLED, text="Voice N/A")

        self.toggle_tts_mute_button = tk.Button(controls_frame, text="Mute TTS", command=self.toggle_tts_mute, font=self.button_font, relief=tk.RAISED, bd=2)
        self.toggle_tts_mute_button.pack(side=tk.LEFT, padx=(2,5))

        # --- Feedback Buttons ---
        self.feedback_label = tk.Label(controls_frame, text="Feedback on last response:", font=self.status_font)
        self.feedback_label.pack(side=tk.LEFT, padx=(10,2))
        self.thumb_up_button = tk.Button(controls_frame, text="👍 Up", command=self.give_positive_feedback, font=self.button_font, relief=tk.RAISED, bd=2, state=tk.DISABLED)
        self.thumb_up_button.pack(side=tk.LEFT, padx=(0,2))
        self.thumb_down_button = tk.Button(controls_frame, text="👎 Down", command=self.give_negative_feedback, font=self.button_font, relief=tk.RAISED, bd=2, state=tk.DISABLED)
        self.thumb_down_button.pack(side=tk.LEFT, padx=(0,2))

        # --- Confirmation Buttons Frame (initially hidden) ---
        self.confirmation_frame = tk.Frame(controls_frame)
        self.confirmation_frame.pack(side=tk.RIGHT, padx=5) 
        self.yes_button = tk.Button(self.confirmation_frame, text="Yes", command=self.confirm_yes, font=self.button_font, relief=tk.RAISED, bd=2)
        self.no_button = tk.Button(self.confirmation_frame, text="No", command=self.confirm_no, font=self.button_font, relief=tk.RAISED, bd=2)
        # Yes/No buttons are not packed initially, shown on demand by _update_status_labels

    def _show_user_dialog_and_initialize_core(self):
        if self.is_shutting_down or not self.praxis_core:
            self.praxis_core_initialized_event.set() # Ensure event is set if we abort
            return

        user_name = None
        try:
            # This dialog is now called from the main Tkinter thread via root.after
            user_name = simpledialog.askstring("User Identification", 
                                               "Welcome to Praxis. Who am I speaking to today?", 
                                               parent=self.root)
        except tk.TclError as e:
            # This might occur if the window is destroyed very rapidly after scheduling.
            print(f"GUI Info: User identification dialog error: {e}")
            self.add_message_to_response_area_thread_safe(f"Dialog error during user identification: {e}", "SystemError")
            # Fallback or error state for praxis_core initialization
            if self.praxis_core and not self.is_shutting_down:
                 self.praxis_core.initialize_user_session("Anonymous_DialogError")
            self.praxis_core_initialized_event.set()
            return
        except Exception as e: # Catch other potential dialog errors
            print(f"GUI Error: Unexpected error during user identification dialog: {e}")
            self.add_message_to_response_area_thread_safe(f"Unexpected dialog error: {e}", "SystemError")
            if self.praxis_core and not self.is_shutting_down:
                 self.praxis_core.initialize_user_session("Anonymous_UnexpectedDialogError")
            self.praxis_core_initialized_event.set()
            return

        if self.is_shutting_down: # Check if window was closed while dialog was open or immediately after
            self.praxis_core_initialized_event.set()
            return

        if user_name:
            self.praxis_core.initialize_user_session(user_name)
        else: # User cancelled or entered nothing
            self.add_message_to_response_area_thread_safe("User identification cancelled. Using 'Anonymous'.", "System")
            self.praxis_core.initialize_user_session("Anonymous")
        self.praxis_core_initialized_event.set() # Signal that core init is done

    def _start_inactivity_timer_if_ready(self):
        if self.praxis_core_initialized_event.is_set() and not self.is_shutting_down:
            self.root.after(INACTIVITY_THRESHOLD_SECONDS * 1000, self.check_inactivity)
        elif not self.is_shutting_down:
            self.root.after(100, self._start_inactivity_timer_if_ready) # Check again soon

    def _on_closing(self):
        """Handle window close event."""
        if self.is_shutting_down: # Prevent re-entry
            return
        self.is_shutting_down = True

        if self.praxis_core:
            self.add_message_to_response_area_thread_safe("GUI closing. Shutting down Praxis Core...", "System")
            
            # Define a function to destroy the root after a delay
            def delayed_destroy():
                if self.root.winfo_exists():
                    self.root.destroy()

            # Start core shutdown in a separate thread
            shutdown_thread = threading.Thread(target=self.praxis_core.shutdown, daemon=True)
            shutdown_thread.start()
            
            # Schedule the window destruction.
            # This allows the shutdown thread to run and potentially send its last messages
            # via the GUI callback (which uses root.after).
            self.root.after(750, delayed_destroy) 
        else:
            if self.root.winfo_exists():
                self.root.destroy()

    def _make_thread_safe_gui_call(self, func_to_call: Callable, *args):
        """Schedules a function to be called in the main Tkinter thread."""
        if self.root.winfo_exists() and not self.is_shutting_down: # Check if root window still exists
            self.root.after(0, lambda: func_to_call(*args))

    def add_message_to_response_area_thread_safe(self, message: str, prefix: Optional[str] = None):
        """Thread-safe way to add messages to the response area."""
        self._make_thread_safe_gui_call(self._add_message_to_response_area, message, prefix)
        
    def _add_message_to_response_area(self, message: str, prefix: Optional[str] = None):
        """Helper to add messages to the response area, ensuring it's enabled/disabled correctly."""
        if not self.response_area.winfo_exists(): return

        self.response_area.configure(state=tk.NORMAL)
        # Strip potential "Praxis: " prefix if already handled by GUI prefix
        if message.startswith("Praxis: ") and prefix == "Praxis":
            message_to_display = message[len("Praxis: "):].strip()
        elif message.startswith("Praxis Warning: ") and prefix == "Praxis":
            message_to_display = message[len("Praxis Warning: "):].strip()
            prefix = "Praxis Warn" # Shorten for display
        else:
            message_to_display = message.strip()

        full_message = f"{prefix}: {message_to_display}" if prefix else message_to_display
        self.response_area.insert(tk.END, f"{full_message}\n")
        self.response_area.configure(state=tk.DISABLED)
        self.response_area.see(tk.END) # Auto-scroll

    def update_status_labels_thread_safe(self, status: Dict[str, str], enable_feedback_buttons: bool = False):
        """Thread-safe way to update status labels."""
        # Pass enable_feedback_buttons to the actual update method
        self._make_thread_safe_gui_call(self._update_status_labels, status, enable_feedback_buttons)

    def _update_status_labels(self, status: Dict[str, str], enable_feedback_buttons: bool = False):
        """Updates the GUI status labels based on dict from PraxisCore."""
        if not self.root.winfo_exists(): return

        self.user_status_label.config(text=f"User: {status.get('user', '[N/A]')}")
        current_mode = status.get('mode', '[N/A]')
        self.mode_status_label.config(text=f"Mode: {current_mode}")
        self.praxis_status_label.config(text=f"Praxis: {status.get('praxis_state', 'Idle')}")
        
        # Update rate limit labels
        self.rpm_status_label.config(text=f"RPM: {status.get('rpm', '0/0')}")
        self.tpm_status_label.config(text=f"TPM: {status.get('tpm', '0/0')}") # Ensure this uses a reasonable default if key missing
        self.rpd_status_label.config(text=f"RPD: {status.get('rpd', '0/0')}")

        effective_sr_available = SPEECH_RECOGNITION_AVAILABLE and self.praxis_core and \
                                 self.praxis_core.recognizer and self.praxis_core.microphone

        if effective_sr_available:
            self.toggle_input_mode_button.config(state=tk.NORMAL)
            if current_mode == 'voice':
                self.toggle_input_mode_button.config(text="To Text Input")
            else:
                self.toggle_input_mode_button.config(text="To Voice Input")
        else:
            self.toggle_input_mode_button.config(state=tk.DISABLED, text="Voice N/A")
        
        confirmation_prompt = status.get("confirmation_prompt")
        if confirmation_prompt and status.get("praxis_state") == "Awaiting Confirmation":
            self.show_confirmation_buttons()
        else:
            self.hide_confirmation_buttons()
        
        # Re-enable command input if not awaiting confirmation and not shutting down
        if not confirmation_prompt and status.get("praxis_state") != "Awaiting Confirmation" and \
           status.get("praxis_state") not in ["Thinking...", "Listening...", "Speaking...", "Proactive...", "Shutting down", "Shutdown"] and \
           not self.is_shutting_down:
            self.send_button.config(state=tk.NORMAL)
            self.command_entry.config(state=tk.NORMAL)
            if current_mode == 'text': # Only focus if in text mode
                self.command_entry.focus_set()
        elif status.get("praxis_state") in ["Thinking...", "Listening...", "Speaking...", "Proactive..."] or confirmation_prompt:
            self.send_button.config(state=tk.DISABLED)
            self.command_entry.config(state=tk.DISABLED)
        
        # Enable/disable feedback buttons
        feedback_state = tk.NORMAL if enable_feedback_buttons and self.praxis_core and self.praxis_core.last_interaction_id_for_feedback is not None else tk.DISABLED
        self.thumb_up_button.config(state=feedback_state)
        self.thumb_down_button.config(state=feedback_state)


    def send_command_event(self, event=None): # Event handler for Enter key, event is optional
        self.send_command()

    def send_command(self):
        if not self.praxis_core or not self.praxis_core_initialized_event.is_set():
            self._add_message_to_response_area("Praxis Core not ready to process commands.", "SystemError")
            return
        
        command_text = self.command_entry.get()
        if command_text:
            user_display_name = self.praxis_core.current_user_name if self.praxis_core.current_user_name else "User"
            self.add_message_to_response_area_thread_safe(command_text, f"You ({user_display_name})")
            
            self.send_button.config(state=tk.DISABLED)
            self.command_entry.config(state=tk.DISABLED)
            
            # Run command processing in a thread to keep GUI responsive
            threading.Thread(target=self.praxis_core.process_command_text, args=(command_text,), daemon=True).start()
            self.command_entry.delete(0, tk.END)

    def toggle_input_mode(self):
        if not self.praxis_core or not self.praxis_core_initialized_event.is_set(): return
        # PraxisCore.toggle_input_mode_core will handle speaking and updating status
        # Run in a thread if it might block (e.g., starting voice input)
        threading.Thread(target=self.praxis_core.toggle_input_mode_core, daemon=True).start()

    def toggle_tts_mute(self):
        if not self.praxis_core or not self.praxis_core.skill_context or not self.praxis_core_initialized_event.is_set(): return
        is_now_muted = self.praxis_core.toggle_tts_mute_core()
        if is_now_muted:
            self.toggle_tts_mute_button.config(text="Unmute TTS")
        else:
            self.toggle_tts_mute_button.config(text="Mute TTS")

    def check_inactivity(self):
        """Periodically called to check for user inactivity."""
        if self.praxis_core and self.praxis_core.is_running and self.praxis_core_initialized_event.is_set() and not self.is_shutting_down:
            # Run inactivity check in a thread as it might involve LLM calls / speaking
            threading.Thread(target=self.praxis_core.handle_inactivity, daemon=True).start()
            if self.root.winfo_exists() and not self.is_shutting_down: # Reschedule only if window exists
                self.root.after(INACTIVITY_THRESHOLD_SECONDS * 1000, self.check_inactivity)

    def show_confirmation_buttons(self):
        """Makes Yes/No buttons visible."""
        self.yes_button.pack(side=tk.LEFT, padx=(0, 2))
        self.no_button.pack(side=tk.LEFT, padx=(0, 2))
        self.send_button.config(state=tk.DISABLED) 
        self.command_entry.config(state=tk.DISABLED)

    def hide_confirmation_buttons(self):
        """Hides Yes/No buttons."""
        self.yes_button.pack_forget()
        self.no_button.pack_forget()
        # Re-enabling is handled by _update_status_labels based on praxis_state

    def confirm_yes(self):
        if self.praxis_core and self.praxis_core_initialized_event.is_set():
            self.add_message_to_response_area_thread_safe("Yes (confirmed)", "You")
            threading.Thread(target=self.praxis_core.handle_gui_confirmation, args=(True,), daemon=True).start()

    def confirm_no(self):
        if self.praxis_core and self.praxis_core_initialized_event.is_set():
            self.add_message_to_response_area_thread_safe("No (declined)", "You")
            threading.Thread(target=self.praxis_core.handle_gui_confirmation, args=(False,), daemon=True).start()

    def give_positive_feedback(self):
        if self.praxis_core and self.praxis_core.last_interaction_id_for_feedback is not None:
            self.add_message_to_response_area_thread_safe("Provided positive feedback.", "System")
            threading.Thread(target=self.praxis_core.handle_response_feedback, args=(True,), daemon=True).start()
            self.thumb_up_button.config(state=tk.DISABLED) # Disable after use
            self.thumb_down_button.config(state=tk.DISABLED)

    def give_negative_feedback(self):
        if self.praxis_core and self.praxis_core.last_interaction_id_for_feedback is not None:
            self.add_message_to_response_area_thread_safe("Provided negative feedback.", "System")
            threading.Thread(target=self.praxis_core.handle_response_feedback, args=(False,), daemon=True).start()
            self.thumb_up_button.config(state=tk.DISABLED) # Disable after use
            self.thumb_down_button.config(state=tk.DISABLED)

if __name__ == "__main__":
    root = tk.Tk()
    app = PraxisGUI(root)
    root.mainloop()