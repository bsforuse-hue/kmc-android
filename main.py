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
        
        self.log_label = Label(text="Click 'FORCE DETECT USB'...", size_hint_y=None, markup=True)
        self.log_label.bind(texture_size=self.log_label.setter('size'))
        scroll = ScrollView(size_hint=(1, 0.65))
        scroll.add_widget(self.log_label)
        self.layout.add_widget(scroll)
        
        btn_fix = Button(text="FIX PERMISSIONS", size_hint=(1, 0.1), background_color=(1, 0, 0, 1))
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

    def show_load_popup(self, instance):
        content = BoxLayout(orientation='vertical', spacing=5)
        
        btn_usb = Button(text="FORCE DETECT USB", size_hint_y=0.1, background_color=(0, 0.5, 0.8, 1))
        btn_usb.bind(on_press=self.find_usb_via_linux_mounts)
        content.add_widget(btn_usb)

        # התחלה מוגדרת היטב
        start_path = "/storage/emulated/0/"
        
        # כאן אנחנו מגדירים rootpath רחב יותר כדי לאפשר תנועה
        self.file_chooser = FileChooserListView(
            path=start_path, 
            rootpath="/storage",  # זה השינוי הקריטי - מאפשר לראות הכל תחת storage
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
        
        self._popup = Popup(title="Choose Folder", content=content, size_hint=(0.95, 0.95))
        self._popup.open()

    def find_usb_via_linux_mounts(self, instance):
        self.log("Scanning mounts...", "cccccc")
        usb_found_path = None
        
        try:
            with open("/proc/mounts", "r") as f:
                lines = f.readlines()
            
            for line in lines:
                parts = line.split()
                if len(parts) < 2: continue
                path = parts[1]
                
                if "/mnt/media_rw" in path:
                    # המרה לנתיב storage שפתוח לקריאה
                    possible_storage_path = path.replace("/mnt/media_rw", "/storage")
                    
                    if os.path.exists(possible_storage_path):
                        usb_found_path = possible_storage_path
                        self.log(f"Found USB: {usb_found_path}", "00ff00")
                        break

            if usb_found_path:
                # טריק: שחרור הנעילה ורענון
                # אנחנו משנים את ה-rootpath לתיקיית ה-USB עצמה כדי להכריח את הרכיב להיכנס לשם
                self.file_chooser.rootpath = "/storage" 
                self.file_chooser.path = usb_found_path
                self.file_chooser._update_files()
                
                self.log(f"SUCCESS: Jumped to {usb_found_path}", "00ff00")
            else:
                self.log("No USB found via mounts.", "ff5555")

        except Exception as e:
            self.log(f"Error: {e}", "ff0000")

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
