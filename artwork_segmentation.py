
# !/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
艺术品图像分割模块 - 基于 FastSAM 的中国古代书画分割功能
"""
import os
import torch
import numpy as np
from PIL import Image
import uuid
import cv2  # 确保导入 cv2

# 尝试导入FastSAM，如果失败，可能是因为依赖未完全安装
try:
    from fastsam import FastSAM, FastSAMPrompt
    print("✓ 成功导入FastSAM库")
except ImportError as e:
    print("=" * 80)
    print("错误: 无法导入 FastSAM 库。")
    print("请确保您已根据 FastSAM 官方指南正确安装其依赖。")
    print("通常需要执行: pip install -r requirements.txt (在FastSAM克隆的仓库中)")
    print(f"原始错误: {e}")
    print("=" * 80)
    # 不直接退出，而是继续执行，这样模块至少会被加载
    FastSAM = None
    FastSAMPrompt = None
    print("模块将继续加载，但图像分割功能将不可用")


class ArtworkSegmentationService:
    """艺术品图像分割服务类"""

    def __init__(self, model_path="./weights/FastSAM_X.pt"):
        """
        初始化艺术品图像分割服务。

        Args:
            model_path (str): FastSAM 模型权重文件的路径。
        """
        self.model_path = model_path
        self.model = None
        self.device = torch.device(
            "cuda" if torch.cuda.is_available() else
            "mps" if torch.backends.mps.is_available() else
            "cpu"
        )

        # 确保所有必要的静态目录都存在
        os.makedirs("./weights", exist_ok=True)
        os.makedirs("./static/uploads", exist_ok=True)
        os.makedirs("./static/segmented", exist_ok=True)

        # 加载模型
        self._load_model()

    def _load_model(self):
        """
        加载FastSAM模型，包含针对新版PyTorch的兼容性修复。
        如果模型文件不存在，会自动下载。
        """
        # 检查模型文件是否存在，如果不存在则自动下载
        if not os.path.exists(self.model_path):
            print(f"模型文件不存在: {self.model_path}")
            print("正在尝试自动下载模型...")
            if not download_fastsam_model(self.model_path):
                print("✗ 模型下载失败，无法加载模型")
                return False

        print(f"正在加载 FastSAM 模型: {self.model_path} ...")

        # 方法1: 尝试修改torch.load的weights_only参数
        try:
            print("尝试修改torch.load的weights_only参数...")
            # 保存原始的torch.load函数
            original_torch_load = torch.load
            
            # 临时修改torch.load的默认参数
            def modified_torch_load(*args, **kwargs):
                if 'weights_only' not in kwargs:
                    kwargs['weights_only'] = False
                return original_torch_load(*args, **kwargs)
            
            # 替换torch.load
            torch.load = modified_torch_load
            
            # 现在尝试加载模型
            self.model = FastSAM(self.model_path)
            
            # 恢复原始的torch.load函数
            torch.load = original_torch_load
            
            print(f"✓ FastSAM 模型加载成功 (修改weights_only), 使用设备: {self.device}")
            return True
            
        except Exception as e:
            print(f"⚠ 修改weights_only加载失败: {e}")
            
        # 方法2: 尝试直接导入FastSAM，不使用ultralytics
        try:
            print("尝试直接导入FastSAM...")
            # 直接导入FastSAM，绕过ultralytics的导入问题
            self.model = FastSAM(self.model_path)
            print(f"✓ FastSAM 模型加载成功 (直接导入), 使用设备: {self.device}")
            return True
            
        except Exception as e2:
            print(f"✗ 直接导入也失败: {e2}")
            print("模型加载失败，请检查您的 PyTorch、ultralytics 和 FastSAM 版本兼容性。")
            return False

    def save_uploaded_image(self, image_file):
        """
        保存上传的图像文件

        Args:
            image_file: 上传的图像文件对象

        Returns:
            str: 保存的图像文件路径
        """
        try:
            # 生成唯一文件名
            import uuid
            timestamp = str(uuid.uuid4())

            # 保留原始文件扩展名
            original_filename = image_file.filename
            if original_filename and '.' in original_filename:
                file_ext = original_filename.rsplit('.', 1)[1].lower()
                filename = f"upload_{timestamp}.{file_ext}"
            else:
                filename = f"upload_{timestamp}.jpg"

            filepath = os.path.join("./static/uploads", filename)

            # 保存文件
            image_file.save(filepath)
            print(f"✓ 图像已保存到: {filepath}")

            return filepath

        except Exception as e:
            print(f"保存上传图像失败: {e}")
            return None

    def segment_artwork(self, image_path,
                      input_size=1024,
                      iou_threshold=0.7,
                      conf_threshold=0.25,
                      better_quality=False,
                      withContours=True,
                      use_retina=True,
                      mask_random_color=True,
                      text_prompt=None,
                      point_prompts=None,
                      point_labels=None,
                      box_prompts=None):
        """
        对图像进行分割

        Args:
            image_path: 输入图像路径
            input_size: 输入图像尺寸
            iou_threshold: IoU阈值
            conf_threshold: 置信度阈值
            better_quality: 是否使用更好的质量
            withContours: 是否绘制轮廓
            use_retina: 是否使用retina masks
            mask_random_color: 是否使用随机颜色
            text_prompt: 文本提示
            point_prompts: 点提示
            point_labels: 点标签
            box_prompts: 框提示

        Returns:
            tuple: (分割结果图像路径, 原始图像路径, 分割信息)
        """
        # 检查模型是否加载，如果未加载则尝试重新加载
        if not self.model:
            print("模型未加载，尝试重新加载...")
            # 尝试下载模型（如果需要）
            download_fastsam_model(self.model_path)
            # 尝试重新加载模型
            if not self._load_model():
                return None, None, "模型未加载"


        try:
            # 加载和预处理图像
            input_image = Image.open(image_path).convert("RGB")

            # 调整图像尺寸
            w, h = input_image.size
            scale = input_size / max(w, h)
            new_w = int(w * scale)
            new_h = int(h * scale)
            resized_image = input_image.resize((new_w, new_h))

            # 运行FastSAM模型
            results = self.model(
                resized_image,
                device=self.device,
                retina_masks=use_retina,
                iou=iou_threshold,
                conf=conf_threshold,
                imgsz=input_size,
            )

            # 使用FastSAMPrompt进行后处理
            prompt_process = FastSAMPrompt(resized_image, results, device=str(self.device))

            # 处理不同类型的提示
            if text_prompt:
                # 文本提示分割
                annotations = prompt_process.text_prompt(text_prompt)
            elif point_prompts and point_labels:
                # 点提示分割
                # 调整点坐标到缩放后的图像
                scaled_points = [[int(x * scale) for x in point] for point in point_prompts]
                annotations = prompt_process.point_prompt(scaled_points, point_labels)
            elif box_prompts:
                # 框提示分割
                # 调整框坐标到缩放后的图像
                scaled_boxes = [[int(coord * scale) for coord in box] for box in box_prompts]
                annotations = prompt_process.box_prompt(bboxes=scaled_boxes)
            else:
                # 默认全图分割
                annotations = prompt_process.everything_prompt()

            # 生成分割结果图像
            segmented_image_array = prompt_process.plot_to_result(
                annotations=annotations,
                mask_random_color=mask_random_color,
                better_quality=better_quality,
                retina=use_retina,
                withContours=withContours,
            )

            # 保存分割结果
            timestamp = str(uuid.uuid4())
            segmented_filename = f"segmented_{timestamp}.png"
            segmented_path = os.path.join("./static/segmented", segmented_filename)

            # 将numpy数组转换为PIL图像并保存
            if isinstance(segmented_image_array, np.ndarray):
                if segmented_image_array.dtype != np.uint8:
                    segmented_image_array = (segmented_image_array * 255).astype(np.uint8)
                segmented_pil = Image.fromarray(segmented_image_array)
                segmented_pil.save(segmented_path)
            else:
                # 如果是其他类型，尝试直接保存
                segmented_image_array.save(segmented_path)

            # 生成分割信息
            num_masks = len(annotations) if annotations is not None else 0
            segmentation_info = {
                "num_masks": num_masks,
                "input_size": input_size,
                "device": str(self.device),
                "iou_threshold": iou_threshold,
                "conf_threshold": conf_threshold,
                "original_size": (w, h),
                "processed_size": (new_w, new_h)
            }

            return segmented_path, image_path, segmentation_info

        except Exception as e:
            print(f"图像分割失败: {e}")
            return None, None, f"分割失败: {str(e)}"

    def get_model_status(self):
        """获取当前模型的状态。"""
        return {
            "model_loaded": self.model is not None,
            "model_path": self.model_path,
            "device": str(self.device),
            "model_file_exists": os.path.exists(self.model_path)
        }

def download_fastsam_model(model_path="./weights/FastSAM_X.pt"):
    """如果模型文件不存在，则自动下载。"""
    if os.path.exists(model_path):
        return True

    print("FastSAM 模型权重文件不存在，正在尝试下载...")
    model_url = "https://github.com/CASIA-IVA-Lab/FastSAM/releases/download/v1.0.0/FastSAM_X.pt"

    try:
        import requests
        print(f"从 {model_url} 下载到 {model_path}")
        with requests.get(model_url, stream=True) as r:
            r.raise_for_status()
            with open(model_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print("✓ 模型下载完成。")
        return True
    except Exception as e:
        print(f"✗ 模型自动下载失败: {e}")
        print("请手动从 https://github.com/CASIA-IVA-Lab/FastSAM/releases 下载 FastSAM_X.pt 并放入 ./weights 目录。")
        return False

# 全局图像分割服务实例
try:
    print("初始化全局图像分割服务实例...")
    image_segmentation_service = ArtworkSegmentationService()
    print("✓ 全局图像分割服务实例初始化成功")
except Exception as e:
    print(f"✗ 全局图像分割服务实例初始化失败: {e}")
    import traceback
    traceback.print_exc()
    # 设置为None，以便在其他地方能够检测到初始化失败
    image_segmentation_service = None


# --- 主程序入口，用于独立测试 ---
if __name__ == "__main__":
    # 1. 自动下载模型（如果需要）
    if not download_fastsam_model():
        exit()  # 如果下载失败，则退出

    # 2. 实例化服务
    # 只有在模型下载成功后才进行实例化
    artwork_segmentation_service = ArtworkSegmentationService()
    status = artwork_segmentation_service.get_model_status()
    print("\n艺术品分割服务状态:", status)

    if not status["model_loaded"]:
        print("\n模型未能加载，测试中止。")
        exit()

    # 3. 准备测试图片
    # <<< 请将此路径替换为您自己的古代书画图片路径 >>>
    test_image_path = r'F:\Chineseart\artwork_images\artworks\千里江山图_3.jpg'

    if not os.path.exists(test_image_path):
        print(f"\n[测试警告]: 测试图片 '{test_image_path}' 不存在。")
        print("请将脚本中的 'test_image_path' 替换为您电脑上一张真实的书画图片路径，然后重新运行。")
        exit()

    print("-" * 80)
    # --- 测试用例 1: 全图分割 ---
    print(f"\n[测试 1/2] 正在对《{os.path.basename(test_image_path)}》进行【全图分割】...")

    # 获取返回值
    result = artwork_segmentation_service.segment_artwork(test_image_path)
    output_path_1, original_image_path_1, masks_info_dict = result  # 正确对应三个返回值

    # 从字典中获取对象数量
    objects_found = masks_info_dict.get('num_masks', 0)
    print(f"  ✓ 全图分割成功! 找到 {objects_found} 个对象。")
    print(f"     分割结果已保存至: {output_path_1}")

    print("-" * 80)
    # # --- 测试用例 2: 文本提示分割 ---
    # print(f"\n[测试 2/2] 正在对《{os.path.basename(test_image_path)}》进行【文本提示分割】...")
    # # << 您可以修改这里的文本提示来分割不同的对象, e.g., "船", "树", "房屋" >>
    # text_prompt = "山"
    # output_path_2, info_2 = artwork_segmentation_service.segment_artwork(test_image_path, text_prompt=text_prompt)
    # if output_path_2:
    #     print(f"  ✓ 文本提示分割成功! 找到 {info_2['num_objects_found']} 个与 '{text_prompt}' 相关的对象。")
    # else:
    #     print(f"  ✗ 文本提示分割失败: {info_2}")
