# הוראות דחיפה ל-GitHub

## אופציה 1: שימוש בסקריפט (PowerShell)

1. פתח PowerShell בתיקיית הפרויקט
2. הרץ:
   ```powershell
   .\deploy-to-github.ps1
   ```
3. אם תתבקש, הכנס את ה-GitHub credentials שלך

## אופציה 2: פקודות ידניות

הרץ את הפקודות הבאות בסדר:

```powershell
# 1. אתחל git repository
git init

# 2. הוסף את כל הקבצים
git add .

# 3. צור commit ראשוני
git commit -m "Initial commit: Coach Scraper application"

# 4. הוסף את ה-remote repository
git remote add origin https://github.com/dorontzurs-commits/coaches-data.git

# 5. הגדר את ה-branch הראשי
git branch -M main

# 6. דחוף ל-GitHub
git push -u origin main
```

## אם יש שגיאות:

### אם ה-repository לא ריק ב-GitHub:
```powershell
git pull origin main --allow-unrelated-histories
git push -u origin main
```

### אם צריך להוסיף authentication:
- GitHub לא מאפשר יותר password authentication
- השתמש ב-Personal Access Token:
  1. לך ל-GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
  2. צור token חדש עם הרשאות `repo`
  3. השתמש ב-token במקום password כשמתבקש

### או השתמש ב-GitHub CLI:
```powershell
# התקן GitHub CLI אם אין
# ואז:
gh auth login
git push -u origin main
```

