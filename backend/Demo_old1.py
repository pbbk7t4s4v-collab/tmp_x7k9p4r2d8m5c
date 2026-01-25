# layout_merged_aligned.py
from manim import *

class MergedLayoutScene2(Scene):
    def __init__(self, class_title_text="Regression", avatar_image="csh.png", professor_name="Prof. Siheng Chen", background_image="SAI.png", **kwargs):
        self.class_title_text = class_title_text
        self.avatar_image = avatar_image
        self.professor_name = professor_name
        self.background_image = background_image
        
        # 预处理图片以避免截断错误
        self._preprocess_images()
        
        super().__init__(**kwargs)
    
    def _preprocess_images(self):
        """预处理图片文件以确保Manim能正常加载"""
        # 移除了临时文件生成，直接使用原文件
        pass
    
    def construct(self):
        # 1. 背景和右上角 Logo (保持不变)
        bg = ImageMobject(self.background_image)
        bg.scale_to_fit_height(config.frame_height)
        bg.scale_to_fit_width(config.frame_width)
        bg.set_opacity(0.9)
        bg.move_to(ORIGIN)
        self.add(bg)

        logo = ImageMobject("TeachingMaster.png").scale(0.15).to_corner(UP + RIGHT, buff=0.5)
        left_logo = ImageMobject("logo.png").scale(0.2).to_corner(UP + LEFT, buff=0.5)

        # 2. 创建右侧内容 (保持不变)
        avatar_size = 3.0
        teacher_avatar = ImageMobject(self.avatar_image)
        teacher_avatar.set_height(avatar_size)
        bg_circle = Circle(radius=avatar_size / 2, color=WHITE, fill_opacity=1, stroke_width=0)
        bg_circle.move_to(teacher_avatar.get_center())
        border = Circle(radius=avatar_size / 2, color=WHITE, stroke_width=6)
        border.move_to(teacher_avatar.get_center())
        circular_avatar = Group(bg_circle, teacher_avatar, border)
        presenter = Text(f"Presented by {self.professor_name}'s Agent", font_size=20, color=GREY_A)
        right_content = Group(circular_avatar, presenter)
        right_content.arrange(DOWN, buff=0.4)
        
        # 3. 创建左侧内容 (保持不变)
        course_title = Text("Machine Learning", font_size=45, weight=BOLD)
        class_title = Text(self.class_title_text, font_size=30, slant=ITALIC)
        subtitle = Text("School of Artificial Intelligence", font_size=25, color=GREY_B)
        university = Text("Shanghai Jiao Tong University", font_size=25, color=GREY_B)
        left_content = VGroup(course_title, class_title, subtitle, university)
        left_content.arrange(DOWN, buff=0.3, aligned_edge=LEFT)
        
        # --- 主要修改点在这里 ---
        # 4. 将左右内容组合并统一布局
        # 创建一个主内容组，包含左侧和右侧的所有元素
        main_content = Group(left_content, right_content)
        
        # 使用 .arrange() 方法来排列主内容组中的元素
        # RIGHT 表示水平排列
        # buff=2.0 增大了左右之间的间距，使其更清晰
        # aligned_edge=ORIGIN 在水平排列时，会使它们的垂直中心对齐
        # main_content.arrange(RIGHT, buff=2.0, aligned_edge=ORIGIN)
        main_content.arrange(RIGHT, buff=1.0, aligned_edge=ORIGIN)

        # 将整个主内容组移动到屏幕中心，实现完美居中
        main_content.move_to(ORIGIN)
        # --- 修改结束 ---
        left_content.shift(0.7 * RIGHT)
        right_content.shift(0.5 * LEFT)
        # 5. 编排动画 (保持不变)
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