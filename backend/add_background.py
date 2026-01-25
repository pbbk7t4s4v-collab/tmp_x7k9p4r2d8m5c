import os
import sys
import re
import shutil

def is_color(value: str) -> bool:
    return value.startswith("#") or value.isupper()

def build_background_code(bg_input: str, image_filename: str = None) -> str:
    if is_color(bg_input):
        if bg_input.startswith("#"):
            return f'self.camera.background_color = Color("{bg_input}")  # 自定义颜色\n'
        else:
            return f'self.camera.background_color = {bg_input}  # 内置颜色\n'
    else:
        # 如果是图片，使用拷贝后的文件名
        img_name = image_filename if image_filename else bg_input
        # abs_img_path = os.path.abspath(img_name)
        return (
            "###BACKGROUND###\n"
            f'bg = ImageMobject("{img_name}")\n'
            f'bg.set_z_index(-100)\n'
            f'bg.scale(max(config.frame_width  / bg.width, config.frame_height / bg.height))\n'
            f'bg.move_to(ORIGIN)\n'
            f'self.add(bg)\n'
            "###BACKGROUND###\n"
        )
    
def remove_existing_background(file_path: str):
    """
    删除文件中已有的背景代码(通过###BACKGROUND###标记识别)
    
    Args:
        file_path (str): 文件路径
    """
    with open(file_path, "r") as f:
        lines = f.readlines()
    
    new_lines = []
    in_bg_code = False
    
    for line in lines:
        
        # 检测背景代码开始标记
        if "###BACKGROUND###" in line and not in_bg_code:
            in_bg_code = True
            continue

        # 跳过背景代码块中的行
        if in_bg_code:
            if "###BACKGROUND###" in line:
                in_bg_code = False
            continue
        print(line)
        new_lines.append(line)

    with open(file_path, "w") as f:
        f.writelines(new_lines)

def insert_background_code(file_path: str, bg_code: str):
    remove_existing_background(file_path)
    with open(file_path, "r") as f:
        lines = f.readlines()

    new_lines = []
    inserted = False
    for line in lines:
        new_lines.append(line)
        if not inserted and re.match(r"\s*def construct\(self\):", line):
            indent = re.match(r"(\s*)", line).group(1) + "    "  # 四空格缩进
            bg_code_indented = "".join(indent + line for line in bg_code.splitlines(True))
            new_lines.append(bg_code_indented)
            inserted = True

    if inserted:
        with open(file_path, "w") as f:
            f.writelines(new_lines)
        print(f"插入成功: {file_path}")
    else:
        print(f"未找到 construct(self): 跳过: {file_path}")

def copy_image_to_target_dir(image_path: str, target_dir: str) -> str:
    """
    将图片文件拷贝到目标目录中
    
    Args:
        image_path (str): 原始图片路径
        target_dir (str): 目标目录
    
    Returns:
        str: 拷贝后的文件名（不含路径）
    """
    if not os.path.exists(image_path):
        print(f"警告：图片文件不存在: {image_path}")
        return os.path.basename(image_path)  # 返回文件名，让用户自己处理
    
    # 获取文件名
    image_filename = os.path.basename(image_path)
    target_path = os.path.join(target_dir, image_filename)
    
    try:
        # 如果目标文件已存在且内容相同，跳过拷贝
        if os.path.exists(target_path):
            if os.path.getsize(image_path) == os.path.getsize(target_path):
                print(f"图片已存在，跳过拷贝: {image_filename}")
                return image_filename
        
        # 拷贝文件
        shutil.copy2(image_path, target_path)
        print(f"图片拷贝成功: {image_path} -> {target_path}")
        return image_filename
    
    except Exception as e:
        print(f"拷贝图片失败: {str(e)}")
        return os.path.basename(image_path)

def add_background(target_dir: str, bg_input: str):
    """
    为目标目录中的所有Manim代码文件添加背景

    Args:
        target_dir (str): Manim代码文件夹路径
        bg_input (str): 背景图路径或颜色值
    """
    # 检查目标目录是否存在
    if not os.path.exists(target_dir):
        print(f"错误：目标目录不存在: {target_dir}")
        return
    image_filename = None
    # 如果是图片文件，先拷贝到目标目录
    if not is_color(bg_input):
        image_filename = copy_image_to_target_dir(bg_input, target_dir)
    # 生成背景代码
    bg_code = build_background_code(bg_input, image_filename)
    # 处理所有Python文件
    python_files = [f for f in os.listdir(target_dir) if f.endswith(".py")]
    if not python_files:    
        print(f"警告：在目录 {target_dir} 中没有找到Python文件")
        return
    print(f"找到 {len(python_files)} 个Python文件，开始处理...")
    success_count = 0
    for filename in python_files:
        file_path = os.path.join(target_dir, filename)
        try:
            insert_background_code(file_path, bg_code)
            success_count += 1
        except Exception as e:
            print(f"处理文件失败 {filename}: {str(e)}")
    print(f"\n处理完成！成功处理 {success_count}/{len(python_files)} 个文件")
    

def main():
    if len(sys.argv) != 3:
        print("用法: python add_background.py <Manim代码文件夹路径> <背景图路径|颜色>")
        sys.exit(1)

    target_dir = sys.argv[1]
    bg_input = sys.argv[2]
    
    # 检查目标目录是否存在
    if not os.path.exists(target_dir):
        print(f"错误：目标目录不存在: {target_dir}")
        sys.exit(1)
    
    image_filename = None
    
    # 如果是图片文件，先拷贝到目标目录
    if not is_color(bg_input):
        print(f"检测到图片背景: {bg_input}")
        image_filename = copy_image_to_target_dir(bg_input, target_dir)
    else:
        print(f"检测到颜色背景: {bg_input}")
    
    # 生成背景代码
    bg_code = build_background_code(bg_input, image_filename)
    
    # 处理所有Python文件
    python_files = [f for f in os.listdir(target_dir) if f.endswith(".py")]
    
    if not python_files:
        print(f"警告：在目录 {target_dir} 中没有找到Python文件")
        return
    
    print(f"找到 {len(python_files)} 个Python文件，开始处理...")
    success_count = 0
    
    for filename in python_files:
        file_path = os.path.join(target_dir, filename)
        try:
            insert_background_code(file_path, bg_code)
            success_count += 1
        except Exception as e:
            print(f"处理文件失败 {filename}: {str(e)}")
    
    print(f"\n处理完成！成功处理 {success_count}/{len(python_files)} 个文件")

if __name__ == "__main__":
    main()