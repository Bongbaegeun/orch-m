# 2020. 4.13 - lsh
# Orch-M 용 Password 를 AES 로 암호화 
#
# -*- coding: utf-8 -*-

from aes_cipher import AESCipher
import sys, base64

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



def main(arg) :
    salt = "6F6E65626F783132333440"
    key = "646964636A7335636D644B5421"
    ##dec_base64 (salt)
    ##dec_base64 (key)
    # enc_aes (salt, key, 'kkh@2016!ok')

    ## 암호화 Print
    #enc_aes (salt, key, 'nfv1234!')

    ## 복호화
    #dec_aes(salt, key, 'nqqe6yW7LNKXrP19kPgBPouosYSwUR7AZ7jOwbvWMvdHcJhJEqcvLLQqYJIiv7mN')

 
    if len(arg) == 1 :
        print """ ex1) aes_creaty.py encrypt PASSWORD!\n ex2) aes_creaty.py decrypt PASSWORD!"""
 
    if arg[1] == "encrypt" and len(arg) > 2 :
        enc_aes (salt, key, arg[2])
    elif arg[1] == "decrypt" and len(arg) > 2 :
        dec_aes (salt, key, arg[2])
    else :
        print """ ex1) aes_creaty.py encrypt PASSWORD!\n ex2) aes_creaty.py decrypt PASSWORD!"""
 
if __name__ == "__main__" :
    main(sys.argv)


