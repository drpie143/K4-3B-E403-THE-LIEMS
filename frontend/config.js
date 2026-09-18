/*
 * Địa chỉ backend cho giao diện.
 *
 * - Chạy trên một máy (backend phục vụ luôn frontend tại /app/index.html): để trống.
 * - Deploy tách đôi (frontend trên Vercel, backend trên Render):
 *     • Nếu đã bật rewrites trong vercel.json thì vẫn để trống — Vercel chuyển tiếp
 *       /api và /health sang Render, trình duyệt thấy cùng origin nên không dính CORS.
 *     • Nếu không dùng rewrites thì điền thẳng URL Render vào đây, ví dụ:
 *         window.VLEARN_API_BASE = "https://vlearn-tutor-api.onrender.com";
 *       và nhớ đặt ALLOWED_ORIGINS bên Render cho đúng tên miền Vercel.
 *
 * File này KHÔNG chứa bí mật: mọi API key chỉ nằm ở backend.
 */
window.VLEARN_API_BASE = "";
