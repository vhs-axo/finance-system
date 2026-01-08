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
`uv sync`
`uv venv`

then run `immudb` inside the project directory
then run `uvicorn main:app`

then if yall wann check the test run lang `streamlit run frontend_test.py`
