#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown to HTML Converter for WeChat Public Accounts
将Markdown文章转换为适合微信公众号的美化HTML
"""

import argparse
import os
import sys
import re
from pathlib import Path
from typing import Optional, Dict
import markdown
from markdown.extensions import codehilite, fenced_code, tables, nl2br
from bs4 import BeautifulSoup
import cssutils
import logging

# 禁用cssutils的警告日志
cssutils.log.setLevel(logging.CRITICAL)


class WeChatHTMLConverter:
    """微信公众号HTML转换器"""

    def __init__(self, theme: str = 'ai-tech'):
        self.theme = theme
        self.theme_css = self._load_theme_css()
        self.code_text_color = self._extract_var('--code-text', '#e8d4cf')
        self.code_bg_color = self._extract_var('--code-bg', '#2d3748')
        # 表格主题色
        self.table_header_bg = self._extract_var('--primary-purple', '#7c3aed')
        self.table_border_color = self._extract_var('--border-light', '#e5e7eb')
        self.table_even_bg = self._extract_var('--bg-purple-50', '#faf5ff')

    def _extract_var(self, var_name: str, fallback: str) -> str:
        """从主题 CSS 中提取 CSS 变量值"""
        pattern = rf'{re.escape(var_name)}:\s*([^;]+);'
        match = re.search(pattern, self.theme_css)
        if match:
            return match.group(1).strip()
        return fallback

    def _load_theme_css(self) -> str:
        """加载主题CSS"""
        theme_map = {
            'ai-tech': 'ai-tech-theme.css',
            'mist-blue': 'mist-blue-theme.css',
            'forest': 'forest-theme.css',
            'sunset': 'sunset-theme.css',
            'slate': 'slate-theme.css',
            'midnight': 'midnight-theme.css',
            # 新增主题
            'tech-blue': 'tech-blue-theme.css',
            'warm-orange': 'warm-orange-theme.css',
            'forest-green': 'forest-green-theme.css',
            'midnight-purple': 'midnight-purple-theme.css',
            'business-gray': 'business-gray-theme.css',
            'light-purple': 'light-purple-theme.css',
        }

        if self.theme not in theme_map:
            raise ValueError(f"Unknown theme: {self.theme}. Available: {', '.join(theme_map.keys())}")

        css_file = Path(__file__).parent.parent / 'templates' / theme_map[self.theme]

        if not css_file.exists():
            raise FileNotFoundError(f"Theme CSS file not found: {css_file}")

        with open(css_file, 'r', encoding='utf-8') as f:
            return f.read()

    def _parse_css_to_dict(self) -> Dict[str, Dict[str, str]]:
        """解析CSS为字典格式，用于内联样式"""
        css_rules = {}

        # 解析CSS变量
        css_vars = {}
        var_pattern = r'--([a-zA-Z0-9-]+):\s*([^;]+);'
        for match in re.finditer(var_pattern, self.theme_css):
            var_name = f'--{match.group(1)}'
            var_value = match.group(2).strip()
            css_vars[var_name] = var_value

        # 使用cssutils解析CSS规则
        sheet = cssutils.parseString(self.theme_css)

        for rule in sheet:
            if rule.type == rule.STYLE_RULE:
                selector = rule.selectorText
                styles = {}

                for prop in rule.style:
                    value = prop.value
                    # 替换CSS变量
                    for var_name, var_value in css_vars.items():
                        value = value.replace(f'var({var_name})', var_value)
                    styles[prop.name] = value

                # 处理多个选择器
                for sel in selector.split(','):
                    sel = sel.strip()
                    if sel not in css_rules:
                        css_rules[sel] = {}
                    css_rules[sel].update(styles)

        return css_rules

    def _apply_inline_styles(self, html: str, css_rules: Dict[str, Dict[str, str]]) -> str:
        """将CSS样式内联到HTML标签中"""
        soup = BeautifulSoup(html, 'html.parser')

        # 处理简单选择器（标签、类、ID）
        for selector, styles in css_rules.items():
            # 跳过伪类、伪元素、媒体查询等复杂选择器
            if any(x in selector for x in [':', '@', '>', '+', '~', '[', '*']):
                continue

            try:
                elements = soup.select(selector)
                for elem in elements:
                    # 合并现有style属性
                    existing_style = elem.get('style', '')
                    style_dict = {}

                    # 解析现有style
                    if existing_style:
                        for item in existing_style.split(';'):
                            if ':' in item:
                                key, value = item.split(':', 1)
                                style_dict[key.strip()] = value.strip()

                    # 添加新样式（不覆盖现有样式）
                    for prop, value in styles.items():
                        if prop not in style_dict:
                            style_dict[prop] = value

                    # 生成新的style字符串
                    new_style = '; '.join(f'{k}: {v}' for k, v in style_dict.items())
                    elem['style'] = new_style
            except Exception as e:
                # 忽略无法处理的选择器
                continue

        # 特殊处理：修复代码块样式，确保微信公众号兼容
        # 微信公众号可能会过滤部分样式，所以需要：
        # 1. 确保 pre 有正确的深色背景
        # 2. 确保 code 继承背景色并使用正确的文字颜色
        for pre in soup.find_all('pre'):
            # 设置 pre 的深色背景
            pre_style = pre.get('style', '')
            if 'background' not in pre_style:
                pre['style'] = f'{pre_style}; background: {self.code_bg_color}'.lstrip('; ')

            code = pre.find('code')
            if code:
                # 设置 code 继承背景色并使用正确的文字颜色
                code['style'] = f'background: transparent; color: {self.code_text_color}; font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace; font-size: 14px; line-height: 1.65; border: none; padding: 0'

        # 特殊处理：修复表格样式，确保微信公众号兼容
        # 微信公众号不支持 CSS 变量，需要直接设置颜色值
        for table in soup.find_all('table'):
            # 表格整体样式
            table['style'] = f'width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 15px; border: 1px solid {self.table_border_color}; border-radius: 8px;'

            # 处理 thead
            thead = table.find('thead')
            if thead:
                thead['style'] = f'background: {self.table_header_bg}; color: #ffffff;'

            # 处理所有 th
            for th in table.find_all('th'):
                th['style'] = f'padding: 12px 16px; text-align: left; font-weight: 600; border: 1px solid {self.table_border_color}; color: #ffffff; background: {self.table_header_bg};'

            # 处理所有 td
            for i, td in enumerate(table.find_all('td')):
                # 斑马纹：偶数行浅色背景
                parent_tr = td.find_parent('tr')
                if parent_tr:
                    tbody = parent_tr.find_parent('tbody')
                    if tbody:
                        trs = tbody.find_all('tr')
                        tr_index = trs.index(parent_tr) if parent_tr in trs else -1
                        if tr_index % 2 == 1:  # 偶数行（0-indexed）
                            td['style'] = f'padding: 12px 16px; border: 1px solid {self.table_border_color}; background: {self.table_even_bg};'
                        else:
                            td['style'] = f'padding: 12px 16px; border: 1px solid {self.table_border_color};'
                    else:
                        td['style'] = f'padding: 12px 16px; border: 1px solid {self.table_border_color};'
                else:
                    td['style'] = f'padding: 12px 16px; border: 1px solid {self.table_border_color};'

        return str(soup)

    def _enhance_code_blocks(self, html: str) -> str:
        """增强代码块显示效果"""
        soup = BeautifulSoup(html, 'html.parser')

        # 处理代码块
        for pre in soup.find_all('pre'):
            code = pre.find('code')
            if code:
                # 提取语言信息
                classes = code.get('class', [])
                language = None
                for cls in classes:
                    if cls.startswith('language-'):
                        language = cls.replace('language-', '')
                        break

                # 添加语言标签
                if language:
                    pre['data-lang'] = language

                # 清理 code 标签的内联样式，让 pre 的深色背景显示
                # 微信公众号可能会过滤 pre 的样式，所以需要把样式放到 code 上
                if code.has_attr('style'):
                    # 移除浅色背景和边框，继承 pre 的深色主题
                    style_dict = {}
                    for item in code['style'].split(';'):
                        if ':' in item:
                            key, value = item.split(':', 1)
                            key = key.strip()
                            value = value.strip()
                            # 保留字体相关样式，移除背景和边框
                            if key not in ['background', 'background-color', 'border', 'padding', 'color']:
                                style_dict[key] = value
                    # 设置深色主题的代码样式
                    style_dict['background'] = 'transparent'
                    style_dict['color'] = '#e8d4cf'
                    style_dict['font-family'] = '"SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace'
                    style_dict['font-size'] = '14px'
                    style_dict['line-height'] = '1.65'
                    code['style'] = '; '.join(f'{k}: {v}' for k, v in style_dict.items())

        return str(soup)

    def _process_images(self, html: str) -> str:
        """处理图片标签，确保适合微信显示"""
        soup = BeautifulSoup(html, 'html.parser')

        for img in soup.find_all('img'):
            # 确保图片有必要的样式
            existing_style = img.get('style', '')
            if 'max-width' not in existing_style:
                style_additions = 'max-width: 100%; height: auto; display: block; margin: 24px auto;'
                img['style'] = f'{existing_style}; {style_additions}' if existing_style else style_additions

        return str(soup)

    def _strip_subtitle_label(self, markdown_text: str) -> str:
        """移除正文中的「副标题：」标签，保留副标题文案"""
        # **副标题：** 文案 → 文案
        markdown_text = re.sub(
            r'\*\*副标题[：:]\*\*\s*',
            '',
            markdown_text,
        )
        # > **副标题：** 文案 → > 文案
        markdown_text = re.sub(
            r'(>\s*)\*\*副标题[：:]\*\*\s*',
            r'\1',
            markdown_text,
        )
        return markdown_text

    def _strip_subtitle_label_html(self, html: str) -> str:
        """HTML 兜底：移除 <strong>副标题：</strong> 标签"""
        soup = BeautifulSoup(html, 'html.parser')
        for strong in soup.find_all('strong'):
            text = strong.get_text(strip=True)
            if text in ('副标题：', '副标题:'):
                strong.decompose()
        return str(soup)

    def _process_custom_blocks(self, markdown_text: str) -> str:
        """处理自定义块语法（::: 语法）"""
        # ::: info -> <div class="alert alert-info">
        # ::: success -> <div class="alert alert-success">
        # ::: warning -> <div class="alert alert-warning">
        # ::: danger -> <div class="alert alert-danger">
        # ::: tech -> <div class="alert alert-tech">

        pattern = r':::\s*(info|success|warning|danger|tech)\s*\n(.*?)\n:::'

        def replace_block(match):
            block_type = match.group(1)
            content = match.group(2)
            return f'<div class="alert alert-{block_type}">{content}</div>'

        return re.sub(pattern, replace_block, markdown_text, flags=re.DOTALL)

    def _process_badges(self, html: str) -> str:
        """处理徽章语法"""
        # [!NEW] -> <span class="badge badge-new">NEW</span>
        # [!AI] -> <span class="badge badge-ai">AI</span>
        # [!推荐] -> <span class="badge badge-primary">推荐</span>

        badge_map = {
            'NEW': 'badge-new',
            'AI': 'badge-ai',
            '推荐': 'badge-primary',
            '成功': 'badge-success',
            '警告': 'badge-warning',
        }

        pattern = r'\[!([^\]]+)\]'

        def replace_badge(match):
            text = match.group(1)
            badge_class = badge_map.get(text, 'badge-primary')
            return f'<span class="badge {badge_class}">{text}</span>'

        return re.sub(pattern, replace_badge, html)

    def convert(self, markdown_text: str) -> str:
        """转换Markdown为HTML"""
        # ⚠️ 移除 H1 标题（微信公众号有独立的标题输入框）
        # 删除以 "# " 开头的行（注意：## 和更多 # 的不删除）
        lines = markdown_text.split('\n')
        filtered_lines = []
        for line in lines:
            # 只删除单个 # 开头的行（H1 标题）
            if line.strip().startswith('# ') and not line.strip().startswith('## '):
                continue  # 跳过 H1 标题行
            filtered_lines.append(line)

        markdown_text = '\n'.join(filtered_lines)

        # 移除「副标题：」标签（保留副标题正文）
        markdown_text = self._strip_subtitle_label(markdown_text)

        # ✅ 新增：处理自定义块语法
        markdown_text = self._process_custom_blocks(markdown_text)

        # 配置Markdown扩展
        extensions = [
            'markdown.extensions.fenced_code',
            'markdown.extensions.tables',
            'markdown.extensions.nl2br',
            'markdown.extensions.sane_lists',
            'markdown.extensions.codehilite',
        ]

        extension_configs = {
            'codehilite': {
                'linenums': False,
                'guess_lang': True,
                'noclasses': True,
            }
        }

        # 转换Markdown为HTML
        md = markdown.Markdown(extensions=extensions, extension_configs=extension_configs)
        html_content = md.convert(markdown_text)

        # HTML 兜底：移除可能残留的「副标题：」标签
        html_content = self._strip_subtitle_label_html(html_content)

        # ✅ 新增：处理徽章语法
        html_content = self._process_badges(html_content)

        # 增强代码块
        html_content = self._enhance_code_blocks(html_content)

        # 处理图片
        html_content = self._process_images(html_content)

        # 解析CSS并内联样式
        css_rules = self._parse_css_to_dict()
        html_content = self._apply_inline_styles(html_content, css_rules)

        # 包装为完整HTML文档
        full_html = self._wrap_html(html_content)

        return full_html

    def _wrap_html(self, body_content: str) -> str:
        """包装为完整的HTML文档"""
        # 提取CSS变量以在head中定义
        css_vars_match = re.search(r':root\s*\{([^}]+)\}', self.theme_css)
        css_vars = css_vars_match.group(1) if css_vars_match else ''

        html_template = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>微信公众号文章</title>
    <style>
        :root {{
            {css_vars}
        }}

        /* 基础样式 */
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
            font-size: 16px;
            line-height: 1.8;
            color: var(--text-primary, #333);
            background: var(--bg-white, #fff);
            padding: 20px;
            max-width: 720px;
            margin: 0 auto;
        }}
    </style>
</head>
<body>
    <!-- ⚠️ 标题请在微信公众号编辑器中单独填写，HTML 中已自动移除 H1 标题 -->
    {body_content}
</body>
</html>'''

        return html_template

    @staticmethod
    def _strip_frontmatter(markdown_text: str) -> str:
        """剥离文件开头的 YAML frontmatter（--- ... ---）。

        仅在文本起始处匹配一次，避免误删正文中作为分隔线的 ``---``。
        frontmatter 是元数据（title/summary/author/coverImage 等），
        不应进入公众号正文。
        """
        return re.sub(r'\A---\s*\n[\s\S]*?\n---\s*\n?', '', markdown_text, count=1)

    def convert_file(self, input_file: str, output_file: Optional[str] = None) -> str:
        """转换Markdown文件为HTML文件"""
        input_path = Path(input_file)

        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")

        # 读取Markdown文件
        with open(input_path, 'r', encoding='utf-8') as f:
            markdown_text = f.read()

        # 剥离 frontmatter 元数据，避免 title/author/coverImage 等进入正文
        markdown_text = self._strip_frontmatter(markdown_text)

        # 转换为HTML
        html_content = self.convert(markdown_text)

        # 确定输出文件路径
        if output_file is None:
            output_file = input_path.with_suffix('.html')

        output_path = Path(output_file)

        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 写入HTML文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return str(output_path)


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description='将Markdown文章转换为适合微信公众号的美化HTML',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例用法:
  # 使用雾霾蓝主题转换（默认）
  python markdown_to_html.py --input article.md

  # 显式指定雾霾蓝主题
  python markdown_to_html.py --input article.md --theme mist-blue

  # 指定输出文件
  python markdown_to_html.py --input article.md --output output.html

  # 转换后在浏览器预览
  python markdown_to_html.py --input article.md --preview

可用主题:
  mist-blue - 雾霾蓝主题（默认，低饱和蓝灰编辑风，适合技术长文与公众号正文）
  ai-tech   - AI 科技主题（渐进式紫蓝绿配色，丰富组件，专为 AI 领域内容设计）
  forest    - 森林绿主题（清新自然的绿色系）
  sunset    - 日落主题（温暖的橙红色系）
  slate     - 石板灰主题（中性的灰蓝色系）
  midnight  - 深夜主题（深邃的暗蓝色系）
  light-purple - 浅紫主题（明亮紫色调，浅色代码块，适合技术教程和 AI 主题）

新增语法支持:
  信息框：::: info / success / warning / danger / tech
  徽章：[!NEW] [!AI] [!推荐]
        '''
    )

    parser.add_argument('-i', '--input', required=True, help='输入的Markdown文件路径')
    parser.add_argument('-o', '--output', help='输出的HTML文件路径（默认：与输入文件同名.html）')
    parser.add_argument('-t', '--theme', default='ai-tech',
                        choices=['ai-tech', 'mist-blue', 'forest', 'sunset', 'slate', 'midnight',
                                 'tech-blue', 'warm-orange', 'forest-green', 'midnight-purple', 'business-gray', 'light-purple'],
                        help='选择主题：ai-tech（默认）、mist-blue、forest、sunset、slate、midnight、tech-blue、warm-orange、forest-green、midnight-purple、business-gray、light-purple')
    parser.add_argument('-p', '--preview', action='store_true',
                        help='转换后在浏览器中打开预览')

    args = parser.parse_args()

    try:
        # 创建转换器
        converter = WeChatHTMLConverter(theme=args.theme)

        # 转换文件
        output_path = converter.convert_file(args.input, args.output)

        print(f'✅ 转换成功！')
        print(f'📄 输入文件: {args.input}')
        print(f'📄 输出文件: {output_path}')
        print(f'🎨 使用主题: {args.theme}')

        # 预览
        if args.preview:
            import webbrowser
            webbrowser.open(f'file://{Path(output_path).absolute()}')
            print(f'🌐 已在浏览器中打开预览')

        print('\n💡 提示：')
        print('   1. 在浏览器中打开HTML文件预览效果')
        print('   2. 使用浏览器的"审查元素"工具查看样式')
        print('   3. 复制HTML内容粘贴到微信公众号编辑器')
        print('   4. 在微信编辑器中可能需要微调图片和代码块')

    except Exception as e:
        print(f'❌ 转换失败: {e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
