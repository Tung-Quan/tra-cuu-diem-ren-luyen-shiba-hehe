# 🌐 Port Forwarding Configuration Guide

## Tình Huống: Frontend đã forward port

Khi bạn forward port cho frontend (VD: expose localhost:5173 ra public), bạn cần cấu hình để frontend có thể gọi được backend.

## 📋 Các Cách Giải Quyết

### **Cách 1: Trỏ thẳng đến Backend URL (Recommended)**

Sửa file `frontend/.env`:

```properties
VITE_API_BASE_URL=/api
VITE_API_TIMEOUT=60000000000

# Uncomment và sửa URL phù hợp:
VITE_API_URL=http://YOUR_BACKEND_IP:8000
```

**Ví dụ**:
```properties
# Nếu backend chạy trên máy local
VITE_API_URL=http://localhost:8000

# Nếu backend chạy trên IP trong LAN
VITE_API_URL=http://192.168.1.100:8000

# Nếu backend đã deploy lên domain
VITE_API_URL=https://api.yourdomain.com
```

**Sau đó restart frontend**:
```powershell
# Ctrl+C để stop
cd frontend
npm run dev
```

---

### **Cách 2: Forward cả Backend port**

Nếu bạn đang dùng VS Code port forwarding:

1. **Forward backend port 8000** (ngoài port 5173 đã forward)
2. **Copy public URL** của backend (VD: `https://xxx-8000.app.github.dev`)
3. **Sửa `.env`**:
```properties
VITE_API_URL=https://xxx-8000.app.github.dev
```

---

### **Cách 3: Sửa Vite Proxy (nếu dùng proxy)**

Nếu muốn dùng proxy thay vì trỏ thẳng, sửa `vite.config.ts`:

```typescript
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://YOUR_BACKEND_URL:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
});
```

**Lưu ý**: Cách này chỉ hoạt động khi dùng `npm run dev`, không hoạt động sau khi build production.

---

## 🔧 CORS Configuration (Nếu cần)

Nếu frontend và backend ở khác domain, bạn cần enable CORS trong backend.

Sửa `backend/backend.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Thêm CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://your-frontend-url.com",
        "*",  # Cho phép tất cả (chỉ dùng khi dev)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Restart backend sau khi sửa**:
```powershell
# Ctrl+C để stop backend
.venv\Scripts\python.exe -m uvicorn backend.backend:app --reload --host 0.0.0.0 --port 8000
```

**Lưu ý**: `--host 0.0.0.0` cho phép truy cập từ ngoài localhost.

---

## 🧪 Testing

### 1. Test Backend từ Browser
Mở browser và truy cập:
```
http://YOUR_BACKEND_URL:8000/health
```

Nên thấy:
```json
{"ok":true,"rows":344,"sheets":4,"links":637}
```

### 2. Test Frontend → Backend connection
Mở frontend, mở Console (F12), chạy:
```javascript
fetch('/api/health')
  .then(r => r.json())
  .then(console.log)
```

Hoặc nếu dùng direct URL:
```javascript
fetch('http://YOUR_BACKEND_URL:8000/health')
  .then(r => r.json())
  .then(console.log)
```

---

## 📝 Quick Reference

### Development (Local)
```properties
# frontend/.env
VITE_API_URL=http://localhost:8000
```

### Production / Deployed
```properties
# frontend/.env
VITE_API_URL=https://api.yourdomain.com
```

### VS Code Port Forwarding
```properties
# frontend/.env
VITE_API_URL=https://xxx-8000.app.github.dev
```

---

## ⚠️ Troubleshooting

### Lỗi: "Network Error" hoặc "Failed to fetch"

**Nguyên nhân**: CORS hoặc backend không accessible

**Giải quyết**:
1. Check backend có chạy không: `curl http://localhost:8000/health`
2. Enable CORS trong backend (xem phần CORS Configuration)
3. Đảm bảo `VITE_API_URL` đúng
4. Restart cả frontend và backend

### Lỗi: "404 Not Found" trên API endpoints

**Nguyên nhân**: Proxy config sai hoặc URL sai

**Giải quyết**:
1. Check `VITE_API_URL` có đúng không
2. Thử truy cập trực tiếp: `http://YOUR_BACKEND_URL:8000/mysql/ctv/count`
3. Check console log trong browser để xem URL thực tế được gọi

### Frontend không nhận `.env` changes

**Giải quyết**:
1. Stop frontend (Ctrl+C)
2. Restart: `npm run dev`
3. Hard refresh browser: Ctrl+Shift+R

---

## 📋 Complete Setup Checklist

- [ ] Backend đang chạy: `http://localhost:8000/health` returns OK
- [ ] Sửa `frontend/.env` với `VITE_API_URL` đúng
- [ ] Restart frontend: `npm run dev`
- [ ] (Nếu cần) Enable CORS trong backend
- [ ] (Nếu cần) Backend listen trên `0.0.0.0` thay vì `127.0.0.1`
- [ ] Test API call từ frontend console
- [ ] Test MySQL search page: `http://localhost:5173/mysql`

---

## 🎯 Recommended Configuration

**Development (localhost)**:
```properties
# frontend/.env
VITE_API_URL=http://localhost:8000
```

```powershell
# Backend
.venv\Scripts\python.exe -m uvicorn backend.backend:app --reload --host 127.0.0.1 --port 8000

# Frontend
cd frontend
npm run dev
```

**Production / Remote Access**:
```properties
# frontend/.env
VITE_API_URL=http://YOUR_SERVER_IP:8000
```

```powershell
# Backend (accept connections from outside)
.venv\Scripts\python.exe -m uvicorn backend.backend:app --host 0.0.0.0 --port 8000
```

---

**Tạo ngày**: 2025-10-20
**File**: `PORT_FORWARDING_GUIDE.md`
