import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.utils import platform
from kivy.clock import Clock
import os
import shutil
import time

# ייבוא ספריות אנדרואיד (רק אם רץ על אנדרואיד)
if platform == 'android':
    from android import activity
    from jnius import autoclass, cast
    
    Intent = autoclass('android.content.Intent')
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    Context = autoclass('android.content.Context')
    Uri = autoclass('android.net.Uri')

class KMCAndroidApp(App):
    def build(self):
        self.check_permissions_startup()
        
        # --- עיצוב המסך: חלוקה נוקשה כדי שכלום לא יעלם ---
        self.root = BoxLayout(orientation='vertical', padding=5, spacing=5)
        
        # 1. אזור עליון: כותרת + לוגים (65% גובה)
        top_section = BoxLayout(orientation='vertical', size_hint_y=0.65)
        top_section.add_widget(Label(text="KMC Analyzer Pro", font_size='22sp', color=(0,1,0,1), size_hint_y=0.15))
        
        self.log_label = Label(text="Welcome.\nChoose an option below.", size_hint_y=None, markup=True, font_size='16sp')
        self.log_label.bind(texture_size=self.log_label.setter('size'))
        
        scroll = ScrollView(size_hint_y=0.85)
        scroll.add_widget(self.log_label)
        top_section.add_widget(scroll)
        self.root.add_widget(top_section)
        
        # 2. אזור תחתון: כפתורים (35% גובה) - קבוע, לא נגלל
        bottom_section = GridLayout(cols=1, spacing=5, size_hint_y=0.35)
        
        # כפתור אדום: תיקון הרשאות
        btn_fix = Button(text="1. FIX PERMISSIONS", background_color=(0.8, 0, 0, 1))
        btn_fix.bind(on_press=self.open_settings_manual)
        bottom_section.add_widget(btn_fix)
        
        # כפתור כחול: יבוא מהמערכת (הפתרון ל-USB)
        btn_import = Button(text="2. IMPORT FROM USB (System Picker)", background_color=(0, 0.5, 1, 1))
        btn_import.bind(on_press=self.open_native_picker)
        bottom_section.add_widget(btn_import)

        # כפתור כתום: סריקת הורדות (גיבוי)
        btn_scan_dl = Button(text="3. SCAN 'DOWNLOAD' FOLDER", background_color=(1, 0.6, 0, 1))
        btn_scan_dl.bind(on_press=self.scan_downloads)
        bottom_section.add_widget(btn_scan_dl)
        
        # שורה תחתונה: שמירה ויציאה
        footer = BoxLayout(spacing=5)
        btn_save = Button(text="SAVE LOG", background_color=(0, 0.8, 0, 1))
        btn_save.bind(on_press=self.save_log)
        btn_exit = Button(text="EXIT", background_color=(0.4, 0.4, 0.4, 1))
        btn_exit.bind(on_press=self.exit_app)
        footer.add_widget(btn_save)
        footer.add_widget(btn_exit)
        
        bottom_section.add_widget(footer)
        self.root.add_widget(bottom_section)
        
        # רישום לקבלת קבצים מהמערכת
        if platform == 'android':
            activity.bind(on_activity_result=self.on_activity_result)
            
        return self.root

    def log(self, text, color="ffffff"):
        self.log_label.text += f"\n[color={color}]{text}[/color]"

    # --- לוגיקה 1: יבוא קבצים דרך המערכת (הפתרון ל-USB) ---
    def open_native_picker(self, instance):
        if platform == 'android':
            self.log("Opening System File Picker...", "cccccc")
            try:
                intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
                intent.addCategory(Intent.CATEGORY_OPENABLE)
                intent.setType("*/*") # אפשר לשנות לסוג ספציפי
                intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, True)
                
                # קוד קסם שמפעיל את הבחירה
                PythonActivity.mActivity.startActivityForResult(intent, 0x123)
            except Exception as e:
                self.log(f"Error launching picker: {e}", "ff0000")
        else:
            self.log("Not on Android", "ff0000")

    def on_activity_result(self, request_code, result_code, intent):
        if request_code != 0x123: return
        
        if result_code != -1: # RESULT_OK
            self.log("Selection canceled.", "ffff00")
            return
            
        self.log("Processing files...", "00ff00")
        
        # תיקייה זמנית לעבודה
        dest_folder = "/storage/emulated/0/Download/KMC_Import"
        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder)
            
        # ניקוי ישן
        for f in os.listdir(dest_folder):
            try: os.remove(os.path.join(dest_folder, f))
            except: pass

        try:
            context = PythonActivity.mActivity.getApplicationContext()
            resolver = context.getContentResolver()
            
            uris = []
            if intent.getData():
                uris.append(intent.getData())
            elif intent.getClipData():
                clip = intent.getClipData()
                for i in range(clip.getItemCount()):
                    uris.append(clip.getItemAt(i).getUri())
            
            count = 0
            for uri in uris:
                # קריאת הקובץ מה-USB דרך ה-Stream
                input_stream = resolver.openInputStream(uri)
                
                # ניסיון לחלץ שם (מסובך, ניתן שם גנרי אם צריך)
                filename = f"file_{count}.req" 
                
                # שמירה לתיקייה שלנו
                with open(os.path.join(dest_folder, filename), 'wb') as f:
                    # קריאת גושים
                    buffer = bytearray(4096)
                    while True:
                        read = input_stream.read(buffer)
                        if read == -1: break
                        f.write(buffer[:read])
                
                input_stream.close()
                count += 1
            
            self.log(f"Imported {count} files to:", "00ff00")
            self.log(f"{dest_folder}", "cccccc")
            self.scan_folder_path(dest_folder)
            
        except Exception as e:
            self.log(f"Import Error: {e}", "ff0000")

    # --- לוגיקה 2: סריקה רגילה ---
    def scan_downloads(self, instance):
        path = "/storage/emulated/0/Download"
        self.scan_folder_path(path)

    def scan_folder_path(self, path):
        self.log(f"Analyzing: {path}", "cccccc")
        if not os.path.exists(path):
            self.log("Folder not found!", "ff0000")
            return
            
        files = [f for f in os.listdir(path) if f.lower().endswith(('.req', '.rsp'))]
        if not files:
            # אם אין קבצים עם סיומת, נסרוק את הכל (אולי השם השתנה ביבוא)
            files = os.listdir(path)
        
        if not files:
            self.log("No files found.", "ffff00")
            return

        for f_name in files:
            self.analyze(os.path.join(path, f_name), f_name)

    # --- שאר הפונקציות (ניתוח, הרשאות, שמירה) ---
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

    def check_permissions_startup(self):
        if platform == 'android':
            try:
                from android.permissions import request_permissions, Permission
                request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE, Permission.MANAGE_EXTERNAL_STORAGE])
            except: pass

    def open_settings_manual(self, instance):
        if platform == 'android':
            try:
                intent = Intent('android.settings.MANAGE_APP_ALL_FILES_ACCESS_PERMISSION')
                uri = Uri.parse("package:" + PythonActivity.mActivity.getPackageName())
                intent.setData(uri)
                PythonActivity.mActivity.startActivity(intent)
            except: pass

    def save_log(self, instance):
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = f"KMC_Log_{timestamp}.txt"
        target_path = f"/storage/emulated/0/Download/{filename}"
        clean_text = self.log_label.text.replace('[color=ffffff]', '').replace('[/color]', '').replace('[color=00ff00]', '').replace('[color=ff0000]', '').replace('[color=cccccc]', '').replace('[color=ffff00]', '')
        try:
            with open(target_path, 'w', encoding='utf-8') as f: f.write(clean_text)
            self.log(f"\nSaved Log to Downloads!", "00ff00")
        except Exception as e: self.log(f"Save Failed: {e}", "ff0000")

    def exit_app(self, instance):
        App.get_running_app().stop()

if __name__ == '__main__':
    KMCAndroidApp().run()
