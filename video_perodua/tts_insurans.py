"""Jana voice over lelaki (ms-MY-OsmanNeural) + masa setiap perkataan -> vo/*.mp3, vo/timing.json"""
import certifi, os, json, asyncio, sys
if os.path.exists("/root/.ccr/ca-bundle.crt"):
    certifi.where = lambda: "/root/.ccr/ca-bundle.crt"
import edge_tts
SEG = {
    "v1": ("Insurans kereta dah nak tamat? Tapi tak pasti berapa premium yang kena bayar nanti?", "+5%"),
    "v2": ("Jangan risau! Anda tak perlu pening-pening nak agak berapa kos insurans kereta.", "+0%"),
    "v3": ("Sebenarnya, premium insurans bergantung pada beberapa faktor seperti model kereta, nilai perlindungan, N C D, dan jenis perlindungan yang dipilih.", "+0%"),
    "v4a": ("Nak tahu berapa anggaran premium insurans kereta anda? Mudah sahaja, hubungi Perodua Dungun hari ini, kami sedia bantu semak untuk anda.", "+15%"),
    "v4b": ("Jangan tunggu sampai insurans tamat, baru nak renew!", "+10%"),
}
async def gen(k, text, rate):
    c = edge_tts.Communicate(text, "ms-MY-OsmanNeural", rate=rate, boundary="WordBoundary")
    words = []
    with open(f"vo/{k}.mp3", "wb") as f:
        async for ch in c.stream():
            if ch["type"] == "audio": f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                words.append((ch["text"], ch["offset"] / 1e7, ch["duration"] / 1e7))
    return words
async def main():
    os.makedirs("vo", exist_ok=True)
    out = {}
    for k, (t, r) in SEG.items():
        out[k] = await gen(k, t, r)
    json.dump(out, open("vo/timing.json", "w"), indent=1)
asyncio.run(main())
