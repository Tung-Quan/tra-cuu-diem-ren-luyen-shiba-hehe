# ⚡ Quick Setup - Port Forwarding

## Tình huống của bạn

✅ **Frontend**: Đã forward port (VD: VS Code Port Forwarding)
❓ **Backend**: Cần cấu hình để frontend gọi được

---

## 🚀 Giải pháp nhanh nhất

### Bước 1: Xác định Backend URL

Bạn có 3 options:

**Option A: Backend trên localhost (same machine)**
- URL: `http://localhost:8000`

**Option B: Backend forward port (VS Code/ngrok)**
- Forward backend port 8000
- URL: `https://xxx-8000.app.github.dev` (copy từ VS Code)

**Option C: Backend trên server/IP khác**
- URL: `http://192.168.1.X:8000` (thay X bằng IP thật)

---

### Bước 2: Sửa Frontend Config

Mở file `frontend/.env` và thêm:

```properties
VITE_API_URL=http://localhost:8000
```

**Thay `http://localhost:8000` bằng URL backend thật của bạn** (từ Bước 1)

**Ví dụ**:
```properties
# Nếu dùng VS Code port forwarding cho backend
VITE_API_URL=https://xxx-8000.app.github.dev

# Nếu backend trên IP khác
VITE_API_URL=http://192.168.1.100:8000
```

---

### Bước 3: Restart Frontend

```powershell
# Stop frontend (Ctrl+C)
# Rồi start lại:
cd frontend
npm run dev
```

---

### Bước 4: Test

Mở browser console (F12) và chạy:

```javascript
fetch('/api/health').then(r => r.json()).then(console.log)
```

Nếu thấy `{ok: true, rows: 344, ...}` → **Thành công!** ✅

---

## 🔧 Nếu Backend cần accept remote connections

Nếu backend đang chạy với `--host 127.0.0.1`, cần đổi sang `0.0.0.0`:

```powershell
# Stop backend (Ctrl+C)
# Rồi start lại với:
.venv\Scripts\python.exe -m uvicorn backend.backend:app --reload --host 0.0.0.0 --port 8000
```

`0.0.0.0` cho phép truy cập từ ngoài localhost.

---

## 📋 Complete Example

**Scenario**: Frontend forward qua VS Code, backend trên localhost

1. **Forward backend port 8000** trong VS Code
2. **Copy forwarded URL**: `https://abc123-8000.app.github.dev`
3. **Sửa `frontend/.env`**:
   ```properties
   VITE_API_URL=https://abc123-8000.app.github.dev
   ```
4. **Restart frontend**:
   ```powershell
   cd frontend
   npm run dev
   ```
5. **Test**: Mở `http://localhost:5173/mysql` và search

---

## ✅ Checklist

- [ ] Xác định backend URL (localhost/forwarded/IP)
- [ ] Sửa `frontend/.env` với `VITE_API_URL`
- [ ] Restart frontend (`npm run dev`)
- [ ] Test API call: `fetch('/api/health')`
- [ ] Test MySQL search page

---

## 💡 Tips

- Backend đã có CORS enabled (`allow_origins=["*"]`), không cần sửa gì thêm
- Nếu dùng HTTPS cho backend, frontend phải dùng HTTPS (hoặc localhost)
- VS Code Port Forwarding tự động cung cấp HTTPS
- File `.env` chỉ load khi start frontend, nhớ restart sau mỗi thay đổi

---

**Vấn đề của bạn**: Frontend đã forward → **Giải pháp**: Sửa `VITE_API_URL` trong `.env` 🎯
