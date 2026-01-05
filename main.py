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
import re
import time

MSG_TYPES = {0x01: "REPLACE_ALL", 0x03: "ADD_AUTH (KMAC)", 0x41: "RESPONSE"}

class KMCAndroidApp(App):
    def build(self):
        # הפעלה מיידית של בקשת ההרשאות
        self.check_permissions()
        
        self.last_scanned_path = "/storage/emulated/0/Download"
        
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.layout.add_widget(Label(text="KMC Analyzer Pro", font_size='24sp', color=(0,1,0,1)))
        
        self.log_label = Label(text="1. Check Settings -> All Files Access = ON\n2. Ensure USB is FAT32\n3. Click CHOOSE FOLDER -> Go to USB", size_hint_y=None, markup=True)
        self.log_label.bind(texture_size=self.log_label.setter('size'))
        scroll = ScrollView(size_hint=(1, 0.75))
        scroll.add_widget(self.log_label)
        self.layout.add_widget(scroll)
        
        btn_browse = Button(text="CHOOSE FOLDER / USB", size_hint=(1, 0.12), background_color=(1, 0.6, 0.2, 1))
        btn_browse.bind(on_press=self.show_load_popup)
        self.layout.add_widget(btn_browse)

        bottom_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, 0.12))
        
        btn_save = Button(text="SAVE LOG", background_color=(0, 0.8, 0, 1))
        btn_save.bind(on_press=self.save_log)
        
        btn_exit = Button(text="EXIT", background_color=(1, 0, 0, 1))
        btn_exit.bind(on_press=self.exit_app)
        
        bottom_layout.add_widget(btn_save)
        bottom_layout.add_widget(btn_exit)
        self.layout.add_widget(bottom_layout)
        return self.layout

    def check_permissions(self):
        if platform == 'android':
            try:
                from jnius import autoclass
                from android.permissions import request_permissions, Permission
                
                # שלב 1: הרשאות רגילות
                request_permissions([
                    Permission.READ_EXTERNAL_STORAGE, 
                    Permission.WRITE_EXTERNAL_STORAGE,
                    Permission.MANAGE_EXTERNAL_STORAGE
                ])
                
                # שלב 2: בדיקת הרשאת מנהל (All Files Access)
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                Environment = autoclass('android.os.Environment')
                Intent = autoclass('android.content.Intent')
                Settings = autoclass('android.provider.Settings')
                Uri = autoclass('android.net.Uri')
                
                # האם יש לנו אישור מנהל?
                has_permission = Environment.isExternalStorageManager()
                print(f"DEBUG: Has Manage External Storage? {has_permission}")
                
                if not has_permission:
                    # ניסיון לפתוח ישירות את המסך לאפליקציה שלנו
                    try:
                        intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
                        uri = Uri.parse("package:" + PythonActivity.mActivity.getPackageName())
                        intent.setData(uri)
                        PythonActivity.mActivity.startActivity(intent)
                    except Exception as e:
                        print(f"DEBUG: Error opening specific settings: {e}")
                        # אם נכשל, פתח את הרשימה הכללית
                        intent = Intent(Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION)
                        PythonActivity.mActivity.startActivity(intent)
                        
            except Exception as e:
                print(f"DEBUG: Permission Critical Error: {e}")

    def log(self, text, color="ffffff"):
        self.log_label.text += f"\n[color={color}]{text}[/color]"

    def save_log(self, instance):
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = f"KMC_Log_{timestamp}.txt"
        
        if os.path.exists(self.last_scanned_path) and os.access(self.last_scanned_path, os.W_OK):
            save_path = os.path.join(self.last_scanned_path, filename)
        else:
            save_path = f"/storage/emulated/0/Download/{filename}"
        
        try:
            clean_text = re.sub(r'\[.*?\]', '', self.log_label.text)
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(clean_text)
            self.log(f"\nLog Saved:\n{save_path}", "00ff00")
        except Exception as e:
            self.log(f"\nSave Failed: {e}", "ff0000")
            # ניסיון גיבוי
            try:
                backup = f"/storage/emulated/0/Download/{filename}"
                with open(backup, 'w', encoding='utf-8') as f:
                    f.write(clean_text)
                self.log(f"Saved to Backup:\n{backup}", "ffff00")
            except: pass

    def exit_app(self, instance):
        App.get_running_app().stop()

    def show_load_popup(self, instance):
        content = BoxLayout(orientation='vertical', spacing=5)
        btn_usb = Button(text="Go to USB / Drives Root", size_hint_y=0.1, background_color=(0, 0.5, 0.8, 1))
        btn_usb.bind(on_press=self.goto_drives_root)
        content.add_widget(btn_usb)

        start_path = "/storage/emulated/0/"
        if not os.path.exists(start_path): start_path = "/"

        self.file_chooser = FileChooserListView(
            path=start_path, rootpath="/storage", dirselect=True, filters=['*.req', '*.rsp', '*']
        )
        content.add_widget(self.file_chooser)
        
        btn_layout = BoxLayout(size_hint_y=0.15, spacing=5)
        btn_select = Button(text="Scan This Folder", background_color=(0, 1, 0, 1))
        btn_select.bind(on_press=self.load_folder)
        btn_cancel = Button(text="Cancel", background_color=(0.5, 0.5, 0.5, 1))
        btn_cancel.bind(on_press=self.dismiss_popup)
        
        btn_layout.add_widget(btn_select)
        btn_layout.add_widget(btn_cancel)
        content.add_widget(btn_layout)
        
        self._popup = Popup(title="Choose Folder", content=content, size_hint=(0.95, 0.95))
        self._popup.open()

    def goto_drives_root(self, instance):
        target_path = "/storage"
        self.log(f"Checking {target_path}...", "cccccc")
        try:
            drives = os.listdir(target_path)
            self.log(f"Found: {drives}", "cccccc")
            self.file_chooser.path = target_path
            self.file_chooser._update_files()
        except PermissionError:
            self.log("PERMISSION DENIED on /storage. Check Settings!", "ff0000")
        except Exception as e:
            self.log(f"Error: {e}", "ff0000")
            if os.path.exists("/mnt/media_rw"):
                self.file_chooser.path = "/mnt/media_rw"

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
            # בדיקת הרשאות קריאה לפני ניסיון סריקה
            if not os.access(path, os.R_OK):
                self.log(f"NO READ PERMISSION for:\n{path}", "ff0000")
                return

            files = [f for f in os.listdir(path) if f.lower().endswith(('.req', '.rsp'))]
            if not files:
                self.log("No .req/.rsp files found here.", "ffff00")
                return
            
            for f_name in files:
                self.analyze(os.path.join(path, f_name), f_name)
                
        except PermissionError:
             self.log("PERMISSION DENIED (Error 13).\nVerify FAT32 USB & App Settings.", "ff0000")
        except Exception as e:
            self.log(f"Error: {e}", "ff0000")

    def analyze(self, filepath, filename):
        try:
            with open(filepath, 'rb') as f: data = f.read(64)
            if len(data) < 25: return
            
            m_type = data[24]
            info = "REQ"; status = "Pending"
            
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
        except: pass

if __name__ == '__main__':
    KMCAndroidApp().run()
