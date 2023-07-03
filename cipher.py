
def rot(msg:str, n:int=13, alphabet:"str|None"=None)->str:
    if alphabet is None:
        return "".join([chr((ord(char)+n)%256) for char in msg])
    else:
        table = {char:index for index, char in enumerate(alphabet)}
        tableSize = len(alphabet)
        return "".join([alphabet[(table[char]+n)%tableSize] for char in msg])


def substitut(msg:str, tableAlphabet:"dict[str, str]")->str:
    return "".join([tableAlphabet.get(char, '') for char in msg])



def xor(message:"str|bytes", key:"str|bytes")->bytes:
    """to string using res.decode('utf-8') """
    if isinstance(message, str): message = message.encode('utf-8')
    if isinstance(key, str): key = key.encode('utf-8')
    keyLength = len(key)
    return bytes([val ^ key[index %keyLength] for index,val in enumerate(message)])



def findPaterns(msg:"str|bytes", minSize:int=1, maxSize:int=5)->"list[list[str|bytes]]":
    return [[msg[index: index+size] for index in range(len(msg)-size)]  for size in range(minSize, maxSize+1)]

def countPaterns(msg:"str|bytes", minSize:int=1, maxSize:int=5, minimunCount:int=1)->"list[dict[str|bytes, int]]":
    paterns = findPaterns(msg, minSize, maxSize)
    result = []
    for index in range(len(paterns)):
        result.append(dict())
        tmpResultIndex = dict()
        for part in paterns[index]:
            if part in tmpResultIndex:
                tmpResultIndex[part] += 1
            else:
                tmpResultIndex[part] = 1

        for part, count in tmpResultIndex.items():
            if count >= minimunCount:
                result[index][part] = count

    return result


