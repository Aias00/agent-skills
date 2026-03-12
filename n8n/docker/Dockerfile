FROM n8nio/n8n:latest

USER root

RUN apk add --no-cache \
    bash \
    curl \
    git \
    python3 \
    py3-pip \
    chromium \
    nss \
    freetype \
    harfbuzz \
    ttf-freefont \
    udev

ENV BUN_INSTALL=/opt/bun
RUN curl -fsSL https://bun.sh/install | bash && ln -sf /opt/bun/bin/bun /usr/local/bin/bun

RUN if [ -x /usr/bin/chromium-browser ]; then \
      ln -sf /usr/bin/chromium-browser /usr/bin/google-chrome; \
    elif [ -x /usr/bin/chromium ]; then \
      ln -sf /usr/bin/chromium /usr/bin/google-chrome && \
      ln -sf /usr/bin/chromium /usr/bin/chromium-browser; \
    fi

COPY post-to-xhs/requirements.txt /tmp/post-to-xhs-requirements.txt
COPY toutiao-publisher/requirements.txt /tmp/toutiao-publisher-requirements.txt
COPY tencent-dev-community-publisher/requirements.txt /tmp/tencent-dev-community-publisher-requirements.txt

RUN python3 -m pip install --break-system-packages --no-cache-dir \
    -r /tmp/post-to-xhs-requirements.txt \
    -r /tmp/toutiao-publisher-requirements.txt \
    -r /tmp/tencent-dev-community-publisher-requirements.txt

COPY wechat-publisher/package.json /tmp/wechat-package.json
COPY post-to-xhs/scripts/package.json /tmp/post-to-xhs-package.json
COPY post-to-xhs/scripts/package-lock.json /tmp/post-to-xhs-package-lock.json

COPY n8n/docker/entrypoint.sh /usr/local/bin/ai-hotspot-n8n-entrypoint.sh
RUN chmod +x /usr/local/bin/ai-hotspot-n8n-entrypoint.sh

USER node

ENV HOTSPOT_WORKSPACE=/workspace/agent-skills
ENV WECHAT_BROWSER_CHROME_PATH=/usr/bin/google-chrome
ENV CHROME_EXECUTABLE=/usr/bin/google-chrome
ENV XHS_PROFILES_BASE=/workspace/runtime/xhs-profiles
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

WORKDIR /workspace/agent-skills

ENTRYPOINT ["/usr/local/bin/ai-hotspot-n8n-entrypoint.sh"]
CMD ["n8n"]
