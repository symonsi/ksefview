name: Build EXE

on: [push]

env:
  FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true

jobs:
  build:
    runs-on: windows-latest

    steps:
    - uses: actions/checkout@v4

    - name: Setup Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: pip install pyinstaller lxml

    - name: Build EXE
      run: pyinstaller --onefile viewer.py

    - name: Upload EXE
      uses: actions/upload-artifact@v4
      with:
        name: viewer-exe
        path: dist/viewer.exe
