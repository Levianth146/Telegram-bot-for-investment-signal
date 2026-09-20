<!-- converted from Khung chien luoc tich hop - Fundamental Filter  Quant Regime Engine.docx -->

KHUNG CHIẾN LƯỢC TÍCH HỢP
FUNDAMENTAL FILTER (GRAHAM–DODD HIỆN ĐẠI) + QUANT REGIME ENGINE
Telegram Bot Tín hiệu Đầu tư Chứng khoán Việt Nam — Tài liệu hợp nhất
Phạm vi V1: doanh nghiệp phi tài chính niêm yết tại Việt Nam. Ngân hàng, chứng khoán và một số mô hình đặc thù cần bộ chỉ số riêng.
Tài liệu phục vụ mục đích học tập và xây dựng project; không phải khuyến nghị đầu tư.
# 0. Sơ đồ tổng thể: Hai tầng, hai nhịp
Điểm khác biệt lớn nhất giữa framework này với bản đầu tiên là: Fundamental Filter và Quant Regime Engine không chạy cùng một nhịp. Fundamental đo “doanh nghiệp này có đáng sở hữu không” — câu hỏi chỉ đổi câu trả lời vài lần một năm, theo BCTC. Quant Engine đo “bây giờ có phải lúc không, và nếu vào thì bao nhiêu” — câu hỏi đổi câu trả lời mỗi phiên. Trộn hai nhịp vào một vòng lặp duy nhất là cách chắc chắn nhất để tạo ra look-ahead bias hoặc để phần cơ bản bị nhiễu bởi biến động ngắn hạn.
Bot chỉ đọc kết quả đã tính sẵn từ hai pipeline trên; không có mô hình nào được fit lại khi người dùng gõ lệnh trong Telegram. Chi tiết cadence và các điểm nối cụ thể nằm ở Phần 9.
# 1. Bức tranh tổng thể của Fundamental Filter: Bot đang cố trả lời điều gì?
Phần phân tích cơ bản không nên bắt đầu bằng việc tìm một vài tỷ số rồi đặt ngưỡng tùy ý. Cách tiếp cận của nhóm là đi từ câu hỏi kinh tế đến dữ liệu, rồi mới đến công thức. Bốn câu hỏi trung tâm là:

## 1.1 Luồng logic của chiến lược
- Fundamental Filter trả lời chủ yếu: “Có đáng quan tâm về mặt doanh nghiệp và định giá không?”
- Quant Regime Engine trả lời chủ yếu: “Nếu đáng quan tâm, thời điểm hiện tại có phù hợp để hành động không, và với quy mô/rủi ro nào?”
- Không để Fundamental Engine tự động biến một chỉ số đẹp thành lệnh BUY — quyết định cuối luôn đi qua Tầng 2.
## 1.2 Ba nguyên tắc đọc mọi chỉ số

Một con số đứng một mình thường chưa đủ. Ví dụ ROE = 20% chỉ thật sự có ý nghĩa khi biết ROE đã tăng hay giảm, được tạo ra nhờ biên lợi nhuận/hiệu quả tài sản hay nhờ đòn bẩy, và mức này so với doanh nghiệp cùng ngành như thế nào.
## 1.3 Quy tắc chống “double-count”
Nguyên tắc này áp dụng xuyên cả hai tầng: Merton Distance-to-Default (mục 4.6) là phần mở rộng thị trường của Safety, không chấm lại D/E hay Interest Coverage; Valuation score không chấm lại Growth score dù cả hai đều “nhìn thấy” tăng trưởng — Valuation chỉ hỏi giá đã trả bao nhiêu cho tăng trưởng đó.
# 2. Câu hỏi 1 — Doanh nghiệp có thật sự tăng trưởng không?
Mục tiêu của module Growth là xác nhận tăng trưởng xảy ra xuyên suốt chuỗi: Doanh thu → Lợi nhuận → EPS → Dòng tiền → Tính bền vững. Không kết luận “tăng trưởng tốt” chỉ vì doanh thu hoặc lợi nhuận một năm tăng mạnh.
## 2.1 Doanh thu hiện tại có tăng không?
### Revenue Growth YoY
Ý nghĩa: đo tốc độ mở rộng quy mô bán hàng/dịch vụ so với cùng kỳ. Trong BCTC Việt Nam nên ưu tiên “Doanh thu thuần về bán hàng và cung cấp dịch vụ”.
- Tốt hơn khi tăng trưởng dương và không phụ thuộc vào một năm đột biến.
- Cẩn thận nếu doanh thu tăng nhờ M&A, thay đổi hợp nhất, tăng giá mạnh nhưng sản lượng giảm hoặc ghi nhận bất thường.
## 2.2 Lợi nhuận có tăng cùng doanh thu không?
### NPAT Growth YoY
### Growth Spread
Nếu Growth Spread dương, lợi nhuận đang tăng nhanh hơn doanh thu; nếu âm sâu, cần kiểm tra chi phí, biên lợi nhuận, lãi vay hoặc yếu tố bất thường. Growth Spread là chỉ báo chẩn đoán, không tự động tốt/xấu vì còn phụ thuộc chu kỳ và nền so sánh.
## 2.3 EPS có thật sự tăng không?
EPS trả lời câu hỏi quan trọng hơn “doanh nghiệp lớn hơn”: lợi nhuận trên mỗi cổ phiếu của cổ đông có tăng hay không.
### Share Count Growth
Nếu lợi nhuận tăng nhưng số cổ phiếu tăng nhanh hơn, EPS có thể giảm do pha loãng. Vì vậy bot cần đọc Profit Growth và Share Count Growth cùng EPS Growth.
## 2.4 Tăng trưởng có chuyển thành tiền thật không?
### CFO Growth
### Free Cash Flow (FCF)
## 2.5 Tăng trưởng có bền vững hay chỉ là một cú nhảy?
### CAGR 3Y/5Y
Nên tính CAGR cho Revenue, NPAT, EPS và CFO. CAGR làm mượt chuỗi nhưng có thể che giấu biến động giữa các năm, vì vậy không dùng một mình.
### Positive Growth Years
### Growth Volatility
Độ lệch chuẩn tăng trưởng càng cao cho thấy tốc độ tăng trưởng càng biến động. Không phải volatility cao luôn xấu (do chu kỳ ngành), nhưng nó làm độ tin cậy của CAGR thấp hơn.
### Sustainable Growth Rate — chỉ số nâng cao
SGR ước tính tốc độ tăng trưởng doanh nghiệp có thể hỗ trợ từ lợi nhuận giữ lại và hiệu quả vốn hiện tại mà không cần thay đổi mạnh cấu trúc vốn. Đây là chỉ số Advanced, không cần bắt buộc trong V1.
# 3. Câu hỏi 2 — Doanh nghiệp tạo lợi nhuận có chất lượng và hiệu quả không?
Module Quality không hỏi “lợi nhuận bao nhiêu tỷ?”, mà hỏi “mỗi đồng doanh thu/vốn tạo ra bao nhiêu lợi nhuận, lợi nhuận có được hỗ trợ bởi tiền thật và có lặp lại được không?”.
## 3.1 Mỗi đồng doanh thu tạo ra được bao nhiêu lợi nhuận?
### Gross Margin
Đo phần lợi nhuận còn lại sau giá vốn. Hữu ích để quan sát sức mạnh định giá, chi phí đầu vào và cơ cấu sản phẩm. Nên theo dõi xu hướng 3–5 năm và so với peers.
### Operating Margin
Đo hiệu quả sau khi tính các chi phí vận hành chủ yếu. Nếu doanh thu tăng nhưng Operating Margin giảm liên tục, doanh nghiệp có thể đang phải chi ngày càng nhiều để tạo doanh thu.
### Net Profit Margin
Cho biết 100 đồng doanh thu cuối cùng giữ lại bao nhiêu đồng lợi nhuận sau chi phí, lãi vay và thuế.
## 3.2 Mỗi đồng tài sản và vốn tạo ra được bao nhiêu lợi nhuận?
### ROA
### ROE
ROE cao chưa đủ để kết luận tốt vì có thể được nâng lên nhờ đòn bẩy tài chính.
### ROIC
ROIC đo hiệu quả của vốn thực sự đầu tư vào hoạt động kinh doanh. Đây là chỉ số quan trọng để phân biệt doanh nghiệp tái đầu tư hiệu quả với doanh nghiệp phải bơm nhiều vốn nhưng tạo ít lợi nhuận.
## 3.3 ROE cao do doanh nghiệp giỏi hay do vay nợ nhiều?
### DuPont Analysis
DuPont bóc ROE thành ba nguồn: (1) biên lợi nhuận, (2) hiệu quả tài sản, (3) đòn bẩy. Hai công ty cùng ROE 20% có chất lượng rất khác nếu một bên đạt được nhờ margin/turnover còn bên kia chủ yếu nhờ leverage cao.
## 3.4 Lợi nhuận có chuyển thành tiền thật không?
### Cash Conversion
Kiểm tra mức độ lợi nhuận kế toán được hỗ trợ bởi dòng tiền hoạt động. Nên xem theo nhiều năm vì vốn lưu động có thể làm CFO dao động mạnh từng kỳ.
### Accrual Ratio
Accrual dương cao kéo dài cho thấy lợi nhuận phụ thuộc nhiều hơn vào ghi nhận kế toán so với tiền thu được. Không tự động có nghĩa gian lận; cần kiểm tra phải thu, tồn kho, tài sản hợp đồng và các khoản khác.
## 3.5 Lợi nhuận có đến từ hoạt động cốt lõi và có lặp lại được không?
### Recurring Earnings vs One-off Earnings
Mục tiêu là tách lợi nhuận lặp lại từ hoạt động chính khỏi các khoản như lãi bán tài sản, thoái vốn, đánh giá lại, hoàn nhập lớn bất thường hoặc thu nhập khác. Vì BCTC chuẩn không luôn tách sẵn, đây nên là metric Advanced và có thể cần đọc thuyết minh BCTC.
# 4. Câu hỏi 3 — Doanh nghiệp có an toàn tài chính không?
Safety kiểm tra khả năng sống sót khi điều kiện xấu đi: doanh thu giảm, lãi suất tăng, khách hàng trả chậm hoặc thị trường tín dụng thắt chặt. Bộ chỉ số dưới đây dành cho doanh nghiệp phi tài chính.
## 4.1 Có đủ khả năng thanh toán ngắn hạn không?
### Current Ratio
Không nên kết luận chỉ bằng Current Ratio vì chất lượng tài sản ngắn hạn có thể thấp nếu chủ yếu là tồn kho hoặc phải thu khó thu.
### Quick Ratio
### Cash Ratio
Mức bảo thủ nhất. Cash Ratio quá cao không luôn tốt vì tiền nhàn rỗi lớn có thể làm giảm hiệu quả vốn.
## 4.2 Doanh nghiệp đang vay nợ nhiều đến mức nào?
### Debt / Equity
Nên dùng nợ vay chịu lãi, không đồng nhất toàn bộ Total Liabilities với Debt.
### Debt / Assets
### Net Debt
### Net Debt / EBITDA
Quan trọng nhất là xu hướng và so với đặc thù ngành, không dùng một ngưỡng chết cho mọi doanh nghiệp.
## 4.3 Doanh nghiệp có đủ sức trả lãi vay không?
### Interest Coverage
### EBITDA / Interest
Thường cao hơn EBIT/Interest vì chưa trừ khấu hao. Nên dùng như chỉ số bổ sung, không thay thế hoàn toàn EBIT/Interest.
## 4.4 Dòng tiền có thật sự đủ để hỗ trợ nợ không?
### CFO / Total Debt
### FCF / Debt
Khắt khe hơn CFO/Debt vì đã trừ CAPEX. Cần nhớ FCF âm do Growth CAPEX không nên bị đánh đồng với dòng tiền hoạt động yếu.
### DSCR — Advanced
Đo khả năng trả cả lãi lẫn gốc. Hữu ích nhưng khó chuẩn hóa tự động từ BCTC công khai; nên để V2/Advanced.
## 4.5 Có rủi ro ẩn nào trong bảng cân đối không?
### Short-term Debt Ratio
Tỷ trọng nợ ngắn hạn cao làm tăng refinancing risk — rủi ro phải liên tục vay lại/đáo hạn.
### Cash / Short-term Debt
### Receivables / Revenue và DSO
### DIO
DIO tăng mạnh có thể cho thấy hàng tồn kho bán chậm hoặc vốn bị kẹt. Cần so với ngành và mùa vụ.
Ngoài ratio, nên đọc thuyết minh BCTC về bảo lãnh, cam kết vốn, nghĩa vụ thuê, kiện tụng và các nghĩa vụ tiềm tàng khác.
## 4.6 Thị trường đang định giá rủi ro vỡ nợ ra sao? — Merton Distance-to-Default (Advanced, MỚI)
Đây là điểm ghép nối trực tiếp với mô hình BSM đã thảo luận ở Tầng 2. Toàn bộ mục 4.1–4.5 là góc nhìn kế toán, chỉ cập nhật theo quý. Merton coi vốn chủ sở hữu như một quyền chọn mua trên tài sản doanh nghiệp với giá thực hiện là khoản nợ, nên Distance-to-Default (DD) có thể tính lại mỗi ngày từ vốn hóa thị trường và biến động cổ phiếu, cho một tín hiệu an toàn “sớm hơn” BCTC quý sau.
- DD thấp và đang giảm giữa hai kỳ BCTC là cảnh báo sớm rằng Safety score (dựa trên số liệu quý trước) có thể đã lạc hậu.
- Không chấm điểm lại D/E hay Interest Coverage — DD chỉ bổ sung góc nhìn thị trường, không thay thế góc nhìn kế toán.
- Đây là ADVANCED, cần bảng cân đối nợ mới nhất (điểm-thời-gian) và biến động cổ phiếu; nếu thiếu dữ liệu nợ chi tiết, giữ Safety score ở mức accounting-only (4.1–4.5).
# 5. Câu hỏi 4 — Giá cổ phiếu hiện tại có hợp lý không?
Valuation là bước cuối: một doanh nghiệp tăng trưởng, chất lượng và an toàn vẫn có thể là khoản đầu tư không hấp dẫn nếu giá đã phản ánh quá nhiều kỳ vọng. Không dùng một multiple đơn lẻ để kết luận “rẻ/đắt”.
## 5.1 Ta đang trả bao nhiêu cho 1 đồng lợi nhuận?
### P/E
P/E thấp không tự động là rẻ và P/E cao không tự động là đắt. Cần xem tăng trưởng, chất lượng lợi nhuận, chu kỳ và so sánh lịch sử/peers.
### Earnings Yield
### Normalized P/E
Hữu ích khi lợi nhuận kỳ hiện tại bị méo bởi khoản one-off hoặc chu kỳ cực đoan. “Normalized Earnings” phải được định nghĩa minh bạch.
## 5.2 Ta đang trả bao nhiêu cho một đồng tài sản ròng?
### P/B
P/B phải đọc cùng ROE. Một doanh nghiệp ROE cao, bền vững và bảng cân đối tốt có thể xứng đáng với P/B cao hơn. P/B đặc biệt hữu ích với ngân hàng, nhưng bank model cần bộ phân tích riêng.
## 5.3 Giá trị toàn doanh nghiệp so với lợi nhuận hoạt động thế nào?
### Enterprise Value — biến đầu vào, không phải metric chấm điểm độc lập
### EV / EBITDA
Hữu ích khi so doanh nghiệp có cấu trúc vốn khác nhau. EBITDA chưa trừ khấu hao nên phải thận trọng với ngành thâm dụng tài sản.
### EV / EBIT
## 5.4 Giá cổ phiếu so với dòng tiền thật thế nào?
### FCF Yield
### P/FCF — chỉ số hiển thị bổ sung
P/FCF và FCF Yield là nghịch đảo; không nên chấm điểm cả hai để tránh double-count.
## 5.5 Giá thị trường có thấp hơn giá trị nội tại không?
### DCF — Discounted Cash Flow
DCF là phương pháp định giá, không phải ratio. V1 nên dùng kịch bản Bear/Base/Bull thay vì giả vờ chính xác đến một mức giá duy nhất, vì kết quả rất nhạy với tăng trưởng, biên lợi nhuận, CAPEX, WACC và terminal growth.
### Margin of Safety
Thể hiện khoảng cách giữa giá trị nội tại ước tính và giá thị trường. Đây là tinh thần rất phù hợp với Graham: luôn thừa nhận sai số trong ước tính và yêu cầu “biên an toàn”.
## 5.6 Hai phép so sánh bắt buộc của Valuation

# 6. Phân loại chỉ số để Bot V1 không trở thành “ratio zoo”
Không phải mọi chỉ số đều cần cùng trọng số. Nhóm chia thành ba tầng: CORE dùng để chấm điểm chính; DIAGNOSTIC dùng giải thích nguyên nhân/cảnh báo; ADVANCED dùng khi dữ liệu đủ tốt hoặc cần phân tích sâu. Cột “Nhịp cập nhật” là bổ sung mới, nối trực tiếp với cadence ở Phần 9.

Ghi chú: đây là đề xuất kiến trúc V1, chưa phải trọng số cuối cùng. Trọng số/ngưỡng phải được kiểm nghiệm bằng dữ liệu và backtest thay vì chọn vì “nghe hợp lý” — xem phương pháp đề xuất ở Phần 10.
## 6.1 Chấm điểm rộng, kể chuyện hẹp — quy tắc “im lặng trừ khi cần giải thích” (MỚI)
Bảng phân loại CORE/DIAGNOSTIC/ADVANCED ở trên trả lời câu hỏi “tính cái gì để chấm điểm”, và nên giữ nguyên độ rộng đó — bớt đi sẽ làm mất đúng khả năng chẩn đoán mà nguyên tắc CURRENT/TREND/RELATIVE và quy tắc chống double-count ở mục 1.2–1.3 được sinh ra để bảo vệ. Nhưng khi bot giải thích tín hiệu cho người dùng, hoặc khi nhóm viết báo cáo/thuyết trình, không cần và không nên liệt kê hết các chỉ số CORE cùng lúc — cần một lớp hiển thị riêng, hẹp hơn nhiều, để câu chuyện về doanh nghiệp rõ ràng.
Cách làm chuẩn trong equity research thật: mỗi câu hỏi có đúng một headline metric dẫn chuyện; các metric khác chỉ được nhắc tới khi headline có điều bất thường cần giải thích. Bot “im lặng” về DuPont, Accrual Ratio, DSO/DIO... trừ khi con số đó là lý do khiến headline lệch khỏi kỳ vọng.

# 7. Dữ liệu lấy từ đâu trong Báo cáo tài chính?

## 7.1 Kỷ luật point-in-time (MỚI — bắt buộc cho backtest)
Đây là yêu cầu không có trong bản thảo ban đầu nhưng bắt buộc để backtest không bị look-ahead bias: mỗi số liệu BCTC chỉ được coi là “khả dụng” từ ngày công bố chính thức (theo quy định công bố thông tin, thường trễ 20–45 ngày sau kỳ báo cáo), cộng thêm một độ trễ an toàn (ví dụ +1–2 ngày) để mô phỏng thời gian bot xử lý dữ liệu. Bảng “signals” và mọi backtest phải dùng dấu thời gian công bố này, không dùng ngày kết thúc kỳ báo cáo.
# 8. Nhắc lại Tầng 2: Quant Regime Engine
Phần này tóm tắt lại 6 lớp của Quant Regime Engine đã thống nhất trước đó, để mục 9 có thể chỉ ra chính xác Fundamental Filter cắm vào đâu. Đây không phải nội dung mới cần tranh luận lại — chỉ là bảng tra cứu nhanh.
# 9. Từ Fundamental View đến Quant Regime Engine — các điểm nối cụ thể
Đây là phần bổ sung chính so với bản gốc. Trước đây tài liệu dừng ở “sau khi qua Fundamental Filter, Technical Analysis mới được dùng để chọn thời điểm” mà chưa nói “Technical Analysis” cụ thể là gì. Bây giờ nó chính là Quant Regime Engine, và có bốn điểm nối rõ ràng.
## 9.1 Cadence: hai vòng lặp độc lập
Một mã bị Fundamental Filter loại (FAIL) thì không bao giờ vào vòng lặp Quant, bất kể tín hiệu kỹ thuật đẹp đến đâu — đây là cách hiện thực hóa nguyên tắc “Graham trước, timing sau” bằng code chứ không chỉ bằng lời văn.
## 9.2 Điểm nối (a): Fundamental Score → Watchlist / Universe
Đơn giản nhất và bắt buộc: Fundamental View PASS/WATCH mới được đưa vào universe của Quant Engine; FAIL bị loại khỏi mọi tính toán regime/alpha/risk cho tới kỳ BCTC kế tiếp làm nó PASS trở lại.
## 9.3 Điểm nối (b): Growth + Quality Score → trọng số Alpha
Ở Tầng 2, module Alpha xếp hạng cổ phiếu theo momentum (khi regime trending) hoặc theo độ lệch OU (khi regime đi ngang). Thay vì coi mọi cổ phiếu trong watchlist ngang nhau, nhân thêm hệ số chất lượng:
Đây chính là volatility-managed momentum kết hợp “quality minus junk” đã nhắc ở lần trao đổi trước: momentum giá vẫn là driver chính, nhưng một cổ phiếu tăng giá mạnh trong khi Growth/Quality suy yếu (ví dụ tăng giá đầu cơ) sẽ bị hạ trọng số alpha thay vì được xếp ngang một cổ phiếu tăng giá có nền tảng cải thiện thật.
## 9.4 Điểm nối (c): Valuation Score → View của Black-Litterman
Black-Litterman cần hai đầu vào chủ quan: view Q (kỳ vọng lợi nhuận cao/thấp hơn thị trường) và độ tin cậy Ω. Trước đây view Q lấy thẳng từ tín hiệu regime/momentum. Bây giờ Valuation score bổ sung một view độc lập:
- Margin of Safety cao và P/E/EV-EBITDA thấp hơn median lịch sử lẫn peer (đồng thuận ở mục 5.6) → view Q dương, kỳ vọng vượt trội trung hạn.
- Hai phép so sánh 5.6 lệch nhau (ví dụ rẻ so với lịch sử của chính nó nhưng đắt so với ngành) → giữ view trung tính, giảm độ tin cậy Ω thay vì bỏ view.
- View từ Valuation và view từ Alpha (Kalman/momentum) được đưa vào cùng ma trận P của Black-Litterman như hai “view” riêng biệt trên cùng một mã — Black-Litterman tự cân bằng theo covariance và độ tin cậy tương đối, không cần bot tự quyết định cái nào “thắng”.
## 9.5 Điểm nối (d): Safety / Merton DD → Risk overlay hằng ngày
Safety score theo quý quyết định một mã có đủ an toàn để nằm trong watchlist hay không. Nhưng giữa hai kỳ BCTC, rủi ro tín dụng có thể xấu đi nhanh (ví dụ căng thanh khoản, tin đồn trái phiếu). Nếu Merton DD tính được hằng ngày, dùng nó làm cờ overlay:
## 9.6 Ví dụ minh họa xuyên suốt một mã
## 9.7 Vị trí của TA cổ điển: không dùng để ra quyết định, chỉ dùng để trình bày (MỚI)
Một câu hỏi hợp lý hay gặp khi trình bày framework này: “Sao không thấy RSI, MACD, Bollinger Bands — những indicator quen thuộc với nhà đầu tư Việt Nam?”. Câu trả lời: các indicator TA cổ điển không bị bỏ sót, mà được thay bằng phiên bản thống kê chặt hơn của đúng ý tưởng đó, và dùng cùng một chỉ số ở cả TA lẫn Quant song song sẽ vi phạm quy tắc chống double-count đã nêu ở mục 1.3.

Chart pattern (đầu vai, cờ, tam giác), candlestick pattern và support/resistance cổ điển bị loại có chủ đích — đây là nhận dạng chủ quan, thiếu công thức rõ ràng để backtest khách quan, và nhiều nghiên cứu học thuật cho thấy chúng không có edge đáng kể sau khi kiểm soát data-snooping bias.
TA cổ điển (EMA/RSI) vẫn có vai trò chính đáng trong project — làm baseline B1 trong ablation (Phần 10/12) để chứng minh bằng số liệu rằng Kalman/OU/GARCH thực sự cải thiện so với công cụ quen thuộc, chứ không chỉ “nghe có vẻ cao cấp hơn”.
### Quyết định UX: hiện TA trong tin nhắn bot để tăng độ tin cậy với người dùng quen TA
Nhà đầu tư Việt Nam nhìn chung quen thuộc với TA hơn các khái niệm thống kê (Kalman, GARCH, regime). Để tránh bot trở nên khó hiểu/mất tin cậy vì toàn số liệu lạ, tách riêng hai việc: (1) dịch các con số quant sang một câu diễn giải bằng lời dễ hiểu ngay trong phần chính, và (2) thêm một khối “Tham khảo thêm” hiển thị TA cổ điển, ghi rõ không dùng để ra tín hiệu — chỉ để người dùng tự đối chiếu.
- Ranh giới bắt buộc: TA trong khối “Tham khảo thêm” chỉ hiển thị, KHÔNG được đưa ngược vào bất kỳ công thức tính điểm/sizing nào — nếu để TA ảnh hưởng ngược lại quyết định, sẽ phá vỡ chính lý do đã chọn Kalman/GARCH/Regime thay vì RSI/MACD ở mục 9.7 phía trên.
- Tác dụng phụ có ích: trong giai đoạn đầu khi các mô hình quant còn đang tinh chỉnh (tuần 3–4), khối TA tham khảo còn dùng làm sanity-check rẻ tiền cho chính nhóm — ví dụ Regime báo bull nhưng RSI đang cực đoan quá mua, đó là dấu hiệu nên xem lại tín hiệu trước khi tin tưởng hoàn toàn.
- Vị trí trong code: logic dịch ngôn ngữ và khối tham khảo TA nằm ở `bot/formatters.py`, tách biệt hoàn toàn khỏi `quant_engine/` — đổi cách hiển thị không bao giờ cần đụng tới logic tính toán.
# 10. Đề xuất phương pháp chấm điểm (giải quyết “chưa đặt ngưỡng”)
Tài liệu gốc cố ý chưa đặt ngưỡng chấm điểm và điều đó đúng ở giai đoạn thiết kế. Nhưng để nhóm code có điểm bắt đầu cụ thể thay vì bế tắc ở “ngưỡng nào là đúng”, đề xuất một phương pháp không dùng ngưỡng tuyệt đối — bám đúng nguyên tắc RELATIVE ở mục 1.2 và tránh đúng sai lầm đầu tiên ở mục 12.
- Bước 1 — Chuẩn hóa: với mỗi metric CORE, tính z-score cross-sectional trong cùng ngành/nhóm ngành tại cùng thời điểm: z = (x − median_ngành) / MAD_ngành (dùng median/MAD thay vì mean/std để bớt nhạy với outlier).
- Bước 2 — Kết hợp CURRENT và TREND: điểm mỗi metric = w1·z_current + w2·z_trend(slope 3–5 năm chuẩn hóa cùng cách), với w1, w2 khởi tạo bằng nhau rồi tinh chỉnh bằng backtest.
- Bước 3 — Điểm module: trung bình có trọng số các z-score CORE trong module đó (Growth, Quality, Safety, Valuation).
- Bước 4 — Điểm tổng hợp và ngưỡng theo percentile, không theo giá trị tuyệt đối: PASS = top percentile trong chính universe đang xét (ví dụ top 40%), WATCH = dải giữa, FAIL = phần còn lại — ngưỡng percentile này tự thích nghi theo từng thời điểm và từng ngành thay vì một con số cố định như “ROE > 15%”.
- Bước 5 — Kiểm nghiệm: chạy ablation giống Tầng 2 (thêm/bớt từng module) để xem module nào thật sự có sức phân loại (information coefficient) trước khi cố định trọng số cuối.
# 11. Điều chỉnh triển khai
## 11.1 Phân tầng bắt buộc: P0 / P1 / P2

Quyết định cắt P2 nên chốt ở tuần 1–2, dựa trên kết quả audit dữ liệu ở mục 11.2
## 11.2 Audit khả thi dữ liệu trước khi code
## 11.3 Tiêu chí giữ/cắt một tầng — chốt trước khi chạy ablation
Rủi ro lớn nhất khi đã đầu tư công sức code một tầng là giữ lại nó dù ablation cho thấy không đóng góp, chỉ vì “đã code rồi, tiếc công”. Để tránh tự lừa chính mình, chốt tiêu chí bằng văn bản trước khi chạy ablation lần đầu, ví dụ:
## 11.4 Fallback khi thiếu dữ liệu — hành vi cụ thể của bot
Mục 4.6 đã nói “nếu thiếu dữ liệu nợ chi tiết, giữ Safety score ở mức accounting-only” nhưng chưa định nghĩa hành vi cụ thể khi một tầng Advanced không tính được cho một mã cụ thể. Cần quy tắc tường minh, áp dụng thống nhất cho mọi tầng P2:
- Nếu một metric Advanced không tính được cho một mã (thiếu input), bỏ qua metric đó trong điểm tổng hợp của mã đó — không quy về 0 và không loại mã khỏi watchlist chỉ vì thiếu một chỉ số phụ.
- Ghi rõ trong `reason_json` của bảng signals là thiếu dữ liệu gì, để người dùng đọc tin nhắn biết tín hiệu đang thiếu góc nhìn nào.
- Không để một lỗi tính toán ở tầng P2 làm crash toàn bộ pipeline của mã đó — mỗi tầng nên có try/except riêng và log lỗi, không dừng cả batch.
## 11.5 Cách trình bày trong báo cáo
Đổi khung tường thuật từ “chúng tôi xây framework vượt trội” sang “chúng tôi thiết kế framework có cơ sở lý thuyết để giải quyết các lỗ hổng đã biết của baseline (CANSLIM/ngưỡng cố định), và dùng ablation trên walk-forward để kiểm chứng đóng góp thực tế của từng phần”.
# 12. Những sai lầm nhóm cần tránh khi triển khai
## 12.1 Nhóm sai lầm ở tầng Fundamental (giữ nguyên từ bản gốc)
- Dùng ngưỡng chết cho mọi ngành (ví dụ ROE > 15% luôn tốt, D/E < 1 luôn an toàn).
- Dùng một năm thay cho chuỗi 3–5 năm và bỏ qua mùa vụ theo quý.
- Chấm cùng một metric ở nhiều module và vô tình double-count.
- Nhìn lợi nhuận nhưng bỏ qua CFO, FCF, phải thu và tồn kho.
- Xem FCF âm là xấu mà không kiểm tra CFO, CAPEX, ROIC và cách tài trợ.
- Xem P/E thấp là rẻ mà không kiểm tra normalized earnings, growth và quality.
- Dùng Total Liabilities như Interest-bearing Debt mà không định nghĩa rõ.
- Không tách doanh nghiệp phi tài chính khỏi ngân hàng/chứng khoán/bảo hiểm.
- Không chuẩn hóa đơn vị, kỳ báo cáo, phạm vi hợp nhất và số cổ phiếu bình quân.
- Đưa quá nhiều ratio vào V1 nhưng không giải thích được logic kinh tế phía sau.
## 12.2 Nhóm sai lầm ở tầng Quant và tại điểm ghép nối (MỚI)
- Dùng smoothed probability của Markov regime thay vì filtered probability trong backtest — smoothed dùng thông tin tương lai nên kết quả ảo tốt hơn thực tế.
- Fit lại (refit) bất kỳ mô hình nào khi người dùng gõ lệnh trong Telegram — mọi thứ phải tính sẵn trong pipeline offline, bot chỉ đọc cache.
- Dùng BCTC theo ngày kết thúc kỳ thay vì ngày công bố cộng độ trễ khi backtest Fundamental Filter — đây là look-ahead bias phổ biến nhất và dễ bị bỏ sót nhất.
- Bỏ qua chi phí giao dịch thực tế (T+2, không short, phí + thuế bán, biên độ trần/sàn) khi đánh giá cả hai tầng.
- Để một mã FAIL ở Fundamental Filter vẫn lọt vào Quant Engine vì tín hiệu kỹ thuật quá hấp dẫn — phá vỡ đúng nguyên tắc “Graham trước, timing sau” mà cả hai tài liệu cùng thống nhất.
- Coi Fundamental score và Valuation-based Black-Litterman view là hai nguồn độc lập rồi cộng dồn ảnh hưởng của cùng một sự thật (ví dụ Growth tốt) hai lần vào cả trọng số Alpha lẫn view BL — cần rà lại theo đúng quy tắc double-count ở mục 1.3.
# 13. Bảng công thức nhanh (Quick Reference)
## 13.1 Fundamental Filter

## 13.2 Quant Regime Engine
# 14. Thuật ngữ cần nhớ
## 14.1 Thuật ngữ Fundamental

## 14.2 Thuật ngữ Quant (MỚI)

# 15. Framework chốt lại
# 16. Nguồn nền tảng và phạm vi sử dụng
## 16.1 Nền tảng Fundamental
- Benjamin Graham & David Dodd, Security Analysis (bản dịch/tài liệu do nhóm cung cấp): nền tảng tư duy phân tích thu nhập, bảng cân đối và mối quan hệ giữa giá và giá trị.
- Đề Project.pdf — Xây dựng Telegram Bot tín hiệu đầu tư chứng khoán: yêu cầu kết hợp dữ liệu tài chính với logic chiến lược và hệ thống bot.
- Các thước đo như ROIC, DuPont, FCF Yield, Net Debt/EBITDA, Accrual Ratio, DSO/DIO được dùng như phần cập nhật hiện đại để biến triết lý phân tích thành hệ thống có thể code và kiểm thử.
## 16.2 Nền tảng Quant (MỚI)
- Andrew Lo, Adaptive Markets Hypothesis — khung lý thuyết cho việc để chiến lược thích nghi theo regime thay vì áp một bộ luật cố định.
- Barroso & Santa-Clara (2015); Moreira & Muir (2017) — volatility-managed momentum, cơ sở cho việc dùng GARCH để scale exposure và giảm momentum crash.
- Bharath & Shumway (2008) — ước lượng thực nghiệm Merton Distance-to-Default, cơ sở cho công thức ở mục 4.6.
- Filimonov & Sornette (2012) — ước lượng branching ratio của Hawkes process, cơ sở cho bộ lọc crowding.
- Merton (1974); Black & Scholes (1973) — nền tảng lý thuyết quyền chọn cho mô hình Distance-to-Default.
- Lưu ý: các bằng chứng thực nghiệm trên chủ yếu từ thị trường Mỹ/quốc tế; trên thị trường Việt Nam mới có bằng chứng cho F-score/Quality và momentum HOSE. Phần còn lại nên được trình bày như giả thuyết cần kiểm chứng bằng ablation (Phần 10 và mục 4 của phần Quant), không phải kết luận đã chứng minh.
| Mục tiêu tài liệu
Tài liệu này hợp nhất hai phần đã thảo luận trong dự án: (1) Bộ lọc Cơ bản (Fundamental Filter) theo tinh thần Graham & Dodd, cập nhật bằng các thước đo tài chính hiện đại, tổ chức quanh 4 câu hỏi Growth – Quality – Safety – Valuation; và (2) Quant Regime Engine — tầng định thời điểm và quản trị rủi ro dùng Markov regime switching, Kalman filter, GARCH, Ornstein–Uhlenbeck mean reversion, Black–Litterman, Monte Carlo và Hawkes process.
Bản gốc của Phần I (Fundamental Filter) được giữ gần như nguyên vẹn vì đã đủ chặt chẽ; phần bổ sung chính là các điểm nối cụ thể sang Phần II, để hai tầng không chạy song song một cách rời rạc mà thực sự truyền tín hiệu cho nhau. |
| --- |
| Luồng dữ liệu tổng thể
TẦNG 1 — FUNDAMENTAL FILTER (chạy lại mỗi khi có BCTC mới, ~theo quý)
BCTC + thuyết minh → Growth → Quality → Safety → Valuation → Fundamental Score/View → WATCHLIST (universe hợp lệ cho tầng 2)

TẦNG 2 — QUANT REGIME ENGINE (chạy lại mỗi phiên, sau giờ đóng cửa)
Giá/khối lượng hằng ngày + Watchlist từ Tầng 1 → Regime (Markov) → Alpha (Kalman trend / OU mean reversion, có trọng số theo Growth+Quality score) → Risk (GARCH) → Portfolio (Black-Litterman, view lấy từ Valuation score) → Monte Carlo + Hawkes crowding filter → BUY / WATCH / SELL kèm stop, size, xác suất |
| --- |
| Câu hỏi trung tâm | Ý nghĩa quyết định |
| --- | --- |
| 1. Doanh nghiệp có thật sự tăng trưởng không? | Quy mô, lợi nhuận, EPS và dòng tiền có tăng một cách có thật và bền vững hay không. |
| 2. Lợi nhuận có chất lượng và hiệu quả không? | Lợi nhuận có biên tốt, dùng vốn hiệu quả, có tiền thật hỗ trợ và đến từ hoạt động cốt lõi hay không. |
| 3. Doanh nghiệp có an toàn tài chính không? | Doanh nghiệp có đủ thanh khoản, khả năng trả lãi/trả nợ và sức chịu đựng trước biến động xấu hay không. |
| 4. Giá cổ phiếu hiện tại có hợp lý không? | Một doanh nghiệp tốt vẫn có thể là khoản đầu tư kém nếu mức giá phải trả quá cao. |
| Luồng phân tích
BÁO CÁO TÀI CHÍNH → GROWTH → QUALITY → SAFETY → VALUATION → FUNDAMENTAL VIEW / WATCHLIST → QUANT REGIME ENGINE (regime, timing, sizing) → BUY / WATCH / SELL |
| --- |
| Nguyên tắc | Cách hiểu |
| --- | --- |
| CURRENT | Giá trị hiện tại đang ở mức nào? |
| TREND | 3–5 năm gần đây đang cải thiện, ổn định hay xấu đi? |
| RELATIVE | So với doanh nghiệp tương đồng/cùng ngành thì ở đâu? |
| Một chỉ số chỉ có một “nhà chính”
Một chỉ số có thể được tham chiếu ở nhiều chỗ nhưng chỉ nên chấm điểm chính ở một module. Ví dụ Gross Margin thuộc Quality; CFO/NPAT thuộc Quality; Revenue CAGR thuộc Growth Sustainability; DSO/DIO thuộc Safety; ROIC thuộc Capital Efficiency; P/E thuộc Valuation. Làm vậy giúp bot không phạt hoặc thưởng cùng một vấn đề hai lần. |
| --- |
| Revenue Growth YoY = (Revenue_t − Revenue_(t-1)) / Revenue_(t-1) × 100%
Với quý: so quý hiện tại với cùng quý năm trước để tránh sai lệch mùa vụ. |
| --- |
| NPAT Growth = (NPAT_t − NPAT_(t-1)) / NPAT_(t-1) × 100%
Với BCTC hợp nhất, ưu tiên LNST thuộc về cổ đông công ty mẹ khi phân tích lợi ích cổ đông. |
| --- |
| Growth Spread = NPAT Growth − Revenue Growth |
| --- |
| EPS = LNST thuộc cổ đông phổ thông / Số cổ phiếu phổ thông bình quân gia quyền |
| --- |
| EPS Growth = (EPS_t − EPS_(t-1)) / EPS_(t-1) × 100% |
| --- |
| EPS CAGR_nY = (EPS_end / EPS_begin)^(1/n) − 1 |
| Share Count Growth = (Shares_t − Shares_(t-1)) / Shares_(t-1) × 100% |
| --- |
| CFO Growth = (CFO_t − CFO_(t-1)) / CFO_(t-1) × 100% |
| --- |
| FCF ≈ CFO − CAPEX
CAPEX: tiền chi mua sắm/xây dựng tài sản dài hạn phục vụ hoạt động kinh doanh; cần chuẩn hóa theo doanh nghiệp. |
| --- |
| FCF âm không tự động là xấu
Phải chẩn đoán nguyên nhân. CFO âm + nợ tăng + phải thu/tồn kho tăng thường đáng lo hơn. Ngược lại, CFO dương nhưng FCF âm do CAPEX tăng trưởng lớn, ROIC tốt và nợ được kiểm soát có thể là dấu hiệu doanh nghiệp đang tái đầu tư cho tăng trưởng. Vì vậy FCF < 0 không nên bị bot “FAIL” tự động. |
| CAGR_nY = (Value_end / Value_begin)^(1/n) − 1 |
| --- |
| Positive Growth Ratio = Số kỳ tăng trưởng dương / Tổng số kỳ quan sát |
| --- |
| Growth Volatility = SD(g_1, g_2, ..., g_n) |
| --- |
| SGR ≈ ROE × Retention Ratio
Retention Ratio = 1 − Dividend Payout Ratio |
| --- |
| Kết luận Module Growth
Không hỏi “Revenue có tăng không?” mà hỏi: Revenue ↑ → NPAT ↑ → EPS ↑ sau pha loãng → CFO/FCF theo kịp → chuỗi tăng trưởng 3–5 năm đủ nhất quán. Chỉ khi nhiều mắt xích cùng xác nhận, ta mới có bằng chứng mạnh rằng doanh nghiệp thật sự tăng trưởng.
Điểm nối sang Tầng 2: điểm Growth (đặc biệt CAGR và Positive Growth Ratio) là một trong hai đầu vào của trọng số “momentum có chất lượng” ở module Alpha (xem 9.3.b) — một cổ phiếu có momentum giá mạnh nhưng Growth kém sẽ bị hạ trọng số thay vì được coi ngang bằng. |
| --- |
| Gross Margin = Gross Profit / Revenue × 100% |
| --- |
| Operating Margin = Operating Profit / Revenue × 100% |
| --- |
| Net Profit Margin = NPAT / Revenue × 100% |
| --- |
| ROA = NPAT / Average Total Assets × 100% |
| --- |
| Average Total Assets = (Assets_begin + Assets_end) / 2 |
| ROE = LNST thuộc cổ đông công ty mẹ / Average Equity × 100% |
| --- |
| ROIC = NOPAT / Invested Capital × 100% |
| --- |
| NOPAT ≈ EBIT × (1 − Effective Tax Rate) |
| ROE = Net Margin × Asset Turnover × Equity Multiplier |
| --- |
| Asset Turnover = Revenue / Average Total Assets |
| Equity Multiplier = Average Total Assets / Average Equity |
| Cash Conversion = CFO / NPAT |
| --- |
| Accrual Ratio = (Net Income − CFO) / Average Total Assets |
| --- |
| Core Earnings Ratio ≈ Core Earnings / Reported Earnings |
| --- |
| Kết luận Module Quality
Quality tốt khi biên lợi nhuận ổn định/cải thiện, ROA/ROE/ROIC tốt theo ngành, ROE không dựa quá nhiều vào đòn bẩy, CFO hỗ trợ lợi nhuận và lợi nhuận cốt lõi chiếm tỷ trọng lớn.
Điểm nối sang Tầng 2: Quality score (cùng Growth score) thay thế vai trò của F-score “thô” trong bản thảo luận trước — nó đã bao trùm cả biên lợi nhuận, hiệu quả vốn và chất lượng dòng tiền chi tiết hơn 9 tiêu chí Piotroski gốc, nên nhóm dùng trực tiếp Quality score này làm bộ lọc chất lượng cho module Alpha, không cần tính riêng F-score. |
| --- |
| Current Ratio = Current Assets / Current Liabilities |
| --- |
| Quick Ratio ≈ (Current Assets − Inventory) / Current Liabilities |
| --- |
| Cash Ratio = (Cash + Cash Equivalents) / Current Liabilities |
| --- |
| Debt / Equity = Interest-bearing Debt / Equity |
| --- |
| Debt / Assets = Interest-bearing Debt / Total Assets |
| --- |
| Net Debt = Interest-bearing Debt − Cash & Cash Equivalents |
| --- |
| Net Debt / EBITDA = Net Debt / EBITDA |
| --- |
| Interest Coverage = EBIT / Interest Expense |
| --- |
| EBITDA Interest Coverage = EBITDA / Interest Expense |
| --- |
| CFO / Debt = CFO / Interest-bearing Debt |
| --- |
| FCF / Debt = FCF / Interest-bearing Debt |
| --- |
| DSCR = Cash Available for Debt Service / (Interest + Principal Due) |
| --- |
| Short-term Debt Ratio = Short-term Debt / Total Debt |
| --- |
| Cash Coverage = Cash & Cash Equivalents / Short-term Debt |
| --- |
| DSO = Average Receivables / Revenue × 365 |
| --- |
| DIO = Average Inventory / COGS × 365 |
| --- |
| DD = [ln(V/D) + (μ − ½σ_V²)T] / (σ_V√T)
V, σ_V giải hệ phương trình E = V·N(d1) − D·e^(−rT)·N(d2) và σ_E·E = N(d1)·σ_V·V; D = nợ ngắn hạn + 0.5 × nợ dài hạn (Bharath & Shumway, 2008). |
| --- |
| Kết luận Module Safety
Không hỏi “nợ nhiều hay ít?” mà hỏi: doanh nghiệp có đủ thanh khoản, lợi nhuận và dòng tiền để chịu cấu trúc nợ hiện tại hay không; nợ có đang tăng nhanh; và bảng cân đối có chứa rủi ro tái tài trợ, phải thu/tồn kho hoặc nghĩa vụ tiềm tàng hay không.
Điểm nối sang Tầng 2: DD (4.6), khi có dữ liệu, chạy hằng ngày như một risk overlay độc lập với Safety score theo quý — nếu DD xấu đi đột ngột dù Safety score theo quý vẫn PASS, module Risk (GARCH sizing) nên giảm size hoặc mở rộng stop cho mã đó. |
| --- |
| P/E = Price per Share / EPS = Market Capitalization / Net Income |
| --- |
| Earnings Yield = EPS / Price = 1 / P/E |
| --- |
| Normalized P/E = Market Cap / Normalized Earnings |
| --- |
| P/B = Price per Share / Book Value per Share |
| --- |
| BVPS = Equity attributable to owners / Shares Outstanding |
| EV ≈ Market Cap + Interest-bearing Debt − Cash |
| --- |
| EV / EBITDA = Enterprise Value / EBITDA |
| --- |
| EV / EBIT = Enterprise Value / EBIT |
| --- |
| FCF Yield = FCF / Market Capitalization × 100% |
| --- |
| P/FCF = Market Capitalization / FCF |
| --- |
| Intrinsic Value ≈ Σ [FCF_t / (1+r)^t] + Terminal Value / (1+r)^n |
| --- |
| Margin of Safety = (Intrinsic Value − Market Price) / Intrinsic Value × 100% |
| --- |
| So sánh | Câu hỏi cần trả lời |
| --- | --- |
| Historical Valuation | P/E, P/B, EV/EBITDA hiện tại đang ở đâu so với median/range 3–5 năm của chính doanh nghiệp? |
| Peer Valuation | Multiple hiện tại đang ở đâu so với các doanh nghiệp thực sự tương đồng về ngành/mô hình/tăng trưởng? |
| Fundamental-adjusted | Mức định giá cao/thấp có được biện minh bởi Growth, Quality và Safety hay không? |
| Kết luận Module Valuation
Mục tiêu không phải tìm “P/E thấp nhất”, mà tìm doanh nghiệp có Growth + Quality + Safety đủ tốt trong khi mức giá hiện tại chưa phản ánh quá mức các đặc điểm đó.
Điểm nối sang Tầng 2: Valuation score (đặc biệt Margin of Safety và vị trí P/E so với median 5 năm) chuyển trực tiếp thành view Q trong Black-Litterman, còn mức đồng thuận của hai phép so sánh 5.6 (historical + peer cùng chiều) quyết định độ tin cậy Ω của view đó — xem 9.3.c. |
| --- |
| Module | Metric | Vai trò | Nhịp cập nhật |
| --- | --- | --- | --- |
| Growth | Revenue Growth YoY | CORE | Quý |
| Growth | NPAT Growth YoY | CORE | Quý |
| Growth | EPS Growth YoY | CORE | Quý |
| Growth | Revenue/NPAT/EPS CAGR 3Y–5Y | CORE | Quý |
| Growth | CFO/FCF Growth | CORE | Quý |
| Growth | Positive Growth Years | DIAGNOSTIC | Quý |
| Growth | Growth Volatility | DIAGNOSTIC | Quý |
| Growth | SGR | ADVANCED | Quý |
| Quality | Gross / Operating / Net Margin | CORE | Quý |
| Quality | ROE | CORE | Quý |
| Quality | ROIC | CORE | Quý |
| Quality | ROA | DIAGNOSTIC | Quý |
| Quality | DuPont decomposition | DIAGNOSTIC | Quý |
| Quality | CFO/NPAT | CORE | Quý |
| Quality | Accrual Ratio | DIAGNOSTIC | Quý |
| Quality | Core vs One-off Earnings | ADVANCED | Quý |
| Safety | Current Ratio / Quick Ratio | CORE | Quý |
| Safety | Debt/Equity | CORE | Quý |
| Safety | Net Debt/EBITDA | CORE | Quý |
| Safety | Interest Coverage | CORE | Quý |
| Safety | CFO/Debt | CORE | Quý |
| Safety | Short-term Debt Ratio | DIAGNOSTIC | Quý |
| Safety | Cash/Short-term Debt | DIAGNOSTIC | Quý |
| Safety | DSO / DIO | DIAGNOSTIC | Quý |
| Safety | DSCR | ADVANCED | Quý |
| Safety | Merton Distance-to-Default | ADVANCED | Ngày |
| Valuation | P/E + Earnings Yield | CORE | Ngày |
| Valuation | P/B + ROE context | CORE | Ngày |
| Valuation | EV/EBITDA + EV/EBIT | CORE | Ngày |
| Valuation | FCF Yield | CORE | Ngày |
| Valuation | Historical/Peer Comparison | CORE | Ngày |
| Valuation | DCF + Margin of Safety | ADVANCED | Quý |
| Câu hỏi | Headline (luôn nói) | Supporting (chỉ nói khi headline bất thường) |
| --- | --- | --- |
| 1. Tăng trưởng thật không? | EPS CAGR 3–5Y | Growth Spread (nếu lệch nhiều so với Revenue Growth); CFO Growth (nếu lợi nhuận tăng nhưng không có tiền theo) |
| 2. Lợi nhuận chất lượng không? | ROIC | DuPont decomposition (nếu ROE cao bất thường — để lộ có phải nhờ đòn bẩy không); Cash Conversion (nếu lợi nhuận cao nhưng CFO thấp) |
| 3. An toàn tài chính không? | Net Debt / EBITDA | Interest Coverage (nếu Net Debt/EBITDA đang xấu đi, kiểm tra có đang trả nổi lãi không) |
| 4. Giá hợp lý không? | P/E so với median 5Y & peer | Margin of Safety từ DCF (nếu đủ dữ liệu); FCF Yield (nếu P/E bị méo bởi khoản one-off) |
| Vì sao đây là lớp hiển thị, không phải lớp tính toán
Bot vẫn tính đủ CORE để chấm điểm chính xác và chống double-count; bảng trên chỉ lọc `reason_json` xuống còn 1–2 con số khi sinh câu giải thích cho người dùng hoặc slide báo cáo.
Ví dụ minh họa ở mục 9.6 (“GROWTH: Tốt — Revenue, NPAT và EPS cùng tăng...”) đã ngầm áp dụng đúng tinh thần này — mục này chỉ chính thức hóa nó thành quy tắc chung cho cả 4 module.
Việc cắt hẳn một DIAGNOSTIC/ADVANCED khỏi tầng tính toán chỉ nên xảy ra sau khi ablation (mục 10, 11.3) cho thấy nó không có sức phân loại thật — không phải vì muốn câu chuyện gọn hơn. |
| --- |
| Báo cáo | Dữ liệu chính phục vụ framework |
| --- | --- |
| Báo cáo kết quả kinh doanh | Doanh thu thuần, giá vốn, lợi nhuận gộp, chi phí bán hàng/QLDN, EBIT/operating profit (cần chuẩn hóa), chi phí lãi vay, LNST, LNST thuộc cổ đông công ty mẹ, EPS. |
| Bảng cân đối kế toán | Tiền và tương đương tiền, phải thu, tồn kho, tài sản ngắn hạn, nợ ngắn hạn, vay ngắn/dài hạn, tổng tài sản, vốn chủ sở hữu. |
| Báo cáo lưu chuyển tiền tệ | CFO, chi đầu tư tài sản dài hạn/CAPEX proxy, dòng tiền tài chính, vay/trả nợ. |
| Thuyết minh BCTC | One-off earnings, chi tiết nợ vay/lãi suất/kỳ hạn, cam kết, bảo lãnh, chính sách kế toán, M&A, các khoản phải thu/tồn kho bất thường. |
| Dữ liệu thị trường | Giá cổ phiếu, số cổ phiếu lưu hành, vốn hóa; cần cho P/E, P/B, EV, FCF Yield, so sánh định giá và Merton DD. |
| Ưu tiên BCTC hợp nhất
Nếu doanh nghiệp có công ty con, nên ưu tiên BCTC hợp nhất và dùng LNST thuộc cổ đông công ty mẹ/EPS tương ứng. Phải bảo đảm tử số – mẫu số của mọi ratio cùng kỳ, cùng phạm vi hợp nhất và cùng đơn vị. |
| --- |
| Lớp | Mô hình | Câu hỏi trả lời |
| --- | --- | --- |
| 1. Regime | Markov regime switching trên VN-Index | Thị trường đang ở chế độ nào: bull / bear / turbulent? |
| 2. Quality filter | Fundamental Score (Tầng 1) thay cho F-score thô | Doanh nghiệp có đáng tin để cân nhắc không? |
| 3. Alpha | Kalman trend + momentum rank (trending) / OU mean reversion (đi ngang) | Có xu hướng/độ lệch thật đang khai thác được không? |
| 4. Risk | GARCH/GJR-GARCH | Nên cược bao nhiêu, stop ở đâu? |
| 5. Portfolio | Black-Litterman | Phân bổ tổng thể giữa các mã như thế nào? |
| 6. Xác suất hóa | Monte Carlo (filtered historical simulation) + Hawkes crowding filter | Nếu sai thì mất bao nhiêu, xác suất đúng là bao nhiêu, đám đông có đang quá nóng không? |
| Vòng lặp Fundamental (theo quý, event-driven theo ngày công bố BCTC)
1. Khi có BCTC mới công bố cho một mã → tính lại Growth, Quality, Safety, Valuation score cho mã đó.
2. Cập nhật Fundamental Score/View (PASS/WATCH/FAIL) và WATCHLIST.
3. Universe của Quant Engine = giao giữa VN100 (hoặc universe đã chọn) và Watchlist PASS/WATCH. |
| --- |
| Vòng lặp Quant (mỗi phiên, sau 15:00)
1. Regime → Alpha (có trọng số Growth+Quality) → Risk (GARCH) → Portfolio (Black-Litterman, view từ Valuation) → Monte Carlo + Hawkes.
2. Ghi kết quả vào bảng signals; bot chỉ đọc bảng này khi người dùng gõ lệnh.
3. Nếu DD (4.6) tính được hằng ngày, chạy như risk overlay song song, độc lập với Safety score theo quý. |
| Alpha_effective = Alpha_raw × f(Growth score, Quality score)
f là hàm tăng đơn điệu, ví dụ trung bình có trọng số của hai z-score chuẩn hóa theo ngành, giới hạn trong [0.5, 1.5] để không lấn át tín hiệu giá. |
| --- |
| size_final = size_GARCH × g(DD_hiện tại so với DD trung bình 60 phiên)
g giảm dần khi DD tụt sâu dưới trung bình, độc lập với việc Safety score theo quý vẫn đang PASS. |
| --- |
| Mã ABC — từ Fundamental đến Quant signal
Fundamental (quý gần nhất): Growth PASS (Revenue/NPAT/EPS cùng tăng, CAGR 3Y ổn định); Quality PASS (ROIC 18%, CFO/NPAT > 1); Safety WATCH (Net Debt/EBITDA tăng nhẹ, Interest Coverage vẫn an toàn); Valuation trung tính (P/E dưới median 5Y nhưng FCF Yield chưa hấp dẫn) → Fundamental View: WATCH, được đưa vào Watchlist.
Quant (phiên hôm nay): Regime P(bull) = 0.78; Kalman slope t-stat 2.6 và momentum rank cao, nhân với hệ số chất lượng 1.2 (Growth/Quality tốt) → Alpha_effective mạnh hơn alpha thô; GARCH cho σ̂ → stop −4.7%, size 6% NAV trước điều chỉnh; Merton DD ổn định so với trung bình 60 phiên → không giảm size; Black-Litterman nhận thêm view trung tính từ Valuation nên không đẩy trọng số portfolio lên quá cao dù Alpha đang mạnh; Hawkes cho n = 0.5, chưa có dấu hiệu crowding; Monte Carlo: P(+8% trước −4.7% trong 10 phiên) = 55%, CVaR95 = −6.3%.
Kết quả: BUY, size 6% NAV, stop −4.7%, kèm chú thích “Fundamental: WATCH — theo dõi Net Debt/EBITDA kỳ báo cáo tới”. |
| --- |
| TA cổ điển | Ý tưởng cốt lõi | Thay bằng gì trong framework | Vì sao thay thế |
| --- | --- | --- | --- |
| SMA/EMA, MACD | Phát hiện xu hướng | Kalman filter (Alpha) | EMA phản ứng trễ, không cho biết độ tin cậy; Kalman cho cả slope lẫn t-stat của slope |
| RSI, Stochastic | Bắt “quá mua/quá bán” để đảo chiều | Ornstein-Uhlenbeck (Alpha) | RSI dùng ngưỡng cố định 70/30 cho mọi mã; OU ước lượng tốc độ hồi quy và biên độ riêng theo từng mã |
| Bollinger Bands, ATR | Đo biến động để đặt vùng dao động/dừng lỗ | GARCH (Risk) | Bollinger/ATR dùng cửa sổ trượt cố định, phản ứng chậm; GARCH dự báo vol có điều kiện, phản ứng nhanh hơn với cú sốc mới |
| ADX | Đo sức mạnh xu hướng | t-stat của slope Kalman | Cùng mục đích, nền tảng thống kê rõ hơn công thức heuristic của Wilder |
| OBV, Volume spike | Dòng tiền/khối lượng bất thường | Hawkes crowding filter (P2) | Hawkes mô hình hóa việc volume tăng có đang tự lây lan hay không, sâu hơn một chỉ báo khối lượng đơn thuần |
| Mẫu tin nhắn cập nhật
📈 BUY — ABC | 18/09/2026
Regime: Bull (P = 0.78) → thị trường đang trong xu hướng tăng, độ tin cậy khá cao
Trend (Kalman): t-stat 2.6 → xu hướng tăng rõ ràng
Entry ~27.5 | Stop 26.2 | Size 6% NAV
P(+8% trước −4.7% trong 10 phiên) = 57% | CVaR95 = −6.1%

📊 Tham khảo thêm (không dùng để ra tín hiệu): RSI(14) = 62, MA20/MA50 = tăng, Volume/MA20 = 1.3x
⚠️ Sản phẩm học thuật, không phải tư vấn đầu tư. |
| --- |
| Mức | Thành phần | Lý do |
| --- | --- | --- |
| P0 — bắt buộc | Growth/Quality/Safety/Valuation (accounting); Regime (Markov); Alpha (Kalman/OU); Risk (GARCH); backtest + ablation cơ bản | Xương sống trả lời đúng hai câu hỏi cốt lõi: đáng mua không, và khi nào mua. Thiếu một trong số này thì sản phẩm không hoàn chỉnh. |
| P1 — nên có nếu đúng tiến độ | Black-Litterman; Monte Carlo | Nâng chất lượng output (phân bổ hợp lý hơn, xác suất hóa cho tin nhắn) nhưng bot vẫn chạy được nếu tạm thay bằng equal-weight/fixed sizing. |
| P2 — mở rộng, cắt không ảnh hưởng cấu trúc | Merton DD; Hawkes crowding; Institutional Flow (khối ngoại/tự doanh) | Phụ thuộc dữ liệu chưa chắc có sẵn/đủ tốt ở VN; cắt bỏ không làm framework mất tính hợp lệ, chỉ mất phần mở rộng. |
| Việc cần làm trong 2–3 ngày đầu tuần 1
Thử kéo thật dữ liệu cho 5–10 mã mẫu cho từng nhóm chỉ số Advanced: chi tiết nợ vay/kỳ hạn (cho Merton DD), dữ liệu khối lượng/sự kiện theo ngày (cho Hawkes), dữ liệu khối ngoại/tự doanh ròng (cho Institutional Flow).
Ghi lại: cột nào có sẵn, cột nào phải tự tính/ước lượng, cột nào không thể lấy được với nguồn hiện tại.
Chốt P2 nào khả thi ngay sau audit này, thay vì code xong khung rồi mới phát hiện không có dữ liệu để chạy. |
| --- |
| Một tầng chỉ được giữ trong bản cuối nếu nó cải thiện Sharpe ngoài mẫu (out-of-sample, walk-forward) tối thiểu một ngưỡng đã thống nhất trước (ví dụ +0.1). Nếu không đạt, tầng đó được báo cáo là “đã thử nghiệm nhưng không đóng góp đủ để giữ lại” — đây vẫn là một phát hiện hợp lệ và đáng trình bày, không phải một thất bại cần giấu đi. |
| --- |
| Metric | Công thức rút gọn | Module |
| --- | --- | --- |
| Revenue Growth | (Rev_t − Rev_t-1) / Rev_t-1 | Growth |
| CAGR | (End/Begin)^(1/n) − 1 | Growth |
| NPAT Growth | (NPAT_t − NPAT_t-1) / NPAT_t-1 | Growth |
| EPS | NPAT attributable / weighted avg shares | Growth |
| Share Growth | (Shares_t − Shares_t-1) / Shares_t-1 | Growth |
| FCF | CFO − CAPEX | Growth |
| Gross Margin | Gross Profit / Revenue | Quality |
| Operating Margin | Operating Profit / Revenue | Quality |
| Net Margin | NPAT / Revenue | Quality |
| ROA | NPAT / Avg Assets | Quality |
| ROE | NPAT attributable / Avg Equity | Quality |
| ROIC | NOPAT / Invested Capital | Quality |
| Asset Turnover | Revenue / Avg Assets | Quality |
| Equity Multiplier | Avg Assets / Avg Equity | Quality |
| Cash Conversion | CFO / NPAT | Quality |
| Accrual Ratio | (Net Income − CFO) / Avg Assets | Quality |
| Current Ratio | Current Assets / Current Liabilities | Safety |
| Quick Ratio | (Current Assets − Inventory) / Current Liabilities | Safety |
| Cash Ratio | Cash / Current Liabilities | Safety |
| D/E | Interest-bearing Debt / Equity | Safety |
| Net Debt | Debt − Cash | Safety |
| Net Debt/EBITDA | Net Debt / EBITDA | Safety |
| Interest Coverage | EBIT / Interest Expense | Safety |
| CFO/Debt | CFO / Debt | Safety |
| Short-term Debt % | Short-term Debt / Total Debt | Safety |
| DSO | Avg Receivables / Revenue × 365 | Safety |
| DIO | Avg Inventory / COGS × 365 | Safety |
| Merton DD | [ln(V/D)+(μ−½σ_V²)T] / (σ_V√T) | Safety |
| P/E | Price / EPS | Valuation |
| Earnings Yield | EPS / Price = 1/P/E | Valuation |
| P/B | Price / BVPS | Valuation |
| EV | Market Cap + Debt − Cash | Valuation |
| EV/EBITDA | EV / EBITDA | Valuation |
| EV/EBIT | EV / EBIT | Valuation |
| FCF Yield | FCF / Market Cap | Valuation |
| Margin of Safety | (Intrinsic Value − Price) / Intrinsic Value | Valuation |
| Thành phần | Công thức rút gọn | Lớp |
| --- | --- | --- |
| Regime probability | P(s_t = k | F_t), filtered | Regime |
| Kalman trend | l_t = l_t-1 + b_t-1 + η_t ; b_t = b_t-1 + ζ_t | Alpha |
| OU mean reversion | dr = θ(μ − r)dt + σdW ; half-life = ln2/θ | Alpha |
| GJR-GARCH | σ²_t = ω + (α+γ·1[ε<0])ε²_t-1 + βσ²_t-1 | Risk |
| Position size | size = min(w_max, σ_target/σ̂) | Risk |
| Black-Litterman | μ_BL = [(τΣ)⁻¹+P′Ω⁻¹P]⁻¹[(τΣ)⁻¹π+P′Ω⁻¹Q] | Portfolio |
| Hawkes intensity | λ(t) = μ + Σ α·e^(−β(t−t_i)) ; n = α/β | Crowding |
| Monte Carlo output | P(TP trước SL trong H phiên), CVaR95 | Xác suất |
| Thuật ngữ | Giải thích ngắn |
| --- | --- |
| Revenue | Doanh thu thuần. |
| NPAT | Net Profit After Tax — lợi nhuận sau thuế. |
| CFO | Cash Flow from Operations — dòng tiền từ hoạt động kinh doanh. |
| CAPEX | Chi đầu tư tài sản dài hạn phục vụ hoạt động kinh doanh. |
| FCF | Free Cash Flow — dòng tiền tự do. |
| EBIT | Lợi nhuận trước lãi vay và thuế. |
| EBITDA | EBIT trước khấu hao và phân bổ. |
| NOPAT | Lợi nhuận hoạt động sau thuế giả định. |
| Market Cap | Giá trị vốn hóa thị trường. |
| EV | Enterprise Value — giá trị doanh nghiệp theo cấu trúc vốn. |
| One-off | Khoản lợi nhuận/chi phí không mang tính lặp lại. |
| Peer | Doanh nghiệp so sánh tương đồng. |
| Margin of Safety | Khoảng đệm giữa giá trị nội tại ước tính và giá thị trường. |
| TTM | Trailing Twelve Months — 12 tháng gần nhất. |
| Thuật ngữ | Giải thích ngắn |
| --- | --- |
| Regime switching | Mô hình Markov cho phép thị trường chuyển đổi giữa các trạng thái ẩn (bull/bear/turbulent). |
| Filtered vs smoothed probability | Filtered chỉ dùng dữ liệu đến thời điểm t; smoothed dùng cả dữ liệu tương lai — chỉ filtered mới hợp lệ cho backtest/live. |
| Kalman filter | Thuật toán ước lượng trạng thái ẩn (ví dụ trend, slope) cập nhật tuần tự, kèm độ bất định. |
| OU process | Ornstein–Uhlenbeck — mô hình mean reversion với tốc độ hồi quy θ và half-life = ln2/θ. |
| GARCH | Mô hình biến động có điều kiện, nắm bắt tính “cụm” của volatility. |
| Distance-to-Default (DD) | Số độ lệch chuẩn tài sản doanh nghiệp còn cách mức nợ, suy ra từ mô hình Merton. |
| Black-Litterman | Mô hình phân bổ danh mục kết hợp lợi nhuận cân bằng thị trường với các “view” chủ quan có trọng số theo độ tin cậy. |
| Hawkes process | Mô hình sự kiện tự kích hoạt (self-exciting); branching ratio n đo mức độ một sự kiện “đẻ” ra sự kiện kế tiếp. |
| Monte Carlo (filtered historical simulation) | Mô phỏng nhiều kịch bản giá bằng cách bootstrap residual đã chuẩn hóa theo GARCH. |
| CVaR (Conditional Value at Risk) | Mức lỗ kỳ vọng trong các kịch bản xấu nhất vượt ngưỡng VaR. |
| Một đoạn để nhớ
Không tìm cổ phiếu chỉ vì “tăng trưởng cao”, “P/E thấp” hay “momentum mạnh”. Nhóm tìm doanh nghiệp: (1) tăng trưởng có thật và đủ bền; (2) tạo lợi nhuận có chất lượng và hiệu quả; (3) có bảng cân đối đủ an toàn — cả theo kế toán lẫn theo góc nhìn thị trường; và (4) đang được định giá hợp lý so với chất lượng đó. Chỉ sau khi một mã vượt qua bốn câu hỏi này, Quant Regime Engine mới được dùng để trả lời: có phải lúc không, mua/bán bao nhiêu, và nếu sai thì thiệt hại được giới hạn ở đâu.
Ngưỡng chấm điểm và trọng số của cả hai tầng cố ý chưa cố định. Bước tiếp theo của project là: chuẩn hóa dữ liệu → chọn CORE metrics → chấm điểm theo phương pháp percentile ở Phần 10 → chạy walk-forward và ablation trên cả Fundamental lẫn Quant → điều chỉnh trọng số và ngưỡng dựa trên bằng chứng, không dựa trên trực giác. |
| --- |