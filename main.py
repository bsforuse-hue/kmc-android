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
        self.check_permissions_startup()
        
        self.last_scanned_path = "/storage/emulated/0/Download"
        
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.layout.add_widget(Label(text="KMC Analyzer Pro", font_size='24sp', color=(0,1,0,1)))
        
        self.log_label = Label(text="Click 'AUTO-DETECT USB' to find drives", size_hint_y=None, markup=True)
        self.log_label.bind(texture_size=self.log_label.setter('size'))
        scroll = ScrollView(size_hint=(1, 0.65))
        scroll.add_widget(self.log_label)
        self.layout.add_widget(scroll)
        
        # כפתור תיקון הרשאות
        btn_fix = Button(text="FIX PERMISSIONS (If Error 13)", size_hint=(1, 0.1), background_color=(1, 0, 0, 1))
        btn_fix.bind(on_press=self.open_settings_manual)
        self.layout.add_widget(btn_fix)
        
        btn_browse = Button(text="CHOOSE FOLDER / USB", size_hint=(1, 0.12), background_color=(1, 0.6, 0.2, 1))
        btn_browse.bind(on_press=self.show_load_popup)
        self.layout.add_widget(btn_browse)

        bottom_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, 0.12))
        btn_save = Button(text="SAVE LOG", background_color=(0, 0.8, 0, 1))
        btn_save.bind(on_press=self.save_log)
        btn_exit = Button(text="EXIT", background_color=(0.5, 0.5, 0.5, 1))
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
            except Exception as e:
                self.log(f"Error opening settings: {e}", "ff0000")

    def log(self, text, color="ffffff"):
        self.log_label.text += f"\n[color={color}]{text}[/color]"

    def save_log(self, instance):
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = f"KMC_Log_{timestamp}.txt"
        
        # מנסה לשמור קודם כל בתיקייה שנסרקה
        target_path = os.path.join(self.last_scanned_path, filename)
        clean_text = re.sub(r'\[.*?\]', '', self.log_label.text)

        try:
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(clean_text)
            self.log(f"\nSaved to: {target_path}", "00ff00")
        except:
            # גיבוי לתיקיית ההורדות
            backup = f"/storage/emulated/0/Download/{filename}"
            try:
                with open(backup, 'w', encoding='utf-8') as f: f.write(clean_text)
                self.log(f"Saved to backup: {backup}", "ffff00")
            except Exception as e:
                self.log(f"Save Failed: {e}", "ff0000")

    def exit_app(self, instance):
        App.get_running_app().stop()

    def show_load_popup(self, instance):
        content = BoxLayout(orientation='vertical', spacing=5)
        
        # כפתור הזיהוי החכם
        btn_usb = Button(text="AUTO-DETECT USB (Java API)", size_hint_y=0.1, background_color=(0, 0.5, 0.8, 1))
        btn_usb.bind(on_press=self.find_usb_via_android_api)
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

    def find_usb_via_android_api(self, instance):
        # שיטה חסינת-אש למציאת נתיבים דרך ג'אווה
        if platform != 'android':
            self.log("Not on Android", "ff0000")
            return

        try:
            from jnius import autoclass, cast
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Context = autoclass('android.content.Context')
            context = PythonActivity.mActivity.getApplicationContext()
            
            # מבקש מאנדרואיד את כל נתיבי האחסון הזמינים
            files_dirs = context.getExternalFilesDirs(None)
            
            found_usb = False
            
            for file_dir in files_dirs:
                if file_dir is None: continue
                
                # ממיר את אובייקט הג'אווה למחרוזת פייתון
                path_str = file_dir.getAbsolutePath()
                
                # הנתיב חוזר בצורה כזו:
                # /storage/12AB-34CD/Android/data/org.kmc.../files
                # אנחנו רוצים לחתוך הכל אחרי ה-UUID של הכונן
                
                if "emulated" in path_str:
                    continue # זה הזיכרון הפנימי, מדלגים
                
                # מנסים למצוא את השורש של הכונן
                # בדרך כלל הפורמט הוא /storage/XXXX-XXXX
                parts = path_str.split("/")
                if len(parts) > 2:
                    usb_root = f"/{parts[1]}/{parts[2]}" # אמור לתת /storage/1234-5678
                    
                    self.log(f"USB DETECTED: {usb_root}", "00ff00")
                    self.file_chooser.path = usb_root
                    self.file_chooser._update_files()
                    found_usb = True
                    break
            
            if not found_usb:
                self.log("Android says: No USB mounted.", "ffff00")
                
        except Exception as e:
            self.log(f"Java API Error: {e}", "ff0000")

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
                self.log(f"READ DENIED. Try 'FIX PERMISSIONS'", "ff0000")
                return

            files = [f for f in os.listdir(path) if f.lower().endswith(('.req', '.rsp'))]
            if not files:
                self.log("No .req/.rsp files found.", "ffff00")
                return
            
            for f_name in files:
                self.analyze(os.path.join(path, f_name), f_name)
                
        except Exception as e:
            self.log(f"Scan Error: {e}", "ff0000")

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
