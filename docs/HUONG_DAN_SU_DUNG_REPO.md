# Hướng dẫn dùng Repo (dành cho người mới dùng Git/GitHub)

Tài liệu này viết cho người **chưa quen Git**, chỉ cần đọc từ trên xuống và làm theo là
đủ để đóng góp vào repo. Nếu bạn đã rành Git, đọc `CONTRIBUTING.md` và `BRANCHING.md` sẽ
nhanh hơn.

## 1. Vài khái niệm cần hiểu trước (bằng ví dụ, không phải định nghĩa hàn lâm)

| Khái niệm | Hiểu đơn giản như |
|---|---|
| **Repo (repository)** | Một thư mục dự án dùng chung, có lịch sử thay đổi, lưu trên GitHub |
| **Clone** | Tải cả repo về máy mình lần đầu |
| **Branch (nhánh)** | Một "bản nháp riêng" của code, để bạn sửa mà không ảnh hưởng tới bản chính (`main`) |
| **Commit** | Một "lần lưu" thay đổi, kèm ghi chú ngắn bạn đã làm gì |
| **Push** | Đẩy các commit từ máy mình lên GitHub |
| **Pull** | Tải các thay đổi mới nhất từ GitHub về máy mình |
| **Pull Request (PR)** | Đề nghị "gộp nhánh của tôi vào `main`", để người khác xem qua trước khi đồng ý |
| **Merge** | Gộp nhánh của bạn vào `main` sau khi PR được duyệt |

Nguyên tắc quan trọng nhất: **không ai code trực tiếp lên `main`**. Mọi người luôn làm
việc trên một branch riêng của mình, xong thì mở PR để gộp vào.

## 2. Cài đặt — chọn 1 trong 2 cách

### Cách A — GitHub Desktop (khuyên dùng nếu bạn chưa quen dòng lệnh)

1. Tải tại <https://desktop.github.com/>, cài đặt, đăng nhập bằng tài khoản GitHub của bạn.
2. Vào repo trên trình duyệt: <https://github.com/Levianth146/Telegram-bot-for-investment-signal>
3. Bấm nút xanh **Code** → **Open with GitHub Desktop**.
4. Chọn thư mục trên máy để lưu repo → bấm **Clone**.

Từ giờ, mọi thao tác (tạo branch, commit, push, mở PR) đều có thể làm bằng nút bấm trong
GitHub Desktop, không cần gõ lệnh. Các bước ở mục 4 bên dưới có ghi chú riêng cho GitHub
Desktop.

### Cách B — Dòng lệnh (Git CLI)

1. Cài Git: <https://git-scm.com/downloads>
2. Kiểm tra đã cài xong: mở terminal, gõ `git --version`
3. Cấu hình tên/email một lần duy nhất:
   ```bash
   git config --global user.name "Tên bạn"
   git config --global user.email "email-github-của-bạn"
   ```

## 3. Lấy code về máy lần đầu (chỉ làm 1 lần)

**GitHub Desktop:** đã làm ở bước Cách A phần 3–4 ở trên, bỏ qua bước này.

**Dòng lệnh:**
```bash
git clone https://github.com/Levianth146/Telegram-bot-for-investment-signal.git
cd Telegram-bot-for-investment-signal
```

## 4. Quy trình làm việc hằng ngày — làm đúng thứ tự này mỗi lần

### Bước 0 — Nhận việc

Vào tab **Issues** trên GitHub, tìm issue thuộc module bạn phụ trách (xem bảng phân công
trong `docs/ARCHITECTURE.md`), bấm **Assign yourself**. Nếu chưa có issue cho việc bạn định
làm, tạo issue mới trước, mô tả ngắn gọn cần làm gì.

### Bước 1 — Cập nhật `main` mới nhất trước khi bắt đầu

Luôn làm bước này trước khi tạo branch mới, để không bị code trên bản cũ.

- **GitHub Desktop:** chọn nhánh `main` ở góc trên, bấm **Fetch origin** rồi **Pull origin**.
- **Dòng lệnh:**
  ```bash
  git checkout main
  git pull origin main
  ```

### Bước 2 — Tạo branch mới cho việc của bạn

Đặt tên theo mẫu `feature/<số-issue>-<mô-tả-ngắn>`, ví dụ `feature/12-garch-sizing`.

- **GitHub Desktop:** menu **Branch → New Branch**, đặt tên, bấm **Create Branch**.
- **Dòng lệnh:**
  ```bash
  git checkout -b feature/12-garch-sizing
  ```

### Bước 3 — Code

Mở thư mục repo bằng VS Code (hoặc editor bạn quen), sửa file trong đúng thư mục module
của bạn (xem mục 5 bên dưới). Chạy thử/test nếu có thể.

### Bước 4 — Lưu lại (commit)

- **GitHub Desktop:** tab bên trái hiện danh sách file đã đổi, tick chọn file, gõ một dòng
  mô tả ngắn ở ô "Summary" (ví dụ: "Thêm hàm tính GARCH sizing"), bấm **Commit to
  feature/12-garch-sizing**.
- **Dòng lệnh:**
  ```bash
  git add .
  git commit -m "Thêm hàm tính GARCH sizing"
  ```

Có thể commit nhiều lần trong lúc làm việc — không cần đợi xong hẳn mới commit.

### Bước 5 — Đẩy lên GitHub (push)

- **GitHub Desktop:** bấm **Push origin** ở thanh trên cùng.
- **Dòng lệnh:**
  ```bash
  git push origin feature/12-garch-sizing
  ```

### Bước 6 — Mở Pull Request (PR)

- **GitHub Desktop:** sau khi push, sẽ có nút **Create Pull Request** hiện ra — bấm vào,
  trình duyệt sẽ mở trang GitHub để bạn hoàn tất.
- **Trên trình duyệt (cả hai cách đều cần bước này):**
  1. Vào repo trên GitHub, sẽ thấy banner vàng "Compare & pull request" — bấm vào.
  2. Điền theo mẫu có sẵn (issue liên quan, thay đổi gì, cách test — xem
     `.github/PULL_REQUEST_TEMPLATE.md`).
  3. Bấm **Create pull request**.
  4. Ở cột phải, mục **Reviewers**, chọn 1 người trong nhóm để review.

### Bước 7 — Chờ review, sửa nếu cần, rồi merge

- Nếu reviewer để lại comment yêu cầu sửa: sửa code trên máy, lặp lại Bước 4–5 (commit +
  push vào **cùng branch cũ**, không cần tạo branch mới) — PR sẽ tự cập nhật.
- Khi CI (dấu tick xanh) chạy xong và reviewer bấm **Approve**: bấm **Squash and merge**
  trên GitHub để gộp vào `main`.
- Sau khi merge, xóa branch (GitHub sẽ có nút **Delete branch** ngay đó).

### Bước 8 — Quay lại Bước 1 cho việc tiếp theo

Luôn `pull` lại `main` mới nhất trước khi bắt đầu một task mới.

## 5. Tôi nên sửa file ở đâu?

Xem bảng phân công trong `docs/ARCHITECTURE.md`, nhưng tóm tắt nhanh:

| Bạn làm về... | Sửa trong thư mục |
|---|---|
| Dữ liệu BCTC, giá, cache | `data/`, `store/` |
| Growth/Quality/Safety/Valuation | `fundamental_filter/` |
| Regime, xu hướng giá (Kalman/OU) | `quant_engine/regime.py`, `quant_engine/alpha/` |
| Biến động, sizing, xác suất | `quant_engine/risk/`, `quant_engine/probabilistic/` |
| Phân bổ danh mục | `quant_engine/portfolio/` |
| Backtest | `backtest/` |
| Bot Telegram | `bot/` |

Nếu không chắc code của mình thuộc `fundamental_filter/` hay `quant_engine/`, xem câu hỏi
thường gặp trong `CONTRIBUTING.md`.

## 6. Các tình huống hay gặp và cách xử lý

### "Tôi lỡ sửa code ngay trên `main`, chưa tạo branch"

Đừng push. Tạo branch mới ngay từ trạng thái hiện tại rồi tiếp tục như bình thường:
```bash
git checkout -b feature/13-fix-typo
```
Các thay đổi bạn đã sửa sẽ tự động đi theo qua branch mới, `main` không bị ảnh hưởng.

### "GitHub báo lỗi khi push: có ai đó đã push trước tôi"

Nghĩa là branch của bạn trên máy đang cũ hơn trên GitHub (thường do bạn hoặc reviewer đã
sửa gì đó). Chạy:
```bash
git pull origin feature/12-garch-sizing
```
Nếu không có xung đột, Git tự gộp xong, push lại bình thường. Nếu báo "conflict", xem mục
tiếp theo.

### "Bị conflict (xung đột)" — đừng hoảng

Conflict nghĩa là hai người sửa cùng một dòng code ở cùng một file. Git sẽ đánh dấu đoạn
xung đột trong file bằng `<<<<<<<`, `=======`, `>>>>>>>`. Mở file đó, đọc cả hai phiên bản,
sửa tay thành bản đúng, xóa các dấu `<<<<<<<`/`=======`/`>>>>>>>`, rồi:
```bash
git add .
git commit -m "Xử lý conflict"
git push
```
Nếu không chắc nên giữ đoạn nào, nhắn hỏi người đã sửa đoạn đó trước khi tự quyết.

### "Tôi commit nhầm file không nên commit (vd file `.env` chứa token)"

Báo ngay cho người giữ repo (chủ repo) — không tự ý `push --force` để xóa, vì có thể ảnh
hưởng người khác. Nếu lỡ push token/mật khẩu, đổi token/mật khẩu đó ngay lập tức.

### "Tôi không biết PR của mình còn thiếu gì để được duyệt"

Xem checklist cuối `.github/PULL_REQUEST_TEMPLATE.md` — phần lớn lý do PR bị yêu cầu sửa
là thiếu test, hoặc hardcode ngưỡng thay vì đọc từ `pipeline/config.yaml`.

## 7. Bảng lệnh Git tối thiểu cần nhớ (nếu dùng dòng lệnh)

| Muốn làm gì | Lệnh |
|---|---|
| Xem trạng thái hiện tại | `git status` |
| Cập nhật `main` mới nhất | `git checkout main && git pull origin main` |
| Tạo branch mới | `git checkout -b feature/<số>-<mô-tả>` |
| Lưu thay đổi | `git add . && git commit -m "mô tả"` |
| Đẩy lên GitHub | `git push origin <tên-branch>` |
| Xem mình đang ở branch nào | `git branch` |
| Chuyển sang branch khác | `git checkout <tên-branch>` |

## 8. Nếu vẫn bị kẹt

Đừng tự loay hoay quá 15 phút với một lỗi Git — chụp màn hình lỗi, nhắn vào nhóm chat của
team. Git rất khó gây mất code vĩnh viễn nếu bạn chưa `push`, nên cứ hỏi trước khi làm gì
"nghe có vẻ nguy hiểm" (như `git reset --hard`, `git push --force`).
