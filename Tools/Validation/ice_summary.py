from pathlib import Path
import re,json,sys,hashlib
folder=Path(sys.argv[1])
raw=(folder/'ice_raw.log').read_text(encoding='utf-8-sig',errors='replace')
b=(folder/'windows_installer_full.log').read_bytes()
native=b.decode('utf-16',errors='replace') if b[:2] in (b'\xff\xfe',b'\xfe\xff') else b.decode('cp1252',errors='replace')
expected=re.findall(r'^EXPECTED_ICE\t(ICE\d+)\s*$',raw,re.M)
started=set(re.findall(r'(?:Doing action:|Action start[^\n:]*[^\n]*:)\s*(ICE\d+)\b',native))
ended=dict(re.findall(r'Action ended[^\n]*?\b(ICE\d+)\.[^\n]*?Return value (\d+)',native))
errors=[];warnings=[];failures=[]
for line in raw.splitlines():
    if not line.startswith('ICE_RAW\t'):continue
    f=line.split('\t')
    if len(f)<5:failures.append(line)
    elif f[3] in ('0','1'):errors.append(line)
    elif f[3]=='2':warnings.append(line)
missing=sorted(set(expected)-set(ended))
bad_actions={k:v for k,v in ended.items() if v!='1'}
complete=bool(expected) and not missing and not bad_actions and set(expected)<=started
summary={'expected_ICEs':expected,'expected_count':len(expected),'started_ICEs':sorted(started),'completed_ICE_return_values':ended,'missing_completion':missing,'failed_actions':bad_actions,'raw_errors':errors,'raw_warnings':warnings,'raw_failures':failures,'suppressed_ICEs':[],'coverage_complete':complete,'validator_return_true':'VALIDATOR_RETURN\tTrue' in raw,'status':'PASS' if complete and not errors and not failures and 'VALIDATOR_RETURN\tTrue' in raw else 'FAILED_OR_INCOMPLETE','ICE33_executed':'ICE33' in ended,'ICE66_executed':'ICE66' in ended}
(folder/'ICE_SUMMARY.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
print(json.dumps({k:summary[k] for k in ['expected_count','coverage_complete','status','ICE33_executed','ICE66_executed']}))
raise SystemExit(0 if summary['status']=='PASS' else 2)
