# 第一步：使用Python 3.9作为基础镜像
FROM python:3.9-slim

# 第二步：设置工作目录
WORKDIR /app

# 第三步：安装系统依赖
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    wget \
    sudo \
    libfuse2 \
    gpg \
    procps \
    fuse \
    && rm -rf /var/lib/apt/lists/*

# 第四步：安装MEGAcmd
RUN wget https://mega.nz/linux/repo/Debian_12/amd64/megacmd-Debian_12_amd64.deb && \
    apt install -y ./megacmd-Debian_12_amd64.deb && \
    rm megacmd-Debian_12_amd64.deb

# 第五步：复制项目文件
COPY . /app/

# 第六步：安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 第七步：创建配置目录和文件
RUN mkdir -p /app/config && \
    if [ ! -f /app/config/config.yaml ]; then \
    cp /app/config/config.yaml.example /app/config/config.yaml; \
    fi

# 第八步：设置环境变量
ENV PYTHONUNBUFFERED=1

# 第九步：设置启动命令
CMD ["python", "main.py"]
