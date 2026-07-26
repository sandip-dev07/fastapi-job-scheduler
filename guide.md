# Project Commands

## 1. Create virtual environment

```powershell
python -m venv env
```

## 2. Activate virtual environment

```powershell
.\env\Scripts\Activate.ps1
```

## 3. Install dependencies from requirements file

```powershell
python -m pip install -r requirements.txt
```

## 4. Install packages manually

Install FastAPI and Uvicorn:

```powershell
python -m pip install fastapi uvicorn
```

Install Alembic:

```powershell
python -m pip install alembic
```

## 5. Run FastAPI project

Recommended command:

```powershell
python -m uvicorn main:app --reload --port 8080
```

Alternative command:

```powershell
uvicorn main:app --reload --port 8080
```

## 6. Initialize Alembic

```powershell
alembic init alembic
```

## 7. Create migrations

Create users table migration:

```powershell
alembic revision --autogenerate -m "create users table"
```

Create tasks table migration:

```powershell
alembic revision --autogenerate -m "add tasks table"
```

## 8. Apply migrations to database

```powershell
alembic upgrade head
```

## 9. Optional useful commands

Check installed packages:

```powershell
python -m pip list
```

Show package details:

```powershell
python -m pip show fastapi uvicorn
```

Check Uvicorn version:

```powershell
.\env\Scripts\uvicorn.exe --version
```

Update pip:

```powershell
python -m pip install --upgrade pip
```
