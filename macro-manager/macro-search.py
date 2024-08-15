import tkinter as tk
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
    logging.info("Refreshing listbox...")
    listbox.delete(0, tk.END)
    for key in macros.keys():
        if search_query.lower() in key.lower():
            listbox.insert(tk.END, key)
    logging.debug(f"Listbox contents: {list(macros.keys())}")

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

def create_and_show_window():
    global root, listbox, macros, search_var
    if root is not None:
        root.deiconify()
        center_window(root, 600, 600)
        root.lift()  # Lift the window to the top of the stacking order
        root.focus_force()  # Force focus on the window
        return

    root = tk.Tk()
    root.title("Macro Manager")

    window_width = 600
    window_height = 600
    center_window(root, window_width, window_height)
    root.resizable(True, True)

    # Set window to be topmost
    root.attributes('-topmost', True)
    root.update()

    search_var = StringVar()
    search_var.trace("w", update_listbox)
    search_entry = Entry(root, textvariable=search_var)
    search_entry.pack(fill=tk.X, padx=5, pady=5)
    search_entry.focus_set()

    search_entry.bind('<Return>', on_search_enter)

    listbox = tk.Listbox(root)
    listbox.pack(fill=tk.BOTH, expand=True)

    add_button = tk.Button(root, text="Add", command=add_macro)
    add_button.pack(side=tk.LEFT)

    edit_button = tk.Button(root, text="Edit", command=edit_macro)
    edit_button.pack(side=tk.LEFT)

    delete_button = tk.Button(root, text="Delete", command=delete_macro)
    delete_button.pack(side=tk.LEFT)

    listbox.bind('<Return>', on_enter)

    macros = load_macros()
    refresh_listbox()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # After a short delay, remove the topmost attribute
    root.after(100, lambda: root.attributes('-topmost', False))
    
    root.mainloop()

def on_closing():
    global root
    root.withdraw()

def on_activate():
    logging.info("Hotkey detected, showing Macro Manager")
    create_and_show_window()

def on_press(key):
    global current_keys
    logging.debug(f"Key pressed: {key}")
    
    if isinstance(key, keyboard.Key):
        current_keys.add(key)
    elif isinstance(key, keyboard.KeyCode):
        if key.char:
            current_keys.add(key.char.lower())
        else:
            current_keys.add(key.vk)
    
    if check_hotkey():
        on_activate()

def on_release(key):
    global current_keys
    logging.debug(f"Key released: {key}")
    
    if isinstance(key, keyboard.Key):
        current_keys.discard(key)
    elif isinstance(key, keyboard.KeyCode):
        if key.char:
            current_keys.discard(key.char.lower())
        else:
            current_keys.discard(key.vk)

def check_hotkey():
    ctrl = keyboard.Key.ctrl_l in current_keys or keyboard.Key.ctrl_r in current_keys
    alt = keyboard.Key.alt_l in current_keys or keyboard.Key.alt_r in current_keys
    t_key = 't' in current_keys or 84 in current_keys  # 84 is the virtual key code for 'T'
    
    hotkey_pressed = ctrl and alt and t_key
    if hotkey_pressed:
        logging.info(f"Hotkey detected. Current keys: {current_keys}")
    
    return hotkey_pressed

def listen_keyboard():
    global running
    logging.info("Starting keyboard listener")
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        while running:
            if not listener.running:
                logging.warning("Listener stopped running")
                break
            time.sleep(0.1)
    logging.info("Keyboard listener stopped")

if __name__ == "__main__":
    logging.info("Starting Macro Manager main execution")
    
    listener_thread = threading.Thread(target=listen_keyboard)
    listener_thread.start()
    logging.info("Keyboard listener thread started")
    
    print("Macro Manager is running. Use Ctrl+Alt+T to open the manager, or Ctrl+C here to exit.")
    
    try:
        while running:
            time.sleep(0.1)
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt detected, exiting Macro Manager")
        print("\nExiting Macro Manager...")
    finally:
        logging.info("Cleaning up before exit")
        running = False
        if root:
            root.quit()
        listener_thread.join()

    logging.info("Exiting Python script")