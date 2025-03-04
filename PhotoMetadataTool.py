import os
import json
import piexif
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

# GUI 應用程式
class ExifEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("圖片 EXIF JSON 編輯器")
        self.root.geometry("600x650")  # 增加高度以適應圖片預覽
        
        self.image_path = None
        
        # 按鈕：選擇圖片
        tk.Button(root, text="選擇圖片", command=self.select_image).pack(pady=10)
        
        # 圖片預覽框架
        self.image_label = tk.Label(root)
        self.image_label.pack()
        
        # 標籤與輸入框
        tk.Label(root, text="店家名稱:").pack()
        self.store_name_entry = tk.Entry(root, width=50)
        self.store_name_entry.pack()
        
        tk.Label(root, text="描述:").pack()
        self.description_entry = tk.Entry(root, width=50)
        self.description_entry.pack()
        
        tk.Label(root, text="地點:").pack()
        self.location_entry = tk.Entry(root, width=50)
        self.location_entry.pack()
        

        
        
        # 按鈕：寫入 & 讀取 EXIF
        tk.Button(root, text="寫入 EXIF JSON", command=self.write_exif).pack(pady=5)
        tk.Button(root, text="讀取 EXIF JSON", command=self.read_exif).pack(pady=5)
    
    def select_image(self):
        """選擇圖片檔案並預覽，並自動讀取 EXIF"""
        file_path = filedialog.askopenfilename(filetypes=[("JPEG 圖片", "*.jpg;*.jpeg")])
        if file_path:
            self.image_path = file_path
            self.show_image_preview()
            self.read_exif()
            # messagebox.showinfo("成功", f"已選擇圖片: {file_path}")
    
    def show_image_preview(self):
        """顯示圖片預覽"""
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
        
        img = Image.open(self.image_path)
        img.save(self.image_path, exif=exif_bytes)
        # messagebox.showinfo("成功", "✅ Metadata 已寫入 EXIF！")
    


    
    def read_exif(self):
        """讀取 EXIF JSON"""
        if not self.image_path:
            return

        try:
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
            # messagebox.showwarning("警告", f"EXIF 讀取失敗或不存在: {e}")
            self.clear_entries()  # 清空輸入框

    def clear_entries(self):
        """清空輸入框"""
        self.store_name_entry.delete(0, tk.END)
        self.description_entry.delete(0, tk.END)
        self.location_entry.delete(0, tk.END)
        self.tags_entry.delete(0, tk.END)
       


# 啟動 GUI 應用程式
if __name__ == "__main__":
    root = tk.Tk()
    app = ExifEditorApp(root)
    root.mainloop()
