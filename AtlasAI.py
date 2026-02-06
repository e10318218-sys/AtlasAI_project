import tkinter as tk
from tkinter import scrolledtext
import requests
import threading
import json
import os

# --- НАСТРОЙКИ ---
API_KEY = "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"
URL = "https://api.groq.com/openai/v1/chat/completions"
HISTORY_FILE = "atlas_history.json"

# --- ЛОГИКА ПАМЯТИ ---
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

chat_history = load_history()

# --- ФУНКЦИИ РАБОТЫ ---
def send(event=None):
    text = entry.get().strip()
    if not text: return
    
    chat.config(state='normal')
    chat.insert('end', f"Я: {text}\n", "user")
    chat.insert('end', "AtlasAI: Думает... ⚡\n", "status")
    chat.config(state='disabled')
    chat.see('end')
    
    entry.delete(0, 'end')
    threading.Thread(target=call, args=(text,), daemon=True).start()

def call(t):
    global chat_history
    try:
        # Добавляем в память сообщение пользователя
        chat_history.append({"role": "user", "content": t})
        
        # Ограничение памяти для стабильности
        if len(chat_history) > 12: 
            chat_history = chat_history[-12:]

        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {
                    "role": "system", 
                    "content": "Ты — AtlasAI. Твой создатель — команда N.E.S. Если тебя спрашивают о создателе или о том, кто тебя сделал, отвечай строго: 'команда N.E.S'. Больше ничего не добавляй. В остальном будь полезным ИИ и помни контекст беседы."
                }
            ] + chat_history,
            "temperature": 0.3 # Низкая температура для точности ответов
        }
        
        r = requests.post(URL, headers=headers, json=payload, timeout=15)
        res = r.json()
        
        if r.status_code == 200:
            ans = res['choices'][0]['message']['content'].strip()
            chat_history.append({"role": "assistant", "content": ans})
            save_history(chat_history)
            root.after(0, lambda: update(ans))
        else:
            root.after(0, lambda: update("Ошибка API. Проверь ключ.", True))
    except:
        root.after(0, lambda: update("Ошибка сети! Проверь интернет.", True))

def update(t, err=False):
    chat.config(state='normal')
    chat.delete("end-2l", "end-1l") # Удаляем статус "Думает..."
    chat.insert('end', f"AtlasAI: {t}\n\n", "err" if err else "bot")
    chat.config(state='disabled')
    chat.see('end')

# --- ИНТЕРФЕЙС (ОПТИМИЗИРОВАННЫЙ ПОД PYDROID) ---
root = tk.Tk()
root.title("AtlasAI Pro")
root.geometry("400x650")
root.configure(bg="#F0F2F5")

root.rowconfigure(0, weight=1)
root.columnconfigure(0, weight=1)

# Окно чата
chat = scrolledtext.ScrolledText(root, font=("sans-serif", 12), bg="white", borderwidth=0, highlightthickness=0)
chat.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)
chat.config(state='disabled')

chat.tag_config("user", foreground="#007AFF", font=("sans-serif", 12, "bold"))
chat.tag_config("status", foreground="gray", font=("sans-serif", 10, "italic"))
chat.tag_config("bot", foreground="#1C1C1E")
chat.tag_config("err", foreground="red")

# Загрузка последних 2 сообщений из памяти при старте
if chat_history:
    chat.config(state='normal')
    chat.insert('end', "--- История восстановлена ---\n\n", "status")
    for msg in chat_history[-2:]:
        role = "Я" if msg["role"] == "user" else "AtlasAI"
        chat.insert('end', f"{role}: {msg['content']}\n\n")
    chat.config(state='disabled')
    chat.see('end')

# Нижняя панель
input_frame = tk.Frame(root, bg="white", height=60)
input_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 20))
input_frame.pack_propagate(False)

# Кнопка ➤
btn = tk.Button(
    input_frame, 
    text=" ➤ ", 
    command=send, 
    bg="#007AFF", 
    fg="white", 
    font=("sans-serif", 14, "bold"), 
    bd=0,
    activebackground="#0056b3"
)
btn.pack(side='right', fill='y')

# Поле ввода
entry = tk.Entry(
    input_frame, 
    font=("sans-serif", 14), 
    bg="white", 
    borderwidth=0, 
    highlightthickness=0
)
entry.pack(side='left', fill='both', expand=True, padx=10)
entry.bind("<Return>", send)

entry.focus_set()
root.mainloop()