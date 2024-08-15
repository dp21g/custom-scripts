import tkinter as tk
from tkinter import ttk
import json
import os
import ctypes
import logging
from tkinter import simpledialog, Toplevel, Label, Entry, Button, Radiobutton, StringVar
import pyautogui
import pyperclip 
import time
from pynput import keyboard
import threading
import queue

# Use a relative path for logging
log_file_path = os.path.join(os.path.dirname(__file__), 'python_logfile.txt')
logging.basicConfig(filename=log_file_path, level=logging.DEBUG, format='%(asctime)s %(message)s')

logging.info("Starting the macro manager script...")

# Global variables
root = None
listbox = None
macros = None

# Global flag to control the listener loop
running = True

# Hotkey state
current_keys = set()

# Caps Lock detection variables
caps_lock_presses = []
CAPS_LOCK_THRESHOLD = 0.5  # Time threshold in seconds

def check_triple_caps_lock():
    global caps_lock_presses
    now = time.time()
    
    # Remove old presses
    caps_lock_presses = [t for t in caps_lock_presses if now - t < CAPS_LOCK_THRESHOLD]
    
    # Check if we have 3 presses within the threshold
    if len(caps_lock_presses) == 3:
        caps_lock_presses.clear()  # Reset the presses
        return True
    return False


def paste_in_last_app():
    logging.info("Minimizing the window")
    root.iconify()
    time.sleep(0.5)
    logging.info("Alt-tabbing to switch window")
    pyautogui.hotkey('alt', 'tab')
    time.sleep(0.5)
    logging.info("Pasting content")
    pyautogui.hotkey('ctrl', 'v')

def load_macros():
    macros_file_path = os.path.join(os.path.dirname(__file__), 'macros.json')
    if not os.path.exists(macros_file_path):
        logging.info(f"{macros_file_path} does not exist. Creating a new one.")
        default_macros = {}
        with open(macros_file_path, "w") as file:
            json.dump(default_macros, file, indent=4)
        logging.info(f"Created {macros_file_path} with default content.")
    
    with open(macros_file_path, "r") as file:
        logging.info(f"Loading macros from {macros_file_path}")
        return json.load(file)

def save_macros(macros):
    macros_file_path = os.path.join(os.path.dirname(__file__), 'macros.json')
    logging.info(f"Saving macros to {macros_file_path}")
    with open(macros_file_path, "w") as file:
        json.dump(macros, file, indent=4)

def send_to_app(command):
    logging.info(f"Sending command to application: {command}")
    last_app_window = ctypes.windll.user32.GetForegroundWindow()
    logging.info("send_to_app: ShowWindow")
    ctypes.windll.user32.ShowWindow(root.winfo_id(), 6)  # 6 = Minimize
    logging.info("Sending command to pyperclip copy")
    pyperclip.copy(command)
    logging.info("Alt-tabbing to switch window")
    pyautogui.hotkey('alt', 'tab')
    logging.info("Sending command to sleep")
    time.sleep(0.5)
    logging.info("Sending command to pyautogui pasting")
    pyautogui.hotkey('ctrl', 'v')
    ctypes.windll.user32.ShowWindow(root.winfo_id(), 9)  # 9 = Restore

def center_window(window, width, height):
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x_cordinate = int((screen_width/2) - (width/2))
    y_cordinate = int((screen_height/2) - (height/2))
    window.geometry(f"{width}x{height}+{x_cordinate}+{y_cordinate}")

def macro_popup(title, name='', command='', action='Send'):
    popup = Toplevel(root)
    popup.title(title)
    popup.geometry("300x300")
    popup.transient(root)
    popup.grab_set()
    center_window(popup, 300, 300)
    
    Label(popup, text="Macro Name:").pack(pady=5)
    name_entry = Entry(popup)
    name_entry.pack(pady=5)
    name_entry.insert(0, name)
    
    Label(popup, text="Command:").pack(pady=5)
    command_entry = Entry(popup)
    command_entry.pack(pady=5)
    command_entry.insert(0, command)
    
    action_var = StringVar(value=action)
    Label(popup, text="Action:").pack(pady=5)
    Radiobutton(popup, text="Send", variable=action_var, value="Send").pack()
    Radiobutton(popup, text="Run", variable=action_var, value="Run").pack()
    
    save_button = Button(popup, text="Save", command=lambda: save(name_entry, command_entry, action_var, popup))
    save_button.pack(pady=20)
    save_button.focus_set()
    
    popup.bind('<Return>', lambda event: save(name_entry, command_entry, action_var, popup))
    popup.mainloop()

def save(name_entry, command_entry, action_var, popup):
    name = name_entry.get()
    command = command_entry.get()
    action = action_var.get()
    if name and command:
        macros[name] = {"command": command, "action": action}
        save_macros(macros)
        refresh_listbox()
        popup.destroy()

def add_macro():
    macro_popup("Add Macro")

def edit_macro():
    selected = listbox.get(tk.ACTIVE)
    logging.debug(f"Editing macro: {selected}")
    if selected:
        macro = macros[selected]
        macro_popup("Edit Macro", name=selected, command=macro["command"], action=macro["action"])

def delete_macro():
    selected = listbox.get(tk.ACTIVE)
    logging.debug(f"Deleting macro: {selected}")
    if selected:
        del macros[selected]
        save_macros(macros)
        refresh_listbox()

def refresh_listbox(search_query=''):
    global listbox
    if listbox:
        listbox.delete(0, tk.END)
        for key in macros.keys():
            if search_query.lower() in key.lower():
                listbox.insert(tk.END, key)
    logging.debug(f"Listbox contents after filtering: {[listbox.get(i) for i in range(listbox.size())]}")

def on_search_enter(event):
    if listbox.size() > 0:
        first_item = listbox.get(0)
        command = macros[first_item]["command"]
        send_to_app(command)

def on_enter(event):
    selected = listbox.get(tk.ACTIVE)
    logging.debug(f"Selected macro: {selected}")
    if selected:
        send_to_app(macros[selected]["command"])

def update_listbox(*args):
    search_query = search_var.get()
    refresh_listbox(search_query)

root = None
listbox = None
search_entry = None
current_keys = set()
stop_event = threading.Event()
ui_queue = queue.Queue()


def on_double_click(event):
    selected = listbox.get(listbox.curselection())
    if selected:
        send_to_app(macros[selected]["command"])

def on_button_click(action):
    if action == "Add":
        add_macro()
    elif action == "Edit":
        edit_macro()
    elif action == "Delete":
        delete_macro()

def create_and_show_window():
    global root, listbox, search_entry, search_var
    if root is None or not root.winfo_exists():
        root = tk.Tk()
        root.title("Macro Manager")

        window_width = 600
        window_height = 600
        center_window(root, window_width, window_height)
        root.resizable(True, True)

        # Apply a theme for better appearance
        style = ttk.Style()
        style.theme_use('clam')

        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        search_var = tk.StringVar()
        search_var.trace("w", update_listbox)
        search_entry = ttk.Entry(main_frame, textvariable=search_var, font=('Arial', 12))
        search_entry.pack(fill=tk.X, padx=5, pady=10)

        listbox = tk.Listbox(main_frame, font=('Arial', 12))
        listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        listbox.bind('<Double-1>', on_double_click)

        # Add key bindings for navigation
        search_entry.bind('<Down>', lambda event: move_focus_to_listbox(event))
        listbox.bind('<Up>', lambda event: move_focus_to_search(event))

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=10)

        button_width = 15
        button_style = ttk.Style()
        button_style.configure('TButton', font=('Arial', 12), padding=5)

        for text in ["Add", "Edit", "Delete"]:
            btn = ttk.Button(button_frame, text=text, width=button_width, 
                             command=lambda t=text: on_button_click(t))
            btn.pack(side=tk.LEFT, expand=True, padx=5)

        listbox.bind('<Return>', on_enter)
        search_entry.bind('<Return>', on_search_enter)

        # Enable keyboard navigation for buttons
        for child in button_frame.winfo_children():
            child.bind('<Return>', lambda event, b=child: b.invoke())

        root.protocol("WM_DELETE_WINDOW", on_closing)

        # Load macros and refresh listbox
        global macros
        macros = load_macros()
        refresh_listbox()

    root.deiconify()
    root.lift()
    root.focus_force()
    root.attributes('-topmost', True)
    root.update()
    root.attributes('-topmost', False)
    
    if search_entry:
        search_entry.focus_set()

def move_focus_to_listbox(event):
    if listbox.size() > 0:
        listbox.selection_clear(0, tk.END)
        listbox.selection_set(0)
        listbox.activate(0)
        listbox.focus_set()

def move_focus_to_search(event):
    if listbox.curselection() == (0,):
        search_entry.focus_set()
        search_entry.icursor(tk.END)
    else:
        listbox.selection_clear(0, tk.END)
        listbox.selection_set(0)
        listbox.activate(0)

def on_closing():
    global root
    root.withdraw()

current_keys = set()
stop_event = threading.Event()

def process_ui_events():
    try:
        while True:
            function = ui_queue.get_nowait()
            function()
            ui_queue.task_done()
    except queue.Empty:
        pass
    if not stop_event.is_set():
        root.after(100, process_ui_events)

def on_activate():
    logging.info("Hotkey detected, showing Macro Manager")
    ui_queue.put(create_and_show_window)

def on_press(key):
    global caps_lock_presses
    logging.debug(f"Key pressed: {key}")
    
    if key == keyboard.Key.caps_lock:
        caps_lock_presses.append(time.time())
        if check_triple_caps_lock():
            on_activate()

def on_release(key):
    if stop_event.is_set():
        return False

def check_hotkey():
    ctrl = keyboard.Key.ctrl_l in current_keys or keyboard.Key.ctrl_r in current_keys
    option_win = keyboard.Key.cmd in current_keys or keyboard.Key.alt_l in current_keys or keyboard.Key.alt_r in current_keys
    t_key = 't' in current_keys or 84 in current_keys  # 84 is the virtual key code for 'T'
    
    return ctrl and option_win and t_key

def listen_keyboard():
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()

if __name__ == "__main__":
    logging.info("Starting Macro Manager main execution")
    
    listener_thread = threading.Thread(target=listen_keyboard)
    listener_thread.daemon = True
    listener_thread.start()
    logging.info("Keyboard listener thread started")
    
    print("Macro Manager is running. Press Caps Lock quickly 3 times to open the manager, or Ctrl+C here to exit.")
    
    create_and_show_window()  # Create the initial window in the main thread
    root.after(100, process_ui_events)  # Start processing UI events
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt detected, exiting Macro Manager")
        print("\nStopping the Macro Manager...")
    finally:
        stop_event.set()
        logging.info("Cleaning up before exit")
        if root:
            root.quit()
    
    logging.info("Exiting Python script")