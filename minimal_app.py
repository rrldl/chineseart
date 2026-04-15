import os
import json
from flask import Flask, request, jsonify, send_from_directory
from image_search_app_zhao import ImageSearchService
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 创建Flask应用
app = Flask(__name__)

# 初始化图像搜索服务
image_search_service = None

def init_image_search():
    """初始化图像搜索服务"""
    global image_search_service
    try:
        image_search_service = ImageSearchService(
            neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
            neo4j_password=os.getenv("NEO4J_PASSWORD", "Zyr123456")
        )
        print("✓ 图像搜索服务初始化成功")
        return True
    except Exception as e:
        print(f"✗ 图像搜索服务初始化失败: {e}")
        return False

# 初始化服务
init_image_search()

@app.route("/", methods=["GET"])
def index():
    """首页"""
    return "以图搜图功能测试"

@app.route('/search_by_image', methods=['POST'])
def search_by_image():
    """以图搜图"""
    if 'image' not in request.files:
        return jsonify({"error": "请上传图片"}), 400

    image_file = request.files['image']
    if image_file.filename == '':
        return jsonify({"error": "请选择图片文件"}), 400

    # 获取数量参数，默认为5
    try:
        top_k = int(request.form.get('count', 5))
    except:
        top_k = 5
    # 确保数量在有效范围内
    top_k = max(1, min(top_k, 10))  # 限制在1-10之间

    # 保存临时文件
    import time
    timestamp = int(time.time())
    temp_path = f"temp_{timestamp}_{image_file.filename}"
    try:
        image_file.save(temp_path)
    except Exception as e:
        print(f"保存临时文件失败: {e}")
        return jsonify({"error": f"保存图片失败: {str(e)}"}), 500

    try:
        # 检查服务是否初始化
        if image_search_service is None:
            success = init_image_search()
            if not success or image_search_service is None:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return jsonify({"error": "图像搜索服务未初始化"}), 500

        # 进行图像搜索，传入数量参数
        results = image_search_service.search_by_image(temp_path, top_k=top_k)

        # 清理临时文件
        if os.path.exists(temp_path):
            os.remove(temp_path)

        # 检查是否有错误
        if 'error' in results:
            return jsonify({"error": results['error']}), 500

        # 统一返回格式
        artworks = results.get('artworks', [])
        actual_count = len(artworks)

        return jsonify({
            "success": True,
            "results": artworks,
            "count": actual_count,
            "requested_count": top_k,
            "message": f"找到 {actual_count} 个相似作品 (请求 {top_k} 个)",
            "seals": results.get('seals', []),
            "inscriptions": results.get('inscriptions', [])
        })

    except Exception as e:
        print(f"以图搜图失败: {e}")
        # 清理临时文件
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        return jsonify({"error": f"搜索失败: {str(e)}"}), 500

@app.route('/artwork_image/<filename>')
def get_artwork_image(filename):
    """获取画作图片"""
    try:
        import urllib.parse
        # 解码文件名
        filename_decoded = urllib.parse.unquote(filename)

        # 去除扩展名，获取画作标题
        base_name = os.path.splitext(filename_decoded)[0]

        # 尝试不同的图片扩展名
        extensions = ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']

        # 直接在artwork_images/artworks目录查找
        image_dir = "artwork_images/artworks"

        for ext in extensions:
            image_path = os.path.join(image_dir, base_name + ext)
            if os.path.exists(image_path):
                return send_from_directory(image_dir, base_name + ext)

        # 如果找不到，尝试查找原始文件名（带扩展名的）
        if os.path.exists(os.path.join(image_dir, filename_decoded)):
            return send_from_directory(image_dir, filename_decoded)

        print(f"找不到画作图片: {filename_decoded}")
        # 返回404图片或占位符
        return jsonify({"error": "图片未找到"}), 404

    except Exception as e:
        print(f"获取图片失败: {e}")
        return jsonify({"error": "获取图片失败"}), 500

if __name__ == "__main__":
    # 确保静态目录存在
    os.makedirs("static/uploads", exist_ok=True)
    os.makedirs("static/segmented", exist_ok=True)
    
    app.run(debug=True, host="0.0.0.0", port=5001, threaded=True, use_reloader=False)
