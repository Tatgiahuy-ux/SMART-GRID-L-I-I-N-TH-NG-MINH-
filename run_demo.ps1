<#
    Chạy demo Smart Grid (Nhóm 17) bằng một lệnh duy nhất.

    Cách dùng:
        powershell -ExecutionPolicy Bypass -File .\run_demo.ps1
        powershell -ExecutionPolicy Bypass -File .\run_demo.ps1 -Port 8502
        powershell -ExecutionPolicy Bypass -File .\run_demo.ps1 -SkipTests     # khi đã kiểm thử trước đó

    Script tự làm:
      1. Tạo .venv nếu thiếu.
      2. Cài thư viện từ requirements.txt nếu thiếu.
      3. Huấn luyện mô hình nếu chưa có ml\model.pkl.
      4. Chạy kiểm thử nhanh tools\smoke_test.py.
      5. Tạo ~\.streamlit\credentials.toml để Streamlit không hỏi email lần đầu.
      6. Mở Streamlit ở cổng chỉ định.

    Lưu ý: file này phải lưu dạng UTF-8 CÓ BOM để Windows PowerShell 5.1 đọc đúng tiếng Việt.
#>

param(
    [int]$Port = 8501,
    [switch]$SkipTests
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$venvPython = Join-Path $root '.venv\Scripts\python.exe'

function Write-Step([string]$text) {
    Write-Host "`n=== $text ===" -ForegroundColor Cyan
}

Write-Step '0/6 Kiểm tra môi trường Python'
if (-not (Test-Path $venvPython)) {
    $systemPython = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $systemPython) {
        throw 'Không tìm thấy python trên PATH. Cài Python 3.11+ (hoặc bật lại App execution alias) rồi chạy lại.'
    }
    Write-Host "Chưa có .venv, tạo mới bằng $systemPython"
    & $systemPython -m venv --system-site-packages (Join-Path $root '.venv')
}
Write-Host "Python: $venvPython"

Write-Step '1/6 Kiểm tra thư viện'
& $venvPython -c "import streamlit, sklearn, joblib, pandas" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Thiếu thư viện, đang cài từ requirements.txt ...'
    & $venvPython -m pip install --disable-pip-version-check --no-input -r (Join-Path $root 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Cài thư viện thất bại. Kiểm tra kết nối mạng rồi chạy lại.' }
}
else {
    Write-Host 'Đủ thư viện: streamlit, scikit-learn, joblib, pandas.'
}

Write-Step '2/6 Kiểm tra mô hình ML'
$modelPath = Join-Path $root 'ml\model.pkl'
if (Test-Path $modelPath) {
    Write-Host "Đã có mô hình: $modelPath"
}
else {
    Write-Host 'Chưa có ml\model.pkl, huấn luyện lại từ data\power_consumption.csv ...'
    & $venvPython (Join-Path $root 'ml\train_model.py')
    if ($LASTEXITCODE -ne 0) { throw 'Huấn luyện thất bại.' }
}

if ($SkipTests) {
    Write-Step '3/6 Bỏ qua kiểm thử (-SkipTests)'
}
else {
    Write-Step '3/6 Kiểm thử nhanh luồng tích hợp'
    & $venvPython (Join-Path $root 'tools\smoke_test.py')
    if ($LASTEXITCODE -ne 0) { throw 'smoke_test.py thất bại, xem log phía trên trước khi demo.' }
}

Write-Step '4/6 Chuẩn bị cấu hình Streamlit'
$credDir = Join-Path $env:USERPROFILE '.streamlit'
$credFile = Join-Path $credDir 'credentials.toml'
if (Test-Path $credFile) {
    Write-Host "Đã có $credFile"
}
else {
    New-Item -ItemType Directory -Path $credDir -Force | Out-Null
    Set-Content -Path $credFile -Value "[general]`nemail = `"`"" -Encoding ascii
    Write-Host "Đã tạo $credFile (để Streamlit không hỏi email ở lần chạy đầu)."
}

Write-Step "5/6 Kiểm tra cổng $Port"
$portBusy = $false
try {
    $portBusy = Test-NetConnection -ComputerName '127.0.0.1' -Port $Port -InformationLevel Quiet -WarningAction SilentlyContinue
}
catch {
    $portBusy = $false
}
if ($portBusy) {
    throw "Cổng $Port đang bận. Chạy lại với cổng khác, ví dụ: .\run_demo.ps1 -Port 8502"
}
Write-Host "Cổng $Port đang trống."

Write-Step '6/6 Khởi động giao diện Streamlit'
Write-Host "Địa chỉ demo: http://localhost:$Port" -ForegroundColor Green
Write-Host 'Nhấn Ctrl + C trong cửa sổ này để dừng demo.' -ForegroundColor DarkGray
& $venvPython -m streamlit run (Join-Path $root 'app.py') --server.port $Port --browser.gatherUsageStats false
