import json
import os
import requests
import threading
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.clock import Clock

# --- НАСТРОЙКИ (Те же самые) ---
API_KEY = "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"
URL = "https://api.groq.com/openai/v1/chat/completions"
HISTORY_FILE = "atlas_history.json"

class AtlasApp(App):
    def build(self):
        self.chat_history = self.load_history()
        
        # Главный контейнер
        self.main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Область чата (Scroll)
        self.scroll = ScrollView(size_hint=(1, 0.8))
        self.chat_label = Label(
            text="[color=808080]AtlasAI готов к работе...[/color]\n\n",
            markup=True,
            size_hint_y=None,
            halign='left',
            valign='top',
            text_size=(None, None)
        )
        self.chat_label.bind(texture_size=self.chat_label.setter('size'))
        self.scroll.add_widget(self.chat_label)
        
        # Поле ввода и кнопка
        input_area = BoxLayout(size_hint=(1, 0.1), spacing=5)
        self.entry = TextInput(multiline=False, hint_text="Введите сообщение...")
        btn = Button(text="➤", size_hint=(0.2, 1), background_color=(0, 0.5, 1, 1))
        btn.bind(on_release=self.send_message)
        
        input_area.add_widget(self.entry)
        input_area.add_widget(btn)
        
        self.main_layout.add_widget(self.scroll)
        self.main_layout.add_widget(input_area)
        
        return self.main_layout

    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: return []
        return []

    def save_history(self):
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.chat_history, f, ensure_ascii=False, indent=2)

    def send_message(self, instance):
        text = self.entry.text.strip()
        if not text: return
        
        self.chat_label.text += f"[b][color=007AFF]Я:[/color][/b] {text}\n"
        self.entry.text = ""
        
        # Запуск запроса в отдельном потоке, чтобы экран не завис
        threading.Thread(target=self.call_api, args=(text,), daemon=True).start()

    def call_api(self, text):
        try:
            self.chat_history.append({"role": "user", "content": text})
            if len(self.chat_history) > 12: self.chat_history = self.chat_history[-12:]

            headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "system", "content": "Ты — AtlasAI. Создатель — команда N.E.S."}] + self.chat_history,
                "temperature": 0.3
            }
            
            r = requests.post(URL, headers=headers, json=payload, timeout=15)
            if r.status_code == 200:
                ans = r.json()['choices'][0]['message']['content'].strip()
                self.chat_history.append({"role": "assistant", "content": ans})
                self.save_history()
                Clock.schedule_once(lambda dt: self.update_ui(ans))
            else:
                Clock.schedule_once(lambda dt: self.update_ui("Ошибка API", True))
        except:
            Clock.schedule_once(lambda dt: self.update_ui("Ошибка сети", True))

    def update_ui(self, text, is_error=False):
        color = "ff0000" if is_error else "ffffff"
        self.chat_label.text += f"[b][color=10bb10]AtlasAI:[/color][/b] [color={color}]{text}[/color]\n\n"

if __name__ == "__main__":
    AtlasApp().run()
