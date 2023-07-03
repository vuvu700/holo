import random



def shuffle_str(string:str)->str:
    tmp = list(string)
    random.shuffle(tmp)
    return "".join(tmp)