import os, glob, json, subprocess, re
HERE=os.path.dirname(os.path.abspath(__file__))
files=sorted(glob.glob(os.path.join(HERE,"datasets","*_optichat_query.jsonl")))
results={}; fail_records=[]
for f in files:
    model=os.path.basename(f)[:-len("_optichat_query.jsonl")]
    base=os.path.join(HERE,"feas_model",f"{model}.py")
    red=os.path.join(HERE,"reduced_data",f"{model}_small.json")
    data=red if os.path.exists(red) else os.path.join(HERE,"feas_model",f"{model}_data.json")
    try:
        out=subprocess.run(["conda","run","--no-capture-output","-n","opti","python","grade_harness.py",
                            "selfcheck","--dataset",f,"--base-py",base,"--data-json",data],
                           cwd=HERE,capture_output=True,text=True,timeout=600).stdout
    except subprocess.TimeoutExpired:
        results[model]=("TIMEOUT",0,0); continue
    pas = "SELFCHECK: PASS" in out
    # per-record rows: "  <i>  <name>   <ms> OK  <ms> FAIL"  (OK=self-grade equiv; FAIL=control caught=good)
    rows=re.findall(r"^\s*\d+\s+(\S+)\s+\d+\s+(OK|FAIL|z3_\w+|ERR\w*)\s+\S+\s+(OK|FAIL|z3_\w+|ERR\w*|nan|\?)",out,re.M)
    ngood=sum(1 for nm,sg,ctl in rows if sg=="OK")
    nbad=[(nm,sg,ctl) for nm,sg,ctl in rows if sg!="OK"]
    results[model]=("PASS" if pas else "FAIL", ngood, len(nbad))
    for nm,sg,ctl in nbad: fail_records.append({"model":model,"constraint":nm,"selfgrade":sg,"control":ctl})
allpass=[m for m,(s,g,b) in results.items() if s=="PASS"]
withfail=[m for m,(s,g,b) in results.items() if s!="PASS"]
tot_good=sum(g for s,g,b in results.values()); tot_bad=sum(b for s,g,b in results.values())
print(f"models graded: {len(results)} | all-PASS: {len(allpass)} | with failures/timeout: {len(withfail)}")
print(f"records self-grade OK: {tot_good} | not-OK: {tot_bad}")
if withfail: print("models with issues:", withfail)
if fail_records: 
    print("failing records (first 25):")
    for r in fail_records[:25]: print("  ",r)
json.dump({"results":results,"fail_records":fail_records},open(os.path.join(HERE,"_optichat_grade.json"),"w"))
