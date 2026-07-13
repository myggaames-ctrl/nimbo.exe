import os
import requests
from dotenv import load_dotenv

load_dotenv('/home/ictor_axtor/micocina-dashboard/.env')

FB_PAGE_TOKEN = os.getenv("FB_PAGE_TOKEN", "")
FB_PAGE_ID = os.getenv("FB_PAGE_ID", "")
IG_ACCOUNT_ID = os.getenv("IG_ACCOUNT_ID", "")

def publicar_facebook(mensaje, ruta_video=None, ruta_foto=None):
    if not FB_PAGE_TOKEN or not FB_PAGE_ID:
        return False, "Facebook no configurado"
    try:
        if ruta_video:
            r = requests.post(
                f"https://graph.facebook.com/{FB_PAGE_ID}/videos",
                data={
                    "access_token": FB_PAGE_TOKEN,
                    "description": mensaje
                },
                files={"file": open(ruta_video.replace('/static/', '/home/ictor_axtor/micocina-dashboard/static/'), 'rb')}
            )
        elif ruta_foto:
            r = requests.post(
                f"https://graph.facebook.com/{FB_PAGE_ID}/photos",
                data={
                    "access_token": FB_PAGE_TOKEN,
                    "caption": mensaje
                },
                files={"source": open(ruta_foto.replace('/static/', '/home/ictor_axtor/micocina-dashboard/static/'), 'rb')}
            )
        else:
            r = requests.post(
                f"https://graph.facebook.com/{FB_PAGE_ID}/feed",
                data={"access_token": FB_PAGE_TOKEN, "message": mensaje}
            )
        data = r.json()
        if "id" in data:
            return True, data["id"]
        return False, str(data.get("error", {}).get("message", "Error"))
    except Exception as e:
        return False, str(e)

def publicar_instagram_reel(ruta_video, caption):
    if not FB_PAGE_TOKEN or not IG_ACCOUNT_ID:
        return False, "Instagram no configurado"
    try:
        ruta_real = ruta_video.replace('/static/', '/home/ictor_axtor/micocina-dashboard/static/')
        r1 = requests.post(
            f"https://graph.facebook.com/{IG_ACCOUNT_ID}/media",
            data={
                "access_token": FB_PAGE_TOKEN,
                "media_type": "REELS",
                "caption": caption,
                "share_to_feed": "true"
            },
            files={"video": open(ruta_real, 'rb')}
        )
        data1 = r1.json()
        if "id" not in data1:
            return False, str(data1.get("error", {}).get("message", "Error subiendo video"))
        container_id = data1["id"]
        import time
        time.sleep(30)
        r2 = requests.post(
            f"https://graph.facebook.com/{IG_ACCOUNT_ID}/media_publish",
            data={"access_token": FB_PAGE_TOKEN, "creation_id": container_id}
        )
        data2 = r2.json()
        if "id" in data2:
            return True, data2["id"]
        return False, str(data2.get("error", {}).get("message", "Error publicando"))
    except Exception as e:
        return False, str(e)
