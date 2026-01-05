import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.utils import platform
import os

MSG_TYPES = {0x01: "REPLACE_ALL", 0x03: "ADD_AUTH (KMAC)", 0x41: "RESPONSE"}

class KMCAndroidApp(App):
    def build(self):
        # בקשת הרשאות באנדרואיד
        if platform == 'android':
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])

        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.layout.add_widget(Label(text="KMC Analyzer", font_size='24sp', color=(0,1,0,1)))
        
        # אזור הלוגים
        self.log_label = Label(text="Select a folder to scan...", size_hint_y=None, markup=True)
        self.log_label.bind(texture_size=self.log_label.setter('size'))
        scroll = ScrollView(size_hint=(1, 0.8))
        scroll.add_widget(self.log_label)
        self.layout.add_widget(scroll)
        
        # כפתור בחירת תיקייה
        btn_browse = Button(text="CHOOSE FOLDER", size_hint=(1, 0.15), background_color=(1, 0.6, 0.2, 1))
        btn_browse.bind(on_press=self.show_load_popup)
        self.layout.add_widget(btn_browse)

        return self.layout

    def log(self, text, color="ffffff"):
        self.log_label.text += f"\n[color={color}]{text}[/color]"

    def show_load_popup(self, instance):
        # יצירת תוכן החלון הקופץ
        content = BoxLayout(orientation='vertical')
        
        # רכיב בחירת הקבצים
        # ברירת מחדל: התיקייה הראשית של המשתמש
        start_path = "/storage/emulated/0/"
        if not os.path.exists(start_path):
            start_path = "/" # גיבוי למקרה שאנחנו לא באנדרואיד

        self.file_chooser = FileChooserListView(
            path=start_path,
            dirselect=True, # מאפשר לבחור תיקייה
            filters=['*.req', '*.rsp', '*'] # מציג הכל כדי שנוכל לראות תיקיות
        )
        
        content.add_widget(self.file_chooser)
        
        # כפתורי אישור וביטול בחלון
        btn_layout = BoxLayout(size_hint_y=0.2, spacing=5)
        btn_select = Button(text="Select This Folder", background_color=(0, 1, 0, 1))
        btn_select.bind(on_press=self.load_folder)
        
        btn_cancel = Button(text="Cancel", background_color=(1, 0, 0, 1))
        btn_cancel.bind(on_press=self.dismiss_popup)
        
        btn_layout.add_widget(btn_select)
        btn_layout.add_widget(btn_cancel)
        content.add_widget(btn_layout)
        
        self._popup = Popup(title="Choose Folder", content=content, size_hint=(0.9, 0.9))
        self._popup.open()

    def dismiss_popup(self, instance):
        self._popup.dismiss()

    def load_folder(self, instance):
        # קבלת הנתיב שנבחר
        path = self.file_chooser.path
        self.dismiss_popup(instance)
        self.scan_files(path)

    def scan_files(self, path):
        self.log_label.text = f"Scanning: {path}..."
        try:
            if not os.path.exists(path):
                 self.log(f"Path not found!", "ff0000")
                 return

            # סריקת כל הקבצים בתיקייה שנבחרה
            files = [f for f in os.listdir(path) if f.lower().endswith(('.req', '.rsp'))]
            
            if not files:
                self.log("No .req or .rsp files found here.", "ffff00")
                return
            
            for f_name in files:
                self.analyze(os.path.join(path, f_name), f_name)
                
        except Exception as e:
            self.log(f"Access Error: {e}", "ff0000")
            self.log("Note: Android restricts access to some system folders.", "ffff00")

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
