from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import json
import piexif
from PIL import Image
from werkzeug.utils import secure_filename
import io

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/api/upload', methods=['POST'])
def upload_file():
    print("=== 開始處理上傳請求 ===")
    if 'file' not in request.files:
        print("錯誤：請求中沒有檔案")
        return jsonify({'error': '沒有檔案'}), 400
    
    file = request.files['file']
    print(f"收到檔案：{file.filename}")
    
    if file.filename == '':
        print("錯誤：檔案名稱為空")
        return jsonify({'error': '沒有選擇檔案'}), 400
    
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        print(f"儲存檔案到：{filepath}")
        file.save(filepath)
        
        try:
            metadata = read_metadata(filepath)
            print(f"讀取到的 metadata：{metadata}")
            return jsonify({
                'filename': filename,
                'metadata': metadata
            })
        except Exception as e:
            print(f"處理檔案時發生錯誤：{str(e)}")
            return jsonify({'error': str(e)}), 500

@app.route('/api/save', methods=['POST'])
def save_metadata():
    data = request.json
    filename = data.get('filename')
    metadata = data.get('metadata')
    
    if not filename or not metadata:
        return jsonify({'error': '缺少必要參數'}), 400
    
    filepath = os.path.join(UPLOAD_FOLDER, secure_filename(filename))
    
    try:
        # 讀取圖片
        img = Image.open(filepath)
        
        # 準備metadata
        json_data = json.dumps(metadata, ensure_ascii=False)
        exif_dict = {"0th": {}}
        exif_dict["0th"][piexif.ImageIFD.ImageDescription] = json_data.encode("utf-8")
        exif_bytes = piexif.dump(exif_dict)
        
        # 建立暫存檔案
        output = io.BytesIO()
        img.save(output, format='JPEG', exif=exif_bytes)
        output.seek(0)
        
        return send_file(
            output,
            mimetype='image/jpeg',
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/scan', methods=['POST'])
def scan_folder():
    print("=== 開始掃描資料夾 ===")
    print(f"請求內容：{request.json}")
    
    folder_path = request.json.get('path')
    print(f"掃描資料夾路徑：{folder_path}")
    
    if not folder_path:
        print("錯誤：未提供資料夾路徑")
        return jsonify({'error': '無效的資料夾路徑'}), 400
        
    if not os.path.exists(folder_path):
        print(f"錯誤：資料夾不存在：{folder_path}")
        return jsonify({'error': '無效的資料夾路徑'}), 400
    
    print(f"資料夾存在，開始掃描")
    results = []
    try:
        files = os.listdir(folder_path)
        print(f"資料夾中的檔案：{files}")
        
        for filename in files:
            if filename.lower().endswith(('.jpg', '.jpeg')):
                filepath = os.path.join(folder_path, filename)
                print(f"處理圖片：{filepath}")
                try:
                    metadata = read_metadata(filepath)
                    print(f"圖片 {filename} 的 metadata：{metadata}")
                    results.append({
                        'filename': filename,
                        'hasMetadata': bool(metadata),
                        'metadata': metadata
                    })
                except Exception as e:
                    print(f"處理圖片 {filename} 時發生錯誤：{str(e)}")
                    results.append({
                        'filename': filename,
                        'hasMetadata': False,
                        'metadata': None
                    })
    except Exception as e:
        print(f"掃描資料夾時發生錯誤：{str(e)}")
        return jsonify({'error': f'掃描資料夾時發生錯誤：{str(e)}'}), 500
    
    print(f"掃描完成，找到 {len(results)} 個圖片")
    return jsonify(results)

def read_metadata(filepath):
    print(f"=== 讀取檔案 metadata：{filepath} ===")
    try:
        img = Image.open(filepath)
        print("成功打開圖片")
        
        exif = img.info.get("exif", b"")
        print(f"EXIF 資料存在：{'是' if exif else '否'}")
        
        if not exif:
            print("沒有 EXIF 資料")
            return None
            
        exif_dict = piexif.load(exif)
        print("成功載入 EXIF 字典")
        
        if "0th" not in exif_dict or piexif.ImageIFD.ImageDescription not in exif_dict["0th"]:
            print("找不到 ImageDescription")
            return None
            
        json_data = exif_dict["0th"][piexif.ImageIFD.ImageDescription].decode("utf-8")
        print(f"JSON 資料：{json_data}")
        
        metadata = json.loads(json_data)
        print(f"解析後的 metadata：{metadata}")
        return metadata
    except Exception as e:
        print(f"讀取 metadata 時發生錯誤：{str(e)}")
        return None

if __name__ == '__main__':
    app.run(debug=True)
