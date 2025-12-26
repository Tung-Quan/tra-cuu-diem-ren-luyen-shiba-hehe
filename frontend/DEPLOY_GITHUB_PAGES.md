# Deploy Frontend lên GitHub Pages

## Chuẩn bị

1. **Cập nhật `.env.production`**  
   Mở file `frontend/.env.production` và thay `YOUR_BACKEND_URL` bằng URL backend thật (ví dụ: `https://your-api.onrender.com/`):
   ```bash
   VITE_API_URL=https://your-backend-url.com/
   ```

2. **Kiểm tra `base` trong `vite.config.ts`**  
   Đã được set `base: '/tracuudiemrenluyen/'` — phù hợp với URL `Tung-Quan.github.io/tracuudiemrenluyen/`.

## Phương án 1: Deploy bằng `gh-pages` package (khuyến nghị)

### Cài đặt
```bash
cd frontend
npm install --save-dev gh-pages
```

### Thêm script vào `package.json`
Mở `frontend/package.json` và thêm:
```json
{
  "scripts": {
    "predeploy": "npm run build",
    "deploy": "gh-pages -d dist"
  }
}
```

### Deploy
```bash
npm run deploy
```

Lệnh này sẽ:
- Build production (sử dụng `.env.production`)
- Push nội dung `dist/` lên branch `gh-pages`

### Cấu hình GitHub Pages
1. Vào **Settings** → **Pages** của repo `tra-cuu-diem-ren-luyen-shiba-hehe`
2. **Source**: chọn **Deploy from a branch**
3. **Branch**: chọn `gh-pages` / `/ (root)`
4. Sau vài phút, site sẽ live tại: `https://Tung-Quan.github.io/tracuudiemrenluyen/`

---

## Phương án 2: Deploy từ thư mục `docs` trên branch `main`

### Cấu hình `vite.config.ts`
Thêm `outDir`:
```typescript
build: {
  outDir: '../docs',  // hoặc 'docs' nếu muốn cùng cấp
  // ... các config khác
}
```

### Build và commit
```bash
cd frontend
npm run build
cd ..
git add docs
git commit -m "Deploy: build frontend to docs/"
git push origin main
```

### Cấu hình GitHub Pages
1. **Settings** → **Pages**
2. **Source**: `Deploy from a branch`
3. **Branch**: `main` / `/docs`

---

## Lưu ý quan trọng

### CORS Backend
Backend cần cho phép origin của GitHub Pages:
```python
# backend/app.py (FastAPI)
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://tung-quan.github.io"  # thêm domain GitHub Pages
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Kiểm tra trước khi deploy
```bash
# Build local và kiểm tra
npm run build
npx vite preview --base /tracuudiemrenluyen/
```

Truy cập `http://localhost:4173/tracuudiemrenluyen/` để test.

---

## Cập nhật sau này
Mỗi lần thay đổi code:
```bash
npm run deploy
```

Hoặc với phương án 2:
```bash
npm run build
git add docs && git commit -m "Update build" && git push
```
