import os
import ssl
import json
import requests
import threading
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.clock import Clock
from kivy.utils import platform
from kivy.animation import Animation
from kivy.properties import BooleanProperty, StringProperty, NumericProperty, ListProperty
from kivy.factory import Factory
from kivy.core.window import Window

# --- НАСТРОЙКИ ---
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except: pass
os.environ['KIVY_GL_BACKEND'] = 'sdl2'
Window.softinput_mode = 'below_target'

# --- КАСТОМНАЯ КНОПКА МЕНЮ (УДАЛЕНИЕ ПРИ УДЕРЖАНИИ) ---
class HistoryItemBtn(ButtonBehavior, BoxLayout):
    title = StringProperty("")
    idx = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._long_press_event = None
        self._is_long_pressed = False

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._is_long_pressed = False
            # Если удерживать 2 секунды - сработает on_long_press
            self._long_press_event = Clock.schedule_once(self.on_long_press, 2.0)
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if self.collide_point(*touch.pos):
            if self._long_press_event:
                self._long_press_event.cancel()
                self._long_press_event = None
        return super().on_touch_up(touch)

    def on_long_press(self, dt):
        self._long_press_event = None
        self._is_long_pressed = True
        App.get_running_app().delete_chat(self.idx) # Вызываем удаление

    def on_release(self):
        # Если было долгое нажатие (удаление), не переключаем чат
        if self._is_long_pressed:
            self._is_long_pressed = False
            return
        App.get_running_app().switch_chat(self.idx)

# --- ШЕДЕВРОДИЗАЙН ---
KV = """
<HistoryItemBtn>:
    size_hint_y: None
    height: "50dp"
    padding: ["20dp", 0]
    canvas.before:
        Color:
            rgba: (1, 1, 1, 0.05) if self.state == 'down' else (0, 0, 0, 0)
        Rectangle:
            pos: self.pos
            size: self.size
    Label:
        text: root.title
        color: (1, 1, 1, 1)
        font_size: "16sp"
        shorten: True
        text_size: self.width, None
        valign: 'middle'
        halign: 'left'

<MessageBubble@BoxLayout>:
    text: ""
    is_user: False
    size_hint_y: None
    height: self.minimum_height
    padding: ["15dp", "10dp"]
    pos_hint: {'right': 0.95} if self.is_user else {'x': 0.05}
    size_hint_x: None
    width: min(dp(300), lbl.texture_size[0] + dp(30))
    canvas.before:
        Color:
            rgba: (0, 0.37, 1, 1) if self.is_user else (0.12, 0.13, 0.16, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(15), dp(15), dp(4), dp(15)] if self.is_user else [dp(15), dp(15), dp(15), dp(4)]
    Label:
        id: lbl
        text: root.text
        size_hint: None, None
        size: self.texture_size
        text_size: dp(270), None
        color: (1, 1, 1, 1)

FloatLayout:
    BoxLayout:
        id: main_content
        orientation: 'vertical'
        canvas.before:
            Color:
                rgba: (0.04, 0.05, 0.05, 1)
            Rectangle:
                pos: self.pos
                size: self.size

        BoxLayout:
            size_hint_y: None
            height: "60dp"
            padding: ["10dp", 0]
            canvas.before:
                Color:
                    rgba: (0.07, 0.08, 0.1, 1)
                Rectangle:
                    pos: self.pos
                    size: self.size
            
            Button:
                text: "≡"
                size_hint_x: None
                width: "50dp"
                background_color: (0, 0, 0, 0)
                font_size: "30sp"
                color: (1, 1, 1, 1)
                on_release: app.toggle_menu()
            
            Label:
                text: "ATLAS.AI"
                bold: True
                font_size: "20sp"
                color: (1, 1, 1, 1)
            
            Widget:
                size_hint_x: None
                width: "50dp"

        ScrollView:
            id: chat_scroll
            BoxLayout:
                id: chat_container
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                padding: "15dp"
                spacing: "15dp"

        BoxLayout:
            size_hint_y: None
            height: "80dp"
            padding: ["15dp", "15dp"]
            spacing: "10dp"
            canvas.before:
                Color:
                    rgba: (0.07, 0.08, 0.1, 1)
                Rectangle:
                    pos: self.pos
                    size: self.size

            TextInput:
                id: user_input
                hint_text: "+ СПРОСИТЬ У ATLAS"
                hint_text_color: (0.5, 0.5, 0.5, 1)
                multiline: False
                background_normal: ""
                background_color: (0.12, 0.13, 0.16, 1)
                foreground_color: (1, 1, 1, 1)
                padding: ["15dp", "15dp"]
                on_text_validate: app.send_message()
                canvas.after:
                    Color:
                        rgba: (0, 0, 0, 0)
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [dp(20)]

            Button:
                text: "›"
                size_hint_x: None
                width: "50dp"
                background_normal: ""
                background_color: (0, 0.37, 1, 1)
                color: (1, 1, 1, 1)
                font_size: "30sp"
                on_release: app.send_message()
                canvas.before:
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [dp(25)]

    BoxLayout:
        id: side_menu
        orientation: 'vertical'
        size_hint: None, 1
        width: "280dp"
        x: -self.width
        canvas.before:
            Color:
                rgba: (0.07, 0.08, 0.1, 1)
            Rectangle:
                pos: self.pos
                size: self.size
            Color:
                rgba: (0, 0, 0, 0.5)
            Line:
                points: [self.right, self.y, self.right, self.top]
                width: 2
        
        BoxLayout:
            size_hint_y: None
            height: "80dp"
            padding: ["20dp", "20dp", "20dp", "10dp"]
            Button:
                text: "Новый чат"
                background_normal: ""
                background_color: (0, 0, 0, 0)
                color: (1, 1, 1, 1)
                font_size: "18sp"
                bold: True
                halign: "left"
                text_size: self.size
                valign: "middle"
                on_release: app.start_new_chat()

        Widget:
            size_hint_y: None
            height: "1dp"
            canvas.before:
                Color:
                    rgba: (1, 1, 1, 0.1)
                Rectangle:
                    pos: self.pos
                    size: self.size

        ScrollView:
            BoxLayout:
                id: history_list
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                padding: ["0dp", "10dp"]
                spacing: "5dp"

        BoxLayout:
            size_hint_y: None
            height: "70dp"
            padding: ["20dp", "10dp"]
            canvas.before:
                Color:
                    rgba: (1, 1, 1, 0.05)
                Rectangle:
                    pos: self.pos
                    size: self.size
            Label:
                text: "Озвучка ИИ"
                color: (1, 1, 1, 1)
                halign: "left"
                text_size: self.size
                valign: "middle"
            Switch:
                active: app.voice_enabled
                on_active: app.voice_enabled = self.active
                size_hint_x: None
                width: "50dp"
"""

class AtlasApp(App):
    voice_enabled = BooleanProperty(False)
    history = ListProperty([])
    current_chat_idx = -1

    def build(self):
        return Builder.load_string(KV)

    def on_start(self):
        if platform == 'android':
            try:
                from android.permissions import request_permissions, Permission
                request_permissions([Permission.INTERNET, Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_EXTERNAL_STORAGE])
            except: pass
        self.load_history()
        self.start_new_chat()

    def speak_text(self, text):
        try:
            from plyer import tts
            tts.speak(text)
        except Exception as e:
            print("Ошибка голоса:", e)

    def toggle_menu(self):
        menu = self.root.ids.side_menu
        if menu.x < 0: Animation(x=0, duration=0.25, t='out_quad').start(menu)
        else: Animation(x=-menu.width, duration=0.25, t='out_quad').start(menu)

    def start_new_chat(self):
        self.root.ids.chat_container.clear_widgets()
        self.current_chat_idx = -1
        self.add_bubble("Я Atlas AI. Чем могу помочь?", is_user=False)
        if self.root.ids.side_menu.x == 0: self.toggle_menu()

    def switch_chat(self, idx):
        self.root.ids.chat_container.clear_widgets()
        self.current_chat_idx = idx
        for msg in self.history[idx]['messages']:
            self.add_bubble(msg['content'], is_user=(msg['role'] == 'user'))
        if self.root.ids.side_menu.x == 0: self.toggle_menu()

    # --- УДАЛЕНИЕ ЧАТА ---
    def delete_chat(self, idx):
        if 0 <= idx < len(self.history):
            del self.history[idx]
            self.save_history()
            
            # Переназначаем индекс, если удалили текущий или предыдущий чат
            if self.current_chat_idx == idx:
                self.start_new_chat()
            elif self.current_chat_idx > idx:
                self.current_chat_idx -= 1
                
            self.update_menu()

    def send_message(self):
        txt = self.root.ids.user_input.text.strip()
        if not txt: return
        self.root.ids.user_input.text = ""
        self.add_bubble(txt, True)
        
        is_first_message = False
        if self.current_chat_idx == -1:
            self.history.append({'title': 'Новая тема...', 'messages': []})
            self.current_chat_idx = len(self.history) - 1
            is_first_message = True
            
        self.history[self.current_chat_idx]['messages'].append({'role': 'user', 'content': txt})
        threading.Thread(target=self.call_ai, args=(txt, is_first_message), daemon=True).start()

    def call_ai(self, text, need_title):
        api_key = "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"
        system_prompt = "Ты Atlas AI, обычный ИИ с памятью. Твой создатель — команда N.E.S из 142 школы. Отвечай кратко."
        try:
            res = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": text}]},
                verify=False, timeout=15
            )
            ans = res.json()['choices'][0]['message']['content']
            
            Clock.schedule_once(lambda dt: self.add_bubble(ans, False))
            self.history[self.current_chat_idx]['messages'].append({'role': 'assistant', 'content': ans})
            self.save_history()

            # БЕЗОПАСНЫЙ ВЫЗОВ ГОЛОСА НА ОСНОВНОМ ПОТОКЕ (БОЛЬШЕ НЕ ВЫЛЕТИТ)
            if self.voice_enabled:
                Clock.schedule_once(lambda dt: self.speak_text(ans))

            if need_title:
                res_title = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": f"Сделай заголовок из 1-2 слов для: {text}"}]},
                    verify=False, timeout=10
                )
                self.history[self.current_chat_idx]['title'] = res_title.json()['choices'][0]['message']['content'].strip().replace('"', '')
                self.save_history()
                Clock.schedule_once(lambda dt: self.update_menu())
        except Exception as e:
            Clock.schedule_once(lambda dt: self.add_bubble(f"Ошибка сети: {e}", False))

    def add_bubble(self, text, is_user):
        b = Factory.MessageBubble()
        b.text = text
        b.is_user = is_user
        self.root.ids.chat_container.add_widget(b)
        Clock.schedule_once(lambda dt: self.root.ids.chat_scroll.scroll_to(b), 0.1)

    def load_history(self):
        path = os.path.join(self.user_data_dir, "atlas_history.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
                self.update_menu()
            except: pass

    def save_history(self):
        path = os.path.join(self.user_data_dir, "atlas_history.json")
        try:
            with open(path, 'w', encoding='utf-8') as f: json.dump(self.history, f, ensure_ascii=False)
        except: pass

    def update_menu(self):
        lst = self.root.ids.history_list
        lst.clear_widgets()
        for i, chat in reversed(list(enumerate(self.history))):
            # Теперь кнопки создаются через наш класс
            btn = HistoryItemBtn(title=chat['title'], idx=i)
            lst.add_widget(btn)

if __name__ == '__main__':
    AtlasApp().run()
