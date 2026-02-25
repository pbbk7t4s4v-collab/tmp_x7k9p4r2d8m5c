# ending_scene.py
from manim import *

class EndingScene(Scene):
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
        # 1. 背景和右上角 Logo
        bg = ImageMobject(self.background_image)
        bg.scale_to_fit_height(config.frame_height)
        bg.scale_to_fit_width(config.frame_width)
        bg.set_opacity(0.9)
        bg.move_to(ORIGIN)
        self.add(bg)

        logo = ImageMobject("TeachingMaster.png").scale(0.15).to_corner(UP + RIGHT, buff=0.5)
        left_logo = ImageMobject("logo.png").scale(0.15).to_corner(UP + LEFT, buff=0.5)

        # 2. 创建右侧内容 - 教师头像
        avatar_size = 2.5
        teacher_avatar = ImageMobject(self.avatar_image)
        teacher_avatar.set_height(avatar_size)
        bg_circle = Circle(radius=avatar_size / 2, color=WHITE, fill_opacity=1, stroke_width=0)
        bg_circle.move_to(teacher_avatar.get_center())
        border = Circle(radius=avatar_size / 2, color=WHITE, stroke_width=6)
        border.move_to(teacher_avatar.get_center())
        circular_avatar = Group(bg_circle, teacher_avatar, border)
        presenter = Text(f"Presented by {self.professor_name}'s Agent", font_size=23, color=GREY_A)
        right_content = Group(circular_avatar, presenter)
        right_content.arrange(DOWN, buff=0.4)
        
        # 3. 创建左侧内容 - 感谢词
        thank_you = Text("Thank you for listening", font_size=35, weight=BOLD)
        course_name = Text(self.class_title_text, font_size=30, slant=ITALIC)
        subtitle = Text("School of Artificial Intelligence", font_size=25, color=GREY_B)
        university = Text("Anonymous University", font_size=25, color=GREY_B)
        left_content = VGroup(thank_you, course_name, subtitle, university)
        left_content.arrange(DOWN, buff=0.3, aligned_edge=LEFT)
        
        # 4. 将左右内容组合并统一布局
        main_content = Group(left_content, right_content)
        main_content.arrange(RIGHT, buff=1.0, aligned_edge=ORIGIN)
        main_content.move_to(ORIGIN)
        left_content.shift(RIGHT * 0.7)
        right_content.shift(LEFT * 0.5)

        # 5. 编排动画 (与封面保持一致)
        self.play(FadeIn(logo), FadeIn(left_logo))
        self.wait(0.5)

        self.play(
            Write(left_content),
            FadeIn(right_content, scale=0.9)
        )

        self.wait(4.5)
        
        self.play(
            FadeOut(logo),
            FadeOut(left_logo),
            FadeOut(left_content),
            FadeOut(right_content)
        )
        self.wait(1)