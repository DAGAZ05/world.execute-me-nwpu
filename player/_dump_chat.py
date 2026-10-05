import gzip, json, sys
sys.stdout.reconfigure(encoding="utf-8")
d = json.loads(gzip.decompress(open("film/pv_dsh_frontend_20260927/dsh_text.json.gz","rb").read()).decode("utf8"))
ch = d["changes"]
out=[]; prev=None; lastmsg=None
for n, av, theme, ent in ch:
    msgs = tuple((r,x) for r,x in ent if r in ("user","ai","card","sub","err","meta","state","name"))
    if msgs == prev: continue
    prev = msgs
    t = n/24.0
    # show only new messages since last printed
    new = []
    if lastmsg:
        # find longest common prefix
        k=0
        while k<len(msgs) and k<len(lastmsg) and msgs[k]==lastmsg[k]: k+=1
        new = msgs[k:]
    else:
        new = msgs
    lastmsg = msgs
    if not new: 
        out.append(f"[{t:7.2f}] (state: {msgs[-1][1] if msgs else ''})")
        continue
    for r,x in new:
        out.append(f"[{t:7.2f}] {r:6s}| {x}")
open("_chat_speech.txt","w",encoding="utf-8").write("\n".join(out))
print(len(out))
