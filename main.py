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
        self.check_permissions()
        
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.layout.add_widget(Label(text="KMC Analyzer Pro", font_size='24sp', color=(0,1,0,1)))
        
        self.log_label = Label(text="Select a folder to scan...", size_hint_y=None, markup=True)
        self.log_label.bind(texture_size=self.log_label.setter('size'))
        scroll = ScrollView(size_hint=(1, 0.8))
        scroll.add_widget(self.log_label)
        self.layout.add_widget(scroll)
        
        btn_browse = Button(text="CHOOSE FOLDER", size_hint=(1, 0.15), background_color=(1, 0.6, 0.2, 1))
        btn_browse.bind(on_press=self.show_load_popup)
        self.layout.add_widget(btn_browse)

        return self.layout

    def check_permissions(self):
        """
        פונקציה זו בודקת אם יש לנו גישה מלאה לקבצים.
        אם לא - היא פותחת את מסך ההגדרות של אנדרואיד כדי שהמשתמש יאשר.
        """
        if platform == 'android':
            from jnius import autoclass
            from android.permissions import request_permissions, Permission
            
            # בקשת הרשאות רגילות
            request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])
            
            # בדיקה וטיפול בהרשאת 'גישה לכל הקבצים' (Android 11+)
            try:
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                Environment = autoclass('android.os.Environment')
                Intent = autoclass('android.content.Intent')
                Settings = autoclass('android.provider.Settings')
                Uri = autoclass('android.net.Uri')
                
                # אם אין הרשאת מנהל, פתח את מסך ההגדרות
                if not Environment.isExternalStorageManager():
                    intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
                    uri = Uri.parse("package:" + PythonActivity.mActivity.getPackageName())
                    intent.setData(uri)
                    PythonActivity.mActivity.startActivity(intent)
            except Exception as e:
                print(f"Permission Error: {e}")

    def log(self, text, color="ffffff"):
        self.log_label.text += f"\n[color={color}]{text}[/color]"

    def show_load_popup(self, instance):
        content = BoxLayout(orientation='vertical')
        
        # התחלה מתיקיית הבית של המכשיר
        start_path = "/storage/emulated/0/"
        if not os.path.exists(start_path):
            start_path = "/"

        self.file_chooser = FileChooserListView(
            path=start_path,
            dirselect=True,
            filters=['*.req', '*.rsp', '*'] # מציג הכל כדי לאפשר ניווט בתיקיות
        )
        
        content.add_widget(self.file_chooser)
        
        btn_layout = BoxLayout(size_hint_y=0.2, spacing=5)
        btn_select = Button(text="Scan This Folder", background_color=(0, 1, 0, 1))
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
        path = self.file_chooser.path
        self.dismiss_popup(instance)
        self.scan_files(path)

    def scan_files(self, path):
        self.log_label.text = f"Scanning: {path}..."
        try:
            if not os.path.exists(path):
                 self.log(f"Path not found!", "ff0000")
                 return

            # בדיקה מה המערכת רואה בתיקייה (לצורך דיבוג)
            all_files = os.listdir(path)
            self.log(f"Total files seen: {len(all_files)}", "cccccc")
            
            files = [f for f in all_files if f.lower().endswith(('.req', '.rsp'))]
            
            if not files:
                self.log("No .req or .rsp files found visible to the app.", "ffff00")
                return
            
            for f_name in files:
                self.analyze(os.path.join(path, f_name), f_name)
                
        except Exception as e:
            self.log(f"Access Error: {e}", "ff0000")
            self.log("Did you grant 'All Files Access'?", "ffff00")

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
