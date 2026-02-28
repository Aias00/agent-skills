#!/bin/bash
# Twitter 页面抓取脚本 - 使用 OpenClaw browser 工具（基于 CDP）

set -e

# 配置
WORKSPACE="${WORKSPACE:-$HOME/.openclaw/workspace}"
OUTPUT_DIR="$WORKSPACE/skills/playwright-twitter-access/outputs"
mkdir -p "$OUTPUT_DIR"

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 显示帮助
show_help() {
    echo "Twitter 页面抓取工具 - Playwright"
    echo ""
    echo "用法: $0 <command> [args]"
    echo ""
    echo "命令:"
    echo "  user <username>         抓取用户主页"
    echo "  tweet <tweet_url>       抓取单条推文"
    echo "  search <query>          搜索推特"
    echo "  help                   显示此帮助"
    echo ""
    echo "示例:"
    echo "  $0 user elonmusk"
    echo "  $0 tweet https://x.com/elonmusk/status/123456789"
    echo "  $0 search 'AI technology'"
}

# 抓取用户主页
fetch_user() {
    local username="$1"

    echo -e "${BLUE}抓取用户主页: @$username${NC}"
    echo "URL: https://x.com/$username"
    echo ""

    # 打开页面
    echo "1. 打开页面..."
    cd "$WORKSPACE"
    browser action=open targetUrl="https://x.com/$username" > /dev/null

    # 等待加载
    echo "2. 等待加载..."
    sleep 5

    # 获取快照
    echo "3. 获取页面快照..."
    local snapshot_file="$OUTPUT_DIR/${username}_snapshot.json"
    browser action=snapshot depth=5 refs=role > "$snapshot_file"

    # 截图
    echo "4. 截取页面截图..."
    local screenshot=$(browser action=screenshot type="png" 2>&1 | grep "MEDIA:" | cut -d: -f2- | tr -d ' ')
    echo "   截图: $screenshot"

    echo -e "${GREEN}✅ 完成${NC}"
    echo "   快照: $snapshot_file"
}

# 抓取单条推文
fetch_tweet() {
    local tweet_url="$1"

    echo -e "${BLUE}抓取单条推文${NC}"
    echo "URL: $tweet_url"
    echo ""

    # 提取推文 ID
    local tweet_id=$(echo "$tweet_url" | grep -o 'status/[0-9]*' | cut -d/ -f2)

    if [ -z "$tweet_id" ]; then
        echo "错误: 无法提取推文 ID"
        exit 1
    fi

    echo "推文 ID: $tweet_id"
    echo ""

    # 打开页面
    echo "1. 打开页面..."
    cd "$WORKSPACE"
    browser action=open targetUrl="$tweet_url" > /dev/null

    # 等待加载
    echo "2. 等待加载..."
    sleep 5

    # 获取快照
    echo "3. 获取页面快照..."
    local snapshot_file="$OUTPUT_DIR/${tweet_id}_tweet_snapshot.json"
    browser action=snapshot depth=5 refs=role > "$snapshot_file"

    # 截图
    echo "4. 截取页面截图..."
    local screenshot=$(browser action=screenshot type="png" 2>&1 | grep "MEDIA:" | cut -d: -f2- | tr -d ' ')
    echo "   截图: $screenshot"

    echo -e "${GREEN}✅ 完成${NC}"
    echo "   快照: $snapshot_file"
}

# 搜索推特
search_twitter() {
    local query="$1"

    echo -e "${BLUE}搜索推特${NC}"
    echo "查询: $query"
    echo ""

    # URL 编码
    local encoded_query=$(echo "$query" | sed 's/ /+/g')

    # 打开页面
    echo "1. 打开搜索页面..."
    cd "$WORKSPACE"
    browser action=open targetUrl="https://x.com/search?q=$encoded_query&src=typed_query" > /dev/null

    # 等待加载
    echo "2. 等待加载..."
    sleep 5

    # 获取快照
    echo "3. 获取页面快照..."
    local snapshot_file="$OUTPUT_DIR/search_${encoded_query}_snapshot.json"
    browser action=snapshot depth=5 refs=role > "$snapshot_file"

    # 截图
    echo "4. 截取页面截图..."
    local screenshot=$(browser action=screenshot type="png" 2>&1 | grep "MEDIA:" | cut -d: -f2- | tr -d ' ')
    echo "   截图: $screenshot"

    echo -e "${GREEN}✅ 完成${NC}"
    echo "   快照: $snapshot_file"
}

# 主入口
case "$1" in
    user)
        if [ -z "$2" ]; then
            echo "错误: 请提供用户名"
            echo "示例: $0 user elonmusk"
            exit 1
        fi
        fetch_user "$2"
        ;;
    tweet)
        if [ -z "$2" ]; then
            echo "错误: 请提供推文 URL"
            echo "示例: $0 tweet https://x.com/elonmusk/status/123456789"
            exit 1
        fi
        fetch_tweet "$2"
        ;;
    search)
        if [ -z "$2" ]; then
            echo "错误: 请提供搜索查询"
            echo "示例: $0 search 'AI technology'"
            exit 1
        fi
        search_twitter "$2"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "错误: 未知命令 '$1'"
        echo ""
        show_help
        exit 1
        ;;
esac

echo ""
echo "💡 提示: 查看生成的 JSON 文件了解详细数据结构"