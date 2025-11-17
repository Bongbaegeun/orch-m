# -*- coding: utf-8 -*-
from aes_cipher import AESCipher
import base64

def enc_base64 ( s ) :
        print base64.b16encode(s)

def dec_base64 ( s ) :
        print base64.b16decode(s)

def enc_aes ( salt, key, s ) :
        cipher = AESCipher(salt, key)
        print cipher.encrypt( s )

def dec_aes ( salt, key, s ) :
        cipher = AESCipher(salt, key)
        print cipher.decrypt( s )

if __name__ == "__main__" :
        salt = "6F6E65626F783132333440"
        key = "646964636A7335636D644B5421"

        #dec_base64 (salt)
        #dec_base64 (key)

        enc_aes (salt, key, 'kkh@2016!ok')

        # 암호화 Print
        enc_aes (salt, key, 'nfv1234!')

        # 복호화 Print
        #dec_aes(salt, key, 'NGVk9MBDGKnmtA4rqENIWGxLG1AxgEBTQaPiyDJx/IOUJnisuwz2JYPtdTMMjkyZ')
        dec_aes(salt, key, 'nqqe6yW7LNKXrP19kPgBPouosYSwUR7AZ7jOwbvWMvdHcJhJEqcvLLQqYJIiv7mN')
        dec_aes(salt, key, 'I9/EGsSJkZtXunjuAfy6qjvVqaiNVjP3q6kkk/Z7yUr5Ef3Ace3ostoMKY2KBvDj')
        dec_aes(salt, key, '2NIHNVG81AkOA8W6ZLSL99gDHgde5JSVJY6GH2csk2re8dGcmTVTfb4k6pwYUVjm')

