@echo off
cd /d "%~dp0"
echo === Installing dependencies ===
call .\venv\Scripts\python.exe -m pip install Django==5.1.4 djangorestframework==3.15.2 django-cors-headers==4.6.0 django-filter==24.3 PyPDF2==3.0.1 python-docx==1.1.2 sentence-transformers==3.3.1 numpy==1.26.4 requests==2.32.3 python-magic==0.4.27 python-magic-bin==0.4.14 Pillow==11.0.0 python-decouple==3.8 --only-binary=:all:

echo.
echo === Verifying imports ===
call .\venv\Scripts\python.exe -c "import django; print('Django', django.VERSION)"
call .\venv\Scripts\python.exe -c "import chromadb; print('ChromaDB OK')"
call .\venv\Scripts\python.exe -c "import sentence_transformers; print('sentence-transformers OK')"

echo.
echo === Running migrations ===
if not exist "media" mkdir media
if not exist "documents" mkdir documents
if not exist "chroma_db" mkdir chroma_db
call .\venv\Scripts\python.exe manage.py makemigrations
call .\venv\Scripts\python.exe manage.py migrate

echo.
echo === Setup Complete! ===
echo Run: .\venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
pause