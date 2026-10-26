# Pulse Sales Lab — Sales Data Visualization (Task 26)

A lightweight local web dashboard that uses **Python, Pandas and Matplotlib** to visualize sales data. It includes a category bar chart, monthly sales line chart, KPI cards, automatically calculated observations, a transaction preview, and CSV upload. It does **not** use Jupyter Notebook or any web framework.

## Requirements

- Python 3.10 or newer
- Internet is needed only if you want the optional Google Fonts in the design; charts and the dashboard work without them.
- Git is optional for running the app, but needed to push it to GitHub.

## Run on Windows (Terminal / PowerShell)

1. Extract the ZIP. Open the extracted `sales-data-visualization` folder in VS Code.
2. In VS Code, choose **Terminal → New Terminal**.
3. Confirm Python is installed:

   ```powershell
   py --version
   ```

4. Install the two required libraries:

   ```powershell
   py -m pip install -r requirements.txt
   ```

5. Start the web application:

   ```powershell
   py app.py
   ```

6. Open **http://127.0.0.1:8000** in Chrome. Leave the terminal running while you use the site. To stop the server, return to the terminal and press **Ctrl + C**.

If `py` is not recognized, try `python --version`, then use `python -m pip install -r requirements.txt` and `python app.py` instead.

## Use your own CSV

Click **Choose a .csv file** on the dashboard, select a CSV file, then click **Analyze CSV**. The file is processed locally on your computer. To return to the bundled example, click **Restore sample dataset**.

Required columns:

- `Date` (or `Order Date`)
- `Sales` (or `Revenue` / `Amount`)

Recommended columns: `Category`, `Product`, `Profit`, `Quantity`, `Region`. The app recognizes common alternative names and fills optional missing columns with sensible defaults. Excel files are not supported; save your data as `.csv` first.

## Project structure

```text
sales-data-visualization/
├── app.py                         # Local web server, data processing, and chart generation
├── requirements.txt               # Pandas and Matplotlib only
├── README.md                      # Setup and usage instructions
├── .gitignore                     # Excludes uploaded files and generated charts
├── data/
│   └── sales_data.csv             # Bundled sample dataset
├── templates/
│   └── index.html                 # Dashboard layout
└── static/
    ├── style.css                  # Responsive visual design
    └── charts/                    # Charts are generated here when app runs
```

## Push to GitHub

1. Open **https://github.com/new** while signed in to your GitHub account (`PranathiM15`).
2. Repository name: `sales-data-visualization-task26`.
3. Choose **Public** (unless your instructor requests private). Leave **Add a README**, **.gitignore**, and **license** unchecked because this folder already contains its own files.
4. Click **Create repository**. In VS Code's terminal, make sure the current directory is this project folder and run the commands below one at a time:

   ```powershell
   git --version
   git init
   git add .
   git commit -m "Build sales data visualization dashboard"
   git branch -M main
   git remote add origin https://github.com/PranathiM15/sales-data-visualization-task26.git
   git push -u origin main
   ```

5. When Git asks you to sign in, finish the browser sign-in prompt. Do not paste your GitHub password into the terminal.
6. Refresh the repository page to verify the files are visible.

### If a Git command reports an issue

- **`git` is not recognized:** install Git for Windows from https://git-scm.com/download/win, close and reopen VS Code, then check `git --version` again.
- **`remote origin already exists`:** run `git remote set-url origin https://github.com/PranathiM15/sales-data-visualization-task26.git`, then run `git push -u origin main`.
- **`nothing to commit`:** check `git status`; the files may already be committed.
- **Push rejected because the remote contains work:** this can happen if you accidentally added a README when creating the repository. Do not force-push. Tell the instructor or review the remote repository before deciding how to combine the histories.

## What to demonstrate for the task

1. Dashboard KPI cards loaded from Pandas data.
2. Bar chart comparing sales by category.
3. Line chart displaying month-by-month sales trends.
4. At least two data observations shown in the Quick insights panel.
5. CSV upload and reset to sample data.
6. Terminal showing `py app.py` and the GitHub repository containing your project files.

> The bundled sample values are fictional and are included for demonstration and testing.
