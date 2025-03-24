FROM python:3.9

# 设置非root用户（Hugging Face Space要求）
RUN useradd -m -u 1000 user
WORKDIR /app

# 复制依赖文件并安装
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# 复制所有项目文件
COPY . /app

# 设置正确的权限
RUN chown -R user:user /app && \
    chmod -R 755 /app && \
    chmod 666 /app/config.json  # 确保 config.json 可写

USER user

# 设置端口（Hugging Face Space默认使用7860端口）
ENV PORT=7860

# 启动命令
CMD ["python", "main.py"]
