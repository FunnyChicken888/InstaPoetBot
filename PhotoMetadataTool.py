import os
import json
import piexif
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import pyheif

def convert_heic_to_jpeg(heic_path):
    heif_file = pyheif.read(heic_path)
    image = Image.frombytes(
        heif_file.mode, 
        heif_file.size, 
        heif_file.data,
        "raw",
        heif_file.mode,
        heif_file.stride,
    )
    return image

class ExifEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("圖片 EXIF JSON 編輯器")
        self.root.geometry("900x650")  # 加寬視窗以容納列表
        
        self.image_path = None
        self.folder_path = None
        self.images_info = []
        
        # 左側面板 - 圖片列表
        left_panel = ttk.Frame(root)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        # 按鈕：選擇資料夾
        ttk.Button(left_panel, text="選擇資料夾", command=self.select_folder).pack(pady=5)
        
        # 圖片列表（Treeview）
        self.tree = ttk.Treeview(left_panel, columns=("filename", "status"), show="headings", height=20)
        self.tree.heading("filename", text="檔案名稱")
        self.tree.heading("status", text="Metadata狀態")
        self.tree.column("filename", width=150)
        self.tree.column("status", width=100)
        self.tree.pack(pady=5)
        self.tree.bind("<<TreeviewSelect>>", self.on_select_image)
        
        # 右側面板 - 編輯區域
        right_panel = ttk.Frame(root)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 按鈕：選擇單一圖片
        ttk.Button(right_panel, text="選擇圖片", command=self.select_image).pack(pady=5)
        
        # 圖片預覽框架
        self.image_label = tk.Label(right_panel)
        self.image_label.pack()
        
        # 標籤與輸入框
        ttk.Label(right_panel, text="店家名稱:").pack()
        self.store_name_entry = ttk.Entry(right_panel, width=50)
        self.store_name_entry.pack()
        
        ttk.Label(right_panel, text="描述:").pack()
        self.description_entry = ttk.Entry(right_panel, width=50)
        self.description_entry.pack()
        
        ttk.Label(right_panel, text="地點:").pack()
        self.location_entry = ttk.Entry(right_panel, width=50)
        self.location_entry.pack()
        
        # 按鈕：寫入 & 讀取 EXIF
        ttk.Button(right_panel, text="寫入 EXIF JSON", command=self.write_exif).pack(pady=5)
        ttk.Button(right_panel, text="讀取 EXIF JSON", command=self.read_exif).pack(pady=5)

    def select_folder(self):
        """選擇資料夾並列出所有圖片"""
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.folder_path = folder_path
            self.scan_folder()
    
    def scan_folder(self):
        """掃描資料夾中的所有圖片並檢查metadata狀態"""
        # 清空現有列表
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 掃描資料夾
        for filename in os.listdir(self.folder_path):
            if filename.lower().endswith(('.jpg', '.jpeg', '.heic', '.HEIC')):
                file_path = os.path.join(self.folder_path, filename)
                has_metadata = self.check_metadata(file_path)
                status = "✅ 已設定" if has_metadata else "❌ 未設定"
                self.tree.insert("", tk.END, values=(filename, status))
    
    def check_metadata(self, image_path):
        """檢查圖片是否有metadata"""
        try:
            img = Image.open(image_path)
            exif_dict = piexif.load(img.info.get("exif", b""))
            json_data = exif_dict["0th"].get(piexif.ImageIFD.ImageDescription, b"").decode("utf-8")
            metadata = json.loads(json_data)
            return bool(metadata.get("store_name") or metadata.get("description") or metadata.get("location"))
        except:
            return False
    
    def on_select_image(self, event):
        """當在列表中選擇圖片時"""
        selection = self.tree.selection()
        if selection:
            filename = self.tree.item(selection[0])["values"][0]
            self.image_path = os.path.join(self.folder_path, filename)
            self.show_image_preview()
            self.read_exif()
    
    def select_image(self):
        """選擇單一圖片檔案並預覽"""
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg;*.jpeg;*.heic;*.HEIC")])
        if file_path:
            self.image_path = file_path
            self.show_image_preview()
            self.read_exif()
    
    def show_image_preview(self):
        """顯示圖片預覽"""
        if self.image_path.lower().endswith('.heic'):
            img = convert_heic_to_jpeg(self.image_path)
        else:
            img = Image.open(self.image_path)
        img.thumbnail((300, 300))  # 讓圖片維持比例縮放到適合大小
        img_tk = ImageTk.PhotoImage(img)
        self.image_label.config(image=img_tk)
        self.image_label.image = img_tk
    
    def write_exif(self):
        """寫入 JSON 至 EXIF"""
        if not self.image_path:
            messagebox.showerror("錯誤", "請先選擇圖片！")
            return
        
        metadata = {
            "store_name": self.store_name_entry.get().strip(),
            "description": self.description_entry.get().strip(),
            "location": self.location_entry.get().strip(),
        }
        
        json_data = json.dumps(metadata, ensure_ascii=False)
        exif_dict = {"0th": {}}
        exif_dict["0th"][piexif.ImageIFD.ImageDescription] = json_data.encode("utf-8")
        exif_bytes = piexif.dump(exif_dict)
        
        if self.image_path.lower().endswith('.heic'):
            img = convert_heic_to_jpeg(self.image_path)
            jpeg_path = self.image_path.rsplit('.', 1)[0] + '.jpg'
            img.save(jpeg_path, exif=exif_bytes)
            self.image_path = jpeg_path  # 更新圖片路徑
        else:
            img = Image.open(self.image_path)
            img.save(self.image_path, exif=exif_bytes)
        
        # 更新列表中的狀態
        if self.folder_path:
            self.scan_folder()
    
    def read_exif(self):
        """讀取 EXIF JSON"""
        if not self.image_path:
            return

        try:
            if self.image_path.lower().endswith('.heic'):
                img = convert_heic_to_jpeg(self.image_path)
            else:
                img = Image.open(self.image_path)
            exif_dict = piexif.load(img.info.get("exif", b""))
            json_data = exif_dict["0th"].get(piexif.ImageIFD.ImageDescription, b"").decode("utf-8")
            metadata = json.loads(json_data)

            self.store_name_entry.delete(0, tk.END)
            self.store_name_entry.insert(0, metadata.get("store_name", ""))

            self.description_entry.delete(0, tk.END)
            self.description_entry.insert(0, metadata.get("description", ""))

            self.location_entry.delete(0, tk.END)
            self.location_entry.insert(0, metadata.get("location", ""))

        except Exception as e:
            self.clear_entries()

    def clear_entries(self):
        """清空輸入框"""
        self.store_name_entry.delete(0, tk.END)
        self.description_entry.delete(0, tk.END)
        self.location_entry.delete(0, tk.END)

# 啟動 GUI 應用程式
if __name__ == "__main__":
    root = tk.Tk()
    app = ExifEditorApp(root)
    root.mainloop()