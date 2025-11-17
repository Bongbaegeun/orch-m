import base64
import hashlib
from Crypto.Cipher import AES


BS = 16
#pad = (lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS).encode())
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS) 

unpad = (lambda s: s[:-ord(s[len(s)-1:])])



class AESCipher(object):
    def __init__(self, key):
        self.key = key
        
    def encrypt(self, raw):
        #raw = pad(raw)
        #cipher = AES.new(self.key, AES.MODE_ECB)
        #return base64.b64encode(cipher.encrypt(raw)) 

        message = raw.encode()
        raw = pad(message)
        cipher = AES.new(self.key, AES.MODE_CBC)
        enc = cipher.encrypt(raw)
        return enc
        #return base64.b64encode(enc).decode('utf-8')

    def __iv(self):
        return chr(0) * 16


class AESCipher2:
       def __init__( self, key ):
           self.key = key

       def encrypt( self, raw ):
           raw = pad(raw)
           cipher = AES.new(self.key, AES.MODE_ECB)
           return cipher.encrypt(raw)


key = '79715953B9D5CED9'
message = '006400055222'
  
#aes = AESCipher2(key)
#encrypt = aes.encrypt(message)

print AES(key).encrypt(message).encdoe('hex')

#print encrypt
print encrypt.encode("hex")
print "".join("{:02x}".format(ord(c)) for c in encrypt)

#hex_ciphertext = "".join("{:02x}".format(ord(c)) for c in encrypt)

#print 'CIPHER = ' + hex_ciphertext

# print(encrypt)
