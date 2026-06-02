# Makefile - 文章生产流水线
# 在 content/ 目录下执行
# 用法：make review ARTICLE=articles/workspaces/my-article/my-article.md

ARTICLE ?= articles/workspaces/my-article/my-article.md
ARTICLE_DIR := $(dir $(ARTICLE))
ARTICLE_NAME := $(basename $(notdir $(ARTICLE)))

.PHONY: review format cover publish all clean

review:
	@echo "📋 审阅文章..."
	python3 ../technical-article-review/scripts/check_banned_scaffolding.py --input $(ARTICLE)

format:
	@echo "🎨 格式化..."
	../wechat-article-formatter/.venv/bin/python \
		../wechat-article-formatter/scripts/markdown_to_html.py \
		--input $(ARTICLE) \
		--theme mist-blue \
		--output $(ARTICLE_DIR)$(ARTICLE_NAME).html

cover:
	@echo "🖼️ 生成封面..."
	python3 ../wechat-publisher/scripts/generate-cover-image.py \
		--markdown $(ARTICLE) \
		--out $(ARTICLE_DIR)imgs/cover.png

publish: review format cover
	@echo "🚀 发布..."
	cd ../wechat-publisher && bun scripts/wechat-publish.ts ../content/$(ARTICLE)

all: review format cover
	@echo "✅ 流水线完成，可以发布了"
	@echo "   HTML: $(ARTICLE_DIR)$(ARTICLE_NAME).html"
	@echo "   封面: $(ARTICLE_DIR)imgs/cover.png"

clean:
	@echo "🧹 清理生成的文件..."
	rm -f $(ARTICLE_DIR)$(ARTICLE_NAME).html
	rm -f $(ARTICLE_DIR)imgs/cover.png

help:
	@echo "文章生产流水线"
	@echo ""
	@echo "用法:"
	@echo "  make review   - 审阅文章（禁用词检查）"
	@echo "  make format   - 格式化为 HTML"
	@echo "  make cover    - 生成封面图"
	@echo "  make all      - 完整流水线（不含发布）"
	@echo "  make publish  - 完整流水线 + 发布"
	@echo "  make clean    - 清理生成的文件"
	@echo ""
	@echo "指定文章:"
	@echo "  make review ARTICLE=path/to/article.md"
