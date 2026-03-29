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
