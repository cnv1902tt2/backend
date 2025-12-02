# Hướng Dẫn Deploy Backend lên Render

## Bước 1: Chuẩn Bị Database (PostgreSQL)

### Option A: Sử dụng Neon.tech (Đã có DATABASE_URL trong .env)
✅ Bạn đã có sẵn PostgreSQL database từ Neon.tech trong file `.env`:
```
DATABASE_URL='postgresql://neondb_owner:npg_0RL5afcNplGy@ep-cool-credit-a1qfzj69-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require'
```

### Option B: Tạo PostgreSQL Database mới trên Render (Free)
1. Truy cập: https://dashboard.render.com/
2. Click **New** → **PostgreSQL**
3. Cấu hình:
   - **Name**: `revit-key-db`
   - **Database**: `revit_keys`
   - **User**: `revit_admin`
   - **Region**: `Singapore` (gần Việt Nam nhất)
   - **Plan**: `Free` (0$/month - có giới hạn)
4. Click **Create Database**
5. Đợi vài phút để database được tạo
6. Copy **Internal Database URL** hoặc **External Database URL**

---

## Bước 2: Chuẩn Bị Code

### 2.1. Kiểm tra file cần thiết
✅ Các file đã được tạo sẵn:
- `requirements.txt` - Dependencies Python
- `render.yaml` - Cấu hình Render
- `Procfile` - Lệnh khởi động
- `runtime.txt` - Python version
- `.gitignore` - Loại trừ file không cần thiết

### 2.2. Push code lên GitHub
```cmd
cd d:\Workspace\Revit\Web\backend

# Khởi tạo git (nếu chưa có)
git init

# Add tất cả files
git add .

# Commit
git commit -m "Initial backend deployment for Render"

# Tạo repository trên GitHub (https://github.com/new)
# Sau đó link repository:
git remote add origin https://github.com/YOUR_USERNAME/revit-key-backend.git

# Push code
git branch -M main
git push -u origin main
```

**⚠️ LƯU Ý:** Đảm bảo file `.env` KHÔNG được push lên GitHub (đã có trong `.gitignore`)

---

## Bước 3: Deploy lên Render

### 3.1. Tạo Web Service
1. Truy cập: https://dashboard.render.com/
2. Click **New** → **Web Service**
3. Connect GitHub repository của bạn
4. Chọn repository `revit-key-backend`

### 3.2. Cấu hình Web Service
**Basic Settings:**
- **Name**: `revit-key-backend`
- **Region**: `Singapore` (hoặc Oregon)
- **Branch**: `main`
- **Root Directory**: (để trống hoặc nhập `backend` nếu có thư mục cha)
- **Runtime**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

**Plan:**
- Chọn **Free** (0$/month - có giới hạn)

### 3.3. Cấu hình Environment Variables
Click **Advanced** → **Add Environment Variable**, thêm các biến sau:

#### Bắt buộc:
```
DATABASE_URL = postgresql://neondb_owner:npg_0RL5afcNplGy@ep-cool-credit-a1qfzj69-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
```
*(Hoặc URL từ Render PostgreSQL nếu dùng Option B)*

```
JWT_SECRET_KEY = 9f7d6e4a2b3c1d8e9f0a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e
```

#### Email (SMTP) - Gmail:
```
MAIL_HOST = smtp.gmail.com
MAIL_PORT = 587
MAIL_USERNAME = cnv1902@gmail.com
MAIL_PASSWORD = voof ymlb afdm kfrj
MAIL_FROM_ADDRESS = cnv1902@gmail.com
MAIL_FROM_NAME = KEY MANAGEMENT ADMINISTRATOR
```

#### Optional (có giá trị mặc định):
```
CORS_ORIGINS = *
ACCESS_TOKEN_EXPIRE_MINUTES = 60
OTP_EXPIRE_MINUTES = 10
```

### 3.4. Deploy
1. Click **Create Web Service**
2. Đợi 5-10 phút để Render build và deploy
3. Theo dõi logs trong tab **Logs**

---

## Bước 4: Kiểm Tra Deployment

### 4.1. URL của bạn
Sau khi deploy thành công, bạn sẽ có URL:
```
https://revit-key-backend.onrender.com
```

### 4.2. Test API
**Test health check:**
```bash
curl https://revit-key-backend.onrender.com/
```
Kết quả: `{"status":"ok"}`

**Test login:**
```bash
curl -X POST https://revit-key-backend.onrender.com/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"admin\",\"password\":\"@Abc12324\"}"
```

**Test create key:**
```bash
# Lấy token từ login trước
curl -X POST https://revit-key-backend.onrender.com/keys/create \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d "{\"type\":\"trial\",\"note\":\"Test key\"}"
```

---

## Bước 5: Cập Nhật Frontend

Cập nhật file `frontend/src/services/api.js` để trỏ đến backend Render:

```javascript
const API_BASE_URL = process.env.REACT_APP_API_URL || 'https://revit-key-backend.onrender.com';
```

Hoặc tạo file `frontend/.env`:
```
REACT_APP_API_URL=https://revit-key-backend.onrender.com
```

---

## Bước 6: Monitoring & Maintenance

### 6.1. Xem Logs
- Truy cập: https://dashboard.render.com/
- Chọn service `revit-key-backend`
- Tab **Logs** để xem real-time logs

### 6.2. Restart Service
- Tab **Settings** → **Manual Deploy** → **Deploy latest commit**
- Hoặc **Suspend** và **Resume** service

### 6.3. Free Plan Limitations
⚠️ **Render Free Plan:**
- Service sẽ **tự động sleep** sau 15 phút không hoạt động
- Request đầu tiên sau khi sleep sẽ mất 30-60s để wake up
- 750 giờ/tháng free (đủ cho 1 service chạy liên tục)
- PostgreSQL free: 90 ngày, sau đó phải upgrade hoặc tạo mới

### 6.4. Giữ Service Luôn Active (Optional)
Sử dụng cron job hoặc UptimeRobot để ping API mỗi 10 phút:
```
https://revit-key-backend.onrender.com/
```

---

## Troubleshooting

### Lỗi: "Application failed to start"
- Kiểm tra logs trong tab **Logs**
- Đảm bảo `requirements.txt` có đúng dependencies
- Kiểm tra Python version trong `runtime.txt`

### Lỗi: "Database connection failed"
- Kiểm tra `DATABASE_URL` trong Environment Variables
- Đảm bảo PostgreSQL database đang chạy
- Nếu dùng Render PostgreSQL, dùng **Internal Database URL**

### Lỗi: "Port binding failed"
- Đảm bảo start command có `--port $PORT`
- Render tự động gán port, không được hardcode

### Lỗi: "CORS blocked"
- Kiểm tra `CORS_ORIGINS` environment variable
- Thêm frontend URL vào CORS nếu cần
- Hoặc dùng `*` để allow tất cả

---

## Chi Phí

### Free Plan (Đủ dùng cho development):
- **Web Service**: Free (có sleep sau 15 phút)
- **PostgreSQL**: Free 90 ngày đầu (256 MB, 1GB storage)
- **Total**: $0/month

### Paid Plan (Nếu cần production):
- **Starter Web Service**: $7/month (512 MB RAM, no sleep)
- **Starter PostgreSQL**: $7/month (256 MB RAM, 1 GB storage)
- **Total**: $14/month

---

## Tài Liệu Tham Khảo

- Render Documentation: https://render.com/docs
- FastAPI Deployment: https://fastapi.tiangolo.com/deployment/
- PostgreSQL on Render: https://render.com/docs/databases
- Environment Variables: https://render.com/docs/environment-variables

---

## Checklist Deploy

- [ ] Tạo PostgreSQL database (Neon hoặc Render)
- [ ] Push code lên GitHub
- [ ] Tạo Web Service trên Render
- [ ] Cấu hình Environment Variables
- [ ] Deploy và theo dõi logs
- [ ] Test API endpoints
- [ ] Cập nhật frontend URL
- [ ] Test toàn bộ flow từ frontend → backend

**🎉 Chúc bạn deploy thành công!**
