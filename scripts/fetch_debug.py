import requests
url = 'https://govt.westlaw.com/calregs/Document/I943C96035A1E11EC8227000D3A7C4BC3?viewType=FullText&originationContext=documenttoc&transitionType=CategoryPageItem&contextData=(sc.Default)'
headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get(url, headers=headers)
with open('debug_fail.html', 'w', encoding='utf-8') as f:
    f.write(r.text)
print("Downloaded debug_fail.html with utf-8")
