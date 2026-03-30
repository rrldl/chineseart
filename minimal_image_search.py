#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最小化测试以图搜图功能
"""

import os
import sys
import numpy as np
from PIL import Image
import torch
from transformers import CLIPProcessor, CLIPModel

print("开始导入模块...")
print(f"Python版本: {sys.version}")
print(f"当前目录: {os.getcwd()}")

# 测试基本依赖
print("\n测试基本依赖:")
try:
    import numpy
    print("✓ numpy 导入成功")
except Exception as e:
    print(f"✗ numpy 导入失败: {e}")

try:
    from PIL import Image
    print("✓ PIL 导入成功")
except Exception as e:
    print(f"✗ PIL 导入失败: {e}")

try:
    import torch
    print(f"✓ torch 导入成功, 版本: {torch.__version__}")
    print(f"  CUDA 可用: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"  CUDA 设备: {torch.cuda.get_device_name(0)}")
except Exception as e:
    print(f"✗ torch 导入失败: {e}")

try:
    from transformers import CLIPProcessor, CLIPModel
    print("✓ transformers 导入成功")
except Exception as e:
    print(f"✗ transformers 导入失败: {e}")

try:
    from py2neo import Graph, NodeMatcher
    print("✓ py2neo 导入成功")
except Exception as e:
    print(f"✗ py2neo 导入失败: {e}")

# 测试模型加载
print("\n测试模型加载:")
try:
    model_name = "openai/clip-vit-base-patch32"
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"使用设备: {device}")
    
    print("加载 CLIP 模型...")
    model = CLIPModel.from_pretrained(model_name).to(device)
    print("✓ 模型加载成功")
    
    print("加载 CLIP 处理器...")
    processor = CLIPProcessor.from_pretrained(model_name)
    print("✓ 处理器加载成功")
    
except Exception as e:
    print(f"✗ 模型加载失败: {e}")
    import traceback
    traceback.print_exc()

# 测试图像加载
print("\n测试图像加载:")
try:
    test_image_path = "artwork_images/artworks/千里江山图.jpg"
    if os.path.exists(test_image_path):
        print(f"✓ 测试图片存在: {test_image_path}")
        image = Image.open(test_image_path).convert("RGB")
        print(f"✓ 图像加载成功, 大小: {image.size}")
    else:
        print(f"✗ 测试图片不存在: {test_image_path}")
        # 尝试其他图片
        test_image_path = "artwork_images/artworks/步溪图.png"
        if os.path.exists(test_image_path):
            print(f"✓ 测试图片存在: {test_image_path}")
            image = Image.open(test_image_path).convert("RGB")
            print(f"✓ 图像加载成功, 大小: {image.size}")
        else:
            print(f"✗ 测试图片不存在: {test_image_path}")
except Exception as e:
    print(f"✗ 图像加载失败: {e}")
    import traceback
    traceback.print_exc()

print("\n测试完成!")
