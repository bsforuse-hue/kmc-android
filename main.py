import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.utils import platform
from kivy.metrics import dp
import os
import re
import time

class KMCAndroidApp(App):
    def build(self):
        self.check_permissions_startup()
        self.last_scanned_path = "/storage/emulated/0/Download"
        
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        self.layout.add_widget(Label(text="KMC Analyzer Pro", font_size='24sp', color=(0,1,0,1), size_hint_y=None, height=dp(50)))
        
        self.log_label = Label(text="Ready.\nClick 'DETECT USB' to start.", size_hint_y=None, markup=True)
        self.log_label.bind(texture_size=self.log_label.setter('size'))
        
        scroll = ScrollView(size_hint_y=1)
        scroll.add_widget(self.log_label)
        self.layout.add_widget(scroll)
        
        btn_fix = Button(text="FIX PERMISSIONS", size_hint_y=None, height=dp(60), background_color=(0.8, 0, 0, 1))
        btn_fix.bind(on_press=self.open_settings_manual)
        self.layout.add_widget(btn_fix)
        
        btn_browse = Button(text="OPEN BROWSER / DETECT USB", size_hint_y=None, height=dp(80), background_color=(1, 0.6, 0.2, 1))
        btn_browse.bind(on_press=self.show_load_popup)
        self.layout.add_widget(btn_browse)

        bottom_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=dp(60))
        btn_save = Button(text="SAVE LOG", background_color=(0, 0.8, 0, 1))
        btn_save.bind(on_press=self.save_log)
        btn_exit = Button(text="EXIT", background_color=(0.3, 0.3, 0.3, 1))
        btn_exit.bind(on_press=self.exit_app)
        
        bottom_layout.add_widget(btn_save)
        bottom_layout.add_widget(btn_exit)
        return self.layout

    def check_permissions_startup(self):
        if platform == 'android':
            try:
                from jnius import autoclass
                from android.permissions import request_permissions, Permission
                request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE, Permission.MANAGE_EXTERNAL_STORAGE])
            except: pass

    def show_load_popup(self, instance):
        content = BoxLayout(orientation='vertical', spacing=5)
        
        # הכפתור החדש שמפעיל את הטריק
        btn_usb = Button(text="DETECT USB (Private App Path)", size_hint_y=None, height=dp(60), background_color=(0, 0.5, 0.8, 1))
        btn_usb.bind(on_press=self.find_usb_via_app_folder)
        content.add_widget(btn_usb)

        start_path = "/storage/emulated/0/Download"
        if not os.path.exists(start_path): start_path = "/"

        self.file_chooser = FileChooserListView(
            path=start_path, 
            rootpath="/storage", 
            dirselect=True, 
            filters=['*.req', '*.rsp', '*']
        )
        content.add_widget(self.file_chooser)
        
        btn_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=5)
        btn_select = Button(text="Scan Folder", background_color=(0, 1, 0, 1))
        btn_select.bind(on_press=self.load_folder)
        btn_cancel = Button(text="Cancel", background_color=(0.5, 0.5, 0.5, 1))
        btn_cancel.bind(on_press=self.dismiss_popup)
        
        btn_layout.add_widget(btn_select)
        btn_layout.add_widget(btn_cancel)
        content.add_widget(btn_layout)
        
        self._popup = Popup(title="File Browser", content=content, size_hint=(0.95, 0.95))
        self._popup.open()

    def find_usb_via_app_folder(self, instance):
        self.log("Asking for App External Dirs...", "cccccc")
        
        if platform != 'android':
            self.log("Not on Android!", "ff0000")
            return

        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            context = PythonActivity.mActivity.getApplicationContext()
            
            # מבקש מאנדרואיד: תביא לי את כל התיקיות ששייכות לי (פנימי וחיצוני)
            # זה מחזיר רשימה של נתיבים "בטוחים" שאנדרואיד יצר עבורנו
            external_files_dirs = context.getExternalFilesDirs(None)
            
            usb_found = False
            
            for f in external_files_dirs:
                if f is None: continue
                
                # המרת אובייקט Java למחרוזת Python
                path = f.getAbsolutePath()
                
                # נתיב פנימי נראה ככה: /storage/emulated/0/Android/data/...
                # נתיב חיצוני נראה ככה: /storage/E65A-046E/Android/data/...
                
                if "emulated" not in path:
                    self.log(f"Found Safe Path: {path}", "cccccc")
                    
                    # ניתוח הנתיב כדי למצוא את השורש
                    # אנחנו מפרקים לפי '/' ולוקחים את החלקים הראשונים
                    parts = path.split("/")
                    # parts[0] = ""
                    # parts[1] = "storage"
                    # parts[2] = "E65A-046E" (ה-ID של הכונן!)
                    
                    if len(parts) > 2:
                        usb_root = f"/{parts[1]}/{parts[2]}" # בונים מחדש: /storage/E65A-046E
                        
                        self.log(f"Derived Root: {usb_root}", "00ff00")
                        
                        if os.path.exists(usb_root):
                            self.file_chooser.path = usb_root
                            self.file_chooser._update_files()
                            self.log("SUCCESS! Jumped to USB.", "00ff00")
                            usb_found = True
                            return

            if not usb_found:
                self.log("No external app folder found.", "ff5555")
                self.log("Try: 1. Reconnect USB. 2. Restart App.", "ffff00")

        except Exception as e:
            self.log(f"Error: {e}", "ff0000")

    def open_settings_manual(self, instance):
        if platform == 'android':
            try:
                from jnius import autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                Intent = autoclass('android.content.Intent')
                Settings = autoclass('android.provider.Settings')
                Uri = autoclass('android.net.Uri')
                intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
                uri = Uri.parse("package:" + PythonActivity.mActivity.getPackageName())
                intent.setData(uri)
                PythonActivity.mActivity.startActivity(intent)
            except: pass

    def log(self, text, color="ffffff"):
        self.log_label.text += f"\n[color={color}]{text}[/color]"

    def save_log(self, instance):
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = f"KMC_Log_{timestamp}.txt"
        target_path = os.path.join(self.last_scanned_path, filename)
        clean_text = re.sub(r'\[.*?\]', '', self.log_label.text)
        try:
            with open(target_path, 'w', encoding='utf-8') as f: f.write(clean_text)
            self.log(f"\nSaved to: {target_path}", "00ff00")
        except:
            backup = f"/storage/emulated/0/Download/{filename}"
            try:
                with open(backup, 'w', encoding='utf-8') as f: f.write(clean_text)
                self.log(f"Saved to backup: {backup}", "ffff00")
            except Exception as e: self.log(f"Save Failed: {e}", "ff0000")

    def exit_app(self, instance):
        App.get_running_app().stop()

    def dismiss_popup(self, instance):
        self._popup.dismiss()

    def load_folder(self, instance):
        path = self.file_chooser.path
        self.dismiss_popup(instance)
        self.last_scanned_path = path
        self.scan_files(path)

    def scan_files(self, path):
        self.log_label.text = f"Scanning: {path}..."
        try:
            if not os.access(path, os.R_OK):
                self.log(f"READ DENIED.", "ff0000")
                return

            files = [f for f in os.listdir(path) if f.lower().endswith(('.req', '.rsp'))]
            if not files:
                self.log("No .req/.rsp files found.", "ffff00")
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
            info = "REQ"; status = "Pending"
            if m_type == 0x41: 
                nid = int.from_bytes(data[9:13][1:], 'big')
                info = f"RSP (NID {nid})"
                if len(data)>26: status = "Success" if data[26]==0 else f"Err {data[26]}"
            elif m_type == 0x03:
                if len(data)>=64:
                    nid = int.from_bytes(data[61:64], 'big')
                    info = f"KMAC (NID {nid})"
            else:
                nid = int.from_bytes(data[5:9][1:], 'big')
                info = f"REQ (NID {nid})"
            color = "ff5555" if "Err" in status else "00ff00"
            self.log(f"{filename}\n{info} | {status}", color)
            self.log("- - -", "555555")
        except: pass

if __name__ == '__main__':
    KMCAndroidApp().run()
