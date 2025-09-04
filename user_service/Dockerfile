# 1️⃣ Base image: slim Python for smaller image size
FROM python:3.11-slim

# 2️⃣ Working directory inside the container
WORKDIR /app

# 3️⃣ Install system dependencies needed for mysqlclient, not needed for python:3.11-slim
#RUN apk add --no-cache \
#    gcc \
#    musl-dev \
#    python3-dev \
#    mariadb-dev \
#    pkgconfig \
#    py3-pip

# 4️⃣ Copy requirements first to leverage Docker layer caching
COPY requirements.txt ./requirements.txt

# 5️⃣ Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 6️⃣ Copy application code
COPY . ./user_service
#COPY . .

ENV PYTHONPATH=/app

# 7️⃣ Expose port Flask will run on
EXPOSE 5001

# 8️⃣ Start the Flask app
CMD ["python", "user_service/run.py"]

# 🚫 Commented out ENTRYPOINT to avoid overriding CMD
# ENTRYPOINT ["top", "-b"]