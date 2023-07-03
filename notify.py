"""This module is meant to work with https://ntfy.sh/ notification system"""
import requests

PRIORITY_TABLE:"dict[str, int]" = {
    "max":5, "high":4, "default":3, "low":2, "min":1
}


def sendNotification(
        chanel:str, message:"str|bytes", title:"str|None"=None, priorityLevel:"int|str"="default",
        tags:"str|list[str]|None"=None, raiseReqError:bool=False)->bool:
    """send the notification and return if the request sended correctly\n
    `raiseError` is whether an error will be raise if request fail (will print the status otherwise)"""
    url:str = chanel
    data:bytes = message.encode("utf-8") if isinstance(message, str) else message
    # create the headers
    headers:"dict[str, str]|None" = {}
    if title is not None:
        headers["Title"] = title
        
    if isinstance(priorityLevel, str):
        priorityLevel = PRIORITY_TABLE[priorityLevel]
    if  5 >= priorityLevel >= 1:
        headers["Priority"] = str(priorityLevel)
    else: raise ValueError(f"invalide priority: {priorityLevel}")
    
    if tags is not None:
        if isinstance(tags, str):
            headers["Tags"] = tags
        else: # => list[str] of tags
            headers["Tags"] = ",".join(tags)
            
    if len(headers) == 0:
        headers = None
    
    req = requests.post(url, data=data, headers=headers)
    if req.status_code != 200:
        if raiseReqError is False:
            print(f"notification failed with status: {req.status_code}")
            return False
        raise ValueError(f"notification failed with status: {req.status_code}")
    return True

