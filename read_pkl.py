import base64

# Thay tên file tương ứng của bạn
with open('cookies.pkl', 'rb') as f:
    encoded_string = base64.b64encode(f.read()).decode('utf-8')
    print("--- COPY CHUỖI DƯỚI ĐÂY ---")
    print(encoded_string)
    print("--- HẾT ---")