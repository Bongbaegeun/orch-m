# -*- encoding: utf-8 -*-
import re


def strcut_utf8(str, destlen, checkmb=True ):
    """
     UTF-8 Format
      0xxxxxxx = ASCII, 110xxxxx 10xxxxxx or 1110xxxx 10xxxxxx 10xxxxxx
      라틴 문자, 그리스 문자, 키릴 문자, 콥트 문자, 아르메니아 문자, 히브리 문자, 아랍 문자 는 2바이트
      BMP(Basic Mulitilingual Plane) 안에 들어 있는 것은 3바이트(한글, 일본어 포함)
    """
    slen=len(str)

    if slen <= destlen:
        return str

    pattern="[\xE0-\xFF][\x80-\xFF][\x80-\xFF]"
    count=0
    text=[]
    for match in re.finditer(pattern, str):
        if len(checkmb == True and match.group(0)) > 1:
            count=count + 2
        else:
            count=count + 1

        text.append(match.group(0))

    return "".join(text)

 print strcut_utf8("가나다라마바사아자차카타파하", 5, True, "")
