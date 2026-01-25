from manim import *
from pathlib import Path
from PIL import Image, ImageDraw

class MergedLayoutScene2(Scene):
    def __init__(self, class_title_text="Regression", 
                 avatar_image="/home/TeachMasterAppV3/backend/TeachingMaster.png", professor_name="Timo", 
                 background_image="SAI.png", school=" ",  
                 university=" ", left_logo="/home/TeachMasterAppV3/backend/logo.png", **kwargs):
        self.class_title_text = class_title_text
        self.avatar_image = avatar_image
        self.professor_name = professor_name
        self.background_image = background_image
        self.school = school
        self.university = university
        self.left_logo = left_logo
        # 预处理图片以避免截断错误
        self._preprocess_images()       
        super().__init__(**kwargs)
    
    def _preprocess_images(self):
        """把头像图片裁剪成真正的圆形（四角透明），JPG/PNG 都支持"""
        try:
            avatar_path = Path(self.avatar_image)
            if not avatar_path.exists():
                print(f"[WARN] 找不到头像文件: {avatar_path}")
                return

            # 输出文件名：原名 + "_circle.png"
            out_path = avatar_path.with_name(avatar_path.stem + "_circle.png")

            # 若圆形头像已存在，直接使用，避免重复处理
            if out_path.exists():
                self.avatar_image = str(out_path)
                return

            # 无论原图是 JPG 还是 PNG，都转成 RGBA（带透明通道）
            img = Image.open(avatar_path).convert("RGBA")
            w, h = img.size
            size = min(w, h)

            # 居中裁成正方形，避免变形
            left = (w - size) // 2
            top = (h - size) // 2
            img = img.crop((left, top, left + size, top + size))

            # 生成一张纯透明的底图，后面把圆形图贴到这里
            base = Image.new("RGBA", (size, size), (0, 0, 0, 0))

            # 创建圆形遮罩：白色区域=显示，黑色=透明
            mask = Image.new("L", (size, size), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, size, size), fill=255)

            # 把裁好的头像贴到透明底图上，并通过 mask 实现“抠圆”
            base.paste(img, (0, 0), mask=mask)
            self._temp_avatar_to_delete = out_path
            # 输出最终的圆形 PNG
            base.save(out_path)

            # 更新路径，后续 construct() 中加载的就是圆形头像了
            self.avatar_image = str(out_path)
            print(f"[INFO] 头像已成功裁剪为圆形: {out_path}")

        except Exception as e:
            print(f"[WARN] 头像裁剪失败: {e}")
        # 出错不要直接中断场景渲染，只是继续用原图

    
    def construct(self):
        # 1. 背景和右上角 Logo
        bg = ImageMobject(self.background_image)
        bg.set_z_index(-100)
        bg.scale(max(config.frame_width  / bg.width, config.frame_height / bg.height))
        bg.move_to(ORIGIN)
        self.add(bg)
        logo = ImageMobject("/home/TeachMasterAppV2/backend/TeachingMaster.png").scale(0.05).to_corner(UP + RIGHT, buff=0.5)
        left_logo = ImageMobject(self.left_logo).scale_to_fit_height(0.5).to_corner(UP + LEFT, buff=0.5)

        # 2. 创建右侧内容 - 教师头像
        avatar_size = 3.0
        teacher_avatar = ImageMobject(self.avatar_image)
        teacher_avatar.set_height(avatar_size)
        bg_circle = Circle(radius=avatar_size / 2, color=WHITE, fill_opacity=1, stroke_width=0)
        bg_circle.move_to(teacher_avatar.get_center())
        border = Circle(radius=avatar_size / 2, color=WHITE, stroke_width=6)
        border.move_to(teacher_avatar.get_center())
        circular_avatar = Group(bg_circle, teacher_avatar, border)
        presenter = Text(f"Presented by {self.professor_name}", font_size=20, color=GREY_A)
        website = MarkupText(
            "<u>www. teachmaster. cn</u>",
            font_size=20,
            weight=BOLD
        )
        right_content = Group(circular_avatar, presenter, website)
        right_content.arrange(DOWN, buff=0.4)
        website.shift(UP * 0.2)
        
        # 3. 创建左侧内容
        class_title = Text(self.class_title_text, font_size=40, slant=ITALIC)
        school = Text(self.school, font_size=25, color=GREY_B)
        university = Text(self.university, font_size=25, color=GREY_B)
        left_content = VGroup(class_title, school, university)
        left_content.arrange(DOWN, buff=0.3, aligned_edge=LEFT)

        # 4. 将左右内容组合并统一布局
        main_content = Group(left_content, right_content)
        main_content.arrange(RIGHT, buff=2.5, aligned_edge=UP)
        left_content.shift(0.7 * LEFT).shift(DOWN * 1.0)
        main_content.move_to(ORIGIN)
        left_content.shift(0.7 * RIGHT)
        right_content.shift(0.5 * LEFT)
        
        # 5. 编排动画 (与封面保持一致)
        self.play(FadeIn(logo), FadeIn(left_logo))
        self.wait(0.5)

        self.play(
            Write(left_content), 
            FadeIn(right_content, scale=0.9)
        )

        self.wait(7.5)
        
        self.play(
            FadeOut(logo),
            FadeOut(left_logo),
            FadeOut(left_content),
            FadeOut(right_content)
        )
        self.wait(1)
        if hasattr(self, "_temp_avatar_to_delete"):
            try:
                Path(self._temp_avatar_to_delete).unlink()
                print("[INFO] 已删除临时头像文件:", self._temp_avatar_to_delete)
            except Exception as e:
                print("[WARN] 删除临时头像失败:", e)