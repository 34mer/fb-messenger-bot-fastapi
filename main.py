import os, requests
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from starlette.background import BackgroundTasks

app = FastAPI()

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "my-super-secret-verify")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN", "7c0fa9617d69dfe13b10936ece41f998")

FB_SEND_URL = "https://graph.facebook.com/v18.0/me/messages"

def send_text(recipient_id: str, text: str):
    params = {"access_token": PAGE_ACCESS_TOKEN}
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    r = requests.post(FB_SEND_URL, params=params, json=payload, timeout=20)
    r.raise_for_status()

@app.get("/webhook")
def verify(mode: str = "", hub_mode: str = "", token: str = "", hub_verify_token: str = "",
           challenge: str = "", hub_challenge: str = ""):
    # Meta may send either namespaced or non-namespaced params; accept both.
    m = hub_mode or mode
    t = hub_verify_token or token
    c = hub_challenge or challenge
    if m == "subscribe" and t == VERIFY_TOKEN:
        return PlainTextResponse(c, status_code=200)
    raise HTTPException(status_code=403, detail="Verification failed")

@app.post("/webhook")
async def receive_webhook(req: Request, bt: BackgroundTasks):
    body = await req.json()
    # Basic shape: {"object":"page","entry":[{"messaging":[{...}]}]}
    for entry in body.get("entry", []):
        for msg_event in entry.get("messaging", []):
            sender = msg_event.get("sender", {}).get("id")
            if not sender:
                continue
            # If it's a text message
            if "message" in msg_event and msg_event["message"].get("text"):
                text = msg_event["message"]["text"]
                # Respond in background to avoid timeouts
                bt.add_task(send_text, sender, f"Got it: {text}")
            # If it's a postback from a button
            elif "postback" in msg_event:
                payload = msg_event["postback"].get("payload", "POSTBACK")
                bt.add_task(send_text, sender, f"Postback received: {payload}")
    return {"status": "ok"}

@app.get("/")
def health():
    return {"ok": True}
