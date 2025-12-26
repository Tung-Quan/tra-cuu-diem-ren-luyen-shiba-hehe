// src/pages/ContactPage.tsx
import { useNavigate } from "react-router-dom";

export default function ContactPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-100">
      {/* Header */}
      <div className="bg-white border-b sticky top-0 z-10 shadow-sm">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center gap-4">
          <button
            onClick={() => navigate("/")}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            <span className="font-medium">Quay lại</span>
          </button>
          <div className="flex-1"></div>
          <h1 className="text-xl font-bold text-gray-900">Liên Hệ & Hỗ Trợ</h1>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto px-6 py-12">
        <div className="space-y-8">
          {/* Support Section */}
          <div className="bg-white rounded-3xl shadow-xl p-8 border border-slate-100">
            <div className="text-center mb-8">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-yellow-100 rounded-full mb-4">
                <svg className="w-8 h-8 text-yellow-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                </svg>
              </div>
              <h2 className="text-3xl font-bold text-gray-900 mb-2">Ủng Hộ Dự Án</h2>
              <p className="text-gray-600">
                Nếu dự án này hữu ích với bạn, hãy mua cho tôi một tách cà phê ☕
              </p>
            </div>

            <div className="flex flex-col items-center gap-6">
              {/* QR Code */}
              <div className="bg-white p-6 rounded-2xl border-4 border-gray-100 shadow-lg">
                <img
                  src={`${import.meta.env.BASE_URL}bmc_qr.png`}
                  alt="Buy Me a Coffee QR Code"
                  className="w-64 h-64"
                />
                <p className="text-center text-sm text-gray-500 mt-4">
                  Quét mã QR để ủng hộ
                </p>
              </div>

              {/* Buy Me a Coffee Link */}
              <a
                href="https://buymeacoffee.com/tungquan32w"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-3 px-8 py-4 bg-gradient-to-r from-yellow-400 to-yellow-500 hover:from-yellow-500 hover:to-yellow-600 text-gray-900 font-bold rounded-2xl shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105"
              >
                <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M20.216 6.415l-.132-.666c-.119-.598-.388-1.163-.766-1.541-.777-.777-1.98-1.208-3.302-1.208H7.984c-1.322 0-2.525.431-3.302 1.208-.378.378-.647.943-.766 1.541l-.132.666c-.247 1.363.416 2.724 1.633 3.379l.32.207c.155.099.309.198.459.305.069.05.125.092.175.128.05.036.088.061.113.073a3.042 3.042 0 001.587.88l.148.04c.076.021.146.036.213.047.068.011.13.016.184.017h3.657c.054-.001.116-.006.184-.017.067-.011.137-.026.213-.047l.148-.04c.683-.184 1.257-.535 1.587-.88.025-.012.063-.037.113-.073.05-.036.106-.078.175-.128.15-.107.304-.206.459-.305l.32-.207c1.217-.655 1.88-2.016 1.633-3.379z"/>
                  <path d="M8 11h8v10H8z"/>
                </svg>
                Mua Cho Tôi Một Ly Cà Phê
              </a>

              <div className="text-center text-sm text-gray-500">
                <p>Hoặc truy cập:</p>
                <a
                  href="https://buymeacoffee.com/tungquan32w"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:text-blue-800 hover:underline font-mono"
                >
                  buymeacoffee.com/tungquan32w
                </a>
              </div>
            </div>
          </div>

          {/* Feedback Section */}
          <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-3xl shadow-xl p-8 border border-blue-100">
            <div className="text-center mb-6">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-100 rounded-full mb-4">
                <svg className="w-8 h-8 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
              </div>
              <h2 className="text-3xl font-bold text-gray-900 mb-2">Báo Lỗi & Góp Ý</h2>
              <p className="text-gray-700 max-w-2xl mx-auto">
                Gặp vấn đề hoặc có ý tưởng cải tiến? Hãy cho chúng tôi biết!
              </p>
            </div>

            <div className="flex flex-col items-center gap-4">
              <a
                href="https://forms.gle/uPViWCfnZF3Wo2Ee7"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-3 px-8 py-4 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-2xl shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105"
              >
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Gửi Feedback
              </a>

              <div className="text-center text-sm text-gray-600">
                <p>Hoặc truy cập form:</p>
                <a
                  href="https://forms.gle/uPViWCfnZF3Wo2Ee7"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:text-blue-800 hover:underline font-mono break-all"
                >
                  forms.gle/uPViWCfnZF3Wo2Ee7
                </a>
              </div>
            </div>
          </div>

          {/* Features Section */}
          <div className="bg-gradient-to-br from-emerald-50 to-teal-50 rounded-3xl shadow-xl p-8 border border-emerald-100">
            <div className="text-center mb-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-3">Tính Năng Hệ Thống</h2>
              <p className="text-gray-700 max-w-3xl mx-auto leading-relaxed">
                Hệ thống hỗ trợ xử lý API <span className="font-semibold text-emerald-700">Google Docs, Google Sheets, Excel, Word</span> và trích xuất thông tin từ <span className="font-semibold text-emerald-700">link có hình ảnh</span>. 
                <span className="text-sm text-gray-600 block mt-2">(Tính năng PDF đang được phát triển)</span>
              </p>
            </div>
          </div>

          {/* Info Cards */}
          <div className="grid md:grid-cols-3 gap-4">
            <div className="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm">
              <div className="flex items-start gap-3">
                <div className="flex items-center justify-center w-10 h-10 bg-green-100 rounded-lg flex-shrink-0">
                  <svg className="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 mb-1">Nhanh Chóng</h3>
                  <p className="text-sm text-gray-600">Tìm kiếm trong vài mili giây</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm">
              <div className="flex items-start gap-3">
                <div className="flex items-center justify-center w-10 h-10 bg-purple-100 rounded-lg flex-shrink-0">
                  <svg className="w-5 h-5 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 mb-1">Bảo Mật</h3>
                  <p className="text-sm text-gray-600">Dữ liệu được bảo vệ an toàn</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm">
              <div className="flex items-start gap-3">
                <div className="flex items-center justify-center w-10 h-10 bg-orange-100 rounded-lg flex-shrink-0">
                  <svg className="w-5 h-5 text-orange-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 mb-1">Cập Nhật</h3>
                  <p className="text-sm text-gray-600">Liên tục cải tiến tính năng</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="bg-slate-900 text-slate-300 py-8 mt-16">
        <div className="max-w-6xl mx-auto px-6 text-center">
          <p className="text-sm mb-2">
            © 2024 Hệ Thống Tra Cứu Sinh Viên. All rights reserved.
          </p>
          <p className="text-xs text-slate-400">
            Made with ❤️ by a passionate developer.
          </p>
        </div>
      </footer>
    </div>
  );
}
