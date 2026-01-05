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

class KMCAndroidApp(App):
    def build(self):
        self.check_permissions_startup()
        self.last_scanned_path = "/storage/emulated/0/Download"
        
        # מבנה ראשי: כותרת למעלה, כפתורים למטה, לוג באמצע
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # 1. כותרת (10% מהמסך)
        self.layout.add_widget(Label(text="KMC Analyzer Pro", font_size='24sp', color=(0,1,0,1), size_hint_y=0.1))
        
        # 2. לוגים (50% מהמסך - גמיש)
        self.log_label = Label(text="System Ready.\nClick 'DETECT USB (JAVA)' to start.", size_hint_y=None, markup=True)
        self.log_label.bind(texture_size=self.log_label.setter('size'))
        
        scroll = ScrollView(size_hint_y=0.5)
        scroll.add_widget(self.log_label)
        self.layout.add_widget(scroll)
        
        # 3. כפתור תיקון הרשאות (10%)
        btn_fix = Button(text="FIX PERMISSIONS", size_hint_y=0.1, background_color=(0.8, 0, 0, 1))
        btn_fix.bind(on_press=self.open_settings_manual)
        self.layout.add_widget(btn_fix)
        
        # 4. כפתור פתיחת הסייר / USB (15%)
        btn_browse = Button(text="OPEN BROWSER / USB", size_hint_y=0.15, background_color=(1, 0.6, 0.2, 1))
        btn_browse.bind(on_press=self.show_load_popup)
        self.layout.add_widget(btn_browse)

        # 5. כפתורים תחתונים - שמירה ויציאה (15%)
        bottom_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=0.15)
        
        btn_save = Button(text="SAVE LOG", background_color=(0, 0.8, 0, 1))
        btn_save.bind(on_press=self.save_log)
        
        btn_exit = Button(text="EXIT", background_color=(0.3, 0.3, 0.3, 1))
        btn_exit.bind(on_press=self.exit_app)
        
        bottom_layout.add_widget(btn_save)
        bottom_layout.add_widget(btn_exit)
        
        self.layout.add_widget(bottom_layout)
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
        
        # כפתור ה-USB החדש
        btn_usb = Button(text="DETECT USB (Official Java API)", size_hint_y=0.15, background_color=(0, 0.5, 0.8, 1))
        btn_usb.bind(on_press=self.find_usb_java_native)
        content.add_widget(btn_usb)

        # התחלה מתיקיית ההורדות
        start_path = "/storage/emulated/0/Download"
        if not os.path.exists(start_path): start_path = "/"

        self.file_chooser = FileChooserListView(
            path=start_path, 
            rootpath="/storage", 
            dirselect=True, 
            filters=['*.req', '*.rsp', '*']
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
        
        self._popup = Popup(title="File Browser", content=content, size_hint=(0.95, 0.95))
        self._popup.open()

    def find_usb_java_native(self, instance):
        self.log("Asking Android for Storage Volumes...", "cccccc")
        
        if platform != 'android':
            self.log("Not on Android!", "ff0000")
            return

        found_usb = False
        try:
            from jnius import autoclass, cast
            
            # גישה לשירות האחסון של אנדרואיד
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Context = autoclass('android.content.Context')
            StorageManager = autoclass('android.os.storage.StorageManager')
            
            context = PythonActivity.mActivity.getApplicationContext()
            storage_manager = cast(StorageManager, context.getSystemService(Context.STORAGE_SERVICE))
            
            # קבלת רשימת כל הכוננים (Volumes)
            storage_volumes = storage_manager.getStorageVolumes()
            
            for volume in storage_volumes:
                # בדיקה אם הכונן הוא "נשלף" (Removable) - כלומר USB או SD
                if volume.isRemovable():
                    # קבלת הנתיב (דורש API 30+ שיש לך)
                    directory = volume.getDirectory()
                    if directory:
                        path = directory.getAbsolutePath()
                        self.log(f"Found Removable: {path}", "00ff00")
                        
                        if os.path.exists(path):
                            self.file_chooser.path = path
                            self.file_chooser._update_files()
                            self.log("SUCCESS: USB Opened!", "00ff00")
                            found_usb = True
                            return # מצאנו, יוצאים

            if not found_usb:
                self.log("Android reported no removable drives.", "ff5555")
                self.log("Try reconnecting the USB.", "ffff00")

        except Exception as e:
            self.log(f"Java Error: {e}", "ff0000")
            # ניסיון אחרון למקרה שה-API נכשל
            self.find_usb_legacy_fallback()

    def find_usb_legacy_fallback(self):
        # תוכנית גיבוי: חיפוש בתיקיות האפליקציה החיצוניות
        self.log("Trying fallback method...", "cccccc")
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            context = PythonActivity.mActivity.getApplicationContext()
            files_dirs = context.getExternalFilesDirs(None)
            
            for f in files_dirs:
                if f is None: continue
                path = f.getAbsolutePath()
                if "emulated" not in path:
                    # זה חיצוני! בוא נחתוך את הנתיב לשורש
                    parts = path.split("/")
                    if len(parts) > 2:
                        usb_root = f"/{parts[1]}/{parts[2]}" # /storage/XXXX-XXXX
                        if os.path.exists(usb_root):
                             self.file_chooser.path = usb_root
                             self.file_chooser._update_files()
                             self.log(f"Fallback found: {usb_root}", "00ff00")
                             return
        except: pass
        self.log("Fallback failed too.", "ff0000")

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
