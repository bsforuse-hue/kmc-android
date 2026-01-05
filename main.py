import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.utils import platform
import os

MSG_TYPES = {0x01: "REPLACE_ALL", 0x03: "ADD_AUTH (KMAC)", 0x41: "RESPONSE"}

class KMCAndroidApp(App):
    def build(self):
        # בקשת הרשאות באנדרואיד (חשוב!)
        if platform == 'android':
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])

        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.layout.add_widget(Label(text="KMC Analyzer", font_size='24sp', color=(0,1,0,1)))
        
        self.log_label = Label(text="Ready to scan...", size_hint_y=None, markup=True)
        self.log_label.bind(texture_size=self.log_label.setter('size'))
        scroll = ScrollView(size_hint=(1, 0.8))
        scroll.add_widget(self.log_label)
        self.layout.add_widget(scroll)
        
        btn = Button(text="SCAN DOWNLOADS", size_hint=(1, 0.15), background_color=(0.2, 0.6, 1, 1))
        btn.bind(on_press=self.scan_files)
        self.layout.add_widget(btn)
        return self.layout

    def log(self, text, color="ffffff"):
        self.log_label.text += f"\n[color={color}]{text}[/color]"

    def scan_files(self, instance):
        self.log_label.text = "Scanning /storage/emulated/0/Download..."
        path = "/storage/emulated/0/Download"
        try:
            # בדיקה אם התיקייה קיימת בכלל
            if not os.path.exists(path):
                 self.log(f"Path not found: {path}", "ff0000")
                 return

            files = [f for f in os.listdir(path) if f.lower().endswith(('.req', '.rsp'))]
            if not files:
                self.log("No files found.", "ffff00")
                return
            
            for f_name in files:
                self.analyze(os.path.join(path, f_name), f_name)
        except Exception as e:
            self.log(f"Error: {e}", "ff0000")

    def analyze(self, filepath, filename):
        try:
            with open(filepath, 'rb') as f: data = f.read(64)
            if len(data) < 25: return
            
            m_type = data[24]
            info = "REQ"
            status = "Pending"
            
            if m_type == 0x41: # RSP
                nid = int.from_bytes(data[9:13][1:], 'big')
                info = f"RSP (NID {nid})"
                if len(data)>26: status = "Success" if data[26]==0 else f"Err {data[26]}"
            elif m_type == 0x03: # KMAC
                if len(data)>=64:
                    nid = int.from_bytes(data[61:64], 'big')
                    info = f"KMAC (NID {nid})"
            else:
                nid = int.from_bytes(data[5:9][1:], 'big')
                info = f"REQ (NID {nid})"
            
            color = "ff5555" if "Err" in status else "00ff00"
            self.log(f"{filename}\n{info} | {status}", color)
            self.log("- - -", "555555")
        except Exception as e:
            self.log(f"Read Error: {e}", "ff5555")

if __name__ == '__main__':
    KMCAndroidApp().run()
