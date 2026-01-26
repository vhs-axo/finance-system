ano

install sa immudb guys

here links sa what to install (add them sa environment variable nyo)

[`immudb`](https://github.com/codenotary/immudb/releases/download/v1.10.0/immudb-v1.10.0-windows-amd64.exe)
[`immuclient`](https://github.com/codenotary/immudb/releases/download/v1.10.0/immuclient-v1.10.0-windows-amd64.exe)
[`immuadmin`](https://github.com/codenotary/immudb/releases/download/v1.10.0/immuadmin-v1.10.0-windows-amd64.exe)

tapos install `uv` from pypi
```bash
pip install uv
```

then sulod sa cloned na directory tapos run
```bash
uv sync
uv venv
```

then run `immudb` inside the project directory
```bash
immudb
```

then run using `uvicorn`
```bash
uvicorn main:app
```


then if yall wann check the test run lang 
```bash
streamlit run frontend_test.py
```

oh shit also make a `.env`
kani ra sulod
```
INITIAL_ADMIN_PASS=admin123
INITIAL_STAFF_PASS=staff123
INITIAL_AUDITOR_PASS=auditor123
INITIAL_IT_PASS=it123
INITIAL_PAYABLES_PASS=payables123
INITIAL_VP_FINANCE_PASS=vpfinance123
INITIAL_PRESIDENT_PASS=president123
INITIAL_PROCUREMENT_PASS=procurement123
INITIAL_DEPT_HEAD_PASS=depthead123
INITIAL_BOOKKEEPER_PASS=bookkeeper123
```

login details to check each of the ff accounts are just the names of the roles and the password login would be the role123

i.e.

username: admin
password: admin123

there are 2 sutudent accounts already created

username: student
password: student123

username: 24-87456
password: 123