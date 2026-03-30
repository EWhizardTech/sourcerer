# sourcerer-backend
One place to learn and grow

Usage
On a machine with GPU (dev machine):

```
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

```powershell
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up
```

On a machine without GPU (CI, cloud, etc.):
```powershell
docker compose up
```



```
# first time on a new machine — pull the base so cache_from works
docker pull premdharshan/sourcerer-base:latest

# then just normal compose — builds in ~30 seconds
docker compose up --build
```

```
# after editing pyproject.toml or uv.lock
docker build -f Dockerfile.base -t premdharshan/sourcerer-base:latest .
docker push premdharshan/sourcerer-base:latest
```




docker compose -f docker-compose.infra.yml up

