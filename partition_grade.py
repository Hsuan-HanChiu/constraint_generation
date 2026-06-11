import os, glob, json, subprocess, re
HERE=os.path.dirname(os.path.abspath(__file__))
files=sorted(glob.glob(os.path.join(HERE,"datasets","*_optichat_query.jsonl")))
kept_tot=0; quar=[]; vac=0; model_stat={}
for f in files:
    model=os.path.basename(f)[:-len("_optichat_query.jsonl")]
    recs=[json.loads(l) for l in open(f)]
    base=os.path.join(HERE,"feas_model",f"{model}.py")
    red=os.path.join(HERE,"reduced_data",f"{model}_small.json")
    data=red if os.path.exists(red) else os.path.join(HERE,"feas_model",f"{model}_data.json")
    try:
        out=subprocess.run(["conda","run","--no-capture-output","-n","opti","python","grade_harness.py",
                            "selfcheck","--dataset",f,"--base-py",base,"--data-json",data],
                           cwd=HERE,capture_output=True,text=True,timeout=900).stdout
    except subprocess.TimeoutExpired:
        for i,r in enumerate(recs): quar.append({"model":model,"i":i,"reason":"selfcheck_timeout","query":r["query"][:60],"pyomo":r["expected_pyomo"][:80]})
        model_stat[model]=("TIMEOUT",0,len(recs)); 
        open(f,"w").close(); continue
    # parse per-record: rows + optional reason lines
    verdict={}  # idx -> (selfgrade, reason)
    lines=out.split("\n")
    for j,l in enumerate(lines):
        m=re.match(r"\s*(\d+)\s+\S+\s+\d+\s+(OK|FAIL|z3_\w+|\?)\s+\S+\s+(OK|FAIL|z3_\w+|\?|nan)",l)
        if m:
            idx=int(m.group(1)); sg=m.group(2); ctl=m.group(3)
            reason=""
            if j+1<len(lines) and "self-grade reason" in lines[j+1]:
                reason=lines[j+1].split("reason:",1)[1].strip()
            verdict[idx]=(sg,ctl,reason)
    keep=[]; 
    for i,r in enumerate(recs):
        sg,ctl,reason=verdict.get(i,("?","?","no_row"))
        if sg=="OK":
            keep.append(r)
            if ctl!="FAIL": 
                globals().__setitem__('vac', vac+1) if False else None
        else:
            quar.append({"model":model,"i":i,"reason":reason or f"selfgrade={sg}","query":r["query"][:60],"pyomo":r["expected_pyomo"][:90]})
    # count vacuous (kept but control not caught)
    vc=sum(1 for i,r in enumerate(recs) if verdict.get(i,('?','?',''))[0]=="OK" and verdict.get(i,('?','?',''))[1]!="FAIL")
    vac+=vc
    with open(f,"w") as fh:
        for r in keep: fh.write(json.dumps(r,ensure_ascii=False)+"\n")
    if not keep: os.remove(f)
    kept_tot+=len(keep); model_stat[model]=("OK",len(keep),len(recs)-len(keep))
print(f"KEPT (graded clean): {kept_tot} | QUARANTINED: {len(quar)} | vacuous-control kept: {vac}")
from collections import Counter
rc=Counter(re.sub(r"'[^']*'","'..'",q["reason"]).split(":")[0][:40] for q in quar)
print("quarantine reasons:", dict(rc))
json.dump({"kept_total":kept_tot,"quarantined":quar,"model_stat":model_stat,"vacuous":vac},
          open(os.path.join(HERE,"_optichat_partition.json"),"w"))
print("models with kept records:", sum(1 for m,(s,k,q) in model_stat.items() if k>0))
