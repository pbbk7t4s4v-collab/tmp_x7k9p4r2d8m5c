import subprocess
import os
readtxtPath = f"generated_content/101/d8440e0e-02ae-49a5-87d5-254950260b61/speech"

# 使用readtxt脚本合并讲稿
readtxt_command = [
            "/home/EduAgent/miniconda3/envs/manim_env/bin/python", 
            "readtxt.py",
            readtxtPath,
            "--out",
            os.path.join(readtxtPath, "讲稿文件"),
        ]
# 运行readtxt脚本

subprocess.run(readtxt_command, check=True)

