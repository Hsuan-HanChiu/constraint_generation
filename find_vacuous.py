import os, glob, json, subprocess, re
HERE=os.path.dirname(os.path.abspath(__file__))
vac=[]
for f in sorted(glob.glob(os.path.join(HERE,"datasets","*_optichat_query.jsonl"))):
    model=os.path.basename(f)[:-len("_optichat_query.jsonl")]
    recs=[json.loads(l) for l in open(f)]
    red=os.path.join(HERE,"reduced_data",f"{model}_small.json")
    data=red if os.path.exists(red) else os.path.join(HERE,"feas_model",f"{model}_data.json")
    try:
        out=subprocess.run(["conda","run","--no-capture-output","-n","opti","python","grade_harness.py","selfcheck",
                            "--dataset",f,"--base-py",os.path.join(HERE,"feas_model",f"{model}.py"),"--data-json",data],
                           cwd=HERE,capture_output=True,text=True,timeout=900).stdout
    except subprocess.TimeoutExpired: continue
    for l in out.split("\n"):
        m=re.match(r"\s*(\d+)\s+(\S+)\s+\d+\s+OK\s+\S+\s+(OK|FAIL|nan)",l)
        if m and m.group(3)!="FAIL":   # self-grade OK but control NOT caught -> vacuous
            i=int(m.group(1))
            if i<len(recs):
                vac.append({"model":model,"constraint":m.group(2),"query":recs[i]["query"],"expected_pyomo":recs[i]["expected_pyomo"]})
json.dump(vac,open(os.path.join(HERE,"_vacuous_list.json"),"w"),ensure_ascii=False)
print(f"VACUOUS records: {len(vac)} across {len(set(v['model'] for v in vac))} models")
for v in vac[:10]: print(f"  {v['model']} :: {v['constraint']} :: {v['query'][:50]}")
