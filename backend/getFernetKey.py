import os
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

# 1. 你的密码
password = b"Teach Master"

# 2. 生成一个随机的盐 (Salt)
# 你需要保存这个盐，解密时需要用到它
salt = os.urandom(16)
print(f"生成的盐 (请保存好): {salt.hex()}")

# 3. 配置密钥派生函数 (KDF)
kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,  # 期望的密钥长度，对于Fernet是32字节
    salt=salt,
    iterations=390000, # 推荐的迭代次数
    backend=default_backend()
)

# 4. 从你的密码派生出密钥
key_bytes = kdf.derive(password)

# 5. 将派生出的密钥进行Base64编码，使其可用于Fernet
key_for_fernet = base64.urlsafe_b64encode(key_bytes)

print("\n从 'Teach Master' 安全派生出的Fernet密钥:")
print(key_for_fernet.decode())