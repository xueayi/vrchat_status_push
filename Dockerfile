FROM python:3.12-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制源码
COPY src/ ./src/
COPY main.py .

# 创建数据目录
RUN mkdir -p /app/data

CMD ["python", "main.py"]
