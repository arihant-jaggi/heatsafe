# Base on OSGeo's official GDAL image: GDAL, PROJ (>=9.2.0), and GEOS are all
# pre-installed at matched, coherent versions. python:3.11-slim's Debian-packaged
# PROJ (9.1.1) is too old for pyproj>=3.7, which caused the previous build to fail.
FROM ghcr.io/osgeo/gdal:ubuntu-small-3.8.0

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first so this layer is cached across code-only changes.
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port $PORT"]
