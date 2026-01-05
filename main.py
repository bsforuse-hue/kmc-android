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
        
        # בניית המסך הראשי - חלוקה באחוזים כדי שהכל יכנס
        self.layout = BoxLayout(orientation='vertical', padding=5, spacing=5)
        
        # 1. כותרת (10% גובה)
        self.layout.add_widget(Label(text="KMC Analyzer Pro", font_size='24sp', color=(0,1,0,1), size_hint_y=0.1))
        
        # 2. לוגים (50% גובה - הקטנתי כדי לפנות מקום)
        self.log_label = Label(text="Welcome. Click buttons below.", size_hint_y=None, markup=True)
        self.log_label.bind(texture_size=self.log_label.setter('size'))
        scroll = ScrollView(size_hint_y=0.5)
        scroll.add_widget(self.log_label)
        self.layout.add_widget(scroll)
        
        # 3. כפתור תיקון הרשאות (10% גובה)
        btn_fix = Button(text="FIX PERMISSIONS (Allow All)", size_hint_y=0.1, background_color=(0.8, 0, 0, 1))
        btn_fix.bind(on_press=self.open_settings_manual)
        self.layout.add_widget(btn_fix)
        
        # 4. כפתור בחירה (15% גובה)
        btn_browse = Button(text="OPEN FILE BROWSER / USB", size_hint_y=0.15, background_color=(1, 0.6, 0.2, 1))
        btn_browse.bind(on_press=self.show_load_popup)
        self.layout.add_widget(btn_browse)

        # 5. כפתורים תחתונים - שמירה ויציאה (15% גובה)
        bottom_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=0.15)
        
        btn_save = Button(text="SAVE LOG", background_color=(0, 0.8, 0, 1))
        btn_save.bind(on_press=self.save_log)
        
        btn_exit = Button(text="EXIT APP", background_color=(0.3, 0.3, 0.3, 1))
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

    def get_real_usb_path(self):
        # פונקציית הקסם למציאת ה-USB בלי לגשת ל-/storage האסור
        if platform != 'android':
            return None
            
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            context = PythonActivity.mActivity.getApplicationContext()
            # שימוש ב-API הרשמי לקבלת נתיבים
            files_dirs = context.getExternalFilesDirs(None)
            
            for f in files_dirs:
                if f is None: continue
                path = f.getAbsolutePath()
                # הנתיב נראה כמו: /storage/XXXX-XXXX/Android/data/...
                # אנחנו רוצים רק את ההתחלה
                if "emulated" not in path:
                    # זה כונן חיצוני! נחתוך את הנתיב כדי לקבל את השורש
                    parts = path.split("/")
                    if len(parts) > 2:
                        # מחזיר משהו כמו /storage/E65A-046E
                        usb_root = f"/{parts[1]}/{parts[2]}"
                        return usb_root
        except Exception as e:
            self.log(f"USB Detect Error: {e}", "ff0000")
        return None

    def show_load_popup(self, instance):
        content = BoxLayout(orientation='vertical', spacing=5)
        
        # כפתור חכם ל-USB
        btn_usb = Button(text="JUMP TO USB (Direct)", size_hint_y=0.15, background_color=(0, 0.5, 0.8, 1))
        btn_usb.bind(on_press=self.jump_to_usb)
        content.add_widget(btn_usb)

        # התחלה מתיקיית ההורדות הבטוחה
        start_path = "/storage/emulated/0/Download"
        if not os.path.exists(start_path): start_path = "/"

        # שינינו את ה-rootpath ל-None כדי לאפשר חופש תנועה, אבל נזהרים לא לעלות ל-/storage
        self.file_chooser = FileChooserListView(
            path=start_path, 
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
        
        self._popup = Popup(title="Browse Files", content=content, size_hint=(0.95, 0.95))
        self._popup.open()

    def jump_to_usb(self, instance):
        # במקום לנחש, אנחנו שואלים את המערכת
        usb_path = self.get_real_usb_path()
        
        if usb_path and os.path.exists(usb_path):
            self.log(f"USB Found: {usb_path}", "00ff00")
            try:
                # קפיצה ישירה לנתיב
                self.file_chooser.path = usb_path
                self.file_chooser._update_files()
            except Exception as e:
                 self.log(f"Access Error: {e}", "ff0000")
        else:
            self.log("USB not detected via API.", "ff0000")
            self.log("Try reconnecting USB.", "ffff00")

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
